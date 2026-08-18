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