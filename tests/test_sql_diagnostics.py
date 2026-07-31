from __future__ import annotations

from sqlalchemy import text

from nicegui_app.persistence.database import create_sqlite_engine, migrate_database
from nicegui_app.persistence.sql_diagnostics import (
    capture_sql_diagnostics,
    statement_fingerprint,
)


def test_statement_fingerprint_is_stable_and_does_not_retain_payload() -> None:
    first = statement_fingerprint("SELECT * FROM prefects WHERE name_zh = ?")
    second = statement_fingerprint("  select  *  from prefects where name_zh = ?  ")

    assert first == second
    assert len(first) == 16
    assert "prefects" not in first
    assert "name_zh" not in first


def test_sql_diagnostic_capture_reports_aggregate_timing_without_parameters(tmp_path) -> None:
    database_path = tmp_path / "diagnostics.sqlite3"
    migrate_database(database_path)
    engine = create_sqlite_engine(database_path)
    try:
        with capture_sql_diagnostics() as snapshot:
            with engine.connect() as connection:
                assert connection.execute(text("SELECT :private_value"), {"private_value": "測試姓名"}).scalar_one() == "測試姓名"

        assert snapshot.statement_count == 1
        assert snapshot.total_db_ms >= 0
        assert snapshot.slowest_ms >= 0
        assert snapshot.slowest_fingerprint in snapshot.fingerprints
        assert all("測試姓名" not in fingerprint for fingerprint in snapshot.fingerprints)
    finally:
        engine.dispose()
