import os
import subprocess
import sys
import time
from datetime import datetime

CWD = r"C:\Users\Admin\PycharmProjects\Relay"
VENV_PY = sys.executable
DB_URL = "postgresql+asyncpg://postgres:relay@localhost:5433/relay_w5d1"

print("=== Step 6: Terminal-Mark Boundary & Outage Post-Handler ===")

# 1. Clean relay_w5d1
clean_cmd = [
    "docker", "exec", "relay-db-1", "psql", "-U", "postgres", "-d", "relay_w5d1",
    "-c", "TRUNCATE jobs, job_executions, side_effects, outbox RESTART IDENTITY CASCADE; "
          "INSERT INTO jobs (type, payload, status) VALUES ('email', '{\"seconds\": 4.0}', 'pending');"
]
subprocess.run(clean_cmd, check=True)
print("Prepared relay_w5d1 with a 4-second handler job.")

stdout_path = os.path.join(CWD, "logs", "w5d1_step6_worker.stdout.log")
stderr_path = os.path.join(CWD, "logs", "w5d1_step6_worker.stderr.log")
stdout_file = open(stdout_path, "w", encoding="utf-8")
stderr_file = open(stderr_path, "w", encoding="utf-8")

env = os.environ.copy()
env["DATABASE_URL"] = DB_URL
env["APPLICATION_NAME"] = "relay-worker-step6"
env["PYTHONUNBUFFERED"] = "1"

worker_proc = subprocess.Popen(
    [VENV_PY, "-u", "-m", "relay.worker"],
    cwd=CWD,
    env=env,
    stdout=stdout_file,
    stderr=stderr_file,
)
print(f"Started worker (PID: {worker_proc.pid}). Waiting 2s for worker to commit side effect...")
time.sleep(2.0)

# Stop Postgres right while handler is sleeping (side effect already committed!)
print("Stopping Postgres before mark can execute...")
subprocess.run(["docker", "compose", "stop"], cwd=CWD)

# Wait 5 seconds so handler finishes sleep and tries to execute mark block
time.sleep(5.0)

# Start Postgres back up
print("Starting Postgres back up...")
subprocess.run(["docker", "compose", "start"], cwd=CWD)
time.sleep(4.0)

stdout_file.close()
stderr_file.close()

poll_res = worker_proc.poll()
is_alive = poll_res is None
if is_alive:
    worker_proc.terminate()

print(f"\n1. Worker alive after un-guarded mark failure? {'ALIVE' if is_alive else f'DEAD (exit code {poll_res})'}")

# Inspect DB state
psql_state = [
    "docker", "exec", "relay-db-1", "psql", "-U", "postgres", "-d", "relay_w5d1",
    "-x", "-c", "SELECT id, status, attempts, claim_generation, claimed_at FROM jobs WHERE id=1; "
                "SELECT count(*) AS side_effects_count FROM side_effects; "
                "SELECT count(*) AS outbox_count FROM outbox;"
]
res = subprocess.run(psql_state, capture_output=True, text=True)
print("\n2. DB State right after recovery:")
print(res.stdout)

# Now run Reaper to show recovery of this stranded job!
print("Running Reaper to reclaim stranded job...")
reaper_cmd = [
    VENV_PY, "-u", "-c",
    f"import asyncio, os; os.environ['DATABASE_URL'] = '{DB_URL}'; from relay.reaper import reap_stuck_jobs; asyncio.run(reap_stuck_jobs())"
]
subprocess.run(reaper_cmd)

res_post = subprocess.run(psql_state, capture_output=True, text=True)
print("\n3. DB State AFTER Reaper reclaim:")
print(res_post.stdout)
