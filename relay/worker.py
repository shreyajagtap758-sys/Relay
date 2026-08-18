import asyncio
import os
import signal
import sys
from collections.abc import Callable, Coroutine
from typing import Any
from sqlalchemy import select, update

from relay.db import async_session
from relay.models import Job, JobExecution

POLL_INTERVAL_SECONDS = 2.0
WORKER_ID = f"worker-{os.getpid()}"
SHUTDOWN_REQUESTED = False


def request_shutdown(signum: int, frame: Any) -> None:
    global SHUTDOWN_REQUESTED
    sig_name = signal.Signals(signum).name
    print(
        f"\n[{WORKER_ID}] Signal {sig_name} received. Finishing current job before shutdown..."
    )
    SHUTDOWN_REQUESTED = True


async def handle_sleep(payload: dict) -> None:
    await asyncio.sleep(20)


async def handle_boom(payload: dict) -> None:
    raise RuntimeError("Simulated handler failure: BOOM!")


REGISTRY: dict[str, Callable[[dict], Coroutine[Any, Any, None]]] = {
    "sleep": handle_sleep,
    "boom": handle_boom,
}


async def run_worker() -> None:
    print(f"[{WORKER_ID}] Starting worker process (PID: {os.getpid()})...")

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, request_shutdown)

    while not SHUTDOWN_REQUESTED:
        claimed_job = None

        async with async_session() as session:
            async with session.begin():
                claim_query = (
                    select(Job.id, Job.type, Job.payload)
                    .where(Job.status == "pending")
                    .order_by(Job.created_at, Job.id)
                    .limit(1)
                    .with_for_update()
                )
                result = await session.execute(claim_query)
                job = result.first()

                if job:
                    update_stmt = (
                        update(Job)
                        .where(Job.id == job.id, Job.status == "pending")
                        .values(status="running")
                    )
                    update_result = await session.execute(update_stmt)
                    if update_result.rowcount == 0:
                        print(
                            f"[{WORKER_ID}] Conflict: Job {job.id} was claimed by another writer (rowcount=0)."
                        )
                    else:
                        claimed_job = (job.id, job.type, job.payload)
                        print(
                            f"[{WORKER_ID}] Claimed job {job.id} (rowcount={update_result.rowcount}). Status is now 'running'."
                        )

        if not claimed_job:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            continue


        job_id, job_type, payload = claimed_job

        async with async_session() as session:
            async with session.begin():
                execution = JobExecution(
                    job_id=job_id,
                    worker_id=WORKER_ID,
                )
                session.add(execution)


        handler = REGISTRY.get(job_type)

        if not handler:
            print(
                f"[{WORKER_ID}] Unknown job type: '{job_type}'. Marking failed."
            )
            new_status = "failed"
        else:
            try:
                print(f"[{WORKER_ID}] Executing job {job_id} (type={job_type})...")
                await handler(payload)
                print(f"[{WORKER_ID}] Finished execution for job {job_id}.")
                new_status = "succeeded"
            except Exception as exc:
                print(
                    f"[{WORKER_ID}] Job {job_id} raised an exception: {exc}. Marking failed."
                )
                new_status = "failed"

        async with async_session() as session:
            async with session.begin():
                mark_stmt = (
                    update(Job)
                    .where(Job.id == job_id, Job.status == "running")
                    .values(status=new_status)
                )
                mark_result = await session.execute(mark_stmt)
                if mark_result.rowcount == 0:
                    print(
                        f"[{WORKER_ID}] Conflict on mark: Job {job_id} status was modified by another transaction (rowcount=0)."
                    )
                else:
                    print(
                        f"[{WORKER_ID}] Marked job {job_id} as '{new_status}' (rowcount={mark_result.rowcount})."
                    )

    print(f"[{WORKER_ID}] Clean shutdown complete. Exiting with code 0.")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(run_worker())