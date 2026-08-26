# we cant ADD this reaper into worker.py, because if worker crash, reaper should not be dead with it.
# Postgres me now() transaction shuru hone ka time return karta hai. Agar transaction lambi chali to wo purani (stale) clock ke hisab se lease evaluate karega.

import asyncio
from datetime import datetime
import os
import signal
import sys
from typing import Any
from sqlalchemy import func, or_, select, text, update

from relay.db import async_session
from relay.models import Job


POLL_INTERVAL_SECONDS = 2.0
CLAIM_TIMEOUT_SECONDS = 5.0
REAPER_ID = f"reaper-{os.getpid()}"
SHUTDOWN_REQUESTED = False


def request_shutdown(signum: int, frame: Any) -> None:
    global SHUTDOWN_REQUESTED
    sig_name = signal.Signals(signum).name
    print(f"\n[{REAPER_ID}] Signal {sig_name} received. Shutting down...")
    SHUTDOWN_REQUESTED = True


async def reap_stuck_jobs() -> int:
    reclaimed_count = 0
    async with async_session() as session:
        async with session.begin():
            predicate = or_(
                Job.claimed_at.is_(None),
                Job.claimed_at < func.now() - text(f"interval '{CLAIM_TIMEOUT_SECONDS} seconds'"),
            )
            select_stmt = (
                select(Job.id, Job.status, Job.claimed_at)
                .where(Job.status == "running", predicate)
                .order_by(Job.id)
            )
            result = await session.execute(select_stmt)
            candidates = result.all()

            for candidate in candidates:
                update_stmt = (
                    update(Job)
                    .where(
                        Job.id == candidate.id,
                        Job.status == "running",
                        predicate,
                    )
                    .values(status="pending", claimed_at=None)
                    .returning(Job.status)
                )
                update_result = await session.execute(update_stmt)
                returned_row = update_result.first()
                matched = 1 if returned_row else 0
                post_status = returned_row[0] if returned_row else candidate.status
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                print(
                    f"[{REAPER_ID}] [{ts}] id={candidate.id} pre_status={candidate.status} matched={matched} post_status={post_status}"
                )
                if matched > 0:
                    reclaimed_count += matched

            if len(candidates) == 0:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                print(
                    f"[{REAPER_ID}] [{ts}] Pass completed: candidates=0 reclaimed=0"
                )

    return reclaimed_count


async def run_reaper() -> None:
    print(
        f"[{REAPER_ID}] Starting reaper process (PID: {os.getpid()}, poll={POLL_INTERVAL_SECONDS}s, lease={CLAIM_TIMEOUT_SECONDS}s)..."
    )

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, request_shutdown)

    while not SHUTDOWN_REQUESTED:
        await reap_stuck_jobs()
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

    print(f"[{REAPER_ID}] Clean shutdown complete. Exiting with code 0.")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(run_reaper())