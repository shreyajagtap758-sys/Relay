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
```text 
Whichever is smallest breaks first. This matters for Relay later: if I run 10 workers each with pool_size=20, that is 200 connections against a max_connections of 100. The pool would think everything is fine, and Postgres would refuse new connections with a completely different error: FATAL: sorry, too many clients already. Different layer, different error, different fix. So capacity planning means keeping workers × pool_size below max_connections.
```

---

## TCP DEEP DOWN:
### TCP 3-WAY HANDSHAKE:
- a PostgreSQL conn is basically TCP conn.
- "await engine.connect()" -> establish tcp conn to PostgreSQL.
- tcp establishes an agreement (confirmation) before application data starts flowing.
- as tcp is two-way, it needs to take agreement from both sides.
```text 
- relay          postgresQl
   |       SYN  ->       |

   |   <-  SYN+ACK       |

   |       ACK   ->      |

       Connection Ready
```
-> SYN : "i want to establish TCP conn"

-> SYN-ACK : "i received reQ, i am willing to establish the conn"

-> ACK : "received response"

- NOW tcp considers the conn established.

- db conn is not free, and without pooling , every job does :
```text
create TCP CONN, 3 way handshake, talk to postgres, finish job, close conn.
```
-repreatedly paying conn-establish cost = expensive.
- so, as conn pooling has multiple conn open and can be reused, tcp handshake only happens when conn established, and every job uses it.

### 1 RTT(round trip time):
- how long it takes for a message to travel from relay -> postgres and response to come back.

- eg = relaye to postgres = 10ms, postgres to relay = 10ms => RRT = 20ms.

- a system creating 100 connections would take much RTT(under load), so thats why creating new tcp establish, new postgres conn setup etc would cost much, instead use pooling for every reQuest.

-> so, if pool_size = 2, only 2 conn exist in cool and 10 reQ, only 2 job work and 8 waits, then why not simply create more connections? -> creating conn itself has cost.
```text 
too few conn
-> reQuests wait

too many conn
-> conn establish, db, os/network resources increase.
```
#### "the more != the better"
- this was when tcp establishes the connection, what about when closing it?

### TCP CONN TEARDOWN:
- conn is not just "closed/deleted" after the work is over.
- when conn is closed, its 4-step teardown :
```text 
RELAY          POSTGRESQL
  |      FIN ->      | "no more data sending"

  |      <- ACK      | "got the message"


  |       <- FIN     | "postgres is also done, no data sending"

  |        ACK ->    | "got it"

   CONN GRACEFULLY CLOSED
```

### TIME-WAIT:
- after conn close, tcp immediately dont forget everything, instead it stays into time-wait state temporarily.
```text 
- ACTIVE CONN - FIN/ACK - CONN CLOSED - TIME-WAIT~60 sec - wait - FULLY GONE.
```
- ensures that any delayed or stray packets from a closed connection safely expire in the network.

### WHY NEED TIME-WAIT?
- suppose a conn is established and relay sent data, but network delayed that packet(data), meanwhile conn got closed. 
- now the old/delayed packet can show up and interfere a newly opened connection sharing exact same source and address pair. 
- without handling this : if new conn has same ip address and port, it may use these old packets, causing data corruption and application-level error.

### PREVENTATION:
- so old connections are not removed immediately, instead its identity stays in time-wait so no conn with same resource/port/identity is created, 
- so old delayed packets gets disappeared from network, and new conn flow is safe(safe reuse).

#### this is network correctness/safety mechanism.


### EPHEMERAL PORT : when relay makes tcp conn with postgres, relay side gets temporary source port(ephemeral port) by os.

- if pool dont exist : 100 req, new tcp connections, close, 100 time-wait.
- so pool is essential.

- if 10 req and pool_size = 100 for future traffic then it costs much more : 100 tcp conn, 100 sockets, 100 FD, postgres resources.

- as pool keeps connections alive for reuse, TCP conn is not closed.
- these connections are not alive forever : it can be closed when : application shutdown, pool disposal, conn invalidation, database/network failures.

#### FIX: use conn pooling, no time-wait.
```text
so normal conn flow: job - use existing conn - query - return to pool.

when conn close: pool shutdown/conn invalide - TCP teardown - TIME-WAIT - temporary network-resource occupancy etc
```
#### so conn management affects : application, TCP, os resources/sockets/FD, network, postgres


### TCP RETRANSMISSION:
- if packet sent by relay gets lost in the network:
```text
relay : packet sent, wait for ack
postgres : no data received, no ack
```
- relay didn't get expected response/ACK back from postgres

#### TCP dont immediately starts packet resend, it wait as network/packet delayed, so tcp uses a timer : RTO(RETRANSMISSION TIMEOUT).

- RTO = 200 ms. so relay sends data - wait 200 ms - no ACK - RETRANSMIT.

-> what if second packet also gets lost : retry immediately, retry immediately, retry... packet resending makes more congestion instead solving.

- this sequence needs *Exponential backoff* (attempt 1 : wait 200ms - lost, attempt 2 : wait 400ms - lost, attempt 3 : wait 800ms - lost...)

- if network packet temporarily lost/delayed # TCP INTERNALLY HANDLES THIS(not application) and wait/retramists if needed.

-> BUT, when network completely dead : retry, retry, retry... timeout
- now application has "no response", so application-level timeouts are important too.
```text
- TCP RETRY : packet retransmit/backoff(packet lost : wait 200ms, 400, 800...)
- APPLICATION RETRY : try:
                  await db.execute(...)
                      except:
                  await db.execute(...), backoff(job failed : wait 1s, retry job, wait 2s, retry...)
```

### RETRIES CAREFULLY DESIGN:
```text
when relay -> PostgreSQL
"update job set status='done'" ->
PostgreSQL executes it ->
response gets lost ->
relay sees timeout
```
- relay thinks operation failed while database has operation succeeded, relay cant blindly retry job(duplicate side effect), so retry must be carefully designed.

### responsibilities:
```text
TCP : make communication reliable, packet lost - retransmission.

CONNECTION POOL : manage/reuse connection, conn invalid - pool must discard/replace it.
```

-> lets say packet sent at t=0s

-> now its t=1s
possible:
- response late, traveling network
- packet lost
- PostgreSQL slow/dead
- network path broken

-> application only says : no response yet

### so we need read timeout:
- eg : read timeout = 30 sec
- 0s -> reQ sent -> wait -> 10s -> wait -> ..30s -> timeout.

- now application makes decision : response time limit cross. this cant identify the actual cause.

### timeout != operation definitely failed.

```text
Situation        	       Actual reality	                      Application sees
 ------                          --------                               ----------------
Slow network	           packets eventually arrive                  	response late
Temporary packet loss        	TCP retries	                               delay
Slow PostgreSQL              	DB takes time	                        response late
Dead network	              packets never arrive	                     no response
Dead PostgreSQL                  no response	                         no response
```

-> when slow : read timeout decides how much to wait.
- timeout too long : system waits more
- timeout too short: slow operations gets killed.

```text
Relay
  │
  │ ① Connect timeout
  ↓
PostgreSQL
  │
  │ ② Read timeout
  ↓
Relay
```
#### Connect timeout(postgres unreachable/wrong host/network route broken) : MAX WAIT TO ESTABLISH TCP CONNECTION. if 5-10 sec and conn didn't establish : ConnectTimeout. this should be kept short.

#### Read timeout(query waiting for lock/db overloaded/query expensive) : MAX WAIT TO RECEIVE RESPONSE/DATA TO RELAY. when connection and query is sent but response is taking time. this should be kept longer.

---

## TRANSACTION:
```text
Client -> API -> Postgres -> jobs table(job_id, status) -> worker.

worker's work : find job, claim job, status update = running, work, status=complete.
```
#### transaction : database operation logical unit where database works in a controlled operation.
```text
BEGIN -> DATABASE OPERATION -> COMMIT

BEGIN -> status=running -> something fails -> ROLLBACK -> status=queue
```

### CONCURRENT TRANSACTION : 
- job 101 = queue

-> worker A sees job 101 is queue.
-> worker B sees same job queue.

- both BEGIN -> read job 101 -> take it

- we need to handle concurrency and race conditions even though transaction exist.

### TYPE OF PROBLEMS :

### assume :
```text
jobs table
----------
id    status
101   queue
102   queue
```

### DIRTY READ (read uncommitted data of other transaction) :
- worker A BEGIN -> update jobs, set status = 'running', where id = 101;

- worker A didn't commit anything yet.

- worker B sees status = running for job 101.

-> now worker A got problem -> rollback, now job 101 = queue.
- while worker B saw status 'running'.

-thats dirty read (reading uncommitted changes)

### NON-REPEATABLE READ (different outputs in the same transaction) :
- worker A begin(transaction), select status from jobs where id = 101; 
- it shows = queue(first read).

-> meanwhile B : update jobs, set status = 'running' where id = 101, commit;

- now in same transaction of worker A now status shows = 'running'(second read), while it showed 'queue' before in the same transaction.

### PHANTOM READ (different rows(new/deleted) appear in same transaction) :

-> lets say job 101 = queue and job 102 = running.

- worker A -> BEGIN, select * from jobs where status = 'queue'.
- worker A gets job 101.

-> while worker B has job 102 which is running, it inserts a row : insert into jobs(id, status) values (103, 'queue'), COMMIT.

- in same transaction of worker A, now if it executes same query status = 'queue' -> this gives 101, 103, while it showed only 101 before.

### WRITE SKEW :
-> IMAGINE relay has business rule : at least one worker must remain available.
```text
database : workerA = available, workerB = available.
```
- now transaction A reads both workerA AND B available, so it occupies workerA
- simultaneously transaction B reads both available and occupies worker
```text
now database : workerA = UNAVAILABLE, worker = UNAVAILABLE.
```
### This is write skew.

## ISOLATION (four levels):
### how much one transaction has visibility of activity of another concurrent transaction?

### READ UNCOMMITTED :
-> this is the weakest isolation property, when one transaction can read another transaction's uncommitted changes. how it works:

- worker A transaction -> update row 1 (not committed)

- worker B transaction -> reads updated row 1(read uncommitted)

#### RISK : dirty read, non-repeatable, phantom, write skew problems.


### READ COMMITTED : 
-> this is default isolation level for postgres.
- dont read uncommitted changes of another transactions, only read the committed data.

#### RISK : non-repeatable, phantom, write skew problems.


### REPEATABLE READ :
-  if a transaction reads a row once, it will see the exact same values if it reads that row again later in the same transaction. Even if other concurrent transactions modify and commit changes to that row in the meantime, those changes remain completely invisible to the current transaction.
-> prevents data from changing mid-transaction by taking a snapshot (at the transaction beginning) of data or holding locks on read rows.

#### RISK : write skew problems


### SERIALIZABLE :
-> this is the strongest isolation level with no dirty read, non-repeatable, phantom, write skew problems.
-> completely isolates transactions from each other, even though they work simultaneously. done by database itself.

- transactions a and b run concurrently, unblocked. A finishes work and COMMIT. B also calls COMMIT, database identifies transaction B's write overlaps with transaction A read, so it aborts transaction B (serialization failure error), so application must catch this error and must RETRY.
```text
B
 ↓
SerializationError
 ↓
ROLLBACK
 ↓
WAIT briefly
 ↓
retry
 ↓
read latest data
 ↓
make decision again
```
### "concurrent transaction final result should be safe"

### trade offs : 
- transactions frequently wait for others to finish : blocking and high latency.
- transaction failures/deadlocks/must have retry mechanism.

```text
Level                  	Dirty Read        	Non-Repeatable     Read	Phantom     	Write Skew
READ UNCOMMITTED	       ✅	           ✅	            ✅                  ✅
READ COMMITTED	               ❌                  ✅	            ✅                 	✅
REPEATABLE READ	               ❌	            ❌	            ❌                 	✅
SERIALIZABLE	               ❌                  ❌	            ❌	                ❌
```

### MVCC (MULTI-VERSION CONCURRENCY CONTROL) :
- if database locks each rows for workers, many workers waits(unnecessarily blocking) which can congest and take longer time.

-> instead locking normal reads unnecessarily, maintain versions of the data and show the visible version to each transaction according to its snapshot(multi-version).

- suppose job 101 status = queue.
- worker A starts transaction -> snapshot -> updates status = running.
- now job 101 --> version1 : queue, version2 : running.
- worker B can still read version 1 = queue in its snapshot.
- so worker A sees the same snapshot it was working on, no other updates from other transactions.

-> both read and write operations are unblocking.

### WHAT MVCC COSTS? :
- postgres doesn't immediately remove old row-versions until active transaction needs it.
#### BLOAT : 
- creating multiple updated old versions and it dont die/clean then higher database storage, high table bloat, less performance.
- this can be solved by 'VACUUM' in postgres.

#### MVCC CLAIMS 'CONCURRENT TRANSACTION GETS WHAT VERSION OF DATA', IT DOES NOT CLAIM 'IF TWO WORKERS WANTS TO CLAIM THE SAME JOB, WHICH ONE WILL GET IT'.

#### MVCC ≠ "only one worker can modify this row"

- thats why we need explicit locking :

-> IF TWO WORKERS WANTS TO CLAIM THE SAME JOB :

### LOST UPDATE (change silently overwritten) :
```text
- worker A : x + y
 UPDATE attempt = 1

- worker B : x + y (same, concurrently)
 UPDATE attempt = 1

FINAL ATTEMPTS = 1
EXPECTED = 2
```
-> error didn't show up, but first transaction update silently got overwritten by second transaction - silently wrong data while database shows success.


### FOR UPDATE - LOCKING :
- to avoid duplicate work/lost update/business-rule violation(write skew), we use temporary lock row.

- worker A takes job 101 -> temporary lock till transaction completion, no other worker can update/lock this row. other transaction waits till lock release.
```text
so worker 1 has job 101
   worker 2 waits for lock release
   worker 3 waits...
```
-> BUT THIS CAN BE INEFFICIENT BECAUSE WORKER 1,2,3,4.. ALL WANTS JOB 101 WHILE JOB 102,103.. ARE FREE.

### FOR UPDATE SKIP LOCK :
-> finds Queue jobs that are free and lock them while skipping jobs that are already locked by other transactions.
```text
so worker 1 has job 101
   worker 2 has job 102 (skip 101)
   worker 3 has job 103 (skip 101, 102)
```
```text
BEGIN
 ↓
claim job
 ↓
mark running
 ↓
COMMIT
 ↓
lock released
 ↓
process job
```

#### SO NOW, even if worker A skip locked and worker dead mid-way, lease-reaper-heartbeat handles this.

---

# ingestion API setup (post/get)

```text
HTTP STATUS CODES :

       Client                        Relay API Server                  Postgres DB
         |                                  |                               |
         | --- POST /jobs (Create Job) ---> |                               |
         |                                  | --- INSERT INTO jobs ... ---> |
         |                                  | <--- COMMIT Confirmed ------- |
         | <--- 202 Accepted -------------- |                               |
 (Job queued, execution deferred)
```

## 200 OK :
-> REQUEST SUCCESSFULLY processed, and requested operation is fully finished with sync execution.

- use for synchronous operations. eg : GET/users/42 or POST/calcie/add_operation. 

## CONTRACT VIOLATION :
- for the reQuest, a job does this : 
```text
Client
  |
  | POST /jobs
  ↓
Relay API
  |
  | validate
  | create job
  | enqueue job
  ↓
Queue
  |
  | then
  ↓
Worker
  |
  | execute
  ↓
Email sent
```

- API only did job accept + enqueue, actual execution is done by worker.

-> now 200 can be problematic :
```text
- server actual state : request received - validated - job created - job enqueued - waiting for worker

- while client gets : request received - job executed(assume) - DONE.
```
- this is mismatch, in real the worker never did the job while client sees 200 ok(confirmed/successfully processed job).

-> Eg : POST/jobs : client request(send email)
- backend : API - create email job - push to redis - return response(200).
- in redis : job_123, status=queued.
- worker didn't touch the job yet, while API returned 200 ok.
- client may assume - email successfully sent. (not sent yet)
- worker may fail later, email never sent, but claimed 200 ok.

