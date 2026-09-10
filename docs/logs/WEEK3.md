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

| # | I said                                                                 | Actual                                                                                                                          | The transferable lesson                                                                                                                              |
|---|------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| Q1 | payload hash se compare kro                                            | Correct: job_id ek uniue instance ko identify krti chaahe kitne bhi retry ho                                                    | payload hash fail bcz do alag alag genuine job ko duplicate manega. Retries change delivery metadata; effect identity must anchor on business intent |
| Q2 | Worker 1 gets rowcount=1, Worker 2 gets Python exception               | Worker 1 gets rowcount=1, Worker 2 gets `rowcount=0` (NO exception with `ON CONFLICT DO NOTHING`)                               | `ON CONFLICT DO NOTHING` turns uniqueness violations into clean DML no-ops without transaction abort                                                 |
| Q3 | Migration reject hogi kyunki Postgres me 2 NULL equal maane jaate hain | Migration accepted: In standard SQL/PostgreSQL `NULL != NULL`, so multiple NULLs do not conflict                                | Unique constraints only enforce distinctness on non-null values                                                                                      |
| Q4 | `idk`                                                                  | Race window exists between Session A's `SELECT` and Session A's `COMMIT`. Interleaved reads before commits cause both to insert | Concurrency cannot be guarded by separate read and write statements                                                                                  |
| Q5 | `idk`                                                                  | 2 executions + 2 distinct workers + measured overlap interval + `{1, 0}` rowcounts + final `count = 1`                          | Dedup proof requires proving that duplicate execution happened AND was suppressed at effect layer                                                    |
| Q6 | Shayad retry karega                                                    | Correct: Generic handler exception boundary catches `UniqueViolation` and retries until attempts exhausted                      | Unhandled integrity errors cause false retries and poison DLQ                                                                                        |

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

## Din 3 — 🎯 Crash side effect ke BEECH me (`2026-09-02`)

**Original goal (from the plan):** crash point `payload` se controllable, crash **asli** (`os._exit()` /
bahar se `kill`, `raise` **nahi**) · teeno crash points chalao aur **reaper chalne se PEHLE** ka DB state
verbatim likho · phir reaper chalao aur dobara padho · aur outbox ka faisla likho (side effect + mark ek
transaction me **kyu nahi**).

**Goal met?** Yes `[MEASURED]` — Three exact process crash boundaries executed with `os._exit(86)`, pre-reaper snapshots and post-reaper recoveries measured, Case B durable orphan effect proved dedup on redispatch (executions 1->2, rowcount=0, effects 1->1), and outbox architectural trade-off documented.

**Anything else learned?** A job row's recovery-relevant projection in `jobs` (`running`, attempts 1, lease active, executions 1) can look identical while underlying business side-effects are completely split (0 vs 1). External side-effects can never join database ACID transactions.

---

### 📊 Measured / Observed

| Kya | Value | Label |
|---|---|---|
| Opening check (teeno) | 111 jobs (93 succeeded / 15 failed / 3 dead_letter), 100 executions, 5 effects, alembic dbe13b69056d, 0 python, 0 idle tx | `[MEASURED]` |
| Crash point kaise controllable banaya (`payload` ka key) | `payload["crash_at"]` with values `before_effect_commit`, `after_effect_commit`, `after_mark_commit` | `[INFERRED]` |
| Crash ka mechanism (`os._exit` / `kill` / kuch aur) | `os._exit(86)` — immediate OS-level process termination bypassing exception/finally handlers | `[MEASURED]` |

**Teen crash points — reaper se PEHLE ka state. Ye state reclaim ke baad WAPAS NAHI AA SAKTI:**

| Crash kahan | side-effect record | `jobs.status` | `attempts` | `claimed_at` | `job_executions` count |
|---|---|---|---|---|---|
| side effect commit se **pehle** (Job 113) | 0 rows | `running` | 1 | 2026-09-02 08:46:52.076 UTC | 1 |
| side effect ke **baad**, mark se **pehle** (Job 114) 🎯 | 1 row (`id=8`, `key=job:114`) | `running` | 1 | 2026-09-02 08:48:36.879 UTC | 1 |
| mark ke **baad** (Job 115) | 1 row (`id=10`, `key=job:115`) `[MEASURED-R correction; original transcription was id=9]` | `succeeded` | 1 | 2026-09-02 08:50:03.279 UTC | 1 |

**Reaper ke BAAD:**

| Crash kahan | `status` | Handler dobara chala? (`job_executions` delta) | **Side effect count** | Label |
|---|---|---|---|---|
| pehle (Job 113) | `succeeded` | Yes (`1 → 2`) | **1** (`id=7`, `worker-15804`, written) | `[MEASURED]` |
| **beech me** 🎯 (Job 114) | `succeeded` | Yes (`1 → 2`) | **1** (`id=8`, `worker-20848`, deduped rowcount=0) | `[MEASURED]` |
| baad me (Job 115) | `succeeded` | No (`1 → 1`) — Reaper & worker ignored | **1** (`id=10`, `worker-24384`) `[MEASURED-R correction; original transcription was id=9]` | `[RECORDED; ID correction separately labelled]` |

| Kya | Value / text | Label |
|---|---|---|
| **Do rows jinka recovery-relevant `jobs` projection (`status`, `attempts`, lease presence, execution count) same dikhta hai** — wo projection actually same tha? IDs/payload/timestamps exclude karo | Yes — Pre-reaper snapshot on Job 113 and 114 both showed `status='running'`, `attempts=1`, `claimed_at` active, `executions=1` | `[MEASURED]` |
| Aur side-effect store me wo **alag** dikhi? | Yes — Job 113 had 0 effects (absent); Job 114 had 1 effect (durable orphan) | `[MEASURED]` |
| `1` aaya — **dedup ki wajah se ya handler dobara chala hi nahi?** (`job_executions` count separate karta hai) | Proved by `job_executions` delta: 1 pre-reaper to 2 post-recovery + stdout `rowcount=0` (`Side-effect deduped`) | `[MEASURED]` |
| **Outbox ka faisla** — side effect + mark ek transaction me? Do reason, aur ek aisa side effect jise transaction me rakha hi nahi ja sakta | (1) Long open transaction across handler work causes lock contention; (2) Status mark CAS race (`rowcount=0`) would require forcing rollback; (3) External effects (email/Stripe payment) cannot join Postgres transactions | `[INFERRED]` |
| `P-16` ka aaj ka roop — `running` ke do situations database se distinguishable hui? | Yes: In `jobs` table alone they are indistinguishable; only inspecting the side-effect ledger reveals whether business effect committed or not | `[MEASURED]` |
| `D-22` Cost 10 (`completed_at`) — aaj usne kaise chubha, aur faisla kya | `completed_at` absence leaves no completion timestamp on `job_executions`; completion remains observable only via job status `succeeded` | `[INFERRED]` |

**M1 — Three-Case Differential Matrix (`C5` Output):**

```text
 id  |  status   | attempts | has_hook | executions | effects
-----+-----------+----------+----------+------------+---------
 113 | succeeded |        2 | f        |          2 |       1   (Case A: Before Effect Crash)
 114 | succeeded |        2 | f        |          2 |       1   (Case B: Middle Crash - Durable Orphan)
 115 | succeeded |        1 | f        |          1 |       1   (Case C: After Mark Crash - Terminal Control)
```

**Closing reconciliation:**

| Line | Value |
|---|---|
| opening | 111 jobs (93 succeeded / 15 failed / 3 dead_letter), 100 executions, 5 effects |
| `+` nayi rows, ids naam se | `+3` jobs (Job 113, 114, 115), `+5` executions (2 on 113, 2 on 114, 1 on 115), `+3` effects (id=7 on 113, id=8 on 114, id=10 on 115 `[MEASURED-R correction; original transcription was id=9]`) |
| `=` expected closing | 114 jobs (96 succeeded / 15 failed / 3 dead_letter), 105 executions, 8 effects |
| `psql` actual | 114 jobs (96 succeeded / 15 failed / 3 dead_letter), 105 executions, 8 effects `[MEASURED]` |
| `job_executions` delta, aur excess naam se | Delta = `+5`, Excess = `+2` (Executions 109 on 113 and 111 on 114 recovery claims) |
| `created_at`/`executed_at` `group by` agree karta hai? | Yes: `jobs` group by = 3 (`2026-09-02`), `job_executions` group by = 5 (`2026-09-02`) `[MEASURED]` |
| **Chain juda?** | ✅ Yes — `max(id) = 115`, `jobs_id_seq = 115`, Gap = 0 `[MEASURED]` |

