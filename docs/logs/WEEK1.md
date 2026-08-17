# WEEK 1 — Relay Core: Queue banao, at-least-once ka matlab dekho

## Day 1 — Schema design + Week 0 remaining (2026-08-14)

**Original goal (from the plan):** clear Week 0's four pending items (Part A), then decide every column of the `jobs` table and ship it as a migration (Part B). No endpoints, no worker.

**Anything else learned?** Yes, and it was the most valuable part of the day — see the `server_default` bug and P-06. Neither was on the plan. Recording separately from the goal, because learning something is not the same as finishing what was started.

---

### 📊 Measured / Observed

Nothing today was a performance measurement. Everything below is a **verification** — a claim that was previously inference, and now is not.

**M1 — Live schema (`\d jobs`), after `upgrade head`**

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `bigint` | not null | `nextval('jobs_id_seq'::regclass)` |
| `type` | `text` | not null | — |
| `payload` | `jsonb` | not null | `'{}'::jsonb` |
| `status` | `text` | not null | `'pending'::text` |
| `attempts` | `integer` | not null | `0` |
| `created_at` | `timestamp with time zone` | not null | `now()` |

```
Indexes:
    "jobs_pkey" PRIMARY KEY, btree (id)
Check constraints:
    "jobs_status_check" CHECK (status = ANY (ARRAY['pending'::text, 'running'::text,
                                                  'succeeded'::text, 'failed'::text]))
```

All six columns `NOT NULL`. No index beyond the primary key. No extra columns.

**M2 — Migration reversibility**

```
alembic downgrade -1   → INFO  Running downgrade 81b6e20c9ea7 -> , create_jobs_table
\dt jobs               → Did not find any relation named "jobs".
alembic upgrade head   → INFO  Running upgrade  -> 81b6e20c9ea7, create_jobs_table
\d jobs                → identical to M1
```

**M3 — Model/DB drift check**

```
alembic check → No new upgrade operations detected.
```

Meaningful only *after* the cleanup in M6 — before that it failed on Week 0's leftover tables.

**M4 — Enum values inside a transaction (PG 16)**

```sql
BEGIN;
ALTER TYPE t_enumtest ADD VALUE 'c';       -- OK
CREATE TABLE tt_enumtest (x t_enumtest);   -- OK
INSERT INTO tt_enumtest VALUES ('c');      -- ERROR
```
```
ERROR:  unsafe use of new value "c" of enum type t_enumtest
HINT:   New enum values must be committed before they can be used.
```

**M5 — Does `ADD COLUMN ... DEFAULT` rewrite the table? (50,000 rows)**

`relfilenode` changes on rewrite, so it is a direct indicator.

| Operation | `relfilenode` | Rewrite? |
|---|---|---|
| baseline | 24660 | — |
| `ADD COLUMN c1 integer NOT NULL DEFAULT 0` | 24660 | **No** |
| `ADD COLUMN c2 timestamptz NOT NULL DEFAULT clock_timestamp()` | **24665** | **Yes** |

**M6 — `pg_stat_activity` during a hung `DROP TABLE`**

| PID | `state` | `wait_event_type` | `wait_event` |
|---|---|---|---|
| 38 | `idle` | `Client` | `ClientRead` |
| 45 | `idle in transaction (aborted)` | `Client` | `ClientRead` |
| 53 | `idle in transaction` | `Client` | `ClientRead` |
| 61 | `active` | `Lock` | `transactionid` |
| 1724 | `active` | `Lock` | `relation` |

Leftover data before dropping: `counters` had 1 row (`foo = 102`), `doctors` had 3 (Alice `t`, Bob `t`, Carol `f`, all `shift_id = 1234`).

---

### 💡 What I Understood

**The `jobs` table is six decisions, not six columns.** Recorded in full as `D-03`..`D-08` in `DECISIONS.md`, including which alternative was rejected and, importantly, *when that alternative would be the correct choice*. Summary:

| Column | Chose | The reason that actually decided it |
|---|---|---|
| `id` | `bigint`, DB-generated | A primary key and an idempotency key are **different concerns**; merging them makes storage identity depend on client input |
| `type` | `text`, no DB constraint | The DB cannot see the worker's handler registry, so a constraint would enforce only part of the invariant |
| `payload` | `jsonb NOT NULL DEFAULT '{}'` | Free option value; normalisation also helps Week 3's payload hashing |
| `status` | `text` + `CHECK` | `DROP VALUE` does not exist for enums, and Alembic cannot autogenerate enum value changes |
| `attempts` | `integer NOT NULL DEFAULT 0` | Adding it later bundles the column decision with **backfill semantics** for in-flight rows |
| `created_at` | `timestamptz NOT NULL DEFAULT now()` | One clock, not one clock per API instance |

