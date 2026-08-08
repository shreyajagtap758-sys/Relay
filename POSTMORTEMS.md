# EVENT LOOP FROZEN
> *(dont give blocking work to event loop, use async)*

- when i wrote `time.sleep(6)` in `/blocking`, and `await asyncio.sleep(2)` in `/nonblocking`,
- and sent request eg. at `time=0` from blocking and immediately after requested for nonblocking at `time=1`,
- so now at `time=0`, event loop is **BUSY(froze)**, so when at `time=1` second request arrived, it waits till request 1 ends.
- so `time.sleep(6)` waits till `time=6` then finally it finishes. now event loop continues the second request.

### Execution

- blocking request
- wait 6 seconds
- finishes
- nonblocking started
- wait 2 second
- finishes

```text
Blocking request started
Blocking request finished
Non-blocking request started
Non-blocking request finished
```

### NOW REVERSE THE FUNCTION EXECUTION

- now hit `await asyncio.sleep(2)` eg. at `time=0` and immediately after hit `time.sleep(6)` at `time=0.1`,
- nonblocking request
- says 2 seconds wait
- this request wait while others are taken
- took blocking request
- finished
- continue nonblocking after 2 seconds

```text
Non-blocking request started
Blocking request started
Blocking request finished
Non-blocking request finished
```

---

# LIMITED THREAD POOL
> *(blocking work can be done by threads, but they are limited)*

- now event loop has helper = thread 1, thread 2, thread 3...
- now we have multiple tasks which has blocking work, so event loop distributes work to threads.
- now we send request `/executor` -> and it is blocking function,
- so event loop -> threadpool -> worker threads -> `time.sleep(3)` (blocking function)

- lets say we have `thread max workers = 3`,
- so worker1 takes request 1, worker2 takes req2 and so on,
- all executes at same time because work is done by individual workers
- ~3 seconds total

### Now let max worker = 1

```text
event loop
      ↓
   worker1
```

- now three req again
- worker1 takes req1 -> `time.sleep(3)`
- now req2 no worker available so it waits/queue
- same for req3.
- this makes pool full, new task waits.

Timeline:

```text
t=0  -> worker1 -> req1
t=3  -> worker1 -> req2
t=6  -> worker1 -> req3
```

~6 seconds

### Key Points

- So this didnt freeze event loop(it didnt took blocking work as per previous experiment).
- even if event loop is free/healthy, application can be slow as thread pool can be the reason(one worker work on one blocking req at a time)
- when workers busy -> pool full -> makes queue(waiting req) -> latency high(takes more time)

---

# CPU HEAVY PYTHON COMPUTATION (GIL PROBLEM)

- now if a blocking work has cpu heavy computations(image/vdo process, math computation, recursive algo), it can be sent to threads, but threads are not enough for the speed,
- because cpu heavy work assigns GIL -> GIL is like a key, given to one thread at a time to execute python bytecode.
- so what else can we do to speed it up?

### Instead of

```text
one process
    ├── thread1
    ├── thread2
    └── ...
(one GIL)
```

### Use

```text
process1 (own GIL)
process2 (own GIL)
process3 (own GIL)
```

- so now CPU task 1, CPU task 2... runs parallel
- also we can use dedicated worker service (better)

### Summary

```text
event loop
      ↓
blocking work
      ↓
threadpool
      ↓
but they are limited
      ↓
increase workers

cpu-heavy work
      ↓
cant use threadpool
      ↓
do processpool
```

---

# SIGNAL

> when a process is running and an interrupt/signal was sent to it by os.

- signal are async
- arrive at any point
- they are unreliable (not wait in queue, signals can be lost).

Example:

```text
docker
   ↓
worker
   ↓
DBstatus = (running)
   ↓
signal(interrupt)
   ↓
kill? terminate?
```

---

# SIGKILL AND SIGTERM

## sigterm

