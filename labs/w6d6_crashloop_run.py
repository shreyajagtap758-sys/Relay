r"""labs/w6d6_crashloop_run.py -- Week 6 Din 6: scripts/supervisor.py under a poison-pill payload, DISPOSABLE DB only.
Values and labels only (P-52). Refuses any DB not named relay_w6d6*. --env prints NAMES only.
Every event this script causes is written with a wall clock to <run>_timeline.txt at the moment it happens (P-53(a)).
  starts   scripts/supervisor.py (it starts worker, reaper, dispatcher); RELAY_SUPERVISOR_PREFIX=<run>
  inserts  --count jobs of --type with --payload, after the supervisor's worker has printed its start line
  samples  the jobs every 1 s for --seconds (changes only, into the timeline)
  stops    the supervisor's whole process tree, then sweeps leftovers by command line
  census   supervisor: per process -- starts, exits (code, uptime), backoff values in order, PIDs it logged,
           child_pid= values it logged; children: the PIDs they print about themselves; overlap of the two (P-53(b));
           jobs: status / attempts / generation / executions / reclaims / crash lines; side_effects + outbox rows and
           sequence deltas
Usage (PowerShell -- single quotes keep the JSON intact):
  .\.venv\Scripts\python.exe -u labs\w6d6_crashloop_run.py --label s3_crashloop --count 3 --seconds 120 --type effect --payload '{"seconds": 1, "crash_at": "before_commit"}'"""
import argparse
import asyncio
import datetime as dt
import json
import os
import re
import subprocess
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

REPO = Path(__file__).resolve().parents[1]
PY = REPO / ".venv" / "Scripts" / "python.exe"
NAMES = ("worker", "reaper", "dispatcher")


def base_url() -> str:
    env_file = REPO / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ["DATABASE_URL"]


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else f"git_error_{r.returncode}"


def now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def sweep() -> int:
    # venv python.exe is a launcher stub; the interpreter is its child (P-53(b)) -- sweep by command line
    ps = ("$n = @(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*"
          + str(REPO) + "*' -and $_.CommandLine -match '(src|relay)\\.(worker|reaper|dispatcher)|supervisor\\.py' });"
          " $n | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; $n.Count")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    return int((r.stdout.strip() or "0").splitlines()[-1])


