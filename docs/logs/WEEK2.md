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

## Din 3 — 🎯 Zinda par slow worker: ek job, do execution (`____`)

**Original goal (from the plan):** `____`

**Goal met?** `____` — yes / no / partial, aur partial pe kaunsa hissa.

**Anything else learned?** `____` — goal-met se alag field.

---

### 📊 Measured / Observed

**Opening check (`P-13`, `P-06`), plus aaj ka extra:**

| Kya | Value | Label |
|---|---|---|
| worker processes / `idle in transaction` / connections | `____` | `____` |
| 41/63/65 ki current state (Din 2 ke baad) | `____` | `____` |
| job 75 abhi bhi `failed`? | `____` | `____` |
| Aaj ki seeded stuck rows ke ids | `____` | `____` |

**Paanch-sawaal ka diagnosis — isi fixed order me, aur count iske BAAD (E3, `P-12`, `P-18`):**

| # | Sawaal | Jawab | Label |
|---|---|---|---|
| 1 | Do distinct `worker_id`, overlapping `executed_at`? | `____` | `____` |
| 2 | Lease expiry versus handler duration — **ek hi clock** me | `____` | `____` |
| 3 | Reaper uss window me actually chala? | `____` | `____` |
| 4 | Row uss waqt claimable thi? | `____` | `____` |
| 5 | Log poora hai (`python -u`, aakhri line adhoori nahi)? | `____` | `____` |

**Duplicate count — sirf paanchon jawab likhne ke BAAD:**

| Run | Duplicate count | Overlap window proven? | Label |
|---|---|---|---|
| Run 1 — heartbeat **ke bina** | `____` | `____` | `____` |
| Run 2 — heartbeat **ke saath** | `____` | `____` | `____` |

**Zero ka matlab:** zero duplicates ka matlab hai overlap window **bani hi nahi** — ye nahi ki system safe
hai. Jis sawaal pe "nahi" mila wahi aaj ka result hai: `____` · Agle run me badalne wala **ek** variable
(handler duration / lease duration / reaper poll interval): `____`

**Aaj ye likhna hai (plan ka Din 3 obligation):**

| Kya | Value / text | Label |
|---|---|---|
| Chuna hua handler duration, apne reason ke saath | `____` | — |
| Dono run ka expiry-se-completion gap | `____` | `____` |
| Heartbeat ke teen faisle — interval | `____` | — |
| Heartbeat ke teen faisle — guard | `____` | — |
| Heartbeat ke teen faisle — sender (kaun bhejta hai) | `____` | — |
| Teeno ki cost | `____` | — |
| Pehle worker ke mark statement ka **verbatim** output | `____` | `____` |
| Heartbeat ne window **narrow** kiya — kitna, aur wo band kyun nahi hua | `____` | `____` |
| `count(*) > 1` ka matlab badalna (`P-11`) — aaj ka evidence | `____` | `____` |

**Closing reconciliation** — opening counts **Din 2 ke log se**:

| Line | Value |
|---|---|
| opening counts (Din 2 log) | `____` |
| `+` aaj seed/enqueue hui rows (ids naam se) | `____` |
| `=` closing counts, aur `psql` ka actual | `____` |
| Match? | `____` |
| `job_executions` delta — duplicate rows isme count hote hain | `____` |

Match na kare to finding (E5). Pehla suspect ek bhoola hua teesra worker (`P-13`), doosra suspect reaper ka
ek extra run: `____`

**Cleanup:** teen stdout capture files (worker A, worker B, reaper) delete hui? `____` — andar ka relevant
output pehle upar copy hua? `____` · Probe rows delete nahi hoti, ids: `____`

**`DECISIONS.md` me aaj kuch nahi.** `D-21` ka amendment aur `D-22` dono Din 6 pe. Aaj sirf evidence banta
hai.

---

### 💡 What I Understood

`____`

---

### 🧠 Self-Check (honest — `____` / `____` self-answered)

`____`

**Corrections:**

| # | I said | Actual | The transferable lesson |
|---|---|---|---|
| `__` | `____` | `____` | `____` |

---

### 🚧 Unresolved / Follow-ups

**New, from today:** `____`

