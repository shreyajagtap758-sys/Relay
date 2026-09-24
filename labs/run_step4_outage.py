import os
import subprocess
import sys
import time
from datetime import datetime

VENV_PY = sys.executable
CWD = r"C:\Users\Admin\PycharmProjects\Relay"
DB_URL = "postgresql+asyncpg://postgres:relay@localhost:5433/relay_w5d1"

os.makedirs(os.path.join(CWD, "logs"), exist_ok=True)
stdout_path = os.path.join(CWD, "logs", "w5d1_step4_worker.stdout.log")
stderr_path = os.path.join(CWD, "logs", "w5d1_step4_worker.stderr.log")

print("=== Step 4: Outage with Exception Boundary & 3 Numbers Measurement ===")

# 1. Clean jobs in relay_w5d1 and insert 1 pending job for post-recovery claim
clean_cmd = [
    "docker", "exec", "relay-db-1", "psql", "-U", "postgres", "-d", "relay_w5d1",
    "-c", "TRUNCATE jobs, job_executions, side_effects, outbox RESTART IDENTITY CASCADE; "
          "INSERT INTO jobs (type, payload, status) VALUES ('email', '{\"test\": \"step4_pre\"}', 'pending');"
]
subprocess.run(clean_cmd, check=True)
print("Prepared relay_w5d1 with initial pending job.")

stdout_file = open(stdout_path, "w", encoding="utf-8")
stderr_file = open(stderr_path, "w", encoding="utf-8")

env = os.environ.copy()
env["DATABASE_URL"] = DB_URL
env["APPLICATION_NAME"] = "relay-worker-step4"
env["PYTHONUNBUFFERED"] = "1"

print(f"[{datetime.now().strftime('%X')}] Starting worker with claim exception boundary...")
worker_proc = subprocess.Popen(
    [VENV_PY, "-u", "-m", "relay.worker"],
    cwd=CWD,
    env=env,
    stdout=stdout_file,
    stderr=stderr_file,
)
print(f"Worker PID: {worker_proc.pid}")

# Wait 6s for worker to claim and finish initial job, entering idle poll
print("Waiting 6s for worker to process job and enter idle poll...")
time.sleep(6)

# Insert another job that will be claimed AFTER recovery
insert_post = [
    "docker", "exec", "relay-db-1", "psql", "-U", "postgres", "-d", "relay_w5d1",
    "-c", "INSERT INTO jobs (type, payload, status) VALUES ('email', '{\"test\": \"step4_post\"}', 'pending');"
]
subprocess.run(insert_post, check=True)

# 2. Stop Postgres
print(f"\n[{datetime.now().strftime('%X')}] --- Stopping Postgres: docker compose stop ---")
t_stop = time.time()
subprocess.run(["docker", "compose", "stop"], cwd=CWD)
stop_wall = datetime.now()
print(f"Postgres stopped at wall-clock: {stop_wall.strftime('%Y-%m-%d %H:%M:%S.%f')}")

# Outage window: 25 seconds
print("Waiting 25 seconds during outage window...")
time.sleep(25)

# 3. Start Postgres
print(f"\n[{datetime.now().strftime('%X')}] --- Starting Postgres: docker compose start ---")
t_start = time.time()
subprocess.run(["docker", "compose", "start"], cwd=CWD)
start_wall = datetime.now()
print(f"Postgres started at wall-clock: {start_wall.strftime('%Y-%m-%d %H:%M:%S.%f')}")

# Wait for 30s observation window
print("Waiting 30 seconds post-recovery observation window...")
time.sleep(30)

# Check worker process status
poll_result = worker_proc.poll()
is_alive = poll_result is None

worker_proc.terminate()
try:
    worker_proc.wait(timeout=3)
except Exception:
    worker_proc.kill()

stdout_file.close()
stderr_file.close()

print("\n=== Step 4 Executable End Analysis ===")
print(f"1. alive: {'YES (ALIVE)' if is_alive else f'NO (DEAD, exit {poll_result})'}")

with open(stdout_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

poll_failures = 0
first_success_ts = None
post_start_first_poll_line = None

for line in lines:
    if "Claim poll failed" in line:
        poll_failures += 1
    if "Claimed job_id=2" in line or "Claimed job_id=" in line:
        # Check if this claim happened post-recovery
        pass

print(f"2. poll_failures during outage: {poll_failures}")

# Scan stdout for timestamps and lines after start_wall
print("\n--- Worker stdout around and after recovery ---")
post_recovery_lines = []
for line in lines:
    if "Claim poll failed" in line or "Claimed job_id" in line or "event=mark" in line:
        print(line.strip())