### SO WHAT FITS HERE? 
- 202 ACCEPTED(req accepted for processing, but processing isn't complete).
```text
Client
  ↓
POST /jobs
  ↓
Relay accepts request
  ↓
Job created
  ↓
Job queued
  ↓
202 Accepted
```
- request accepted - yes
- job completed - NO


## 201 CREATED :
- client : POST/users/{id} (create user acct)
```text
request - validate user data - INSERT INTO users - user created - 201 Created.
```
- 201 Created -> New resource exists.
- this doesn't mean - job execution completed.(job status = pending still).


## 202 ACCEPTED :
- use for async tasks.
- Accepted job is never lost : this ensures job is safe even though execution is not started yet, job_id status poll is given, track you job status.


# 'ACCEPTED' PROBLEM :
## MEMORY FIRST, DB LATER :
- suppose relay receives job from client :
```text
client - FastAPI - memory Queue - 202 ACCEPTED - later-> PostgreSQL
```
-> problem : client got 202, job is stored in RAM - API crash - RAM CLEAR - job lost.
```text
client - fastapi - memeory Queue - 202 accepted(client assumed request accepted done, now job wont lose) - before entering db, API CRASH - job lost
```
- while client got wrong information.
- RULE #1 : ACCEPTED JOB NEVER LOSE - broken.

-> MEMORY - 202 - DB INSERT

DB COMMIT FIRST :
```text
client - FASTAPI - POSTGRESQL INSERT - commit - 202 accepted - worker later picks this job.
```
- client got 202 when job is safely persisted in DB (no job lost) even when API crash.

-> DB - COMMIT - 202

### DB COMMIT FIRST IS SAFER , BUT LATENCY DIFFERENCE IS HIGH :

```text
Metric	Memory-First (Option A)	DB-Commit-First (Option B)
Enqueue Latency	~2-5 ms	~20-50 ms
Crash Safety	❌ Data Loss Risk	✅ Zero Data Loss
Durability Level	Volatile (In-Memory)	Non-Volatile (ACID Committed)
Relay Contract Compliance	❌ Violates Rule #1	✅ Strictly Satisfies Rule #1
```

### SO - relay chooses persist safely, then accept(DB FIRST COMMIT) - core is to ensure durability, not minimize enqueue latency only(durability costs latency).

```text
Verification Tests — Final Summary :

Test                              	Kya test kiya?	                                                    Success ka meaning
1. POST /jobs — Valid Enqueue.	    Valid job request accept + DB mein save ho rahi hai ya nahi.    	Job successfully create/persist hui
2. GET /jobs/{id} — Status Query.	Existing job ko ID se retrieve kar sakte hain ya nahi.	            Job lookup/status endpoint working hai
3. GET /jobs/{invalid-id}—Not Found.	Non-existing job ko correctly handle kar raha hai ya nahi.  	404 error handling correct hai; API fake data return nahi karti
4. POST /jobs — Invalid Body.    	Input validation properly reject kar rahi hai ya nahi.             	Pydantic validation working hai; invalid request DB tak nahi jaati
5. Durability / Crash Test       	API restart ke baad committed job survive karti hai ya nahi      	Data API process ki memory mein nahi, PostgreSQL mein durably persisted hai
```

---

# WORKER 3 STEP LIFECYCLE :
```text
CLAIM  -->  EXECUTE -->  MARK
```

## CLAIM : 
- find oldest Queue job(pending), lock it so no other worker takes it, make status 'pending -> running' mark, and commit transaction.

-> RULE : whole work must be in one atomic transaction.


## EXECUTE :
- execute business logic of job(eg: image resize, email send).

-> RULE : while executing, NO database transaction should be opened.


## MARK :
- after execution finishes, save job's final outcome in database.

-> successfully work done : 
- status = 'succeeded'
- else status = 'failed'

-> RULE : this update must commit in a fresh, independent database transaction.


## THREE CRITICAL CONCURRENCY TRAPS :

### TRAP 1 :
-> WHY CLAIM QUERY MUST BE IN "ONE" TRANSACTION ?

- worker must "see" job and "claim" it in one db transaction, else 2 workers can 'see' same job and execute same.

- problem : db has job 101 = pending
- two workers : 1 and 2

-> (two separate transactions) :
```text
transaction 1(only SELECT) :

SELECT id
FROM jobs
WHERE status = 'pending'
LIMIT 1;
```
- worker 1 and 2 does same query, and both gets job 101, then both :
```text
transaction 2(UPDATE) :

Worker A:
UPDATE jobs SET status = 'running' WHERE id = 101;

Worker B:
UPDATE jobs SET status = 'running' WHERE id = 101;
```
-> PROBLEM : 'UPDATE' statement didn't decide which worker's job it is.

-> duplicate execution, LOST UPDATE.

#### CORRECT APPROACH :
-> start transaction :
```text
BEGIN;
SELECT id
FROM jobs
WHERE status = 'pending'
ORDER BY created_at ASC
LIMIT 1
FOR UPDATE;
```
-> so worker 1 got job 101, does FOR UPDATE : worker 1 is claiming this job, other worker wait for this row.

```text
Worker A
   ↓
SELECT ... FOR UPDATE
   ↓
Job 101 LOCKED 🔒
```

-> IMMEDIATELY in the same transaction :
```text
UPDATE jobs
SET status = 'running'
WHERE id = 101;
COMMIT;
```
- now, job 101 - running, then lock - released.

```text
FLOW : 
worker 1 took job (SELECT FOR UPDATE)

worker 2 does same, but job 101 locked, so waits.

worker 1 UPDATE STATUS = RUNNING
COMMIT (lock released)

worker 2 ready to take job as lock releases, but sees status = running, so doesn't execute it.(no duplication running)
```

- so when in two transaction (select COMMIT then UPDATE set running), two worker may do update the same job = running as lock is released in middle, so this must be in one transaction.


### TRAP 2 :
 -> CLAIM AND EXECUTE - WHY IN DIFFERENT TRANSACTIONS ?

```text
-> WRONG (Anti-Pattern):
[ BEGIN -> SELECT FOR UPDATE -> UPDATE running ---- EXECUTE (2-10 sec sleep) ----> COMMIT ]
  ^                                                 ^
  |                                                 |
  Tx Starts                                         Holding locks! DB connection busy!
                                                    State = "idle in transaction"



-> CORRECT:
[ BEGIN -> SELECT FOR UPDATE -> UPDATE running -> COMMIT ] ---- [ EXECUTE (No Trans) ] ---- [ BEGIN -> UPDATE succeeded -> COMMIT ]
```

#### PROBLEM IF COMBINED :
- PERSPECTIVE OF POSTGRES : worker opened transaction, did lock, now its doing nothing(idle in transaction). meanwhile its executing python code(business logic), for which postgres connection status becomes : idle in transaction.

- job didn't release the lock even though its not working on that row, so no other process/worker can touch that row till lock release.

- worker's db connections stays occupied in connection pool even though its not working on db, so other workers or API connections starves.

- lock is released while worker is executing(job=running), but worker may die/crash in this state, now db doesn't know this and job stays 'running' forever, thats why we have : lease - reaper - heartbeat architecture.


### TRAP 3 :
 -> ORDER BY + LIMIT 1 + FOR UPDATE - SUBTLE INTERACTION :

- THE QUERY:
```text
SELECT * FROM jobs 
WHERE status = 'pending' 
ORDER BY created_at ASC 
LIMIT 1 
FOR UPDATE;
```

---> subtlety(without SKIP LOCKED what happens?) :

-> when multiple workers concurrently runs this query :
- two workers scan table and finds same(oldest pending job 1).
- worker 1 does FOR UPDATE lock on that job.
- worker 2 does same query, postgres query planner first executes ORDER BY and LIMIT 1 and selects row 1, and tries taking lock on that row.
- it sees row 1 is already locked by other worker, so worker 2 BLOCK(freezes).
- even if queue had 100 other pending jobs, worker 2 is next available only for this job(waits till worker 1 commits).


## SEPARATE PROCESS AND FAILURE DOMAINS :

-> why worker is a completely separate process(relay/worker) :

- In relay architecture, API and Worker are two different OS processes.

```text
[ OS Process 1: FastAPI API ]  <--- (Independent Failure Domain)
         |
    (Writes to DB)
         |
         v
    [ Postgres ]
         ^
         |
    (Reads from DB)
         |
[ OS Process 2: Worker Loop ]  <--- (Independent Failure Domain)
```

## FAILURE DOMAIN ISOLATION :
- if a bad job does C-extension segfault or MEMORY LEAK(OOM) in payload worker, so only worker process dies. API process is alive to take/accept new jobs.
- if API process crashes on traffic spike, worker process continues executing existing jobs in background.

```text
WORKER LOOP LIFECYCLE :

         +---------------------------------------+
         |                                       |
         v                                       |
[ Start Loop ] ---> [ Claim Next Job (Tx 1) ]    |
                           |                     |
                  Job mila?|                     |
                 /         \                     |
             (YES)         (NO)                  |
              /               \                  |
    [ Execute Handler ]   [ Sleep (Poll Interval)]
            |                     |
    [ Mark Status (Tx 2)]         |
            |                     |
            +---------------------+
```

- when job is not found and queue is empty, worker should not burn CPU(busy-looping). worker does : sleep(poll_interval), no worker available -> sleep.

-> busy looping : worker continuously checking for available jobs. CPU high usage and unnecessary DB queries.

---> TRADE-OFF for sleep/polling :
- worker : sleep(2 sec)
- just after sleep starts, job arrives.
- after worker's 2 sec sleep, if executes job, job waited 2 sec extra.
- job-start latency.

> so sleep/polling costs latency.


### pg_stat_activity state(transaction hygiene monitoring) :
- state='active' : when worker is claiming or marking.
- when worker in 2-sec sleep/polling : connection pool state : idle (transaction closed)
- while execution if state = 'idle in transaction', then transaction is open and locks are holding(trap 2 failure).

---

### PHASE 1 : 

## scenario : 
```
jobs table

id : 1, 2 , 3
status : pending, pending, pending
```
- we have two worker A AND B : both arrives at approximately the same time.

- two workers competing for same pending row creates database concurrency problem.
- so we learn for update VS for update skip locked under that concurrency.


### why isn't job.status enough? 

- id : 1
status : succeeded

- job 1 executed successfully, but cant say job 1 executed exactly once.
````
this may happen :

Worker A
    ↓
executes Job 1
    ↓
Worker B
    ↓
also executes Job 1
    ↓
both eventually mark it succeeded
````

-> job 1 = succeeded, looks perfectly normal.

> so, everything must be measured/observed, else it doesn't exist.

- so in experiments : we should execute job once, not concurrently/multiple times.

-> we have table job_execution : what happened during execution.
````
job_executions

101 | worker-A | 10:00
101 | worker-B | 10:05
````

-> so job is inserted in job_execution table after claim and before execution.


-> if this happens:
````
claim
  ↓
execution record committed
  ↓
handler starts
  ↓
💥 worker crashes
````

you would still have:

job_executions
→ execution attempt recorded

- even though the job might remain running.

- That is useful information. It means job_executions is recording an execution attempt, not merely successful completion.

- That's exactly what we want for the failure/concurrency experiments.


-> we have : with_for_update() meaning FOR UPDATE : so when worker A does this query(row level lock), other worker waits for the lock release.
- worker b waits for this job until lock release even if theres 100 other jobs pending.

- thats wasteful, so we use skip locked, so worker b doesnt wait for the same job and start executing other pending jobs.

#### prediction 1 : when two workers run FOR UPDATE at the same time, will both workers execute same job or one worker blocks?
=> one worker claims while other waits/block, no concurrently execution.

#### prediction 2 : worker a locks job, and worker b wait for that job, now what will worker b do after lock is released(job is now succeeded), will it execute job? or move on to find another pending job?
=> it will again do status='pending' for that job, but it is succeeded, so it continues/return no job and poll again.

#### prediction 3 : we go from FOR UPDATE to FOR UPDATE SKIP LOCKED, what will happen when two job need same job?
=> worker b doesn't wait, it finds other pending jobs. 

#### prediction 4 : with 10 jobs, 2 workers, FOR UPDATE -> what will be duplicate execution ? total runtime ? worker blocking ?
=> duplicates : 0, runtime : higher because of waiting, blocking : yes, both contend for the same locked row.

#### and with SKIP LOCKED ? duplicate execution ? total runtime ? worker blocking ?
=> duplicates : 0, runtime : lower. blocking : no.


## PREDICTIONS : 
## p1 :
-> if worker gets kill -9 in mid execution, what status will it get?
- MY GUESS => status='running' forever.

## p2 :
-> how much time will it take to recover?
- MY GUESS => we need exclusive retry logic for this(reaper,lease,heartbeat), other wise, job stuck forever.

## p3 :
-> SIGTERM sent, whats different than kill -9?
- MY GUESS => sigterm is basically saying worker to stop, but we can use gradual steps(complete mid execution first, then stop) in our code.

## p4 :
-> 20 jobs, 3 workers, in middle one worker gets kill -9, now how many jobs will be stuck forever?
- MY GUESS => as one worker got kill -9, idk if one worker gets kill -9 or after kill -9 every worker stops its work, but if one worker gets it, maybe other worker dont care, one job will be lost.

## p5 :
-> in job_executions table, will that stuck job does entry in the table?
- MY GUESS => as job is inserted in job_execution table after CLAIM and before COMMIT(during execution), maybe it will have entry, but just lock was released from claim and something crashes before entry in table, maybe no entry then.


## EXPERIMENT 1 : do kill-9 mid-job.

- I expanded job handler time to 10 sec, start worker, and did kill -9 <worker_id> in mid execution.

- when i immediately after search for job status=running : it showed the killed job

- when i saw status of all jobs after some minutes :killed job = running still.

-> does new worker picks that pending job that was died? => NO, status is not pending anymore for that job so no-one can pick it.


## EXPERIMENT 2 :

- enqueue 20 jobs, and run 3 workers concurrently. give kill -9 to one worker, let others complete their work.
- how many jobs are stuck in running ?
````
- Seeded 20 jobs (sleep): IDs [1..20]
// made 20 jobs.

- python -m relay.worker
// in three diff terminals, made three workers and noted one of the worker's id.

- after a worker claims job and starts executing, stop-process -id <worker_pid> -force (kill -9)
````

> OUTPUT :
````
id |  status   
----+-----------
  1 | running  -> killed
  2 | succeeded
  3 | succeeded
  4 | succeeded
  5 | succeeded
  6 | succeeded
  7 | succeeded
  8 | succeeded
  9 | succeeded
````
````
status   | count 
-----------+-------
 succeeded |     9
 pending   |    10 -> i didn't wait
 running   |     1 -> killed
(3 rows)
````
````
SIGTERM / Ctrl+C
      ↓
worker says "finishing current job"
      ↓
handler completes
      ↓
job = succeeded
      ↓
clean shutdown

- exit 0
````
> EXAMPLE TERMINAL : 
````
[worker-7420] Executing job 9 (type=sleep)...

[worker-7420] Signal SIGINT received. Finishing current job before shutdown...
[worker-7420] Finished execution for job 9.
2026-08-18 23:42:36,439 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-08-18 23:42:36,440 INFO sqlalchemy.engine.Engine UPDATE jobs SET status=$1::VARCHAR WHERE jobs.id = $2::BIGINT AND jobs.status = $3::VARCHAR
2026-08-18 23:42:36,440 INFO sqlalchemy.engine.Engine [cached since 80.3s ago] ('succeeded', 9, 'running')
[worker-7420] Marked job 9 as 'succeeded' (rowcount=1).
2026-08-18 23:42:36,443 INFO sqlalchemy.engine.Engine COMMIT
[worker-7420] Clean shutdown complete. Exiting with code 0.
````
````
Metric	                          kill -9	                                   SIGTERM
------------                  ------------------------------             -------------------------
Handler chala?	       Haan, agar kill execution ke beech hua tha   	Haan, current job finish hone diya gaya
Job complete hui?                     	Nahi	                              Haan
Final status	                      running                              	succeeded
running me atke jobs	      1 (jo killed worker ne claim ki)	                    0
Exit code	                   Non-zero / forcibly terminated	                   0
Recovery kisne kiya?	      Kisi ne nahi — job stuck reh gayi        	Worker itself — graceful shutdown ne current job finish ki
````

---

relay cant show or say how many workers are alive, reaper has two situations where it cant tell any difference :
1. worker crashed
2. worker is alive but slow/ can create duplicate execution.

reaper's decision is always a guess.

duplication is not a guard failure, this is a time-window result, this needs idempotency not guard.
- eg : worker A claims a job when its status is pending.
worker B claimed when job's status is pending(reaper expired and status back to pending).
- no GUARD was harmed.


if worker A claimed a job, and its slow so lease expires.
reaper does : running -> pending.
NOW worker b claims the same job and does pending -> running.
AT THE SAME MOMENT, worker A finally finishes and does status = running -> succeeded(guard matched because worker b picked and status= running while running -> success is valid).
now worker B is executing while worker A marked succeeded.

status only shows current state, doesn't really gurantee the concurrency.
Isliye running → pending → running cycle ke baad old Worker A ko new Worker B se distinguish karne ke liye Fencing Token chahiye.


why not just kill worker because in case of short lease expiry time we take authority of that job from the expired worker and assign to another, but that worker doesn't die, which can create duplication risk.

- why not kill? if its killed, we dont know how much that worker has completed the work, this creates new problem. second thing is reaper only owns job number, status and lease expiry, it doesn't know worker pid, what machine/container its in, process is alive or not etc.. so this is not the solution or can be done.

thats why we use lease renewal/heartbeat, fencing tokens(for duplications), idempotent handlers(limit duplication damage) etc.



LOG : 
before building HEARTBEAT : i tested what happened and how duplication worked :

Job ID = 22
Type   = slow
Lease  = 5 seconds
Slow handler = ~15 seconds


11:08:54.058  Worker B claims Job 22 → running
11:08:54.xxx  Worker B starts slow handler

11:08:55.878  Reaper reclaims Job 22 → pending ❌
11:08:56.638  Worker A claims SAME Job 22 → running
11:08:56.xxx  Worker A starts slow handler

               Worker A + Worker B BOTH executing Job 22

11:09:09.130  Worker B finishes first, tries succeeded → rowcount=1
11:09:11.724  Worker A finishes, tries succeeded → rowcount=0

result rowcount = 0 why? 
- we have compare-and-set guard :

UPDATE jobs
SET status = 'succeeded'
WHERE
    id = 22
    AND status = 'running'

so worker sees compare id = 22 and status = running then only set status succeeded, worker B set running, so worker A didn't harm any guard.

so rowcount = 0; meaning worker A tries succees but it already got success by worker B first so conflict on mark error -> rowcount = 1 means job successfully done.

job_id |  worker_id   |          executed_at          
--------+--------------+-------------------------------
     22 | worker-11040 | 2026-08-26 05:38:54.064126+00
     22 | worker-23088 | 2026-08-26 05:38:56.651132+00



NOW IMPLEMENT HEARTBEAT AND EXECUTE THE SAME :

Worker alive
    ↓
heartbeat every ~2 sec
    ↓
lease continuously extended
    ↓
reaper shouldn't reclaim it

- job = 23, lease = 5 sec, heartbeat = 2 sec

NORMAL SITUATION :

worker A:

11:42:03  Claimed Job 23
          status = running
          lease = 11:42:08

11:42:05  HEARTBEAT
          lease = 11:42:10(extend)

11:42:07  HEARTBEAT
          lease = 11:42:12

11:42:09  HEARTBEAT
          lease = 11:42:14

- heartbeat → lease extend → lease expiry future me


id |  status   |          claimed_at           |       lease_expires_at        |              now              
----+-----------+-------------------------------+-------------------------------+-------------------------------
 24 | succeeded | 2026-08-26 06:33:34.611379+00 | 2026-08-26 06:33:45.767051+00 | 2026-08-26 06:36:52.215766+00
(1 row)



DUPLICATION SITUATION :

WORKER A :

healthy sending heartbeats, but due to some cause :

Worker process crash ho gaya
Machine/container crash hua
Network/DB temporarily unavailable
Event loop block ho gaya
Heartbeat task itself fail/hang ho gaya
CPU/resource starvation

heartbeat missed, now if lease expires at that moment, reaper does status = running -> pending, while worker A is still executing, another worker can take it.


so Fencing token
   ↓
   old worker baad me wapas aaye to
   new worker ke against kuch modify na kar sake


also heartbeat updates must be before the lease expiry, or it will get expired until heartbeat arrives.

---

job queue lifecycle roughly :

pending
   │
   │ worker claims
   ▼
running
   │
   ├── success ──► succeeded
   │
   └── failure ──► retry wait
                       │
                       │ retry_at <= now()
                       ▼
                    pending
                       │
                       ▼
                     running

if after every failure, immediate status update pending, then :
10:00:00.000  Attempt 1 → fail
10:00:00.001  Attempt 2 → fail
10:00:00.002  Attempt 3 → fail

this is failure loop.

if external API/database/payment service is down, queue will load on that already-down system.

so we do failure -> wait -> retry mechanism. but fixed wait is not enough.

EXPONENTIAL BACKOFF :
- formula :

delay(n)=min(base×multiplier
(n−1)
,cap)

Recommended:

base       = 3 seconds
multiplier = 2
cap        = 12 seconds
max_attempts = 3

Ab ek-ek component samjho.

HERE :
- n = attempt number.
- so when attempt 1 = delay(1) = 3 x 2(1-1) = 3x1 => delay = 3 sec.

- attempt 2 = delay(2) = 3 x 2(2-1) = 3 x 2(1) => 6 sec.

- attempt 3 = delay(3) = 3 x 2(3-1) = 3 x 4 => 12 sec...

so everytime attempt increases, delay increases till its max_attempt, if max_attempt = 3, and when delay(4) comes, attempts(4) > maxattempts(3) => now dont delay, do dead_letter.


why base = 3 ?
- we have poll_interval = 2(worker checks for 2 every 2 sec).
- when job failed at 10:00, if retry delay <= poll interval, potentially timing behavior in retry has no meaningful spacing, so base > poll_interval.


- WHATS CAP :
if max retry is greater than 3 so => 

Attempt 1 → 3s
Attempt 2 → 6s
Attempt 3 → 12s
Attempt 4 → 24s
Attempt 5 → 48s
Attempt 6 → 96s
Attempt 7 → 192s (too much wait)
...

with cap :

Attempt 1 → 3s
Attempt 2 → 6s

Attempt 3 → 12s (cap = 12)

Attempt 4 → 12s (delay(4) = 24 sec, min(24, 12) = 12.

Attempt 5 → 12s
Attempt 6 → 12s (constant after a time)
...


JITTER :

exponential backoff is not enough alone, suppose we have 10,000 jobs calling external API :
- now external service down : 10,000 jobs fail synchronously, all retry after 3 sec, 6 sec...
- 10,000 jobs hit external API at same time, so external service collapses, this is retry storm.

so jitter formula :

actual_delay=delay/2 ​+ random(0,delay/2​).

for delay = 6s,

then 3 + random(0,3)

- so each job gets random delay :
Job A → 3.2 sec
Job B → 4.7 sec
Job C → 5.1 sec

- LOAD spreads.

instead of :
A B C D E
↓ ↓ ↓ ↓ ↓
ALL RETRY AT 6 SEC



this jitter gives random retry range.

half jitter/equal jitter :
formula : actual_delay=delay/2 ​+ random(0,delay/2​).

for delay = 6s,

then 3 + random(0,3)

- so we get 3s to 6s random range.
- but this gets monotinicity, not random :
3.2s
4.1s
5.4s
5.9s

also because full jitter could get = range(0,6), random could generate 0.5, meaning retry only took 0.5 sec which is too short as its random, to avoid this + for monotonicity, we use half jitter.

this gives half spreading.

full jitter :
- actual_delay=random(0,delay)

delay = 6s, then range(0,6) :
possible values for 5 jobs: 

A → 0.8s
B → 4.2s
C → 1.3s
D → 5.7s
E → 3.6s

very strong spreading, but delay might be too short.


TESTS :

1. single boom job retry chain :

- Ek failed job automatically retry hoti hai, har retry par backoff badhta hai, attempts track hote hain, aur maximum attempts ke baad job permanently failed ho jaati hai.

retry mechanism + exponential backoff + max_attempts guard ka test hai


worker A claimed job 
eg : job = 25, status = pending -> running, attempts = 0 (now 1)

attempt 1 executes : 
Executing job 25 (type=boom, attempt=1/3)...

FIRST FAILURE :
Job 25 failed attempt 1/3:
Simulated handler failure: BOOM!.
Scheduling retry in 1.59s
(new_status='pending').


handler failed : running -> failed.
worker decided 1 < 3, so retry.

RETRY WRITE :
Marked job 25 as 'pending' (rowcount=1).

next_attempt_at = now + 1.59s

SECOND CLAIM :
Claimed job 25 (attempt=2, rowcount=1)

FAILURE :
Job 25 failed attempt 2/3...
Scheduling retry in 3.58s

after third failure :
attempts = 3
max_attempts = 3


now no more retry, running->failed.

jitter difference :
Attempt 1
    ↓ ~1.99s
Attempt 2
    ↓ ~3.93s
Attempt 3

so this est : does retry work?


2. Jitter spread test :

When multiple jobs fail together, does jitter prevent them from continuing to retry together?

we have four jobs and they start together -> type = boom, so they will fail.

26 → 18:14:57.035
27 → 18:14:57.097
28 → 18:14:57.166
29 → 18:14:57.261

spread ≈ 0.226s

they are synchronized.

then in round 2, they started again together :

26 → +4.104s
27 → +4.248s
28 → +4.361s
29 → +4.473s

spread = 0.369s

now round 3 :

27 → +8.372898
29 → +8.443082
26 → +10.408285
28 → +10.449493

spread = 2.076595s => 2.08s

so now they are not sync group anymore, the spread increased. so instead one giant spike, load is distributed.

this test : does jitter spread retries

3. Real Bound Check :

can the retry system run forever?

query :

SELECT id, status, attempts
FROM jobs
WHERE id IN (26,27,28,29);

result :
26 | failed | 3
27 | failed | 3
28 | failed | 3
29 | failed | 3

so max_attempts = 3 was enforced.

Without a maximum-attempt guard, a permanently broken job can behave like:

fail
 ↓
retry
 ↓
fail
 ↓
retry
 ↓
fail
 ↓
retry
 ↓
 ∞


attempts < max_attempts
        ↓
       retry

attempts >= max_attempts
        ↓
      STOP


Test 1 — Retry Chain

A single boom job was executed three times. The first two failures transitioned the job from running back to pending using the guarded retry UPDATE with rowcount=1, while increasing the attempt count and scheduling a future retry. The third failure reached max_attempts=3, so the job transitioned to terminal failed. The observed inter-execution gaps increased consistently with the configured exponential backoff, with jitter and the 2-second polling interval affecting the exact wall-clock gaps.

Test 2 — Jitter

Four jobs were initially executed within approximately 226 ms of each other, showing that they started nearly synchronized. Subsequent retry executions became increasingly spread out, with the third round spanning approximately 2.08 seconds. This demonstrates that randomized jitter reduces retry synchronization and therefore mitigates thundering-herd behavior. The observed spread is evidence of desynchronization, not a guaranteed minimum spread.

Test 3 — Maximum Attempts

All four jobs ended with attempts=3 and status=failed, demonstrating that the retry loop is bounded by max_attempts and does not continue indefinitely.

---

JOB STATES :

pending
   ↓
running
   ↓
failure
   ↓
pending       ← retry possible
   ↓
running
   ↓
...
   ↓
max attempts reached
   ↓
dead_letter

dead letter means that job is now removed from retry cycle permanently.


TEST 1 :
Dead letter execution :
checks when job completes its maximum retry attempts and then goes into dead letter.


TERMINAL :

[worker-11256] Claimed job 31 (attempt=3, rowcount=1). Status is now 'running'.
[worker-11256] Executing job 31 (type=boom, attempt=3/3)...
[worker-11256] Job 31 reached max_attempts (3): Simulated handler failure: BOOM!. Marking terminal 'dead_letter'.
[worker-11256] Marked job 31 as 'dead_letter' (rowcount=1).

[worker-11256] Claimed job 30 (attempt=2, rowcount=1). Status is now 'running'.
[worker-11256] Job 30 failed attempt 2/3... Scheduling retry in 3.15s
[worker-11256] Claimed job 30 (attempt=3, rowcount=1)...
[worker-11256] Job 30 reached max_attempts (3): Simulated handler failure: BOOM!. Marking terminal 'dead_letter'.
[worker-11256] Marked job 30 as 'dead_letter' (rowcount=1).



TEST 2 :
Once job dead_letter ho gayi, kya koi worker ya reaper accidentally usko dobara touch kar sakta hai?

we have multiple writers as :

Worker:
pending → running

Reaper:
running → pending

Retry:
running → pending

now dead letter -> ??

TERMINAL :

select id, status, attempts from jobs where id in (30, 31);

//Dono jobs ka status dead_letter raha aur execution count freeze raha.

dead-letter job worker ke claim/retry path aur reaper ke recovery path dono se isolated hai.

Worker sirf eligible jobs ko claim karta hai, aur Reaper sirf stale running jobs ko recover karta hai. dead_letter dono ke scope se bahar hai.

Isliye accidentally same job dobara execute nahi hoti.


TEST 3 :

check if a worker is executing a long-running job and it gets shutdown signal mid job, then whats the behaviour of curr job, lease and heartbeat?

Enqueued Jobs: Job 32 (slow, 12.0s) aur Job 34 (sleep, pending).
Test: Worker chalu kiya. Job 32 claim hone ke 3 second baad (jab handler sleep me tha), worker ko SIGBREAK signal bheja.

TERMINAL :

[worker-1524] Starting worker process (PID: 1524)...
[worker-1524] Claimed job 32 (attempt=2, rowcount=1). Status is now 'running'.
[worker-1524] [SLOW HANDLER] Work started (12.0s)...

[worker-1524] Signal SIGBREAK received. Finishing current job before shutdown...

[worker-1524] Heartbeat sent for job 32
[worker-1524] [SLOW HANDLER] Work completed.
[worker-1524] Finished execution for job 32.
[worker-1524] Marked job 32 as 'succeeded' (rowcount=1).
[worker-1524] Clean shutdown complete. Exiting with code 0.


1. Handler Pura Hua: Shutdown signal milne ke bawajood handler crash nahi hua, usne apna poora 12 second execution complete kiya.

2. Heartbeat Zinda Raha: Shutdown ke dauran 10 second par [worker-1524] Heartbeat sent for job 32 fire hua, jisse lease extend hoti rahi aur reaper job ko steal nahi kar paya!

3. Guard Matches & Mark Succeeded: Job 32 safely succeeded mark hua (rowcount = 1).

4. No New Claims: Shutdown signal ke baad queue me pada Job 34 claim nahi hua aur pending hi raha.

---

week 3 - day 1 :

week 2 me dekha ki worker slow + lease expiry hone pr reaper wapas pending krke overlap/duplicate kr sakta.
(duplicate hi nhi hota hamesha, pehla worker mar sakta + duja worker chalra = technically ek hi kaam hora, but rows 2 hori)


Asli Problem: Ab tak hamara worker sirf print() karta tha ya asyncio.sleep() karta tha. Lekin real-world me background job ka matlab hota hai — Email bhejna, Payment katna, ya Database me Order record insert karna (Side Effect).

Agar do worker chal gaye, to User ke account se 2 baar paise kat jayenge ya 2 emails chale jayenge!

Lekin abhi tak hamare paas koi aisi table nahi thi jahan hum dekh sakein ki side effect kitni baar hua.


- Aaj kya prove karna hai? (The Target) :

Target: Hum database me ek nayi Side-Effect Table banayenge, ek naya handler banayenge jo wahan insert karega, aur jaan-boojh kar 2 workers chala kar ek job ko 2 baar chalayenge taaki us table me count 2 dikhe!

Interim Guarantee (Aaj ki limit): Aaj hum duplicate ko rokenge nahi. Aaj sirf yeh guarantee hogi ki "Side effect kitni baar hua, wo ab database me saaf-saaf gina ja sakta hai (Observable hai)." (Rokege hum Din 2 par UNIQUE constraint laga kar).


job enqueue (slow) -> worker a claims -> worker A inserts side eff = 1, worker A lease expire -> reaper -> worker b claims job -> worker b inserts side eff = 2, PROVEN.


Relay yeh promise nahi karti ki "side effect 1 baar hoga". Aaj promise sirf yeh hai ki "side effect ka count ab database me measurable/observable hai."


database me new table banani jisme handler apna record daale -> 
option 1 : counter : Ek row jisme integer update hota rahe. (Nuksan: Kis worker ne kab kiya wo time aur ID mit jata hai, bcz counter update picchle kisne kya kiya wo overwrite krta he).
option 2 : Ledger : har execution ka ek naya row insert(id, job_id, worker_id, created_at), porri timeline dikhegi with worker_id.



Aaj is table par UNIQUE(job_id) NAHI lagana hai! Agar aaj hi UNIQUE laga diya to duplicate insert error de dega aur aaj ka target (Count = 2) fail ho jayega.


aj ke experiment me kya hua :

heartbeat mene disable/handler me time.sleep(45) kr diya jisse event loop block ho and heartbeat run hi na ho, warna lease expire hi nhi hone dega or test nhi chalega.


The Execution Flow:
Job enqueue karein (seconds = 45).
Worker A Job claim karega 
→
→ Step 2 wali table me Row #1 daalega 
→
→ 45s ke kaam me lag jayega.
30s baad Lease expire hogi 
→
→ Reaper job ko pending bana dega!
Worker B usi job ko claim kar lega 
→
→ Step 2 wali table me Row #2 daalega!


then : select count(*) from <side_effect_table> where job_id = <id>;


2 rows aane se overlap pakka nhi hota, ek worker mar gya ho and dusra chala ho, prove krne :
- worker A kab shuru hua and khatm hua
- worker b kab claim kiya

Dono ke beech kitne seconds ka actual concurrent overlap tha.


slow job me worker ko sigbreak bhejo, shurtdown ke daruan lease expire hoti hai to kya reaper doosre worker ko job de dega?


Side effect -> handler ke andar likha jaaye, uske baad nahi. Agar tum effect ko mark ke saath likhoge, to aaj ka duplicate dikhega hi nahi — kyunki doosre worker ka mark rowcount = 0 pe reject ho sakta hai aur effect uske saath rollback ho jaayega

Duration payload se aaye, exactly jaise handle_slow payload.get("seconds", 8.0) padhta hai. Naya named handler har duration ke liye NAHI.

bina Idempotency ke Relay system 'At-Least-Once' hai — yani agar worker slow hua to duplicate side-effects (emails) database me chale jate hain. Kal (Din 2) hum UNIQUE constraint lagakar in duplicates ko rokna seekhenge.

Worker A aaya (Attempt 1):

Usne insert kiya: (job_id=36, worker_id='worker-A', action='email')
Database: ✅ Success! (Pehli email record ho gayi).
Worker B aaya (Attempt 2 - Overlap/Duplicate):

Usne wahi insert karne ki koshish ki: (job_id=36, worker_id='worker-B', action='email')
Database: ❌ STOP! UniqueViolationError: Key (job_id)=(36) already exists.
Insert REJECT ho gaya!

Database me UNIQUE lagane ke baad code me hum us error ko handle karte hain: ON CONFLICT (job_id) DO NOTHING — jiska matlab hota hai: "Agar pehle se exist karta hai, to shanti se aage badh jao, error mat feko aur duplicate mat banao."

---

AWS : Timeouts, Retries, Backoff with Jitter :

FAILURES :

- Whenever one service or system calls another, failures can happen. These failures can come from a variety of factors. They include servers, networks, load balancers, software, operating systems, or even mistakes from system operators. We design our systems to reduce the probability of failure, but impossible to build systems that never fail.

- so amazon says,we design our systems to tolerate and reduce the probability of failure, and avoid magnifying a small percentage of failures into a complete outage. To build resilient systems, we employ three essential tools: timeouts, retries, and backoff.


Many kinds of failures become apparent as requests taking longer than usual, and potentially never completing. When a client is waiting longer than usual for a request to complete, it also holds on to the resources it was using for that request for a longer time. When a number of requests hold on to resources for a long time, the server can run out of those resources. These resources can include memory, threads, connections, ephemeral ports, or anything else that is limited. To avoid this situation, clients set timeouts. Timeouts are the maximum amount of time that a client waits for a request to complete.


It's not always safe to retry. A retry can increase the load on the system being called, if the system is already failing because it’s approaching an overload. To avoid this problem, we implement our clients to use backoff. This increases the time between subsequent retries, which keeps the load on the backend even. The other problem with retries is that some remote calls have side effects. A timeout or failure doesn't necessarily mean that side effects haven't happened. If doing the side effects multiple times is undesirable, a best practice is designing APIs to be idempotent, meaning they can be safely retried.


 If errors are caused by load, retries can be ineffective if all clients retry at the same time. To avoid this problem, we employ jitter. This is a random amount of time before making or retrying a request to help prevent large bursts by spreading out the arrival rate.


TIME OUTS :

the most difficult problem is choosing a timeout value to set.

Setting a timeout too high reduces its usefulness, because resources are still consumed while the client waits for the timeout. 

Setting the timeout too low has two risks:

- Increased traffic on the backend and increased latency because too many requests are retried.

- Increased small backend latency leading to a complete outage, because all requests start being retried.


-> Isliye Amazon mein, jab hum ek service se kisi dusri service ko call karwate hain, toh hum sabse pehle false timeouts (galat ya premature timeouts) ka ek acceptable rate choose karte hain (jaise ki 0.1%).

Uske baad, hum downstream service (service jisko call kiya ja rha he) par uske corresponding latency percentile ko dekhte hain (is example ke hisaab se p99.9 percentile).

PITFALLS(where this approach fails) :

- clients ke paas bohot zyada network latency hoti hai, jaise ki public internet ke through aane wali traffic.
Aise cases mein, hum ek reasonable worst-case network latency ko bhi calculation mein jodte.

-  latency bounds bohot tight (narrow) hote hain — yaani jahan p99.9 percentile aur p50 (median) percentile aapas mein bohot close hote hain.
Aise cases mein, thoda sa padding (extra buffer time) add karna help karta hai, taaki latency mein aane wale small increases ki wajah se high numbers of unnecessary timeouts na hone lagein.


In one system that I worked on at Amazon, we saw a small number of timeouts talking to a dependency immediately following deployments. The timeout was set very low, to around 20 milliseconds. Outside of deployments, even with this low timeout value, we did not see timeouts happening regularly. Digging in, I found that the timer included establishing a new secure connection, which was reused on subsequent requests. Because connection establishment took longer than 20 milliseconds, we saw a small number of requests time out when a new server went into service after deployments. In some cases, the requests retried and succeeded. We initially worked around this problem by increasing the timeout value in case a connection was established. Later, we improved the system by establishing these connections when a process started up, but before receiving traffic. This got us around the timeout issue altogether.


RETRIES AND BACKOFF :

- When failures are caused by overload, retries that increase load can make matters significantly worse. They can even delay recovery by keeping the load high long after the original issue is resolved. Retries are similar to a powerful medicine -- useful in the right dose, but can cause significant damage when used too much. Unfortunately, in distributed systems there's almost no way to coordinate between all of the clients to achieve the right number of retries.

The preferred solution that we use in Amazon is a backoff. Instead of retrying immediately and aggressively, the client waits some amount of time between tries. The most common pattern is an exponential backoff, where the wait time is increased exponentially after every attempt. Exponential backoff can lead to very long backoff times, because exponential functions grow quickly. To avoid retrying for too long, implementations typically cap their backoff to a maximum value. This is called, predictably, capped exponential backoff. 

However, this introduces another problem. Now all of the clients are retrying constantly at the capped rate.

Despite these risks and challenges, retries are a powerful mechanism for providing high availability in the face of transient and random errors.


JITTER :

- When failures are caused by overload or contention, backing off often doesn't help as much as it seems like it should. This is because of correlation. If all the failed calls back off to the same time, they cause contention or overload again when they are retried. Our solution is jitter. Jitter adds some amount of randomness to the backoff to spread the retries around in time.


 the traffic to our services, including both control-planes and data-planes, tends to spike a lot. These spikes of traffic can be very short, and are often hidden by aggregated metrics. When building systems, we consider adding some jitter to all timers, periodic jobs, and other delayed work. This helps spread out spikes of work, and makes it easier for downstream services to scale for a workload.


CONCLUSION :

Timeouts keep systems from hanging unreasonably long, retries can mask those failures, and backoff and jitter can improve utilization and reduce congestion on systems.

At Amazon, we have learned that it is important to be cautious about retries. Retries can amplify the load on a dependent system. If calls to a system are timing out, and that system is overloaded, retries can make the overload worse instead of better. We avoid this amplification by retrying only when we observe that the dependency is healthy. We stop retrying when the retries are not helping to improve availability.

---

Din 1 par kya hua tha: 2 workers ne ek hi job chalaya 
→
→ job_executions me 2 rows bani 
→
→ aur side_effects me 2 duplicate emails chale gaye.
Din 2 par kya karna hai: Hum wahi exact collision (2 workers, 
45
s
45s duration, proved overlap) phir se repeat karenge...
Lekin aaj ka Result: job_executions me 2 rows banengi, par side_effects table me count 1 hi rahega!
Core Lesson: Database-level UNIQUE constraint (ON CONFLICT DO NOTHING) duplicate delivery ko execute hone se rok deta hai, jabki application level par SELECT-then-INSERT check concurrency me fail ho jata hai.



job -> worker A claim -> inserts effect_key, rowcount = 1 -> worker A blocks event loop -> reaper reclaim -> worker B -> insert effect_key(same), DB unique constraint conflict, rowcount = 0(no operation) -> side_eff count =1.


if i have already two same job rows sitting there and apply migration/unique constraint, it will reject.
- so we make a new nullable column "effect_key" and apply unique there. so old rows get NULL and new jobs gets a stable key that enforces uniqueness.

- Key ke andar worker_id, attempts, execution ID, timestamp ya random UUID kabhi mat daalna! Agar unhe key me daal diya to har duplicate dispatch alag key banayega aur UNIQUE constraint duplicate ko pakad hi nahi payega.


OUTPUT TERMINAL :

do worker + 1 reaper + no heartbeat.

expectation :
Worker A: Claims job 
→
→ inserts effect_key 
→
→ rowcount=1 
→
→ enters 45s sleep.
Reaper (at 30s): Reclaims job running -> pending.


Worker B: Claims same job 
→
→ tries to insert same effect_key 
→
→ DB catches unique conflict 
→
→ statement returns rowcount=0 (Duplicate skipped!) 
→
→ enters sleep.


Worker A (at 45s): Conflict on mark (rowcount=0).
Worker B (at ~75s): Marks succeeded (rowcount=1).



id | job_id |  worker_id   |          executed_at          
----+--------+--------------+-------------------------------
 67 |     39 | worker-24256 | 2026-09-01 14:18:00.736362+00
 68 |     39 | worker-4668  | 2026-09-01 14:18:07.948207+00



 id | job_id |  worker_id   |  effect_key  |          created_at           
----+--------+--------------+--------------+-------------------------------
  7 |     39 | worker-24256 | job:39:email | 2026-09-01 14:18:00.765132+00
(1 row)


 effect_count 
--------------
            1
(1 row)



Worker A 
14
:
18
:
00
14:18:00 par shuru hua aur 
45
s
45s chala (yani 
14
:
18
:
45
14:18:45 tak).
Worker B 
14
:
18
:
07
14:18:07 par shuru hua (
7.2
s
7.2s baad).
Measured Overlap: 
45
−
7.21
=
37.79
 seconds
45−7.21=37.79 seconds tak dono workers ne ek sath kaam kiya!


Din 1 par kya hua tha: 2 workers chale the to side-effects 2 ban gaye the.
Aaj Din 2 par kya hua: 3 dispatches huye, 2 alag workers chale, 
37.8
s
37.8s ka overlap hua... LEKIN side_effects me count EXACTLY 1 raha!
Pehle worker ne job:39:email insert kiya (rowcount=1), aur jab doosre worker ne insert karne ki koshish ki to Database ke UNIQUE(effect_key) constraint ne use block kar diya (rowcount=0)!



THE RACE WINDOW (application level):

# ❌ GALTI: Check-then-Act
record = db.query("SELECT * FROM side_effects WHERE job_id = 39")
if not record:  # 1. Pehle Check kiya
  db.execute("INSERT INTO side_effects ...")  # 2. Phir Action liya


Problem: Step 1 (Check karne) aur Step 2 (Insert karne) ke beech me kuch milliseconds ka gap hota hai.
Jab do workers concurrently chalte hain, to dono ko Step 1 me yahi lagta hai ki "kisine abhi tak email nahi bheji hai", aur dono ke dono email insert kar dete hain!


DATABASE UNIQUE CONSTRAINT (DB level):
- ON CONFLICT DO NOTHING.

Humne application ke upar bharosa chhod kar Database Engine (PostgreSQL) ko referee (Arbiter) bana diya.

PostgreSQL ke paas disk/index level par atomic lock hota hai:

Worker A aaya: Database index me job:39:email likh diya 
→
→ Success!
Worker B aaya: Chahe usne pehle kuch bhi dekha ho, jab wo database me likhne gaya to Postgres ne bola:
"Ruko! Yeh job:39:email pehle se index me darj hai. Main ise insert nahi karunga!"

Nateeja: Kissi bhi race condition me duplicate banna mathematically IMPOSSIBLE ho jata hai!

---

WEEK 3 - DAY 3 :

The Out-of-Memory (OOM) killer is a built-in Linux kernel safeguard that forcefully terminates a process to save the operating system from a total freeze when RAM and swap space are completely exhausted.


Din 2 me humne kya dekha tha: Do zinda workers concurrently chal rahe the, aur database ke UNIQUE(effect_key) constraint ne duplicate insert ko rok diya tha (rowcount = 0).

Din 3 ka Asli Sawaal: "Agar worker crash ho jaye (process achanak mar jaye, power cut ya OOM killer se), to kya hamara system recover ho payega? Aur recovery ke dauran kya duplicate side-effect banega ya nahi?"


SIDE EFFECT : Job ko process karte waqt application ke bahar/DB mein koi actual persistent change karna.

handler:
    calculate invoice      ← execution

    INSERT payment record  ← side-effect

    send email             ← side-effect

    charge credit card     ← side-effect



-> Worker ke execution me 3 critical points (boundaries) hote hain jahan crash ho sakta hai:


Case A (Before Effect): Worker ne job claim kiya, par side-effect insert hone se pehle mar gaya.

claim job
   ↓
handler start
   ↓
❌ worker dies
   ↓
side-effect hua hi nahi

Example: email send hone se pehle worker crash.


Case B (After Effect, Before Mark — The Centrepiece): Worker ne side-effect database me commit kar diya, par job ko succeeded mark karne se pehle mar gaya! (Yahan Durable Orphan Effect banta hai).

claim job
   ↓
side-effect execute
   ↓
DB mein side-effect COMMIT ✅
   ↓
❌ worker dies
   ↓
job = running


Ab database mein:

job  = running
effect = already exists

Lekin worker ko job succeeded mark karne ka chance nahi mila.


Case C (After Mark — The Control): Worker ne job ko succeeded mark karke commit kar diya, aur theek uske baad mar gaya.

side-effect COMMIT ✅
   ↓
job = succeeded COMMIT ✅
   ↓
❌ worker dies

Ab database clearly bol raha hai:

job       = succeeded
effect    = exists

Worker/reaper ko job dobara execute karne ki zarurat nahi.


-> Din 3 ka Target: Hum code me temporary hooks daal kar in teeno jagahon par jaan-boojh kar worker ko hard kill (os._exit(86)) karenge aur dekhenge ki Reaper aur Recovery Worker har boundary par system ko kaise handle karte hain.

os._exit(86): Python ka raw OS-level exit. Yeh try/except, finally, context managers, aur graceful shutdown sabko bypass karke process ko turant mar deta hai. Exit code 86 isliye use karte hain taaki prove ho sake ki exit crash hook se hua hai, normal crash se nahi.


TESTS AND OBSERVATIONS :

Pehle worker crash hoga (os._exit(86)).
Phir hum database ki photo (Snapshot) lenge ki crash ke waqt database me kya haal tha.
Phir hum Reaper aur Recovery Worker chalayenge yeh dekhne ke liye ki system us crash se kaise ubaarta hai!
Phir hum final photo (Snapshot) lenge ki recovery ke baad kya duplicate banta hai ya sab kuch sahi ho jata hai.


STEP 1 : worker me temporary crash hooks lagana jisse worker wahan jaan bujh kr crash kre :

---------------

CASE A :

job claim -> crash(exit:86) -> Pre-reaper Snapshot:
status = running, attempts = 1
job_executions = 1 (worker ne claim kiya tha)
side_effects = 0 (kyunki effect likhne se pehle hi mar gaya tha!) -> Hum SQL se hook hatayenge aur lease expire karenge. Reaper job ko running -> pending kar dega -> Doosra worker aayega, job ko claim karega, email side-effect insert karega (rowcount = 1), aur job ko succeeded kar dega.

OBSERVATIONS :

TERMINAL :
WORKER A :

[worker-17808] Claimed job 40 (attempt=1, rowcount=1). Status is now 'running'.
[worker-17808] Executing job 40 (type=email, attempt=1/3)...
[worker-17808] [CRASH HOOK] Crashing at before_effect_commit for job 40
Worker exited with code: 86

PRE REAPER SNAPSHOT : status: running | attempts: 1 | executions: 1 | effects: 0

REAPER RECLAIM

WORKER B :

[worker-17092] Claimed job 40 (attempt=2, rowcount=1). Status is now 'running'.
[worker-17092] [SIDE EFFECT] Committed 'email' for job 40 (key='job:40:email', rowcount=1).
[worker-17092] Marked job 40 as 'succeeded' (rowcount=1).


Post-Recovery Snapshot:
Status: succeeded
Attempts: 2
Executions: 2
Effects: 1 (At-least-once verified: Kaam khoya nahi, recovery ne effect create kar diya!).

------------------

CASE B :

Crash AFTER Effect Commit, Before Mark.

Database me email ja chuki hai, par Relay ko lagta hai job abhi bhi chal raha hai (Durable Orphan Effect). Jab recovery worker aayega, to kya wo doosri email bhej dega? Yahan hamara Din 2 ka UNIQUE constraint test hoga!

Worker side-effect insert karega (COMMIT hoga), fir Hook 2 fire hoga aur worker Exit 86 par mar jayega!
Pre-reaper Snapshot:
status = running, attempts = 1
side_effects = 1 (Email already database me commit ho chuki hai!)
Reaper Reclaim karega: Reaper job ko wapas pending bana dega.
Recovery Worker B chalega (Asli Test):
Recovery worker B job claim karega.
Wo side-effect insert karne jayega.
🎯 Database Unique Index use rok dega!
Worker B ke log me aayega: Side-effect duplicate skipped (rowcount=0).
Worker B job ko succeeded mark karega.(isne email wapis nhi bheji, success mark kr diya)


OBSERVATIONS :

TERMINAL :
WORKER A :

[worker-1104] Claimed job 41 (attempt=1, rowcount=1). Status is now 'running'.
[worker-1104] [SIDE EFFECT] Committed 'email' for job 41 (key='job:41:email', rowcount=1).
[worker-1104] [CRASH HOOK] Crashing at after_effect_commit for job 41
Worker exited with code: 86

PRE REAPER SNAPSHOT : status: running | attempts: 1 | executions: 1 | effects: 1 (key='job:41:email')

REPAER RECLAIM

WORKER B :

[worker-4756] Claimed job 41 (attempt=2, rowcount=1). Status is now 'running'.
[worker-4756] [SIDE EFFECT] Duplicate 'email' skipped for job 41 (key='job:41:email', rowcount=0).
[worker-4756] Marked job 41 as 'succeeded' (rowcount=1).


Post-Recovery Snapshot:
Status: succeeded
Attempts: 2
Executions: 2
Effects: EXACTLY 1 (Duplicate suppress ho gaya!).


Conclusion: Dedup Proven! Crash hone ke bawajood recovery worker ne duplicate email nahi bheji, balki use skip karke job ko safely succeed kar diya!

-------------------

CASE C :

Yahan worker ne job ko succeeded mark kar diya aur transaction COMMIT ho gayi, aur uske theek baad worker mar gaya.

Sawaal: Kya Reaper ya koi doosra worker is job ko dobara chhedega?
Nahi! Kyunki job already succeeded ho chuki hai, to system ko ise bilkul ignore karna chahiye.


Crash Worker chalega: Mark UPDATE 
→
→ COMMIT 
→
→ Hook 3 fire 
→
→ Exit 86.
Snapshot: Job already succeeded hai, side_effects = 1, executions = 1.
Liveness Test (Reaper & Worker):
Hum Reaper ko chalayenge kam se kam 6 seconds ke liye. Reaper poll karega par Job ko touch nahi karega (candidates=0, reclaimed=0).
Hum Worker ko chalayenge kam se kam 6 seconds ke liye. Worker queue dekhega par Job ko claim nahi karega.
Conclusion: Terminal commit process death ke baad bhi survive kar gaya, aur live workers ne ise sahi tarike se chhod diya (No accidental re-execution).


OBSERVATIONS :

TERMINAL :
WORKER A :

[worker-4296] Claimed job 42 (attempt=1, rowcount=1). Status is now 'running'.
[worker-4296] [SIDE EFFECT] Committed 'email' for job 42 (key='job:42:email', rowcount=1).
[worker-4296] Marked job 42 as 'succeeded' (rowcount=1).
[worker-4296] [CRASH HOOK] Crashing at after_mark_commit for job 42
Worker exited with code: 86


PRE TEST SNAPSHOT : status: succeeded | attempts: 1 | executions: 1 | effects: 1

Post-Control Snapshot:
Status: succeeded
Attempts: 1
Executions: 1
Effects: 1 (Terminal Invariant verified: Completed job ko kisi ne re-execute nahi kiya!).

----------------------

 id |  status   | attempts | has_hook | executions | effects 
----+-----------+----------+----------+------------+---------
 40 | succeeded |        2 | f        |          2 |       1   <-- Case A (Before Effect)
 41 | succeeded |        2 | f        |          2 |       1   <-- Case B (After Effect)
 42 | succeeded |        1 | f        |          1 |       1   <-- Case C (After Mark)


KUCH SAWAAL :


Kya Case A aur Case B ka Recovery-Relevant Projection Same Tha?
Haan! Dono cases me recovery se pehle database me: Status running, attempts 1, lease expired thi. 
Recovery worker ko bahar se dekhne par dono jobs identical dikhti hain, lekin Case B me effect pehle hi durable tha aur Case A me nahi tha. Yahi wajah hai ki recovery worker ka idempotent hona compulsory hai!


Local Effect aur Job Mark ko ek hi transaction me merge kyu nahi kar dete?
Real Cost: Agar hum side-effect aur mark ko ek transaction me daalenge, to handler ka poora execution time database transaction ke andar fas jayega (long-running transaction locks pakad kar rakhegi).
Aur agar mark statement rowcount = 0 par fail ho jaye, to pura transaction rollback karna padega.


External Effect (Stripe/Email) same transaction me kyu nahi aa sakta?
Kyunki PostgreSQL ka COMMIT ya ROLLBACK sirf database rows par kaam karta hai. Agar aapne Stripe se paise kaat liye ya email bhej diya, aur uske baad Postgres me crash ya rollback hua, to database to rollback ho jayega par user ke paise wapas nahi aayenge! Isliye Transactional Outbox pattern ki zaroorat padti hai (Week 4 topic).


CONCLUSION :

to aj humne dekha ki har worker cliam - execute - commit krta he, har ek step pr worker fail krke deka ki kya hota he .

first fail : agar job claim ki but mar gya claim ke baad.
recovery : lease expiry + reaper(duja worker reclaim krega and execute krega).
GUARANTEE : "At-Least-Once Execution Guarantee" (Loss Prevention)
Matlab: Agar worker kaam shuru karte hi mar jaye, to kaam hamesha ke liye gayab (lost) nahi hoga. Reaper use zinda karega aur kam se kam ek baar effect zaroor execute hoga!


sec fail : worker claim + execute and commit kiya, but mark success krna reh gya jisse running hi rhega db me. ab reaper running fasi jobs ko duje ko dega.
recovery : DATABASE unique constraint = table me duje worker ko ghusne nhi diya, ON CONFLICT DO NOTHING = duje worker ko crash nhi hone diya and statement ko safe no-op banaya(rowcount=0) jisse worker agge badhke status successed kr dega.
GUARANTEE : "At-Most-Once Side-Effect Guarantee / Idempotency" (Duplicate Prevention)
Matlab: Chahe worker email likhte hi mar jaye aur doosra worker recovery ke liye aaye, user ko kabhi bhi doosri email nahi jayegi! Side-effect hamesha EXACTLY 1 hi rahega.


third fail : worker ne sb kuch kr diya(commit, execute, mark), or fir mar gya.
recovery : DATABASE ACID DURABILITY : process commit krke mara jisse commit status safe he, reaper sirf running job ko dhundega, yaha wo reclaim krne nhi dega, or kisi worker ne nahi uthaya bcz status pending nhi tha.
GUARANTEE : "Terminal State Invariant" (Zombie Prevention / Completion Durability)
Matlab: Ek baar jab Relay ne kisi job ko succeeded mark kar diya, to wo pathar ki lakeer hai. Uske baad process mare ya computer reboot ho jaye, koi bhi Reaper ya Worker us completed job ko dobara restart (zombie execution) nahi karega!

---

WEEK 3 - DAY 4

Enqueue Idempotency: Ek hi caller intent jab network fail hone par retry kare, to system use wahi pehle wali job identity wapas kare, naya duplicate job create na kare.


Pehle (Din 2/3): Humne dekha ki agar 1 job database me hai aur 2 workers use chala dein, to duplicate email nahi jaani chahiye (Execute Dedup).

Aaj (Din 4): Hum yeh dekh rahe hain ki agar client ne network slow hone ki wajah se Button 2 baar daba diya aur API ko 2 baar request bhej di, to database me 2 alag jobs nahi banne chahiye! API ko pehli hi job ka response wapas kar dena chahiye (Enqueue Dedup).



STEP 1 : 

Agar client do baar request bhejta hai, to server ko kaise pata chalega ki yeh wahi puraani request hai ya koi nayi request?

WHAT ADDING IN CODE :

- Caller-minted Key: Client har request ke sath ek ID bhejega: idempotency_key = "req-123".

BLANK KEY REJECTED, MAX LEN = 128 CHAR.

- Request Fingerprint (SHA-256 Hash): Agar client ne key wahi rakhi ("req-123"), par payload badal diya ({"amount": 10} ki jagah {"amount": 500}), to kya hum use purani job ka success de dein? Bilkul nahi! Yeh fraud ya bug ho sakta hai. Isliye hum request ke content ka ek SHA-256 Fingerprint nikaal kar store karenge.

KEY ORDER AGGE PICHE HONE SE BHI FINGERPRINT SAME BAN RHI(order_same=True), payload ya type badlne se fingerprint badl jata.

- Canonical JSON: {"a": 1, "b": 2} aur {"b": 2, "a": 1} ka hash same aana chahiye. 
- JSON = json me ye dono bilkul ek hi chiz he same, lekin hashing algo(SHA-256) character by char padhega jisse iska HASH alag aa sakta he.



- CONONICAL JSON = isme client ne chaahe {"b": 2, "a": 1} bheja ho ya {"a": 1, "b": 2}, sort_keys=TRUE dono ko alphabetic order me sort krega, to dono ab {"a": 1, "b": 2} ban jayege.
- ab string ek jesi ban gyi, to SHA-256 hash bhi SAME ho jayega.

JSONB = ye whie-space, duplicate keys hata deta he + SORT krke store krta he.

- agar postgres ka jsonb dono ko same manta he, to hum isme python ka SHA-256 hash fingerprint kyu banayege?
- Kyunki Database me UNIQUE constraint sirf simple types (jaise Text ya Number) par tezi se index banata hai.
- Agar hum pure payload jsonb par unique constraint lagate, to badi JSON payloads par database slow ho jata, aur hum idempotency_key ke sath fingerprint mismatch ko detect nahi kar paate.

Humara rule hai:

- idempotency_key par database ka UNIQUE constraint lagega.
- request_fingerprint me Python ka canonical hash jayega.



STEP 2 :

Ek client request bhejta hai: key = "k1", payload = {"a": 1, "b": 2}. Server use insert karta hai aur job_id = 116 deta hai.

Client ka network drop ho gaya. Client ne dobara wahi request bheji: key = "k1", payload = {"b": 2, "a": 1}.

Expectation: Server naya job nahi banayega! Wo dekhega ki "k1" pehle se hai, fingerprint match karega, aur wahi purana job_id = 116 wapas return kar dega.


Request 1 bheji:

Payload: type='sleep', payload={'a': 1, 'b': 2}, key='din4-seq-7f03...'

API ne Return kiya: Job ID: 43, Status: pending (HTTP 202)


Request 2 bheji (Same key, par reversed keys {'b': 2, 'a': 1}):

API ne Return kiya: Job ID: 43, Status: pending (HTTP 202)


Database Check:

select count(*) from jobs where idempotency_key='din4-seq-7f03...';
-- Result: 1 row!


JOB SEQUENCE MOVEMENT :

Customer 1 aaya (Request 1):

Machine ka button dabaya 
→
→ Token nikla #43.
Counter ho gaya 43.
Customer 1 counter par gaya, apna form bhara aur account khul gaya (Commit ho gaya!).
Customer 2 aaya (Duplicate Replay):

Usne machine ka button dabaya 
→
→ Machine ne turant agla Token generate kar diya #44!
Machine ka counter ho gaya 44.
Ab Customer 2 counter par gaya. Officer ne dekha: "Arey! Aap to wahi Customer 1 ho, aapka account to pehle se khula hua hai (Duplicate Key Conflict)!"
Officer ne uska form faad kar dustbin me phenk diya (Rollback ho gaya!).
Ab Token #44 ka kya hua?

customer 2 ka Form to dustbin me chala gaya, isliye DB me sirf Customer 1 ki 1 hi row bachi rahi, lekin Token #44 machine ke andar wapas reverse nahi ja sakta!
Machine ka counter ab 44 par hi khada rahega.
Agla naya customer aayega to use Token #45 milega!

43(row=1) -> 44(no row exist) -> 45(next job)

POSTGRES Rollback ke sath sequence ko wapas 43 kyu nahi karta?

- Agar Postgres sequence ko rollback karne lagta, to jab tak ek transaction poori nahi hoti, tab tak doosre transactions ko sequence lock karke wait karwana padta. System bohot slow ho jata.

Database me IDs hamesha 1, 2, 3, 4... lagataar nahi aayengi. Beech me gaps aayenge (jaise 43 ke baad seedha 45).
Never Assume count(*) == max(id): Agar database me 100 rows hain, to zaroori nahi ki aakhri ID 100 ho, wo 120 bhi ho sakti hai!



STEP 3 :

CODE bugs to see :

1. Mismatch Control: Client ne wahi key use ki par payload badal diya ({"a": 1, "b": 3}). Agar server ne purana job_id return kar diya, to client samjhega uska naya payload accept ho gaya! Server ko 409 Conflict fekna chahiye.

HTTP_STATUS: 409
BODY: {"detail": {"code": "idempotency_key_mismatch", "job_id": 43}}


2. Postgres 25P02 Control: The Scenario: Jab database me duplicate key takrati hai, to PostgreSQL transaction ko Aborted State me daal deta hai. Postgres ka rule hai: "Jab tak tum ROLLBACK nahi karte, tab tak tum is connection par koi naya SELECT ya query nahi chala sakte."

WRONG :

try:
  await db.commit()  # Duplicate key takrayi!

except IntegrityError:
  # Galti: Rollback karna bhool gaye aur seedha original row dhundhne chale gaye!
   // await db.rollback() -> missing.
  existing = await db.execute(select(Job).where(...))

- Error 25P02: current transaction is aborted, commands ignored until end of transaction block!`**  
  Aur user ko milta hai **500 Internal Server Error**!


- before_rollback_caught = PendingRollbackError (SELECT fail hua!)
- after_rollback_rows = 1 (Rollback ke baad SELECT successful!)


3. Unrelated Integrity Control: Agar job status check constraint (jobs_status_check) violate hui, to generic except IntegrityError use replay na maan le! Use 500 Internal Error hi aana chahiye.

Hamara code kisi bhi random error ko replay nahi maanta. Wo sirf aur sirf uq_jobs_idempotency_key ke conflict ko replay maanta hai, baki integrity errors par 500 deta hai.


STEP 4 :

Agar do requests ek hi millisecond me concurrently aayi, to application layer ka koi if check kaam nahi aayega. Dono DB me insert karne jayengi.

-> Database me kya hoga?
- Ek transaction Winner banegi aur insert karegi.

- Doosri transaction Loser banegi aur database ke lock par wait (block) karegi jab tak Winner commit na ho jaye!

- Winner ke commit hote hi Loser ko unique violation milega, wo replay contract me convert hoga aur winner ka job_id return karega.


- Dono clients ko response mila aur dono ke paas same job_id tha!

- Database me EXACTLY 1 row bani!

-> Conclusion: Concurrency me application timing nahi, Postgres ka unique index referee banta hai aur loser safely wait karke replay paata hai.

TERMINAL :

Humne DB me ek trigger lagaya jo pehle request (Winner) ko 5 second ke liye sula deta hai (pg_sleep(5)).


=== PG_STAT_ACTIVITY DURING 5s RACE HOLD ===
 pid | wait_event_type |  wait_event   | query                                  
-----+-----------------+---------------+------------------------------------------------
 695 | Timeout         | PgSleep       | INSERT INTO jobs ...
 531 | Lock            | transactionid | INSERT INTO jobs ...
(2 rows)


AFTER 5 SECONDS :

Client 1: status=202, elapsed=5227.5ms, body={'job_id': 53, 'status': 'pending'}
Client 2: status=202, elapsed=5207.7ms, body={'job_id': 53, 'status': 'pending'}
DB Rows count for race key: 1


(NOTE : yaha clients queue me daal rhe he job ko, not success/running hore because worker ne nhi liya abi, isliye status pending retrun hua. winner jo client 1 tha ne job ko db me insert kiya initial status = pending. loser client 2 wait krega jab tk winner commit nhi hota, or ab isko unique conflict milega, or whi original job ka current status bhej dega jo he pending. to jab worker ayega, usko ek hi row job = 53 milegi, duplicate job loser daal nhi paya)


STEP 5 :

Key wali job (Opt-in): Client bolta hai "Yeh mera request #123 hai. Agar main network drop hone par dobara #123 bhejoon, to mujhe naya job mat dena, purana hi dena."

Bina key wali normal job (Opt-out): Client key nahi bhejta. Wo bolta hai "Mujhe ek email bhejni hai." Agar wo 5 minute baad dobara bina key ke wahi email bhejta hai, to wo chahta hai ki doosri email bhi jaye!

Dikkat kya ho sakti thi: Agar hum galti se bina key wale jobs ko bhi payload ke hisab se dedup kar dete, to client jab bhi same data bhejta, purani job merge ho jati aur naya kaam chalta hi nahi!

Postgres me yeh kaise kaam karta hai: Postgres ka UNIQUE index NULL values par enforce nahi hota (NULL != NULL). Isliye jitni marzi unkeyed jobs aane do, unpe koi constraint error nahi aata!


=== STEP 5 UNKEYED RESULTS ===
Request 1 -> Status: 202, Job ID: 55
Request 2 -> Status: 202, Job ID: 56
Are Job IDs distinct?: True

Dono requests ko alag-alag Job IDs (55 aur 56) mile aur database me 2 rows bani


"Bina key wali jobs me to ek hi email do baar ja sakta hai na? To kya hum bina key ke bhi duplicate rok sakte hain, ya answer yahi hai ki key wala hi bhejo?"

Iska answer hai: Answer yahi hai ki Client ko KEY hi bhejni padegi! Server bina key ke duplicate rok hi nahi sakta.
- bina key tb use kre jab same work intensionally do bar krvana ho(no duplication manage), jisse same work pr bhi alag job assign hogi or usko NAYA work mana jayega jo execute hoga.
- key(idempotency_key) ke sath tb bhejo jab ek hi baar krvana ho and retry pr safely no duplication ho.


STEP 6 :

1. Enqueue Dedup (Din 4)
- API Layer par
- prevent failure : Client ke browser/app ke network retry se database me 2 rows banne se rokti hai.

2. Execute Dedup (Din 2/3)
- Worker / DB Engine par
- prevent failure : Agar database me 1 job hai, aur worker crash ho gaya ya lease expire ho gayi, to doosre worker ko duplicate side-effect (email/payment) karne se rokti hai.


Kyu ek ke bina doosra adhoora hai?
Agar aap sirf Enqueue dedup lagaoge aur worker crash ho gaya, to Reaper job ko restart karega aur naya worker aakar dobara email bhej dega! Isliye Execute Dedup zinda rehna compulsory hai.


FLOW WORK :

WORKER A :

[worker-19136] Claimed job 58 (attempt=1)
[worker-19136] [SIDE EFFECT] Committed 'email' for job 58 (rowcount=1)

Worker A 45s sleep me gaya. Humne lease expire karke Reaper chalaya:

[reaper-9964] id=58 pre_status=running matched=1 post_status=pending

WORKER B :

[worker-14812] Claimed job 58 (attempt=2)
[worker-14812] [SIDE EFFECT] Duplicate 'email' skipped for job 58 (key='job:58:email', rowcount=0).
[worker-14812] Marked job 58 as 'succeeded' (rowcount=1).


id: 58 | status: succeeded | attempts: 2 | executions: 2 | workers: 2 | effects: 1.

---

WEEK 3 - DAY 5

Pehle ke Dino me humne kya kiya?

Humne manually kuch scenarios test kiye: 2 concurrent workers chalaye (Din 2), exact 3 points par crash kiya (Din 3), aur network replay bheja (Din 4).

Lekin ek reviewer ya interviewer keh sakta hai: "Tumne to wahi tests chalaye jo tumne soche the. Agar workers ka koi ajeeb random order ho jaye (Interleaving), ya achanak 5 baar crash aur 3 baar retry ho jaye, to kya tab bhi side effect ek hi baar hoga?"


Aaj hum Hypothesis library use karke ek Property-Based Test likhenge jo random sequences of actions (claim, crash, retry, reclaim, execute) generate karega.

Aur yeh prove karega: Chahe events ka order kitna bhi random ya chaotic kyu na ho, side effect count hamesha ≤ 1 hi rahega!


WHY EFFECTS ≤ 1(AT MOST ONCE), NOT EXACTLY ONE ?

- Job fail ho gayi (boom handler): Worker ne job uthai, par pehli line par hi code fat gaya (Exception). Kaam hua hi nahi. To side effect kitna hoga? 0!

- Worker effect likhne se pehle hi mar gaya: Worker ne job claim ki, par database me email likhne se theek 1 millisecond pehle server ka power cut ho gaya. Effect kitna hua? 0!

- Job Dead-Letter me chali gayi: Job ne 3 attempts try kiye, teeno baar network error aaya aur job dead_letter ban gayi. Effect kitna hua? 0!


Agar hum test me likhte: assert effects == 1: To jaise hi koi job crash hoti ya fail hoti, hamara test chilaane lagta: "Error! Effect 0 kyu hai, 1 hona chahiye tha!" — Yeh galat hota, kyunki failure ek valid state hai.

Isliye Distributed Systems me do alag niyam hote hain:

- Safety Rule (Buri cheez kabhi na ho):

Side effect kabhi bhi 1 se zyada nahi hoga → effects <= 1 (0 chalega agar fail hua, 1 chalega agar pass hua, par 2 ya 3 KABHI NAHI!).

- Conditional Liveness Rule (Agar sab theek raha to kaam zaroor ho):

AGAR handler bina error ke commit ho gaya, TAB effect exactly 1 hoga → effects == 1.


Din 2, 3 aur 4 me humne kya kiya?

Humne ek car banayi jisme humne naye brakes lagaye (hamara UNIQUE constraint).
Humne seedhi saaf road par car chala kar brake dabaya: "Dekho car ruk gayi (Dedup ho gaya)!"

Ab Din 5 par interviewer ya senior engineer aapse aakar kehta hai:

"Tumne to sirf wahi 2-3 situations test ki jo tumhare dimaag me aayi thi.
Agar car pahaad par ho, barish ho rahi ho, achanak pahiya slip kare, 5 baar starter band ho, tab kya car rukegi?
Kya tumne hazaron ajeeb-o-gareeb random situations me test karke dekha hai?"



Real database me 30 second ki lease aur 10 second ka heartbeat hota hai. Agar hum random testing real DB par time sleep ke sath karenge, to 100 tests chalane me ghanto lag jayenge! Isliye hum pehle ek In-Memory State Machine (Model) banate hain jo Relay ke lifecycle (claim, effect_write, crash, reclaim, retry, mark) ko microseconds me run karti hai.


Aaj hum 4 aasan kaam kar rahe hain:

1. Computer se hazaron random situations banwana (Step 2 & 3)
Hum khud hath se test nahi likhenge. Hum Hypothesis naam ke ek tool ko bolte hain:

"Tu ek pagal monkey ki tarah behave kar. Kabhi job claim kar, achanak process crash kar de, kabhi 3 baar retry kar, kabhi 4 baar reclaim kar — jo marzi aaye ajeeb sequence bana kar test kar."

Aur hum check karte hain: Chahe events ka order kitna bhi ajeeb ho, kya side-effect hamesha ≤1 rehta hai?

TEST AND OBSERVATIONS :

Humne kya kiya: 

Humne Python ke andar Relay ka ek chhota fast model (Simulation) banaya, bina database aur bina 30-second ke sleep ke (microseconds me chalne wala).
Kya test kiya (4 Scenarios):

Write se pehle crash → Effect = 0.

Normal ek worker chala → Effect = 1.

Worker A chala → Crash hua → Reclaim hua → Worker B chala → Dispatches = 2, Effect = 1.

Extra retries hue (P-27 Overdraft) → Dispatches = 4, Effect = 1.


Terminal Observation: 4 passed in 0.05s.

Conclusion: In-memory simulation prove karta hai ki hamari state-machine transitions bilkul sahi hain.



2. Jaan-boojh kar Brake tod kar dekhna (Step 4 - Mutation)
Hum yeh check karte hain: "Kahin hamara test jhootha to nahi hai jo har baar pass ho jata hai?"

Hum code me se dedup logic ko thodi der ke liye band (tod) kar dete hain.
Aur test ko dobara chalate hain.
Test turant RED (FAIL) ho jata hai!
Isse prove hota hai ki hamara test sach me kaam kar raha hai, koi dikhava nahi hai.

TESTS AND OBSERVATION :

Humne kya kiya: 

Humne Hypothesis library ko bola ki wo ek pagal monkey ki tarah behaves kare aur Relay ke actions (claim, write, crash, reclaim, retry, mark) ko random order me ghuma-phirakar 300 alag-alag ajeeb scenarios generate kare.

- 200 random legal sequences.

- 100 forced-redispatch sequences (jisme kam se kam 2 workers ka chalna 100% guaranteed tha).


Terminal Observation: 300 passed, 0 safety failures.

Conclusion: Chahe events ka order kitna bhi ulta-pulta, chaotic ya ajeeb ho jaye, side effect count kisi bhi scenario me 1 se upar nahi gaya!



3. Asli Database me do-do workers daudana (Step 5, 6, 7)
Hypothesis to computer ki memory me chala. Par kya asli PostgreSQL database me bhi yeh sach hai?

Hum ek alag khali ground (disposable DB) banate hain.
Usme do real worker processes ko ek sath daudate hain.
Ek worker ko beech me goli maar kar (crash) dekhte hain.
Aur dekhte hain ki real Postgres bhi duplicate email ko rok deta hai.

TESTS AND OBSERVATION :

Humne kya kiya: 

Humne socha: "Kahin hamara Hypothesis test bekar to nahi hai jo har baar pass ho jata hai?" Isliye humne model ke andar se dedup ko band kar diya (DIN5_MUTANT=no_dedup) — matlab ab har insert duplicate row banayega.

Terminal Observation (FAIL HUA!): Test turant RED ho gaya! Hypothesis ne 30 steps ke complex sequence ko shrink (chhota) karke seedha 2 step ka minimal case dikha diya:

```
Falsifying example: [claim -> write -> reclaim -> claim -> write]
AssertionError: effect_count = 2 (Expected <= 1)
```

Conclusion (Mutation Killed): Isse saabit hua ki hamara test koi "dummy" test nahi hai. Jab dedup tootega, to yeh test 100% use pakad lega! Aur jab humne mutant hataya, to test wapas GREEN ho gaya.


4. Humne kya kiya: 

Ab hum memory se nikal kar asli PostgreSQL me gaye (ek naye temporary database relay_din5_... me). 

Humne 2 real worker processes ko ek hi millisecond me ek hi job ke side-effect par attack karwaya.


Terminal Observation (JSON output):

dispatches: 2

distinct_workers: 2

effect_rowcounts: [1, 0] (Ek worker ko insert mila, doosre ko DB constraint ne skip kar diya).

final_effects_in_db: 1!


Conclusion: Real multi-process concurrency me PostgreSQL ka Unique Index ek atomic referee ki tarah kaam karta hai aur duplicate insert nahi hone deta.


5. Humne kya kiya: 

Real PostgreSQL me Worker A ne side-effect likha, aur theek agle pal humne Worker A ko OS-kill (goli maar di) status update hone se pehle (Durable Orphan state). 

Phir Reaper ne job reclaim ki aur Worker B ne kaam shuru kiya.


Terminal Observation:

Worker A ke marne ke baad DB state:

running | attempts=1 | effects=1.


Reaper ne reclaim kiya:

pending | 1 | true.


Worker B ne dobara email insert karni chahi → Database ne use rowcount = 0 diya!



Final DB state: succeeded | attempts=2 | executions=2 | effects=1.

Conclusion: Hard process crashes ke baad bhi jab doosra worker recovery karta hai, to system safe rehta hai aur duplicate side effect create nahi hota.



6. Hamare system ki aakhri kamzori dhoondna (Step 8 - Fencing)
Hum yeh dekhte hain ki hamara UNIQUE constraint kya NAHI rok sakta?

UNIQUE constraint email ko duplicate hone se to bacha leta hai.
Lekin agar koi purana mara hua worker neend se jaag kar job ka Status badalne chala aaye, to constraint use nahi rok pati!
Isse hume pata chalta hai ki agle hafte (Week 4) hume Fencing Token banana padega.


Terminal Observation:

effect_count = 1 (Email to 1 hi rahi, Dedup ne bacha liya!)

LEKIN: stale_mark_rowcount = 1 aur current_owner_mark_rowcount = 0!



Universal claim "har job ka side effect = 1" galat hai kyunki boom/crash/dead_letter jobs bina effect write ke terminate ho sakti hain. Safety invariant strictly effects <= 1 hai, aur conditional exactness effects = 1 sirf un jobs par laagu hota hai jinka handler legal effect-write transaction complete kare.



----

WEEK4 - DAY 1 


Week 3 ki Jeet: Humne UNIQUE(effect_key) constraint lagakar yeh guarantee kar di thi ki chahe 10 workers retry karein, asli duniya ka side-effect (email/payment) sirf 1 hi baar commit hoga.


Week 3 ki Haar (The Stale-Writer Vulnerability):

- Worker A ne job uthayi aur email bhej di.
- Worker A ka event loop freeze/block ho gaya (jaise heavy CPU task ya garbage collection pause).
- 30s ki lease expire hui → Reaper ne job reclaim karke Worker B ko de di.
- Worker B ne job execute karna shuru kiya (Job ka status abhi running hai).

-> THE DISASTER: Worker A achanak neend se jaag gaya! Usne query chalayi:

```
UPDATE jobs SET status = 'succeeded' WHERE id = :id AND status = 'running';
```

Kyunki Worker B ki wajah se status running tha, Worker A ka UPDATE pass ho gaya (rowcount = 1)!

Jab Worker B ne apna kaam khatam karke status mark karna chaha, to wo fail ho gaya (rowcount = 0)!



FENCING TOKEN / CLAIM GENERATION :

- put a Monotonic Epoch counter claim_generator in DB.

- each worker has its own generator count

- Agar koi purana worker (Generation 1) neend se jaag kar status ya heartbeat likhne aayega, to database use bolega:

"Tu purana hai! Abhi generation 2 chal rahi hai!" aur uska write rowcount = 0 dekar fence (block) kar dega!



Compare-And-Set (CAS):

SQL me atomic update: UPDATE jobs SET status='running' WHERE id=:id AND status='pending'.

Agar rowcount = 1 aaya to main jeeta. Agar 0 aaya to kisi aur ne mujhse pehle le liya.


Blocking Handler : 

asyncio.sleep() = heartbeat stays active in background and lease dont expire.

time.sleep() = poor python thread and event loop blocks. lease expires.


STALE WORKER : worker who's lease is expired while its code is still active in background.


CLAIM GENERATION BLINDNESS :

to mark a job status from running to succeeded, WHERE status = 'running'.

- this check can lead to make WORKER A with expired lease still make status = succeeded as it had status = 'running' that was updated by WORKER B.


TESTS AND OBSERVATIONS :

TEST1 :

SEE THE HARM FIRST :

T=0s: Worker A ne job claim ki (attempts = 1, status = running). Email likhi (rowcount = 1). 45s sleep me gaya.

T=30s: Worker A ka event loop freeze tha, heartbeat nahi gayi. Reaper ne lease expire dekhi aur job ko wapas pending kar diya.

T=31s: Worker B ne wahi job claim kar li (attempts = 2, status = running). Worker B ne email likhni chahi, par UNIQUE constraint ne skip kar di (rowcount = 0). Worker B ab apna kaam kar raha hai.

T=45s (THE CORRUPTION):
Worker A ki 45s ki neend poori hui!

Worker A ne query chalayi: UPDATE jobs SET status='succeeded' WHERE id=$step1Job AND status='running'.

Kyunki Worker B ne status running kar rakha tha, Worker A ka update pass ho gaya (rowcount = 1)!

T=76s: Worker B ka kaam poora hua. Usne status succeeded mark karna chaha, par dekha status to pehle hi succeeded hai → Worker B ka mark fail ho gaya (rowcount = 0)!


TEST2 AFTER FENCING TOKEN :

TERMINAL :

[Worker A] Claimed job 60 (generation=1, attempt=1, rowcount=1). Status is now 'running'.
[Worker A] Executing job 60 (type=effect, generation=1, attempt=1/3)...
[Worker A] [SIDE EFFECT] Committed 'email' for job 60 (key='job:60:email', rowcount=1).
[Worker A] [email HANDLER] Blocking event loop (15s)...


REAPER TOOK THE JOB


[Worker B] Claimed job 60 (generation=2, attempt=2, rowcount=1). Status is now 'running'.
[Worker B] Executing job 60 (type=effect, generation=2, attempt=2/3)...
[Worker B] [SIDE EFFECT] Duplicate 'email' skipped for job 60 (key='job:60:email', rowcount=0).
[Worker B] [email HANDLER] Blocking event loop (15s)...



[Worker A] [email HANDLER] Work completed.
[Worker A] Finished execution for job 60.
[Worker A] Mark fenced: job_id=60 held_generation=1 rowcount=0

// held_generation 1 < current_generation 2 => purana worker
// worker A's rowcount = 0, rejected, no status updated.


[Worker B] [email HANDLER] Work completed.
[Worker B] Finished execution for job 60.
[Worker B] Marked job 60 as 'succeeded' (generation=2, rowcount=1).



har ek job keliye generation count 0 se start hoga, or monotonically agge hi badhega.

---

WEEK 4 - DAY 2



lets say we have 5000 job rows in job table, postgres doesn't store row1, row2... row 5000 linear file.

postgres stores and organizes data in pages :

HEAP PAGE :

HEAP

┌───────────────┐
│ Page 0        │ 8192 bytes
├───────────────┤
│ Page 1        │ 8192 bytes
├───────────────┤
│ Page 2        │ 8192 bytes
├───────────────┤
│ Page 3        │ 8192 bytes
├───────────────┤
│ ...           │
└───────────────┘


- each page has 8192 bytes ~ 8KB
- lets say we ave a row = 100 bytes, one 8KB page can fit roughly 8192 / 100 = 81 rows.

- usually successful/new jobs has NULL so its row is small.

- now worker polls every 2 seconds(search pending jobs in DB(postgres)), if postgres uses a sequential scan in a query, so worker needs to examine heap pages of table.

jobs table

Page 0
Page 1
Page 2
Page 3
...
Page 111

lets say table is 112 pages, so scan need to touch around 112 pages.

so 5000 job rows ab 112 heap pages me he

toh database ab har ek page inspect krega.

LETS say last_error aya and wo kuch zyada bada he ~400 bytes, toh ab ek job ki row moti hui.

- pehle 8KB ke page me bhot jobs fit thi, ab har job moti ho gyi bcz uska last_error aane laga.

- same 8KB page me kam jobs fit hongi, same 5000 job, now 250 pages.


- now agar worker 250 seuential scan krega to scan ka physical page workload substantially badh gaya.

TOAST : 

Agar row ke andar koi value bahut badi ho rahi hai, PostgreSQL usko handle karne ki koshish karta hai. compress krke

row ~10 KB -> compression -> 298 bytes(this change is done in main heap row, not in separate table)

NOW lets say we have 100 KB, and its not getting compressed sufficiently, so postgres has option :


Main jobs table
┌─────────────────────┐
│ id = 42             │
│ status = failed     │
│ last_error → pointer│
└─────────────────────┘
          │
          ▼
     TOAST table
┌─────────────────────┐
│ actual large value  │
└─────────────────────┘
store separately


100 KB
  ↓
compress
  ↓
still huge?
  ↓
TOAST storage


wrong thinking :

"Arey! last_error me agar Python ka 30-40 line ka lamba traceback daal diya, to row 2032 bytes cross kar jayegi aur TOAST table me chali jayegi. Jab worker poll karega to use TOAST table se data uthana padega aur system slow ho jayega!"

Facts :

Python traceback me repeated file paths (jaise C:\Users\Admin\..., line numbers, repeated words) hote hain.
PostgreSQL ka compression algorithm traceback ko 10:1 ratio me compress kar deta hai!
Yani 10 KB ka lamba traceback compress hokar sirf 298 bytes ka reh jata hai!
298 bytes threshold (2032 bytes) se bohot chhota hai, isliye wo hamesha main table ke andar hi rehta hai, kabhi TOAST table me nahi jata!

Asli Khatra TOAST nahi, HEAP PAGES hain!

Worker har 2 second me jobs dhundhne ke liye Sequential Scan chalata hai (poori table shuru se aakhri tak padhta hai).
Jab last_error = NULL tha, to 5,000 rows sirf 112 heap pages me fit aa jati thi.
Lekin jab har row me 200-300 bytes ka inline error jud gaya, to wahi 5,000 rows 250 heap pages me phail gayi!
Iska matlab: Worker ko har poll par 2.2 guna zyada disk I/O padhna padega!


Hum last_error ke size ko isliye bound (chhota) rakhte hain taaki main table ke heap pages kam rahein aur worker ka poll fast chale, TOAST table se bachne ke liye nahi!


Graceful Shutdown ka wada: Worker ko jab band karne ka signal (SIGBREAK / Ctrl+C) milta hai, to wo bolta hai: "Main chalu job ko adhoora nahi chhodunga, poora karke hi exit karunga."
Lease ka niyam: Reaper har job ko sirf 30 second ki lease deta hai.
Ab sochiye: Agar job 45 second lambi ho, aur T=3s par shutdown signal aa jaye:
Shutdown pehle poora hoga ya lease pehle expire hogi? Aur jab Reaper beech me job chheen lega, to 45s baad worker jab status likhne aayega to kya hoga?


time.sleep ne event loop freeze kar diya, heartbeat band ho gayi!
Timeline:
T=3s par signal aaya, worker shutdown mode me gaya. T=30s par Reaper ne dekha heartbeat nahi aayi, usne job ko reclaim karke pending kar diya! T=45s par Worker A ki neend khuli aur usne status succeeded likhna chaha.
THE DISCOVERY: Kyunki kal humne claim_generation fencing gate lagaya tha, isliye Database ne Worker A ka update reject kar diya!
Worker A ne log kiya: Mark fenced ... rowcount=0.


Worker A freeze hua → Reaper ne reclaim kiya → Worker B ne Generation 2 ke sath job utha li!
Worker A jaaga aur status likhna chaha with Generation 1 → FENCE FIRED!
Worker B ne Generation 2 ke sath kaam khatam karke status succeeded mark kiya.
Database me side-effects sirf 1 raha, status sahi worker se mark hua, aur Worker A chup-chaap exit ho gaya!


FULL DAY :

Dono columns (completed_at, last_error) sirf jobs table me add hote hain.
worker.py me status marks ke sath completion timestamp aur error clearing lag chuka hai.
TOAST se zyada main table ke Heap Pages matter karte hain sequential scan ke liye.
boom job retry aur lifecycle log ko prove karti hai, aur SQL se pehla latency number nikalta hai.
SIGBREAK run prove karta hai ki chahe worker graceful shutdown me ho, agar lease expire ho gayi to Fencing Token use database corrupt nahi karne dega! 🚀


 id | type |   status    | attempts | claim_generation |         completed_at          |            last_error            |    duration     
----+------+-------------+----------+------------------+-------------------------------+----------------------------------+-----------------
 62 | boom | dead_letter |        3 |                3 | 2026-09-08 19:13:29.708878+00 | Simulated handler failure: BOOM! | 00:00:46.819622



 n |       p50       |       p99       |  min_duration   |  max_duration   
---+-----------------+-----------------+-----------------+-----------------
 2 | 00:00:44.421245 | 00:00:46.771654 | 00:00:42.022867 | 00:00:46.819622
(1 row)

   status    | count |       p50       
-------------+-------+-----------------
 dead_letter |     2 | 00:00:44.421245


n = db me two terminal jobs jiska completed_at record hua
p50 = 44.4s: Aadhi jobs lagbhag 44 seconds me finish hui.
p99 = 46.7s: 99% jobs 46.7 seconds ke andar khatam ho gayi!

---

week 4 - day 3 :


Maan lijiye aapke system ko do kaam karne hain:

Database me likhna ki order complete ho gaya (side_effects table).

Customer ko email ya Stripe payment API call karni hai (POST /charge).


Agar pehle Database me commit kiya, aur uske baad API call fail ho gayi (network cut gaya), to database bolega kaam ho gaya, par email/paisa kabhi gaya hi nahi!

Agar pehle API call ki aur wo chali gayi, par uske baad Database commit fail ho gaya (power cut), to customer ke paise cut gaye par database me koi record hi nahi hai!


PostgreSQL ka COMMIT sirf database ke andar atomic hota hai, wo bahar ke internet/API call ko rollback nahi kar sakta! Is problem ko bolte hain "Dual Write Problem".


Solution: "Transactional Outbox Pattern"
Hum API call seedha worker se nahi karenge!

Worker ek hi transaction ke andar do cheezein likhega:

- Asli side-effect (side_effects table).
- Bhejne ka irada (outbox table me ek row: "Yeh email bhejna baki hai").

Ek COMMIT: Ya to dono tables me row likhi jayegi, ya kisi me nahi!

Phir ek alag process (src/dispatcher.py) aayega, wo outbox table se pending rows padhega aur bahar ke receiver (src/sink.py) ko HTTP request bhejega.


```
lets say we have two work to do in a transaction, and one work has background work, so we put that into queue :

BEGIN
  ↓
db_op1()
  ↓
queue_job()
  ↓
db_op2()
  ↓
COMMIT

now, if db_op1() data got inserted into db and job is queued, so when worker executes this job, data will be in database?

- no, data is in transaction, transaction is not yet committed.

RACE CONDITION :

now db_op1() does insert user id and email
- but transaction is not yet committed, then queue_job() will send this job into queue.
- lets say queue is extremely fast so it picks this immediately, not it does select user, but its not found as data is not yet committed, while user is inserted into uncommitted transaction, yet user is not visible to another transaction(get user).
- worker ran before commit.
```

 imagine db_op1() inserts a user record. queue_job() puts a job in the queue to retrieve that record, and add that user’s email address (along with a unique internal ID) to an email whitelist managed by another service. A background worker dequeues the job, but finds that the user record it’s looking for is nowhere to be found in the database.

- User DOES exist conceptually,
but the transaction that inserted it hasn't committed yet.

- if transaction gets rollback :

insert user 43, Queue job 20, db_op2() fails, rollback.

- if this happens again and again, worker will try 100 attempts and user 43 still doesn't exist.

- SO, retry is not a solution to every failure.


so why dont we do :
- begin transaction -> create user -> commit, then Queue job ?

this solves one problem only to introduce another:

API PROCESS

BEGIN
  ↓
INSERT user
  ↓
COMMIT ✅
  ↓
💥 CRASH
  ↓
queue_job() never runs


just after commit and before Queue job, application crashed, now user exist in db, but job doesn't exist in queue(email never sent).

- this problem doesn't even give any error, no log, no retry.

- can we just add retry ?
worker starts at 10 ms -> attempt 1 -> fail -> retry after 1 sec -> 1010ms -> so attempt 2 success.

Attempt 1 → expected failure
Attempt 2 → maybe expected failure
Attempt 3 → maybe succeeds

this is a timing assumption, also in high traffic, repeated retry and failed attempts would make a LOT executions(lot of wasted work is done), worker unnecessarily consumes cpu, db conn, db queries, network calls, logs, retry storage, lot of errors etc.


SO WHAT CAN WE DO FOR THIS PROBLEM ?

Problem: DB transaction aur external queue ko directly coordinate karoge toh ya toh job too early run ho sakti hai, ya lost ho sakti hai.

solution : Queue ko transaction ke andar directly touch hi mat karo. Pehle job ko same DB transaction mein ek staging table mein save karo. Commit ke baad ek separate process us staged job ko actual queue mein bheje.


so after commit :
COMMIT ✅
        ↓
job visible
        ↓
enqueuer can take it


so now architecture : 

Application
    ↓
DB transaction
    ↓
staged_jobs table
    ↓
does other execution
    ↓
COMMIT

then AFTER commit, separately :

Enqueuer
    ↓
staged_jobs
    ↓
actual queue(when job is safely committed)
    ↓
Worker

-jobs are not immediately sent to job queue, it first sets in staged_jobs(waiting area), we dont touch queuing in transaction.

Transaction A
     ↓
INSERT staged job
     ↓
uncommitted
     ↓
❌ Enqueuer cannot see it
DUE to the ACID properties of the running transaction keep them invisible until they’re ready to be worked.

1. Application

Creates DB data + staged job.

2. Enqueuer

Moves staged job → actual queue. delete staged job row.

3. Worker

Actually performs the job.


- if enqueuer crashes, still at least once delivery are guaranteed, but duplication can happen :

eg : staged_jobs :
1,2,3,4

enueued : 1,2,3 CRASH
NOW when enueuer restarts :
job 1 → enqueue again
job 2 → enqueue again
job 3 → enqueue again
job 4 → enqueue

so this can make duplicates, but permanent loss is avoided with atleast once delivery. 0 execution is avoided but 2 executions can happen.

IN ROLLBACK, THIS stays safe :

BEGIN
 ↓
INSERT user
 ↓
INSERT staged_job
 ↓
ERROR
 ↓
ROLLBACK

so user and staged_job both doesn't have this job data.

TESTS AND OBSERVATIONS :

TEST 1 :

relay/sink.py
 banaya (FastAPI receiver on port 8001) with endpoint POST /deliver.
Isme receiver-side idempotency (ON CONFLICT DO NOTHING on idempotency_key) aur ek DEDUP_OFF switch diya.
Dedup ON (DEDUP_OFF=0): Same idempotency key se 2 baar POST kiya.
Dedup OFF (DEDUP_OFF=1): Nayi idempotency key se 2 baar POST kiya.

Network par at-least-once delivery me duplicate calls aana natural hai. Receiver ko pata hona chahiye ki kya request nayi hai (applied) ya duplicate hai (duplicate).


OBSERVATIONS :

DEDUP ON :

Request 1 -> [deliver] idempotency_key=w4d3-manual-... result=applied (HTTP 200)
Request 2 -> [deliver] idempotency_key=w4d3-manual-... result=duplicate (HTTP 200)
sink_deliveries rows: 1


DEDUP OFF :

Request 1 -> [deliver] idempotency_key=w4d3-manual-off-... result=applied (HTTP 200)
Request 2 -> [deliver] idempotency_key=w4d3-manual-off-... result=applied (HTTP 200)
sink_deliveries rows: 2


Receiver ka dedup switch positively prove ho gaya: Dedup ON hone par duplicate reject hota hai aur table me sirf 1 row aati hai; Dedup OFF hone par wahi same request 2 rows bana deti hai.


TEST 2 :

dispatched_at : Outbox mein jo event/job abhi dispatch nahi hua (dispatched_at IS NULL), usko uthao → sink ko bhejo → successfully bhejne ke baad dispatched_at bhar do.
(ye outbox table me job save kiya hue ko actual queue/sink tk bhejta he)

flow :
BEGIN
 ↓
row lock
 ↓
HTTP call
 ↓
dispatched_at update
 ↓
COMMIT

if dispatcher crashes, db rollbacks, and dispatched_at is not updated(so it says this job is not yet dispatched)


TEST 3(THE CORE) :

Outbox pattern at-least-once delivery deta hai, exactly-once nahi.
Jab dispatcher HTTP 200 lene ke baad aur DB mark karne se pehle mar jata hai, to recovery ke waqt wahi delivery dobara network pe jayegi (2 requests).

Agar receiver ke paas dedup ON hai (Run A) to application safe hai. Agar receiver ke paas dedup OFF hai (Run B) to double execution / duplicate records create ho jate hain.


Run A (Dedup ON + Crash After HTTP):

Job 65 enqueue ki (crash_at: 'after_http'). Worker ne 1 side_effect + 1 outbox row banayi.

Dispatcher Attempt 1: Sink ko POST bheja (result: applied). Lekin mark karne se pehle crash ho gaya (os._exit(1)). Transaction rollback ho gayi, row unlock ho gayi, dispatched_at NULL raha.

Dispatcher Attempt 2 (Recovery): Dispatcher ne row dobara pick ki, sink ko dobara POST bheja (result: duplicate). Dispatcher ne safely mark karke commit kiya. NO EXTERNAL REAPER NEEDED IF DISPATCHER CRASHES AND TO BRING IT BACK/RETRY, ROLLBACK DOES THE WORK.


Run B (Dedup OFF + Crash After HTTP):

Job 66 enqueue ki (crash_at: 'after_http'). Worker ne 1 side_effect + 1 outbox row banayi.

Dispatcher Attempt 1: Sink (dedup off) ko POST bheja (result: applied). 

Dispatcher crash hua (os._exit(1)).

Dispatcher Attempt 2 (Recovery): Sink ko dobara POST bheja (result: applied). Dispatcher commit hua.


run A : SINK HTTP Requests: 2(applied, duplicate).
       SIDE EFFECTS row = 1
      SINK_DELIVERIES row = 1(deduplication protected)

run B : SINK HTTP Requests: 2(applied, APPLIED).
       SIDE EFFECTS row = 1
      SINK_DELIVERIES row = 2(deduplication inserted).


Outbox dual-write ko khatam karta hai, duplicate delivery ko nahi: Worker aur Outbox ek atomic boundary me hain, par dispatcher crash hone par network pe 2 deliveries jati hain.
Exactly-Once is an end-to-end property: Outbox at-least-once delivery ensure karta hai; receiver-side deduplication uske upar milkar system ko effectively "exactly-once" banata hai. Run B ne prove kiya ki bina receiver dedup ke outbox duplicate effects ko rok nahi sakta.

---

WEEK 4 - DAY 4


Iss project me jo bhi safety claim likha hai (jaise "fencing stale writes ko rokti hai", ya "dedup duplicate side effects ko rokti hai"), wo usi code path ke against measure hona chahiye jo production me chalta hai — kisi mathematical model ya test mock ke against nahi. Aur ye measurement evidence database (relay) ko bina chhue witness DB par repeat kiya ja sake.

ye saare test WITNESS DB pr chale jo temporary database create kiya :

alembic.ini me database URL hardcoded thi. Agar hum bina guard ke migration chalate to wo temporary DB ke bajaye permanent DB ko alter kar deta.
Isko rokne ke liye Pre-flight Check lagaya gaya: Har process (API, Worker A, Worker B, Reaper, Dispatcher) startup par print karta hai [db] resolved_db=relay_w4_witness. Agar koi ek bhi relay bolta, to run abort ho jata.
Day 4 ka sabse aakhri check ye tha ki evidence DB me 53 jobs the aur aakhri me bhi exact 53 hi bache!


TEST 1 : mark fenced

Jab ek worker kisi slow ya blocking task me phans jata hai aur uska heartbeat band ho jata hai:

Worker A job claim karta hai (claim_generation = 1).
Worker A 15 second ke liye block hota hai (time.sleep(15)).
5 second baad lease expire hoti hai. Reaper job ko reclaim karta hai (status = 'pending').
Worker B job ko claim karta hai (claim_generation = 2).
Worker B execution khatam karke job ko succeeded mark kar deta hai (claim_generation = 2).
Worker A 15 second baad neend se jaagta hai! Wo sochta hai "mera kaam ho gaya, ab main success mark karta hoon".
Worker A mark query chalata hai:

UPDATE jobs SET status='succeeded', completed_at=clock_timestamp()
WHERE id = 2 AND status = 'running' AND claim_generation = 1;

CAS Fencing Action: Rowcount milta hai 0!
Worker A turant DB me dekhta hai ki actual_generation = 2 hai jabki uske paas held_generation = 1 tha.
Worker A log karta hai: [worker-8820] Mark fenced: job_id=2 worker_id=worker-8820 held_generation=1 actual_generation=2 rowcount=0 event=fenced


Snapshot 1 (Pre-Reaper): Job ID 2, status='running', claim_generation=1, attempts=1.
Snapshot 2 (Post-Reaper): Job ID 2, status='pending', claim_generation=1, attempts=1.
Snapshot 3 (Terminal): Job ID 2, status='succeeded', claim_generation=2, attempts=2.
Job Executions Table: 2 distinct worker executions: (worker-8820, gen=1) aur (worker-15252, gen=2).
Side Effects Table: Exactly 1 row (job:2:email).


NOTE : WORKER A KI LEASE KESE RUKI :
- Agar payload me asyncio.sleep(15) hota, to Python ka event loop chalta rehta aur background me send_heartbeat coroutine har 10s me claimed_at = now() update karti rehti! Lease kabhi expire hi nahi hoti!
Humne block: true karke time.sleep(15) chalaya, jisne Python OS thread aur event loop dono ko freeze (block) kar diya.
Is wajah se heartbeat ruk gayi aur Reaper ko lease expire mili


TEST 2 : side effect dedup

Worker ne external effect commit kiya, lekin network/system uske baad crash ho gaya:

Worker A job claim karta hai (claim_generation=1).
Worker A record_side_effect chalata hai -> side_effects table me row insert hoti hai aur commit ho jati hai.
Commit ke turant baad Worker A crash ho jata hai (payload: {crash_at: 'after_effect'} -> os._exit(1)).
Job DB me status='running' reh jati hai.
Lease expire hone par Reaper isko reclaim karta hai (status='pending').
Worker B job ko claim karta hai (claim_generation=2) aur dobara wahi handler execute karta hai.
Worker B jab record_side_effect chalata hai, to uq_side_effects_effect_key par conflict hota hai.
on_conflict_do_nothing() trigger hota hai aur rowcount = 0 milta hai.
Worker B log karta hai: [SIDE EFFECT] Duplicate 'email' skipped for job 3 (key='job:3:email', rowcount=0).
Worker B job ko succeeded mark karta hai.


Total Worker Executions: 2 (worker-17952 aur worker-14252).
Total side_effects Rows: Exactly 1 row!
Conclusion: D-25 design rule production path par successfully verify hua: handler ke multiple executions ke bawajood business side-effect duplicate nahi hua.



TEST 3 : Poison Pill Loop


Job ka payload har attempt par before_commit crash trigger karta hai:

Worker job claim karta hai -> handler dono rows insert karne ki koshish karta hai -> os._exit(1).
PostgreSQL transaction abort ho jati hai. DB me 0 rows likhi jati hain.
Lekin PostgreSQL sequences (id_seq) transaction rollback ke bawajood wapas peeche nahi aate (sequences monotonic hote hain).
Worker mar chuka hai, to except Exception wala MAX_ATTEMPTS dead-letter branch kabhi nahi chalta.
Reaper job ko wapas reclaim karta hai, aur loop chalta rehta hai.


Measured Observations (3 Iterations Run):

Initial Sequences: side_effects_id_seq = 7, outbox_id_seq = 7.
Iteration 1: Worker crashed via os._exit(1). Job state: running -> pending.
Iteration 2: Worker crashed via os._exit(1). Job state: running -> pending.
Iteration 3: Worker crashed via os._exit(1).
Committed DB Rows: side_effects = 0, outbox = 0.
Final Sequences: side_effects_id_seq = 10, outbox_id_seq = 10.
Sequence Delta: +3 in side_effects, +3 in outbox.

Conclusion & Proof of P-36: Har crash iteration par database me 0 rows commit hoti hain, par har iteration 1 sequence number permanently burn kar deti hai. Aur iteration ka cycle period application backoff se nahi, balki reaper ke lease timeout (~5s) se drive hota hai!


TEST 4 :

Outbox table se HTTP dispatch karte waqt agar dispatcher crash ho ya do dispatchers ek saath deliver karein:

Outbox me row create hoti hai with payload: {crash_at: "after_http"}.
Dispatcher 1 HTTP POST bhejta hai sink ko (http://127.0.0.1:8011/deliver).
Sink delivery save kar leta hai (result = applied).
Dispatcher 1 mark karne se pehle crash ho jata hai (os._exit(1)).
Do dispatchers concurrently recovery attempt karte hain.
Sink receiver ke paas uq_sink_deliveries_idempotency_key constraint laga hua hai.
Ek request applied hoti hai aur baaki saari requests duplicate return hoti hain.
Sink deliveries table me exactly 1 row save hoti hai.


Serial Delivery: first=applied, second=duplicate -> 1 row in DB.
Concurrent 
N
=
2
N=2: ['duplicate', 'applied'] -> 1 row in DB.
Concurrent 
N
=
5
N=5: ['applied', 'duplicate', 'duplicate', 'duplicate', 'duplicate'] -> 1 row in DB.

Conclusion: Receiver-side idempotency constraint race conditions ko 100% defeat karta hai.



TEST 5 : concurrent claim with for update skip locked

Jab 1 pending job ho aur do workers exact same millisecond par use claim karne aate hain:

Worker A aur Worker B dono SELECT ... FOR UPDATE SKIP LOCKED execute karte hain.
PostgreSQL row-level lock Worker A ko milta hai.
Worker B block nahi hota (zero delay), balki wo us row ko skip karke khaali haath laut jata hai (rowcount = 0).


Measured Output:

Worker A Result: ('Worker_A', 'CLAIMED', job_id=7).
Worker B Result: ('Worker_B', 'EMPTY_SKIPPED', None).
Conclusion: Exactly 1 worker ne claim kiya, rival process block nahi hua aur conflict error ke bina clean empty skip mila.


Conclusion: Zero lock contention: Exactly 1 worker ne claim kiya, rival process bina kisi delay ke clean empty skip ke saath laut gaya.

---

WEEK 4 - DAY 5

"Relay Ko Todo, Aur Naam Se Todo: Pool Exhaustion, Sustained Load, Postgres-Down, Aur /healthz Ka Sach"

- Pehle ke dino me humne Relay ke safety features (fencing, outbox, dedup) ko ek-ek karke verify kiya. Din 5 ka maksad Relay ko todna (break karna) hai — par bina samjhe nahi, balki "naam se todna". Hume ye prove karna hai ki jab system bohot heavy load me aata hai ya database crash hoti hai, to system kis tarike se degrade hota hai, uska pehla bottleneck (binding constraint) kaunsa banta hai, aur wo exact kaunsa error deta hai.

- Aaj ka saara heavy load testing, pool exhaustion, aur database band karne ka dangerous kaam sirf aur sirf Disposable Witness DB par chalega.
- Permanent Evidence DB (relay) ka delta strictly 0 hona chahiye (ek bhi nayi row nahi jaani chahiye).
- Ek aur zaroori rule: Aaj ke din ke baad Evidence DB (relay) Alembic ke HEAD revision par upgraded honi chahiye.


pool_size: Engine kitne active database connections ko future queries ke reuse ke liye hamesha zinda rakhta hai.

max_overflow: Jab load peak par ho aur pool_size ke saare connections busy hon, to engine temporary taur par kitne extra connections khol sakta hai. (Kaam khatam hote hi overflow connections band ho jaate hain).

pool_timeout: Agar pool_size + max_overflow ke saare connections busy hain, to naya aane wala request kitne seconds tak line (queue) me khada hokar intezaar karega. Default: 30 seconds. 30s ke baad ye TimeoutError phenk deta hai.

max_connections: PostgreSQL server ka overall global limit (default 100). Isse zyada connection pura server accept nahi karega.

superuser_reserved_connections: max_connections me se kitni connections superuser (postgres) ke emergency login ke liye reserve rehti hain (default: 3).

pg_stat_activity: PostgreSQL ka real-time system view jo batata hai ki kaunsa backend process active hai, kaunsa idle hai, kaunsa lock ke liye wait kar raha hai (wait_event), aur kis query par atka hai.

application_name: Client ka apna naam jo pg_stat_activity me chhapta hai (e.g. relay-api, relay-worker).

pool_pre_ping: SQLAlchemy ka flag jo pool se connection nikal kar query chalane se pehle ek sasta check (SELECT 1) karta hai taaki ye pata chal sake ki kya connection abhi bhi zinda hai ya Postgres peeche se band ho chuka hai.

Liveness vs Readiness:

Liveness: "Kya mera process zinda hai ya crash ho gaya?" (Agar zinda hai to restart mat karo).

Readiness: "Kya mera process is waqt traffic lene ke kabil hai ya DB/pool full hone ki wajah se saturated hai?" (Traffic mat bhejo, par kill bhi mat karo).


TESTS AND OBSERVATIONS :

Engine Defaults:
SQLAlchemy default: pool_size = 5, max_overflow = 10.
Iska matlab ek single engine maximum 15 connections le sakta hai.

Processes Count:
Hamare paas 5 processes hain: API (uvicorn) + Worker A + Worker B + Reaper + Dispatcher = 5 engines

Teen Numbers Calculate Karna:
- Ceiling (Maximum theoretical limit): 5 processes × 15 connections = 75 connections (+ psql sessions + test scripts). Total ≈80 connections. Postgres limit 100 hai, to ye safe margin me hai.
- Idle State: Jab saare 5 process shuru ho chuke hain par koi kaam nahi kar rahe, to DB connections kitni hain? (Kyunki pool lazy hai, ye number ceiling se bohot kam hoga).
- Peak State: Load ke waqt kitni connections khulti hain.

application_name Set Karna:
src/database.py me connect_args={"server_settings": {"application_name": "..."}} daalna taaki pg_stat_activity me har process ka alag naam dikhe.


TEST1 : 

