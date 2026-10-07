import asyncio
import os
import pathlib
import subprocess
import time
import httpx

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
LOGS_DIR = REPO_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def query_pg():
    cmd = [
        "docker", "exec", "relay-db-1", "psql", "-U", "postgres", "-d", "relay",
        "-t", "-A", "-F", "|", "-c",
        "SELECT application_name, state, left(query,40), now()-query_start FROM pg_stat_activity WHERE application_name LIKE 'api_w5d4%';"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.stdout.strip()


async def client_worker(hold_seconds: float = 15.0, abort_after: float = 3.0):
    print(f"[CLIENT] Sending GET /slow-hold?seconds={hold_seconds}...")
    try:
        async with httpx.AsyncClient() as client:
            # Send request with a strict timeout so client disconnects after abort_after seconds
            await client.get(
                f"http://127.0.0.1:8000/slow-hold?seconds={hold_seconds}",
                timeout=abort_after,
            )
            print("[CLIENT] Request completed normally (unexpected).")
    except httpx.TimeoutException:
        print(f"[CLIENT] Client timed out / disconnected after {abort_after}s! Connection closed.")
    except Exception as exc:
        print(f"[CLIENT] Client exception: {type(exc).__name__}: {exc}")


async def main():
    hold_seconds = 15.0
    abort_after = 3.0

    print("=== [P-44 STEP 4: CLIENT DISCONNECT PROBE START] ===")
    
    # Launch client task
    client_task = asyncio.create_task(client_worker(hold_seconds, abort_after))

    # Wait for client to abort (t = 4.0s)
    await asyncio.sleep(abort_after + 1.0)
    print("\n[PROBE] Client has disconnected! Querying Postgres pg_stat_activity immediately (t=4s)...")
    snap1 = query_pg()
    print("--- SNAPSHOT 1 (Immediately after disconnect) ---")
    print(snap1)
    (LOGS_DIR / "w5d4_step4_after_disconnect.txt").write_text(snap1 + "\n", encoding="utf-8")

    # Wait until hold duration expires (t = 16.0s)
    remaining_wait = hold_seconds - (abort_after + 1.0) + 1.5
    print(f"\n[PROBE] Waiting {remaining_wait:.1f}s for original query duration ({hold_seconds}s) to pass...")
    await asyncio.sleep(remaining_wait)

    print("\n[PROBE] Querying Postgres pg_stat_activity after full hold duration (t=16.5s)...")
    snap2 = query_pg()
    print("--- SNAPSHOT 2 (After full hold time elapsed) ---")
    print(snap2)
    (LOGS_DIR / "w5d4_step4_after_completion.txt").write_text(snap2 + "\n", encoding="utf-8")

    await client_task
    print("\n=== [P-44 STEP 4 PROBE COMPLETED] ===")


if __name__ == "__main__":
    asyncio.run(main())
