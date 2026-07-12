"""Database initialization, Alembic migrations, and SQLite connection policy."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, event
from sqlalchemy.engine import URL, create_engine
from sqlalchemy.orm import Session, sessionmaker

from nicegui_app.config import PROJECT_ROOT


def database_url(database_path: Path) -> str:
    return str(URL.create("sqlite", database=str(database_path.resolve())))


def migrate_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url(database_path))
    command.upgrade(config, "head")


def create_sqlite_engine(database_path: Path) -> Engine:
    engine = create_engine(
        database_url(database_path),
        connect_args={"check_same_thread": False, "timeout": 10},
        future=True,
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA busy_timeout = 10000")
        cursor.close()

    return engine


def create_session_factory(database_path: Path) -> sessionmaker[Session]:
    migrate_database(database_path)
    return sessionmaker(bind=create_sqlite_engine(database_path), expire_on_commit=False, future=True)
