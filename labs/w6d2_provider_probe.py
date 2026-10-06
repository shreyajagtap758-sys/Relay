r"""labs/w6d2_provider_probe.py -- Week 6 Din 2, Step 4: the fake provider as the CALLER sees it.
One httpx.AsyncClient(timeout=5.0), calls strictly one at a time. Pass 1 posts once per label and records status,
exception class, str(exc), elapsed, Retry-After, and the provider's own ledger before and after the call. Pass 2
streams three labels to record when the response headers arrived and the largest gap between body chunks.
Prints values only; it writes no conclusions (P-52).
Usage: .\.venv\Scripts\python.exe -u labs\w6d2_provider_probe.py                 (every label + both passes)
       .\.venv\Scripts\python.exe -u labs\w6d2_provider_probe.py ok ok_repeat   (only these labels, pass 1 only)
The TWO HOOKS marked below depend on your Step 2 design and are yours to fill in. Nothing else needs editing."""
import asyncio
import json
import sys
import time

import httpx

BASE = "http://127.0.0.1:8002"
TIMEOUT = 5.0
SLOW_BELOW_S = 3.0  # provider waits this long before answering: below the client timeout
SLOW_ABOVE_S = 7.0  # and this long: above it
PROMPT = "the quick brown fox"
LONGER = "the quick brown fox jumps over the lazy dog again and again"
LABELS = ["ok", "ok_repeat", "ok_longer", "429", "500", "400", "401", "slow_below", "slow_above", "hang", "trickle"]
STREAM_LABELS = ["slow_below", "hang", "trickle"]


# ---------------------------------------------------------------------------------------------------------------
# HOOK 1 (yours): how ONE request selects ONE mode. Return (headers, json_body).
#   - every body carries a prompt: PROMPT, except "ok_longer" which carries LONGER
#   - "ok" and "ok_repeat" must be byte-identical requests
#   - "slow_below" / "slow_above" must make the provider wait SLOW_BELOW_S / SLOW_ABOVE_S before it answers
def request_for(label: str) -> tuple[dict, dict]:
    prompt_text = LONGER if label == "ok_longer" else PROMPT
    mode = "ok" if label in ("ok", "ok_repeat", "ok_longer") else label
    headers = {"X-Fake-Mode": mode}
    if label == "slow_below":
        headers["X-Slow-Seconds"] = str(SLOW_BELOW_S)
    elif label == "slow_above":
        headers["X-Slow-Seconds"] = str(SLOW_ABOVE_S)
    return headers, {"prompt": prompt_text}


# HOOK 2 (yours): the provider's OWN total call count, from YOUR ledger (an endpoint, a log file, or a table).
async def read_ledger(client: httpx.AsyncClient) -> int:
    try:
        r = await client.get(f"{BASE}/v1/ledger", timeout=2.0)
        return int(r.json()["count"])
    except Exception:
        return 0
# ---------------------------------------------------------------------------------------------------------------


async def post_once(client, label, headers, body=None, content=None):
    before = await read_ledger(client)
    t = time.perf_counter()
    status, exc, msg, ra, text = "-", "none", "", None, ""
    try:
        if content is not None:
            r = await client.post(f"{BASE}/v1/complete", headers=headers, content=content)
        else:
            r = await client.post(f"{BASE}/v1/complete", headers=headers, json=body)
        status, ra, text = str(r.status_code), r.headers.get("retry-after"), r.text
    except Exception as e:  # recorded, not handled: the class IS the measurement
        exc, msg = type(e).__name__, str(e)
    elapsed = time.perf_counter() - t
    after = await read_ledger(client)
    print(f"label={label} status={status} exc={exc} str={msg!r} elapsed={elapsed:.3f} retry_after={ra!r} "
          f"ledger_delta={after - before} body={text.strip()[:70]!r}", flush=True)
    return text


async def stream_once(client, label):
    headers, body = request_for(label)
    t = time.perf_counter()
    headers_at, chunks, max_gap, exc = None, 0, 0.0, "none"
    try:
        async with client.stream("POST", f"{BASE}/v1/complete", headers=headers, json=body) as r:
            headers_at = time.perf_counter() - t
            last = time.perf_counter()
            async for _ in r.aiter_raw():
                now = time.perf_counter()
                max_gap, last, chunks = max(max_gap, now - last), now, chunks + 1
    except Exception as e:
        exc = type(e).__name__
    h = "-" if headers_at is None else f"{headers_at:.3f}"
    print(f"stream label={label} headers_at={h} chunks={chunks} max_gap={max_gap:.3f} exc={exc} "
          f"total={time.perf_counter() - t:.3f}", flush=True)


def tokens(text):
    try:
        d = json.loads(text)
        return d.get("tokens_in"), d.get("tokens_out"), sorted(d.keys())
    except Exception:
        return None, None, []


async def main(selected):
    full = selected == LABELS
    sent = 0
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        print(f"timeout_repr={client.timeout!r} labels={','.join(selected)}", flush=True)
        a, b = await read_ledger(client), await read_ledger(client)
        print(f"ledger_read_stable={a == b} ledger_start={a}", flush=True)
        bodies = {}
        for label in selected:
            headers, body = request_for(label)
            bodies[label] = await post_once(client, label, headers, body)
            sent += 1
        if full:
            await post_once(client, "malformed", {"content-type": "application/json"}, content=b"{not json")
            sent += 1
            for label in STREAM_LABELS:
                await stream_once(client, label)
                sent += 1
        if all(k in bodies for k in ("ok", "ok_repeat", "ok_longer")):
            ok, rep, lon = tokens(bodies["ok"]), tokens(bodies["ok_repeat"]), tokens(bodies["ok_longer"])
            print(f"ok_keys={','.join(ok[2])} tokens_ok={ok[:2]} tokens_repeat={rep[:2]} tokens_longer={lon[:2]}", flush=True)
            print(f"tokens_same_for_same_prompt={ok[:2] == rep[:2] and ok[0] is not None} "
                  f"tokens_in_differs_for_longer_prompt={lon[0] is not None and lon[0] != ok[0]}", flush=True)
        end = await read_ledger(client)
        print(f"posts_sent={sent} ledger_end={end} ledger_total_delta={end - a}", flush=True)


if __name__ == "__main__":
    chosen = sys.argv[1:] or LABELS
    unknown = [x for x in chosen if x not in LABELS]
    if unknown:
        raise SystemExit(f"unknown label(s): {unknown}; known: {LABELS}")
    asyncio.run(main(chosen))
