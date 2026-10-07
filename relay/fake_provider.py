import asyncio
import json
import random
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

flaky_rng = random.Random(42)

app = FastAPI(title="Fake LLM Provider")

call_count = 0
print("[fake_provider] listening on 127.0.0.1:8002 ledger=in_memory", flush=True)


@app.get("/v1/ledger")
async def get_ledger():
    return {"count": call_count}


@app.post("/v1/complete")
async def complete(request: Request):
    global call_count
    # Handler-level counter: incremented only when request reaches the handler
    call_count += 1

    # Check for malformed JSON if raw content was sent
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "malformed_json"})

    mode = request.headers.get("X-Fake-Mode", "ok")
    prompt = body.get("prompt", "")

    # Deterministic token calculation
    tokens_in = len(prompt.split()) if prompt else 0
    tokens_out = 8

    if mode in ("ok", "ok_repeat", "ok_longer"):
        return {
            "text": "simulated response",
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }

    elif mode == "429":
        raw_ra = request.headers.get("X-Fake-Retry-After") or request.headers.get("Retry-After") or "2"
        try:
            ra_int = min(int(raw_ra), 60)
        except Exception:
            ra_int = 2
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(ra_int)},
            content={"error": "rate_limit_exceeded"},
        )

    elif mode == "flaky":
        raw_pct = request.headers.get("X-Fake-Fail-Pct", "30")
        try:
            fail_pct = float(raw_pct)
        except Exception:
            fail_pct = 30.0
        if flaky_rng.uniform(0, 100) < fail_pct:
            return JSONResponse(status_code=500, content={"error": "flaky_internal_server_error"})
        return {
            "text": "simulated flaky response",
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }

    elif mode == "500":
        return JSONResponse(status_code=500, content={"error": "internal_server_error"})

    elif mode == "400":
        return JSONResponse(status_code=400, content={"error": "bad_request"})

    elif mode == "401":
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    elif mode in ("slow", "slow_below", "slow_above"):
        raw_sec = request.headers.get("X-Slow-Seconds", "3.0")
        try:
            seconds = min(float(raw_sec), 30.0)
        except Exception:
            seconds = 3.0
        await asyncio.sleep(seconds)
        return {
            "text": "simulated slow response",
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }

    elif mode == "hang":
        # Silence: wait 12s (well above client's 5.0s timeout), returning nothing
        await asyncio.sleep(12.0)
        return {"text": "hung_response"}

    elif mode == "trickle":
        # Trickle: send headers immediately (200), then chunk bytes every 1.2s for >= 8s
        async def trickle_stream():
            chunks = [
                b'{"text":',
                b' "simulated',
                b' trickle",',
                b' "tokens_in":',
                f' {tokens_in},'.encode("utf-8"),
                b' "tokens_out":',
                f' {tokens_out}}}'.encode("utf-8"),
            ]
            for chunk in chunks:
                yield chunk
                await asyncio.sleep(1.2)

        return StreamingResponse(trickle_stream(), media_type="application/json")

    return JSONResponse(status_code=400, content={"error": f"unknown_mode_{mode}"})
