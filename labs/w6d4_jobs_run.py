r"""labs/w6d4_jobs_run.py -- Week 6 Din 4: N jobs through Relay's real worker, on a DISPOSABLE database.
Optionally starts the fake provider (127.0.0.1:8002) and the reaper, starts ONE worker, inserts every job in one
transaction, waits until all are terminal or a deadline, stops every child it started, and writes one census file.
Per job: terminal, attempts, executions, the status sequence the worker's [mark] lines report, the retry delays the
worker says it scheduled, the gaps between executions as the DB recorded them, and the exception class at the end of
last_error. Values and labels only; it writes no conclusions (P-52). Refuses any DB not named relay_w6d4*.
--env prints NAMES only, never values. The DB must already exist and be migrated (BRIEF Step 1).
Usage (PowerShell -- single quotes keep the JSON intact):
  .\.venv\Scripts\python.exe -u labs\w6d4_jobs_run.py --label s3_401 --fake --payload '{"prompt": "the quick brown fox", "fake_mode": "401"}'
Options: --payload JSON (repeatable; each one is inserted --count times; "__I__" inside it becomes the job's index) ·
--count N · --type (default llm_completion) · --db (default relay_w6d4) · --table NAME (count NAME's rows per job;
repeatable) · --env NAME=VALUE (worker env; repeatable) · --reaper · --break-executions (rename job_executions away
BEFORE any process starts, restore it after every process is stopped) · --deadline S · --linger S (default 2)."""
import argparse
import asyncio
import datetime as dt
import json
import os
import re
import subprocess
import time
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

REPO = Path(__file__).resolve().parents[1]
PY = REPO / ".venv" / "Scripts" / "python.exe"
FAKE = "http://127.0.0.1:8002"
TERMINAL = {"succeeded", "dead_letter", "failed"}


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


def start(name: str, module_args: list[str], env: dict, run: str, logs: Path) -> subprocess.Popen:
    e = dict(env, RELAY_PROCESS_NAME=f"{name}_w6d4")
    out = open(logs / f"{run}_{name}.log", "w", encoding="utf-8")
    err = open(logs / f"{run}_{name}.err.log", "w", encoding="utf-8")
    return subprocess.Popen([str(PY), "-u", *module_args], cwd=REPO, env=e, stdout=out, stderr=err)


def stop_all(procs: list[subprocess.Popen]) -> int:
    for p in reversed(procs):
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
    for p in procs:
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
    # the venv python.exe is a launcher stub; the real interpreter is its child (P-53(b)) -- sweep by command line
    ps = ("$n = @(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*"
          + str(REPO) + "*' -and $_.CommandLine -match '(src|relay)\\.(worker|reaper|fake_provider)' });"
          " $n | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; $n.Count")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    return int(r.stdout.strip() or "0")


def wait_for_line(path: Path, needle: str, seconds: float) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if path.exists() and needle in path.read_text(encoding="utf-8", errors="replace"):
            return True
        time.sleep(0.2)
    return False


async def ledger(client: httpx.AsyncClient):
    try:
        r = await client.get(f"{FAKE}/v1/ledger", timeout=3.0)
        data = r.json()
        return data.get("calls") if "calls" in data else data.get("count")
    except Exception as exc:
        return f"ERR:{type(exc).__name__}"


def last_class(le: str) -> str:
    # the LAST line naming an exception class; SQLAlchemy tracebacks end with a "(Background on this error ...)" line
    lines = [ln.strip() for ln in (le or "").strip().splitlines() if ln.strip()]
    if not lines:
        return "-"
    for ln in reversed(lines):
        m = re.match(r"^([A-Za-z_][\w.]*(?:Error|Exception|Exit|Interrupt))\b", ln)
        if m:
            return m.group(1)
    return "unparsed"


