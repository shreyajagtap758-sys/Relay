r"""labs/w6d5_jobs_run.py -- Week 6 Din 5: N jobs through Relay's real worker(s), on a DISPOSABLE database.
Same contract as w6d4_jobs_run.py (values and labels only, P-52; refuses any DB not named relay_w6d5*; --env prints
NAMES only), plus what Din 5 needs:
  --workers N        start N workers (worker_0 .. worker_N-1); marks/heartbeats are read from all of them
  ledger timeline    the fake's /v1/ledger is sampled every 0.25 s into <run>_ledger.txt; the census gets the first
                     call time, the peak calls in any 1 s window, and (with --window S) the calls in the first S s
  --gap-threshold S  counts execution gaps (DB executed_at deltas) shorter than S -- "came back before S"
  worker exit codes  read BEFORE the harness kills anything: alive / exit code (an os._exit(1) shows as 1)
  per job            mark conflicts (fenced or status changed), heartbeat-lost lines, and for every --table that has a
                     claim_generation column, the generations of its rows
Usage (PowerShell -- single quotes keep the JSON intact):
  .\.venv\Scripts\python.exe -u labs\w6d5_jobs_run.py --label s1_control --fake --workers 2 --count 30 --payload '{"prompt": "job __I__ quick brown fox", "fake_mode": "ok"}'
Options: --payload JSON (repeatable; each inserted --count times; "__I__" becomes the job's index) · --count N ·
--type (default llm_completion) · --db (default relay_w6d5) · --table NAME (repeatable) · --env NAME=VALUE (repeatable)
· --workers N · --reaper · --window S · --gap-threshold S · --deadline S · --linger S (default 2)."""
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
    e = dict(env, RELAY_PROCESS_NAME=f"{name}_w6d5")
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
        return (await client.get(f"{FAKE}/v1/ledger", timeout=3.0)).json().get("calls")
    except Exception as exc:
        return f"ERR:{type(exc).__name__}"


async def sampler(client: httpx.AsyncClient, samples: list, stop: asyncio.Event) -> None:
    while not stop.is_set():
        v = await ledger(client)
        if isinstance(v, int):
            samples.append((time.monotonic(), v))
        try:
            await asyncio.wait_for(stop.wait(), timeout=0.25)
        except asyncio.TimeoutError:
            pass


def last_class(le: str) -> str:
    lines = [ln.strip() for ln in (le or "").strip().splitlines() if ln.strip()]
    if not lines:
        return "-"
    for ln in reversed(lines):
        m = re.match(r"^([A-Za-z_][\w.]*(?:Error|Exception|Exit|Interrupt))\b", ln)
        if m:
            return m.group(1)
    return "unparsed"


