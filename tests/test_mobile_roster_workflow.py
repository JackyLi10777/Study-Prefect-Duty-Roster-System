from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from nicegui_app.access_context import AccessMode, PageContext, Principal
from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.services.guest_adapter import GuestWorkspaceAdapter
from nicegui_app.services.guest_workspace import GuestWorkspaceRegistry
from nicegui_app.services.roster_workflow import RosterWorkflow


WEEK_START = date(2026, 9, 7)
OTHER_WEEK = date(2026, 9, 14)
ROOT = Path(__file__).resolve().parents[1]
WEEKLY_SOURCE = (ROOT / "nicegui_app" / "ui" / "page_routes" / "weekly.py").read_text(
    encoding="utf-8"
)
MOBILE_CSS = (
    ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-roster-mobile-v1.css"
).read_text(encoding="utf-8")


def test_admin_exact_week_lookup_does_not_depend_on_history_scan(tmp_path: Path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "roster.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(
        WEEK_START,
        expected_week_version=0,
        command_id="mobile-exact-week-admin",
    )

    selected = workflow.roster_week_for_start(WEEK_START)

    assert selected is not None
    assert selected["id"] == draft.id
    assert selected["weekStart"] == WEEK_START
    assert workflow.roster_week_for_start(OTHER_WEEK) is None


def test_guest_exact_week_lookup_normalizes_serialized_dates() -> None:
    registry = GuestWorkspaceRegistry(b"mobile-workflow-secret-is-32-bytes")
    context = PageContext.create(
        Principal(
            mode=AccessMode.GUEST,
            subject="guest:mobile-workflow",
            session_id="guest-mobile-workflow",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ),
        request_reference="MOBILE-WORKFLOW",
    )
    adapter = GuestWorkspaceAdapter(
        context,
        registry,
        workspace_id="mobile-workspace",
        tab_id="mobile-tab",
    )
    draft = adapter.generate_and_save_draft(
        WEEK_START,
        expected_week_version=0,
        command_id="mobile-exact-week-guest",
    )

    selected = adapter.roster_week_for_start(WEEK_START)

    assert context.principal.mode is AccessMode.GUEST
    assert selected is not None
    assert selected["id"] == draft.id
    assert selected["weekStart"] == WEEK_START
    assert adapter.roster_week_for_start(OTHER_WEEK) is None


def test_mobile_roster_uses_one_day_phone_view_and_two_column_tablet_view() -> None:
    assert "@media (max-width: 767px)" in MOBILE_CSS
    assert ".sy-draft-mobile--phone" in MOBILE_CSS
    assert "display: grid !important" in MOBILE_CSS
    assert "@media (min-width: 768px) and (max-width: 900px)" in MOBILE_CSS
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in MOBILE_CSS
    assert "@media (max-width: 900px)" in MOBILE_CSS
    assert ".sy-draft-grid-scroll" in MOBILE_CSS
    assert "display: none !important" in MOBILE_CSS


def test_mobile_roster_editor_is_a_shared_sheet_with_one_dirty_dock() -> None:
    assert "data-testid=draft-mobile-day-tabs" in WEEKLY_SOURCE
    assert "data-testid=draft-candidate-search-mobile" in WEEKLY_SOURCE
    assert 'ui.dialog(value=mobile_dialog_state["open"])' in WEEKLY_SOURCE
    assert 'reopen_mobile_editor = mobile_dialog_state["open"]' not in WEEKLY_SOURCE
    assert "data-testid=draft-mobile-save-dock" in WEEKLY_SOURCE
    assert 'test_id="draft-undo-mobile"' in WEEKLY_SOURCE
    assert 'test_id="draft-save-all-mobile-confirm"' in WEEKLY_SOURCE
    assert WEEKLY_SOURCE.count("data-testid=draft-mobile-save-dock") == 1
    assert "cell.focus({preventScroll: true})" in WEEKLY_SOURCE
    assert "cell.scrollIntoView({block: 'nearest', inline: 'nearest'})" in WEEKLY_SOURCE
    assert "ui.timer(" not in WEEKLY_SOURCE
    assert 'selector.run_method("focus")' in WEEKLY_SOURCE


def test_mobile_day_tabs_report_operational_risk_not_only_the_day_name() -> None:
    assert "draft_mobile_day_summary" in WEEKLY_SOURCE
    assert "pending=pending" in WEEKLY_SOURCE
    assert "vacancies=vacancies" in WEEKLY_SOURCE
    assert "unavailable=unavailable" in WEEKLY_SOURCE
    assert "draft_mobile_day_closed_summary" in WEEKLY_SOURCE


def test_draft_leave_guard_replaces_and_cleans_up_its_browser_listener() -> None:
    assert "window.__syDraftBeforeUnloadCleanup?.();" in WEEKLY_SOURCE
    assert "window.removeEventListener('beforeunload', beforeUnload);" in WEEKLY_SOURCE
    assert "window.addEventListener('pagehide', cleanupBeforeUnload, {once: true});" in WEEKLY_SOURCE
