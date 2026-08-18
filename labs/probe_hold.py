import asyncio
import pathlib
import sys

repo_root = str(pathlib.Path(__file__).resolve().parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from sqlalchemy import text
from relay.db import async_session


async def test_case(change_status: bool = True):
    async with async_session() as session:
        async with session.begin():
            res = await session.execute(
                text("INSERT INTO jobs (type, payload) SELECT 'sleep', '{}'::jsonb FROM generate_series(1, 2) RETURNING id;")
            )
            ids = [r[0] for r in res.fetchall()]
            print(f"[PROBE] Seeded Jobs: {ids}")

    print(f"[PROBE] Locking Job {ids[0]} with FOR UPDATE and holding 6 seconds...")
    async with async_session() as session:
        async with session.begin():
            await session.execute(
                text("SELECT id FROM jobs WHERE id=:id FOR UPDATE;"),
                {"id": ids[0]},
            )
            print(f"[PROBE] Lock acquired on Job {ids[0]}. Worker will block when polling! Holding 6s...")
            await asyncio.sleep(6.0)

            if change_status:
                print(f"[PROBE] Updating Job {ids[0]} to 'running' and committing...")
                await session.execute(
                    text("UPDATE jobs SET status='running' WHERE id=:id;"),
                    {"id": ids[0]},
                )
            else:
                print(f"[PROBE] Committing Job {ids[0]} WITHOUT changing status (remains 'pending')...")

    print(f"[PROBE] Lock released for Job {ids[0]}!")


if __name__ == "__main__":
    change = True
    if len(sys.argv) > 1 and sys.argv[1].lower() == "nochange":
        change = False
    asyncio.run(test_case(change_status=change))