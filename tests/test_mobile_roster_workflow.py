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
    assert ".sy-draft-mobile-view" in MOBILE_CSS
    assert ".sy-draft-mobile-day:not(.sy-draft-mobile-day--selected)" in MOBILE_CSS
    assert "display: grid !important" in MOBILE_CSS
    assert "@media (min-width: 768px) and (max-width: 900px)" in MOBILE_CSS
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in MOBILE_CSS
    assert "@media (max-width: 900px)" in MOBILE_CSS
    assert ".sy-draft-grid-scroll" in MOBILE_CSS
    assert "display: none !important" in MOBILE_CSS
    assert "sy-draft-mobile--phone" not in WEEKLY_SOURCE
    assert "sy-draft-mobile--tablet" not in WEEKLY_SOURCE
    assert "def render_mobile_day(day_item: Any) -> None:" in WEEKLY_SOURCE
    assert "def update_mobile_days() -> None:" in WEEKLY_SOURCE
    assert "mobile_selected_day.refresh()" not in WEEKLY_SOURCE
    assert "for day_item in presentation.days:\n                        render_mobile_day(day_item)" in WEEKLY_SOURCE
    assert 'surface_refreshers["mobile_day"] = update_mobile_days' in WEEKLY_SOURCE
    assert 'data-mobile-day="{attr(day.name)}"' in WEEKLY_SOURCE


def test_mobile_roster_editor_is_a_shared_sheet_with_one_dirty_dock() -> None:
    assert "data-testid=draft-mobile-day-tabs" in WEEKLY_SOURCE
    assert "draft-candidate-search-mobile" in WEEKLY_SOURCE
    assert "with semantic_native_dialog(" in WEEKLY_SOURCE
    assert 'presentation="sheet"' in WEEKLY_SOURCE
    assert 'dialog.run_method("showModal")' in WEEKLY_SOURCE
    assert 'dialog.run_method("close")' in WEEKLY_SOURCE
    assert 'cell_editor_dialog.on(\n                    "cancel"' in WEEKLY_SOURCE
    assert "event.key !== 'Tab'" in WEEKLY_SOURCE
    assert "event.currentTarget.querySelectorAll(" in WEEKLY_SOURCE
    assert 'with ui.dialog().props("persistent") as cell_editor_dialog' not in WEEKLY_SOURCE
    assert "selector = ui.radio(" in WEEKLY_SOURCE
    assert "def filter_mobile_candidates(_event: Any) -> None:" in WEEKLY_SOURCE
    assert "data-testid=draft-candidate-options-mobile" in WEEKLY_SOURCE
    assert 'ui.dialog(value=mobile_dialog_state["open"])' not in WEEKLY_SOURCE
    assert 'reopen_mobile_editor = mobile_dialog_state["open"]' not in WEEKLY_SOURCE
    assert "data-testid=draft-mobile-save-dock" in WEEKLY_SOURCE
    assert 'test_id="draft-undo-mobile"' in WEEKLY_SOURCE
    assert 'test_id="draft-save-all-mobile-confirm"' in WEEKLY_SOURCE
    assert WEEKLY_SOURCE.count("data-testid=draft-mobile-save-dock") == 1
    assert "cell.focus({preventScroll: true})" in WEEKLY_SOURCE
    assert "cell.scrollIntoView({block: 'nearest', inline: 'nearest'})" in WEEKLY_SOURCE
    assert "[...document.querySelectorAll(" in WEEKLY_SOURCE
    assert "item.getClientRects().length" in WEEKLY_SOURCE
    assert "ui.timer(" not in WEEKLY_SOURCE
    assert 'selector.run_method("focus")' in WEEKLY_SOURCE
    assert 'data-testid=draft-desktop-cell-detail' in WEEKLY_SOURCE
    assert 'test_id="draft-mobile-editor-sheet"' in WEEKLY_SOURCE
    close_editor = WEEKLY_SOURCE.split("def close_mobile_editor() -> None:", 1)[1].split(
        "def editor() -> None:", 1
    )[0]
    assert "refresh_draft_surfaces(" in close_editor
    assert "desktop_detail.clear()" not in close_editor
    assert "mobile_detail.clear()" not in close_editor
    assert 'desktop_candidate_selector_ref["control"] = None' not in close_editor
    assert 'mobile_candidate_selector_ref["control"] = None' not in close_editor
    assert 'name=draft-batch-reason autocomplete=off' in WEEKLY_SOURCE
    focus_restore = WEEKLY_SOURCE.split("mobile_editor_focus_restore_js = (", 1)[1].split(
        "def close_mobile_editor()", 1
    )[0]
    assert "window.setTimeout(" in focus_restore
    assert "window.removeEventListener('pointerdown',cancel,true)" in focus_restore
    assert "window.removeEventListener('keydown',cancel,true)" in focus_restore
    assert "mobile_close_action.on(" in WEEKLY_SOURCE
    assert "+ mobile_editor_focus_restore_js" in WEEKLY_SOURCE


