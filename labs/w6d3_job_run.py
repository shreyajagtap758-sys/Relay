r"""labs/w6d3_job_run.py -- Week 6 Din 3: ONE job through Relay's real worker, on a DISPOSABLE database.
Optionally starts the fake provider (127.0.0.1:8002) and the reaper, starts the worker, inserts one job, waits for a
terminal status or a deadline, stops every child it started, and writes one census file. Values and labels only; it
writes no conclusions (P-52). Refuses the evidence DB `relay`. The DB must already exist and be migrated (Step 2a).
Usage (PowerShell -- single quotes keep the JSON intact):
  .\.venv\Scripts\python.exe -u labs\w6d3_job_run.py --label ok --fake --payload '{"prompt": "the quick brown fox"}'
Options: --db (default relay_w6d3) · --type (default llm_completion) · --table NAME (also dump NAME's rows whose
job_id is this job; repeatable) · --env NAME=VALUE (extra env for the worker; repeatable) · --reaper · --deadline S ·
--linger S (keep the processes S seconds after the terminal status, default 2)."""
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
ECHO_TS = r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3}) INFO sqlalchemy\.engine\.Engine "


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
    e = dict(env, RELAY_PROCESS_NAME=f"{name}_w6d3")
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
          + str(REPO) + "*' -and $_.CommandLine -match '(relay|src)\\.(worker|reaper|fake_provider)' });"
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
        return data.get("count") if "count" in data else data.get("calls")
    except Exception as exc:
        return f"ERR:{type(exc).__name__}"


