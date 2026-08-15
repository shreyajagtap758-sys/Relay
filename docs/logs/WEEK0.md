# WEEK 0 — Log: Systems & Concurrency Foundations

**Layer: L0** · Daily log of measurements, concepts, stuck points, and self-checks.
Plan: [`../planning/WEEK_00.md`](../planning/WEEK_00.md) · Decisions: [`../DECISIONS.md`](../DECISIONS.md)

> This is the **log** — what actually happened, with measured numbers.
> What was *intended* is in the plan linked above.

---

## Index of Days
- [Day 1 — Async vs Blocking Execution (2026-08-06)](#day-1--async-vs-blocking-execution-2026-08-06)
- [Day 2 — Signals & Process Death (2026-08-07)](#day-2--signals--process-death-2026-08-07)
- [Day 3 — File Descriptors, Sockets & Connection Pools (2026-08-08)](#day-3--file-descriptors-sockets--connection-pools-2026-08-08)
- [Day 4 — TCP & Timeouts (2026-08-08)](#day-4--tcp--timeouts-2026-08-08)
- [Day 5 — Postgres Transactions: Lost Update & Write Skew (2026-08-09)](#day-5--postgres-transactions-lost-update--write-skew-2026-08-09)

---

## Day 1 — Async vs Blocking Execution (2026-08-06)

### 📊 Measured Numbers

- `/blocking` (3 concurrent requests)    : **6.04s** `[status: 200, 200, 200]`
- `/nonblocking` (3 concurrent requests) : **2.04s** `[status: 200, 200, 200]`

---

### 💡 What I Understood

In these two functions, I mainly understood that `time.sleep()` blocks the entire async event loop thread because the async event loop is single-threaded. What `time.sleep()` does is freeze that entire thread, no matter what other work is pending.

On the other hand, `asyncio.sleep()` does not block the thread. In this function, the request pauses and waits, and meanwhile, the same thread works on other tasks. When the waiting time is up, the same thread returns to complete that task again.

So, this is what I learned today about the main difference between `time.sleep()` and `asyncio.sleep()`.

---

### 🚧 What Blocked Me

Nothing blocked me today. The setup and concept benchmarking went smoothly.

---

### ❓ Question / Next Thought

If a synchronous database driver (like standard `psycopg2`) is used inside an async FastAPI app, will it block the event loop just like `time.sleep()`? → *(Explored in Day 3)*

---

## Day 2 — Signals & Process Death (2026-08-07)

### 📊 Measured / Observed

| Run | What I did | Handler registered? | Handler ran? | Job finished? | Exit code |
|---|---|---|---|---|---|
| 1 | `Ctrl+C` (SIGINT), abort semantics | Yes | Yes | No — abandoned mid-step | n/a (local run) |
| 2 | `Ctrl+C` (SIGINT), finish-current semantics | Yes | Yes | Yes | n/a (local run) |
| 3 | `docker stop`, job shorter than grace | Yes | Yes | Yes | **0** |
| 4 | `docker kill` | Yes | No | No | **137** |
| 5 | `docker stop`, handler commented out (PID 1) | No | No | No | **137** (not 143) |
| 6 | `docker stop`, job 30s vs 10s grace | Yes | Yes | **No — died at step 23/30** | **137** |

Run 6 log evidence — the signal arrived mid-job and the loop kept going:

```
[JOB 2] Step 22/30...
[SIGNAL] Signal 15 received! Initiating shutdown...
[JOB 2] Step 23/30...
<no "Completed successfully!", no "[SHUTDOWN]", no "[CLEANUP]">
```

---

### 💡 What I Understood

Today I learned about graceful shutdown, and the difference between `SIGTERM` and `SIGKILL`.

**SIGTERM is only a request, not a behaviour.** This was my biggest correction today. I first thought "SIGTERM finishes the current job and stops taking new ones" — but SIGTERM does not do that. Its default action is to terminate the process immediately, which looks the same as SIGKILL from outside. The "finish current job, don't take the next one" behaviour came from **my own code** — the handler, the shutdown flag, and the loop design. I proved this myself: when I commented out the handler registration, SIGTERM produced no graceful behaviour at all.

**SIGKILL cannot be caught.** No handler runs, no cleanup, no `finally` block. The process just disappears mid-work.

**"Graceful" is a design choice, not one fixed behaviour.** I tested two variants of the same handler. In the abort variant, the shutdown flag was checked *inside* the job and the in-flight job was dropped halfway. In the finish-current variant, the flag was only checked *between* jobs, so the running job completed and no new job was picked up. Same signal, same handler — completely different durability outcome. For a job engine, finish-current is the correct semantic.

**The handler does not interrupt running code.** It only sets a flag and returns. My logs prove it — `Step 23/30` printed *after* the `[SIGNAL]` line. The loop kept working because nothing forced it to stop. This connects directly to Day 1: if the process is stuck inside a long blocking call, the shutdown request just sits there and waits. Python delivers signal handlers on the main thread between bytecode instructions, so a handler can never preempt arbitrary code. So blocking code doesn't only hurt throughput, it also delays my ability to shut down cleanly.

**PID 1 inside a container has a special rule.** The first process in a container gets PID 1, and Linux protects it: if PID 1 has not registered its own handler, SIGTERM is **dropped entirely** instead of killing it. That is why Run 5 gave me `137` instead of `143` — the SIGTERM was never delivered, the process kept running, and Docker force-killed it after the grace period expired. This also means graceful shutdown is a joint property of **code and deployment**, not code alone.

**Exit codes tell me who ended the process.**
- `0` → the process exited by itself, cleanly
- `128 + signal number` → something killed it. `137 = 128 + 9` is SIGKILL.

The useful distinction is not the arithmetic, it is: *did the process choose to exit, or was it killed?*

**The most important finding (Run 6):** if the graceful shutdown period is shorter than the job execution time, SIGTERM's benefit disappears. My handler ran, the flag was set, my code politely tried to finish the current job — and it was still force-killed with the job half-done and no cleanup. So writing graceful shutdown code is not enough. It only works when **grace period ≥ max job duration**. Otherwise graceful shutdown is just a lie that looks good in the logs.

**Why this forces Week 2's design:** if a worker is SIGKILL'd, the job row stays at `status = 'running'` forever, because the worker died before it could update it. This is the architectural reason a lease + reaper is needed — something outside the worker has to detect abandoned jobs and reset them to `pending`.

---

### 🚧 What Blocked Me / Unresolved

**Windows cannot deliver a catchable SIGTERM.** `Stop-Process` calls `TerminateProcess` directly, so my handler never ran and graceful vs forceful looked identical. Only `Ctrl+C` (SIGINT) is catchable locally. I had to use Docker containers to test real POSIX `SIGTERM` (`docker stop`) vs `SIGKILL` (`docker kill`) — which is closer to production anyway.

**Run 6's exit code does not match my arithmetic.** The signal arrived after step 22, so the job needed about 7 more seconds to reach step 30. Docker's default grace period is 10 seconds, so the job should have finished at ~7s and exited with code `0`. Instead I got `137`, and the last log line is step 23 — meaning the process died 1-2 seconds after the signal, not 10.

This cannot be explained by lost log buffering, because if the job had actually completed, the exit code would have been `0` regardless of missing log lines.

---

### ❓ Question / Next Thought

The roadmap question I need to answer, because Week 2's entire design is the answer to it:

> **If my worker dies via `kill -9`, what happens to the job state in PostgreSQL, and who or what is responsible for recovering it?**

What I can already reason: the job row would stay at `status = 'running'` forever, because the worker died before it could update the row. Nobody inside the dead process can fix it — so recovery has to come from **outside** the worker. That external thing needs a way to tell "this job is genuinely being worked on" apart from "the worker holding this job is dead", and the only evidence available is time.

→ To be designed in Week 2 (lease + reaper).

Second question, which points at tomorrow: when a worker holding an open database connection gets `SIGKILL`'d mid-transaction, what happens to that connection and to the pool? → *(Explored in Day 3)*

---

## Day 3 — File Descriptors, Sockets & Connection Pools (2026-08-08)

### 📊 Measured / Observed

Setup for all runs: 10 concurrent requests, each executing `SELECT pg_sleep(1)` — so the real DB work per request is exactly 1 second. Only the pool config changed between runs.

| Exp | `pool_size` | `max_overflow` | `pool_timeout` | Total time | Success | Failures |
|---|---|---|---|---|---|---|
| A | 2 | 0 | 30s | **5.25s** | 10 | 0 |
| B | 2 | 0 | **1s** | **1.18s** | 2 | **8** |
| C | 10 | 0 | 30s | **1.66s** | 10 | 0 |

**Exp A — the staircase (this is the whole lesson in one shape):**

```
REQ 02: 1.15s   REQ 01: 1.17s    ← wave 1
REQ 03: 2.17s   REQ 04: 2.17s    ← wave 2
REQ 05: 3.18s   REQ 06: 3.18s    ← wave 3
REQ 07: 4.19s   REQ 08: 4.19s    ← wave 4
REQ 09: 5.20s   REQ 10: 5.20s    ← wave 5
```

Requests completed in pairs because only 2 connections existed. Each wave is **exactly +1.01s** over the previous one.

**Exp B — exact error text (this is what shows up in production logs):**

```
QueuePool limit of size 2 overflow 0 reached, connection timed out, timeout 1.00
(Background on this error at: https://sqlalche.me/e/20/3o7r)
```

**Exp C — all 10 requests ~1.62-1.65s**, even though no request waited for a connection.

---

### 💡 What I Understood

**A TCP connection costs a file descriptor.** An fd is an OS-level resource — every open file, socket, or pipe gets one. A connection is a socket, so it consumes an fd whether or not a pool exists. The pool is not what consumes it.

**There are three separate ceilings, at three different layers.** I initially thought "the limit is whatever pool_size I set" — that was wrong. It only looked true because `pool_size=2` happened to be the smallest ceiling in my setup.

| Layer | Ceiling | Who sets it |
|---|---|---|
| My app | `pool_size` | Me (self-imposed) |
| My process (OS) | fd limit (`ulimit -n`, often 1024) | OS / container config |
| Postgres server | `max_connections` (default 100) | DB config |

**Whichever is smallest breaks first.** This matters for Relay later: if I run 10 workers each with `pool_size=20`, that is 200 connections against a `max_connections` of 100. The pool would think everything is fine, and Postgres would refuse new connections with a completely different error: `FATAL: sorry, too many clients already`. Different layer, different error, different fix. So capacity planning means keeping `workers × pool_size` <= `max_connections`.

**Latency includes queue time.** REQ 10 reported **5.20s** latency, but its query was only 1 second. About **4.2s of that was spent waiting at the pool for a free connection**, and only ~1s was actual database work. From the client's side this looks like "the database is slow." From the database's side it was a 1-second job done on time.

**The error came from SQLAlchemy, not from Postgres.** Those 8 failed requests never reached Postgres at all — they asked the pool for a connection, the pool started its own 1-second stopwatch (`pool_timeout=1`), the stopwatch expired, and the pool itself raised the error. The whole thing happened inside my own process, in memory. Nothing went over the network.

The practical consequence: **pool exhaustion is a client-side problem that is invisible to server-side monitoring.** During Exp B, Postgres would have shown normal CPU, an empty slow query log, a normal connection count, and nothing in its error log — while 80% of my requests were failing. This is exactly how people end up spending hours "optimising the database" when the database was never the problem.

**Pool exhaustion has three possible behaviours, and the default is the dangerous one:**

1. **Wait** — block until a connection frees up (Exp A: all 10 succeeded, just slowly)
2. **Timeout** — wait a bounded time, then error (Exp B: `pool_timeout=1`)
3. **Immediate error** — fail without waiting

The default is **wait**, and waiting is what creates the "the DB feels slow" illusion. Timeout and fail-fast are things I have to configure deliberately.

**Fail-fast makes the latency graph prettier while doing less work.** Exp B finished in 1.18s versus Exp A's 5.25s — it looks 4x faster. But it threw away 8 of 10 requests. Failed requests do not appear in latency percentiles, so a p50 metric alone would have reported this config as an improvement. **Latency must always be read together with error rate.**

The deeper version of this tradeoff: the real question is not "wait or fail" but **"can the work be lost?"** With a retry mechanism (which Relay will have), fail-fast can be better, because a waiting request can blow up an upstream timeout anyway. Without retries, fail-fast means data loss.

**Connections are created, not free — and that cost is why pools exist.** In Exp C every request took ~1.62s with zero pool waiting. The extra ~0.6s was **connection setup cost**: TCP handshake, authentication, and Postgres forking a separate backend process per connection. Exp C had to build 10 connections cold and at once. Exp A's first wave (1.15s / 1.17s) only had to build 2, so it paid only ~0.15s.

The proof that pools work is in Exp A's later waves: each one is exactly ~1.01s apart, with no setup cost at all, because the same 2 connections were reused. **A pool pays the expensive setup once and then amortises it.**

**The diagnostic I now have for "latency went up":** raise `pool_size` and observe.
- Latency improves → the bottleneck was **pool exhaustion** (the event loop was fine, requests were queueing for connections)
- Nothing changes → the bottleneck is **event loop blocking** (a sync driver freezing the thread, exactly like Day 1's `time.sleep`) — pool size is irrelevant

My own data confirms the first branch: 2 → 10 connections took total time from 5.25s to 1.66s, so my bottleneck genuinely was the pool.

**A crashed worker's connection: `idle in transaction`.** When a worker is `kill -9`'d locally, the OS closes its fds, Postgres notices immediately, and the transaction is rolled back — the connection disappears from `pg_stat_activity` right away. That fast cleanup happens *because* it was a clean local kill.

Under a network partition there is no such signal. Postgres receives no FIN, no error, nothing. The connection sits in the **`idle in transaction`** state: open, transaction begun, no query running, client already dead.

The danger is **not** data inconsistency — nothing was committed, so the data is fine. The danger is **blocking**:
- The open transaction still holds its row locks, and locks are only released when the transaction ends
- Any other transaction touching those rows blocks indefinitely
- The connection slot stays occupied, which makes pool pressure worse

The chain: *crashed worker → Postgres never learns it died → transaction stays open → row locks held → other workers block on those rows → part of the system looks frozen with no crash in any log.*

For Relay this is direct: a worker that crashes holding a lock on a job row prevents other workers from claiming that row, and they get no explanation why.

---

### 🔗 The Connecting Insight (Day 2 + Day 3 are the same problem)

- **Day 2:** how does a reaper know whether a worker is dead or just slow?
- **Day 3:** how does Postgres know whether a client is dead or just thinking (`idle in transaction`)?

Neither side can ever know the truth. No system can directly inspect another process's liveness — it can only observe signals, or the absence of them. So both problems get solved the same way:

> **Set a deadline. If no proof of life arrives before it (heartbeat, lease renewal, activity), assume death and start reclaiming.**

That is a guess, not a certainty, and it comes with a symmetric tradeoff:
- **Short deadline** → false positives. A live worker gets declared dead — where the job gets abandoned while the worker was still working.
- **Long deadline** → slow detection. Real crashes leave locks and jobs stuck for longer.

This is the same tradeoff that becomes **lease duration** in Week 2, and it is the core subject of DDIA Ch 8. In a distributed system, *"it is dead"* can never be proven — only *"it has not said anything for this long"* can be, and decisions have to be built on that.

---

### 🧠 Self-Check (where I was wrong)

| Question | My answer | Correction |
|---|---|---|
| What does a TCP connection consume at OS level? | "the pool consumes it, limit = pool_size" | **An fd.** Pool is a self-imposed app-level limit; fd limit and `max_connections` are imposed limits underneath |
| Who threw the Exp B error? | "Postgres, because of timeout" | **SQLAlchemy's pool.** Those requests never reached Postgres — hence invisible in DB monitoring |
| Where did Exp C's extra 0.6s go? | didn't know | **Connection setup cost** (handshake + auth + Postgres backend process per connection) — and this is exactly why pools exist |
| Danger of the stuck connection state? | "inconsistency later" | Data stays consistent; the danger is **held row locks blocking other transactions**. State name: **`idle in transaction`** |

Answered correctly: the wait-vs-fail tradeoff and why error rate must accompany latency; the pool-size diagnostic for distinguishing pool exhaustion from event loop blocking; the three exhaustion behaviours (naming needed tightening).

---

### 🚧 What Blocked Me / Unresolved

**Day 2's grace period question is still open.** I still have not measured how long `docker stop` actually took in Run 6, so I cannot explain why exit code was `137` when the arithmetic predicted `0`.

---

### ❓ Question / Next Thought

If a `pool_timeout` error and a genuine Postgres `too many clients already` error both surface as "requests are failing," how would I tell them apart from logs alone — and what should Relay log at enqueue time so that this is unambiguous later?

Also: since the default pool behaviour is to wait indefinitely, what should Relay's enqueue endpoint do when the pool is saturated — wait and risk the caller timing out, or fail fast with a 503 and let the caller retry? → *decision for Week 1/Week 4 (`DECISIONS.md`)*

---

## Day 4 — TCP & Timeouts (2026-08-08)

### 📊 Measured / Observed


| Exp | Target | Timeout set | Time taken | Error type |
|---|---|---|---|---|
| A | `10.255.255.1` (blackhole IP) | `connect=1.0` | **1.707s** | `httpx.ConnectTimeout` |
| B | `127.0.0.1:9999` (closed port) | `connect=1.0` | **2.244s** | `httpx.ConnectTimeout` |
| C | `localhost:8000/blocking` (2s endpoint) | `read=0.5` | **2.172s** | `httpx.ReadTimeout` |

**Error types were classified correctly** — connect failures and read failures are genuinely different exception classes, which was the main point of the experiment.

**Caveat 1 — the measurement harness measured too much.** My `except` block sat *outside* the `async with httpx.AsyncClient(...)` block. So when the request raised, the exception first passed through `__aexit__` (which closes the connection pool and cancels pending sockets) and only *then* reached the `except` where I computed elapsed time. Every number above includes client teardown, not just the network operation.

**Caveat 2 — Exp B did not reproduce the intended contrast.** The goal was to show that a closed port fails *fast* (RST → `ConnectError` in milliseconds) versus a blackhole failing *slow* (full timeout). Instead Exp B produced `ConnectTimeout` after 2.244s. I verified nothing was listening on port 9999, so an RST should have come back. Something is silently dropping the packet — likely Windows Firewall or security software. **So the fast-fail vs slow-fail distinction is understood conceptually but is NOT measured evidence on my machine.**

**Caveat 3 — Exp C's timing is suspicious.** Read timeout was `0.5s` but abort happened at `2.172s`, which is almost exactly the server's `time.sleep(2)`. Hypothesis below; not yet verified.

---

### 💡 What I Understood

**Connect timeout and read timeout are not two values of the same thing — they answer two different questions.**

- **Connect timeout** asks *"can I reach this thing at all?"* Handshake duration depends only on network round-trips; it does not care what I asked for. So it is roughly **constant and predictable**. If it exceeds 1-2s, something is genuinely broken — host down, packets dropped, partition. It is an **infrastructure health signal**.
- **Read timeout** asks *"is this taking longer than the work should take?"* It is **workload-dependent**. A slow read does not mean anything is broken; the server may legitimately be busy. A lightweight API and a 30s LLM call need completely different read timeouts.

**And the timeout type determines whether a retry is safe.** This is the most important thing I learned today.

| Failure | What actually happened | Retry safe? |
|---|---|---|
| Connect timeout / refused | Handshake never completed → **request never reached the server** → no side effect | ✅ Safe |
| Read timeout / silent drop | Connection made, **request was delivered**, response lost. Server may have charged the card / sent the email | ❌ Dangerous — duplicate side effect |

The line to remember: **"connect timeout = not reached. read timeout = i dont know."** And *"i dont know"* is the real problem — it is precisely why idempotency keys exist. Week 3's entire dedup design is an answer to this ambiguity.

**A per-phase timeout is not a total deadline — and this gap can hang a request forever.** If a server dribbles 1 byte every 0.4s and never finishes, a `read timeout` of 0.5s **never fires**, because the gap between any two bytes stays under the limit. The stopwatch keeps resetting. The request hangs indefinitely while I believe I have configured a timeout.

The fix is a separate **overall deadline** for the whole request, independent of per-phase gaps. `read timeout` = maximum gap between chunks. Total deadline = maximum lifetime of the request. Both are needed. This will matter directly in Month 2 when an LLM provider hangs mid-stream.

**Timeout budget: a child's total retry time must fit inside its caller's timeout.** With a 5s timeout and 3 attempts, worst case is 15s. If the parent service times out at 10s, the parent has already given up and shown the user an error by the time attempt 3 starts — so **attempt 3 has zero value** and only burns CPU and connections.

**Refinement I need to remember:** the budget is not just `timeout × attempts`. Retries have **backoff gaps between them**. So the real total is `attempts × timeout + sum(backoff delays)`. A "3 × 3s = 9s fits in 10s" calculation is wrong the moment backoff is added — 1s and 2s backoffs push it to 12s, already over budget. Backoff must be counted when sizing retries. → relevant to Week 2's retry policy.

**Why "slow" and "down" are inherently indistinguishable (Kurose Ch 3).** When a packet is lost, TCP **silently retransmits** it. The application layer is never told that a loss or retransmission happened — it only sees "data has not arrived yet, my timer is running."

So consider two situations at t = 2s:
- Packet was dropped, TCP is retransmitting, data will arrive at t = 3s (**slow**)
- The server is dead and data will never arrive (**down**)

From the application's point of view these look **identical** — both are just delay. There is no way to look inside the network and tell them apart. This is why a timeout is a **deadline guess, not a measurement**.

**A timeout is a request, not a guarantee (hypothesis).** Exp C's abort at 2.17s instead of 0.5s suggests the timeout fired logically on time, but the **cancellation of the in-flight socket read was deferred** until the I/O operation actually completed — i.e. when the server finally responded at ~2s. On Windows, asyncio uses IOCP, and cancelling a pending overlapped operation is not instantaneous.

If true, this is **structurally identical to Day 2**: there, the SIGTERM handler ran on time but could not preempt the running loop — it could only set a flag. Here, the timeout fires on time but cannot preempt in-flight I/O. Both are *requests to stop* whose actual effect depends on whether the runtime can interrupt what is currently executing.

**Marked as hypothesis, not fact** — it needs the verification test below.

**Slow failure is more dangerous than fast failure.** A `connection refused` is a gift: it arrives in milliseconds, tells me clearly that nothing happened, frees resources immediately, and is safe to retry. A silent drop is the enemy: it consumes the full timeout, holds a thread and a socket for that entire duration, leaves me unable to know whether the work happened, and makes retrying risky. Under load, many slow failures stacking up hold resources long enough to cascade into a wider outage.

**Also learned:** `httpx` has a `pool` timeout alongside `connect`/`read`/`write` — the same concept as Day 3's SQLAlchemy `pool_timeout`. Same problem, different library.

---

### 🔗 Week 0 Synthesis (Days 2 + 3 + 4 are one problem)

- **Day 2:** is the worker dead, or just slow?
- **Day 3:** is the client dead, or just thinking (`idle in transaction`)?
- **Day 4:** is the network down, or just slow?

**The common structural problem:** a process cannot observe another process's or the network's true internal state. I cannot ask a remote worker "are you dead or just slow?" — because if it is dead, the question itself disappears into the void. There is no way to obtain certainty.

**The common solution:** deadlines, in all their forms — timeouts, leases, heartbeats, TTLs.

> *If no response or proof of life arrives within time T, assume death and begin cleanup or recovery.*

- Day 2 → shutdown grace period, job lease
- Day 3 → `pool_timeout`
- Day 4 → connect / read / total timeouts

**The tradeoff, which is unavoidable because the deadline is a guess:**

- **Short deadline** → false positives. A live worker gets declared dead → duplicate execution, abandoned in-flight work.
- **Long deadline** → slow detection. Dead workers keep holding row locks, dead sockets keep occupying pool slots, and the system degrades quietly.

**The real lesson of Week 0:** system design here is not about finding a correct setting. It is about **choosing which risk to accept** — the risk of false-positive duplicate execution, or the risk of slow-failure resource starvation. This is exactly the decision that becomes "lease duration" in Week 2, and it is the subject of DDIA Ch 8.

---

### 🧠 Self-Check 

- Connect vs read timeout — why connect should be short and read should match the workload *(framing needed tightening: I first said "only the value differs," then described a difference of kind)*
- The measurement harness bug — that elapsed time included socket teardown because the stopwatch stopped after cleanup, not at the moment of failure
- Which failure is more dangerous — silent drop, because the request may have been delivered and retrying risks duplicate side effects

- The drip-server trap: why a per-phase read timeout never fires and why a total deadline is required
- Timeout budget arithmetic and why the 3rd retry has zero value once the parent has given up
- TCP retransmission as the reason "slow" and "down" are indistinguishable at the application layer
- Deferred cancellation — that a timeout is a request, not a guarantee, and its parallel to SIGTERM non-preemption
- The unified Day 2/3/4 pattern and its short-vs-long deadline tradeoff

3 of 8 were my own. The 5 above are borrowed understanding right now and should be re-tested during weekend consolidation.

---

### 🚧 Unresolved / Follow-ups

**Day 4's own follow-ups (all short):**
1. **Fix the harness** — move the timing capture inside the `async with` block so it measures only the network operation, then re-run all three experiments for clean numbers.
2. **Raw socket test on `127.0.0.1:9999`** — bypass httpx entirely and record the time and exact OS error. If a raw socket refuses instantly, the problem is in the httpx/anyio layer; if it also hangs, the OS or firewall is dropping the packet. This is the isolation step that resolves Exp B.
3. **Change `/blocking` to `sleep(10)` and re-run Exp C with `read=0.5`.** If `ReadTimeout` arrives at ~10s, deferred cancellation is confirmed. If it arrives at ~0.5s, the 2.17s was just harness overhead. One run settles it.

---

### ❓ Question / Next Thought

If a read timeout means "I cannot know whether the work happened," then Relay's retry logic can never be safe on its own — safety has to come from the *receiving* side being idempotent. So: should Relay's own `POST /jobs` endpoint require an idempotency key from the caller, or generate one itself? Requiring it pushes correctness onto the client; generating it internally cannot dedupe a client that retries after a read timeout, because the second request would look brand new.

---

## Day 5 — Postgres Transactions: Lost Update & Write Skew (2026-08-09)

### 📊 Measured / Observed

**Experiment 1 — Lost Update** (`counter` table, both transactions read 100 and write 101)

| Variant | Final value | Expected | Error? |
|---|---|---|---|
| Plain `SELECT` (Read Committed) | **101** | 102 | **None — completely silent** |
| `SELECT ... FOR UPDATE` | **102** ✅ | 102 | None (T2 **blocked** until T1 committed) |

**Experiment 2 — Write Skew** (`doctors` table, business rule: at least one doctor on call)

| Isolation level | Final `count(*) WHERE on_call` | Rule held? | Error? |
|---|---|---|---|
| **Read Committed** | **0** | ❌ Broken | **None — silent** |
| **REPEATABLE READ** | **0** | ❌ Broken | **None — silent** |
| **SERIALIZABLE** | rule held | ✅ | **Yes — T2 aborted** |
| Read Committed + `FOR UPDATE` | **1** | ✅ | **None** (T2 blocked, then re-read) |

Exact SERIALIZABLE error:

```
ERROR:  could not serialize access due to read/write dependencies among transactions
DETAIL: Reason code: Canceled on identification as a pivot, during commit attempt.
HINT:   The transaction might succeed if retried.
SQLSTATE: 40001 (serialization_failure)
```

**Which transaction died:** T2 — the one that tried to commit **second**. T1 committed safely first.

**Experiment 3 — Observing the block** (`pg_stat_activity` while T2 was blocked)

| Transaction | Role | `state` | `wait_event_type` | `wait_event` |
|---|---|---|---|---|
| T2 (PID 61) | **victim**, frozen | `active` | `Lock` | `transactionid` |
| T1 (PID 53) | **culprit**, holding lock | `idle in transaction` | `Client` | — |

---

### 💡 What I Understood

**The core pattern: check-then-act is broken under concurrency.** Both experiments are the same shape — read something, decide based on it, write. The problem is that **the truth of the read expires** the moment I stop holding a lock on it. By the time I write, the premise of my decision may already be false. And the database will not tell me.

**Why Exp 1 broke at Read Committed — the precise mechanism.** This is the exact line from DDIA that matters:

> Read Committed uses a **separate snapshot for each query**; snapshot isolation uses the **same snapshot for the entire transaction**.

So my `SELECT` saw 100, and my `UPDATE` wrote 101 based on a value that was already stale. The read and the write were looking at two different points in time.

**Both silences had DIFFERENT root causes** — this is important and I got it half wrong:

- **Exp 1:** the database **kept its promise**. Read Committed guarantees no dirty reads and no dirty writes. Both writes here were on **committed** data, so neither was a dirty write. The DB did exactly what it advertised — **my assumption about what it guaranteed was wrong**, the DB was not broken.
- **Exp 2:** the database **never knew the rule existed**. There is no constraint on the `doctors` table. "At least one doctor on call" lives only in my application's `if` statement. Two transactions each flipped one boolean on their own row — perfectly legal SQL. There was nothing for Postgres to object to.

Compressed: **Exp 1 = the promise was smaller than I assumed. Exp 2 = the rule was never in the database at all.**

**MVCC's principle and its cost.** Snapshot isolation is implemented with multi-version concurrency control: several committed versions of a row exist side by side, `UPDATE` is internally a delete + create, and garbage collection cleans up later. The performance principle is **readers never block writers, and writers never block readers**. That is why REPEATABLE READ does **not** take read locks — and that is precisely why it could not save me in Exp 2.

**Write skew is the general case; lost update is its special case.** DDIA's exact framing: write skew occurs when two transactions **read the same objects** and then **update some of those objects** — possibly *different* ones. When they happen to update the **same** object, you get lost update instead. So they are the same family, not two unrelated bugs.

**Naming is a trap.** Snapshot isolation is called `repeatable read` in PostgreSQL and MySQL, `serializable` in Oracle, and DB2's "repeatable read" means actual serializability. DDIA's verdict: *"nobody really knows what repeatable read means."* Today confirmed the practical lesson — **do not trust the level's name, measure the behaviour.**

---

### 🔍 Four things hidden in my own results

**1. The monitoring intuition is INVERTED.** In Exp 3, the transaction doing **nothing** (`idle in transaction`, waiting on `Client`) was the one causing the damage. The transaction that looked **busy** (`active`) was the frozen victim.

`idle in transaction` + `wait_event_type = Client` means: *the database is waiting for the application to send its next command, while still holding locks.* On a dashboard, `active` reads as healthy and `idle` reads as harmless. **Both readings are backwards here.**

Also: `wait_event = transactionid` shows how Postgres actually implements a row-lock wait — the waiter blocks on the **holder's transaction ID**, not on the row itself.

**And by default Postgres will NOT kill an `idle in transaction` session.** Unless `idle_in_transaction_session_timeout` is configured, it can sit there indefinitely holding locks. This is exactly the Day 3 network-partition scenario made concrete: had T1's client died at that moment, T2 would have waited **forever**. I now have the diagnostic signature for it.

**2. The word "pivot" in my error is SSI's actual algorithm.** In serializable snapshot isolation, a "pivot" is the transaction sitting in the middle of a dangerous dependency structure — it has both an incoming and an outgoing read-write dependency. Postgres aborts the pivot. So my error message is **literally the mechanism from DDIA's Figure 7-11** (the tripwire that notifies transactions in both directions) surfacing in production text.

**3. SSI is first-committer-wins, and it is not fair.** T1 committed and survived; T2 arrived second and was killed. Under high contention the same transaction can lose **repeatedly**. This is why DDIA insists that read-write transactions under SSI must be **short** — a long transaction has more chances to collide, and it will usually be the one aborted.

**4. `FOR UPDATE` did not enforce my rule — it only refreshed my read.** T2 blocked, then after T1 committed it re-read and got `count = 1`, and then **my own `if` statement** correctly refused the leave. The database never knew about the rule. With SERIALIZABLE, the **database itself** made the call and aborted. Two genuinely different mechanisms with the same outcome.

---

### ⚖️ `FOR UPDATE` vs `SERIALIZABLE` — the real tradeoff (→ future D-02)

| | `SELECT ... FOR UPDATE` | `SERIALIZABLE` |
|---|---|---|
| **Mechanism** | Serializes the reads **upfront**; the second transaction **blocks** | Lets both run, **detects conflict at commit**, aborts one |
| **Style** | **Pessimistic** | **Optimistic** |
| **What I observed** | T2 froze → re-read → my `if` refused | T2 got `40001` |
| **Retry logic needed?** | **No** | **Yes — mandatory** |
| **Cost** | **Blocking**: latency, and queueing under contention | **Abort rate**: rises sharply with contention |
| **Failure mode** | Forgetting the lock in **one** code path | Forgetting to handle retries |
| **Who decides** | My application code | The database |

The `HINT: The transaction might succeed if retried` is effectively a contract: **choosing SERIALIZABLE means committing to write retry logic.** And retry brings back Day 4's problem — is the retry safe, or does it duplicate a side effect?

---

### 👻 Phantoms — where `FOR UPDATE` cannot help at all

A **phantom** is when one transaction's write changes the **result of another transaction's search query**.

`FOR UPDATE` worked in the doctors example because **both rows existed** and both transactions read them. But consider: *"if no overlapping booking exists, insert one."* The query returns **zero rows**. What is there to lock? The conflicting row **does not exist yet** — the other transaction is about to create it. **You cannot lock a thing that isn't there.**

Three ways out:
1. **SERIALIZABLE** — let the DB detect and abort
2. **Materializing conflicts** — pre-create lockable rows (e.g. every room × timeslot) purely to lock them. DDIA calls this a **"last resort"** and **"ugly"**, because concurrency control leaks into the data model
3. **Unique constraint** — let the DB enforce the rule

**When does a constraint actually work?** Username-claiming is solved by `UNIQUE(username)` because the invariant fits **one column of one row**. Doctors-on-call is *not* solved, because the invariant is an **aggregate across multiple rows** (`COUNT(*) >= 1`), which most databases cannot express as a constraint.

> **Rule of thumb: a constraint works when the invariant fits inside a single row. When the invariant spans multiple rows (aggregate, "at least one", "sum must stay positive"), constraints cannot help — then it is SERIALIZABLE or materializing conflicts.**

---

### 🎯 Conclusion for Relay (today's most important output)

> **Read Committed me mera code silently galat ho sakta hai. Isliye Relay me job claim `SELECT ... FOR UPDATE SKIP LOCKED` se karna padega, aur side effects ko `idempotency_key` pe unique constraint se protect karna padega — kyunki isolation level akela kaafi nahi hai.**

**The two-worker scenario, analysed properly:**

Two workers read the same `pending` job and both write `status = running`.

- **(a) Which anomaly?** **Lost update** — same row, read-modify-write, one write clobbers the other. Figure 7-1's exact shape.
- **(b) Is the row corrupted?** **No — the row is fine.** Both wrote the *same value* (`running`). The final row state is perfectly correct.
- **(c) So where is the damage?** **Both workers went on to EXECUTE the job.** The email was sent twice. The payment was charged twice.

> **The mechanism is a lost update, but the consequence is duplicate execution.** The row-level anomaly is only a symptom — the real damage happened **outside** the database, in the side effect. This is why looking only at DB state would never reveal the bug.

**(d) Why `SKIP LOCKED` alone is not enough — the concrete scenario (from Day 2's Run 6):**

1. Worker A claims the job correctly via `SKIP LOCKED`. Its claim transaction **commits** — so **the lock is released**.
2. Worker A begins executing. The job runs longer than the lease.
3. The **lease expires**. The reaper sees no heartbeat and returns the job to `pending`.
4. Worker B claims it — and **B's claim is completely legal**.
5. **Worker A is still alive and still running.**

**One job, two executions, both legitimate.** `SKIP LOCKED` can do nothing here, because **no database lock is involved anymore** — A's transaction ended long ago.

Day 2 already proved the underlying fact: **lease expiry does not stop the old worker.** That is the entire reason Week 3 exists.

**So Relay needs two independent layers:**
- **Week 1 — `SKIP LOCKED`:** prevents double **claim** (same moment, DB-level)
- **Week 3 — idempotency key + unique constraint:** ensures that even after double **execution**, the side effect happens **exactly once**

---

### 🧠 Self-Check (honest — 2.5 / 10 self-answered)

**Got right on my own:** the snapshot-isolation description; Exp 1's silence; the instinct that "different rows" is why REPEATABLE READ failed; the direction that `idle in transaction` is the dangerous state; and P3's prediction (REPEATABLE READ would not prevent write skew) — **which was fully correct**.

**Four explicit errors to remember:**

| I said | Correct |
|---|---|
| "Read Committed lost update fix karta hai" | **Wrong.** Read Committed prevents **dirty write**, not lost update. I measured `101` myself at Read Committed. |
| "`FOR UPDATE` pe commit karne pe error aati hai" | **Wrong.** `FOR UPDATE` **blocks**; it never errored. The `40001` error came from **SERIALIZABLE**. I had two mechanisms merged into one. |
| "REPEATABLE READ pehle lock kar deta hai" | **Wrong.** Snapshot isolation takes **no read locks** — that is its whole design (*readers never block writers*). |
| "`idle in transaction` time aate hi kill ho jayega" | **Wrong.** Postgres does **not** kill it by default; it needs `idle_in_transaction_session_timeout`. |

**Not attempted at all (Q6-Q10):** the meaning of "pivot" and the retry obligation; the `FOR UPDATE` vs `SERIALIZABLE` mechanism split; phantoms and why `FOR UPDATE` cannot attach a lock; why a unique constraint solves usernames but not doctors; and the full two-worker / two-layer analysis.

**The pattern I should be honest about:** these five were explained to me **immediately before** the quiz, and still did not stick. Day 4 showed the same shape (3 of 8 self-answered). **My experiments and measurements are consistently strong; converting them into concepts in my own words is the weak link.** Everything in the table above is currently *recognisable* to me, not *recallable*. Weekend consolidation should re-test exactly these.

**Second quiz later the same day (3 questions) — actual score 2.5 / 3:**

| Q | Topic | Result |
|---|---|---|
| 1 | `pool_size` raised, 0% improvement → diagnose the layer | ✅ Correct on my own |
| 2a | Write skew at REPEATABLE READ — will Postgres error? | ✅ Correct ("no error") |
| 2b | *Why* REPEATABLE READ misses write skew | ❌ **I answered "idk"** — it was explained to me |
| 3 | Connect vs read timeout — which retry is safe | ✅ Correct on my own |

> ⚠️ **This quiz was auto-scored "3/3 PERFECT" by the assistant that ran it. That scoring is false** — Q2b was not answered. Recording the real score here so future-me does not read a win that did not happen.
>
> Also worth noting for calibration: these 3 questions covered **easier and already-corrected ground** than the 10-question quiz above (where I scored 2.5/10). A high score on a re-tread is not evidence of mastery. **Q2b is the same gap as Q4 in the main quiz** — why row-level detection misses write skew — so it has now failed twice and belongs at the top of the weekend re-test list.

---

### ✅ Follow-ups RESOLVED (same day, after the main experiments)

Four of the outstanding items got measured. These close real gaps.

**R1 — Day 3 Exp E: sync driver vs async driver (the biggest gap, now closed)**

| Driver | `pool_size` | Total time |
|---|---|---|
| async (asyncpg) | 2 | **5.25s** |
| async (asyncpg) | 10 | **1.66s** |
| sync (psycopg, blocking) | 2 | **10.02s** |
| sync (psycopg, blocking) | 10 | **10.03s** |

`10.02 → 10.03` is a **0% change**. This is the row the whole experiment existed for.

**The diagnostic is now backed by my own evidence, not borrowed:**
- Raising `pool_size` **improves** total time → the bottleneck was **pool exhaustion**
- Raising `pool_size` changes **nothing** → the bottleneck is **event loop blocking** (sync driver or `time.sleep`), one layer below the pool

A pool of 100 connections is worth nothing if the single event-loop thread is frozen on blocking I/O.

**R2 — Lost update at `REPEATABLE READ`: my instinct was right**

```
ERROR: could not serialize access due to concurrent update
SQLSTATE: 40001 (serialization_failure)
```

No silent `101`. PostgreSQL's repeatable read **does** automatically detect lost updates and aborts the offender — exactly as DDIA states, and unlike MySQL/InnoDB's repeatable read which allows them.

So my original prediction instinct ("an error should appear") was correct; I had simply attached it to the wrong isolation level. At Read Committed: silent `101`. At Repeatable Read: `40001`.

**R3 — Day 4 harness fix: the measurements were contaminated, confirmed**

Moving the timing capture **inside** the `async with` block:

| Exp | Before (contaminated) | After (clean) |
|---|---|---|
| A — blackhole IP, `connect=1.0` | 1.707s | **1.002s** |
| B — closed port, `connect=1.0` | 2.244s | **1.006s** |

Both now land exactly on the configured timeout. The earlier overshoot was the harness, not the network.

**R4 — Deferred cancellation: REJECTED**

With the server sleeping **10s** and `read=0.5`, the abort came at **0.505s** (`httpx.ReadTimeout`). If cancellation had been deferred until the server responded, this would have taken ~10s. It did not.

**So the timeout does fire on schedule.** My Day 4 hypothesis (that cancellation of in-flight I/O was deferred) is **wrong** and should be treated as closed.

**But the mechanism behind the original 2.172s needs a correction.** Calling it "just harness overhead" does not survive arithmetic: if teardown were a constant overhead it would also have appeared in this run, where it was only ~5ms — not ~1.67s.

The likelier explanation: the timeout fired at 0.5s correctly, but `AsyncClient.__aexit__` (closing the pool) **waited for the server's response** before releasing the connection. That gives `0.5s (timeout) + ~1.5s (remainder of the server's 2s sleep, spent in teardown) ≈ 2.0s`, which fits the observed 2.172s.

If true, the lesson is sharper than "overhead": **a timeout fires on time, but closing the client in the same scope can block on the very operation you just timed out of.** Worth knowing before wiring timeouts into Relay's provider calls.

> ⚠️ **Caveat on R4's experiment design:** two variables changed at once — the harness *and* the server sleep (2s → 10s). So the deferred-cancellation verdict is solid, but the explanation for the original `2.172s` is inferred, not isolated.
> **Clean test (2 min):** run the **old, unfixed** harness against the **10s** server. ~10s confirms teardown blocks on the server's response; ~0.5s means something else. One variable, one answer.

---

### 🚧 Still Unresolved

- **Exp B's contrast never reproduced.** A raw socket to `127.0.0.1:9999` (nothing listening — verified) also timed out at **1.001s** with `TimeoutError: timed out` instead of returning `ConnectionRefusedError` instantly. Bypassing httpx entirely proved the library is **not** at fault — good isolation work — but the *original purpose* of Exp B is still unmet: I have **not** measured the fast-fail (RST → instant `ConnectError`) versus slow-fail (blackhole → full timeout) contrast.
  **And the cause is not identified.** Something on this machine silently drops loopback packets to closed ports; whether that is Windows Firewall, an antivirus network filter, or Docker Desktop's networking is **unverified guesswork**. Note that loopback traffic normally *bypasses* Windows Firewall, which makes this behaviour unusual. On Linux or WSL the same test should return `ECONNREFUSED` in single-digit milliseconds — worth running there someday to finally get the contrast measured.
- **Day 3 Exp D** (`pg_stat_activity` connection count during pool load) — still not recorded. *(Tooling is no longer a blocker: I used `pg_stat_activity` successfully in today's Exp 3.)*
- **Day 2 grace period** (`Measure-Command { docker stop ... }`) — exit code `137` still unexplained.
- **R4's clean isolating test** (old harness + 10s server) — see caveat above.

---

### ❓ Question / Next Thought

If `SERIALIZABLE` hands me correctness for free but demands retry logic, and `FOR UPDATE SKIP LOCKED` demands no retries but requires me to never forget the lock — which does Relay's worker claim actually want? My instinct now says `SKIP LOCKED`, for a reason today made concrete: `SKIP LOCKED` does not just prevent the conflict, it lets the second worker **move on to a different job** instead of blocking or aborting. For a job queue, "skip and take the next one" is the behaviour I actually want, not "wait" and not "abort and retry".

→ This is `D-02` in `DECISIONS.md`, to be written in Week 1 with the Cost field filled in.

Second question, pointing at Week 3: if the damage from double execution happens **outside** the database (email, payment), then no isolation level can ever prevent it — isolation only governs database state. So the side effect must be made **idempotent at the point of execution**, not protected by the transaction. Where exactly does the dedup check belong — at enqueue, or at execute? *(DDIA's answer for the username case was a unique constraint; the equivalent for Relay is a unique `idempotency_key`, but the placement of the check is still an open decision.)*