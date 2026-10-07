import asyncio
import os
import random
import signal
import sys
import time
from collections.abc import Callable, Coroutine
from typing import Any
from sqlalchemy import func, insert, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert

from relay.db import async_session
from relay.models import Job, JobExecution, Outbox, SideEffect, LlmCall


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



async def record_side_effect(
    job_id: int, worker_id: str, action: str = "email", payload: dict | None = None
) -> int:
    """Inserts a business side-effect record AND outbox row in ONE atomic transaction.
      return rowcount = 1 if inserted else 0 if duplicate skipped."""
    effect_key = f"job:{job_id}:{action}"  # Stable key across all retries/workers

    stmt_effect = insert(SideEffect).values(
        job_id=job_id,
        worker_id=worker_id,
        action=action,
        effect_key=effect_key,
    ).on_conflict_do_nothing(constraint="uq_side_effects_effect_key")

    stmt_outbox = insert(Outbox).values(
        job_id=job_id,
        effect_key=effect_key,
        payload=payload or {},
    )

    async with async_session() as session:
        async with session.begin():
            result = await session.execute(stmt_effect)
            rowcount = result.rowcount
            await session.execute(stmt_outbox)

            # Reusable crash hook: before_commit
            if payload and payload.get("crash_at") == "before_commit":
                print(
                    f"[{worker_id}] CRASH: crash_at='before_commit' triggered! Exiting via os._exit(1)...",
                    flush=True,
                )
                os._exit(1)

    if rowcount == 1:
        print(
            f"[{worker_id}] [SIDE EFFECT] Committed '{action}' for job {job_id} (key='{effect_key}', rowcount=1).",
            flush=True,
        )
    else:
        print(
            f"[{worker_id}] [SIDE EFFECT] Duplicate '{action}' skipped for job {job_id} (key='{effect_key}', rowcount=0).",
            flush=True,
        )
    return rowcount


async def handle_email(payload: dict) -> None:
    """Handler that produces a persistent side-effect and supports payload-driven duration."""
    seconds = payload.get("seconds", 0.0)
    job_id = payload.get("job_id", 0)  # Pass job_id in payload if needed

    print(
        f"[{WORKER_ID}] [email HANDLER] Work started (duration={seconds}s)...",
        flush=True,
    )
    await record_side_effect(
        job_id=job_id, worker_id=WORKER_ID, action="email", payload=payload
    )

    if payload and payload.get("crash_at") == "after_effect":
        print(
            f"[{WORKER_ID}] CRASH: crash_at='after_effect' triggered for job_id={job_id}! Exiting via os._exit(1)...",
            flush=True,
        )
        os._exit(1)


    if seconds > 0:
        if payload.get("blocking", False) or payload.get("block", False):
            print(
                f"[{WORKER_ID}] [email HANDLER] Blocking event loop ({seconds}s)...",
                flush=True,
            )
            time.sleep(seconds)
        else:
            await asyncio.sleep(seconds)
    print(f"[{WORKER_ID}] [email HANDLER] Work completed.", flush=True)


async def handle_sleep(payload: dict) -> None:
    await asyncio.sleep(2.0)


async def handle_boom(payload: dict) -> None:
    raise RuntimeError("Simulated handler failure: BOOM!")


async def handle_slow(payload: dict) -> None:
    seconds = payload.get("seconds", 8.0)
    print(f"[{WORKER_ID}] [SLOW HANDLER] Work started ({seconds}s)...")
    await asyncio.sleep(seconds)
    print(f"[{WORKER_ID}] [SLOW HANDLER] Work completed.")


from relay.providers import (
    FakeProvider,
    GeminiProvider,
    ProviderError,
    ProviderBadRequestError,
    ProviderAuthError,
    ProviderServerError,
    ProviderRateLimitedError,
)


async def record_llm_call(
    job_id: int,
    claim_generation: int | None,
    result_text: str,
    tokens_in: int,
    tokens_out: int,
    status: str = "succeeded",
) -> None:
    async with async_session() as session:
        async with session.begin():
            await session.execute(
                insert(LlmCall).values(
                    job_id=job_id,
                    claim_generation=claim_generation,
                    result_text=result_text,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    status=status,
                )
            )


