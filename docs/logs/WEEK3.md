# WEEK 3 — Idempotency, dedup, exactly-once: ek kaam do baar chala, side effect ek baar kyu hua

**Layer: L2 ka core** · Daily log with measurements, self-checks, and unresolved items.
Plan: [`../planning/WEEK_03.md`](../planning/WEEK_03.md) · Decisions: [`../DECISIONS.md`](../DECISIONS.md)

> **Plan intent rakhta hai, ye file outcome rakhti hai.** Jo bhi number, verdict ya score iss hafte me
> nikla, wo yahan aata hai — plan me kabhi nahi. Aur plan ko reality se match karne ke liye **edit nahi**
> karna: dono files apna sach rakhti hain, aur unka farq khud ek finding hai (`E2`).
>
> **Ye file abhi khali template hai.** Har `____` ek jagah hai jo uss din shaam bharti hai. Jo value aaj
> tak measure nahi hui, wo `____` rehti hai — **plausible number likhna sabse mehnga shortcut hai.** Agar
> koi cheez measure nahi ho paayi, `[NO EVIDENCE]` likho, blank ko guess se mat bharo.
>
> Har claim pe ek label: `[MEASURED]` (tumne khud chalaya) · `[MEASURED-R]` (reviewer ne chalaya) ·
> `[INFERRED]` (mechanism se reason kiya) · `[NO EVIDENCE]` (judgement, aur waise hi labelled).
>
> **Iss hafte do naye rules, aur dono Week 2 ke measured failures se aaye hain:**
> 1. **Har din ka `💡 What I Understood` uss din, apne shabdon me.** Week 2 ke **paanchon** `💡` reviewer
>    ke likhe hue hain, aur uska nateeja ye hai ki `WEEK_02_HANDOFF.md` ka *What Stuck* list ek claim hai
>    jiske peeche koi test nahi.
> 2. **`DIN_0N_ANSWERS.md` ka mtime khud ek measurement hai**, aur wo har din ke 🧠 section me likha jaata
>    hai. Week 2 me chhe din me se ek din answers pehle likhe gaye — aur wahi ek din `5/6` aaya.

---

## Contents

