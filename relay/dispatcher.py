import asyncio
import os
import signal
import sys
from typing import Any
import httpx
from sqlalchemy import func, select, update

from relay.db import async_session
from relay.models import Outbox

DISPATCHER_ID = f"dispatcher-{os.getpid()}"
SHUTDOWN_REQUESTED = False
SINK_URL = os.getenv("SINK_URL", "http://127.0.0.1:8001/deliver")
POLL_INTERVAL_SECONDS = 2.0


def request_shutdown(signum: int, frame: Any) -> None:
    global SHUTDOWN_REQUESTED
    sig_name = signal.Signals(signum).name
    print(
        f"\n[{DISPATCHER_ID}] Signal {sig_name} received. Finishing current dispatch before shutdown...",
        flush=True,
    )
    SHUTDOWN_REQUESTED = True


async def run_dispatcher() -> None:
    print(
        f"[{DISPATCHER_ID}] Starting dispatcher process (PID: {os.getpid()})...",
        flush=True,
    )

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, request_shutdown)

    async with httpx.AsyncClient(timeout=5.0) as client:
        while not SHUTDOWN_REQUESTED:
            dispatched_any = False

            async with async_session() as session:
                async with session.begin():
                    # Pick 1 undispatched row with FOR UPDATE SKIP LOCKED
                    query = (
                        select(Outbox)
                        .where(Outbox.dispatched_at.is_(None))
                        .order_by(Outbox.created_at, Outbox.id)
                        .limit(1)
                        .with_for_update(skip_locked=True)
                    )
                    result = await session.execute(query)
                    outbox_row = result.scalar_one_or_none()

                    if outbox_row:
                        dispatched_any = True
                        delivery_payload = {
                            "idempotency_key": outbox_row.effect_key,
                            "job_id": outbox_row.job_id,
                            "body": outbox_row.payload or {},
                        }

                        try:
                            # Send HTTP POST to sink receiver
                            resp = await client.post(
                                SINK_URL, json=delivery_payload
                            )
                            resp_data = resp.json()
                            res_text = resp_data.get("result", "unknown")

                            # Reusable crash hook: after_http
                            crash_trigger = (
                                (
                                    outbox_row.payload
                                    and outbox_row.payload.get("crash_at")
                                    == "after_http"
                                )
                                or os.getenv("CRASH_AT") == "after_http"
                            ) and os.getenv("DISABLE_CRASH") != "1"

                            if crash_trigger:
                                print(
                                    f"[{DISPATCHER_ID}] CRASH: crash_at='after_http' job_id={outbox_row.job_id} outbox_id={outbox_row.id}! Exiting via os._exit(1)...",
                                    flush=True,
                                )
                                os._exit(1)

                            # Mark dispatched_at inside transaction
                            outbox_row.dispatched_at = func.clock_timestamp()
                            outbox_row.attempts += 1
                            await session.flush()

                            print(
                                f"[{DISPATCHER_ID}] [dispatch] job_id={outbox_row.job_id} outbox_id={outbox_row.id} effect_key={outbox_row.effect_key} result={res_text}",
                                flush=True,
                            )
                        except Exception as exc:
                            outbox_row.attempts += 1
                            outbox_row.last_error = str(exc)
                            await session.flush()
                            print(
                                f"[{DISPATCHER_ID}] [dispatch_error] job_id={outbox_row.job_id} outbox_id={outbox_row.id}: {exc}",
                                flush=True,
                            )

            if not dispatched_any:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)

    print(
        f"[{DISPATCHER_ID}] Clean shutdown complete. Exiting with code 0.",
        flush=True,
    )
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(run_dispatcher())
