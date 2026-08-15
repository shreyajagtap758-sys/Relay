from logging.config import fileConfig
import os
import asyncio

from dotenv import load_dotenv

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from relay.models import Base


# ---------------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# ---------------------------------------------------------

load_dotenv()


# ---------------------------------------------------------
# ALEMBIC CONFIG
# ---------------------------------------------------------

config = context.config


# Configure Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Alembic uses this to detect model changes
target_metadata = Base.metadata


# ---------------------------------------------------------
# DATABASE URL
# ---------------------------------------------------------

DATABASE_URL = os.environ["DATABASE_URL"]


# ---------------------------------------------------------
# OFFLINE MIGRATIONS
# ---------------------------------------------------------

def run_migrations_offline() -> None:
    """
    Run migrations without creating a database connection.
    """

    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------
# ACTUAL MIGRATION LOGIC
# ---------------------------------------------------------

def do_run_migrations(connection) -> None:
    """
    Run migrations using an active database connection.

    This function itself is synchronous because Alembic's
    migration operations are synchronous.
    """

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------
# ONLINE ASYNC MIGRATIONS
# ---------------------------------------------------------

async def run_migrations_online() -> None:
    """
    Run migrations using SQLAlchemy's async engine.
    """

    connectable = async_engine_from_config(
        {
            "sqlalchemy.url": DATABASE_URL
        },
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:

        await connection.run_sync(
            do_run_migrations
        )

    await connectable.dispose()


# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(
        run_migrations_online()
    )