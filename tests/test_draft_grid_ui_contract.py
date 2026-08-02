from __future__ import annotations

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.page_routes.weekly import _stage_atomic_draft_selection


WEEKLY_SOURCE = (
    PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "weekly.py"
).read_text(encoding="utf-8")
COMPONENT_SOURCE = (
    PROJECT_ROOT
    / "nicegui_app"
    / "assets"
    / "css"
    / "sing-yin-components-v1.css"
).read_text(encoding="utf-8")
I18N_SOURCE = (
    PROJECT_ROOT
    / "nicegui_app"
    / "ui"
    / "i18n_catalog"
    / "stewardship.py"
).read_text(encoding="utf-8")


def test_generation_records_explicit_whole_day_closures_atomically() -> None:
    assert "pre-generation-day-closures" in WEEKLY_SOURCE
    assert "generation_requirements(\n                                week_start,\n                                closed_days=" in WEEKLY_SOURCE
    assert "generate_and_save_draft(" in WEEKLY_SOURCE
    assert "closed_days=tuple(day_closure_select.value or ())" in WEEKLY_SOURCE


def test_draft_editor_uses_one_canonical_matrix_and_one_batch_patch() -> None:
    assert "build_roster_presentation(" in WEEKLY_SOURCE
    assert "workflow.roster_schedule_snapshot(roster_week_id)" in WEEKLY_SOURCE
    assert "DraftCellEdit(cell_key=key, replacement_prefect_id=value)" in WEEKLY_SOURCE
    assert "DraftDayEdit(day=day, closed=closed)" in WEEKLY_SOURCE
    assert "workflow.apply_draft_patch(" in WEEKLY_SOURCE
    assert "workflow.update_draft_assignment(" not in WEEKLY_SOURCE
    assert 'with_input=True' in WEEKLY_SOURCE
    assert '"__vacant__": t("draft_explicit_vacancy")' in WEEKLY_SOURCE


def test_unsaved_changes_support_undo_discard_and_conflict_preservation() -> None:
    assert "pending_cells: dict[str, str | None]" in WEEKLY_SOURCE
    assert "undo_stack:" in WEEKLY_SOURCE
    assert "ui.keyboard(" in WEEKLY_SOURCE
    assert 'ignore=["input", "select", "textarea"]' in WEEKLY_SOURCE
    assert "key_name = event.key.name.lower()" in WEEKLY_SOURCE
    assert 'key_name == "z"' in WEEKLY_SOURCE
    assert 'key_name in {"f2", "enter"}' in WEEKLY_SOURCE
    assert 'key_name == "escape"' in WEEKLY_SOURCE
    assert "draft_conflict_preserved_title" in WEEKLY_SOURCE
    assert "draft_conflict_keep_editing" in WEEKLY_SOURCE
    assert "draft_conflict_comparison_title" in WEEKLY_SOURCE
    assert "draft_conflict_reapply" in WEEKLY_SOURCE
    assert "draft_conflict_reload" in WEEKLY_SOURCE
    assert "compare_draft_conflict" in WEEKLY_SOURCE
    assert 'test_id="draft-conflict-reapply"' in WEEKLY_SOURCE


def test_same_day_selection_stages_one_atomic_exchange_and_can_be_undone() -> None:
    originals = {
        "MONDAY:ROOM_302:0": "prefect-a",
        "MONDAY:ROOM_303:0": "prefect-b",
        "TUESDAY:ROOM_302:0": "prefect-c",
    }
    pending: dict[str, str | None] = {}

    occupied = _stage_atomic_draft_selection(
        "MONDAY:ROOM_302:0",
        "prefect-b",
        original_assignments=originals,
        pending_cells=pending,
    )

    assert occupied == "MONDAY:ROOM_303:0"
    assert pending == {
        "MONDAY:ROOM_302:0": "prefect-b",
        "MONDAY:ROOM_303:0": "prefect-a",
    }

    _stage_atomic_draft_selection(
        "MONDAY:ROOM_302:0",
        "prefect-a",
        original_assignments=originals,
        pending_cells=pending,
    )
    assert pending == {}


def test_vacancy_selection_does_not_affect_another_cell() -> None:
    originals = {
        "MONDAY:ROOM_302:0": "prefect-a",
        "MONDAY:ROOM_303:0": "prefect-b",
        "MONDAY:ROOM_303:1": None,
    }
    pending: dict[str, str | None] = {}

    occupied = _stage_atomic_draft_selection(
        "MONDAY:ROOM_302:0",
        None,
        original_assignments=originals,
        pending_cells=pending,
    )

    assert occupied is None
    assert pending == {"MONDAY:ROOM_302:0": None}


def test_draft_matrix_has_desktop_mobile_and_accessible_interaction_contracts() -> None:
    for selector in (
        ".sy-draft-grid-desktop",
        ".sy-draft-mobile",
        ".sy-draft-grid-day-closed",
        ".sy-draft-pending-bar",
        ".sy-draft-grid-cell:focus-visible",
    ):
        assert selector in COMPONENT_SOURCE
    assert "@media (max-width: 900px)" in COMPONENT_SOURCE
    assert "@media (forced-colors: active)" in COMPONENT_SOURCE
    assert "min-height: 52px" in COMPONENT_SOURCE
    assert 'role="grid"' in WEEKLY_SOURCE
    assert 'aria-live=polite data-testid=draft-pending-bar' in WEEKLY_SOURCE
    assert "draft-day-confirm-close-" in WEEKLY_SOURCE
    assert "draft-day-confirm-reopen-" in WEEKLY_SOURCE
    assert "and cell.prefect_id" in WEEKLY_SOURCE


def test_draft_editor_copy_is_bilingual_and_keeps_duty_posts_in_english() -> None:
    for key in (
        "draft_schedule_title",
        "draft_explicit_vacancy",
        "draft_pending_count",
        "draft_day_closed",
        "draft_candidate_swap_suffix",
        "draft_conflict_reapply",
        "pre_generation_day_closure",
    ):
        assert f"'{key}'" in I18N_SOURCE
    assert "Assist. in charge" not in I18N_SOURCE
    assert "Room 302 Study Room" not in I18N_SOURCE
    assert "X / × / 空缺 / 待安排" in I18N_SOURCE
