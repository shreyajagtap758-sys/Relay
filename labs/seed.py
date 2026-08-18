import asyncio
import pathlib
import sys

# Ensure repository root is on sys.path
repo_root = str(pathlib.Path(__file__).resolve().parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from sqlalchemy import text
from relay.db import async_session


async def seed_jobs(n: int = 20, job_type: str = "sleep") -> tuple[int, int]:
    async with async_session() as session:
        async with session.begin():
            stmt = text("""
                INSERT INTO jobs (type, payload)
                SELECT :job_type, '{}'::jsonb
                FROM generate_series(1, :n)
                RETURNING id;
            """)
            result = await session.execute(stmt, {"job_type": job_type, "n": n})
            ids = [row[0] for row in result.fetchall()]
            min_id = min(ids)
            max_id = max(ids)
            print(f"Seeded {len(ids)} jobs ({job_type}): IDs [{min_id}..{max_id}]")
            return min_id, max_id


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    asyncio.run(seed_jobs(count))