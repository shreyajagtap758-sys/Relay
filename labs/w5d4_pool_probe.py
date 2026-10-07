import asyncio
from datetime import datetime
import json
import os
import pathlib
import subprocess
import time
import httpx

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
LOGS_DIR = REPO_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)


async def send_slow_hold(idx: int, client: httpx.AsyncClient, seconds: float = 8.0):
    t0 = time.perf_counter()
    url = f"http://127.0.0.1:8000/slow-hold?seconds={seconds}"
    try:
        response = await client.get(url, timeout=15.0)
        elapsed = time.perf_counter() - t0
        return {
            "req_id": idx,
            "status_code": response.status_code,
            "elapsed_s": round(elapsed, 4),
            "response_text": response.text[:200],
            "error_class": None if response.status_code < 400 else "HTTPStatusError",
        }
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return {
            "req_id": idx,
            "status_code": None,
            "elapsed_s": round(elapsed, 4),
            "response_text": str(exc),
            "error_class": type(exc).__name__,
        }


def query_pg_stat():
    cmd = [
        "docker", "exec", "relay-db-1", "psql", "-U", "postgres", "-d", "relay",
        "-t", "-A", "-F", "|", "-c",
        "SELECT application_name, count(*), array_agg(distinct state) FROM pg_stat_activity WHERE application_name LIKE 'api_w5d4%' GROUP BY 1;"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.stdout.strip()


async def pg_sampler():
    await asyncio.sleep(2.0)
    return query_pg_stat()


async def main():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    step2_log_path = LOGS_DIR / f"w5d4_step2_{run_id}.log"
    step1_peak_path = LOGS_DIR / "w5d4_step1_peak.txt"
    step1_clients_path = LOGS_DIR / "w5d4_step1_peak_clients.txt"

    print(f"=== [P-45 POOL PROBE START] run_id={run_id} ===")
    print("Sending 3 concurrent requests to /slow-hold?seconds=8 (pool_size=2+0, timeout=3.0)...")

    async with httpx.AsyncClient() as client:
        sampler_task = asyncio.create_task(pg_sampler())
        req_tasks = [asyncio.create_task(send_slow_hold(i, client, seconds=8.0)) for i in range(1, 4)]

        pg_peak_raw = await sampler_task
        results = await asyncio.gather(*req_tasks)

    # Save Step 1 peak output
    step1_peak_path.write_text(pg_peak_raw + "\n", encoding="utf-8")

    # Format Step 1 clients output
    clients_summary = "\n".join([f"{r['status_code']} {r['elapsed_s']}" for r in results])
    step1_clients_path.write_text(clients_summary + "\n", encoding="utf-8")

    # Extract API log error if any
    api_log_file = LOGS_DIR / "w5d4_step1_api.log"
    api_error_line = "[None]"
    if api_log_file.exists():
        for line in reversed(api_log_file.read_text(encoding="utf-8", errors="replace").splitlines()):
            if "TimeoutError" in line or "QueuePool limit" in line:
                api_error_line = line.strip()
                break

    # Build Step 2 log
    lines = [
        f"RUN_ID: {run_id}",
        f"CONFIG: POOL_SIZE=2, MAX_OVERFLOW=0, POOL_TIMEOUT=3.0, echo=True",
        f"PG_STAT_ACTIVITY_PEAK: {pg_peak_raw}",
        "--- REQUEST RESULTS ---",
    ]
    for r in results:
        lines.append(
            f"REQ #{r['req_id']}: status={r['status_code']} elapsed={r['elapsed_s']}s error_class={r['error_class']} body={r['response_text']}"
        )
    lines.append(f"API_SERVER_LOG_MATCH: {api_error_line}")
    log_content = "\n".join(lines) + "\n"

    step2_log_path.write_text(log_content, encoding="utf-8")

    print("\n" + log_content)
    print(f"[P-45 POOL PROBE FINISHED] Saved to {step2_log_path}")


if __name__ == "__main__":
    asyncio.run(main())