**Deliberately open (owner ke saath):** `____`

**Slipped (aur specifically kya chahiye):** `____`

**Carried forward, unchanged:** `____`

---

### ❓ Question / Next Thought

`____`

---

## Din 4 — Bounded retry, backoff, jitter (`____`)

**Original goal (from the plan):** `____`

**Goal met?** `____` — yes / no / partial, aur partial pe kaunsa hissa.

**Anything else learned?** `____` — goal-met se alag field.

---

### 📊 Measured / Observed

**Opening check (`P-13`, `P-06`):**

| Kya | Value | Label |
|---|---|---|
| worker processes / `idle in transaction` / connections | `____` | `____` |
| `attempts` ka current state (kitni rows non-zero) | `____` | `____` |

**Aaj ye likhna hai (plan ka Din 4 obligation):**

| Kya | Value / text | Label |
|---|---|---|
| `attempts` increment point ka faisla (claim pe ya failure pe), **apni cost ke saath** | `____` | — |
| *"abhi nahi"* store karne ka faisla, apni cost ke saath | `____` | — |
| Backoff ka formula, **verbatim** | `____` | — |
| Jitter ka formula, alag se | `____` | — |
| Jitter kyun — apne shabdon me | `____` | — |
| Retry ka `status` write compare-and-set guard ke saath? affected-row-count | `____` | `____` |
| Ek always-failing job ke **measured inter-attempt gaps** (`executed_at` diffs, `Etc/UTC`) | `____` | `____` |
| Kai jobs ka **jitter spread** | `____` | `____` |
| Bounded-out job pe final `attempts` | `____` | `____` |
| Log poora hai — failure lines ka count versus `attempts` (`P-18`) | `____` | `____` |

**M1 — `____`**

```
____
```

**Closing reconciliation** — opening counts **Din 3 ke log se**:

| Line | Value |
|---|---|
| opening counts (Din 3 log) | `____` |
| `+` aaj enqueue hui `boom` jobs (ids naam se) | `____` |
| `=` closing counts, aur `psql` ka actual | `____` |
| Match? | `____` |
| `job_executions` delta — har attempt ek row | `____` |

Match na kare to finding (E5): `____`

**Cleanup:** worker stdout capture delete hua? `____` — output pehle upar copy hua? `____` · `boom` jobs ke
ids (rows delete nahi hoti): `____`

**`DECISIONS.md` me aaj kuch nahi.** `D-23` Din 6 pe likhi jaati hai, aaj ke measured delays ke saath.

---

### 💡 What I Understood

`____`

---

### 🧠 Self-Check (honest — `____` / `____` self-answered)

`____`

**Corrections:**

| # | I said | Actual | The transferable lesson |
|---|---|---|---|
| `__` | `____` | `____` | `____` |

---

### 🚧 Unresolved / Follow-ups

**New, from today:** `____`

**Deliberately open (owner ke saath):** `____`

**Slipped (aur specifically kya chahiye):** `____`

**Carried forward, unchanged:** `____`

---

### ❓ Question / Next Thought

`____`

---

## Din 5 — `dead_letter` + graceful shutdown (`____`)

**Original goal (from the plan):** `____`

**Goal met?** `____` — yes / no / partial, aur partial pe kaunsa hissa.

**Anything else learned?** `____` — goal-met se alag field.

---

### 📊 Measured / Observed

**Opening check (`P-13`, `P-06`):**

| Kya | Value | Label |
|---|---|---|
| worker processes / `idle in transaction` / connections | `____` | `____` |
| `attempts` aur `status` ka current spread | `____` | `____` |

**Aaj ye likhna hai (plan ka Din 5 obligation):**

