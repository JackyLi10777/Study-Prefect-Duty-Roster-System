"""NiceGUI route registrations grouped by operator domain."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from nicegui import ui

from nicegui_app.runtime import get_workflow
from nicegui_app.services.roster_presentation import (
    RosterCellState,
    build_roster_presentation,
    roster_display_label,
)
from nicegui_app.services.roster_workflow import (
    FLEXIBLE_WEEKLY,
    LEGACY_FIXED_WEEKDAY,
    WorkflowError,
)
from nicegui_app.ui.access_control import render_roster_share_action, revoke_roster_shares
from nicegui_app.ui.components import action
from nicegui_app.ui.edit_sessions import DraftEditSession
from nicegui_app.ui.html_safety import attr
from nicegui_app.ui.i18n import day_label, t
from nicegui_app.ui.navigation import navigate_to
from nicegui_app.ui.page_shared import (
    _OPERATION_FAILED,
    _navigate_with_feedback,
    _next_monday,
    _open_roster_export_dialog,
    _render_empty_state,
    _render_operation_hint,
    _render_responsive_table,
    _render_roster_route_state,
    _render_roster_table,
    _render_storage_lifecycle,
    _run_with_progress,
    _safe_read_action,
    _tone_badge,
)
from nicegui_app.ui.shell import page_shell
from nicegui_app.ui.theme import current_theme
from nicegui_app.ui.workflow_navigation import (
    WorkflowStep,
    render_back_action,
    render_route_trail,
    render_workflow_navigation,
)
from roster_core import HISTORY_PRIORITY_MULTIPLIER_MAX, HISTORY_PRIORITY_MULTIPLIER_MIN
from roster_policy import SchoolDay, is_room_open


_ASSIST_MODE_LABEL_KEYS = {
    LEGACY_FIXED_WEEKDAY: "assist_assignment_mode_legacy",
    FLEXIBLE_WEEKLY: "assist_assignment_mode_flexible",
}
_ASSIST_MODE_DETAIL_KEYS = {
    LEGACY_FIXED_WEEKDAY: "assist_assignment_mode_legacy_detail",
    FLEXIBLE_WEEKLY: "assist_assignment_mode_flexible_detail",
}
_DRAFT_VACANCY_VALUE = "__vacant__"
_DRAFT_VACANCY_ALIASES = frozenset(
    {"x", "×", "空缺", "待安排", "vacant", "unassigned", _DRAFT_VACANCY_VALUE}
)


def _install_roster_mobile_styles() -> None:
    """Install the route-owned responsive layer after the shared design system."""

    ui.add_head_html(
        '<link rel="stylesheet" href="/assets/css/sing-yin-roster-mobile-v1.css" '
        'data-sy-style-layer="roster-mobile">'
    )


def _normalize_draft_candidate_value(value: object) -> str | None:
    """Normalize explicit vacancy aliases without treating blank input as a change."""

    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return ""
    if normalized.casefold() in _DRAFT_VACANCY_ALIASES:
        return _DRAFT_VACANCY_VALUE
    return normalized


def _generation_requirements_query_key(
    week_start: date,
    closed_days: object,
) -> tuple[str, tuple[str, ...]]:
    """Return one stable key for a rendered generation-requirements result."""

    normalized_days = tuple(sorted(str(day) for day in (closed_days or ())))
    return week_start.isoformat(), normalized_days


def _assist_assignment_mode_code(value: object, *, fallback: str) -> str:
    """Keep stable rule codes separate from their bilingual presentation labels."""

    normalized = str(value or "").strip()
    return normalized if normalized in _ASSIST_MODE_LABEL_KEYS else fallback


def _assist_assignment_mode_label(value: object) -> str:
    mode = _assist_assignment_mode_code(value, fallback=FLEXIBLE_WEEKLY)
    return t(_ASSIST_MODE_LABEL_KEYS[mode])


def _stage_atomic_draft_selection(
    cell_key: str,
    replacement_prefect_id: str | None,
    *,
    original_assignments: dict[str, str | None],
    pending_cells: dict[str, str | None],
) -> str | None:
    """Stage one selection and exchange an occupied same-day cell in the same patch."""

    session = DraftEditSession(
        original_assignments=original_assignments,
        original_unavailable=set(),
        original_closed_days=set(),
        reviewed_version=0,
        pending_cells=pending_cells,
    )
    return session.stage_candidate(
        cell_key,
        replacement_prefect_id,
    ).exchanged_cell_key


def _stage_draft_move(
    source_key: str,
    target_key: str,
    *,
    original_assignments: dict[str, str | None],
    pending_cells: dict[str, str | None],
) -> tuple[str | None, str | None]:
    """Stage one atomic move or exchange and return the prior cell values."""

    session = DraftEditSession(
        original_assignments=original_assignments,
        original_unavailable=set(),
        original_closed_days=set(),
        reviewed_version=0,
        pending_cells=pending_cells,
    )
    mutation = session.stage_move(source_key, target_key)
    return mutation.source_prefect_id, mutation.target_prefect_id


def _render_draft_grid_editor(workflow: Any, roster_week_id: int) -> None:
    """Render one batch-safe draft editor around the canonical roster matrix."""

    week_snapshot, assignments = workflow.roster_schedule_snapshot(roster_week_id)
    presentation = build_roster_presentation(
        week_snapshot,
        assignments,
        closed_days=week_snapshot.get("closedDays", ()),
        editable=True,
    )
    cells_by_key = {
        cell.cell_key: cell
        for row in presentation.rows
        for cell in row.cells
        if cell.cell_key
    }
    service_time_by_cell = {
        cell.cell_key: "–".join(row.spec.service_time)
        for row in presentation.rows
        for cell in row.cells
        if cell.cell_key
    }
    desktop_candidate_selector_ref: dict[str, Any | None] = {"control": None}
    mobile_candidate_selector_ref: dict[str, Any | None] = {"control": None}
    cell_editor_dialog_ref: dict[str, Any | None] = {"control": None}
    save_review_dialog_ref: dict[str, Any | None] = {"control": None}
    mobile_dialog_state: dict[str, bool] = {"open": False}
    mobile_day_state: dict[str, str] = {
        "value": presentation.days[0].day.name if presentation.days else ""
    }
    reason_state: dict[str, str] = {"value": ""}
    announcement_state: dict[str, str] = {"value": ""}
    candidate_cache: dict[str, list[dict[str, object]] | None] = {}
    conflict_reapply_ref: dict[str, Any | None] = {"control": None}
    prefect_names = {
        str(cell.prefect_id): str(cell.prefect_name)
        for cell in cells_by_key.values()
        if cell.prefect_id and cell.prefect_name
    }
    original_assignments = {
        cell_key: (str(cell.prefect_id) if cell.prefect_id else None)
        for cell_key, cell in cells_by_key.items()
    }
    original_unavailable = {
        cell_key
        for cell_key, cell in cells_by_key.items()
        if cell.state is RosterCellState.UNAVAILABLE
    }
    original_closed_days = {
        item.day.name for item in presentation.days if item.state == "day_closed"
    }
    edit_session = DraftEditSession(
        original_assignments=original_assignments,
        original_unavailable=original_unavailable,
        original_closed_days=original_closed_days,
        reviewed_version=int(week_snapshot["version"]),
    )
    pending_cells = edit_session.pending_cells
    pending_days = edit_session.pending_days
    pending_slots = edit_session.pending_slots
    navigable_keys = [
        cell.cell_key
        for row in presentation.rows
        for cell in row.cells
        if cell.cell_key
        and cell.state not in {RosterCellState.ROOM_CLOSED, RosterCellState.DAY_CLOSED}
    ]

    def day_is_closed(day: SchoolDay) -> bool:
        return edit_session.day_is_closed(day.name)

    def pending_count() -> int:
        return edit_session.pending_count

    def slot_is_unavailable(cell_key: str) -> bool:
        return edit_session.slot_is_unavailable(cell_key)

    def cell_display(cell: Any) -> tuple[str, str, str]:
        if slot_is_unavailable(cell.cell_key):
            return t("draft_slot_unavailable"), t("draft_slot_unavailable_meta"), "unavailable"
        if cell.cell_key in pending_cells:
            replacement_id = pending_cells[cell.cell_key]
            if replacement_id is None:
                return t("vacant"), t("draft_pending_value"), "vacant"
            candidates = candidate_cache.get(cell.cell_key) or []
            replacement = next(
                (item for item in candidates if str(item.get("id")) == replacement_id),
                None,
            )
            return (
                str(replacement.get("nameZh"))
                if replacement
                else prefect_names.get(replacement_id, t("draft_pending_value")),
                t("draft_pending_value"),
                "assigned",
            )
        effective_state = cell.state
        if cell.state is RosterCellState.DAY_CLOSED:
            effective_state = (
                RosterCellState.VACANT
                if is_room_open(cell.post, cell.day)
                else RosterCellState.ROOM_CLOSED
            )
        if effective_state is RosterCellState.ASSIGNED:
            return (
                str(cell.prefect_name or ""),
                service_time_by_cell.get(cell.cell_key, ""),
                "assigned",
            )
        if effective_state in {RosterCellState.VACANT, RosterCellState.UNAVAILABLE}:
            return t("vacant"), service_time_by_cell.get(cell.cell_key, ""), "vacant"
        return t("closed"), "", "closed"

    def load_candidates(cell: Any) -> list[dict[str, object]] | None:
        if cell.cell_key in candidate_cache:
            return candidate_cache[cell.cell_key]

        def read() -> list[dict[str, object]]:
            by_cell = getattr(workflow, "draft_cell_candidates", None)
            if callable(by_cell):
                return list(by_cell(roster_week_id, cell.cell_key))
            if cell.assignment_id is None:
                raise WorkflowError("This reopened duty cell must be saved before candidates can be loaded.")
            return list(
                workflow.draft_assignment_candidates(roster_week_id, int(cell.assignment_id))
            )

        candidates = _safe_read_action(read, action_name="load_draft_cell_candidates")
        if candidates is None:
            return None
        candidate_cache[cell.cell_key] = list(candidates)
        prefect_names.update(
            {
                str(candidate["id"]): str(candidate["nameZh"])
                for candidate in candidates
                if candidate.get("id") and candidate.get("nameZh")
            }
        )
        return candidate_cache[cell.cell_key]

    def open_cell_editor(cell_key: str, *, compact: bool = False) -> None:
        if edit_session.move_source and edit_session.move_source != cell_key:
            stage_move(edit_session.move_source, cell_key)
            return
        edit_session.selected_cell = cell_key
        mobile_dialog_state["open"] = compact
        refresh_editor()
        selector_ref = (
            mobile_candidate_selector_ref
            if compact
            else desktop_candidate_selector_ref
        )
        selector = selector_ref["control"]
        if selector is not None:
            selector.run_method("focus")

    def focus_cell(cell_key: str) -> None:
        edit_session.selected_cell = cell_key
        mobile_dialog_state["open"] = False
        refresh_editor()
        ui.run_javascript(
            "requestAnimationFrame(() => { const cell = [...document.querySelectorAll("
            f"'[data-cell-key=\"{attr(cell_key)}\"]'"
            ")].find(item => item.getClientRects().length && "
            "getComputedStyle(item).visibility !== 'hidden'); cell?.focus(); })"
        )

    def neighboring_cell(cell_key: str, key_name: str) -> str | None:
        cell = cells_by_key[cell_key]
        row_index = next(
            index
            for index, row in enumerate(presentation.rows)
            if row.spec.post == cell.post and row.spec.slot_index == cell.slot_index
        )
        day_index = next(
            index for index, day in enumerate(presentation.days) if day.day == cell.day
        )
        row_delta, day_delta = {
            "arrowup": (-1, 0),
            "arrowdown": (1, 0),
            "arrowleft": (0, -1),
            "arrowright": (0, 1),
        }.get(key_name, (0, 0))
        next_row = row_index + row_delta
        next_day = day_index + day_delta
        while 0 <= next_row < len(presentation.rows) and 0 <= next_day < len(presentation.days):
            target = next(
                item
                for item in presentation.rows[next_row].cells
                if item.day == presentation.days[next_day].day
            )
            if target.cell_key in navigable_keys and not day_is_closed(target.day):
                return target.cell_key
            next_row += row_delta
            next_day += day_delta
        return None

    def handle_cell_key(event: Any, cell_key: str) -> None:
        event_args = event.args if isinstance(event.args, dict) else {}
        key_name = str(event_args.get("key", "")).lower()
        compact = bool(event_args.get("compact", False))
        if key_name in {"arrowup", "arrowdown", "arrowleft", "arrowright"}:
            neighbor = neighboring_cell(cell_key, key_name)
            if neighbor:
                focus_cell(neighbor)
        elif key_name == " ":
            if edit_session.move_source == cell_key:
                edit_session.move_source = None
            elif edit_session.move_source:
                stage_move(edit_session.move_source, cell_key)
            elif not slot_is_unavailable(cell_key) and (
                pending_cells.get(cell_key, original_assignments.get(cell_key)) is not None
            ):
                edit_session.move_source = cell_key
                refresh_editor()
        elif key_name in {"enter", "f2"}:
            open_cell_editor(cell_key, compact=compact)
        elif key_name == "escape" and edit_session.selected_cell == cell_key:
            mobile_dialog_state["open"] = False
            edit_session.selected_cell = None
            refresh_editor()

    def handle_pointer_move(event: Any) -> None:
        event_args = event.args if isinstance(event.args, dict) else {}
        source_key = str(event_args.get("source", ""))
        target_key = str(event_args.get("target", ""))
        if source_key in cells_by_key and target_key in cells_by_key:
            stage_move(source_key, target_key)

    def stage_candidate(cell_key: str, raw_value: object) -> None:
        if slot_is_unavailable(cell_key):
            ui.notify(t("draft_slot_reopen_before_assign"), type="warning")
            return
        normalized_value = _normalize_draft_candidate_value(raw_value)
        if normalized_value in (None, ""):
            return
        replacement_id = (
            None if normalized_value == _DRAFT_VACANCY_VALUE else normalized_value
        )
        if replacement_id is not None:
            candidate_ids = {
                str(candidate["id"])
                for candidate in (candidate_cache.get(cell_key) or [])
                if candidate.get("id")
            }
            original_id = original_assignments.get(cell_key)
            if original_id is not None:
                candidate_ids.add(original_id)
            if replacement_id not in candidate_ids:
                ui.notify(t("draft_candidate_invalid"), type="warning")
                refresh_editor()
                return
        current_id = pending_cells.get(cell_key, original_assignments[cell_key])
        if replacement_id == current_id:
            return
        mutation = edit_session.stage_candidate(cell_key, replacement_id)
        if mutation.exchanged_cell_key:
            message = t("draft_swap_staged", name=prefect_names.get(replacement_id, ""))
            announcement_state["value"] = message
            ui.notify(message, type="info")
        else:
            announcement_state["value"] = t("draft_assignment_staged")
        refresh_editor()

    def stage_move(source_key: str, target_key: str) -> None:
        edit_session.move_source = None
        if source_key == target_key or slot_is_unavailable(target_key):
            ui.notify(t("draft_move_invalid_target"), type="warning")
            refresh_editor()
            return
        source_id = edit_session.effective_assignment(source_key)
        target_id = edit_session.effective_assignment(target_key)
        if source_id is None:
            ui.notify(t("draft_move_source_empty"), type="warning")
            refresh_editor()
            return
        target_candidates = load_candidates(cells_by_key[target_key])
        source_candidates = load_candidates(cells_by_key[source_key]) if target_id else []
        target_ids = {
            str(candidate["id"])
            for candidate in (target_candidates or [])
            if candidate.get("id")
        }
        source_ids = {
            str(candidate["id"])
            for candidate in (source_candidates or [])
            if candidate.get("id")
        }
        if source_id not in target_ids or (target_id is not None and target_id not in source_ids):
            ui.notify(t("draft_move_policy_rejected"), type="warning")
            refresh_editor()
            return
        mutation = edit_session.stage_move(source_key, target_key)
        if mutation.kind in {"blocked", "noop", "empty"}:
            ui.notify(t("draft_move_invalid_target"), type="warning")
            refresh_editor()
            return
        message = (
            t("draft_exchange_staged")
            if mutation.kind == "swap"
            else t("draft_move_staged")
        )
        announcement_state["value"] = message
        ui.notify(message, type="info")
        refresh_editor()

    def toggle_move_source(cell_key: str) -> None:
        edit_session.move_source = (
            None if edit_session.move_source == cell_key else cell_key
        )
        refresh_editor()

    def stage_slot(cell_key: str, unavailable: bool) -> None:
        if not edit_session.stage_slot(cell_key, unavailable):
            return
        announcement_state["value"] = t(
            "draft_slot_state_staged_unavailable"
            if unavailable
            else "draft_slot_state_staged_open"
        )
        refresh_editor()

    def stage_day(day: SchoolDay, closed: bool) -> None:
        if not edit_session.stage_day(day.name, closed):
            return
        announcement_state["value"] = t(
            "draft_day_state_staged_closed" if closed else "draft_day_state_staged_open",
            day=day_label(day),
        )
        refresh_editor()

    def undo_pending() -> None:
        if not edit_session.undo():
            return
        announcement_state["value"] = t("draft_undo_announced")
        refresh_editor()

    def redo_pending() -> None:
        if not edit_session.redo():
            return
        announcement_state["value"] = t("draft_redo_announced")
        refresh_editor()

    def discard_pending() -> None:
        edit_session.discard()
        reason_state["value"] = ""
        ui.run_javascript("window.__syDraftDirty = false")
        discard_dialog.close()
        refresh_editor()

    def reload_latest() -> None:
        conflict_dialog.close()
        ui.navigate.reload()

    def compare_latest(_error: Exception | None = None) -> None:
        latest = _safe_read_action(
            lambda: workflow.roster_schedule_snapshot(roster_week_id),
            action_name="compare_draft_conflict",
        )
        if latest is None:
            edit_session.set_conflict(
                latest_version=None,
                changes=[t("draft_conflict_compare_unavailable")],
            )
        else:
            latest_week, latest_assignments = latest
            latest_presentation = build_roster_presentation(
                latest_week,
                latest_assignments,
                closed_days=latest_week.get("closedDays", ()),
                editable=True,
            )
            latest_cells = {
                candidate.cell_key: candidate
                for candidate_row in latest_presentation.rows
                for candidate in candidate_row.cells
                if candidate.cell_key
            }
            changes: list[str] = []
            for cell_key in pending_cells:
                previous = cells_by_key.get(cell_key)
                current = latest_cells.get(cell_key)
                previous_id = str(previous.prefect_id) if previous and previous.prefect_id else None
                current_id = str(current.prefect_id) if current and current.prefect_id else None
                if previous_id != current_id:
                    label = cell_key
                    if previous:
                        row = next(
                            row_item
                            for row_item in presentation.rows
                            if row_item.spec.post == previous.post
                            and row_item.spec.slot_index == previous.slot_index
                        )
                        label = f"{day_label(previous.day)} · {row.spec.display_label}"
                    changes.append(
                        t(
                            "draft_conflict_cell_changed",
                            cell=label,
                            before=(previous.prefect_name if previous and previous.prefect_name else t("vacant")),
                            after=(current.prefect_name if current and current.prefect_name else t("vacant")),
                        )
                    )
            previous_closed_days = {
                item.day.name for item in presentation.days if item.state == "day_closed"
            }
            latest_closed_days = {
                item.day.name for item in latest_presentation.days if item.state == "day_closed"
            }
            for day_name in pending_days:
                if (day_name in previous_closed_days) != (day_name in latest_closed_days):
                    changes.append(
                        t(
                            "draft_conflict_day_changed",
                            day=day_label(SchoolDay[day_name]),
                        )
                    )
            previous_unavailable = {
                cell_key
                for cell_key, cell in cells_by_key.items()
                if cell.state is RosterCellState.UNAVAILABLE
            }
            latest_unavailable = {
                cell_key
                for cell_key, cell in latest_cells.items()
                if cell.state is RosterCellState.UNAVAILABLE
            }
            for cell_key in pending_slots:
                if (cell_key in previous_unavailable) != (cell_key in latest_unavailable):
                    slot_cell = cells_by_key.get(cell_key)
                    slot_label = cell_key
                    if slot_cell is not None:
                        slot_row = next(
                            row_item
                            for row_item in presentation.rows
                            if row_item.spec.post == slot_cell.post
                            and row_item.spec.slot_index == slot_cell.slot_index
                        )
                        slot_label = f"{day_label(slot_cell.day)} · {slot_row.spec.display_label}"
                    changes.append(t("draft_conflict_slot_changed", cell=slot_label))
            edit_session.set_conflict(
                latest_version=int(latest_week["version"]),
                changes=changes,
            )
        reapply_control = conflict_reapply_ref["control"]
        if reapply_control is not None:
            if edit_session.conflict.latest_version is None:
                reapply_control.disable()
            else:
                reapply_control.enable()
        conflict_comparison.refresh()
        conflict_dialog.open()

    async def reapply_latest() -> None:
        if not edit_session.reapply_conflict():
            compare_latest()
            return
        conflict_dialog.close()
        await save_pending()

    with ui.dialog().props("persistent") as conflict_dialog, ui.card().classes(
        "sy-surface w-full max-w-lg p-6"
    ):
        ui.label(t("draft_conflict_preserved_title")).classes("text-lg font-semibold")
        ui.label(t("draft_conflict_preserved_body")).classes(
            "text-sm leading-6 text-[var(--sy-muted)] mt-2"
        )

        @ui.refreshable
        def conflict_comparison() -> None:
            ui.label(t("draft_conflict_comparison_title")).classes(
                "font-semibold mt-4"
            )
            changes = list(edit_session.conflict.changes)
            if not changes:
                ui.label(t("draft_conflict_no_overlap")).classes(
                    "text-sm leading-6 text-[var(--sy-muted)]"
                )
            else:
                with ui.element("ul").classes("list-disc pl-5 text-sm leading-6"):
                    for change in changes:
                        ui.label(str(change)).classes("list-item")

        conflict_comparison()
        with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5"):
            action(
                t("draft_conflict_keep_editing"),
                icon="arrow_back",
                on_click=conflict_dialog.close,
                variant="secondary",
            )
            conflict_reapply_ref["control"] = action(
                t("draft_conflict_reapply"),
                icon="difference",
                on_click=reapply_latest,
                variant="attention",
                disabled=edit_session.conflict.latest_version is None,
                test_id="draft-conflict-reapply",
            )
            action(
                t("draft_conflict_reload"),
                icon="refresh",
                on_click=reload_latest,
                variant="danger",
            )

    with ui.dialog() as discard_dialog, ui.card().classes("sy-surface w-full max-w-md p-6"):
        ui.label(t("draft_discard_confirm_title")).classes("text-lg font-semibold")
        ui.label(t("draft_discard_confirm_body")).classes(
            "text-sm leading-6 text-[var(--sy-muted)] mt-2"
        )
        with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5"):
            action(t("cancel"), icon="close", on_click=discard_dialog.close, variant="quiet")
            action(
                t("draft_discard_all"),
                icon="delete_sweep",
                on_click=discard_pending,
                variant="danger",
            )

    async def save_pending() -> None:
        cell_values, day_values, slot_values = edit_session.patch_edits()
        if not cell_values and not day_values and not slot_values:
            return
        expected_week_version = edit_session.reviewed_version
        reason = reason_state["value"].strip() or None
        command_id = edit_session.ensure_command_id()
        result = await _run_with_progress(
            lambda: workflow.apply_draft_patch(
                roster_week_id=roster_week_id,
                expected_week_version=expected_week_version,
                cell_edits=cell_values,
                day_edits=day_values,
                slot_edits=slot_values,
                reason=reason,
                command_id=command_id,
            ),
            title_key="progress_draft_change_title",
            working_key="progress_draft_change_working",
            icon="edit_note",
            on_conflict=compare_latest,
        )
        if result is not _OPERATION_FAILED:
            ui.notify(t("draft_batch_saved"), type="positive")
            ui.run_javascript("window.__syDraftDirty = false")
            ui.navigate.reload()

    def close_mobile_editor() -> None:
        cell_key = edit_session.selected_cell
        mobile_dialog_state["open"] = False
        dialog = cell_editor_dialog_ref["control"]
        if dialog is not None:
            dialog.close()
        edit_session.selected_cell = None
        refresh_editor()
        if cell_key:
            ui.run_javascript(
                "requestAnimationFrame(() => { const cell=[...document.querySelectorAll("
                f"'[data-cell-key=\"{attr(cell_key)}\"]'"
                ")].find(item => item.getClientRects().length && "
                "getComputedStyle(item).visibility !== 'hidden'); "
                "if (!cell) return; cell.focus({preventScroll: true}); "
                "cell.scrollIntoView({block: 'nearest', inline: 'nearest'}); })"
            )

    @ui.refreshable
    def editor() -> None:
        desktop_candidate_selector_ref["control"] = None
        mobile_candidate_selector_ref["control"] = None
        cell_editor_dialog_ref["control"] = None
        save_review_dialog_ref["control"] = None
        day_dialogs: dict[SchoolDay, Any] = {}
        visible_navigable_keys = [
            key
            for key in navigable_keys
            if not day_is_closed(cells_by_key[key].day)
        ]
        active_key = (
            edit_session.selected_cell
            if edit_session.selected_cell in visible_navigable_keys
            else (visible_navigable_keys[0] if visible_navigable_keys else None)
        )
        with ui.element("section").classes("sy-draft-editor").props(
            "data-testid=draft-grid-editor"
        ):
            ui.label(t("draft_schedule_title")).classes("text-xl font-semibold")
            ui.label(t("draft_schedule_intro")).classes(
                "text-sm leading-6 text-[var(--sy-muted)]"
            )
            ui.label(announcement_state["value"]).classes("sr-only").props(
                "role=status aria-live=polite aria-atomic=true "
                "data-testid=draft-grid-announcement"
            )
            if edit_session.move_source:
                ui.label(t("draft_move_choose_target")).classes(
                    "sy-draft-move-guidance text-sm font-semibold"
                ).props("role=status aria-live=polite")

            with ui.element("div").classes("sy-draft-grid-shell"):
                with ui.element("div").classes("sy-draft-grid-scroll"):
                    with ui.element("div").classes("sy-draft-grid-desktop").props(
                        'role="grid" aria-label="' + attr(t("draft_schedule_title")) + '"'
                    ):
                        with ui.element("div").classes("sy-draft-grid-corner").style(
                            "grid-column:1;grid-row:1"
                        ):
                            ui.label(t("duty_position"))
                        for day_index, day_item in enumerate(presentation.days, start=2):
                            day = day_item.day
                            effective_closed = day_is_closed(day)
                            with ui.element("div").classes("sy-draft-grid-day-head").style(
                                f"grid-column:{day_index};grid-row:1"
                            ):
                                ui.label(day_label(day)).classes("font-semibold")
                                if day_item.duty_date:
                                    ui.label(day_item.duty_date.strftime("%m/%d")).classes("text-xs")
                                day_action = action(
                                    t(
                                        "draft_day_reopen_action"
                                        if effective_closed
                                        else "draft_day_close_action"
                                    ),
                                    icon="event_available" if effective_closed else "event_busy",
                                    variant="quiet",
                                    classes="sy-draft-grid-day-action",
                                    test_id=f"draft-day-toggle-{day.name.lower()}",
                                )
                                affected = sum(
                                    1
                                    for row in presentation.rows
                                    for cell in row.cells
                                    if cell.day == day
                                    and cell.prefect_id
                                )
                                with ui.dialog() as day_dialog, ui.card().classes(
                                    "sy-surface w-full max-w-md p-6"
                                ):
                                    day_dialogs[day] = day_dialog
                                    ui.label(
                                        t(
                                            "draft_day_reopen_confirm_title"
                                            if effective_closed
                                            else "draft_day_close_confirm_title",
                                            day=day_label(day),
                                        )
                                    ).classes("text-lg font-semibold")
                                    ui.label(
                                        t(
                                            "draft_day_reopen_confirm_body"
                                            if effective_closed
                                            else "draft_day_close_confirm_body",
                                            day=day_label(day),
                                            count=affected,
                                        )
                                    ).classes("text-sm leading-6 text-[var(--sy-muted)] mt-2")
                                    with ui.row().classes(
                                        "sy-mobile-actions w-full justify-end gap-3 mt-5"
                                    ):
                                        action(
                                            t("cancel"),
                                            icon="close",
                                            on_click=day_dialog.close,
                                            variant="quiet",
                                        )

                                        def confirm_day_change(
                                            selected_day: SchoolDay = day,
                                            close_day: bool = not effective_closed,
                                            dialog: Any = day_dialog,
                                        ) -> None:
                                            dialog.close()
                                            stage_day(selected_day, close_day)

                                        action(
                                            t(
                                                "draft_day_reopen_action"
                                                if effective_closed
                                                else "draft_day_close_action"
                                            ),
                                            icon="event_available"
                                            if effective_closed
                                            else "event_busy",
                                            on_click=confirm_day_change,
                                            variant="attention",
                                            test_id=(
                                                "draft-day-confirm-reopen-"
                                                if effective_closed
                                                else "draft-day-confirm-close-"
                                            )
                                            + day.name.lower(),
                                        )
                                day_action.on_click(day_dialog.open)

                        for row_index, row in enumerate(presentation.rows, start=2):
                            with ui.element("div").classes("sy-draft-grid-row-head").style(
                                f"grid-column:1;grid-row:{row_index}"
                            ):
                                ui.label(row.spec.display_label).classes("font-semibold")
                                ui.label("–".join(row.spec.service_time)).classes("text-xs")
                            for day_index, cell in enumerate(row.cells, start=2):
                                if day_is_closed(cell.day):
                                    if row_index == 2:
                                        with ui.element("div").classes(
                                            "sy-draft-grid-day-closed"
                                        ).style(
                                            f"grid-column:{day_index};grid-row:2 / span {len(presentation.rows)}"
                                        ):
                                            ui.icon("event_busy").props("aria-hidden=true")
                                            ui.label(t("draft_day_closed")).classes("font-semibold")
                                            ui.label(day_label(cell.day)).classes("text-sm")
                                    continue
                                name, meta, state = cell_display(cell)
                                classes = f"sy-draft-grid-cell sy-draft-grid-cell--{state}"
                                if edit_session.selected_cell == cell.cell_key:
                                    classes += " sy-draft-grid-cell--selected"
                                if cell.cell_key in pending_cells:
                                    classes += " sy-draft-grid-cell--pending"
                                if cell.cell_key in pending_slots:
                                    classes += " sy-draft-grid-cell--pending"
                                if edit_session.move_source == cell.cell_key:
                                    classes += " sy-draft-grid-cell--move-source"
                                aria = f"{day_label(cell.day)}, {row.spec.display_label}, {name}"
                                interaction_props = (
                                    'role="gridcell" aria-disabled="true" tabindex="-1"'
                                    if state == "closed"
                                    else (
                                        'role="gridcell" tabindex="0"'
                                        if cell.cell_key == active_key
                                        else 'role="gridcell" tabindex="-1"'
                                    )
                                )
                                button = ui.element("button").classes(classes).style(
                                    f"grid-column:{day_index};grid-row:{row_index}"
                                ).props(
                                    f'type="button" aria-label="{attr(aria)}" '
                                    f'data-cell-key="{attr(cell.cell_key)}" '
                                    + interaction_props
                                )
                                with button:
                                    ui.label(name).classes("sy-draft-cell-name")
                                    if meta:
                                        ui.label(meta).classes("sy-draft-cell-meta")
                                if state != "closed":
                                    button.on(
                                        "click",
                                        lambda _event=None, key=cell.cell_key: open_cell_editor(key),
                                        js_handler=(
                                            "(event) => { if (window.__syDraftSuppressClick) { "
                                            "window.__syDraftSuppressClick = false; return; } emit({}); }"
                                        ),
                                    )
                                    button.on(
                                        "pointerdown",
                                        lambda _event=None: None,
                                        js_handler=(
                                            "(event) => { if (event.pointerType !== 'mouse') return; "
                                            "window.__syDraftPointerMove = { source: event.currentTarget.dataset.cellKey, "
                                            "x: event.clientX, y: event.clientY }; }"
                                        ),
                                    )
                                    button.on(
                                        "pointerup",
                                        handle_pointer_move,
                                        args=["source", "target"],
                                        js_handler=(
                                            "(event) => { const state = window.__syDraftPointerMove; "
                                            "window.__syDraftPointerMove = null; if (!state) return; "
                                            "const distance = Math.hypot(event.clientX - state.x, event.clientY - state.y); "
                                            "const target = event.currentTarget.dataset.cellKey; "
                                            "if (distance > 8 && state.source !== target) { "
                                            "window.__syDraftSuppressClick = true; emit({source: state.source, target}); } }"
                                        ),
                                    )
                                    button.on(
                                        "keydown",
                                        lambda event, key=cell.cell_key: handle_cell_key(event, key),
                                        args=["key"],
                                        js_handler=(
                                            "(event) => { if (['Enter', 'F2', 'Escape', ' ', 'ArrowUp', "
                                            "'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) { "
                                            "event.preventDefault(); event.stopPropagation(); "
                                            "emit({key: event.key}); } }"
                                        ),
                                    )

                def select_mobile_day(day_name: str) -> None:
                    mobile_day_state["value"] = day_name
                    refresh_editor()
                    ui.run_javascript(
                        "requestAnimationFrame(() => document.querySelector("
                        f"'[data-mobile-day-tab=\"{attr(day_name)}\"]'"
                        ")?.focus({preventScroll: true}))"
                    )

                def mobile_day_summary(day: SchoolDay) -> tuple[int, int, int, bool]:
                    cells = [
                        cell
                        for row in presentation.rows
                        for cell in row.cells
                        if cell.day == day and cell.cell_key
                    ]
                    keys = {cell.cell_key for cell in cells}
                    pending = (
                        len(keys.intersection(pending_cells))
                        + len(keys.intersection(pending_slots))
                        + int(day.name in pending_days)
                    )
                    closed_all_day = day_is_closed(day)
                    unavailable = sum(
                        1 for cell in cells if slot_is_unavailable(cell.cell_key)
                    )
                    vacancies = sum(
                        1
                        for cell in cells
                        if not slot_is_unavailable(cell.cell_key)
                        and cell_display(cell)[2] == "vacant"
                    )
                    return pending, vacancies, unavailable, closed_all_day

                def render_mobile_day(day_item: Any) -> None:
                    day = day_item.day
                    classes = "sy-draft-mobile-day"
                    if mobile_day_state["value"] == day.name:
                        classes += " sy-draft-mobile-day--selected"
                    with ui.element("section").classes(classes).props(
                        f'data-mobile-day="{attr(day.name)}" '
                        f'data-testid="draft-mobile-day-{attr(day.name.lower())}"'
                    ):
                        with ui.row().classes("w-full items-center justify-between gap-3"):
                            with ui.column().classes("gap-0"):
                                ui.label(day_label(day)).classes("font-semibold")
                                if day_item.duty_date:
                                    ui.label(day_item.duty_date.strftime("%Y-%m-%d")).classes(
                                        "text-xs text-[var(--sy-muted)]"
                                    )
                            action(
                                t(
                                    "draft_day_reopen_action"
                                    if day_is_closed(day)
                                    else "draft_day_close_action"
                                ),
                                icon="event_available" if day_is_closed(day) else "event_busy",
                                on_click=day_dialogs[day].open,
                                variant="quiet",
                            )
                        if day_is_closed(day):
                            ui.label(t("draft_day_closed")).classes(
                                "sy-fg-attention font-semibold py-4"
                            )
                            return
                        for row in presentation.rows:
                            cell = next(item for item in row.cells if item.day == day)
                            name, meta, state = cell_display(cell)
                            classes = f"sy-draft-mobile-cell sy-draft-mobile-cell--{state}"
                            if edit_session.selected_cell == cell.cell_key:
                                classes += " sy-draft-mobile-cell--selected"
                            if cell.cell_key in pending_cells or cell.cell_key in pending_slots:
                                classes += " sy-draft-mobile-cell--pending"
                            if edit_session.move_source == cell.cell_key:
                                classes += " sy-draft-mobile-cell--move-source"
                            interaction_props = (
                                'role="gridcell" aria-disabled="true" tabindex="-1"'
                                if state == "closed"
                                else 'role="gridcell" tabindex="0"'
                            )
                            button = ui.element("button").classes(classes).props(
                                f'type="button" aria-label="{attr(day_label(day) + ", " + row.spec.display_label + ", " + name)}" '
                                f'data-cell-key="{attr(cell.cell_key)}" '
                                + interaction_props
                            )
                            with button:
                                ui.label(row.spec.display_label).classes("text-sm font-semibold")
                                with ui.column().classes("gap-0"):
                                    ui.label(name).classes("sy-draft-cell-name")
                                    if meta:
                                        ui.label(meta).classes("sy-draft-cell-meta")
                            if state != "closed":
                                button.on(
                                    "click",
                                    lambda _event=None, key=cell.cell_key: open_cell_editor(
                                        key, compact=True
                                    ),
                                )
                                button.on(
                                    "keydown",
                                    lambda event, key=cell.cell_key: handle_cell_key(event, key),
                                    args=["key", "compact"],
                                    js_handler=(
                                        "(event) => { if (['Enter', 'F2', 'Escape', ' ', 'ArrowUp', "
                                        "'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) { "
                                        "event.preventDefault(); event.stopPropagation(); "
                                        "emit({key: event.key, compact: true}); } }"
                                    ),
                                )

                ui.label(t("draft_grid_mobile_notice")).classes(
                    "sy-draft-mobile-notice text-xs leading-5 text-[var(--sy-muted)] px-1"
                )
                with ui.element("div").classes("sy-draft-mobile-view"):
                    with ui.element("nav").classes("sy-draft-mobile-day-tabs").props(
                        f'aria-label="{attr(t("draft_preview"))}" data-testid=draft-mobile-day-tabs'
                    ):
                        for day_item in presentation.days:
                            day = day_item.day
                            pending, vacancies, unavailable, closed_all_day = (
                                mobile_day_summary(day)
                            )
                            classes = "sy-draft-mobile-day-tab"
                            if mobile_day_state["value"] == day.name:
                                classes += " sy-draft-mobile-day-tab--active"
                            summary = (
                                t("draft_mobile_day_closed_summary", pending=pending)
                                if closed_all_day
                                else t(
                                    "draft_mobile_day_summary",
                                    pending=pending,
                                    vacancies=vacancies,
                                    unavailable=unavailable,
                                )
                            )
                            tab = ui.button(
                                on_click=lambda day_name=day.name: select_mobile_day(day_name),
                            ).classes(classes).props(
                                f'flat no-caps data-mobile-day-tab="{attr(day.name)}" '
                                f'aria-label="{attr(day_label(day) + ", " + summary)}" '
                                f'aria-current={"page" if mobile_day_state["value"] == day.name else "false"}'
                            )
                            with tab:
                                ui.label(day_label(day)).classes(
                                    "sy-draft-mobile-day-tab-title"
                                )
                                ui.label(summary).classes(
                                    "sy-draft-mobile-day-tab-summary"
                                )
                    for day_item in presentation.days:
                        render_mobile_day(day_item)

            with ui.element("div").classes(
                "sy-draft-editor-panel sy-draft-editor-panel--desktop"
            ):
                key = edit_session.selected_cell
                if not key:
                    ui.label(t("draft_select_cell")).classes("font-semibold")
                    ui.label(t("draft_candidate_search_hint")).classes(
                        "text-sm leading-6 text-[var(--sy-muted)]"
                    )
                else:
                    cell = cells_by_key[key]
                    row = next(
                        item
                        for item in presentation.rows
                        if item.spec.post == cell.post and item.spec.slot_index == cell.slot_index
                    )
                    ui.label(
                        t(
                            "draft_selected_cell",
                            cell=f"{day_label(cell.day)} · {row.spec.display_label}",
                        )
                    ).classes("font-semibold")
                    if slot_is_unavailable(key):
                        ui.label(t("draft_slot_unavailable_body")).classes(
                            "text-sm leading-6 text-[var(--sy-muted)]"
                        )
                        action(
                            t("draft_slot_reopen_action"),
                            icon="event_available",
                            on_click=lambda cell_key=key: stage_slot(cell_key, False),
                            variant="secondary",
                            test_id="draft-slot-reopen",
                        )
                    else:
                        candidates = load_candidates(cell)
                        options: dict[str, str] = {
                            "__vacant__": t("draft_explicit_vacancy")
                        }
                        if cell.prefect_id:
                            options[str(cell.prefect_id)] = (
                                f"{cell.prefect_name} · {t('draft_current_assignment')}"
                            )
                        for candidate in candidates or []:
                            swap_suffix = (
                                f" · {t('draft_candidate_swap_suffix')}"
                                if candidate.get("requiresSwap")
                                else ""
                            )
                            options[str(candidate["id"])] = (
                                f"{candidate['nameZh']} ({candidate['form']} {candidate['className']})"
                                f"{swap_suffix}"
                            )
                        selected_value: str | None
                        if key in pending_cells:
                            selected_value = pending_cells[key] or "__vacant__"
                        else:
                            selected_value = str(cell.prefect_id) if cell.prefect_id else None
                        selector = ui.select(
                            label=t("draft_candidate_search"),
                            options=options,
                            value=selected_value,
                            with_input=True,
                            clearable=True,
                            on_change=lambda event, cell_key=key: stage_candidate(
                                cell_key, event.value
                            ),
                        ).classes("w-full").props(
                            "use-input input-debounce=0 "
                            "data-testid=draft-candidate-search "
                            f'data-cell-key="{attr(key)}"'
                        )
                        desktop_candidate_selector_ref["control"] = selector
                        if candidates is None:
                            selector.disable()
                            ui.label(t("draft_candidate_unavailable")).classes(
                                "sy-fg-attention text-sm leading-6"
                            )
                        ui.label(t("draft_candidate_search_hint")).classes(
                            "text-xs leading-5 text-[var(--sy-muted)]"
                        )
                        with ui.row().classes("sy-mobile-actions gap-2 flex-wrap"):
                            effective_prefect = pending_cells.get(
                                key, original_assignments.get(key)
                            )
                            action(
                                t("draft_move_cancel")
                                if edit_session.move_source == key
                                else t("draft_move_start"),
                                icon="close" if edit_session.move_source == key else "open_with",
                                on_click=lambda cell_key=key: toggle_move_source(cell_key),
                                variant="quiet",
                                disabled=effective_prefect is None,
                                test_id="draft-move-start",
                            )
                            action(
                                t("draft_slot_unavailable_action"),
                                icon="block",
                                on_click=lambda cell_key=key: stage_slot(cell_key, True),
                                variant="attention",
                                test_id="draft-slot-unavailable",
                            )

                ui.textarea(
                    label=t("draft_batch_reason"),
                    value=reason_state["value"],
                    on_change=lambda event: reason_state.__setitem__(
                        "value", str(event.value or "")
                    ),
                ).props("name=draft-batch-reason autocomplete=off").classes("w-full")

            with ui.dialog(value=mobile_dialog_state["open"]).props(
                "persistent"
            ) as cell_editor_dialog, ui.card().classes(
                "sy-surface sy-draft-editor-sheet"
            ) as cell_editor_sheet:
                cell_editor_dialog_ref["control"] = cell_editor_dialog
                with ui.element("div").classes("sy-draft-editor-sheet-header"):
                    ui.label(t("draft_select_cell")).classes("font-semibold")
                    action(
                        t("close"),
                        icon="close",
                        on_click=close_mobile_editor,
                        variant="quiet",
                        test_id="draft-mobile-editor-close",
                    )
                key = edit_session.selected_cell
                if key:
                    cell = cells_by_key[key]
                    row = next(
                        item
                        for item in presentation.rows
                        if item.spec.post == cell.post and item.spec.slot_index == cell.slot_index
                    )
                    ui.label(
                        t(
                            "draft_selected_cell",
                            cell=f"{day_label(cell.day)} · {row.spec.display_label}",
                        )
                    ).classes("text-lg font-semibold")
                    if slot_is_unavailable(key):
                        ui.label(t("draft_slot_unavailable_body")).classes(
                            "text-sm leading-6 text-[var(--sy-muted)]"
                        )
                        action(
                            t("draft_slot_reopen_action"),
                            icon="event_available",
                            on_click=lambda cell_key=key: stage_slot(cell_key, False),
                            variant="secondary",
                            test_id="draft-slot-reopen-mobile",
                        )
                    else:
                        candidates = load_candidates(cell)
                        options: dict[str, str] = {
                            "__vacant__": t("draft_explicit_vacancy")
                        }
                        if cell.prefect_id:
                            options[str(cell.prefect_id)] = (
                                f"{cell.prefect_name} · {t('draft_current_assignment')}"
                            )
                        for candidate in candidates or []:
                            swap_suffix = (
                                f" · {t('draft_candidate_swap_suffix')}"
                                if candidate.get("requiresSwap")
                                else ""
                            )
                            options[str(candidate["id"])] = (
                                f"{candidate['nameZh']} ({candidate['form']} {candidate['className']})"
                                f"{swap_suffix}"
                            )
                        selected_value = (
                            pending_cells[key] or "__vacant__"
                            if key in pending_cells
                            else str(cell.prefect_id) if cell.prefect_id else None
                        )
                        selector = ui.select(
                            label=t("draft_candidate_search"),
                            options=options,
                            value=selected_value,
                            with_input=True,
                            clearable=True,
                            on_change=lambda event, cell_key=key: stage_candidate(
                                cell_key, event.value
                            ),
                        ).classes("w-full").props(
                            "use-input input-debounce=0 "
                            "data-testid=draft-candidate-search-mobile "
                            f'data-cell-key="{attr(key)}"'
                        )
                        mobile_candidate_selector_ref["control"] = selector
                        if candidates is None:
                            selector.disable()
                            ui.label(t("draft_candidate_unavailable")).classes(
                                "sy-fg-attention text-sm leading-6"
                            )
                        ui.label(t("draft_candidate_search_hint")).classes(
                            "text-xs leading-5 text-[var(--sy-muted)]"
                        )
                        with ui.row().classes("sy-mobile-actions gap-2 flex-wrap"):
                            effective_prefect = pending_cells.get(
                                key, original_assignments.get(key)
                            )
                            action(
                                t("draft_move_cancel")
                                if edit_session.move_source == key
                                else t("draft_move_start"),
                                icon="close" if edit_session.move_source == key else "open_with",
                                on_click=lambda cell_key=key: toggle_move_source(cell_key),
                                variant="quiet",
                                disabled=effective_prefect is None,
                                test_id="draft-move-start-mobile",
                            )
                            action(
                                t("draft_slot_unavailable_action"),
                                icon="block",
                                on_click=lambda cell_key=key: stage_slot(cell_key, True),
                                variant="attention",
                                test_id="draft-slot-unavailable-mobile",
                            )
                cell_editor_sheet.on(
                    "keydown",
                    lambda _event=None: close_mobile_editor(),
                    args=["key"],
                    js_handler=(
                        "(event) => { if (event.key === 'Escape') { "
                        "event.preventDefault(); event.stopPropagation(); emit({key: event.key}); } }"
                    ),
                )

            count = pending_count()
            ui.run_javascript(
                f"window.__syDraftDirty = {'true' if count else 'false'}"
            )
            with ui.element("div").classes(
                "sy-draft-pending-bar sy-draft-pending-bar--desktop"
            ).props(
                "aria-live=polite data-testid=draft-pending-bar"
            ):
                with ui.column().classes("gap-0"):
                    ui.label(
                        t("draft_pending_count", count=count)
                        if count
                        else t("draft_pending_none")
                    ).classes("font-semibold")
                    ui.label(t("draft_undo_hint")).classes(
                        "text-xs text-[var(--sy-muted)]"
                    )
                with ui.row().classes("sy-mobile-actions gap-2 flex-wrap"):
                    action(
                        t("draft_undo"),
                        icon="undo",
                        on_click=undo_pending,
                        variant="quiet",
                        disabled=not edit_session.can_undo,
                        test_id="draft-undo",
                    )
                    action(
                        t("draft_redo"),
                        icon="redo",
                        on_click=redo_pending,
                        variant="quiet",
                        disabled=not edit_session.can_redo,
                        test_id="draft-redo",
                    )
                    action(
                        t("draft_discard_all"),
                        icon="delete_sweep",
                        on_click=discard_dialog.open,
                        variant="secondary",
                        disabled=not count,
                    )
                    action(
                        t("draft_save_all"),
                        icon="save",
                        on_click=save_pending,
                        disabled=not count,
                        test_id="draft-save-all",
                    )

            with ui.dialog().props("persistent") as save_review_dialog, ui.card().classes(
                "sy-surface sy-draft-editor-sheet"
            ):
                save_review_dialog_ref["control"] = save_review_dialog
                with ui.element("div").classes("sy-draft-editor-sheet-header"):
                    ui.label(t("draft_save_all")).classes("font-semibold")
                    action(
                        t("close"),
                        icon="close",
                        on_click=save_review_dialog.close,
                        variant="quiet",
                        test_id="draft-mobile-save-close",
                    )
                ui.label(t("draft_pending_count", count=count)).classes(
                    "text-lg font-semibold"
                )
                ui.label(t("draft_undo_hint")).classes(
                    "text-sm leading-6 text-[var(--sy-muted)]"
                )
                ui.textarea(
                    label=t("draft_batch_reason"),
                    value=reason_state["value"],
                    on_change=lambda event: reason_state.__setitem__(
                        "value", str(event.value or "")
                    ),
                ).props(
                    "name=draft-mobile-batch-reason autocomplete=off"
                ).classes("w-full")

                async def save_from_mobile() -> None:
                    save_review_dialog.close()
                    await save_pending()

                with ui.row().classes("sy-mobile-actions w-full justify-end gap-2"):
                    action(
                        t("cancel"),
                        icon="close",
                        on_click=save_review_dialog.close,
                        variant="quiet",
                    )
                    action(
                        t("draft_save_all"),
                        icon="save",
                        on_click=save_from_mobile,
                        disabled=not count,
                        test_id="draft-save-all-mobile-confirm",
                    )

            mobile_dock_classes = "sy-draft-mobile-save-dock"
            if not count:
                mobile_dock_classes += " sy-draft-mobile-save-dock--empty"
            with ui.element("div").classes(mobile_dock_classes).props(
                "aria-live=polite data-testid=draft-mobile-save-dock"
            ):
                with ui.column().classes("gap-0 min-w-0"):
                    ui.label(
                        t("draft_pending_count", count=count)
                        if count
                        else t("draft_pending_none")
                    ).classes("font-semibold")
                    ui.label(t("draft_undo_hint")).classes(
                        "text-xs text-[var(--sy-muted)]"
                    )
                with ui.row().classes("sy-mobile-actions gap-2 flex-wrap"):
                    action(
                        t("draft_undo"),
                        icon="undo",
                        on_click=undo_pending,
                        variant="quiet",
                        disabled=not edit_session.can_undo,
                        test_id="draft-undo-mobile",
                    )
                    action(
                        t("draft_save_all"),
                        icon="save",
                        on_click=save_review_dialog.open,
                        disabled=not count,
                        test_id="draft-save-all-mobile",
                    )

    def refresh_editor() -> None:
        editor.refresh()

    def handle_undo_key(event: Any) -> None:
        if not event.action.keydown or event.action.repeat:
            return
        key_name = event.key.name.lower()
        if (
            key_name == "z"
            and (event.modifiers.ctrl or event.modifiers.meta)
            and event.modifiers.shift
        ):
            redo_pending()
        elif key_name == "y" and (event.modifiers.ctrl or event.modifiers.meta):
            redo_pending()
        elif key_name == "z" and (event.modifiers.ctrl or event.modifiers.meta):
            undo_pending()
        elif key_name in {"f2", "enter"} and edit_session.selected_cell is not None:
            selector_ref = (
                mobile_candidate_selector_ref
                if mobile_dialog_state["open"]
                else desktop_candidate_selector_ref
            )
            selector = selector_ref["control"]
            if selector is not None:
                selector.run_method("focus")
        elif key_name == "escape" and edit_session.selected_cell is not None:
            mobile_dialog_state["open"] = False
            edit_session.selected_cell = None
            refresh_editor()

    ui.keyboard(
        on_key=handle_undo_key,
        repeating=False,
        ignore=["input", "select", "textarea"],
    )
    ui.run_javascript(
        """
        window.__syDraftBeforeUnloadCleanup?.();
        window.__syDraftDirty = false;
        const beforeUnload = (event) => {
          if (!window.__syDraftDirty) return;
          event.preventDefault();
          event.returnValue = '';
        };
        const cleanupBeforeUnload = () => {
          window.removeEventListener('beforeunload', beforeUnload);
          window.removeEventListener('pagehide', cleanupBeforeUnload);
          window.__syDraftDirty = false;
          if (window.__syDraftBeforeUnload === beforeUnload) {
            delete window.__syDraftBeforeUnload;
            delete window.__syDraftBeforeUnloadCleanup;
          }
        };
        window.__syDraftBeforeUnload = beforeUnload;
        window.__syDraftBeforeUnloadCleanup = cleanupBeforeUnload;
        window.addEventListener('beforeunload', beforeUnload);
        window.addEventListener('pagehide', cleanupBeforeUnload, {once: true});
        """
    )
    editor()


def _roster_workflow_steps(
    *,
    roster_week_id: int | None = None,
    status: str | None = None,
) -> tuple[WorkflowStep, ...]:
    detail_route = f"/rosters/{roster_week_id}" if roster_week_id is not None else "/rosters"
    adjustment_route = (
        f"/rosters/{roster_week_id}/adjustments"
        if roster_week_id is not None and status == "published"
        else detail_route
    )
    return (
        WorkflowStep(t("roster_workflow_generate"), "/rosters", "edit_calendar"),
        WorkflowStep(
            t("roster_workflow_review"),
            detail_route,
            "fact_check",
            "available" if roster_week_id is not None else "locked",
        ),
        WorkflowStep(
            t("roster_workflow_adjust"),
            adjustment_route,
            "event_busy",
            "available" if roster_week_id is not None and status == "published" else "locked",
        ),
        WorkflowStep(t("roster_workflow_history"), "/rosters/history", "history"),
    )


def _render_withdraw_action(workflow, week: dict[str, object], roster_week_id: int) -> None:
    """Render the same audited withdrawal action wherever a published week appears."""

    reviewed_version = int(week["version"])
    withdrawal_command_id = f"roster-withdraw-ui:{uuid4().hex}"
    with ui.dialog().props("persistent") as withdraw_dialog, ui.card().classes(
        "sy-surface w-full max-w-lg p-6"
    ):
        with ui.row().classes("items-start gap-3 no-wrap"):
            ui.icon("warning_amber").classes("sy-fg-danger text-2xl").props("aria-hidden=true")
            with ui.column().classes("gap-1 min-w-0"):
                ui.label(t("withdraw_roster_title")).classes("text-xl font-semibold")
                ui.label(t("withdraw_roster_body")).classes("text-sm leading-6 text-[var(--sy-muted)]")
        with ui.element("section").classes("sy-surface-subtle w-full p-4 mt-4"):
            for key in (
                "withdraw_roster_consequence_fairness",
                "withdraw_roster_consequence_share",
                "withdraw_roster_consequence_audit",
            ):
                with ui.row().classes("items-start gap-2 no-wrap"):
                    ui.icon("check_circle_outline").classes("sy-fg-attention mt-1").props("aria-hidden=true")
                    ui.label(t(key)).classes("text-sm leading-6")
        withdraw_reason = ui.textarea(label=t("withdraw_roster_reason")).props(
            "name=withdraw-roster-reason autocomplete=off data-testid=withdraw-roster-reason"
        ).classes("w-full mt-4")
        withdraw_week = ui.input(
            label=t("withdraw_roster_confirm_week", week=week["weekStart"])
        ).props("autocomplete=off data-testid=withdraw-roster-week-confirmation").classes("w-full")

        async def withdraw_roster() -> None:
            reason = str(withdraw_reason.value or "").strip()
            confirmation = str(withdraw_week.value or "").strip()
            if confirmation != str(week["weekStart"]):
                ui.notify(t("withdraw_roster_week_required", week=week["weekStart"]), type="warning")
                withdraw_week.run_method("focus")
                return
            withdraw_dialog.close()
            result = await _run_with_progress(
                lambda: workflow.withdraw_published_roster(
                    roster_week_id=roster_week_id,
                    expected_version=reviewed_version,
                    reason=reason,
                    command_id=withdrawal_command_id,
                ),
                title_key="progress_withdraw_title",
                working_key="progress_withdraw_working",
                icon="undo",
            )
            if result is _OPERATION_FAILED:
                return
            if result.share_ids_to_revoke:
                revocation = await _run_with_progress(
                    lambda: revoke_roster_shares(workflow, result.share_ids_to_revoke),
                    title_key="progress_share_revoke_title",
                    working_key="progress_share_revoke_working",
                    icon="link_off",
                )
                if revocation is _OPERATION_FAILED or revocation[1]:
                    ui.notify(t("withdraw_roster_share_pending"), type="warning")
            ui.notify(t("withdraw_roster_success"), type="positive")
            ui.navigate.reload()

        with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5"):
            ui.button(t("cancel"), icon="close", on_click=withdraw_dialog.close).props("flat")
            ui.button(
                t("withdraw_roster_confirm_action"),
                icon="undo",
                on_click=withdraw_roster,
            ).props("color=negative data-testid=confirm-withdraw-roster")
    ui.button(
        t("withdraw_roster_action"),
        icon="undo",
        on_click=withdraw_dialog.open,
    ).props("outline color=negative data-testid=withdraw-published-roster")

@ui.page("/rosters")
def rosters_page() -> None:
    _install_roster_mobile_styles()
    ui.run_javascript(
        "if (window.location.hash === '#roster-history') "
        "window.location.replace('/rosters/history')"
    )
    workflow = get_workflow()
    prefects = workflow.prefects()
    with page_shell("/rosters"):
        if not prefects:
            with ui.element("section").classes("sy-empty-state sy-empty-state--illustrated w-full").props(
                "data-testid=roster-requires-directory role=status"
            ):
                ui.icon("groups").classes("sy-empty-state-icon").props("aria-hidden=true")
                ui.label(t("roster_requires_directory_title")).classes("text-xl font-semibold")
                ui.label(t("roster_requires_directory_detail")).classes(
                    "text-sm leading-6 text-[var(--sy-muted)] max-w-2xl text-center"
                )
                ui.button(
                    t("roster_requires_directory_action"),
                    icon="group_add",
                    on_click=lambda: _navigate_with_feedback("/prefects"),
                ).props("color=primary data-testid=roster-open-prefects")
            return
        _render_storage_lifecycle(workflow)
        latest_week = workflow.latest_roster_week()
        render_workflow_navigation(
            _roster_workflow_steps(
                roster_week_id=int(latest_week["id"]) if latest_week else None,
                status=str(latest_week["status"]) if latest_week else None,
            ),
            current_index=1,
            label=t("roster_workflow_label"),
        )
        with ui.tabs().classes("w-full sy-fg-action") as tabs:
            generate_tab = ui.tab("generate_view", label=t("generate_view"), icon="calendar_month")
            adjust_tab = ui.tab("adjust_edit", label=t("adjust_edit"), icon="edit_calendar")
        with ui.tab_panels(tabs, value="generate_view", animated=False, keep_alive=False).classes("w-full bg-transparent"):
            with ui.tab_panel("generate_view").classes("px-0"):
                with ui.card().classes(
                    "sy-surface sy-operations-panel sy-roster-generation-card w-full p-6"
                ):
                    ui.html(t("generate_roster"), tag="h2").classes("text-lg font-semibold")
                    _render_operation_hint("hint_generate_roster", icon="calendar_month")
                    week_input = ui.input(label=t("week_start"), value=_next_monday().isoformat()).props(
                        "type=date name=week-start autocomplete=off"
                    ).classes("sy-roster-step-week")
                    try:
                        initial_week = date.fromisoformat(str(week_input.value))
                    except ValueError:
                        initial_week = _next_monday()
                    selected_week_state: dict[str, object] = {
                        "week_start": initial_week,
                        "record": workflow.roster_week_for_start(initial_week),
                    }

                    def selected_week_record(
                        selected: date | None,
                        *,
                        refresh: bool = False,
                    ) -> dict[str, object] | None:
                        if selected is None:
                            return None
                        if refresh or selected_week_state["week_start"] != selected:
                            selected_week_state["week_start"] = selected
                            selected_week_state["record"] = workflow.roster_week_for_start(
                                selected
                            )
                        record = selected_week_state["record"]
                        return record if isinstance(record, dict) else None

                    initial_record = selected_week_record(initial_week)
                    initial_assist_mode = _assist_assignment_mode_code(
                        initial_record.get("assistAssignmentMode") if initial_record else None,
                        fallback=LEGACY_FIXED_WEEKDAY,
                    )
                    with ui.element("section").classes(
                        "sy-surface-subtle sy-policy-panel sy-roster-step-availability w-full p-4 mt-4"
                    ).props("data-testid=pre-generation-day-closure-panel"):
                        ui.label(t("pre_generation_day_closure")).classes("font-semibold")
                        ui.label(t("pre_generation_day_closure_detail")).classes(
                            "text-sm leading-6 text-[var(--sy-muted)] mt-1"
                        )
                        day_closure_select = ui.select(
                            options={day.name: day_label(day) for day in SchoolDay},
                            value=list(
                                (
                                    day.name if isinstance(day, SchoolDay) else str(day)
                                    for day in (
                                        initial_record.get("closedDays", ())
                                        if initial_record
                                        else ()
                                    )
                                )
                            ),
                            multiple=True,
                        ).props(
                            "use-chips clearable data-testid=pre-generation-day-closures"
                        ).classes("w-full mt-3")
                    def toggle_mobile_rules() -> None:
                        ui.run_javascript(
                            "const card=document.querySelector('.sy-roster-generation-card');"
                            "const trigger=document.querySelector('[data-testid=roster-mobile-rules-toggle]');"
                            "if(!card||!trigger)return;"
                            "const open=card.classList.toggle('sy-roster-rules-open');"
                            "trigger.setAttribute('aria-expanded', String(open));"
                        )

                    action(
                        f"{t('assist_assignment_mode_title')} · {t('history_priority_title')}",
                        icon="tune",
                        on_click=toggle_mobile_rules,
                        variant="secondary",
                        classes="sy-roster-rules-toggle",
                        test_id="roster-mobile-rules-toggle",
                    ).props(
                        "aria-expanded=false "
                        "aria-controls=assist-mode-rules history-priority-rules"
                    )

                    with ui.element("section").classes(
                        "sy-surface-subtle sy-policy-panel sy-roster-step-rules w-full p-4 mt-4"
                    ).props(
                        "id=assist-mode-rules data-testid=assist-assignment-mode-panel "
                        "data-sy-ambient-light=true"
                    ):
                        ui.label(t("assist_assignment_mode_title")).classes("font-semibold")
                        ui.label(t("assist_assignment_mode_detail")).classes(
                            "text-sm leading-6 text-[var(--sy-muted)] mt-1"
                        )
                        assist_assignment_mode = ui.select(
                            label=t("assist_assignment_mode_label"),
                            options={
                                LEGACY_FIXED_WEEKDAY: t("assist_assignment_mode_legacy"),
                                FLEXIBLE_WEEKLY: t("assist_assignment_mode_flexible"),
                            },
                            value=initial_assist_mode,
                        ).props(
                            "data-testid=assist-assignment-mode "
                            "aria-describedby=assist-mode-description"
                        ).classes("w-full mt-3")
                        assist_mode_explanation = ui.label(
                            t(_ASSIST_MODE_DETAIL_KEYS[initial_assist_mode])
                        ).props(
                            "id=assist-mode-description aria-live=polite"
                        ).classes("text-sm leading-6 text-[var(--sy-muted)]")
                        ui.label(t("assist_assignment_mode_constraints")).classes(
                            "text-xs leading-5 text-[var(--sy-muted)]"
                        )

                    def update_assist_mode_explanation(value: object) -> None:
                        mode = _assist_assignment_mode_code(value, fallback=LEGACY_FIXED_WEEKDAY)
                        assist_mode_explanation.set_text(t(_ASSIST_MODE_DETAIL_KEYS[mode]))

                    assist_assignment_mode.on_value_change(
                        lambda event: update_assist_mode_explanation(event.value)
                    )
                    with ui.element("section").classes(
                        "sy-surface-subtle sy-policy-panel sy-roster-step-rules w-full p-4 mt-4"
                    ).props(
                        "id=history-priority-rules data-sy-ambient-light=true"
                    ):
                        ui.label(t("history_priority_title")).classes("font-semibold")
                        ui.label(t("history_priority_detail")).classes(
                            "text-sm leading-6 text-[var(--sy-muted)] mt-1"
                        )
                        initial_multiplier = float(
                            initial_record.get("historyPriorityMultiplier", 1.0)
                            if initial_record
                            else 1.0
                        )
                        history_priority = ui.slider(
                            min=HISTORY_PRIORITY_MULTIPLIER_MIN,
                            max=HISTORY_PRIORITY_MULTIPLIER_MAX,
                            step=0.1,
                            value=initial_multiplier,
                        ).props(
                            f'label label-always snap data-testid=history-priority-multiplier '
                            f'aria-label="{attr(t("history_priority_label"))}"'
                        ).classes("w-full mt-3")
                        with ui.element("div").classes("sy-history-scale w-full").props(
                            f'role=img aria-label="{attr(t("history_priority_scale"))}"'
                        ):
                            for value, position in (
                                ("0.8", "0%"),
                                ("1.0", "16.6667%"),
                                ("2.0", "100%"),
                            ):
                                with ui.element("span").classes("sy-history-scale-mark").style(
                                    f"left: {position}"
                                ).props(f"data-value={value}"):
                                    ui.label(value).classes("sy-history-scale-value")
                                    ui.element("i").classes("sy-history-scale-tick").props("aria-hidden=true")
                            ui.label(t("history_priority_scale_detail")).classes("sy-history-scale-help")

                        chart_dark = current_theme() == "dark"
                        chart_text = "#F5F5F7" if chart_dark else "#30343A"
                        chart_muted = "#C5C7CA" if chart_dark else "#59686D"
                        chart_line = "rgba(235,235,245,.16)" if chart_dark else "rgba(60,60,67,.14)"
                        chart_action = "#9BC2D2" if chart_dark else "#35647C"
                        chart_neutral = "#7ED7C4" if chart_dark else "#0F766E"
                        history_priority_chart = ui.echart(
                            {
                                "animationDuration": 220,
                                "animationDurationUpdate": 180,
                                "textStyle": {"color": chart_text},
                                "aria": {
                                    "enabled": True,
                                    "label": {
                                        "description": t(
                                            "history_priority_chart_aria",
                                            value=f"{initial_multiplier:.1f}",
                                        )
                                    },
                                },
                                "grid": {"left": 8, "right": 48, "top": 8, "bottom": 4, "containLabel": True},
                                "xAxis": {
                                    "type": "value",
                                    "min": 0,
                                    "max": 2.0,
                                    "axisLabel": {"color": chart_muted, "formatter": "{value}×"},
                                    "axisLine": {"lineStyle": {"color": chart_line}},
                                    "splitLine": {"lineStyle": {"color": chart_line}},
                                },
                                "yAxis": {
                                    "type": "category",
                                    "data": [
                                        t("history_priority_history_factor"),
                                        t("history_priority_week_factor"),
                                    ],
                                    "axisLabel": {"color": chart_muted},
                                    "axisLine": {"show": False},
                                    "axisTick": {"show": False},
                                },
                                "series": [
                                    {
                                        "type": "bar",
                                        "barWidth": 18,
                                        "data": [
                                            {"value": initial_multiplier, "itemStyle": {"color": chart_action}},
                                            {"value": 1.0, "itemStyle": {"color": chart_neutral}},
                                        ],
                                        "label": {
                                            "show": True,
                                            "position": "right",
                                            "color": chart_text,
                                            "formatter": "{c}×",
                                        },
                                        "itemStyle": {"borderRadius": [0, 7, 7, 0]},
                                    }
                                ],
                            }
                        ).classes(
                            "sy-history-priority-chart sy-roster-advanced-chart w-full"
                        ).props(
                            f'role=img aria-label="{attr(t("history_priority_chart"))}" '
                            'data-testid=history-priority-chart'
                        )
                        ui.label(t("history_priority_chart_detail")).classes(
                            "sy-history-priority-chart-note sy-roster-advanced-chart"
                        )

                    def update_history_priority_chart(value: float) -> None:
                        normalized = min(
                            max(float(value), HISTORY_PRIORITY_MULTIPLIER_MIN),
                            HISTORY_PRIORITY_MULTIPLIER_MAX,
                        )
                        history_priority_chart.options["series"][0]["data"][0]["value"] = normalized
                        history_priority_chart.options["aria"]["label"]["description"] = t(
                            "history_priority_chart_aria",
                            value=f"{normalized:.1f}",
                        )
                        history_priority_chart.update()

                    history_priority.on_value_change(
                        lambda event: update_history_priority_chart(float(event.value))
                    )

                    def refresh_history_priority() -> None:
                        selected = selected_week_start()
                        record = selected_week_record(selected)
                        history_priority.value = float(
                            record.get("historyPriorityMultiplier", 1.0)
                            if record
                            else 1.0
                        )
                        history_priority.update()
                        update_history_priority_chart(float(history_priority.value or 1.0))

                    def selected_week_start(*, announce_error: bool = False) -> date | None:
                        try:
                            selected = date.fromisoformat(str(week_input.value or ""))
                        except ValueError:
                            if announce_error:
                                ui.notify(t("week_start_invalid"), type="warning")
                                week_input.run_method("focus")
                            return None
                        try:
                            workflow.validate_week_start(selected)
                        except WorkflowError:
                            if announce_error:
                                ui.notify(t("week_start_monday_required"), type="warning")
                                week_input.run_method("focus")
                            return None
                        return selected

                    def refresh_assist_assignment_mode() -> None:
                        selected = selected_week_start()
                        record = selected_week_record(selected)
                        mode = _assist_assignment_mode_code(
                            record.get("assistAssignmentMode") if record else None,
                            fallback=LEGACY_FIXED_WEEKDAY,
                        )
                        assist_assignment_mode.value = mode
                        assist_assignment_mode.update()
                        update_assist_mode_explanation(mode)

                    def refresh_day_closures() -> None:
                        selected = selected_week_start()
                        record = selected_week_record(selected)
                        day_closure_select.value = list(
                            day.name if isinstance(day, SchoolDay) else str(day)
                            for day in (
                                record.get("closedDays", ()) if record else ()
                            )
                        )
                        day_closure_select.update()

                    requirements_area = ui.column().classes(
                        "sy-roster-step-readiness w-full gap-2 mt-4"
                    )
                    requirements_state: dict[str, tuple[str, tuple[str, ...]] | None] = {
                        "rendered_key": None
                    }

                    def refresh_requirements() -> None:
                        week_start = selected_week_start()
                        if week_start is None:
                            requirements_state["rendered_key"] = None
                            requirements_area.clear()
                            return
                        query_key = _generation_requirements_query_key(
                            week_start,
                            day_closure_select.value,
                        )
                        if requirements_state["rendered_key"] == query_key:
                            return
                        requirements_area.clear()
                        requirements = _safe_read_action(
                            lambda: workflow.generation_requirements(
                                week_start,
                                closed_days=tuple(day_closure_select.value or ()),
                            ),
                            action_name="load_generation_requirements",
                        )
                        if requirements is None:
                            return
                        requirements_state["rendered_key"] = query_key
                        with requirements_area:
                            with ui.expansion(t("generation_requirements"), icon="assignment_late").classes("w-full"):
                                ui.label(t("generation_requirements_notice")).classes("p-4 pb-1 text-sm text-[var(--sy-muted)]")
                                rows = [
                                    {
                                        "id": index,
                                        "day": day_label(item["day"]),
                                        "post": roster_display_label(
                                            str(item["postCode"]),
                                            int(item.get("slotIndex", 1)),
                                        ),
                                        "slot": item["slotIndex"],
                                        "eligible": item["eligibleCount"],
                                        "status": t("vacancy_risk") if item["hasVacancyRisk"] else t("awaiting_generation"),
                                    }
                                    for index, item in enumerate(requirements, start=1)
                                ]
                                _render_responsive_table(
                                    rows=rows,
                                    columns=[
                                        {"name": "day", "label": t("day"), "field": "day", "align": "left"},
                                        {"name": "post", "label": t("post"), "field": "post", "align": "left"},
                                        {"name": "slot", "label": "#", "field": "slot", "align": "right"},
                                        {"name": "eligible", "label": t("eligible_count"), "field": "eligible", "align": "right"},
                                        {"name": "status", "label": t("status"), "field": "status", "align": "left"},
                                    ],
                                    row_key="id",
                                    classes="p-4",
                                )

                    def refresh_requirements_after_leave_change() -> None:
                        """Invalidate the rendered preflight before leave-dependent refresh."""

                        requirements_state["rendered_key"] = None
                        refresh_requirements()

                    refresh_requirements()
                    day_closure_select.on_value_change(
                        lambda _event: refresh_requirements()
                    )

                    ui.separator().classes("sy-roster-step-availability my-5")
                    ui.label(t("pre_generation_leave")).classes(
                        "sy-roster-step-availability text-base font-semibold"
                    )
                    ui.label(t("leave_generation_notice")).classes(
                        "sy-roster-step-availability text-sm text-[var(--sy-muted)]"
                    )
                    prefect_options = {
                        str(prefect["id"]): f"{prefect['nameZh']} ({prefect['form']} {prefect['className']})"
                        for prefect in workflow.prefects()
                    }
                    with ui.row().classes(
                        "sy-mobile-field-row sy-roster-step-availability w-full gap-3 flex-wrap"
                    ):
                        leave_prefect = ui.select(
                            label=t("select_prefect"),
                            options=prefect_options,
                            value=next(iter(prefect_options), None),
                        ).props("data-testid=pre-generation-leave-prefect").classes(
                            "grow min-w-[220px]"
                        )
                        leave_day = ui.select(
                            label=t("leave_day"),
                            options={day.name: day_label(day) for day in SchoolDay},
                            value=SchoolDay.MONDAY.name,
                        ).classes("grow min-w-[180px]")
                    leave_reason = ui.input(label=t("leave_reason")).props(
                        "name=pre-generation-leave-reason autocomplete=off"
                    ).classes("sy-roster-step-availability w-full")
                    leave_list = ui.column().classes(
                        "sy-roster-step-availability w-full gap-2 mt-3"
                    )
                    leave_versions: dict[tuple[str, str], int] = {}

                    def refresh_leave_list() -> None:
                        leave_list.clear()
                        leave_versions.clear()
                        week_start = selected_week_start()
                        if week_start is None:
                            return
                        declarations = _safe_read_action(
                            lambda: workflow.pre_generation_leaves(week_start),
                            action_name="load_pre_generation_leaves",
                        )
                        if declarations is None:
                            return
                        with leave_list:
                            if declarations:
                                ui.label(t("declared_leaves")).classes("text-sm font-semibold")
                            for declaration in declarations:
                                declaration_key = (
                                    str(declaration["prefectId"]),
                                    str(declaration["day"]),
                                )
                                leave_versions[declaration_key] = int(declaration["version"])
                                with ui.row().classes("sy-mobile-list-action w-full items-center justify-between gap-3 py-1"):
                                    reason_text = str(declaration.get("reason") or t("leave_reason_not_provided"))
                                    ui.label(
                                        f"{day_label(str(declaration['day']))} | {declaration['prefectName']} | {reason_text}"
                                    ).classes("text-sm text-[var(--sy-muted)]")

                                    async def cancel_leave(
                                        leave_id: int = int(declaration["id"]),
                                        leave_version: int = int(declaration["version"]),
                                        cancel_command_id: str = f"leave-cancel-ui:{uuid4().hex}",
                                    ) -> None:
                                        result = await _run_with_progress(
                                            lambda: workflow.cancel_pre_generation_leave(
                                                leave_id,
                                                expected_version=leave_version,
                                                command_id=cancel_command_id,
                                            ),
                                            title_key="progress_leave_cancel_title",
                                            working_key="progress_leave_cancel_working",
                                            icon="event_available",
                                        )
                                        if result is not _OPERATION_FAILED:
                                            ui.notify(t("leave_cancelled"), type="positive")
                                            refresh_leave_list()
                                            refresh_requirements_after_leave_change()

                                    ui.button(t("cancel_leave"), icon="close", on_click=cancel_leave).props("flat dense color=negative")

                    async def declare_leave() -> None:
                        week_start = selected_week_start(announce_error=True)
                        if week_start is None:
                            return
                        if not leave_prefect.value:
                            ui.notify(t("leave_prefect_required"), type="warning")
                            leave_prefect.run_method("focus")
                            return
                        if not leave_day.value:
                            ui.notify(t("leave_day_required"), type="warning")
                            leave_day.run_method("focus")
                            return
                        reason = str(leave_reason.value or "").strip()
                        prefect_id = str(leave_prefect.value)
                        leave_day_value = str(leave_day.value)
                        expected_leave_version = leave_versions.get(
                            (prefect_id, leave_day_value),
                            0,
                        )
                        declare_command_id = f"leave-declare-ui:{uuid4().hex}"
                        declare_leave_button.disable()
                        declare_leave_button.set_icon("hourglass_top")
                        declare_leave_button.props("aria-busy=true")
                        result = await _run_with_progress(
                            lambda: workflow.declare_leave(
                                week_start=week_start,
                                prefect_id=prefect_id,
                                day=leave_day_value,
                                reason=reason or None,
                                expected_version=expected_leave_version,
                                command_id=declare_command_id,
                            ),
                            title_key="progress_leave_title",
                            working_key="progress_leave_working",
                            icon="event_busy",
                        )
                        if result is not _OPERATION_FAILED:
                            declare_leave_button.set_icon("task_alt")
                            leave_reason.value = ""
                            leave_reason.update()
                            refresh_leave_list()
                            refresh_requirements_after_leave_change()
                            ui.notify(t("leave_declared"), type="positive")
                        else:
                            declare_leave_button.set_icon("event_busy")
                        declare_leave_button.enable()
                        declare_leave_button.props(remove="aria-busy")

                    declare_leave_button = action(
                        t("declare_leave"),
                        icon="event_busy",
                        on_click=declare_leave,
                        variant="secondary",
                        classes="sy-roster-step-availability mt-3",
                        motion_role="edit",
                        icon_story_to="event_note",
                        icon_story_category="lifecycle",
                        test_id="declare-pre-generation-leave",
                    )
                    week_input.on(
                        "change",
                        lambda _event: (
                            selected_week_record(selected_week_start(), refresh=True),
                            refresh_leave_list(),
                            refresh_history_priority(),
                            refresh_assist_assignment_mode(),
                            refresh_day_closures(),
                            refresh_requirements(),
                        ),
                    )
                    refresh_leave_list()

                    async def generate() -> None:
                        week_start = selected_week_start(announce_error=True)
                        if week_start is None:
                            return
                        current_week = selected_week_record(week_start, refresh=True)
                        expected_week_version = int(current_week["version"]) if current_week else 0
                        generation_command_id = f"draft-generate-ui:{uuid4().hex}"
                        result = await _run_with_progress(
                            lambda: workflow.generate_and_save_draft(
                                week_start,
                                history_priority_multiplier=float(history_priority.value or 1.0),
                                assist_assignment_mode=_assist_assignment_mode_code(
                                    assist_assignment_mode.value,
                                    fallback=LEGACY_FIXED_WEEKDAY,
                                ),
                                closed_days=tuple(day_closure_select.value or ()),
                                expected_week_version=expected_week_version,
                                command_id=generation_command_id,
                            ),
                            title_key="progress_generate_title",
                            working_key="progress_generate_working",
                            icon="edit_calendar",
                        )
                        if result is not _OPERATION_FAILED:
                            ui.notify(t("draft_saved"), type="positive")
                            navigate_to(f"/rosters/{result.id}")

                    ui.button(
                        t("create_draft"), icon="edit_calendar", on_click=generate
                    ).props("color=primary").classes(
                        "sy-roster-step-generate sy-roster-generate-dock mt-4"
                    )
                with ui.element("section").classes(
                    "sy-roster-history-cta sy-surface w-full px-5 py-4 mt-5"
                ).props(
                    "id=roster-history data-testid=roster-history"
                ):
                    with ui.column().classes("gap-1 min-w-0"):
                        ui.html(t("current_rosters"), tag="h2").classes(
                            "text-xl font-semibold"
                        )
                        ui.label(t("dashboard_history_copy")).classes(
                            "text-sm leading-6 text-[var(--sy-muted)]"
                        )
                    action(
                        t("roster_workflow_history"),
                        icon="history",
                        on_click=lambda: navigate_to("/rosters/history"),
                        variant="secondary",
                        test_id="open-roster-history",
                    )
            with ui.tab_panel("adjust_edit").classes("px-0"):
                with ui.element("section").classes(
                    "sy-surface sy-roster-history-cta w-full px-5 py-5"
                ).props("data-testid=adjustments-history-shortcut"):
                    ui.label(t("adjustments")).classes("text-lg font-semibold")
                    _render_operation_hint("hint_adjust_roster", icon="event_busy")
                    action(
                        t("roster_workflow_history"),
                        icon="history",
                        on_click=lambda: navigate_to("/rosters/history"),
                        variant="primary",
                        test_id="adjustments-open-roster-history",
                    )


@ui.page("/rosters/new")
def generate_roster_page() -> None:
    navigate_to("/rosters")


@ui.page("/rosters/history")
def roster_history_page(page: int = 1) -> None:
    """Render bounded roster history outside the generation critical path."""

    _install_roster_mobile_styles()
    workflow = get_workflow()
    try:
        current_page = max(int(page), 1)
    except (TypeError, ValueError):
        current_page = 1
    page_size = 12
    page_rows = workflow.roster_week_history(
        page=current_page,
        page_size=page_size + 1,
    )
    has_next = len(page_rows) > page_size
    weeks = page_rows[:page_size]
    with page_shell("/rosters"):
        render_back_action(
            t("back_to_roster_hub"),
            "/rosters",
            test_id="back-to-roster-hub",
        )
        render_route_trail(
            (
                (t("rosters"), "/rosters"),
                (t("roster_workflow_history"), None),
            ),
            label=t("roster_route_hierarchy"),
        )
        render_workflow_navigation(
            _roster_workflow_steps(),
            current_index=4,
            label=t("roster_workflow_label"),
        )
        with ui.row().classes("w-full items-start justify-between gap-4"):
            with ui.column().classes("gap-1 min-w-0"):
                ui.html(t("current_rosters"), tag="h1").classes(
                    "text-2xl font-semibold"
                )
                ui.label(t("dashboard_history_copy")).classes(
                    "text-sm leading-6 text-[var(--sy-muted)]"
                )
            _tone_badge(str(current_page), "neutral")

        if not weeks:
            _render_empty_state(
                title_key="empty_roster_title",
                body_key="empty_roster_detail",
                icon="event_note",
                illustrated=True,
            )
        else:
            with ui.element("section").classes("w-full grid gap-3 mt-4").props(
                "data-testid=roster-history-page"
            ):
                for week in weeks:
                    history_priority_value = (
                        f"{float(week.get('historyPriorityMultiplier', 1.0)):.1f}"
                    )
                    with ui.element("article").classes(
                        "sy-surface sy-roster-week-item w-full px-5 py-4"
                    ):
                        with ui.row().classes(
                            "w-full items-start justify-between gap-3"
                        ):
                            with ui.column().classes("gap-1 min-w-0"):
                                ui.label(str(week["weekStart"])).classes(
                                    "text-lg font-semibold"
                                )
                                ui.label(
                                    f"{t('version')} {week['version']} · "
                                    f"{t('history_priority_used', value=history_priority_value)} · "
                                    f"{t('assist_assignment_mode_used', mode=_assist_assignment_mode_label(week.get('assistAssignmentMode')))}"
                                ).classes(
                                    "sy-roster-week-meta text-sm text-[var(--sy-muted)]"
                                )
                            status = str(week["status"])
                            status_tone = (
                                "stable"
                                if status == "published"
                                else "attention"
                                if status == "withdrawn"
                                else "action"
                            )
                            _tone_badge(t(status), status_tone)
                        with ui.row().classes(
                            "sy-mobile-actions w-full justify-end gap-2 mt-3"
                        ):
                            action(
                                t("view"),
                                icon="arrow_forward",
                                on_click=lambda item=week: navigate_to(
                                    f"/rosters/{item['id']}"
                                ),
                                variant="secondary",
                            )
                            if status == "published":
                                action(
                                    t("adjust_roster"),
                                    icon="swap_horiz",
                                    on_click=lambda item=week: navigate_to(
                                        f"/rosters/{item['id']}/adjustments"
                                    ),
                                    variant="secondary",
                                )
                                _render_withdraw_action(
                                    workflow,
                                    week,
                                    int(week["id"]),
                                )

        with ui.row().classes(
            "sy-mobile-actions w-full items-center justify-between gap-3 mt-5"
        ).props("aria-label=Pagination"):
            action(
                t("reference_previous"),
                icon="arrow_back",
                on_click=lambda: navigate_to(
                    f"/rosters/history?page={current_page - 1}"
                ),
                variant="quiet",
                disabled=current_page <= 1,
                test_id="roster-history-previous",
            )
            action(
                t("reference_next"),
                icon="arrow_forward",
                on_click=lambda: navigate_to(
                    f"/rosters/history?page={current_page + 1}"
                ),
                variant="quiet",
                disabled=not has_next,
                test_id="roster-history-next",
            )


@ui.page("/rosters/{roster_week_id}")
def roster_detail_page(roster_week_id: int) -> None:
    _install_roster_mobile_styles()
    workflow = get_workflow()
    with page_shell("/rosters"):
        try:
            week = workflow.roster_week(roster_week_id)
        except WorkflowError:
            _render_roster_route_state(
                title_key="roster_unavailable_title",
                body_key="roster_unavailable_body",
                icon="link_off",
                test_id="roster-unavailable-state",
                primary_key="review_current_rosters",
                primary_path="/rosters",
                secondary_key="review_restore_settings",
                secondary_path="/settings",
            )
            return
        render_back_action(t("back_to_roster_hub"), "/rosters", test_id="back-to-roster-hub")
        render_route_trail(
            (
                (t("rosters"), "/rosters"),
                (f"{t('roster_week_detail')} · {week['weekStart']}", None),
            ),
            label=t("roster_route_hierarchy"),
        )
        render_workflow_navigation(
            _roster_workflow_steps(roster_week_id=roster_week_id, status=str(week["status"])),
            current_index=4 if week["status"] == "withdrawn" else 2,
            label=t("roster_workflow_label"),
        )
        with ui.row().classes("sy-roster-detail-head w-full items-start justify-between gap-4"):
            with ui.column().classes("gap-1"):
                ui.label(str(week["weekStart"])).classes("text-2xl font-semibold")
                ui.label(f"{t('version')} {week['version']}").classes("text-[var(--sy-muted)]")
                ui.label(
                    t(
                        "history_priority_used",
                        value=f"{float(week.get('historyPriorityMultiplier', 1.0)):.1f}",
                    )
                ).classes("text-sm text-[var(--sy-muted)]")
                ui.label(
                    t(
                        "assist_assignment_mode_used",
                        mode=_assist_assignment_mode_label(week.get("assistAssignmentMode")),
                    )
                ).classes("text-sm text-[var(--sy-muted)]")
            with ui.row().classes("sy-mobile-actions sy-roster-detail-actions gap-2"):
                if week["status"] == "draft":
                    reviewed_version = int(week["version"])
                    publish_command_id = f"roster-publish-ui:{uuid4().hex}"
                    with ui.dialog() as publish_conflict_dialog, ui.card().classes("sy-surface w-full max-w-md p-6"):
                        ui.label(t("publish_conflict_title")).classes("text-lg font-semibold")
                        ui.label(t("publish_conflict_body", version=reviewed_version)).classes(
                            "text-sm text-[var(--sy-muted)] mt-2"
                        )

                        def reload_after_publish_conflict() -> None:
                            publish_conflict_dialog.close()
                            ui.navigate.reload()

                        with ui.row().classes("sy-mobile-actions w-full justify-end mt-5"):
                            ui.button(
                                t("publish_conflict_review_action"),
                                icon="refresh",
                                on_click=reload_after_publish_conflict,
                            ).props("color=primary")

                    with ui.dialog() as publish_dialog, ui.card().classes("sy-surface w-full max-w-md p-6"):
                        ui.label(t("confirm_publish")).classes("text-lg font-semibold")
                        ui.label(t("publish_warning")).classes("text-sm text-[var(--sy-muted)] mt-2")
                        ui.label(t("publish_reviewed_version", version=reviewed_version)).classes(
                            "text-sm font-medium mt-3"
                        )

                        async def publish() -> None:
                            publish_dialog.close()
                            result = await _run_with_progress(
                                lambda: workflow.publish(
                                    roster_week_id,
                                    expected_week_version=reviewed_version,
                                    command_id=publish_command_id,
                                ),
                                title_key="progress_publish_title",
                                working_key="progress_publish_working",
                                icon="publish",
                                on_conflict=lambda _error: publish_conflict_dialog.open(),
                            )
                            if result is not _OPERATION_FAILED:
                                ui.notify(t("published_success"), type="positive")
                                ui.navigate.reload()

                        with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5"):
                            ui.button(t("cancel"), icon="close", on_click=publish_dialog.close).props("flat")
                            ui.button(t("confirm_publish_action"), icon="publish", on_click=publish).props("color=primary")
                    ui.button(t("publish"), icon="publish", on_click=publish_dialog.open).props("color=primary")
                elif week["status"] == "published":
                    ui.button(t("adjust_roster"), icon="swap_horiz", on_click=lambda: navigate_to(f"/rosters/{roster_week_id}/adjustments")).props("outline color=primary")
                    _render_withdraw_action(workflow, week, roster_week_id)
                if week["status"] != "withdrawn":
                    ui.button(t("export_pdf"), icon="picture_as_pdf", on_click=lambda: _open_roster_export_dialog(roster_week_id)).props("outline color=primary")
        if week["status"] == "draft":
            ui.label(t("draft_export_warning")).classes("sy-fg-attention font-medium")
        if week["status"] != "withdrawn":
            ui.label(t("export_pdf_notice")).classes("text-sm text-[var(--sy-muted)]")
        if week["status"] == "draft":
            ui.label(t("draft_preview")).classes("text-xl font-semibold mt-2")
            ui.label(t("draft_preview_notice")).classes("text-sm text-[var(--sy-muted)]")
            _render_draft_grid_editor(workflow, roster_week_id)
        elif week["status"] == "published":
            with ui.card().classes("sy-surface sy-border-attention sy-operations-panel w-full border-l-4 p-6"):
                ui.label(t("post_publication_leave")).classes("text-lg font-semibold")
                ui.label(t("post_publication_leave_notice")).classes("text-sm text-[var(--sy-muted)] mt-1")
                ui.button(t("adjust_roster"), icon="swap_horiz", on_click=lambda: navigate_to(f"/rosters/{roster_week_id}/adjustments")).props("color=primary").classes("mt-4")
            render_roster_share_action(workflow, roster_week_id)
        else:
            with ui.card().classes("sy-surface sy-border-attention sy-operations-panel w-full border-l-4 p-6"):
                ui.label(t("withdrawn_roster_history_title")).classes("text-lg font-semibold")
                ui.label(t("withdrawn_roster_history_body")).classes(
                    "text-sm leading-6 text-[var(--sy-muted)] mt-1"
                )
                ui.label(
                    t(
                        "withdrawn_roster_reason",
                        reason=str(week.get("withdrawalReason") or t("withdraw_reason_not_provided")),
                    )
                ).classes("text-sm font-medium mt-3")
        declarations = workflow.pre_generation_leaves(week["weekStart"])
        if declarations:
            with ui.element("section").classes("sy-surface w-full px-5 py-4"):
                ui.label(t("declared_leaves")).classes("font-semibold")
                for declaration in declarations:
                    ui.label(
                        f"{day_label(str(declaration['day']))} | {declaration['prefectName']} | {declaration['reason']}"
                    ).classes("text-sm text-[var(--sy-muted)] mt-1")
        if week["status"] != "draft":
            _render_roster_table(roster_week_id)


@ui.page("/adjustments")
def adjustments_page() -> None:
    navigate_to("/rosters")


@ui.page("/rosters/{roster_week_id}/adjustments")
def adjustment_detail_page(roster_week_id: int) -> None:
    _install_roster_mobile_styles()
    workflow = get_workflow()
    with page_shell("/rosters"):
        try:
            week = workflow.roster_week(roster_week_id)
        except WorkflowError:
            _render_roster_route_state(
                title_key="roster_unavailable_title",
                body_key="roster_unavailable_body",
                icon="link_off",
                test_id="adjustment-roster-unavailable-state",
                primary_key="review_current_rosters",
                primary_path="/rosters",
                secondary_key="review_restore_settings",
                secondary_path="/settings",
            )
            return
        if week["status"] != "published":
            _render_roster_route_state(
                title_key="adjustment_unavailable_title",
                body_key="adjustment_unavailable_body",
                icon="pending_actions",
                test_id="adjustment-unavailable-state",
                primary_key="return_to_roster",
                primary_path=f"/rosters/{roster_week_id}",
                secondary_key="review_current_rosters",
                secondary_path="/rosters",
                secondary_icon="format_list_bulleted",
            )
            return
        render_back_action(
            t("back_to_week_detail"),
            f"/rosters/{roster_week_id}",
            test_id="back-to-roster-detail",
        )
        render_route_trail(
            (
                (t("rosters"), "/rosters"),
                (str(week["weekStart"]), f"/rosters/{roster_week_id}"),
                (t("roster_adjustment_detail"), None),
            ),
            label=t("roster_route_hierarchy"),
        )
        render_workflow_navigation(
            _roster_workflow_steps(roster_week_id=roster_week_id, status=str(week["status"])),
            current_index=3,
            label=t("roster_workflow_label"),
        )
        ui.label(t("adjustments")).classes("text-2xl font-semibold")
        _render_operation_hint("hint_leave_adjustment", icon="swap_horiz")
        adjustment_command_id = f"leave-ui:{uuid4().hex}"
        active_assignments = [item for item in workflow.assignments(roster_week_id) if item["status"] == "active"]
        options = {
            str(item["id"]): (
                f"{day_label(item['day'])} | "
                f"{roster_display_label(str(item['postCode']), int(item.get('slotIndex', 1)))} | "
                f"{item['prefectName']}"
            )
            for item in active_assignments
        }
        if not options:
            _render_empty_state(
                title_key="empty_published_title",
                body_key="empty_published_detail",
                icon="fact_check",
                action_key="empty_review_action",
                action=lambda: navigate_to("/rosters"),
            )
            return
        with ui.card().classes("sy-surface sy-adjustment-form sy-operations-panel w-full p-6"):
            with ui.element("section").classes("sy-adjustment-step"):
                ui.label(t("adjustment_step_assignment")).classes("sy-adjustment-step-title")
                assignment_select = ui.select(
                    label=t("select_assignment"), options=options, value=next(iter(options))
                ).classes("w-full")

            with ui.element("section").classes("sy-adjustment-step"):
                ui.label(t("adjustment_step_replacement")).classes("sy-adjustment-step-title")
                replacement_select = ui.select(
                    label=t("replacement"), options={"__vacant__": t("leave_vacant")}, value="__vacant__"
                ).classes("w-full")
                loaded_substitutes: dict[str, dict[str, object]] = {}

                def clear_loaded_substitutes() -> None:
                    loaded_substitutes.clear()
                    replacement_select.options = {"__vacant__": t("leave_vacant")}
                    replacement_select.value = "__vacant__"
                    replacement_select.update()

                assignment_select.on_value_change(lambda _event: clear_loaded_substitutes())

            def load_substitutes() -> None:
                def action() -> None:
                    candidates = workflow.recommend_substitutes(roster_week_id, int(assignment_select.value))
                    loaded_substitutes.clear()
                    loaded_substitutes.update({str(item["id"]): item for item in candidates})
                    replacement_select.options = {"__vacant__": t("leave_vacant")}
                    replacement_select.options.update({str(item["id"]): f"{item['nameZh']} ({item['form']} {item['className']}; {item['historyWeight']:.1f})" for item in candidates})
                    replacement_select.value = "__vacant__"
                    replacement_select.update()
                    ui.notify(t("eligible_substitutes") if candidates else t("no_substitutes"), type="info")

                _safe_read_action(action, action_name="load_adjustment_candidates")

            adjustment_complete_dialog = ui.dialog().props("persistent")
            with adjustment_complete_dialog, ui.card().classes(
                "sy-surface w-full max-w-lg p-6"
            ):
                with ui.row().classes("w-full items-center gap-3"):
                    ui.icon("task_alt").classes("sy-fg-stable text-2xl").props("aria-hidden=true")
                    ui.label(t("adjustment_receipt_title")).classes("text-xl font-semibold")
                adjustment_receipt_summary = ui.label("").classes("text-base font-medium mt-4")
                adjustment_receipt_version = ui.label("").classes("text-sm text-[var(--sy-muted)] mt-2")
                adjustment_receipt_safety = ui.label("").classes("text-sm text-[var(--sy-muted)] mt-2")
                with ui.element("section").classes("sy-border-attention border-l-4 pl-4 mt-4"):
                    ui.label(t("adjustment_old_pdf_warning")).classes("text-sm font-medium")

                def open_updated_export() -> None:
                    adjustment_complete_dialog.close()
                    _open_roster_export_dialog(roster_week_id)

                with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5"):
                    ui.button(
                        t("review_updated_roster"),
                        icon="fact_check",
                        on_click=lambda: navigate_to(f"/rosters/{roster_week_id}"),
                    ).props("outline color=primary")
                    ui.button(
                        t("export_share_updated_pdf"),
                        icon="ios_share",
                        on_click=open_updated_export,
                    ).props("color=primary data-testid=export-updated-roster")
            # This receipt is page-owned rather than a one-shot runtime dialog.
            # It deliberately remains mounted while it launches the nested PDF
            # delivery dialog; deleting it on close would detach that new child
            # before PDF preparation finishes.

            async def apply_adjustment() -> None:
                reason = str(reason_input.value or "").strip()
                assignment_id = int(assignment_select.value)
                replacement_id = None if replacement_select.value == "__vacant__" else str(replacement_select.value)
                result = await _run_with_progress(
                    lambda: workflow.apply_leave_adjustment(
                        roster_week_id=roster_week_id,
                        assignment_id=assignment_id,
                        replacement_prefect_id=replacement_id,
                        reason=reason,
                        command_id=adjustment_command_id,
                        expected_week_version=int(week["version"]),
                    ),
                    title_key="progress_adjustment_title",
                    working_key="progress_adjustment_working",
                    icon="swap_horiz",
                )
                if result is not _OPERATION_FAILED:
                    share_revocation_pending = False
                    if result.share_ids_to_revoke:
                        revocation = await _run_with_progress(
                            lambda: revoke_roster_shares(workflow, result.share_ids_to_revoke),
                            title_key="progress_share_revoke_title",
                            working_key="progress_share_revoke_working",
                            icon="link_off",
                        )
                        share_revocation_pending = (
                            revocation is _OPERATION_FAILED or bool(revocation[1])
                        )
                        if share_revocation_pending:
                            ui.notify(t("adjustment_share_pending"), type="warning", timeout=8_000)
                    ui.notify(
                        t("adjustment_replay_confirmed") if result.idempotent else t("adjustment_saved"),
                        type="info" if result.idempotent else "positive",
                    )
                    if result.status == "vacant":
                        adjustment_receipt_summary.set_text(
                            t(
                                "adjustment_receipt_vacant",
                                original=result.original_prefect_name,
                                weight=f"{result.weight:g}",
                            )
                        )
                    else:
                        adjustment_receipt_summary.set_text(
                            t(
                                "adjustment_receipt_transfer",
                                original=result.original_prefect_name,
                                replacement=result.replacement_prefect_name or "—",
                                weight=f"{result.weight:g}",
                            )
                        )
                    adjustment_receipt_version.set_text(
                        t("adjustment_receipt_version", version=result.version)
                    )
                    safety_parts = [t("adjustment_receipt_safety")]
                    if result.backup_path is not None:
                        safety_parts.append(t("adjustment_receipt_backup_verified"))
                    elif result.idempotent:
                        safety_parts.append(t("adjustment_receipt_replayed"))
                    if result.share_ids_to_revoke:
                        safety_parts.append(
                            t(
                                "adjustment_receipt_share_pending"
                                if share_revocation_pending
                                else "adjustment_receipt_share_revoked"
                            )
                        )
                    adjustment_receipt_safety.set_text(" ".join(safety_parts))
                    save_adjustment_button.disable()
                    adjustment_complete_dialog.open()

            with ui.element("section").classes("sy-adjustment-step"):
                ui.label(t("adjustment_step_reason")).classes("sy-adjustment-step-title")
                reason_input = ui.textarea(label=t("reason")).props(
                    "name=leave-adjustment-reason autocomplete=off"
                ).classes("w-full")
            with ui.row().classes("sy-adjustment-actions w-full gap-3"):
                ui.button(t("load_substitutes"), icon="group_add", on_click=load_substitutes).props("outline color=primary")
                save_adjustment_button = ui.button(
                    t("apply_adjustment"), icon="save", on_click=apply_adjustment
                ).props("color=primary")
