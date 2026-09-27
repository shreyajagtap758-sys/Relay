import os
import subprocess
import sys
import time
from datetime import datetime

VENV_PY = sys.executable
CWD = r"C:\Users\Admin\PycharmProjects\Relay"
DB_URL = "postgresql+asyncpg://postgres:relay@localhost:5433/relay_w5d2"

os.makedirs(os.path.join(CWD, "logs"), exist_ok=True)
stdout_path = os.path.join(CWD, "logs", "w5d2_step1_worker.stdout.log")
stderr_path = os.path.join(CWD, "logs", "w5d2_step1_worker.stderr.log")

print("=== Step 1: Heartbeat Death Point Measurement ===")

# 1. Truncate and insert job with 25s duration
clean_cmd = [
    "docker", "exec", "relay-db-1", "psql", "-U", "postgres", "-d", "relay_w5d2",
    "-c", "TRUNCATE jobs, job_executions, side_effects, outbox RESTART IDENTITY CASCADE; "
          "INSERT INTO jobs (type, payload, status) VALUES ('effect', '{\"seconds\": 25.0}', 'pending');"
]
subprocess.run(clean_cmd, check=True)
print("Prepared relay_w5d2 with 25s effect job.")

stdout_file = open(stdout_path, "w", encoding="utf-8")
stderr_file = open(stderr_path, "w", encoding="utf-8")

env = os.environ.copy()
env["DATABASE_URL"] = DB_URL
env["APPLICATION_NAME"] = "relay-worker-step1-w5d2"
env["PYTHONUNBUFFERED"] = "1"

print(f"[{datetime.now().strftime('%X')}] Starting worker process...")
worker_proc = subprocess.Popen(
    [VENV_PY, "-u", "-m", "relay.worker"],
    cwd=CWD,
    env=env,
    stdout=stdout_file,
    stderr=stderr_file,
)
print(f"Worker PID: {worker_proc.pid}")

# Wait 3s for worker to claim and commit side effect
print("Waiting 3s for worker to claim job and commit side-effect...")
time.sleep(3)

# Check side-effect commit in stdout so far
stdout_file.flush()

# Now wait 3s post-commit (as per brief: "Uske 3 s baad docker compose stop db")
print(f"[{datetime.now().strftime('%X')}] Waiting 3s post-commit, then stopping Postgres...")
time.sleep(3)

print(f"[{datetime.now().strftime('%X')}] --- Stopping Postgres: docker compose stop ---")
t_stop = time.time()
subprocess.run(["docker", "compose", "stop"], cwd=CWD)
stop_wall = datetime.now()
print(f"Postgres stopped at: {stop_wall.strftime('%X')}")

# Wait ~35 seconds
print(f"[{datetime.now().strftime('%X')}] Waiting 35 seconds for heartbeat failure and handler completion...")
time.sleep(35)

poll_result = worker_proc.poll()
is_alive = poll_result is None

if is_alive:
    print(f"[{datetime.now().strftime('%X')}] Worker is STILL ALIVE!")
    worker_proc.terminate()
    try:
        worker_proc.wait(timeout=3)
    except Exception:
        worker_proc.kill()
else:
    print(f"[{datetime.now().strftime('%X')}] Worker is DEAD! Exit code: {poll_result}")

stdout_file.close()
stderr_file.close()

# Start Postgres back up to inspect DB
print(f"[{datetime.now().strftime('%X')}] Starting Postgres to inspect database state...")
subprocess.run(["docker", "compose", "start"], cwd=CWD)
time.sleep(3)

# Inspect job state in relay_w5d2
inspect_cmd = [
    "docker", "exec", "relay-db-1", "psql", "-U", "postgres", "-d", "relay_w5d2",
    "-c", "SELECT id, status, attempts, claim_generation, claimed_at, completed_at FROM jobs;"
]
subprocess.run(inspect_cmd)

print("\n--- Executable End Analysis ---")
print(f"1. Worker alive: {'YES' if is_alive else f'NO (exit code {poll_result})'}")

with open(stderr_path, "r", encoding="utf-8") as f:
    stderr_content = f.read()

print("2. Stderr Traceback:")
print(stderr_content)
