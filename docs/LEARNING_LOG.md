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
```