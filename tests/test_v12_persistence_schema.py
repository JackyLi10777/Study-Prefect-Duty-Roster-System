from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.persistence.database import create_session_factory, database_url
from nicegui_app.persistence.models import (
    AuditEventRecord,
    BackupObligationRecord,
    ExternalShareOutboxRecord,
    LeaveDeclarationRecord,
    OperationCommandRecord,
    PrefectRecord,
)


def _alembic_config(database_path: Path) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url(database_path))
    return config


def _insert_prefect(
    connection: sqlite3.Connection,
    prefect_id: str,
    name_zh: str,
    *,
    active: int = 1,
) -> None:
    connection.execute(
        """
        INSERT INTO prefects (
            id, name_zh, form, class_name, role_code,
            history_weight, history_duties, history_weight_anchor, history_duties_anchor,
            needs_mentoring, fixed_general_duty, remarks, version, active, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            prefect_id,
            name_zh,
            "F.5",
            "5A",
            "study_prefect",
            0.0,
            0,
            0.0,
            0,
            0,
            "NONE",
            "",
            1,
            active,
            "2026-09-01",
            "2026-09-01",
        ),
    )


def test_v12_models_publish_the_additive_persistence_contract() -> None:
    assert LeaveDeclarationRecord.__table__.c.version.server_default is not None
    assert {
        "actor_subject",
        "actor_mode",
        "command_id",
        "request_reference",
    }.issubset(AuditEventRecord.__table__.c.keys())
    assert {
        "operation_commands",
        "backup_obligations",
        "external_share_outbox",
    }.issubset(PrefectRecord.metadata.tables)
    assert set(OperationCommandRecord.__table__.c.keys()) == {
        "command_id",
        "operation_type",
        "request_fingerprint",
        "status",
        "result_json",
        "created_at",
        "completed_at",
    }
    assert {
        "command_id",
        "operation_type",
        "roster_week_id",
        "status",
        "backup_path",
        "error",
        "created_at",
        "completed_at",
    }.issubset(BackupObligationRecord.__table__.c.keys())
    assert {
        "command_id",
        "share_id",
        "roster_week_id",
        "roster_version",
        "content_digest",
        "status",
        "attempts",
        "error",
        "created_at",
        "updated_at",
        "delivered_at",
    }.issubset(ExternalShareOutboxRecord.__table__.c.keys())

    active_name_indexes = {
        index.name: index
        for index in PrefectRecord.__table__.indexes
    }
    assert active_name_indexes["uq_prefects_active_name_zh"].unique is True
    assert active_name_indexes["uq_prefects_active_name_zh"].dialect_options["sqlite"]["where"] is not None


def test_0007_to_head_preserves_data_and_adds_v12_contracts(tmp_path: Path) -> None:
    database_path = tmp_path / "pre-v12.sqlite3"
    config = _alembic_config(database_path)
    command.upgrade(config, "0007")
    with sqlite3.connect(database_path) as connection:
        _insert_prefect(connection, "prefect-existing", "遷移保留測試")
        connection.execute(
            """
            INSERT INTO leave_declarations (
                week_start, prefect_id, day, reason, active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2026-09-07",
                "prefect-existing",
                "MONDAY",
                "保留原因",
                1,
                "2026-09-01",
                "2026-09-01",
            ),
        )
        connection.execute(
            """
            INSERT INTO audit_events (
                event_type, roster_week_id, metadata_json, occurred_at
            ) VALUES (?, ?, ?, ?)
            """,
            ("legacy_event", None, "{}", "2026-09-01"),
        )
        connection.commit()

    command.upgrade(config, "head")

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0013",)
        assert connection.execute(
            "SELECT reason, version FROM leave_declarations WHERE prefect_id = ?",
            ("prefect-existing",),
        ).fetchone() == ("保留原因", 1)
        assert connection.execute(
            """
            SELECT actor_subject, actor_mode, command_id, request_reference
            FROM audit_events
            WHERE event_type = 'legacy_event'
            """
        ).fetchone() == (None, None, None, None)
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {
            "operation_commands",
            "backup_obligations",
            "external_share_outbox",
        }.issubset(tables)
        indexes = {
            row[1]
            for row in connection.execute("PRAGMA index_list(prefects)")
        }
        assert "uq_prefects_active_name_zh" in indexes
        roster_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(roster_weeks)")
        }
        assert {"withdrawn_at", "withdrawal_reason"}.issubset(roster_columns)
        roster_indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(roster_weeks)")
        }
        assert "uq_roster_weeks_active_week_start" in roster_indexes
        ledger_indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(fairness_ledger)")
        }
        assert "ix_fairness_ledger_prefect_id" in ledger_indexes
        assert "ix_fairness_ledger_roster_week_created_id" in ledger_indexes
        assert "ix_roster_weeks_status_week_start_id" in roster_indexes
        assert "uq_prefects_active_assist_fixed_weekday" in indexes
        assert {
            row[1] for row in connection.execute("PRAGMA index_list(leave_adjustments)")
        } >= {"ix_leave_adjustments_roster_week_created_id"}
        assert {
            row[1] for row in connection.execute("PRAGMA index_list(backup_runs)")
        } >= {"ix_backup_runs_created_id"}


