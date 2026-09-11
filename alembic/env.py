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
# DATABASE URL (P-39 Repair: Precedence -c > env > alembic.ini)
# ---------------------------------------------------------

custom_ini = config.config_file_name and not os.path.basename(config.config_file_name).lower() == "alembic.ini"
ini_url = config.get_main_option("sqlalchemy.url")

if custom_ini and ini_url:
    DATABASE_URL = ini_url
    url_source = f"-c ({os.path.basename(config.config_file_name)})"
elif "DATABASE_URL" in os.environ:
    DATABASE_URL = os.environ["DATABASE_URL"]
    url_source = "env"
elif ini_url:
    DATABASE_URL = ini_url
    url_source = "alembic.ini"
else:
    raise RuntimeError("No database URL found in config or environment")

from urllib.parse import urlparse
parsed = urlparse(DATABASE_URL.replace("+asyncpg", "").replace("+psycopg", ""))
db_name = parsed.path.lstrip("/")
print(f"[alembic] resolved_db={db_name} source={url_source}", flush=True)


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