import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

POOL_SIZE = int(os.getenv("POOL_SIZE", "5"))
MAX_OVERFLOW = int(os.getenv("MAX_OVERFLOW", "10"))
POOL_TIMEOUT = float(os.getenv("POOL_TIMEOUT", "30.0"))
# D-31: pool_pre_ping stays False. Measured 0 benefit against outage (pre-ping runs at checkout, not mid-transaction),
# while protecting API p99 tail latency from a +3.3ms to +33.7ms per-checkout round-trip penalty.
POOL_PRE_PING = False
APP_NAME = os.getenv("APPLICATION_NAME", "relay")

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_pre_ping=POOL_PRE_PING,
    connect_args={"server_settings": {"application_name": APP_NAME}},
)
print(f"[db] resolved_db={engine.url.database} app={APP_NAME} pool={POOL_SIZE}+{MAX_OVERFLOW}", flush=True)

async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise