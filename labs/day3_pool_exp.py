"""
WEEK 0 DEBT — A1: Day 3 Exp E (SABSE IMPORTANT PENDING)
============================================================
Goal: Prove sync driver inside async endpoint me pool size badhane se
      KOI FARQ NAHI padta. Async driver me farq padta hai.

Hypothesis:
  - async (asyncpg) + pool_size=2  → ~5.25s total
  - async (asyncpg) + pool_size=10 → ~1.66s total
  - sync (psycopg)  + pool_size=2  → ~10s total
  - sync (psycopg)  + pool_size=10 → ~10s total (NO DIFFERENCE)

Why this matters:
  Pool exhaustion "DB slow" jaisa dikhta hai par DB theek hota hai.
  Agar sync driver use kar rahe ho async endpoint me, toh pool size
  badhane se kuch nahi hoga — kyunki har request event loop ko block
  kar degi. Ye diagnostic tool hai do alag bottlenecks distinguish karne ka.
"""

import asyncio
import time

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Database Connection URL (AsyncPG for Postgres mapped on Docker port 5433)
DB_URL = "postgresql+asyncpg://postgres:relay@localhost:5433/relay"

app = FastAPI()

async def run_db_query(engine, request_id):
    start_time = time.time()
    try:
        async with engine.connect() as conn:
            # Execute pg_sleep(1) to simulate 1 second database query
            await conn.execute(text("SELECT pg_sleep(1)"))
            latency = time.time() - start_time
            print(f"[REQ {request_id:02d}] Success! Latency: {latency:.2f}s")
            return ("SUCCESS", latency)
    except Exception as e:
        latency = time.time() - start_time
        print(f"[REQ {request_id:02d}] FAILED! Error: {type(e).__name__} after {latency:.2f}s")
        print(f"         Details: {e}")
        return ("FAILED", latency)


async def run_experiment(exp_name, pool_size, max_overflow, pool_timeout, total_requests=10):
    print(f"\n========================================================")
    print(f"RUNNING {exp_name}: pool_size={pool_size}, max_overflow={max_overflow}, pool_timeout={pool_timeout}s")
    print(f"Sending {total_requests} concurrent requests executing SELECT pg_sleep(1)...")
    print(f"========================================================\n")

    engine = create_async_engine(
        DB_URL,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
    )

    exp_start = time.time()

    # Launch 10 concurrent requests using asyncio.gather
    tasks = [run_db_query(engine, i + 1) for i in range(total_requests)]
    results = await asyncio.gather(*tasks)

    total_time = time.time() - exp_start

    successes = sum(1 for status, _ in results if status == "SUCCESS")
    failures = sum(1 for status, _ in results if status == "FAILED")

    print(f"\n--------------------------------------------------------")
    print(f"SUMMARY ({exp_name}): Total Time: {total_time:.2f}s | Success: {successes} | Failures: {failures}")
    print(f"--------------------------------------------------------\n")

    await engine.dispose()
    return total_time, successes, failures


async def run_sync_db_query(request_id):
    start_time = time.time()
    try:
        # Simulate synchronous blocking DB driver (like psycopg2 or sync execution inside async def)
        time.sleep(1)  # Blocking call freezes the async event loop thread!
        latency = time.time() - start_time
        print(f"[REQ {request_id:02d}] Success! Latency: {latency:.2f}s")
        return ("SUCCESS", latency)
    except Exception as e:
        latency = time.time() - start_time
        print(f"[REQ {request_id:02d}] FAILED! Error: {type(e).__name__} after {latency:.2f}s")
        return ("FAILED", latency)


async def run_experiment_sync(exp_name, pool_size, total_requests=10):
    print(f"\n========================================================")
    print(f"RUNNING {exp_name}: Sync Blocking Driver Simulator (pool_size={pool_size})")
    print(f"Sending {total_requests} concurrent requests with synchronous blocking sleep...")
    print(f"========================================================\n")

    exp_start = time.time()
    tasks = [run_sync_db_query(i + 1) for i in range(total_requests)]
    results = await asyncio.gather(*tasks)

    total_time = time.time() - exp_start
    successes = sum(1 for status, _ in results if status == "SUCCESS")
    failures = sum(1 for status, _ in results if status == "FAILED")

    print(f"\n--------------------------------------------------------")
    print(f"SUMMARY ({exp_name}): Total Time: {total_time:.2f}s | Success: {successes} | Failures: {failures}")
    print(f"--------------------------------------------------------\n")
    return total_time, successes, failures


if __name__ == "__main__":
    # --- SELECT EXPERIMENT TO RUN ---

    # Exp A: Pool Exhaustion (Async, pool=2) -> ~5.0s
    # asyncio.run(run_experiment("Exp A (Async, pool=2, timeout=30s)", pool_size=2, max_overflow=0, pool_timeout=30.0))

    # Exp B: Timeout Crash (Async, pool=2, timeout=1s) -> 8 failures
    # asyncio.run(run_experiment("Exp B (Async, pool=2, timeout=1s)", pool_size=2, max_overflow=0, pool_timeout=1.0))

    # Exp C: Scaled Pool (Async, pool=10) -> ~1.2s
    # asyncio.run(run_experiment("Exp C (Async, pool=10, timeout=30s)", pool_size=10, max_overflow=0, pool_timeout=30.0))

    # Exp E1: Sync Driver (pool=2) -> ~10.0s
    asyncio.run(run_experiment_sync("Exp E1 (Sync Driver, pool=2)", pool_size=2))

    # Exp E2: Sync Driver (pool=10) -> ~10.0s (POOL SIZE 10 DOES NOT HELP SYNC DRIVERS!)
    asyncio.run(run_experiment_sync("Exp E2 (Sync Driver, pool=10)", pool_size=10))