async def main(a) -> None:
    if not re.fullmatch(r"relay_w6d4[a-z0-9_]*", a.db):
        raise SystemExit(f"refusing db={a.db!r}: this harness only runs on relay_w6d4* (never the evidence DB)")
    for t in a.table:
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", t):
            raise SystemExit(f"bad table name {t!r}")
    if not a.payload:
        raise SystemExit("at least one --payload")
    for p in a.payload:
        json.loads(p.replace("__I__", "0"))  # fail before starting anything if a payload is not JSON
    url = re.sub(r"/[^/]+$", f"/{a.db}", base_url())
    if not url.endswith(f"/{a.db}"):
        raise SystemExit("DATABASE_URL rewrite failed")
    logs = REPO / "logs"
    logs.mkdir(exist_ok=True)
    run = f"w6d4_{a.label}_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    o: list[str] = [f"run_id={run}"]
    o.append(f"label={a.label} type={a.type} fake={a.fake} reaper={a.reaper} count={a.count} "
             f"payloads={len(a.payload)} break_executions={a.break_executions} "
             f"extra_env_names={','.join(p.split('=', 1)[0] for p in a.env) or '-'}")
    o.append("head=" + git("rev-parse", "--short", "HEAD"))
    src_dir = "relay/" if (REPO / "relay").exists() else "src/"
    o.append("src_diff_files_vs_HEAD=" + ",".join(git("diff", "--name-only", "HEAD", "--", src_dir, "alembic/").split()))
    o.append("src_untracked=" + ",".join(git("ls-files", "--others", "--exclude-standard", "--", src_dir, "alembic/").split()))

    eng = create_async_engine(url, echo=False)
    async with eng.connect() as c:
        o.append("current_database=" + (await c.execute(text("SELECT current_database()"))).scalar_one())
        try:
            o.append("db_revision=" + ",".join(r[0] for r in (await c.execute(text("SELECT version_num FROM alembic_version"))).all()))
        except Exception as exc:
            raise SystemExit("\n".join(o) + f"\ndb_revision=ERR:{type(exc).__name__} -- DB not migrated, run BRIEF Step 1 first")
        o.append("jobs_before=" + str((await c.execute(text("SELECT count(*) FROM jobs"))).scalar_one()))
        left = (await c.execute(text("SELECT count(*) FROM jobs WHERE status NOT IN ('succeeded', 'dead_letter', 'failed')"))).scalar_one()
        o.append(f"nonterminal_before={left}")
        if left:
            # a job left running/pending by an earlier run gets claimed or reclaimed during this one and mixes its
            # lines into this census (reviewer's own P-51 arm B was contaminated exactly this way)
            raise SystemExit("\n".join(o) + "\nrefusing: earlier non-terminal jobs exist -- see BRIEF Step 5 cleanup")

    env = dict(os.environ, DATABASE_URL=url, PYTHONUNBUFFERED="1")
    for pair in a.env:
        k, v = pair.split("=", 1)
        env[k] = v
    procs: list[subprocess.Popen] = []
    ids: list[int] = []
    broke = False
    t_ins = None
    pkg = "relay" if (REPO / "relay").exists() else "src"
    try:
        if a.break_executions:
            async with eng.begin() as c:
                await c.execute(text("ALTER TABLE job_executions RENAME TO job_executions_w6d4_off"))
            broke = True
            o.append("executions_table=renamed_away")
        async with httpx.AsyncClient() as hc:
            try:
                if a.fake:
                    procs.append(start("provider", ["-m", "uvicorn", f"{pkg}.fake_provider:app", "--host", "127.0.0.1",
                                                    "--port", "8002"], env, run, logs))
                    for _ in range(60):
                        if isinstance(await ledger(hc), int):
                            break
                        await asyncio.sleep(0.25)
                led0 = await ledger(hc) if a.fake else "-"
                if a.reaper:
                    procs.append(start("reaper", ["-m", f"{pkg}.reaper"], env, run, logs))
                procs.append(start("worker", ["-m", f"{pkg}.worker"], env, run, logs))
                o.append("worker_ready=" + str(wait_for_line(logs / f"{run}_worker.log", "Starting worker process", 20)))
                async with eng.begin() as c:
                    i = 0
                    for p in a.payload:
                        for _ in range(a.count):
                            row = (await c.execute(text("INSERT INTO jobs (type, payload) VALUES (:t, CAST(:p AS jsonb)) "
                                                        "RETURNING id"), {"t": a.type, "p": p.replace("__I__", str(i))})).one()
                            ids.append(row[0])
                            i += 1
                t_ins = time.monotonic()
                o.append(f"job_ids={ids[0]}..{ids[-1]} n={len(ids)}")
                deadline = t_ins + a.deadline
                statuses: dict = {}
                while time.monotonic() < deadline:
                    async with eng.connect() as c:
                        statuses = dict((await c.execute(text("SELECT id, status FROM jobs WHERE id = ANY(:i)"),
                                                         {"i": ids})).all())
                    if all(s in TERMINAL for s in statuses.values()):
                        break
                    await asyncio.sleep(0.25)
                done = sum(s in TERMINAL for s in statuses.values())
                o.append(f"all_terminal={done == len(ids)} terminal_jobs={done}/{len(ids)} wait_s={time.monotonic() - t_ins:.3f}")
                await asyncio.sleep(a.linger)
                led1 = await ledger(hc) if a.fake else "-"
                o.append(f"ledger_before={led0} ledger_after={led1} ledger_delta="
                         + (str(led1 - led0) if isinstance(led0, int) and isinstance(led1, int) else "-"))
            finally:
                o.append(f"swept_leftover_python={stop_all(procs)}")
    finally:
        if broke:
            async with eng.begin() as c:
                await c.execute(text("ALTER TABLE job_executions_w6d4_off RENAME TO job_executions"))
            o.append("executions_table=restored")

    wtext = (logs / f"{run}_worker.log").read_text(encoding="utf-8", errors="replace") if procs else ""
    w = wtext.splitlines()
    rp = (logs / f"{run}_reaper.log").read_text(encoding="utf-8", errors="replace").splitlines() if a.reaper else []
    agg = {"terminal": {}, "attempts": 0, "executions": 0, "tables": {t: 0 for t in a.table}}
    async with eng.connect() as c:
        for jid in ids:
            j = (await c.execute(text("SELECT status, attempts, claim_generation, payload::text, last_error FROM jobs "
                                      "WHERE id = :i"), {"i": jid})).one()
            ex = (await c.execute(text("SELECT executed_at FROM job_executions WHERE job_id = :i ORDER BY id"),
                                  {"i": jid})).scalars().all()
            gaps = [f"{(b - x).total_seconds():.3f}" for x, b in zip(ex, ex[1:])]
            marks = [m.group(1) for ln in w if (m := re.search(rf"\[mark\] Marked job {jid} as '(\w+)'", ln))]
            # an exception message can span lines (SQLAlchemy's does), so match across them, shortest first
            sched = re.findall(rf"Job_id={jid} failed attempt \d+/\d+: .*?Scheduling retry in ([\d.]+)s", wtext, re.S)
            hb = sum(bool(re.search(rf"Heartbeat sent for job_id={jid}\b", ln)) for ln in w)
            rc = sum(f"[reclaim] job_id={jid} " in ln for ln in rp)
            tcounts = []
            for t in a.table:
                n = (await c.execute(text(f"SELECT count(*) FROM {t} WHERE job_id = :i"), {"i": jid})).scalar_one()
                agg["tables"][t] += n
                tcounts.append(f"{t}_rows={n}")
            agg["terminal"][j[0]] = agg["terminal"].get(j[0], 0) + 1
            agg["attempts"] += j[1]
            agg["executions"] += len(ex)
            o.append(f"job id={jid} status={j[0]} attempts={j[1]} gen={j[2]} executions={len(ex)} "
                     f"mark_seq={marks or '-'} scheduled_retry_s={sched or '-'} exec_gaps_s={gaps or '-'} "
                     f"heartbeats={hb} reclaims={rc} {' '.join(tcounts)} last_error_class={last_class(j[4])} "
                     f"last_error_len={len(j[4] or '')} payload={j[3]}")
    await eng.dispose()
    o.append("totals terminal=" + json.dumps(agg["terminal"], sort_keys=True) + f" sum_attempts={agg['attempts']} "
             f"sum_executions={agg['executions']} " + " ".join(f"sum_{t}_rows={n}" for t, n in agg["tables"].items()))
    o.append("worker_error_tags=" + str(sum(any(t in ln for t in ("[poll_error]", "[heartbeat_error]", "[mark_error]",
                                                                       "[heartbeat_join_error]", "[mark_abandoned]")) for ln in w)))
    o.append("worker_traceback_lines=" + str(sum(ln.startswith("Traceback") for ln in w)))
    if a.fake:
        p = (logs / f"{run}_provider.log").read_text(encoding="utf-8", errors="replace").splitlines()
        p += (logs / f"{run}_provider.err.log").read_text(encoding="utf-8", errors="replace").splitlines()
        o.append("provider_access_post_lines=" + str(sum('"POST /v1/complete HTTP/1.1"' in ln for ln in p)))
        o.append("provider_status_counts=" + json.dumps(
            {s: sum(f'"POST /v1/complete HTTP/1.1" {s}' in ln for ln in p) for s in ("200", "400", "401", "429", "500")}))
    o.append("logs=" + ",".join(sorted(x.name for x in logs.glob(f"{run}_*"))))
    out = logs / f"{run}_census.txt"
    out.write_text("\n".join(o) + "\n", encoding="utf-8")
    print("\n".join(o))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, type=lambda s: s if re.fullmatch(r"[a-z0-9_]+", s) else ap.error("label: [a-z0-9_]+"))
    ap.add_argument("--payload", action="append", default=[])
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--type", default="llm_completion")
    ap.add_argument("--db", default="relay_w6d4")
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--reaper", action="store_true")
    ap.add_argument("--break-executions", action="store_true")
    ap.add_argument("--deadline", type=float, default=60.0)
    ap.add_argument("--linger", type=float, default=2.0)
    ap.add_argument("--table", action="append", default=[])
    ap.add_argument("--env", action="append", default=[])
    asyncio.run(main(ap.parse_args()))
