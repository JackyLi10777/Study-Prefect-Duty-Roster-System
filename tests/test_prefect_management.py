from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
import sqlite3
from threading import Barrier

import pytest

from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.services.maintenance import MaintenanceModeError
from nicegui_app.services.roster_workflow import (
    BackupResult,
    CommittedWriteBackupError,
    PrefectInput,
    RosterWorkflow,
    WorkflowConflictError,
    WorkflowError,
    WorkflowMaintenanceError,
)
from nicegui_app.utils.prefect_import import parse_prefect_import_text, prefect_import_template_csv


def _workflow(tmp_path) -> RosterWorkflow:
    workflow = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    return workflow


def test_prefect_can_be_created_updated_and_archived_without_erasing_history(tmp_path) -> None:
    workflow = _workflow(tmp_path)
    created = workflow.create_prefect(
        PrefectInput(
            name_zh="許朗然",
            form="F.4",
            class_name="4H",
            role_code="study_prefect",
            available_days=("MONDAY", "WEDNESDAY", "FRIDAY"),
            needs_mentoring=False,
            remarks="Test record",
        )
    )

    updated = workflow.update_prefect(
        created["id"],
        PrefectInput(
            name_zh="許朗然",
            form="F.4",
            class_name="4H",
            role_code="study_prefect",
            available_days=("TUESDAY", "THURSDAY"),
            needs_mentoring=True,
            remarks="Updated availability",
        ),
    )
    workflow.archive_prefect(created["id"])

    assert updated["availableDays"] == ["TUESDAY", "THURSDAY"]
    assert updated["needsMentoring"] is True
    assert created["id"] not in {item["id"] for item in workflow.prefects()}
    assert len(list((tmp_path / "backups").glob("*.sqlite3"))) == 3


def test_new_school_year_rollover_clears_active_directory_and_retains_audited_history(tmp_path) -> None:
    workflow = _workflow(tmp_path)
    original = workflow.prefects()[0]
    workflow.declare_leave(
        week_start=date(2026, 7, 20),
        prefect_id=str(original["id"]),
        day="MONDAY",
        reason="Fictional rollover test",
    )

    receipt = workflow.prepare_new_school_year()

    assert receipt["archivedPrefectCount"] == 24
    assert receipt["cancelledLeaveCount"] == 1
    assert workflow.prefects() == []
    assert workflow.prefect(str(original["id"]))["active"] is False
    assert workflow.verify_backup(receipt["beforeBackup"])["valid"] is True
    assert workflow.verify_backup(receipt["afterBackup"])["valid"] is True

    replacement = workflow.create_prefect(
        PrefectInput(
            name_zh=str(original["nameZh"]),
            form="F.5",
            class_name="5A",
            role_code="study_prefect",
            available_days=("MONDAY", "WEDNESDAY"),
        )
    )
    assert replacement["id"] != original["id"]
    assert workflow.prefect(str(original["id"]))["active"] is False

    with sqlite3.connect(tmp_path / "sing-yin.sqlite3") as connection:
        audit_count = connection.execute(
            "SELECT COUNT(*) FROM audit_events WHERE event_type = 'school_year_directory_archived'"
        ).fetchone()[0]
        active_leave_count = connection.execute(
            "SELECT COUNT(*) FROM leave_declarations WHERE active = 1"
        ).fetchone()[0]
    assert audit_count == 1
    assert active_leave_count == 0


def test_new_school_year_rollover_refuses_an_already_empty_directory_without_new_backup(tmp_path) -> None:
    workflow = _workflow(tmp_path)
    workflow.prepare_new_school_year()
    backup_count = len(list((tmp_path / "backups").glob("*.sqlite3")))

    with pytest.raises(WorkflowError, match="already empty"):
        workflow.prepare_new_school_year()

    assert len(list((tmp_path / "backups").glob("*.sqlite3"))) == backup_count


