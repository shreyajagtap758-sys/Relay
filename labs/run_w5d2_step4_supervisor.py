import os
import signal
import subprocess
import sys
import time
from datetime import datetime

VENV_PY = sys.executable
CWD = r"C:\Users\Admin\PycharmProjects\Relay"
DB_URL = "postgresql+asyncpg://postgres:relay@localhost:5433/relay_w5d2"

os.makedirs(os.path.join(CWD, "logs"), exist_ok=True)
worker_pidfile = os.path.join(CWD, "logs", "worker.pid")
reaper_pidfile = os.path.join(CWD, "logs", "reaper.pid")
sup_worker_log = os.path.join(CWD, "logs", "w5d2_step4_sup_worker.transcript.log")
sup_reaper_log = os.path.join(CWD, "logs", "w5d2_step4_sup_reaper.transcript.log")

print("=== Step 4: Supervisor & fault_to_reclaim Measurement ===")

# 1. Truncate relay_w5d2 and insert 1 job with 10s lease
prepare_sql = """
TRUNCATE jobs, job_executions, side_effects, outbox RESTART IDENTITY CASCADE;
INSERT INTO jobs (type, payload, status) VALUES ('email', '{"test": "step4_sup"}', 'pending');
"""
subprocess.run([
    "docker", "exec", "relay-db-1", "psql", "-U", "postgres", "-d", "relay_w5d2", "-c", prepare_sql
], check=True)
print("Prepared relay_w5d2 with pending job.")

env = os.environ.copy()
env["DATABASE_URL"] = DB_URL
env["PYTHONUNBUFFERED"] = "1"

# Clear transcripts
for p in [worker_pidfile, reaper_pidfile, sup_worker_log, sup_reaper_log]:
    if os.path.exists(p):
        os.remove(p)

# 2. Launch supervised worker and supervised reaper
print(f"[{datetime.now().strftime('%X')}] Starting supervised worker and reaper...")

worker_cmd = [VENV_PY, "scripts/supervisor.py", "worker", sup_worker_log, worker_pidfile, VENV_PY, "-u", "-m", "relay.worker"]
reaper_cmd = [VENV_PY, "scripts/supervisor.py", "reaper", sup_reaper_log, reaper_pidfile, VENV_PY, "-u", "-m", "relay.reaper"]

worker_sup = subprocess.Popen(worker_cmd, cwd=CWD, env=env)
reaper_sup = subprocess.Popen(reaper_cmd, cwd=CWD, env=env)

# Wait 4s for worker to claim the job and finish
time.sleep(4)

# Insert a stuck job with expired lease (claimed_at 15s ago) to measure fault_to_reclaim
insert_stuck = """
INSERT INTO jobs (type, payload, status, claimed_at, claim_generation, attempts)
VALUES ('email', '{"test": "stuck"}', 'running', now() - interval '15 seconds', 1, 1)
RETURNING id, claimed_at;
"""
res = subprocess.run([
    "docker", "exec", "relay-db-1", "psql", "-U", "postgres", "-d", "relay_w5d2", "-t", "-A", "-c", insert_stuck
], capture_output=True, text=True, check=True)
stuck_info = res.stdout.strip()
print(f"Inserted stuck job: {stuck_info}")

# 3. Simulate process death during DB outage:
print(f"[{datetime.now().strftime('%X')}] Stopping Postgres: docker compose stop...")
t_db_stop = time.time()
subprocess.run(["docker", "compose", "stop"], cwd=CWD)

# Kill child worker and child reaper (read PIDs from pidfiles)
print("Simulating child worker/reaper death during outage...")
for pidfile in [worker_pidfile, reaper_pidfile]:
    if os.path.exists(pidfile):
        try:
            with open(pidfile, "r") as pf:
                child_pid = int(pf.read().strip())
            os.kill(child_pid, signal.SIGTERM)
            print(f"Killed child PID {child_pid} from {os.path.basename(pidfile)}")
        except Exception as e:
            print(f"Could not kill PID from {pidfile}: {e}")

# Outage window: 20 seconds
print("Waiting 20 seconds during outage window...")
time.sleep(20)

# Restart DB
print(f"[{datetime.now().strftime('%X')}] Starting Postgres: docker compose start...")
t_db_start = time.time()
subprocess.run(["docker", "compose", "start"], cwd=CWD)
start_wall = datetime.now()
print(f"Postgres started at: {start_wall.strftime('%Y-%m-%d %H:%M:%S.%f')}")

# Wait 10s post-recovery window
print("Waiting 10s post-recovery window for supervisor relaunch & reclamation...")
time.sleep(10)

# Terminate supervisors
worker_sup.terminate()
reaper_sup.terminate()
try:
    worker_sup.wait(timeout=2)
    reaper_sup.wait(timeout=2)
except Exception:
    worker_sup.kill()
    reaper_sup.kill()

print("\n=== Step 4 Executable End Analysis ===")

with open(sup_worker_log, "r", encoding="utf-8") as f:
    worker_sup_lines = f.readlines()

with open(sup_reaper_log, "r", encoding="utf-8") as f:
    reaper_sup_lines = f.readlines()

print("--- Supervisor Worker Transcript ---")
for l in worker_sup_lines:
    print(l.strip())

print("\n--- Supervisor Reaper Transcript ---")
for l in reaper_sup_lines:
    print(l.strip())

inspect_cmd = [
    "docker", "exec", "relay-db-1", "psql", "-U", "postgres", "-d", "relay_w5d2",
    "-c", "SELECT id, status, attempts, claim_generation, claimed_at, completed_at FROM jobs ORDER BY id;"
]
subprocess.run(inspect_cmd)
