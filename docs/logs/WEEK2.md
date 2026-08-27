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