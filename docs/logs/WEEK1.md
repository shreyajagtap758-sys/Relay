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