| Kya | Value / text | Label |
|---|---|---|
| Constraint ka **purana naam aur purani definition, verbatim** | `____` | `____` |
| Ek migration ya do — faisla, apni cost ke saath | `____` | — |
| `NOT VALID` ke baad `VALIDATE CONSTRAINT` — dono ka output | `____` | `____` |
| `downgrade` ka actual output **ek `dead_letter` row ke saath** | `____` | `____` |
| Terminal writer ka faisla (A ya B), apni cost ke saath | `____` | — |
| `max_attempts` → `dead_letter` transition ka guard + affected-row-count | `____` | `____` |
| Always-failing job ka `attempts` count `dead_letter` pe pahunchte waqt | `____` | `____` |
| Shutdown pe lease ka faisla, apni cost ke saath | `____` | — |
| Teen durations ek line pe: handler · lease · grace period | `____` | `____` |
| SIGTERM ke baad naye `running` rows | `____` | `____` |
| `ACCESS EXCLUSIVE` measurement ka result — **ya** saaf likha hua ki attempt fail hua aur procedure kya thi | `____` | `____` |
| Log poora hai — `Claimed job` lines ka count, aur file ka aakhri line (`P-18`) | `____` | `____` |

**Shutdown ek lease ka sawaal hai, signals ka nahi (`P-15`):** grace period handler se bandha hai, aur
Relay handler ko bound nahi karta. Aaj ka evidence: `____`

**Closing reconciliation** — opening counts **Din 4 ke log se**. Kabhi `max(id)` se nahi:

| Line | Value |
|---|---|
| opening counts (Din 4 log) | `____` |
| `+` aaj enqueue hui probe rows (ids naam se) | `____` |
| `±` `dead_letter` me gayi rows (paanchwan bucket ab exist karta hai) | `____` |
| `=` closing counts, aur `psql` ka actual — **paanchon** buckets | `____` |
| Match? | `____` |
| `job_executions` delta | `____` |

Match na kare to finding (E5): `____`

**Cleanup:**
- Worker aur reaper stdout capture delete hua? `____` — relevant output pehle upar copy hua? `____`
- Lock-queue measurement ke liye jaan-boojh ke banayi `idle in transaction` session band hui —
  `COMMIT`/`ROLLBACK` se ya `pg_terminate_backend` se? `____` · **PID naam se:** `____`
  *(`P-06` ka pura sabaq: chhoda hua session locks pakde baitha rehta hai, aur koi participant khud usko
  resolve nahi kar sakta. Aaj wo session jaan-boojh ke bani thi, to uska hatana bhi jaan-boojh ke likha
  jaata hai.)*
- `boom` jobs aur `dead_letter` probe row ke ids (rows delete nahi hoti): `____`

**`DECISIONS.md` me aaj kuch nahi.** `D-06` ka amendment Din 6 pe. Aaj sirf evidence — `D-06` ka Cost 4 ek
**prediction** hai, aur aaj ka output batata hai wo prediction poora tha ya adhoora: `____`

---

### 💡 What I Understood

`____`

---

### 🧠 Self-Check (honest — `____` / `____` self-answered)

`____`

**Corrections:**

| # | I said | Actual | The transferable lesson |
|---|---|---|---|
| `__` | `____` | `____` | `____` |

---

### 🚧 Unresolved / Follow-ups

**New, from today:** `____`

**Deliberately open (owner ke saath):** `____`

**Slipped (aur specifically kya chahiye):** `____`

**Carried forward, unchanged:** `____`

---

### ❓ Question / Next Thought

`____`

---

## Din 6 — Close: reconcile, likho, handoff (`____`)

**Original goal (from the plan):** `____`

**Goal met?** `____` — yes / no / partial, aur partial pe kaunsa hissa.

**Anything else learned?** `____` — goal-met se alag field.

---

### 📊 Measured / Observed

**Opening check (`P-13`, `P-06`):**

| Kya | Value | Label |
|---|---|---|
| worker processes / `idle in transaction` / connections | `____` | `____` |

**Aaj ka grep output — number assign karne ke din chalta hai, plan likhne ke din nahi (E6):**

```
grep -n "^## \`\?D-" docs/DECISIONS.md
____

grep -n "^## P-" docs/PROBLEMS.md
____
```

| Kya | Value |
|---|---|
| Grep plan ke expected ranges se match karta hai? | `____` |
| Aaj assign hue `D-` numbers | `____` |
| Aaj assign hue `P-` numbers | `____` |
| Collision mili? (naya entry hilta hai, purana kabhi nahi) | `____` |
| Dangling citation mili? | `____` |

**Doc-sync — kya actually likha gaya (files kholke check, `git status` se nahi):**

