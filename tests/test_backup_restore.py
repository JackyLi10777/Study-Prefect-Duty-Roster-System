from __future__ import annotations

from datetime import date

from nicegui_app.services.roster_workflow import PrefectInput, RosterWorkflow


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
