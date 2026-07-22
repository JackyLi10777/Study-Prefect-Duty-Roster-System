from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_handover_exposes_a_confirmation_gated_new_school_year_rollover() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "stewardship.py").read_text(
        encoding="utf-8"
    )

    assert "workflow.prepare_new_school_year" in source
    assert "data-testid=school-year-rollover" in source
    assert "data-testid=school-year-rollover-confirmation" in source
    assert "data-testid=confirm-school-year-rollover" in source
    assert "confirm_rollover.disable()" in source
    assert "confirm_rollover.enable()" in source
    assert "from nicegui_app.ui.navigation import navigate_to" in source
    assert 'navigate_to("/prefects")' in source


def test_handover_copy_explains_backup_history_and_new_directory_import() -> None:
    messages = (PROJECT_ROOT / "nicegui_app" / "ui" / "i18n_catalog" / "stewardship.py").read_text(
        encoding="utf-8"
    )

    for expected in (
        "操作前備份",
        "舊週表、公平帳本及審計紀錄會完整保留",
        "新學年名單",
        "pre-operation backup",
        "fairness ledger",
        "new school-year directory",
    ):
        assert expected in messages


def test_committed_rollover_backup_failure_has_a_locked_recovery_state() -> None:
    workflow_source = (
        PROJECT_ROOT / "nicegui_app" / "services" / "workflow_parts" / "people.py"
    ).read_text(encoding="utf-8")
    shared_ui = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_shared.py").read_text(encoding="utf-8")
    messages = (PROJECT_ROOT / "nicegui_app" / "ui" / "i18n_catalog" / "weekly.py").read_text(
        encoding="utf-8"
    )

    assert 'reason_code="school_year_rollover_post_backup_failed"' in workflow_source
    assert "recovery_required=get_workflow().maintenance_status().recovery_required" in shared_ui
    assert "partial-recovery-guide-action" in shared_ui
    assert "系統已鎖定等候復原核對" in messages
    assert "Do not repeat the action, reboot" in messages