async def main(a) -> None:
    if not re.fullmatch(r"relay_w6d3[a-z0-9_]*", a.db):
        raise SystemExit(f"refusing db={a.db!r}: this harness only runs on relay_w6d3* (never the evidence DB)")
    for t in a.table:
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", t):
            raise SystemExit(f"bad table name {t!r}")
    json.loads(a.payload)  # fail before starting anything if the payload is not JSON
    url = re.sub(r"/[^/]+$", f"/{a.db}", base_url())
    if not url.endswith(f"/{a.db}"):
        raise SystemExit("DATABASE_URL rewrite failed")
    logs = REPO / "logs"
    logs.mkdir(exist_ok=True)
    run = f"w6d3_{a.label}_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    o: list[str] = []
    o.append(f"run_id={run}")
    o.append(f"label={a.label} type={a.type} fake={a.fake} reaper={a.reaper} extra_env={','.join(a.env) or '-'}")
    src_dir = "relay/" if (REPO / "relay").exists() else "src/"
    o.append("src_diff_files_vs_HEAD=" + ",".join(git("diff", "--name-only", "HEAD", "--", src_dir, "alembic/").split()))
    o.append("src_untracked=" + ",".join(git("ls-files", "--others", "--exclude-standard", "--", src_dir, "alembic/").split()))

    eng = create_async_engine(url, echo=False)
    async with eng.connect() as c:
        o.append("current_database=" + (await c.execute(text("SELECT current_database()"))).scalar_one())
        try:
            o.append("db_revision=" + ",".join(r[0] for r in (await c.execute(text("SELECT version_num FROM alembic_version"))).all()))
        except Exception as exc:
            o.append(f"db_revision=ERR:{type(exc).__name__}")
            raise SystemExit("\n".join(o) + "\nDB not migrated -- run Step 2a first")
        o.append("jobs_before=" + str((await c.execute(text("SELECT count(*) FROM jobs"))).scalar_one()))

    env = dict(os.environ, DATABASE_URL=url, PYTHONUNBUFFERED="1")
    for pair in a.env:
        k, v = pair.split("=", 1)
        env[k] = v
    procs: list[subprocess.Popen] = []
    job_id, status, t_ins = None, "not_inserted", None
    pkg = "relay" if (REPO / "relay").exists() else "src"
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
                row = (await c.execute(text("INSERT INTO jobs (type, payload) VALUES (:t, CAST(:p AS jsonb)) "
                                            "RETURNING id, clock_timestamp()"), {"t": a.type, "p": a.payload})).one()
            job_id, t_ins = row[0], time.monotonic()
            o.append(f"job_id={job_id} inserted_at={row[1].isoformat()}")
            deadline = t_ins + a.deadline
            while time.monotonic() < deadline:
                async with eng.connect() as c:
                    status = (await c.execute(text("SELECT status FROM jobs WHERE id = :i"), {"i": job_id})).scalar_one()
                if status in TERMINAL:
                    break
                await asyncio.sleep(0.25)
            o.append(f"terminal={status if status in TERMINAL else 'deadline:' + status} "
                     f"wait_s={time.monotonic() - t_ins:.3f}")
            await asyncio.sleep(a.linger)
            led1 = await ledger(hc) if a.fake else "-"
            o.append(f"ledger_before={led0} ledger_after={led1} ledger_delta="
                     + (str(led1 - led0) if isinstance(led0, int) and isinstance(led1, int) else "-"))
        finally:
            o.append(f"swept_leftover_python={stop_all(procs)}")

    if job_id is not None:
        async with eng.connect() as c:
            j = (await c.execute(text("SELECT to_jsonb(j) - 'payload' - 'last_error', j.last_error FROM jobs j "
                                      "WHERE j.id = :i"), {"i": job_id})).one()
            o.append("job_row=" + json.dumps(j[0], sort_keys=True)[:2000])
            le = j[1] or ""
            tail = [ln.strip() for ln in le.strip().splitlines() if ln.strip()][-3:]
            o.append(f"last_error_len={len(le)} last_error_tail=" + " | ".join(tail)[:600])
            ex = (await c.execute(text("SELECT count(*), array_agg(claim_generation ORDER BY id), "
                                       "EXTRACT(EPOCH FROM (SELECT completed_at FROM jobs WHERE id = :i) - min(executed_at)), "
                                       "EXTRACT(EPOCH FROM (SELECT completed_at FROM jobs WHERE id = :i) - max(executed_at)) "
                                       "FROM job_executions WHERE job_id = :i"), {"i": job_id})).one()
            o.append(f"executions={ex[0]} execution_generations={ex[1]} completed_minus_first_executed_s="
                     f"{'-' if ex[2] is None else f'{float(ex[2]):.3f}'} completed_minus_last_executed_s="
                     f"{'-' if ex[3] is None else f'{float(ex[3]):.3f}'}")
            for t in a.table:
                rows = (await c.execute(text(f"SELECT to_jsonb(t) FROM {t} t WHERE t.job_id = :i ORDER BY 1"),
                                        {"i": job_id})).all()
                o.append(f"table={t} rows={len(rows)}")
                for r in rows:
                    o.append(f"  {t}: " + json.dumps(r[0], sort_keys=True)[:1000])
    await eng.dispose()

    w = (logs / f"{run}_worker.log").read_text(encoding="utf-8", errors="replace").splitlines()
    jid = str(job_id)
    o.append("worker_claim_lines=" + str(sum(f"[claim] Claimed job {jid} " in ln or f"Claimed job_id={jid}" in ln for ln in w)))
    o.append("worker_execute_lines=" + str(sum(f"[execute] Executing job {jid} " in ln or f"Executing job_id={jid}" in ln for ln in w)))
    o.append("worker_failed_attempt_lines=" + str(sum(f"Job_id={jid} failed attempt" in ln for ln in w)))
    o.append("worker_mark_lines=" + str(sum(f"[mark] Marked job {jid} " in ln or f"Marked job_id={jid}" in ln for ln in w)))
    o.append("worker_heartbeat_sent_lines=" + str(sum(f"Heartbeat sent for job_id={jid}" in ln for ln in w)))
    o.append("worker_error_tags=" + str(sum(any(t in ln for t in ("[poll_error]", "[heartbeat_error]", "[mark_error]",
                                                                       "[heartbeat_join_error]")) for ln in w)))
    hb = [m.group(1) for ln in w if (m := re.match(ECHO_TS + r"UPDATE jobs SET claimed_at=now\(\)", ln))]
    ex_at = [m.group(1) for ln in w if (m := re.match(ECHO_TS + r"INSERT INTO job_executions", ln))]
    o.append("echo_heartbeat_update_at=" + (",".join(x[11:] for x in hb) or "-"))
    o.append("echo_execution_insert_at=" + (",".join(x[11:] for x in ex_at) or "-"))
    if a.reaper:
        r = (logs / f"{run}_reaper.log").read_text(encoding="utf-8", errors="replace").splitlines()
        o.append("reaper_reclaim_lines=" + str(sum(f"[reclaim] job_id={jid} " in ln for ln in r)))
    if a.fake:
        p = (logs / f"{run}_provider.log").read_text(encoding="utf-8", errors="replace").splitlines()
        if (logs / f"{run}_provider.err.log").exists():
            p += (logs / f"{run}_provider.err.log").read_text(encoding="utf-8", errors="replace").splitlines()
        o.append("provider_access_post_lines=" + str(sum('"POST /v1/complete HTTP/1.1"' in ln for ln in p)))
    o.append("logs=" + ",".join(sorted(x.name for x in logs.glob(f"{run}_*"))))
    out = logs / f"{run}_census.txt"
    out.write_text("\n".join(o) + "\n", encoding="utf-8")
    print("\n".join(o))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, type=lambda s: s if re.fullmatch(r"[a-z0-9_]+", s) else ap.error("label: [a-z0-9_]+"))
    ap.add_argument("--payload", required=True)
    ap.add_argument("--type", default="llm_completion")
    ap.add_argument("--db", default="relay_w6d3")
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--reaper", action="store_true")
    ap.add_argument("--deadline", type=float, default=60.0)
    ap.add_argument("--linger", type=float, default=2.0)
    ap.add_argument("--table", action="append", default=[])
    ap.add_argument("--env", action="append", default=[])
    asyncio.run(main(ap.parse_args()))
