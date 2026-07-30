"""Alembic environment for the local Sing Yin SQLite database."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

from nicegui_app.persistence.models import Base


config = context.config
if config.config_file_name is not None:
    # Alembic's default disables every logger that is not named in alembic.ini.
    # The application configures its privacy-safe rotating logger before running
    # migrations, so disabling existing loggers here would silently remove all
    # subsequent operator and request diagnostics.
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def _validated_database_url() -> str:
    """Reject cwd-relative SQLite targets before Alembic opens a database."""

    raw_url = config.get_main_option("sqlalchemy.url")
    parsed = make_url(raw_url)
    if parsed.drivername.startswith("sqlite") and parsed.database not in {None, "", ":memory:"}:
        from pathlib import Path

        if not Path(parsed.database).is_absolute():
            raise RuntimeError(
                "Alembic requires an absolute SQLite URL. "
                "Use the application migration command or set sqlalchemy.url explicitly."
            )
    return raw_url


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=_validated_database_url(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    _validated_database_url()
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