async def handle_llm_completion(payload: dict) -> tuple[str, int, int]:
    prompt = payload.get("prompt", "")
    provider_name = os.getenv("RELAY_LLM_PROVIDER", "fake")
    if provider_name == "gemini":
        provider = GeminiProvider()
    else:
        provider = FakeProvider()

    params = {}
    if "fake_mode" in payload:
        params["fake_mode"] = payload["fake_mode"]
    if "delay" in payload:
        params["delay"] = payload["delay"]
    if "fake_retry_after" in payload:
        params["fake_retry_after"] = payload["fake_retry_after"]
    if "fail_pct" in payload:
        params["fail_pct"] = payload["fail_pct"]

    text, tokens_in, tokens_out = await provider.complete(prompt, **params)
    job_id = payload.get("job_id", 0)
    claim_gen = payload.get("claim_generation")
    print(f"[{WORKER_ID}] [llm] job_id={job_id} tokens_in={tokens_in} tokens_out={tokens_out}", flush=True)

    try:
        await record_llm_call(
            job_id=job_id,
            claim_generation=claim_gen,
            result_text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            status="succeeded",
        )
    except Exception as llm_db_exc:
        print(
            f"[{WORKER_ID}] [P-60] record_llm_call failed: {type(llm_db_exc).__name__}: {llm_db_exc}. LLM call succeeded, suppressing retry to prevent duplicate billing.",
            flush=True,
        )
    return text, tokens_in, tokens_out


REGISTRY: dict[str, Callable[[dict], Coroutine[Any, Any, Any]]] = {
    "sleep": handle_sleep,
    "boom": handle_boom,
    "slow": handle_slow,
    "email": handle_email,
    "effect": handle_email,
    "llm_completion": handle_llm_completion,
}


async def record_execution(
    job_id: int, worker_id: str, claim_generation: int | None = None
) -> None:
    async with async_session() as session:
        async with session.begin():
            await session.execute(
                insert(JobExecution).values(
                    job_id=job_id,
                    worker_id=worker_id,
                    claim_generation=claim_generation,
                )
            )


async def send_heartbeat(
    job_id: int, stop_event: asyncio.Event, claim_generation: int, last_lease_refresh: list[float] | None = None
) -> None:
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=HEARTBEAT_INTERVAL_SECONDS
            )
            break
        except asyncio.TimeoutError:
            try:
                hb_sent = False
                hb_lost = False
                async with async_session() as session:
                    async with session.begin():
                        update_stmt = (
                            update(Job)
                            .where(
                                Job.id == job_id,
                                Job.status == "running",
                                Job.claim_generation == claim_generation,
                            )
                            .values(claimed_at=func.now())
                        )
                        result = await session.execute(update_stmt)
                        if result.rowcount == 0:
                            hb_lost = True
                        else:
                            hb_sent = True

                # Print outcome lines only after COMMIT has succeeded
                if hb_lost:
                    print(
                        f"[{WORKER_ID}] Heartbeat lost: job_id={job_id} worker_id={WORKER_ID} claim_generation={claim_generation} is no longer 'running' or fenced event=heartbeat_lost",
                        flush=True,
                    )
                    break
                if hb_sent:
                    if last_lease_refresh is not None:
                        last_lease_refresh[0] = time.time()
                    print(
                        f"[{WORKER_ID}] Heartbeat sent for job_id={job_id} worker_id={WORKER_ID} claim_generation={claim_generation} event=heartbeat",
                        flush=True,
                    )
            except Exception as exc:
                print(
                    f"[{WORKER_ID}] Heartbeat failed: {type(exc).__name__}: {exc} event=heartbeat_failed",
                    flush=True,
                )


