from logging.config import fileConfig
import os

from sqlalchemy import create_engine, pool
from alembic import context

from app.core.database import Base
from app.models import *  # ensure all models are imported

# Alembic Config object
config = context.config

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate
target_metadata = Base.metadata


# -------------------------
# Get DATABASE URL (IMPORTANT)
# -------------------------
def get_database_url():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("❌ DATABASE_URL not set")
    return url


# -------------------------
# OFFLINE MODE
# -------------------------
def run_migrations_offline() -> None:
    url = get_database_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# -------------------------
# ONLINE MODE
# -------------------------
def run_migrations_online() -> None:
    url = get_database_url()

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# -------------------------
# ENTRYPOINT
# -------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()