async def main(a) -> None:
    if not re.fullmatch(r"relay_w6d6[a-z0-9_]*", a.db):
        raise SystemExit(f"refusing db={a.db!r}: this harness only runs on relay_w6d6* (never the evidence DB)")
    json.loads(a.payload)
    url = re.sub(r"/[^/]+$", f"/{a.db}", base_url())
    if not url.endswith(f"/{a.db}"):
        raise SystemExit("DATABASE_URL rewrite failed")
    logs = REPO / "logs"
    logs.mkdir(exist_ok=True)
    run = f"w6d6_{a.label}_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    tl = open(logs / f"{run}_timeline.txt", "w", encoding="utf-8")

    def ev(msg: str) -> None:
        tl.write(f"{now()} {msg}\n")
        tl.flush()

    o: list[str] = [f"run_id={run}"]
    o.append(f"label={a.label} type={a.type} count={a.count} seconds={a.seconds} "
             f"extra_env_names={','.join(p.split('=', 1)[0] for p in a.env) or '-'}")
    o.append("head=" + git("rev-parse", "--short", "HEAD"))
    o.append("src_diff_files_vs_HEAD=" + ",".join(git("diff", "--name-only", "HEAD", "--", "src/", "relay/", "alembic/", "scripts/").split()))

    eng = create_async_engine(url, echo=False)
    seq_sql = "SELECT (SELECT last_value FROM side_effects_id_seq), (SELECT last_value FROM outbox_id_seq)"
    async with eng.connect() as c:
        o.append("current_database=" + (await c.execute(text("SELECT current_database()"))).scalar_one())
        o.append("db_revision=" + ",".join(r[0] for r in (await c.execute(text("SELECT version_num FROM alembic_version"))).all()))
        left = (await c.execute(text("SELECT count(*) FROM jobs WHERE status NOT IN ('succeeded', 'dead_letter', 'failed')"))).scalar_one()
        o.append(f"nonterminal_before={left}")
        if left:
            raise SystemExit("\n".join(o) + "\nrefusing: earlier non-terminal jobs exist")
        seq0 = tuple((await c.execute(text(seq_sql))).one())

    env = dict(os.environ, DATABASE_URL=url, PYTHONUNBUFFERED="1", RELAY_SUPERVISOR_PREFIX=run)
    for pair in a.env:
        k, v = pair.split("=", 1)
        env[k] = v
    sup_out = open(logs / f"{run}_supervisor.console.log", "w", encoding="utf-8")
    ev("supervisor_start")
    sup = subprocess.Popen([str(PY), "-u", "scripts/supervisor.py"], cwd=REPO, env=env, stdout=sup_out,
                           stderr=subprocess.STDOUT)
    wlog = logs / f"{run}_worker.stdout.log"
    ready = False
    for _ in range(100):
        if "Starting worker process" in read(wlog):
            ready = True
            break
        time.sleep(0.2)
    ev(f"worker_ready={ready}")
    o.append(f"worker_ready={ready}")
    ids: list[int] = []
    try:
        async with eng.begin() as c:
            for _ in range(a.count):
                ids.append((await c.execute(text("INSERT INTO jobs (type, payload) VALUES (:t, CAST(:p AS jsonb)) "
                                                 "RETURNING id"), {"t": a.type, "p": a.payload})).scalar_one())
        ev(f"inserted job_ids={ids}")
        o.append(f"job_ids={ids[0]}..{ids[-1]} n={len(ids)}")
        last = None
        end = time.monotonic() + a.seconds
        while time.monotonic() < end:
            async with eng.connect() as c:
                rows = (await c.execute(text("SELECT id, status, attempts, claim_generation FROM jobs WHERE id = ANY(:i) "
                                             "ORDER BY id"), {"i": ids})).all()
            snap = " ; ".join(f"{r[0]}|{r[1]}|{r[2]}|{r[3]}" for r in rows)
            if snap != last:
                ev(f"jobs {snap}")
                last = snap
            await asyncio.sleep(1.0)
        o.append("supervisor_alive_at_end=" + str(sup.poll() is None))
    finally:
        ev("stop_begin")
        subprocess.run(["taskkill", "/PID", str(sup.pid), "/T", "/F"], capture_output=True)
        try:
            sup.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        n = sweep()
        ev(f"stop_end swept_leftover_python={n}")
        o.append(f"swept_leftover_python={n}")
        tl.close()
        sup_out.close()

    slog = read(logs / f"{run}_supervisor.log").splitlines()
    o.append(f"supervisor_log_lines={len(slog)}")
    child_self: set[int] = set()
    for name in NAMES:
        txt = read(logs / f"{run}_{name}.stdout.log")
        mine = [int(x) for x in re.findall(rf"Starting {name} process \(PID: (\d+)", txt)]
        child_self |= set(mine)
        starts = [int(x) for x in re.findall(rf"\] Started {name} \(PID: (\d+)", "\n".join(slog))]
        exits = re.findall(rf"\] {name} \(PID: \d+\) EXITED with code (-?\d+) after ([\d.]+)s uptime", "\n".join(slog))
        backoffs = re.findall(rf"sleeping ([\d.]+)s before restarting {name}\.", "\n".join(slog))
        o.append(f"{name}: starts={len(starts)} self_reported_starts={len(mine)} exits={len(exits)} "
                 f"exit_codes={sorted(set(c for c, _ in exits)) or '-'} "
                 f"uptimes_s={[u for _, u in exits] or '-'} backoffs_s={backoffs or '-'}")
    sup_pids = {int(x) for x in re.findall(r"\(PID: (\d+)", "\n".join(slog))}
    child_pid_logged = {int(x) for x in re.findall(r"child_pid=(\d+)", "\n".join(slog))}
    o.append(f"pids_children_self_reported={len(child_self)} pids_in_supervisor_log={len(sup_pids)} "
             f"overlap_supervisor_PID_field={len(child_self & sup_pids)} child_pid_logged={len(child_pid_logged)} "
             f"overlap_child_pid={len(child_self & child_pid_logged)}/{len(child_self)}")

    wtxt = read(wlog)
    rtxt = read(logs / f"{run}_reaper.stdout.log")
    async with eng.connect() as c:
        for jid in ids:
            j = (await c.execute(text("SELECT status, attempts, claim_generation FROM jobs WHERE id = :i"), {"i": jid})).one()
            ex = (await c.execute(text("SELECT count(*) FROM job_executions WHERE job_id = :i"), {"i": jid})).scalar_one()
            se = (await c.execute(text("SELECT count(*) FROM side_effects WHERE job_id = :i"), {"i": jid})).scalar_one()
            ob = (await c.execute(text("SELECT count(*) FROM outbox WHERE job_id = :i"), {"i": jid})).scalar_one()
            crash = len(re.findall(rf"crash for job_id={jid} ", wtxt))
            rc = rtxt.count(f"[reclaim] job_id={jid} ")
            o.append(f"job id={jid} status={j[0]} attempts={j[1]} gen={j[2]} executions={ex} crash_lines={crash} "
                     f"reclaims={rc} side_effects_rows={se} outbox_rows={ob}")
        seq1 = tuple((await c.execute(text(seq_sql))).one())
    await eng.dispose()
    o.append(f"side_effects_id_seq={seq0[0]}->{seq1[0]} outbox_id_seq={seq0[1]}->{seq1[1]}")
    o.append("worker_traceback_lines=" + str(sum(ln.startswith("Traceback") for ln in read(logs / f"{run}_worker.stderr.log").splitlines())))
    o.append("logs=" + ",".join(sorted(x.name for x in logs.glob(f"{run}_*"))))
    (logs / f"{run}_census.txt").write_text("\n".join(o) + "\n", encoding="utf-8")
    print("\n".join(o))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, type=lambda s: s if re.fullmatch(r"[a-z0-9_]+", s) else ap.error("label: [a-z0-9_]+"))
    ap.add_argument("--payload", required=True)
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--type", default="effect")
    ap.add_argument("--db", default="relay_w6d6")
    ap.add_argument("--seconds", type=float, default=90.0)
    ap.add_argument("--env", action="append", default=[])
    asyncio.run(main(ap.parse_args()))