- now when os sends sigterm, the worker dont exit immediately,
- instead it is given a specific timeline to complete the rest of the execution
- so complete workand then exit(cleanup possible),
- and when finally it exits, dbstatus = success.

## sigkill

- it kills the job immediately no matter what it was doing/executing,
- it stops immediately with no dbstatus update.
- meaning when job started dbstatus = running,
- and when in middle it got kill,
- db status would remain running forever.
- no cleanup chance is there in sigkill(incomplete work).

### then why sigkill exists?

- if when sigterm is given, and the job stucks on deadlock/hang
- then eventually after its timeline dead, sigkill is sent so job dont run forever,
- there is also tradeoff that is sigterm is sent, and remaining work takes more than the limited timeline,
- then even if job was not hang/deadlock, it gets killed.

```bash
kill job      = sigterm
kill -9 job   = sigkill
```

Example:

```text
worker
   ↓
openai api
   ↓
do work
   ↓
openai respond
   ↓
save db
   ↓
exit
```

---

### Power failure example

- lets say job got response from openai,
- now power failure/kernel panic/machine crash,
- now no os exist for signal,
- so again workers are dead,
- and db status = running(still)
- because no db save was done.

---

# GRACEFUL SHUTDOWN (sigterm)

Example:

```text
worker
   ↓
openai api
   ↓
save db
   ↓
exit
```

- lets say worker - calling openai api :
- in middle i do `docker compose up --build` (old container stop),
- os sends sigterm,
- now there must be strict steps to complete remaining work.

### Steps

1. stop taking new jobs/work first.
   - if not done first then it may take multiple jobs and may take longer time which can kill the job.

2. complete the remaining process.
   - openai response
   - save db
   - success.

3. close all the resources(redis connection/db connection etc cleanup).

4. finally exit.

> but still this dont gurantee job will not lost as for limited timeline given to job.

---

# SIGNAL HANDLER

- when os sends signal
- and worker catches the signal,
- the signal is catched by signal handler not the worker.

### Important

- signal handler is only the message receiver and giver,
- it dont complete the remaining work of the job.
- (`shutting_down = true/false`)
- this function is not used for cleanup.

### Flow

```text
worker
   ↓
os send signal (sigkill)
   ↓
signal handler takes it
   ↓
stop immediately
```

```text
worker
   ↓
os send signal (sigterm)
   ↓
signal handler takes it
   ↓
confirm to os
   ↓
worker now completes remaining work in graceful steps
   ↓
if done in timeline
   ↓
success and exit

else

sigkill
   ↓
worker dead
```

---

# KUBERNETES POD TERMINATION

- docker handles one container while Kubernetes manages multiple containers.

- suppose relay has 20 workers,
- traffic is low,
- so Kubernetes auto decides only 10 workers are needed,
- so it doesn't kill those workers,
- it firstly stops giving work/traffic to those workers who need to be stopped.

- now send sigterm to each worker,
- workers gracefully shutsdown(complete all steps),
- Kubernetes wait by default 30 seconds for workers to finish,
- if done then safe,
- but if a worker takes more than 30 seconds
- sigkill,
- worker dead,
- job lost.

### Same behavior

```text
docker stop
      ↓
sigterm
      ↓
wait
      ↓
sigkill
```

```text
delete pod
      ↓
sigterm
      ↓
wait
      ↓
sigkill
```

```text
systemctl stop relay
      ↓
sigterm
      ↓
wait
      ↓
sigkill
```

> relay worker works the same with signal.

---

