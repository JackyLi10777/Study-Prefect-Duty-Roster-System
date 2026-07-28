from __future__ import annotations

from datetime import date, datetime
import sqlite3

import pytest
from sqlalchemy import select

from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.persistence.models import BackupObligationRecord, OperationCommandRecord
from nicegui_app.services.roster_workflow import (
    BackupResult,
    CommittedWriteBackupError,
    RosterWorkflow,
    WorkflowMaintenanceError,
)


WEEK_START = date(2026, 9, 7)


def test_startup_repairs_a_committed_write_whose_backup_was_interrupted(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "sing-yin.sqlite3"
    backup_dir = tmp_path / "backups"
    first = RosterWorkflow(
        database_path=database_path,
        backup_dir=backup_dir,
        seed_path=PREFECT_SEED_PATH,
    )
    first.bootstrap()
    original = first._create_and_record_backup

    def fail_once(event_type: str, roster_week_id: int | None) -> BackupResult:
        monkeypatch.setattr(first, "_create_and_record_backup", original)
        return BackupResult(False, None, "simulated crash window")

    monkeypatch.setattr(first, "_create_and_record_backup", fail_once)

    with pytest.raises(CommittedWriteBackupError, match="draft_generated"):
        first.generate_and_save_draft(
            WEEK_START,
            expected_week_version=0,
            command_id="crash-window-draft",
        )

    assert first.pending_backup_obligation_count() == 1

    restarted = RosterWorkflow(
        database_path=database_path,
        backup_dir=backup_dir,
    )
    restarted.bootstrap()

    assert restarted.backup_repair_error is None
    assert restarted.pending_backup_obligation_count() == 0
    assert restarted.roster_weeks()[0]["version"] == 1
    assert restarted.backup_status()["latestVerification"]["valid"] is True


def test_failed_startup_repair_keeps_diagnostics_available_and_blocks_later_writes(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "sing-yin.sqlite3"
    backup_dir = tmp_path / "backups"
    first = RosterWorkflow(
        database_path=database_path,
        backup_dir=backup_dir,
        seed_path=PREFECT_SEED_PATH,
    )
    first.bootstrap()
    monkeypatch.setattr(
        first,
        "_create_and_record_backup",
        lambda *_args, **_kwargs: BackupResult(False, None, "simulated crash window"),
    )
    with pytest.raises(CommittedWriteBackupError):
        first.generate_and_save_draft(
            WEEK_START,
            expected_week_version=0,
            command_id="unrepaired-draft",
        )

    restarted = RosterWorkflow(
        database_path=database_path,
        backup_dir=backup_dir,
    )
    monkeypatch.setattr(
        restarted,
        "_create_and_record_backup",
        lambda *_args, **_kwargs: BackupResult(False, None, "backup device unavailable"),
    )
    restarted.bootstrap()

    assert restarted.backup_repair_error == "CommittedWriteBackupError"
    assert restarted.pending_backup_obligation_count() == 1
    assert restarted.roster_weeks()[0]["version"] == 1
    with pytest.raises(WorkflowMaintenanceError, match="read-only"):
        restarted.generate_and_save_draft(
            WEEK_START,
            expected_week_version=1,
            command_id="blocked-while-unrepaired",
        )


def test_backup_repair_attempts_later_obligations_before_raising_first_failure(
    tmp_path,
    monkeypatch,
) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    now = datetime.now()
    command_ids = ("first-repair-fails", "second-repair-can-run")
    with workflow._session() as session:
        for command_id in command_ids:
            session.add(
                OperationCommandRecord(
                    command_id=command_id,
                    operation_type="audit_probe",
                    request_fingerprint="0" * 64,
                    status="committed",
                    result_json="{}",
                    created_at=now,
                    completed_at=now,
                )
            )
        session.flush()
        for command_id in command_ids:
            session.add(
                BackupObligationRecord(
                    command_id=command_id,
                    operation_type="audit_probe",
                    roster_week_id=None,
                    status="pending",
                    created_at=now,
                )
            )
        session.commit()

    calls: list[str] = []
    fulfill_backup_obligation = workflow._fulfill_backup_obligation

    def fulfill(command_id: str):
        calls.append(command_id)
        if command_id == command_ids[0]:
            raise CommittedWriteBackupError("audit_probe", "record-specific failure")
        return fulfill_backup_obligation(command_id)

    monkeypatch.setattr(workflow, "_fulfill_backup_obligation", fulfill)

    with pytest.raises(CommittedWriteBackupError, match="audit_probe"):
        workflow.repair_pending_backup_obligations()

    assert calls == list(command_ids)
    with workflow._session() as session:
        statuses = {
            record.command_id: record.status
            for record in session.scalars(
                select(BackupObligationRecord).where(
                    BackupObligationRecord.command_id.in_(command_ids)
                )
            ).all()
        }
    assert statuses == {
        command_ids[0]: "pending",
        command_ids[1]: "completed",
    }
    assert workflow.pending_backup_obligation_count() == 1


def test_manual_verified_backup_repairs_pending_obligations_and_allows_the_next_write(
    tmp_path,
    monkeypatch,
) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    original = workflow._create_and_record_backup

    def fail_once(event_type: str, roster_week_id: int | None) -> BackupResult:
        monkeypatch.setattr(workflow, "_create_and_record_backup", original)
        return BackupResult(False, None, "simulated backup interruption")

    monkeypatch.setattr(workflow, "_create_and_record_backup", fail_once)
    with pytest.raises(CommittedWriteBackupError, match="draft_generated"):
        workflow.generate_and_save_draft(
            WEEK_START,
            expected_week_version=0,
            command_id="manual-repair-source",
        )

    assert workflow.pending_backup_obligation_count() == 1

    recovery_snapshot = workflow.create_verified_backup()

    assert workflow.pending_backup_obligation_count() == 0
    assert workflow.verify_backup(recovery_snapshot)["valid"] is True
    with sqlite3.connect(recovery_snapshot) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM backup_obligations WHERE status <> 'completed'"
        ).fetchone() == (0,)

    next_draft = workflow.generate_and_save_draft(
        date(2026, 9, 14),
        expected_week_version=0,
        command_id="write-after-manual-repair",
    )
    assert next_draft.version == 1
    assert workflow.pending_backup_obligation_count() == 0
