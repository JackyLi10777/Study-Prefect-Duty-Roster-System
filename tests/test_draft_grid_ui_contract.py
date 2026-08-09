from __future__ import annotations

import ast
from datetime import date

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.edit_sessions import DraftEditSession
from nicegui_app.ui.page_routes.weekly import (
    _generation_requirements_query_key,
    _normalize_draft_candidate_value,
    _stage_atomic_draft_selection,
    _stage_draft_move,
)


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
EDIT_SESSION_SOURCE = (
    PROJECT_ROOT / "nicegui_app" / "ui" / "edit_sessions.py"
).read_text(encoding="utf-8")
WEEKLY_TREE = ast.parse(WEEKLY_SOURCE)


def _calls_named(name: str) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(WEEKLY_TREE)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == name)
            or (isinstance(node.func, ast.Attribute) and node.func.attr == name)
        )
    ]


def _function_named(name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    matches = [
        node
        for node in ast.walk(WEEKLY_TREE)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    ]
    assert len(matches) == 1
    return matches[0]


def _function_calls(function: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    return {
        node.func.id
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


def test_generation_records_explicit_whole_day_closures_atomically() -> None:
    assert "pre-generation-day-closures" in WEEKLY_SOURCE
    requirements_calls = _calls_named("generation_requirements")
    generation_calls = _calls_named("generate_and_save_draft")
    assert any(
        any(keyword.arg == "closed_days" for keyword in call.keywords)
        for call in requirements_calls
    )
    assert any(
        any(keyword.arg == "closed_days" for keyword in call.keywords)
        for call in generation_calls
    )


def test_generation_requirements_query_key_deduplicates_equivalent_week_context() -> None:
    week_start = date(2026, 8, 10)
    assert _generation_requirements_query_key(
        week_start,
        ["FRIDAY", "MONDAY"],
    ) == _generation_requirements_query_key(
        week_start,
        ["MONDAY", "FRIDAY"],
    )
    assert 'requirements_state["rendered_key"] == query_key' in WEEKLY_SOURCE


def test_leave_mutations_invalidate_and_refresh_generation_requirements() -> None:
    refresh_after_change = _function_named("refresh_requirements_after_leave_change")
    assignment = next(
        node
        for node in ast.walk(refresh_after_change)
        if isinstance(node, ast.Assign)
    )
    assert isinstance(assignment.value, ast.Constant)
    assert assignment.value.value is None
    assert "refresh_requirements" in _function_calls(refresh_after_change)

    for callback_name in ("declare_leave", "cancel_leave"):
        callback = _function_named(callback_name)
        assert "refresh_requirements_after_leave_change" in _function_calls(callback)


def test_draft_editor_uses_one_canonical_matrix_and_one_batch_patch() -> None:
    assert "build_roster_presentation(" in WEEKLY_SOURCE
    assert "workflow.roster_schedule_snapshot(roster_week_id)" in WEEKLY_SOURCE
    assert "edit_session = DraftEditSession(" in WEEKLY_SOURCE
    assert "cell_values, day_values, slot_values = edit_session.patch_edits()" in WEEKLY_SOURCE
    assert "DraftCellEdit(cell_key=key, replacement_prefect_id=value)" in EDIT_SESSION_SOURCE
    assert "DraftDayEdit(day=day, closed=closed)" in EDIT_SESSION_SOURCE
    assert "DraftSlotStateEdit(" in EDIT_SESSION_SOURCE
    assert 'state="unavailable" if unavailable else "open"' in EDIT_SESSION_SOURCE
    assert "workflow.apply_draft_patch(" in WEEKLY_SOURCE
    assert "workflow.update_draft_assignment(" not in WEEKLY_SOURCE
    assert 'with_input=True' in WEEKLY_SOURCE
    assert '"__vacant__": t("draft_explicit_vacancy")' in WEEKLY_SOURCE
    assert 'f\'data-cell-key="{attr(key)}"\'' in WEEKLY_SOURCE


def test_unsaved_changes_support_undo_discard_and_conflict_preservation() -> None:
    assert "edit_session = DraftEditSession(" in WEEKLY_SOURCE
    assert "edit_session.undo()" in WEEKLY_SOURCE
    assert "edit_session.redo()" in WEEKLY_SOURCE
    assert "edit_session.ensure_command_id()" in WEEKLY_SOURCE
    assert "_undo: list[DraftEditSnapshot]" in EDIT_SESSION_SOURCE
    assert "_redo: list[DraftEditSnapshot]" in EDIT_SESSION_SOURCE
    assert "window.__syDraftDirty" in WEEKLY_SOURCE
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


def test_move_and_exchange_are_one_atomic_pending_state() -> None:
    originals = {
        "MONDAY:ROOM_302:1": "prefect-a",
        "MONDAY:ROOM_303:1": "prefect-b",
        "MONDAY:ROOM_303:2": None,
    }
    pending: dict[str, str | None] = {}

    moved, exchanged = _stage_draft_move(
        "MONDAY:ROOM_302:1",
        "MONDAY:ROOM_303:2",
        original_assignments=originals,
        pending_cells=pending,
    )
    assert (moved, exchanged) == ("prefect-a", None)
    assert pending == {
        "MONDAY:ROOM_302:1": None,
        "MONDAY:ROOM_303:2": "prefect-a",
    }

    pending.clear()
    moved, exchanged = _stage_draft_move(
        "MONDAY:ROOM_302:1",
        "MONDAY:ROOM_303:1",
        original_assignments=originals,
        pending_cells=pending,
    )
    assert (moved, exchanged) == ("prefect-a", "prefect-b")
    assert pending == {
        "MONDAY:ROOM_302:1": "prefect-b",
        "MONDAY:ROOM_303:1": "prefect-a",
    }


def test_typed_draft_session_owns_dirty_history_retry_and_conflict_reapply() -> None:
    session = DraftEditSession(
        original_assignments={
            "MONDAY:ROOM_302:0": "prefect-a",
            "MONDAY:ROOM_303:0": "prefect-b",
            "TUESDAY:ROOM_302:0": None,
        },
        original_unavailable=set(),
        original_closed_days=set(),
        reviewed_version=4,
        _command_factory=lambda: "stable-draft-command",
    )

    mutation = session.stage_candidate("MONDAY:ROOM_302:0", "prefect-b")
    assert mutation.kind == "swap"
    assert mutation.exchanged_cell_key == "MONDAY:ROOM_303:0"
    assert session.dirty is True
    assert session.pending_count == 2
    assert session.ensure_command_id() == "stable-draft-command"
    assert session.ensure_command_id() == "stable-draft-command"

    assert session.undo() is True
    assert session.dirty is False
    assert session.redo() is True
    assert session.pending_cells["MONDAY:ROOM_302:0"] == "prefect-b"

    assert session.stage_slot("MONDAY:ROOM_302:0", True) is True
    assert session.slot_is_unavailable("MONDAY:ROOM_302:0") is True
    assert "MONDAY:ROOM_302:0" not in session.pending_cells
    assert session.undo() is True
    assert session.pending_cells["MONDAY:ROOM_302:0"] == "prefect-b"

    session.set_conflict(latest_version=9, changes=["Monday changed"])
    assert session.reapply_conflict() is True
    assert session.reviewed_version == 9
    assert session.command_id is None
    cell_edits, day_edits, slot_edits = session.patch_edits()
    assert len(cell_edits) == 2
    assert day_edits == ()
    assert slot_edits == ()


def test_typed_draft_session_rejects_edits_on_closed_surfaces() -> None:
    session = DraftEditSession(
        original_assignments={
            "MONDAY:ROOM_302:0": "prefect-a",
            "MONDAY:ROOM_303:0": None,
            "TUESDAY:ROOM_302:0": "prefect-b",
        },
        original_unavailable={"MONDAY:ROOM_303:0"},
        original_closed_days={"TUESDAY"},
        reviewed_version=1,
    )

    assert session.stage_candidate("MONDAY:ROOM_303:0", "prefect-a").kind == "blocked"
    assert session.stage_candidate("TUESDAY:ROOM_302:0", None).kind == "blocked"
    assert (
        session.stage_move("MONDAY:ROOM_302:0", "MONDAY:ROOM_303:0").kind
        == "blocked"
    )
    assert (
        session.stage_move("TUESDAY:ROOM_302:0", "MONDAY:ROOM_302:0").kind
        == "blocked"
    )
    assert session.dirty is False


def test_vacancy_aliases_normalize_without_treating_blank_input_as_vacant() -> None:
    for alias in ("X", "x", "×", "空缺", "待安排", "Vacant", "unassigned"):
        assert _normalize_draft_candidate_value(alias) == "__vacant__"
    assert _normalize_draft_candidate_value("  X  ") == "__vacant__"
    assert _normalize_draft_candidate_value("") == ""
    assert _normalize_draft_candidate_value("   ") == ""
    assert _normalize_draft_candidate_value(None) is None
    assert _normalize_draft_candidate_value("prefect-id") == "prefect-id"


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
    assert 'role="gridcell" tabindex="0"' in WEEKLY_SOURCE
    assert 'aria-disabled="true" tabindex="-1"' in WEEKLY_SOURCE
    assert "'ArrowDown', 'ArrowLeft', 'ArrowRight'" in WEEKLY_SOURCE
    assert '"pointerdown"' in WEEKLY_SOURCE
    assert '"pointerup"' in WEEKLY_SOURCE
    assert "distance > 8" in WEEKLY_SOURCE
    assert "visible_navigable_keys = [" in WEEKLY_SOURCE
    assert "edit_session.selected_cell in visible_navigable_keys" in WEEKLY_SOURCE
    assert 'draft_conflict_slot_changed", cell=slot_label' in WEEKLY_SOURCE
    assert "event.preventDefault(); event.stopPropagation()" in WEEKLY_SOURCE
    assert '"__vacant__": t("draft_explicit_vacancy")' in WEEKLY_SOURCE
    assert 'new_value_mode="add-unique"' not in WEEKLY_SOURCE
    assert 'ui.notify(t("draft_candidate_invalid"), type="warning")' in WEEKLY_SOURCE
    assert ":not(.sy-draft-grid-cell--closed):hover" in COMPONENT_SOURCE
    assert ":not(.sy-draft-mobile-cell--closed):hover" in COMPONENT_SOURCE
    assert 'aria-live=polite data-testid=draft-pending-bar' in WEEKLY_SOURCE
    assert 'role=status aria-live=polite aria-atomic=true' in WEEKLY_SOURCE
    assert 'data-testid=draft-grid-announcement' in WEEKLY_SOURCE
    assert "draft-day-confirm-close-" in WEEKLY_SOURCE
    assert "draft-day-confirm-reopen-" in WEEKLY_SOURCE
    assert "and cell.prefect_id" in WEEKLY_SOURCE
    assert "sy-draft-grid-cell--unavailable" in COMPONENT_SOURCE
    assert "sy-draft-grid-cell--move-source" in COMPONENT_SOURCE
    assert "outline: 2px dashed CanvasText" in COMPONENT_SOURCE
    assert "outline: 3px solid Highlight" in COMPONENT_SOURCE


def test_draft_editor_copy_is_bilingual_and_keeps_duty_posts_in_english() -> None:
    for key in (
        "draft_schedule_title",
        "draft_explicit_vacancy",
        "draft_pending_count",
        "draft_day_closed",
        "draft_candidate_swap_suffix",
        "draft_candidate_invalid",
        "draft_conflict_reapply",
        "pre_generation_day_closure",
        "draft_slot_unavailable",
        "draft_slot_reopen_action",
        "draft_redo",
    ):
        assert f"'{key}'" in I18N_SOURCE
    assert "Assist. in charge" not in I18N_SOURCE
    assert "Room 302 Study Room" not in I18N_SOURCE
    assert "X / × / 空缺 / 待安排" in I18N_SOURCE
