import asyncio
import os
import random
import signal
import sys
from collections.abc import Callable, Coroutine
from typing import Any
from sqlalchemy import func, insert, or_, select, text, update

from relay.db import async_session
from relay.models import Job, JobExecution


POLL_INTERVAL_SECONDS = 2.0
HEARTBEAT_INTERVAL_SECONDS = 10.0
MAX_ATTEMPTS = 3
BASE_BACKOFF_SECONDS = 3.0
BACKOFF_MULTIPLIER = 2.0
BACKOFF_CAP_SECONDS = 15.0
WORKER_ID = f"worker-{os.getpid()}"
SHUTDOWN_REQUESTED = False


def request_shutdown(signum: int, frame: Any) -> None:
    global SHUTDOWN_REQUESTED
    sig_name = signal.Signals(signum).name
    print(
        f"\n[{WORKER_ID}] Signal {sig_name} received. Finishing current job before shutdown..."
    )
    SHUTDOWN_REQUESTED = True


async def send_heartbeat(job_id: int, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=HEARTBEAT_INTERVAL_SECONDS
            )
            break
        except asyncio.TimeoutError:
            async with async_session() as session:
                async with session.begin():
                    update_stmt = (
                        update(Job)
                        .where(Job.id == job_id, Job.status == "running")
                        .values(claimed_at=func.now())
                    )
                    result = await session.execute(update_stmt)
                    if result.rowcount == 0:
                        print(
                            f"[{WORKER_ID}] Heartbeat lost: job {job_id} is no longer 'running'"
                        )
                        break
                    print(f"[{WORKER_ID}] Heartbeat sent for job {job_id}")


async def handle_sleep(payload: dict) -> None:
    await asyncio.sleep(2.0)


async def handle_boom(payload: dict) -> None:
    raise RuntimeError("Simulated handler failure: BOOM!")


async def handle_slow(payload: dict) -> None:
    print(f"[{WORKER_ID}] [SLOW HANDLER] Work started...")
    await asyncio.sleep(8.0)
    print(f"[{WORKER_ID}] [SLOW HANDLER] Work completed.")


REGISTRY: dict[str, Callable[[dict], Coroutine[Any, Any, None]]] = {
    "sleep": handle_sleep,
    "boom": handle_boom,
    "slow": handle_slow,
}


async def record_execution(job_id: int, worker_id: str) -> None:
    async with async_session() as session:
        async with session.begin():
            await session.execute(
                insert(JobExecution).values(
                    job_id=job_id,
                    worker_id=worker_id,
                )
            )


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
                    select(Job.id, Job.type, Job.payload, Job.attempts)
                    .where(
                        Job.status == "pending",
                        or_(
                            Job.next_attempt_at.is_(None),
                            Job.next_attempt_at <= func.now(),
                        ),
                    )
                    .order_by(Job.created_at, Job.id)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                result = await session.execute(claim_query)
                job = result.first()

                if job:
                    update_stmt = (
                        update(Job)
                        .where(Job.id == job.id, Job.status == "pending")
                        .values(
                            status="running",
                            claimed_at=func.now(),
                            attempts=Job.attempts + 1,
                        )
                    )
                    update_result = await session.execute(update_stmt)
                    if update_result.rowcount == 0:
                        print(
                            f"[{WORKER_ID}] Conflict: Job {job.id} was claimed by another writer (rowcount=0)."
                        )
                    else:
                        current_attempts = job.attempts + 1
                        claimed_job = (
                            job.id,
                            job.type,
                            job.payload,
                            current_attempts,
                        )
                        print(
                            f"[{WORKER_ID}] Claimed job {job.id} (attempt={current_attempts}, rowcount={update_result.rowcount}). Status is now 'running'."
                        )

        if not claimed_job:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            continue

        job_id, job_type, payload, current_attempts = claimed_job
        handler = REGISTRY.get(job_type)
        next_attempt_at = None

        if not handler:
            print(
                f"[{WORKER_ID}] Unknown job type: '{job_type}'. Marking failed."
            )
            new_status = "failed"
        else:
            stop_event = asyncio.Event()
            heartbeat_task = asyncio.create_task(
                send_heartbeat(job_id, stop_event)
            )
            try:
                print(
                    f"[{WORKER_ID}] Executing job {job_id} (type={job_type}, attempt={current_attempts}/{MAX_ATTEMPTS})..."
                )
                await record_execution(job_id, WORKER_ID)
                await handler(payload)
                print(f"[{WORKER_ID}] Finished execution for job {job_id}.")
                new_status = "succeeded"
            except Exception as exc:
                if current_attempts < MAX_ATTEMPTS:
                    delay = min(
                        BASE_BACKOFF_SECONDS
                        * (BACKOFF_MULTIPLIER ** (current_attempts - 1)),
                        BACKOFF_CAP_SECONDS,
                    )
                    actual_delay = (delay / 2.0) + random.uniform(
                        0, delay / 2.0
                    )
                    new_status = "pending"
                    next_attempt_at = func.now() + text(
                        f"interval '{actual_delay} seconds'"
                    )
                    print(
                        f"[{WORKER_ID}] Job {job_id} failed attempt {current_attempts}/{MAX_ATTEMPTS}: {exc}. Scheduling retry in {actual_delay:.2f}s (new_status='pending')."
                    )
                else:
                    new_status = "failed"
                    print(
                        f"[{WORKER_ID}] Job {job_id} reached max_attempts ({MAX_ATTEMPTS}): {exc}. Marking terminal 'failed'."
                    )
            finally:
                stop_event.set()
                await heartbeat_task

        async with async_session() as session:
            async with session.begin():
                mark_stmt = (
                    update(Job)
                    .where(Job.id == job_id, Job.status == "running")
                    .values(
                        status=new_status,
                        next_attempt_at=next_attempt_at,
                    )
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