| File | Kya gaya | Ho gaya? |
|---|---|---|
| `docs/DECISIONS.md` — `D-22` (lease duration + handler timeout, ek decision) | `____` | `____` |
| `docs/DECISIONS.md` — `D-23` (retry policy: increment point, backoff formula, jitter ka reason) | `____` | `____` |
| `docs/DECISIONS.md` — `D-06` amendment (`dead_letter` via `NOT VALID` + `VALIDATE CONSTRAINT`) | `____` | `____` |
| `docs/DECISIONS.md` — `D-21` amendment (`count(*) > 1` ka matlab) | `____` | `____` |
| Har naye entry ka **non-empty `Cost`**, aur har `Cost`/`Rejected` line pe ek provenance tag | `____` | `____` |
| `docs/PROBLEMS.md` — Din 1–5 ki bachi hui entries | `____` | `____` |
| `docs/MAP.md` — per naye entry ek index row, **reasoning nahi** | `____` | `____` |
| `docs/LEARNING_LOG.md` — open-items table, Week 2 row, next-free numbers | `____` | `____` |
| `docs/roadmap/CURRENT_WEEK.md` — week status table + pointer Week 3 pe | `____` | `____` |
| `docs/daily/WEEK_02_HANDOFF.md` — teen headings, dono definitions, content | `____` | `____` |
| Commit — staged paths naam se, `.` kabhi nahi | `____` | `____` |

`docs/roadmap/` aur `docs/daily/` gitignored hain — wo do files `git status` me dikhengi hi nahi, isliye
kholke check hoti hain.

**Cleanup:** aaj naye probe rows nahi bante. Reconcile ke liye koi temporary capture file bani? `____` —
delete hui? `____` — output pehle log me copy hua? `____` · Hafte bhar ki probe rows **delete nahi** hoti,
unke ids aaj ki chain me count hote hain: `____`

---

### 💡 What I Understood

`____`

---

### 🧠 Self-Check (honest — `____` / `____` self-answered)

`____`

**Corrections:**

| # | I said | Actual | The transferable lesson |
|---|---|---|---|
| `__` | `____` | `____` | `____` |

---

### 🚧 Unresolved / Follow-ups

**New, from today:** `____`

**Deliberately open (owner ke saath):** `____`

**Slipped (aur specifically kya chahiye):** `____`

**Carried forward, unchanged:** `____`

---

### ❓ Question / Next Thought

`____`

---

## Week close — reconcile chain aur handoff

Din 6 ka closing **hi** hafte ka closing hai. Chain ka shape ek hi hai: **week opening + har din ka delta =
aaj ke actual counts.** Chain kabhi `max(id)` se nahi jodi jaati — id contiguity `jobs` ka invariant nahi
hai, aur `P-05` hi uska evidence hai.

**Full reconcile chain:**

| Line | Kahan se | Value |
|---|---|---|
| Week opening counts | BENCH block (ya E2 ka naya baseline) | `____` |
| `+` Din 1 delta | Din 1 log entry | `____` |
| `+` Din 2 delta | Din 2 log entry | `____` |
| `+` Din 3 delta | Din 3 log entry | `____` |
| `+` Din 4 delta | Din 4 log entry | `____` |
| `+` Din 5 delta | Din 5 log entry | `____` |
| `=` expected closing | arithmetic | `____` |
| aaj ke `psql` counts — **paanchon** status buckets + total | aaj ka opening check | `____` |
| `job_executions` — opening + per-din delta = aaj ka count | log + aaj ka output | `____` |
| **Chain juda?** | — | `____` |

**Week close pe `running` rows — ye ek DoD item hai, aur zero ho ya na ho, dono cases likhe jaate hain:**

| Kya | Value | Label |
|---|---|---|
| `running` count at close | `____` | `____` |
| Uske ids (agar zero nahi) | `____` | `____` |
| Ye ids Week 3 ka input hain — handoff me gaye? | `____` | — |

Non-zero `running` ka matlab hai hafte ke end pe bhi kaam atka pada hai. Usko *"reaper chalake saaf kar
diya"* karke count zero banana **arithmetic adjust karna** hai — wo E5 hai aur wo nahi hota.