## A SCENARIO FROM REAL SYSTEM
```text
ThoughtBot was using Unicorn (a Ruby application server) for a client project. During deployments:
They deployed new code
Unicorn spawned new worker processes with the new code
Unicorn sent SIGTERM to OLD worker processes
Old workers were supposed to finish current HTTP requests, then exit
BUT: The Unicorn master process had a timeout configured
- If an old worker didn't exit within the timeout, the master sent SIGKILL
Some requests were in the middle of database writes
SIGKILL killed the worker mid-write → database connections left in inconsistent state
- Result: Data corruption, 500 errors, customer impact
--> Root Cause :
The timeout was set too short for the actual request duration. The system was configured to be "impatient",
— it didn't give workers enough time to finish gracefully.

--> The Fix :
- Increase the graceful shutdown timeout to match the longest expected request
- Add request draining — stop sending new requests to old workers immediately
- Monitor graceful shutdown duration — alert if workers are frequently killed by timeout
- Make requests idempotent — if a request is retried after SIGKILL, it doesn't corrupt data


--> The exact same thing will happen to Relay's worker. If:
- Lease duration = 30s, terminationGracePeriodSeconds = 10s
- A job takes 20s to process
- Then K8s will SIGKILL the worker after 10s. The job is lost. The lease expires after 30s. The reaper finds it and retries.
- If the side effect (email) was sent before SIGKILL, the customer gets a duplicate email.
--> This is why idempotency is non-negotiable. Not a nice-to-have. A requirement.
```

---

# NOW

> when job lost/sigkill, dbstatus = running, no signal, so how is it recovered?

## THIS IS "LOST JOB PROBLEM"

#### Answer

- lease
- heartbeat
- reaper

### LEASE: 
- it's like a timer for each worker, lease stores the timer for each worker, if worker is still alive(not in deadlock or killed),
- then worker sends the signal so it can extend the timer to successfully complete the job it was doing.
- like giving temporary ownership to each worker until expiry, but if worker is alive it can extend the expiry to complete the work.

### HEARTBEAT:
- this is the way of worker sending signal to lease that its alive and extend its ownership.

### REAPER:
- this only finds expired/killed workers(job lost workers), it confirms if a worker is dead by expired lease, and recovers the job/retry job to another worker.

```text
worker A -> job#101 -> lease: 30 sec -> after 25 sec -> heartbeat: lease extend(alive) -> more 30 sec -> worker dies -> no more heartbeat : lease expires -> reaper detects expired lease -> job #101 recover/retry -> worker B can take it.
```

### (there are still some edge cases that cant guarantee job lost recovery in this architecture)

## File Descriptors :
- fd is a number/handle by os that represent any open resource.
- when relay opens connection with postgres/redis, os makes fd for that connection.
- relay -> postgres connection : fd 21, redis socket : fd 22, log/file : fd 23..
- fd is like an access card for resources connections.
- fd is limited : a process cant use unlimited resources(fd).
- also number of workers and pool size (connection limit) matters, f relay as 20 workers a pool size for each is 20 = so 20x20 = 400 connections open +   fd consumption.

- so scaling doesn't mean : more workers or more connections per worker.
- connection lifecycle management is important, else fd leak, relay failures.
```text
flow : DB connection -> TCP socket -> FD
```

## TCP SOCKET :
- when sQlalchemy needs connection with PostgreSQL:
- relay : make connection with PostgreSQL -> os creates socket -> socket gets FD; eg: fd 21 -> now TCP connection establish(makes actual connection b/w them) -> now relay can send sQl to postgres DB and PostgreSQL can send response -> when connection closes: socket/FD releases.
```text
- python - sQlalchemy - TCP Socket - FD - OS - Network - PostgreSQL.
```
```text
SOCKET: communication point
TCP: rules that transfer data reliably.
OS gives FD to relay to access the socket.
```

### CONNECTION POOL INTERNALS:
-> without connection pool : job -> new tcp connection each time -> postgres -> connection close.
- this is expensive to create 1000 connections create/close.

- each time to create connection : socket create - TCP connection establish - resource connection.

- keep some connections ready and reuse it :
```text
connection pool : C1, C2, C3 -> PostgreSQL.

so if relay needs db work - job - pool connection - got c1 - Query run - return connection pool.

if pool_size = 4, 4 jobs has all connections, then incoming job will wait till one connection gets free.

-> many jobs -> limited conn pool -> db.
```

