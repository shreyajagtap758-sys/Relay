import argparse
import ctypes
from ctypes import wintypes
import datetime as dt
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable
NAMES = ("worker", "reaper", "dispatcher")
PKG = "relay" if (REPO / "relay").exists() else "src"


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]


def find_child_pid_win32(parent_pid: int) -> int | None:
    try:
        kernel32 = ctypes.windll.kernel32
        hSnapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
        if hSnapshot == -1:
            return None
        pe = PROCESSENTRY32()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
        success = kernel32.Process32First(hSnapshot, ctypes.byref(pe))
        child_pid = None
        while success:
            if pe.th32ParentProcessID == parent_pid:
                child_pid = pe.th32ProcessID
                break
            success = kernel32.Process32Next(hSnapshot, ctypes.byref(pe))
        kernel32.CloseHandle(hSnapshot)
        return child_pid
    except Exception:
        return None


def resolve_child_pid(launcher_pid: int, stdout_path: Path, timeout: float = 0.5) -> int:
    t_end = time.monotonic() + timeout
    while time.monotonic() < t_end:
        pid = find_child_pid_win32(launcher_pid)
        if pid:
            return pid
        if stdout_path.exists():
            txt = stdout_path.read_text(encoding="utf-8", errors="replace")
            matches = re.findall(r"\(PID: (\d+)\)", txt)
            if matches:
                return int(matches[-1])
        time.sleep(0.02)
    if stdout_path.exists():
        txt = stdout_path.read_text(encoding="utf-8", errors="replace")
        matches = re.findall(r"\(PID: (\d+)\)", txt)
        if matches:
            return int(matches[-1])
    return launcher_pid


def now_str() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def supervise_child(name: str, prefix: str, stop_event: threading.Event) -> None:
    logs_dir = REPO / "logs"
    logs_dir.mkdir(exist_ok=True)
    sup_log_path = logs_dir / f"{prefix}_supervisor.log"
    out_path = logs_dir / f"{prefix}_{name}.stdout.log"
    err_path = logs_dir / f"{prefix}_{name}.stderr.log"

    def log_sup(msg: str) -> None:
        with open(sup_log_path, "a", encoding="utf-8") as f:
            f.write(f"[{now_str()}] {msg}\n")
            f.flush()

    backoff = 1.0
    cmd = [str(PY), "-u", "-m", f"{PKG}.{name}"]
    env = dict(os.environ, PYTHONUNBUFFERED="1")

    while not stop_event.is_set():
        with open(out_path, "a", encoding="utf-8") as out_f, open(err_path, "a", encoding="utf-8") as err_f:
            proc = subprocess.Popen(cmd, cwd=REPO, env=env, stdout=out_f, stderr=err_f)
            child_pid = resolve_child_pid(proc.pid, out_path)
            log_sup(f"Started {name} (PID: {proc.pid}) child_pid={child_pid}")
            t0 = time.monotonic()
            exit_code = proc.wait()
            uptime = time.monotonic() - t0

        log_sup(f"{name} (PID: {proc.pid}) EXITED with code {exit_code} after {uptime:.2f}s uptime")

        if stop_event.is_set():
            break

        # Crash-loop backoff logic
        if uptime < 5.0:
            log_sup(f"sleeping {backoff:.2f}s before restarting {name}.")
            # sleep with stop_event check
            t_sleep_end = time.monotonic() + backoff
            while time.monotonic() < t_sleep_end and not stop_event.is_set():
                time.sleep(0.05)
            backoff = min(backoff * 2.0, 30.0)
        else:
            backoff = 1.0


def main_multi() -> None:
    prefix = os.environ.get("RELAY_SUPERVISOR_PREFIX", "manual_run")
    stop_event = threading.Event()
    threads = []
    for name in NAMES:
        t = threading.Thread(target=supervise_child, args=(name, prefix, stop_event), daemon=True)
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop_event.set()


def run_legacy(command: list[str], name: str, transcript_path: str, pidfile_path: str, max_restarts: int = 100, backoff_seconds: float = 2.0):
    restarts = 0
    with open(transcript_path, "a", encoding="utf-8") as f:
        f.write(f"[{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] [SUPERVISOR] Starting {name} supervisor...\n")
        f.flush()

        while restarts < max_restarts:
            launch_time = dt.datetime.now()
            f.write(f"[{launch_time.strftime('%Y-%m-%d %H:%M:%S.%f')}] [SUPERVISOR] Launching {name} (restart_count={restarts})\n")
            f.flush()

            t0 = time.time()
            proc = subprocess.Popen(command)

            try:
                with open(pidfile_path, "w", encoding="utf-8") as pf:
                    pf.write(str(proc.pid))
            except Exception:
                pass

            exit_code = proc.wait()
            elapsed = time.time() - t0
            restarts += 1

            exit_time = dt.datetime.now()
            f.write(f"[{exit_time.strftime('%Y-%m-%d %H:%M:%S.%f')}] [SUPERVISOR] {name} (PID: {proc.pid}) exited with code {exit_code} after {elapsed:.2f}s (total_restarts={restarts})\n")
            f.flush()

            if elapsed < 2.0:
                f.write(f"[{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] [SUPERVISOR] Applying crash-loop backoff ({backoff_seconds}s)...\n")
                f.flush()
                time.sleep(backoff_seconds)
            else:
                time.sleep(0.5)


if __name__ == "__main__":
    if len(sys.argv) >= 5:
        proc_name = sys.argv[1]
        log_path = sys.argv[2]
        pid_path = sys.argv[3]
        cmd = sys.argv[4:]
        run_legacy(cmd, proc_name, log_path, pid_path)
    else:
        main_multi()
