from __future__ import annotations

from datetime import date
import hashlib
import json
import sqlite3

import pytest

from nicegui_app.services.roster_workflow import PrefectInput, RosterWorkflow, WorkflowError


WEEK_START = date(2026, 9, 7)


def test_restore_reverts_to_a_verified_snapshot_and_preserves_a_pre_restore_snapshot(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(WEEK_START)

    workflow.create_prefect(
        PrefectInput(
            name_zh="陳樂行",
            name_en="Chan Lok Hang",
            form="F.4",
            class_name="4B",
            role_code="study_prefect",
            available_days=("MONDAY", "WEDNESDAY", "FRIDAY"),
        )
    )
    assert any(prefect["nameZh"] == "陳樂行" for prefect in workflow.prefects())

    result = workflow.restore_backup(draft.backup_path)

    assert result["restoredFrom"] == draft.backup_path
    assert result["preRestoreBackup"].exists()
    assert workflow.verify_backup(result["preRestoreBackup"])["valid"] is True
    assert workflow.roster_week(draft.id)["status"] == "draft"
    assert not any(prefect["nameZh"] == "陳樂行" for prefect in workflow.prefects())


def test_restore_rejects_a_checksum_valid_but_unreconciled_candidate_before_swap(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(WEEK_START)
    live_before = workflow.prefect_loads()

    with sqlite3.connect(draft.backup_path) as connection:
        connection.execute(
            "UPDATE prefects SET history_weight = history_weight + 10 "
            "WHERE id = (SELECT id FROM prefects LIMIT 1)"
        )
        connection.commit()
    _refresh_manifest_checksum(draft.backup_path)
    assert workflow.verify_backup(draft.backup_path)["valid"] is True

    with pytest.raises(WorkflowError, match="Fairness"):
        workflow.restore_backup(draft.backup_path)

    assert workflow.prefect_loads() == live_before
    assert workflow.maintenance_status().active is False


def test_restore_rejects_a_checksum_valid_snapshot_missing_a_core_table_before_swap(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    workflow.bootstrap()
    snapshot = workflow.create_verified_backup()
    live_draft = workflow.generate_and_save_draft(WEEK_START)

    with sqlite3.connect(snapshot) as connection:
        connection.execute("DROP TABLE leave_declarations")
        connection.commit()
    _refresh_manifest_checksum(snapshot)

    verification = workflow.verify_backup(snapshot)
    assert verification["valid"] is False
    assert verification["reasonCode"] == "schema_incomplete"
    assert "leave_declarations" in str(verification["error"])

    with pytest.raises(WorkflowError, match="Backup verification failed"):
        workflow.restore_backup(snapshot)

    assert workflow.roster_week(live_draft.id)["status"] == "draft"
    assert workflow.pre_generation_leaves(WEEK_START) == []
    assert workflow.maintenance_status().active is False


def test_failed_post_swap_validation_rolls_back_to_the_original_database(tmp_path, monkeypatch) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(WEEK_START)
    created = workflow.create_prefect(
        PrefectInput(
            name_zh="測試風紀",
            form="F.4",
            class_name="4B",
            role_code="study_prefect",
            available_days=("MONDAY", "WEDNESDAY", "FRIDAY"),
        )
    )
    audit = workflow._audit

    def fail_restored_audit(session, event_type, roster_week_id, payload):
        if event_type == "backup_restored":
            raise RuntimeError("forced post-swap failure")
        return audit(session, event_type, roster_week_id, payload)

    monkeypatch.setattr(workflow, "_audit", fail_restored_audit)

    with pytest.raises(WorkflowError, match="original database was restored automatically"):
        workflow.restore_backup(draft.backup_path)

    assert workflow.prefect(str(created["id"]))["nameZh"] == "測試風紀"
    assert workflow.maintenance_status().active is False


def _refresh_manifest_checksum(backup_path) -> None:
    manifest_path = backup_path.with_suffix(".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sha256"] = hashlib.sha256(backup_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
