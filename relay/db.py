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
POOL_PRE_PING = os.getenv("POOL_PRE_PING", "0") == "1"
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