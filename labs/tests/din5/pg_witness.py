import argparse
import asyncio
import ctypes
import json
import os
import re
import subprocess
import sys
import time
from typing import Any

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

# Target URL verification
TEST_URL = os.environ.get("DIN5_TEST_DATABASE_URL")
if not TEST_URL:
    print("FATAL: DIN5_TEST_DATABASE_URL is not set", file=sys.stderr)
    sys.exit(1)

# Ensure DATABASE_URL matches DIN5_TEST_DATABASE_URL for any imported Relay modules
os.environ["DATABASE_URL"] = TEST_URL

from sqlalchemy import create_engine, func, insert, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Guard check: target database name must match relay_din5_\d+_[0-9a-f]{8}
sync_url = TEST_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://")
sync_engine = create_engine(sync_url)
with sync_engine.connect() as conn:
    current_db = conn.scalar(text("select current_database()"))
sync_engine.dispose()

if not re.match(r"^relay_din5_\d+_[0-9a-f]{8}$", current_db):
    print(f"FATAL: Refusing target database '{current_db}' (must match relay_din5_*)", file=sys.stderr)
    sys.exit(1)

from relay.models import Job, JobExecution, SideEffect


def is_pid_alive(pid: int) -> bool:
    try:
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return code.value == 259
    except Exception:
        return False


def get_async_session():
    engine = create_async_engine(TEST_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory


# =========================================================================
# Scenario 1: baseline
# =========================================================================
async def run_baseline(output_path: str):
    engine, session_factory = get_async_session()
    worker_id = f"worker-baseline-{os.getpid()}"

    async with session_factory() as session:
        async with session.begin():
            # Create job
            res = await session.execute(
                insert(Job)
                .values(
                    type="effect",
                    payload={"seconds": 0.01},
                    status="pending",
                )
                .returning(Job.id)
            )
            job_id = res.scalar_one()

            # Claim job
            claim_res = await session.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == "pending")
                .values(
                    status="running",
                    claimed_at=func.now(),
                    attempts=Job.attempts + 1,
                )
                .returning(Job.id)
            )
            assert claim_res.first() is not None

            # Record execution
            await session.execute(
                insert(JobExecution).values(
                    job_id=job_id,
                    worker_id=worker_id,
                )
            )

            # Effect write
            stmt = (
                pg_insert(SideEffect)
                .values(
                    job_id=job_id,
                    effect_key=f"job:{job_id}",
                    worker_id=worker_id,
                )
                .on_conflict_do_nothing(constraint="uq_side_effects_effect_key")
            )
            await session.execute(stmt)

            # Mark succeeded
            await session.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == "running")
                .values(status="succeeded")
            )

        # Query metrics
        async with session.begin():
            dispatches = await session.scalar(
                select(func.count()).select_from(JobExecution).where(JobExecution.job_id == job_id)
            )
            effects = await session.scalar(
                select(func.count()).select_from(SideEffect).where(SideEffect.job_id == job_id)
            )

    await engine.dispose()

    result = {
        "database": current_db,
        "scenario": "baseline",
        "dispatches": int(dispatches),
        "effects": int(effects),
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"[baseline] Completed: {result}")


# =========================================================================
# Scenario 2: concurrent
# =========================================================================
async def run_concurrent(output_path: str):
    engine, session_factory = get_async_session()

    async with session_factory() as session:
        async with session.begin():
            res = await session.execute(
                insert(Job)
                .values(
                    type="effect",
                    payload={"seconds": 0.01},
                    status="running",
                    attempts=2,
                )
                .returning(Job.id)
            )
            job_id = res.scalar_one()

    worker_1 = f"worker-c1-{os.getpid()}"
    worker_2 = f"worker-c2-{os.getpid()}"

    barrier = asyncio.Barrier(2)

    async def worker_attempt(w_id: str):
        async with session_factory() as s:
            async with s.begin():
                await s.execute(
                    insert(JobExecution).values(job_id=job_id, worker_id=w_id)
                )
            await barrier.wait()
            async with s.begin():
                stmt = (
                    pg_insert(SideEffect)
                    .values(
                        job_id=job_id,
                        effect_key=f"job:{job_id}",
                        worker_id=w_id,
                    )
                    .on_conflict_do_nothing(constraint="uq_side_effects_effect_key")
                )
                res = await s.execute(stmt)
                rc = res.rowcount
            return rc

    rowcounts = await asyncio.gather(
        worker_attempt(worker_1),
        worker_attempt(worker_2),
    )

    async with session_factory() as session:
        async with session.begin():
            dispatches = await session.scalar(
                select(func.count()).select_from(JobExecution).where(JobExecution.job_id == job_id)
            )
            distinct_workers = await session.scalar(
                select(func.count(func.distinct(JobExecution.worker_id))).where(
                    JobExecution.job_id == job_id
                )
            )
            effects = await session.scalar(
                select(func.count()).select_from(SideEffect).where(SideEffect.job_id == job_id)
            )

    await engine.dispose()

    result = {
        "database": current_db,
        "scenario": "concurrent",
        "dispatches": int(dispatches),
        "distinct_workers": int(distinct_workers),
        "effects": int(effects),
        "effect_rowcounts": list(rowcounts),
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"[concurrent] Completed: {result}")


# =========================================================================
# Scenario 3: crash_reclaim
# =========================================================================
async def run_internal_worker_a(job_id: int):
    engine, session_factory = get_async_session()
    worker_id = f"worker-A-{os.getpid()}"
    async with session_factory() as session:
        async with session.begin():
            res = await session.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == "pending")
                .values(
                    status="running",
                    claimed_at=func.now(),
                    attempts=Job.attempts + 1,
                )
                .returning(Job.id)
            )
            assert res.first() is not None
            await session.execute(
                insert(JobExecution).values(job_id=job_id, worker_id=worker_id)
            )
            stmt = (
                pg_insert(SideEffect)
                .values(
                    job_id=job_id,
                    effect_key=f"job:{job_id}",
                    worker_id=worker_id,
                )
                .on_conflict_do_nothing(constraint="uq_side_effects_effect_key")
            )
            await session.execute(stmt)

    await engine.dispose()
    print(f"WORKER_A_EFFECT_COMMITTED:{worker_id}", flush=True)
    while True:
        await asyncio.sleep(1)


async def run_internal_worker_b(job_id: int):
    engine, session_factory = get_async_session()
    worker_id = f"worker-B-{os.getpid()}"
    replay_rowcount = -1
    async with session_factory() as session:
        async with session.begin():
            res = await session.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == "pending")
                .values(
                    status="running",
                    claimed_at=func.now(),
                    attempts=Job.attempts + 1,
                )
                .returning(Job.id)
            )
            assert res.first() is not None
            await session.execute(
                insert(JobExecution).values(job_id=job_id, worker_id=worker_id)
            )
            stmt = (
                pg_insert(SideEffect)
                .values(
                    job_id=job_id,
                    effect_key=f"job:{job_id}",
                    worker_id=worker_id,
                )
                .on_conflict_do_nothing(constraint="uq_side_effects_effect_key")
            )
            eff_res = await session.execute(stmt)
            replay_rowcount = eff_res.rowcount

            await session.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == "running")
                .values(status="succeeded")
            )

    await engine.dispose()
    print(f"WORKER_B_DONE:{replay_rowcount}", flush=True)


