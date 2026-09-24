import os
import subprocess
import sys
import time
from datetime import datetime

VENV_PY = sys.executable
CWD = r"C:\Users\Admin\PycharmProjects\Relay"
DB_URL = "postgresql+asyncpg://postgres:relay@localhost:5433/relay_w5d1"

os.makedirs(os.path.join(CWD, "logs"), exist_ok=True)
stdout_path = os.path.join(CWD, "logs", "w5d1_step1_worker.stdout.log")
stderr_path = os.path.join(CWD, "logs", "w5d1_step1_worker.stderr.log")

print("=== Step 1 Control: Reproducing Worker Crash on DB Outage ===")

stdout_file = open(stdout_path, "w", encoding="utf-8")
stderr_file = open(stderr_path, "w", encoding="utf-8")

env = os.environ.copy()
env["DATABASE_URL"] = DB_URL
env["APPLICATION_NAME"] = "relay-worker-control"
env["PYTHONUNBUFFERED"] = "1"

print(f"[{datetime.now().strftime('%X')}] Starting worker with unbuffered stdout/stderr...")
worker_proc = subprocess.Popen(
    [VENV_PY, "-u", "-m", "relay.worker"],
    cwd=CWD,
    env=env,
    stdout=stdout_file,
    stderr=stderr_file,
)
print(f"Worker PID: {worker_proc.pid}")

# Give it 6 seconds to claim the job, complete it, and enter idle poll
print("Waiting 6s for worker to process job and enter idle poll...")
time.sleep(6)

print(f"\n[{datetime.now().strftime('%X')}] --- Stopping Postgres: docker compose stop ---")
t_stop = time.time()
subprocess.run(["docker", "compose", "stop"], cwd=CWD)
stop_wall = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"Postgres stopped at wall-clock: {stop_wall}")

print("Waiting 25 seconds during outage window...")
time.sleep(25)

print(f"\n[{datetime.now().strftime('%X')}] --- Starting Postgres: docker compose start ---")
t_start = time.time()
subprocess.run(["docker", "compose", "start"], cwd=CWD)
start_wall = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"Postgres started at wall-clock: {start_wall}")

print("Waiting 30 seconds post-recovery observation window...")
time.sleep(30)

stdout_file.close()
stderr_file.close()

# Poll process
poll_result = worker_proc.poll()
is_alive = poll_result is None

print("\n=== Executable End Measurements ===")
print(f"1. Worker alive check: {'ALIVE' if is_alive else f'DEAD (Exited with code {poll_result})'}")

with open(stdout_path, "r", encoding="utf-8") as f:
    stdout_lines = f.readlines()
last_stdout = stdout_lines[-1].strip() if stdout_lines else "EMPTY"
print(f"2. stdout last line: {last_stdout}")

with open(stderr_path, "r", encoding="utf-8") as f:
    stderr_lines = f.readlines()

print(f"3. stderr contents:\n{''.join(stderr_lines[:25])}")