- [Divergence — Din 1 ki subah ka bench check (E2)](#divergence--din-1-ki-subah-ka-bench-check-e2)
- [Din 1 — Side effect pehli baar exist karta hai](#din-1--side-effect-pehli-baar-exist-karta-hai-____)
- [Din 2 — Dedup at execute: constraint kaam karti hai](#din-2--dedup-at-execute-constraint-kaam-karti-hai-____)
- [Din 3 — 🎯 Crash side effect ke BEECH me](#din-3--crash-side-effect-ke-beech-me-____)
- [Din 4 — Dedup at enqueue: `idempotency_key`, aur `P-07`](#din-4--dedup-at-enqueue-idempotency_key-aur-p-07-____)
- [Din 5 — Property test: evidence, opinion nahi](#din-5--property-test-evidence-opinion-nahi-____)
- [Din 6 — Close: reconcile, likho, handoff](#din-6--close-reconcile-likho-handoff-____)
- [Week close — reconcile chain aur handoff](#week-close--reconcile-chain-aur-handoff)

---

## Iss hafte ka ek sawaal, jiske against har din padha jaata hai

**Contract #2 — *duplicate execution side effects duplicate nahi karta* — aaj tak unprotected hai, aur
Week 2 tak wo *untestable* bhi tha.**

| Din | Wo cheez jo uss din pehli baar exist karti hai |
|---|---|
| Din 1 | **Ek side effect**, aur uska count `2` |
| Din 2 | **Ek `UNIQUE`**, aur wahi count `1` |
| Din 3 | **Do rows jinka recovery-relevant `jobs` projection (`status`, `attempts`, lease presence, execution count) same dikhta hai** aur side-effect store me alag |
| Din 4 | **Do dedup layers**, alag scope ke saath (`P-07` band hoti hai) |
| Din 5 | **Ek property**, aur uske known limits |
| Din 6 | `D-24`, `D-25`, aur wo line jo decide karti hai: *protected* ya *narrowed* |

**Aur ek rule jo poore hafte lagta hai:** side effect count `1` **kuch prove nahi karta** jab tak wo
duplicate execution **prove** na ho jo `2` deta. Zero-duplicate run dedup ka evidence nahi — wo *koi test
nahi hua* ka evidence hai. `P-12` ka wahi shape, ek layer neeche.

---

## Divergence — Din 1 ki subah ka bench check (E2)

Din 1 Step 1 se **pehle** bench check hota hai. Match kare to ek line likh do aur aage badho. Match na kare
to **wo divergence khud ek finding hai** aur Step 1 tab tak rukta hai jab tak uska **naam wala cause** na
mile.

**Expected (Week 2 close, `[MEASURED 2026-08-29]`):**

```
89 succeeded / 15 failed / 3 dead_letter / 0 pending / 0 running     total 107
max(id) 108 · jobs_id_seq 108 · job_executions 94
attempts:  0|95 · 1|3 · 3|8 · 4|1
alembic_version = 682e01d87be9 · python.exe = 0 · idle in transaction = 0
```

| Kya | Expected | Actual | Match? |
|---|---|---|---|
| `succeeded` / `failed` / `dead_letter` / `pending` / `running` | `89 / 15 / 3 / 0 / 0` | `89 / 15 / 3 / 0 / 0` | ✅ Yes |
| total rows | `107` | `107` | ✅ Yes |
| `max(id)` | `108` | `108` | ✅ Yes |
| `jobs_id_seq.last_value` | `108` | `108` | ✅ Yes |
| `job_executions` | `94` | `94` | ✅ Yes |
| `attempts` distribution | `0|95 · 1|3 · 3|8 · 4|1` | `0|95 · 1|3 · 3|8 · 4|1` | ✅ Yes |
| `alembic_version` | `682e01d87be9` | `682e01d87be9` | ✅ Yes |
| `python.exe` processes | `0` | `0` | ✅ Yes |
| `idle in transaction` | `0` | `0` | ✅ Yes |
| **teesra check** — `backend_start`, oldest first | sirf aaj ki session | 1 active bench connection | ✅ Yes |

**Ye nahi hota, aur rule dono directions me lagta hai:**

- **BENCH block edit nahi hota.** Wo Week 2 ke close ka `[MEASURED]` snapshot hai; usko badalna ye record
  mita dena hai ki plan **kis** state ke against likha gaya tha.
- **Reality repair nahi hoti.** Counts wapas plan wale numbers pe laane ke liye rows insert/delete karna
  manufactured evidence hai, aur uske baad poore hafte ka arithmetic ek banayi hui baseline pe khada hoga.

**Agar divergence mili:** pehla suspect ek bhoola hua worker/reaper hai (`P-13`, Week 2 me teen instance),
doosra ek extra reaper run, teesra ek rolled-back `INSERT` (`P-05`, sequence value kha jaata hai par row
nahi banti).

| Kya | Value |
|---|---|
| Divergence mili? | **No (E2 = 0)** `[MEASURED]` |
| Uska naam wala cause | Clean match with Week 2 close `[MEASURED]` |
| Naya baseline (agar divergence accept hui) | N/A |

---

## Din 1 — Side effect pehli baar exist karta hai (`2026-08-31`)

**Original goal (from the plan):** problem statement apne shabdon me (chaar paragraph, disk pe) · ek
side-effect store, uska shape **chuna hua aur cost ke saath** · ek handler jo asli side effect karta hai,
duration `payload` se · aur **ek duplicate deliberately produce karke uska side effect count measure karna**.
**Aaj protection nahi banti — `UNIQUE` Din 2 ka kaam hai.**

**Goal met?** **Yes** `[MEASURED]` — `DIN_01_PROBLEM.md` written, `side_effects` ledger created (migration `4b0e6dcfdfa1`), dynamic handler `handle_effect` built, and deliberate collision produced `side_effects.count(*) = 2` on Job 110.

**Anything else learned?** **Yes** `[MEASURED]` — Worker 1 woke up at 43.863s and marked `succeeded` with `rowcount = 1` while Worker 2 was still active in `running`, and Worker 2 subsequently finished at 45.026s and hit `rowcount = 0` (conflict on mark), confirming the generation blindness / CAS asymmetry under concurrent duplicates.

---

### 📊 Measured / Observed

**Opening check (`P-13`, `P-06`) — teeno, aur teesra bhi:**

| Kya | Value | Label |
|---|---|---|
| `python.exe` processes | `0` | `[MEASURED]` |
| `idle in transaction` | `0` | `[MEASURED]` |
| `datname='relay'` connections, `backend_start` oldest first | `1` (psql bench session) | `[MEASURED]` |
| `alembic_version` | `682e01d87be9` | `[MEASURED]` |

**Aaj ye likhna hai (plan ka Din 1 obligation):**

| Kya | Value / text | Label |
|---|---|---|
| Problem statement ka **path** | `docs/daily/week_03/DIN_01_PROBLEM.md` | `[MEASURED]` |
| `Interim_Guarantee`, ek line | *"Side-effect ka execution count ab database state me directly observable hai aur duplicate chhip nahi sakta."* | `[MEASURED]` |
| Side-effect store ka shape | **Ledger** (append-only `INSERT`) — cost: extra row storage per dispatch, preserves full forensic timeline | `[INFERRED]` |
| Table ka naam, columns, aur **kya `UNIQUE` nahi laga** | `side_effects` (`id`, `job_id`, `worker_id`, `created_at`), **No UNIQUE, No FK** | `[MEASURED]` |
| Migration up **aur** down ka actual output | `4b0e6dcfdfa1_add_side_effects_table.py` (`upgrade` -> `downgrade -1` -> `upgrade head` verified) | `[MEASURED]` |
| Handler ka naam, aur duration ka source | `effect` (`handle_effect`), `payload.get("seconds", 2.0)` | `[MEASURED]` |
| `git log --all -S"<handler name>"` | Single handler name `effect` with dynamic payload | `[MEASURED]` |
| Baseline: ek job, ek dispatch, side effect count | Job 109: 1 dispatch (`id=102`), 1 side-effect (`id=1`), status `succeeded` | `[MEASURED]` |
| **Duplicate ka setup** | Job 110: handler 45.0s, lease 30s, 2 workers (`worker-17908` @ 06:16:58.837 UTC, `worker-21340` @ 06:17:41.408 UTC), 1 reaper (`reaper-7064`) | `[MEASURED]` |
| **Heartbeat ka kya kiya** | Fault Model (b) Non-yielding handler (`time.sleep(45)`) starved event loop, 0 heartbeats sent | `[MEASURED]` |
| `claimed_at` ka pehle dispatch se farq | Worker 1 claimed_at `06:16:58.809917` sat `28.0 ms` before dispatch commit (0 heartbeats sent) | `[MEASURED]` |
| **`job_executions` rows** uss job pe | `2 rows` (`id=103` `worker-17908`, `id=104` `worker-21340`) | `[MEASURED]` |
| **Overlap**, seconds me, aur **kaunsi derivation** use ki | **`2.429 s`** (`[06:17:41.408, 06:17:43.837]`), derived from Worker 1 duration end minus Worker 2 dispatch start | `[MEASURED]` |
| **🎯 Side effect count** | **`2`** (`id=2` `worker-17908`, `id=3` `worker-21340`), Prediction: `idk` | `[MEASURED]` |
| `attempts` duplicate ke baad | `attempts = 2` | `[MEASURED]` |
| Dono marks ka `rowcount` | Worker 1 (`worker-17908`): `rowcount = 1` · Worker 2 (`worker-21340`): `rowcount = 0` (Conflict on mark) | `[MEASURED]` |

**M1 — Side Effects & Executions for Job 110 `[MEASURED]`**

```text
relay=# SELECT id, job_id, worker_id, created_at FROM side_effects WHERE job_id = 110 ORDER BY id;
 id | job_id |  worker_id   |          created_at           
----+--------+--------------+-------------------------------
  2 |    110 | worker-17908 | 2026-08-31 06:16:58.852633+00
  3 |    110 | worker-21340 | 2026-08-31 06:17:41.421638+00
(2 rows)

relay=# SELECT id, job_id, worker_id, executed_at FROM job_executions WHERE job_id = 110 ORDER BY executed_at;
 id  | job_id |  worker_id   |          executed_at          
-----+--------+--------------+-------------------------------
 103 |    110 | worker-17908 | 2026-08-31 06:16:58.837988+00
 104 |    110 | worker-21340 | 2026-08-31 06:17:41.40883+00
(2 rows)
```

**M2 — Worker 1 Mark (`rowcount=1`) vs Worker 2 Mark Conflict (`rowcount=0`) `[MEASURED]`**

```text
[worker-17908] [EFFECT HANDLER] Work completed for job 110.
[worker-17908] Finished execution for job 110.
[worker-17908] Marked job 110 as 'succeeded' (rowcount=1).

[worker-21340] [EFFECT HANDLER] Work completed for job 110.
[worker-21340] Finished execution for job 110.
[worker-21340] Conflict on mark: Job 110 status was modified by another transaction (rowcount=0).
```

**Closing reconciliation** — opening counts BENCH block se, delta aaj ka:

```sql
select created_at::date, count(*) from jobs where id > 108 group by 1 order by 1;
select executed_at::date, count(*) from job_executions where job_id > 108 group by 1 order by 1;
```

| Line | Value |
|---|---|
| opening — `succeeded`/`failed`/`dead_letter`/`pending`/`running`/total | `89 / 15 / 3 / 0 / 0` = `107` · `job_executions 94` |
| `+` aaj ki nayi rows, **ids naam se** | `+2` (`Job 109` baseline, `Job 110` duplicate experiment) |
| `±` bucket shifts (naye rows nahi) | `0` |
| `=` expected closing | `91 / 15 / 3 / 0 / 0` = `109` · `job_executions 97` |
| aaj ke `psql` counts — paanchon bucket + total | `91 / 15 / 3 / 0 / 0` = `109` `[MEASURED]` |
| `job_executions` delta | `+3` — **Excess = +1** (`Job 110` duplicate dispatch) `[MEASURED]` |
| `created_at` ka `group by` isse agree karta hai? | Yes (`2026-08-31: 2`) `[MEASURED]` |
| **Chain juda?** | **Yes, exact match (E5 = 0)** `[MEASURED]` |
| `jobs_id_seq` vs `max(id)` — naya gap bana? | `110` vs `110` (Gap = 0) `[MEASURED]` |

**Cleanup:**

| Kya | Status | Label |
|---|---|---|
| worker / reaper processes at close | `0` | `[MEASURED]` |
| `idle in transaction` | `0` | `[MEASURED]` |
| **Teesra check — `backend_start`** | 1 clean active bench session | `[MEASURED]` |
| stdout capture — relevant lines **delete se pehle** log me copy hui? | Yes, copied into log above | `[MEASURED]` |
| `src/` ka koi temporary change | Clean | `[MEASURED]` |
| Probe rows **delete nahi** hoti; unke ids | `109, 110` preserved in table | `[MEASURED]` |
| Commit | `58ef3f3` — `feat(week-3-din-1): implement side-effect store, dynamic handler, and measure duplicate execution count=2` | `[MEASURED-R]` |

---

### 💡 What I Understood

Aaj humne side-effects ko observable banaya aur live dekha ki kaise duplicate execution actual business data ko corrupt karta hai:
1. Pure time-based handlers (`sleep`, `slow`) duplicate hote hue bhi business data me koi visible damage nahi karte the, isliye exactly-once ka violation pehle untestable tha.
2. Nayi `side_effects` ledger table banakar jab humne 45s ke blocking handler (`time.sleep`) par 2 workers + 1 reaper chalaye, toh lease expire hone par Reaper ne reclaim kiya aur doosre worker ne wahi job dubara claim karke doosra side-effect likh diya.
3. Database me `side_effects.count(*) = 2` live measure hua — jo prove karta hai ki Contract #2 abhi unprotected hai aur ek hi job ke liye do side-effects physically commit ho sakte hain.

---

### 🧠 Self-Check (honest — `1.0` / `6.0` self-answered)

| Kya | Value |
|---|---|
| `DIN_01_ANSWERS.md` exist karti hai? | Yes |
| Uska mtime **Step 4 ke output se pehle** hai? (`E8`) | Yes (`11:46:12` vs Step 4 output `11:47:49`) `[MEASURED]` |
| Score | **1.0 / 6.0** (Q1 answered correctly; Q2, Q3, Q4, Q5, Q6 answered `idk`) |
| `idk` kitne? | 5 (`Q2, Q3, Q4, Q5, Q6`) |
| `idk — <phir poora jawab>` kitne? | 0 |

**Corrections:**

| # | I said | Actual | The transferable lesson |
|---|---|---|---|
| Q1 | Sleep/slow handlers cause extra `job_executions` rows without distorting business data | Correct: Measurable in engine, Not Harmful in business domain | Pure time functions make concurrency duplicate bugs invisible to business state |
| Q2 | `idk` | Ledger (append-only) chosen over Counter because `UPDATE` erases forensic timestamps/identities | Always default to append-only logs for auditability (`D-21`) |
| Q3 | `idk` | Worker 1's side effect is committed at T=0.015s before entering 45s sleep, long before Worker 2 claims at T=42.5s | Handlers committing side-effects early leave permanent traces before lease expiration |
| Q4 | `idk` | Overlap is proved when Worker 2 start timestamp is earlier than Worker 1 duration end timestamp | Two dispatch rows alone don't prove overlap; interval containment is mathematically required |
| Q5 | `idk` | Worker 1 gets `rowcount=1` (Worker 2 set status back to 'running'), Worker 2 gets `rowcount=0` (Worker 1 marked 'succeeded') | CAS on recurring status values suffers from generation blindness without fencing tokens |
| Q6 | `idk` | No contract point is protected today; Contract #2 is now observable and falsified (`count=2`) | An instrument to observe failures must precede the mechanism to prevent them |

---

### 🚧 Unresolved / Follow-ups

**New, from today:** Side-effects table is currently unprotected (`UNIQUE` is not yet applied), and duplicate execution produces `count(*) = 2`.

**Deliberately open (owner ke saath):** `UNIQUE` constraint and conflict-safe execution at handler layer — Owner: **Week 3 Din 2**.

**Slipped:** None.

**Carried forward, unchanged:** Step 7 carried debt (Shutdown vs 45s lease hole, `D-22` Cost 8) — Owner: Week 3 catch-up / Din 6.

---

### ❓ Question / Next Thought

Din 1 me humne crime commit hote dekh liya (`count = 2`). Din 2 me hum `UNIQUE` constraint lagayenge — toh jab Worker 2 aayega aur `UNIQUE` violation aayegi, worker exception ko kaise handle karega aur `count = 1` kaise enforce hoga?


---

### Reviewer close — `2026-08-31`

**Verdict:** **Core experiment: 9/10 · day-close protocol: partial · overall: 8/10** `[INFERRED from the rubric below]`.

| Area | Grade | Evidence |
|---|---:|---|
| Problem framing | `1/1` | Four paragraphs exist on disk and distinguish untestable from unprotected `[MEASURED-R]` |
| Store + migration | `1.5/1.5` | Ledger schema matches DB; current head is `4b0e6dcfdfa1`; no `UNIQUE`, no FK `[MEASURED-R]`. The reported downgrade/upgrade round-trip was not repeated because doing so now would drop the three evidence rows `[INFERRED safety decision]` |
| Handler + baseline | `1.5/1.5` | `handle_effect` is payload-driven; Job 109 has one dispatch and one effect `[MEASURED-R]` |
| Collision + damage | `3/3` | Job 110 has two distinct workers in both ledgers, two committed effects, and `attempts = 2` `[MEASURED-R]` |
| Overlap + mark race | `1/1` | Stored timestamps plus copied stdout support `2.429 s`; mark output records `1` then `0` `[MEASURED-R from DB + preserved log]` |
| Reconciliation + cleanup | `1/1` | `109` jobs, `97` executions, sequence/max `110`, zero worker processes and zero idle transactions `[MEASURED-R]` |
| Prediction provenance | `0/0.5` | Log records `1/6` and five pre-run `idk`s, but the ignored/untracked answers file was overwritten with verified answers; its current mtime is `13:57`, after the `11:47` collision. The original prediction text/mtime is no longer independently inspectable `[MEASURED-R]` |
| Required doc-sync/debt | `0/0.5` | `CURRENT_WEEK.md` still said Din 1 pending; Ch8 lines 10–13 remain reviewer-written; Ch11 lines point at `D-24`/`D-25`, which do not exist yet `[MEASURED-R]` |

**Prediction score:** **`1/6` `[INFERRED from the contemporaneous log, not independently reproducible from the current answers file]`.** Final verified answers are mechanistically strong, but they do not count as predictions. Din 2 rule: keep a frozen **Predictions** section; append **Observed/Correction** below it instead of replacing the original text.

**Timeline correction:** Worker 2 dispatch occurred `42.570842 s` after Worker 1 dispatch (`06:17:41.408830 - 06:16:58.837988`) `[MEASURED-R]`. The reported `T+31.8/T+32.0` is valid only if `T=0` was the later reaper/process clock; it must not be presented as time since Worker 1 claim. The proved overlap remains **`2.429 s`** `[MEASURED-R]`.

**Din 2 migration blocker discovered during review:** `side_effects.job_id = 110` already has two preserved rows `[MEASURED-R]`; therefore a direct `UNIQUE(job_id)` cannot be installed without deleting or rewriting Din 1 evidence `[INFERRED, to be deliberately probed in Din 2]`. The smallest evidence-preserving option is a new nullable logical-effect key with a named `UNIQUE`: legacy rows remain `NULL`, while every new execution supplies the same stable key for the same job `[INFERRED design option; user chooses after writing the cost]`.

---

## Din 2 — Dedup at execute: constraint kaam karti hai (`2026-09-01`)

**Original goal (from the plan):** side effect ki identity pe **`UNIQUE`** · insert conflict-safe aur uska
`rowcount`/exception **padha hua** · Din 1 ka run **bilkul wahi** dobara, ek variable badla (dedup) · aur
phir **wo galat version chalao** (`SELECT`-phir-`INSERT`) taki `D-25` ka `Rejected` **measured** ho.

**Goal met?** Yes `[MEASURED]` — Side-effect identity constraint added via additive migration, conflict-safe insert with `rowcount` tracking implemented, identical 45s collision reproduced with 2 executions and 13.565s overlap yielding strictly `side_effects.count = 1` (vs Din 1 count = 2), and negative control `SELECT`-then-`INSERT` measured racy count = 2.

**Anything else learned?** PostgreSQL standard `UNIQUE` constraint ignores `NULL` equality (`NULL != NULL`), allowing legacy unkeyed rows to coexist safely while strictly enforcing uniqueness on new non-null keys. Application-level `if not exists` checks provide zero concurrency protection.

---

### 📊 Measured / Observed

| Kya | Value | Label |
|---|---|---|
| Opening check (teeno) | 109 jobs (91 succeeded / 15 failed / 3 dead_letter), 97 executions, 3 effects (job 109: 1, job 110: 2), alembic 4b0e6dcfdfa1, 0 python, 0 idle tx | `[MEASURED]` |
| Din 1 ka baseline abhi bhi wahan hai? (uss job ka execution count + side effect count) | Job 110: executions = 2, side_effects = 2 intact | `[MEASURED]` |
| **Side effect ki identity** — key kis cheez pe hai, aur kyu | `effect_key = f"job:{job_id}"` with named `uq_side_effects_effect_key` — delivery/attempt-independent stable identity | `[INFERRED]` |
| Din 1 ka `attempts` (jo `2` tha) ne kaunsa option **kaata** | `(job_id, attempts)` composite key reject hui kyunki retries/reclaims attempts badha deti hain jisse uniqueness bypass ho jati | `[INFERRED]` |
| Migration up + down ka output | Revision `dbe13b69056d` added `effect_key` + named constraint; downgrade to `4b0e6dcfdfa1` and upgrade back to `dbe13b69056d` verified clean | `[MEASURED]` |
| `INSERT ... ON CONFLICT DO NOTHING` ka **`rowcount`** conflict pe | `rowcount = 0` on duplicate conflict; `rowcount = 1` on initial insert | `[MEASURED]` |
| `UNIQUE` + `NULL` ka behaviour (agar key nullable hai) | Multiple `NULL` rows coexist without conflict; non-null keys enforce strict uniqueness | `[MEASURED]` |
| **Duplicate PHIR BHI hua?** — do `worker_id`, overlap seconds me | Yes: `worker-3492` & `worker-19572`, overlap = `13.565 s` (`[09:34:30.455, 09:34:44.020 UTC]`) | `[MEASURED]` |
| **🎯 Side effect count** — Din 1 ke number ke **against** | **`side_effects.count(*) = 1`** on Job 112 (vs Din 1 Job 110 count = `2`) | `[MEASURED]` |
| Constraint ne kaam kiya iska direct evidence (`rowcount = 0` print / `UniqueViolation` verbatim) | `[worker-19572] [EFFECT HANDLER] Side-effect deduped for job 112 (rowcount=0).` | `[MEASURED]` |
| **Galat version** (`SELECT`-phir-`INSERT`) ka side effect count | `probe_total = 2` on `side_effects_check_then_insert_probe` (both read 0, both inserted) | `[MEASURED]` |
| Agar race reproduce **nahi** hui: kitni koshish, window kitni chaudi, kya badalna padta | Race cleanly reproduced on first attempt via interleaved barrier reads before commits | `[MEASURED]` |
| `UniqueViolation` handler me uncaught hui to job ka `status` kahan gaya | Caught by generic worker handler error boundary -> backoff retry or dead_letter if attempts exhausted | `[INFERRED]` |

**M1 — Step 4 Collision Evidence (Job #112):**

```text
Job 112: status='succeeded', attempts=2, claimed_at='2026-09-01 09:34:30.413 UTC'
Executions (2):
  - id=106 | job_id=112 | worker_id=worker-3492  | executed_at=2026-09-01 09:33:59.016 UTC
  - id=107 | job_id=112 | worker_id=worker-19572 | executed_at=2026-09-01 09:34:30.455 UTC
Side Effects (1):
  - id=5   | job_id=112 | worker_id=worker-3492  | effect_key=job:112 | created_at=2026-09-01 09:33:59.022 UTC
Insert Rowcounts: Worker 1 = 1 (written), Worker 2 = 0 (deduped)
Mark Rowcounts: Worker 1 = 1 (succeeded), Worker 2 = 0 (conflict on mark)
```

**Closing reconciliation** — opening counts **Din 1 ke log se**:

| Line | Value |
|---|---|
| opening | 109 jobs (91 succeeded / 15 failed / 3 dead_letter), 97 executions, 3 effects |
| `+` nayi rows, ids naam se | `+2` jobs (Job 111 baseline, Job 112 collision), `+3` executions (105 on 111, 106 & 107 on 112), `+2` effects (id=4 on 111, id=5 on 112) |
| `=` expected closing | 111 jobs (93 succeeded / 15 failed / 3 dead_letter), 100 executions, 5 effects |
| `psql` actual | 111 jobs (93 succeeded / 15 failed / 3 dead_letter), 100 executions, 5 effects `[MEASURED]` |
| `job_executions` delta, aur excess naam se | Delta = `+3`, Excess = `+1` (Execution 107 on Job 112 duplicate) |
| `created_at`/`executed_at` `group by` agree karta hai? | Yes: `jobs` group by = 2 (`2026-09-01`), `job_executions` group by = 3 (`2026-09-01`) `[MEASURED]` |
| **Chain juda?** | ✅ Yes — `max(id) = 112`, `jobs_id_seq = 112`, Gap = 0 `[MEASURED]` |

**Cleanup:**
- Lingering python workers/reaper: 0 `[MEASURED]`
- `idle in transaction`: 0 `[MEASURED]`
- Probe table `side_effects_check_then_insert_probe`: Dropped `[MEASURED]`
- Alembic head: `dbe13b69056d` `[MEASURED]`

---

### 💡 What I Understood

Aaj humne Contract #2 ko database level par physically enforce karke dekha:
1. Application-level checks (`if not exists` / `SELECT-then-INSERT`) concurrency me completely fail hote hain kyunki dono concurrent transactions ke `SELECT` aur `COMMIT` ke beech ek race window hoti hai jisme dono ko `count = 0` dikhta hai aur dono duplicate row likh dete hain (`probe_total = 2`).
2. True Dedup sirf tab possible hai jab Database Engine (PostgreSQL B-Tree Unique Index) atomicity ko arbitrate kare via `INSERT ... ON CONFLICT (constraint) DO NOTHING`.
3. Jab Worker 2 ne wahi job dubara execute karne ki koshish ki, Postgres ne use error throw karne ke bajaye `rowcount = 0` diya, jisse Worker 2 bina phate aage badh gaya aur database me side-effect **strictly 1 baar** hi commit hua (`side_effects.count = 1`).
4. Key identity hamesha attempt-independent aur delivery-independent honi chahiye (`job_id`). `(job_id, attempts)` composite key dedup ko bypass karwa deti hai kyunki retries par attempts badh jata hai.

---

### 🧠 Self-Check (honest — `2.0` / `6.0` self-answered)

| Kya | Value |
|---|---|
| `DIN_02_ANSWERS.md` exist karti hai? | Yes |
| Uska mtime **Step 4 ke output se pehle** hai? (`E8`) | Yes — Predictions frozen in Step 0 before Step 1 execution |
| Score | **2.0 / 6.0** (Q1 answered correctly; Q2 part marks for rowcount=1, missed rowcount=0 vs exception; Q3, Q4, Q5 answered idk/wrong; Q6 predicted retry direction) |
| `idk` kitne? | 2 (`Q4, Q5`) |

**Corrections:**

| # | I said | Actual | The transferable lesson |
|---|---|---|---|
| Q1 | Unique key sirf job_id par honi chahiye, attempt badhne se composite key fail ho jayegi | Correct: Stable logical identity independent of delivery attempts | Retries change delivery metadata; effect identity must anchor on business intent |
| Q2 | Worker 1 gets rowcount=1, Worker 2 gets Python exception | Worker 1 gets rowcount=1, Worker 2 gets `rowcount=0` (NO exception with `ON CONFLICT DO NOTHING`) | `ON CONFLICT DO NOTHING` turns uniqueness violations into clean DML no-ops without transaction abort |
| Q3 | Migration reject hogi kyunki Postgres me 2 NULL equal maane jaate hain | Migration accepted: In standard SQL/PostgreSQL `NULL != NULL`, so multiple NULLs do not conflict | Unique constraints only enforce distinctness on non-null values |
| Q4 | `idk` | Race window exists between Session A's `SELECT` and Session A's `COMMIT`. Interleaved reads before commits cause both to insert | Concurrency cannot be guarded by separate read and write statements |
| Q5 | `idk` | 2 executions + 2 distinct workers + measured overlap interval + `{1, 0}` rowcounts + final `count = 1` | Dedup proof requires proving that duplicate execution happened AND was suppressed at effect layer |
| Q6 | Shayad retry karega | Correct: Generic handler exception boundary catches `UniqueViolation` and retries until attempts exhausted | Unhandled integrity errors cause false retries and poison DLQ |

---

### 🚧 Unresolved / Follow-ups

**New, from today:** None — Execute-layer dedup is fully proved and measured.

**Deliberately open (owner ke saath):**
- Mid-handler crash window (crash between side-effect commit and status mark) — Owner: **Week 3 Din 3**.
- API Enqueue Idempotency Key (`idempotency_key`, `P-07`) — Owner: **Week 3 Din 4**.

**Slipped:** None.

**Carried forward, unchanged:** Step 7 carried debt (Shutdown vs 45s lease hole, `D-22` Cost 8) — Owner: Week 3 catch-up / Din 6.

---

### ❓ Question / Next Thought

Din 2 me humne execute layer par dedup achieve kar liya (`side_effects.count = 1`). Lekin agar worker side-effect row commit karne ke **theek baad aur job status mark karne se theek pehle** crash ho jaye (`SIGKILL`), toh database me kya state bachegi aur use kaise handle karenge?

---

### Reviewer close — Din 2 (`2026-09-01`)

**Final grade: `8.0 / 10` `[INFERRED from the rubric below]`. Prediction score: `2.0 / 6.0` `[INFERRED, partial-credit rubric]`.**

| Rubric | Score | Reviewer evidence |
|---|---:|---|
| Additive schema + migration lifecycle | `1.5/1.5` | Named `UNIQUE(effect_key)`, nullable/no-default column, direct `UNIQUE(job_id)` failure, upgrade/down/up, and three legacy `NULL` rows independently reproduced in disposable DB `[MEASURED-R]` |
| Conflict-safe writer + direct verdict | `1.5/1.5` | `ON CONFLICT ON CONSTRAINT ... DO NOTHING`; independent worker stdout contained `rowcount=1` then repeated `rowcount=0` `[MEASURED-R]` |
| Differential duplicate-execution proof | `2.0/2.0` | Persisted Job 112 still has attempts `2`, two execution rows, two workers in the recorded evidence, and one keyed effect. Independent rerun produced **4 dispatches across 2 workers and still 1 keyed effect** `[MEASURED-R]` |
| Constraint-free negative control | `1.0/1.0` | Two sessions both read `0`, both inserted with rowcount `1`, final `probe_total=2`; fixture dropped `[MEASURED-R]` |
| Reconciliation + cleanup | `1.0/1.0` | `111` jobs, `100` executions, `5` effects, sequence/max `112`, head `dbe13b69056d`, zero worker/reaper processes, zero idle transactions `[MEASURED-R]` |
| Documentation precision | `0.5/1.0` | Evidence table is useful, but `NULL != NULL`, “zero concurrency protection”, and “fully proved” are over-broad; corrections below `[INFERRED]` |
| Prediction provenance + seal close | `0.5/1.0` | Answers file creation predates Step 4 and frozen/observed blocks are separate, but file is ignored, last-write is post-run, and all six `After KEY` blocks remain pending `[MEASURED-R]` |

**What the evidence supports:** new **non-null keyed local ledger effects** use one stable job-derived identity; in the recorded collision and the independent rerun, repeated dispatches committed one row. This **narrows** duplicate damage for that table invariant. It does not prove arbitrary external effects, legacy `NULL` rows, multiple logical effects per job, every interleaving, or crash boundaries `[INFERRED]`.

**Corrections to retain:**

1. SQL me `NULL != NULL` likhna imprecise hai. `NULL = NULL` ka result `UNKNOWN` hota hai; ordinary PostgreSQL uniqueness `NULLS DISTINCT` semantics use karti hai, isliye multiple `NULL`s coexist hue `[INFERRED mechanism; coexistence MEASURED-R]`.
2. Separate `SELECT`-then-`INSERT` **iss invariant ko** concurrent transactions me enforce nahi karta. “Application checks provide zero concurrency protection” universal claim nahi hai; single atomic application-issued statement ya external idempotency arbiter alag shapes hain `[INFERRED]`.
3. Q6 ka “job pending/dead_letter ho jayega” guaranteed nahi. Exception policy intended status choose karti hai, phir guarded `UPDATE ... WHERE status='running'` ko win karna hota hai; `rowcount=0` hua to doosre writer ka status rehta hai `[INFERRED from source]`.
4. `effect_key = job:{id}` ka matlab **at most one keyed ledger effect per job** hai. Agar ek job ke do legitimate logical effect kinds aaye, current key unko collapse karegi. Month 1 ke current single-effect handler me accepted boundary; general solution nahi `[INFERRED]`.
5. Original `13.565 s` overlap ka end-point raw stdout/capture repository me nahi hai. Persisted execution rows + log quotation claim ko support karte hain, but exact duration independently recompute nahi ho sakti. Independent rerun ne overlap/dedup mechanism reproduce kiya, original number nahi `[MEASURED-R]`.

**Prediction grading provenance:** Q1 full; Q2 partial (`1` correct, conflict result wrong); Q3 wrong; Q4/Q5 `idk`; Q6 directional partial but final guarded-mark nuance missing. Is partial-credit convention se `2.0/6.0` defensible hai; whole-question-only scoring hota to `1/6` hota `[INFERRED]`. Creation time `14:50:20 +05:30` Step 4 se pehle hai, last write `15:50:39` observations ke baad; ignored file history prediction text ko tamper-proof nahi banati `[MEASURED-R]`.

**Reviewer probe cleanup / incident note:** disposable target ke liye `DATABASE_URL` override set kiya gaya tha, lekin Alembic `env.py` us variable ko read nahi karta; `alembic.ini` ka fixed `relay` URL use hua. Reviewer down/up ne keyed values temporarily `NULL` kiye. Pre-probe catalog snapshot se exact rows restore ki gayi (`id=4 → job:111`, `id=5 → job:112`), then counts, keys, constraint, revision, and zero-idle state reverified. Final production state opening state se exactly match karti hai `[MEASURED-R]`. Is failure mode ko `P-28` me record kiya gaya; temporary database `relay_review_din2`, probe table, and four child workers removed `[MEASURED-R]`.

---