def test_new_school_year_rollover_has_one_winner_across_concurrent_clients(tmp_path) -> None:
    first = _workflow(tmp_path)
    second = _workflow(tmp_path)
    barrier = Barrier(2)

    def rollover(workflow: RosterWorkflow) -> tuple[str, object]:
        barrier.wait(timeout=5)
        try:
            return "completed", workflow.prepare_new_school_year()
        except (MaintenanceModeError, WorkflowError) as error:
            return "refused", error

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(rollover, (first, second)))

    assert [status for status, _ in outcomes].count("completed") == 1
    assert [status for status, _ in outcomes].count("refused") == 1
    assert first.prefects() == []
    with sqlite3.connect(tmp_path / "sing-yin.sqlite3") as connection:
        audit_count = connection.execute(
            "SELECT COUNT(*) FROM audit_events WHERE event_type = 'school_year_directory_archived'"
        ).fetchone()[0]
        active_count = connection.execute("SELECT COUNT(*) FROM prefects WHERE active = 1").fetchone()[0]
    assert audit_count == 1
    assert active_count == 0
    backups = list((tmp_path / "backups").glob("*.sqlite3"))
    assert len(backups) == 2
    assert all(first.verify_backup(path)["valid"] is True for path in backups)
    assert not (tmp_path / ".sing-yin.sqlite3.maintenance.json").exists()


def test_new_school_year_rollover_does_not_archive_when_pre_operation_backup_fails(monkeypatch, tmp_path) -> None:
    workflow = _workflow(tmp_path)

    monkeypatch.setattr(
        workflow,
        "_create_and_record_backup",
        lambda *_args, **_kwargs: BackupResult(False, None, "simulated pre-backup failure"),
    )

    with pytest.raises(WorkflowError, match="did not start"):
        workflow.prepare_new_school_year()

    assert len(workflow.prefects()) == 24
    assert workflow.maintenance_status().active is False


def test_new_school_year_rollover_preserves_recovery_lock_when_post_backup_fails(monkeypatch, tmp_path) -> None:
    workflow = _workflow(tmp_path)
    create_backup = workflow._create_and_record_backup
    calls = 0

    def fail_second_backup(event_type: str, roster_week_id: int | None) -> BackupResult:
        nonlocal calls
        calls += 1
        if calls == 2:
            return BackupResult(False, None, "simulated post-backup failure")
        return create_backup(event_type, roster_week_id)

    monkeypatch.setattr(workflow, "_create_and_record_backup", fail_second_backup)

    with pytest.raises(CommittedWriteBackupError) as captured:
        workflow.prepare_new_school_year()

    assert captured.value.event_type == "school_year_directory_archived"
    status = workflow.maintenance_status()
    assert status.active is True
    assert status.recovery_required is True
    assert "school_year_rollover_post_backup_failed" in workflow.maintenance.marker_path.read_text(encoding="utf-8")
    with sqlite3.connect(tmp_path / "sing-yin.sqlite3") as connection:
        active_count = connection.execute("SELECT COUNT(*) FROM prefects WHERE active = 1").fetchone()[0]
    assert active_count == 0
    assert len(list((tmp_path / "backups").glob("*.sqlite3"))) == 1
    with pytest.raises(WorkflowMaintenanceError, match="maintenance mode"):
        workflow.create_prefect(
            PrefectInput(
                name_zh="測試風紀",
                form="F.5",
                class_name="5A",
                role_code="study_prefect",
                available_days=("MONDAY",),
            )
        )


def test_stale_prefect_editor_cannot_overwrite_a_newer_saved_version(tmp_path) -> None:
    workflow = _workflow(tmp_path)
    original = workflow.prefect(str(workflow.prefects()[0]["id"]))
    first_edit = PrefectInput(
        name_zh=str(original["nameZh"]),
        name_en=original["nameEn"],
        form=str(original["form"]),
        class_name=str(original["className"]),
        role_code=str(original["roleCode"]),
        available_days=tuple(original["availableDays"]),
        needs_mentoring=bool(original["needsMentoring"]),
        remarks="First browser saved this note",
    )
    stale_edit = PrefectInput(
        **{**first_edit.__dict__, "remarks": "Stale browser tried to overwrite it"}
    )

    saved = workflow.update_prefect(
        str(original["id"]),
        first_edit,
        expected_version=int(original["version"]),
    )

    with pytest.raises(WorkflowConflictError, match="another browser"):
        workflow.update_prefect(
            str(original["id"]),
            stale_edit,
            expected_version=int(original["version"]),
        )

    current = workflow.prefect(str(original["id"]))
    assert saved["version"] == int(original["version"]) + 1
    assert current["remarks"] == "First browser saved this note"