async def run_worker() -> None:
    print(f"[{WORKER_ID}] Starting worker process (PID: {os.getpid()})...", flush=True)

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, request_shutdown)

    while not SHUTDOWN_REQUESTED:
        claimed_job = None

        conflict_job_id = None
        claim_print_info = None
        try:
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
                                claim_generation=Job.claim_generation + 1,
                            )
                            .returning(Job.claim_generation)
                        )
                        update_result = await session.execute(update_stmt)
                        current_generation = update_result.scalar_one_or_none()

                        if current_generation is None:
                            conflict_job_id = job.id
                        else:
                            current_attempts = job.attempts + 1
                            claimed_job = (
                                job.id,
                                job.type,
                                job.payload,
                                current_attempts,
                                current_generation,
                            )
                            claim_print_info = (
                                job.id,
                                WORKER_ID,
                                current_generation,
                                current_attempts,
                            )

                # Print outcome lines only after COMMIT has succeeded
                if conflict_job_id is not None:
                    print(
                        f"[{WORKER_ID}] Conflict: Job {conflict_job_id} was claimed by another writer (rowcount=0).",
                        flush=True,
                    )
                elif claim_print_info is not None:
                    c_jid, c_wid, c_gen, c_att = claim_print_info
                    print(
                        f"[{c_wid}] Claimed job_id={c_jid} worker_id={c_wid} claim_generation={c_gen} attempt={c_att} rowcount=1 event=claim. Status is now 'running'.",
                        flush=True,
                    )
        except Exception as exc:
            print(
                f"[{WORKER_ID}] Claim poll failed: {type(exc).__name__}: {exc}",
                flush=True,
            )
            claimed_job = None

        if not claimed_job:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            continue

        job_id, job_type, payload, current_attempts, current_generation = claimed_job
        handler = REGISTRY.get(job_type)
        next_attempt_at = None
        error_msg = None

        last_lease_refresh = [time.time()]
        if not handler:
            print(
                f"[{WORKER_ID}] Unknown job type: '{job_type}' job_id={job_id} worker_id={WORKER_ID} claim_generation={current_generation}. Marking failed.",
                flush=True,
            )
            new_status = "failed"
            error_msg = f"Unknown job type: '{job_type}'"
        else:
            # P-51: record_execution is an instrument write, outside handler try block and before heartbeat
            try:
                await record_execution(job_id, WORKER_ID, current_generation)
            except Exception as inst_exc:
                print(
                    f"[{WORKER_ID}] [P-51] record_execution failed: {type(inst_exc).__name__}: {inst_exc}. Abandoning iteration, leaving for reaper reclaim.",
                    flush=True,
                )
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue

            stop_event = asyncio.Event()
            heartbeat_task = asyncio.create_task(
                send_heartbeat(job_id, stop_event, current_generation, last_lease_refresh)
            )
            try:
                print(
                    f"[{WORKER_ID}] Executing job_id={job_id} worker_id={WORKER_ID} claim_generation={current_generation} type={job_type} attempt={current_attempts}/{MAX_ATTEMPTS} event=execute...",
                    flush=True,
                )

                payload["job_id"] = job_id
                payload["claim_generation"] = current_generation
                await handler(payload)
                print(f"[{WORKER_ID}] Finished execution for job_id={job_id} worker_id={WORKER_ID} claim_generation={current_generation}.", flush=True)
                new_status = "succeeded"
            except Exception as exc:
                error_msg = f"{type(exc).__name__}: {exc}"
                is_non_retryable = isinstance(exc, (ProviderBadRequestError, ProviderAuthError))
                if is_non_retryable:
                    new_status = "dead_letter"
                    next_attempt_at = None
                    print(
                        f"[{WORKER_ID}] Job_id={job_id} non-retryable {type(exc).__name__}: {exc}. Marking terminal 'dead_letter' immediately event=non_retryable.",
                        flush=True,
                    )
                elif current_attempts < MAX_ATTEMPTS:
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
                        f"[{WORKER_ID}] Job_id={job_id} failed attempt {current_attempts}/{MAX_ATTEMPTS}: {exc}. Scheduling retry in {actual_delay:.2f}s (new_status='pending') event=retry.",
                        flush=True,
                    )
                else:
                    new_status = "dead_letter"
                    print(
                        f"[{WORKER_ID}] Job_id={job_id} reached max_attempts ({MAX_ATTEMPTS}): {exc}. Marking terminal 'dead_letter' event=dead_letter.",
                        flush=True,
                    )
            finally:
                stop_event.set()
                try:
                    await heartbeat_task
                except Exception as exc:
                    print(
                        f"[{WORKER_ID}] Heartbeat task ended with exception: {type(exc).__name__}: {exc} event=heartbeat_ended",
                        flush=True,
                    )

        # Option 3 (Refined): Fast Bounded Backoff with Jitter & Mathematical Lease Guard
        # Guarantees:
        # 1. 1-2ms network glitches recover in ~200-300ms without burning extra attempts or triggering 30s Reaper wait.
        # 2. Jitter prevents Thundering Herd stampedes when multiple workers finish concurrently.
        # 3. Explicit Lease Guard checks remaining lease before every sleep to ensure retries NEVER run past lease expiry.
        MAX_MARK_RETRIES = 3
        MARK_BASE_DELAYS = [0.2, 0.5, 1.0]
        CLAIM_TIMEOUT_SECONDS = float(os.getenv("CLAIM_TIMEOUT_SECONDS", "30.0"))
        LEASE_SAFETY_MARGIN = 1.0
        mark_succeeded = False

        for mark_attempt in range(1, MAX_MARK_RETRIES + 1):
            mark_fenced_info = None
            mark_conflict_info = None
            mark_success_info = None
            try:
                async with async_session() as session:
                    async with session.begin():
                        mark_values = {
                            "status": new_status,
                            "next_attempt_at": next_attempt_at,
                        }
                        if new_status in ("succeeded", "dead_letter", "failed"):
                            mark_values["completed_at"] = func.clock_timestamp()

                        if new_status == "succeeded":
                            mark_values["last_error"] = None
                        elif error_msg is not None:
                            mark_values["last_error"] = error_msg

                        mark_stmt = (
                            update(Job)
                            .where(
                                Job.id == job_id,
                                Job.status == "running",
                                Job.claim_generation == current_generation,
                            )
                            .values(**mark_values)
                        )
                        mark_result = await session.execute(mark_stmt)
                        if mark_result.rowcount == 0:
                            check_stmt = select(Job.status, Job.claim_generation).where(Job.id == job_id)
                            check_res = await session.execute(check_stmt)
                            actual_row = check_res.first()
                            if actual_row and actual_row.claim_generation != current_generation:
                                mark_fenced_info = (job_id, WORKER_ID, current_generation, actual_row.claim_generation)
                            else:
                                mark_conflict_info = (job_id, WORKER_ID, current_generation)
                        else:
                            mark_success_info = (job_id, WORKER_ID, current_generation, new_status, mark_result.rowcount)
                        mark_succeeded = True

                # Print outcome lines only after COMMIT has succeeded
                if mark_fenced_info is not None:
                    m_jid, m_wid, m_cgen, m_agen = mark_fenced_info
                    print(
                        f"[{m_wid}] Mark fenced: job_id={m_jid} worker_id={m_wid} held_generation={m_cgen} actual_generation={m_agen} rowcount=0 event=fenced",
                        flush=True,
                    )
                elif mark_conflict_info is not None:
                    m_jid, m_wid, m_cgen = mark_conflict_info
                    print(
                        f"[{m_wid}] Conflict on mark: job_id={m_jid} worker_id={m_wid} claim_generation={m_cgen} status was modified by another transaction (rowcount=0) event=conflict",
                        flush=True,
                    )
                elif mark_success_info is not None:
                    m_jid, m_wid, m_cgen, m_status, m_rc = mark_success_info
                    print(
                        f"[{m_wid}] Marked job_id={m_jid} worker_id={m_wid} claim_generation={m_cgen} as '{m_status}' (rowcount={m_rc}) event=mark.",
                        flush=True,
                    )
                break
            except Exception as exc:
                if mark_attempt < MAX_MARK_RETRIES:
                    base_delay = MARK_BASE_DELAYS[mark_attempt - 1]
                    jitter = random.uniform(0.0, base_delay * 0.5)
                    retry_wait = base_delay + jitter

                    # Mathematical Lease Guard: check remaining time before sleeping
                    lease_deadline = last_lease_refresh[0] + CLAIM_TIMEOUT_SECONDS
                    remaining_after_wait = lease_deadline - (time.time() + retry_wait)

                    if remaining_after_wait < LEASE_SAFETY_MARGIN:
                        print(
                            f"[{WORKER_ID}] Terminal mark lease expiring (remaining after wait: {remaining_after_wait:.2f}s < {LEASE_SAFETY_MARGIN}s safety margin): {type(exc).__name__}: {exc}. Aborting retries to prevent Reaper collision event=mark_lease_abort.",
                            flush=True,
                        )
                        break

                    print(
                        f"[{WORKER_ID}] Terminal mark transient failure (attempt {mark_attempt}/{MAX_MARK_RETRIES}): {type(exc).__name__}: {exc}. Retrying in {retry_wait:.3f}s (base={base_delay}s, jitter=+{jitter:.3f}s, lease_remaining={remaining_after_wait:.2f}s)...",
                        flush=True,
                    )
                    await asyncio.sleep(retry_wait)
                else:
                    print(
                        f"[{WORKER_ID}] Terminal mark bounded retries exhausted ({MAX_MARK_RETRIES} attempts): {type(exc).__name__}: {exc}. Leaving in-flight for Reaper reclamation event=mark_failed.",
                        flush=True,
                    )

    print(f"[{WORKER_ID}] Clean shutdown complete. Exiting with code 0.", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(run_worker())