### POOL EXHAUSTION:
- pool_size = 3 reusable connections.
- 3 jobs took 3 connections.
- now what if 97 jobs are waiting = pool exhaustion.
- this seems relay/postgres/network is slow but in real connection is not available.
```text
- if process takes much time/stuck - connection doesn't return -> pool fills - exhaustion - new job wait/fail.
```
### POOL CONFIGURATION :
- *increasing pool size != better*.
- 100 relay workers x pool_size = 50 = 5000 DB connections = PostgreSQL cant handle them.

#### 1. pool size :
how many reusable connections to put in the pool.

#### 2. max overflow :
if heavy traffic, then extra temporary connection allowed.
eg: poolsize = 5, max_overflow = 3, heavy traffic : 5 + 3 = 8 max connections.

#### 3. pool_timeout :
max time to wait if connection is not free. eg: pool_timeout = 5,
-job - pool - no conn - 5 sec wait - timeout error.

#### 4. pool_recycle :
using same connection for longer time can mean the connection is broken, so set how much a connection can get old. replaces old connections.


### FAST FAILURE :
- in pool_timeout : wait x seconds, got conn? yes : continue | no : error.

instead blocking 30 sec and waiting more process, let say pool_timeout = 1 :
```text
- 100 jobs - 1 sec wait - no conn - fail/retry mechanism(fast failure).
```
fast failure doesn't make system healthy but prevents unnecessary wait for unavailable resource.

- this doesn't mean everytime pool_timeout = 1, in default if conn takes 2-3 sec, 1 sec wait makes unnecessary failures.
```text
- so this can be decided seeing matrics : pool utilization? pool timeout errors? etc
- if 99% request, connection takes 100ms, then pool_timeout = 1
- if normally 2 sec conn time occasionally 5 sec, then put timeout=30 is okay.
```


### CONNECTION LEAKS :
- when process took connection, but didnt return properly.
```text
- eg : pool -> C1,C2,C3,C4,C5
     : job -> C1 -> (bug)didnt return to pool (conn leak)
```
- now pool has 4 conn only, if bug repeats -> empty pool : no conn.

#### "SILENT KILLER" : this conn leak happened at 1 conn leak, then gradually increased later - pool exhausted.

this makes postgres/relay slow in reality connections were lost.

##### GROUND TRUTH : for this postgresQl has built in view - "pg_stat_activity" where we can see how many conn, how many conn active, Query, whos idle, time Query/conn running.

## common code mistakes - make conn leaks :
```text
1. conn = pool.acQuire()
   await conn.execute(..)
   // didnt do : conn.release()

2. conn = pool.acQuire()
   await conn.execute("..") // exeception
   conn.release() // before release

3. conn.pool.aQuire()
   if something_wrong: return
   // conn dont return !
   conn.release()

4. conn = await acQuire()
   await long_operation()
   await release()
// acQuire() - long operation - task cancelled - release skipped = conn leak.
```
## Bad pattern:
```text
DB connection acquire
 ↓
DB query
 ↓
OpenAI API call — 20 sec
 ↓
some processing
 ↓
DB update
 ↓
release
```
- unnecessary conn hold for too long.

## Better conceptual flow:
```text
DB connection
 ↓
DB work
 ↓
release

OpenAI call
 ↓
DB connection
 ↓
DB work
 ↓
release
```

## REAL INCIDENT : 
- 100 jobs -> conn pool = 10 -> 10 conn busy -> 90 job waiting -> db timeout.

- db slow/issue - wrong
- application couldn't take db conn

### so there must be some of these reason when application/db feels slow :
```text
Slow query
OR
Pool too small
OR
Connections leaked
OR
Connections unnecessarily held
OR
DB genuinely overloaded
```
### so we trust truth : application pool matrics + pg_stat_activity + query latency + root cause.