**Cleanup:**
- `src/worker.py` temporary hooks: Reverted cleanly (`git diff HEAD -- src/worker.py` is empty) `[MEASURED]`
- Python worker/reaper processes: 0 `[MEASURED]`
- `idle in transaction`: 0 `[MEASURED]`
- Hash of `DIN_03_PREDICTIONS_FROZEN.md`: `105C15A8ED25FFD45C930FFC9606E2CDEE523B79B10D2BCD18E13DCACB3CD790` `[MEASURED]`

---

### 💡 What I Understood

Aaj humne crash boundaries ko real OS death (`os._exit(86)`) ke zariye measure karke dual-write hole ko physical reality me dekha:
1. Jab worker side-effect likhkar aur status mark karne se pehle mar jata hai (Case B), toh database me ek **Durable Orphan Effect** ban jata hai — effect disk par permanently save ho chuka hota hai par job abhi bhi `running` rehti hai.
2. Reaper aur Naye Worker ke perspective se Job 113 (effect nahi hua) aur Job 114 (effect ho chuka hai) bilkul identical dikhti hain (`status='running', attempts=1`). Engine ko khud nahi pata hota ki kaam hua ya nahi!
3. Jab naya worker aakar dobara handler chalata hai, toh **Din 2 ki Database Unique Constraint (`uq_side_effects_effect_key`)** recovery ko safe banati hai — Postgres naye worker ko `rowcount = 0` deta hai, jisse naya worker bina duplicate row likhe aage badh kar job ko `succeeded` mark kar deta hai.
4. Side-effect aur Status mark ko ek hi transaction me merge nahi kiya ja sakta kyunki: (a) Transaction handler ke lambe execution/sleep ke across open rahegi; (b) Status mark CAS race hone par rollback force karna padega; (c) External effects (email, payment) database transaction ka hissa ban hi nahi sakte. Yahi Transactional Outbox Pattern ka mathematical reason hai.

---

### 🧠 Self-Check (honest — `3.5` / `6.0` self-answered)

| Kya | Value |
|---|---|
| `DIN_03_ANSWERS.md` exist karti hai? | Yes |
| Uska mtime Step 2 se pehle hai aur frozen copy hash verified hai? (`E8`) | Yes — `DIN_03_PREDICTIONS_FROZEN.md` created in Step 0 with SHA256 `105C15A8...` `[MEASURED]` |
| Score | **3.5 / 6.0** (Q1 partial for running; Q2 correct; Q3 idk; Q4 correct; Q5 correct on os._exit vs raise; Q6 partial for attempts on claim) |
| `idk` kitne? | 1 (`Q3`) |

**Corrections:**

| # | I said | Actual | The transferable lesson |
|---|---|---|---|
| Q1 | Status running reh jayega; entry number nahi pata | Correct status='running'; entry is P-16 running conflation | P-16 defines the inability of a single status value to distinguish active work from orphaned crash |
| Q2 | Count 1 hi rahega unique constraint ki wajah se | Correct: Unique constraint dedupes replay to rowcount=0 | Execute-layer dedup absorbs mid-handler crash recovery without business corruption |
| Q3 | idk | Long transaction locks, status CAS rollback coupling, and external non-transactional effects | Dual writes across heterogeneous stores require decoupled outbox architectures |
| Q4 | job_executions table ka count | Correct: job_executions count 1->2 proves redispatch occurred | A passing count=1 only proves dedup when independent evidence shows redispatch happened |
| Q5 | raise exception handle karega, os._exit turant marega | Correct: raise caught by handler error boundary; os._exit bypasses Python runtime entirely | Never use exceptions to simulate crash boundaries; real failure kills the process |
| Q6 | Case A: 1, Case B: 1, Case C: 0 shayad | Case A = 2, Case B = 2, Case C = 1 | Attempts increment strictly on claim (D-23); retried jobs increment, terminal jobs do not |

---

### 🚧 Unresolved / Follow-ups

**New, from today:** None — Mid-handler crash boundary behavior is fully measured and absorbed by execute dedup.

**Deliberately open (owner ke saath):**
- API Enqueue Idempotency Key (`idempotency_key`, `P-07`) — Owner: **Week 3 Din 4**.
- Property-based failure testing (Hypothesis) — Owner: **Week 3 Din 5**.

**Slipped:** None.

**Carried forward, unchanged:** Step 7 carried debt (Shutdown vs 45s lease hole, `D-22` Cost 8) — Owner: Week 3 catch-up / Din 6.

---

### ❓ Question / Next Thought

Din 2 aur Din 3 me humne worker execute side par duplicate execution aur crash ko database constraint se protect kar liya. Lekin agar **Client (API caller)** hi do baar `POST /jobs` bhej de (network retry ya double click), toh engine do alag-alag `job_id` bana dega! Is API enqueue-level duplicate ko kaise rokenge (`idempotency_key`)?

---

### Reviewer close — Din 3 (`2026-09-02`)

**Final grade: `8.0 / 10` `[INFERRED from the rubric below]`. Prediction score: `2.5 / 6.0` `[INFERRED, frozen-text partial-credit rubric]`.** Core crash/recovery mechanism passes; evidence-retention close is partial `[INFERRED]`.

| Rubric | Score | Reviewer evidence |
|---|---:|---|
| Three pre-recovery durable states | `2.0/2.0` | User log names A=`running/1/1/0`, B=`running/1/1/1`, C=`succeeded/1/1/1` `[RECORDED]`; the same role-based states were independently reproduced in an isolated database `[MEASURED-R]` |
| Reclaim, redispatch, and dedup attribution | `2.0/2.0` | Current evidence rows preserve final `2/2/1`, `2/2/1`, `1/1/1`; fresh Case B showed reclaim, second dispatch, `rowcount=0`, effects `1→1`, then success `[MEASURED-R]` |
| Exact hard-crash placement | `1.5/2.0` | Fresh worker copy proved execution COMMIT→A exit `86`, effect COMMIT→B exit `86`, and mark COMMIT→C exit `86` `[MEASURED-R]`; the user's temporary hook diff and original COMMIT-order transcript were not retained `[MEASURED-R file audit]` |
| After-mark negative control | `0.5/1.0` | User log preserves unchanged counts `[RECORDED]`, but not the required live PID reads/repeated passes; fresh control observed one live reaper for 4 empty passes and one live worker for 3 empty claim polls, with no target reclaim/claim `[MEASURED-R]` |
| Architectural explanation | `0.5/1.0` | Transaction length, ownership/CAS rollback coupling, and external effects were named `[RECORDED]`; “cannot be merged” is too strong—local effect+mark **can** merge at those costs, while external email/HTTP/payment cannot join Postgres atomicity `[INFERRED from source/transaction model]` |
| Reconciliation and cleanup | `1.0/1.0` | Current DB is `114` jobs / `105` executions / `8` effects, named attempts `2/2/1`, head `dbe13b69056d`, zero idle transactions, zero Relay processes; source compiles and HEAD-relative checks pass `[MEASURED-R]` |
| Prediction provenance and precision | `0.5/1.0` | Frozen SHA-256 exactly matches the logged value and prediction text remains separate `[MEASURED-R]`; the hash does not prove authorship/freeze time, and the user's `3.5/6` self-score gave unsupported credit to Q6 `[INFERRED]` |

**Official prediction grading — frozen text only:**

| Q | Credit | Why |
|---|---:|---|
| Q1 | `0.5/1` | `running` correct; requested `P-16` entry not recalled `[INFERRED grading]` |
| Q2 | `0.5/1` | Final count and uniqueness direction correct; required scope—new non-null keyed local-ledger rows, not legacy/external/multi-effect work—missing `[INFERRED grading]` |
| Q3 | `0/1` | Honest `idk`; no prediction answer `[MEASURED-R text, INFERRED score]` |
| Q4 | `1/1` | `job_executions` count correctly separates redispatch+dedup from no redispatch `[INFERRED grading]` |
| Q5 | `0.5/1` | Handler `raise` versus immediate exit direction correct; worker-stays-alive and separate post-mark placement not answered `[INFERRED grading]` |
| Q6 | `0/1` | `1/1/0` is wrong; no increment-on-claim derivation appears `[MEASURED-R text, INFERRED score]` |