async def main(a) -> None:
    if not re.fullmatch(r"relay_w6d5[a-z0-9_]*", a.db):
        raise SystemExit(f"refusing db={a.db!r}: this harness only runs on relay_w6d5* (never the evidence DB)")
    for t in a.table:
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", t):
            raise SystemExit(f"bad table name {t!r}")
    if not a.payload:
        raise SystemExit("at least one --payload")
    if a.workers < 1:
        raise SystemExit("--workers >= 1")
    for p in a.payload:
        json.loads(p.replace("__I__", "0"))
    url = re.sub(r"/[^/]+$", f"/{a.db}", base_url())
    if not url.endswith(f"/{a.db}"):
        raise SystemExit("DATABASE_URL rewrite failed")
    logs = REPO / "logs"
    logs.mkdir(exist_ok=True)
    run = f"w6d5_{a.label}_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    o: list[str] = [f"run_id={run}"]
    o.append(f"label={a.label} type={a.type} fake={a.fake} reaper={a.reaper} workers={a.workers} count={a.count} "
             f"payloads={len(a.payload)} window={a.window} gap_threshold={a.gap_threshold} "
             f"extra_env_names={','.join(p.split('=', 1)[0] for p in a.env) or '-'}")
    o.append("head=" + git("rev-parse", "--short", "HEAD"))
    o.append("src_diff_files_vs_HEAD=" + ",".join(git("diff", "--name-only", "HEAD", "--", "src/", "relay/", "alembic/").split()))
    o.append("src_untracked=" + ",".join(git("ls-files", "--others", "--exclude-standard", "--", "src/", "relay/", "alembic/").split()))

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
            raise SystemExit("\n".join(o) + "\nrefusing: earlier non-terminal jobs exist -- see BRIEF cleanup line")
        gen_tables = set()
        for t in a.table:
            has = (await c.execute(text("SELECT count(*) FROM information_schema.columns WHERE table_name = :t AND "
                                        "column_name = 'claim_generation'"), {"t": t})).scalar_one()
            if has:
                gen_tables.add(t)

    env = dict(os.environ, DATABASE_URL=url, PYTHONUNBUFFERED="1")
    for pair in a.env:
        k, v = pair.split("=", 1)
        env[k] = v
    procs: list[subprocess.Popen] = []
    workers: list[subprocess.Popen] = []
    ids: list[int] = []
    samples: list = []
    t_ins = None
    led0 = "-"
    pkg = "relay" if (REPO / "relay").exists() else "src"
    async with httpx.AsyncClient() as hc:
        stop = asyncio.Event()
        samp = None
        try:
            if a.fake:
                procs.append(start("provider", ["-m", "uvicorn", f"{pkg}.fake_provider:app", "--host", "127.0.0.1",
                                                "--port", "8002"], env, run, logs))
                for _ in range(60):
                    if isinstance(await ledger(hc), int):
                        break
                    await asyncio.sleep(0.25)
                led0 = await ledger(hc)
            if a.reaper:
                procs.append(start("reaper", ["-m", f"{pkg}.reaper"], env, run, logs))
            for i in range(a.workers):
                w = start(f"worker_{i}", ["-m", f"{pkg}.worker"], env, run, logs)
                procs.append(w)
                workers.append(w)
            ready = [wait_for_line(logs / f"{run}_worker_{i}.log", "Starting worker process", 20) for i in range(a.workers)]
            o.append("workers_ready=" + str(sum(ready)) + f"/{a.workers}")
            if a.fake:
                samp = asyncio.create_task(sampler(hc, samples, stop))
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
            o.append("worker_exit=" + ",".join("alive" if w.poll() is None else str(w.returncode) for w in workers))
        finally:
            stop.set()
            if samp:
                await samp
            o.append(f"swept_leftover_python={stop_all(procs)}")

    if a.fake and t_ins is not None and isinstance(led0, int):
        rel = [(t - t_ins, v - led0) for t, v in samples]
        (logs / f"{run}_ledger.txt").write_text("".join(f"t_rel_s={t:.3f} calls={v}\n" for t, v in rel), encoding="utf-8")
        first = next((t for t, v in rel if v > 0), None)
        peak = 0
        for i, (ti, vi) in enumerate(rel):
            for tj, vj in rel[i:]:
                if tj - ti > 1.0:
                    break
                peak = max(peak, vj - vi)
        o.append(f"ledger_samples={len(rel)} first_call_s=" + (f"{first:.3f}" if first is not None else "-")
                 + f" peak_calls_in_any_1s={peak}")
        if a.window is not None and first is not None:
            in_w = max((v for t, v in rel if t <= first + a.window), default=0)
            total = rel[-1][1] if rel else 0
            o.append(f"window_s={a.window} calls_in_window={in_w} window_avg_calls_per_s={in_w / a.window:.2f} "
                     f"calls_after_window={total - in_w}")

    wlines: list[str] = []
    wtext = ""
    for i in range(len(workers)):
        t_ = (logs / f"{run}_worker_{i}.log").read_text(encoding="utf-8", errors="replace")
        wtext += t_ + "\n"
        wlines += t_.splitlines()
    rp = (logs / f"{run}_reaper.log").read_text(encoding="utf-8", errors="replace").splitlines() if a.reaper else []
    agg = {"terminal": {}, "attempts": 0, "executions": 0, "tables": {t: 0 for t in a.table}}
    gaps_all: list[float] = []
    async with eng.connect() as c:
        for jid in ids:
            j = (await c.execute(text("SELECT status, attempts, claim_generation, payload::text, last_error, "
                                      "completed_at FROM jobs WHERE id = :i"), {"i": jid})).one()
            ex = (await c.execute(text("SELECT executed_at FROM job_executions WHERE job_id = :i ORDER BY id"),
                                  {"i": jid})).scalars().all()
            gaps = [(b - x).total_seconds() for x, b in zip(ex, ex[1:])]
            gaps_all += gaps
            span = f"{(j[5] - ex[0]).total_seconds():.3f}" if (j[5] is not None and ex) else "-"
            # worker lines carry no timestamp, and with N workers one job's lines sit in different files -- so marks
            # are COUNTED, not sequenced, and retry delays are ordered by the attempt number the line itself prints
            mk: dict = {}
            for ln in wlines:
                if m := re.search(rf"\[mark\] Marked job {jid} as '(\w+)'", ln):
                    mk[m.group(1)] = mk.get(m.group(1), 0) + 1
            marks = json.dumps(mk, sort_keys=True) if mk else "-"
            sched = [d for _, d in sorted((int(n), d) for n, d in re.findall(
                rf"Job_id={jid} failed attempt (\d+)/\d+: .*?Scheduling retry in ([\d.]+)s", wtext, re.S))]
            hb = sum(bool(re.search(rf"Heartbeat sent for job_id={jid}\b", ln)) for ln in wlines)
            hb_lost = sum(bool(re.search(rf"Heartbeat lost: job_id={jid}\b", ln)) for ln in wlines)
            conflicts = sum(bool(re.search(rf"(Conflict on mark|Mark fenced): job_id={jid}\b", ln)) for ln in wlines)
            rc = sum(f"[reclaim] job_id={jid} " in ln for ln in rp)
            tcounts = []
            for t in a.table:
                if t in gen_tables:
                    gens = (await c.execute(text(f"SELECT claim_generation FROM {t} WHERE job_id = :i ORDER BY id"),
                                            {"i": jid})).scalars().all()
                    n = len(gens)
                    tcounts.append(f"{t}_rows={n} {t}_gens={list(gens) or '-'}")
                else:
                    n = (await c.execute(text(f"SELECT count(*) FROM {t} WHERE job_id = :i"), {"i": jid})).scalar_one()
                    tcounts.append(f"{t}_rows={n}")
                agg["tables"][t] += n
            agg["terminal"][j[0]] = agg["terminal"].get(j[0], 0) + 1
            agg["attempts"] += j[1]
            agg["executions"] += len(ex)
            o.append(f"job id={jid} status={j[0]} attempts={j[1]} gen={j[2]} executions={len(ex)} "
                     f"mark_counts={marks} scheduled_retry_s={sched or '-'} "
                     f"exec_gaps_s={[f'{g:.3f}' for g in gaps] or '-'} span_s={span} heartbeats={hb} hb_lost={hb_lost} "
                     f"mark_conflicts={conflicts} reclaims={rc} {' '.join(tcounts)} last_error_class={last_class(j[4])} "
                     f"payload={j[3]}")
    await eng.dispose()
    o.append("totals terminal=" + json.dumps(agg["terminal"], sort_keys=True) + f" sum_attempts={agg['attempts']} "
             f"sum_executions={agg['executions']} " + " ".join(f"sum_{t}_rows={n}" for t, n in agg["tables"].items()))
    if a.gap_threshold is not None:
        below = sum(g < a.gap_threshold for g in gaps_all)
        o.append(f"exec_gaps_below_threshold={below}/{len(gaps_all)} threshold_s={a.gap_threshold} "
                 + (f"min_gap_s={min(gaps_all):.3f} max_gap_s={max(gaps_all):.3f}" if gaps_all else "min_gap_s=- max_gap_s=-"))
    o.append("worker_error_tags=" + str(sum(any(t in ln for t in ("[poll_error]", "[heartbeat_error]", "[mark_error]",
                                                                       "[heartbeat_join_error]", "[mark_abandoned]",
                                                                       "[instrument_error]")) for ln in wlines)))
    o.append("worker_traceback_lines=" + str(sum(ln.startswith("Traceback") for ln in wlines)))
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
    ap.add_argument("--db", default="relay_w6d5")
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--reaper", action="store_true")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--window", type=float, default=None)
    ap.add_argument("--gap-threshold", type=float, default=None)
    ap.add_argument("--deadline", type=float, default=60.0)
    ap.add_argument("--linger", type=float, default=2.0)
    ap.add_argument("--table", action="append", default=[])
    ap.add_argument("--env", action="append", default=[])
    asyncio.run(main(ap.parse_args()))
