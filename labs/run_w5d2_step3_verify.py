import os
import subprocess
import sys
import time
from datetime import datetime

VENV_PY = sys.executable
CWD = r"C:\Users\Admin\PycharmProjects\Relay"
DB_URL = "postgresql+asyncpg://postgres:relay@localhost:5433/relay_w5d2"

os.makedirs(os.path.join(CWD, "logs"), exist_ok=True)
reaper_stdout = os.path.join(CWD, "logs", "w5d2_step3_reaper.stdout.log")
reaper_stderr = os.path.join(CWD, "logs", "w5d2_step3_reaper.stderr.log")
disp_stdout = os.path.join(CWD, "logs", "w5d2_step3_dispatcher.stdout.log")
disp_stderr = os.path.join(CWD, "logs", "w5d2_step3_dispatcher.stderr.log")

print("=== Step 3: Verification of Reaper & Dispatcher Boundaries under Outage ===")

# 1. Clean relay_w5d2 and insert:
# - Stuck running job (claimed_at 15s ago, expired lease)
# - Undispatched outbox row
prepare_sql = """
TRUNCATE jobs, job_executions, side_effects, outbox, sink_deliveries RESTART IDENTITY CASCADE;
INSERT INTO jobs (type, payload, status, claimed_at, claim_generation, attempts) 
VALUES ('email', '{"test": "step3"}', 'running', now() - interval '15 seconds', 1, 1);
INSERT INTO outbox (job_id, effect_key, payload) 
VALUES (1, 'job:step3:email', '{"hello": "world"}');
"""
subprocess.run([
    "docker", "exec", "relay-db-1", "psql", "-U", "postgres", "-d", "relay_w5d2", "-c", prepare_sql
], check=True)
print("Prepared relay_w5d2 with stuck running job and pending outbox item.")

env = os.environ.copy()
env["DATABASE_URL"] = DB_URL
env["PYTHONUNBUFFERED"] = "1"

# 2. Start Sink receiver in background
print("Starting sink receiver on port 8001...")
sink_proc = subprocess.Popen(
    [VENV_PY, "-m", "uvicorn", "relay.sink:app", "--port", "8001", "--log-level", "warning"],
    cwd=CWD, env=env
)
time.sleep(2)

# 3. Start Reaper and Dispatcher
env["APPLICATION_NAME"] = "relay-reaper-step3"
r_out = open(reaper_stdout, "w", encoding="utf-8")
r_err = open(reaper_stderr, "w", encoding="utf-8")
reaper_proc = subprocess.Popen([VENV_PY, "-u", "-m", "relay.reaper"], cwd=CWD, env=env, stdout=r_out, stderr=r_err)

env["APPLICATION_NAME"] = "relay-dispatcher-step3"
d_out = open(disp_stdout, "w", encoding="utf-8")
d_err = open(disp_stderr, "w", encoding="utf-8")
disp_proc = subprocess.Popen([VENV_PY, "-u", "-m", "relay.dispatcher"], cwd=CWD, env=env, stdout=d_out, stderr=d_err)

print(f"Processes started: Reaper PID={reaper_proc.pid}, Dispatcher PID={disp_proc.pid}")

# Wait 2 seconds, then stop DB
time.sleep(2)
print(f"[{datetime.now().strftime('%X')}] Stopping Postgres: docker compose stop...")
subprocess.run(["docker", "compose", "stop"], cwd=CWD)
print(f"[{datetime.now().strftime('%X')}] Postgres stopped. Waiting 15s during outage...")
time.sleep(15)

# Check liveness during outage
r_alive_outage = reaper_proc.poll() is None
d_alive_outage = disp_proc.poll() is None
print(f"During Outage Liveness: Reaper={'ALIVE' if r_alive_outage else 'DEAD'}, Dispatcher={'ALIVE' if d_alive_outage else 'DEAD'}")

# Restart DB
print(f"[{datetime.now().strftime('%X')}] Starting Postgres...")
subprocess.run(["docker", "compose", "start"], cwd=CWD)
print("Waiting 8s for processes to recover, reclaim, and dispatch...")
time.sleep(8)

# Check liveness after recovery
r_alive_post = reaper_proc.poll() is None
d_alive_post = disp_proc.poll() is None
print(f"Post-Recovery Liveness: Reaper={'ALIVE' if r_alive_post else 'DEAD'}, Dispatcher={'ALIVE' if d_alive_post else 'DEAD'}")

reaper_proc.terminate()
disp_proc.terminate()
sink_proc.terminate()
try:
    reaper_proc.wait(timeout=2)
    disp_proc.wait(timeout=2)
    sink_proc.wait(timeout=2)
except Exception:
    reaper_proc.kill()
    disp_proc.kill()
    sink_proc.kill()

r_out.close()
r_err.close()
d_out.close()
d_err.close()

print("\n--- Reaper Output ---")
with open(reaper_stdout, "r", encoding="utf-8") as f:
    for line in f.readlines():
        if "[reclaim]" in line or "Poll failed" in line or "reaper_poll_failed" in line:
            print(line.strip())

print("\n--- Dispatcher Output ---")
with open(disp_stdout, "r", encoding="utf-8") as f:
    for line in f.readlines():
        if "[dispatch]" in line or "Poll failed" in line or "dispatcher_poll_failed" in line:
            print(line.strip())
