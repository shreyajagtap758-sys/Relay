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