def test_stale_prefect_archive_cannot_hide_a_newer_saved_version(tmp_path) -> None:
    workflow = _workflow(tmp_path)
    original = workflow.prefect(str(workflow.prefects()[0]["id"]))
    edited = workflow.update_prefect(
        str(original["id"]),
        PrefectInput(
            name_zh=str(original["nameZh"]),
            name_en=original["nameEn"],
            form=str(original["form"]),
            class_name=str(original["className"]),
            role_code=str(original["roleCode"]),
            available_days=tuple(original["availableDays"]),
            needs_mentoring=bool(original["needsMentoring"]),
            remarks="Latest reviewed record",
        ),
        expected_version=int(original["version"]),
    )

    with pytest.raises(WorkflowConflictError, match="another browser"):
        workflow.archive_prefect(
            str(original["id"]),
            expected_version=int(original["version"]),
        )

    current = workflow.prefect(str(original["id"]))
    assert current["active"] is True
    assert current["version"] == edited["version"]
    workflow.archive_prefect(str(original["id"]), expected_version=int(edited["version"]))
    assert workflow.prefect(str(original["id"]))["active"] is False


def test_concurrent_duplicate_chinese_name_creation_has_one_winner(tmp_path) -> None:
    database_path = tmp_path / "sing-yin.sqlite3"
    backup_dir = tmp_path / "backups"
    first = RosterWorkflow(database_path=database_path, backup_dir=backup_dir)
    second = RosterWorkflow(database_path=database_path, backup_dir=backup_dir)
    first.bootstrap()
    second.bootstrap()
    barrier = Barrier(2)
    prefect_input = PrefectInput(
        name_zh="測試風紀甲",
        form="F.4",
        class_name="4H",
        role_code="study_prefect",
        available_days=("MONDAY", "WEDNESDAY"),
    )

    def create(service: RosterWorkflow):
        barrier.wait(timeout=5)
        try:
            return service.create_prefect(prefect_input)
        except WorkflowError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(create, (first, second)))

    assert len([item for item in outcomes if isinstance(item, dict)]) == 1
    errors = [item for item in outcomes if isinstance(item, WorkflowError)]
    assert len(errors) == 1
    assert "Chinese name already exists" in str(errors[0])
    assert [item["nameZh"] for item in first.prefects()].count("測試風紀甲") == 1


def test_ai_import_preview_normalizes_traditional_chinese_csv_before_persistence(tmp_path) -> None:
    preview = parse_prefect_import_text(
        "姓名,級別,班別,職務,可值班日\n"
        "梁子軒,F.3,3H,導學風紀,星期一、星期三、星期五\n"
        "范皓朗,F.5,5F,助理首席導學風紀,星期二、星期四\n"
    )
    workflow = _workflow(tmp_path)
    imported = workflow.import_prefects(preview.rows)

    assert preview.issues == ()
    assert {item["nameZh"] for item in imported} == {"梁子軒", "范皓朗"}
    assert {item["roleCode"] for item in imported} == {"study_prefect", "assistant_head"}


def test_downloadable_import_template_contains_only_fictional_rows_that_pass_preview_validation() -> None:
    template = prefect_import_template_csv().decode("utf-8-sig")
    preview = parse_prefect_import_text(template)

    assert "姓名,級別,班別,職務,可值班日,備註" in template
    assert preview.issues == ()
    assert [row.name_zh for row in preview.rows] == ["範例風紀甲", "範例風紀乙"]


def test_english_only_name_is_rejected_by_preview_and_workflow_boundary(tmp_path) -> None:
    preview = parse_prefect_import_text(
        "姓名,級別,班別,職務,可值班日\nTest Prefect,F.3,3H,導學風紀,星期一\n"
    )
    assert preview.rows == ()
    assert "display name must be Chinese" in preview.issues[0]

    workflow = _workflow(tmp_path)
    with pytest.raises(WorkflowError, match="display name must be Chinese"):
        workflow.create_prefect(
            PrefectInput(
                name_zh="Test Prefect",
                form="F.3",
                class_name="3H",
                role_code="study_prefect",
                available_days=("MONDAY",),
            )
        )
