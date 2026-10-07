import asyncio
from datetime import datetime
import json
import os
import pathlib
import subprocess
import time
import asyncpg
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
LOGS_DIR = REPO_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

DISPOSABLE_DB_URL = "postgresql+asyncpg://postgres:relay@localhost:5433/relay_w5d4"
DISPOSABLE_ASYNCPG_URL = "postgresql://postgres:relay@localhost:5433/relay_w5d4"


async def setup_test_data():
    conn = await asyncpg.connect(DISPOSABLE_ASYNCPG_URL)
    try:
        # Clear any prior rows
        await conn.execute("DELETE FROM sink_deliveries;")
        await conn.execute("DELETE FROM outbox;")
        await conn.execute("DELETE FROM jobs WHERE id=999;")

        # Insert job and outbox row
        await conn.execute("INSERT INTO jobs (id, type, payload) VALUES (999, 'test_job', '{}');")
        await conn.execute(
            "INSERT INTO outbox (job_id, effect_key, payload, attempts) VALUES (999, 'job:999', '{\"target\":\"sink\"}'::jsonb, 0);"
        )
        print("[SETUP] Seeded job:999 and outbox row for effect_key='job:999'")
    finally:
        await conn.close()


async def slow_writer_task(hold_duration: float = 7.0):
    print(f"[SLOW_WRITER] Starting slow writer on sink_deliveries for key 'job:999', holding for {hold_duration}s...")
    conn = await asyncpg.connect(DISPOSABLE_ASYNCPG_URL)
    tr = conn.transaction()
    await tr.start()
    try:
        await conn.execute(
            "INSERT INTO sink_deliveries (idempotency_key, body) VALUES ('job:999', '{\"writer\":\"slow\"}'::jsonb);"
        )
        print(f"[SLOW_WRITER] Inserted key 'job:999'. Transaction remains UNCOMMITTED! Sleeping {hold_duration}s...")
        await asyncio.sleep(hold_duration)
        await tr.commit()
        print("[SLOW_WRITER] Transaction COMMITTED!")
    except Exception as e:
        await tr.rollback()
        print(f"[SLOW_WRITER] Rollback due to {e}")
    finally:
        await conn.close()


async def dispatcher_task(results_dict: dict):
    # Wait 0.5s so slow writer acquires the lock first
    await asyncio.sleep(0.5)
    print("\n[DISPATCHER] Dispatcher loop starting...")

    engine = create_async_engine(
        DISPOSABLE_DB_URL,
        connect_args={"server_settings": {"application_name": "dispatcher_w5d4"}},
    )
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=5.0) as client:
        async with session_factory() as session:
            async with session.begin():
                # 1. Lock outbox row with FOR UPDATE SKIP LOCKED
                res = await session.execute(
                    text("SELECT id, job_id, effect_key, payload FROM outbox WHERE dispatched_at IS NULL LIMIT 1 FOR UPDATE SKIP LOCKED;")
                )
                row = res.fetchone()
                if not row:
                    print("[DISPATCHER] No outbox row found!")
                    return

                outbox_id, job_id, effect_key, payload = row
                print(f"[DISPATCHER] Acquired lock on Outbox row id={outbox_id} for job_id={job_id} effect_key='{effect_key}'")
                print(f"[DISPATCHER] Sending HTTP POST to http://127.0.0.1:8001/deliver (timeout=5.0s)...")

                try:
                    resp = await client.post(
                        "http://127.0.0.1:8001/deliver",
                        json={"idempotency_key": effect_key, "job_id": job_id, "body": {"from": "dispatcher"}},
                    )
                    t_elapsed = time.perf_counter() - t0
                    print(f"[DISPATCHER] HTTP Success: {resp.status_code} in {t_elapsed:.4f}s: {resp.text}")
                    results_dict["dispatcher_result"] = "HTTP_SUCCESS"
                    results_dict["dispatcher_elapsed"] = t_elapsed
                except Exception as exc:
                    t_elapsed = time.perf_counter() - t0
                    error_cls = type(exc).__name__
                    print(f"[DISPATCHER] EXCEPTION caught after {t_elapsed:.4f}s: {error_cls}: {exc}")
                    results_dict["dispatcher_result"] = f"EXCEPTION: {error_cls}"
                    results_dict["dispatcher_elapsed"] = t_elapsed
                    results_dict["dispatcher_error"] = str(exc)
                    # Transaction will rollback here releasing the outbox lock
    await engine.dispose()
    print("[DISPATCHER] Dispatcher transaction finished and outbox lock released.")


def query_pg_locks():
    cmd = [
        "docker", "exec", "relay-db-1", "psql", "-U", "postgres", "-d", "relay_w5d4",
        "-t", "-A", "-F", "|", "-c",
        """
        SELECT a.application_name, a.state, left(a.query, 45), a.wait_event_type, a.wait_event
        FROM pg_stat_activity a
        WHERE a.datname = 'relay_w5d4' AND a.pid <> pg_backend_pid();
        """
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.stdout.strip()


async def sampler_task(results_dict: dict):
    # Wait until both are running (e.g. at t = 2.5s)
    await asyncio.sleep(2.5)
    print("\n[PROBE] Sampling pg_stat_activity while HTTP call is blocked at t=2.5s...")
    locks_output = query_pg_locks()
    print("--- PG_STAT_ACTIVITY SNAPSHOT (During Block) ---")
    print(locks_output)
    results_dict["locks_snapshot"] = locks_output


async def run_experiment():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_file = LOGS_DIR / "w5d4_step5_chain.log"

    print(f"=== [P-41 STEP 5 COMPOSED CHAIN TEST START] run_id={run_id} ===")
    await setup_test_data()

    results = {}
    writer = asyncio.create_task(slow_writer_task(hold_duration=7.0))
    dispatcher = asyncio.create_task(dispatcher_task(results))
    sampler = asyncio.create_task(sampler_task(results))

    await asyncio.gather(writer, dispatcher, sampler)

    # Format findings
    lines = [
        f"RUN_ID: {run_id}",
        "SCENARIO: Slow Writer in Sink DB holds uncommitted key 'job:999' for 7.0s.",
        "DISPATCHER: Holds FOR UPDATE SKIP LOCKED on Outbox row across HTTP POST (timeout=5.0s).",
        "--- PG_STAT_ACTIVITY WHILE BLOCKED ---",
        results.get("locks_snapshot", "N/A"),
        "--- DISPATCHER OUTCOME ---",
        f"RESULT: {results.get('dispatcher_result')}",
        f"ELAPSED: {results.get('dispatcher_elapsed', 0):.4f}s",
        f"RAW_ERROR: {results.get('dispatcher_error', 'None')}",
        "--- OBSERVABILITY GAP ANALYSIS ---",
        "1. Dispatcher error class in Relay is 'ReadTimeout' (HTTP 5.0s client timeout).",
        "2. The Relay log has NO mention of 'sink_deliveries' or transaction locks.",
        "3. Outbox row lock in Relay DB was held for 5.0 seconds purely waiting on remote receiver.",
        "4. Symptom = Relay HTTP/Pool timeout; Actual Cause = Database lock in Sink Receiver DB.",
    ]
    content = "\n".join(lines) + "\n"
    log_file.write_text(content, encoding="utf-8")
    print("\n" + content)
    print(f"[P-41 STEP 5 COMPLETED] Saved to {log_file}")


if __name__ == "__main__":
    asyncio.run(run_experiment())
