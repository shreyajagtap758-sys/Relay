import os
import subprocess
import sys
import time
from datetime import datetime

def run_supervisor(command: list[str], name: str, transcript_path: str, pidfile_path: str, max_restarts: int = 100, backoff_seconds: float = 2.0):
    restarts = 0
    with open(transcript_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] [SUPERVISOR] Starting {name} supervisor...\n")
        f.flush()

        while restarts < max_restarts:
            launch_time = datetime.now()
            f.write(f"[{launch_time.strftime('%Y-%m-%d %H:%M:%S.%f')}] [SUPERVISOR] Launching {name} (restart_count={restarts})\n")
            f.flush()

            t0 = time.time()
            proc = subprocess.Popen(command)

            # Write child PID to pidfile
            try:
                with open(pidfile_path, "w", encoding="utf-8") as pf:
                    pf.write(str(proc.pid))
            except Exception:
                pass

            exit_code = proc.wait()
            elapsed = time.time() - t0
            restarts += 1

            exit_time = datetime.now()
            f.write(f"[{exit_time.strftime('%Y-%m-%d %H:%M:%S.%f')}] [SUPERVISOR] {name} (PID: {proc.pid}) exited with code {exit_code} after {elapsed:.2f}s (total_restarts={restarts})\n")
            f.flush()

            # Crash loop protection: If process lived less than 2s, apply backoff
            if elapsed < 2.0:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] [SUPERVISOR] Applying crash-loop backoff ({backoff_seconds}s)...\n")
                f.flush()
                time.sleep(backoff_seconds)
            else:
                time.sleep(0.5)

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python supervisor.py <name> <transcript_log> <pidfile> <command...>")
        sys.exit(1)
    proc_name = sys.argv[1]
    log_path = sys.argv[2]
    pid_path = sys.argv[3]
    cmd = sys.argv[4:]
    run_supervisor(cmd, proc_name, log_path, pid_path)