The earlier `3.5/6` remains above as the user's self-score; **`2.5/6` is the reviewer score** `[INFERRED]`. Post-run explanations and KEY corrections receive no prediction credit `[INFERRED rubric rule]`.

**Fresh independent probe `[MEASURED-R]`:** a GUID-named disposable database was migrated only after `current_database()` matched the target. Current `worker.py` fingerprints were raw Windows-byte SHA-256 `7d6dc55733653a4c821ea07c7c4e770dac5cb5922586b3cffe0769f06395e43f` and LF-normalized UTF-8 text SHA-256 `af5e480a394ec215f6d4af597788db40ee2bf6247f1d14467e7b5f406eb86b6d`. The temporary copy's recorded source fingerprint was that normalized-text hash; it then carried exact-value hooks, while workspace `src/` was never edited.

```text
A: exit=86; pre running/attempts1/executions1/effects0
   reclaim matched=1 + COMMIT; final succeeded/2/2/1; effect rowcount=1
B: side-effect INSERT + COMMIT, then exit=86
   pre running/attempts1/executions1/effects1; reclaim; replay rowcount=0
   side_effects_id_seq 2→3; final succeeded/2/2/1
C: mark UPDATE + mark line + COMMIT, then exit=86
   live reaper: 4 empty passes; live worker: 3 empty claim polls
   final unchanged succeeded/1/1/1
raise control: exception caught; process remained live; row became pending/attempts1; clean exit=0
```

Role-local probe IDs were `1/2/3`; they are not evidence-DB Jobs `113/114/115` `[MEASURED-R]`. The disposable DB, temporary worker, harness, and generated bytecode were removed; no matching process/database remains `[MEASURED-R]`. Evidence DB before/after fingerprints were identical `[MEASURED-R]`.

**Persisted-row correction:** Job `115`'s surviving effect is **`id=10`**, not `id=9`; current rows are `7→job113`, `8→job114`, `10→job115`, and `side_effects_id_seq=10` `[MEASURED-R]`. The missing `9` is consistent with Case B's conflict consuming a sequence value `[INFERRED from current rows + recorded chronology]`; a fresh Case B directly measured the same no-op insert advancing `2→3` `[MEASURED-R]`. The three earlier Din 3 references retain durable `id=10` while preserving the user's original `id=9` text in explicit `[MEASURED-R correction; original transcription was id=9]` annotations; they are provenance-annotated rather than silently corrected or presented as original `[MEASURED]`.

**Evidence boundary:** current terminal rows corroborate final counts but cannot reconstruct historical pre-reaper snapshots, original hook placement, native exits, or whether original negative-control processes were live `[INFERRED from stored schema]`. Fresh reproduction validates the mechanism, not the missing original transcript `[INFERRED]`. This retention defect is recorded as `P-29` `[MEASURED-R file audit]`.

**Architectural correction:** local ledger effect + terminal mark are not mathematically forbidden from sharing a transaction; merging narrows the middle local split at the cost of transaction ownership coupling, possible longer transactions under current ordering, and mandatory rollback when guarded mark returns `0` `[INFERRED from source]`. External actions still require a different boundary; an outbox makes local state+intent atomic but does not eliminate remote redelivery `[INFERRED]`.

---

## Din 4 — Dedup at enqueue: `idempotency_key`, aur `P-07` (`2026-09-03`)

**Original goal (from the plan):** `idempotency_key text NULL UNIQUE` `jobs` pe, migration up aur down ·
`POST /jobs` ka replay behaviour ek **decision** ke saath · `P-07` ke **chaar** sawaalon ka jawab, apni cost
ke saath · aur do **concurrent** identical `POST`.

**Goal met?** Yes `[MEASURED for outputs / INFERRED overall judgement]` — API enqueue idempotency implemented with `idempotency_key TEXT NULL` and `uq_jobs_idempotency_key`, request fingerprinting with compact sorted-key JSON SHA-256, transparent `202-original` replay contract, `409 idempotency_key_mismatch` on tampered payload, genuine concurrent race proved `Lock/transactionid` wait and single winner, unkeyed requests confirmed distinct via `NULLS DISTINCT`, and full execute-layer regression proved one retained local effect (`executions=2, effects=1`). **Reviewer qualification:** this serializer is stable for today's inputs, not a complete canonical-JSON standard `[INFERRED from source]`.

**Anything else learned?** `jobs_id_seq` advanced on every measured conflicting attempt even when `ON CONFLICT DO NOTHING` inserted no row `[MEASURED]`; this is consistent with PostgreSQL evaluating non-transactional `nextval()` before the unique-conflict verdict `[INFERRED mechanism]`. The isolated duplicate-flush transaction rejected the pre-rollback read with `PendingRollbackError` / underlying `25P02`, then accepted it after explicit rollback `[MEASURED]`.

---

### 📊 Measured / Observed

| Kya | Value | Label |
|---|---|---|
| Opening direct DB + Python runtime target + schema/process/source bench + frozen SHA | `114 jobs (96 succeeded / 15 failed / 3 dead_letter), max_id=115, jobs_id_seq=115, 105 executions, 8 effects, side_effects_id_seq=10, alembic dbe13b69056d, 0 processes, 0 idle tx, SHA256: E77BF4EAD1C4E3E16F85A7971732DEF72EE544A493047DD07C18F2C80D047358` | `[MEASURED]` |
| Key normalization/bounds — chosen max, blank rejected, at-limit accepted, over-limit rejected | `max_key_length=128, blank_rejected=True, at_limit_accepted=True, over_limit_rejected=True` | `[MEASURED]` |
| Migration catalog + lifecycle — first head `2/1`, parent `0/0`, re-upgrade `2/1`; evidence upgrade only | `catalog head 2/1, lifecycle head 2/1 -> parent 0/0 -> re-upgrade 2/1, evidence upgrade relay|w3d4_enqueue_idempotency with 114 null rows preserved` | `[MEASURED]` |

**`P-07` ke chaar sawaal + same-key/different-request safety question — aaj jawab ke saath:**

| Sawaal | Chuna hua jawab | Uski cost | Label |
|---|---|---|---|
| Key kaun mint karta hai (caller / payload hash) | Caller-minted string (transport: optional JSON field `idempotency_key`) | Requires caller discipline; key loss prevents retry correlation | `[INFERRED]` |
| Dedup window (row lifetime / N time) | Retention-bound (while job row exists in PostgreSQL) | Post-deletion retries can create new jobs; no time horizon without retention worker | `[INFERRED]` |
| Duplicate request ko kya milta hai (`202` + original id / `409`) | `202-original` (returns original `job_id` and current `status`) | Transparent acceptance lowers replay visibility for caller | `[INFERRED]` |
| Race pe kya hota hai | **measured, decided nahi:** Winner commits, loser lock-waits on `transactionid`, then returns `202-original` with winner's `job_id` | — | `[MEASURED]` |
| Same key + different request | `409 Conflict` with `detail={"code": "idempotency_key_mismatch", "job_id": <original_id>}` | Rejects invalid reuse, preserves original row unmodified | `[MEASURED]` |