def test_draft_editor_keeps_shell_controls_mounted_and_updates_local_surfaces() -> None:
    editor_scope = WEEKLY_SOURCE.split("def editor() -> None:", 1)[1].split(
        "def handle_undo_key", 1
    )[0]

    assert "editor.refresh()" not in WEEKLY_SOURCE
    assert "def refresh_draft_surfaces(" in WEEKLY_SOURCE
    assert 'surface_refreshers["cells"] = update_mounted_cells' in editor_scope
    assert 'surface_refreshers["tabs"] = update_mobile_day_tabs' in editor_scope
    assert 'surface_refreshers["details"] = refresh_selected_details' in editor_scope
    assert 'surface_refreshers["pending"] = update_pending_controls' in editor_scope
    assert "mount_cell_detail_surface(compact=True)" in editor_scope
    assert 'cell_editor_native_ref["control"] = cell_editor_dialog' in editor_scope
    assert "container.clear()" not in editor_scope
    assert "mobile_detail.clear()" not in editor_scope
    assert 'mobile_dock_ref["control"] = mobile_dock' in editor_scope
    assert "def mount_day_header(day_index: int, day_item: Any) -> None:" in editor_scope
    assert "day_header_refreshers[day] = day_header.refresh" in editor_scope
    assert "closed_panel.set_visibility(day_is_closed(day))" in editor_scope
    assert "button.set_visibility(not day_is_closed(cell.day))" in editor_scope
    assert "and is_room_open(cell.post, cell.day)" in WEEKLY_SOURCE
    assert 'button.classes(\n                                    replace=cell_classes(' in editor_scope
    assert "meta_label.set_visibility(bool(meta))" in editor_scope
    assert "def update_mobile_days() -> None:" in editor_scope
    assert "for day_item in presentation.days:" in editor_scope


def test_history_cards_prioritize_date_status_and_one_primary_action() -> None:
    history_scope = WEEKLY_SOURCE.split(
        'data-testid=roster-history-page', 1
    )[1].split('aria-label=Pagination', 1)[0]

    primary_scope = history_scope.split('with ui.expansion(t("mobile_more")', 1)[0]
    assert 'ui.label(str(week["weekStart"]))' in primary_scope
    assert '_tone_badge(t(status), status_tone)' in primary_scope
    assert 'variant="primary"' in primary_scope
    assert "history_priority_used" not in primary_scope
    assert 'data-testid=roster-history-more' in history_scope


def test_mobile_day_tabs_report_operational_risk_not_only_the_day_name() -> None:
    assert "draft_mobile_day_summary" in WEEKLY_SOURCE
    assert "pending=pending" in WEEKLY_SOURCE
    assert "vacancies=vacancies" in WEEKLY_SOURCE
    assert "unavailable=unavailable" in WEEKLY_SOURCE
    assert "draft_mobile_day_closed_summary" in WEEKLY_SOURCE


