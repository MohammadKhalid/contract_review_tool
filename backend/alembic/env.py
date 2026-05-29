from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# -----------------------------------------------------------------------------
# Wire Alembic to the application's SQLAlchemy models and DATABASE_URL.
# This enables `alembic revision --autogenerate` and `alembic upgrade head`.
# -----------------------------------------------------------------------------

# Use the same DATABASE_URL that the FastAPI app uses (from Pydantic Settings).
# This ensures consistency between the app and migrations, especially inside Docker
# where the DB host is "db" rather than "localhost".
try:
    from core.config import settings

    if settings.DATABASE_URL:
        config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
except Exception:
    # Graceful fallback when running Alembic outside the normal app context
    # (e.g. certain CI jobs or manual invocation from the host with env vars set directly).
    pass

# Import the declarative Base and all model modules.
# Importing the models registers every table on Base.metadata so autogenerate works.
from database.connection import Base

# These imports are required for Alembic autogenerate to "see" the tables.
# Do not remove even if the linter complains about "unused import".
import models.contract  # noqa: F401
import models.legal_kb  # noqa: F401

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

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