| Kya | Value | Label |
|---|---|---|
| Fingerprint contract — fields, canonicalization, sample hash length | Cleaned `type` + canonical payload (`sort_keys=True, separators=(',', ':')`) -> 64-char lowercase SHA-256 hex | `[MEASURED]` |
| Fingerprint differential — same payload, different `type`: inputs + both hashes | `sleep + {a:1,b:2} -> f00f935ab...` vs `boom + {a:1,b:2} -> 26732cf07...` (`type_changes=True`) | `[MEASURED]` |
| Fingerprint differential — same `type`, different payload: inputs + both hashes | `sleep + {a:1,b:2} -> f00f935ab...` vs `sleep + {a:1,b:3} -> d72b78996...` (`payload_changes=True`) | `[MEASURED]` |
| Sequential replay — first/replay status, same original id, keyed row count | `first=202 (job_id=116), replay=202 (job_id=116), rows_for_key=1, stored fingerprint=f00f935ab1d22460395f5248c2a7786fc1a82c74cdb13ba5c7d8f6f960ced251` | `[MEASURED]` |
| Sequence role ledger — before/after + delta for first, replay, mismatch, failed-session, unrelated-integrity, race, execute job (`jobs_id_seq`), and execute effect (`side_effects_id_seq`) | `first: 115->116 (d=1), replay: 116->117 (d=1), mismatch: 117->118 (d=1), failed-session: 118->119 (d=1), unrelated: 119->120 (d=1), race: 120->122 (d=2), exec job: 124->125 (d=1), exec effect: 10->12 (d=2)` | `[MEASURED]` |
| Conflict verdict — exception / no returned row / `rowcount=0`; `execute`/`flush`/`commit` kahan | `ON CONFLICT ON CONSTRAINT uq_jobs_idempotency_key DO NOTHING RETURNING id, status -> returns no row (result.first() is None) on await db.execute(stmt)` | `[MEASURED]` |
| Failed transaction path — exact `PendingRollbackError` or DBAPI `25P02` before rollback; post-rollback original SELECT | `Duplicate flush raised IntegrityError (23505/uq_jobs_idempotency_key); pre-rollback SELECT raised PendingRollbackError (DBAPI SQLSTATE 25P02); post-rollback SELECT returned count=1` | `[MEASURED]` |
| Mismatch full before/after snapshot — `id/type/payload/request_fingerprint` verbatim; HTTP status/code; original unchanged? | `before=after={"id": 116, "type": "sleep", "payload": {"a": 1, "b": 2}, "request_fingerprint": "f00f935ab1d22460395f5248c2a7786fc1a82c74cdb13ba5c7d8f6f960ced251"}; HTTP status=409, code=idempotency_key_mismatch, original row unchanged` | `[MEASURED]` |
| Unrelated integrity control — HTTP status/code + exact API log `23514/jobs_status_check`; replay/mismatch nahi | `HTTP status=500, detail includes check constraint jobs_status_check (23514), no replay/mismatch returned` | `[MEASURED]` |
| **Do concurrent identical POST** — both status/body/job id/elapsed ms | `Winner: 202 {"job_id":121,"status":"pending"} 5062.6 ms; Loser: 202 {"job_id":121,"status":"pending"} 5416.5 ms` | `[MEASURED]` |
| Concurrent overlap proof — `PgSleep` winner + `Lock/transactionid` loser | `PID 3283 Timeout/PgSleep; PID 3505 Lock/transactionid` | `[MEASURED]` |
| Concurrent final keyed row count | `1 (Job 121)` | `[MEASURED]` |
| Bina key wale POST — both status, distinct IDs, two `NULL` keys/fingerprints | `Job 123 (status=202) and Job 124 (status=202), distinct IDs, both keys NULL and fingerprints NULL` | `[MEASURED]` |
| Execute reclaim proof — reaper target `matched=1`; committed `pending/attempts=1/claimed_at=NULL` barrier before Worker B; target heartbeat lines `0` | `reclaim_committed_barrier=pending|1|true (attempts=1, claimed_at IS NULL), target heartbeat lines=0` | `[MEASURED]` |
| **Execute regression final** — attempts/executions/workers/effects + `{1,0}` insert rowcounts | `Job 125: attempts=2, executions=2, distinct workers=2, effects=1, effect insert rowcounts={1, 0}` | `[MEASURED]` |
| Exact four-ID gate cleanup — IDs, per-ID reset result, global infinity count `0` | `gate_reset_ids=116,121,123,124, exact_remaining=0, global_remaining=0` | `[MEASURED]` |
| Trigger AND function cleanup — mismatch + race objects absent from `pg_trigger` AND `pg_proc` | `pg_trigger=0, pg_proc=0 for both mismatch and race fixtures` | `[MEASURED]` |
| Catalog/lifecycle DB cleanup — both DB names + absence proof | `relay_din4_catalog_26280_2b3f5745 and relay_din4_lifecycle_14536_ff4c86f5 dropped; remaining_probe_dbs=0` | `[MEASURED]` |
| `D-24` input only — enqueue vs execute scope, dono kyu; Din 6 same-day grep ke baad publish karega | `Enqueue uniqueness prevents duplicate job rows on client retry; Execute uniqueness prevents duplicate business effects on worker reclaim/redispatch. Both layers are mandatory and protect distinct failure domains. Formal publication deferred to Din 6` | `[INFERRED]` |
| `P-07` band hui, ya uska kaunsa hissa khula raha | `Resolved for local database enqueue idempotency via caller key + request fingerprint + uq_jobs_idempotency_key; retention cleanup window remains open for Week 4` | `[INFERRED]` |

**M1 — Concurrent POST wait + response transcript**

```text
 pid  | wait_event_type |  wait_event   |                                            left
------+-----------------+---------------+--------------------------------------------------------------------------------------------
 3505 | Lock            | transactionid | INSERT INTO jobs (type, payload, idempotency_key, request_fingerprint) VALUES ($1::VARCHAR
 3283 | Timeout         | PgSleep       | INSERT INTO jobs (type, payload, idempotency_key, request_fingerprint) VALUES ($1::VARCHAR
(2 rows)

status body                              elapsed_ms RunspaceId
------ ----                              ---------- ----------
   202 {"job_id":121,"status":"pending"}    5416.50 6c30d1a1-1c65-4ec4-8d3c-be0331cdb9f6
   202 {"job_id":121,"status":"pending"}    5062.60 03e6b835-25d0-4f2a-887b-54de7e053e7f

race_observer: sleepers=1 lock_waiters=1
race_sequence: before=120 after=122 delta=2
raceKey=din4-race-26d27d654fc5489b8a4204da52576b2e raceJobId=121 snapshot={"id" : 121, "type" : "sleep", "payload" : {"probe": "concurrent"}, "request_fingerprint" : "21e3021d707e7be14371898433b4b3a0299ee29a76cacb2d43ee9a8b41f5333b"}
DROP TRIGGER
DROP FUNCTION
0
0
```

**M2 — Execute-layer regression transcript**

```text
reclaim_committed_barrier=pending|1|true
 id  |  status   | attempts |              idempotency_key               | executions | workers | effects
-----+-----------+----------+--------------------------------------------+------------+---------+---------
 125 | succeeded |        2 | din4-exec-cc0cde87474346f191a52b83028f3db6 |          2 |       2 |       1
(1 row)

 id | effect_key |  worker_id
----+------------+--------------
 11 | job:125    | worker-18188
(1 row)

exec_job_sequence: before=124 after=125 delta=1
exec_effect_sequence: before=10 after=12 delta=2
gate_reset_ids=116,121,123,124 exact_remaining=0 global_remaining=0
```

**Closing reconciliation (`+5 jobs / +2 executions / +1 effect` expected by role):**
- Starting: 114 jobs (96 succeeded / 15 failed / 3 dead_letter), max/seq=115, 105 executions, 8 effects, seq=10 `[MEASURED]`
- Ending: 119 jobs (97 succeeded / 15 failed / 4 pending / 3 dead_letter), max/seq=125, 107 executions, 9 effects, seq=12 `[MEASURED]`
- Net additions:
  - +5 jobs: Job 116 (sequential first), Job 121 (race winner), Job 123 (unkeyed 1), Job 124 (unkeyed 2), Job 125 (execute regression target) `[MEASURED]`
  - +2 executions: Job 125 Worker A + Job 125 Worker B `[MEASURED]`
  - +1 effect: Job 125 effect id=11 (Worker A committed, Worker B deduped with rowcount=0) `[MEASURED]`
  - +4 pending: Jobs 116, 121, 123, 124 (all unexecuted fixtures cleanly reset from infinity gate) `[MEASURED]`
  - +1 succeeded: Job 125 `[MEASURED]`

**Cleanup (API/workers/reaper, PowerShell jobs, mismatch + race triggers AND functions, catalog + lifecycle DBs, exact four-ID gate + global infinity, idle tx):**
- API uvicorn processes stopped: `relay_processes = 0` `[MEASURED]`
- Worker and Reaper processes: 0 `[MEASURED]`
- PowerShell jobs: 0 `[MEASURED]`
- Triggers and functions: `din4_hold_race_insert_trigger` = 0, `din4_force_unrelated_integrity_trigger` = 0, `din4_hold_race_insert` = 0, `din4_force_unrelated_integrity` = 0 `[MEASURED]`
- Disposable databases: `remaining_probe_dbs = 0` `[MEASURED]`
- Infinity gates: `exact_remaining = 0`, `global_remaining = 0` `[MEASURED]`
- Idle transactions: `idle in transaction = 0` `[MEASURED]`
- Revision: `w3d4_enqueue_idempotency` `[MEASURED]`

---