**Sequence:**

| Kya | Value | Label |
|---|---|---|
| `jobs_id_seq` `last_value` | `____` | `____` |
| `max(id)` | `____` | `____` |
| Gap — aur wo `P-05` ka evidence hai | `____` | `____` |

**Agar chain nahi judi (E5):** mismatch **finding ki tarah** likhi jaati hai, difference ko kisi din me fit
karke chain band nahi hoti.

| Kya | Value |
|---|---|
| Kaunsa din toota | `____` |
| Kitna difference | `____` |
| Kya check kiya gaya (bhoola hua worker `P-13`, extra reaper run, delete hui row, consumed sequence value) | `____` |
| **Ye din handoff ki teesri heading me naam se gaya?** | `____` |

Toote hue din ka naam Week 2 ke handoff ki teesri heading me jaata hai, kyunki Week 3 ko pata hona chahiye
ki **kis din ka number bharosa ke layak nahi hai**.

---

### Definition of Done — week close pe audit

Plan ka koi box shipped file me ticked nahi tha. Ab har item ka ek status hai, aur **har untick ek line
maangta hai**: *deliberately deferred* apne **owner** ke saath, **ya** *slipped* uske saath jo usko
**specifically** chahiye. Do me se ek — dono nahi, koi nahi bhi nahi.

| Group | DoD item | Status | Evidence | Untick ho to: deferred (owner) / slipped (kya chahiye) |
|---|---|---|---|---|
| Build | `____` | `____` | `____` | `____` |
| Measured | Centrepiece duplicate count | `____` | `____` | `____` |
| Measured | Reaper ki reclaim latency | `____` | `____` | `____` |
| Measured | Chuni hui lease duration + uske peeche ka measurement | `____` | `____` | `____` |
| Measured | Always-failing job ka `attempts` `dead_letter` pe | `____` | `____` | `____` |
| Measured | Week close pe `running` rows ka count | `____` | `____` | `____` |
| Measured | Reaper run jo 41 · 63 · 75 ko **alag** karta hai | `____` | `____` | `____` |
| Likha | `____` | `____` | `____` | `____` |
| Carried debt | Stage Day exit criteria (slip yahan zinda rehta hai) | `____` | `____` | `____` |

**Kitne clean, kitne nahi:** `____`

---

### Week 2 handoff — Week 3 ka input

Teen headings, exactly ye teen, Stage Day wale handoff ke **same shape** me. File:
`docs/daily/WEEK_02_HANDOFF.md`.

| Heading | Matlab | Likha? |
|---|---|---|
| **What Stuck** | bina notes ke, scratch se rebuild kar sakta hoon | `____` |
| **What Needs Reinforcement** | pehchaan leta hoon, par viva pressure me derive nahi kar paunga | `____` |
| **What Week 3 Must Not Assume** | wo baatein jo Week 3 taken-for-granted na le — isme toote hue din ka naam bhi | `____` |

---

### Hafte ke process findings

Ye numbers nahi hain, par ye hi batate hain ki hafte ka evidence kitna bharosemand hai.

| Kya | Kitni baar / kahan | Detail |
|---|---|---|
| **Seal tooti (E8)** — kisi step ka KEY section measurement se **pehle** khula | `____` | Wo step reconstruction ki tarah score hota hai, aur wo yahan naam se likha jaata hai: `____` |
| **Decorative check ship hui (E7)** — *mechanism maujood* aur *mechanism ghayab* column same nikle | `____` | Kaunsi check, aur uska rewrite: `____` |
| **Scope pressure (E9)** — mann kiya ki agla item aaj hi kar lein | `____` | Kaunsa item, aur wo signal kis hard problem ko avoid kar raha tha: `____` |
| **Score wapas aaya?** — Week 1 me chaar din bina score gaye the, aur missing score ek acha score nahi hota | `____` | Kitne din score ke saath: `____` |

---

### ❓ Week 3 ki taraf — pehla sawaal

`____`

*(Week 3 ka preview plan me ek line hai: idempotency key, aur crash/retry interleavings ke upar ek property
test. Iss hafte ke evidence me se wo sawaal jo uss line ko sharp karta hai — wo yahan.)*