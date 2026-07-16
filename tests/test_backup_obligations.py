from __future__ import annotations

from datetime import date

import pytest

from nicegui_app.config import PREFECT_SEED_PATH
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