### 💡 What I Understood

Aaj humne API enqueue layer par idempotency implement karke systems-level guarantees verify ki:
1. **`NULLS DISTINCT` & Opt-Out:** PostgreSQL standard UNIQUE constraint do `NULL` values ko equal nahi maanta (`NULL = NULL` is UNKNOWN). Iski wajah se bina idempotency key wali normal requests aapas me merge nahi hoti aur independent jobs banati hain.
2. **Deterministic Fingerprinting (Canonical JSON):** Client payload keys ka order aage-peechhe kar sakta hai (`{"a":1,"b":2}` vs `{"b":2,"a":1}`). Sorting dictionary keys and stripping spaces (`separators=(',', ':')`) ensures a deterministic SHA-256 hash. If payload changes under the same key, it is rejected with `409 Conflict (idempotency_key_mismatch)`, preventing silent execution of mismatched work.
3. **PostgreSQL XID Lock Wait on Concurrent Race:** Jab do concurrent requests same unique key insert karti hain, Postgres doosre contender ko fail nahi karta balki winner ke `transactionid` par wait karwata hai (`wait_event_type = 'Lock'`). Jab winner commit karta hai, loser jaagkar `ON CONFLICT DO NOTHING` evaluate karta hai aur safely winner ka original `job_id` return karta hai.
4. **Sequence Consumption on Conflict:** Non-transactional sequences (`nextval()`) conflict check se pehle number allocate karti hain. Isliye replay request par koi row insert na hone par bhi sequence advance hota hai (`delta = 1`).
5. **Enqueue UNIQUE vs Execute UNIQUE Necessity:** Dono layers alag-alag failure domains ko protect karti hain: Enqueue uniqueness ek client intent se multiple job rows banna rokti hai; Execute uniqueness lease expiry/reclaim ke baad legal worker redispatch me duplicate local business side-effects commit hona rokti hai. Dono ek doosre ke bina incomplete hain.

---

### 🧠 Self-Check (honest — `0.0` / `6.0` self-answered)

| Kya | Value |
|---|---|
| `DIN_04_ANSWERS.md` exist karti hai? | Yes |
| Uska mtime Step 1 se pehle hai aur frozen copy hash verified hai? (`E77BF4...`) | Yes — `DIN_04_PREDICTIONS_FROZEN.md` SHA256 verified `[MEASURED]` |
| Score | **0.0 / 6.0** (All 6 questions frozen as `idk` in Step 0 before code/measurements) |
| `idk` kitne? | 6 (`Q1`–`Q6`) |

**Corrections:**

| # | I said | Actual | The transferable lesson |
|---|---|---|---|
| Q1 | idk | 2 rows; PostgreSQL `NULLS DISTINCT` treats `NULL = NULL` as UNKNOWN | Nullable uniqueness preserves opt-out compatibility for unkeyed clients |
| Q2 | idk | 1 row, but sequence delta=1; conflict surfaces as `result.first() is None` on `execute` | Non-transactional sequences allocate eagerly before unique conflict determination |
| Q3 | idk | Loser waits on `Lock/transactionid` while winner is in `Timeout/PgSleep`; final row count 1 | Unique-index arbitration serialises the verdict for this conflicting key; it does not imply transaction-level `SERIALIZABLE` isolation `[INFERRED reviewer correction]` |
| Q4 | idk | False success / silent data corruption; compact sorted-key JSON makes object-key order stable for today's inputs | Idempotency must protect against payload tampering under the same key; this is not a complete canonical-JSON standard `[INFERRED reviewer correction]` |
| Q5 | idk | `PendingRollbackError` / SQLSTATE `25P02`; aborted transaction requires explicit rollback | Once a transaction fails in PostgreSQL, no further queries can execute before rollback |
| Q6 | idk | Cannot remove `side_effects.effect_key`; protects worker redispatch after lease expiry | Enqueue dedup and execute dedup protect completely distinct distributed boundaries |

---

### 🚧 Unresolved / Follow-ups

**New, from today:** None — API enqueue idempotency, deterministic fingerprinting, concurrent race handling, and execute-layer regression fully measured and clean.

**Deliberately open (owner ke saath):**
- Property-based testing of deduplication under random interleavings (Hypothesis) — Owner: **Week 3 Din 5**.
- Formal `D-24` publication in `DECISIONS.md` — Owner: **Week 3 Din 6** (after same-day grep).
- Time-based idempotency key expiration / retention cleanup worker — Owner: **Week 4**.

**Slipped:** None.

**Carried forward, unchanged:** Step 7 carried debt (Shutdown vs 45s lease hole, `D-22` Cost 8) — Owner: Week 3 catch-up / Din 6.

---

### ❓ Question / Next Thought

Din 4 me humne ek deterministic 2-client race dekhi jisme trigger lagakar race condition simulate ki. Lekin real production me interleavings random hoti hain — worker aage-peechhe ho sakte hain, network delays random ho sakte hain. Hum mathematically kaise prove karein ki koi bhi random interleaving hamare system me duplicate side-effect nahi bana sakti? (Din 5: Property-based testing with Hypothesis).

---

### Reviewer close — Din 4 (`2026-09-03`)

**Final grade: `9.5 / 10` `[INFERRED from the rubric below]`. Recorded prediction score: `0.0 / 6.0` `[RECORDED, accepted without re-grading as requested]`.** Implementation and measured failure controls pass; the deduction is documentation precision, not mechanism correctness `[INFERRED]`.

| Rubric | Score | Reviewer evidence |
|---|---:|---|
| Schema + shape-reversible migration | `2.0/2.0` | Source/catalog match two nullable `TEXT` columns plus named validated uniqueness; fresh exact-target disposable lifecycle measured `2/1 → 0/0 → 2/1` `[MEASURED-R]`. Downgrade is data-destructive: it drops stored key/fingerprint history, so re-upgrade restores shape but not replay identity `[INFERRED from migration]` |
| Sequential identity + negative controls | `2.0/2.0` | Fresh disposable API reproduced same-id `202` replay, stable reordered-key fingerprint, `409` mismatch, `23505`/`PendingRollbackError`, and unrelated-check honest `500` `[MEASURED-R]` |
| Concurrent arbitration | `2.0/2.0` | Fresh race measured PID `4200` in `Timeout/PgSleep`, PID `4283` in `Lock/transactionid`, two `202` responses for Job `8`, and one stored row `[MEASURED-R]` |
| Opt-out + execute-layer separation | `2.0/2.0` | Fresh unkeyed control created distinct Jobs `4/5` with null key/fingerprint pairs `[MEASURED-R]`; evidence DB independently corroborates Job `125` at `2 attempts / 2 executions / 2 workers / 1 effect` `[MEASURED-R]`, while original `{1,0}` stdout is `[RECORDED]` rather than re-run |
| Reconciliation + cleanup | `1.0/1.0` | Evidence DB remains `119/107/9`, max/sequence `125`, effect sequence `12`, correct status buckets and head; zero probe DBs/objects, Relay processes, idle transactions, infinity gates, and PowerShell jobs `[MEASURED-R]` |
| Explanation precision | `0.5/1.0` | Layer separation and sequence-gap mechanism are sound `[INFERRED from source + measurements]`; two phrases below overstate what was established `[INFERRED]` |

**Prediction boundary:** `DIN_04_ANSWERS.md` was not opened or scored in this review `[MEASURED-R process record]`. The user's frozen `idk × 6` and honest `0.0/6.0` remain the official recorded result; no post-run explanation receives prediction credit `[RECORDED/INFERRED protocol rule]`.

**Fresh independent reproduction `[MEASURED-R]`:** all behavior probes ran in `relay_din4_behavior_a91c73e4`, never in the evidence database. First/replay returned `202/202`, the same Job `1`, and one row. Changed payload returned `409 idempotency_key_mismatch`. Two unkeyed requests returned Jobs `4/5` and two null key/fingerprint pairs. A direct duplicate flush raised `23505/uq_jobs_idempotency_key`; the pre-rollback read raised `PendingRollbackError`; the post-rollback key count was `1`. A trigger-induced `jobs_status_check` violation returned HTTP `500`, not replay/mismatch. The race returned Job `8` twice with one row while the observer saw the wait pair above `[MEASURED-R]`.