def test_roster_generation_uses_compact_semantic_choices() -> None:
    assert "sy-day-closure-chips" in WEEKLY_SOURCE
    assert "day_closure_controls" in WEEKLY_SOURCE
    assert "selected_closed_days()" in WEEKLY_SOURCE
    assert "assist_control = ui.toggle(" in WEEKLY_SOURCE
    assert 'with_input=True,\n                            clearable=True,' in WEEKLY_SOURCE
    closure_group = WEEKLY_SOURCE.split(
        '"sy-choice-chips sy-day-closure-chips w-full gap-2 flex-wrap mt-3"', 1
    )[1].split("for day in SchoolDay:", 1)[0]
    assert 'role="group"' in closure_group
    assert 'aria-label="{attr(t("pre_generation_day_closure"))}"' in closure_group
    assist_group = WEEKLY_SOURCE.split("assist_control = ui.toggle(", 1)[1].split(
        "advanced_rule_controls", 1
    )[0]
    assert 'role="group"' in assist_group
    assert 'aria-label="{attr(t("assist_assignment_mode_label"))}"' in assist_group


def test_optional_generation_rules_mount_only_after_explicit_disclosure() -> None:
    lazy_rules = WEEKLY_SOURCE.split("def advanced_rule_panels()", 1)[1].split(
        "def toggle_mobile_rules()", 1
    )[0]
    toggle = WEEKLY_SOURCE.split("def toggle_mobile_rules()", 1)[1].split(
        "advanced_rule_panels()", 1
    )[0]
    generate = WEEKLY_SOURCE.split("async def generate()", 1)[1].split(
        'ui.button(\n                        t("create_draft")', 1
    )[0]

    assert '"mounted": False' in WEEKLY_SOURCE
    assert 'if not advanced_rules_state["mounted"]:\n                            return' in lazy_rules
    assert "assist_control = ui.toggle(" in lazy_rules
    assert 'data-testid=history-priority-chart' in lazy_rules
    assert 'advanced_rules_state["mounted"] = True' in toggle
    assert "advanced_rule_panels.refresh()" in toggle
    assert 'advanced_rules_state["history_priority"]' in generate
    assert 'advanced_rules_state["assist_mode"]' in generate
    assert ".sy-roster-step-rules {" in MOBILE_CSS
    assert ".sy-roster-generation-card.sy-roster-rules-open .sy-roster-step-rules" in MOBILE_CSS
    assert ".sy-roster-advanced-chart {\n    display: none !important;" not in MOBILE_CSS


def test_high_risk_roster_dialogs_use_semantic_alert_contracts() -> None:
    for test_id in (
        "draft-conflict-dialog",
        "draft-discard-dialog",
        "withdraw-roster-dialog",
        "publish-conflict-dialog",
        "publish-confirmation-dialog",
    ):
        dialog_scope = WEEKLY_SOURCE.split(f'test_id="{test_id}"', 1)[0].rsplit(
            "with semantic_dialog(", 1
        )[1]
        assert 'persistent=True' in dialog_scope
        assert 'presentation="alert"' in dialog_scope

    assert "role=alertdialog" in (
        ROOT / "nicegui_app" / "ui" / "components.py"
    ).read_text(encoding="utf-8")


def test_adjustment_requires_an_explicit_assignment_and_outcome() -> None:
    adjustment = WEEKLY_SOURCE.split(
        'with ui.card().classes("sy-surface sy-adjustment-form', 1
    )[1]
    assert 'value=None,\n                    with_input=True' in adjustment
    assert "replacement_select.disable()" in adjustment
    assert "assignment_select.on_value_change(lambda _event: load_substitutes())" in adjustment
    assert "adjustment_selection_incomplete" in adjustment
    assert "data-testid=adjustment-selection-summary" in adjustment
    assert "save_adjustment_button.disable()" in adjustment
    assert 't("load_substitutes"), icon="group_add"' not in adjustment


def test_draft_leave_guard_replaces_and_cleans_up_its_browser_listener() -> None:
    assert "window.__syDraftBeforeUnloadCleanup?.();" in WEEKLY_SOURCE
    assert "window.removeEventListener('beforeunload', beforeUnload);" in WEEKLY_SOURCE
    assert "window.addEventListener('pagehide', cleanupBeforeUnload, {once: true});" in WEEKLY_SOURCE
