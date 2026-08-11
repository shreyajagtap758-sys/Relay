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