**Migration and retained-state audit `[MEASURED-R]`:** `relay_din4_reviewer_8148_d13eb009` was targeted only after `current_database()` matched its explicit overridden URL. It measured head `2 columns / 1 constraint`, parent `0/0`, then head `2/1`. This proves schema-shape reversibility only: downgrade drops both identity columns and therefore erases stored replay history; re-upgrade cannot reconstruct it `[INFERRED from migration]`. The evidence database independently measured `119` jobs (`97 succeeded / 15 failed / 4 pending / 3 dead_letter`), `107` executions, `9` effects, all `114` historical rows still null/null, and Job `125` owning effect `id=11` with key `job:125` `[MEASURED-R]`.

**Cleanup `[MEASURED-R]`:** both reviewer databases were dropped; API terminal stopped; temporary triggers/functions removed; `remaining relay_din4_* databases=0`, Relay processes `0`, PowerShell jobs `0`, evidence infinity rows `0`, and idle transactions `0`. Evidence fingerprint after probing remained `119|125|107|9|w3d4_enqueue_idempotency` `[MEASURED-R]`.

**Two wording corrections:**
1. “Unique constraints enforce serializability” is too broad. This run proves unique-index arbitration serialises the verdict for one conflicting key; it does **not** establish transaction-level `SERIALIZABLE` semantics `[INFERRED from measured wait + PostgreSQL mechanism]`.
2. `sort_keys=True, separators=(',', ':')` is a stable compact sorted-key serialization for the current JSON inputs, not a complete canonical-JSON standard: numeric representations and Unicode normalization remain contract choices `[INFERRED from source]`.

**Regression retention:** no checked-in executable suite currently protects replay, mismatch, or concurrent arbitration; this close retains measured historical evidence, not an ongoing guard `[MEASURED-R file/test discovery]`. Din 5 owns the property/mutation test work; no test was added during this reviewer-only close `[INFERRED scope boundary]`.

**Retained boundaries:** key/fingerprint pairing is application-owned rather than database-enforced; the key namespace is global; omitted/lost keys bypass dedup; deleting a row forgets the intent; and same-key contenders can inherit winner latency because this path sets no local statement/transaction timeout `[INFERRED from source/catalog]`. These narrow the guarantee; they do not invalidate today's current-scope contract `[INFERRED]`.

---

## Din 5 — Property test: evidence, opinion nahi (`2026-09-04`)

**Original goal (from the plan):** property ka **wording** pehle likhna (code se pehle), aur uske do hisse
iss hafte ke measurements ke hisaab se theek karna (`har job` ka scope, aur `= 1` vs `<= 1` — `P-27`) ·
Hypothesis se random **interleavings** · test isolation ka faisla (107 purani rows, aur wo **delete nahi**
hoti) · aur **dedup hata ke test red hona verify karna**.

**Goal met?** Partial `[INFERRED]` — Model-level effect-safety test, mutation kill, and PostgreSQL uniqueness were established `[MEASURED]`, but Layer B used custom test-side SQL rather than production `src.worker` and C6 ran concurrent coroutines in one process rather than two worker processes `[MEASURED]`.

**Anything else learned?** Deduplication and fencing protect orthogonal failure domains: dedup ensures business side-effects commit at most once across retries/redispatches (`effects <= 1`), but CAS status updates (`WHERE status='running'`) are generation-blind without fencing tokens, allowing stale workers to mark succeeded behind the back of active claimants (`stale_mark_rowcount = 1`).

---

### 📊 Measured / Observed

| Kya | Value / text | Label |
|---|---|---|
| Opening check (teeno) | 119 jobs (97 succeeded / 15 failed / 4 pending / 3 dead_letter), max/seq=125, 107 executions, 9 effects, seq=12, w3d4_enqueue_idempotency, 0 python, 0 idle tx, probe_dbs=0 | `[MEASURED]` |
| **Property ka wording, subah likha hua** | `For any sequence of worker claims, crashes, lease expirations, and reaper redispatches, the number of durable committed side effects for any logical job identity must never exceed one (safety), and must equal exactly one for any job whose handler reached committed effect execution (conditional exactness).` | — |
| **Property ka wording, shaam ka** — aur jo badla, wo kis measurement se badla | `For all non-null local ledger effect keys job:<id> across any sequence of claims, crashes, lease expirations, and redispatches, durable committed side effects <= 1 (safety); if a legal effect-write transaction completes, durable committed side effects = 1 (conditional exactness). Badla: Completion evidence is absent (job_executions is dispatch evidence, status='succeeded' is generation-blind); scope is explicitly restricted to non-null local ledger keys and write boundaries.` | — |
| Scope: `har job` ya `wo jobs jinka handler ek baar poora chala`? Aur wo kis column se pata chalta hai | Non-null effect keys `job:<id>` jo effect-write transaction boundary tak pahuche; boom/dead_letter excluded. Schema me `completed_at` column absent hai (`job_executions` me sirf `executed_at` hai), isliye scope handler completion nahi balki legal effect-write transaction boundary hai. | — |
| `= 1` ya `<= 1`? (`P-27`) Aur kaunsa asli contract hai | Safety contract `<= 1` asli contract hai. P-27 overdraft se 4th attempt/dispatch generate hone par bhi effect count `<= 1` hi rehta hai. Conditional exactness `= 1` sirf completed write boundaries par laagu hota hai. | — |
| Test isolation ka faisla (separate DB / rollback per example / key prefix) + cost | Separate physical disposable DB (`relay_din5_<PID>_<8hex>`); rollback cannot contain child subprocess commits, prefixing does not constrain worker claim query; cost: migration and cleanup plumbing. | — |
| `jobs` ka `count(*)` test se **pehle** aur **baad** | Evidence DB `relay`: pre=119, post=119 (Delta = 0). Disposable DB: created at 0, peak at 4, dropped at close. | `[MEASURED]` |
| Hypothesis ki **example count** | `all_sequence_examples = 200, redispatch_examples = 100` | `[MEASURED]` |
| Kitne examples me **do dispatch** hue (warna test ne duplicate dekha hi nahi — `P-12`) | `100 / 100` (100% of forced-redispatch examples reached `dispatches >= 2` by construction) | `[MEASURED]` |
| **Dedup hata ke test red hui?** — ye aaj ka sabse zaroori check hai | Yes, exit code 1; `DIN5_MUTANT='no_dedup'` immediately broke assertion `effect_count <= 1`. | `[MEASURED]` |
| Property fail hui? **Shrunk counterexample verbatim** | `shrunk_trace=['claim(worker-1)', 'effect_write()', 'crash()', 'reclaim()', 'claim(worker-2)', 'effect_write()']; dispatches=2; effect_writes=2; effect_count=2` | `[MEASURED]` |
| Property paas hui **bina** fencing token ke? | Yes (Layer A model and Layer B pg_witness both passed `effect_count <= 1` without fencing). | `[MEASURED]` |
| **Ek concrete interleaving jo dedup se bachta hai par fencing se rukta hai** (Week 4 ka input) | `claim:A -> effect:A -> reclaim -> claim:B -> mark:A(stale, rowcount=1) -> effect:B(dedup, rowcount=0) -> mark:B(current owner, rowcount=0)` | `[MEASURED]` |
| Property ke **known limits** — kya ye test check **nahi** karta | Finite model traces only; model omits OS scheduler/wall-clock; only 2-3 real DB witnesses; current local non-null keyed ledger row only; external side-effects (email/HTTP) `[NO EVIDENCE]`; legacy NULL effects unconstrained; single effect kind per job only; no liveness under permanent crashes; no fencing/ownership guarantee. | — |

**M1 — Verbatim Mutant Kill Trace and Layer B JSON Witnesses:**

```text
Mutation exit: 1
AssertionError: Falsifying example: shrunk_trace=['claim(worker-1)', 'effect_write()', 'crash()', 'reclaim()', 'claim(worker-2)', 'effect_write()']; dispatches=2; effect_writes=2; effect_count=2

Layer B Witnesses:
- baseline: {"database": "relay_din5_13404_ab0a8a34", "scenario": "baseline", "dispatches": 1, "effects": 1}
- concurrent: {"database": "relay_din5_13404_ab0a8a34", "scenario": "concurrent", "dispatches": 2, "distinct_workers": 2, "effects": 1, "effect_rowcounts": [0, 1]}
- crash_reclaim: {"database": "relay_din5_13404_ab0a8a34", "scenario": "crash_reclaim", "crash_kind": "hard_process_exit", "worker_a_exit_code": 1, "pre_reclaim": "running|1|1|1", "reclaim_barrier": "pending|1|true", "final": "succeeded|2|2|2|1", "replay_effect_rowcount": 0, "child_pids": [11044, 16920, 26464], "live_children_after_cleanup": 0}
- stale_mark: {"database": "relay_din5_13404_ab0a8a34", "scenario": "stale_mark", "dispatches": 2, "effect_count": 1, "stale_mark_rowcount": 1, "current_owner_mark_rowcount": 0, "trace": "claim:A -> effect:A -> reclaim -> claim:B -> mark:A -> effect:B -> mark:B"}
```

**Closing reconciliation:**
- Starting: `119 jobs (97 succeeded / 15 failed / 4 pending / 3 dead_letter), max/seq=125, 107 executions, 9 effects, seq=12`
- Din 5 delta on evidence DB: `+0 jobs, +0 executions, +0 effects` (All Layer B tests executed in disposable DB `relay_din5_13404_ab0a8a34`).
- Ending: `119 jobs (97 succeeded / 15 failed / 4 pending / 3 dead_letter), max/seq=125, 107 executions, 9 effects, seq=12` `[MEASURED]`
- Chain juda? Yes, exact logical match. Evidence untouched `[MEASURED]`.

**Cleanup:**
- Disposable DB: `relay_din5_13404_ab0a8a34` dropped (`remaining = 0`) `[MEASURED]`
- Worker/reaper/witness processes: 0 `[MEASURED]`
- Idle transactions: 0 `[MEASURED]`
- Full Din 5 suite close: 7 passed in 1.22s `[MEASURED]`
- Predictions frozen SHA256: `1E89D02AAB0D73ECAEF6FC71DFE82CD8D062E433D855CE6CF82A04CCDCC99427` `[MEASURED]`

---

### 💡 What I Understood

> **Aaj, apne shabdon me.**

Aaj humne property-based testing aur real PostgreSQL witnesses ke zariye deduplication ke invariants aur limits ko verify kiya:
1. **Property Formulation:** Universal claim "har job ka side effect = 1" galat hai kyunki boom/crash/dead_letter jobs bina effect write ke terminate ho sakti hain. Safety invariant strictly `effects <= 1` hai, aur conditional exactness `effects = 1` sirf un jobs par laagu hota hai jinka handler legal effect-write transaction complete kare.
2. **Mutation Testing (Sensitivity Proof):** Test tabhi bharosemand hai jab wo bug aane par fail ho sake. Jab humne `$env:DIN5_MUTANT='no_dedup'` set karke dedup bypass kiya, toh test turant RED ho gaya aur Hypothesis ne minimal counterexample shrink karke diya (`claim -> effect_write -> crash -> reclaim -> claim -> effect_write => effect_count=2`).
3. **Physical DB Isolation:** Subprocess testing ke liye transaction rollback ya key prefixing useless hai kyunki child worker alag session me commit karta hai aur claim query prefix ignore karti hai. Isliye physical disposable database (`relay_din5_*`) hi ekmatra safe option hai.
4. **Dedup vs Fencing Boundary:** Dedup ne duplicate business side-effect commit hona strictly rok liya (`effects = 1`), lekin stale worker ko status mark karne se nahi rokk saka (`stale_mark_rowcount = 1`). Status CAS updates generation-blind hote hain, isliye stale owners ko rokne ke liye fencing token (`claim_generation`) zaroori hai (Week 4 input).

---

### 🧠 Self-Check (honest — `0.0` / `6` self-answered)

| Kya | Value |
|---|---|
| `DIN_05_ANSWERS.md` exist karti hai? | Yes |
| Uska mtime Step 1 se pehle hai aur frozen copy hash verified hai? (`1E89D0...`) | Yes — `DIN_05_PREDICTIONS_FROZEN.md` SHA256 verified `[MEASURED]` |
| Score | **0.0 / 6.0** (All 6 questions frozen as `idk` in Step 0 before code/measurements) |
| `idk` kitne? | 6 (`Q1`–`Q6`) |

**Corrections:**

| # | I said | Actual | The transferable lesson |
|---|---|---|---|
| Q1 | idk | Safety is `effects <= 1`; conditional exactness is `effects = 1` for completed writes; boom/dead_letter excluded | Universal statements confuse safety with progress; missing completion columns force scoping to write boundaries |
| Q2 | idk | Real contract is safety `<= 1`; P-27 overdrafts retry scheduling, not effect semantics | Retries and bound overdrafts are failure modes dedup must absorb, not an excuse to duplicate |
| Q3 | idk | Separate physical disposable DB; rollback cannot undo child commits, prefixing does not constrain worker claim query | Concurrency with real OS subprocesses requires physical catalog separation |
| Q4 | idk | Test failure (surviving mutant); red test with `effect_count=2` proves sensitivity | A test that cannot fail on a known defect provides zero guarantee |
| Q5 | idk | Minimal legal action history / precondition trace in domain terms (claim-write-crash-reclaim-claim-write) | Shrinking strips irrelevant noise to expose the minimal structural violation |
| Q6 | idk | Fencing protects claim ownership/control-plane CAS writes, not effect uniqueness; stale A marked succeeded while B active | Dedup and fencing solve orthogonal problems: dedup bounds effect damage, fencing bounds ownership authority |

---

### 🚧 Unresolved / Follow-ups

**New, from today:** Fencing token / claim generation boundary explicitly identified and measured via stale mark witness (`stale_mark_rowcount=1`, `current_owner_mark_rowcount=0`).

**Deliberately open (owner ke saath):**
- Fencing token / monotonic claim generation build — Owner: **Week 4**.
- Formal `D-24` & `D-25` publication in `DECISIONS.md` — Owner: **Week 3 Din 6** (after same-day grep).
- Time-based idempotency key expiration / retention worker — Owner: **Week 4**.

**Slipped:** None.

**Carried forward, unchanged:** Step 7 carried debt (Shutdown vs 45s lease hole, `D-22` Cost 8) — Owner: Week 3 catch-up / Din 6.

---

### ❓ Question / Next Thought

Din 5 me humne property-based testing se prove kar liya ki deduplication safe hai aur stale marks generation-blind hain. Ab Week 3 Din 6 me hum entire week ka reconciliation karenge, `D-24` aur `D-25` ko formally publish karenge, aur Week 4 (outbox dispatcher, fencing tokens, observability) ka handoff taiyyar karenge!

---

### Reviewer close — Din 5 (`2026-09-04`)

**Final grade: `6.5 / 10` `[INFERRED from the reviewer rubric below]`. Prediction score: `0.0 / 6.0` `[INFERRED from the KEY rubric applied to frozen text]`.** The local effect-row safety invariant and mutation sensitivity were upheld, but the complete Layer B witness contract was not: the harness reimplements worker SQL instead of invoking current `src.worker`, and C6 uses concurrent sessions in one process rather than two worker processes `[MEASURED]`.

| Reviewer rubric | Score | Mechanism-level evidence |
|---|---:|---|
| Contract and property precision | `2.0/2.0` | Safety `effects <= 1`, conditional exactness `effects = 1`, missing completion evidence, and P-27 scope are separated correctly `[MEASURED]`. “Exhaustively verifies all finite generated sequences” and “proves current Relay worker implementation” overstate the implementation `[MEASURED]` |
| Deterministic model boundary | `2.0/2.0` | All four required controls exist and passed, including two-dispatch reclaim and four-attempt P-27 traces `[MEASURED]`. The model does not retain live/stale actors or claim generations, and C8 injects stale behavior manually rather than deriving it from modeled ownership `[MEASURED]` |
| Hypothesis coverage and mutation sensitivity | `2.0/2.0` | Source config contains 200 broad and 100 forced-redispatch examples; the forced skeleton guarantees at least two dispatches `[MEASURED]`. The mutant independently failed with the required minimal two-write trace and the normal control returned green `[MEASURED]`. The randomized oracle checks safety only, not conditional exactness, and the forced skeleton does not itself guarantee two write boundaries in every example `[MEASURED]` |
| Isolation and target discipline | `1.0/1.0` | The harness refuses targets not matching `relay_din5_<PID>_<8hex>` and overrides `DATABASE_URL` before importing Relay models `[MEASURED]`. Current reconciliation found zero Din 5 probe databases and an unchanged evidence database `[MEASURED]` |
| PostgreSQL and production-path correspondence | `0.5/2.0` | The recorded witnesses demonstrate PostgreSQL unique-conflict arbitration, a real reaper process, a hard-killed child, and generation-blind SQL updates `[MEASURED]`. C6 is two coroutines/sessions sharing one PID, C7 uses custom harness workers with different transaction boundaries, and none of C6–C8 invokes `handle_effect()` or `run_worker()` `[MEASURED]` |
| Reconciliation, cleanup, and provenance | `1.0/1.0` | Fresh review measured the exact evidence fingerprint, expected status buckets, zero idle transactions, zero probe databases, zero Relay Python processes, matching frozen hash, and 7 passed in 1.20s `[MEASURED]`. `git diff --check` reported no whitespace error, with only an LF-to-CRLF working-tree warning `[MEASURED]` |
| **Total** | **`6.5 / 10`** | The score reflects strong model-level safety evidence but partial compliance with the required production-path witness contract `[INFERRED]`. |

