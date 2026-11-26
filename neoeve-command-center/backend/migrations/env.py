"""Alembic environment configuration."""

from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config, pool
from alembic import context

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.models import Base

config = context.config

# Interpret config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# NOTE: Database URL is determined in run_migrations_online() with priority:
# 1. TEST_DATABASE_URL environment variable
# 2. DATABASE_URL environment variable
# 3. sqlalchemy.url from alembic.ini (respects alembic_etapa_a.ini for ETAPA A)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    import sys
    print("[ALEMBIC_DEBUG] run_migrations_online() START", file=sys.stderr)

    configuration = config.get_section(config.config_ini_section)

    # Debug: show config state
    ini_url = config.get_main_option("sqlalchemy.url")
    print(f"[ALEMBIC_DEBUG] config.config_file_name: {config.config_file_name}", file=sys.stderr)
    print(f"[ALEMBIC_DEBUG] INI sqlalchemy.url: {ini_url}", file=sys.stderr)
    print(f"[ALEMBIC_DEBUG] ENV TEST_DATABASE_URL: {os.getenv('TEST_DATABASE_URL')}", file=sys.stderr)
    print(f"[ALEMBIC_DEBUG] ENV DATABASE_URL: {os.getenv('DATABASE_URL')}", file=sys.stderr)

    # Priority: TEST_DATABASE_URL env > DATABASE_URL env > alembic.ini url
    # This ensures alembic_etapa_a.ini's sqlalchemy.url is respected when no env vars are set
    db_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")

    if not db_url:
        # Fall back to what's configured in alembic.ini (critical for alembic_etapa_a.ini)
        db_url = ini_url
        print(f"[ALEMBIC_DEBUG] No env vars, using INI url: {db_url}", file=sys.stderr)
    else:
        print(f"[ALEMBIC_DEBUG] Using env var: {db_url}", file=sys.stderr)

    configuration["sqlalchemy.url"] = db_url
    print(f"[ALEMBIC_DEBUG] FINAL DATABASE_URL: {db_url}", file=sys.stderr)

    print("[ALEMBIC_DEBUG] Creating engine...", file=sys.stderr)
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    print("[ALEMBIC_DEBUG] Engine created, connecting...", file=sys.stderr)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
