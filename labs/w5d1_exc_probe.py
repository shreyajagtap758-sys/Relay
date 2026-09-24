import asyncio
import os
import sys
import traceback
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DB_URL = "postgresql+asyncpg://postgres:relay@localhost:5433/relay_w5d1"

async def probe_stale_vs_refused():
    print("=== Step 2 Exception Probe: Investigating Exception Classes & MRO ===")
    
    # 1. Fresh connection refusal test (point to non-existent port or down DB)
    bad_url = "postgresql+asyncpg://postgres:relay@localhost:5439/relay_w5d1"
    engine_bad = create_async_engine(bad_url)
    try:
        async with engine_bad.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        print("\n[Scenario B: Connection Refused (DB down on fresh connect)]")
        print(f"Exception Class: {type(e).__module__}.{type(e).__name__}")
        print("MRO (Method Resolution Order):")
        for cls in type(e).__mro__:
            print(f"  - {cls.__module__}.{cls.__name__}")
        print(f"Underlying cause: {type(e.__cause__).__name__ if e.__cause__ else 'None'}")
        if e.__cause__:
            for cls in type(e.__cause__).__mro__:
                print(f"    cause MRO: {cls.__module__}.{cls.__name__}")
    finally:
        await engine_bad.dispose()

    # 2. Inspect the InterfaceError from Step 1
    from sqlalchemy.exc import InterfaceError, OperationalError, DBAPIError
    print("\n[SQLAlchemy Hierarchy Check]")
    print(f"issubclass(InterfaceError, DBAPIError): {issubclass(InterfaceError, DBAPIError)}")
    print(f"issubclass(OperationalError, DBAPIError): {issubclass(OperationalError, DBAPIError)}")
    print(f"issubclass(DBAPIError, Exception): {issubclass(DBAPIError, Exception)}")
    print(f"issubclass(Exception, BaseException): {issubclass(Exception, BaseException)}")

if __name__ == "__main__":
    asyncio.run(probe_stale_vs_refused())