async def run_crash_reclaim(output_path: str):
    engine, session_factory = get_async_session()
    # 1. Create job
    async with session_factory() as session:
        async with session.begin():
            res = await session.execute(
                insert(Job)
                .values(
                    type="effect",
                    payload={"seconds": 300},
                    status="pending",
                )
                .returning(Job.id)
            )
            job_id = res.scalar_one()

    child_env = os.environ.copy()
    child_env["DIN5_TEST_DATABASE_URL"] = TEST_URL
    child_env["DATABASE_URL"] = TEST_URL

    # 2. Spawn Worker A
    worker_a = subprocess.Popen(
        [sys.executable, "-u", "tests/din5/pg_witness.py", "--internal-worker-a", str(job_id)],
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    worker_a_pid = worker_a.pid
    print(f"[crash_reclaim] Spawned Worker A (PID: {worker_a_pid})")

    # Poll DB until Worker A has committed effect
    for _ in range(50):
        async with session_factory() as session:
            async with session.begin():
                job_row = (
                    await session.execute(
                        select(Job.status, Job.attempts).where(Job.id == job_id)
                    )
                ).first()
                exec_count = await session.scalar(
                    select(func.count()).select_from(JobExecution).where(JobExecution.job_id == job_id)
                )
                effect_count = await session.scalar(
                    select(func.count()).select_from(SideEffect).where(SideEffect.job_id == job_id)
                )
                if (
                    job_row
                    and job_row.status == "running"
                    and exec_count == 1
                    and effect_count == 1
                ):
                    break
        await asyncio.sleep(0.1)

    # 3. Hard-kill Worker A
    worker_a.kill()
    worker_a.wait()
    worker_a_exit_code = worker_a.returncode
    print(f"[crash_reclaim] Hard-killed Worker A (exit: {worker_a_exit_code})")

    # 4. Pre-reclaim snapshot
    async with session_factory() as session:
        async with session.begin():
            job_row = (
                await session.execute(
                    select(Job.status, Job.attempts).where(Job.id == job_id)
                )
            ).first()
            exec_count = await session.scalar(
                select(func.count()).select_from(JobExecution).where(JobExecution.job_id == job_id)
            )
            effect_count = await session.scalar(
                select(func.count()).select_from(SideEffect).where(SideEffect.job_id == job_id)
            )
            pre_reclaim = f"{job_row.status}|{job_row.attempts}|{exec_count}|{effect_count}"

            # Age claimed_at beyond lease (30s lease)
            await session.execute(
                update(Job)
                .where(Job.id == job_id)
                .values(claimed_at=func.now() - text("interval '35 seconds'"))
            )

    # 5. Spawn Reaper process
    reaper = subprocess.Popen(
        [sys.executable, "-u", "-m", "src.reaper"],
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    reaper_pid = reaper.pid
    print(f"[crash_reclaim] Spawned Reaper (PID: {reaper_pid})")

    # Await reclaim barrier
    reclaim_barrier = None
    for _ in range(50):
        async with session_factory() as session:
            async with session.begin():
                row = (
                    await session.execute(
                        select(Job.status, Job.attempts, Job.claimed_at).where(Job.id == job_id)
                    )
                ).first()
                if row and row.status == "pending" and row.attempts == 1 and row.claimed_at is None:
                    reclaim_barrier = f"{row.status}|{row.attempts}|true"
                    break
        await asyncio.sleep(0.2)

    assert reclaim_barrier == "pending|1|true", f"Reaper did not reclaim in time: {reclaim_barrier}"
    reaper.terminate()
    try:
        reaper.wait(timeout=3)
    except subprocess.TimeoutExpired:
        reaper.kill()
        reaper.wait()
    print(f"[crash_reclaim] Reclaim barrier reached: {reclaim_barrier}")

    # 6. Spawn Worker B
    worker_b = subprocess.Popen(
        [sys.executable, "-u", "tests/din5/pg_witness.py", "--internal-worker-b", str(job_id)],
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    worker_b_pid = worker_b.pid
    print(f"[crash_reclaim] Spawned Worker B (PID: {worker_b_pid})")

    stdout_b, _ = worker_b.communicate(timeout=10)
    assert worker_b.returncode == 0, f"Worker B failed: {stdout_b}"

    replay_rowcount = -1
    for line in stdout_b.splitlines():
        if line.startswith("WORKER_B_DONE:"):
            replay_rowcount = int(line.split(":")[1])

    # 7. Final snapshot
    async with session_factory() as session:
        async with session.begin():
            job_row = (
                await session.execute(
                    select(Job.status, Job.attempts).where(Job.id == job_id)
                )
            ).first()
            exec_count = await session.scalar(
                select(func.count()).select_from(JobExecution).where(JobExecution.job_id == job_id)
            )
            distinct_workers = await session.scalar(
                select(func.count(func.distinct(JobExecution.worker_id))).where(
                    JobExecution.job_id == job_id
                )
            )
            effect_count = await session.scalar(
                select(func.count()).select_from(SideEffect).where(SideEffect.job_id == job_id)
            )
            final = f"{job_row.status}|{job_row.attempts}|{exec_count}|{distinct_workers}|{effect_count}"

    child_pids = [worker_a_pid, reaper_pid, worker_b_pid]
    live_children = sum(1 for p in child_pids if is_pid_alive(p))

    await engine.dispose()

    result = {
        "database": current_db,
        "scenario": "crash_reclaim",
        "crash_kind": "hard_process_exit",
        "worker_a_exit_code": worker_a_exit_code,
        "pre_reclaim": pre_reclaim,
        "reclaim_barrier": reclaim_barrier,
        "final": final,
        "replay_effect_rowcount": replay_rowcount,
        "child_pids": child_pids,
        "live_children_after_cleanup": live_children,
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"[crash_reclaim] Completed: {result}")


# =========================================================================
# Scenario 4: stale_mark
# =========================================================================
async def run_stale_mark(output_path: str):
    engine, session_factory = get_async_session()

    async with session_factory() as session:
        # Create job
        async with session.begin():
            res = await session.execute(
                insert(Job)
                .values(
                    type="effect",
                    payload={"seconds": 0.01},
                    status="pending",
                )
                .returning(Job.id)
            )
            job_id = res.scalar_one()

        # Step 1: claim:A
        async with session.begin():
            await session.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == "pending")
                .values(
                    status="running",
                    claimed_at=func.now(),
                    attempts=Job.attempts + 1,
                )
            )
            await session.execute(
                insert(JobExecution).values(job_id=job_id, worker_id="worker-stale-A")
            )

        # Step 2: effect:A
        async with session.begin():
            stmt = (
                pg_insert(SideEffect)
                .values(
                    job_id=job_id,
                    effect_key=f"job:{job_id}",
                    worker_id="worker-stale-A",
                )
                .on_conflict_do_nothing(constraint="uq_side_effects_effect_key")
            )
            await session.execute(stmt)

        # Step 3: reclaim
        async with session.begin():
            await session.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == "running")
                .values(status="pending", claimed_at=None)
            )

        # Step 4: claim:B
        async with session.begin():
            await session.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == "pending")
                .values(
                    status="running",
                    claimed_at=func.now(),
                    attempts=Job.attempts + 1,
                )
            )
            await session.execute(
                insert(JobExecution).values(job_id=job_id, worker_id="worker-stale-B")
            )

        # Step 5: mark:A (stale mark executed by Worker A)
        async with session.begin():
            res_mark_a = await session.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == "running")
                .values(status="succeeded")
            )
            stale_mark_rowcount = res_mark_a.rowcount

        # Step 6: effect:B (Worker B repeats effect, should dedup)
        async with session.begin():
            stmt_b = (
                pg_insert(SideEffect)
                .values(
                    job_id=job_id,
                    effect_key=f"job:{job_id}",
                    worker_id="worker-stale-B",
                )
                .on_conflict_do_nothing(constraint="uq_side_effects_effect_key")
            )
            res_eff_b = await session.execute(stmt_b)
            # rowcount is 0

        # Step 7: mark:B (Worker B tries to mark succeeded)
        async with session.begin():
            res_mark_b = await session.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == "running")
                .values(status="succeeded")
            )
            current_owner_mark_rowcount = res_mark_b.rowcount

        # Query metrics
        async with session.begin():
            dispatches = await session.scalar(
                select(func.count()).select_from(JobExecution).where(JobExecution.job_id == job_id)
            )
            effects = await session.scalar(
                select(func.count()).select_from(SideEffect).where(SideEffect.job_id == job_id)
            )

    await engine.dispose()

    trace = "claim:A -> effect:A -> reclaim -> claim:B -> mark:A -> effect:B -> mark:B"

    result = {
        "database": current_db,
        "scenario": "stale_mark",
        "dispatches": int(dispatches),
        "effect_count": int(effects),
        "stale_mark_rowcount": int(stale_mark_rowcount),
        "current_owner_mark_rowcount": int(current_owner_mark_rowcount),
        "trace": trace,
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"[stale_mark] Completed: {result}")


