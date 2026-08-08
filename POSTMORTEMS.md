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