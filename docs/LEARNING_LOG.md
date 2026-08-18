## Learning Summary


## Event loop + blocking work
→ use async/await (never block the event loop), use threads.

## Blocking I/O library
→ move blocking work to ThreadPool
→ increase workers if needed (limited solution)

## CPU-heavy Python work
→ ThreadPool is not enough (GIL)
→ use ProcessPool or Dedicated Worker Service

## SIGTERM
→ graceful shutdown (must do steps sequence)
→ finish current job → cleanup → exit

## SIGKILL
→ immediate termination
→ no cleanup
→ job may remain incomplete - solution : lease, heartbeat, reaper.

## Graceful Shutdown - steps
→ stop taking new jobs
→ finish current job
→ cleanup resources
→ exit (if done in limited timeline after sigterm, else sigkill)

## Kubernetes Pod Termination
→ stop routing traffic
→ send SIGTERM
→ wait (30s default)
→ if not finished → SIGKILL

## Lost Job Problem
→ job killed before DB update
→ DB status remains "running"
→ solved using Lease + Heartbeat + Reaper


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