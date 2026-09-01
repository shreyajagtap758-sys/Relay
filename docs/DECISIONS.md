# DECISIONS.md — Architecture Decision Records (ADR)

Format for each entry:
```markdown
## D-NN: <decision in one line>
Problem:  What problem am I solving?
Options:  (a) ... (b) ... (c) ...
Chose:    Which option and why?
Cost:     What is the trade-off or downside of this choice?
Rejected: (x) because <concrete reason, ideally measured>
```

## D-01: Postgres is Relay's queue, not Redis and not RabbitMQ

**Problem:** Relay's contract #1 says *an accepted job is never silently lost.* A job is almost never
the only thing that happens at accept time — something in the business domain happened too (an order
was placed, a document was uploaded), and the job exists to finish that work. So the real problem is
not "where do I store queued work?" It is:

> **How do I make the business write and the enqueue succeed or fail together?**

Any answer that puts the queue in a different system than the business data cannot make that
guarantee, because two systems cannot share one transaction.

**Options:**
- (a) **Postgres** — the `jobs` table *is* the queue, workers poll it directly
- (b) **Redis** (list / stream) — in-memory, optional AOF persistence
- (c) **RabbitMQ** — a real broker with consumer acknowledgements and redelivery
- (d) **Classic outbox** — Postgres outbox table + a separate publisher process + a broker

**Chose:** (a).

**The decisive reason, and it is now measured rather than asserted.** Din 6 Step 1 ran three cases in
one `psql` session against a `TEMP` `orders_probe` table. `[MEASURED]`

| Case | Shape | Result |
|---|---|---|
| **A** — order + job in **one** transaction, committed | what Relay does | `orders = 1`, `jobs = 1`. Both present |
| **B** — order + job in one transaction, `ROLLBACK` before commit | crash *inside* the transaction | order count **unchanged**. No job. **Clean** |
| **C** — order committed, then the process dies **before** the enqueue | what Redis or RabbitMQ forces | order count **incremented**, `jobs = 0` |

**Case B and Case C are the same crash at the same instant, and they are not the same failure.** That
asymmetry is the entire entry:

- **Case B is transient and self-healing.** Nothing was written. The client retries, the retry works.
- **Case C is a permanent inconsistency, and no retry addresses it.** The order exists. The customer
  was billed. Nothing anywhere recorded that a job was supposed to exist, so a retry would create a
  *second* order rather than the missing job.

And the uncomfortable half, which is what makes it permanent rather than merely bad: **Relay cannot
detect Case C at all.** `[INFERRED]` Detection needs a join between the business row and the job, and
there is no join key — `jobs` has no `order_id`, and `D-03` deliberately kept `id` internal with no
client-supplied identity. The only party who could detect it is the business system, reconciling its
own rows against `jobs`, and only if it kept a reference. **That reconciliation job is exactly what
the outbox pattern exists to make unnecessary.**

So the choice is not "Postgres is convenient". It is that **(b) and (c) reintroduce a failure mode
that has no repair path and no detection path**, and (a) does not have it at all.

**Two of Week 0's four roles now live in one process, and that is a deliberate acceptance.** Postgres
is playing **store** and **queue** simultaneously. Three failures exist *only* because of that, and
they belong in `Cost` rather than being hidden:

1. Queue load lands on the instance serving business queries. `jobs` is unusually update-heavy — every
   row is updated at least twice on its way to `succeeded`, and under MVCC an `UPDATE` is
   delete-plus-insert (Week 0 Day 5), so vacuum and bloat pressure are structural rather than
   incidental. `[INFERRED]`
2. **One failure removes both capabilities.** Postgres down means Relay can neither serve nor even
   *record that work needs doing later*. With a separate broker one of the two survives. `[INFERRED]`
3. Lock pathologies cross between the two roles. `P-06` measured an abandoned `idle in transaction`
   session blocking a `DROP TABLE` for days, with no visible connection between cause and effect.
   `[MEASURED]`

**Why not the classic outbox, option (d):** Relay skips both the broker and the publisher, so the
outbox *is* the queue. `[INFERRED]` A classic outbox still has a dual-write between the outbox and the
broker — it only moves the problem somewhere retryable, which is why the publisher must be
at-least-once and consumers must be idempotent regardless. Skipping it buys one fewer component to
crash, monitor and scale, and removes dual-write from the *whole* system rather than just from enqueue.
What it gives up is routing, fan-out and topic semantics: `jobs` gives one row claimed by one worker.
Relay does not need fan-out; recorded as a capability foregone, not a cost paid.

### Cost

> **Lead item, because it is about correctness rather than load, and because it is the largest.**

1. **Relay owns crash recovery, and a broker gives it away for free.** `[MEASURED]` Din 5 `kill -9`'d a
   worker 3 s into an 8 s handler. The row stayed `running`, `attempts = 0`, execution row present,
   completion evidence gone. Three stuck-count readings over five minutes were identical, and a
   **fresh, visibly-polling worker ignored the row** — the claim query says `WHERE status = 'pending'`
   and the row is not in that set. Job **63** is still in the database. A broker redelivers an
   unacknowledged message when a consumer dies, because that is what a consumer ack *is*. Postgres has
   no equivalent.

   **So the trade is not "free outbox in exchange for polling overhead". It is "free outbox in exchange
   for writing redelivery yourself"** — and Week 2 is the invoice.

2. **That cost recurs; it is not a one-off Week 2 payment.** `[INFERRED]` Writing the reaper takes
   ownership of everything adjacent to it: lease duration, heartbeats, the reaper's own liveness, DLQ
   policy, retry backoff, and the interaction of all of them. `P-16` shows the reaper's central
   question — *dead or merely slow?* — is not answerable with today's schema, so the fix adds a column,
   which creates a lease, which needs a handler timeout (`P-15`), which `P-02` says cannot be enforced
   reliably against an uncooperative handler. A broker's maintainers test that surface; here it is my
   code and my tests, forever.

