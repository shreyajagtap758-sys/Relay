import asyncio
import socket
import time
import httpx
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import uvicorn
import threading

# Experiment A: Connect Timeout on Unreachable IP (Blackhole) - Fixed Harness
async def exp_a_blackhole():
    print("\n========================================================")
    print("EXP A: Connect Timeout (Unreachable IP: 10.255.255.1) [Fixed Harness]")
    print("========================================================")
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=1.0, read=5.0, write=5.0, pool=5.0)) as client:
        start = time.time()
        try:
            await client.get("http://10.255.255.1")
            elapsed = time.time() - start
            return ("Exp A (Blackhole)", elapsed, "No Error")
        except Exception as e:
            elapsed = time.time() - start
            err_class = f"{type(e).__module__}.{type(e).__name__}"
            print(f"Time Taken (Inside Client) : {elapsed:.3f}s")
            print(f"Error Type                 : {err_class}")
            print(f"Error Msg                  : {e}")
            return ("Exp A (Blackhole IP)", elapsed, err_class)

# Experiment B: Connection Refused (Closed Port) - Fixed Harness
async def exp_b_refused():
    print("\n========================================================")
    print("EXP B: Connection Refused (Closed Port: 127.0.0.1:9999) [Fixed Harness]")
    print("========================================================")
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=1.0, read=5.0, write=5.0, pool=5.0)) as client:
        start = time.time()
        try:
            await client.get("http://127.0.0.1:9999")
            elapsed = time.time() - start
            return ("Exp B (Closed Port)", elapsed, "No Error")
        except Exception as e:
            elapsed = time.time() - start
            err_class = f"{type(e).__module__}.{type(e).__name__}"
            print(f"Time Taken (Inside Client) : {elapsed:.3f}s")
            print(f"Error Type                 : {err_class}")
            print(f"Error Msg                  : {e}")
            return ("Exp B (Closed Port)", elapsed, err_class)

# Experiment A3.2: Raw Socket Test to 127.0.0.1:9999
def exp_a3_raw_socket():
    print("\n========================================================")
    print("EXP A3.2: Plain Raw Socket Test (127.0.0.1:9999)")
    print("========================================================")
    start = time.time()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        s.connect(("127.0.0.1", 9999))
        s.close()
        elapsed = time.time() - start
        print(f"Raw Socket Time: {elapsed:.3f}s | Connected successfully")
    except Exception as e:
        elapsed = time.time() - start
        print(f"Raw Socket Time: {elapsed:.3f}s | Exact OS Error: {type(e).__name__}: {e}")

# Experiment A3.3: 10s Server Sleep vs Read Timeout 0.5s (Deferred Cancellation Check)
sleep_app = FastAPI()

@sleep_app.get("/sleep10")
async def sleep10():
    await asyncio.sleep(10.0)
    return {"status": "done"}

def run_sleep10_server():
    uvicorn.run(sleep_app, host="127.0.0.1", port=8002, log_level="warning")

async def exp_a3_sleep10_read_timeout():
    print("\n========================================================")
    print("EXP A3.3: Deferred Cancellation Check (10s Sleep Endpoint vs Read=0.5s)")
    print("========================================================")
    t = threading.Thread(target=run_sleep10_server, daemon=True)
    t.start()
    await asyncio.sleep(1.0) # Wait for server startup

    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=0.5, write=5.0, pool=5.0)) as client:
        start = time.time()
        try:
            await client.get("http://127.0.0.1:8002/sleep10")
            elapsed = time.time() - start
            print(f"Completed in {elapsed:.3f}s")
        except Exception as e:
            elapsed = time.time() - start
            err_class = f"{type(e).__module__}.{type(e).__name__}"
            print(f"Time Taken (Inside Client) : {elapsed:.3f}s")
            print(f"Error Type                 : {err_class}")
            print(f"Error Msg                  : {e}")
            if elapsed < 1.0:
                print("--> RESULT: ReadTimeout fired promptly (~0.5s). The previous 2.17s was harness/teardown overhead!")
            else:
                print(f"--> RESULT: ReadTimeout was deferred until ~{elapsed:.1f}s (deferred cancellation confirmed!).")

if __name__ == "__main__":
    print("--- DAY 4 RE-TESTS & HARNESS FIXES ---")
    res_a = asyncio.run(exp_a_blackhole())
    res_b = asyncio.run(exp_b_refused())
    exp_a3_raw_socket()
    asyncio.run(exp_a3_sleep10_read_timeout())