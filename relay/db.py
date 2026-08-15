"""
Database configuration — single source of truth for DB URL and engine setup.

URL format: postgresql+asyncpg://user:password@host:port/dbname
Port is 5433 because docker-compose maps host 5433 → container 5432.
"""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:relay@localhost:5433/relay"

engine = create_async_engine(DATABASE_URL, echo=True)

async_session = async_sessionmaker(engine, expire_on_commit=False)