# WEEK 2 — Lease, heartbeat, reaper: atka hua job wapas kaun laayega

**Layer: L0 + L2** · Daily log with measurements, self-checks, and unresolved items.
Plan: [`../planning/WEEK_02.md`](../planning/WEEK_02.md) · Decisions: [`../DECISIONS.md`](../DECISIONS.md)

> **Plan intent rakhta hai, ye file outcome rakhti hai.** Jo bhi number, verdict ya score iss hafte me
> nikla, wo yahan aata hai — plan me kabhi nahi. Aur plan ko reality se match karne ke liye **edit nahi**
> karna: dono files apna sach rakhti hain, aur unka farq khud ek finding hai (E2).
>
> **Ye file abhi khali template hai.** Har `____` ek jagah hai jo uss din shaam bharti hai. Jo value aaj
> tak measure nahi hui, wo `____` rehti hai — plausible number likhna sabse mehnga shortcut hai. Agar koi
> cheez measure nahi ho paayi, `[NO EVIDENCE]` likho, blank ko guess se mat bharo.
>
> Har claim pe ek label: `[MEASURED]` (tumne khud chalaya) · `[MEASURED-R]` (reviewer ne chalaya) ·
> `[INFERRED]` (mechanism se reason kiya) · `[NO EVIDENCE]` (judgement, aur waise hi labelled).

---

## Contents

