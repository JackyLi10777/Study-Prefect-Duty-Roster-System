"""Database initialization, Alembic migrations, and SQLite connection policy."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, event
from sqlalchemy.engine import URL, create_engine
from sqlalchemy.orm import Session, sessionmaker

from nicegui_app.config import PROJECT_ROOT, SQLITE_BUSY_TIMEOUT_MS
from nicegui_app.persistence.models import Base


def _alembic_config(database_path: Path | None = None) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    if database_path is not None:
        config.set_main_option("sqlalchemy.url", database_url(database_path))
    return config


@lru_cache(maxsize=1)
def current_migration_heads() -> frozenset[str]:
    """Return the checked-in Alembic heads used by readiness and restore."""
    return frozenset(ScriptDirectory.from_config(_alembic_config()).get_heads())


def required_database_tables() -> frozenset[str]:
    """Return the complete current schema contract without opening user data."""
    return frozenset({"alembic_version", *Base.metadata.tables.keys()})


def database_readiness(database_path: Path) -> str:
    """Verify SQLite bytes, full table contract, and the current Alembic head read-only."""
    if not database_path.is_file():
        return "missing"
    try:
        connection = sqlite3.connect(
            f"file:{database_path.resolve().as_posix()}?mode=ro",
            uri=True,
            timeout=SQLITE_BUSY_TIMEOUT_MS / 1_000,
        )
        try:
            integrity = connection.execute("PRAGMA quick_check").fetchone()
            if not integrity or integrity[0] != "ok":
                return "failed"
            tables = {
                str(row[0])
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
            }
            if required_database_tables() - tables:
                return "schema_incomplete"
            versions = {
                str(row[0])
                for row in connection.execute("SELECT version_num FROM alembic_version").fetchall()
            }
            if versions != current_migration_heads():
                return "migration_pending"
        finally:
            connection.close()
    except sqlite3.Error:
        return "unavailable"
    return "ok"


def database_url(database_path: Path) -> str:
    return str(URL.create("sqlite", database=str(database_path.resolve())))


def migrate_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    command.upgrade(_alembic_config(database_path), "head")


def create_sqlite_engine(database_path: Path) -> Engine:
    engine = create_engine(
        database_url(database_path),
        connect_args={
            "check_same_thread": False,
            "timeout": SQLITE_BUSY_TIMEOUT_MS / 1_000,
        },
        future=True,
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = connection.cursor()
        cursor.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    return engine


def create_session_factory(database_path: Path) -> sessionmaker[Session]:
    migrate_database(database_path)
    # WAL is a persistent database setting rather than a per-connection
    # option. Applying it before the pooled engine opens avoids two concurrent
    # checkouts contending on `PRAGMA journal_mode` during a write.
    connection = sqlite3.connect(database_path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1_000)
    try:
        connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
        journal_mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()
        if not journal_mode or str(journal_mode[0]).lower() != "wal":
            raise sqlite3.OperationalError("SQLite did not enable WAL journal mode")
    finally:
        connection.close()
    return sessionmaker(bind=create_sqlite_engine(database_path), expire_on_commit=False, future=True)