def test_active_chinese_name_uniqueness_allows_archived_history(tmp_path: Path) -> None:
    database_path = tmp_path / "active-name.sqlite3"
    sessions = create_session_factory(database_path)
    now = datetime(2026, 9, 1)
    try:
        with sessions() as session:
            session.add(
                PrefectRecord(
                    id="prefect-active",
                    name_zh="同名測試",
                    form="F.5",
                    class_name="5A",
                    role_code="study_prefect",
                    active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.commit()

        with sessions() as session:
            session.add(
                PrefectRecord(
                    id="prefect-archived",
                    name_zh="同名測試",
                    form="F.4",
                    class_name="4A",
                    role_code="study_prefect",
                    active=False,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.commit()

        with sessions() as session:
            session.add(
                PrefectRecord(
                    id="prefect-conflict",
                    name_zh="同名測試",
                    form="F.3",
                    class_name="3A",
                    role_code="study_prefect",
                    active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
            with pytest.raises(IntegrityError, match="uq_prefects_active_name_zh|UNIQUE constraint failed"):
                session.commit()
    finally:
        sessions.kw["bind"].dispose()


def test_v12_receipts_obligations_and_outbox_enforce_replay_keys(tmp_path: Path) -> None:
    database_path = tmp_path / "receipt-contract.sqlite3"
    sessions = create_session_factory(database_path)
    inspector = inspect(sessions.kw["bind"])
    now = datetime(2026, 9, 1)
    try:
        assert {
            "operation_commands",
            "backup_obligations",
            "external_share_outbox",
        }.issubset(inspector.get_table_names())
        assert {column["name"] for column in inspector.get_columns("leave_declarations")} >= {
            "version"
        }

        with sessions() as session:
            command_record = OperationCommandRecord(
                command_id="command-001",
                operation_type="roster_publish",
                request_fingerprint="a" * 64,
                status="committed",
                result_json="{}",
                created_at=now,
                completed_at=now,
            )
            session.add(command_record)
            session.flush()
            session.add(
                BackupObligationRecord(
                    command_id=command_record.command_id,
                    operation_type="roster_publish",
                    status="pending",
                    created_at=now,
                )
            )
            session.commit()

        with sessions() as session:
            session.add(
                OperationCommandRecord(
                    command_id="command-001",
                    operation_type="roster_publish",
                    request_fingerprint="b" * 64,
                    status="committed",
                    result_json="{}",
                    created_at=now,
                    completed_at=now,
                )
            )
            with pytest.raises(IntegrityError, match="operation_commands.command_id|UNIQUE constraint failed"):
                session.commit()
    finally:
        sessions.kw["bind"].dispose()


def test_duplicate_active_names_block_v12_migration_without_data_loss(tmp_path: Path) -> None:
    database_path = tmp_path / "duplicate-active-name.sqlite3"
    config = _alembic_config(database_path)
    command.upgrade(config, "0007")
    with sqlite3.connect(database_path) as connection:
        _insert_prefect(connection, "duplicate-a", "衝突測試")
        _insert_prefect(connection, "duplicate-b", "衝突測試")
        connection.commit()

    with pytest.raises(RuntimeError, match="duplicate active names"):
        command.upgrade(config, "head")

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM prefects WHERE name_zh = ?",
            ("衝突測試",),
        ).fetchone() == (2,)
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0007",)


def test_duplicate_fixed_assistant_weekday_blocks_0012_without_data_changes(tmp_path: Path) -> None:
    database_path = tmp_path / "duplicate-assist-weekday.sqlite3"
    config = _alembic_config(database_path)
    command.upgrade(config, "0011")
    with sqlite3.connect(database_path) as connection:
        _insert_prefect(connection, "assistant-a", "助理首席甲")
        _insert_prefect(connection, "assistant-b", "助理首席乙")
        connection.execute(
            "UPDATE prefects SET role_code='assistant_head', fixed_general_duty='MONDAY' "
            "WHERE id IN ('assistant-a','assistant-b')"
        )
        connection.commit()

    with pytest.raises(RuntimeError, match="more than one active Assistant Head Study Prefect"):
        command.upgrade(config, "head")

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM prefects WHERE role_code='assistant_head' "
            "AND fixed_general_duty='MONDAY'"
        ).fetchone() == (2,)
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0011",)


def test_v12_migration_downgrades_cleanly_to_0007(tmp_path: Path) -> None:
    database_path = tmp_path / "v12-downgrade.sqlite3"
    config = _alembic_config(database_path)
    command.upgrade(config, "head")
    command.downgrade(config, "0007")

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0007",)
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {
            "operation_commands",
            "backup_obligations",
            "external_share_outbox",
        }.isdisjoint(tables)
        leave_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(leave_declarations)")
        }
        audit_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(audit_events)")
        }
        assert "version" not in leave_columns
        assert {
            "actor_subject",
            "actor_mode",
            "command_id",
            "request_reference",
        }.isdisjoint(audit_columns)
