from __future__ import annotations

from pathlib import Path

from nicegui_app.config import SQLITE_BUSY_TIMEOUT_MS
from nicegui_app.persistence.database import create_sqlite_engine


def test_sqlite_engine_applies_the_configured_busy_timeout(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "configured.sqlite3")
    try:
        with engine.connect() as connection:
            configured_timeout = connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one()
        assert configured_timeout == SQLITE_BUSY_TIMEOUT_MS
        assert engine.url.get_backend_name() == "sqlite"
    finally:
        engine.dispose()