# =========================================================================
# CLI Entrypoint
# =========================================================================
def main():
    parser = argparse.ArgumentParser(description="Relay Din 5 PostgreSQL Witness Harness")
    parser.add_argument("--scenario", choices=["baseline", "concurrent", "crash_reclaim", "stale_mark"])
    parser.add_argument("--output", help="Path to output JSON file")
    parser.add_argument("--internal-worker-a", type=int, help="Internal child worker A for job ID")
    parser.add_argument("--internal-worker-b", type=int, help="Internal child worker B for job ID")

    args = parser.parse_args()

    if args.internal_worker_a:
        asyncio.run(run_internal_worker_a(args.internal_worker_a))
        return

    if args.internal_worker_b:
        asyncio.run(run_internal_worker_b(args.internal_worker_b))
        return

    if not args.scenario or not args.output:
        parser.error("--scenario and --output are required for scenario runs")

    if args.scenario == "baseline":
        asyncio.run(run_baseline(args.output))
    elif args.scenario == "concurrent":
        asyncio.run(run_concurrent(args.output))
    elif args.scenario == "crash_reclaim":
        asyncio.run(run_crash_reclaim(args.output))
    elif args.scenario == "stale_mark":
        asyncio.run(run_stale_mark(args.output))


if __name__ == "__main__":
    main()