**Official prediction grading — frozen text only:**

| Q | Credit | Reason |
|---|---:|---|
| Q1 | `0/1` | Frozen answer is `idk`; none of the required scope/completion mechanism appears in frozen text `[MEASURED]` |
| Q2 | `0/1` | Frozen answer is `idk`; no safety/P-27/conditional-exactness mechanism appears in frozen text `[MEASURED]` |
| Q3 | `0/1` | Frozen answer is `idk`; no isolation strategies or trade-offs appear in frozen text `[MEASURED]` |
| Q4 | `0/1` | Frozen answer is `idk`; no surviving-mutant interpretation appears in frozen text `[MEASURED]` |
| Q5 | `0/1` | Frozen answer is `idk`; no minimal-falsifier or admissibility reasoning appears in frozen text `[MEASURED]` |
| Q6 | `0/1` | Frozen answer is `idk`; no stale-A/new-B interleaving appears in frozen text `[MEASURED]` |
| **Total** | **`0.0 / 6.0`** | Post-run explanations and KEY-derived corrections receive no prediction credit `[INFERRED from the explicit KEY scoring rule]` |

**C0–C9 audit:**
- **C0 — pass.** The frozen file contains exactly six idk answers, and its freshly recomputed SHA-256 is `1E89D02AAB0D73ECAEF6FC71DFE82CD8D062E433D855CE6CF82A04CCDCC99427` `[MEASURED]`. Current evidence DB fingerprint is `relay|119|125|125|107|9|12|w3d4_enqueue_idempotency`, with buckets `dead_letter|3, failed|15, pending|4, succeeded|97` `[MEASURED]`.
- **C1 — partial.** The property card contains the required safety, conditional-exactness, completion-gap, P-27, isolation, mutation, and boundary fields `[MEASURED]`. Layer A ran a finite configured sample, not every finite model sequence; Layer B did not exercise the current worker implementation as claimed `[MEASURED]`.
- **C2 — partial pass.** The four named deterministic tests passed and independently assert dispatch count versus effect count `[MEASURED]`. The model tracks only one current worker_id, erases it on crash/reclaim, and has no claim generation or retained stale actor `[MEASURED]`. It therefore models effect-count safety more strongly than ownership interleavings `[INFERRED]`.
- **C3 — pass for the recorded finite safety search, not exhaustive proof.** The source config is 200 broad examples plus 100 forced-redispatch examples, and the redispatch skeleton guarantees `dispatches >= 2` `[MEASURED]`. The recorded 100/100, maximum dispatch count 4, and zero failures are consistent with the implementation `[MEASURED]`. Arbitrary generated actions can become no-ops, and the forced prefix guarantees a second claim but not a second effect-write boundary in every green example `[MEASURED]`.
- **C4 — pass.** A fresh `DIN5_MUTANT=no_dedup` run failed with exit code 1 and shrank to `claim(worker-1) -> effect_write() -> crash() -> reclaim() -> claim(worker-2) -> effect_write()`, with `dispatches=2, effect_writes=2, and effect_count=2` `[MEASURED]`. With the mutant unset, the same test passed `[MEASURED]`. This proves sensitivity to the model’s missing-dedup mutation, not broad mutation coverage of production code `[INFERRED]`.
- **C5 — pass.** The disposable-target guard checks `current_database()` and refuses names outside the exact Din 5 pattern `[MEASURED]`. The recorded disposable database began empty at Alembic head, and current review found `PROBE_DBS=0` with the evidence fingerprint unchanged `[MEASURED]`.
- **C6 — database invariant passes; required witness contract fails.** The recorded result `dispatches=2, distinct_workers=2, effects=1`, and rowcounts `{0,1}` demonstrates unique-index arbitration between two database sessions `[MEASURED]`. Both worker IDs embed the same `os.getpid()`, and `asyncio.gather()` runs both attempts inside the harness process `[MEASURED]`. The harness manually issues the conflict-safe insert rather than calling current `handle_effect()` `[MEASURED]`. It is therefore not the required two-process production-path witness `[INFERRED]`.
- **C7 — partial pass.** Worker A was a real child process, was hard-killed after its effect became durable, and the real `src.reaper` process established the committed reclaim barrier `[MEASURED]`. The required pre/barrier/final states and replay rowcount were recorded correctly `[MEASURED]`. Worker A and B were custom `pg_witness.py` functions, not `src.worker`; Worker A also combined claim, execution, and effect in one transaction, unlike production’s separate commits `[MEASURED]`. The state witness is valid, but production transaction-path correspondence is not established `[INFERRED]`.
- **C8 — pass as a direct boundary witness.** Both tests reproduced effect count 1, stale-A mark rowcount 1, and B mark rowcount 0 for the named trace `[MEASURED]`. The PostgreSQL witness is scripted sequential SQL rather than two live production workers, so it demonstrates generation blindness of the current predicate, not a reproduced production scheduler interleaving `[MEASURED]`.
- **C9 — pass.** Fresh review measured 7 passed in 1.20s, the mutant environment unset, zero Relay Python processes, zero idle transactions, zero Din 5 databases, and the exact unchanged evidence fingerprint `[MEASURED]`. The frozen hash still matches the opening value `[MEASURED]`. Temporary artifacts are absent as required after their summaries were copied into the log `[MEASURED]`.

**Required corrections:**
1. Replace “Layer A exhaustively verifies all finite generated sequences” with “Layer A checked the recorded finite Hypothesis examples within this model” `[INFERRED]`.
2. Replace “Layer B proves current Relay worker implementation” with “Layer B demonstrates the corresponding PostgreSQL constraints and SQL predicates using a test-side harness” `[INFERRED]`.
3. Do not describe C6 as two worker processes; it is two concurrent sessions/coroutines in one process with two logical worker strings `[MEASURED]`.
4. Do not describe C7 as current-worker correspondence; its custom workers clone the SQL and use transaction boundaries different from `src.worker` `[MEASURED]`.
5. Do not claim the model explores fencing state space. It lacks retained stale actors and claim generations; C8 is a manually scripted special case `[MEASURED]`.
6. Do not generalize one local `side_effects` row into “business side-effects commit at most once.” External email, HTTP, payment, or receiver behavior has no evidence here `[INFERRED]`.
7. Keep safety and progress separate: `effects <= 1` is the tested safety invariant; `effects = 1` is conditional on a legal committed write boundary and is not the randomized property oracle `[MEASURED]`.
8. Keep P-27 precise: dedup absorbs the extra dispatch’s duplicate local write, but it does not prevent duplicate execution or bound wasted work `[INFERRED]`.

**Retained limits:** The guarantee covers the current non-null local-ledger `effect_key` identity only; legacy NULL rows, missing keys, external effects, multiple legitimate effect kinds per job, and permanent-crash liveness remain outside the evidence `[INFERRED]`. `job_executions` remains pre-handler dispatch evidence rather than completion evidence, and `jobs.status` remains generation-blind `[MEASURED]`. Dedup narrows duplicate local-effect damage but does not provide fencing against stale marks or heartbeats `[INFERRED]`. The mutation kill covers one model policy fault and does not establish production-source mutation coverage `[INFERRED]`.

**Reviewer verdict:** Din 5 established a load-bearing model-level effect-safety test, a genuine mutation kill, PostgreSQL uniqueness behavior, crash/reclaim state evidence, and the stale-mark boundary `[MEASURED]`. Din 5 did not satisfy its own production-path/two-process witness requirement, so “Goal met: Yes” must be narrowed to “Goal partially met” `[INFERRED]`.

---