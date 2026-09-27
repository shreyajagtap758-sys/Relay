import os
import subprocess
import sys
import time
from datetime import datetime

VENV_PY = sys.executable
CWD = r"C:\Users\Admin\PycharmProjects\Relay"
DB_URL = "postgresql+asyncpg://postgres:relay@localhost:5433/relay_w5d2"

os.makedirs(os.path.join(CWD, "logs"), exist_ok=True)
happy_stdout = os.path.join(CWD, "logs", "w5d2_step2_happy.stdout.log")
happy_stderr = os.path.join(CWD, "logs", "w5d2_step2_happy.stderr.log")
outage_stdout = os.path.join(CWD, "logs", "w5d2_step2_outage.stdout.log")
outage_stderr = os.path.join(CWD, "logs", "w5d2_step2_outage.stderr.log")

print("=== Step 2: Verification of Guarded Worker (Happy Path + Outage) ===")

# --- Part A: Happy Path ---
print("\n--- Part A: Happy Path Test ---")
subprocess.run([
    "docker", "exec", "relay-db-1", "psql", "-U", "postgres", "-d", "relay_w5d2",
    "-c", "TRUNCATE jobs, job_executions, side_effects, outbox RESTART IDENTITY CASCADE; "
          "INSERT INTO jobs (type, payload, status) VALUES ('email', '{\"test\": \"happy\"}', 'pending');"
], check=True)

env = os.environ.copy()
env["DATABASE_URL"] = DB_URL
env["APPLICATION_NAME"] = "relay-worker-step2-happy"
env["PYTHONUNBUFFERED"] = "1"

with open(happy_stdout, "w", encoding="utf-8") as out, open(happy_stderr, "w", encoding="utf-8") as err:
    proc = subprocess.Popen([VENV_PY, "-u", "-m", "relay.worker"], cwd=CWD, env=env, stdout=out, stderr=err)
    time.sleep(3)
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except Exception:
        proc.kill()

print("Happy path run finished.")
with open(happy_stdout, "r", encoding="utf-8") as f:
    print(f.read())

# --- Part B: Step 1 Outage Repeat (Heartbeat Outage) ---
print("\n--- Part B: 25s Job Heartbeat Outage Test ---")
subprocess.run([
    "docker", "exec", "relay-db-1", "psql", "-U", "postgres", "-d", "relay_w5d2",
    "-c", "TRUNCATE jobs, job_executions, side_effects, outbox RESTART IDENTITY CASCADE; "
          "INSERT INTO jobs (type, payload, status) VALUES ('effect', '{\"seconds\": 25.0}', 'pending');"
], check=True)

env["APPLICATION_NAME"] = "relay-worker-step2-outage"

out_f = open(outage_stdout, "w", encoding="utf-8")
err_f = open(outage_stderr, "w", encoding="utf-8")

print(f"[{datetime.now().strftime('%X')}] Starting guarded worker process...")
proc = subprocess.Popen([VENV_PY, "-u", "-m", "relay.worker"], cwd=CWD, env=env, stdout=out_f, stderr=err_f)
print(f"Worker PID: {proc.pid}")

# Wait 3s for claim + side effect commit
time.sleep(3)

# Wait 3s post-commit then stop DB
print(f"[{datetime.now().strftime('%X')}] Stopping Postgres: docker compose stop...")
subprocess.run(["docker", "compose", "stop"], cwd=CWD)
print(f"[{datetime.now().strftime('%X')}] Postgres stopped. Waiting 35s for heartbeat failure & handler completion...")
time.sleep(35)

# Check worker process status BEFORE starting DB
is_alive_during_outage = proc.poll() is None
print(f"[{datetime.now().strftime('%X')}] Worker status after 35s outage: {'ALIVE (SURVIVED!)' if is_alive_during_outage else f'DEAD (code {proc.poll()})'}")

# Start DB back up
print(f"[{datetime.now().strftime('%X')}] Starting Postgres...")
subprocess.run(["docker", "compose", "start"], cwd=CWD)
time.sleep(5)

is_alive_post_recovery = proc.poll() is None
print(f"[{datetime.now().strftime('%X')}] Worker status after DB recovery: {'ALIVE' if is_alive_post_recovery else f'DEAD (code {proc.poll()})'}")

proc.terminate()
try:
    proc.wait(timeout=2)
except Exception:
    proc.kill()

out_f.close()
err_f.close()

print("\n--- Outage Run Worker Stdout Tail ---")
with open(outage_stdout, "r", encoding="utf-8") as f:
    lines = f.readlines()
    for l in lines[-15:]:
        print(l.strip())