**The most reusable idea from the day: a constraint that enforces part of an invariant is worse than no constraint.** This came up three separate times (`type`, `status`, and Day 5's `doctors`), and it generalises: *a database constraint can only enforce an invariant that fits inside one row at one point in time.* Written up as `P-04`, because the ranking is counter-intuitive — the middle position is the dangerous one, since the confidence is real and the protection is not.

**Status transitions are not enforceable by the schema, and the guard is something I already had.** Neither `ENUM` nor `CHECK` can prevent `succeeded → running`, because judging a transition requires seeing the old *and* new value, and a `CHECK` sees only the current row. Enforcement lives in the claim statement:

```sql
UPDATE jobs SET status='running' WHERE id=$1 AND status='pending'
```

The `AND status='pending'` is not an optimisation — it is the transition guard, and the worker must check affected row count (`0` means someone else claimed it). This is **compare-and-set**, and it does three jobs at once: blocks illegal transitions, blocks double claims, and is atomic because check and write are one statement. That last property is what defeats Day 5's lost update. From my own Day 5 log: *"check-then-act is broken under concurrency."* A separate `SELECT` then `UPDATE` is check-then-act. This is not.

**`NOT NULL` is correctness here, not style.** `NULL + 1 = NULL`, so a nullable `attempts` means the retry counter never increments, `if attempts >= max_attempts` is never true, and jobs retry **forever** — contract #3 broken silently, by one missing keyword. Generalised: *counters, flags, and states should never be nullable; NULL should mean "unknown", and a counter's value is always known.*

**Two claims I had accepted were wrong, and measuring them changed the reasoning without changing the decision.** M4 showed enum values *can* be added inside a transaction on PG 16 — so the usual "enum migrations are painful" argument is largely false, and my choice of `CHECK` rests on `DROP VALUE` not existing, not on that. M5 showed `ADD COLUMN ... DEFAULT 0` does **not** rewrite the table (`relfilenode` unchanged at 50k rows) while a volatile default **does** — so the performance argument for adding `attempts` early was invalid, and the real justification is backfill semantics. Both cases: **the stated reason has to be the real reason, or the entry is worthless in six months.**

**`server_default` in SQLAlchemy quotes plain strings.** This produced a real latent bug, found by compiling the model's DDL rather than reading it:

```
payload JSONB DEFAULT '''{}''::jsonb' NOT NULL     ← wrong
status  TEXT  DEFAULT '''pending'''   NOT NULL     ← wrong
```

`server_default="'pending'"` became `DEFAULT '''pending'''` — a literal string *including* the quote characters. The `status` default would have **violated its own CHECK constraint**, and the `payload` default would have been invalid JSONB.

The live table was correct the whole time, because the *migration* used `sa.text(...)`. Only the model was wrong. So it would have surfaced later, in tests — `Base.metadata.create_all()` is common in test setup — as a table whose default breaks its own constraint, with the migration looking fine. Fix: wrap any SQL expression or quoted literal in `text()`.

The transferable lesson is about method, not SQLAlchemy: **the model and the database agreeing is not the same as either being right.** Compiling the DDL and reading the actual output is a five-second check that reading the source would never have caught.

**`alembic check` is a real tool and leftover tables destroy it.** Week 0's `counters` and `doctors` were still in the `relay` database, so every `alembic check` failed wanting to drop them, and the next `--autogenerate` would have silently produced a `DROP TABLE` migration. Two costs: an unread destructive migration, and a permanently-red check that I would have learned to ignore — losing drift detection exactly when it eventually matters.

**Choosing a sync driver for Alembic and async for the app was the right call.** The plan warned that async Alembic needs `env.py` surgery. Using `psycopg` in `alembic.ini` and `asyncpg` in `database.py` sidesteps the problem entirely. Noted in the shared context so future-me does not "fix" the mismatch.

---

### 🔗 Day 5's prediction came true by accident (full writeup: `P-06`)

`DROP TABLE counters, doctors;` hung with no error. M6 shows why: the psql sessions from the Week 0 Day 5 experiments were **still open**, with uncommitted transactions holding locks. PID 53 was still the culprit and PID 61 still the victim, in precisely the roles the Day 5 log recorded.

The Day 5 log had already predicted this as theory:

> *"by default Postgres will NOT kill an `idle in transaction` session... it can sit there indefinitely holding locks... T2 would have waited **forever**."*

Now measured rather than inferred. Three things the accident taught that the deliberate experiment did not:

1. **The blast radius reached something unrelated.** The original experiment was two transactions over `doctors` rows. What actually got blocked was a **DDL** statement needing `ACCESS EXCLUSIVE` — routine maintenance, with no visible link to the cause.
2. **A new wait event: `Lock` / `relation`** (table-level), distinct from Day 5's `Lock` / `transactionid` (waiting on another transaction to finish). The event name identifies *what kind* of thing is being waited on.
3. **`idle in transaction (aborted)` is a worse, distinct state.** PID 45 was in it — a transaction that had already failed, could accomplish nothing further, and was *still* holding locks because it was never rolled back.

Resolved with `pg_terminate_backend` on every stale session, after which `DROP TABLE` returned instantly. The fix had to come from **outside** every participant — none of the blocked sessions could act, and the culprit did not know it was one. Same shape as Day 2's conclusion about dead workers.

Direct relevance: Din 3's Trap 2 is this exact failure. If the worker holds its transaction open across execution, it *becomes* PID 53.

---

### 🧠 Self-Check

The nine items: `id`, `type`, `payload`, `status`, `attempts`, `created_at`, plus `NOT NULL` across all columns, `now()` vs `clock_timestamp()`, and who enforces status transitions.

**Errors in the material I was reviewing** (I brought Gemini-produced notes; the review found these, I did not):

| The notes said | Correct |
|---|---|
| "`attempts` column abhi daalo kyunki baad me `ADD COLUMN DEFAULT` table lock karta hai" | **Wrong on PG 16.** Constant default = no rewrite — **I measured this myself today (M5)**, `relfilenode` unchanged at 50k rows. Real reason to add early is backfill semantics |
| "Postgres enum me value add karna transactional migrations me jhamela hai" | **Largely wrong on PG 12+.** `ALTER TYPE ADD VALUE` runs inside a transaction — **measured (M4)**. Real constraint: the value cannot be *used* until commit. And the real argument against enum is that `DROP VALUE` does not exist |
| `CHECK` constraint changes are "seamless" | `ADD CONSTRAINT ... CHECK` takes `ACCESS EXCLUSIVE` **and scans the table**. Needs `NOT VALID` + `VALIDATE CONSTRAINT`. The notes contradicted themselves — locks were a danger in one section and seamless in another |
| `id` is `bigserial` vs `UUIDv4` | **False binary.** UUIDv7 is time-ordered *and* client-generatable. (PG 16 has no built-in `uuidv7()`; that arrived in PG 18) |

**Entirely absent from the material** (and these were the important ones): `NOT NULL` on any column; that neither `ENUM` nor `CHECK` enforces transitions; `now()` vs `clock_timestamp()` (the plan asked explicitly); sequence gaps and id-order ≠ commit-order; TOAST; and any connection to Week 0's own measured results.

choosing the sync driver for Alembic and async for the app, which avoided the `env.py` problem the plan warned about.

---

### ❓ Question / Next Thought

day 2 builds `POST /jobs`, and today's `id` decision sharpened the question waiting there. `D-03` deliberately kept `id` internal and DB-generated, on the grounds that a primary key and an idempotency key are different concerns. That leaves the duplicate-POST problem entirely unsolved for now: response lost in the network → client retries → two rows, both legitimate-looking, with nothing linking them.

So the day 2 question is not "how do I stop that" — it is **what does `202 Accepted` actually promise when the caller may never learn that it was accepted?** Relay's contract says an accepted job is never lost. It says nothing about a job the client does not know was accepted. That gap is exactly where Week 3 lives, and Din 2 should make it concrete rather than close it.

Second, smaller: today's `status` decision means the claim's safety rests entirely on my discipline in never writing a `status` update without a `WHERE` guard on the old value. The database will not remind me. Is that something a test can enforce, or only a convention? *(day 3.)*


## Day 2 — API: `POST /jobs` and `GET /jobs/{id}` (2026-08-15)

*(Session ran past midnight into 2026-08-16; dated by start, following Day 1's sequence.)*

**Original goal (from the plan):** two endpoints — `POST /jobs` returning `202` after the row is committed, and `GET /jobs/{id}` returning status or `404`. Pydantic models for request and response. Manual verification via `curl`/`httpx`. No worker, no dedup, no idempotency.

**Goal met?** Yes. Both endpoints work and every path in the plan's checklist was verified, plus the durability test in a stronger form than the checklist asked for.

**Anything else learned?** Yes, and the most useful thing was a **bug in my own size limit that the plan's checklist would have passed**. The limit returned `413` correctly and still provided none of the protection it existed for. Details in M10/M11 and `P-08`. Separately: the day started by writing all three files at once, which had to be deleted and restarted in six small steps — that process failure is recorded in the self-check because it, not any concept, was the real problem.

> **Provenance — read before trusting the numbers below.**
>
> I wrote every line of `src/` myself. **Most of the measurements below were run by the reviewer, not by me** — specifically M2, M3, M6, M9, M10, M11, M12, and the `synchronous_commit` check. I ran M13, M14, M15, and my own end-to-end latency numbers. Where a measurement is not mine it is marked `[R]`, because a number I did not produce is not a number I can claim to have verified.
>
> Two of my recorded claims were **falsified by measurement** (see the corrections table). One of the reviewer's predictions was also wrong (M12) and is recorded as such.

---

### 📊 Measured / Observed

**M1 — `GET /health`** → `200`, `{"ok": true}`. Zero DB interaction. Deliberately built first so that a failure here could only be an import-path or uvicorn problem, not application logic.

**M2 — `GET /db-ping`** `[R]` → `200`, `{"db": 1}`. SQL log:
```
BEGIN (implicit)
SELECT 1
ROLLBACK
```
The `ROLLBACK` is the interesting line: nothing failed. It is the session teardown returning the connection to the pool. This is direct evidence for the Step 1 Q2 correction below — rollback comes from the framework, not from my `except` block.

**M3 — `POST /jobs`, valid body** `[R]` → `202`, `{"job_id": 4, "status": "pending"}`. SQL log:
```
INSERT INTO jobs (type, payload) VALUES ($1::VARCHAR, $2::JSONB)
  RETURNING jobs.id, jobs.status, jobs.attempts, jobs.created_at
COMMIT
```
Two facts in this one output. **First:** `RETURNING` fetches **four** columns, not just `id` — SQLAlchemy 2.0's `eager_defaults="auto"` pulls every server-default column in the same statement on a RETURNING-capable backend. That is why `job.status` is readable after `commit()` with no `refresh()` and no second query. **Second:** `INSERT` and `COMMIT` are *separate* statements, which falsified my claim that `commit()` issues the INSERT.

**Round trips per enqueue: one** (`INSERT ... RETURNING`) plus the `COMMIT`. No `SELECT`.

**M4 — `type: ""`** → `422`, `type=string_too_short`. Rejected by the `min_length=1` constraint; my custom validator never ran.

**M5 — `type: "   "`** → `422`, `type=value_error`, *"Job type cannot be empty or whitespace only"*. Constraint **passed** (3 characters), custom validator caught it. Same status code as M4 from a different layer.

**M6 — constraint ordering** `[R]` → `"a"*100 + "  "` → `422`, `string_too_long`. 102 characters, so `max_length=100` rejects it *before* stripping, even though the stripped value would be exactly 100 and valid. `Field(...)` constraints run on raw input; `@field_validator` runs after.

**M7 — `type: 123`** `[R]` → `422`, `type=string_type`, *"Input should be a valid string"*. **No coercion.** Pydantic 2.13.4 default (smart) mode does not accept `int` for a `str` field.

**M8 — `payload: dict = {}` is not shared across instances** `[R]`:
```
a.payload['leak'] = 1
b.payload              -> {}       # untouched
a.payload is b.payload -> False
```
Pydantic copies mutable defaults per instance.

**M9 — `GET /jobs/4`** `[R]` → `200`, `{"job_id": 4, "status": "pending"}`. SQL: `SELECT jobs.id, jobs.status WHERE jobs.id = $1`. No `payload` selected, so no TOAST dereference.

**M10 — `GET /jobs/9999999`** → `404`. **`GET /jobs/abc`** `[R]` → `422`, `type=int_parsing`, `loc: ["path", "job_id"]` — rejected during request validation, before the handler and before any DB access.

**M11 — the size limit bug, and the fix** `[R]`. Three ~306 KB requests, run against the check placed inside the handler, then again after moving it to HTTP middleware:

| Request | Check in handler | Check in middleware |
|---|---|---|
| oversized, valid JSON | `413` | `413` |
| oversized, `type: ""` | `422` `string_too_short` | **`413`** |
| oversized, malformed JSON | `422` `json_invalid`, `loc: ["body", 306274]` | **`413`**, no `loc` |

`loc: ["body", 306274]` is the whole finding: the JSON parser reached character **306,274**, so the entire body was buffered and parse was attempted before the size check ran. After the move the offset is absent — no parse occurs. Also note the *second* row: before the fix, an oversized body's status code depended on whether the body was valid.

**M12 — enqueue latency, decomposed** `[R]` for the first two rows, mine for the third. `N=12` per configuration, one variable changed between the first two:

| What | Cold | Warm median | Warm range |
|---|---|---|---|
| `INSERT + COMMIT`, in-process, `echo=False` | 178 ms | **7.5 ms** | 7.0 – 10.0 |
| `INSERT + COMMIT`, in-process, `echo=True` | 123 ms | **9.8 ms** | 8.2 – 13.6 |
| Full `POST /jobs` over HTTP (my harness) | 298 ms | **~21 ms** | 14.8 – 31.2 |

So: **DB work ≈ 7.5 ms**, `echo=True` logging ≈ **+2.3 ms**, and **≈ 11 ms is unexplained** — FastAPI/ASGI overhead plus my measurement harness. If the harness spawned a `curl` process per request, process startup alone on Windows accounts for most of it. **That 11 ms is not isolated**, so "durable enqueue costs 21 ms" is not a supportable statement. The supportable one is ~7.5 ms of database work.

Caveat on the 7.5 ms itself: Postgres is running in a Docker Desktop VM on Windows with a virtualised disk, where `fsync` is far slower than on native Linux. This is *"on this machine, in this setup"*, not *"the cost of a Postgres commit."*

**M13 — `synchronous_commit`** → `on`. Checked because the durability claim depends on it and nothing in my code sets or asserts it.

**M14 — durability, graceful shutdown.** `docker compose restart db` → all 8 rows present afterwards. **This test proves less than it appears to.** `restart` sends `SIGTERM`, Postgres shuts down cleanly, checkpoints, and flushes shared buffers — so committed data would survive even with `synchronous_commit = off`. It does not isolate WAL durability at all.

**M15 — durability, unclean kill.** `docker compose kill db` (`SIGKILL`) → `docker compose up -d` → all 8 rows present. No checkpoint, no graceful flush; Postgres performed crash recovery from the WAL on restart. This is the real test, and it is the Week 0 Day 2 `SIGTERM`-vs-`SIGKILL` distinction applied to the database instead of the worker.

Precisely what M15 establishes, and what it does not:

| Claim | Status |
|---|---|
| Committed data survives **process** death | ✅ measured |
| Committed data survives **power loss / OS crash** | ❌ **not tested** — `SIGKILL` does not drop the OS page cache, and the volume outlives the process |

`fsync`-to-durable-media therefore remains **inferred** from `synchronous_commit = on`, not measured.

**M16 — sequence gap after `ROLLBACK`.**
```sql
BEGIN;
INSERT INTO jobs (type) VALUES ('rollback_gap_test');
ROLLBACK;
INSERT INTO jobs (type) VALUES ('after_rollback_test') RETURNING id;  -- 37
```
`jobs_id_seq` afterwards: `last_value = 37`, `is_called = t`. Arithmetic closes exactly, accounting for 24 reviewer probe rows that were inserted and deleted in between:

```
max id before probes                     = 11
24 probe rows (inserted, later deleted)  = 12 .. 35
rolled-back INSERT                       = 36    ← consumed, never returned
committed INSERT                         = 37
```

`nextval` is non-transactional: the rolled-back transaction permanently consumed `36`. **This is the gap half of `P-05`, now measured** — where an earlier claim that rows `1, 2, 4` proved it was wrong, since those holes came from `DELETE`s.

**Method note:** this would have been airtight with `RETURNING id` *inside* the transaction, showing `36` directly. As run, it is established by reconstruction, not direct observation.

---

### 💡 What I Understood

**The whole day is one ordering.** `COMMIT` happens, and *then* `202` is sent. Everything else — schemas, status codes, response shape — is detail around that single sequence. Reverse it and *"an accepted job is never lost"* becomes false while every test still passes, because the tests would be checking the response, and the response would be a lie.

**Durability is a joint property of my code and a setting my code never mentions.** M13 makes this concrete. `COMMIT`-before-response is my contribution; whether that `COMMIT` reaches durable storage is `synchronous_commit`'s. Flip it to `off` and the guarantee evaporates with no line of my code changing and no test failing. This is the same family as `P-06`'s `idle_in_transaction_session_timeout`: the guarantee lives in a default nobody in this repo owns. Which is why M13 is in this log as a *measurement* and not as an assumption.

**A check that runs after the work it was meant to prevent is not weak — it is decorative.** M11 is the day's most valuable finding precisely because it *passed*. `413` was returned. The status code was right. The plan's checklist item (*"over-limit payload → `413`"*) was satisfied. And the 306 KB had already been read and parsed, which was the entire point of having a limit. The lesson is not about FastAPI's parameter resolution order; it is that **"the test passes" and "the mechanism works" are different claims**, and only one of them was checked. The proof came from an error message's byte offset, not from reading the code — the same shape as Day 1's `server_default` bug, which was caught by compiling the DDL rather than reading the model.

**Where a rejection happens is a design decision, and there are five distinct layers.** Verified individually rather than assumed:

| Layer | Rejects | Status |
|---|---|---|
| HTTP middleware | body over 266,240 bytes | `413` |
| Request validation (path) | `/jobs/abc` | `422` `int_parsing` |
| Pydantic constraints | `type: ""`, over-length `type`, `type: 123` | `422` |
| Custom `field_validator` | `type: "   "` | `422` `value_error` |
| Application + storage | id absent from `jobs` | `404` |

Two things fall out. The `422`s come from **three different layers** with different error `type`s, which is what makes a `422` debuggable at all. And moving a check between layers changes its meaning, not just its location — M11 is exactly that.

**PostgreSQL is a row-store, so "select fewer columns" is usually not an optimisation.** I had this wrong (correction #7). A whole 8 KB heap page is read regardless; `SELECT id, status` and `SELECT id, status, type, created_at` cost the same heap I/O. The *only* saving from a narrow select here is skipping the **TOAST dereference** for `payload`. Two consequences: the TOAST reasoning in `D-05` Cost #3 is real and correctly applied, *and* adding `type`/`created_at` to `GET` later is nearly free — so the reason to keep the response minimal is not performance. It is that **adding a response field is backward-compatible and removing one is breaking**, which makes minimal the reversible starting point.

**Mitigation is not elimination, and I wrote the opposite three times in one day** (corrections #1, #8, #9). Excluding `payload` from `GET` narrows exposure; `404`-vs-`200` still enumerates ids and `status` still reveals activity, and the real fix is authorization — `D-03` already said so. Removing `refresh()` narrowed the post-commit window; nothing closes it. Option A's `404` is a race, not a guarantee. The failure is not technical, it is **wording**, and in this project the wording *is* the deliverable.

**`202` earns a property that `Option A` would have destroyed.** Can `202` hand back a `job_id` that immediately `404`s? Not through visibility: the row is committed before the response, and a subsequent `READ COMMITTED` statement sees committed data. Under Option A it becomes a routine race. So the `202`-then-`404` question is not a separate topic — it is a **test of whether the commit ordering was actually implemented**, and the two plan questions are one question. It *is* still reachable by a different route: the row being deleted (Din 4/5 resets, Week 4 retention). "Impossible" was too clean.

**`flush()` and `commit()` are different operations, and the difference is usable.** M3 shows `INSERT ... RETURNING` and `COMMIT` as separate statements. `flush()` sends the DML and yields `job.id` while the transaction stays open. That is the mechanism Week 2 or 3 will need to write a job and something else atomically — and I would not have known it existed if the echo output hadn't contradicted my claim.

---

### 🧠 Self-Check (honest — 11.25 / 18 self-answered ≈ 62%)

Day 1 was `0/9`. This is the first day with a real positive score, and the reason is a process change rather than better preparation: questions were asked **before** each step's code, in six small steps, instead of after a large block.

| Step | Asked | Self-claimed | Actual | Where the marks went |
|---|---|---|---|---|
| 1 — `get_db` | 3 | 3/3 | **1.5 / 3** | Q1 ✅. Q2 misattributed rollback to my `except` block. Q3 invented "5-10 connections" |
| 2 — Pydantic | 3 | 3/3 | **1.5 / 3** | Q1 ✅. Q2 projected a plain-Python bug onto Pydantic. Q3 recalled v1 behaviour |
| 3 — enqueue / `202` | 4 | 4/4 | **2.5 / 4** | Q1 ✅. Q2 half (`flush` vs `commit`). Q3 contradicted `P-01`. Q4 explained `202` without refuting `201` |
| 4 — `GET` | 3 | 2/2 | **1 / 3** | Q1 half (row-store, invented numbers). Q2 half ("zero"). **Two questions not attempted** |
| 5 — payload limit | 2 | 1/2 | **2 / 2** | Both correct. I marked my own `413` answer wrong when it was right |
| Follow-ups | 3 | — | **2.75 / 3** | Best of the day; the `202→404` reasoning was mine |

Two scoring notes worth keeping, because both directions of dishonesty are dishonesty. I **claimed 3/3 and 4/4 on steps I had not self-derived**, which is the Day 1 pattern repeating. And on Step 5 I **recorded a failure that never happened** — I answered `413` correctly and logged it as a miss. A false negative corrupts revision material exactly as much as a false positive: I would have re-studied something I already knew.

**Corrections — things I stated that measurement or review refuted:**

| # | I said | Actual | The transferable lesson |
|---|---|---|---|
| 1 | "Without explicit `rollback()`, locks will hang as `idle in transaction`" | `async with async_session()`, `session.close()`, and pool check-in **each** roll back. Three layers already do it | Protection misattribution. The explicit line buys *explicitness*, not safety. `P-06`'s hanging sessions had no teardown at all — a different situation |
| 2 | "Pool exhausts after 5-10 requests" | Defaults are `pool_size=5` + `max_overflow=10` = **15**, then a 30 s `pool_timeout` | A plausible number stated as fact. It was one config lookup away |
| 3 | "`default_factory=dict` fixes the mutable-default bug in Pydantic" | M8: Pydantic copies defaults per instance. `payload: dict = {}` was never buggy | Real Python trap, wrong target. `default_factory` is for *dynamic* defaults (`datetime.now`) |
| 4 | "Pydantic coerces `123` → `"123"`" | M7: rejected, `string_type`. That was **v1** behaviour; v2 default (smart) mode refuses it | Library behaviour from memory instead of a 5-second check — same root cause as Day 1's `server_default` bug |
| 5 | "`commit()` runs the `INSERT ... RETURNING`" | M3: `INSERT` at flush, `COMMIT` separately. Two statements in the echo output | Decoupling is usable: `flush()` gives `job.id` inside an open transaction |
| 6 | "On read timeout the client concludes the request never arrived" | `P-01`, my own entry: *connect timeout = pahuncha nahi, read timeout = **pata nahi***. The client concludes **nothing** | **Contradicted my own recorded measurement.** And it matters: "wrong information" implies better error handling would fix it; "no information" is why Week 3 must exist |
| 7 | "`SELECT id, status` saves disk I/O by columnar projection" | Row-store, whole 8 KB heap pages. Narrow and wide selects read the same page. Only the **TOAST dereference** is saved | Right conclusion, wrong mechanism — which would have led me to wrongly believe adding `type`/`created_at` is expensive |
| 8 | "Excluding `payload` reduces the attack surface to **zero**" | Narrows it. `404`-vs-`200` still enumerates; `status` still leaks activity. `D-03`: *"The real fix is authorization"* | Mitigation ≠ elimination (`P-04` family). Second instance of this wording failure in one day |
| 9 | "Under Option A, `202`-then-`404` is **guaranteed**" | A race between the background insert and the client's `GET` | A non-deterministic race is *worse* than a guarantee: intermittent, load-dependent, hard to reproduce |
| 10 | "Under Option B, `202`-then-`404` is **impossible**" | Impossible via visibility. Still reachable if the row is **deleted** — which Din 4/5 will do routinely | Separate "timing/visibility" from "the entity is gone". Do not close a question cleanly when a second path exists |
| 11 | "Rows `1, 2, 4` prove `P-05`'s sequence gaps" | Those holes came from `DELETE`s. Deletion leaves holes in *any* scheme — no insight. M16 is the actual proof | The observation was real and the *cause* was wrong, which makes it a worse entry than no entry |
| 12 | "`413` is rejected before buffering/parsing" (written while the check was in the handler) | M11: `loc: ["body", 306274]` — 306 KB buffered and parsed first. **True only after** moving to middleware | The claim described intent, not behaviour. Both states are now recorded, because the gap between them is the day's real finding |
| 13 | Reviewer's prediction: "`echo=True` is eating most of the 21 ms" | M12: `echo=True` costs **~2.3 ms**. ~11 ms remains unexplained | Recorded per rule 12 — the reviewer's wrong prediction is data too, and it is what forced the decomposition |

**The process failure, which mattered more than any single answer.** The day began by generating all of `schemas.py`, `main.py`, `database.py`, and a `tests/` directory in one pass. The result was correct and I could not follow it — I could not trace a request through code that existed in my own repo. All of it was deleted and rebuilt in six steps of 10–15 minutes each, every step runnable, every step's questions answered before writing. The score went from `0/9` on Day 1 to `62%` today, and the variable that changed was **step size**, not effort or preparation. Recording this as the day's primary finding about method: *a step is too large when I cannot state, before writing it, what would break.*

**Where the marks actually went.** Nine of the thirteen corrections are one of two failures: **stating a plausible number as measured** (#2, and the invented "400 MB/s" and "100x" in the same answer), or **stating a mitigation as an elimination** (#1, #8, #9, #10, #12). Neither is a gap in systems knowledge. Both are wording, and in a document whose purpose is to be trustworthy in six months, wording is the product.

**Still recognisable rather than recallable:** correction #6 is the sharpest evidence. I *wrote* `P-01` on Day 4 of Week 0 and then stated its exact inverse. Day 1's log diagnosed this and the diagnosis holds. Weekend consolidation must therefore cover `P-01` alongside the nine schema items — the list is not only about Day 1's material.

---

### 🚧 Unresolved / Follow-ups

**New, from today:**
- **`P-08` — the size limit depends on `Content-Length`, a header the sender controls.** Omit it (chunked, HTTP/2) and the check is skipped. Threat model is an honest client. Fix is ASGI stream byte-counting, deferred to Week 4; when it lands, its own overshoot bound (limit + one chunk) must be recorded rather than described as a limit.
- **`P-07` — the post-`COMMIT` window cannot be closed.** Week 3. Four things genuinely undecided and listed there: who mints the idempotency key, the dedup window, whether a payload hash is acceptable given that two legitimately identical jobs would collapse, and whether a duplicate gets `202` with the original id or `409`.
- **≈ 11 ms of enqueue latency unexplained** (M12). Not isolated between framework overhead and my harness. Clean test: time the endpoint in-process via ASGI, no subprocess per request, `echo=False`. Until then the honest figure is ~7.5 ms of database work, not 21 ms.
- **`fsync`-to-durable-media is still inferred** (M15). `SIGKILL` proved survival of process death only; the OS page cache is untouched by it. A real test needs the VM or host to die.
- **The DB is unbounded on both `payload` size and `type` length.** Both limits are API-layer only, and Din 4/5 write directly via `psql`. `D-04` Cost #3 and the `D-05` amendment both record this.

**Carried, still open:**
- **`POSTMORTEMS.md` entry #2 (Cloudflare)** — Week 0's Definition of Done wants 2, there is 1. Open since Din 1 by choice. Moved to weekend.
- **`P-03` claim-query index** — Week 4, by `EXPLAIN ANALYZE`. Today's invented "400 MB/s polling" number is precisely the guess `P-03` exists to prevent.
- **`P-05`'s dangerous half is still unverified.** M16 measured the *gap* mechanism. The claim that **id order ≠ commit order** — a lower id becoming visible later — needs two concurrent transactions and will fall out of Din 4 naturally.
- **`idle_in_transaction_session_timeout`** — unowned default, Week 4 with pool sizing. M13's `synchronous_commit` check belongs in the same family and the same eventual entry.
- **`ACCESS EXCLUSIVE` lock-queue hazard** in `D-07` — still inference.
- **Week 0 Day 4 Exp B** — fast-fail vs slow-fail contrast never reproduced on this machine, cause **not identified**. Newly relevant: the ~11 ms unexplained latency and Week 0's odd 1.001 s localhost timeouts are both on this Windows/Docker Desktop setup, and may share a cause. Not established — noting the coincidence, not a conclusion.
- **Week 0 Day 3 Exp D** and **Day 2's exit-code `137`** — unchanged.

**Housekeeping:** `RabbitMQ acknowledgements` reading (ack before vs after work, why `auto-ack` is dangerous, `nack`/`requeue`) was **not done** — deferred to before Din 3, where it compares directly against when the worker marks `running` versus `succeeded`.

---

### ❓ Question / Next Thought

Din 3 builds the worker, and today produced the exact tension it will run into. `POST /jobs` proves the pattern works when the safe order is *commit, then tell the caller* — the row is durable before anyone is promised anything. The worker cannot use that pattern. It must claim a job, **commit the claim** so it does not sit in `idle in transaction` holding locks (`P-06`, Din 3's Trap 2), and only then execute. Committing the claim is what releases the protection: the job is `running` with nothing guarding it, and if the worker dies there it stays that way forever.

So the day's shape inverts. On the API side, committing early is what *creates* the guarantee. On the worker side, committing early is what *destroys* it. Same operation, opposite effect, and the difference is only whether the durable record describes something already finished or something about to start.

That reframes what `202` actually promised. It promised the *record* is safe, never that the *work* will happen — and Din 2 had no way to notice the gap because nothing executed yet. Din 3 will make it visible, and Din 5 will make it painful.

Second, smaller, and it follows from correction #12: the plan's checklist item *"over-limit payload → `413`"* passed against a limit that protected nothing. The checklist was satisfied and the mechanism was absent. So for Din 3, what is the equivalent trap — a check whose passing tells me nothing? The obvious candidate is *"`pg_stat_activity` shows no `idle in transaction`"*: with a single worker and a fast fake handler, that check passes whether or not I committed the claim before executing, because the window is too small to observe. Worth designing the verification so it can actually fail before trusting it.

---

## Day 3 — Worker loop: `claim → execute → mark` (2026-08-16)

**Original goal (from the plan):** a separate worker process that claims one `pending` job in a single transaction (`FOR UPDATE`, no `SKIP LOCKED`), commits the claim, executes a fake handler, then marks the terminal status in a second guarded transaction. Failure path via a handler registry. Graceful shutdown with finish-current semantics. No lease, no reaper, no retry, no second worker.

**Goal met?** Yes, for the build. `src/worker.py` does claim → execute → mark with the compare-and-set guard on **both** writes, and the emitted SQL confirms the claim is one transaction. C1–C5 were verified; C6 was run by me but its numbers were **not recorded by the reviewer** (see provenance).

**Anything else learned?** Yes, two things that were not on the plan. The idle poll is **a transaction per poll**, not a bare `SELECT` — visible in the echo, and it is the raw material `D-01` was waiting for. And today's system turns out to be **at-most-once** on worker death, which is the inverse of the week's title (`P-09`).

> **Provenance — read before trusting the numbers below.**
>
> I wrote every line of `src/worker.py` myself. I answered Part B from my own head first and ran C1–C6 myself; for some questions I could not answer, I resolved them from the KEY file after running the step, and a few concepts came via Gemini. **At my own request, no per-question score was computed for this day** — this is a deliberate deviation from the protocol's scoring rule, recorded here so the absence is not mistaken for a `0` or for a clean sheet.
>
> Every measurement below marked `[R]` was re-run by the reviewer on a clean bench, independently of my own run. **C6's exit code and elapsed times are mine and were not re-measured** — they are therefore listed as *not recorded* rather than given values.

---

### 📊 Measured / Observed

Starting bench `[R]`: 14 rows, all terminal (11 `succeeded`, 3 `failed`), nothing in `running`, `attempts = 0` everywhere. The brief's stated 9 `pending` rows had already been consumed by my own Day 3 run, so the reviewer's arithmetic starts from 14, not from 9.

**M1 — `EXPLAIN` for the claim query** `[R]`, on the live table:

```
Limit  (cost=1.16..1.17 rows=1 width=33)
  ->  LockRows  (cost=1.16..1.17 rows=1 width=33)
        ->  Sort  (cost=1.16..1.16 rows=1 width=33)
              Sort Key: created_at
              ->  Seq Scan on jobs  (cost=0.00..1.15 rows=1 width=33)
                    Filter: (status = 'pending'::text)
```

`LockRows` sits **below** `Limit`. Execution order bottom-up: scan → sort → **lock** → `Limit` stops. So the row is locked *before* `Limit` has decided it has enough rows. `Seq Scan` at this size is correct and is not evidence about indexing — that stays `P-03`, Week 4.

**M2 — C1, the claim is one transaction** `[R]`. From the worker's own SQL echo, verbatim shape:

```
BEGIN (implicit)
SELECT jobs.id, jobs.type, jobs.payload FROM jobs
  WHERE jobs.status = $1::VARCHAR ORDER BY jobs.created_at LIMIT $2::INTEGER FOR UPDATE
UPDATE jobs SET status=$1::VARCHAR WHERE jobs.id = $2::BIGINT AND jobs.status = $3::VARCHAR
  -- params: ('running', 16, 'pending')
COMMIT
```

**Affected row counts, as numbers:** claim `rowcount=1`, mark `rowcount=1` (`('succeeded', 16, 'running')`). Both statements carry the guard. **K1 did not happen** — the compare-and-set survived into the emitted SQL, because the code uses an explicit Core `update()` rather than ORM attribute mutation. This was verified by reading the SQL, not by reading the code.

**M3 — the idle poll is a transaction, not a query** `[R]`. Unplanned, and the most reusable number of the day. With no work available the echo repeats, once per interval:

```
BEGIN (implicit)
SELECT ... FOR UPDATE   [cached since 8.305s ago] ('pending', 1)
COMMIT
```

So at `POLL_INTERVAL_SECONDS = 2.0`, one idle worker costs **0.5 transactions/second, indefinitely**, each one a `Seq Scan` plus a `BEGIN`/`COMMIT` round trip. Two further observations from the same log: the statement is reported `cached`, so SQLAlchemy is reusing the prepared statement rather than re-planning; and the poll is read-only, so it writes no WAL. **This is `D-01`'s missing cost figure** — measured for one worker at one interval on this machine, not a general claim.

**M4 — C2, the transition guard is load-bearing** `[R]`. Job 20, a `sleep` job. A server-side probe polled until the row went `running`, then applied interference inside the handler's window:

```sql
UPDATE jobs SET status='failed' WHERE id=20 AND status='running';   -- the other writer
```

Worker's response, verbatim:

```
UPDATE jobs SET status=$1::VARCHAR WHERE jobs.id = $2::BIGINT AND jobs.status = $3::VARCHAR
  [cached since 186.8s ago] ('succeeded', 20, 'running')
[worker-20168] Conflict on mark: Job 20 status was modified by another transaction (rowcount=0).
COMMIT
```

Final status of job 20: **`failed`**. The guarded implementation got `rowcount=0`, logged the conflict, and did **not** overwrite the other writer's decision. An unguarded `WHERE id=20` would have returned `1` and silently converted it to `succeeded`. This is the check that Day 2's `413` lesson demanded: it can actually fail, and it was run against interference rather than against a happy path.

**M5 — C3, the `running` state is observable through the API** `[R]`. Job 27, polled through `GET /jobs/{id}` at 200 ms intervals while the worker held it:

```
POST /jobs -> job_id=27, status=pending
GET  /jobs/27 over time -> pending -> running -> succeeded
```

All three states visible externally, so contract point 5 (*"it can always say where a job is"*) is met for the happy path — not merely satisfied in `psql`. Note the sampling caveat: at a 2 s handler and 200 ms polling the window is wide; a faster handler would make `running` easy to miss, and missing it would not mean it never happened.

**M6 — C4, failure path and unknown type** `[R]`. Enqueued in this order, deliberately failing job first:

| id | `type` | Final status | Worker afterwards |
|---|---|---|---|
| 21 | `boom` | `failed` | kept polling |
| 22 | `sleep` | `succeeded` | proves the loop survived the exception |
| 23 | `does_not_exist` | `failed` | one mark, then back to polling |

The unregistered type did **not** produce a hot loop: it is claimed, marked `failed` once, and never seen again. That is the direct consequence of the chosen option, and its cost is now recorded against `D-04`.

**M7 — C5, the differential that establishes the check can fail** `[R]`. Run A used a throwaway probe (`labs/probe_din3_runA.py`, deliberately wrong, since deleted) which held the claim transaction open across a 12 s handler. Run B is `src/worker.py` unmodified. Both rows are real `pg_stat_activity` output:

| | PID | `state` | `wait_event_type` / `wait_event` | `xact_start` | last `query` |
|---|---|---|---|---|---|
| **Run A** — transaction held open across the handler | 845 | **`idle in transaction`** | `Client` / `ClientRead` | present, age **`00:00:11.295`** | the claim `UPDATE` |
| **Run B** — claim committed before executing | 751 | **`idle`** | `Client` / `ClientRead` | **`NULL`** | `COMMIT` |

`wait_event` is **identical in both rows**, which is exactly why a check written on the wait event would prove nothing. The discriminators are `state` and `xact_start`. Run A is the same row shape as Day 1's PID 53 in `P-06` — reproduced deliberately, in my own worker, instead of by accident five days later.

**M8 — day-close state** `[R]`:

```
failed | 6        running: 0 rows
succeeded | 21    jobs with attempts <> 0: 0
```

Arithmetic: started at 14 terminal rows; the reviewer enqueued 13 more (ids 15–27) across C1–C5; `14 + 13 = 27 = 6 + 21`. It closes exactly. Nothing left in `running`, `attempts` untouched at `0` everywhere, and no probe columns were added to the table (`information_schema` check returned `0`).

**Not established — an attempt that failed, recorded as such.** I tried to convert the KEY's *inference* that Run A's open transaction would queue behind routine DDL into a measurement, using `LOCK TABLE jobs IN ACCESS EXCLUSIVE MODE` with `lock_timeout='3s'` against a live Run A. **The lock was granted immediately**, because the probe process was not actually running at that moment — a reused terminal handed back a stale, already-exited process. So the result says nothing about the hazard. `D-07`'s `ACCESS EXCLUSIVE` lock-queue item remains **inference**, unchanged since Day 1. A clean test needs the lock attempt issued while a confirmed `idle in transaction` row is visible in `pg_stat_activity`.

**Not recorded — C6.** I ran the Ctrl+C tests myself, mid-job and idle-polling, and the reviewer did not re-measure them. The four fields the brief asked for — exit code, elapsed time to exit in each case, and the `running` count after exit — are therefore **not in this log as values**. The `running` count at day close is `0` (M8), which is consistent with finish-current but was measured after everything had stopped, so it does not isolate the shutdown path.

---

### 💡 What I Understood

**The day is one sentence: committing the claim buys visibility and costs protection.** Before the commit, the row is locked and nobody else can touch it — but the transaction is open, so the worker is `P-06`'s culprit, holding locks across a sleep for reasons the database cannot see. After the commit, the lock is gone, the `running` state is visible to everyone including `GET /jobs/{id}`, and the job has **nothing** guarding it. Day 2's ordering created a guarantee; the same ordering here removes one. That is not a bug to fix today — it is Week 2's problem statement, and Part D was explicit that leaving it broken is the deliverable.

**`FOR UPDATE` is not what makes the claim correct — the compare-and-set is.** With one worker, `FOR UPDATE` protected against exactly one competitor: a human at the `psql` prompt. What actually defended the transition was `AND status='running'` plus reading `rowcount`, and M4 is the proof, because interference came from outside the lock's protection window entirely. The two mechanisms do different jobs: the guard is *correctness*, the lock is *ordering under contention*. Which of them costs what with two real workers is Din 4, and it stays unanswered here.

**`rowcount = 0` means "my belief about this job is stale", and the only correct response is to stop writing.** M4 makes the abstract rule concrete: another writer had better information, and forcing the write would have destroyed a decision. Same shape as `alembic check` — an assertion that is boring on correct code and is the only signal on broken code.

**Polling has a measurable price and I now have the number.** M3 turns the poll interval from a preference into a trade: 0.5 tx/s per idle worker at 2 s, against an upper bound on enqueue-to-start latency of roughly the same 2 s. Neither figure is right or wrong; the interval is where one is spent to buy the other. Two consequences worth carrying: the cost scales with worker count, not with job count, so an idle fleet is not free; and because the loop sleeps the whole interval in a single `await`, **the poll interval also bounds shutdown latency** — a coupling that matters the moment a 10 s Docker grace period is involved (`P-10`).

**Today's worker is at-most-once, which is the opposite of the week's title.** If the process dies after the claim commits, the row sits in `running` forever, and the claim query filters on `pending`, so no restart will ever re-execute it. There is no path to a second execution today — not because duplication was prevented, but because **recovery does not exist**. Duplicate execution is the price of adding recovery, not a defect that appears on its own. Written up as `P-09`, because it reframes contract points 1 and 2 as being in tension rather than in sequence.

**The RabbitMQ mapping, in my own words.** A broker can redeliver because it holds a connection to the consumer and notices when it breaks. Postgres holds a connection to my worker too, and notices — but it has no idea that connection was supposed to *finish a job*, so noticing buys nothing. Committing the claim is therefore not `auto-ack` (that would be marking `succeeded` before running the handler); it is manual-ack semantics **with the redelivery mechanism missing**. Relay's replacement for "the broker noticed" has to be a deadline, not a connection, which is why the reaper must be timeout-based.

**Reviewer's code review of `src/worker.py` — findings, not opinions:**

| # | Finding | Status |
|---|---|---|
| 1 | Claim is one transaction; guard present on **both** the claim and the mark; `rowcount` checked on both. K1 avoided | ✅ `[MEASURED]` in the echo (M2) |
| 2 | Claim commits before the handler runs — Trap 2 avoided | ✅ `[MEASURED]` (M7 Run B) |
| 3 | `except Exception`, not `BaseException`, so `CancelledError`/`KeyboardInterrupt` are not swallowed by the handler's error path | ✅ correct as written `[INFERRED from code]` |
| 4 | Shutdown flag is checked only at the top of the loop, and the idle wait is a single `await asyncio.sleep(2.0)`. Idle shutdown latency is therefore bounded by the poll interval, up to ~2 s | ⚠️ `[INFERRED from code]`, elapsed time **not recorded** |
| 5 | `signal.SIGBREAK` (21) is not registered. `SIGTERM` is registered but is not deliverable on this platform (KEY T-c), so on Windows only `SIGINT` is live. Keeping `SIGTERM` is still right — it is the one that matters inside Docker | ⚠️ real gap, small |
| 6 | `ORDER BY created_at` has **no tiebreak**. `now()` is per-transaction (K2), so any single-statement bulk seed gives identical `created_at` and "which job was picked" becomes unfalsifiable | ⚠️ **blocks Din 4** unless jobs are inserted one statement each, or the order becomes `(created_at, id)` |
| 7 | `sys.exit(0)` is called from inside the coroutine, raising `SystemExit` through `asyncio.run` | works; exit code **not recorded** by the reviewer |
| 8 | Unknown `type` consumes the claim and marks `failed` — one mark, no hot loop | ✅ `[MEASURED]` (M6), cost recorded against `D-04` |

---

### 🧠 Self-Check

**No per-question score this day, at my request.** Rules 1–2 of the reviewer contract were deliberately not applied, so this entry cannot be compared with Day 1's `0/9` or Day 2's `62%`. That break in the series is the honest cost of skipping it, and it is recorded rather than papered over.

What is true and worth keeping: Part B was attempted from my own head before each step, several answers were `idk`, and those were resolved **after** running the step, from the KEY — which is the protocol working as intended. The KEY was also used for some vocabulary, which is allowed. Some concept help came from Gemini.

**Corrections — where reality differed from what the KEY or I had assumed:**

| # | Claim | Actual | Lesson |
|---|---|---|---|
| 1 | The brief's bench state: *"9 rows, all `status='pending'`"* | `[R]` At review time: 14 rows, **0 pending**, 11 `succeeded` + 3 `failed`. My own run had already consumed them | A stated bench state has a timestamp attached. `K6`'s warning was correct in form and stale in content |
| 2 | KEY 2.3's `EXPLAIN`, captured on the 9-row table | Same node order, different row estimates (`rows=1` throughout, M1). The **shape** is what transferred, not the numbers | Plan shape is stable at this size; costs are not. Quoting a cost from a different table state would have been wrong |
| 3 | KEY 5.3: Run A's open transaction *would* queue behind `ACCESS EXCLUSIVE` DDL | Attempted and **not established** — the lock was granted because no Run A was live at the time | A measurement that did not land is not a measurement. Recorded as failed, per rule 15 |
| 4 | The idle poll is a `SELECT` | It is `BEGIN` + `SELECT ... FOR UPDATE` + `COMMIT` — a full transaction per poll (M3) | The cost of polling is a transaction rate, not a query rate. Neither the plan nor the KEY stated this |

---

### 🚧 Unresolved / Follow-ups

**New, from today:**
- **`P-09` — today's engine is at-most-once, and at-least-once requires building the thing that duplicates.** Din 4 supplies one route (two claimers), Week 2 the other (a reaper resetting `running → pending`).
- **`P-10` — the poll interval bounds shutdown latency as well as enqueue latency.** One `await` per interval means the flag is observed up to a full interval late. At 2 s inside Docker's 10 s grace period there is headroom; the coupling is what matters, not today's margin. Fix (slice the sleep, or wait on an `asyncio.Event`) is Week 2 shutdown hardening.
- **C6's four fields are not recorded** — exit code (mid-job and idle), elapsed time to exit in both cases. Cheap to redo, and `P-10`'s idle-case claim of "up to one poll interval" is currently `[INFERRED from code]`.
- **`ORDER BY created_at` has no tiebreak** (review finding 6). This must be settled **before** Din 4 seeds ten jobs, or Din 4's central question — *which* job the second worker got — becomes unanswerable.
- **`SIGBREAK` unregistered** (review finding 5). Small, and it decides whether `Ctrl+Break` is graceful or fatal.

**Carried, still open:**
- **`D-07`'s `ACCESS EXCLUSIVE` lock-queue hazard** — still inference, and today's attempt to close it failed (M7 note). Now has a known-good test procedure attached.
- **`P-03` claim-query index** — Week 4, `EXPLAIN ANALYZE`. M1's `Seq Scan` is *not* evidence either way at 27 rows.
- **`P-05`'s dangerous half** (id order ≠ commit order) — Din 4's two workers will produce it naturally.
- **`P-07`, `P-08`, ≈11 ms unexplained enqueue latency, `fsync`-to-media, `idle_in_transaction_session_timeout`, `POSTMORTEMS.md` entry #2, Week 0 Day 4 Exp B, Week 0 Day 3 Exp D, Day 2's `137`** — all unchanged.
- **DDIA Ch 7 second pass (pages 233–251)** — the brief scheduled RabbitMQ acks first and said DDIA may slip to Din 5. It slipped. **Recorded as a deliberate slip, not an omission.**

---

### ❓ Question / Next Thought

Din 4 runs two workers against one queue with `FOR UPDATE` and no `SKIP LOCKED`, and M1 is what makes the question sharp: `LockRows` sits **below** `Limit`, so the lock is taken before the limit is satisfied. Worker B therefore blocks inside a query that has not yet decided which row it wants. When A commits and B wakes up, what does B see — the same row (now `running`, so it no longer matches the filter), a different row, or nothing at all? I have three plausible answers and no basis to choose between them, which is exactly the right state to run the experiment in.

The sharper trap is one Day 2 already taught. Whatever Din 4 measures, the `jobs` table **cannot** show a double execution: both workers would write the same value to the same column and the row would look perfect — my own Week 0 words, *"dono ne same value likhi, row bilkul theek dikhi."* So the measurement instrument has to exist before the experiment, and it cannot be the `jobs` table. That is why `job_executions` gets built first tomorrow, and it is a general rule worth stating plainly: **a failure I cannot observe does not exist for me**, and building the observer is part of the experiment rather than overhead before it.

