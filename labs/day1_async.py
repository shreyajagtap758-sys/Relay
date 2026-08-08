from fastapi import FastAPI
import time
import asyncio

app = FastAPI()


from concurrent.futures import ThreadPoolExecutor
_thread_pool = ThreadPoolExecutor(max_workers=3)

def blocking_function():
    time.sleep(3)
    return "Done"

@app.get("/executor")
async def executor():
    loop = asyncio.get_running_loop()

    result = await loop.run_in_executor(
        _thread_pool,
        blocking_function
    )

    return result


@app.get("/blocking")
async def blocking():
    print("Blocking request started")
    time.sleep(6) # this makes the current thread sleep =
    print("Blocking request finished")
    return {"endpoint": "blocking"}


@app.get("/nonblocking")
async def nonblocking():
    print("Non-blocking request started")
    await asyncio.sleep(2)
    print("Non-blocking request finished")
    return {"endpoint": "nonblocking"}