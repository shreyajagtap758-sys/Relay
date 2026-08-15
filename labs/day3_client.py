import asyncio
import time

import httpx


URL = "http://127.0.0.1:8000"


async def send_request(client, request_id):
    start = time.perf_counter()

    response = await client.get(URL)

    elapsed = time.perf_counter() - start

    print(
        f"Request {request_id}: "
        f"status={response.status_code}, "
        f"time={elapsed:.2f}s"
    )


async def main():
    async with httpx.AsyncClient() as client:
        start = time.perf_counter()

        await asyncio.gather(
            *[
                send_request(client, i)
                for i in range(1, 11)
            ]
        )

        total = time.perf_counter() - start

        print(f"\nTotal time: {total:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())