- [Stage Day — slip register](#stage-day--slip-register)
- [Divergence — Din 1 ki subah ka bench check (E2)](#divergence--din-1-ki-subah-ka-bench-check-e2)
- [Din 1 — Problem statement, phir lease column](#din-1--problem-statement-phir-lease-column-____)
- [Din 2 — Reaper: recovery bahar se aati hai](#din-2--reaper-recovery-bahar-se-aati-hai-____)
- [Din 3 — 🎯 Zinda par slow worker: ek job, do execution](#din-3--zinda-par-slow-worker-ek-job-do-execution-____)
- [Din 4 — Bounded retry, backoff, jitter](#din-4--bounded-retry-backoff-jitter-____)
- [Din 5 — `dead_letter` + graceful shutdown](#din-5--dead_letter--graceful-shutdown-____)
- [Din 6 — Close: reconcile, likho, handoff](#din-6--close-reconcile-likho-handoff-____)
- [Week close — reconcile chain aur handoff](#week-close--reconcile-chain-aur-handoff)

---

## Stage Day — slip register

Stage Day ka apna din hai (Din 7 ke agle din), aur uska **koi** `src/` change nahi hai. Yahan sirf ek cheez
likhi jaati hai: kaunsa item exit pe **file me** dikha aur kaunsa nahi. Exit criterion ek **file state** hai
— file kholke check hota hai, "kar liya" se nahi.

Label ek hi hai: **slip**. *Deferral* nahi. Deferral ek faisla hai jiska owner hota hai; slip ek din hai jo
nikal gaya. `POSTMORTEMS.md` ki entry #2 poore Week 0 se *"deferred"* label ke saath ghoom rahi thi jabki
honest label hamesha *"slipped"* tha — wahi galti dobara nahi.

**Stage Day date:** `2026-08-22` `[MEASURED-R]` — from file mtimes on the four artifacts plus the system date, not from a recorded start.

> **A gap in the date chain, recorded because it cannot be reconstructed later.** Din 6's log entry is
> `2026-08-19`. The plan's BENCH block *inferred* Din 7 as `2026-08-20`. Stage Day measures as
> `2026-08-22`. **Din 7 has no log entry at all** (`docs/logs/WEEK_01.md` ends at `# DIN 6`), so the
> day between `08-19` and `08-22` is unaccounted for in writing. This is not a Stage Day slip — it is a
> Week 1 Din 7 documentation gap, and it is carried below.

| Item | Exit criterion (file state) | Exit pe file me kya tha | Slip? | Ye item **specifically** kya maangta hai |
|---|---|---|---|---|
| `POSTMORTEMS.md` entry #2 | Third `## Incident` heading exists; answers the protection-vs-coverage question | `## Incident 02 — Cloudflare` present. Protection-vs-coverage answered explicitly, with a `[INFERRED — Relay extension]` tag separating the reviewer-supplied framing from the source | **No** | Nothing. Closed. Reviewer applied 9 factual corrections against the source — see corrections table below |
| `POSTMORTEMS.md` entry #3 (`P-06`, apna incident) | `## Incident` heading; cites `P-06` by name; contains the `pg_stat_activity` blast-radius table, the "resolution came from outside" line, and the age-not-established uncertainty | All four present. Blast-radius table has PIDs 53/61/45/1724, `pg_terminate_backend` line present, 5-day inferred-upper-bound recorded as inferred | **No** | Nothing. Closed. Reviewer removed one **fabricated** number (`12ms`) and corrected the four-session state claim, which contradicted `P-06`'s own table |
| DDIA Ch 7 doosra pass + Ch 8 intro | `DDIA_CH7_SUMMARY.md` ends with a `## Links` section, each line → a named `D-`/`P-`; `DDIA_CH8_LINKS.md` exists with ≥5 lines, no prose summary | CH7: `## Links — kaunsi line kis entry se judi hai`, 5 lines, each with a named entry. CH8: new file, 5 lines, no prose | **No** | Nothing. Closed. One right-hand side (`"Week 2 Reaper"`) was not an existing entry and was repointed to `P-06` by the reviewer |
| `docs/daily/WEEK_01_HANDOFF.md` (teen headings) | Three headings, exact names, exact order; none empty; both definitions written in the file | All three present in order, 4 + 2 + 4 lines, both definitions written out | **No** | Nothing. Closed |

**Gate arithmetic: 3 items, 3 closed. 0 slipped.** First week in the project where the Stage-Day-style
items did not slip — and the reason is structural, not motivational: they had their own day with
file-state exit criteria instead of being absorbed into a build day. `POSTMORTEMS.md` entry #2 had been
carrying a *"deferred"* label since Week 0; it is now closed, and the label was always *"slipped"*.

> **One process finding, and it is the plan's own warning firing on the plan's own gate.** The first
> gate check ran against **unsaved editor buffers**: all four files were on disk as
> `0 B` / stale (`POSTMORTEMS.md` `2787 B`, last written `2026-08-14`; `DDIA_CH7_SUMMARY.md` last
> written `2026-08-11`; the two new files `0 B`). The work was reported complete and, measured, was
> absent. Eight minutes later the same four paths measured `10415 / 48850 / 2188 / 1962 B`.
>
> Nothing was lost, and this is worth a line rather than a shrug: the plan says *"check karne ka
> tareeka teen file kholna hai, 'lagta hai ho gaya' nahi"* — and the thing that nearly passed the gate
> was **an editor showing content that the filesystem did not have**. Opening the file in the editor
> would *also* have shown content. So the check has to read the file **from disk**, and `git status`
> cannot help here because `docs/daily/` and `docs/roadmap/` are gitignored. This is `P-18`'s shape at
> the process level: a verification step that passes equally whether or not the mechanism is present.

**Slip line kaisi honi chahiye.** *"postmortems pending"* ek slip line nahi hai — wo status hai. Slip line
me wo cheez hoti hai jo item ko **abhi** chahiye: kaunsa source pick nahi hua, kaunse kitne pages bache,
kaunsi heading khali hai. Agar line padh ke agla kadam pata nahi chalta, line adhoori hai.

**Partial completion per item likhi jaati hai**, item-level pe — "Stage Day mostly ho gaya" jaisi line
kahin nahi jaati.

**Ye slip zinda kahan rehta hai:**

| Kahan | Kya likha jaata hai | Bhara? |
|---|---|---|
| DoD ka carried-debt group (`WEEK_02.md`) | Stage Day items: **nothing to carry, 3/3 closed.** What *does* carry is the Din 7 debt below, and it is a Week 1 item, not a Stage Day one | ✅ recorded here |
| `LEARNING_LOG.md` open-items table | Same — no Stage Day item to add. The Din 7 debt needs a row, owner = user | ❌ **not done** — needs the Din 7 question answered first (see below) |

**Carried into Din 1 — Week 1 Din 7 debt, and this is the only open item on the board:**

| Item | Status | What it specifically needs |
|---|---|---|
| **Din 7 has no log entry** | Open `[MEASURED-R]` — `docs/logs/WEEK_01.md` ends at `# DIN 6` (`2026-08-19`) | Either the Din 7 entry gets written from the day's actual output, **or** it is recorded that Din 7 was not run and the BENCH block's provenance is corrected. Right now the plan's BENCH block says *"Measured on: Din 7 ke end pe"* and reports 86 rows / `max(id) 87`, while `CURRENT_WEEK.md` reports Din 6 close as 78 rows / `max(id) 78` / seq `79`. **Those two cannot both be Din 6.** So something was run and measured after Din 6 — but there is no entry saying what |
| **The five written Week 2 answers** | Open, and this is the fourth slip in a row for the same item | `CURRENT_WEEK.md` names them: the reaper's predicate with today's columns and why it fails, the smallest schema addition and the new failure it creates, 41 versus 63, and the short lease. Slipped Din 5 Step 6 → Din 6 Step 2 → Din 7 → now. `CURRENT_WEEK.md` states the blocking rule in its own words: *"Week 2 Din 1 should not start before it exists in his own words."* **This is deliberately not being written for the user** |
| `CURRENT_WEEK.md` still points at Week 1 | Open | Repoint to Week 2 + update the week status table. Plan assigns this to **Din 1's** log obligation, so it is on schedule, not late |

**Gate ka result:** Din 1 tab tak shuru nahi hota jab tak teeno exit criteria satisfy na ho. Handoff list
ki **teesri heading** khali hone wala slip Din 1 ko **rok deta hai** — wo heading Din 1 Step 1 ka input hai.

- **Gate result:** ✅ **PASS** on all three Stage Day exit criteria, verified by reading the four files
  **from disk** (sizes and `## ` headings grepped, not eyeballed in an editor).
- Din 1 shuru hua? **Not yet.** The Stage Day gate is clear; Din 1's own prereq table is not — the
  `psql` bench check is still unrun, and it is Din 1's first executable step.
- Kitne din late, aur kis item ki wajah se? Stage Day itself: **zero days late.** The unaccounted day
  sits between Din 6 (`08-19`) and Stage Day (`08-22`), and it belongs to Din 7, not here.
- Din 1 kis named debt ke saath shuru hua? **Two named debts, both Week 1's:** (1) no Din 7 log entry,
  so the BENCH block's `[MEASURED]` provenance is unverifiable; (2) the five written Week 2 answers,
  fourth consecutive slip. Din 1's Step 1 consumes the handoff's third heading **and** *"Din 5/Din 7 ka
  likha hua text"* as given — half of that given does not exist.
- **What this does NOT block:** the handoff file's third heading exists and is good, so Din 1 Step 1 has
  its primary input. The BRIEF for Din 1 is written and carries the five answers as **Step 0**, which is
  the honest place for a debt that has now outlived three attempts to schedule it.

---

## Divergence — Din 1 ki subah ka bench check (E2)

Din 1 Step 1 se **pehle** bench check hota hai. Match kare to ek line likh do aur aage badho. Match na kare
to **Step 1 rukta hai**, pehle divergence classify hoti hai — classify ka matlab naye numbers ka **cause**
naam lena hai, *"numbers alag hain"* likhna nahi.

**Check ki date:** `2026-08-23` · **Match?** **Haan — zero divergence, saari aath lines pe.**

| Kya check kiya | Expected (BENCH block se copy) | Mila (`psql` se, verbatim) | Match? |
|---|---|---|---|
| `failed` / `running` / `succeeded` counts | 9 / 3 / 74 | 9 / 3 / 74 | ✅ |
| total rows | 86 | 86 | ✅ |
| `max(id)` aur `jobs_id_seq` `last_value` | 87 / 87 | 87 / 87 | ✅ |
| `job_executions` rows | 57 | 57 | ✅ |
| jobs 41 / 63 / 65 ka `status` | teeno `running` | teeno `running` | ✅ |
| job 75 ka `status` | `failed` | `failed` | ✅ |
| `\d jobs` — columns aur `pg_constraint` definition | 6 columns, `jobs_status_check` 4 values pe | 6 columns, `jobs_status_check` 4 values pe | ✅ |
| connections to `relay`, `idle in transaction`, worker processes | 1 / 0 / 0 | idle sessions 0, worker processes 0 | ✅ |

**Classification — E2 ki kaunsi row lagi:** **koi nahi. E2 aaj trigger hua hi nahi.**

**Aur ye result apne aap me ek finding hai, kyunki iska ek doosra sawaal band hota hai.** BENCH block ka
label `[MEASURED] on Din 7 ke end` tha, par `docs/logs/WEEK_01.md` `# DIN 6` pe khatam hoti hai — Din 7 ki
koi entry nahi hai. To Din 1 ki subah tak ye khula tha ki BENCH block ke numbers asli hain ya kahin se
aaye hain. **Aaj ke bench ne unhe exactly reproduce kar diya (86 / `max(id)` 87 / seq 87 / 57), Din 6 ke
numbers ko nahi (78 / 78 / 79 / 46).** Matlab: Din 7 **chala tha aur measure hua tha** — jo gayab hai wo
sirf uski log entry hai. BENCH block ki provenance theek hai; documentation gap asli hai.

Ye Week 2 ke KEY ki teen possibilities me se **pehli** thi, aur wo `E2`/`P-13` wali nahi thi. Uss
distinction ko `[MEASURED]` ki tarah likhna theek hai, kyunki dono candidate baselines me `8` rows aur
`11` sequence values ka farq tha — reproduce hone ki gunjaish nahi thi.

**Naya baseline — iss hafte ka arithmetic yahan se shuru hoga:** **BENCH block hi baseline hai**, badla
nahi. Din 1 ka closing (niche) usme se delta nikaal ke banta hai.

**Ek carried debt band hota hai, ek nahi:**

| Debt | Ab kya hai |
|---|---|
| *"BENCH block ki `[MEASURED]` provenance unverifiable hai"* | **Band.** Aaj ke bench ne reproduce kar diya `[MEASURED]` |
| *"Din 7 ki log entry maujood nahi hai"* | **Khula.** Numbers verify ho gaye, par Din 7 me kya hua — kaunsa experiment, kaunsa verdict — wo kahin likha nahi hai aur reconstruct nahi hoga. `WEEK_01.md` me ye gap ek line ki tarah rehna chahiye, silently bhara nahi jaana chahiye |

**Ye nahi hota, aur rule dono directions me lagta hai:**

- Plan ka BENCH block **edit nahi** hota. Wo Din 7 ke end ka `[MEASURED]` snapshot hai; usko badalna ye
  record mita dena hai ki plan **kis** state ke against likha gaya tha.
- Reality **repair nahi** hoti. Counts wapas plan wale numbers pe laane ke liye rows insert/delete karna
  manufactured evidence hai, aur uske baad poore hafte ka arithmetic ek banayi hui baseline pe khada hoga.

**Agar fixture (41/63/65) khatam ho gayi:** Din 2 apni stuck rows **seed** karega, aur yahan likha jaata
hai ki 41/63/65 ka evidence dobara reproducible **nahi** hai: `____`

---

## Din 1 — Problem statement, phir lease column (`2026-08-23`)

**Original goal (from the plan):** Problem statement apne shabdon me likhna (aaj ke columns kya measure
karte hain, naive predicate kis direction me fail karta hai, sabse chhoti schema addition, wo addition
kaunsa naya failure laati hai, `Interim_Guarantee`) — **phir** ek column, ek migration dono direction me,
aur claim `UPDATE` me lease ka write. Lease ki **duration** aaj decide nahi hoti.

**Goal met? — `partial`.** Jo hua: bench check (zero divergence), migration up+down, claim lease likhti
hai, backfill decision Option B cost ke saath, three-valued logic differential measured. Jo **nahi** hua:
**Step 0 ke paanch likhe hue answers** (paanchwi baar slip), **Part B ke prediction answers likhit roop me**
(is review ko supply nahi hue, to score nahi ho sakte), **Ch 8 links file me append** (`DDIA_CH8_LINKS.md`
ka mtime abhi bhi `2026-08-22 17:28`, Stage Day ka), aur **cleanup** — Step 7 ke **do worker processes
abhi bhi zinda hain**.

**Anything else learned?** Haan, teen cheezein jo plan ne poochhi hi nahi thi:

1. **Migration chain me ek khaali revision permanently baithi hai** (`79cb2ee38481`, `upgrade(): pass`).
   Step 6 ka reversibility check **pass hua, par ek layer shallow reason se** — `downgrade -1` uss khaali
   revision pe utra, aur wahan column drop hona hi tha. Doosra `downgrade -1` success report karke kuch
   nahi badalta.
2. **Column ka naam `claimed_at` chuna gaya, aur wo *event* hai, *deadline* nahi** — matlab lease ki
   duration Din 2 ke predicate me ghus aayi hai, jabki plan usko `D-22`/Din 6 tak defer karta hai.
3. **Job 88 ka enqueue-to-claim gap `00:01:33.705`** `[MEASURED-R]` — yaani aaj ki apni row pe naive
   `created_at` predicate ka dangerous failure literally reproduce ho sakta tha. Ye number report me nahi
   tha aur ye Step 2 ki poori argument ka apna evidence hai.

---

### 📊 Measured / Observed

**Opening check (`P-13`, `P-06`) — din ka pehla kaam, aur ye har din hota hai:**

| Kya | Value | Label |
|---|---|---|
| worker processes chal rahe hain | 0 | `[MEASURED]` |
| `idle in transaction` sessions | 0 | `[MEASURED]` |
| connections to `relay` | not recorded separately; `idle in transaction` = 0 tha | `[MEASURED]` |

**M1 — bench, zero divergence.** Poora table upar ke Divergence section me hai. Short: `9 / 3 / 74`,
total `86`, `max(id) 87`, seq `87`, `job_executions 57`, 41/63/65 `running`, 75 `failed`. `[MEASURED]`

**M2 — `\d jobs` migration ke pehle aur baad, aur `downgrade` ka cycle** `[MEASURED]`

```
alembic downgrade -1   -> \d jobs  =  6 columns  (claimed_at absent)
alembic upgrade head   -> \d jobs  =  7 columns  (claimed_at | timestamp with time zone | nullable)
```

Aaj shaam re-verified `[MEASURED-R]`:

```
 claimed_at | timestamp with time zone |           |          |
 alembic_version.version_num = 75a845575d2e
```

**M3 — claim lease likhti hai (job 88, `slow` handler, 8 s)** `[MEASURED]`

```
id 88 | status running | claimed_at 2026-08-23 09:46:55.549422+00 | now() 2026-08-23 09:47:05+00   (Etc/UTC)
```

Shaam ko wahi row `[MEASURED-R]`:

```
 id | type | status    | created_at                   | claimed_at                    | claimed_at - created_at
 88 | slow | succeeded | 2026-08-23 09:45:21.84424+00 | 2026-08-23 09:46:55.549422+00 | 00:01:33.705182
 job_executions: job_id 88 | worker-32636 | 2026-08-23 09:46:55.597239+00
```

Teesra column aaj ka sabse kaam ka number hai aur report me nahi tha: **enqueue se claim tak 93.7 s**.
Naive predicate `created_at < now() - interval '60 seconds'` iss row pe **claim hone ke instant** match
kar jaata — job zinda, handler abhi shuru bhi nahi hua, aur reaper usko utha leta. Step 2 ka
"dangerous direction" wala argument aaj apni hi row pe reproduce ho sakta tha.

**M4 — three-valued logic differential** `[MEASURED]`, aaj shaam reproduce `[MEASURED-R]`

```
select count(*) from jobs where status='running' and claimed_at < now();                          -> 0
select count(*) from jobs where status='running' and (claimed_at is null or claimed_at < now());   -> 3
```

**Aaj ye numbers likhne hain (plan ka Din 1 obligation):**

| Kya | Value / text | Label |
|---|---|---|
| **Problem statement ka poora text** (apne shabdon me, Step 1 ka output) | Substance niche 💡 me hai, par **apne shabdon me disk pe nahi likha gaya** — ye field abhi bhi user ka hai | `[NO EVIDENCE]` for authorship |
| Chuna hua column name, type, nullability | `claimed_at`, `DateTime(timezone=True)` → `timestamptz`, `nullable=True` | `[MEASURED]` |
| Migration up + down chala — `downgrade` ka actual output | M2, dono `\d jobs` | `[MEASURED]` |
| `NULL` backfill ka faisla (migration me backfill **ya** `IS NULL` branch) | **Option B** — `NULL` rehne diya, predicate me `IS NULL` branch | — |
| Uss faisle ki **cost**, apne shabdon me | `D-07` ka argument: backfilled value 41/63/65 ke liye **fiction** hoti, aur `downgrade` usko wapas nahi laa sakti — migration shape me reversible hoti, information me nahi. Iski keemat: `IS NULL` branch **hamesha** predicate me rahegi, aur wo har `NULL`-lease row ko reclaimable banati hai — including koi future writer jo `SET` me `claimed_at` likhna bhool jaaye | — |
| Claim ke baad ek row ka lease value (non-null) | M3 | `[MEASURED]` |
| Purani `running` rows (41/63/65) pe lease column ka value | teeno pe `NULL` | `[MEASURED]` |
| Three-valued logic wala differential — dono counts | `0` aur `3` | `[MEASURED]` |
| `Interim_Guarantee` — kaunsa contract point kis ke against trade hua | Contract **#1** behtar hota hai: accepted job hamesha ke liye `running` me atki nahi rehti, wo wapas claimable ho jaati hai. Iski keemat contract **#2** deta hai: reclaim ka matlab hai ek handler jo already chal chuka hai dobara chal sakta hai, aur dono executions individually legit hain. To lease + reaper stranded-work ka window **narrow karta hai** aur duplicate side effect ka window **band nahi karta**. #2 Week 3 ke dedup tak **unprotected** rehta hai. Aur ye strict improvement nahi, ek **trade** hai: pehle atki hui job bekaar padi rehti thi — bura, par **ek baar**. Ab wo dobara chalayi jaayegi jabki pehla worker possibly abhi bhi chal raha hai | — |

**Aur ek cheez jo aaj plan ne poochhi nahi thi par reaper ka faisla decide karti hai** — `claimed_at`
naam ka structural asar:

`claimed_at` ek **event** hai, `lease_expires_at` ek **deadline** hota. Farq predicate me dikhta hai:

```
deadline column:  WHERE lease_expires_at < now()                        -- duration query me nahi hai
event column:     WHERE claimed_at < now() - interval '<duration>'      -- duration ab har predicate me hai
```

Matlab lease ki **duration** — jo plan `D-22` / Din 6 tak defer karta hai, kyunki uski `Cost` line Din 3
ke duplicate number ke bina likhi hi nahi ja sakti — **Din 2 ke predicate me aa gayi hai**. Ye galat
choice nahi hai (`claimed_at` sach record karta hai: ye row iss instant claim hui; `lease_expires_at` ek
policy record karta hai jo tab badalti hai jab duration badalti hai), par iski keemat aaj likhni hai:
Din 2 ko ek duration **chunni padegi**, aur wo number Din 3 ka evidence aane se **pehle** chuna hua
number hoga. `D-22` ko Din 6 pe likhte waqt ye baat yaad rakhni hai — us waqt sawaal hoga
*"ye number measure kiya ya choose kiya"*, aur jawab "choose kiya, Din 2 pe, evidence se pehle" hoga.

**Aur isi wajah se Step 9 ki pehli query reaper ka predicate nahi hai.** `claimed_at < now()` ka matlab
hai *"kabhi bhi claim hui thi"* — yaani **zero-second lease**. Aaj usne `0` diya sirf isliye ki teeno
`running` rows pe `claimed_at` `NULL` hai. Agar job 88 uss waqt `running` hoti, ye query usko claim hone
ke **usi second** utha leti. Differential (`0` vs `3`) `NULL` trap theek dikhata hai — aur usi line me ek
doosra defect chhupa rehta hai. Din 2 ka predicate iss query ki shape se **nahi** aa sakta.

**Closing reconciliation** — opening counts BENCH block se, delta aaj ka. **Kabhi `max(id)` se nahi, kabhi
id contiguity se nahi:**

| Line | Value |
|---|---|
| opening `pending` / `running` / `succeeded` / `failed` / total (BENCH block) | `0 / 3 / 74 / 9 / 86` |
| `+` aaj enqueue hui probe jobs (ids **naam se**) | **id 88** (`type='slow'`) — ek row |
| `−` unme se jo `succeeded` / `failed` hui | 88 → `succeeded` |
| `=` closing counts | `0 / 3 / 75 / 9 / 87` |
| `psql` ke actual counts | `running 3`, `succeeded 75`, `failed 9`, total `87`, `max(id) 88`, seq `88` — `[MEASURED-R]` aaj shaam |
| Match? | **Haan.** `9 + 3 + 75 = 87` |
| `job_executions` delta | `57 → 58`, `+1`. Sirf ek job dispatch hui, to `+1` sahi hai `[MEASURED-R]` |
| Migration ne kisi row ka `status` badla? | **Nahi.** `running` opening `3` (41/63/65) tha aur closing bhi `3` hai, aur wo wahi teen ids hain `[MEASURED-R]`. `attempts <> 0` wali rows aaj bhi `0` hain — retry ka koi rasta galti se nahi chala `[MEASURED-R]` |

Match na kare to wo **finding** hai (E5), adjust karke balance nahi hoti. Pehla suspect ek bhoola hua worker
(`P-13`). **Finding: reconciliation match karta hai, par `P-13` phir bhi hua — sirf usne counts contaminate
nahi kiye.** Niche cleanup dekho: do worker abhi zinda hain, aur unhone kuch claim nahi kiya kyunki
`pending` count `0` hai aur `running` rows claim query ko dikhti hi nahi (`P-16`). **Yaani clean
reconciliation ne ek asli hygiene failure ko chhupa liya.** Arithmetic ne wo cheez detect nahi ki jo
detect karne ke liye wo likhi gayi thi — aur agar aaj ek bhi `pending` row hoti, ye entry galat hoti.

**Cleanup — ye hissa fail hua, aur ye sabse important line hai iss entry me:**

| Kya | Status |
|---|---|
| stdout capture file (`python -u` wali) delete hui? | not recorded — report me mention nahi tha, aur koi capture file repo me nahi mili |
| Worker processes band hue? | **Nahi.** `2026-08-23 10:27 UTC` pe **do** processes zinda the: OS PID `34280` aur `32636`, dono `python -m src.worker`, dono `StartTime 15:16:54 IST` `[MEASURED-R]` |
| Live DB backend? | **Haan, ek.** backend PID `3119`, `application_name` khali (asyncpg), `backend_start 09:46:55.463+00`, aur `state_change` do baar 2 s ke andar aage badha (`10:26:29.02`, phir `10:27:21.67`) — **~40 minute baad bhi poll kar raha tha** `[MEASURED-R]` |
| Kaunsa process job 88 chalayi thi? | `job_executions.worker_id = worker-32636` → OS PID `32636` `[MEASURED-R]` |
| Do process, par ek hi asyncpg backend — kyun? | **Not established.** Ek hi non-psql connection dikhi. Doosre process ka connection kahan hai, ye measure nahi hua |
| Leftover `psql` sessions | `8`, sabhi `state = 'idle'`, sabka `xact_start` `NULL`, sabse purani `09:17:53+00` `[MEASURED-R]`. **`idle in transaction` zero hai** — matlab `P-06` ka mechanism (locks pakde baithna) maujood **nahi** hai. Ye hygiene hai, lock hazard nahi |
| Probe **rows delete nahi** hoti; unke ids | **id 88** — rakhi gayi hai, delta me count hai |

**Ye `P-13` ka teesra instance hai** aur pehla jisme wo *bina nuksaan* hua. Nuksaan na hone ki wajah luck
hai, discipline nahi: `pending` count `0` thi. Aur closing report me *"Zero idle sessions"* likha gaya tha —
wo `idle in transaction` ke liye sach hai, par *"0 worker processes"* closing pe **re-verify nahi hua**, aur
wo sach nahi tha.

**Commit:** **nahi hua.** `git log` ka HEAD abhi bhi `9d60df7 docs: complete Stage Day requirements` hai,
aur `git status` ye dikhata hai `[MEASURED-R]`:

```
 M labs/day2_signals.py
 M src/models.py
 M src/worker.py
?? alembic/versions/75a845575d2e_add_claimed_at_to_jobs.py
?? alembic/versions/79cb2ee38481_add_claimed_at_to_jobs.py
```

`labs/day2_signals.py` bhi modified hai — wo Din 1 ke scope me nahi tha. Kya badla, ye recorded nahi hai;
stage karne se pehle uska diff dekh lena chahiye, aur agar wo aaj ka kaam nahi hai to usko **alag** commit
me rakhna hai. `docs/planning/`, `docs/roadmap/` aur `docs/daily/` gitignored hain, to khali `git status`
ka matlab "kuch likha nahi" **nahi** hai.

---

### 🔧 Migration chain — ek khaali revision jo permanently baithi rahegi

Ye report me nahi tha aur reversibility check ke matlab ko badalta hai `[MEASURED-R]`.

```
$ python -m alembic history
79cb2ee38481 -> 75a845575d2e (head), add claimed_at to jobs
4bc263254b10 -> 79cb2ee38481, add claimed_at to jobs
81b6e20c9ea7 -> 4bc263254b10, create_job_executions_table
<base> -> 81b6e20c9ea7, create_jobs_table
```

**Do revisions, ek hi message, aur pehli khaali hai:**

| Revision | Create Date | `upgrade()` | `downgrade()` |
|---|---|---|---|
| `79cb2ee38481` | `15:07:40.511` | `pass` | `pass` |
| `75a845575d2e` | `15:09:36.624` | `op.add_column('jobs', sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True))` | `op.drop_column('jobs', 'claimed_at')` |

**Cause, aur ye mtime se establish hota hai:** `src/models.py` ka mtime `15:08:44` hai — pehli revision
`15:07:40` pe generate hui, yaani **`claimed_at` model me aane se pehle**. Autogenerate ne diff nahi paaya,
`pass` likh diya, aur **exit status zero** diya. `[MEASURED-R]`

**Iska asar Step 6 ke verification pe:**

- `alembic downgrade -1` head (`75a845575d2e`) se **khaali revision** pe utra. Column drop hua, `\d jobs`
  ne 6 columns dikhaye. Check **pass**, aur uska mechanism asli tha.
- Par ek **doosra** `alembic downgrade -1` khaali revision ka `downgrade()` chalata — `pass` — aur success
  report karke **kuch nahi badalta**. Yaani chain me ek step hai jo hamesha "chala" bolega aur kabhi kuch
  nahi karega.
- **Aur asli baat:** agar sirf wahi khaali revision bani hoti, `alembic upgrade head` `Running upgrade
  4bc263254b10 -> 79cb2ee38481` print karke exit `0` deta, aur column **nahi** banta. Migration ka output
  success aur no-op me **farq nahi** karta.

Ye `P-18` ki exact shape hai, migration layer pe: **ek verification jiska expected output mechanism ke
hone aur na hone, dono se milta hai.** Iss baar wo pakda gaya kyunki agli hi statement (claim ka
`SET claimed_at=...`) column ke bina **loud** fail karti. Silent version wo hota jo `DIN_01_KEY.md` Step 7
me likha hai: column migration me ho aur `models.py` me na ho.

**Aaj isko theek nahi karna.** Khaali revision chain ka hissa hai aur `alembic_version` usse guzar chuki
hai; usko delete karna history rewrite hai. Wo wahan rehti hai aur **iss log me uska naam** likha rehta
hai — yahi record hai ki wo dead hai, bhooli hui nahi.

---

### 💡 What I Understood

> ⚠️ **Ye section reviewer ne likha hai, user ne nahi.** Isme wo hai jo aaj ke session ne **establish**
> kiya — user ki samajh ka record nahi. Iska poora point yahi hai ki ise **apne shabdon me replace kiya
> jaaye**, aur jo cheez sirf padhke aayi uske saath likha jaaye ki wo padhi hui hai. Jab tak replace nahi
> hota, ye entry apni sabse zaroori field pe `[NO EVIDENCE]` carry karti hai.

Aaj ke session ne teen cheezein establish ki, aur teeno measurement se aayi hain:

**1. Column add karna aasan tha; column ka *naam* asli decision tha.** `claimed_at` aur
`lease_expires_at` ek hi type, ek hi nullability, ek hi migration lete hain — aur do bilkul alag
predicates maangte hain. Event column duration ko **query me** rakhta hai, deadline column duration ko
**writer me** rakhta hai. Kyunki `claimed_at` chuna gaya, lease ki duration Din 2 ke predicate me aa gayi
hai, jabki plan usko `D-22`/Din 6 tak defer kar raha tha. Aaj ka sabaq: schema ka shape decide karte waqt
ye poochhna padta hai ki **iss column ko padhne wali query kaisi dikhegi**, sirf ye nahi ki column me kya
store hoga.

**2. `NULL` ne `false` ki tarah behave nahi kiya, aur wo do counts me dikha — `0` versus `3`.** Ye
prediction se aayi baat nahi hai, output se aayi hai. Aur ek layer neeche: Step 9 ki pehli query
(`claimed_at < now()`) ne `0` diya, aur wo `0` **do** wajah se aa sakta tha — `NULL` trap, ya "koi row
expired nahi thi". Aaj wo pehli wajah thi. Same output, do kahaniyan; farq sirf doosri query ne dikhaya.
**Ek count kabhi apna cause nahi batata.**

**3. Ek migration jo "chali" aur kuch nahi badla.** `--autogenerate` ne khaali `upgrade(): pass` likha
kyunki `models.py` me column tab tha hi nahi, aur usne exit status `0` diya. Yahan wo silent nahi raha
sirf isliye ki agli statement column ke bina loud fail karti. Ye `P-18` ka wahi shape hai jo Din 6 pe
verification me mila tha — ab tooling layer pe. **Exit code `0` ka matlab "kaam hua" nahi hai; matlab
"error nahi aayi" hai.**

**Aur ek cheez jo aaj sabse mehngi nahi thi par ho sakti thi:** clean reconciliation ne ek asli failure
chhupa liya. Do worker chalte reh gaye, aur arithmetic ne unhe nahi pakda — kyunki `pending` count `0`
thi. Agar ek bhi `pending` row hoti, closing counts galat hote. Reconciliation ne aaj kaam kiya, par wo
`P-13` ko **detect** nahi kar sakti; uske liye process check chahiye, aur wo closing pe chala hi nahi.

---

### 🧠 Self-Check (honest — 0 / 6 self-answered on Part B, aur ye score data ke absence ka hai, galat jawab ka nahi)

`____`

**Part B ke chhe sawaalon ka koi likha hua pre-measurement answer iss review ko supply nahi hua.** Report
me **outcomes** the, predictions nahi. Reviewer rule 1 aur 6 saaf hain: jo field report nahi hui uska
plausible value nahi bharna, aur jo answer nahi hua usko correct me count nahi karna. To aaj ka honest
score **0/6 scorable** hai — iska matlab "chhe galat" nahi, iska matlab "chhe ka evidence nahi".

Agar wo chhe jawab kaagaz pe ya kisi file me likhe hue hain, unhe paste karo aur ye section per-question
re-score ho jaayega. **Aur agar wo likhe hi nahi gaye the, to wahi likhna hai** — kyunki uske bina din ke
measurements ka comparison base hi nahi banta, aur `DIN_01_KEY.md` khulne ke baad wo base dobara nahi ban
sakta (`E8` — seal khulne ke baad answer *reconstruction* score karta hai, *answered* nahi).

Per-question status, taki gap naam se dikhe:

| Part B Q | Kya poochha gaya | Status |
|---|---|---|
| 1 | `created_at` kya measure karta hai; naive predicate safe ya dangerous direction | **not supplied.** Report ka content isse cover karta hai, par execution ke **baad** aaya |
| 2 | `job_executions` row = claim current? `record_execution()` kis transaction me | **not supplied.** Report me `D-21`/evidence-not-control-input ka jawab hai, phir bhi post-hoc |
| 3 | `now()` transaction-start ya statement time; lambi reaper transaction me matlab | **not supplied**, aur ye Din 2 ka direct input hai |
| 4 | `NOT NULL` 86 rows se kya demand karta hai; `NULL` predicate se kya | **not supplied.** Faisla (Option B) aur uski cost aayi — wo Step 8 ka deliverable hai, Q4 ka answer nahi |
| 5 | Kaunsa contract point behtar, kaunsa kamzor | **not supplied.** `Interim_Guarantee` ka text sahi shape me aaya (`narrows` / `does not close`), par prediction ki tarah nahi |
| 6 | Claim ka `rowcount` ab kuch **naya** batata hai? | **not supplied**, aur ye woh sawaal hai jiska galat jawab sabse mehnga hota — `rowcount = 1` lease likhne ka proof **nahi** hai |

**Step 0 — paanch likhe hue answers: paanchwi baar slip.** `docs/logs/WEEK_02.md` ka mtime din shuru hone
tak `2026-08-22 18:01` tha, to wo paanch answers disk pe nahi the `[MEASURED-R]`. Report ka content
teen-chaar ko cover karta hai, par wo BRIEF aur plan padhne ke **baad** likha gaya — `E8` ke hisaab se wo
**reconstruction** hai, *answered* nahi. Paanchwa item (*"short lease — handler se chhoti lease me kya
galat hota hai"*) report me bilkul nahi aaya, aur wo **Din 3 ka centrepiece** hai.

`idk` ek valid answer hai aur wo **not-answered** ki tarah score hota hai. Guess ko knowledge ki tarah
likhna dono directions me dishonest hai — jo aata tha usko miss likhna bhi revision material kharab karta
hai.

**Corrections — jo maine kaha aur jo measurement/review ne refute kiya:**

| # | I said | Actual | The transferable lesson |
|---|---|---|---|
| 1 | *"Week 2 Din 1 ka execution **100% complete aur verify** ho gaya hai"* | **Partial.** Step 0 (paanch answers) nahi hua, Step 10 ka deliverable disk pe nahi hai (`DDIA_CH8_LINKS.md` mtime abhi bhi Stage Day ka `2026-08-22 17:28`), Step 11 ka log / `PROBLEMS.md` / `CURRENT_WEEK.md` / commit nahi hua, aur cleanup fail hua `[MEASURED-R]` | "Verified" ka matlab **file state check karna** hai. Ye wahi galti hai jo Stage Day pe unsaved buffers ke saath hui thi — us din bhi kaam complete report hua tha aur disk khali tha. Do baar, ek hi hafte me |
| 2 | *"Zero idle sessions"* aur implicitly clean close | `idle in transaction` **0** — ye sach hai. Par closing pe **do worker process zinda** the aur ek asyncpg backend `~40 min` baad bhi poll kar raha tha `[MEASURED-R]` | `idle in transaction = 0` aur `workers = 0` do **alag** checks hain. Pehla lock hazard dekhta hai (`P-06`), doosra measurement contamination (`P-13`). Ek ko dekhkar doosre ka dava nahi kar sakte |
| 3 | *"Migration 'add claimed_at to jobs' generated"* — ek migration | **Do** revisions bani, dono ka message same, aur pehli (`79cb2ee38481`) **khaali** hai — `upgrade(): pass` `[MEASURED-R]` | `--autogenerate` model state ke against diff leta hai. Model me column aane se **pehle** chalane pe wo khaali revision banata hai aur exit `0` deta hai. Ek `alembic revision` ka success uske andar kuch hone ka proof nahi hai |
| 4 | Step 7 ka clock evidence: `claimed_at 09:46:55+00` aur `now() 09:47:05+00` | Dono **DB clock** ke hain. Ye pair lease value verify karta hai — par KEY ne jo maanga tha (DB clock versus worker stdout ka **offset**) wo isse measure hi nahi hota `[MEASURED-R]` | *"Ek hi query me dono"* clock-consistency ke liye sahi hai, par do **different** clocks ka offset measure karne ke liye dono clocks ko padhna padta hai. Ek clock ko do baar padhna offset nahi deta |
| 5 | Step 9 ka `claimed_at < now()` → `0` = *"koi expired lease nahi"* | `0` aaya kyunki teeno rows pe `claimed_at` `NULL` hai. **Aur usi query me ek doosra defect hai:** `claimed_at` event column hai, to `< now()` ka matlab zero-second lease hai — job 88 `running` hoti to wo claim ke **usi second** match kar jaati `[MEASURED-R]` | Ek `0` count ke kai causes hote hain. Aur ek query ka differential ek defect dikha ke doosre ko chhupa sakta hai — Step 9 ne `NULL` trap dikhaya aur duration ki gayabi chhupa li |

*(Ye table kabhi delete nahi hoti, na chhoti hoti hai.)*

---

### 🚧 Unresolved / Follow-ups

**New, from today:**

| # | Item | Kya specifically chahiye |
|---|---|---|
| 1 | **Do worker process abhi zinda hain** — OS PID `34280` aur `32636` | Din 2 ka pehla kaam. Inhe band karo (`Stop-Process -Id 34280,32636`), phir opening check **dobara** chalao. Jab tak ye chal rahe hain, Din 2 ka opening bench contaminated hai — aur Din 2 ka poora experiment 41/63/65 pe hai, jo reclaim hone ke baad `pending` ban jaayengi aur **turant claimable** ho jaayengi. Ek chalta worker unhe uthaa lega aur reclaim latency ka number kisi ka nahi hoga |
| 2 | **Do process, ek asyncpg backend** — kyun? | Not established. Measure karne layak hai: dono PIDs ka `pg_stat_activity` me mapping. Ho sakta hai ek process apna connection kho chuka hai aur retry kar raha hai, ya wo loop me hi nahi hai |
| 3 | **`claimed_at` event column hai, to duration Din 2 ke predicate me aa gayi** | Din 2 pe ek duration **chunni** padegi, Din 3 ka evidence aane se pehle. Din 6 pe `D-22` likhte waqt ye line jaani chahiye: *"ye number choose kiya gaya, Din 2 pe, measurement se pehle"* |
| 4 | **`79cb2ee38481` — khaali revision chain me permanent hai** | Aaj theek **nahi** karna (history rewrite). Naam iss log me hai, wahi record hai. Follow-up ye hai: aage `alembic revision --autogenerate` chalane se pehle `models.py` save ho chuki hai, ye check karna |
| 5 | **`labs/day2_signals.py` modified hai aur wo Din 1 ka scope nahi tha** | Uska diff dekho. Agar aaj ka kaam nahi hai to alag commit, ya revert |
| 6 | **Clock offset ka aadha measurement** | DB session versus **worker stdout** — dono ko ek jagah padho aur actual difference likho. Aaj ka `+5:30` process-start versus `backend_start` se nikla hai, jisme `~1.5 s` interpreter startup ka hai |

**Deliberately open (owner ke saath):**

- **Lease ki duration** — `D-22`, Din 6. Aaj number nahi chuna, aur ye sahi hai. Par item 3 ke wajah se
  Din 2 pe ek **working** number chunna padega; wo `D-22` nahi hai, wo Din 2 ka input hai.
- **Contract #2 unprotected hai** — Week 3 ke dedup tak. Ye iss hafte ka accepted trade hai, gap nahi.
- **`ADD COLUMN` fast-path ka number** — Option B ne `DEFAULT` use nahi kiya, to KEY ka `now()`-as-default
  sawaal iss path pe uthta hi nahi. Agar Option A kabhi revisit hui, `\timing` ke saath measure karna.

**Slipped (aur specifically kya chahiye):**

| Item | Kaunsi baar | Kya chahiye |
|---|---|---|
| **Step 0 ke paanch likhe hue answers** | **paanchwi** | Paanchon apne shabdon me, iss log ki Din 1 entry me. Chaar ka content report me hai par execution ke baad aaya (`E8` — reconstruction). **Paanchwa — *"lease handler se chhoti ho to kya galat hota hai"* — bilkul nahi aaya**, aur wo Din 3 ka centrepiece hai. Ye ek hi item hai jo Din 3 ko technically block karta hai |
| **Part B ke chhe prediction answers** | pehli | Likhit roop me, measurement se pehle. Aaj ke liye ab reconstruct **nahi** ho sakte — seal khul chuki hai. Din 2 ke chhe sawaal `WEEK_02.md` ke PART B block me hain; unhe **kal subah, kaam shuru karne se pehle** likhna hai |
| **Ch 8 links append** | pehli | `DDIA_CH8_LINKS.md` me kam se kam **do naye** one-line links, *Network Faults in Practice* aur *Detecting Faults* se, har ek ka right-hand side ek **existing** named `D-`/`P-`. Note: file me line 2 aur 3 already `pp. 278–284` aur `281–283` cite karti hain — wo Stage Day pe likhi gayi thi, to aaj ka reading un lines se **aage** jaana chahiye, unhe dohrana nahi |
| **Commit** | pehli | Staged paths naam se: `src/models.py`, `src/worker.py`, `alembic/versions/75a845575d2e_*.py`, `alembic/versions/79cb2ee38481_*.py`, `docs/logs/WEEK_02.md`, `docs/PROBLEMS.md`. `docs/planning/`, `docs/roadmap/`, `docs/daily/` gitignored hain |

**Carried forward, unchanged:**

- **Din 7 ki log entry maujood nahi hai.** Aaj ke bench ne BENCH block ke **numbers** verify kar diye, to
  provenance wala aadha band ho gaya. Par Din 7 me kya chala aur kya verdict nikla — wo kahin likha nahi
  hai aur reconstruct nahi hoga. `WEEK_01.md` me ye ek line ki tarah rehna chahiye.
- **`LEARNING_LOG.md` ka open-items table** — Din 7 debt ke liye row abhi bhi nahi bani.

---

### ❓ Question / Next Thought

**Kal ka asli sawaal, aur ye Din 2 ka experiment define karta hai:** predicate `claimed_at` pe likha
jaayega, aur `claimed_at` ek **event** hai — to predicate me ek duration term aayega jo aaj tak kisi
evidence se nahi aaya. To Din 2 pe do cheezein ek saath hongi: ek **measurement** (predicate ne 41/63/65/75
pe kya kiya) aur ek **choice** (duration kitni). Aur `P-12` ka pura sabaq yahi hai ki ek run me do
variable rakhne se pata nahi chalta ki result kis ka tha.

Isliye kal ka sawaal ye hai: **agar predicate ne 41/63/65 ko utha liya, to wo mere predicate ke sahi hone
ka evidence hai, ya meri chuni hui duration ke uss row ke age se chhoti hone ka?** Dono ek hi output dete
hain. Farq nikalne ka ek hi tareeka hai — duration ko **pehle** likhna, uske reason ke saath, aur phir
chalana. Reverse order me wo number "jo kaam kar gaya" ban jaayega, aur Din 6 pe `D-22` uske upar khadi
nahi ki ja sakti.

**Aur ek chhota sawaal jo aaj ka output khud utha raha hai:** teeno fixture rows pe `claimed_at` `NULL`
hai, to `IS NULL` branch unhe reclaim karegi. Par wo branch ye nahi jaanti ki row **kab** atki. Yaani
41/63/65 ke liye reaper ke paas duration ka koi input hi nahi hai — wo unhe reclaim karega kyunki wo
`NULL` hain, na ki kyunki wo expired hain. **Kal wo teen rows expiry ki wajah se reclaim nahi hongi;
`NULL` ki wajah se hongi.** Ye do bilkul alag reasons hain aur reaper ka output dono me same dikhega.

---

## Din 2 — Reaper: recovery bahar se aati hai (`2026-08-25`)

> **Date, aur ek gap jo record karna zaroori hai.** Din 1 ki entry `2026-08-23` hai. `src/reaper.py` ka
> mtime `2026-08-25 15:41:32 IST` hai `[MEASURED-R]`, to Din 2 `2026-08-25` hai. **`2026-08-24` ka koi
> record nahi hai** — na log, na file mtime. Ye plausible kahani se band nahi hota: **cause not
> identified.** Ye Week 1 ke Din 7 gap ka doosra instance hai, aur ab ye ek pattern hai.

**Original goal (from the plan):** ek **alag process** me ek reaper loop banana jo `running` → `pending`
ek statement me kare — compare-and-set guard purani value pe, predicate `WHERE` me (Python `if` me nahi),
aur `rowcount` check har pass pe. Predicate **pehle likha jaaye, phir chalaya jaaye**. Chaar rows
(41/63/65/75) pe **per-row verdict**, `3 reclaimed` wali ek line nahi. Reclaim se **pehle** ka fixture
state verbatim log me. Ek reclaim latency number. `attempts` aaj touch nahi hota, `DECISIONS.md` me aaj
kuch nahi jaata.

**Goal met? — `partial`.**

| Hua | Nahi hua |
|---|---|
| Reaper ek alag process me bana (`src/reaper.py`), `worker.py` ke andar nahi | **Part B ke chhe answers** — dusre din lagataar supply nahi hue, to `0/6` scorable |
| Predicate, lease duration aur poll interval **pehle** likhe gaye, "chosen ahead of measurement" label ke saath | **Step 4 ka three-query split** (a/b/c) aur uska chaar-row verdict table — supply nahi hua, **aur ab reproduce nahi ho sakta**: fixture ja chuki hai |
| Pre-reclaim state **verbatim** — aaj ka sabse valuable output, aur ye ek hi baar liya ja sakta tha | **Step 6** — guard ka differential. Chala hi nahi, aur iss implementation se **chal bhi nahi sakta** (`P-20`) |
| Reclaim actually hua: 41/63/65 `pending`, `claimed_at NULL`; 75 `failed` untouched `[MEASURED-R]` | **Step 7** — reclaim latency. Koi number supply nahi hua |
| `attempts` kisi row pe touch nahi hua — `D-23`/Din 4 ka scope respect hua `[MEASURED-R]` | **Step 8** — Ch 8 links. `DDIA_CH8_LINKS.md` ka mtime abhi bhi `2026-08-22 17:28` (Stage Day ka) `[MEASURED-R]`. **Doosri consecutive slip** |
| Reconciliation match karta hai, total badla nahi, `job_executions` delta `0` | **Cleanup** — reaper band nahi hua. Doosri consecutive cleanup failure |

**Anything else learned?** Haan, chaar cheezein jo plan ne poochhi nahi thi:

1. **Din 1 ka *"do worker process"* galat tha — wo ek worker tha.** Aaj ke process tree ne wo band kar
   diya, aur ye Din 1 ka open item #2 hai.
2. **Reaper ka per-row output apna verdict padhta nahi, assert karta hai** — `post_status` sirf `matched`
   ka doosra roop hai. `P-20`.
3. **Ek khaali pass **kuch bhi** print nahi karta**, to Step 6 ka differential iss shape me satisfy hi
   nahi ho sakta — aur ek zinda-par-idle reaper ko ek mare hue reaper se alag karne wali ek hi cheez hai:
   `echo=True`, jo ek debug flag hai.
4. **Clock offset pehli baar poora measure hua** — `5:29:59.994671`, `7.262 ms` read gap ke saath. Din 1 ka
   open item #6 band.

---

### 📊 Measured / Observed

**Opening check (`P-13`, `P-06`) plus aaj ka extra: 41/63/65 aur 75 abhi bhi wahi hain?**

| Kya | Value | Label |
|---|---|---|
| worker processes / `idle in transaction` / connections | Din 1 ke do leftover PIDs band kiye gaye (PIDs report me naam se **nahi** aaye — *not recorded*). Uske baad: `1` active connection, `0` `idle in transaction` | `[MEASURED]` |
| jobs 41 / 63 / 65 ka `status` | teeno `running`, `claimed_at NULL` | `[MEASURED]` |
| job 75 ka `status` | `failed` | `[MEASURED]` |
| counts | `75 succeeded / 9 failed / 3 running / 0 pending`, total `87`, `max(id) 88` | `[MEASURED]` |
| `job_executions` | `58` | `[MEASURED]` |
| job 88 | `succeeded`, `claimed_at` non-null | `[MEASURED]` |

**Din 1 ke close se zero divergence.** E2 aaj trigger nahi hua.

**Pre-reclaim state — reaper chalane se PEHLE ka verbatim output.** Ye reclaim ke baad **wapas nahi aa
sakta**, isliye pehle yahan (`Etc/UTC`):

```
-- jobs (41, 63, 65 running with claimed_at NULL, 75 failed):
--  id | status  | claimed_at | created_at                    | attempts
    41 | running | NULL       | 2026-08-17 13:57:24.155331+00 | 0
    63 | running | NULL       | 2026-08-18 13:55:22.845247+00 | 0
    65 | running | NULL       | 2026-08-18 14:10:18.301994+00 | 0
    75 | failed  | NULL       | 2026-08-19 12:51:56.711211+00 | 0

-- job_executions:
    63 | worker-18960 | 2026-08-18 13:55:25.538209+00
    65 | worker-24152 | 2026-08-18 14:10:28.184853+00
-- 41 has NO row in job_executions.
```

**`select now()`** Step 2 me maanga gaya tha aur report me **nahi** aaya — *not recorded*. Iska asar: aaj ke
`now()` ke against un rows ki age exactly nahi likhi ja sakti, sirf `created_at` se derive hoti hai.

**Aur ye dump khud ek cheez saabit kar deta hai jo baaki poore din se nahi hui:** chaaron rows me
`claimed_at` `NULL` hai, matlab database me ek bhi `running` row aisi nahi thi jiska `claimed_at` non-null
ho. **To expiry branch (`claimed_at < now() - interval '30 seconds'`) zero rows pe match karta, aur wo aaj
exercise hua hi nahi** `[INFERRED from Step 2 verbatim]`. Reclaim `IS NULL` branch se hua — legacy-data
branch se, na ki uss branch se jiske liye reaper exist karta hai.

**M1 — post-reclaim state, reviewer ne verify kiya** `[MEASURED-R]` (`2026-08-25 10:53:00+00`):

```
 id |  status   |          claimed_at           |          created_at           | attempts
 41 | pending   |                               | 2026-08-17 13:57:24.155331+00 |        0
 63 | pending   |                               | 2026-08-18 13:55:22.845247+00 |        0
 65 | pending   |                               | 2026-08-18 14:10:18.301994+00 |        0
 75 | failed    |                               | 2026-08-19 12:51:56.711211+00 |        0
 88 | succeeded | 2026-08-23 09:46:55.549422+00 | 2026-08-23 09:45:21.84424+00  |        0

 status    | count            job_executions = 58   (delta 0)
 failed    |     9            total = 87, max(id) = 88, jobs_id_seq.last_value = 88
 pending   |     3
 succeeded |    75
```

Chaar cheezein isme confirm hoti hain: **41 actually move hui** (`pending` + `claimed_at NULL`), **75
untouched hai**, **`attempts` kahin touch nahi hua**, aur **`job_executions` ka delta `0` hai** — matlab
reclaim ke waqt koi worker nahi chal raha tha.

**M2 — reaper ka predicate, compiled SQL, source comment se nahi** `[MEASURED-R]`:

```sql
SELECT jobs.id, jobs.status, jobs.claimed_at FROM jobs
 WHERE jobs.status = 'running'
   AND (jobs.claimed_at IS NULL OR jobs.claimed_at < now() - interval '30 seconds')
 ORDER BY jobs.id
```

`func.now() - text("interval '30 seconds'")` **theek render hota hai**. Ye check karne layak tha kyunki
SQLAlchemy me `text()` ko arithmetic me daalna silently galat parenthesisation de sakta tha; nahi diya.

**M3 — `now()` ek transaction ke andar freeze hai (Part B Q4 ka mechanism, measured)** `[MEASURED-R]`:

```
first  now()=2026-08-25 10:55:08.738597+00   clock_timestamp()=2026-08-25 10:55:08.750751+00
second now()=2026-08-25 10:55:08.738597+00   clock_timestamp()=2026-08-25 10:55:10.260537+00
now() identical: True     clock_timestamp advanced: 0:00:01.509786
```

`reap_stuck_jobs()` `SELECT` aur **saare** per-row `UPDATE` ek hi `session.begin()` me rakhta hai. To
selecting `now()` aur rechecking `now()` **ek hi instant** hain — expiry branch pe guard ka time term pass
ke andar hil hi nahi sakta, aur jo rows pass ke **dauran** expire hoti hain wo agle pass tak nahi uthti.
Bias **under**-reclaim ki taraf hai, jo aaj safe direction hai — **luck, design nahi.**

**M4 — clock offset, pehli baar ek jagah dono clocks padh ke** `[MEASURED-R]`:

```
python datetime.now()  (naive, local) before = 2026-08-25 16:25:10.266437
db     clock_timestamp() (tz-aware, UTC)     = 2026-08-25 10:55:10.271766+00
python datetime.now()  (naive, local) after  = 2026-08-25 16:25:10.273699
local - db_utc = 5:29:59.994671        (read gap = 0:00:00.007262)
```

Din 1 ne ek clock do baar padha tha aur usse offset nahi nikalta. Aaj offset `+5:30:00` measure hua,
`~5 ms` ke andar, aur ye **compute nahi kiya gaya** ("IST = UTC+5:30" maan ke) — wahi maanna hi test tha.
Din 1 ka open item #6 **band**.

**M5 — poll cadence aur pass duration** `[MEASURED-R]`, reaper 7 s chalaya gaya (0 `running` rows):

```
BEGIN 16:26:12.548 -> COMMIT 16:26:12.560     pass ≈ 12 ms
BEGIN 16:26:14.568                            interval 2.020 s
BEGIN 16:26:16.581                            interval 2.013 s
```

Read-only imitation, teen pass: `12.06 / 9.78 / 11.65 ms` (aur isme `echo=True` ka logging overhead shaamil
hai, jo Week 1 pe `2.3 ms` measure hua tha). **Sleep kaam ke *baad* hai, to period `poll_interval + pass
duration` hai, fixed `2.0 s` cadence nahi.** Aaj `~20 ms` ka farq hai, par yahi shape load pe drift banata
hai.

**M6 — khaali pass silent hai, aur ye Step 6 ko marta hai** `[MEASURED-R]`. 7 second, 3 pass, 25 lines:

```
[reaper-30276] Starting reaper process (PID: 30276, poll=2.0s, lease=30s)...
... 24 lines of SQLAlchemy echo ...
```

**Zero `[reaper-...]` per-row lines.** `SELECT` candidates ko pehle filter karta hai, to `pending` row
guard tak pahunchti hi nahi — wo print hi nahi hoti. Matlab Step 6 ka expected output ek **khaali** output
hai, aur khaali output ek mara hua reaper, ek truncated capture, aur ek theek se guarded reaper — teeno
deta hai. `P-18`, aur poora `P-20`.

**M7 — Din 1 ka *"do worker process"* ek worker tha** `[MEASURED-R]`. Aaj ke leftover reaper pe wahi
pattern mila aur process tree ne usko resolve kar diya:

| PID | ParentProcessId | Threads | WorkingSet | CommandLine |
|---|---|---|---|---|
| `33540` | `44460` | 1 | 3.9 MB | `python.exe -u -m src.reaper` |
| `33584` | **`33540`** | 2 | 56.9 MB | `python.exe -u -m src.reaper` |

`33584` ka parent `33540` hai; parent 1-thread/3.9 MB ka stub hai, child 2-thread/56.9 MB ka asli
interpreter. Aur `pg_stat_activity` me **ek** asyncpg backend tha (PID `66`), jiska `state_change` har
`~2 s` pe aage badh raha tha. **Do OS PID = ek Python interpreter = ek DB connection.** Din 1 ke log me
likha *"do worker processes zinda the"* isliye **galat** tha — wo ek worker tha, aur `P-13` ka instance
ab bhi asli hai, sirf uska count ek hai. Din 1 ka open item #2 **band**; launcher-stub ka exact mechanism
`[INFERRED]` hai (venv `python.exe` re-exec), aur process tree `[MEASURED-R]`.

**Aaj ye numbers likhne hain (plan ka Din 2 obligation):**

| Kya | Value / text | Label |
|---|---|---|
| Likha hua predicate, **as-written** (traps padhne se pehle wala) | `status = 'running' AND (claimed_at IS NULL OR claimed_at < now() - interval '30 seconds')` — compiled SQL isse match karta hai `[MEASURED-R]` | — |
| Chuni hui **lease duration** + reason | `30 seconds`. Reason: *"8 s slow handler ko headroom de"*. Label jo user ne khud lagaya: **"chosen on Din 2, ahead of measurement"** | `[NO EVIDENCE]` for the value being *right* |
| Chuna hua **poll interval** + reason | `2.0 s`. Reason: *"detection latency ko 2 s pe bound karta hai bina DB thrash kiye"*. Measured cadence `2.013–2.020 s` | choice `[NO EVIDENCE]`, cadence `[MEASURED-R]` |
| Per-row verdict — job **41** | Reclaimed. Matched **`IS NULL` branch**, expiry branch se nahi. Reclaim **muft** tha: `job_executions` me row nahi thi, to side effect possible hi nahi tha | `[MEASURED-R]` (outcome) · `[INFERRED]` (branch, Step 2 dump se) |
| Per-row verdict — job **63** | Reclaimed, `IS NULL` branch. **Duplicate risk: haan** — `job_executions` row `2026-08-18 13:55:25.538209+00`, `worker-18960`. Handler arbitrary code chala tha aur kitna chala ye Relay bata nahi sakta | `[MEASURED-R]` / `[INFERRED]` |
| Per-row verdict — job **65** | Wahi shape. `job_executions` row `2026-08-18 14:10:28.184853+00`, `worker-24152`. **Duplicate risk: haan** | `[MEASURED-R]` / `[INFERRED]` |
| Per-row verdict — job **75** | **Not matched, untouched, `failed`.** Correct outcome | `[MEASURED-R]` |
| Ek hi output me chaar rows ka farq dikha? | **Nahi.** Reaper ka stdout iss review ko supply nahi hua, aur uss shape me ho bhi nahi sakta tha: 75 kabhi candidate nahi thi, to reaper usko print hi nahi karta. 75 ka *not-matched* verdict sirf ek alag `select` se aata hai — reaper ke output se nahi (`P-20`) | `[MEASURED-R]` for the structural limit |
| **Expiry branch kitni rows pe match kiya** | **0, aur wo branch aaj exercise hua hi nahi.** Database me ek bhi `running` row nahi thi jiska `claimed_at` non-null ho | `[INFERRED from Step 2 verbatim]` |
| Reclaim latency | **Supply nahi hui.** Aur jo quantity plan maang raha tha (*expiry → `pending`*) wo aaj **undefined** thi, `0` nahi: teeno rows kabhi expire hui hi nahi, `IS NULL` pe matched. Jo measurable tha — reaper-start → row `pending` — wo record nahi hua | `[NO EVIDENCE]` |
| Compare-and-set guard ka affected-row-count | Per-row `rowcount` code me padha jaata hai aur print hota hai — shape maujood. Par **koi run output supply nahi hua**, aur guard **exercise nahi hua**: single reaper, koi worker nahi, to `SELECT` aur `UPDATE` ke beech koi window bani hi nahi. **Present aur untested** | `[MEASURED-R]` (code) · `[NO EVIDENCE]` (behaviour) |
| Din 5 ke liye notice hui baat (`status` akela guard kaafi nahi rehta) | Reclaim ke baad `running → pending → running` reachable ho gaya. Worker A ka mark `WHERE id = :id AND status = 'running'` **do** situations me match karta hai: uska apna `running`, aur worker B ka `running`. Guard sirf **value** poochhta hai, *kis ka* value nahi — to worker A wo kaam `succeeded` mark kar sakta hai jo worker B abhi kar raha hai. Compare-and-set ek recurring value pe generations distinguish nahi kar sakta. Structural jawab fencing token hai — **Din 5, aaj sirf likha** | `[INFERRED]` |
| Kaunsa number **measure** kiya aur kaunsa **choose** kiya | **Choose:** lease `30 s`, poll `2.0 s`. **Measure:** poll cadence `2.013–2.020 s`, pass duration `~10–12 ms`, clock offset `5:29:59.994671`, `now()` freeze. **Neither:** reclaim latency — na choose, na measure. Aur lease duration ke saath aaj **koi** measurement attached nahi hai | — |

**Agar reaper ne fixture row strand ki, ya terminal row sweep kar li (E4):** **dono nahi hue.** 41/63/65
teeno reclaim hui, 75 untouched rahi. Predicate ne `job_executions` pe key **nahi** kiya, `claimed_at` pe
kiya — aur `D-21`/`P-16` ka trap isliye nahi laga. Ye credit predicate ko jaata hai, run ko nahi: KEY dono
directions pehle se naam se likh chuki thi.

**Closing reconciliation** — opening counts **Din 1 ke log se** (BENCH block se nahi, wo Din 1 ka opening
tha):

| Line | Value |
|---|---|
| opening counts (Din 1 log) — `pending`/`running`/`succeeded`/`failed`/total | `0 / 3 / 75 / 9 / 87` |
| `+` aaj enqueue hui probe jobs (ids naam se) | **koi nahi.** Aaj ek bhi row insert nahi hui |
| `±` reclaim se `running` → `pending` shift | `−3 running`, `+3 pending` — ids **41, 63, 65** |
| `=` closing counts | `3 / 0 / 75 / 9 / 87` |
| `psql` ke actual counts | `pending 3`, `running 0`, `succeeded 75`, `failed 9`, total `87`, `max(id) 88`, seq `88` `[MEASURED-R]` |
| Match? | **Haan.** `3 + 0 + 75 + 9 = 87`, total badla nahi — reclaim buckets ke beech move karta hai, banata ya mitata kuch nahi |
| `job_executions` delta | `58 → 58`, **`+0`** `[MEASURED-R]`. Consistent with worker-off — koi handler dispatch nahi hua |
| Job 75 abhi bhi `failed` aur count me hai? | **Haan**, `failed 9` me ginti hai `[MEASURED-R]` |

Match na kare to finding (E5), pehla suspect `P-13`: **chain judti hai — par `P-13` aaj phir hua, aur ek
naye roop me.** Din 1 pe leftover **worker** tha; aaj leftover **reaper** hai (niche cleanup). Dono baar
arithmetic ne usko pakda **nahi**, aur dono baar wajah ek hi thi: jo process chhoot gaya usne kuch move
nahi kiya. Aaj reaper ke paas move karne ko kuch nahi tha kyunki `running` count `0` ho gayi thi. **Ye
detection nahi hai, ye khaali queue hai** — aur agar Din 3 ki ek seeded `running` row iss reaper ke chalte
hue bani hoti, wo turant reclaim ho jaati aur Din 3 ka number kisi ka nahi hota.

**Cleanup — ye hissa fail hua, lagataar doosre din:**

| Kya | Status |
|---|---|
| Reaper ka stdout capture delete hua? | *Not recorded.* Repo me koi capture file nahi mili `[MEASURED-R]`. Report me per-row **format** likha tha, actual lines **nahi** — to jo output copy hona chahiye tha wo copy hua hi nahi |
| Reaper band hua? | **Nahi.** `2026-08-25 16:25 IST` pe do PIDs zinda the — `33540` (stub) aur `33584` (interpreter), dono `python -u -m src.reaper`, dono `StartTime 15:51:43 IST`, matlab **~33 minute** se chal rahe the `[MEASURED-R]` |
| Live DB backend? | Haan, ek — backend PID `66`, `application_name` khaali (asyncpg), `state = idle`, `xact_start NULL`, `wait_event = ClientRead`, aur `state_change` har `~2 s` pe aage badh raha tha `[MEASURED-R]` |
| Locks pakde the? | **Nahi.** `state = idle` + `xact_start NULL` = koi lock, koi snapshot nahi. `P-06` ka mechanism **absent** hai; ye `P-13` hazard hai, `P-06` nahi |
| Reviewer ne kya kiya | `Stop-Process -Id 33584,33540`. Uske baad `Get-Process python` **khaali** `[MEASURED-R]` |
| Reclaim ki hui rows delete nahi hoti | **41, 63, 65** — teeno rakhi gayi hain, `pending` hain, delta me ginti hain. Ab ye **fixture nahi** hain: Din 3 apni stuck rows khud seed karega |
| Reviewer ke probes | Ek temporary file `labs/_probe_din2.py` bani, read-only chali, aur **delete ho gayi** `[MEASURED-R]`. Ek reaper 7 s chalaya gaya jab `running` count `0` thi — usne kisi row ko touch nahi kiya. Probe ke pehle aur baad ke counts identical: `9 failed / 3 pending / 75 succeeded / 87 total / 58 job_executions`. **Koi probe row nahi banayi, koi row delete nahi hui** |

**Commit:** Din 1 ka commit **ho gaya** — `6db1042 feat(worker): add claimed_at lease column and update claim
statement (Week 2 Din 1)` `[MEASURED-R]`. Din 2 ka **nahi** hua:

```
 M labs/day2_signals.py
?? src/reaper.py
```

`src/reaper.py` untracked hai. `labs/day2_signals.py` abhi bhi modified hai, mtime `2026-08-20 15:33` —
matlab wo Din 1 se **aage nahi badha** aur wo carried debt hai, aaj ka kaam nahi.

**`DECISIONS.md` me aaj kuch nahi jaata.** `D-22` Din 6 pe likhi jaayegi. Aaj ke numbers yahan `[MEASURED]`
tag ke saath baithe rehte hain taki Din 6 unhe utha sake. **Aur Din 6 ke liye ek line abhi likhna zaroori
hai:** lease duration `30 s` ke saath aaj **koi** measurement attached nahi hui, kyunki jis run ne predicate
ko validate karta dikha wo run poora `IS NULL` branch pe chala. `D-22` likhte waqt honest phrasing hai
*"chosen on Din 2, ahead of measurement, and the Din 2 run did not test it."*

---

### 🔧 Code review — `src/reaper.py`, aur yahan transition sahi hai par evidence nahi

Reaper ne jo **transition** maangi thi wo theek se banayi: alag process, `UPDATE` me compare-and-set guard
purani value pe, predicate `WHERE` me (Python `if` me nahi), `rowcount` har row pe padha, `attempts`
untouched. Ye teen-chaar cheezein aksar chhoot jaati hain aur nahi chhooti. **Jo galat hai wo transition
nahi, uske baare me nikalne wala evidence hai** — aur Din 2 ka poora deliverable wahi evidence tha.

| # | Kya | Label | Kyu ye matter karta hai |
|---|---|---|---|
| **R1** | `post_status = "pending" if matched == 1 else candidate.status` — row **dobara padhi nahi jaati** | `[MEASURED-R]` | `post_status` sirf `matched` ka restatement hai. Wo line wahi print karti hai jo code **maanta** hai. Fix ek clause hai, extra round trip nahi: `UPDATE ... RETURNING status`, phir wo value database se aayi hui hoti hai. Sabse zyada value dene wali ek-line correction hai |
| **R2** | Poora pass ek transaction me, to `now()` freeze | `[MEASURED-R]` (M3) | Expiry branch pe recheck kabhi select ke `now()` se disagree nahi kar sakta. Pass ke dauran expire hone wali rows next pass tak nahi uthti. Bias under-reclaim ki taraf — aaj safe, aur luck |
| **R3** | Khaali pass koi per-row line print nahi karta | `[MEASURED-R]` (M6) | Step 6 ka differential iss shape me satisfy hi nahi ho sakta. Aur idle-versus-dead reaper me farq karne wali ek hi cheez `echo=True` hai, jo `src/database.py` me ek **debug flag** hai. Off karo aur liveness evidence uske saath chala jaata hai. `P-20` |
| **R4** | `SELECT` filter guard se **pehle** hai | `[INFERRED]` | Deletion test: `AND status = 'running'` `UPDATE` se hataa do — aaj ka observable behaviour **same** hota, kyunki `SELECT` already filter kar chuka tha. Guard decorative **nahi** hai (wo `SELECT` aur `UPDATE` ke beech ki window pe hi lagta hai), par aaj wo window bani hi nahi. **Present aur untested** — verified likhna galat hoga |
| **R5** | `text(f"interval '{LEASE_DURATION_SECONDS} seconds'")` | `[MEASURED-R]` renders theek (M2) | Aaj `LEASE_DURATION_SECONDS` ek int constant hai, to injection surface nahi hai. Jis din wo env/config se aayi, ye ek raw-SQL interpolation ban jaayega. Parameterised shape `func.make_interval(secs=...)` hai. Aaj ye **pattern** ka note hai, bug nahi |
| **R6** | `SHUTDOWN_REQUESTED` sirf loop top pe check hota hai, `asyncio.sleep(2.0)` ke baad | `[MEASURED-R]` (M5 cadence) | `SIGTERM` ke baad exit up to `2.0 s` late. Ye `P-10` ka wahi shape hai — poll interval ek saath teen cheezein price karta hai, aur shutdown latency unme se ek hai |
| **R7** | `reap_stuck_jobs()` `reclaimed_count` return karta hai, `run_reaper()` usko discard karta hai | `[MEASURED-R]` | Dead code. Per-row output hi maanga gaya tha, to ye galat nahi — par ek total jo compute hota hai aur kahin nahi jaata baad me chup-chaap "3 reclaimed" ban jaata hai, aur `P-18` wahi line ban chuki hai |
| **R8** | stdout timestamp `datetime.now()` se — naive, local, **bina tz label** | `[MEASURED-R]` (M4) | Offset ab measured hai (`+5:30:00`), to arithmetic chal sakti hai. Par label ke bina ek lease bug aur ek timezone bug ek diff me **bilkul same** dikhte hain, aur Din 3 ka poora duplicate proof do stdout aur ek DB column ko ek clock pe laane pe khada hai |

**Ek line jo genuinely earned hai:** predicate `job_executions` pe key **nahi** kiya. KEY ne dono galat
directions (strand 41 / sweep 75) naam se likhi hui thi aur dono avoid hui.

---

### 💡 What I Understood

> ⚠️ **Ye section reviewer ne likha hai, user ne nahi.** Isme wo hai jo aaj ke session ne **establish**
> kiya — user ki samajh ka record nahi. Ise **apne shabdon me replace karna hai**, aur jo cheez sirf
> padhke aayi uske saath likhna hai ki wo padhi hui hai. Jab tak replace nahi hota, ye entry apni sabse
> zaroori field pe `[NO EVIDENCE]` carry karti hai.

**1. Reclaim ho gaya, aur reclaim ne wo branch test nahi kiya jiske liye reaper banaya gaya hai.** Teen
rows `pending` ho gayi — aur teeno `claimed_at IS NULL` pe matched, kyunki database me ek bhi `running` row
non-null `claimed_at` ke saath nahi thi. Matlab `30 seconds` ki jagah `10 seconds` ya `10 hours` likhne se
**bilkul wahi teen lines** aati. Predicate ke do branches **do alag sawaal** poochhte hain — ek *"kya ye
claim lease se aage nikal gaya"* (elapsed time), doosra *"iss claim ke baare me koi information hai hi
nahi"* (missing data) — aur reaper dono ko "reclaim this" maanta hai. Aaj sirf doosra chala. Log me likhne
wali line: **"expiry branch matched 0 rows and was not exercised today."**

**2. Ek loop jo sahi kaam karta hai aur galat report karta hai, ek loop hai jise audit nahi kiya ja
sakta.** `post_status` padha nahi gaya, khaali pass silent hai, aur 75 kabhi print hi nahi hui kyunki wo
candidate nahi thi. Teeno ek hi structural baat ke roop hain: **jo `SELECT` bahar kar deta hai, wo per-row
report se bhi bahar ho jaata hai.** Isliye "chaar rows ek output me" iss shape me possible hi nahi thi —
aur ye implementation ka choice tha, effort ka nahi.

**3. `now()` transaction-start hai, aur ye measure ho gaya, maana nahi gaya.** Ek transaction me do
`select now()` **identical** aaye jabki `clock_timestamp()` `1.51 s` aage badha. Iska seedha asar: pass ke
andar guard ka time term hil nahi sakta, aur reaper conservative ho jaata hai. Aaj wo safe direction hai —
par wahi mechanism khatarnak ho jaata hai jis din transaction ka use ye decide karne me hoga ki kuch
**abhi expire nahi hua**.

**4. Do PID ka matlab do process nahi hota.** Din 1 ne *"do worker"* likha tha; aaj process tree ne dikhaya
ki parent ek 1-thread stub hai aur asli interpreter uska child hai, aur DB connection **ek** thi. Ek
count ko interpret karne se pehle ye poochhna padta hai ki wo count **kis cheez** ka hai — `P-12` ka rule,
OS process table pe.

**5. Clean reconciliation ne dobara ek hygiene failure chhupa liya, aur ab ye pattern hai.** Din 1 pe
leftover worker, aaj leftover reaper — dono baar arithmetic match kar gaya, dono baar isliye ki chhoote
hue process ke paas move karne ko kuch nahi tha. Reconciliation `P-13` ko **detect nahi kar sakti**; uske
liye process check chahiye, aur wo closing pe dono din chala nahi.

---

### 🧠 Self-Check (honest — 0 / 6 self-answered on Part B, aur ye score data ke absence ka hai, galat jawab ka nahi)

**Part B ke chhe sawaalon ka koi likha hua pre-measurement answer iss review ko supply nahi hua** — Din 1
ke baad **doosra** consecutive din. Report me choices aur outputs the, predictions nahi. Reviewer rule 1
aur 6: jo answer nahi hua usko correct me count nahi karna, aur jo field report nahi hui uska plausible
value nahi bharna. Honest score **0/6 scorable** — matlab "chhe galat" nahi, matlab "chhe ka evidence
nahi".

**Aur ye ab pehle din se mehnga hai.** Din 1 ka `0/6` ek missing baseline tha. Din 2 ka `0/6` iska matlab
hai ki hafte ke do din ke measurements ke saath comparison ke liye **koi** prediction base nahi hai — aur
`DIN_02_KEY.md` khud yahi line apni pehli scoring note me likh chuki hai: *"that is the single most
expensive thing that can go wrong this week, and it costs 10 minutes to prevent."*

Per-question status, taki gap naam se dikhe:

| Part B Q | Kya poochha gaya | Status | KEY ab kholi ja sakti hai? |
|---|---|---|---|
| 1 | 41 ka reclaim aur 63 ka — ek hi cheez? Farq `status` me ya evidence me? | **not supplied.** Step 2 ka dump farq **dikhata** hai (41 ka koi `job_executions` row nahi, 63/65 ka hai), par wo observation likha gaya, prediction nahi | **Haan** — Step 2 ka measurement chala |
| 2 | `job_executions` pe join wala predicate → 41 ka kya, aur stranded row output me kaisi dikhti? | **not supplied.** Aur Step 4 chala hi nahi, to iska measurement **kabhi nahi hoga** — fixture ja chuki hai | **Explanation ki tarah**, recall ki tarah nahi. Ye din ke liye permanently unscoreable |
| 3 | Ulta rule (*"execution row nahi hai to reset"*) 75 pe kya karta, aur kitni der me pakda jaata? | **not supplied.** Wahi baat — Step 4 ka read-only probe nahi chala | Same as Q2 |
| 4 | Lambi reaper transaction — `now()` kis waqt ka, expiry kis clock ke against? | **not supplied**, aur ye woh sawaal hai jiska mechanism aaj **measure** ho gaya (M3) | **Haan** — M3 chala |
| 5 | Pehla worker zinda — mark kab `rowcount 0` deta, aur kab `1` jabki kaam doosra worker kar raha hai? | **not supplied.** Ye Din 5 ka direct input hai aur uska text obligation table me reviewer ne bhara hai — matlab wo baat *establish* hui, *answered* nahi | **Haan** — Step 3/5 chale |
| 6 | Reclaim latency — duration se, poll interval se, ya dono se? Kya measure kiya, kya choose kiya? | **not supplied**, aur latency ka number bhi nahi. Ye ek hi sawaal hai jiska **dono** hissa gayab hai | Step 7 chala nahi — **sealed rehna chahiye** |

**Seal status (`E8`):** koi seal-break report nahi hui. Par Q2/Q3/Q6 ke liye ye ab academic hai — un steps
ka measurement chala hi nahi, to unka prediction data iss din ke liye khatam hai chahe KEY khuli ho ya na
khuli. **`idk` likhna teeno se behtar hota.**

**Corrections — jo maine kaha aur jo measurement/review ne refute kiya:**

| # | I said | Actual | The transferable lesson |
|---|---|---|---|
| 1 | *"day 2 complete"* | **Partial.** Step 4 (three-query split + verdict table), Step 6 (guard differential), Step 7 (latency), Step 8 (Ch 8 links — `DDIA_CH8_LINKS.md` mtime abhi bhi `2026-08-22 17:28`), Part B ke chhe answers, cleanup, aur commit — saat items missing `[MEASURED-R]` | Ye Din 1 ki correction #1 ka **exact repeat** hai, ek din baad. "Complete" ka matlab **file state aur process state check karna** hai. Do din, ek hi galti, aur doosri baar wo pehle se named thi |
| 2 | Per-row output format `[REAPER] [ts] id={id} pre_status={} matched={} post_status={}` — jaise ye chaar rows ka verdict de raha hai | Format theek hai; **content nahi.** `post_status` row se padha nahi jaata, wo `matched` ka restatement hai `[MEASURED-R]`. Aur **75 kabhi print hi nahi hoti** kyunki wo `SELECT` ka candidate nahi hai — to "chaar rows ek output me" iss shape me possible nahi thi | Ek output format design karte waqt sawaal ye nahi hai *"kaunse fields print karun"*, sawaal ye hai *"inme se kaunsa field database se aaya aur kaunsa main assert kar raha hoon"*. Assert kiya hua field verification me zero weight rakhta hai |
| 3 | Lease `30 s` chuna — *"8 s slow handler ko headroom de"* — aur reclaim ne teen rows uthaayi, matlab predicate kaam kar gaya | Predicate ka **`IS NULL` branch** kaam kar gaya. Expiry branch **zero rows** pe chala, kyunki ek bhi `running` row non-null `claimed_at` ke saath nahi thi `[INFERRED from your own Step 2 dump]`. `30 s` ki jagah kuch bhi likha hota, wahi teen lines aati | Ek run jo pass karta hai, **kaunsa** mechanism validate karta hai — ye alag se poochhna padta hai. Teen reclaim dikhne se predicate confirm nahi hota; sirf wo branch confirm hota hai jo actually evaluate hua |
| 4 | Step 6 — reaper do baar chalaya (do PIDs zinda mile, dono `src.reaper`) | Do PID **ek** process hain: `33584` ka parent `33540`, parent 1-thread/3.9 MB stub, ek asyncpg backend `[MEASURED-R]`. To do concurrent reaper nahi chale (scope violation nahi hua — accha), par Step 6 ka differential **produce bhi nahi hua**, aur wo iss implementation se ho hi nahi sakta: doosra run khaali output deta hai (`P-20`) | Aur ye Din 1 ki *"do worker"* claim ko bhi correct karta hai — wo bhi ek worker tha. OS process count aur "kitne mere program chal rahe hain" do alag numbers hain |
| 5 | Step 0 — *"1 active connection, 0 idle in transaction"*, clean baseline | Sach hai, **aur adhoora**: Din 1 ke leftover PIDs kya the ye record nahi hua (*not recorded*), aur closing pe process check dobara chala hi nahi — isliye `~33 minute` chalta hua reaper mila `[MEASURED-R]` | Opening pe process check karna aur closing pe **na** karna — dono din ki wahi galti. `idle in transaction = 0` (jo `P-06` dekhta hai) aur `processes = 0` (jo `P-13` dekhta hai) do alag checks hain, aur doosra dono baar closing pe skip hua |

*(Ye table kabhi delete nahi hoti, na chhoti hoti hai.)*

---

### 🚧 Unresolved / Follow-ups

**New, from today:**

| # | Item | Kya specifically chahiye |
|---|---|---|
| 1 | **`post_status` padha nahi jaata (R1, `P-20`)** | `UPDATE ... RETURNING status` pe move karo, aur us value ko print karo. Ek clause, koi extra round trip nahi. **Din 3 se pehle**, kyunki Din 3 ka duplicate proof reaper ki reclaim line pe khada hai |
| 2 | **Khaali pass silent hai (R3, `P-20`)** | Per-pass ek line chahiye jisme candidate count ho — `0` bhi print ho. Iske bina Step 6 ka differential kabhi nahi chalega, aur Din 3 me *"reaper uss window me chala tha?"* (diagnosis #3) ka jawab nahi milega |
| 3 | **Expiry branch aaj tak kisi row pe evaluate nahi hua** | Din 3 iska pehla asli test hai: ek live-but-slow worker ki lease actually expire hogi. Aaj tak jo evidence hai wo poora `IS NULL` branch ka hai |
| 4 | **Reclaim latency ka koi number nahi hai** | Plan-defined quantity (*expiry → `pending`*) aaj **undefined** thi. Din 3 ka prereq table isko naam se maangta hai — to Din 3 ke pehle ye decide karna hai: Din 3 apna number khud banayega (uske paas expire hone wali lease hai), aur Din 2 ka slot `[NO EVIDENCE]` rehta hai. **Yaad se plausible number bharna nahi hai** |
| 5 | **Reaper poll period `poll_interval + pass_duration` hai, fixed `2.0 s` nahi** | Aaj `~20 ms` ka farq hai `[MEASURED-R]`. Din 3 me jab window seconds me nap rahi ho, ye drift ek line ka note maangta hai — measure karke, maan ke nahi |
| 6 | **`echo=True` production shape nahi hai** | Aaj wo accidentally liveness evidence de raha hai (R3). Off karne ka faisla apne aap me ek decision hai (Week 4, metrics ke saath) — par jab off ho, tab reaper ka apna per-pass line **pehle** exist karna chahiye |

**Deliberately open (owner ke saath):**

- **Lease duration ka final number** — `D-22`, Din 6. Aaj `30 s` ek **working number** hai, `D-22` nahi.
  Aur aaj ka run usko test **nahi** karta — ye line `D-22` me jaani chahiye.
- **Fencing token** — Din 5 ka reading, aur uska argument aaj likha gaya (obligation table ki aakhri
  rows). Aaj banana nahi hai.
- **Contract #2 unprotected** — Week 3 ke dedup tak. Accepted trade, gap nahi.
- **Do reaper / leader election** — Week 4. Aaj scope violation hua **nahi** (do PID ek process the).

**Slipped (aur specifically kya chahiye):**

| Item | Kaunsi baar | Kya chahiye |
|---|---|---|
| **Part B ke chhe prediction answers** | **doosri** | Likhit roop me, measurement se **pehle**. Din 2 ke liye ab reconstruct nahi ho sakte. Din 3 ke sawaal `WEEK_02.md` ke PART B block, `## Din 3` me hain — wo **kal subah, kaam shuru karne se pehle** likhne hain, `idk` include |
| **Ch 8 links append** | **doosri** | `DDIA_CH8_LINKS.md` me ab **chaar** lines owed hain: Din 1 ke do (*Network Faults in Practice*, *Detecting Faults*) aur Din 2 ke do (*Timeouts and Unbounded Delays*, aur unme se **ek `P-02` pe** jaani chahiye). File ki lines 2 aur 3 already `pp. 278–284` aur `281–283` cite karti hain — nayi lines unse **aage** jaani chahiye |
| **Step 4 — three-query split aur chaar-row verdict table** | pehli, aur **permanent** | Ye ab **poora nahi ho sakta**. 41/63/65 `pending` hain, to (a)/(b)/(c) teeno khaali aate hain `[MEASURED-R]`. Jo bacha hai wo Step 2 ka verbatim dump hai — aur wo isliye bacha hai ki wo liya gaya tha. **Yahi iss discipline ka poora proof hai** |
| **Step 6 — guard ka differential** | pehli | Pehle R1 aur R3 fix karo, phir ye check meaningful ban jaayega. Aaj ise "pass" likhna decorative hoga (`E7`) |
| **Step 7 — reclaim latency** | pehli | Din 3 pe, apni expire hone wali lease ke saath. Aaj ka slot `[NO EVIDENCE]` rehta hai |
| **Cleanup — reaper band karna** | **doosri** (Din 1 pe worker) | Closing pe `Get-Process python` chalao, output log me. Opening pe chalana aur closing pe nahi chalana — dono din ki wahi galti |
| **Commit** | **pehli for Din 2** | Staged paths naam se: `src/reaper.py`, `docs/logs/WEEK_02.md`, `docs/PROBLEMS.md`. `labs/day2_signals.py` **alag** commit ya revert — wo Din 1 ka carried debt hai aur uska mtime `2026-08-20` hai |

**Carried forward, unchanged:**

- **`2026-08-24` ka koi record nahi.** Din 1 `08-23`, Din 2 `08-25`. **Cause not identified.** Week 1 Din 7
  gap ka doosra instance — ab ye ek pattern hai aur Din 6 ke week-close pe iska naam jaana chahiye.
- **Din 7 (Week 1) ki log entry maujood nahi hai.** Numbers verify ho chuke hain; kya chala wo nahi.
- **`labs/day2_signals.py` modified** — mtime `2026-08-20 15:33`, Din 1 se aage nahi badha.
- **`79cb2ee38481` — khaali migration revision** chain me permanent hai. Theek nahi karna; naam log me hai.
- **`LEARNING_LOG.md` ka open-items table** — Din 7 debt ke liye row abhi bhi nahi bani.
- ~~`CURRENT_WEEK.md` abhi bhi Week 1 pe point karta hai~~ — **reviewer ki galti, aur wo yahan rehti hai.**
  File kholke measure kiya: wo Din 1 pe hi Week 2 pe repoint ho chuki thi, week status table ke saath
  `[MEASURED-R]`. Ye claim Stage Day register ki ek stale line se copy hui thi, aur wahi galti hai jo iss
  poore log me manaa hai — **ek doosre document ki line ko measurement ki tarah padhna.** Din 2 ke close pe
  file Din 3 pe repoint kar di gayi.
- **Do process / ek backend ka sawaal — BAND.** M7 ne resolve kiya: parent stub + child interpreter.

---

### ❓ Question / Next Thought

**Kal ka asli sawaal, aur ye Din 3 ke paanch-sawaal diagnosis ka pehla dandaa hai:** aaj reaper ne teen
rows uthaayi aur uska output usme se **ek bhi** cheez prove nahi karta jo Din 3 ko chahiye. Din 3 ka pura
duplicate proof teen timestamps ke ek clock pe aane pe khada hai — reaper ki reclaim line, worker A ka
handler end, worker B ka `executed_at` — aur aaj measure hua ki reaper ki line ka timestamp **naive local**
hai bina label ke, uska post-state **assert kiya hua** hai, aur ek khaali pass **kuch print nahi karta**.

To kal se pehle ka sawaal ye hai: **agar Din 3 ka duplicate count `0` aaya, to main kaise batao ki overlap
window bani hi nahi thi, versus reaper uss window me chala hi nahi tha?** Aaj ke output se ye do cases
**alag nahi** kiye ja sakte — dono me reaper ki koi line nahi hoti. Diagnosis #3 (*"reaper uss window me
chala?"*) ka jawab literally ek line hai jo abhi print hoti hi nahi. Isliye R1 aur R3 Din 3 ke **prereq**
hain, cosmetic nahi.

**Aur ek chhota sawaal jo aaj ka reclaim khud utha raha hai:** 41, 63 aur 65 ab `pending` hain aur teeno
claimable hain. 41 ka reclaim muft tha; 63 aur 65 ka nahi — unke `job_executions` rows batate hain ki
handler code chala tha. Ab jo bhi worker inhe uthayega, wo 63 aur 65 ka handler **doosri baar** chalayega,
aur `jobs` me aisi koi cheez nahi hai jo usko ye bata sake. **Din 2 ne duplicate execution ka darwaza
khol diya hai aur wo darwaza abhi khula hua hai** — teen rows queue me baithi hain, aur unme se do pe
side effect dobara ho sakta hai. Ye Week 2 ka honest guarantee ka literal roop hai: reaper ne stranded
work ka window **narrow** kiya, aur duplicate ka window **band nahi** kiya.

---

## Din 3 — 🎯 Zinda par slow worker: ek job, do execution (`2026-08-26`)

> **Date chain, aur ek gap band ho gaya.** Din 2 `2026-08-25`, Din 3 `2026-08-26` — lagatar din, aur
> commit `f43388c` ka timestamp `2026-08-26 20:35:42 +0530` isko confirm karta hai `[MEASURED-R]`.
> Week 1 Din 7 aur `2026-08-24` ke do gaps **abhi bhi khule hain** aur wo carried hain, par aaj ka din
> khud us pattern me nahi hai.

**Original goal (from the plan):** ek **zinda** worker jiska handler lease se lamba chale, uski lease
expire ho, reaper usko reclaim kare, doosra worker wahi job dobara claim kare — aur ye **overlap** proved
ho, sirf `count(*) > 1` se nahi. Uske **baad** heartbeat, taki wo jo narrow karta hai wo size ho sake.
Do run, ek hi variable ka farq. Paanch-sawaal ka diagnosis count se **pehle**. Aur Din 2 ke do udhaar:
reaper ka readable output, aur pehla asli reclaim-latency number.

**Goal met? — `yes`, aur ye hafte ka pehla din hai jispe ye likha ja sakta hai.**

| Hua | Nahi hua / adhoora |
|---|---|
| **Centrepiece bana, aur overlap proved hua** — job 95, do distinct `worker_id`, do dispatch instants, aur B ka dispatch A ke handler interval ke **andar** `[MEASURED-R]` | **Step 9 chala hi nahi** — heartbeat guard ka inverted-order differential report me nahi hai. Reviewer ne aaj chalaya (M8) |
| **Worker A ka mark `rowcount = 1` diya jabki B kaam kar raha tha** — Q3 ki *dangerous* branch, aur wo narrow branch hai. Ye din ka sabse mehnga output hai aur wo capture hua | **Step 2 ka reclaim latency number galat quantity measure karta hai** — `19.953818 s` reaper ke **start hone** ka number hai, lease + poll ka nahi. Reviewer ne dobara measure kiya: `1.798192 s` (M6) |
| **Step 1 ka reporting fix ship hua** — `RETURNING Job.status, clock_timestamp()`, aur khaali pass pe `candidates=0 reclaimed=0` wali line. `P-20` ke dono aadhe band | **`super_slow` handler kisi bhi commit me maujood nahi hai** — `git log --all -S"super_slow"` khaali `[MEASURED-R]`. Hafte ka centrepiece HEAD se reproduce **nahi** ho sakta (`P-23`) |
| **Step 0 ka drain hua aur uska before/after pair liya gaya** — 63 aur 65 ko doosri `job_executions` row mili, do alag `worker_id` ke saath. Din 2 ka darwaza executing dikha | **Closing reconciliation me aath naye ids me se sirf teen naam se likhe gaye** — 89, 90, 92, 93, 94 unnamed, aur unme do `super_slow` hain, matlab do centrepiece attempts jinka outcome record nahi hua (M9) |
| **Run 2 me heartbeat ne lease ko zinda rakha** — 4 heartbeats, reaper `candidates=0`, ek hi execution row | **Cleanup teesri baar fail hua, aur is baar sach me do process the** — `~4h 55m` zinda, do asyncpg backends. Report me *"Active background processes: 0"* likha tha (M1) |
| **Part B ke chhe jawab pehli baar supply hue**, aur paanch sahi hain (niche self-check) | **`DDIA_CH8_LINKS.md` aaj tak append nahi hui thi** — reading hui, links file me nahi gaye. Reviewer ne aaj likhe; udhaar chaar se chhe line ka ho gaya tha |

**Anything else learned?** Haan, chaar cheezein jo plan ne poochhi nahi thi:

1. **Overlap ko prove karne ke liye clock conversion zaroori nahi hai.** Dono dispatch instants DB clock
   me hain; unka gap `30.243370 s` hai, aur A ka handler `45.026 s` chala. Overlap = `14.783 s` —
   **ek hi clock, zero conversion**. Aur wo stdout se nikale `14.785 s` se `2 ms` ke andar hai, jo khud
   Din 2 ke measured offset ka independent verification ban jaata hai (M5).
2. **Run 2 ka expiry-se-completion gap `0` nahi hai, `undefined` hai.** Lease expire hui hi nahi, to
   "expiry" naam ka koi instant maujood nahi. `0` likhna Din 2 ke `0`-reclaim-latency wali fabrication ka
   dobara roop hota.
3. **`count(*) > 1` ke ab teen mechanism hain, do nahi** — aur teesra Week 1 se table me baitha hai:
   job 44 pe do rows, **same** `worker_id` (`worker-12940`), `6m54s` ke gap pe, `2026-08-17` `[MEASURED-R]`.
4. **Reaper ka compiled `UPDATE` ek column return karta hai jo code ne maanga hi nahi** — `RETURNING
   jobs.id, jobs.status, clock_timestamp()`, jabki `.returning()` me do cheezein hain (M7).

---

### 📊 Measured / Observed

**Opening check (`P-13`, `P-06`), plus aaj ka extra:**

| Kya | Value | Label |
|---|---|---|
| worker processes / `idle in transaction` / connections | **Opening pe report nahi hua** — *not recorded*. Din 2 ka leftover reaper reviewer ne band kiya tha, to opening clean hona chahiye tha | `[NO EVIDENCE]` |
| 41/63/65 ki current state (Din 2 ke baad) | teeno `pending`, `claimed_at NULL` — Din 2 ke close se zero divergence | `[MEASURED]` |
| job 75 abhi bhi `failed`? | **Haan**, `failed`, `claimed_at NULL`, `attempts 0`. Aaj bhi untouched | `[MEASURED-R]` |
| Aaj ki seeded stuck rows ke ids | **id 91** (Step 2 ka seed, `type='sleep'`, hand-`UPDATE` se `running` + `claimed_at = now() - 25s`) | `[MEASURED]` |
| Pre-drain `job_executions` | `58` — Din 2 ke close se match | `[MEASURED]` |
| Pre-drain `job_executions` for 41/63/65 | **do rows** (63 → `worker-18960`, 65 → `worker-24152`, dono Aug 18), **41 ki koi row nahi** | `[MEASURED]` |

**Step 0 — drain, aur uska before/after pair.** Faisla *drain* liya gaya. Post-drain `job_executions` `61`
(`+3`), aur teen ids ka shape aaj `[MEASURED-R]`:

```
 job_id |  worker_id   |          executed_at          
     41 | worker-35640 | 2026-08-26 09:38:43.870431+00   <- 41 ki PEHLI execution row
     63 | worker-18960 | 2026-08-18 13:55:25.538209+00
     63 | worker-35640 | 2026-08-26 09:38:47.073941+00   <- DOOSRI, alag worker
     65 | worker-24152 | 2026-08-18 14:10:28.184853+00
     65 | worker-35640 | 2026-08-26 09:38:55.413770+00   <- DOOSRI, alag worker
```

Aur teeno ka `attempts` abhi bhi `0` hai `[MEASURED-R]`. **Do baar chali hui job ka database me koi
record nahi hai** — sirf `job_executions` me do rows. Ye Din 4 ka poora argument hai, aaj measure hua.

**Paanch-sawaal ka diagnosis — Run 1 (job 95), isi fixed order me, aur count iske BAAD (E3, `P-12`, `P-18`):**

| # | Sawaal | Jawab | Label |
|---|---|---|---|
| 1 | Do distinct `worker_id`, overlapping `executed_at`? | **Haan.** `worker-19804` @ `10:28:27.762549+00`, `worker-54112` @ `10:28:58.005919+00`. B ka dispatch A ke handler interval ke **andar** hai — overlap `14.783 s` | `[MEASURED-R]` |
| 2 | Lease expiry versus handler duration — **ek hi clock** me | **Haan.** Handler `45.026 s` (A ke stdout se), lease `30 s`. Expiry `≤ 10:28:57.762549+00` (A ke `executed_at` se upper-bounded, kyunki A ka `claimed_at` B ne overwrite kar diya). Completion `10:29:12.804329+00`. **Gap `≥ 15.041780 s`** | `[MEASURED-R]` |
| 3 | Reaper uss window me actually chala? | **Haan** — aur ye sawaal iss saal pehli baar *answerable* hai, kyunki Step 1 ne per-pass line add ki. B ka claim `10:28:57.969647+00`, expiry ke `≤ 207.098 ms` baad. Ye khud reaper ke ek pass ke andar hone ka proof hai | `[MEASURED-R]` (DB timestamps se) · reaper capture `[NO EVIDENCE]` (file delete ho gayi) |
| 4 | Row uss waqt claimable thi? | **Haan** — B ne usko `pending` se claim kiya, `rowcount 1`, aur `claimed_at` `10:28:57.969647+00` pe likha | `[MEASURED-R]` |
| 5 | Log poora hai (`python -u`, aakhri line adhoori nahi)? | **User ke hisaab se haan** — teen `python -u` captures. Reviewer verify **nahi** kar saka: teeno files delete ho gayi thi aur `Claimed job` ka grep count report me nahi tha | `[NO EVIDENCE]` |

**Duplicate count — sirf paanchon jawab likhne ke BAAD:**

| Run | Duplicate count | Overlap window proven? | Label |
|---|---|---|---|
| Run 1 — heartbeat **ke bina** (job 95) | **2 execution rows** | **Haan** — overlap `14.783 s`, ek hi clock me derive kiya | `[MEASURED-R]` |
| Run 2 — heartbeat **ke saath** (job 96) | **1 execution row** | **Window bani hi nahi** — lease kabhi expire nahi hui | `[MEASURED-R]` |

**Zero ka matlab.** Run 2 me overlap `0` hai kyunki **overlap window khuli hi nahi**, isliye nahi ki system
safe hai. Jis sawaal pe "nahi" mila: **sawaal 2 — lease expire hui hi nahi.** Heartbeat ne har `10 s` pe
`claimed_at` aage badhaya, to `claimed_at < now() - interval '30 seconds'` kabhi sach nahi hua. Job 96 ka
`claimed_at` closing pe `10:44:56.088549+00` hai jabki uska dispatch `10:44:15.793133+00` tha — yaani
`claimed_at` dispatch ke **40.3 s baad** ka hai, aur wo chautha heartbeat hai `[MEASURED-R]`.
**Sawaal 3 ka jawab "haan" hai, "nahi" nahi** — reaper chala aur uske `candidates=0` wale per-pass lines
usko prove karte hain; usko "nahi" likhna Step 1 ki poori kamai wapas de dena hai (niche correction #1).
· Agle run me badalne wala **ek** variable: **koi nahi.** Handler duration, lease aur poll interval Din 4
pe frozen hain (plan ka scope guard), aur heartbeat interval bhi.

**M1 — cleanup teesri baar fail hua, aur is baar do genuine process the** `[MEASURED-R]`
(`2026-08-26 15:09 UTC` pe padha gaya, yaani run ke `~4h 55m` baad):

| PID | ParentProcessId | Threads | WorkingSet | StartTime (IST) | CommandLine |
|---|---|---|---|---|---|
| `54544` | `32252` | 2 | 17.7 MB | `16:14:13` | `python.exe -u -m src.worker` |
| `42264` | `43768` | 2 | 22.8 MB | `16:14:23` | `python.exe -u -m src.worker` |

**Din 2 ka `M7` pattern aaj lagu nahi hota** — dono ke parents ek doosre nahi hain, dono 2-thread hain, aur
`pg_stat_activity` me **do** asyncpg backends the (`1686` @ `10:44:15.622588+00`, `1689` @
`10:44:25.805670+00`), dono ka `state_change` padhne ke instant pe aage badh raha tha. Yaani Din 3 ke do
worker **sach me do process** the — jo experiment ke liye zaroori tha — aur **dono kabhi band nahi hue.**
`worker-54544` wahi hai jo job 96 chalaya tha, matlab Run 2 ka worker A `~5 ghante` poll karta raha.

Ek aur session bhi mili: backend `37`, `application_name = psql`, `backend_start 2026-08-25 09:55:12+00` —
**ek din purani**. `xact_start NULL`, to koi lock nahi (`P-06` ka mechanism absent, `P-13` ka hazard
maujood).

Reviewer ne `Stop-Process -Id 54544,42264` chalaya; uske baad `python.exe` ki koi row nahi
`[MEASURED-R]`. **Aur aaj wo luck nahi tha:** reviewer ka apna probe ek `pending` row banata hai, aur ye
dono worker `pending` rows uthate hain. Agar pehle band na kiye hote to M6 aur M8 ka number kisi ka nahi
hota.

**M2 — Step 1 ka reporting fix, compiled SQL ke saath** `[MEASURED-R]`:

```
UPDATE jobs SET status=$1::VARCHAR, claimed_at=$2::TIMESTAMP WITH TIME ZONE
 WHERE jobs.id = $3::BIGINT AND jobs.status = $4::VARCHAR
   AND (jobs.claimed_at IS NULL OR jobs.claimed_at < now() - interval '30 seconds')
 RETURNING jobs.id, jobs.status, clock_timestamp() AS clock_timestamp_1
```

Aur khaali pass ab bolta hai:

```
[reaper-43620] [2026-08-26 21:11:54.223374] Pass completed: candidates=0 reclaimed=0
```

`P-20` ke dono aadhe band: `post_status` ab database se aata hai, aur ek zinda-par-idle reaper ek mare hue
reaper se stdout me alag dikhta hai. **Aur ye fix aaj hi kaam aaya** — M6 ka latency number isi
`clock_timestamp()` se nikla hai, aur "reaper chala tha?" ka jawab in `candidates=0` lines se aata hai.

**M3 — Run 1 (job 95) ki poori timeline, dono clock label ke saath.** DB rows `[MEASURED-R]`, stdout
`[MEASURED]` (user ke captures se, files delete ho chuki hain):

```
DB   (Etc/UTC)   10:28:19.460983   job 95 enqueued (type='super_slow')
IST  (stdout)    15:58:27.773      worker A: [SLOW HANDLER] Work started
DB   (Etc/UTC)   10:28:27.762549   job 95 executed_at  <- worker-19804 ka dispatch
DB   (derived)   10:28:57.762549   lease expiry, UPPER BOUND (A ka claimed_at overwrite ho gaya)
DB   (Etc/UTC)   10:28:57.969647   job 95 claimed_at   <- worker-54112 ka claim, expiry ke <=207.098 ms baad
IST  (stdout)    15:58:58.014      worker B: [SLOW HANDLER] Work started
IST  (stdout)    15:59:12.799      worker A: Work completed  -> DB 10:29:12.804329
IST  (stdout)    15:59:43.022      worker B: Work completed  -> DB 10:29:43.027329
```

**M4 — worker A ka mark statement, aur ye Q3 ki dangerous branch hai** `[MEASURED]`:

```
[worker-19804] Marked job 95 as 'succeeded' (rowcount=1).      <- B ka handler ABHI chal raha tha
[worker-54112] Conflict on mark: Job 95 status was modified by another transaction (rowcount=0).
```

Guard ne kuch galat nahi kiya. Usne poochha *"kya value `'running'` hai"* — aur wo `'running'` **worker B
ka** tha. Do me se ye **narrow** branch thi (A ko B ke claim ke baad khatam hona tha, `≤` ek worker poll),
aur wahi mili. Doosri branch (`rowcount = 0`) aaj bhi possible thi.

**M5 — overlap, do independent derivations, aur unka `2 ms` ka farq** `[MEASURED-R]`:

| Derivation | Arithmetic | Overlap | Conversions |
|---|---|---|---|
| stdout only (IST − IST) | `15:59:12.799 − 15:58:58.014` | `14.785 s` | 0, par dono naive local |
| DB dispatch gap only | A ka handler `45.026 s` − dispatch gap `30.243370 s` | **`14.783 s`** | **0**, poora `Etc/UTC` |

Dispatch gap DB me `10:28:58.005919 − 10:28:27.762549 = 30.243370 s` hai. Do raste `2 ms` ke andar milte
hain, aur wo Din 2 ke measured offset (`5:29:59.994671`) ka independent check ban jaata hai. **Doosri
derivation ko preferred maanna chahiye** kyunki usme ek bhi clock cross nahi hota — aur DIN\_03\_KEY ka
poora Step 1 argument yahi tha ki teen-term subtraction me har conversion `5:30:00` galat hone ka mauka hai.

**M6 — reclaim latency, dobara measure hui, kyunki Step 2 ka number galat quantity ka tha**
`[MEASURED-R]`. Reviewer ne reaper **pehle** start kiya, phir ek row `29 s` age pe seed ki (probe job 97),
aur sab kuch DB clock me padha:

```
seed   claimed_at  = 2026-08-26T15:41:24.448822+00:00
seed   seeded_at   = 2026-08-26T15:41:53.456971+00:00   (clock_timestamp, seed ke instant)
       expires_at  = 2026-08-26T15:41:54.448822+00:00   (claimed_at + 30 s)
reaper [DB_TIME: 2026-08-26T15:41:56.247014+00:00] id=97 pre_status=running matched=1 post_status=pending
       RECLAIM LATENCY = 1.798192 s
```

Aur reaper ka apna cadence, usi capture se: pass `21:11:50.192` → `52.208` → `54.223` → *(reclaim pass
`56.24`)* → `58.268` IST, yaani `2.016 / 2.015 / ~2.02 s`. Din 2 ke `2.013–2.020 s` se consistent.

**Sabse kaam ki line:** `21:11:54.223` ka pass `candidates=0` bola — wo expiry se `226 ms` **pehle** chala
aur theek se kuch match nahi kiya. Agla pass usko utha liya. Yaani latency **ek reaper period se bandhi
hai**, jaisa KEY ka floor/jitter model kehta tha: `expiry` floor set karta hai, `poll` uske upar jitter.

**Aur Run 1 se ek doosra, independent reading:** expiry `≤ 10:28:57.762549`, B ka claim
`10:28:57.969647` → expiry-se-claim **`≤ 207.098 ms`**, aur usme reaper ka reclaim **aur** B ka poll dono
shaamil hain. Do alag readings, dono ek poll period ke andar. **`19.953818 s` inse ek order of magnitude
door hai, aur uska cause procedural hai** — Step 2 me reaper row seed hone ke **baad** start hua, to wo
number *"main reaper kab chalaya"* measure karta hai. `P-22` isi ka entry hai.

**M7 — reaper ka compiled `UPDATE` ek extra column return karta hai** `[MEASURED-R]`. Code
`.returning(Job.status, func.clock_timestamp())` maangta hai; SQL me `RETURNING jobs.id, jobs.status,
clock_timestamp()` jaata hai — SQLAlchemy ORM-enabled `UPDATE` pe primary key khud jodta hai. **Indexing
phir bhi sahi hai** aur ye behaviour se proved hai: `returned_row[0]` ne `pending` print kiya (id `97`
nahi), aur `returned_row[1].isoformat()` chala (str pe wo `AttributeError` deta). To `Row` sirf do
requested columns expose karta hai.

**Ye bug nahi hai, ye ek shape ka note hai:** positional index (`[0]`, `[1]`) uss column list pe khada hai
jo code me likhi hai, aur compiled SQL me ek teesri column hai. `RETURNING` me kuch add/reorder hua to ye
**silently** galat column padhega — koi exception nahi, sirf ek galat `post_status`. Named access
(`returned_row.status`) isko structural bana deta hai. Aaj badalna zaroori nahi; likhna zaroori hai.

**M8 — Step 9, jo chala nahi tha. Reviewer ne chalaya: heartbeat ka guard asli guard hai** `[MEASURED-R]`.
Order jaan-boojh ke ulta kiya — pehle reaper ne probe job 97 ko `pending` kar diya, phir `worker.py` ka
**wahi** heartbeat `UPDATE` uss row pe chalaya gaya:

```
STEP9  heartbeat rowcount on released row = 0
STEP9  final row = (97, 'pending', None, 0)
```

**`rowcount = 0`.** Guard ne reject kiya, `claimed_at` `NULL` hi raha, ek released lease resurrect nahi
hui. **`PROBLEMS.md` me iski entry nahi jaati** — expected behaviour mila.

**Par ye check jo prove karta hai wo utna hi important hai jitna jo nahi karta.** Guard `status = 'running'`
poochhta hai. Aaj row `pending` thi, to reject hui. **Agar worker B ne usko dobara claim kar liya hota, to
row `running` hoti aur A ka heartbeat `rowcount = 1` deta** — purana worker naye worker ki lease renew
karta. **Wo case aaj produce nahi hua aur khula hai.** Ye M4 ka bilkul wahi generation problem hai, aur
jawab bhi wahi hai: fencing token, **Din 5**.

**M9 — closing reconciliation me aath naye ids me se paanch unnamed hain** `[MEASURED-R]`. Aaj `jobs` me
`+8` rows aayi (ids `89`–`96`), report me **teen** naam se hain (`91`, `95`, `96`). Poora set:

| id | type | Reported role | `job_executions` rows |
|---|---|---|---|
| 89 | `sleep` | **unnamed** | 1 (`worker-46552` @ `10:17:07.319852`) |
| 90 | `sleep` | **unnamed** | 1 (`worker-46552` @ `10:17:09.806310`) |
| 91 | `sleep` | Step 2 ka seed | 1 (`worker-46552` @ `10:17:11.907722`) |
| 92 | `sleep` | **unnamed** | 1 (`worker-46552` @ `10:17:14.120816`) |
| 93 | `super_slow` | **unnamed** | 1 (`worker-46552` @ `10:17:16.250014`) |
| 94 | `super_slow` | **unnamed** | 1 (`worker-17376` @ `10:19:49.072654`) |
| 95 | `super_slow` | Run 1 — centrepiece | **2** |
| 96 | `super_slow` | Run 2 — heartbeat | 1 |

**Do unnamed rows `super_slow` hain, aur wo centrepiece attempts hain.** `[INFERRED from DB timestamps]`
93 shayad Step 4 ka `is_expired` check hai (ek worker, koi reaper nahi, ek execution row). 94 ka shape
zyada interesting hai: `super_slow`, ek dispatch, **koi duplicate nahi** — yaani ek attempt jisme overlap
**bana hi nahi**. Wo KEY ka *"do execution, koi overlap nahi"* outcome ya ek adhoora attempt ho sakta hai,
aur **wahi cheez Step 3 pe wapas jaane ka evidence hai**. Uska outcome kahin likha nahi gaya.

`job_executions` ka arithmetic phir bhi judta hai (`58 + 3 drain + 5 @10:17 + 1 @10:19 + 2 Run 1 + 1
Run 2 = 70`), par **attribution adhoori hai** — aur plan ka rule *"ids naam se"* isi liye hai. `E5` nahi
laga; ye us se ek layer halka hai: chain judi, kahani adhoori.

**Aaj ye likhna hai (plan ka Din 3 obligation):**

| Kya | Value / text | Label |
|---|---|---|
| Chuna hua handler duration, apne reason ke saath | **`45 s`** (`super_slow`), Option A — handler lamba, lease `30 s` untouched. Reason: `30 s` ko intact rakhna, taki aaj ka duplicate count `30 s` ke **baare me** evidence bane (`D-22` ki `Cost` line ko wahi chahiye), aur ek `5 s` lease duplicate ko trivially aasan bana deti jo kam sikhati | — |
| Dono run ka expiry-se-completion gap | Run 1: **`≥ 15.041780 s`** (expiry upper-bounded, ek hi clock). Run 2: **`undefined` — `0` nahi.** Lease expire hui hi nahi, to "expiry" naam ka instant maujood nahi. Ye Din 2 ke undefined reclaim-latency ka wahi shape hai | `[MEASURED-R]` |
| Heartbeat ke teen faisle — interval | `HEARTBEAT_INTERVAL_SECONDS = 10.0` — lease ka `1/3`. Run 1 me 4 heartbeats bheje gaye ek `45 s` handler pe | `[MEASURED]` |
| Heartbeat ke teen faisle — guard | `where(Job.id == job_id, Job.status == "running")` + `rowcount == 0` pe `break` aur ek `Heartbeat lost` line | `[MEASURED-R from source]` |
| Heartbeat ke teen faisle — sender (kaun bhejta hai) | Handler ke saath ek `asyncio.create_task`, `stop_event` se rukta hai, `finally` me `stop_event.set()` phir `await heartbeat_task` — matlab shutdown pe task orphan nahi hota | `[MEASURED-R from source]` |
| Teeno ki cost | **Interval:** har `10 s` pe ek extra `UPDATE` per running job, aur wo reaper ke poll ke upar aata hai; effective margin `lease − interval − scheduling delay` hai, `lease − interval` nahi. **Guard:** ek `rowcount` check jo har heartbeat pe padhna padta hai, aur wo *released* lease se bachata hai par *re-claimed* lease se nahi (M8). **Sender:** poora mechanism handler ke `await` karne pe khada hai — `handle_slow`/`super_slow` `asyncio.sleep` hain, to yield karte hain; ek CPU-bound ya blocking handler pe heartbeat **bhejа hi nahi jaata** aur Relay handler ko bound nahi karta (`P-15`, `P-21`) | — |
| Pehle worker ke mark statement ka **verbatim** output | M4 — `Marked job 95 as 'succeeded' (rowcount=1).` jabki worker B ka handler chal raha tha | `[MEASURED]` |
| Heartbeat ne window **narrow** kiya — kitna, aur wo band kyun nahi hua | Run 1 ka gap `≥ 15.04 s`, Run 2 me gap **exist hi nahi karta** kyunki lease expire nahi hui. **Ye elimination nahi hai, ek schedule hai.** Wajah M8 aur `P-21` me hai: heartbeat sirf un handlers pe kaam karta hai jo event loop ko yield karte hain, aur uski effectiveness uss failure ki severity se **ulti** proportional hai jiske liye lease exist karti hai | `[MEASURED-R]` |
| `count(*) > 1` ka matlab badalna (`P-11`) — aaj ka evidence | Aaj table me `count(*) > 1` **chaar** job ids pe hai — `44, 63, 65, 95` — aur unke peeche **teen alag mechanism** hain: (i) **44** — ek hi `worker-12940` ne do baar dispatch kiya, `6m54s` ke gap pe, `2026-08-17`, Week 1 ka; (ii) **63, 65** — do alag worker, **ek hafte** ke gap pe, Din 2 ka reclaim executing; (iii) **95** — do alag worker, **overlapping**, aaj ka duplicate. **Sirf 95 pe "duplicate" ka lafz lagta hai** | `[MEASURED-R]` |

**Closing reconciliation** — opening counts **Din 2 ke log se**:

| Line | Value |
|---|---|
| opening counts (Din 2 log) — `pending`/`running`/`succeeded`/`failed`/total | `3 / 0 / 75 / 9 / 87` |
| `±` drain — 41, 63, 65 `pending → succeeded` | `−3 pending`, `+3 succeeded` |
| `+` aaj enqueue hui rows (ids naam se) | `89, 90, 91, 92, 93, 94, 95, 96` — **aath**, aur report me sirf `91/95/96` naam se aaye (M9) |
| `−` unme se jo terminal hui | **aathon** `succeeded` |
| `=` closing counts | `0 / 0 / 86 / 9 / 95` |
| `psql` ke actual counts (user ke close pe, reviewer ne verify kiya) | `succeeded 86`, `failed 9`, `pending 0`, `running 0`, total `95`, `max(id) 96`, seq `96` `[MEASURED-R]` |
| Match? | **Haan.** `86 + 9 = 95`. Sequence gap abhi bhi ek hi hai (id `79`, `P-05`) |
| `job_executions` delta — duplicate rows isme count hote hain | `58 → 70`, **`+12`**, jabki `jobs` ka delta `+8` hai. **Excess `+4`** aur wo naam se: `63` ka doosra, `65` ka doosra, `95` ka doosra, aur `41` ka pehla (jo `jobs` delta me nahi hai kyunki 41 nayi row nahi hai) `[MEASURED-R]` |
| **Reviewer probe ke baad ki state** | `+1` job (**id 97**, `type='sleep'`, closing pe **`pending`**), `job_executions` **badla nahi (`70`)** kyunki probe ne koi handler dispatch nahi kiya. Total `96`, `max(id) 97`, seq `97` `[MEASURED-R]` |

Match na kare to finding (E5). **`E5` aaj trigger nahi hua** — chain judi. Par M9 ke hisaab se
attribution adhoori hai, aur wo `E5` se halka par asli hai: paanch ids ka role likha nahi gaya.

**Cleanup:**

| Kya | Status |
|---|---|
| Teen stdout capture files (worker A, worker B, reaper) delete hui? | **Haan** (report ke hisaab se), aur repo me koi capture file nahi mili `[MEASURED-R]` |
| Andar ka relevant output pehle upar copy hua? | **Aadha.** Worker A/B ke handler lines aur mark lines copy hue (M3, M4). **Reaper ka capture copy nahi hua** — na reclaim line, na `candidates=0` lines, na `Claimed job` ka grep count. Yaani Step 1 ka jo output aaj banaya gaya tha, wo log tak nahi pahuncha |
| Worker / reaper / heartbeat band hue? | **Nahi.** Do worker `~4h 55m` zinda mile (M1). Reviewer ne band kiye |
| Closing pe process check dobara chala? | **Nahi** — report me *"Active background processes: 0"* likha tha aur measurement usko refute karta hai (correction #2) |
| Leftover DB sessions | Do asyncpg backends (`1686`, `1689`) live the; ek `psql` session `1` din purani (backend `37`), `xact_start NULL` to koi lock nahi. `idle in transaction = 0` `[MEASURED-R]` |
| Reviewer ke probes | Ek temporary file `labs/_probe_din3.py` aur ek capture `labs/_reaper_probe.log` bani, dono **delete ho gayi** `[MEASURED-R]`. Ek reaper `~30 min` chalaya gaya aur wo **band kar diya gaya**; closing pe `python.exe` ki zero rows |
| Probe rows delete nahi hoti, ids | **97** — reviewer ka probe row. Closing pe `pending`, `claimed_at NULL`, `attempts 0`. **Ye Din 4 ki subah pehli claimable row hogi** (`type='sleep'`, `created_at 15:41:53.408515+00`, to sabse purani `pending`) |
| Working tree | **Clean**, `f43388c` pushed `[MEASURED-R]`. Aur `labs/day2_signals.py` ka carried debt **band** — wo ab modified nahi hai (revert hua; `git log -- labs/day2_signals.py` me sirf `0b3dc54` hai) |

**`DECISIONS.md` me aaj kuch nahi.** `D-21` ka amendment aur `D-22` dono Din 6 pe. Aaj sirf evidence banta
hai — aur `D-22` ke liye ek line abhi likhni hai: **lease `30 s` ke saath ab do measurements attached hain**
— reclaim latency `1.798192 s` (ek poll period ke andar) aur ek duplicate window `≥ 15.04 s`. Din 6 pe
honest phrasing badal jaati hai: *"chosen on Din 2 ahead of measurement, and first measured on Din 3."*

---

### 💡 What I Understood

> ⚠️ **Ye section reviewer ne likha hai, user ne nahi.** Isme wo hai jo aaj ke session ne **establish**
> kiya — user ki samajh ka record nahi. Ise **apne shabdon me replace karna hai**. Jab tak replace nahi
> hota, ye entry apni sabse zaroori field pe `[NO EVIDENCE]` carry karti hai.

**1. Duplicate execution ek race nahi thi jise ek behtar guard theek kar deta.** Teen compare-and-set
chale — A ka claim, reaper ka reclaim, B ka claim — aur teeno apne instant pe **sahi** the. Phir bhi ek
job do baar chali, `14.783 s` ke overlap ke saath. Matlab jis din tumne *"expired kaam wapas reclaim
karo"* accept kiya, usi din tumne *"kaam do baar chal sakta hai"* accept kar liya, aur baaki sirf ye
sawaal bacha ki window kitni chaudi hai. Isliye Week 3 ka jawab **idempotency key** hai, ek stricter
guard nahi — guard writes ko mutually exclusive banata hai, wo ek chal rahe handler ko rok nahi sakta
(`P-02`).

**2. Aur usi mechanism ka doosra sira: guard poochhta hai "kya value `running` hai", kabhi nahi poochhta
"kis ka `running` hai".** Worker A ne `succeeded` mark kiya `rowcount = 1` ke saath, jabki worker B usi
job ko chala raha tha. Ye guard ka fail hona nahi hai; ye ek **recurring value** pe compare-and-set ka
structural limit hai — `running → pending → running` ek cycle ban gaya, aur cycle pe CAS generations
distinguish nahi kar sakta. Aur bilkul wahi limit heartbeat pe bhi lagta hai (M8): released lease pe
guard reject karta hai, **re-claimed** lease pe nahi. Ek hi sawaal, do jagah, ek hi jawab — fencing
token, Din 5.

**3. Heartbeat ki effectiveness uss failure ki severity se ulti proportional hai jiske liye lease exist
karti hai.** Aaj wo perfectly kaam kiya — kyunki handler `asyncio.sleep` tha, jo yield karta hai, jo
heartbeat task ko chalne deta hai. Yaani heartbeat ne **sabse aasan case** solve kiya: ek worker jo
theek hai aur sirf by-design slow hai. GC pause, blocking I/O, CPU-bound loop, network partition — inme
se ek bhi me heartbeat bhejа hi nahi jaata, aur yahi wo cases hain jinke liye lease banayi jaati hai.
Isliye Run 2 ka `0` **`narrows` hai, `closes` nahi** — aur ye politeness nahi, ye M8 aur `P-21` ka
literal content hai.

**4. Ek number tab bhi galat ho sakta hai jab uska arithmetic bilkul sahi ho.** Step 2 ka
`19.953818 s` — subtraction sahi, dono instants DB clock ke, dono verbatim. Aur wo phir bhi reclaim
latency nahi hai, kyunki reaper row seed hone ke **baad** start hua, to number *"main reaper kab
chalaya"* measure karta hai. Wahi quantity, reaper pehle chalu karke, `1.798192 s` nikalti hai — ek
poll period ke andar. **Measurement ka setup measurement ka hissa hai**, aur ek number ka label uska
formula nahi, uska **procedure** decide karta hai (`P-22`).

**5. Ek hi summary statistic ke peeche ab teen alag mechanism hain.** `count(*) > 1` aaj `44, 63, 65, 95`
pe sach hai: ek same-worker re-dispatch (Week 1), do week-apart re-executions (Din 2 ka reclaim), aur ek
asli overlapping duplicate (aaj). Chaar rows, ek jaisa number, teen alag kahaniyan — aur `attempts` chaaron
pe `0` hai, to database inme farq **nahi** kar sakta. Ye `P-11` ki expiry hoti hui dikh rahi hai, aur Din 4
ke `attempts` increment point ka poora argument yahi hai.

---

### 🧠 Self-Check (honest — **5 / 6 self-answered**, ek partial)

**Pehli baar iss hafte Part B ke jawab supply hue, aur wo teen din ka `0/6` ka silsila todte hain.** Din 1
`0/6`, Din 2 `0/6` — dono data ki **absence** ke liye. Aaj chhe likhe hue jawab aaye, unme mechanism tha
(sirf conclusion nahi), aur paanch sahi hain.

**Ek provenance caveat, aur ye score se alag hai.** Jawab mujhe **day close pe** mile, ek fenced file ki
tarah nahi. Iska matlab main *prediction* aur *reconstruction* me farq **nahi** kar sakta (`E8` ka wahi
sawaal). Score maine likhe hue content pe diya hai. Kal se: jawab jis file me likhe jaate hain wo file
naam se paste karo, taki score ke saath uska mtime bhi ho.

| Part B Q | Kya poochha gaya | Verdict | Detail |
|---|---|---|---|
| 1 | Duplicate — guard ka failure ya window ka? | ✅ **Correct** | *"Window fail hui, koi SQL guard fail nahi hua"*, teeno CAS ko naam se legit bataya, aur `P-02` pe land kiya. KEY ka jawab literally yahi hai, mechanism ke saath |
| 2 | `executed_at` ek instant hai — overlap prove karne me kya kami, aur kahan se poori hoti | ✅ **Correct** | Interval-versus-point ka farq theek pakda, `completed_at` ki gair-maujoodgi naam se, *"completion evidence is a print, not a row"*, aur missing aadha stdout se aata hai. `executed_at` ko dispatch instant bhi kaha — jo `record_execution()` ke apne transaction se aata hai |
| 3 | A ka mark — kab `rowcount 0`, kab `1` jabki B kaam kar raha hai | ✅ **Correct** | Dono branches, aur dono ka mechanism: `0` jab row `pending` thi (reclaim ke baad, B ke claim se pehle), `1` jab B ne usko wapas `running` kar diya. *"Guard sirf value poochhta hai, kis ka value nahi"* — ye line derived hai, recalled nahi lagti. **Aur aaj `rowcount = 1` wali narrow branch actually mili** |
| 4 | Heartbeat kahan **bilkul** madad nahi karta, aur `handle_slow` se kaise alag | ✅ **Correct** | Chaar cases naam se: CPU-bound (no yield), sync blocking I/O, process pauses (GC/paging/VM suspend), network partition. Aur `await asyncio.sleep` ke yield karne wala mechanism theek se `handle_slow` se distinguish kiya |
| 5 | `running → pending` ke baad `count(*) > 1` ke do causes | ✅ **Correct** | Reclaim → re-execution, aur retry-after-failure (Din 4). Aur khud se ye note bhi jodа ki *"count > 1 sirf tab duplicate hai jab overlap prove ho"* — wo KEY ki apni line hai aur wo maangi nahi gayi thi |
| 6 | Zero-duplicate run me paanch me se kaunse pe "nahi", aur setup ki kya baat pata chali | 🟡 **Partial** | **Mechanism poora sahi:** heartbeat ne `claimed_at` aage badhaya → `30 s` lease kabhi expire nahi hui → predicate ne match nahi kiya → window khuli hi nahi. **Assignment galat:** "nahi" **sawaal 2** pe hai (*lease expire hui?*), sawaal 3 pe nahi. Sawaal 3 hai *"reaper uss window me chala?"* — aur reaper **chala**, aur uski `candidates=0` lines usko prove karti hain. Wo line aaj Step 1 me banayi gayi thi **exactly** iss farq ko dikhane ke liye: ek idle reaper aur ek mara hua reaper ab alag dikhte hain. Jawab ne unhe wapas ek kar diya |

**`idk` aaj ek baar bhi nahi likha gaya, aur wo iss baar theek hai** — chhe me se paanch derive kiye hue
lagte hain, ek partial hai, aur koi jawab guess-dressed-as-knowledge jaisa nahi padha.

**Corrections — jo maine kaha aur jo measurement/review ne refute kiya:**

| # | I said | Actual | The transferable lesson |
|---|---|---|---|
| 1 | Q6: *"Run 2 me sawaal 3 (did the reaper run and reclaim inside that window?) par NO mila (0 candidates reclaimed)"* | Reaper **chala**, aur `candidates=0` uske chalne ka **positive** evidence hai, absence ka nahi. Jo sawaal "nahi" pe gira wo **sawaal 2** hai — lease expire hui hi nahi `[MEASURED-R]` | *"Reclaim kiya"* aur *"chala"* do alag sawaal hain, aur Step 1 ka poora kaam unhe alag karne ka tha. `candidates=0` ka matlab *"reaper zinda hai aur usko kaam nahi mila"* hai — jo Din 2 me stdout me **exist hi nahi karta tha**. Apni hi banayi hui distinction ko jawab me collapse kar dena us fix ki value wapas de dena hai |
| 2 | *"Active background processes: 0"* | **Do worker `~4h 55m` zinda the** — PIDs `54544`, `42264`, do 2-thread interpreters, **do** asyncpg backends (`1686`, `1689`) jinka `state_change` padhne ke instant pe aage badh raha tha `[MEASURED-R]`. Ek `psql` session bhi **ek din** purani thi | Teesra consecutive din. Aur is baar Din 2 ka bachaav bhi nahi hai: Din 2 me do PID ek interpreter the, aaj do PID **do** interpreter the. `Get-Process` closing pe chalta hai ya nahi — bas wahi ek line hai. Aur aaj wo `luck` nahi tha: reviewer ka probe ek `pending` row banata hai, jo ye dono uthaa lete |
| 3 | *"Step 2 Reclaim Latency ... Reclaim latency = `19.953818 s` `[MEASURED]`"* | Arithmetic sahi, quantity galat. Reaper row seed hone ke **baad** start hua, to number reaper ke start hone ka hai. Wahi quantity, reaper pehle chalu karke: **`1.798192 s`** `[MEASURED-R]`. Aur Run 1 se independent reading: expiry-se-claim **`≤ 207.098 ms`** | Ek measurement ka label uske formula se nahi, uske **procedure** se aata hai. *"Expiry → `pending`"* ka matlab ye maanta hai ki observer expiry se **pehle** already chal raha ho. Ye `19.95 s` `D-22` ki `Cost` line me chala jaata aur wahan `11x` galat hota (`P-22`) |
| 4 | Run 2 ka gap *"0.0s overlap"* ki tarah report kiya | **Overlap `0` sahi hai** (ek hi execution). Par **expiry-se-completion gap `undefined` hai, `0` nahi** — lease expire hui hi nahi, to "expiry" naam ka instant maujood nahi | Ye Din 2 ke undefined reclaim-latency ka **wahi** shape hai, ek din baad, ulti direction me. Ek quantity jiska ek term exist nahi karta, wo `0` nahi hoti — `0` ek measurement hai aur `undefined` ek absence. DoD dono run ka gap side-by-side maangta hai, aur wahan `0` likhna fabrication hoti |
| 5 | Commit `f43388c` *"day 3 ka code"* ki tarah — *"demonstrate slow worker duplicate execution"* | Commit me `super_slow` **kahin nahi hai.** `git log --all -S"super_slow"` khaali `[MEASURED-R]`, aur HEAD ka `REGISTRY` sirf `sleep/boom/slow` rakhta hai, `handle_slow` abhi bhi `8.0 s`. Jobs 95/96 database me `type='super_slow'` carry karti hain jiska koi handler repo me nahi | Hafte ka centrepiece **HEAD se reproduce nahi ho sakta** (`P-23`). Aur ek dormant hazard: aaj ek worker `super_slow` row claim kare to `REGISTRY.get()` `None` deta hai → `failed`, koi execution row nahi — job 75 ka **exact** shape, self-inflicted. Abhi harmless kyunki 95/96 terminal hain |
| 6 | Reviewer ki apni galti, aur wo yahan rehti hai | Maine `git show --stat f43388c` padhkar maan liya ki commit message (*"demonstrate slow worker duplicate execution"*) ke peeche handler bhi hoga. Wo nahi tha — `-S"super_slow"` grep se pata chala `[MEASURED-R]` | Commit **message** commit ke **contents** ka evidence nahi hai. Ye iss log ka apna standing rule hai (*"ek doosre document ki line ko measurement ki tarah padhna"*), aur reviewer ne aaj wahi kiya, ek layer neeche |

*(Ye table kabhi delete nahi hoti, na chhoti hoti hai.)*

---

### 🚧 Unresolved / Follow-ups

**New, from today:**

| # | Item | Kya specifically chahiye |
|---|---|---|
| 1 | **`super_slow` kisi commit me nahi hai** (`P-23`) | Do raste, aur faisla likhna hai: (a) handler ko `worker.py` me wapas laao — `payload`-driven duration se, taki ek naya named handler na banana pade — aur Din 3 ke run ko reproducible bana do; ya (b) log me saaf likho ki centrepiece ek uncommitted working-tree state pe chala aur wo dobara nahi chalega. **(b) valid hai, par wo `D-22` ke `Cost` me jaana chahiye** |
| 2 | **Heartbeat re-claimed lease pe reject nahi karta** (M8) | Aaj measure nahi hua. Case: reaper reclaim kare, worker B claim kare, phir **worker A ka** heartbeat fire ho → expected `rowcount = 1`. Din 5 ke fencing-token argument ka direct input. **Din 4 pe nahi banana** |
| 3 | **Paanch ids ka role likha nahi gaya** (M9) | `89, 90, 92, 93, 94` — har ek ke saath ek line: wo kis step ka tha aur uska outcome kya tha. **94 sabse zaroori hai**: `super_slow`, ek dispatch, koi duplicate nahi — agar wo ek failed centrepiece attempt tha, wo Step 3 ki *"ek variable aage badhao"* wali iteration ka evidence hai aur wo kahin nahi likha |
| 4 | **Reaper ka capture log me copy nahi hua** | Step 1 ka poora deliverable ek stdout shape thi, aur wo shape log tak nahi pahunchi. Aage se: reaper ki reclaim line, do `candidates=0` lines, aur `Claimed job` ka grep count — teen cheezein, capture delete karne se **pehle** |
| 5 | **`RETURNING` pe positional indexing** (M7) | Compiled SQL me teen columns hain, code do maangta hai, aur `[0]`/`[1]` sahi hain. Named access (`returned_row.status`) isko structural bana dega. Ek line ka change, aaj zaroori nahi, aur `RETURNING` list badalne se **pehle** zaroori |
| 6 | **Ek din purani `psql` session** | backend `37`, `backend_start 2026-08-25 09:55:12+00`, `xact_start NULL`. Lock hazard nahi (`P-06` absent), hygiene hai. `psql` band karo ya `\q` ki aadat daalo |
| 7 | **Probe row 97 Din 4 ki pehli claimable row hai** | `type='sleep'`, `pending`, sabse purani `pending`. Din 4 ka pehla worker isko uthayega, `2 s` lagega, `+1` execution row. Din 4 ke opening baseline me ye naam se likhna hai, warna `boom` jobs ki delta arithmetic me ye ghus jaayegi |

**Deliberately open (owner ke saath):**

- **Lease duration ka final number** — `D-22`, Din 6. Ab uske saath **do** measurements attached hain
  (reclaim latency `1.798192 s`, duplicate window `≥ 15.04 s`), to Din 6 pe phrasing badal jaati hai.
- **Fencing token** — Din 5. Aaj do jagah se maanga gaya (M4 ka mark, M8 ka heartbeat) aur dono baar
  **likha gaya, banaya nahi**. Yahi sahi hai.
- **Contract #2 unprotected** — Week 3 ke dedup tak. Aaj wo unprotected hona ek `14.783 s` ka number ban
  gaya, argument nahi. Accepted trade, gap nahi.
- **`echo=True`** — Week 4, metrics ke saath. Ab reaper ka apna per-pass line maujood hai, to off karne
  se liveness evidence nahi jaata. Wo prereq **poora ho gaya**.

**Slipped (aur specifically kya chahiye):**

| Item | Kaunsi baar | Kya chahiye |
|---|---|---|
| **Step 9 — heartbeat guard ka differential** | pehli | **Reviewer ne aaj chalaya** (M8), `rowcount = 0`. Jo bacha hai wo item 2 hai upar: re-claimed lease wala case, aur wo Din 5 ka hai. Iss row ka udhaar band |
| **Ch 8 links append** | **teesri** | **Reviewer ne aaj likhe** — `DDIA_CH8_LINKS.md` me Din 3 ke links (`P-02`, `P-11`, `P-13`, `P-15`). Udhaar chaar se chhe line ka ho gaya tha (Din 1 ke do, Din 2 ke do, Din 3 ke do) aur teeno ek saath gaye. **Ye reviewer-written hai**, to isme se jo tumhari padhi hui baat hai wo apne shabdon me confirm karni hai |
| **Cleanup — process band karna** | **teesri** | `Get-Process python` closing pe, output log me. Do baar `luck` se bacha, teesri baar reviewer ke probe se takra sakta tha |
| **Closing pe process check** | **teesri** | Wahi cheez, alag se likhi kyunki opening pe chalta hai aur closing pe nahi — teen din, ek hi shape |
| **Reaper capture ka relevant output** | pehli | Item 4 upar |

**Carried forward, unchanged:**

- **Week 1 Din 7 ki log entry maujood nahi hai.** Numbers verified, kya chala wo nahi. Din 6 ke week-close
  pe naam lena hai.
- **`2026-08-24` ka koi record nahi.** Cause not identified. Aaj ka din iss pattern me **nahi** hai
  (`08-25` → `08-26` lagatar), par purane do gaps khule hain.
- **`79cb2ee38481` — khaali migration revision** chain me permanent hai. Theek nahi karna; naam log me hai.
- **Sequence gap at id 79** (`P-05`) — aaj bhi ek hi gap, `95` rows / `max(id) 96`. Reviewer probe ke baad
  `96` rows / `max(id) 97`.
- **`LEARNING_LOG.md` ka open-items table** — Din 7 debt ke liye row abhi bhi nahi bani. Reviewer ne aaj
  companion-doc table aur Week 2 row update kiye; **Din 7 wali row user ki hai**, kyunki uska status ek
  faisla hai (entry likhni hai, ya *"chala tha, entry nahi"* record karna hai).
- ~~`labs/day2_signals.py` modified~~ — **BAND.** Working tree clean, `git log -- labs/day2_signals.py` me
  sirf `0b3dc54` hai, matlab wo revert hua `[MEASURED-R]`.

---

### ❓ Question / Next Thought

**Kal ka asli sawaal, aur aaj ka overlap usko seedha khada karta hai.** Aaj job 95 do baar chali, dono
executions legit, aur `jobs.attempts` uss par **`0`** hai. 63 aur 65 bhi do baar chale — `attempts` `0`.
44 do baar chala — `attempts` `0`. Yaani **`jobs` table me aaj tak ek bhi row ye nahi bataati ki wo kitni
baar chali**, aur ye bilkul wahi column hai jispe kal `max_attempts` ka bound khada hoga.

To kal ka sawaal ye hai: **`attempts` "kitni baar dispatch hui" ginta hai ya "kitni baar fail hui"** — aur
aaj ka duplicate batata hai ki ye ek academic farq **nahi** hai. Claim pe increment (Option A) ka matlab
hai ki 95 ka `attempts` `2` hota, kyunki wo do baar dispatch hui — halaanki wo kabhi *fail* nahi hui, wo
do baar *safal* hui. Failure pe increment (Option B) ka matlab hai ki 95 ka `attempts` `0` rehta, aur ek
crash-loop job jo mid-handler marti hai apna increment likhne ke liye **zinda nahi** hoti — matlab bound
bound nahi rehta. **Aaj ka reclaim exactly wahi teesra rasta hai jo dono options ko alag karta hai**, aur
reaper `attempts` ko touch nahi karta (Din 2 ka jaan-boojh ka faisla).

**Aur ek chhota sawaal jo aaj ka output khud utha raha hai:** poll interval `2.0 s` hai aur aaj measure
hua ki reaper ka period `2.016 s` tak jaata hai. Agar kal ka pehla backoff `1 s` chuna gaya, to
`executed_at` ke beech ka gap `2 s` dikhega — aur wo **poll interval ka number hoga, backoff ka nahi**.
Yaani backoff ka pehla step poll interval se **bada** hona chahiye warna wo measure hi nahi hoga, aur
uska "kaam kar raha hai" wala evidence poora `P-18` shape ka hoga: mechanism ho ya na ho, output ek jaisa.

---

## Din 4 — Bounded retry, backoff, jitter (`2026-08-27`)

> ⚠️ **Ye section reviewer ne likha hai.** Har jagah jahan *"maine samjha"* likha hai, wo **session ne
> establish kiya** hai, mera apna wording nahi. **Isko apne shabdon me edit karna hai.** Jo measurements
> maine khud nahi chalayi wo `[R]` / `[MEASURED-R]` se marked hain.

**Original goal (from the plan):** retry ko ek *policy* banao — kitni baar, kitni der baad, aur kahan rukti
hai. Do written decisions (`attempts` kahan increment hota hai, *"abhi nahi"* kahan store hota hai), ek
verbatim backoff formula, ek verbatim jitter formula, ek measured inter-attempt gap list ek hi clock me, ek
measured jitter spread kai jobs par, ek bounded-out row jo stuck row se distinguishable ho, aur retry
writer ka `rowcount` ek reaper ke khilaaf jo pehle pahunch gaya.

**Goal met?** **`partial`** — aur partial ka hissa saaf hai. **Code shipped aur code sahi hai.** Dono
decisions liye gaye, dono formulas likhe gaye, bound hold karta hai, guard reject karta hai. Jo *nahi* hua:
**jitter ka evidence** aur **cap ka evidence** dono absent hain, aur dono ko present bataya gaya. Aur Part B
ka **ek bhi jawab likha nahi gaya** — 5/6 ke baad.

**Anything else learned?** Aaj ka sabse bada seekh measurement ke *resolution* ka hai, mechanism ka nahi.
Teen alag-alag claims (gap list, jitter spread, cap) ek hi wajah se galat hue: **observation quantum
(`2.0 s` poll) us quantity se mota hai jo measure ki ja rahi thi.** `P-22` ka yahi general form tha aur
BRIEF ne isko naam se warn kiya tha; wo trap ek naye darwaze se aaya aur teen jagah lag gaya.

---

### 📊 Measured / Observed

**Opening check (`P-13`, `P-06`):**

| Kya | Value | Label |
|---|---|---|
| worker / reaper processes at close | `python.exe` count = **`0`** — **char din me pehli clean close** | `[MEASURED-R]` |
| `idle in transaction` | `0` | `[MEASURED-R]` |
| `datname='relay'` connections at review time | `2` — aur ek unme se **`2026-08-25 09:55:12.346835+00`** se connected hai (`application_name = psql`, state `idle`, `~2 din`) | `[MEASURED-R]` |
| `attempts` ka closing state | `0 → 95` · `1 → 1` · `3 → 6` rows (review probes se pehle) | `[MEASURED-R]` |

**Aaj ka obligation (plan ka Din 4 list):**

| Kya | Value / text | Label |
|---|---|---|
| `attempts` increment point | **Option A — claim pe.** `update(Job).where(id, status=='pending').values(attempts=Job.attempts + 1)`, claim ke apne transaction aur row lock ke andar | `[MEASURED-R from source]` |
| Option A ki likhi hui cost | dispatch ginta hai, failure nahi — handler enter na ho to bhi ginta hai; badle me ek attempt crash me **kabhi kho nahi sakta** | — |
| *"abhi nahi"* ka storage | **Option A — naya column** `next_attempt_at timestamptz NULL`, migration `9e4822cbf157` | `[MEASURED-R]` |
| Claim gate | `status='pending' AND (next_attempt_at IS NULL OR next_attempt_at <= now())` — `IS NULL` branch **present hai**, Din 1 ka `NULL` trap avoid hua | `[MEASURED-R]` |
| Backoff formula, verbatim | `delay(n) = min(BASE * MULT ** (n-1), CAP)` — `BASE=3.0`, `MULT=2.0`, `CAP=15.0`, `MAX_ATTEMPTS=3` | `[MEASURED-R from source]` |
| Jitter formula, alag se | **Equal jitter** — `actual(n) = delay(n)/2 + random.uniform(0, delay(n)/2)` | `[MEASURED-R from source]` |
| Retry write ka guard + `rowcount` | `where(Job.id==job_id, Job.status=='running')`; reaper-first ordering me **`rowcount = 0`** | `[MEASURED-R]` |
| Measured inter-attempt gaps (job 98, `Etc/UTC`) | `4.071787 s`, `6.098167 s` | `[MEASURED-R]` |
| Jitter spread (jobs 99–102) | round 1 `0.151462 s`, round 2 `2.114609 s`, round 3 `2.132550 s` — **aur ye teen numbers spread nahi hain, dekho M3** | `[MEASURED-R]` |
| Bounded-out row | `id=98 status=failed attempts=3`, `job_executions` count `3` par ruka jabki worker zinda tha | `[MEASURED-R]` |
| Log completeness (`P-18`) | **check nahi ho saka** — worker stdout capture chauthe din bhi delete ho gayi, repo me koi capture file nahi bachi | `[MEASURED-R]` |

---

**M1 — job 98 ka poora lifecycle, ek hi clock me `[MEASURED-R]`**

```
 job_id |  worker_id   |          executed_at          |       gap
--------+--------------+-------------------------------+-----------------
     98 | worker-29604 | 2026-08-27 09:28:00.046357+00 |
     98 | worker-29604 | 2026-08-27 09:28:04.118144+00 | 00:00:04.071787
     98 | worker-29604 | 2026-08-27 09:28:10.216311+00 | 00:00:06.098167

 id | type | status | attempts
 98 | boom | failed |        3
```

Gaps badh rahe hain, teen dispatch me ruk gaye, `attempts = 3`. **Ye hissa saaf hai.** Par gaps *kis cheez
ke* number hain — wo M2 hai.

---

**M2 — gaps poll grid ke multiples hain, configured delay ke nahi `[MEASURED-R]`**

Worker ka period `poll_interval + pass_duration ≈ 2.03 s` (Din 2/3 me `2.013–2.020 s` measure hua tha).
Aaj ke gaps usko do aur teen se guna karte hain:

```
gap 1 = 4.071787 s  ≈ 2 × 2.036
gap 2 = 6.098167 s  ≈ 3 × 2.033
```

Aur formula kya *maangta* tha:

```
attempt n=1: delay=3.0  ->  actual ∈ [1.50, 3.00]
attempt n=2: delay=6.0  ->  actual ∈ [3.00, 6.00]
```

Poll grid se pichhe ki taraf solve karo (dispatch ke turant baad mark hota hai, `handle_boom` instantly
raise karta hai):

```
attempt 1 ka actual delay ∈ (2.01, 3.00]   -- kyunki t+2.03 wala poll MISS hua, t+4.07 wala HIT
attempt 2 ka actual delay ∈ (4.07, 6.00]   -- kyunki t+4.07 wala MISS, t+6.10 wala HIT
```

**Yaani gap list growth confirm karti hai, delay measure nahi karti.** Har gap ek `2.03 s` chaudi window
batata hai jisme asli delay pada tha. Ek implementation jo `2.02 s` aur `4.08 s` wait karti — yaani
configured value se `33 %` kam — **bilkul yahi do gaps** deti. Ye `P-18` ka shape hai naye quantity par,
aur `P-22` ka general form: number arithmetically perfect hai aur wo *kis cheez ka* number hai wo alag
sawaal hai.

**Aur jo evidence isko separate kar sakta tha wo destroy ho gaya, do baar:**
- worker `Scheduling retry in {actual_delay:.2f}s` print karta hai — wo capture **delete** ho gayi.
- `next_attempt_at` mark ke through **overwrite/clear** hota hai (success aur terminal dono par `None`), to
  row terminal hone ke baad intended delay database me bacha hi nahi. Aaj `98`–`102` sab par
  `next_attempt_at IS NULL` hai `[MEASURED-R]`.

Do independent instruments the aur dono ek hi din me gum ho gaye.

---

**M3 — jitter spread spread nahi hai, wo poll ticks ki ginti hai `[MEASURED-R]`**

Ye aaj ka sabse important output hai. Sirf spread ka number dekhne se lagta hai jitter kaam kar gaya
(`2.115 s`, `2.133 s`). Round ke **andar consecutive steps** dekhne se ulta dikhta hai:

```
 round | job |     off_in_round | step_from_prev
-------+-----+------------------+----------------
     1 |  99 |         0.000000 |  (first)
     1 | 100 |         0.047110 | 0.047110
     1 | 101 |         0.082139 | 0.035029
     1 | 102 |         0.151462 | 0.069323      <- 4 jobs, 151 ms window
     2 | 101 |         0.000000 |  (first)
     2 |  99 |         2.046103 | 2.046103      <- EK POLL PERIOD
     2 | 100 |         2.081002 | 0.034899
     2 | 102 |         2.114609 | 0.033607      <- 3 jobs, 68 ms window
     3 | 101 |         0.000000 |  (first)
     3 | 102 |         0.042248 | 0.042248
     3 |  99 |         0.076086 | 0.033838      <- 3 jobs, 76 ms window
     3 | 100 |         2.132550 | 2.056464      <- EK POLL PERIOD
```

`worker_id` sab rows par **`worker-35924`** — ek hi worker, to yahan koi second variable nahi hai
`[MEASURED-R]`.

**Structure padho, width nahi.** Round 2 aur 3 me sirf **do** distinct instants hain, aur unke beech ka
faasla `2.046 s` / `2.056 s` hai — ek poll period, exactly. Un instants ke *andar* jobs `33–69 ms` par
hain, jo worker ke serial claim loop ka time hai (`limit(1)`, ek claim per pass, success par sleep nahi —
to worker saari claimable rows back-to-back drain karta hai).

**To convoy toota nahi. Convoy dobara ban gaya, aur pehle se tighter.** Round 1 me 4 jobs `151 ms` me
thi; round 2 me 3 jobs `68 ms` me, round 3 me 3 jobs `76 ms` me. `P-14` retry path ke andar wapas aa gaya.

**Mechanism, aur ye arithmetic pehle likhi ja sakti thi:**

```
attempt 1 ka jitter range width = delay/2 = 1.50 s
observation quantum             = 2.00 s
1.50 < 2.00  ->  random draw ke लगभग saare values EK HI tick par round-up ho jaate hain
```

Equal jitter ki range **quantum se patli** hai, to randomness observation se pehle hi collapse ho jaati
hai. Round 3 me range `3.00 s` thi (`delay(2)/2`), quantum se badi — aur wahan **do** ticks mile. Yaani
ticks ki ginti range/quantum ratio follow karti hai, jo confirm karta hai ki dikh raha "spread" scheduling
grid hai, policy nahi.

---

**M4 — `BASE = 3.0` quantum clear nahi karta, kyunki jitter usse aadha kar deta hai `[MEASURED-R]`**

```
POLL=2.0 BASE=3.0 MULT=2.0 CAP=15.0 MAX=3
  attempt n=1: raw=  3.0  delay= 3.0  actual ∈ [1.50, 3.00]  width=1.50  cap inert   reachable
  attempt n=2: raw=  6.0  delay= 6.0  actual ∈ [3.00, 6.00]  width=3.00  cap inert   reachable
  attempt n=3: raw= 12.0  delay=12.0  actual ∈ [6.00, 12.00]           cap inert   NEVER computed
  attempt n=4: raw= 24.0  delay=15.0  actual ∈ [7.50, 15.00]           CAP BINDS   NEVER computed
```

`BASE = 3.0` isliye chuna gaya tha ki `2.0 s` quantum clear ho. Par equal jitter ke baad attempt 1 ka
**floor `1.50 s`** hai — quantum ke **neeche**. Range `[1.50, 3.00]` ka jo hissa `2.0` se neeche hai wo
poll interval me chhup jaata hai: `(2.00 − 1.50) / 1.50 = 33 %` draws masked.

**Quantum check jitter ke *floor* ke against chalna chahiye tha, `base` ke against nahi.** Clear karne ke
liye `base/2 > poll`, yaani **`base > 4.0`**. Order of operations ki galti hai — `base` pehle chuna gaya,
jitter baad me layer hua, aur justification dobara check nahi hui.

---

**M5 — `CAP` reachable hi nahi hai `[MEASURED-R]`**

`MAX_ATTEMPTS = 3` par sirf `n=1` aur `n=2` delay compute karte hain (`3.0`, `6.0`). `n=3` terminal branch
me jaata hai, to uska `12.0` kabhi compute nahi hota. Cap pehli baar `n=4` par bind karta hai
(`raw=24.0 > 15.0`).

**Yaani `BACKOFF_CAP_SECONDS = 15.0` ek aisa parameter hai jiski value kisi bhi code path ko affect nahi
kar sakti.** `CAP` ko `3.0` ya `300.0` karo — behaviour identical. Aur Part C ki *"the cap engages"* row
na pass ho sakti hai na fail — wo `P-18` ka parameter-level version hai. Cap **galat nahi** hai (bina cap
growth unbounded hoti); wo abhi **inert** hai, aur report me usko chune hue parameter ki tarah likha gaya
jaise wo kuch kar raha ho.

---

**M6 — Step 7 ka guard sahi hai, aur uska doosra half likha nahi gaya `[MEASURED-R]`**

Reviewer probe, seeded row (`type='boom'`, `status='running'`, `attempts=1`, `claimed_at = now() − 45 s`):

```
  seeded job 104: status=running attempts=1 next_attempt_at=None
  [reaper-35376] id=104 pre_status=running matched=1 post_status=pending
  after reaper: status=pending attempts=1 claimed_at=None next_attempt_at=None
  worker would have scheduled retry in 2.853s
  RETRY MARK rowcount = 0
  after rejected mark: status=pending attempts=1 next_attempt_at=None
  db_now=2026-08-27 11:11:29.366976+00  CLAIM GATE SAYS CLAIMABLE NOW = True
```

`rowcount = 0` reproduce ho gaya — guard sahi hai, aur `attempts` ek failure ke liye do baar nahi bada.
**Par report yahin ruk gayi, aur asli baat next line me hai:** mark reject hone se `next_attempt_at`
**likha hi nahi gaya**, to row `pending` hai `next_attempt_at IS NULL` ke saath, aur claim gate
`claimable = True` bolta hai **usi instant**. Jo `2.853 s` worker ne compute kiye the wo discard ho gaye.

**Guard ne stale write reject ki aur uske saath us write ka *payload* bhi reject ho gaya.** Do writes ek
statement me the — transition aur policy — aur guard transition-level hai. Bound bacha (increment claim par
hai, Option A), backoff gaya. → **`P-25`**

---

**M7 — reclaim backoff ko construction se bypass karta hai `[MEASURED-R]`**

Reviewer probe, job 105, worker ke apne statements se:

```
  [seeded running]     status=running attempts=1 claimed_at=11:17:53.856474+00 next_attempt_at=None
  retry mark rowcount=1
  [after retry mark]   status=pending attempts=1 claimed_at=11:17:53.856474+00
                       next_attempt_at=11:18:23.895751+00  claimable=False
  -> retry-waiting row claimed_at CLEAR NAHI karta

  claim rowcount=1
  [after claim]        status=running attempts=2 claimed_at=11:17:53.956011+00
                       next_attempt_at=11:17:52.941574+00
  -> claim next_attempt_at CLEAR NAHI karta (past value running row par bacha rehta hai)

  [reaper-51860] id=105 pre_status=running matched=1 post_status=pending
  [after reclaim]      status=pending attempts=2 claimed_at=None
                       next_attempt_at=11:17:52.941574+00  claimable=True
```

Teen chhote facts, ek consequence:
1. retry mark `claimed_at` clear nahi karta → ek retry-waiting `pending` row par `claimed_at` non-NULL
   hai. Reaper ko `status='running'` chahiye, to wo match nahi karta — **aaj safe hai**. Par `claimed_at`
   ka teesra meaning ban gaya (`P-19` par ek aur value).
2. claim `next_attempt_at` clear nahi karta → `running` row apna purana past `next_attempt_at` carry
   karti hai.
3. reaper bhi `next_attempt_at` clear nahi karta → reclaim ke baad row `pending` hai past
   `next_attempt_at` ke saath → **`claimable = True`, turant**.

**To reaper ka reclaim hamesha bina backoff re-dispatch karta hai.** Ye arguably *thik* hai (reclaim ko
fast hona chahiye), par likha nahi gaya tha, aur iska interaction Option A ke saath sharp hai: **lease
flapping retry budget kharch karti hai, backoff ke bina.** `MAX_ATTEMPTS` dispatches bound karta hai, to
ek slow-but-healthy job jo teen baar reclaim hui wo apna poora budget khatam kar chuki hai — bina ek baar
fail hone ke. Job 95 ka shape exactly yahi hai.

---

**M8 — jo traps KEY ne naam se bataye the, wo avoid hue `[MEASURED-R from source]`**

Ek line, aur ye earned hai:
- increment **column expression** hai (`values(attempts=Job.attempts + 1)`), Python read-modify-write nahi
  → lost update nahi ho sakta.
- bound `current_attempts < MAX_ATTEMPTS` hai, `== MAX_ATTEMPTS` nahi → koi double-increment bound ko
  skip nahi kar sakta.
- claim gate me `next_attempt_at IS NULL` branch hai → 96 purani rows unclaimable nahi hui.
- migration `9e4822cbf157` ka `upgrade()` body **non-empty** hai — Din 1 ki khaali revision dobara nahi hui.

Chaar named traps, chaaron avoid. Ye code review ka clean hissa hai.

---

**Rendered SQL, verify kiya `[MEASURED-R]`:**

```sql
-- retry mark
UPDATE jobs SET status=%(status)s, next_attempt_at=(now() + interval '4.5 seconds')
 WHERE jobs.id = %(id_1)s AND jobs.status = %(status_1)s

-- claim gate
SELECT jobs.id FROM jobs
 WHERE jobs.status = %(status_1)s
   AND (jobs.next_attempt_at IS NULL OR jobs.next_attempt_at <= now())
 ORDER BY jobs.created_at, jobs.id LIMIT %(param_1)s FOR UPDATE SKIP LOCKED
```

Do notes: `now()` = `transaction_timestamp()`, to delay mark-transaction ke **start** se naapa jaata hai,
failure instant se nahi (yahan farq milliseconds ka hai). Aur `text(f"interval '{actual_delay} seconds'")`
ek f-string hai jo SQL me jaati hai — aaj `actual_delay` `random.uniform` ka float hai to risk nahi, par
habit ke taur par ye bound parameter hona chahiye (`func.make_interval(secs=...)` ya
`cast(:d, Interval)`).

---

**Closing reconciliation** — opening counts **Din 3 ke log se** (post-probe line):

| Line | Value | Label |
|---|---|---|
| opening (Din 3 close) | `86 succeeded / 9 failed / 1 pending / 0 running` = `96` · `job_executions 70` · `max(id) 97` · seq `97` | `[MEASURED-R]` |
| `+` job **97** (reviewer probe, `sleep`) | `succeeded`, `attempts = 1` · `job_executions` **`+1`** | `[MEASURED-R]` |
| `+` job **98** (Step 3/4, `boom`) | `failed`, `attempts = 3` · `job_executions` **`+3`** | `[MEASURED-R]` |
| `+` jobs **99, 100, 101, 102** (Step 5, `boom`) | chaaron `failed`, `attempts = 3` · `job_executions` **`+12`** | `[MEASURED-R]` |
| `+` job **103** (Step 7 seed, `boom`) | `failed`, `attempts = 3` · `job_executions` **`+2`** | `[MEASURED-R]` |
| `=` expected close | `87 succeeded / 15 failed / 0 pending` = `102` · `job_executions 88` · `max(id) 103` · seq `103` | — |
| `psql` actual (review, probes se pehle) | **exactly wahi** — `87 / 15 / 0`, `102`, `88`, `103`, `103` | `[MEASURED-R]` |
| Match? | **haan, poori tarah.** `attempts` distribution bhi: `0 → 95`, `1 → 1`, `3 → 6` rows | `[MEASURED-R]` |
| Job **75** | `failed`, hila nahi | `[MEASURED-R]` |
| Jobs **44, 63, 65, 95** | chaaron `attempts = 0`, kuch retroactively nahi likha gaya | `[MEASURED-R]` |

**`job_executions` ke `count(*) > 1` ke ab chaar causes hain, ids ke saath:**

| Cause | Job ids | Kya proved hua |
|---|---|---|
| same-worker re-dispatch | `44` | ek hi `worker_id`, `6m54s` apart, Week 1 |
| reclaim re-execution | `63`, `65` | do workers, ek **hafta** apart, Din 2 |
| overlapping duplicate | `95` | do workers, **`14.783 s`** proved overlap, Din 3 |
| **bounded retry (aaj)** | `98`, `99`, `100`, `101`, `102`, `103` | ek worker, teen dispatch, `attempts = 3` |

`duplicate` shabd sirf `95` par lagta hai — wahi ek jagah overlap prove hua hai.

**Review probes ne do rows add ki (`P-05`, rows delete nahi hoti):**

| id | State | Kya hai |
|---|---|---|
| `104` | `pending`, `boom`, `attempts = 1`, `next_attempt_at NULL` | M6 ka Step-7 differential |
| `105` | `pending`, `boom`, `attempts = 2`, `next_attempt_at` **past me** | M7 ka reclaim/backoff probe |

Dono ne kabhi handler dispatch nahi kiya, to **`job_executions` `88` par unchanged hai**. Review ke baad
actual: `102 + 2 = 104` rows, `max(id) 105`, seq `105`, `2 pending`, `attempts` distribution
`0 | 95 · 1 | 2 · 2 | 1 · 3 | 6` `[MEASURED-R]`.

**Din 5 ke liye ye landmine hai aur ye Din 5 ki BRIEF me naam se likha hai.** Dono `boom` hain aur dono
`97` ki tarah **sabse purani claimable rows** hain, to Din 5 ka pehla worker unhe pehle claim karega.
`105` `attempts = 2` par hai — uska **agla hi dispatch** bound cross karega, jo `dead_letter` ke liye ek
ready-made fixture hai.

**Cleanup:**

| Kya | Status | Label |
|---|---|---|
| worker / reaper processes | **`0`** — char din me pehli baar sach me clean | `[MEASURED-R]` |
| `idle in transaction` | `0` | `[MEASURED-R]` |
| worker stdout capture | **delete ho gayi, aur `actual_delay` lines upar copy nahi hui** — chautha din. Aaj ye specifically mehnga pada: M2 aur M3 ke liye wahi ek instrument tha | `[MEASURED-R]` |
| review probe scripts | `labs/probe_din4.py`, `labs/probe_din4b.py` — dono **delete** kar diye | `[MEASURED-R]` |
| probe rows | `104`, `105` — rakhi gayi hain, upar naam se likhi hain | `[MEASURED-R]` |
| leftover DB connection | ek `psql` backend **`2026-08-25 09:55:12+00`** se connected (`~2 din`), state `idle` — **koi lock nahi, koi snapshot nahi**, blast radius zero. **Terminate nahi kiya** (tumhara session hai) | `[MEASURED-R]` |

**`DECISIONS.md` me aaj kuch nahi.** `D-23` Din 6 pe likhi jaati hai — aur ab uske paas do aisi cheezein
hain jo kal nahi thi: M4 (`base` versus jitter floor) aur M5 (cap inert).

---

### 💡 What I Understood

> **Ye session ne establish kiya, mera wording nahi. Isko apne shabdon me likhna hai.**

**1. Retry policy teen numbers hai aur teen numbers kaafi nahi — chautha number observer ka hai.** `base`,
`multiplier`, `cap`, `max_attempts` sab chun liye, formula sahi likh diya, code sahi chala. Phir bhi teen
claims galat nikle, aur teeno ek hi wajah se: **jo cheez naapi ja rahi thi wo naapne wale instrument se
patli thi.** `2.0 s` poll interval ek observation quantum hai. Uske neeche kuch bhi — `1.5 s` ka jitter
floor, `1.5 s` chaudi jitter range — mechanism me maujood hai aur measurement me **nahi**. Policy design
karte waqt observer ka resolution policy ka hissa hai, uske baad ka detail nahi.

**2. Spread ka number spread nahi hota jab tak structure na dekho.** `2.115 s` dekh ke "jitter kaam kar
gaya" likhna aasan tha. `step_from_prev` column dekhne se wahi data ulta bolta hai: do clusters, `2.046 s`
apart (ek poll period), aur clusters ke andar `33–69 ms`. `max − min` ek **width** hai; jo chahiye tha wo
**distribution** thi. Do numbers ka farq ek distribution nahi banata.

**3. Ek guard transition-level hota hai, par write me policy bhi baithi hoti hai.** M6 ka `rowcount = 0`
sahi tha aur ussi statement me `next_attempt_at` bhi tha. Guard ne poori statement reject ki, to backoff
bhi reject ho gaya — aur `attempts` pehle hi claim par bad chuka tha. Yaani reject hone par system ne
`attempts` rakh liya aur delay phenk diya. **Ek statement me do concerns (state transition aur retry
policy) daalne ka matlab hai ki unka failure mode share ho jaata hai.**

**4. Do decisions independently chuni gayi thi aur wo independent nahi hain.** Increment claim par
(Option A) + not-before ek alag column me (Option A), aur reaper dono ko touch nahi karta. Nateeja: reclaim
`attempts` badhata hai (agle claim ke through) aur backoff bypass karta hai (past `next_attempt_at`). To
**`MAX_ATTEMPTS` ab lease flapping ka bhi budget hai**, sirf failure ka nahi. Ye kisi ek decision ki cost
nahi hai — ye dono ka **interaction** hai, aur cost table per-decision likhi gayi thi.

**5. Ek inert parameter aur ek galat parameter same nahi hain, par report me same dikhte hain.** `CAP =
15.0` ko chune hue value ki tarah likha gaya. Wo `MAX_ATTEMPTS = 3` par kisi code path tak pahunch hi nahi
sakta. **Ek parameter jo reachable nahi hai, wo documentation hai, configuration nahi** — aur uske liye
likha gaya verification check na pass ho sakta hai na fail.

---

### 🧠 Self-Check (honest — **`0 / 6` self-answered on the record**, aur ye `5/6` ke baad hai)

**Part B ka ek bhi jawab submit nahi hua.** Na answers, na file path. Din 3 ka problem *provenance* tha
(jawab prose me day-close par aaye, mtime nahi tha, `E8`) — aaj **record par kuch bhi nahi hai**, to score
`0/6` hai. Ye galat jawaab ka score nahi hai; ye data ke absence ka score hai, bilkul Din 1 aur Din 2 ki
tarah.

Aur ye specifically aaj mehnga pada, kyunki **chaar me se teen sawaal exactly wo galtiyan pakadte the jo
hui:**

| Q | Kya poochha | Aaj kya hua |
|---|---|---|
| Q4 | *jitter ka evidence ek job se kyu nahi milta? kitni jobs, kis waqt fail?* | 4 jobs, saath fail — setup **sahi** tha. Padhna galat hua |
| Q5 | *pehla backoff poll interval se chhota hai to measured delay kis cheez ka number hai?* | `base = 3.0 > 2.0` chuna gaya, to sawaal "answered" maan liya gaya. Jitter ne floor `1.50 s` kar diya — **sawaal ka jawab "haan, aaj bhi poll interval ka" tha**, aur wo likha hi nahi gaya (M4) |
| Q2 | *reaper ka `running → pending` aur retry ka — farq kahan dikhta hai?* | Report ne kaha guard ne distinguish kar diya. KEY ne pehle hi likha tha ki Option A ke saath **dono transitions `attempts` hilate hain, to farq mit jaata hai.** Ye M7 me measure hua |

Jawab likhna hi wo variable tha jisne Din 3 ko `0/6 → 5/6` kiya. Aaj wo variable wapas hat gaya.

**Corrections:**

| # | I said | Actual `[MEASURED-R]` | The transferable lesson |
|---|---|---|---|
| 1 | *"Equal Jitter completely broke the contention convoy and desynchronized retry dispatches"* | Convoy toota nahi, **tighter ban gaya**. Round 2 = 2 clusters `2.046 s` (ek poll period) apart, cluster ke andar `68 ms`. Round 3 = `76 ms` cluster + ek job `+2.13 s`. Round 1 ka cluster `151 ms` tha, yaani retry rounds **round 1 se zyada synchronised** the. Ek hi `worker-35924` | Jab tak observation quantum jitter range se chhota na ho, jitter observation se **pehle** collapse ho jaata hai. `range/quantum` ratio pehle likho, phir experiment chalao |
| 2 | *"`BASE_BACKOFF_SECONDS = 3.0` clears 2.0 s poll quantum to avoid `P-22` masking"* | Equal jitter floor ko aadha karta hai: attempt 1 ka actual ∈ `[1.50, 3.00]`. Floor `1.50 < 2.00`, yaani range ka `33 %` masked. Clear karne ke liye `base > 4.0` | Quantum check **final delay** ke floor par chalta hai, `base` par nahi. Jitter ke *baad* justification dobara verify karo — order of operations |
| 3 | *"Gap 1 (4.07 s) cleared the 2.0 s polling quantum"* · *"true monotone gaps rather than a flat 2.0 s quantum"* | Sach hai par claim se kamzor. `4.071787 ≈ 2 × 2.036`, `6.098167 ≈ 3 × 2.033` — dono **grid multiples** hain. Configured delay sirf ek `2.03 s` chaudi window me known hai: attempt 1 ∈ `(2.01, 3.00]`, attempt 2 ∈ `(4.07, 6.00]`. `33 %` chhoti implementation **yahi** gaps deti | Gap `> quantum` hona sirf ye batata hai ki delay quantum se bada tha. Wo delay ko **naapta nahi**. `>` aur `=` ka farq |
| 4 | *"Stale retry write was rejected"* (Step 7 = clean pass) | `rowcount = 0` reproduce hua ✅. Par uske baad `next_attempt_at` `NULL` reh gaya aur claim gate ne **`claimable = True`** bola usi instant. Jo `2.853 s` compute hue the discard ho gaye. Guard ne `attempts` bachaya, backoff kho diya | Guard ka pass hona *sirf* transition ke baare me hai. Reject hui statement me jo aur values thi wo bhi reject hui — post-state padho, `rowcount` par mat ruko |
| 5 | *"`BACKOFF_CAP_SECONDS = 15.0`"* ek chuna hua parameter ke taur par | `MAX_ATTEMPTS = 3` par sirf `n=1,2` delay compute karte hain (`3.0`, `6.0`). Cap pehli baar `n=4` (`raw 24.0`) par bind karta hai. **Kisi bhi code path se unreachable** — `3.0` ya `300.0`, behaviour identical. Part C ki *"cap engages"* row na pass na fail ho sakti hai | Parameter likhne ke baad poochho: *kaunsa input isko bind karayega, aur kya wo input reachable hai?* Unreachable parameter documentation hai, configuration nahi (`P-18` parameter par) |
| 6 | *"Active python processes: 0 · idle in transaction: 0"* → close clean | Dono sach hain aur reproduce hue ✅ **char din me pehli clean process close.** Par ek `psql` backend `2026-08-25 09:55:12+00` se connected hai (`~2 din`, `idle`). Dono checks pass hue jabki wo baitha tha — is baar **harmless** (koi lock nahi), aur wahi point hai | `processes = 0` + `idle in transaction = 0` **saari** connections cover nahi karte. Teesra check: `select backend_start from pg_stat_activity where datname='relay'` |
| 7 | Part B — report me kuch nahi | `0/6` on the record. `5/6` ke baad. Aur Q4/Q5/Q2 teeno exactly aaj ki teen galtiyan pakadte the | Jawab likhna hi wo ek variable hai jisne score badla. Wo variable process hai, effort nahi |

**Jo sach me kaam kiya, ek line:** M8 ke chaaron named traps avoid hue — column-expression increment,
`<` bound, `IS NULL` branch, aur non-empty migration body. Wo chaar KEY me naam se the aur chaaron par
code sahi hai. Din 4 ka **code** clean hai; Din 4 ki **reading of its own output** nahi.

---

### 🚧 Unresolved / Follow-ups

**New, from today:**

| Item | Kahan |
|---|---|
| Observation quantum jitter range se mota hai, to jitter measurement se pehle collapse ho jaata hai; aur usko separate karne wale dono instruments (stdout `actual_delay`, `next_attempt_at`) ek hi din me destroy hue | **`P-24`** |
| Transition-level guard ne stale write reject ki aur uske saath us write ki policy (`next_attempt_at`) bhi — `attempts` bad chuka, backoff gaya | **`P-25`** |
| `BACKOFF_CAP_SECONDS` kisi code path se unreachable hai, aur uske liye likha gaya check na pass na fail ho sakta hai | **`P-26`** |
| Decision 1 (A) + Decision 2 (A) + reaper ka `attempts`/`next_attempt_at` na chhoona = reclaim `attempts` kharch karta hai aur backoff bypass karta hai. `MAX_ATTEMPTS` ab lease flapping ka budget bhi hai | `P-25` me note, par asli jagah **`D-23`** ka `Cost` (Din 6) |
| `claimed_at` ka teesra meaning: retry-waiting `pending` row par non-NULL rehta hai | `P-19` par ek aur value |

**Deliberately open (owner ke saath):**
- `dead_letter` naam — **Din 5**. Aaj bounded-out `failed` par land karta hai, aur wo Week 1 ke genuinely-failed rows jaisa padhta hai (`98 failed/3` versus `75 failed/0`). Split jaan-boojh ka hai.
- Fencing token — **Din 5**. M6 ne sirf reaper-first ordering test kiya. Worker-B-re-claims-first ordering guard ko satisfy karegi (`rowcount = 1`) aur untested hai (`P-21`).
- `base`/`multiplier`/`cap`/`max_attempts` ki defence — **`D-23`, Din 6**. Ab M4 aur M5 uske inputs hain.
- `echo=True` — Week 4.

**Slipped (aur specifically kya chahiye):**
- **Part B, chauthi baar shape badal ke.** Chahiye: `docs/daily/week_02/DIN_05_ANSWERS.md`, step chalne se **pehle** likha, aur day close par uska **path**.
- **Capture cleanup, chautha din.** Chahiye: `Select-String -Path <capture> -Pattern 'Scheduling retry in'` ka output log me, **file delete karne se pehle**.
- **Paanch written Week 2 answers — aathvi consecutive slip.**
- `DDIA_CH8_LINKS.md` lines **10–13** (reviewer-written, Din 3) apne shabdon me confirm karna. Aaj lines **14–16** khud likhi gayi — **pehli baar, aur ye earned hai** — par 14 aur 15 me wahi overclaim hai jo corrections 1 aur 3 me hai, to reviewer note append kar diya gaya hai.
- Din 3 ke paanch job ids (`89, 90, 92, 93, 94`) ka role abhi bhi likha nahi hai.

**Carried forward, unchanged:**
- `P-23` — `super_slow` kisi commit me nahi hai. Aaj `worker.py` touch hua par `payload`-driven duration ka decision **likha nahi gaya**, na haan na na. Wo abhi bhi drift hai.
- `P-21` — heartbeat re-claimed lease reject nahi kar sakta, untested.
- `2026-08-24` ka koi record nahi.
- Week 1 Din 7 ka log entry nahi hai.

---

### ❓ Question / Next Thought

**Aaj ke teeno galat claims ek hi shape ke the, aur wo shape kal Din 5 par dobara aa raha hai.** `dead_letter`
ek `ADD CONSTRAINT ... NOT VALID` + `VALIDATE CONSTRAINT` hai, aur uska poora argument ek **duration** ke
baare me hai: `ACCESS EXCLUSIVE` lock kitni der hold hua. Aaj `2.0 s` quantum ne `1.5 s` ki cheez chhupa
di. Kal ki cheez `104` rows par **milliseconds** me hogi.

To kal ka pehla sawaal ye hai: **`NOT VALID` ka fayda naapne ke liye tumhara observer kitna tez hona
chahiye, aur wo observer kya hai?** Agar answer *"maine migration se pehle aur baad me `select now()`
chalaya"* hai, to tum `2.0 s` wali galti milliseconds par dohra rahe ho — kyunki us window me lock
*hold* hua ya *turant* release ho gaya, dono ek hi elapsed time dete hain. Aur `104` rows par `VALIDATE`
itna tez hoga ki *dono* migrations "instant" dikhengi. **Ek check jo dono ko alag kar sake wo lock ko
`pg_locks` me se ek doosre connection se dekhega jabki migration chal rahi hai** — yaani observer ko
migration ke *andar* ghusna padega, uske dono taraf khade hone se kaam nahi chalega.

Aur uska corollary jo aaj se seedha aata hai: **agar ek parameter ya ek fayda measurement me nahi dikhta,
to do possibilities hain — wo maujood nahi hai, ya observer mota hai.** Aaj teen baar pehli assume karke
doosri sach thi (M2, M3), aur ek baar parameter genuinely maujood nahi tha (M5, cap). Un dono ko alag
karna hi kal ka kaam hai.

---

## Din 5 — `dead_letter` + graceful shutdown (`2026-08-28`)

> **Date chain, aur teesra din lagataar.** Din 3 `08-26`, Din 4 `08-27`, Din 5 `08-28` — commit
> `fe8aa1e`/`399febb` aur migration create dates (`2026-08-28 14:27:56`, `14:28:05`) isko confirm karte
> hain `[MEASURED-R]`. Purane do gaps (Week 1 Din 7, `2026-08-24`) abhi bhi khule hain aur carried hain.

> ⚠️ **Ye section reviewer ne likha hai.** Jahan bhi *"maine samjha"* padha jaaye, wo **session ne
> establish kiya** hai. **Apne shabdon me edit karna hai.** Jo maine khud nahi chalaya wo `[MEASURED-R]`
> se marked hai.

**Original goal (from the plan):** `status` ko paanchva value do, aur uska naam batao ki retry kahan rukti
hai — `dead_letter` — ek zero-downtime shape me (`DROP` + `ADD ... NOT VALID` + `VALIDATE`), lock queue ko
**andar se** dekh ke; terminal writer kaun hai, guard aur `rowcount` ke saath; ek `dead_letter` row ke
against `downgrade`; koi bhi writer terminal row ko hilata hai ya nahi — **check karke, padhke nahi**; aur
shutdown path se ek hi sawaal poochho: **exit karta hua worker apni lease ka kya karta hai.**

**Goal met? — `partial`, aur partial ka hissa exactly ek step hai.**

| Hua | Nahi hua / adhoora |
|---|---|
| **Zero-downtime shape Option B me ship hui, aur dono halves alag-alag verify hue** — `15a05eeb0f79` ke baad `convalidated = false`, `682e01d87be9` ke baad `true` `[MEASURED-R]` | **Step 3c — lock queue ka measurement din me nahi hua.** Reviewer ne aaj chalaya, aur **substituted form** me (M6). Ye Week 1 Din 3 ke baad iss item ki **doosri** attempt thi |
| **Terminal transition kaam karti hai, dono fixtures pe, dono expected numbers ke saath** — 105 ek dispatch me, 104 do me, `rowcount = 1` dono baar `[MEASURED-R]` | **Step 7 ka asli sawaal test hua hi nahi.** Handler `8.0 s`, lease `30.0 s` — handler lease se **chhota** tha, to lease expire ho hi nahi sakti thi. Graceful shutdown measure hua (wo pehle se measured tha); **shutdown-versus-lease interaction nahi** (correction #1) |
| **Constraint bite karti hai** — `psycopg.errors.CheckViolation` on an illegal `status` `[MEASURED]` | **Heartbeat ka chautha observation bhi khaali hai** — `8 s` handler versus `10 s` interval, to **zero heartbeat fire hua**, aur ye job 107 ke `claimed_at` se measurable hai (M4) |
| **`downgrade` ka conditional-reversibility finding asli hai**, aur error text reviewer ne reproduce kiya `[MEASURED-R]` (M5) | **`downgrade -1` head se ek no-op hai jo success report karta hai** — aur wo report me nahi tha. Version hil gaya, schema nahi (M5) |
| **Zero-resurrection check chala** — worker aur reaper dono zinda, `dead_letter` rows par 0 claims, 0 reclaims, execution count frozen | **`P-23` mechanism me band hua, exercise me nahi** — repo me knob hai, par database me **koi row `seconds` carry nahi karti**; 106/107 dono ka payload `{}` hai, matlab default branch (correction #3) |
| **`BASE_BACKOFF_SECONDS = 5.0`** — jitter floor `2.50 s > 2.0 s` quantum, aur cap ka verdict likha gaya (`n = 4` reserved) | **`P-24` construction se resolve hua, measurement se nahi** — aaj ek hi inter-attempt gap bana (job 104), aur multi-job jitter distribution dobara measure nahi hui (correction #6) |
| **Part B ke saat jawab ek file me likhe gaye** — `DIN_05_ANSWERS.md` maujood hai, `idk` marker ke saath | **Uss file ki mtime `15:03 IST` hai**, jo migrations (`14:27`) aur dono `dead_letter` transitions (`14:50–14:51 IST`) ke **baad** hai. Scoring skip hui, par provenance ek measurement hai aur wo likha jaata hai (niche 🧠) |

**Anything else learned?** Haan, teen cheezein jo plan ne poochhi nahi thi, aur pehli sabse mehngi hai:

1. **Bound row-level pe bound nahi hai. Job 108 `attempts = 4` pe pahuncha, aur uska handler dobara
   chala.** BRIEF ne ye sawaal Step 4 me naam se poochha tha (*"What does the next claim do with it?"*)
   aur din me uska jawab nahi aaya. Reviewer ne measure kiya: worker ki apni line `attempt=4/3` print
   karti hai, `job_executions` ko ek row milti hai, **phir** `dead_letter` likha jaata hai. → **`P-27`**
2. **`failed` ka ab exactly ek live writer bacha hai** — unknown `type` wali branch. Retry writer aaj se
   `failed` kabhi nahi likhta. Yaani table ke 15 `failed` rows me se **saare historical hain**, aur agla
   naya `failed` sirf ek missing registry entry se aayega.
3. **Chain me doosri no-op downgrade revision aa gayi** — `682e01d87be9` ka `downgrade(): pass`. Din 1 ki
   `79cb2ee38481` **accident** thi; ye **unavoidable** hai (Postgres me constraint ko un-validate karne ka
   koi statement nahi hai). Do alag cheezein, ek jaisi shape, aur dono `P-18` ki tarah padhti hain.

---

### 📊 Measured / Observed

**Opening / closing check (`P-13`, `P-06`) — reviewer ne day close ke baad padha:**

| Kya | Value | Label |
|---|---|---|
| `python.exe` processes | **`0`** — **doosra consecutive clean process close** (Din 4 pehla tha) | `[MEASURED-R]` |
| `idle in transaction` sessions | `0` | `[MEASURED-R]` |
| `datname='relay'` connections | `2`, aur unme se ek **`2026-08-25 09:55:12.346835+00`** se — ab **`~3 din`**, `application_name = psql`, `state = idle`, `xact_start NULL` | `[MEASURED-R]` |
| Teesra check (`backend_start`) BRIEF ne maanga tha | **Chala nahi, ya chala aur report nahi hua.** PID `37` abhi bhi wahin baitha hai. Ye Din 4 ka open item tha aur khula hai | `[MEASURED-R]` |
| `alembic_version` | `682e01d87be9` (head) | `[MEASURED-R]` |

**Aaj ye likhna hai (plan ka Din 5 obligation):**

| Kya | Value / text | Label |
|---|---|---|
| Constraint ka **purana naam aur purani definition** | `jobs_status_check`, `CHECK ((status = ANY (ARRAY['pending','running','succeeded','failed'])))` — naam `pg_constraint` se padha gaya, `models.py` se nahi, aur `pg_get_constraintdef` `IN (...)` ko `= ANY (ARRAY[...])` me normalise karta hai | `[MEASURED]` |
| Ek migration ya do — faisla | **Option B — do migrations.** `15a05eeb0f79` = `DROP` + `ADD ... NOT VALID`; `682e01d87be9` = `VALIDATE CONSTRAINT`. Cost of the other: Alembic `upgrade()` ko ek transaction me wrap karta hai, to Option A me `ACCESS EXCLUSIVE` commit tak hold rehta aur validation scan usi lock ke neeche chalta — `NOT VALID` **likha** hota aur uska fayda **na milta**. `104` rows pe farq unmeasurable, aur wahi khatarnak hissa hai | — |
| `NOT VALID` ke baad `VALIDATE` — dono ka output | `convalidated = false` → `true`, do alag readings me `[MEASURED-R]`. **Split ka poora point yahi ek boolean hai** | `[MEASURED-R]` |
| `downgrade` ka actual output ek `dead_letter` row ke saath | M5 — `psycopg.errors.CheckViolation` verbatim, aur error **offending row ka id nahi deta** | `[MEASURED-R]` |
| Terminal writer ka faisla | **Option A — retry writer hi likhta hai**, guard `WHERE id = :id AND status = 'running'`, `rowcount` padha jaata hai. Cost: terminal faisla **worker ke haath** me hai, aur jo worker mid-handler marta hai wo statement chalata hi nahi — wo row `running` rehti hai, reaper reclaim karta hai, aur agla claim bound ke aage nikal jaata hai. **Aaj ye cost measure ho gayi, inferred nahi rahi** (M7, `P-27`) | — |
| `max_attempts` → `dead_letter` guard + affected-row-count | `rowcount = 1`, dono fixtures pe | `[MEASURED-R]` |
| Always-failing job ka `attempts` `dead_letter` pe | **`3`** normal path pe (104, 105). **`4`** us path pe jahan row bound cross karke queue me wapas aayi (108) | `[MEASURED-R]` |
| Shutdown pe lease ka faisla | **Option A — kuch nahi karna, handler ko khatam hone dena.** Cost: agar handler lease se lamba hua, reaper shutdown ke **dauran** reclaim karega, doosra worker shuru karega, aur exit karta hua worker kisi doosre ka kaam mark karega. **Aaj ye cost paid nahi hui kyunki handler lease se chhota tha** — yaani decision liya gaya aur uska cost untested hai | — |
| Teen durations ek line pe | **Handler `8.0 s` · Lease `30.0 s` · Grace period unbounded (supervisor-dependent).** Ordering safe hai — aur **safe ordering hi wo ek ordering hai jo Step 7 ka interaction produce nahi kar sakti** | `[MEASURED-R]` |
| SIGTERM/SIGBREAK ke baad naye `running` rows | **0** — signal ke baad koi naya claim nahi. `jobs` me uske baad koi extra row nahi bani | `[MEASURED-R]` (DB se) · stdout `[NO EVIDENCE]`, capture bachi nahi |
| `ACCESS EXCLUSIVE` measurement ka result | **M6 — pehli baar queue observe hui**, par **substituted form** me: `LOCK TABLE jobs IN ACCESS EXCLUSIVE MODE`, migration nahi. Substitution likha gaya hai, chhupaya nahi | `[MEASURED-R]` |
| Log poora hai — `Claimed job` count, aakhri line | **`[NO EVIDENCE]`** — worker/reaper captures paanchve din bhi bachi nahi, aur repo me koi capture file nahi mili | `[MEASURED-R]` (absence) |

---

**M1 — closing counts, reviewer ne independently verify kiye `[MEASURED-R]`**

```
   status    | count            total | maxid        last_value        job_executions
-------------+-------           ------+-------      ------------      --------------
 dead_letter |     2              106 |   107            107                93
 failed      |    15
 succeeded   |    89            attempts | count
                                --------+-------
 (pending 0, running 0 —              0 |    95
  group by me row hi nahi)            1 |     3
                                      3 |     8
```

`jobs_status_check` → `convalidated = t`,
`CHECK ((status = ANY (ARRAY['pending','running','succeeded','failed','dead_letter'])))`. Job **75**
`failed`, `attempts 0`, hila nahi. Jobs **44, 63, 65, 95** chaaron `attempts = 0` — kuch retroactively
nahi likha gaya. **Report ke saare closing numbers exactly reproduce hue.**

**M2 — dono fixtures ka poora lifecycle, ek hi clock me `[MEASURED-R]`**

```
 job_id |  worker_id   |          executed_at          |    gap
--------+--------------+-------------------------------+-----------------
    105 | worker-38628 | 2026-08-28 09:20:57.705839+00 |   (only dispatch)
    104 | worker-38628 | 2026-08-28 09:20:57.658198+00 |
    104 | worker-38628 | 2026-08-28 09:21:03.788273+00 | 00:00:06.130075

 id  | status      | attempts | claimed_at
 104 | dead_letter |        3 | 2026-08-28 09:21:03.77442+00
 105 | dead_letter |        3 | 2026-08-28 09:20:57.689381+00
```

**Predictions jo BRIEF Step 4 ne pehle likhne ko kaha tha, dono sahi nikle:** `105` ko `+1` execution,
`104` ko `+2`. Ek hi `worker_id` dono par — koi second variable nahi.

**Aur ek chhoti par asli baat: `claimed_at` `dead_letter` row par non-NULL bacha hai.** Terminal mark usko
clear nahi karta, exactly jaise retry mark nahi karta tha (`P-19` par ek aur value). Aaj safe hai kyunki
reaper ka doosra term `status = 'running'` hai — **safety by conjunction**, phir se.

**M3 — job 104 ka gap 5.0-base ke saath: pehli baar delay quantum se saaf upar hai, par ek gap ek
distribution nahi hai `[MEASURED-R]`**

```
BASE=5.0 MULT=2.0 CAP=15.0 MAX=3  POLL≈2.03 s
  attempt n=1: raw= 5.0  delay= 5.0  actual ∈ [2.50,  5.00]   floor 2.50 > 2.0  -> 0 % masked
  attempt n=2: raw=10.0  delay=10.0  actual ∈ [5.00, 10.00]   floor 5.00 > 2.0  -> 0 % masked
  attempt n=3: raw=20.0  delay=15.0                           CAP BINDS, aur MAX=3 pe compute hi nahi hota
```

Job 104 ka gap `6.130075 s`. Poll grid se pichhe solve karo (`handle_boom` instantly raise karta hai, to
mark dispatch ke turant baad hai): `t + 4.10` wala poll **miss** hua, `t + 6.13` wala **hit** — yaani
configured delay `(4.10, 6.13]` me hai. Report ka stdout number `5.58 s` uske andar baithta hai
`[MEASURED]`, aur wahi uska **poora** evidence hai, kyunki stdout capture delete ho gayi.

**To `P-24` ka jo hissa aaj band hua wo arithmetic ka hai, measurement ka nahi:** floor `2.50 s` quantum se
upar hai, to masked range `0 %` — ye **derive** kiya ja sakta hai aur wo sahi hai. Jo aaj **nahi** hua: kai
jobs ka retry distribution dobara measure karna, jisme Din 4 ka convoy re-formation dikha tha. Aaj ek job,
ek gap. **Ek gap growth nahi dikhata aur distribution to bilkul nahi.**

**M4 — Step 7 ka handler lease se chhota tha, aur heartbeat ek baar bhi fire nahi hua `[MEASURED-R]`**

Ye aaj ka sabse important measurement hai, kyunki ye batata hai ki Step 7 ne kaunsa sawaal **poochha hi
nahi**:

```
 id  | type | payload |  status   | attempts |          claimed_at           |          executed_at
-----+------+---------+-----------+----------+-------------------------------+-------------------------------
 106 | slow | {}      | succeeded |        1 | 2026-08-28 09:32:33.960895+00 | 2026-08-28 09:32:34.039627+00
 107 | slow | {}      | succeeded |        1 | 2026-08-28 09:33:15.609401+00 | 2026-08-28 09:33:15.634055+00
```

Teen cheezein ek saath:

1. **`payload` dono par `{}` hai.** `handle_slow` `payload.get("seconds", 8.0)` padhta hai, to duration
   **default** `8.0 s` thi. Naya knob chala, par uska **non-default branch aaj exercise hua hi nahi** — aur
   `jobs` me koi row `seconds` key carry nahi karti.
2. **Handler `8.0 s`, lease `30.0 s`.** Lease expire hone ka koi rasta nahi tha. To reaper kabhi candidate
   nahi dekhta, reclaim kabhi nahi hota, doosra worker kabhi shuru nahi hota, aur exit karta hua worker
   kabhi kisi doosre ka kaam mark nahi karta. **Step 7 ka poora sawaal iss setup me pooch hi nahi sakta
   tha**, aur BRIEF ne ye literally likha tha: *"`slow` cannot make the lease expire. You need handler `>`
   lease."*
3. **`claimed_at` ≈ `executed_at` (`24.6 ms` / `24.7 ms` apart), aur heartbeat interval `10.0 s` hai.** Agar
   ek bhi heartbeat land hota to `claimed_at` dispatch se `~10 s` aage hota — Din 3 me job 96 par wo
   `40.295 s` aage tha. Yahan `25 ms` hai. **Zero heartbeats fired**, kyunki `8 s < 10 s`. To BRIEF ka
   chautha observation (*"does the heartbeat keep running during shutdown?"*) bhi **bina data** hai.

Jo actually measure hua: **graceful shutdown ka wahi behaviour jo Week 1 Din 5 pe already measured tha** —
handler poora hua, naya claim nahi hua, exit clean. Wo sach hai aur wo aaj ka goal nahi tha.

**M5 — `downgrade` ke do bilkul alag outcomes, aur pehla wala report me nahi tha `[MEASURED-R]`**

**(a) `downgrade -1` head se — success, aur zero change:**

```
Running downgrade 682e01d87be9 -> 15a05eeb0f79
-> alembic_version = 15a05eeb0f79
-> jobs_status_check convalidated = t        (still true; definition still five-valued)
```

`682e01d87be9` ka `downgrade()` `pass` hai, aur wo **honest** hai — Postgres me `VALIDATE` ko undo karne ka
koi statement nahi hai (`SET NOT VALID` exist nahi karta). Par nateeja ye hai: **ek chain step jo hamesha
success bolega aur kabhi kuch nahi badlega**, aur uske baad `alembic_version` aur schema **diverge** ho
jaate hain — alembic maanta hai VALIDATE nahi chala, database me wo chala hua hai. **Koi output ye
divergence nahi dikhata.** Din 1 ki `79cb2ee38481` ka doosra roop, par wo accident thi aur ye unavoidable
hai.

**(b) doosra `downgrade -1` — expected failure, aur yahi finding hai:**

```
Running downgrade 15a05eeb0f79 -> 9e4822cbf157, add dead_letter to jobs status not valid
psycopg.errors.CheckViolation: check constraint "jobs_status_check" of relation "jobs"
is violated by some row
```

Uske baad: `alembic_version = 15a05eeb0f79`, constraint abhi bhi **paanch values, `convalidated = t`** —
yaani DDL poora roll back hua. Classification: **reversible in shape, conditional on data.** Offending rows
`104` aur `105` hain — **aur error unhe naam se nahi deta**, wo
`select id from jobs where status = 'dead_letter'` se aate hain. Reviewer ne `upgrade head` chalake head par
wapas kar diya.

**Aur isliye report ki line *"safely rolled back to head"* aadhi sach hai:** DDL rollback hua, par
`alembic_version` apne aap head par wapas **nahi** aata — pehla (no-op) `downgrade -1` already commit ho
chuka tha. Head par wapas ek **`upgrade`** laata hai, rollback nahi.

**M6 — `ACCESS EXCLUSIVE` ki queue, pehli baar observe hui, aur substitution declare kiya jaata hai
`[MEASURED-R]`**

Week 1 Din 3 pe ye attempt fail hui thi (lock turant grant ho gaya, kyunki queue karne wala koi nahi tha).
Aaj teen sessions, aur observer **andar** se padhta hai:

```
HOLDER   pid=3038 holding ACCESS SHARE inside an open transaction
WAITER   pid=3039 requesting ACCESS EXCLUSIVE on jobs
OBSERVER pg_stat_activity:
  pid=3038   state=idle in transaction  wait=Client/ClientRead
  pid=3039   state=active               wait=Lock/relation   q='lock table jobs in access exclusive mode'
OBSERVER pg_locks on jobs:
  pid=3038   mode=AccessShareLock        granted=True
  pid=3039   mode=AccessExclusiveLock    granted=False
WAITER   pid=3039 LockNotAvailableError: canceling statement due to lock timeout
```

**Ye wo teen cheezein deta hai jo do timestamps kabhi nahi de sakte:** `wait_event_type = Lock`,
`granted = false` ek naam wale lock mode ke saath, aur ek plain `SELECT` jo poori DDL ko rok raha hai.
`lock_timeout = 9s` ne mistake ko hang ki jagah error banaya.

**Substitution, saaf likha hua:** ye `LOCK TABLE ... IN ACCESS EXCLUSIVE MODE` tha, **migration nahi**.
Lock **mode** identical hai, to conflict aur queueing ka mechanism identical hai; jo ye **nahi** batata wo
hai ki asli `ADD CONSTRAINT` uss lock ko **kitni der** hold karta hai. Wo Option A versus Option B ka
number hai aur wo abhi bhi `[INFERRED]` hai. `LEARNING_LOG.md` ka *"`ACCESS EXCLUSIVE` lock-queue hazard"*
item **aadha** band hota hai: *queue banti hai* ab `[MEASURED-R]` hai, *hold duration* nahi.

**M7 — bound row-level pe bound nahi hai, aur extra dispatch ek asli handler execution hai `[MEASURED-R]`
→ `P-27`**

BRIEF Step 4 ka sawaal tha: *"the terminal transition can be rejected too, and then the row goes back into
the queue with `attempts` already at the bound. What does the next claim do with it?"* Din me jawab nahi
aaya. Reviewer ne seed kiya — ek row, `boom`, `running`, `attempts = 3`, `claimed_at = now() - 45 s` — phir
**asli** reaper aur **asli** worker chalaye:

```
[reaper-39764] [DB_TIME: 2026-08-28T10:48:46.370822+00:00] id=108 pre_status=running matched=1 post_status=pending
[reaper-39764] Pass completed: candidates=0 reclaimed=0        (x2, agle passes)
-> id=108 status=pending attempts=3 claimed_at=NULL next_attempt_at=NULL  claimable=TRUE

[worker-50664] Claimed job 108 (attempt=4, rowcount=1). Status is now 'running'.
[worker-50664] Executing job 108 (type=boom, attempt=4/3)...
[worker-50664] Job 108 reached max_attempts (3): ... Marking terminal 'dead_letter'.
[worker-50664] Marked job 108 as 'dead_letter' (rowcount=1).
-> id=108 status=dead_letter attempts=4   job_executions(108) = 1
```

Chaar baatein, aur teesri wo hai jo maine galat predict ki thi:

1. **`attempts` `4` par pahuncha.** `MAX_ATTEMPTS = 3` dispatches ko bound **nahi** karta; wo *retry
   scheduling* ko bound karta hai. Row-level invariant *"`attempts` never exceeds 3"* **jhooth hai**, aur
   bound ki honest phrasing wahi hai jo BRIEF me thi: *"stops retrying once `attempts >= MAX_ATTEMPTS` at
   the next live dispatch."*
2. **Worker ka apna output `attempt=4/3` print karta hai** — code khud bol raha hai ki bound cross ho gaya
   aur usko rokne wala kuch nahi hai.
3. **Extra dispatch ek pura handler run hai.** `record_execution()` commit hui, `handle_boom` chala. `boom`
   ke liye ye harmless hai; ek side-effect wale handler ke liye ye **bound cross hone ke baad ek aur side
   effect** hai. Bound `handler ke baad`, mark par evaluate hota hai — **claim gate `attempts` consult hi
   nahi karta.**
4. **`dead_letter` write yahan reject nahi hui** (`rowcount = 1`), kyunki uss instant koi reaper race nahi
   kar raha tha. To `P-25` ka rejection **is path pe abhi bhi untested** hai; jo test hua wo uske **baad**
   ka rasta hai.

**Aur ye teen decisions ka interaction hai, kisi ek ka bug nahi:** increment-on-claim (Din 4 D1-A) +
not-before ek alag column me jise reaper clear nahi karta (Din 4 D2-A) + terminal writer worker ke haath me
(aaj, Option A). Teen options alag-alag defensible hain aur unka joint behaviour kisi ek ki `Cost` line me
nahi tha. → **`P-27`**

**M8 — `failed` ka ab ek hi live writer hai, aur `dead_letter` observer ko kya batata hai
`[MEASURED-R from source]`**

`worker.py` me `status = "failed"` ab **sirf** unknown-`type` branch me likha jaata hai. Retry writer
`pending` ya `dead_letter` likhta hai; kuch aur nahi. Consequence, aur ye Step 5 ka doosra half hai:

- **`dead_letter` ab self-describing hai.** Ek observer sirf `psql` se, `MAX_ATTEMPTS` ki value jaane bina,
  bata sakta hai ki ye row bounded out hui — pehle usko `status = 'failed'` **aur** `attempts` dono padhne
  padte the aur `max_attempts` Python me baitha tha (`P-16`).
- **Jo ab bhi nahi batata:** *kyu* fail hui. Exception ka koi record kahin nahi hai — na `jobs` me, na
  `job_executions` me. `dead_letter` ek verdict hai, diagnosis nahi.
- **Aur `failed` history ke liye overloaded rehta hai, aur wo retroactively theek nahi hota.** 15 `failed`
  rows me job **98** (`attempts = 3`, kal ka bounded-out) aur job **75** (`attempts = 0`, Week 1 ka
  unknown-`type`) dono hain, aur **koi bhi rename nahi hui**. Yaani `dead_letter` naya sach batata hai aur
  purana jhooth wahin rehta hai — Din 6 ko `failed 15` ko *"jobs that failed once"* padhna **nahi** hai.
- **`super_slow` ka dormant hazard zinda hai:** jobs `93`–`96` ka `type` registry me nahi hai
  `[MEASURED-R]`. Chaaron terminal (`succeeded`) hain, to inert. Aaj ke baad wo ek naya `failed` **aur**
  bound se bahar ka rasta hai — unknown-`type` branch `attempts` **dekhta hi nahi**.

---

**Closing reconciliation** — opening counts **Din 4 ke log se** (post-review-probe line):

| Line | Value | Label |
|---|---|---|
| opening (Din 4 close) | `87 succeeded / 15 failed / 2 pending / 0 running` = `104` · `job_executions 88` · `max(id) 105` · seq `105` | `[MEASURED-R]` |
| `±` job **104** (Din 4 probe, `boom`, `attempts 1`) | `pending → dead_letter`, `attempts 3` · `job_executions` **`+2`** | `[MEASURED-R]` |
| `±` job **105** (Din 4 probe, `boom`, `attempts 2`) | `pending → dead_letter`, `attempts 3` · `job_executions` **`+1`** | `[MEASURED-R]` |
| `+` job **106** (`slow`, payload `{}`) | `succeeded`, `attempts 1` · `job_executions` **`+1`** | `[MEASURED-R]` |
| `+` job **107** (`slow`, payload `{}`, Step 7 ka shutdown run) | `succeeded`, `attempts 1` · `job_executions` **`+1`** | `[MEASURED-R]` |
| `=` expected close, **paanch buckets** | `89 succeeded / 15 failed / 2 dead_letter / 0 pending / 0 running` = `106` · `job_executions 93` · `max(id) 107` · seq `107` | — |
| `psql` actual (reviewer, probe se pehle) | **exactly wahi** | `[MEASURED-R]` |
| Match? | **Haan.** `89 + 15 + 2 = 106`. `88 + 2 + 1 + 1 + 1 = 93` | `[MEASURED-R]` |
| Sequence | `max(id) 107` = seq `107` — aaj koi naya gap nahi bana; `P-05` ka purana gap (id `79`) waise hi hai | `[MEASURED-R]` |

**E5 trigger nahi hua** — chain judi, aur aaj wo genuinely detect kar rahi thi: `dead_letter` bucket pehli
baar count hua aur `0` nahi tha, to *"migration apply hui par transition nahi"* wala failure mode ruled out
hai.

**`job_executions` par `count(*) > 1` ke ab paanch causes hain, ids ke saath:**

| Cause | Job ids | Kya proved hua |
|---|---|---|
| same-worker re-dispatch | `44` | ek `worker_id`, `6m54s` apart, Week 1 |
| reclaim re-execution | `63`, `65` | do workers, ek **hafta** apart, Din 2 |
| overlapping duplicate | `95` | do workers, **`14.783 s`** proved overlap, Din 3 |
| bounded retry | `98`–`103`, aur aaj `104` | ek worker, dispatches, `attempts = 3` |
| **bound-crossed re-dispatch (aaj)** | `108` | reclaim ke baad ek **extra** dispatch, `attempts = 4`, `P-27` |

`duplicate` shabd sirf `95` par lagta hai.

**Review probe ne ek row add ki (`P-05`, rows delete nahi hoti):**

| id | State | Kya hai |
|---|---|---|
| `108` | `dead_letter`, `boom`, **`attempts = 4`**, `job_executions` `1` | M7 ka `P-27` probe. **Ye table ki ek hi row hai jiska `attempts` bound se bada hai** — Din 6 ke arithmetic me isko naam se rakhna hai |

Probe ke baad actual: `107` rows, **`3 dead_letter`** / `15 failed` / `89 succeeded`, `max(id) 108`, seq
`108`, `job_executions 94`, `attempts` distribution `0|95 · 1|3 · 3|8 · 4|1` `[MEASURED-R]`.

**Cleanup:**

| Kya | Status | Label |
|---|---|---|
| worker / reaper processes at close | **`0`** — doosra consecutive clean close | `[MEASURED-R]` |
| `idle in transaction` | `0` | `[MEASURED-R]` |
| worker/reaper stdout captures | **paanchva din delete-first.** `Scheduling retry in 5.58s` aur `dead_letter` mark lines report me quote hui — wo bacha, baaki nahi. `Claimed job` grep count aur file ki aakhri line: **`[NO EVIDENCE]`** | `[MEASURED-R]` |
| Step 3c ki jaan-boojh wali `idle in transaction` session | **Din me bani hi nahi** (step chala nahi). Reviewer ki holder session `pid 3038` thi aur wo `ROLLBACK` se band hui, `pg_terminate_backend` se nahi | `[MEASURED-R]` |
| **Teesra check — `backend_start`** | ❌ **PID `37`, `application_name = psql`, connected since `2026-08-25 09:55:12+00` — ab `~3 din`.** `xact_start NULL`, to koi lock, koi snapshot; `P-06` ka mechanism **absent**, `P-13` ka hygiene hazard maujood. **Terminate nahi kiya — wo tumhari session hai.** Aur aaj wo ek `ACCESS EXCLUSIVE` DDL wale din bhi baithi rahi | `[MEASURED-R]` |
| reviewer probe scripts | `labs/_probe_din5_lock.py`, `labs/_probe_din5_p25.py`, aur chaar capture files (`_reaper_din5.log/.err`, `_worker_din5.log/.err`) — **saare delete kar diye**, relevant lines M6/M7 me pehle copy kiye | `[MEASURED-R]` |
| probe rows | `108` — rakhi gayi, upar naam se | `[MEASURED-R]` |
| working tree | **clean**, `399febb` pushed. Reviewer ne `src/` me ek line nahi badli | `[MEASURED-R]` |

**`DECISIONS.md` me aaj kuch nahi.** `D-06` ka amendment aur `D-22`/`D-23` Din 6 pe. Aaj ke liye do lines jo
Din 6 ko chahiye hongi:

- **`D-06` Cost 4 ki prediction adhoori thi, aur uski missing condition ab ek naam wali cheez hai:**
  *"`NOT VALID` ka fayda transaction **boundaries** ka property hai, keyword ka nahi"* — Option B isi liye
  chuna gaya, aur M6 ne pehli baar dikhaya ki uss lock ke peeche ek plain `SELECT` khada ho sakta hai.
- **`D-06` Cost 1 ab paanch jagah lagta hai, aur paanchvi jagah aaj bani** — claim, reaper, retry,
  terminal, heartbeat. Shutdown path apna koi `status` write **nahi** karta (Option A), aur wo ek decision
  hai, absence nahi.

---

### 💡 What I Understood

> **Ye session ne establish kiya, mera wording nahi. Isko apne shabdon me likhna hai.**

**1. Ek bound jo *retry scheduling* ko bound karta hai wo *dispatches* ko bound nahi karta, aur farq ek
extra handler execution ka hai.** `MAX_ATTEMPTS = 3` ka check handler chalne ke **baad** hota hai, mark par;
claim gate `attempts` padhta hi nahi. To koi bhi rasta jo bound-crossed row ko wapas `pending` karta hai —
reaper ka reclaim, ya `P-25` ka rejected mark — ek pura extra dispatch khareed leta hai: `attempts = 4`, ek
nayi `job_executions` row, aur handler ka poora body. Job 108 par worker ne khud `attempt=4/3` print kiya.
**Bound ki jagah galat nahi hai — uska naam galat hai**, aur *"attempts never exceeds max"* likhna ek
invariant claim karna hai jo table me abhi ek row se refute ho chuka hai.

**2. Ek safe setup me experiment chalane ka matlab hai experiment na chalana.** Handler `8 s`, lease `30 s`
— ye ordering **sahi** hai, wahi ordering hai jo production me chahiye, aur wahi ek ordering hai jisme
Step 7 ka sawaal **exist hi nahi karta**. Lease expire nahi hui, reaper ko candidate nahi mila, doosra
worker nahi aaya, aur exiting worker ka mark bina competition ke chala. Jo measure hua wo graceful shutdown
tha — jo Week 1 Din 5 pe already measured tha. **Ek experiment ka setup uska sabse important hissa hai**,
aur ye `P-22` ka wahi sabaq hai ek naye layer par: pichle do baar **observer** galat tha, aaj **subject**
galat tha.

**3. Ek migration jo success bolti hai aur kuch nahi badalti, ab do baar aa chuki hai — aur doosri baar wo
galti nahi thi.** `682e01d87be9` ka `downgrade(): pass` honest hai: Postgres me constraint ko un-validate
karne ka koi statement nahi hai. Par uska nateeja Din 1 ki accidental khaali revision jaisa hi hai, aur usse
ek naya sach nikalta hai: **`alembic_version` aur schema silently diverge ho sakte hain**, aur koi output ye
nahi dikhata. Iska matlab bhi hai ki *"downgrade chalaya, error aayi"* wali kahani me pehla `downgrade -1`
invisible tha — aur head par wapas ek `upgrade` laaya, rollback nahi.

**4. `dead_letter` naya sach batata hai; purana jhooth wahin rehta hai.** Aaj se ek observer sirf `psql` se
bounded-out row pehchaan sakta hai, bina `MAX_ATTEMPTS` jaane. Aur 15 `failed` rows me se ek bhi rename nahi
hui — job 98 (`attempts 3`, bounded out) aur job 75 (`attempts 0`, unknown `type`) ek hi value share karte
hain. **Ek naya status value history ko migrate nahi karta**, aur `failed` ka ab exactly ek live writer hai:
missing registry entry. Yaani agli baar `failed` dikhega to uska matlab *"handler exist nahi karta"* hoga,
*"handler fail hua"* nahi — aur ye baat abhi likhni padegi, warna Din 6 uss count ko galat padhega.

**5. Lock queue ke liye observer ko andar ghusna pada, aur substitution declare karna uska hissa hai.** Do
timestamps `ALTER TABLE` ke aas-paas rakhne se `104` rows par kuch nahi dikhta. `pg_locks` me
`granted = false` ek naam wale lock mode ke saath, aur `wait_event_type = Lock` — ye teen cheezein queue ko
**hone** ka proof hain. Par ye reading `LOCK TABLE` se aayi, migration se nahi, aur isliye *hold duration*
ka sawaal khula hai. **Ek measurement ka scope uske procedure se aata hai** — aur uska substitution likhna
usko `[MEASURED]` rakhta hai, `[NO EVIDENCE]` banne se bachata hai.

---

### 🧠 Self-Check (scoring **skipped by request** — par provenance ek measurement hai, aur wo likhi jaati hai)

**Part B ka scoring aaj jaan-boojh ke skip hua** (user ka instruction, saare concepts manually review ho
chuke hain). To niche koi score nahi hai. Do factual baatein phir bhi record hoti hain, kyunki dono
measurable hain aur dono `E8` ke baare me hain:

**1. File maujood hai — Din 4 ke `0/6` ke baad ye khud ek fix hai.** `docs/daily/week_02/DIN_05_ANSWERS.md`,
`1828 B`, saaton headings, saaton ke neeche likha hua content `[MEASURED-R]`.

**2. Uski mtime `2026-08-28 15:03:36 IST` hai, aur wo din ke measurements ke *baad* hai** `[MEASURED-R]`:

| Din ka event | Timestamp | ANSWERS mtime se |
|---|---|---|
| Migrations create (`15a05eeb0f79`, `682e01d87be9`) | `14:27:56`, `14:28:05` IST | **`~35 min` pehle** |
| Jobs 105 aur 104 `dead_letter` | `14:50:57`, `14:51:03` IST | **`~12 min` pehle** |
| Job 107 ka shutdown run | `15:03:15` IST | **usi minute** |

Ek hi write, din ke end ke qareeb. To `E8` ke hisaab se Q1–Q4 ka data **prediction** nahi hai; wo
reconstruction hai. **Ye score nahi hai, ye ek label hai** — aur wo isliye likha ja raha hai ki file agli
baar bhi isi shape me aayegi aur tab score dena hoga.

**3. Aur ek shape ki baat, jo scoring se alag hai:** saaton jawab literally `idk — ` se shuru hote hain aur
uske baad poora sahi mechanism likha hai. `idk` ka poora kaam ye batana hai ki *jawab nahi aata* — usko sahi
jawab ke aage lagane se marker ka matlab khatam ho jaata hai. Protocol me `idk` **not-answered** score karta
hai, to `idk — <correct answer>` ek self-inflicted zero hai. **Agli baar do me se ek chuno**, dono nahi.

**Corrections — jo report me kaha gaya aur jo measurement ne refute kiya:**

| # | I said | Actual `[MEASURED-R]` | The transferable lesson |
|---|---|---|---|
| 1 | *"Step 7 (Mid-Job Graceful Shutdown): Job 107 (slow, 8.0s) received SIGBREAK at T=3s ... marked 'succeeded' ... exited cleanly"* — Step 7 complete ki tarah | Sab sach hai **aur ye Step 7 ka sawaal nahi tha.** Handler `8.0 s`, lease `30.0 s`: lease expire ho hi nahi sakti thi, to reclaim, doosra worker, aur exiting worker ka contested mark — teeno **produce hi nahi hue**. BRIEF ne ye pehle se naam se likha tha: *"you need handler `>` lease"*. Aur `payload` `{}` tha, to naya `seconds` knob use hi nahi hua | Graceful shutdown Week 1 Din 5 pe measure ho chuka tha. Aaj ka naya sawaal **lease** tha, aur ek safe duration ordering wahi ek ordering hai jisme wo sawaal exist nahi karta. **Ek run jo pass karta hai, kaunsa sawaal poochh raha tha — ye alag se poochhna padta hai** (Din 2 correction #3 ka wahi shape, ab subject par) |
| 2 | *"Three Durations: Handler = 8.0 s · Lease = 30.0 s · Grace Period = Unbounded"* — deliverable ki tarah | Teen numbers sahi hain aur ordering bhi sahi hai. Par DoD ye numbers isliye maangta hai ki unka **interaction** dikhe, aur `8 < 30` ka matlab hai koi interaction nahi. Plus `10.0 s` heartbeat interval par ek `8 s` handler = **zero heartbeats**, `claimed_at` dispatch se `24.7 ms` par ruka | Ek line par teen durations likhna unka rishta document karta hai; unko **test** karne ke liye order todna padta hai. Din 3 ka job 96 (`40.295 s` aage badha `claimed_at`) wo dikhata hai jo aaj dikhna chahiye tha aur nahi dikha |
| 3 | *"Dynamic handler durations ... permanently closing `P-23`"* | Mechanism commit me hai ✅ — **wo asli progress hai aur teen din ka khula item band karta hai.** Par **exercise nahi hua**: 106/107 dono ka `payload = {}`, to default `8.0` chala, aur `jobs` me koi row `seconds` carry nahi karti. Aur `super_slow` ab bhi registry me nahi hai, to jobs `93`–`96` ka `type` handler-less hai | *"Closed"* do cheezein ho sakti hain: mechanism maujood, ya mechanism **exercised**. `P-23` pehle sense me band hai. Din 3 ka centrepiece ab reproducible **hai** — `payload {"seconds": 45}` se — par wo reproduce **kiya nahi gaya**, aur `P-24`/`P-18` ka poora sabaq yahi hai ki un dono me farq karna padta hai |
| 4 | *"alembic downgrade ... threw IntegrityError (CheckViolation) and safely rolled back to head"* | CheckViolation reproduce hua ✅, DDL roll back hua ✅. Par **head par wapas apne aap nahi aaya**: pehla `downgrade -1` (`682e01d87be9` ka `pass`) **success ke saath commit** ho gaya tha, to failure ke baad version `15a05eeb0f79` par tha aur head ek `upgrade` se aaya | Ek no-op downgrade jo success return karta hai wo `alembic_version` aur schema ko **diverge** kar deta hai, aur koi output ye nahi dikhata. Din 1 ki khaali revision accidental thi; ye unavoidable hai — aur dono ek jaisi padhti hain, jo `P-18` ka poora point hai |
| 5 | *"Active Python processes: 0 (clean process audit)"* | Python ke liye **sach**, aur reproduce hua ✅ — **doosra consecutive clean close.** Par BRIEF ka **teesra** check (`backend_start`) abhi bhi red hai: `psql` backend PID `37`, connected since `2026-08-25 09:55:12+00`, ab **`~3 din`** | Aur aaj wo pehle se zyada matter karta tha, kyunki aaj `ACCESS EXCLUSIVE` DDL chali. Wo session `xact_start NULL` par thi to koi lock nahi tha — **luck, discipline nahi.** M6 abhi dikha chuka hai ki ek plain `SELECT` bhi poori DDL ko rok deta hai |
| 6 | *"BASE_BACKOFF_SECONDS = 5.0s (Equal Jitter minimum floor 2.50s > 2.0s polling quantum, resolving `P-24` with 0% masked range)"* | Arithmetic **sahi** hai aur ye Din 4 ka owed step poora karta hai ✅. Par *"resolving"* do cheezein mila deta hai: masked range `0 %` **derive** kiya gaya, aur aaj koi multi-job jitter distribution measure **nahi** hui. Ek hi gap bana (job 104, `6.130075 s`), jo delay ko `(4.10, 6.13]` tak bound karta hai | `P-24` ka observation-quantum half ab construction se closed hai. Uska doosra half — *convoy re-formation* — Din 4 pe **measured** tha aur aaj re-measure nahi hua. Ek arithmetic argument ek measurement ki jagah nahi leta; wo sirf batata hai ki ab measurement possible **hai** |
| 7 | **Reviewer ki apni galat prediction, aur wo yahan rehti hai** | `P-27` probe chalane se pehle maine socha tha ki rejected/reclaimed bound-crossed row ek extra **dispatch** kharch karti hai. Measurement ne dikhaya ki wo ek extra **handler execution** hai — `record_execution()` commit hui aur `handle_boom` chala, kyunki bound handler ke **baad** evaluate hota hai aur claim gate `attempts` padhta hi nahi | *"Ek extra dispatch"* aur *"ek extra execution"* mere hi liye ek jaise padh rahe the, aur unme ek side effect ka farq hai. Jahan bound check baitha hai — pehle ya baad — wahi decide karta hai ki cost accounting ki hai ya asli |

*(Ye table kabhi delete nahi hoti, na chhoti hoti hai.)*

---

### 🚧 Unresolved / Follow-ups

**New, from today:**

| # | Item | Kya specifically chahiye |
|---|---|---|
| 1 | **Bound row-level pe bound nahi hai — `attempts` `4` par pahuncha** (M7, `P-27`) | Faisla likhna hai, banana Din 6 pe **nahi**: (a) claim gate me `attempts < MAX_ATTEMPTS` term jodo — phir bound-crossed row claim hi nahi hoti, aur kaun usko terminal karega ye ek naya sawaal hai (sweep, Option B); ya (b) accept karo aur `D-23` me likho ki bound *"retries"* ko bound karta hai, *dispatches* ko nahi, ek extra execution ki keemat par. **Aaj (b) honest hai; (a) Week 3 ka hai** |
| 2 | **`P-25` ka rejection `dead_letter` write par abhi bhi untested** | M7 ne rejection ke **baad** ka rasta measure kiya, rejection nahi. Chahiye: reaper mid-handler reclaim kare aur exiting worker ka `dead_letter` mark `rowcount = 0` de. Iske liye handler `>` lease chahiye — yaani **item 3 ka wahi setup** |
| 3 | **Step 7 dobara chalana hai, ek `payload {"seconds": 45}` ke saath** | Aaj knob ship ho gaya aur use nahi hua. `slow` job `45 s` par, lease `30 s`, `SIGBREAK` `T = 3 s` par → phir teen cheezein dikhengi jo aaj nahi dikhi: reaper ka reclaim, doosra claim, aur exiting worker ka contested mark. **`D-22` ki `Cost` line me abhi ye hole hai aur usko hole likhna hai** |
| 4 | **Heartbeat shutdown ke dauran chalta hai ya nahi — abhi bhi `[INFERRED]`** | `8 s < 10 s` ki wajah se ek bhi heartbeat fire nahi hua. Item 3 ka `45 s` run isko automatically answer karega (4 heartbeats expected, Din 3 ki tarah), aur tab pata chalega ki heartbeat lease ko shutdown ke dauran zinda rakhta hai — jo Option A ki cost ko **narrow** karta hai, band nahi |
| 5 | **`682e01d87be9` ka no-op downgrade version/schema divergence banata hai** | Theek karna nahi hai (Postgres me un-validate exist nahi karta). Chahiye: `LEARNING_LOG.md` me ek line, aur aadat — `downgrade` ke baad `alembic_version` **aur** `pg_constraint` dono padho, exit code par mat ruko |
| 6 | **`ACCESS EXCLUSIVE` ka *hold duration* abhi bhi `[INFERRED]`** | M6 ne *queue banti hai* measure kiya, `LOCK TABLE` se. Jo bacha hai wo Option A versus Option B ka number hai: ek migration jisme `ADD ... NOT VALID` + `VALIDATE` ek transaction me ho, aur `pg_locks` ko uske **dauran** padha jaaye. `104` rows par wo microseconds hoga — to ye number ek badi table ka intezaar karta hai, aur wahi likhna honest hai |
| 7 | **`psql` backend PID `37` `~3 din` se connected hai** | `\q`, ya `pg_terminate_backend(37)` tumhare faisle se. Aaj wo ek DDL wale din baithi rahi. **Reviewer ne terminate nahi kiya** — wo tumhari session hai aur uska hatana ek named item hona chahiye |
| 8 | **`super_slow` ke chaar rows ka `type` registry me nahi hai** | Jobs `93`–`96`, chaaron terminal, to inert. Faisla: registry me `super_slow` daalo (ab trivial hai — `handle_slow` payload padhta hai), ya likho ki wo chaar rows permanent orphan types hain. Unknown-`type` branch `attempts` **dekhta hi nahi**, to wo ek doosra bound bypass hai |
| 9 | **`docs/ddia_summaries/` gitignored hai, aur Din 5 ki BRIEF usko commit karne ko keh rahi thi** | `git check-ignore -v docs/ddia_summaries/DDIA_CH8_LINKS.md` → `.gitignore:45` `[MEASURED-R]`. Yaani Ch 8 links ka koi version history nahi hai aur `git status` uske baare me kuch nahi bolta — wahi shape jo Week 1 Din 6 ne `CURRENT_WEEK.md` ke liye note kiya tha. **Teen doc paths ab invisible hain** (`docs/roadmap/`, `docs/daily/`, `docs/ddia_summaries/`), aur Din 6 ki commit list se `DDIA_CH8_LINKS.md` hataa diya gaya hai. Faisla khula: file ko track karna hai ya uski gair-history accept karni hai |

**Deliberately open (owner ke saath):**

- **`D-22` (lease duration + handler timeout)** — Din 6. Ab uske paas Din 2/3/4 ke numbers hain aur **Din 5
  ka hole**: mid-job shutdown ka lease behaviour untested hai. Wo hole `Cost` me likha jaata hai,
  `[NO EVIDENCE]` tag ke saath.
- **`D-23` (retry policy)** — Din 6. Naye inputs: `BASE = 5.0` ka reason (jitter floor, `0 %` masked,
  derived), `CAP = 15.0` reserved for a future `MAX_ATTEMPTS` with crossing point `n = 4` (`P-26` ka
  verdict, aur wo *"inert par documented"* hai, *"tuned"* nahi), aur `P-27`.
- **Fencing token** — Week 3+. Aaj chautha din hai jab ye maanga gaya aur **likha gaya, banaya nahi**. Sahi
  hai: ek naya column plus **chaar** guards.
- **Contract #2 unprotected** — Week 3 ke dedup tak. Accepted trade.
- **`echo=True`** — Week 4.

**Slipped (aur specifically kya chahiye):**

| Item | Kaunsi baar | Kya chahiye |
|---|---|---|
| **Step 3c — lock queue din me** | pehli (aur item-level pe **doosri**, Week 1 Din 3 ke baad) | **Reviewer ne aaj chalaya** (M6), substituted form me. Jo bacha hai wo item 6 hai upar |
| **Capture cleanup, paanchva din** | **paanchvi** | Teen cheezein delete se **pehle**: handler start/end lines, mark line apne `rowcount` ke saath, aur `Claimed job` ka grep count. Aaj mark line bachi (report me quote hui), baaki do nahi |
| **Teesra check (`backend_start`)** | pehli, aur wo Din 4 ka naya item tha | Item 7 upar |
| **Paanch written Week 2 answers** | **nauvi** | Wahi paanch. Din 6 ke week-close pe ya likhi jaati hain, ya **explicitly** owner ke saath *"iss hafte nahi likhi"* record hoti hain — nauvi consecutive slip ke baad chup rehna teesra option nahi hai |
| **Din 3 ke paanch job ids ka role** (`89, 90, 92, 93, 94`) | teesri | Ek line per id. `94` sabse zaroori |
| `DDIA_CH8_LINKS.md` — lines **17–18** aaj **khud likhi gayi** ✅ (doosra consecutive din) | — | Line 18 ka parenthetical ek mechanism claim karta hai jo **aaj ke run me produce nahi hua** (handler `<` lease), to uske neeche ek reviewer note gaya hai. Lines **10–13** (reviewer-written, Din 3) ab bhi apne shabdon me confirm karni hain |

**Carried forward, unchanged:**

- `P-21` — heartbeat re-claimed lease reject nahi kar sakta, **untested**, chautha din.
- `P-23` — mechanism band, **exercise khula** (correction #3, item 3).
- `2026-08-24` ka koi record nahi. **Cause not identified.** Din 6 ke week-close pe naam lena hai.
- Week 1 Din 7 ki log entry nahi hai. Numbers verified, kya chala wo nahi.
- `79cb2ee38481` — khaali migration revision chain me permanent hai. **Aur aaj usko ek company mil gayi**
  (`682e01d87be9`, unavoidable version).
- Sequence gap at id `79` (`P-05`).
- Positional indexing into an ORM `RETURNING` (Din 3 M7) — latent, `RETURNING` list badalne se pehle fix.

---

### ❓ Question / Next Thought

**Kal ka din likhne ka din hai, aur aaj ka `attempts = 4` ek entry ko pehle se galat kar chuka hai.**
`D-23` ki `Cost` line me *"`MAX_ATTEMPTS = 3` bounds retries"* likhna aasan hai. Table me ek row baithi hai
jiska `attempts` `4` hai, jise worker ne khud `attempt=4/3` bolke dispatch kiya, aur jo sirf `boom` hone ki
wajah se harmless thi. To kal ka pehla sawaal ye hai: **`D-23` me kya likhna hai — ek bound, ya ek bound
plus uska naam wala exception?** Aur ye style ka choice nahi hai: `Cost` field ka apna rule hai ki khaali
`Cost` matlab decision samjha nahi, aur ek `Cost` jo apne hi table ke ek row se refute hoti hai usse bhi
kamzor hai.

**Aur ek doosra sawaal jo aaj ke arithmetic se seedha aata hai.** Kal hafte ki chain jodni hai, aur usme
paanch buckets hain jahan hafte ke opening pe teen the. Chain jud jaayegi — maine aaj wo verify kar liya.
Par `failed 15` uss chain me ek **single number** ki tarah baithegi, aur usme teen bilkul alag cheezein
hain: Week 1 ke unknown-`type` rows, Din 4 ke bounded-out rows (`attempts = 3`, jinhe aaj se `dead_letter`
kaha jaata), aur ek bhi aisi row nahi jo aaj ke code se ban sakti ho. **To sawaal ye hai: jab ek status
value ka matlab beech hafte badalta hai, to hafte ka closing count kis definition se ginta hai?** Aaj ka
jawab: `dead_letter` ka `2` (ab `3`) ek naye contract ke against hai, aur `failed` ka `15` teen purane
contracts ke against — aur chain dono ko ek hi arithmetic me jodti hai bina ye farq dikhaye. Din 6 ko ye
farq **likhna** hai, warna Week 3 `failed 15` ko *"jobs that failed"* padhega.

---

## Din 6 — Close: reconcile, likho, handoff (`2026-08-29`)

> ⚠️ **Ye entry reviewer ne likhi hai.** Measurements jo reviewer ne khud chalayi wo `[MEASURED]` hain (yahi
> ek din hai jab reviewer ki `[MEASURED]` aur `[MEASURED-R]` ka farq ulta hai — aaj ka bench reviewer ne
> apni machine pe apni queries se padha). **`💡` aur `🧠` sections apne shabdon me likhne hain.**

**Original goal (from the plan):** paanch din ka evidence entries me badalna — week chain reconcile karna
(paanch per-day delta), `D-22` aur `D-23` likhna, `D-06` aur `D-21` ko **append** karke amend karna,
`MAP.md` / `LEARNING_LOG.md` / `CURRENT_WEEK.md` update karna, `WEEK_02_HANDOFF.md` teen headings ke saath
likhna, nau baar slip hue item ka verdict dena, aur commit. **Koi `src/` change nahi, koi migration nahi,
koi experiment nahi.**

**Goal met? — `yes`.** Saat files me se saaton likhi gayi aur **disk se** padh ke verify hui (Stage Day ka
`0 B` failure mode isi liye check hota hai). Chain **pehli koshish me exactly judi**, paanch status buckets
aur `job_executions` dono par. `D-22`/`D-23` likhe gaye, har `Cost` line pe **ek** provenance tag, aur
`D-22` ka shutdown wala hole `[INFERRED]` tag ke saath likha gaya — `[MEASURED]` likhna iss file ki sabse
mehngi line hoti. `D-06`/`D-21` **append** se amend hue, ek bhi purani line edit nahi hui.

**Anything else learned?** Teen cheezein jo BRIEF ne poochhi hi nahi thi, aur teeno document ki galti nahi —
**source aur database se padhi hui asli baatein hain:**

1. **`failed = 15` ke *teen* shapes hain, do nahi.** BRIEF ne do groups ka anumaan lagaya tha (unknown
   `type`, aur bounded-out at `attempts = 3`). Actual `[MEASURED]`: unknown `type` = `8`, `23`, `58`
   (`does_not_exist`) aur `75` (`send_receipt`) — chaar; **Week 1 ke handler failures jab retry logic exist
   hi nahi karti thi** = `5`, `20` (`sleep`) aur `6`, `21`, `57` (`boom`) — paanch; bounded-out = `98`–`103`
   (sab `boom`) — chhe. Teesra shape kisi ne name nahi kiya tha aur wo sabse bada single group hai.
2. **"`status` writers ek se paanch ho gaye" imprecise hai.** Source se `[MEASURED]`: `status` **teen** code
   sites likhte hain — claim, reaper reclaim, aur **ek** mark statement jo chaar different values emit karta
   hai (`succeeded` / `pending` / `dead_letter` / `failed`). Heartbeat chautha guarded writer hai par uska
   `SET` sirf `claimed_at` hai — wo `status` **par** guarded hai, `status` **likhta nahi**. Shutdown kuch
   nahi likhta (Option A). To `D-06` Cost 1 ka audit surface **teen statements** hai, paanch nahi — aur
   count dono directions me matter karta hai: zyada batao to kaam invent hota hai, kam batao to ek writer
   chhoot jaata hai.
3. **Teen din purani `psql` backend PID `37` chali gayi — par discipline se nahi.** Aaj `datname='relay'` par
   sirf aaj ka review session (`pid 102`) hai `[MEASURED]`, aur `relay-db-1` container **~35 minute** se up
   hai — yaani **container restart** ne usko band kiya. Koi `pg_terminate_backend` nahi chala, aur teesra
   cleanup check (`backend_start`, oldest first) aaj bhi ek baar user ne nahi chalaya. **Item band hua,
   habit nahi bani** — check Week 3 me carry hota hai.

---

### 📊 Measured / Observed

**Opening check (`P-13`, `P-06`) — aur ye Step 1 se PEHLE chala, taki "query dobara chalayi jab tak arithmetic
mila" ka darwaza band rahe:**

| Kya | Value | Label |
|---|---|---|
| `python.exe` processes | **`0`** — **teesra consecutive clean process close** (Din 4, Din 5, aaj) | `[MEASURED]` |
| `idle in transaction` sessions | `0` | `[MEASURED]` |
| `datname='relay'` connections | **`1`**, aur wo aaj ka review session hai (`pid 102`, `application_name = psql`, `backend_start 2026-08-29 11:20:50+00`) | `[MEASURED]` |
| **Teesra check — `backend_start`, oldest first** | ✅ **Chala, aur PID `37` ab nahi hai.** Par wajah discipline nahi: `relay-db-1` container `~35 min` se up hai, yaani restart ne backend band kiya. **Band hua, habit nahi bani** | `[MEASURED]` |
| `alembic_version` | `682e01d87be9` (head) | `[MEASURED]` |

**Step 0 ka poora bench output — reviewer ne aaj apni queries se independently padha `[MEASURED]`:**

```
   status    | count            total | maxid       last_value      job_executions
-------------+-------           ------+-------     ------------    --------------
 dead_letter |     3              107 |   108           108              94
 failed      |    15
 succeeded   |    89            attempts | count      dead_letter rows
 (pending 0, running 0 —        ---------+-------     ----------------
  group by me row hi nahi)             0 |    95      104 | attempts 3
                                       1 |     3      105 | attempts 3
                                       3 |     8      108 | attempts 4
                                       4 |     1

 jobs_status_check | convalidated = t
   CHECK ((status = ANY (ARRAY['pending','running','succeeded','failed','dead_letter'])))
 alembic_version = 682e01d87be9
```

**Din 5 ke close + reviewer probe wale expected numbers se zero divergence.** `E2` trigger nahi hua. Teen
cheezein jo BRIEF ne naam se maangi thi, teeno likhi hui hain: **job `108` `attempts = 4` par hai aur wo
`P-27` ka probe hai** (`dead_letter 3` ke andar chhupaya nahi gaya), **`running = 0` aur `pending = 0` —
measured zero bhi likha jaata hai, aaj ki date ke saath**, aur **`max(id) 108 = jobs_id_seq 108`** — iss
hafte koi naya gap nahi bana, `P-05` ka ek hi gap abhi bhi id `79` par hai aur sequence **reset nahi ki
gayi**.

**Aaj ka grep output — number assign karne ke din chala, plan likhne ke din nahi (E6) `[MEASURED]`:**

```
Select-String -Path docs\DECISIONS.md -Pattern '^## `?D-'
  5: ## D-NN: <decision in one line>            <- format template, entry nahi
 14: ## `D-01` and `D-02` — written on Din 6...  <- evidence-trail heading
 91: ## D-01   266: ## D-02   451: ## D-03   496: ## D-04   545: ## D-05
629: ## D-06   813: ## D-07   876: ## D-08   930: ## D-21
  -> aaj ke baad: 1080: ## D-22   1260: ## D-23

Select-String -Path docs\PROBLEMS.md -Pattern '^## P-'
  P-01 .. P-27, koi gap nahi, koi duplicate nahi
```

| Kya | Value |
|---|---|
| Grep plan ke expected ranges se match karta hai? | **Haan.** `D-` me next free `D-22`, `P-` me next free `P-28` — dono plan ke expectation se match `[MEASURED]` |
| Aaj assign hue `D-` numbers | **`D-22`, `D-23`.** Next free ab **`D-24`** |
| Aaj assign hue `P-` numbers | **Koi nahi.** Aaj likhne ka din tha, koi naya failure mode produce nahi hua — to `P-28` abhi bhi free hai. *Ek bhi naya `P-` na hona apne aap me suspicious hoga agar aaj koi experiment chala hota; aaj nahi chala* |
| Collision mili? | **Nahi.** `D-09`..`D-20` roadmap Part 2 ke reserved hain aur touch nahi hue. Do purani collisions (`D-09`, `P-07`) isi grep ki wajah se dobara nahi hui |
| Dangling citation mili? | **Nahi.** Aaj cite hue saare numbers — `D-01`, `D-04`, `D-06`, `D-07`, `D-21`, `D-22`, `D-23`, `P-01`, `P-04`, `P-05`, `P-07`, `P-11`, `P-12`, `P-13`, `P-14`, `P-15`, `P-16`, `P-19`, `P-20`, `P-21`, `P-22`, `P-23`, `P-24`, `P-25`, `P-26`, `P-27` — sabke heading maujood hain `[MEASURED]` |

**Doc-sync — kya actually likha gaya (files kholke check, `git status` se nahi):**

| File | Kya gaya | Ho gaya? |
|---|---|---|
| `docs/DECISIONS.md` — `D-22` | Lease `30 s` + heartbeat `10.0 s` + **no handler timeout**, ek entry (`P-15` ki wajah se — Relay handler bound nahi karta, to lease ka koi upper bound nahi jiske neeche wo safe ho). 12 `Cost` lines, 7 `Rejected` lines, `Revisit when` me wo run jo hole band karta hai | ✅ heading line `1080` par, disk se padhi |
| `docs/DECISIONS.md` — `D-23` | Retry policy: increment **on claim**, `next_attempt_at` column, `delay(n) = min(5.0 · 2^(n-1), 15.0)` verbatim, equal jitter verbatim, jitter ke do reason do alag tag ke saath, `CAP` **inert** likha gaya, aur overdraft **accept** kiya gaya. 12 `Cost` lines, 8 `Rejected` lines | ✅ heading line `1260` par, disk se padhi |
| `docs/DECISIONS.md` — `D-06` amendment | Paanch hisse: kaunsa option chala aur `NOT VALID` ka fayda mila ya nahi · lock queue ke do halves (queue `[MEASURED-R]`, hold duration `[INFERRED]`, `LOCK TABLE` substitution **declared**) · `downgrade` ke dono outcomes · Cost 1 ka asli writer count · aur cycle ki wajah se CAS ka generation-blindness | ✅ **append hua**, ek bhi purani line edit nahi hui |
| `docs/DECISIONS.md` — `D-21` amendment | `count(*) > 1` **kab** expire hui (Din 2/3, retry se do din pehle) · ab uska matlab ek **sawaal** hai · paanch causes ids ke saath · identifier ka verdict (**overdue**, owner Week 3, `D-22` Cost 11 me same jawab) · aur `failed = 15` ka teen-shape breakdown | ✅ **append hua** |
| Har naye entry ka **non-empty `Cost`**, aur har `Cost`/`Rejected` line pe ek provenance tag | Dono entries me koi `Cost` line khaali nahi. Tags: `[MEASURED]` / `[MEASURED-R]` / `[INFERRED]` / `[NO EVIDENCE]`, **exactly ek per line** — kyunki untagged line `[MEASURED]` ki tarah padhi jaati hai | ✅ padh ke verify kiya |
| `docs/PROBLEMS.md` — Din 1–5 ki bachi hui entries | **Kuch bacha hi nahi tha** — `P-19`..`P-27` apne apne din pe likhi gayi thi; grep se confirm `[MEASURED]`. Aaj koi nayi entry nahi | ✅ nothing owed |
| `docs/MAP.md` — per naye entry ek index row, **reasoning nahi** | Index A: ek **naya subsection** *"Lease, reaper, and duplicate execution"* (12 rows) + retry/backoff rows *"Retries and duplicate side effects"* me + `NOT VALID`/lock-queue/`downgrade` rows *"Constraints, schema, and migrations"* me + do shutdown rows. Index B: `D-22`/`D-23` ki nayi rows, aur `D-06`/`D-21` ki **purani rows update** hui (nayi nahi jodi). Index C: `jobs.claimed_at`, `jobs.next_attempt_at`, `Reaper`, `Heartbeat`, `dead_letter`, `Migrations / Alembic` — aur `jobs.status`/`jobs.attempts`/`job_executions`/`Claim query`/`Worker loop`/`Shutdown`/`Poll interval` update. Trust ledger aur Open ledger me bhi Week 2 ke blocks — warna dono silently stale reh jaate | ✅ ek line per cell, koi paragraph copy nahi |
| `docs/LEARNING_LOG.md` — open-items table, Week 2 row, next-free numbers | Week 2 row ✅ Complete; companion table me `D-24`/`P-28`; **har touch hua item ko verdict** — closing day + measurement, **ya** owner naam se. Ek stale row pakdi gayi: *"POSTMORTEMS.md — 1 entry, Cloudflare still open"* jabki file me **3 entries** hain aur Cloudflare Incident 02 hai `[MEASURED]`. Nayi sub-table: Din 6 ke apne teen debts | ✅ |
| `docs/roadmap/CURRENT_WEEK.md` — week status table + pointer Week 3 pe | Pointer `Week 3` par, Din 6 ke warnings **superseded** block me shift, Week 2 row ✅ Complete apne closing summary ke saath, Week 3 row 🔄 Active, aur *"Five things Week 3 Din 1 must take as given"* + Week 3 ke liye bench | ✅ **gitignored file — kholke padhi, `git status` se nahi** |
| `docs/daily/WEEK_02_HANDOFF.md` — teen headings, dono definitions, content | Teen headings, `WEEK_01_HANDOFF.md` ke same shape me, pehli do word-for-word. Dono definitions **file me likhi hui** hain, memory me nahi. `What Week 3 Must Not Assume` me chaar items: contract #2 unprotected, `attempts = 4` overdraft, untested shutdown-lease interaction, heartbeat ki event-loop dependency | ✅ **gitignored file — kholke padhi** |
| Commit — staged paths naam se, `.` kabhi nahi | Paanch committable paths: `docs/DECISIONS.md`, `docs/PROBLEMS.md`, `docs/MAP.md`, `docs/LEARNING_LOG.md`, `docs/logs/WEEK_02.md` | niche `Commit` block dekho |

**Do files aaj ki hain aur `git status` me kabhi nahi aayengi** — `docs/roadmap/CURRENT_WEEK.md` aur
`docs/daily/WEEK_02_HANDOFF.md`. `git check-ignore -v` output niche cleanup block me hai. Din 5 ki BRIEF ne
`DDIA_CH8_LINKS.md` ko committable list me daala tha aur wo **galat** tha — `docs/ddia_summaries/` bhi
`.gitignore` line `45` se excluded hai `[MEASURED]`. Wo file aaj touch hi nahi hui (lines 10–13 abhi bhi
unconfirmed).

`docs/roadmap/` aur `docs/daily/` gitignored hain — wo do files `git status` me dikhengi hi nahi, isliye
kholke check hoti hain.

**Cleanup:**

| Kya | Status | Label |
|---|---|---|
| Naye probe rows | **Koi nahi.** Aaj ek bhi `INSERT` nahi hui, ek bhi row ka `status` nahi badla. Saari queries read-only thi (`select`, `pg_constraint`, `pg_stat_activity`) | `[MEASURED]` |
| Temporary capture file | **Koi nahi bani.** Bench output seedha iss log me gaya, kisi file me nahi — to delete karne ko kuch nahi tha, aur "output pehle copy karo" wala rule aaj vacuous hai | `[MEASURED]` |
| Hafte bhar ki probe rows | **Delete nahi hui, aur wahi sahi hai:** `88` (Din 1), `97` (Din 3), `104`, `105` (Din 4), `108` (Din 5). Paanchon aaj ki chain me naam se count hote hain; ek bhi delete karna delta arithmetic todta hai aur `P-05` ka evidence mitata hai | `[MEASURED]` |
| `src/` change | **Zero.** `git status` me sirf `docs/` — HEAD `399febb` se `src/` me ek line farq nahi | `[MEASURED]` |
| worker / reaper processes | **`0`** — teesra consecutive clean close | `[MEASURED]` |
| `idle in transaction` | `0` | `[MEASURED]` |
| **Teesra check — `backend_start`** | PID `37` (`2026-08-25 09:55:12+00` se, `~4 din`) **ab nahi hai.** Sirf aaj ka review session `pid 102` hai. Wajah: `relay-db-1` `~35 min` se up hai → **container restart**, deliberate terminate nahi | `[MEASURED]` |
| `git check-ignore -v` — assume nahi, measure | `.gitignore:46:docs/roadmap/` · `.gitignore:44:docs/daily/` · `.gitignore:45:docs/ddia_summaries/` — teen lines, har ek apna rule naam se | `[MEASURED]` |

**Commit:** paanch paths **naam se**, `.` nahi. `docs/DECISIONS.md` · `docs/PROBLEMS.md` · `docs/MAP.md` ·
`docs/LEARNING_LOG.md` · `docs/logs/WEEK_02.md`. `docs/PROBLEMS.md` aur `docs/LEARNING_LOG.md` Din 5 se
already modified the — wo iss commit me saath jaate hain, aur ye log me likha hai taki baad me *"Din 6 ne
`PROBLEMS.md` kyun touch ki"* ka jawab maujood ho. **`CURRENT_WEEK.md` aur `WEEK_02_HANDOFF.md` stage nahi ho
sakti** — gitignored, aur unki absence `git status` me structurally invisible hai, isliye wo kholke padhi
gayi.

---

### 💡 What I Understood

> **Ye session ne establish kiya, mera wording nahi. Isko apne shabdon me likhna hai** — aur aaj ye baat
> normal se zyada bhaari hai, kyunki iss hafte ke **paanchon** din ka `💡` reviewer ne likha hai. Wo debt
> `LEARNING_LOG.md` me apne owner ke saath likhi hui hai.

**1. Ek `Cost` field wo cheez hai jo entry ko decision se *record* banati hai, aur wo evidence ke bina likhi
hi nahi ja sakti.** `D-22` paanch din intezaar kiya, aur wo intezaar sahi tha: Din 2 pe uski `Cost` line
*"lease `30 s` chuna"* hoti — ek number aur koi consequence nahi. Aaj wahi field kehti hai *"lease uss handler
se chhoti thi jise Relay allow karta hai, aur usne hafte ka duplicate banaya — job 95, overlap `14.783 s`"*.
Ek hi decision, do bilkul alag entries. **Jo cheez badli wo decision nahi thi, uski keemat ka evidence tha.**

**2. Ek prediction ki keemat uske sahi hone me nahi, uske *conditions* likhe hone me hai.** `D-06` Cost 4 ne
Week 1 Din 1 pe `NOT VALID` + `VALIDATE` ka pattern **theek** likh diya tha — do statements, dono naam se.
Aur wo phir bhi adhoora tha, kyunki usne ye nahi likha ki wo do statements **do transactions** me hone
chahiye. Alembic `upgrade()` ko ek transaction me wrap karta hai, to ek-migration version me `NOT VALID`
**likha** hota aur uska fayda **na milta** — lock commit tak hold rehta aur validation scan usi ke neeche
chalta. **Recipe sahi thi, aur wo condition jo usko kaam karati hai unstated thi.** `P-04` ka shape: partial
protection, poora confidence.

**3. Ek summary count ka matlab uss din badal jaata hai jis din koi status value ka contract badalta hai, aur
count khud kuch nahi bolta.** `failed = 15` aaj bhi `15` hai aur uske peeche **teen** alag contracts hain.
`dead_letter` naya sach batata hai; purana `failed` history par baitha rehta hai aur usko rename karna log ko
jhootha banata. To week-close ka kaam count likhna nahi hai — **count ko disambiguate karna hai**, warna
Week 3 `15` ko *"jo jobs ek baar fail hui"* padhega, aur wo galti **plausible** direction me hogi. Wahi baat
`count(*) > 1` par ek layer neeche hai: paanch causes, aur *duplicate* shabd **ek** id par lagta hai.

**4. Chain judna evidence hai, par uss cheez ka nahi jiske liye wo likhi gayi thi.** Paanch delta pehli
koshish me exactly jud gaye. Wo **ye** prove karta hai: recorded deltas ke bahar koi row bani ya mitti nahi.
Wo **ye nahi** prove karta: din saaf the. Iss hafte **teen** din chain perfectly judi jabki ek bhoola hua
process abhi bhi poll kar raha tha — teeno baar wajah ek hi thi, stray ke paas move karne ko kuch nahi tha
(`pending` count `0`). **Wo detection nahi, wo khaali queue hai.** Ek clean arithmetic ko hygiene ka certificate
maan lena iss hafte ki sabse quiet galti thi.

**5. Aakhri din pe likhi hui prose har check pass kar jaati hai jo usko padhti nahi.** Isi liye aaj ka
verification *"likha kya"* nahi tha, *"file kholke line padho"* tha — Stage Day pe chaar files `0 B` thi jab
editor content dikha raha tha, aur `docs/daily/` + `docs/roadmap/` gitignored hain, to `git status` madad hi
nahi kar sakta. **Do aaj ki files kabhi `git status` me nahi aayengi**, aur unki absence structurally silent
hai.

---

### 🧠 Self-Check (honest — `0 / 7` self-answered on Part B, aur ye Din 4 ka `0/6` dohraata hai)

**Part B ke saat sawaalon ka koi likha hua answers file iss review ko supply nahi hua.**
`docs/daily/week_02/DIN_06_ANSWERS.md` disk pe **maujood nahi hai** `[MEASURED]`. To score `0 / 7` hai, aur
ye score *galat jawab* ka nahi — *absent jawab* ka hai, aur wo do alag cheezein hain.

**Iss hafte ka Part B record, poora:** Din 1 `0/6` · Din 2 `0/6` · Din 3 **`5/6`** · Din 4 `0/6` (kuch submit
nahi hua) · Din 5 `7/7` likha gaya par **scoring skip** hui (user ka instruction) aur uska mtime saare
measurements ke **baad** ka tha (`E8` — reconstruction, prediction nahi) · Din 6 `0/7`.

**Aur aaj iski keemat exactly naapne layak hai, kyunki aaj ke saat sawaal *aaj ke kaam ke* sawaal the.**
Sawaal 3 (*`D-06` Cost 4 poori sahi thi ya ek condition missing thi?*) ka jawab iss entry ka `💡` #2 hai —
`transaction boundaries`. Sawaal 5 (*`status` writers kahan lagte hain, aur kis writer pe guard bhoolna sabse
aasan tha?*) ka jawab source se nikla aur wo **BRIEF ke apne phrasing ko correct karta hai**. Sawaal 4
(*`D-21` ki prediction ka kaunsa hissa sahi tha aur kaunsa bada ho gaya?*) ka jawab *"mechanism sahi,
**schedule** galat — do din pehle expire hui"* hai. **Teen sawaal, teen aisi cheezein jo aaj derive hui aur
jinka prediction likha hota to yaad reh jaata.** Yahi `0/7` ki asli keemat hai, score nahi.

**Corrections:**

| # | I said | Actual | The transferable lesson |
|---|---|---|---|
| 1 | *"`status` writers ek se **paanch** ho gaye — claim, reaper, retry, terminal, heartbeat"* (BRIEF, `CURRENT_WEEK.md`, aur Din 5 ki entry, teeno me) | Source se `[MEASURED]`: **teen** code sites `status` likhte hain — claim, reaper, aur **ek** mark statement jo chaar values emit karta hai. Heartbeat chautha guarded writer hai par uska `SET` `claimed_at` hai; wo `status` **par** guarded hai, likhta nahi. Shutdown kuch nahi likhta | **"Kitne writers hain" ek `grep` se aata hai, transitions ki ginti se nahi.** Chaar transitions ek statement se aa sakti hain. Audit surface *statements* ka hota hai, kyunki guard statement pe likha jaata hai — aur ye count dono directions me galat ho sakta hai: zyada batao to kaam invent hota hai, kam batao to writer chhoot jaata hai |
| 2 | *"`failed` rows ke do groups hain — unknown `type` (`attempts = 0`), aur bounded-out (`attempts = 3`)"* (BRIEF Step 2) | **Teen groups** `[MEASURED]`. `attempts = 0` khud do shapes hai: unknown `type` (`8`, `23`, `58`, `75`) **aur** Week 1 ke handler failures jab retry logic exist nahi karti thi (`5`, `20` = `sleep`; `6`, `21`, `57` = `boom`) — paanch rows, aur ye sabse bada group hai | **`attempts = 0` do bilkul alag cheezein matlab rakhta hai: "counter kabhi incremented nahi hua kyunki handler enter hi nahi hua", aur "counter uss code se pehle ka hai jo usko increment karta"**. Ek column ki default value history me ek dusra meaning rakhti hai, aur usko group karne se pehle `type` bhi padhna padta hai |
| 3 | Din 5 ki entry: *"`psql` backend `37` ko terminate nahi kiya — wo user ki session hai, aur uska removal ek named item hai"* — yaani wo abhi bhi wahan hai | Aaj wo **nahi** hai `[MEASURED]`, par kisi ne band nahi ki: `relay-db-1` container `~35 min` se up hai, to restart ne usko close kiya | **Ek open item ka "band" ho jaana aur uske peeche wali habit ka ban jaana do alag events hain.** Item close karke habit ko closed maan lena wahi galti hai jo *"chain judi, to din saaf tha"* hai. Check Week 3 me carry hota hai, item ke bina |

---

### 🚧 Unresolved / Follow-ups

**New, from today:**

1. **Iss hafte ka har `💡` aur `🧠` section reviewer ka likha hua hai** — paanchon din, aur aaj ka bhi. Ye
   hafte ki sabse badi retention debt hai, kyunki `WEEK_02_HANDOFF.md` ka *What Stuck* list **abhi ek claim
   hai jiske peeche koi test nahi**. Owner: **user**. Sabse sasta honest version: Week 3 ke har din ek din ka
   `💡` apne shabdon me dobara likho, reviewer ka text **pehle kholе bina**.
2. **`DIN_06_ANSWERS.md` disk pe exist nahi karta** `[MEASURED]` — Part B `0/7`, aur teen sawaal exactly wo
   the jinke jawab aaj derive hue (`💡` #2, correction #1, `D-21` ka schedule).

**Deliberately open (owner ke saath):**

- **Attempt / claim identifier on `job_executions`** → **Week 3, dedup key ke saath** (`D-21` amendment +
  `D-22` Cost 11 — dono jagah **same** jawab, taki diverge na ho).
- **Completion endpoint (`completed_at`)** → **Week 3**, `D-22` Cost 10 me priced.
- **Fencing token / generation counter** → **Week 3** (`D-06` amendment, `D-22` Cost 7).
- **Handler timeout** → **Week 3/4**, aur wo blocked hai ek asli sawaal pe: *timed-out handler ka `status`
  kya hai?* (`P-15`, `D-22` rejected option c).
- **`attempts < :max` claim gate me** → **Week 3, agar kabhi** — aaj overdraft accept kiya gaya (`P-27`,
  `D-23`).
- **Shutdown-versus-lease ka asli run** (`slow` + `payload {"seconds": 45}`, `SIGBREAK` at `T = 3 s`) →
  **Week 3 Din 1 ya ek named catch-up slot**. Aaj **jaan-boojh ke nahi chalaya**: wo band ho rahi chain me
  execution rows add karta aur measurement din ko writing din me mix karta.
- **`last_error`** → **Week 4** (`dead_letter` verdict hai, diagnosis nahi).
- **`ADD CONSTRAINT` ka hold duration** → bade table ka intezaar, honestly (`D-06` amendment).

**Slipped (aur specifically kya chahiye):**

- **Paanch written Week 2 answers (*the five written Week 2 answers*) — `slipped`, `deferred` nahi. Dasva
  carry, aur hafta khatam.** Kabhi kisi
  slot me schedule nahi hui, kabhi kisi cheez pe blocked nahi thi, aur `CURRENT_WEEK.md` ka apna rule (*"Week
  2 Din 1 shuru na ho jab tak ye apne shabdon me exist na kare"*) das baar override hua bina koi decision
  liye. **Chaar me se chaar sawaal ab measured hain, to unhe likhna ab derivation se zyada recall ban gaya
  hai — aur wahi slip ki asli keemat hai.** Chahiye: `Week 3 Din 1, Step 0 se pehle, user ke haath se`. Agar
  gyaarva slip hota hai to honest move item **delete** karna hai, carry nahi.
- **`DDIA_CH8_LINKS.md` lines 10–13** — paanchva din unconfirmed. File aaj touch nahi hui.
- **Teesra cleanup check user ne ek baar bhi nahi chalaya.** BRIEF me do baar aaya, dono din report nahi hua.
  Chahiye: ek line, har din close pe, output log me.

**Carried forward, unchanged:**

- **Week 1 Din 7 ka log entry** aur **`2026-08-24` ka record** — dono ab **decision** maangte hain, gyaarva
  carry nahi: entry likho jo bacha hai usse, **ya** `WEEK_01.md` me likh do ki Din 7 ka entry kabhi nahi
  banega aur usko debt ki tarah dhona band karo.
- **Din 3 ke paanch unroled job ids (`89, 90, 92, 93, 94`)** — aaj **unrecoverable** declare kar diye. `94`
  (`super_slow`, ek dispatch, koi duplicate nahi) wo tha jo maayne rakhta tha, aur uska outcome permanently
  unknown hai. Koi owner nahi, kyunki karne ko kuch bacha nahi. Jo bacha wo lesson hai: **jis din id banao,
  usi din delta me naam likho** — attribution wo ek cheez hai jo arithmetic recover nahi kar sakti.
- **`super_slow` kisi commit me nahi hai** (`P-23`) — `D-22` Cost 12 me likha hua hai ki hafte ka centrepiece
  ek uncommitted working-tree state pe chala aur **waise dobara nahi chalega**; uska replacement
  payload-driven `slow` run hai.
- **Positional indexing into an ORM `RETURNING`** — aaj bhi correct, aaj bhi latent (W2 D3 M7).
- **`P-03` claim-query index** (Week 4, measure karke), **`P-06` `idle_in_transaction_session_timeout`**
  (Week 4, pool sizing ke saath), **`P-08` stream-level body limit** (Week 4), **FK + index on
  `job_executions.job_id`** (Week 4, retention ke baad).

---

### ❓ Question / Next Thought

**Week 3 ka pehla sawaal iss hafte ke do measurements ke beech ki jagah me baitha hai, aur wo *"idempotency
key kaise banayein"* nahi hai.**

Job 95 ne prove kiya ki do handler **overlap** kar sakte hain (`14.783 s`), aur job 108 ne prove kiya ki bound
ke **baad** bhi ek poora dispatch mil sakta hai. Dono cases me dedup ka check kahin **chalna** hai — aur agar
wo check *"is `key` already present?"* hai, to wo khud ek check-then-act hai, jo Week 0 Din 5 ka poora subject
tha. To sawaal:

> **Dedup ka fayda uss instant aata hai jab dono workers ek saath chal rahe hain — to wo check kis cheez pe
> atomic hoga?** Ek `UNIQUE` constraint (database faisla karta hai, aur loser ko error milta hai), ya ek
> `INSERT ... ON CONFLICT DO NOTHING` ka `rowcount` (wahi compare-and-set ka shape jo `D-06` ne chuna), ya
> handler ke andar ek guard (jo `MAP.md` T6 ki aakhri row hai — *state outside the database*, jahan koi
> isolation level madad nahi karta)?

Aur uske saath ek doosra, kam obvious sawaal jo aaj ke `D-21` amendment se seedha nikalta hai: **key kis
cheez ki identity hai — job ki, ya *dispatch* ki?** Agar job ki hai to legitimate retry (`D-23`, `attempts 1→3`)
bhi duplicate lagega aur bounded retry hi toot jaayega. Agar dispatch ki hai to job 95 ke dono dispatch alag
keys honge aur dedup kuch nahi rokega. **Wo distinction hi wo identifier hai jo `D-21` ne Week 3 pe defer
kiya**, aur isi liye dono ek saath decide hote hain — alag-alag nahi.

---

## Week close — reconcile chain aur handoff

Din 6 ka closing **hi** hafte ka closing hai. Chain ka shape ek hi hai: **week opening + har din ka delta =
aaj ke actual counts.** Chain kabhi `max(id)` se nahi jodi jaati — id contiguity `jobs` ka invariant nahi
hai, aur `P-05` hi uska evidence hai.

**Full reconcile chain:**

| Line | Kahan se | Value |
|---|---|---|
| Week opening counts | BENCH block, jise Din 1 ke bench ne **exactly** reproduce kiya (to provenance settled hai) | `74 succeeded / 9 failed / 3 running (41, 63, 65) / 0 pending` = **`86`** · `job_executions` **`57`** · `max(id) 87` · seq `87` |
| `+` Din 1 delta | Din 1 entry | **jobs `+1`** — id **`88`** (`slow`) → `succeeded`. **`job_executions +1`**. Koi bucket shift nahi; 41/63/65 abhi bhi `running` |
| `±` Din 2 delta | Din 2 entry | **jobs `+0`.** Reaper ne **41, 63, 65** ko `running → pending` kiya: `−3 running`, `+3 pending`, **total wahi** — reclaim buckets ke beech move karta hai, banata ya mitata kuch nahi. Job **75** untouched. **`job_executions +0`** (worker off) |
| `+` Din 3 delta | Din 3 entry | **jobs `+9`** — ids **`89`–`96`** (aathon `succeeded`) **+ reviewer probe `97`**; **plus** drain ne 41/63/65 ko `pending → succeeded` kiya (bucket shift, nayi row nahi). **`job_executions +12`** — drain ke 3 dispatch (41 ka **pehla**, 63/65 ka **doosra**) + `89`–`96` ke 8 + **job 95 ka doosra dispatch** 1 |
| `+` Din 4 delta | Din 4 entry | **jobs `+8`** — `98` aur `99`–`102` aur `103` (chhe `boom`, sab `failed` at `attempts 3`) **+ do reviewer probe** `104`, `105` (`pending`). **`job_executions +18`** — `97`→1, `98`→3, `99`–`102`→12, `103`→2, probes→0 |
| `±` Din 5 delta | Din 5 entry | **jobs `+3`** — `106`, `107` (`slow` → `succeeded`) **+ reviewer probe `108`** (`boom` → `dead_letter`, `attempts 4`); **plus** `104`/`105` `pending → dead_letter` (bucket shift). **`job_executions +6`** — `104`→2, `105`→1, `106`→1, `107`→1, `108`→1 |
| `=` expected closing | arithmetic | jobs `86 + 1 + 0 + 9 + 8 + 3` = **`107`** · executions `57 + 1 + 0 + 12 + 18 + 6` = **`94`** |
| aaj ke `psql` counts — **paanchon** status buckets + total | aaj ka Step 0 output | `89 succeeded / 15 failed / 3 dead_letter / 0 pending / 0 running` = **`107`** `[MEASURED]` |
| `job_executions` — opening + per-din delta = aaj ka count | log + aaj ka output | **`94`** `[MEASURED]` |
| **Chain juda?** | — | **Haan, dono taraf, pehli koshish me.** `89 + 15 + 3 = 107` · `57 + 1 + 0 + 12 + 18 + 6 = 94` |

**Aur per-day delta anumaan se nahi liya gaya — `created_at` aur `executed_at` se padha gaya, jo ki `D-08` aur
`D-21` ke timestamp columns ka poora payoff hai (`MAP.md` T7) `[MEASURED 2026-08-29]`:**

```
jobs, ids 88+ by created_at::date          job_executions by executed_at::date
  2026-08-23  ->  1     (88)                 2026-08-17  -> 30  \
  2026-08-26  ->  9     (89-97)              2026-08-18  -> 16   > 57 = week opening
  2026-08-27  ->  8     (98-105)             2026-08-20  -> 11  /
  2026-08-28  ->  3     (106-108)            2026-08-23  ->  1   Din 1
  ------------------------------             2026-08-26  -> 12   Din 3
  86 + 1 + 0 + 9 + 8 + 3 = 107               2026-08-27  -> 18   Din 4
                                             2026-08-28  ->  6   Din 5
                                             ------------------------------
                                             57 + 1 + 0 + 12 + 18 + 6 = 94
```

**Aur yahin ek finding nikli, aur wo `E5` nahi hai — usse ek rung neeche hai.** Din-close ke reports se banayi
gayi chain ka **total sahi tha aur do per-day deltas galat the, dono opposite direction me, to unka error
cancel ho gaya:**

| Line | Report se | `created_at` / `executed_at` se `[MEASURED]` | Farq |
|---|---|---|---|
| Din 3 — jobs | `+10` | **`+9`** (`89`–`97`) | `−1` |
| Din 4 — jobs | `+7` | **`+8`** (`98`–`105`) | `+1` |
| Din 3 — executions | `+13` | **`+12`** | `−1` |
| Din 4 — executions | `+17` | **`+18`** | `+1` |
| **Total** | `107` / `94` | `107` / `94` | **`0`** |

**Boundary row `97` hai** — reviewer probe, `created_at 2026-08-26 15:41:53` (Din 3 ka din), par uska **pehla
dispatch Din 4 pe hua** aur Din 4 ki opening baseline usko *"Din 4 ki pehli claimable row"* kehti hai. Ek row
jiska **creation** ek din ka hai aur **execution** dusre din ka, aur wo do alag deltas me count hoti hai.

**Ye exactly wo cheez hai jiske against BRIEF ne warn kiya tha — *"difference ko nazdeeki din me fit na
karo"* — aur wo pehle se fit ho chuki thi**, kyunki chain din-close ke likhe hue deltas se banti hai aur wo
deltas ek doosre ke against reconcile nahi hote, sirf total ke against hote hain. **Total match karna do
compensating errors ko chhupa leta hai.** Fix mechanical hai aur aaj hi mil gaya: per-day delta `created_at` /
`executed_at` se derive karo, report ki gin-ti se nahi — ye ek `group by` hai aur wo **har** din chalayi ja
sakti hai, sirf week close pe nahi.

**Isko `E5` na kehna deliberate hai:** koi row banayi ya mitayi nahi gayi, koi day-boundary hilai nahi gayi,
aur closing counts independently verify hue. Jo galat tha wo **attribution** thi — bilkul wahi shape jo Din 3
ka `M9` tha (aath nayi ids, teen naam se likhi). *Chain judi, kahani me ek row galat din pe thi.*

**`E5` trigger nahi hua.** Aur jo isne prove kiya, exactly wahi likha jaata hai: **recorded deltas ke bahar
koi row bani ya mitti nahi.** Jo isne **nahi** prove kiya: din saaf the. Iss hafte teen din (Din 1, 2, 3)
chain perfectly judi jabki ek bhoola hua process poll kar raha tha — teeno baar wajah ek: stray ke paas move
karne ko kuch nahi tha. **Wo detection nahi, khaali queue hai.**

**Aur ek line jo iss hafte nayi hai:** chain **paanch** status buckets par band hui jabki hafta **teen** se
shuru hua tha. `dead_letter` Din 1 pe exist hi nahi karta tha, aur wo bucket pehli baar count hone par `0`
**nahi** tha — to *"migration apply hui par transition nahi"* wala failure mode ruled out hai.

**`failed = 15` ek number hai jo teen contracts pakad kar baitha hai `[MEASURED 2026-08-29]`:**

| Group | ids | Matlab |
|---|---|---|
| unknown `type`, `attempts = 0` | `8`, `23`, `58` (`does_not_exist`), `75` (`send_receipt`) | koi handler registered nahi tha. **Aaj ka code bhi yahi produce karta hai**, aur wo branch `attempts` **dekhta hi nahi** |
| Week 1 handler failure, `attempts = 0` | `5`, `20` (`sleep`), `6`, `21`, `57` (`boom`) | handler ne raise kiya, retry logic ke exist karne se pehle. Counter ko increment karne wala code hi nahi tha |
| bounded out, `attempts = 3` | `98`, `99`, `100`, `101`, `102`, `103` (sab `boom`) | **aaj ka code inhe `dead_letter` kehta** |

**`dead_letter` ne ek bhi historical row rename nahi ki**, aur karna bhi nahi chahiye — wo log ko jhootha
banata. Iss table ka poora kaam ye hai ki agla padhne wala `failed 15` ko *"jo jobs ek baar fail hui"* na
padhe.

**Week close pe `running` rows — ye ek DoD item hai, aur zero ho ya na ho, dono cases likhe jaate hain:**

| Kya | Value | Label |
|---|---|---|
| `running` count at close | **`0`** — aur ye measured zero hai, aaj ki date ke saath (`2026-08-29`). `group by status` me `running` ki row hi nahi aayi, jo `0` ka hi roop hai | `[MEASURED]` |
| Uske ids (agar zero nahi) | **N/A.** Aur ye hafte ka ek chhota par asli result hai: hafta **teen** `running` rows (`41`, `63`, `65`) se shuru hua tha jo ek hafte se atki hui thi, aur **zero** pe khatam hua | `[MEASURED]` |
| Ye ids Week 3 ka input hain — handoff me gaye? | Zero hone ki wajah se koi id nahi gayi. `pending` bhi `0` hai — to **Week 3 Din 1 ek khaali queue pe khulta hai**, aur yahi baat `CURRENT_WEEK.md` ke bench me likhi hui hai taki Week 3 ka pehla worker kisi purani row ko utha ke measurement contaminate na kare | `[MEASURED]` |

Non-zero `running` ka matlab hai hafte ke end pe bhi kaam atka pada hai. Usko *"reaper chalake saaf kar
diya"* karke count zero banana **arithmetic adjust karna** hai — wo E5 hai aur wo nahi hota.

**Sequence:**

| Kya | Value | Label |
|---|---|---|
| `jobs_id_seq` `last_value` | **`108`** | `[MEASURED]` |
| `max(id)` | **`108`** | `[MEASURED]` |
| Gap — aur wo `P-05` ka evidence hai | **Iss hafte koi naya gap nahi bana** (`seq = max(id)`). Poore table me ek hi gap hai, id **`79`** par, Week 1 Din 6 ka rolled-back `INSERT` — ek consumed sequence value, permanently. **Sequence reset nahi ki gayi**, aur wo deliberate hai: reset karna `P-05` ka evidence delete karna hai, sirf numbers tidy dikhane ke liye | `[MEASURED]` |

**Agar chain nahi judi (E5):** mismatch **finding ki tarah** likhi jaati hai, difference ko kisi din me fit
karke chain band nahi hoti.

| Kya | Value |
|---|---|
| Kaunsa din toota | **Koi nahi** — closing totals ke against chain judi. Par **attribution** do jagah galat thi: **Din 3** aur **Din 4** ke deltas ek-ek row se galat the, opposite direction me (upar wali table dekho) |
| Kitna difference | **Total pe `0`.** Per-day pe `∓1` job aur `∓1` execution row, Din 3 ↔ Din 4 ke beech. Boundary row **`97`** hai: `created_at` Din 3 ka, pehla dispatch Din 4 ka |
| Kya check kiya gaya | **Bhoola hua worker (`P-13`):** `python.exe` count `0` aaj `[MEASURED]`, aur `pg_stat_activity` me sirf aaj ka review session — to koi stray claim nahi hui. **Extra reaper run:** `running` count `0` hai aur `claimed_at` kisi bhi non-terminal row pe nahi bacha, to reclaim ka koi bina-record wala nishaan nahi. **Delete hui row:** `count(*) = 107` aur `21` naye ids `88`–`108` contiguous hain, koi id missing nahi `[MEASURED]`. **Consumed sequence value:** `seq = max(id) = 108`, iss hafte koi rollback nahi; `P-05` ka purana gap `79` par hai. Aur asli cause **arithmetic nahi** nikla — `created_at`/`executed_at` ka `group by` |
| **Ye din handoff ki teesri heading me naam se gaya?** | **Nahi, aur wo faisla hai:** koi din *"bharose ke layak nahi"* nahi hua — dono deltas ke errors cancel hote hain aur closing counts independently verify hue, to Week 3 kisi din ka number chhod nahi raha. Jo handoff me jaana chahiye tha wo **din ka naam nahi, habit ka naam** hai, aur wo `LEARNING_LOG.md` me hai: **per-day delta report ki gin-ti se nahi, `created_at`/`executed_at` ke `group by` se aata hai** |

Toote hue din ka naam Week 2 ke handoff ki teesri heading me jaata hai, kyunki Week 3 ko pata hona chahiye
ki **kis din ka number bharosa ke layak nahi hai**.

---

### Definition of Done — week close pe audit

Plan ka koi box shipped file me ticked nahi tha. Ab har item ka ek status hai, aur **har untick ek line
maangta hai**: *deliberately deferred* apne **owner** ke saath, **ya** *slipped* uske saath jo usko
**specifically** chahiye. Do me se ek — dono nahi, koi nahi bhi nahi.

| Group | DoD item | Status | Evidence | Untick ho to: deferred (owner) / slipped (kya chahiye) |
|---|---|---|---|---|
| Build | Lease column, claim `UPDATE` me likhi jaati hai | ✅ | `claimed_at timestamptz NULL`, migration `75a845575d2e`, Din 1 M2/M3 `[MEASURED]` | — |
| Build | Reaper ek **alag** process, compare-and-set guard + `rowcount` ke saath | ✅ | `src/reaper.py`, compiled predicate Din 2 M2; guard `UPDATE` poora predicate re-assert karta hai `[MEASURED from source]` | — |
| Build | Heartbeat | ✅ | `HEARTBEAT_INTERVAL_SECONDS = 10.0`, guard `status='running'`, `asyncio.create_task` + `stop_event`, Din 3 `[MEASURED-R from source]` | — |
| Build | Bounded retry + backoff + jitter | ✅ | Din 4; formulas `D-23` me verbatim; `base` Din 5 pe `3.0 → 5.0` | — |
| Build | `dead_letter` status value | ✅ | Do migrations, `convalidated false → true`, `models.py` usi commit me `[MEASURED-R]` | — |
| Measured | Centrepiece duplicate count | ✅ | **Job 95 — 2 execution rows, overlap `14.783 s` proved**, do independent derivations `2 ms` ke andar, Din 3 `[MEASURED-R]` | — |
| Measured | Reaper ki reclaim latency | ✅ | **`1.798192 s`**, reaper pehle start hua phir row seed hui; independently corroborated `≤ 207.098 ms` job 95 se `[MEASURED-R]`. Din 3 ka pehla number (`19.953818 s`) galat quantity ka tha → `P-22` | Load pe behaviour (>1 candidate per pass) **deferred: Week 4, metrics ke saath** |
| Measured | Chuni hui lease duration + uske peeche ka measurement | 🟡 **partial** | `30 s` **chuna** Din 2 pe, aur uss din ki run ne usko exercise **nahi** kiya (saare reclaims `IS NULL` branch pe). Pehli baar measure **Din 3** pe hua — duplicate window aur reclaim latency dono usi `30 s` ke against `[MEASURED-R]` | Provenance line `D-22` Cost 1 me likhi hui hai: *"chosen Din 2 ahead of measurement, first measured Din 3."* **Untick nahi — honest partial** |
| Measured | Always-failing job ka `attempts` `dead_letter` pe | ✅ **aur expected se zyada** | **`3`** normal path pe (`104`, `105`) aur **`4`** us path pe jahan row bound cross karke queue me wapas aayi (`108`) `[MEASURED-R]` → `P-27`, `D-23` | — |
| Measured | Week close pe `running` rows ka count | ✅ | **`0`**, aaj `[MEASURED]`. Hafta `3` se shuru hua tha (`41`, `63`, `65`) | — |
| Measured | Reaper run jo 41 · 63 · 75 ko **alag** karta hai | 🟡 **partial, aur ye `P-20` hai** | `41`/`63`/`65` reclaim hue, `75` untouched raha — **outcome** measured hai `[MEASURED-R]`. Par **ek hi output me chaaron ka farq nahi dikha**, aur dikh bhi nahi sakta tha: `75` kabhi candidate nahi thi, to reaper usko print hi nahi karta. `75` ka *not-matched* verdict ek alag `select` se aata hai | **Structural, deferred: `P-20`** — reaper ka output candidates ke bahar kuch nahi bol sakta. Chahiye: ek explicit *"not a candidate, and why"* line, ya accept karo ki verdict do queries se aata hai |
| Measured | Expiry branch (`claimed_at < now() - lease`) ne kabhi match kiya | 🟡 **partial** | Din 2 pe **zero** rows (sab `IS NULL`) `[INFERRED from dump]`. Din 3 pe wo branch hi job 95 ka reclaim laayi `[MEASURED-R]` — to branch exercise ho gaya, sirf uss din nahi jis din wo likhi gayi | — |
| Likha | `D-22` + `D-23`, har `Cost` line pe ek provenance tag | ✅ | Aaj, headings line `1080` / `1260`, disk se verify `[MEASURED]` | — |
| Likha | `D-06` + `D-21` amendments, **append** karke | ✅ | Aaj; purani lines verbatim, amendment neeche apni date ke saath | — |
| Likha | `P-19`..`P-27` apne apne din pe | ✅ | Nau nayi entries, ek bhi Din 6 pe nahi ghisatai gayi `[MEASURED, grepped]` | — |
| Likha | `MAP.md` / `LEARNING_LOG.md` / `CURRENT_WEEK.md` / handoff | ✅ | Aaj; gitignored do files kholke padhi | — |
| Likha | Har din ka log entry with filled 📊 Measured | ✅ | Din 1–6, chhe entries | `💡`/`🧠` sections **reviewer ke likhe hue hain** — **slipped, owner: user.** Chahiye: har section apne shabdon me, reviewer ka text pehle bina kholе |
| Carried debt | Stage Day exit criteria — paanch written Week 2 answers | 🔴 **slipped, dasva carry** | Kabhi likhe nahi gaye; `CURRENT_WEEK.md` ka apna blocking rule das baar override hua | **Slipped, not deferred.** Chahiye: `Week 3 Din 1, Step 0 se pehle, user ke haath se`. Gyaarva slip ho to item delete karo |
| Carried debt | Part B answers har din, step se pehle | 🔴 **fail** | `0/6 · 0/6 · 5/6 · 0/6 · 7/7 (mtime measurements ke baad, `E8`) · 0/7`. Aaj answers file **exist hi nahi karti** `[MEASURED]` | **Chahiye:** file **Step 0 se pehle** banao, saat headings, `idk` allowed aur recorded — par `idk — <poora sahi jawab>` **nahi**, wo self-inflicted zero hai |
| Carried debt | Teesra cleanup check (`backend_start`) | 🔴 **fail, do din** | BRIEF me do baar aaya, dono din report nahi hua. PID `37` container restart se gaya `[MEASURED]` | **Chahiye:** ek line, har din close pe, output log me |
| Carried debt | `DDIA_CH8_LINKS.md` lines 10–13 confirm | 🔴 **slipped, paanchva din** | File aaj touch nahi hui | **Chahiye:** chaar lines apne shabdon me, Week 3 |
| Carried debt | Week 1 Din 7 ka log entry · `2026-08-24` ka record | 🔴 **carried, ab decision maangta hai** | Din 7 *chala* (Din 1 ke bench ne uske numbers reproduce kiye) par kya chala wo unrecoverable | **Deferred with owner: user, Week 3 Din 1.** Do endings: likho jo bacha hai usse, **ya** likh do ki kabhi nahi banega aur carry band karo |

**Kitne clean, kitne nahi:** **`14` ✅ · `4` 🟡 partial · `5` 🔴** = 23 items. Teeno partial *honest*
partials hain (lease provenance, reaper output ka structural limit, expiry branch ka timing) aur unme se ek bhi
missing kaam nahi hai — teeno likhe hue hain. **Paanchon 🔴 process items hain, build ya measurement nahi** —
aur wo hi hafte ka asli pattern hai: **code shipped aur measure hua; likhne aur discipline wale items slip
hote rahe.**

---

### Week 2 handoff — Week 3 ka input

Teen headings, exactly ye teen, Stage Day wale handoff ke **same shape** me. File:
`docs/daily/WEEK_02_HANDOFF.md`.

| Heading | Matlab | Likha? |
|---|---|---|
| **What Stuck** | bina notes ke, scratch se rebuild kar sakta hoon | ✅ **5 items** — lease ek deadline hai jo claim ke waqt likhi jaati hai (`claimed_at`) · reaper ek alag process kyun hona chahiye · **har** status transition pe compare-and-set · `NOT VALID` + `VALIDATE` se zero-downtime `CHECK` update · bounded retry + backoff + equal jitter aur jitter floor ka quantum se upar hona. ⚠️ **Ye list abhi ek claim hai jiske peeche test nahi hai**, kyunki iss hafte ke `💡` sections reviewer ke likhe hue hain |
| **What Needs Reinforcement** | pehchaan leta hoon, par viva pressure me derive nahi kar paunga | ✅ **5 items** — dead node vs slow node · SQL me `NULL` ka three-valued logic · `now()` = transaction-start time · fencing token vs compare-and-set · `count(*) > 1` ke paanch causes |
| **What Week 3 Must Not Assume** | wo baatein jo Week 3 taken-for-granted na le — isme toote hue din ka naam bhi | ✅ **4 items** — contract #2 **abhi bhi unprotected** hai · `attempts = 4` ka overdraft (`P-27`) · shutdown-lease interaction **untested** hai · heartbeat ki event-loop dependency (`P-21`). **Koi din naam se nahi gaya**, kyunki koi din toota nahi — dono attribution errors cancel hue aur closing counts independently verify hue (upar E5 wali table) |

**Dono definitions file me likhi hui hain**, memory me nahi — `WEEK_01_HANDOFF.md` ke same shape me, aur pehli
do headings word-for-word same. Teesri sirf week number me alag hai.

**Aur ye check chala aur pehli baar FAIL hui, phir fix hui — likhna zaroori hai kyunki ye ek differential check
ka poora point hai `[MEASURED]`.** Pehla run:

```
Select-String -Path docs\daily\WEEK_01_HANDOFF.md,docs\daily\WEEK_02_HANDOFF.md -Pattern '^## What'
  WEEK_01_HANDOFF.md: ## What Stuck / ## What Needs Reinforcement / ## What Week 2 Must Not Assume
  WEEK_02_HANDOFF.md: (kuch nahi)          <- teen headings the, par '## 1. What Stuck' shape me
```

Headings `## 1.` / `## 2.` / `## 3.` prefix ke saath likhi gayi thi — **content sahi tha aur shape nahi**, to
*"pehli do headings word-for-word identical"* wali condition toot rahi thi aur Week 3 usko usi tarah consume
nahi kar paata jaise iss hafte ke Din 1 ne Week 1 ka handoff kiya. **Numbering hata di, dobara chalayi, chhe
lines aayi, teen-teen per file.** Aur `What Week 3 Must Not Assume` me do items add hue jo BRIEF ne naam se
maange the aur pehle draft me nahi the: **`P-23` ka open-exercise half**, aur **chain ke attribution finding**
(kyunki *"kis din ka number bharose ke layak nahi"* ka jawab *"kisi ka nahi, par method badalna hai"* hai). **Ye teesri heading Week 3 Din 1 ka
problem statement hai**, exactly jaise Week 1 ki teesri heading iss hafte ke Din 1 ka thi.

---

### Hafte ke process findings

Ye numbers nahi hain, par ye hi batate hain ki hafte ka evidence kitna bharosemand hai.

| Kya | Kitni baar / kahan | Detail |
|---|---|---|
| **Seal tooti (E8)** — kisi step ka KEY section measurement se **pehle** khula | **Direct evidence: `0`. Indirect: `1` confirmed, `4` unknowable.** | Seal ka toot-na sirf tab detect hota hai jab answers file ka mtime measurement se **pehle** ka ho — aur wo test chalane ke liye file honi chahiye. **Din 5:** file thi, mtime `15:03`, migrations `14:27` aur dono `dead_letter` transitions `14:50–14:51` ke **baad** `[MEASURED-R]` → **reconstruction, prediction nahi.** **Din 1, 2, 4, 6:** koi file hi nahi, to seal ka status **unknowable** hai — aur wo `0` nahi hai. **Din 3** ek hi din hai jahan answers pehle likhe gaye aur score `5/6` aaya. Ye correlation iss hafte ka sabse saaf signal hai |
| **Decorative check ship hui (E7)** — *mechanism maujood* aur *mechanism ghayab* column same nikle | **`3`, aur teeno alag layer pe** | (i) **Din 2 Step 6** — reaper ka expected output ek **khaali** output tha, aur khaali output ek mara hua reaper, ek truncated capture, aur ek sahi guarded reaper, teeno deta hai (`P-20`). **Rewrite:** per-pass `candidates=0 reclaimed=0` line, jo Din 3 pe ship hui aur usi din kaam bhi aayi. (ii) **Din 4 Part C — *"the cap engages"*** — `MAX_ATTEMPTS = 3` par wo row na pass ho sakti thi na fail (`P-26`), parameter-level decorative check. **Rewrite:** cap ko test karne ke liye `MAX_ATTEMPTS` badalna padega, warna row hatao. (iii) **Din 5 Step 7 — shutdown vs lease** — handler `8 s` < lease `30 s`, to check ka *subject* hi absent tha; wo pass hui aur mechanism produce hi nahi hua. **Rewrite:** `payload {"seconds": 45}`, jo `D-22` ke `Revisit when` me likha hua hai |
| **Scope pressure (E9)** — mann kiya ki agla item aaj hi kar lein | **`3` resist hue, `1` earlier me nahi** | Aaj resist hue: (i) `attempts < :max` claim gate me daalna kyunki `P-27` chubh raha hai — wo `src/` change hota **uss din jab hafte ke numbers freeze hote hain**, aur usko ek sweep chahiye; (ii) `payload {"seconds": 45}` wala run *"ek minute ka hai"* — wo band ho rahi chain me execution rows add karta; (iii) Week 3 ka pehla din aaj plan karna — Week 3 ka plan **iss hafte ke handoff par** khada hai aur handoff aaj hi likha gaya, to pehle plan karna handoff ko decoration bana deta. **Aur ek pehle resist nahi hua:** Din 5 pe fencing token ka lalach — wo build nahi hua (sahi), par uska absence ab `D-22` Cost 7 ka untested case hai |
| **Score wapas aaya?** — Week 1 me chaar din bina score gaye the, aur missing score ek acha score nahi hota | **6 me se 4 din score ke saath, aur unme se 2 shunya** | Din 1 `0/6` · Din 2 `0/6` · Din 3 **`5/6`** · Din 4 `0/6` · Din 5 **scoring skipped by request** (provenance likhi gayi) · Din 6 `0/7`. **To "score wapas aaya" ka jawab: haan, score likha gaya — par jis cheez ko wo naapta hai wo teen din maujood hi nahi thi.** `0/6` aur "answers submit nahi hue" ek hi number dete hain aur wo do bilkul alag failures hain; iss hafte ka `0` teen baar **absence** ka tha, galat jawab ka ek baar bhi nahi |

---

### ❓ Week 3 ki taraf — pehla sawaal

**Key kis cheez ki identity hai — job ki, ya *dispatch* ki? Aur ye sawaal pehle aata hai, "key kaise banayein"
se pehle.**

Iss hafte ke do measurements isko forced karte hain, aur wo opposite directions me pull karte hain:

- **Job 95:** ek job, do **overlapping** dispatch, dono legal (`14.783 s` overlap `[MEASURED-R]`). Dedup ko in
  dono ko **ek** maanna hai, warna side effect do baar hoga.
- **Job 98:** ek job, teen **sequential** dispatch, aur wo `D-23` ka **design** hai — bounded retry. Dedup ko
  in teeno ko **alag** maanna hai, warna pehla retry hi block ho jaayega aur contract #3 toot jaayega.

**To ek hi column dono nahi kar sakta.** Job-level key retry ko maar deta hai; dispatch-level key job 95 ke
dono dispatch ko alag keys deta hai aur kuch nahi rokta. **Jo cheez in dono ko separate karti hai wo "kaunsa
attempt" nahi hai — wo "kaunsa claim" hai**, aur wahi identifier hai jo `D-21` ne Week 3 pe defer kiya aur
`D-22` Cost 11 ne *overdue* declare kiya. **Isi liye dono ek saath decide hote hain.**

Aur uske turant peeche doosra sawaal, jo Week 0 Din 5 ka seedha continuation hai: **dedup ka check kis cheez pe
atomic hoga?** Agar wo *"is key already present?"* padh ke phir likhta hai, to wo **check-then-act** hai aur
concurrency me toot jaata hai — Week 0 ka lost update, naye kapde me. Teen shapes maujood hain aur teeno ki
keemat alag hai: `UNIQUE` constraint (database faisla karta hai, loser ko error milta hai),
`INSERT ... ON CONFLICT DO NOTHING` ka `rowcount` (wahi compare-and-set shape jo `D-06` ne chuna, aur jiska
`rowcount` padhna Relay me already habit hai), ya handler ke andar ek guard — jo `MAP.md` T6 ki **aakhri** row
hai, *state outside the database*, jahan koi isolation level madad nahi karta.

**Aur ek constraint jo Week 3 ko iss hafte se inherit hoti hai:** key ko **bound ke baad ke ek extra dispatch**
ko bhi survive karna hai (`P-27`, job `108`), sirf bound ke andar ke retries ko nahi.

*(Week 3 ka preview plan me ek line hai: idempotency key, aur crash/retry interleavings ke upar ek property
test. Iss hafte ke evidence me se wo sawaal jo uss line ko sharp karta hai — wo upar hai.)*

---