3. **The stuck row is reachable from the *graceful* path too, so this cost is not conditional on
   anyone using `kill -9`.** `[MEASURED-R]` Mid-job graceful shutdown took **5.167 s** for an 8 s
   handler, and the only bound on that path is the handler's own duration — Relay bounds nothing
   (`P-15`). Under a supervisor whose grace period is shorter than the handler (`docker stop`'s 10 s,
   Kubernetes' 30 s default), SIGTERM → handler still running → grace expires → SIGKILL produces
   exactly job 63.

4. **An idle fleet is not free, and the cost scales with workers rather than with work.**
   `[MEASURED]` One idle worker at `POLL_INTERVAL_SECONDS = 2.0` is **0.5 tx/s** — a full
   `BEGIN`/`SELECT`/`COMMIT` per poll, not a bare `SELECT` (`P-10`). Observed at fleet scale by
   accident: four forgotten workers held **3 idle connections and ~2 tx/s for zero work** (`P-13`).

5. **The poll interval prices three different things at once and cannot be tuned for one of them
   alone:** enqueue-to-start latency, database load, and idle shutdown latency — the last now measured
   at up to one full interval late (`P-10`, `[MEASURED-R]`: flag observed `0.962 s` into `0.959 s` of
   remaining sleep).

6. **MVCC churn on the hottest table in the system.** `[INFERRED]` Every job is updated at least twice;
   each transition writes a new row version that vacuum must later reclaim.

7. **The claim query's behaviour at depth is unknown.** `[NO EVIDENCE]` `P-03` is explicit that the
   index question — composite `(status, created_at)` versus partial `WHERE status = 'pending'` — gets
   `EXPLAIN ANALYZE`'d in Week 4 rather than guessed now. At today's table size the planner picks a
   `Seq Scan` (`[MEASURED]`, Din 6 `EXPLAIN`), so nothing about production behaviour follows from it.

8. **Shared blast radius**, per the two-roles discussion above. `[INFERRED]`, except `P-06`'s
   lock-crossing instance, which is `[MEASURED]`.

**The honest summary of the Cost field, and it is worth stating plainly because the opposite is the
usual pitch:** Postgres-as-queue is the right choice here **and it is not the cheap choice.** It trades
an integration problem that cannot be solved (dual-write) for an implementation problem that can
(redelivery). That is a good trade. Describing it as *"Postgres is simpler"* would be false.

### Rejected

**(b) Redis.** *What it does better:* far lower per-operation latency, no vacuum or bloat pressure, and
a push/blocking-pop model instead of polling — which would remove Cost items 4, 5 and 6 outright.
`[INFERRED]` Those are real advantages and they matter if the queue is genuinely hot.

Rejected because **durability and consistency-with-the-business-write are different properties, and
Redis can be given the first without the second.** `[INFERRED]` AOF with `fsync` always buys durability
of the enqueue, so the storage half of contract #1 on that one write. Still missing: the order row is
in Postgres and the job is in Redis, so **the dual-write returns and Case C becomes reachable again.**
Redis cannot participate in a Postgres transaction, and `MULTI` is atomic *within Redis* only — it is
not a cross-system transaction. With a dual-write, the word "accepted" in contract #1 becomes ambiguous,
because the order can exist with no job.

Worth naming separately: Redis's *default* configuration is weaker still — asynchronous persistence
means an acknowledged write can be lost on process death. `[INFERRED]` But that is a configuration
argument and it is fixable. The transactional-coupling argument is not.

**(c) RabbitMQ.** *What it does better, and it is the one thing Relay measurably lacks:* **redelivery
of unacknowledged messages when a consumer dies.** Din 5 measured that Postgres leaves a row nothing
will ever look at again; RabbitMQ makes that case disappear without any code from me. `[MEASURED]` for
the Postgres half, `[INFERRED]` for RabbitMQ's. That is a genuine, significant advantage and `D-01`'s
Cost item 1 is exactly the price of not having it.

Rejected for the same reason as Redis — the job lives outside the business transaction, so Case C
returns — plus a second operational system to run, monitor and reason about.

**And the framing that keeps this entry honest:** a broker gives you redelivery, which is **the easy
half**. The hard half is making redelivery *safe*, and that stays mine in either architecture.
Redelivery is **at-least-once**, not exactly-once: the broker cannot distinguish "consumer finished the
side effect and died before acking" from "consumer died before doing anything", because a missing ack
carries no information about which. `[INFERRED]`, and it is precisely `P-01`'s measured distinction —
*connect timeout = pahuncha nahi, read timeout = pata nahi.* So consumers must be idempotent regardless,
which is Week 3 either way. Postgres does not even give the easy half. That is the accurate comparison,
and it stops `D-01` from overstating what was rejected.

**(d) Classic outbox with a publisher and a broker.** Rejected as unnecessary indirection for Relay's
scope: it keeps a dual-write (outbox → broker), adds a process that can crash, and buys fan-out and
routing that Relay does not use. `[INFERRED]` Becomes correct the moment more than one consumer group
needs the same event.

**Revisit when:** any of these appear — (i) Week 5's measured Postgres-as-queue ceiling shows the claim
query or vacuum pressure limiting real throughput; (ii) fan-out to more than one consumer group is
required; (iii) queue load is measurably degrading business queries on the same instance; or (iv) the
redelivery machinery from Cost items 1–3 grows past the point where operating a broker is cheaper than
maintaining it. Note that (iv) is a **maintenance-cost** trigger, not a performance one, and it is the
most likely of the four.

---

## D-02: the worker claims with `SELECT … FOR UPDATE SKIP LOCKED` **and** a compare-and-set `UPDATE`, and the two halves do different jobs

**Problem:** Several workers poll one table. Each must end up executing a different job, and no job may
be executed twice. Read-then-write is the textbook lost update: two workers read the same `pending`
row, both decide they own it.

**The actual SQL the worker emits**, copied verbatim from the `echo=True` output on Din 6 Step 5 rather
than written from memory `[MEASURED]`:

```sql
SELECT jobs.id, jobs.type, jobs.payload
FROM jobs
WHERE jobs.status = $1::VARCHAR
ORDER BY jobs.created_at, jobs.id
LIMIT $2::INTEGER FOR UPDATE SKIP LOCKED
```

with `('pending', 1)`, followed by a **separate statement in the same transaction**:

```sql
UPDATE jobs SET status='running' WHERE jobs.id = $1 AND jobs.status = $2
```

Three details that only reading the emitted SQL reveals: it is **two** statements, not one; the bind
renders as `$1::VARCHAR` against a `TEXT` column (same type family in Postgres, so no cast or index
consequence — cosmetic, but reading the model instead of the SQL would have missed it); and
`ORDER BY created_at, id` carries the `id` tiebreaker because jobs enqueued in one transaction share
`created_at` exactly (`P-05`).

**Options, and what the *second* worker experiences under each:**

| | Option | Second worker experiences |
|---|---|---|
| (a) | `SELECT … FOR UPDATE` | **waits** on the row lock, then finds the row no longer `pending` |
| (b) | `SELECT … FOR UPDATE SKIP LOCKED` + compare-and-set `UPDATE` | **skips** to the next free row |
| (c) | `UPDATE … WHERE id = (subquery) RETURNING` | **depends entirely on the predicate** — see below |
| (d) | advisory lock around the claim | serialises the claim path; no data |
| (e) | `SERIALIZABLE` isolation | **errors** — `40001`, abort and retry |

**Chose:** (b), and the reason is that it is **two independent defences that solve two different
problems.** Din 6 Step 6 isolated them by running option (c) in three variants across two live `psql`
sessions, with session 1 deliberately left uncommitted. `[MEASURED]`

| Variant | Outer `WHERE` | Subquery | Session 2 blocked? | id returned | `rowcount` | Outcome |
|---|---|---|---|---|---|---|
| **1** | `id = (subquery)` | plain | **yes**, on the row lock | **76 — the same id session 1 claimed** | **1** | ❌ silent duplicate claim |
| **2** | `id = (subquery) AND status='pending'` | plain | **yes** | none | **0** | ✅ safe, but it waited and got nothing |
| **3** | `id = (subquery)` | `FOR UPDATE SKIP LOCKED` | **no** | **77 — the next row** | **1** | ✅ safe, and it got useful work |

**Why variant 1 produces a duplicate, measured rather than reasoned.** `EXPLAIN` on the statement
`[MEASURED, Din 6 reviewer]`:

```
Update on jobs
  InitPlan 1 (returns $0)
    ->  Limit
          ->  Sort  (Sort Key: jobs_1.created_at, jobs_1.id)
                ->  Seq Scan on jobs jobs_1   Filter: (status = 'pending'::text)
  ->  Seq Scan on jobs   Filter: (id = $0)
```

The subquery does not reference the outer row, so it is **uncorrelated** and Postgres evaluates it
**once, before the scan, as an `InitPlan` producing a constant `$0`.** The outer qualification is
therefore literally `Filter: (id = $0)` — **`status` appears nowhere in it.**

That is what makes `EvalPlanQual` unsafe here. Under `READ COMMITTED` a writer that blocks on a locked
row does not wake holding a stale tuple: it re-fetches the newest committed version and **re-evaluates
the statement's qualification** against it. Din 4 saw that save a claim, because Din 4's qual was
`status='pending'` and the recheck failed. In variant 1 the qual is `id = $0`, which is **still true**
after session 1 set `status='running'`. So session 2 updates the row again and `RETURNING` hands back
the same id with `UPDATE 1`. Both sessions were told they own job 76. No error, no warning, both
`rowcount = 1` — **and the row's final state is `status='running'`, which is exactly what one correct
claim looks like.** `jobs` cannot record that this happened.

**The generalisation, and it is the most useful thing either entry produced:** `EvalPlanQual` is not a
concurrency safety feature. It is a recheck of **whatever predicate you wrote.** Variants 1 and 2 are
the same mechanism producing opposite outcomes, and the only difference is whether the changing column
is in the qual. This is a textbook **lost update**, which DDIA Ch 7 names, along with the fix Relay
already uses — compare-and-set.

**So the two halves, priced separately:**

| Half | Provides | What Step 6 shows happens without it |
|---|---|---|
| `FOR UPDATE SKIP LOCKED` in the claim `SELECT` | **liveness** — never wait behind a row another worker holds | Variant 2: correct, but the worker blocks and is then told `rowcount = 0` for its trouble |
| `AND status='pending'` on the `UPDATE` | **safety** — the old value is part of the predicate | Variant 1: a silent duplicate claim |

`D-06` called the guard *"not an optimisation, it is the transition guard"* on Din 1. Din 6 is the
first time in this project that **`rowcount = 0` has actually been observed** — Din 4 and Din 5 both
recorded the branch as never having fired, and Din 5's two workers claimed **4 µs apart** without
provoking it. Variant 2 produces it on demand.

### Cost

1. **Ordering becomes more approximate.** `[INFERRED]` A skipped row is deferred to a later poll, so
   best-effort FIFO (`P-05`) degrades further under contention. Acceptable: ordering is not one of
   Relay's five contract promises.
2. **An extra `UPDATE` per claim** — two statements and two round trips instead of one, more write
   amplification and MVCC churn on the hottest statement in the system. `[INFERRED]`
3. **The `LIMIT` subtlety is real and was measured.** `[MEASURED]` Din 3 found `LockRows` sitting
   **below** `Limit` in the plan, which is why a plain-`FOR UPDATE` worker can block on one row while
   nine are free — the row is locked before the limit is satisfied.
4. **One round trip per claim, with the poll interval bounding throughput.** `[MEASURED]` `P-10`:
   0.5 tx/s per idle worker at 2.0 s, and per-job overhead outside the handler measured at
   **39–57 ms** for three transactions (`[MEASURED-R]`, Din 5 M10).
5. **On conflict the worker sleeps a full poll interval instead of retrying immediately.**
   `[INFERRED from code]`, and this is a Din 6 code-review finding rather than a measurement. In
   `run_worker()`, the `rowcount == 0` branch leaves `claimed_job` as `None`, which falls through to
   `await asyncio.sleep(POLL_INTERVAL_SECONDS)` — so a worker that loses a race waits 2 s even when
   other `pending` rows are available. Step 6 variant 2 shows `rowcount = 0` is genuinely reachable, so
   the branch is no longer hypothetical; it has still **never been observed in the worker itself**.
   Cheap to change (retry immediately, bounded) and deliberately not changed in Week 1.
6. **The safety argument rests on discipline, not on the schema.** `[INFERRED]` `P-04`: no constraint
   can express "`succeeded → running` is illegal", because that needs two versions of one row. Every
   `status` update must carry the guard, and the database will not remind me. Din 6 measured what the
   omission costs — variant 1.

### Rejected

**(a) plain `SELECT … FOR UPDATE`.** *What it does better:* strictly better ordering — it does not skip,
so the oldest pending row is the one that gets claimed. `[INFERRED]`

Rejected on **lock wait**, measured: with a 6 s lock held on the oldest pending row, the `skip_locked`
worker began real work **1.25 s** in, while the plain `FOR UPDATE` worker waited the full **6 s**
(`[MEASURED]`, Din 4). A worker sitting in `Lock`/`transactionid` in front of one row while other rows
are free is doing nothing, and Cost item 3 explains why one row is enough to cause it.

**Not claimed here: any throughput comparison.** `[NO EVIDENCE]` `P-12` disqualified the Din 4 numbers
that looked like one — both two-worker runs had a staggered second worker (10 s and 23 s late), so the
7/3 and 8/2 splits are start-time artifacts. Din 5 produced a clean `SKIP LOCKED` **baseline** (three
workers, first claims within **12.6 ms**, survivors split **4/4**, drain **32.2 s** against a predicted
32 s, **0 duplicates**), but there is still no like-for-like run of plain `FOR UPDATE`, so no comparison
exists in either direction.

**(c) `UPDATE … WHERE status='pending' RETURNING` — and the imprecise rejection is the tempting one.**

**Option (c) is not broken. The naive form of it is.** `[MEASURED]` That distinction is the whole of
Step 6. Variant 2 — the same single statement **with the guard in the predicate** — is a sound claim
mechanism, and it is arguably simpler than what Relay ships: one statement instead of two, no explicit
lock, and it produced `rowcount = 0` correctly under a live race.

What (c)-with-guard gives up is variant 3's property. When two workers collide, Relay's form has
**both** doing useful work (the second skips to the next row); (c)-with-guard has the loser blocked,
then handed `rowcount = 0`, then polling again. That is the real, statable cost, and it is a far better
rejection than *"explicit lock semantics are clearer"*.

The naive form is rejected outright, with the mechanism above: the `InitPlan` freezes the target id
before any lock is taken, `EvalPlanQual` rechecks a qual that does not mention `status`, and two workers
claim one job with no error and no trace in `jobs`.

**(d) advisory lock around the claim.** `[NO EVIDENCE]` — never run, and this entry does not pretend
otherwise. The mechanism argument against it `[INFERRED]`: an advisory lock is not tied to the row, so
it serialises the claim path across all workers rather than per-job, converting a per-row conflict into
a global bottleneck. Its genuine advantage is that it works when the contended resource is not a row at
all. Worth measuring in Week 4 alongside `P-03` if the claim query becomes a bottleneck.

**(e) `SERIALIZABLE`.** `[NO EVIDENCE]` on this project — never run against `jobs`. `[INFERRED]` from
Week 0 Day 5 and DDIA Ch 7: SSI detects the conflict at commit and aborts with `40001` rather than
blocking, so the loser has already done its work and must retry, and every caller needs `40001` handling.
For a claim that is contended by design, abort-and-retry is the wrong shape — the conflict is expected,
not exceptional. Its genuine advantage is that it catches **write skew and phantoms**, which row locks
cannot, and that matters for invariants spanning several rows. Relay's claim is a single-row transition,
so it does not need that reach.

**Revisit when:** `P-03`'s Week 4 `EXPLAIN ANALYZE` shows the claim `SELECT` is the bottleneck at depth,
or Week 2's reaper introduces a second writer to `status` — at which point Cost item 6 stops being a
discipline problem and becomes a design problem, because two independent writers to one column need
their transitions enumerated rather than remembered.

---

# Schema decisions (Week 1, Din 1)

> **Provenance — read this before trusting the reasoning below.**
>
> These six decisions were **explained to me**, not derived by me. I read the trade-offs for the first time on Din 1 and understood roughly 60% on first pass. The conclusions are recorded here because the schema had to be built, but the *reasoning* is currently **recognisable to me, not recallable**.
>
> **Measurement status:** most of the reasoning below is documentation-based **inference** about PostgreSQL 16 behaviour. Two specific claims were subsequently **verified on this instance** and are marked `[MEASURED]` with their actual output — the enum-in-transaction restriction (D-06) and the `ADD COLUMN ... DEFAULT` rewrite question (D-07). Both verifications *contradicted the reason originally given for the choice* without changing the choice itself; that is recorded in place rather than quietly corrected.
>
> Everything not marked `[MEASURED]` is inference. Notably, the `ACCESS EXCLUSIVE` lock-queue hazard in D-07 is **not** measured.
>
> Weekend consolidation must re-test these without context. Whatever survives that is mine; the rest is still borrowed.

---

## D-03: `jobs.id` is a DB-generated `bigint` identity column, not a client-supplied UUID

**Problem:** Every row needs a unique identity. The choice also silently decides *who* is allowed to mint that identity — Relay, or its caller — and that has consequences well beyond this column.

**Options:**
- (a) `bigint GENERATED BY DEFAULT AS IDENTITY` — DB-generated sequence
- (b) `bigserial` — same mechanism, legacy Postgres syntax
- (c) `UUID` v4 — random, client-generatable
- (d) `UUID` v7 — timestamp-prefixed, client-generatable, index-friendly

**Chose:** (a).

The tempting argument for a client-supplied UUID was duplicate suppression: if a `POST /jobs` response is lost and the client retries with the same id, the primary key conflict blocks the duplicate. This is technically true and was the strongest case for (c)/(d).

It was rejected because **a primary key and an idempotency key are different concerns**, and merging them creates three problems:

1. **Storage identity would depend on caller input.** A buggy client reusing one id would have its genuinely-new jobs silently rejected. That is silent data loss, which violates contract #1.
2. **Idempotency needs a time window; a primary key has none.** If Week 4 adds cleanup of old rows, a client replaying the same id six months later would find no conflict and the job would execute again.
3. **Dedup should be opt-in.** Two logically distinct jobs may legitimately carry identical payloads. A PK-based scheme removes that choice from the caller.

The correct shape is two columns: `id` stays internal and DB-owned; Week 3 adds a separate nullable `idempotency_key text UNIQUE` supplied by the caller. This also matches what the Week 0 Day 5 log already anticipated (*"idempotency key + unique constraint"*).

Once that argument is settled, no remaining UUID benefit is consumed by Relay this month:
- Client-side generation → not needed (idempotency lives in its own column)
- Unguessable ids → **there is no auth in Week 1**, so an unguessable id is obscurity, not security. The real fix is authorization, not id format.
- Distributed generation → single Postgres, no sharding, no multi-master

And one practical factor that genuinely matters for this project: Din 4 and Din 5 are entirely `psql`-driven failure injection. Copying `42` versus `550e8400-e29b-41d4-a716-446655440000` dozens of times across two days of experiments directly affects how fast the experiments run — and the experiments are the point of the project.

Chose (a) over (b) because `GENERATED ... AS IDENTITY` is SQL-standard (PG 10+) and handles sequence ownership cleanly. **If SQLAlchemy/Alembic setup creates friction, `bigserial` is an acceptable substitute** — the practical difference is close to zero and this must not become a Din 1 blocker.

**Cost:**
1. **Ordering is not guaranteed.** `nextval` is non-transactional, so ids have gaps after rollbacks, and more importantly **id order is not commit order**: a transaction that took `id = 5` first can commit *after* one that took `id = 6`. So `ORDER BY id` is an approximation of "oldest job", not a guarantee. Accepted knowingly — FIFO fairness is not one of Relay's five contract promises. Tracked as `P-05`.
2. **The door to client-generated ids is closed** for as long as `id` is the only identity column. Reopening it means a table rewrite. Acceptable now because Month 1 has no production data, so the reversal cost is currently low.
3. Ids leak approximate job volume to anyone who can read them. Irrelevant while the only user is the developer; would need revisiting alongside auth.

**Rejected:**
- **(b) `bigserial`** — functionally equivalent, but legacy syntax with messier sequence ownership. Kept as a fallback, not a preference.
- **(c) UUID v4** — 16 bytes instead of 8, and random values insert into the middle of the B-tree index, causing page splits and poor cache locality. Pays a write cost for benefits Relay does not use.
- **(d) UUID v7** — strictly better than v4 when time-ordering is acceptable (timestamp prefix keeps inserts at the index's right edge). Rejected only because the client-generation requirement itself was rejected. Also **not built into PG 16** — [`uuidv7()` arrived in PostgreSQL 18](https://www.postgresql.org/docs/current/release-18.html) — so it would need app-side generation. Note that its timestamp prefix leaks creation time, which is a reason to prefer v4 if that ever matters.

**Revisit when:** Relay needs multi-region or multi-database id generation, or a client genuinely needs the id before the DB round-trip.

---

## D-04: `jobs.type` is unconstrained `text`; validation lives in the application, not the database

**Problem:** `type` selects which handler executes the job. Should the database enforce that the value is one of a known set?

**Options:**
- (a) `text NOT NULL`, no DB constraint
- (b) `text` + `CHECK (type IN (...))`
- (c) native `ENUM`
- (d) `text` + lookup table + foreign key

**Chose:** (a).

**The decisive reason: the database cannot express the invariant I actually care about.** The real rule is not *"type is a valid string"* — it is **"a handler function for this type is registered in the worker."** Postgres has no knowledge of the worker's handler registry.

So a `CHECK` constraint would accept `'send_email'`, and if no `send_email` handler exists, the job still enters the DB, is still claimed, and still fails at execution. The constraint prevents nothing and supplies **false confidence** — which is worse than no constraint, because I would start trusting it. Generalised as `P-04`.

This is the Week 0 Day 5 lesson recurring. From that log: *"Exp 2 = the rule was never in the database at all."* The doctors' on-call rule lived in an application `if`, so Postgres had nothing to object to. Same shape here.

**Second reason: the cost of a bad value is bounded and visible.** A typo (`'send_emial'`) produces: job accepted → handler lookup fails → exception → `failed` → Week 2 retry → attempts exhausted → **DLQ**. That is contract #4 working as designed (*"terminal failures enter a DLQ, not silence"*). No corruption, no silent wrongness, no other job affected.

This is the sharp contrast with `status` (D-06): a bad `status` value makes a row **invisible** to `WHERE status = 'pending'`, which is silent. A bad `type` value produces a loud, contained failure. **The constraint decision follows the failure mode, not a general preference for strictness.**

**Third reason: change frequency.** Adding job types is the single most frequent change in a job queue's lifetime. Putting migration friction on the most-changed axis is backwards. General heuristic: *whatever changes most often should be cheapest to change.*

**Reversal is cheap**, which is what makes (a) safe: going from `text` to `text + CHECK` is one DDL statement with no rewrite, and back again is equally cheap. When reversal is cheap, prefer the option that does not block you and tighten only once real pain appears.

**Cost:**
1. **Typos reach the database.** Garbage job types will accumulate as DLQ entries. Accepted because they are visible and contained.
2. **No single place lists the valid types.** The authoritative set lives in the worker's handler registry, which means the DB alone cannot answer "what job types exist?"
3. `text` is unbounded, so a malformed client could store a very large `type` string. A `CHECK (length(type) <= 100)` bound is cheap and defensible; **not applied yet** — treated as optional hardening, not correctness.

**Rejected:**
- **(c) `ENUM`** — worst of both: requires a migration for the most frequently changing value set, *and* still does not enforce the real invariant. Appropriate for genuinely closed domain sets (weekdays, compass directions), which job types are not.
- **(b) `text + CHECK`** — same objection as (c) with easier migrations. Reconsider only if unbounded typos become a measured operational problem.
- **(d) lookup table + FK** — adds a table and a per-write FK check for a set that will change constantly, and still cannot see the handler registry. Becomes genuinely attractive only when per-type *metadata* is needed (per-type timeout, retry policy, enabled flag) — at which point validation is a free side effect rather than the goal.

**Revisit when:** Week 4 needs per-type configuration. Then (d) arrives naturally and brings validation with it.

**Amendment — Din 3, the bill for this decision arrived, and it was cheaper than the Cost section predicted.** Din 3 built the handler registry, so the invariant this entry said the database could not see now exists somewhere concrete. An unregistered type was enqueued and the worker's behaviour was **measured**: job `23`, `type = 'does_not_exist'` → claimed once, marked `failed` once, then the worker went back to polling. No hot loop, no crash, no other job affected.

Cost #1 above ("typos reach the database … visible and contained") is therefore confirmed rather than assumed. Two refinements the original entry did not state:

1. **The chosen handling — claim it, then mark `failed` — consumes the claim.** That is deliberate (the alternative, leaving it claimable, means writing `running → pending`, which is Week 2's reaper's transition, and it re-encounters the row every poll). The cost is specific: a **deployment ordering mistake**, where the worker rolls out before its handler is registered, becomes permanent for those rows rather than self-healing. With Week 2's retries it will burn every attempt and land in the DLQ for a reason that has nothing to do with the job.
2. **So the mitigation is operational, not schema-level:** deploy handler registration before, or with, the workers that consume the type. Nothing in the database can enforce that ordering — which is the same conclusion this entry started from, now arriving from the deployment side rather than the validation side.

This does not change the decision. It is what *"the invariant lives in the application"* actually costs, priced.

---

## D-05: `jobs.payload` is `jsonb NOT NULL DEFAULT '{}'::jsonb`

**Problem:** Job input data must be stored. Relay never interprets it; it is an opaque blob forwarded to the worker.

**Options:**
- (a) `json` — stored as raw text
- (b) `jsonb` — stored as decomposed binary
- (c) `text` / `bytea` — fully opaque

**Chose:** (b).

**Correction to a common framing:** both `json` and `jsonb` validate JSON syntax on insert, so "validation" is *not* a differentiator between them. The real differences are: `json` preserves byte-exact text, key order, and duplicate keys, and re-parses on every access; `jsonb` normalises (key order lost, duplicate keys collapsed to last-wins), does not re-parse on read, and can carry a GIN index.

The reason usually given for `jsonb` — GIN indexing and querying inside the payload — **is not consumed by Relay**, since the scope lock means Relay never reads inside the payload. Basing the decision on an unused capability would be dishonest. The three reasons that actually apply:

1. **Option value is free.** `jsonb` costs nothing today and leaves the door open to an admin/debug query later (e.g. "which jobs reference `user_id = 5`"). `json` closes that door, and reopening it later means a table rewrite. When two options cost the same today, prefer the one that preserves future options.
2. **Read performance.** The worker reads the payload on every execution. `json` re-parses text on each access; `jsonb` does not. This shows up in Week 4's throughput work.
3. **Normalisation helps Week 3.** If the idempotency key is ever derived from a payload hash, `jsonb`'s normalisation is an asset: two logically identical payloads with different key order hash identically. Under `json`, `{"a":1,"b":2}` and `{"b":2,"a":1}` are different strings with different hashes.

**`NOT NULL DEFAULT '{}'` reasoning:** a NULL payload and an empty payload carry no distinct business meaning — both mean "no arguments". Keeping two representations of one state only creates bugs, since every handler would need to check both and one will eventually be forgotten. The default means jobs needing no input (e.g. a cleanup job) require nothing from the caller, and handlers are guaranteed a dict rather than `None`. General pattern: *represent "missing" as "empty", not as NULL, when both mean the same thing.*

**Cost:**
1. **Byte-exact input is not recoverable.** Key order and duplicate keys are lost. If a signed payload ever needs verification, re-serialising from `jsonb` will break the signature. Not a Relay requirement today — Relay does not sign payloads — but this permanently forecloses that option without a migration.
2. **Insert is slightly more expensive** than `json` (parse + normalise rather than store text).
3. **Large payloads carry a TOAST cost.** Values beyond roughly 2 KB are compressed and stored out-of-line. Precisely: a TOASTed value is **not** read unless the column is actually selected, and an `UPDATE` that does not modify the payload reuses the TOAST pointer rather than rewriting it. So the claim query is only affected if it selects `payload`. A Week 4 concern, not a Din 1 one.
4. **Payload size limit and `GET` response exclusion — resolved in Din 2.** Both ends of the pipeline constrain this one column, for different reasons. Full reasoning in the amendment below.


**Rejected:**
- **(a) `json`** — one strong use case exists: byte-exact preservation for cryptographic signature verification, audit/compliance requirements, or storing third-party signed webhook bodies. None apply to Relay.
- **(c) `text` / `bytea`** — maximally opaque and cheapest to write, but discards free syntax validation and all future query ability for no benefit. Would only make sense if payloads were genuinely non-JSON binary.

---

### `[AMENDED — Din 2]` Cost #4 resolved: what bounds this column, on the way in and on the way out

Cost #4 deferred two things to Din 2: the exact size limit, and where to enforce it. Recorded here rather than as a new `D-` number because both concern this same column.

#### Ingress — the size limit

**Chose:** a **256 KB payload budget**, enforced as a **266,240-byte bound on the whole request body**, in **HTTP middleware**, returning **`413`**.

Two numbers, one check. The 4 KB difference is envelope: the JSON structure and the `type` field. Only 266,240 is enforced; 256 KB is the budget it derives from, not a second independent limit. That distinction is worth stating because the first implementation *did* have two independent checks — a middleware bound on the body and a Pydantic validator on the payload dict — and they disagreed, producing `413` for some oversized requests and `422` for others. There is now exactly one enforcement point, and the Pydantic validator has been removed.

On the status code: RFC 9110 names 413 **`Content Too Large`**. The older `Request Entity Too Large` label is RFC 7231's; both constants exist in Starlette and both mean 413. The code uses the RFC 9110 name to match the RFC being cited.

**Why 256 KB:** a job payload is *arguments to a function call*, not a data transfer. Anything genuinely large — files, images, exports — belongs in object storage with the payload carrying only a reference. Managed queues land in the same order of magnitude for the same reason (AWS SQS caps a message at 256 KB), which is corroboration rather than justification. **No measurement supports 256 KB specifically** — it is an order-of-magnitude judgement, and cheap to move either way.

**Why middleware, and not a validator — this was found the hard way. `[MEASURED]`**

The first implementation put the check inside the `create_job` handler body. FastAPI reads and parses the request body while resolving parameters, *before* the function body runs, so the check ran after the damage. Three ~306 KB requests separated the cases:

| Request | Before the fix | After the fix |
|---|---|---|
| oversized, valid JSON | `413` | `413` |
| oversized, `type: ""` | `422` `string_too_short` | **`413`** |
| oversized, malformed JSON | `422` `json_invalid`, `loc: ["body", 306274]` | **`413`**, no `loc` |

The `loc: ["body", 306274]` is the proof: the JSON parser had reached character 306,274, so the entire body was buffered and parse was attempted before any size check. The limit provided **no** memory or CPU protection, and the status code for an oversized body depended on whether the body happened to be valid. After the move, all three return `413` and the parser offset is gone — no parse is attempted.

This is precisely the property Cost #4 asked for (*"reject before bytes are parsed"*), and it is only obtainable outside the handler: FastAPI reads the body before dependency resolution, so not even a `Depends` guard runs early enough.

**Cost:**
1. **The limit rests on a header the sender controls.** `Content-Length` is absent under `Transfer-Encoding: chunked` and optional in HTTP/2, and the check is skipped when the header is missing. The threat model is therefore *an honest client that made a mistake*, not an adversary. Recorded as `P-08` and deliberately unfixed in Week 1: closing it needs ASGI-level stream byte-counting, which is Week 4 hardening. `D-04`'s heuristic applies — tighten once real pain appears.
2. **The database column stays unbounded.** This constrains one entry point, not the column. Din 4 and Din 5 insert directly via `psql`, entirely outside it. Same shape as `D-04` Cost #3, where `max_length=100` on `type` lives at the API layer and the DB `CHECK` is still unapplied.
3. **The number is not derived from measurement.** If Week 4 finds real payloads clustering above it, the limit was wrong; far below, it was never load-bearing. Both are information; neither exists yet.

**Rejected:**
- **A Pydantic `field_validator` on serialised payload size** — measured above to run after parse, so it cannot prevent the cost that motivates the limit. It also had to re-serialise the payload with `json.dumps` purely to measure it, making the oversized path *more* expensive.
- **A DB `CHECK` on `octet_length(payload)`** — would bound the column (which the API-layer choice does not), but only after the bytes crossed the network, were parsed, and reached Postgres. Worth reconsidering when non-API write paths start mattering.
- **No limit at all** — tenable while the only client is the developer, but the failure mode is unusually bad. Week 0 Day 1 measured that CPU-bound synchronous work inside the event loop stalls every concurrent request (`6.04s vs 2.04s`), and a large `json.loads` is exactly that. One connection could stall the whole API process.

#### Egress — `payload` is excluded from `GET /jobs/{id}`

`GET /jobs/{id}` returns `{job_id, status}` and selects only those two columns at the SQL level. Two independent reasons, and it is worth keeping them separate because one of them turned out to be weaker than assumed:

**(a) Avoids the TOAST read.** Cost #3 above established that a TOASTed value is not read unless the column is selected. `GET` is the polling endpoint, so this is the one query that runs repeatedly per job. **Correction to an earlier framing:** the saving is *only* the TOAST dereference. PostgreSQL is a row-store reading whole 8 KB heap pages, so `SELECT id, status` and `SELECT id, status, type, created_at` cost the same heap I/O — every non-TOASTed column is already in the tuple. Adding `type` or `created_at` to the response later is therefore close to free, and the reason for keeping the response minimal is **not** I/O.

**(b) Narrows unauthenticated data exposure.** `D-03` chose sequential DB-generated ids, explicitly accepting that they are guessable, on the grounds that *"an unguessable id is obscurity, not security. The real fix is authorization."* That acceptance is cheap only while ids reveal nothing. Returning `payload` would turn a guessable id into a data read primitive over an endpoint with no auth — enumeration would yield whatever callers put in payloads. Excluding it **narrows the blast radius; it does not eliminate exposure**: `404` versus `200` still reveals which ids exist, and `status` still reveals what the system is doing. `D-03` Cost #3 already noted ids leak approximate job volume. The real fix remains authorization, which is out of scope for the month.

The actual reason the response is minimal is neither of the above: **adding a response field is backward-compatible, removing one is a breaking change.** Under that asymmetry, minimal is the reversible starting point. `attempts` was excluded on top of that because it is always `0` in Week 1 — a field that cannot vary teaches a client nothing while creating a compatibility obligation.

---

## D-06: `jobs.status` is `text` + `CHECK`; state *transitions* are enforced by compare-and-set, not by the schema

**Problem:** Two separate problems hide in this one column, and conflating them is the trap:
1. Which *values* are legal?
2. Which *transitions between* values are legal?

**Options for (1):**
- (a) native `ENUM`
- (b) `text` + `CHECK (status IN (...))`
- (c) lookup table + FK

**Chose (1): (b)** — `text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','succeeded','failed'))`.

First, the argument usually given for (b) needs correcting. *"Adding an enum value is painful in transactional migrations"* rests on pre-PG 12 behaviour, where `ALTER TYPE ... ADD VALUE` could not run inside a transaction block at all. **On PG 12+ it can** — the new value simply cannot be *used* in the same transaction that added it. Since Relay runs PG 16, adding `dead_letter` in Week 2 would have been easy either way, so that argument does not decide this. **`[MEASURED]`** — see verification at the end of this entry.

The reasons that do decide it:

1. **`DROP VALUE` does not exist, at all.** This is decisive given where the project is. Week 1 is the start of a four-week design I do not yet fully understand, so status naming will very likely change — `failed` may need splitting into retryable and terminal, `cancelled` may appear, `dead_letter` semantics may shift. Under `ENUM`, a wrong value is permanent unless the entire type is recreated and the column cast. Under `CHECK`, it is `DROP CONSTRAINT` + `ADD CONSTRAINT`.
2. **Alembic does not autogenerate enum value changes.** Alembic is being set up today. With `ENUM`, `alembic revision --autogenerate` would run, detect nothing, and give a false all-clear — a silent trap waiting in Week 2.
3. **The storage difference is irrelevant here.** `ENUM` is 4 bytes against roughly 11 for `'pending'` as text. With order-of-thousands rows in Month 1, that is a few KB. Trading flexibility for it would be optimisation without measurement.

The real driver: **this schema is going to change and I do not yet know how.** Under high uncertainty, minimise the cost of change, not the cost of storage.

`DEFAULT 'pending'` is included because a job is *born* pending — it makes that invariant structural, prevents an `INSERT` from accidentally creating a job in `running`, and makes manual `psql` inserts during Din 4/5 experiments trivial.

**Chose (2): compare-and-set in the application.**

**Neither `ENUM`, nor `CHECK`, nor an FK can prevent this:**

```sql
UPDATE jobs SET status = 'running' WHERE id = 1;   -- job was already 'succeeded'
```

Every constraint is satisfied, because `'running'` is in the allowed set. The transition is nonetheless wrong.

The reason no constraint can catch it: evaluating *"succeeded → running is illegal"* requires seeing **both the old and the new value**. A `CHECK` constraint sees only the row's current state; it has no access to what the row was before.

This is the Day 5 rule of thumb again, from my own log: *"a constraint works when the invariant fits inside a single row. When the invariant spans multiple rows, constraints cannot help."* Here the invariant spans two *versions* of one row rather than multiple rows, but the limitation is identical.

Enforcement therefore lives in the claim statement:

```sql
UPDATE jobs SET status = 'running' WHERE id = $1 AND status = 'pending'
```

`AND status = 'pending'` is **not an optimisation — it is the transition guard**, and the worker must check the affected row count: 1 means the claim succeeded, 0 means someone else got there first and this worker should move on.

This single statement does three things at once: it blocks illegal transitions, it blocks double claims, and it is **atomic** — the check and the write are in one statement, so nothing can interleave between them. That third property is what defeats Day 5's lost update. From that log: *"check-then-act is broken under concurrency... the truth of the read expires the moment I stop holding a lock on it."* A separate `SELECT` then `UPDATE` is check-then-act. `UPDATE ... WHERE status = 'pending'` is not.

**Cost:**
1. **Illegal transitions are only prevented where the guard is written.** Any future code path that updates `status` without a `WHERE` predicate on the old value bypasses the rule entirely. The database will not help. This is a permanent discipline requirement, and it is exactly the failure mode listed in the Day 5 log's `FOR UPDATE` column: *"forgetting the lock in one code path."*
2. `text` costs a few bytes more per row than `ENUM`.
3. Every status update site must check affected row count. Ignoring a `0` result would silently swallow a lost claim.
4. Adding `dead_letter` in Week 2 requires `DROP CONSTRAINT` + `ADD CONSTRAINT`, and `ADD CONSTRAINT ... CHECK` takes an `ACCESS EXCLUSIVE` lock and validates the whole table. The correct two-step pattern must be used then:
   ```sql
   ALTER TABLE jobs ADD CONSTRAINT jobs_status_check CHECK (...) NOT VALID;  -- instant
   ALTER TABLE jobs VALIDATE CONSTRAINT jobs_status_check;                   -- scans, but only SHARE UPDATE EXCLUSIVE; writes not blocked
   ```
   Irrelevant on today's empty table; needed in Week 2.

**Rejected:**
- **(a) `ENUM`** — no `DROP VALUE`, Alembic blind spot, and a storage saving too small to measure. Appropriate when the value set is genuinely permanent, when storage has been *measured* as a problem, or when enum's creation-order sorting is wanted (e.g. `('low','medium','high')`, which sorts uselessly as text).
- **(c) lookup table + FK** — adds a table and a per-write FK check for a set of five values that changes perhaps twice in the project's life, and still cannot enforce transitions.
- **A trigger for transition enforcement** — a trigger *can* see `OLD` and `NEW`, so it would work. Rejected because: it hides the rule from the Python code where a reader expects it; it is harder to unit test; it duplicates a guard that is needed anyway for concurrency, so the same rule would live in two places and eventually diverge; and in a project whose purpose is understanding where safety comes from, burying that safety inside the database defeats the purpose. A trigger becomes correct when multiple independent applications write to the same table and none can be trusted individually.

**`[MEASURED]` — enum-in-transaction behaviour on this instance (PostgreSQL 16):**

```sql
CREATE TYPE t_enumtest AS ENUM ('a','b');
BEGIN;
ALTER TYPE t_enumtest ADD VALUE 'c';        -- CREATE TYPE / BEGIN / ALTER TYPE  → all OK
CREATE TABLE tt_enumtest (x t_enumtest);    -- CREATE TABLE → OK
INSERT INTO tt_enumtest VALUES ('c');       -- ERROR
COMMIT;                                      -- became ROLLBACK (txn already aborted)
```

Actual error text:
```
ERROR:  unsafe use of new value "c" of enum type t_enumtest
HINT:   New enum values must be committed before they can be used.
```

**Result:** the corrected framing holds exactly. `ALTER TYPE ... ADD VALUE` **does** run inside a transaction block on PG 16 — so "you cannot add enum values in a transactional migration" is false here. The real restriction is narrower: the new value cannot be *used* until the adding transaction commits. Practically that means a `dead_letter` migration would need **two** migration steps (add the value, then use it), which is an inconvenience rather than the blocker it is usually described as.

**This does not change the decision.** The reasons that actually decided it — no `DROP VALUE`, and Alembic's autogenerate blind spot — are untouched by this measurement. Recording it because the *stated* reason for the choice must be the *real* reason, or the entry is worthless in six months.

*(Test artefacts were rolled back / dropped; `t_enumtest` and `tt_enumtest` do not exist.)*

**Amendment — Week 2 Din 5/Din 6: `dead_letter` landed, Cost 4's pattern held, and the condition it was
missing now has a name.** Nothing above is edited. Cost 4 was written on Week 1 Din 1 as a prediction about a
migration that had not been written yet; this records how much of it was right.

**1. Which option ran, and whether `NOT VALID`'s benefit was actually obtained.** Two migrations, not one
`[MEASURED-R]`:

| Revision | Statement | `convalidated` after |
|---|---|---|
| `15a05eeb0f79` | `DROP CONSTRAINT` + `ADD CONSTRAINT jobs_status_check CHECK (... five values) NOT VALID` | `false` |
| `682e01d87be9` | `ALTER TABLE jobs VALIDATE CONSTRAINT jobs_status_check` | `true` |

Re-read on Din 6, independently: `jobs_status_check`, `convalidated = t`,
`CHECK ((status = ANY (ARRAY['pending','running','succeeded','failed','dead_letter'])))`, `alembic_version =
682e01d87be9` `[MEASURED]`. **The entire deliverable of the split is that one boolean changing twice** — there
is no other observable difference at `104` rows.

**And the missing condition in Cost 4 is this: `NOT VALID`'s benefit is a property of transaction
*boundaries*, not of the keyword.** Alembic wraps `upgrade()` in a single transaction, and
`ADD CONSTRAINT ... NOT VALID` holds `AccessExclusiveLock` for the rest of **its** transaction
`[MEASURED-R, from a rolled-back probe]`. So a single-migration version would have written `NOT VALID`,
held `ACCESS EXCLUSIVE` until commit, and run the validation scan underneath it — the keyword present, the
benefit absent. Cost 4 above prescribes the two statements and never says they must land in **two
transactions**. That omission is the kind `P-04` is about: the recipe was right and the condition that makes
it work was unstated.

**2. The lock queue, measured for the first time — and split into two halves that must not be merged.** Week 1
Din 3 attempted this and failed (nothing was queueing, so the lock was granted instantly); Din 5 ran three
sessions with the observer reading from **inside** the wait `[MEASURED-R]`:

```
HOLDER   pid=3038  ACCESS SHARE held inside an open transaction (a plain SELECT)
WAITER   pid=3039  requesting ACCESS EXCLUSIVE on jobs
pg_stat_activity:  3038 state=idle in transaction  wait=Client/ClientRead
                   3039 state=active              wait=Lock/relation
pg_locks on jobs:  3038 AccessShareLock      granted=True
                   3039 AccessExclusiveLock  granted=False
WAITER   LockNotAvailableError: canceling statement due to lock timeout   (lock_timeout = 9s)
```

**Measured:** the queue forms, and **a plain `SELECT` in an open transaction blocks the whole DDL** —
`wait_event_type = Lock`, a named lock mode with `granted = false` behind one with `granted = true`. That
closes an item `LEARNING_LOG.md` had carried since Week 1 Din 1 as inference only.

**Declared substitution, because this is where the expensive lie would be:** the waiter was
`LOCK TABLE jobs IN ACCESS EXCLUSIVE MODE`, **not the migration**. The lock *mode* is identical, so the
conflict and queueing mechanism is identical. What it does **not** measure is **how long the real
`ADD CONSTRAINT` holds that lock** — and the hold duration is the entire Option A versus Option B number.
That remains **`[INFERRED]`**. It is microseconds at `104` rows and honestly waits for a large table.

**3. `downgrade`'s truth, both halves, and one of them reports success while doing nothing.**
`[MEASURED-R]`

- **`downgrade -1` from head is a no-op that succeeds.** `682e01d87be9`'s `downgrade()` is `pass`, and that is
  honest — Postgres has no statement to un-validate a constraint. Result: `alembic_version` moves to
  `15a05eeb0f79`, `convalidated` stays `t`, the definition stays five-valued, and **nothing in the output
  shows the divergence.** Version and schema can now disagree with a clean exit code. Not fixable; the habit
  is the fix — after any `downgrade`, read `alembic_version` **and** `pg_constraint`, never the exit code.
- **The next `downgrade -1` fails, and that is the finding.** With a `dead_letter` row present the four-value
  constraint cannot come back:
  `psycopg.errors.CheckViolation: check constraint "jobs_status_check" of relation "jobs" is violated by some
  row` — **and the error does not name the offending rows** (`104`, `105`; they come from a separate
  `select id from jobs where status = 'dead_letter'`). DDL rolled back fully. Classification: **reversible in
  shape, conditional on data.** Also: head came back via an **`upgrade`**, not a rollback, because the first
  no-op downgrade had already committed.

**4. Cost 1 now has more places to apply — and the count that was going around is wrong, so here it is from
source.** Cost 1 says an illegal transition is stopped only where a guard is written. Read from
`src/worker.py` and `src/reaper.py` on Din 6 `[MEASURED from source]`:

| Writer | Writes | Guard |
|---|---|---|
| claim (`worker.py`) | `status='running'`, `claimed_at`, `attempts+1` | `WHERE id = :id AND status = 'pending'` + the `next_attempt_at` gate, `rowcount` read |
| reaper reclaim (`reaper.py`) | `status='pending'`, `claimed_at=NULL` | `WHERE id = :id AND status = 'running' AND <the full expiry predicate re-asserted>`, `rowcount` read |
| the mark (`worker.py`) | `status` ∈ {`succeeded`, `pending`, `dead_letter`, `failed`}, `next_attempt_at` | `WHERE id = :id AND status = 'running'`, `rowcount` read |
| heartbeat (`worker.py`) | **`claimed_at` only — not `status`** | `WHERE id = :id AND status = 'running'`, `rowcount` read |
| shutdown | **nothing** | — (Option A, and the absence is a decision — see `D-22`) |

So the widely-repeated *"`status` writers went one → five this week"* is imprecise. **Three code sites write
`status`** (claim, reaper, one mark statement), and the mark emits **four different values** from one guarded
statement — which is why it feels like five. The heartbeat is a fourth guarded writer to the same row but its
`SET` list is `claimed_at`; it is guarded **on** `status` without writing it. The audit surface Cost 1
describes is therefore **three statements**, all three currently guarded and all three reading `rowcount`.
Getting this count right matters in both directions: overstating it invents work, understating it misses a
writer.

**5. The transition graph Cost 1 governs is no longer a line, and that is the real change.** `running` is now
reachable from `pending` **after** having been `running` before (reaper reclaim), so a compare-and-set on the
value `'running'` can match a *different generation* of the same row. Measured consequence on Din 3: worker
A's mark returned `rowcount = 1` on work worker **B** was executing `[MEASURED-R]`. The guard did nothing
wrong — it asked *"is the value `running`"*, never *"whose"*. Compare-and-set on a recurring value cannot
distinguish generations; the structural answer is a fencing token, and it is **not built**. This is the
sharpest limit on `D-06`'s chosen mechanism and it did not exist while the graph was acyclic.

---

## D-07: `attempts integer NOT NULL DEFAULT 0` is added now, in Week 1, although retries arrive in Week 2

**Problem:** Retry logic is Week 2's scope. Should the column exist before the logic that reads it?

**Options:**
- (a) Add `attempts` now
- (b) Add it in Week 2 with the retry logic
- (c) Add `attempts` plus the rest of the retry columns (`max_attempts`, `next_run_at`, `last_error`) now

**Chose:** (a).

First, a **rejected justification**: the common argument is that adding a column with a default to a large table causes a rewrite and lock contention. **On PG 11+ this is wrong for a constant default** — `ADD COLUMN ... DEFAULT 0` stores the default in the catalog and does not touch the table, so it is effectively instant regardless of row count. A rewrite *does* occur for a **volatile** default such as `DEFAULT random()` or `DEFAULT clock_timestamp()`, and that distinction is the part worth remembering. **`[MEASURED]`** — see verification at the end of this entry.

What *is* true, and is the more useful operational lesson: `ALTER TABLE` still takes a brief `ACCESS EXCLUSIVE` lock. The real hazard is not the rewrite but the **lock queue** — if a long-running transaction holds the table, the `ALTER` waits behind it, and every subsequent read and write queues behind the `ALTER`. An "instant" migration can therefore freeze the table. Mitigated with `lock_timeout`, so the migration fails instead of blocking everything. Relevant to Week 4 operations, not to today's empty table.

The actual reason to add it now: **the schema is itself a design document**, and deferring the column bundles two decisions together in Week 2. The second one is the awkward one — **backfill semantics**: for rows already sitting in `running` or `failed` when the column appears, is `attempts` 0 or 1? That question would arrive precisely while wrestling with retry logic. Adding the column today, against an empty table, makes the question disappear: every job starts at 0.

Practically, Week 1's worker already marks jobs `failed`. With the column present, Week 2's change is one line (increment) rather than migration plus backfill plus code.

**`NOT NULL` is a correctness requirement, not style.** In SQL, `NULL + 1` evaluates to `NULL`. A nullable `attempts` means the worker's `attempts = attempts + 1` never increments — it stays `NULL` forever. Week 2's `if attempts >= max_attempts` would then never be true, and the job would **retry indefinitely**. That directly breaks contract #3 (*"bounded retry, not an infinite loop"*), and it breaks it **silently**. One missing keyword, one broken contract, no error message — the same class of silent wrongness Week 0 was built around.

General rule extracted: **counters, flags, and states should never be nullable.** NULL should mean "value unknown"; a counter's value is always known, at worst `0`.

`integer` over `smallint`: `smallint` would save 2 bytes, but Postgres row **alignment padding** ahead of the 8-byte `timestamptz` would likely absorb that saving. With no measurable gain, take the boring option — fewer surprises with Python ints and SQLAlchemy defaults.

**Cost:**
1. **An unused column exists for a week.** Nothing reads or writes it in Week 1, so a reader could reasonably ask why it is there. Accepted deliberately.
2. **Its exact semantics are not yet pinned.** Is `attempts` incremented at claim time or at failure time? That is Week 2's decision, and the column being present does not answer it. Only the counter's *shape* is committed, not its update policy.
3. `integer` is 4 bytes where 2 would functionally do.

**Rejected:**
- **(b) defer to Week 2** — forces the column decision and the backfill-semantics decision to be made simultaneously, under pressure, while the retry logic itself is still being worked out.
- **(c) add all retry columns now** — scope creep, and the distinction matters. `attempts` has an **obvious** semantic (a counter, incremented on attempt) with no embedded design decision. `next_run_at` does **not**: its meaning depends on the backoff strategy (exponential? jittered? capped?), on how the reaper reads it, and on timezone handling — none of which are known yet. Adding it today would commit a guess that Week 2 then has to fight, or leave an unused column that misleads future readers. **Rule: add a column whose meaning is known today; do not add one whose meaning depends on a future design decision.**

**`[MEASURED]` — does `ADD COLUMN ... DEFAULT` rewrite the table? (PostgreSQL 16, 50,000 rows)**

A table rewrite changes the relation's on-disk file, so `pg_class.relfilenode` is a direct indicator — same value means no rewrite.

```sql
CREATE TABLE rw_test (id int);
INSERT INTO rw_test SELECT generate_series(1,50000);
SELECT relfilenode FROM pg_class WHERE relname='rw_test';                          -- 24660
ALTER TABLE rw_test ADD COLUMN c1 integer NOT NULL DEFAULT 0;                      -- constant default
SELECT relfilenode FROM pg_class WHERE relname='rw_test';                          -- 24660  ← unchanged
ALTER TABLE rw_test ADD COLUMN c2 timestamptz NOT NULL DEFAULT clock_timestamp();  -- volatile default
SELECT relfilenode FROM pg_class WHERE relname='rw_test';                          -- 24665  ← changed
DROP TABLE rw_test;
```

| Operation | `relfilenode` | Rewrite? |
|---|---|---|
| baseline | 24660 | — |
| `ADD COLUMN ... DEFAULT 0` (constant) | 24660 | **No** |
| `ADD COLUMN ... DEFAULT clock_timestamp()` (volatile) | **24665** | **Yes** |

**Result:** both halves of the claim confirmed on this instance. The commonly-repeated "adding a column with a default rewrites the table" is **false for a constant default on PG 16**, and **true for a volatile one**. So that argument could not have justified adding `attempts` early — the justification is the backfill-semantics one given above, not a performance one.

What this measurement does **not** cover: the `ACCESS EXCLUSIVE` lock-queue hazard described above. `relfilenode` says nothing about lock waits, and no contention was present during this test. **That part remains inference** and would need a separate experiment (hold a long transaction on the table, then time the `ALTER`).

*(Test table dropped.)*

---

## D-08: `created_at timestamptz NOT NULL DEFAULT now()`, generated by the database

**Problem:** Job creation time must be recorded. Three sub-decisions hide here: which type, which default function, and which process supplies the value.

**Options:**
- (a) `timestamp` vs `timestamptz`
- (b) `now()` vs `clock_timestamp()`
- (c) DB-generated vs application-generated

**Chose (a): `timestamptz`.**

`timestamp` stores a wall-clock reading **without recording which zone it belongs to** — `2026-08-13 14:30:00` gives no way to know whose 14:30 that was. `timestamptz` stores an unambiguous absolute instant, internally as UTC. (The name misleads: it does **not** retain the original zone. It converts to UTC on input and renders via the session's `TimeZone` on output. The point is that the stored value is unambiguous, not that the zone is remembered.)

This matters because Relay is three processes — API, worker, reaper — potentially in different containers today and on different machines in Week 4. Week 2's reaper will compute things like `now() - created_at > interval '30 seconds'`. Under `timestamp`, if writer and reader sit in different zones, that arithmetic is **silently wrong**: the reaper declares live jobs dead, or leaves dead jobs alone. A live job declared dead is duplicate execution — contract #2 broken, with no error raised. `timestamptz` eliminates that entire class of bug at zero cost, since both types occupy 8 bytes.

**Chose (b): `now()`.**

`now()` (= `CURRENT_TIMESTAMP` = `transaction_timestamp()`) returns **transaction start time** and stays constant for the whole transaction. `clock_timestamp()` returns the real clock and advances within a transaction.

The apparent objection to `now()` is that inserting ten jobs in one transaction gives all ten an identical `created_at`, producing ties in FIFO ordering. On reflection **the tie is correct, not a defect.** Consider the outbox pattern that motivates D-01's choice of Postgres:

```sql
BEGIN
  INSERT INTO orders ...
  INSERT INTO jobs (type='send_receipt', ...)
COMMIT
```

Those rows were created **atomically**. The job was not created "after" the order — both became real at the same instant. An identical `created_at` states that truthfully. `clock_timestamp()` would assign them timestamps microseconds apart, implying an ordering with no business meaning — fake precision, which is dangerous precisely because it invites trust.

Ties are then handled cheaply with a deterministic tiebreaker: `ORDER BY created_at, id`.

`now()` is also the convention, so any reader understands it immediately; `clock_timestamp()` would make every reader stop and look for a special reason that does not exist.

**Chose (c): DB-generated.**

If the application set the timestamp, Week 4's multiple API instances would inject **multiple clocks** into the ordering. Even under NTP, machines drift by milliseconds, so a job created on instance A could appear older than one created later on instance B. `DEFAULT now()` means **one clock, one source of truth**.

This connects directly to Week 0's central thread — from the Day 3/4 log: *"No system can directly inspect another process's liveness — it can only observe signals... Set a deadline."* A deadline is meaningless if two processes disagree about the time. Week 2's lease expiry rests entirely on this, and the answer to *"whose clock decides the lease expired?"* is the database's, because there is only one of it.

Secondary benefit: the default cannot be forgotten, so manual `psql` inserts during Din 4/5 experiments always get a valid timestamp.

**Cost:**
1. **`created_at` does not give true FIFO either.** Since `now()` is transaction *start* time and commit happens later, a transaction starting at 10:00:00 and running 5 seconds commits after one that started at 10:00:03. The later-stamped row becomes visible first. This is **the same flaw as D-03's id ordering** — two different columns, one shared cause, which is MVCC's nature rather than any column choice. No column can fix it. Relay's ordering is therefore **best-effort FIFO**, and that is acceptable because ordering is not among the five contract promises. Tracked as `P-05`.
2. **Ties are guaranteed** for jobs enqueued in one transaction, so any query needing deterministic order must add a tiebreaker.
3. **Enqueue time cannot be attributed to a specific application instance**, since the DB stamps it. Fine today; would matter if per-instance latency attribution were ever needed.

**Rejected:**
- **(a) `timestamp`** — correct only for genuinely "floating" local times, where the wall-clock reading is the meaning regardless of zone (a shop opening at 9 AM, a birthday). Server events are absolute instants, never floating.
- **(b) `clock_timestamp()`** — appropriate when measuring real elapsed time *inside* a long transaction, e.g. a batch processing 1000 rows where each row's true processing time matters. Relay's enqueue transactions are deliberately short (Din 2: commit, then respond), so the difference here is microseconds and unmeasurable.
- **(c) application-generated** — introduces clock skew across instances into the one column the claim query orders by, and can be forgotten on manual inserts.

---

## D-21: `job_executions` is an append-only instrument table, written *before* the handler runs, in its own transaction, with no foreign key and no index

*(Week 1, Din 4. Numbered `D-21` because `D-09`..`D-20` belong to the Month 2–4 roadmap — see the numbering note at the top of this file.)*

**Problem:** Relay's contract says a job's side effects must not be duplicated. Din 4 had to test that, and `jobs` alone **cannot** answer the question: `status` is a single column that gets overwritten, so `succeeded` looks identical whether one worker ran the job or five did. An `UPDATE` destroys the evidence of the previous writer by design. So the day needed a place where a second execution cannot erase the first one's record.

**Options:**
- (a) Append-only table, one row per execution, `(job_id, worker_id, executed_at)`
- (b) An `executions integer` counter column on `jobs`, incremented per run
- (c) The execution row written in the **same** transaction as the terminal `succeeded`/`failed` mark
- (d) (a) plus `FOREIGN KEY (job_id) REFERENCES jobs(id)` and an index on `job_id`

**Chose:** (a), with three specific placement decisions that matter more than the schema:

1. **Written after the claim commits, before `await handler(payload)`.** So the row means *"a handler was entered for this job"*.
2. **Written in its own session and its own transaction** (`record_execution()`), not inside the claim transaction and not inside the mark transaction.
3. **No foreign key, no index on `job_id`.**

**Why (1) — the ordering is the whole design.** A row written at *mark* time is evidence of completion, and a worker killed mid-handler leaves no trace at all — exactly the case Din 5 exists to observe. A row written at *claim* time would be evidence of intent, and would count jobs that never reached a handler. Writing it immediately before dispatch is the only position where the row means "work started", which is what a duplicate-execution test needs: two rows mean the handler ran twice, whatever `jobs` says.

**Why (2) — evidence must not share a fate with the thing it is evidence about.** If the execution row is written in the same transaction as the terminal mark, then a failed mark rolls back the proof that the job ran (`P-11`'s starting point, and Din 4's own Step 1 prediction question). Committing separately means the two records can disagree — and that disagreement is the diagnostic. `job_executions` says the handler ran; `jobs` says `running`; the truthful reading is *"it ran and nobody recorded how it ended"*, which is precisely Week 2's problem.

**Why (3) — measured to cost nothing yet, and both parts are reversible.** At 58 jobs and 30 execution rows the duplicate query (`GROUP BY job_id HAVING count(*) > 1`) is a sequential scan over a table of tens of rows. Adding an index today would be `P-03`'s mistake in miniature: freezing a guess before the data shape exists. The FK is a real decision rather than an omission, argued below.

**Cost — all four of these are measured, not theoretical:**

1. **It records handler dispatch, not claims.** `[MEASURED]` A job with an unregistered `type` is claimed, marked `failed`, and leaves **no** row (job `58`); a job whose handler raises leaves one (job `57`, `type = boom`). So "claimed" and "executed" are different populations, and only the second is instrumented. Consequence: the table cannot detect a job that was claimed and lost before dispatch.
2. **`count(*) > 1` is a duplicate test only while retries do not exist.** Week 2's retry legitimately produces several rows for one job. The test expires the moment retries land, and the fix is another column (attempt number, or a claim id), not another query. Tracked as `P-11`.
3. **No FK means orphan rows are accepted.** `[MEASURED]` `INSERT INTO job_executions (job_id, worker_id) VALUES (999999, 'probe-orphan')` succeeded. The instrument can therefore assert an execution of a job that never existed, and nothing catches a typo'd `job_id` in a manual probe. *(Probe row deleted; it consumed `id = 31`.)*
4. **A crash between the claim commit and the execution row's commit under-counts.** `[INFERRED from code]` The gap is milliseconds wide and has not been reproduced deliberately, but in it a job is `running` with no execution row — the mirror image of Cost 1.

**Rejected:**
- **(b) counter column on `jobs`** — an `UPDATE` again, so it inherits the exact problem it was meant to solve: it cannot say *which* worker ran the job, or *when*, and a lost update loses the count silently. It also cannot support Din 4's actual use: `executed_at` is what made it possible to reconstruct a finished experiment's timeline and discover that the two workers barely overlapped (`P-12`). A counter would have hidden that permanently.
- **(c) same transaction as the terminal mark** — kills the evidence exactly when it is most needed (mark fails, DB restarts, worker dies after the handler). Also makes the killed-mid-handler case indistinguishable from the never-started case, which is Din 5's entire subject.
- **(d) FK + index — deferred, not dismissed.** The FK would buy referential honesty (Cost 3), and its price is a specific Week 4 conflict: deleting `jobs` rows older than 30 days then either fails on the FK, or needs `ON DELETE CASCADE`, which **deletes the execution history** — i.e. the audit trail disappears with the audited row, and an audit trail that vanishes with its subject is not much of an audit trail. The third option, `ON DELETE SET NULL`, needs a nullable `job_id` and turns the row into an orphan by design. That is a real decision with three unattractive branches, and it needs Week 4's retention policy to exist first. Recorded as deferred below.

**Revisit when:** Week 2 adds retries (Cost 2 forces an attempt/claim identifier), or Week 4 defines job retention (forces the FK/cascade question), or the duplicate query gets slow enough to measure (then index `job_id`, with `EXPLAIN ANALYZE`, alongside `P-03`).

**Amendment — Week 2 Din 6: Cost 2 has expired, it expired earlier than this entry predicted, and the part
that grew is not the part that was predicted.** Nothing above is edited.

**Cost 2 said** `count(*) > 1` stops being a duplicate test *"the moment Week 2's retry legitimately produces
several rows for one job"*, and named the fix as another column. **What actually happened:** it expired on
**Din 2/Din 3** — the reaper's `running → pending`, i.e. the *second `status` writer* — **two days before
retry landed on Din 4.** So the prediction was right about the mechanism (an `UPDATE`-driven re-dispatch makes
a second row legitimate) and wrong about the schedule, and the schedule is what mattered: the identifier was
scheduled *with* the retry logic and was already needed *before* the reaper.

**What the query means now: it is a question, not an answer.** `count(*) > 1` says only *"this job was
dispatched to a handler more than once"*. Turning that into a verdict needs three more values read
alongside — the rows' `worker_id`, their `executed_at`, and the job's `attempts` — and even then the word
**duplicate** only applies where **overlap was proved**. That is **one** job id in the entire table.

**Five distinct causes, by id `[MEASURED-R unless noted]`:**

| # | Cause | Job ids | What separates it from the others |
|---|---|---|---|
| 1 | same-worker re-dispatch | `44` | one `worker_id` (`worker-12940`), `6m54s` apart, `2026-08-17` — Week 1, and never noticed at the time |
| 2 | reclaim re-execution after a crash | `63`, `65` | two different `worker_id`, **a week** apart, Din 2's reclaim finally executing. Sequential, so not a duplicate |
| 3 | **overlapping execution — the only true duplicate** | `95` | two `worker_id`, **`14.783 s` of proved overlap** in one clock, Din 3. Worker A's mark returned `rowcount = 1` on B's work |
| 4 | bounded retry after a handler exception | `98`–`103`, and `104` | one `worker_id`, sequential dispatches, terminal at `attempts = 3`. Legitimate by design (`D-23`) |
| 5 | bound-crossed re-dispatch | `108` | reclaim of a bound-crossed row → one **extra** dispatch, `attempts = 4`, `P-27`. The handler ran before the bound was evaluated |

**The database distinguishes none of these five.** `attempts` was `0` on `44`, `63`, `65` and `95` at the time
`[MEASURED-R]`, and it is still `0` on all four — nothing was written retroactively. Causes 1–3 are therefore
invisible in `jobs` entirely, and causes 4–5 are only visible because `attempts` happens to be non-zero for an
unrelated reason.

**Cost 1 got a second confirmation and a third shape.** The entry already recorded that the instrument counts
**dispatch**, not claims and not completions. Din 3 made the missing end expensive rather than theoretical:
`executed_at` is the dispatch instant committed *before* the handler body, so proving job 95's overlap needed a
**second** endpoint that only stdout had — and those captures were deleted at day close. **The week's headline
number cannot be recomputed from the database.** `[MEASURED-R]` Priced in `D-22` Cost 10, with the verdict
there: a nullable `completion` column is deferred to **Week 3**, because it adds another writer to the row the
reaper is already racing.

**The identifier question, and it gets the same answer in both places it is asked.** `LEARNING_LOG.md` carries
it as a `D-22`-shaped question (*does the identifier need to exist before the reaper rather than with the retry
logic?*). **Answer: yes, and it is already late** — see `D-22` Cost 11 for the same deferral, so the two
entries do not drift. **Not added on Din 6**, deliberately: Din 6 has no `src/` or schema change, and the
identifier's shape (attempt number vs claim id vs the dedup key itself) should be decided **with** Week 3's
idempotency key rather than invented a week earlier and then reconciled. **Owner: Week 3.** What it must be
able to answer, written down now so the decision is not re-derived: *given two rows for one `job_id`, were they
the same claim or different ones, and did their intervals overlap?*

**One layer up, and it is `failed = 15`'s problem too.** A summary count stops meaning one thing the moment a
status value's contract changes mid-week — `dead_letter` arrived on Din 5 and **did not rename history**. Read
independently on Din 6 `[MEASURED]`, the fifteen `failed` rows are **three** shapes, not the two the plan
expected:

| Shape | ids | Meaning |
|---|---|---|
| unknown `type`, `attempts = 0` | `8`, `23`, `58` (`does_not_exist`), `75` (`send_receipt`) | no handler was registered. **Today's code still produces this**, and that branch never consults `attempts` |
| Week 1 handler failure, `attempts = 0` | `5`, `20` (`sleep`), `6`, `21`, `57` (`boom`) | the handler raised, before retry logic existed. No counter had been incremented yet |
| bounded out before `dead_letter` existed, `attempts = 3` | `98`–`103` (all `boom`) | **today's code would call these `dead_letter`** |

Renaming them would falsify the log, so they stay. The point of writing it here is that `failed` is a count
over three contracts, and the next reader of *"failed 15"* would otherwise take it for *"jobs that failed
once."*

---

## What was deliberately NOT decided today

Recording these so that "not yet decided" is never mistaken for "overlooked":

| Deferred | Scheduled | Why not today |
|---|---|---|
| Index for the claim query | Week 4 | To be **measured** with `EXPLAIN ANALYZE`. Guessing today would freeze an assumption into the schema. Tracked as `P-03` |
| `idempotency_key` + unique constraint | Week 3 | Its scope (what forms the key, what TTL applies) becomes clear only after Din 4's duplicate-POST experiment |
| ~~`lease_expires_at`, heartbeat columns~~ | ~~Week 2~~ | ✅ **Resolved Week 2 Din 1/Din 3, and the answer was *neither column*.** The lease is an **event** (`claimed_at`), so the duration lives in the reaper's predicate instead of on the row; the heartbeat re-writes `claimed_at` rather than adding a column. `D-22` prices both, including the cost this shape imposed: the duration had to be chosen on Din 2, ahead of evidence |
| ~~`max_attempts`, `next_run_at`, `last_error`~~ | ~~Week 2~~ | 🟡 **Partly resolved Week 2 Din 4.** `next_run_at` landed as **`next_attempt_at timestamptz NULL`** (migration `9e4822cbf157`) — `D-23`. `max_attempts` was **not** added as a column; it is `MAX_ATTEMPTS = 3` in Python, which is why `dead_letter` had to become self-describing (`D-23` Cost 8). **`last_error` is still unadded** — `dead_letter` is a verdict with no diagnosis. Owner: Week 4 |
| `updated_at` | Week 2 → **Week 4** | *Original: "No consumer exists yet; the reaper will justify it."* **Still not added, and the reaper did not justify it after all** — it keys on `claimed_at`, not on a generic mtime. Reconsider when an operator-facing view needs *"when did this row last move?"* across all five status values |
| ~~`dead_letter` status value~~ | ~~Week 2~~ | ✅ **Resolved Week 2 Din 5**, via exactly the two-step pattern in `D-06` Cost 4 — `15a05eeb0f79` (`NOT VALID`, `convalidated = false`) then `682e01d87be9` (`VALIDATE`, `convalidated = true`). See `D-06`'s amendment for the condition Cost 4 was missing, the first measurement of the lock queue, and `downgrade`'s two different outcomes |
| ~~Payload size limit and where to enforce it~~ | ~~Din 2~~ | ✅ **Resolved Din 2** — 266,240-byte body bound in HTTP middleware, `413`. See `D-05` Cost #4 amendment. Residual gap: `P-08` |
| ~~`type` validation placement (API vs worker)~~ | ~~Din 2–3~~ | ✅ **Resolved Din 3** — API bounds shape; the real invariant (*a handler is registered*) is now checked by the worker's registry at claim time. Measured: unregistered type → claimed once, `failed` once, no hot loop. `D-04`'s position unchanged; its priced cost is the deploy-ordering hazard in the Din 3 amendment |
| Shutdown observation latency vs poll interval | Week 2 | `P-10`. The loop sleeps the interval in one `await`, so the shutdown flag is seen up to a full interval late. Fix is slicing the sleep or waiting on an `asyncio.Event`; safe at 2 s inside Docker's 10 s grace, so deferred with the rest of shutdown hardening |
| ~~`ORDER BY (created_at, id)` tiebreak on the claim query~~ | ~~Din 4, before seeding~~ | ✅ **Resolved Din 4, Step 0** — claim query now orders by `(created_at, id)`. It was load-bearing: the ten seeded jobs did share one `created_at`, and the reconstruction in the Din 4 log (`M4`) is only possible because job order was deterministic |
| FK `job_executions.job_id → jobs(id)`, and an index on `job_id` | Week 4 (retention), or when the duplicate query gets slow | `D-21`. FK's three branches are all unattractive until a retention policy exists: plain FK blocks the delete, `CASCADE` deletes the audit trail with its subject, `SET NULL` orphans by design. Index deferred for `P-03`'s reason — measure, do not guess |
| An attempt number / claim id on `job_executions` | ~~Week 2, with retries~~ → **Week 3, with the dedup key** | *Original: "`P-11`. `count(*) > 1` stops meaning \"duplicate\" the moment a retry legitimately writes a second row."* 🔴 **Still not added, and it is now overdue rather than deferred.** `P-11` expired on Week 2 **Din 3** — the reaper, not retry — so this slipped past the week it was scheduled in. Five causes of `count(*) > 1` now exist and the database separates none of them. Full verdict and reasoning in `D-21`'s amendment; the same deferral with the same owner is in `D-22` Cost 11 |
| ~~A claim timestamp on `jobs` (`claimed_at` / `lease_expires_at`)~~ | ~~Week 2~~ | ✅ **Resolved Week 2 Din 1** — `claimed_at timestamptz NULL`, migration `75a845575d2e`, written in the claim `UPDATE`. `NULL` was left un-backfilled deliberately (a backfilled value would be fiction for jobs 41/63/65 and `downgrade` cannot un-invent it), which is why the reaper's predicate carries a permanent `IS NULL` branch. `D-22`, `P-19` |
| ~~`signal.SIGBREAK` registration in the worker~~ | ~~Week 2~~ | ✅ **Resolved Week 1 Din 5 / confirmed Week 2** — `SIGBREAK` is registered where the platform has it (`hasattr(signal, "SIGBREAK")`) in both `worker.py` and `reaper.py`; delivered, handler ran, exit `0`, no stuck job `[R]`. A real `Ctrl+C` keypress is still untimed, but every line after the flag is set is identical |
| DB-level bound on `type` length | Week 4 | `D-04` Cost #3's `CHECK (length(type) <= 100)` is still unapplied. Din 2 bounded it at the API layer only, so `psql` inserts bypass it |
| Stream-level body limit (`Content-Length`-independent) | Week 4 | `P-08`. Record the fix's own overshoot bound (limit + one chunk) when it lands |
| Response fields `type` / `created_at` on `GET /jobs/{id}` | When a consumer needs them | Measured to be near-free (row-store; same heap page). Excluded only for response-surface reversibility, not cost |


---

# The two Week 2 architecture decisions (Din 6)

*(Written on Week 2 Din 6, `2026-08-29`. Numbered `D-22`/`D-23` because `D-09`..`D-20` belong to
`roadmap/BACKEND_ROADMAP_PART2.md` and `D-01`..`D-08` plus `D-21` are taken. Grepped on the day of
assignment, not on the day the plan was written — output in `logs/WEEK_02.md`, Din 6.)*

> **Provenance convention, same as `D-01`/`D-02`.** Every `Cost` and `Rejected` line ends in exactly one
> tag: `[MEASURED]` (measured by the user on this machine, number in `logs/WEEK_02.md`), `[MEASURED-R]`
> (measured by the reviewer — usable as evidence about the system, **not** as a number the user can defend
> without re-running it), `[INFERRED]` (reasoned from mechanism or source, not observed), `[NO EVIDENCE]`
> (judgement, and labelled as such). **An untagged line reads as `[MEASURED]`, which is this file's most
> expensive default.**
>
> **No new decision is taken here.** Every choice below was made on Din 1–5 and is copied with its date.
> What Din 6 adds is the `Cost` field, which could not be written before the measurements existed.
>
> **Nothing in these two entries is written as an elimination.** The lease and the reaper **narrow** the
> stranded-work window. Contract #2 (*side effects are not duplicated*) is **unprotected** until Week 3.

---

## D-22: lease duration `30 s`, heartbeat interval `10 s`, and no handler timeout — one decision with three numbers, and only one of them is measured

**Problem:** Din 2 shipped the reaper, so Relay now has to answer *"is this worker dead, or slow?"* — and it
cannot. `P-16` is the row-level form of that: `status = 'running'` is one value covering a worker that is
executing and a worker that died mid-handler. The only available substitute for observing liveness is a
**deadline**, and a deadline is a guess with a two-sided cost:

- **Lease shorter than the handler** → the reaper reclaims live work and Relay *manufactures* duplicate
  execution.
- **Lease longer than the handler** → stranded work sits in `running` for that much longer before anything
  looks at it.

This is **one** decision and not two, because of `P-15`: Relay does not bound its handlers. The lease
therefore has no upper bound to be safely shorter than, and the shutdown path has no budget it can promise
to fit inside. Any lease number is implicitly also a statement about handler duration.

**Options — where the lease lives:**
- (a) event column `claimed_at`, with the duration in the reaper's predicate
- (b) deadline column `lease_expires_at`, written at claim time

**Options — the duration:**
- (a) pick a number now with headroom over the known handlers
- (b) derive it from a measured maximum handler duration
- (c) per-`type` lease, read from a config or lookup table

**Options — keeping a legitimately long handler alive:**
- (a) no heartbeat; require `lease > slowest handler`
- (b) heartbeat pushes `claimed_at` forward while the handler runs
- (c) bound the handler with a timeout, making the lease derivable

**Options — the lease on graceful shutdown:**
- (A) do nothing; let the in-flight handler finish
- (B) release the lease (`running → pending`) so the work is re-dispatched immediately
- (C) extend the lease before exiting

**Chose:** (a) `claimed_at` (Din 1) · duration **`30 s`** (a), chosen Din 2 · heartbeat **`10.0 s`** (b),
chosen Din 3 · **no handler timeout** — (c) deliberately not taken, `P-15` stays open · shutdown **Option A**
(Din 5).

**Why the event column.** `claimed_at` records a fact (*this row was claimed at this instant*);
`lease_expires_at` records a policy (*this row is mine until then*). A fact does not go stale when the policy
changes, so changing the lease is a change to queries and not to data. The price is structural and it landed
immediately: the duration is now a term in **every** reader's predicate, which is how a number the plan
deferred to Din 6 ended up being chosen on Din 2, before any evidence existed.

```sql
-- deadline column: duration is not in the query
WHERE lease_expires_at < now()
-- event column (chosen): duration is in every query that asks the question
WHERE claimed_at IS NULL OR claimed_at < now() - interval '30 seconds'
```

**Why the `IS NULL` branch is not optional.** `NULL < now() - interval '30 seconds'` evaluates to `UNKNOWN`,
which is falsy in a `WHERE` clause, so the expiry term alone silently skips every row whose lease was never
written. Measured as a differential on Din 1: `claimed_at < now()` returned `0`, and
`(claimed_at IS NULL OR claimed_at < now())` returned `3` `[MEASURED]`. That branch is also what makes a
future writer who forgets to set `claimed_at` recoverable rather than permanently stuck — and it is the
branch that did **all** of Din 2's reclaiming.

**Cost:**

1. **The `30 s` was chosen on Din 2, ahead of measurement, and Din 2's own run did not test it.** All three
   reclaims (jobs 41, 63, 65) matched the `IS NULL` branch; not one `running` row in the database had a
   non-null `claimed_at`, so the expiry branch matched **zero** rows and the number was exercised by nothing.
   `[MEASURED-R]` for the reclaim outcomes, `[INFERRED from the Step 2 pre-reclaim dump]` for which branch
   fired. The honest provenance sentence is *"chosen on Din 2 ahead of measurement, first measured on Din 3."*
2. **The lease is shorter than a handler Relay permitted to exist, and that produced the week's duplicate.**
   Job 95: handler `45.026 s` against a `30 s` lease, two distinct workers, **overlap `14.783 s`** derived
   with zero clock conversions, and worker A's mark returned `rowcount = 1` on work worker B was still
   executing. `[MEASURED-R]` This is the entry's central cost and it is not a bug in any guard — all three
   compare-and-sets were correct at the instant they ran.
3. **Reclaim latency is bounded by `lease + one reaper period`, not by `lease`.** `1.798192 s` on a seeded
   row, with the pass `226 ms` before expiry correctly matching nothing and the next pass catching it;
   independently corroborated at `≤ 207.098 ms` from job 95's expiry-to-re-claim gap. `[MEASURED-R]` Both
   readings are single-candidate: the reaper's period is `poll + pass duration` and pass duration grows with
   candidate count, so this number is not a load figure. `[INFERRED]`
4. **The reaper's whole pass shares one `now()`.** `reap_stuck_jobs()` runs its `SELECT` and every per-row
   `UPDATE` inside one `session.begin()`, and `now()` is transaction-start time — measured identical across a
   `1.509786 s` gap while `clock_timestamp()` advanced. `[MEASURED-R]` So rows that expire *during* a pass
   are not picked up until the next one. The bias is towards **under**-reclaim, which is today's safe
   direction — by luck, not by design.
5. **The heartbeat narrows the expiry window and does not close it.** Run 2 (job 96, same shape as job 95)
   pushed `claimed_at` to `40.295 s` past dispatch across four heartbeats, the lease never expired, and one
   execution row was written. `[MEASURED-R]` But the mechanism rests entirely on the handler yielding to the
   event loop: `handle_slow` is `asyncio.sleep`, so it yields; a CPU-bound or synchronously blocking handler
   sends **no** heartbeat, and Relay does not bound handlers. `P-21`'s statement of this is the one worth
   keeping: **the heartbeat's coverage is inverse to the severity of the failure a lease exists to catch.**
6. **The effective margin is `lease − interval − scheduling delay`, not `lease − interval`.** `10.0 s` was
   chosen as `lease / 3` on Din 3 and nothing about the value was measured; what was measured is what it
   *achieved* on one job. `[NO EVIDENCE]` for `10 s` being right. Write cost: one extra `UPDATE` per running
   job per interval, on top of the reaper's own poll. `[INFERRED]`
7. **The heartbeat's guard rejects a *released* lease and is untested against a *re-claimed* one.** Reviewer
   probe on job 97: reaper reclaimed the row, the heartbeat `UPDATE` then returned `rowcount = 0` and
   `claimed_at` stayed `NULL` — a released lease cannot be resurrected. `[MEASURED-R]` The dangerous ordering
   is the other one: reaper reclaims → worker B claims → **worker A's** heartbeat fires against a row that is
   `running` again, expected `rowcount = 1`, after which the reaper can never rescue B's work.
   `[NO EVIDENCE]` — never produced. Same generation blindness as Cost 2's mark: a compare-and-set on a
   **recurring** value cannot ask *whose* `running` this is. The structural answer is a fencing token and it
   is not built.
8. **Shutdown Option A's cost was never paid, so this line is `[INFERRED]` and must stay that way.** Din 5
   ran the shutdown experiment with `handle_slow`'s default `8.0 s` against the `30 s` lease (jobs 106/107,
   `payload = {}`), so the lease could not expire: no reclaim, no second claim, no contested mark, and the
   `10.0 s` heartbeat never fired either — `claimed_at` sits `24.6 ms` / `24.7 ms` after dispatch, against
   `40.295 s` on Din 3's job 96. `[MEASURED-R]` The claim *"graceful shutdown narrows the stranded-work
   window and does not close the duplicate one"* is therefore **`[INFERRED]`**: the run happened, its subject
   did not. What was actually re-confirmed is Week 1 Din 5's result — handler completes, no new claim after
   the signal, exit clean. `[MEASURED-R]`
9. **Option A means the shutdown path writes no `status` at all, and that absence is a decision.** A worker
   exiting mid-handler under a supervisor with a grace period shorter than the handler degrades into the
   crash path, which is `P-15`, and the row's recovery then depends on Cost 2's window rather than on
   anything shutdown did. `[INFERRED]`
10. **Completion evidence is a `print`, not a row, and that turned from a judgement into a blocker.**
    `job_executions.executed_at` is the **dispatch** instant, committed before the handler body runs, so
    proving job 95's overlap needed a second endpoint that only stdout had — and those captures were deleted
    at day close. `[MEASURED-R]` Measured consequence: **the week's headline number cannot be recomputed from
    the database.** Verdict, taken here rather than carried a fourth time: **deferred to Week 3, with the
    dedup work**, because the cheap fix (one nullable `completed_at`) adds another writer to the row the
    reaper is already racing, and Week 3 is where that race gets a fencing/idempotency answer. Owner: Week 3.
11. **`P-11`'s `D-22`-shaped question — *does an attempt/claim identifier on `job_executions` need to exist
    before the reaper rather than with the retry logic?* — is answered `yes`, and it is already late.** The
    instrument became ambiguous on **Din 3**, one week ahead of the retry logic it was scheduled against:
    `count(*) > 1` was true for four job ids via three structurally different mechanisms while `attempts` was
    `0` on all four. `[MEASURED-R]` The identifier is still **not** added. Same deferral, same owner, in
    `D-21`'s amendment: **Week 3**, decided with the idempotency key so the two do not invent competing
    identities.
12. **The handler that produced Cost 2 exists in no commit.** `git log --all -S"super_slow"` returns nothing;
    jobs `93`–`96` carry `type = 'super_slow'` with no handler behind them, and `HEAD`'s registry is
    `sleep`/`boom`/`slow`. `[MEASURED-R]` `P-23` closed the *mechanism* half on Din 5 — handlers now read
    `payload.get("seconds", default)`, committed in `399febb` — but **no row in `jobs` carries a `seconds`
    key**, so only the default branch has ever run. `[MEASURED-R]` Recorded here rather than papered over:
    **the centrepiece ran on an uncommitted working-tree state and does not re-run as it was.** The
    replacement is a payload-driven `slow`, which is the `Revisit when` run below.

**Rejected:**

- **(b) `lease_expires_at` deadline column** — keeps the duration out of every predicate, which is genuinely
  cleaner, and would have prevented the duration from being chosen a week early. Rejected because it stores a
  policy in a column: changing the lease then leaves in-flight rows carrying the old deadline, so the change
  needs a data migration or a mixed-policy period. `[INFERRED]` Becomes the right shape the moment the lease
  is per-`type`, because then the duration genuinely belongs to the row.
- **(b) derive the duration from a measured maximum handler duration** — there is no such maximum. Relay does
  not bound handlers, and Din 3 demonstrated a `45 s` handler existing purely because someone wrote one.
  `[MEASURED-R]` A derived lease requires (c) below to exist first, which is exactly the dependency this
  entry is recording.
- **(c) per-`type` lease** — the right answer once `type` has configuration behind it, which `D-04` schedules
  for Week 4 with the lookup table. Rejected today as scope: it needs a place to put per-type config and a
  decision about the default for an unknown `type`. `[NO EVIDENCE]`
- **(c) handler timeout (`asyncio.wait_for`)** — this is the structurally correct fix and it is deliberately
  not Week 2's. It would bound shutdown, make the lease derivable rather than chosen, and turn `P-15` from an
  open hazard into a parameter. Its price is a new question with no obvious answer: **what is the status of a
  timed-out handler?** Retryable (so a slow-but-healthy job burns its budget, `D-23` Cost 4) or terminal (so a
  legitimately long job is dead-lettered for being slow). That question needs `D-23`'s bound and Week 3's
  dedup to exist first. `[INFERRED]` `P-15` stays open with an owner.
- **Shutdown Option B (release the lease on shutdown)** — returns the work immediately instead of waiting for
  the lease to expire, and it is tempting for exactly that reason. Rejected because it writes `pending` while
  the handler is **still running**, which converts a *possible* duplicate into a *scheduled* one, and it adds
  another `status` writer racing the reaper on the same row. `[INFERRED]`
- **Shutdown Option C (extend the lease before exiting)** — extends a deadline the process is about to stop
  being able to defend, so it moves stranded work further out with no upper bound and no one renewing it.
  `[INFERRED]`
- **A `5 s` lease** — would have made duplicate execution trivially easy to produce, and Din 3 explicitly
  kept `30 s` untouched so that the day's duplicate count would be evidence **about `30 s`** rather than
  about a lease chosen to fail. `[MEASURED-R]` — the `45 s` handler was the moved variable instead.

**Revisit when:**

- **The one run that closes Cost 8, and it is cheap:** one `slow` job with `payload {"seconds": 45}`,
  `SIGBREAK` at `T = 3 s`, worker and reaper both live, worker stdout captured and **copied into the log
  before deletion**. That single run closes Cost 8, `P-21`'s untested half (Cost 7's dangerous ordering), and
  `P-25`'s rejection on the terminal write. **Owner: Week 3 Din 1, or a named catch-up slot.** It was
  deliberately not run on Din 6 — adding execution rows to a chain being closed mixes a measurement day into
  a writing day.
- A handler timeout lands → the lease becomes derivable and Cost 1's provenance sentence can be replaced.
- The reaper ever has more than one candidate per pass under load → Cost 3's latency figure needs re-measuring
  with `pass duration` as a variable, Week 4 with metrics.
- A fencing token or generation counter is designed (Week 3) → Cost 7 and Cost 2's `rowcount = 1` both change
  shape, and `D-06`'s compare-and-set stops being the only transition guard.

---

## D-23: bounded retry — increment on claim, `next_attempt_at` column, `base = 5.0 s` exponential with equal jitter, and the bound is on retry *scheduling*, not on dispatches

**Problem:** Contract #3 says retries are **bounded**, not an infinite loop. Three sub-decisions hide in that
and separating them into three entries would orphan each one's reason: **where `attempts` is incremented**,
**where "not before" is stored**, and **what the delay is**. They interact — the increment point decides what
the bound counts, and the not-before column decides who can bypass the delay.

**Options — increment point:**
- (a) on **claim**, inside the claim statement's row lock
- (b) on **failure**, in the mark statement

**Options — storing "not before":**
- (a) a new column `next_attempt_at timestamptz NULL`
- (b) derive it from `claimed_at + f(attempts)` — no new column
- (c) a separate `retry_schedule` table

**Options — the delay:**
- (a) fixed
- (b) exponential
- (c) exponential + jitter (full / equal / decorrelated)

**Chose:** (a) increment on claim · (a) new column `next_attempt_at`, migration `9e4822cbf157` · (c)
exponential with **equal** jitter. All three on Din 4; `BASE` revised on Din 5.

**The formulas, verbatim, because a paraphrase of a backoff formula is worthless:**

```python
# src/worker.py
MAX_ATTEMPTS = 3
BASE_BACKOFF_SECONDS = 5.0      # was 3.0 on Din 4; changed on Din 5, reason below
BACKOFF_MULTIPLIER   = 2.0
BACKOFF_CAP_SECONDS  = 15.0

delay(n)  = min(BASE * MULT ** (n - 1), CAP)          # exponential, capped
actual(n) = delay(n) / 2 + random.uniform(0, delay(n) / 2)   # equal jitter
```

The claim gate and the retry mark, as rendered by SQLAlchemy `[MEASURED-R]`:

```sql
-- claim gate: the IS NULL branch is mandatory, for D-22's three-valued-logic reason
SELECT jobs.id FROM jobs
 WHERE jobs.status = 'pending'
   AND (jobs.next_attempt_at IS NULL OR jobs.next_attempt_at <= now())
 ORDER BY jobs.created_at, jobs.id LIMIT 1 FOR UPDATE SKIP LOCKED

-- retry mark: one statement, transition and policy together
UPDATE jobs SET status='pending', next_attempt_at=(now() + interval '4.5 seconds')
 WHERE jobs.id = %(id_1)s AND jobs.status = %(status_1)s
```

**Why increment on claim.** `values(attempts=Job.attempts + 1)` is a column expression inside the claim's own
transaction and row lock, so it is a single atomic statement and no Python read-modify-write can lose an
update. Its consequence is the point: **an attempt can never be lost to a crash.** A worker `kill -9`'d
mid-handler has already spent its attempt, so the reaper's reclaim cannot produce an unbounded retry loop —
which is `P-01`'s hazard expressed at row level.

**Why `BASE` moved from `3.0` to `5.0` on Din 5, and why that is *derived* and not measured.** The worker's
observation quantum is its poll period, measured at `2.013–2.020 s` `[MEASURED-R]`. Equal jitter **halves the
floor**, so the quantum check has to run against `delay/2`, not against `base`:

```
base = 3.0 -> attempt-1 range [1.50, 3.00], floor 1.50 < 2.0 quantum -> (2.00 - 1.50)/1.50 = 33 % of draws masked
base = 5.0 -> attempt-1 range [2.50, 5.00], floor 2.50 > 2.0 quantum -> 0 % masked
```

`0 %` masked at `base = 5.0` is **arithmetic**, derivable at a desk, and it is correct. It is **not** a
re-measurement: Din 5 produced exactly **one** inter-attempt gap (job 104, `6.130075 s`, which solves back
against the poll grid to a configured delay in `(4.10, 6.13]`), and no multi-job distribution was re-run.
`[MEASURED-R]` So `P-24`'s arithmetic half is closed by construction and its **convoy** half still rests on
Din 4's rows.

**`BACKOFF_CAP_SECONDS = 15.0` is inert, and it is written as inert.** At `MAX_ATTEMPTS = 3` only `n = 1` and
`n = 2` ever compute a delay (`5.0`, `10.0`); `n = 3` takes the terminal branch. The cap first binds at
`n = 4` (`raw = 24.0`), and attempt 4 does not exist as a *scheduled* retry. So `15.0` could be `3.0` or
`300.0` with identical behaviour. `[MEASURED-R]` `P-26`. Verdict: **reserved for a future `MAX_ATTEMPTS`,
crossing point `n = 4`** — not tuned, and not evidence of anything.

**Why jitter, in two lines with two different tags.** Relay's own argument is `[MEASURED]`: equal handler
durations synchronise workers into a convoy, measured at 4 µs separation across three consecutive rounds
(`P-14`). The general thundering-herd argument — synchronised retries from many clients re-colliding — is
read, not derived here, and is `[INFERRED]`. Equal jitter over full jitter because it keeps a **floor**: full
jitter can schedule a retry almost immediately, which throws away the backoff's purpose on the attempt where
it matters most.

**The sentence this entry is not allowed to contain.** *"`MAX_ATTEMPTS = 3` bounds `attempts`"* is **false**,
and the counterexample is a row in the table this document's own week-close chain counts. Job `108` sits at
`attempts = 4` — `[MEASURED-R]` on Din 5 and re-read independently on Din 6, where the `attempts`
distribution is `0|95 · 1|3 · 3|8 · 4|1` `[MEASURED]`. It got
there through committed code: the reaper reclaimed a bound-crossed `running` row, **the claim gate consults
`status` and `next_attempt_at` and never `attempts`**, the worker printed `attempt=4/3`,
`record_execution()` committed, `handle_boom` ran, and **then** `dead_letter` was written. The bound is
evaluated in the failure branch — *after* the handler.

**Decision taken here, and it is a decision rather than phrasing: accept the overdraft.** The honest form is
**"`MAX_ATTEMPTS` bounds retry *scheduling*; a row that re-enters the queue at the bound costs one more full
dispatch, handler body included."** The alternative — moving `AND attempts < :max` into the claim gate — makes
the bound-crossed row **unclaimable** and immediately raises *then who terminalises it?* That is a sweep, a
new `status` writer with its own guard and `rowcount` check, and it is **not a Week 2 change**. Owner if ever
taken: Week 3, alongside dedup.

**Cost:**

1. **The bound is not a row-level invariant.** *"`attempts` never exceeds `MAX_ATTEMPTS`"* is false; the true
   statement is *"the worker stops **scheduling** retries once `attempts >= MAX_ATTEMPTS`, at the next live
   dispatch."* Measured on job `108`: reclaimed at `attempts = 3`, claimed as `attempt=4/3`, `+1`
   `job_executions` row, `dead_letter` at `attempts = 4`. `[MEASURED-R]` `P-27`. For `boom` that extra
   dispatch is harmless; for any handler with a side effect it is **one more side effect after the bound**.
2. **This is an interaction of three independently defensible choices, not a bug in any one of them.**
   increment-on-claim (this entry) + a not-before column that no writer except the mark clears (this entry) +
   terminal-writer-in-the-worker (`D-22`'s neighbourhood, Din 5 Option A). Each option's own `Cost` line was
   right; their joint behaviour was in none of them. `[MEASURED-R]`
3. **The reaper's reclaim re-dispatches with no backoff at all, by construction.** The retry mark does not
   clear `claimed_at`; the claim does not clear `next_attempt_at`; the reaper clears neither. So a reclaimed
   row is `pending` carrying a **past** `next_attempt_at`, and the claim gate says `claimable = True` at that
   instant. `[MEASURED-R]` Combined with Cost 1: **`MAX_ATTEMPTS` is a budget for dispatches of any origin,
   including lease flapping, and the flapping path spends it with zero delay.** A slow-but-healthy job
   reclaimed three times exhausts its budget without ever failing — job 95's Din 3 shape spends two of three.
4. **A guard that correctly rejects a stale transition also discards the policy that transition was
   carrying.** Reviewer probe, job 104: reaper first, then the retry mark → `rowcount = 0`, `attempts` did not
   move twice (correct), **and** `next_attempt_at` was never written, because transition and policy live in
   the same statement. The row is `pending` with `next_attempt_at IS NULL` and the claim gate returns
   `claimable = True` immediately; the `2.853 s` the worker had computed is gone. `[MEASURED-R]` `P-25`.
5. **Jitter narrower than the observation quantum cannot be measured, and both instruments that could have
   separated them were destroyed the same day.** Din 4's "spread" of `2.115 s` / `2.133 s` is **two poll
   ticks**, with jobs clustered `68 ms` and `76 ms` inside a tick — **tighter than the un-jittered round 1's
   `151 ms`**, i.e. the convoy re-formed inside the retry path. `[MEASURED-R]` `P-24`. The two instruments
   that would have shown intended delay were the worker's `Scheduling retry in {actual_delay:.2f}s` line
   (capture deleted) and `next_attempt_at` (cleared by both terminal branches).
6. **The measured gap list confirms growth and does not measure the delay.** Job 98's gaps `4.071787 s` /
   `6.098167 s` are `≈ 2 ×` and `≈ 3 ×` the `~2.03 s` poll period. `[MEASURED-R]` An implementation waiting
   `33 %` less than configured produces the same two numbers. Any future delay claim needs an instrument
   finer than the poll interval, not more arithmetic.
7. **`job_executions.count(*) > 1` now has five distinct causes, so it is a question and not an answer.**
   Full list with ids in `D-21`'s amendment. Retry (`98`–`104`) is cause four and the bound-crossed
   re-dispatch (`108`) is cause five; both are this entry's. `[MEASURED-R]`
8. **`dead_letter` is a verdict, not a diagnosis.** The exception is recorded nowhere — not in `jobs`, not in
   `job_executions`. An operator can tell from `psql` alone that a row bounded out, without knowing
   `MAX_ATTEMPTS`, which is a real gain over reading `status = 'failed'` **plus** `attempts` against a
   constant living in Python. What they still cannot tell is **why**. `[MEASURED-R from source]` `last_error`
   remains unadded and deferred.
9. **The unknown-`type` branch never consults `attempts`, which is a second route around the bound.** It
   writes `failed` directly. Inert today only because the four `super_slow` rows (`93`–`96`) are all terminal.
   `[MEASURED-R from source]`
10. **The delay interval is built by f-string interpolation into SQL.**
    `text(f"interval '{actual_delay} seconds'")` is safe today because `actual_delay` is a
    `random.uniform` float, but the habit is wrong and the fix is one line
    (`func.make_interval(secs=...)` or a bound parameter). `[MEASURED-R from source]`
11. **`now()` in the retry mark is transaction-start time**, so the delay is measured from the mark
    transaction's `BEGIN` and not from the failure instant. Milliseconds here; the same mechanism is
    load-bearing in `D-22` Cost 4. `[MEASURED-R]`
12. **One new nullable column, and its meaning overlaps `claimed_at`'s.** `P-19` counts the values
    `claimed_at` now carries; a retry-waiting `pending` row keeps the last dispatch instant in it, and the
    reaper misses that row only because its *other* term is `status = 'running'` — safety by conjunction,
    which is a property of the current predicate rather than of the data. `[MEASURED-R]`

**Rejected:**

- **(b) increment on failure** — reads more natural (*"count the failures"*) and is the wrong shape here: the
  crash that never reaches the mark statement is **exactly** the case retries exist for, so the counter would
  not advance in the one situation where an unbounded loop is possible. Increment-on-claim trades honesty
  about *what happened* (it counts dispatches, including ones whose handler was never entered) for a bound
  that cannot be escaped by dying. `[INFERRED]` — and Cost 1 is the bill for that trade.
- **(b) derive not-before from `claimed_at + f(attempts)`** — saves a column and couples the retry schedule to
  the lease column, which the claim, the reaper and the heartbeat all write. Any change to lease bookkeeping
  would then silently move every pending retry. `[INFERRED]` Also unreadable in `psql`: *"when is this row
  next eligible?"* becomes arithmetic over three values instead of one column to select.
- **(c) separate `retry_schedule` table** — a join on the hottest query in the system for one nullable
  timestamp, plus a second row to keep consistent with the first across crashes. `[NO EVIDENCE]` Becomes
  arguable only if a retry needs its own history (per-attempt error, per-attempt scheduled time), which is
  `job_executions`' job with the identifier `D-21` still owes.
- **(a) fixed delay** — no reason to prefer it: it neither reduces load under a persistent failure nor breaks
  synchronisation. `[INFERRED]`
- **(b) exponential without jitter** — Relay's own `P-14` is the measured counter-argument, and Din 4 then
  showed the convoy re-forming *inside* the retry path even **with** jitter, because the jitter was narrower
  than the quantum. `[MEASURED-R]` Removing jitter would make that permanent rather than accidental.
- **Full jitter (`uniform(0, delay)`)** — removes the floor, so an attempt can be retried almost immediately
  and the backoff stops backing off on the attempt where it matters most. `[INFERRED]` Decorrelated jitter
  was not evaluated at all — `[NO EVIDENCE]`.
- **Moving `AND attempts < :max` into the claim gate** — the clean-looking fix for Cost 1, rejected **today**
  and not on the merits: it needs a sweep to terminalise the now-unclaimable row, i.e. another `status`
  writer with its own guard and `rowcount` check, on the day the week's numbers freeze. Owner: Week 3.
  `[INFERRED]`

**Revisit when:**

- **`MAX_ATTEMPTS` changes** — the cap stops being inert at `n = 4` (`P-26`), and Cost 1's overdraft gets one
  dispatch more expensive.
- **The poll interval changes** — the `base/2 > poll` arithmetic must be re-derived, not assumed. It has
  already been got wrong once in the other direction (`base` chosen against the quantum, jitter layered on
  afterwards, justification not re-checked).
- **A handler with a real side effect exists** — Cost 1 stops being a curiosity. That is Week 3's idempotency
  key, and the overdraft is one of the two reasons it is needed (the other is `D-22` Cost 2).
- **An attempt/claim identifier lands on `job_executions`** (Week 3, with the dedup key) — Cost 7 becomes an
  answerable query instead of a five-way question.
- **A delay needs to be claimed as measured** — then the instrument comes first: `Scheduling retry` lines
  copied into the log **before** any capture is deleted, or a `scheduled_at` recorded on the evidence row.

---

## D-25: execute-time dedup uses a stable nullable effect key, a named database `UNIQUE`, and conflict-safe insert

**Problem:** A lease expiry makes two executions of one job legal. Relay needs both executions to be allowed while preventing the same **local ledger effect** from being committed twice.

**Options:**
- (a) application `SELECT` then conditional `INSERT`
- (b) bare `INSERT` under `UNIQUE`, handle `UniqueViolation`
- (c) `INSERT ... ON CONFLICT ON CONSTRAINT ... DO NOTHING`, then read `rowcount`
- (d) key by `(job_id, attempts)` rather than stable logical identity

**Chose:** (c), with nullable `effect_key = "job:{job_id}"` and named constraint `uq_side_effects_effect_key`. The row is the local database effect itself, not a reservation for an external action and not a claim-generation record.

**Evidence:** Job 112 had two recorded executions from distinct workers and one keyed effect; stdout recorded insert rowcounts `{1,0}` `[MEASURED]`. Reviewer rerun in a disposable database produced four dispatches across two workers and one keyed effect, with every replay returning `rowcount=0` `[MEASURED-R; raw capture not retained]`. A constraint-free barrier probe made both sessions read `0`, both insert, and finish at `2` `[MEASURED-R]`.

**Cost:**
1. Protection starts only for non-null keyed rows `[INFERRED from schema]`. Three historical `NULL` rows coexisted with the two keyed rows `[MEASURED]`; ordinary PostgreSQL uniqueness treating those nulls as distinct is the mechanism `[INFERRED from database semantics]`.
2. `job:{id}` encodes **one logical effect per job**. A future job needing two legitimate effect kinds would have them collapsed unless identity expands deliberately `[INFERRED]`.
3. This enforces a local table invariant. It does not atomically cover email, HTTP, payment, or any side effect outside this Postgres transaction `[INFERRED]`.
4. Job 112 still had two executions and attempts advanced across the duplicate delivery `[MEASURED]`. Duplicate delivery can also consume CPU and handler time `[INFERRED from mechanism]`. The mechanism narrows duplicate damage; it does not eliminate duplicate work `[INFERRED]`.
5. Downgrade is shape-reversible but destroys stored logical keys. Re-upgrading makes all surviving rows `NULL`; therefore lifecycle probes belong in a disposable database `[MEASURED-R]`.

**Rejected:**
- (a) because the constraint-free two-session probe finished at `2`; a read and later write do not form one atomic decision `[MEASURED/MEASURED-R]`.
- (b) because an expected duplicate would enter the generic handler exception boundary, conflate dedup with failure, and select retry/dead-letter policy; the final status would still depend on the guarded mark winning `[INFERRED from source]`.
- (d) because attempts changed across the measured duplicate deliveries `[MEASURED]`; if attempts were part of the key, those claims would produce different keys and bypass logical-effect dedup `[INFERRED]`.

**Revisit when:** Din 3 measures the effect-commit/status-mark crash seam; Din 4 adds enqueue identity; or one job legitimately owns more than one logical effect kind. `D-24` remains reserved for the broader enqueue-versus-execute idempotency decision after both layers are measured.

---
