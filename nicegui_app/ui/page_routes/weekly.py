"""NiceGUI route registrations grouped by operator domain."""

from __future__ import annotations

import asyncio
from contextvars import copy_context
from dataclasses import dataclass
from datetime import date
from collections.abc import Callable, Collection, Mapping
from typing import Any
from uuid import uuid4

from nicegui import ui, background_tasks

from nicegui_app.runtime import get_workflow
from nicegui_app.services.roster_document import RosterDocument, capture_roster_document
from nicegui_app.services.roster_presentation import (
    RosterCellState,
    RosterPresentationError,
    build_roster_presentation,
    roster_display_label,
)
from nicegui_app.services.roster_workflow import (
    FLEXIBLE_WEEKLY,
    LEGACY_FIXED_WEEKDAY,
    WorkflowError,
)
from nicegui_app.ui.access_control import render_roster_share_action, revoke_roster_shares
from nicegui_app.ui.components import (
    action,
    dialog as semantic_dialog,
    motion_pattern,
    native_dialog as semantic_native_dialog,
)
from nicegui_app.services.draft_editor import DraftEditor, DraftCommittedWithoutBackup, DraftSaveOutcome
from nicegui_app.ui.html_safety import attr
from nicegui_app.ui.i18n import current_locale, day_label, t
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


def _published_adjustment_targets(document: RosterDocument) -> dict[str, Mapping[str, object]]:
    if document.snapshot.status != "published":
        return {}
    open_ids = {
        cell.assignment_id
        for row in document.presentation.rows for cell in row.cells
        if cell.state in {RosterCellState.ASSIGNED, RosterCellState.VACANT}
        and cell.assignment_id is not None
    }
    return {str(item["id"]): item for item in document.snapshot.assignments if item["id"] in open_ids}


def _adjustment_selection_complete(
    target: Mapping[str, object] | None, choice: object, candidate_ids: Collection[str],
) -> bool:
    if target is None or target.get("status") not in {"active", "replaced", "vacant"}:
        return False
    if choice == _DRAFT_VACANCY_VALUE:
        return target.get("status") != "vacant" and target.get("prefectId") is not None
    return isinstance(choice, str) and bool(choice) and choice in candidate_ids


def _adjustment_target_label(item: Mapping[str, object]) -> str:
    occupant = t("vacant") if item["status"] == "vacant" else str(item["prefectName"])
    post = roster_display_label(str(item["postCode"]), int(item.get("slotIndex", 1)))
    return f"{day_label(item['day'])} | {post} | {occupant}"


@dataclass(frozen=True)
class _DraftCommitView:
    read_only: bool
    can_publish: bool
    saved_version: int | None
    latest_version: int
    status: str
    refresh_failed: bool
    recovery_required: bool


def _draft_commit_view(editor: DraftEditor) -> _DraftCommitView:
    return _DraftCommitView(
        editor.read_only,
        not editor.read_only and not editor.saving and not editor.dirty,
        editor.last_saved_version,
        editor.reviewed_version,
        editor.roster_status,
        editor.snapshot_refresh_failed,
        editor.recovery_required,
    )


def _draft_commit_notice(view: _DraftCommitView, locale: str) -> tuple[str, str]:
    english = locale == "en"
    title = f"Saved v{view.saved_version}" if english else f"已儲存 v{view.saved_version}"
    if view.recovery_required:
        title += " · Backup incomplete" if english else " · 備份未完成"
    if view.refresh_failed:
        body = (
            "The write committed, but the latest roster could not be read. Editing is locked; review the authoritative roster before continuing. This command will not be sent again."
            if english else
            "操作已提交，但未能讀取最新周表。編輯已鎖定；請重新查看權威周表後再繼續。本次命令不會重新送出。"
        )
    else:
        status = {"draft": ("Draft", "草稿"), "published": ("Published", "已發布"), "withdrawn": ("Withdrawn", "已撤回")}[view.status][not english]
        body = (
            f"Latest roster: {status} v{view.latest_version}. This editor is now read-only. Review the authoritative roster before continuing."
            if english else
            f"最新周表：{status} v{view.latest_version}。本編輯器已轉為唯讀，請重新查看權威周表後再繼續。"
        )
    return title, body


def _sync_draft_publish_controls(view: _DraftCommitView, controls, dialog) -> None:
    for control in controls:
        control.set_enabled(view.can_publish)
        if view.can_publish:
            control.props(remove="aria-disabled")
        else:
            control.props("aria-disabled=true")
    if not view.can_publish:
        dialog.close()


async def _save_draft_with_progress(
    editor: DraftEditor,
    reason: str | None,
    *,
    on_settled: Callable[[DraftSaveOutcome | None, Exception | None], None],
    on_state_change: Callable[[], None] | None = None,
    on_conflict: Callable[..., None] | None = None,
):
    """Keep controller settlement alive after a page stops waiting for its write."""
    if not editor.dirty or editor.saving or editor.read_only:
        return _OPERATION_FAILED
    loop = asyncio.get_running_loop()
    # NiceGUI removes request context inside run.io_bound. Only restore it on
    # UI settlement; storage and translations must still belong to this page.
    callback_context = copy_context()
    command = editor.prepare_save(reason)
    admitted = False
    if on_state_change is not None:
        loop.call_soon(on_state_change)

    async def settle_save():
        try:
            outcome = await editor.save_prepared(command)
        except Exception as error:
            loop.call_soon(on_settled, None, error, context=callback_context.copy())
            raise
        loop.call_soon(on_settled, outcome, None, context=callback_context.copy())
        return outcome

    def admitted_action():
        nonlocal admitted
        admitted = True
        # Reservation freezes click-time intent; only the durable-write gate
        # admits persistence. The worker owns this future, so a cancelled page
        # waiter cannot skip the controller's finish/partial settlement.
        return asyncio.run_coroutine_threadsafe(settle_save(), loop).result()

    try:
        result = await _run_with_progress(
            admitted_action,
            title_key="progress_draft_change_title",
            working_key="progress_draft_change_working",
            icon="edit_note",
            on_conflict=on_conflict,
        )
    except asyncio.CancelledError:
        # The gate schedules its worker before its first await. It may still be
        # queued: do not release the reservation merely because it has not yet
        # entered admitted_action. That worker will settle the command.
        raise
    except Exception:
        if not admitted:
            editor.finish_save(None)
            if on_state_change is not None:
                loop.call_soon(on_state_change)
        raise
    if not admitted:
        editor.finish_save(None)
        if on_state_change is not None:
            loop.call_soon(on_state_change)
    return result


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


def _invalidate_draft_candidate_cache_for_days(
    candidate_cache: dict[str, object],
    days: set[SchoolDay],
) -> tuple[str, ...]:
    """Any assignment may affect adjacent days; the bounded week is one cache."""

    invalidated = tuple(sorted(candidate_cache)) if days else ()
    for cell_key in invalidated:
        candidate_cache.pop(cell_key, None)
    return invalidated


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

    session = DraftEditor(
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

    session = DraftEditor(
        original_assignments=original_assignments,
        original_unavailable=set(),
        original_closed_days=set(),
        reviewed_version=0,
        pending_cells=pending_cells,
    )
    mutation = session.stage_move(source_key, target_key)
    return mutation.source_prefect_id, mutation.target_prefect_id


def _render_draft_grid_editor(
    workflow: Any,
    roster_week_id: int,
    *,
    schedule_snapshot: tuple[dict[str, object], list[dict[str, object]]] | None = None,
    on_saved: Callable[[dict[str, object]], None] | None = None,
    on_state_change: Callable[[_DraftCommitView], None] | None = None,
) -> None:
    """Render one batch-safe draft editor around the canonical roster matrix."""

    week_snapshot, assignments = (
        schedule_snapshot
        if schedule_snapshot is not None
        else workflow.roster_schedule_snapshot(roster_week_id)
    )
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
    mobile_candidate_choice_ref: dict[str, Any | None] = {"control": None}
    cell_editor_native_ref: dict[str, Any | None] = {"control": None}
    save_review_dialog_ref: dict[str, Any | None] = {"control": None}
    mobile_dialog_state: dict[str, bool] = {"open": False}
    mobile_day_state: dict[str, str] = {
        "value": presentation.days[0].day.name if presentation.days else ""
    }
    reason_state: dict[str, str] = {"value": ""}
    announcement_state: dict[str, str] = {"value": ""}
    candidate_loads: set[tuple[int, str]] = set()
    conflict_reapply_ref: dict[str, Any | None] = {"control": None}
    desktop_cell_controls: dict[str, dict[str, Any]] = {}
    mobile_cell_controls: dict[str, dict[str, Any]] = {}
    desktop_day_closed_controls: dict[SchoolDay, Any] = {}
    day_header_refreshers: dict[SchoolDay, Any] = {}
    mobile_day_tab_controls: dict[SchoolDay, tuple[Any, Any]] = {}
    mobile_day_controls: dict[SchoolDay, dict[str, Any]] = {}
    detail_surface_controls: dict[str, dict[str, Any]] = {}
    detail_sync_state: dict[str, bool] = {"active": False}
    draft_status_controls: dict[str, Any | None] = {
        "announcement": None,
        "move_guidance": None,
    }
    pending_controls: dict[str, list[Any]] = {
        "labels": [],
        "undo": [],
        "redo": [],
        "requires_changes": [],
    }
    mobile_dock_ref: dict[str, Any | None] = {"control": None}
    save_review_count_ref: dict[str, Any | None] = {"control": None}
    save_review_confirm_ref: dict[str, Any | None] = {"control": None}
    reason_controls: list[Any] = []
    surface_refreshers: dict[str, Any] = {}
    editor_surface = None
    day_dialogs: dict[SchoolDay, Any] = {}
    client = ui.context.client
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
    edit_session = DraftEditor(
        original_assignments=original_assignments,
        original_unavailable=original_unavailable,
        original_closed_days=original_closed_days,
        reviewed_version=int(week_snapshot["version"]),
        workflow=workflow,
        roster_week_id=roster_week_id,
    )
    candidate_cache = edit_session.candidate_cache
    ui.context.client.on_delete(edit_session.close)
    pending_cells = edit_session.pending_cells
    pending_days = edit_session.pending_days
    pending_slots = edit_session.pending_slots
    navigable_keys = [
        cell.cell_key
        for row in presentation.rows
        for cell in row.cells
        if cell.cell_key
        and is_room_open(cell.post, cell.day)
    ]

    def day_is_closed(day: SchoolDay) -> bool:
        return edit_session.day_is_closed(day.name)

    def active_cell_key() -> str | None:
        visible = [
            key
            for key in navigable_keys
            if not day_is_closed(cells_by_key[key].day)
        ]
        if edit_session.selected_cell in visible:
            return edit_session.selected_cell
        return visible[0] if visible else None

    def pending_count() -> int:
        return edit_session.pending_count

    def set_action_enabled(control: Any, enabled: bool) -> None:
        """Synchronize NiceGUI event gating with the accessibility state."""

        control.set_enabled(enabled)
        if enabled:
            control.props(remove="aria-disabled")
        else:
            control.props("aria-disabled=true")

    def update_batch_reason(raw_value: object) -> None:
        value = str(raw_value or "")
        if reason_state["value"] == value:
            return
        reason_state["value"] = value
        for control in reason_controls:
            if control.value != value:
                control.set_value(value)

    def slot_is_unavailable(cell_key: str) -> bool:
        return edit_session.slot_is_unavailable(cell_key)

    def refresh_draft_surfaces(
        *,
        cell_keys: set[str] | None = None,
        days: set[SchoolDay] | None = None,
        details: bool = False,
        mobile_day: bool = False,
        tabs: bool = True,
        pending: bool = True,
    ) -> None:
        """Update only the mounted surfaces affected by one local edit."""

        if callback := surface_refreshers.get("status"):
            callback()
        if callback := surface_refreshers.get("cells"):
            callback(cell_keys)
        for day in days or set():
            if callback := day_header_refreshers.get(day):
                callback()
        if tabs and (callback := surface_refreshers.get("tabs")):
            callback()
        if mobile_day and (callback := surface_refreshers.get("mobile_day")):
            callback()
        if details and (callback := surface_refreshers.get("details")):
            callback()
        if pending and (callback := surface_refreshers.get("pending")):
            callback()
        view = _draft_commit_view(edit_session)
        if on_state_change is not None:
            on_state_change(view)
        if view.read_only and editor_surface is not None:
            editor_surface.props("inert aria-disabled=true")
            hide_mobile_editor()
            conflict_dialog.close()
            discard_dialog.close()
            for dialog in day_dialogs.values():
                dialog.close()
            if save_review_dialog_ref["control"] is not None:
                save_review_dialog_ref["control"].close()
            title, body = _draft_commit_notice(view, current_locale())
            commit_notice_title.set_text(title)
            commit_notice_body.set_text(body)
            commit_notice.set_visibility(True)

    def show_mobile_editor() -> None:
        """Open the mounted native sheet without moving its subtree into a portal."""

        dialog = cell_editor_native_ref["control"]
        if edit_session.read_only or dialog is None or mobile_dialog_state["open"]:
            return
        search = mobile_candidate_selector_ref["control"]
        if search is not None and search.value:
            search.set_value("")
        mobile_dialog_state["open"] = True
        dialog.run_method("showModal")

    def hide_mobile_editor() -> None:
        """Close the native sheet while keeping all controls mounted for reuse."""

        mobile_dialog_state["open"] = False
        dialog = cell_editor_native_ref["control"]
        if dialog is not None:
            dialog.run_method("close")

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

    def cell_classes(prefix: str, cell_key: str, state: str) -> str:
        classes = f"{prefix} {prefix}--{state}"
        if edit_session.selected_cell == cell_key:
            classes += f" {prefix}--selected"
        if cell_key in pending_cells or cell_key in pending_slots:
            classes += f" {prefix}--pending"
        if edit_session.move_source == cell_key:
            classes += f" {prefix}--move-source"
        return classes

    def load_candidates(cell: Any) -> list[dict[str, object]] | None:
        """Return cached choices immediately; mount no people until IO completes."""
        key = cell.cell_key
        if key in candidate_cache:
            return candidate_cache[key]
        query_key = (edit_session.local_revision, key)
        candidate_loads.intersection_update(
            item for item in tuple(candidate_loads) if item[0] == edit_session.local_revision
        )
        if query_key not in candidate_loads:
            candidate_loads.add(query_key)

            async def fetch() -> None:
                try:
                    candidates = await edit_session.candidates(key)
                except Exception as error:
                    def report() -> None:
                        raise error
                    _safe_read_action(report, action_name="load_draft_cell_candidates")
                    return
                if candidates is None:
                    return
                prefect_names.update(edit_session.candidate_names)
                if edit_session.selected_cell == key:
                    refresh_draft_surfaces(cell_keys=set(), details=True, tabs=False, pending=False)

            background_tasks.create(fetch())
        return None

    def open_cell_editor(cell_key: str, *, compact: bool = False) -> None:
        if edit_session.move_source and edit_session.move_source != cell_key:
            source = edit_session.move_source
            background_tasks.create(stage_move(source, cell_key))
            return
        previous_cell = edit_session.selected_cell
        edit_session.selected_cell = cell_key
        if not compact:
            hide_mobile_editor()
        refresh_draft_surfaces(
            cell_keys={key for key in (previous_cell, cell_key) if key},
            details=True,
            mobile_day=False,
            tabs=False,
            pending=False,
        )
        if compact:
            show_mobile_editor()
        selector_ref = (
            mobile_candidate_selector_ref
            if compact
            else desktop_candidate_selector_ref
        )
        selector = selector_ref["control"]
        if selector is not None:
            selector.run_method("focus")

    def focus_cell(cell_key: str, *, compact: bool = False) -> None:
        previous_cell = edit_session.selected_cell
        edit_session.selected_cell = cell_key
        if compact:
            mobile_day_state["value"] = cells_by_key[cell_key].day.name
        hide_mobile_editor()
        refresh_draft_surfaces(
            cell_keys={key for key in (previous_cell, cell_key) if key},
            details=True,
            mobile_day=compact,
            tabs=compact,
            pending=False,
        )
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
                focus_cell(neighbor, compact=compact)
        elif key_name == " ":
            if edit_session.move_source == cell_key:
                edit_session.move_source = None
                refresh_draft_surfaces(
                    cell_keys={cell_key},
                    details=True,
                    tabs=False,
                    pending=False,
                )
            elif edit_session.move_source:
                source = edit_session.move_source
                background_tasks.create(stage_move(source, cell_key))
            elif not slot_is_unavailable(cell_key) and (
                pending_cells.get(cell_key, original_assignments.get(cell_key)) is not None
            ):
                edit_session.move_source = cell_key
                refresh_draft_surfaces(
                    cell_keys={cell_key},
                    details=True,
                    tabs=False,
                    pending=False,
                )
        elif key_name in {"enter", "f2"}:
            open_cell_editor(cell_key, compact=compact)
        elif key_name == "escape" and edit_session.selected_cell == cell_key:
            hide_mobile_editor()
            edit_session.selected_cell = None
            refresh_draft_surfaces(
                cell_keys={cell_key},
                details=True,
                mobile_day=False,
                tabs=False,
                pending=False,
            )

    def handle_pointer_move(event: Any) -> None:
        event_args = event.args if isinstance(event.args, dict) else {}
        source_key = str(event_args.get("source", ""))
        target_key = str(event_args.get("target", ""))
        if source_key in cells_by_key and target_key in cells_by_key:
            background_tasks.create(stage_move(source_key, target_key))

    def stage_candidate(cell_key: str, raw_value: object) -> None:
        if slot_is_unavailable(cell_key):
            ui.notify(t("draft_slot_reopen_before_assign"), type="warning")
            return
        normalized_value = _normalize_draft_candidate_value(raw_value)
        if normalized_value in (None, ""):
            refresh_draft_surfaces(
                cell_keys={cell_key},
                details=True,
                tabs=False,
                pending=False,
            )
            return
        replacement_id = (
            None if normalized_value == _DRAFT_VACANCY_VALUE else normalized_value
        )
        mutation = edit_session.stage_candidate(cell_key, replacement_id)
        if mutation.kind == "noop":
            return
        if mutation.kind in {"invalid", "blocked"}:
            ui.notify(t("draft_candidate_invalid"), type="warning")
            refresh_draft_surfaces(
                cell_keys={cell_key}, details=True, tabs=False, pending=False,
            )
            return
        if mutation.exchanged_cell_key:
            message = t("draft_swap_staged", name=prefect_names.get(replacement_id, ""))
            announcement_state["value"] = message
            ui.notify(message, type="info")
        else:
            announcement_state["value"] = t("draft_assignment_staged")
        selector_value = replacement_id or "__vacant__"
        detail_sync_state["active"] = True
        try:
            for selector_ref in (
                desktop_candidate_selector_ref,
                mobile_candidate_choice_ref,
            ):
                selector = selector_ref["control"]
                if selector is not None and selector.value != selector_value:
                    selector.set_value(selector_value)
        finally:
            detail_sync_state["active"] = False
        changed_cells = {cell_key}
        if mutation.exchanged_cell_key:
            changed_cells.add(mutation.exchanged_cell_key)
        _invalidate_draft_candidate_cache_for_days(
            candidate_cache,
            {cells_by_key[key].day for key in changed_cells},
        )
        refresh_draft_surfaces(cell_keys=changed_cells, details=True)

    async def stage_move(source_key: str, target_key: str) -> None:
        previous_move_source = edit_session.move_source
        edit_session.move_source = None
        if source_key == target_key or slot_is_unavailable(target_key):
            ui.notify(t("draft_move_invalid_target"), type="warning")
            refresh_draft_surfaces(
                cell_keys={key for key in (previous_move_source, source_key, target_key) if key},
                details=True,
            )
            return
        source_id = edit_session.effective_assignment(source_key)
        target_id = edit_session.effective_assignment(target_key)
        if source_id is None:
            ui.notify(t("draft_move_source_empty"), type="warning")
            refresh_draft_surfaces(
                cell_keys={key for key in (previous_move_source, source_key) if key},
                details=True,
            )
            return
        target_candidates = await edit_session.candidates(target_key, source_key=source_key)
        target_ids = {
            str(candidate["id"])
            for candidate in (target_candidates or [])
            if candidate.get("id")
        }
        if source_id not in target_ids:
            ui.notify(t("draft_move_policy_rejected"), type="warning")
            refresh_draft_surfaces(
                cell_keys={key for key in (previous_move_source, source_key, target_key) if key},
                details=True,
            )
            return
        mutation = edit_session.stage_move(source_key, target_key)
        if mutation.kind in {"blocked", "noop", "empty"}:
            ui.notify(t("draft_move_invalid_target"), type="warning")
            refresh_draft_surfaces(
                cell_keys={key for key in (previous_move_source, source_key, target_key) if key},
                details=True,
            )
            return
        message = (
            t("draft_exchange_staged")
            if mutation.kind == "swap"
            else t("draft_move_staged")
        )
        announcement_state["value"] = message
        ui.notify(message, type="info")
        _invalidate_draft_candidate_cache_for_days(
            candidate_cache,
            {cells_by_key[source_key].day, cells_by_key[target_key].day},
        )
        refresh_draft_surfaces(
            cell_keys={source_key, target_key},
            details=True,
        )

    def toggle_move_source(cell_key: str) -> None:
        previous_move_source = edit_session.move_source
        edit_session.move_source = (
            None if edit_session.move_source == cell_key else cell_key
        )
        refresh_draft_surfaces(
            cell_keys={key for key in (previous_move_source, cell_key) if key},
            details=True,
            tabs=False,
            pending=False,
        )

    def stage_slot(cell_key: str, unavailable: bool) -> None:
        candidate_state_before = candidate_eligibility_states()
        if not edit_session.stage_slot(cell_key, unavailable):
            return
        _invalidate_draft_candidate_cache_for_days(
            candidate_cache,
            changed_candidate_eligibility_days(candidate_state_before),
        )
        announcement_state["value"] = t(
            "draft_slot_state_staged_unavailable"
            if unavailable
            else "draft_slot_state_staged_open"
        )
        refresh_draft_surfaces(cell_keys={cell_key}, details=True)

    def stage_day(day: SchoolDay, closed: bool) -> None:
        previous_selected = edit_session.selected_cell
        if not edit_session.stage_day(day.name, closed):
            return
        announcement_state["value"] = t(
            "draft_day_state_staged_closed" if closed else "draft_day_state_staged_open",
            day=day_label(day),
        )
        if previous_selected and edit_session.selected_cell is None:
            hide_mobile_editor()
        _invalidate_draft_candidate_cache_for_days(candidate_cache, {day})
        refresh_draft_surfaces(
            cell_keys={
                cell.cell_key
                for row in presentation.rows
                for cell in row.cells
                if cell.day == day and cell.cell_key
            },
            days={day},
            details=True,
            mobile_day=True,
        )

    def closed_day_states() -> dict[SchoolDay, bool]:
        return {item.day: day_is_closed(item.day) for item in presentation.days}

    def candidate_eligibility_states() -> dict[SchoolDay, tuple[object, ...]]:
        """Capture the local state which can change a weekday's candidate set."""

        return {
            item.day: (
                day_is_closed(item.day),
                *(
                    (
                        cell.cell_key,
                        edit_session.effective_assignment(cell.cell_key),
                        slot_is_unavailable(cell.cell_key),
                    )
                    for row in presentation.rows
                    for cell in row.cells
                    if cell.day == item.day and cell.cell_key
                ),
            )
            for item in presentation.days
        }

    def changed_closed_days(before: dict[SchoolDay, bool]) -> set[SchoolDay]:
        return {
            day
            for day, was_closed in before.items()
            if day_is_closed(day) != was_closed
        }

    def changed_candidate_eligibility_days(
        before: dict[SchoolDay, tuple[object, ...]],
    ) -> set[SchoolDay]:
        after = candidate_eligibility_states()
        return {day for day, state in before.items() if after.get(day) != state}

    def reconcile_editor_after_history_change() -> None:
        selected_cell = edit_session.selected_cell
        if selected_cell and day_is_closed(cells_by_key[selected_cell].day):
            edit_session.selected_cell = None
        if edit_session.selected_cell is None:
            hide_mobile_editor()

    def undo_pending() -> None:
        before = closed_day_states()
        candidate_state_before = candidate_eligibility_states()
        if not edit_session.undo():
            return
        _invalidate_draft_candidate_cache_for_days(
            candidate_cache,
            changed_candidate_eligibility_days(candidate_state_before),
        )
        reconcile_editor_after_history_change()
        announcement_state["value"] = t("draft_undo_announced")
        refresh_draft_surfaces(
            days=changed_closed_days(before),
            details=True,
            mobile_day=True,
        )

    def redo_pending() -> None:
        before = closed_day_states()
        candidate_state_before = candidate_eligibility_states()
        if not edit_session.redo():
            return
        _invalidate_draft_candidate_cache_for_days(
            candidate_cache,
            changed_candidate_eligibility_days(candidate_state_before),
        )
        reconcile_editor_after_history_change()
        announcement_state["value"] = t("draft_redo_announced")
        refresh_draft_surfaces(
            days=changed_closed_days(before),
            details=True,
            mobile_day=True,
        )

    def discard_pending() -> None:
        before = closed_day_states()
        candidate_state_before = candidate_eligibility_states()
        edit_session.discard()
        _invalidate_draft_candidate_cache_for_days(
            candidate_cache,
            changed_candidate_eligibility_days(candidate_state_before),
        )
        reconcile_editor_after_history_change()
        reason_state["value"] = ""
        for control in reason_controls:
            control.set_value("")
        ui.run_javascript("window.__syDraftDirty = false")
        discard_dialog.close()
        refresh_draft_surfaces(
            days=changed_closed_days(before),
            details=True,
            mobile_day=True,
        )

    def reload_latest() -> None:
        conflict_dialog.close()
        ui.navigate.reload()

    def compare_latest(_error: Exception | None = None) -> None:
        latest = _safe_read_action(
            lambda: workflow.roster_schedule_snapshot(roster_week_id),
            action_name="compare_draft_conflict",
        )
        if latest is None:
            edit_session.remember_latest(None)
            edit_session.set_conflict(
                latest_version=None,
                changes=[t("draft_conflict_compare_unavailable")],
            )
        else:
            latest_week, latest_assignments = latest
            edit_session.remember_latest(latest)
            _invalidate_draft_candidate_cache_for_days(
                candidate_cache,
                {item.day for item in presentation.days},
            )
            latest_presentation = build_roster_presentation(
                latest_week,
                latest_assignments,
                closed_days=latest_week.get("closedDays", ()),
                editable=latest_week["status"] == "draft",
            )
            latest_cells = {
                candidate.cell_key: candidate
                for candidate_row in latest_presentation.rows
                for candidate in candidate_row.cells
                if candidate.cell_key
            }
            changes: list[str] = []
            if latest_week["status"] != "draft":
                changes.append(f"{t('status')}: {t(str(latest_week['status']))}")
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
            set_action_enabled(
                reapply_control,
                edit_session.can_reapply_conflict,
            )
        conflict_comparison.refresh()
        conflict_dialog.open()

    async def reapply_latest() -> None:
        latest = edit_session.latest_snapshot
        if not edit_session.reapply_conflict():
            compare_latest()
            return
        conflict_dialog.close()
        if latest is not None:
            adopt_saved_presentation(latest)
        # Rebase is a reviewed preview, not an implicit second write.

    with semantic_dialog(
        title=t("draft_conflict_preserved_title"),
        description=t("draft_conflict_preserved_body"),
        persistent=True,
        presentation="alert",
        test_id="draft-conflict-dialog",
    ) as conflict_dialog:
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

    with semantic_dialog(
        title=t("draft_discard_confirm_title"),
        description=t("draft_discard_confirm_body"),
        persistent=True,
        presentation="alert",
        test_id="draft-discard-dialog",
    ) as discard_dialog:
        with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5"):
            action(t("cancel"), icon="close", on_click=discard_dialog.close, variant="quiet")
            action(
                t("draft_discard_all"),
                icon="delete_sweep",
                on_click=discard_pending,
                variant="danger",
            )

    def adopt_saved_presentation(snapshot) -> None:
        nonlocal presentation
        latest_week, latest_assignments = snapshot
        week_snapshot.clear()
        week_snapshot.update(latest_week)
        assignments[:] = latest_assignments
        presentation = build_roster_presentation(
            latest_week, latest_assignments, closed_days=latest_week.get("closedDays", ()),
            editable=not edit_session.read_only and latest_week["status"] == "draft",
        )
        cells_by_key.clear()
        cells_by_key.update({cell.cell_key: cell for row in presentation.rows for cell in row.cells if cell.cell_key})
        prefect_names.update({str(cell.prefect_id): str(cell.prefect_name) for cell in cells_by_key.values()
                              if cell.prefect_id and cell.prefect_name})
        if on_saved is not None:
            on_saved(latest_week)
        refresh_draft_surfaces(days={item.day for item in presentation.days}, details=True, mobile_day=True)

    async def save_pending() -> None:
        if not edit_session.dirty or edit_session.saving or edit_session.read_only:
            return
        reason = reason_state["value"].strip() or None

        def state_changed() -> None:
            if editor_surface is not None and not editor_surface.is_deleted:
                with client:
                    refresh_draft_surfaces(cell_keys=set(), pending=True, tabs=False)

        def settled(outcome: DraftSaveOutcome | None, error: Exception | None) -> None:
            if editor_surface is None or editor_surface.is_deleted:
                return
            with client:
                if outcome is not None or isinstance(error, DraftCommittedWithoutBackup):
                    view = _draft_commit_view(edit_session)
                    if view.read_only:
                        title, _ = _draft_commit_notice(view, current_locale())
                        announcement_state["value"] = title
                    else:
                        announcement_state["value"] = t("draft_batch_saved") + f" · v{view.saved_version}"
                    ui.notify(announcement_state["value"], type="warning" if view.refresh_failed or view.recovery_required else "positive")
                    snapshot = outcome.snapshot if outcome is not None else error.snapshot
                    if snapshot is not None and not view.refresh_failed:
                        adopt_saved_presentation(snapshot)
                        return
                refresh_draft_surfaces(details=True, pending=True)

        await _save_draft_with_progress(
            edit_session,
            reason,
            on_state_change=state_changed,
            on_settled=settled,
            on_conflict=compare_latest,
        )

    mobile_editor_focus_restore_js = (
        "(()=>{const selected=[...document.querySelectorAll("
        "'.sy-draft-mobile-cell--selected,.sy-draft-grid-cell--selected'"
        ")].find(item=>item.dataset.cellKey);"
        "const key=selected?.dataset.cellKey;if(!key)return;"
        "window.__syDraftFocusRestoreKey=key;"
        "const cleanup=()=>{"
        "window.removeEventListener('pointerdown',cancel,true);"
        "window.removeEventListener('keydown',cancel,true);};"
        "const cancel=()=>{window.__syDraftFocusRestoreKey=null;cleanup();};"
        "window.addEventListener('pointerdown',cancel,true);"
        "window.addEventListener('keydown',cancel,true);"
        "document.querySelectorAll("
        "'.sy-draft-grid-cell--selected,.sy-draft-mobile-cell--selected'"
        ").forEach(item=>item.classList.remove("
        "'sy-draft-grid-cell--selected','sy-draft-mobile-cell--selected'));"
        "window.setTimeout(()=>{cleanup();"
        "if(window.__syDraftFocusRestoreKey!==key)return;"
        "const cell=[...document.querySelectorAll(`[data-cell-key=\"${key}\"]`)]"
        ".find(item=>item.getClientRects().length&&"
        "getComputedStyle(item).visibility!=='hidden');"
        "if (cell) { cell.focus({preventScroll: true});"
        "cell.scrollIntoView({block: 'nearest', inline: 'nearest'}); }"
        "window.__syDraftFocusRestoreKey=null;},340);})();"
    )

    def stage_selected_slot(unavailable: bool) -> None:
        key = edit_session.selected_cell
        if key:
            stage_slot(key, unavailable)

    def toggle_selected_move_source() -> None:
        key = edit_session.selected_cell
        if key:
            toggle_move_source(key)

    def stage_selected_candidate(event: Any) -> None:
        if detail_sync_state["active"]:
            return
        key = edit_session.selected_cell
        if key:
            stage_candidate(key, event.value)

    def filter_mobile_candidates(_event: Any) -> None:
        controls = detail_surface_controls.get("mobile")
        if controls is None or edit_session.selected_cell is None:
            return
        controls["option_signature"] = None
        update_cell_detail_surface(compact=True)

    def mount_cell_detail_surface(*, compact: bool) -> None:
        """Mount one reusable selected-cell form for the lifetime of this page."""

        surface = "mobile" if compact else "desktop"
        suffix = "-mobile" if compact else ""
        empty_state = ui.column().classes("w-full gap-2")
        with empty_state:
            ui.label(t("draft_select_cell")).classes("font-semibold")
            ui.label(t("draft_candidate_search_hint")).classes(
                "text-sm leading-6 text-[var(--sy-muted)]"
            )
        empty_state.set_visibility(not compact)

        detail = ui.column().classes("w-full gap-3")
        with detail:
            selected_label = ui.label("").classes(
                "text-lg font-semibold" if compact else "font-semibold"
            )
            unavailable_group = ui.column().classes("w-full gap-3")
            with unavailable_group:
                ui.label(t("draft_slot_unavailable_body")).classes(
                    "text-sm leading-6 text-[var(--sy-muted)]"
                )
                reopen_action = action(
                    t("draft_slot_reopen_action"),
                    icon="event_available",
                    on_click=lambda: stage_selected_slot(False),
                    variant="secondary",
                    test_id=f"draft-slot-reopen{suffix}",
                )

            assignment_group = ui.column().classes("w-full gap-3")
            with assignment_group:
                if compact:
                    search_input = ui.input(
                        label=t("draft_candidate_search"),
                        value="",
                        on_change=filter_mobile_candidates,
                    ).classes("w-full").props(
                        "type=search autocomplete=off "
                        "data-testid=draft-candidate-search-mobile"
                    )
                    selector = ui.radio(
                        {},
                        value=None,
                        on_change=stage_selected_candidate,
                    ).classes(
                        "sy-draft-mobile-candidate-options w-full"
                    ).style(
                        "display:grid;gap:8px"
                    ).props(
                        'aria-label="'
                        + attr(t("draft_candidate_search"))
                        + '" data-testid=draft-candidate-options-mobile'
                    )
                    assignment_group.props("data-draft-mobile-candidate-surface")
                    mobile_candidate_selector_ref["control"] = search_input
                    mobile_candidate_choice_ref["control"] = selector
                else:
                    search_input = None
                    selector = ui.select(
                        label=t("draft_candidate_search"),
                        options={},
                        value=None,
                        with_input=True,
                        clearable=True,
                        on_change=stage_selected_candidate,
                    ).classes("w-full").props("use-input input-debounce=0")
                candidate_unavailable = ui.label(
                    t("draft_candidate_unavailable")
                ).classes("sy-fg-attention text-sm leading-6")
                ui.label(t("draft_candidate_search_hint")).classes(
                    "text-xs leading-5 text-[var(--sy-muted)]"
                )
                with ui.row().classes("sy-mobile-actions gap-2 flex-wrap"):
                    move_action = action(
                        t("draft_move_start"),
                        icon="open_with",
                        on_click=toggle_selected_move_source,
                        variant="quiet",
                        test_id=f"draft-move-start{suffix}",
                    )
                    unavailable_action = action(
                        t("draft_slot_unavailable_action"),
                        icon="block",
                        on_click=lambda: stage_selected_slot(True),
                        variant="attention",
                        test_id=f"draft-slot-unavailable{suffix}",
                    )

        detail.set_visibility(False)
        unavailable_group.set_visibility(False)
        assignment_group.set_visibility(False)
        candidate_unavailable.set_visibility(False)
        if not compact:
            desktop_candidate_selector_ref["control"] = selector
        detail_surface_controls[surface] = {
            "empty": empty_state,
            "detail": detail,
            "selected_label": selected_label,
            "unavailable_group": unavailable_group,
            "assignment_group": assignment_group,
            "selector": selector,
            "search_input": search_input,
            "option_signature": None,
            "candidate_unavailable": candidate_unavailable,
            "move_action": move_action,
            "reopen_action": reopen_action,
            "unavailable_action": unavailable_action,
        }

    def update_cell_detail_surface(*, compact: bool) -> None:
        """Synchronize a mounted form without replacing any NiceGUI controls."""

        surface = "mobile" if compact else "desktop"
        controls = detail_surface_controls.get(surface)
        if controls is None:
            return
        key = edit_session.selected_cell
        selector = controls["selector"]
        if not key:
            controls["empty"].set_visibility(not compact)
            controls["detail"].set_visibility(False)
            # Retain the editor itself, not the last cell's rendered people.
            # Candidate data remains in the bounded cache; releasing the radio
            # and select options prevents hidden DOM growth after first use.
            if controls["option_signature"] is not None:
                detail_sync_state["active"] = True
                try:
                    selector.set_options({}, value=None)
                    controls["option_signature"] = None
                finally:
                    detail_sync_state["active"] = False
            selector.props(remove="data-testid data-cell-key")
            if compact:
                controls["search_input"].props(remove="data-cell-key")
            return

        cell = cells_by_key[key]
        row = next(
            item
            for item in presentation.rows
            if item.spec.post == cell.post and item.spec.slot_index == cell.slot_index
        )
        controls["empty"].set_visibility(False)
        controls["detail"].set_visibility(True)
        controls["selected_label"].set_text(
            t(
                "draft_selected_cell",
                cell=f"{day_label(cell.day)} · {row.spec.display_label}",
            )
        )

        unavailable = slot_is_unavailable(key)
        controls["unavailable_group"].set_visibility(unavailable)
        controls["assignment_group"].set_visibility(not unavailable)
        if unavailable:
            selector.props(remove="data-testid data-cell-key")
            if compact:
                controls["search_input"].props(remove="data-cell-key")
            return

        candidates = load_candidates(cell)
        options: dict[str, str] = {"__vacant__": t("draft_explicit_vacancy")}
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
        rendered_value = selected_value
        if compact:
            query = str(controls["search_input"].value or "").strip().casefold()
            if query:
                options = {
                    value: label
                    for value, label in options.items()
                    if query in label.casefold()
                }
                if rendered_value not in options:
                    rendered_value = None
        detail_sync_state["active"] = True
        try:
            option_signature = (tuple(options.items()), rendered_value)
            if controls["option_signature"] != option_signature:
                selector.set_options(options, value=rendered_value)
                controls["option_signature"] = option_signature
            elif selector.value != rendered_value:
                selector.set_value(rendered_value)
        finally:
            detail_sync_state["active"] = False
        if compact:
            selector.props(
                f'data-testid=draft-candidate-options-mobile data-cell-key="{attr(key)}"'
            )
            controls["search_input"].props(
                f'data-testid=draft-candidate-search-mobile data-cell-key="{attr(key)}"'
            )
        else:
            selector.props(
                f'data-testid=draft-candidate-search data-cell-key="{attr(key)}"'
            )
        selector.set_enabled(candidates is not None)
        if candidates is None:
            selector.props("aria-disabled=true")
        else:
            selector.props(remove="aria-disabled")
        controls["candidate_unavailable"].set_visibility(candidates is None)

        moving = edit_session.move_source == key
        move_action = controls["move_action"]
        move_action.set_text(t("draft_move_cancel") if moving else t("draft_move_start"))
        move_action.props("icon=close" if moving else "icon=open_with")
        effective_prefect = pending_cells.get(key, original_assignments.get(key))
        set_action_enabled(move_action, effective_prefect is not None)

    def close_mobile_editor() -> None:
        previous_cell = edit_session.selected_cell
        hide_mobile_editor()
        edit_session.selected_cell = None
        refresh_draft_surfaces(
            cell_keys={previous_cell} if previous_cell else set(),
            details=True,
            tabs=False,
            pending=False,
        )

    def editor() -> None:
        nonlocal editor_surface
        desktop_candidate_selector_ref["control"] = None
        mobile_candidate_selector_ref["control"] = None
        mobile_candidate_choice_ref["control"] = None
        cell_editor_native_ref["control"] = None
        save_review_dialog_ref["control"] = None
        with motion_pattern(
            "operation-stage",
            tag="section",
            classes="sy-draft-editor",
            test_id="draft-grid-editor",
        ) as editor_root:
            editor_surface = editor_root
            ui.label(t("draft_schedule_title")).classes("text-xl font-semibold")
            ui.label(t("draft_schedule_intro")).classes(
                "text-sm leading-6 text-[var(--sy-muted)]"
            )
            announcement = ui.label(announcement_state["value"]).classes("sr-only").props(
                "role=status aria-live=polite aria-atomic=true "
                "data-testid=draft-grid-announcement"
            )
            move_guidance = ui.label(t("draft_move_choose_target")).classes(
                "sy-draft-move-guidance text-sm font-semibold"
            ).props("role=status aria-live=polite")
            move_guidance.set_visibility(bool(edit_session.move_source))
            draft_status_controls["announcement"] = announcement
            draft_status_controls["move_guidance"] = move_guidance

            def update_status_controls() -> None:
                announcement.set_text(announcement_state["value"])
                move_guidance.set_visibility(bool(edit_session.move_source))

            surface_refreshers["status"] = update_status_controls

            with ui.element("div").classes("sy-draft-grid-shell"):
                with ui.element("div").classes("sy-draft-grid-scroll"):
                    with ui.element("div").classes("sy-draft-grid-desktop").props(
                        'role="grid" aria-label="' + attr(t("draft_schedule_title")) + '"'
                    ):
                        with ui.element("div").classes("sy-draft-grid-corner").style(
                            "grid-column:1;grid-row:1"
                        ):
                            ui.label(t("duty_position"))
                        def mount_day_header(day_index: int, day_item: Any) -> None:
                            day = day_item.day

                            @ui.refreshable
                            def day_header() -> None:
                                effective_closed = day_is_closed(day)
                                with ui.element("div").classes(
                                    "sy-draft-grid-day-head"
                                ).style(f"grid-column:{day_index};grid-row:1"):
                                    ui.label(day_label(day)).classes("font-semibold")
                                    if day_item.duty_date:
                                        ui.label(
                                            day_item.duty_date.strftime("%m/%d")
                                        ).classes("text-xs")
                                    day_action = action(
                                        t(
                                            "draft_day_reopen_action"
                                            if effective_closed
                                            else "draft_day_close_action"
                                        ),
                                        icon=(
                                            "event_available"
                                            if effective_closed
                                            else "event_busy"
                                        ),
                                        variant="quiet",
                                        classes="sy-draft-grid-day-action",
                                        test_id=f"draft-day-toggle-{day.name.lower()}",
                                    )
                                    affected = sum(
                                        1
                                        for row in presentation.rows
                                        for cell in row.cells
                                        if cell.day == day and cell.prefect_id
                                    )
                                    with semantic_dialog(
                                        title=t(
                                            "draft_day_reopen_confirm_title"
                                            if effective_closed
                                            else "draft_day_close_confirm_title",
                                            day=day_label(day),
                                        ),
                                        description=t(
                                            "draft_day_reopen_confirm_body"
                                            if effective_closed
                                            else "draft_day_close_confirm_body",
                                            day=day_label(day),
                                            count=affected,
                                        ),
                                        persistent=True,
                                        presentation="alert",
                                        test_id=f"draft-day-confirm-{day.name.lower()}",
                                    ) as day_dialog:
                                        day_dialogs[day] = day_dialog
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
                                                icon=(
                                                    "event_available"
                                                    if effective_closed
                                                    else "event_busy"
                                                ),
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

                            day_header_refreshers[day] = day_header.refresh
                            day_header()

                        for day_index, day_item in enumerate(
                            presentation.days, start=2
                        ):
                            mount_day_header(day_index, day_item)
                            day = day_item.day
                            with ui.element("div").classes(
                                "sy-draft-grid-day-closed"
                            ).style(
                                f"grid-column:{day_index};grid-row:2 / span {len(presentation.rows)}"
                            ) as closed_panel:
                                ui.icon("event_busy").props("aria-hidden=true")
                                ui.label(t("draft_day_closed")).classes("font-semibold")
                                ui.label(day_label(day)).classes("text-sm")
                            closed_panel.set_visibility(day_is_closed(day))
                            desktop_day_closed_controls[day] = closed_panel

                        for row_index, row in enumerate(presentation.rows, start=2):
                            with ui.element("div").classes("sy-draft-grid-row-head").style(
                                f"grid-column:1;grid-row:{row_index}"
                            ):
                                ui.label(row.spec.display_label).classes("font-semibold")
                                ui.label("–".join(row.spec.service_time)).classes("text-xs")
                            for day_index, cell in enumerate(row.cells, start=2):
                                name, meta, state = cell_display(cell)
                                classes = cell_classes(
                                    "sy-draft-grid-cell", cell.cell_key, state
                                )
                                aria = f"{day_label(cell.day)}, {row.spec.display_label}, {name}"
                                interaction_props = (
                                    'role="gridcell" aria-disabled="true" tabindex="-1"'
                                    if state == "closed"
                                    else (
                                        'role="gridcell" tabindex="0"'
                                        if cell.cell_key == active_cell_key()
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
                                    name_label = ui.label(name).classes(
                                        "sy-draft-cell-name"
                                    )
                                    meta_label = ui.label(meta).classes(
                                        "sy-draft-cell-meta"
                                    )
                                    meta_label.set_visibility(bool(meta))
                                button.set_visibility(not day_is_closed(cell.day))
                                desktop_cell_controls[cell.cell_key] = {
                                    "button": button,
                                    "name": name_label,
                                    "meta": meta_label,
                                    "row_label": row.spec.display_label,
                                }
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

                        desktop_active_state = {"key": active_cell_key()}

                        def update_mounted_cells(cell_keys: set[str] | None) -> None:
                            new_active = active_cell_key()
                            targets = set(
                                desktop_cell_controls
                                if cell_keys is None
                                else cell_keys
                            )
                            targets.update(
                                key
                                for key in (desktop_active_state["key"], new_active)
                                if key
                            )
                            desktop_active_state["key"] = new_active
                            for key in targets:
                                cell = cells_by_key.get(key)
                                controls = desktop_cell_controls.get(key)
                                if cell is None or controls is None:
                                    continue
                                name, meta, state = cell_display(cell)
                                button = controls["button"]
                                button.classes(
                                    replace=cell_classes(
                                        "sy-draft-grid-cell", key, state
                                    )
                                )
                                aria = (
                                    f"{day_label(cell.day)}, "
                                    f"{controls['row_label']}, {name}"
                                )
                                button.props(
                                    f'aria-label="{attr(aria)}" '
                                    f'tabindex="{0 if key == new_active and state != "closed" else -1}"'
                                )
                                if state == "closed":
                                    button.props("aria-disabled=true")
                                else:
                                    button.props(remove="aria-disabled")
                                button.set_visibility(not day_is_closed(cell.day))
                                controls["name"].set_text(name)
                                controls["meta"].set_text(meta)
                                controls["meta"].set_visibility(bool(meta))

                            for day, closed_panel in desktop_day_closed_controls.items():
                                closed_panel.set_visibility(day_is_closed(day))

                            for key, controls in mobile_cell_controls.items():
                                if cell_keys is not None and key not in cell_keys:
                                    continue
                                cell = cells_by_key[key]
                                name, meta, state = cell_display(cell)
                                button = controls["button"]
                                button.classes(
                                    replace=cell_classes(
                                        "sy-draft-mobile-cell", key, state
                                    )
                                )
                                aria = (
                                    f"{day_label(cell.day)}, "
                                    f"{controls['row_label']}, {name}"
                                )
                                button.props(f'aria-label="{attr(aria)}"')
                                controls["name"].set_text(name)
                                controls["meta"].set_text(meta)
                                controls["meta"].set_visibility(bool(meta))

                        surface_refreshers["cells"] = update_mounted_cells

                def select_mobile_day(day_name: str) -> None:
                    mobile_day_state["value"] = day_name
                    if callback := surface_refreshers.get("mobile_day"):
                        callback()
                    if callback := surface_refreshers.get("tabs"):
                        callback()
                    ui.run_javascript(
                        "requestAnimationFrame(() => {"
                        f"const selected='{attr(day_name)}';"
                        "document.querySelectorAll('[data-mobile-day]').forEach(section => "
                        "section.classList.toggle('sy-draft-mobile-day--selected', "
                        "section.dataset.mobileDay === selected));"
                        "document.querySelectorAll('[data-mobile-day-tab]').forEach(tab => {"
                        "const active=tab.dataset.mobileDayTab === selected;"
                        "tab.classList.toggle('sy-draft-mobile-day-tab--active', active);"
                        "tab.setAttribute('aria-current', active ? 'page' : 'false');"
                        "});"
                        "document.querySelector(`[data-mobile-day-tab=\"${selected}\"]`)"
                        "?.focus({preventScroll: true});"
                        "})"
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
                    ) as day_section:
                        with ui.row().classes("w-full items-center justify-between gap-3"):
                            with ui.column().classes("gap-0"):
                                ui.label(day_label(day)).classes("font-semibold")
                                if day_item.duty_date:
                                    ui.label(day_item.duty_date.strftime("%Y-%m-%d")).classes(
                                        "text-xs text-[var(--sy-muted)]"
                                    )
                            day_action = action(
                                t(
                                    "draft_day_reopen_action"
                                    if day_is_closed(day)
                                    else "draft_day_close_action"
                                ),
                                icon="event_available" if day_is_closed(day) else "event_busy",
                                on_click=lambda selected_day=day: day_dialogs[
                                    selected_day
                                ].open(),
                                variant="quiet",
                            )
                        closed_notice = ui.label(t("draft_day_closed")).classes(
                            "sy-fg-attention font-semibold py-4"
                        )
                        closed_notice.set_visibility(day_is_closed(day))
                        for row in presentation.rows:
                            cell = next(item for item in row.cells if item.day == day)
                            name, meta, state = cell_display(cell)
                            classes = cell_classes(
                                "sy-draft-mobile-cell", cell.cell_key, state
                            )
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
                                    name_label = ui.label(name).classes(
                                        "sy-draft-cell-name"
                                    )
                                    meta_label = ui.label(meta).classes(
                                        "sy-draft-cell-meta"
                                    )
                                    meta_label.set_visibility(bool(meta))
                            mobile_cell_controls[cell.cell_key] = {
                                "button": button,
                                "name": name_label,
                                "meta": meta_label,
                                "row_label": row.spec.display_label,
                            }
                            button.set_visibility(not day_is_closed(day))
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

                        mobile_day_controls[day] = {
                            "section": day_section,
                            "action": day_action,
                            "closed_notice": closed_notice,
                        }

                def update_mobile_days() -> None:
                    for day, controls in mobile_day_controls.items():
                        active = mobile_day_state["value"] == day.name
                        classes = "sy-draft-mobile-day"
                        if active:
                            classes += " sy-draft-mobile-day--selected"
                        controls["section"].classes(replace=classes)
                        closed = day_is_closed(day)
                        day_action = controls["action"]
                        day_action.set_text(
                            t(
                                "draft_day_reopen_action"
                                if closed
                                else "draft_day_close_action"
                            )
                        )
                        day_action.props(
                            "icon=event_available" if closed else "icon=event_busy"
                        )
                        controls["closed_notice"].set_visibility(closed)
                        for key, cell_controls in mobile_cell_controls.items():
                            if cells_by_key[key].day == day:
                                cell_controls["button"].set_visibility(not closed)

                surface_refreshers["mobile_day"] = update_mobile_days

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
                                summary_label = ui.label(summary).classes(
                                    "sy-draft-mobile-day-tab-summary"
                                )
                            mobile_day_tab_controls[day] = (tab, summary_label)

                    def update_mobile_day_tabs() -> None:
                        for day, (tab, summary_label) in mobile_day_tab_controls.items():
                            pending, vacancies, unavailable, closed_all_day = (
                                mobile_day_summary(day)
                            )
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
                            active = mobile_day_state["value"] == day.name
                            if active:
                                tab.classes(add="sy-draft-mobile-day-tab--active")
                            else:
                                tab.classes(remove="sy-draft-mobile-day-tab--active")
                            tab.props(
                                f'aria-label="{attr(day_label(day) + ", " + summary)}" '
                                f'aria-current={"page" if active else "false"}'
                            )
                            summary_label.set_text(summary)

                    surface_refreshers["tabs"] = update_mobile_day_tabs
                    for day_item in presentation.days:
                        render_mobile_day(day_item)
                    update_mobile_days()

            desktop_cell_detail = ui.element("div").classes(
                "sy-draft-editor-panel sy-draft-editor-panel--desktop"
            ).props("data-testid=draft-desktop-cell-detail")
            with desktop_cell_detail:
                mount_cell_detail_surface(compact=False)
                desktop_reason = ui.textarea(
                    label=t("draft_batch_reason"),
                    value=reason_state["value"],
                    on_change=lambda event: update_batch_reason(event.value),
                ).props("name=draft-batch-reason autocomplete=off").classes("w-full")
                reason_controls.append(desktop_reason)

            with semantic_native_dialog(
                title=t("draft_select_cell"),
                description=t("draft_candidate_search_hint"),
                presentation="sheet",
                test_id="draft-mobile-editor-sheet",
            ) as cell_editor_dialog:
                cell_editor_native_ref["control"] = cell_editor_dialog
                with ui.row().classes("sy-mobile-actions w-full justify-end gap-3"):
                    mobile_close_action = action(
                        t("close"),
                        icon="close",
                        variant="quiet",
                        test_id="draft-mobile-editor-close",
                    )
                    mobile_close_action.on(
                        "click",
                        close_mobile_editor,
                        js_handler=(
                            "(event)=>{"
                            + mobile_editor_focus_restore_js
                            + "emit({});}"
                        ),
                    )
                mount_cell_detail_surface(compact=True)
                cell_editor_dialog.on(
                    "cancel",
                    close_mobile_editor,
                    js_handler=(
                        "(event) => { event.preventDefault(); "
                        + mobile_editor_focus_restore_js
                        + "emit({}); }"
                    ),
                )
                cell_editor_dialog.on(
                    "keydown",
                    js_handler="""
                    (event) => {
                      if (event.key !== 'Tab') return;
                      const focusable = [...event.currentTarget.querySelectorAll(
                        'button:not([disabled]), input:not([disabled]), '
                        + 'select:not([disabled]), textarea:not([disabled]), '
                        + '[href], [tabindex]:not([tabindex="-1"])'
                      )].filter(item => item.getClientRects().length > 0);
                      if (!focusable.length) {
                        event.preventDefault();
                        event.currentTarget.focus();
                        return;
                      }
                      const first = focusable[0];
                      const last = focusable[focusable.length - 1];
                      const active = document.activeElement;
                      if (event.shiftKey && (active === first || !event.currentTarget.contains(active))) {
                        event.preventDefault();
                        last.focus();
                      } else if (!event.shiftKey && (active === last || !event.currentTarget.contains(active))) {
                        event.preventDefault();
                        first.focus();
                      }
                    }
                    """,
                )

            def refresh_selected_details() -> None:
                update_cell_detail_surface(compact=False)
                update_cell_detail_surface(compact=True)

            surface_refreshers["details"] = refresh_selected_details
            refresh_selected_details()

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
                    pending_label = ui.label(
                        t("draft_pending_count", count=count)
                        if count
                        else t("draft_pending_none")
                    ).classes("font-semibold")
                    pending_controls["labels"].append(pending_label)
                    ui.label(t("draft_undo_hint")).classes(
                        "text-xs text-[var(--sy-muted)]"
                    )
                with ui.row().classes("sy-mobile-actions gap-2 flex-wrap"):
                    undo_action = action(
                        t("draft_undo"),
                        icon="undo",
                        on_click=undo_pending,
                        variant="quiet",
                        disabled=not edit_session.can_undo,
                        test_id="draft-undo",
                    )
                    pending_controls["undo"].append(undo_action)
                    redo_action = action(
                        t("draft_redo"),
                        icon="redo",
                        on_click=redo_pending,
                        variant="quiet",
                        disabled=not edit_session.can_redo,
                        test_id="draft-redo",
                    )
                    pending_controls["redo"].append(redo_action)
                    discard_action = action(
                        t("draft_discard_all"),
                        icon="delete_sweep",
                        on_click=discard_dialog.open,
                        variant="secondary",
                        disabled=not count,
                    )
                    pending_controls["requires_changes"].append(discard_action)
                    save_action = action(
                        t("draft_save_all"),
                        icon="save",
                        on_click=save_pending,
                        disabled=not count,
                        test_id="draft-save-all",
                    )
                    pending_controls["requires_changes"].append(save_action)

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
                save_review_count = ui.label(t("draft_pending_count", count=count)).classes(
                    "text-lg font-semibold"
                )
                save_review_count_ref["control"] = save_review_count
                ui.label(t("draft_undo_hint")).classes(
                    "text-sm leading-6 text-[var(--sy-muted)]"
                )
                mobile_reason = ui.textarea(
                    label=t("draft_batch_reason"),
                    value=reason_state["value"],
                    on_change=lambda event: update_batch_reason(event.value),
                ).props(
                    "name=draft-mobile-batch-reason autocomplete=off"
                ).classes("w-full")
                reason_controls.append(mobile_reason)

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
                    save_review_confirm = action(
                        t("draft_save_all"),
                        icon="save",
                        on_click=save_from_mobile,
                        disabled=not count,
                        test_id="draft-save-all-mobile-confirm",
                    )
                    save_review_confirm_ref["control"] = save_review_confirm

            mobile_dock_classes = "sy-draft-mobile-save-dock"
            if not count:
                mobile_dock_classes += " sy-draft-mobile-save-dock--empty"
            with ui.element("div").classes(mobile_dock_classes).props(
                "aria-live=polite data-testid=draft-mobile-save-dock"
            ) as mobile_dock:
                mobile_dock_ref["control"] = mobile_dock
                with ui.column().classes("gap-0 min-w-0"):
                    pending_label = ui.label(
                        t("draft_pending_count", count=count)
                        if count
                        else t("draft_pending_none")
                    ).classes("font-semibold")
                    pending_controls["labels"].append(pending_label)
                    ui.label(t("draft_undo_hint")).classes(
                        "text-xs text-[var(--sy-muted)]"
                    )
                with ui.row().classes("sy-mobile-actions gap-2 flex-wrap"):
                    undo_action = action(
                        t("draft_undo"),
                        icon="undo",
                        on_click=undo_pending,
                        variant="quiet",
                        disabled=not edit_session.can_undo,
                        test_id="draft-undo-mobile",
                    )
                    pending_controls["undo"].append(undo_action)
                    mobile_save_action = action(
                        t("draft_save_all"),
                        icon="save",
                        on_click=save_review_dialog.open,
                        disabled=not count,
                        test_id="draft-save-all-mobile",
                    )
                    pending_controls["requires_changes"].append(mobile_save_action)

            def update_pending_controls() -> None:
                count = pending_count()
                ui.run_javascript(
                    f"window.__syDraftDirty = {'true' if count else 'false'}"
                )
                label_text = (
                    t("draft_pending_count", count=count)
                    if count
                    else t("draft_pending_none")
                )
                for label in pending_controls["labels"]:
                    label.set_text(label_text)
                for control in pending_controls["undo"]:
                    set_action_enabled(control, edit_session.can_undo)
                for control in pending_controls["redo"]:
                    set_action_enabled(control, edit_session.can_redo)
                for control in pending_controls["requires_changes"]:
                    set_action_enabled(control, bool(count) and not edit_session.saving and not edit_session.read_only)
                save_review_count.set_text(t("draft_pending_count", count=count))
                set_action_enabled(save_review_confirm, bool(count) and not edit_session.saving and not edit_session.read_only)
                dock_classes = "sy-draft-mobile-save-dock"
                if not count:
                    dock_classes += " sy-draft-mobile-save-dock--empty"
                mobile_dock.classes(replace=dock_classes)

            surface_refreshers["pending"] = update_pending_controls

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
        elif (
            key_name == "escape"
            and edit_session.selected_cell is not None
            and not mobile_dialog_state["open"]
        ):
            previous_cell = edit_session.selected_cell
            hide_mobile_editor()
            edit_session.selected_cell = None
            refresh_draft_surfaces(
                cell_keys={previous_cell},
                details=True,
                tabs=False,
                pending=False,
            )

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
    with ui.element("section").classes("sy-surface w-full p-4").props(
        "role=status aria-live=polite aria-atomic=true data-testid=draft-commit-receipt"
    ) as commit_notice:
        commit_notice_title = ui.label("").classes("font-semibold")
        commit_notice_body = ui.label("").classes("text-sm leading-6")
        ui.link(t("reload_and_review"), f"/rosters/{roster_week_id}").classes("min-h-11 inline-flex items-center underline").props(
            "data-testid=draft-review-authoritative"
        )
    commit_notice.set_visibility(False)
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
    with semantic_dialog(
        title=t("withdraw_roster_title"),
        description=t("withdraw_roster_body"),
        persistent=True,
        presentation="alert",
        test_id="withdraw-roster-dialog",
    ) as withdraw_dialog:
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

                    initial_record = selected_week_record(initial_week)
                    initial_assist_mode = _assist_assignment_mode_code(
                        initial_record.get("assistAssignmentMode") if initial_record else None,
                        fallback=LEGACY_FIXED_WEEKDAY,
                    )
                    initial_multiplier = float(
                        initial_record.get("historyPriorityMultiplier", 1.0)
                        if initial_record
                        else 1.0
                    )
                    advanced_rules_state: dict[str, object] = {
                        "mounted": False,
                        "open": False,
                        "assist_mode": initial_assist_mode,
                        "history_priority": initial_multiplier,
                    }
                    advanced_rule_controls: dict[str, Any | None] = {
                        "assist": None,
                        "assist_explanation": None,
                        "history": None,
                        "history_bar": None,
                        "history_value": None,
                        "history_chart": None,
                    }
                    with ui.element("section").classes(
                        "sy-surface-subtle sy-policy-panel sy-roster-step-availability w-full p-4 mt-4"
                    ).props("data-testid=pre-generation-day-closure-panel"):
                        ui.label(t("pre_generation_day_closure")).classes("font-semibold")
                        ui.label(t("pre_generation_day_closure_detail")).classes(
                            "text-sm leading-6 text-[var(--sy-muted)] mt-1"
                        )
                        initial_closed_days = {
                            day.name if isinstance(day, SchoolDay) else str(day)
                            for day in (
                                initial_record.get("closedDays", ())
                                if initial_record
                                else ()
                            )
                        }
                        day_closure_controls: dict[str, object] = {}

                        def selected_closed_days() -> tuple[str, ...]:
                            return tuple(
                                day.name
                                for day in SchoolDay
                                if day_closure_controls[day.name].value
                            )

                        def day_closure_changed() -> None:
                            refresh_requirements()

                        with ui.row().classes(
                            "sy-choice-chips sy-day-closure-chips w-full gap-2 flex-wrap mt-3"
                        ).props(
                            f'role="group" aria-label="{attr(t("pre_generation_day_closure"))}" '
                            "data-testid=pre-generation-day-closures"
                        ):
                            for day in SchoolDay:
                                control = ui.checkbox(
                                    day_label(day),
                                    value=day.name in initial_closed_days,
                                    on_change=lambda _event: day_closure_changed(),
                                ).props("keep-color")
                                day_closure_controls[day.name] = control
                    def update_assist_mode(value: object) -> None:
                        mode = _assist_assignment_mode_code(
                            value,
                            fallback=LEGACY_FIXED_WEEKDAY,
                        )
                        advanced_rules_state["assist_mode"] = mode
                        explanation = advanced_rule_controls["assist_explanation"]
                        if explanation is not None:
                            explanation.set_text(t(_ASSIST_MODE_DETAIL_KEYS[mode]))

                    def update_history_priority(value: object) -> None:
                        normalized = min(
                            max(float(value), HISTORY_PRIORITY_MULTIPLIER_MIN),
                            HISTORY_PRIORITY_MULTIPLIER_MAX,
                        )
                        advanced_rules_state["history_priority"] = normalized
                        history_bar = advanced_rule_controls["history_bar"]
                        history_value = advanced_rule_controls["history_value"]
                        history_chart = advanced_rule_controls["history_chart"]
                        if history_bar is not None:
                            history_bar.style(f"width: {normalized / 2 * 100:.1f}%")
                        if history_value is not None:
                            history_value.set_text(f"{normalized:.1f}×")
                        if history_chart is not None:
                            history_chart.props(
                                f'aria-label="{attr(t("history_priority_chart_aria", value=f"{normalized:.1f}"))}"'
                            )

                    def refresh_history_priority() -> None:
                        selected = selected_week_start()
                        record = selected_week_record(selected)
                        value = float(
                            record.get("historyPriorityMultiplier", 1.0)
                            if record
                            else 1.0
                        )
                        advanced_rules_state["history_priority"] = value
                        control = advanced_rule_controls["history"]
                        if control is not None:
                            control.value = value
                            control.update()
                        update_history_priority(value)

                    def refresh_assist_assignment_mode() -> None:
                        selected = selected_week_start()
                        record = selected_week_record(selected)
                        mode = _assist_assignment_mode_code(
                            record.get("assistAssignmentMode") if record else None,
                            fallback=LEGACY_FIXED_WEEKDAY,
                        )
                        advanced_rules_state["assist_mode"] = mode
                        control = advanced_rule_controls["assist"]
                        if control is not None:
                            control.value = mode
                            control.update()
                        update_assist_mode(mode)

                    @ui.refreshable
                    def advanced_rule_panels() -> None:
                        """Create optional policy controls only after explicit disclosure."""

                        if not advanced_rules_state["mounted"]:
                            return
                        assist_mode = _assist_assignment_mode_code(
                            advanced_rules_state["assist_mode"],
                            fallback=LEGACY_FIXED_WEEKDAY,
                        )
                        history_value = float(advanced_rules_state["history_priority"])
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
                            ui.label(t("assist_assignment_mode_label")).classes(
                                "text-sm font-medium mt-3"
                            )
                            assist_control = ui.toggle(
                                options={
                                    LEGACY_FIXED_WEEKDAY: t("assist_assignment_mode_legacy"),
                                    FLEXIBLE_WEEKLY: t("assist_assignment_mode_flexible"),
                                },
                                value=assist_mode,
                            ).props(
                                "no-caps spread data-testid=assist-assignment-mode "
                                f'role="group" aria-label="{attr(t("assist_assignment_mode_label"))}" '
                                "aria-describedby=assist-mode-description"
                            ).classes("w-full sy-choice-chips")
                            advanced_rule_controls["assist"] = assist_control
                            explanation = ui.label(
                                t(_ASSIST_MODE_DETAIL_KEYS[assist_mode])
                            ).props(
                                "id=assist-mode-description aria-live=polite"
                            ).classes("text-sm leading-6 text-[var(--sy-muted)]")
                            advanced_rule_controls["assist_explanation"] = explanation
                            ui.label(t("assist_assignment_mode_constraints")).classes(
                                "text-xs leading-5 text-[var(--sy-muted)]"
                            )
                            assist_control.on_value_change(
                                lambda event: update_assist_mode(event.value)
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
                            history_control = ui.slider(
                                min=HISTORY_PRIORITY_MULTIPLIER_MIN,
                                max=HISTORY_PRIORITY_MULTIPLIER_MAX,
                                step=0.1,
                                value=history_value,
                            ).props(
                                f'label label-always snap data-testid=history-priority-multiplier '
                                f'aria-label="{attr(t("history_priority_label"))}"'
                            ).classes("w-full mt-3")
                            advanced_rule_controls["history"] = history_control
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
                                        ui.element("i").classes("sy-history-scale-tick").props(
                                            "aria-hidden=true"
                                        )
                                ui.label(t("history_priority_scale_detail")).classes(
                                    "sy-history-scale-help"
                                )

                            history_chart = ui.element("div").classes(
                                "sy-history-priority-chart sy-history-priority-meter "
                                "sy-roster-advanced-chart w-full"
                            ).props(
                                f'role=img aria-label="{attr(t("history_priority_chart_aria", value=f"{history_value:.1f}"))}" '
                                'data-testid=history-priority-chart'
                            )
                            advanced_rule_controls["history_chart"] = history_chart
                            with history_chart:
                                with ui.element("div").classes(
                                    "sy-history-priority-meter-row"
                                ):
                                    ui.label(t("history_priority_history_factor")).classes(
                                        "sy-history-priority-meter-label"
                                    )
                                    with ui.element("div").classes(
                                        "sy-history-priority-meter-track"
                                    ):
                                        history_bar = ui.element("span").classes(
                                            "sy-history-priority-meter-fill "
                                            "sy-history-priority-meter-fill--history"
                                        ).style(f"width: {history_value / 2 * 100:.1f}%")
                                        advanced_rule_controls["history_bar"] = history_bar
                                    value_label = ui.label(f"{history_value:.1f}×").classes(
                                        "sy-history-priority-meter-value"
                                    )
                                    advanced_rule_controls["history_value"] = value_label
                                with ui.element("div").classes(
                                    "sy-history-priority-meter-row"
                                ):
                                    ui.label(t("history_priority_week_factor")).classes(
                                        "sy-history-priority-meter-label"
                                    )
                                    with ui.element("div").classes(
                                        "sy-history-priority-meter-track"
                                    ):
                                        ui.element("span").classes(
                                            "sy-history-priority-meter-fill "
                                            "sy-history-priority-meter-fill--week"
                                        ).style("width: 50%")
                                    ui.label("1.0×").classes(
                                        "sy-history-priority-meter-value"
                                    )
                            ui.label(t("history_priority_chart_detail")).classes(
                                "sy-history-priority-chart-note sy-roster-advanced-chart"
                            )
                            history_control.on_value_change(
                                lambda event: update_history_priority(event.value)
                            )

                    def toggle_mobile_rules() -> None:
                        open_rules = not bool(advanced_rules_state["open"])
                        advanced_rules_state["open"] = open_rules
                        if open_rules and not advanced_rules_state["mounted"]:
                            advanced_rules_state["mounted"] = True
                            advanced_rule_panels.refresh()
                        open_literal = "true" if open_rules else "false"
                        ui.run_javascript(
                            "const card=document.querySelector('.sy-roster-generation-card');"
                            "const trigger=document.querySelector('[data-testid=roster-mobile-rules-toggle]');"
                            "if(!card||!trigger)return;"
                            f"card.classList.toggle('sy-roster-rules-open', {open_literal});"
                            f"trigger.setAttribute('aria-expanded', '{open_literal}');"
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
                    advanced_rule_panels()

                    def refresh_day_closures() -> None:
                        selected = selected_week_start()
                        record = selected_week_record(selected)
                        selected_days = {
                            day.name if isinstance(day, SchoolDay) else str(day)
                            for day in (
                                record.get("closedDays", ()) if record else ()
                            )
                        }
                        for day_name, control in day_closure_controls.items():
                            control.value = day_name in selected_days
                            control.update()

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
                            selected_closed_days(),
                        )
                        if requirements_state["rendered_key"] == query_key:
                            return
                        requirements_area.clear()
                        requirements = _safe_read_action(
                            lambda: workflow.generation_requirements(
                                week_start,
                                closed_days=selected_closed_days(),
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
                    ui.separator().classes("sy-roster-step-availability my-5")
                    ui.label(t("pre_generation_leave")).classes(
                        "sy-roster-step-availability text-base font-semibold"
                    )
                    ui.label(t("leave_generation_notice")).classes(
                        "sy-roster-step-availability text-sm text-[var(--sy-muted)]"
                    )
                    prefect_options = {
                        str(prefect["id"]): f"{prefect['nameZh']} ({prefect['form']} {prefect['className']})"
                        for prefect in prefects
                    }
                    with ui.row().classes(
                        "sy-mobile-field-row sy-roster-step-availability w-full gap-3 flex-wrap"
                    ):
                        leave_prefect = ui.select(
                            label=t("select_prefect"),
                            options=prefect_options,
                            value=None,
                            with_input=True,
                            clearable=True,
                        ).props(
                            "use-input input-debounce=120 data-testid=pre-generation-leave-prefect"
                        ).classes(
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
                                history_priority_multiplier=float(
                                    advanced_rules_state["history_priority"]
                                ),
                                assist_assignment_mode=_assist_assignment_mode_code(
                                    advanced_rules_state["assist_mode"],
                                    fallback=LEGACY_FIXED_WEEKDAY,
                                ),
                                closed_days=selected_closed_days(),
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
                    status = str(week["status"])
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
                                variant="primary",
                            )
                        with ui.expansion(t("mobile_more"), icon="more_horiz").classes(
                            "w-full"
                        ).props("dense data-testid=roster-history-more"):
                            ui.label(
                                f"{t('version')} {week['version']} · "
                                f"{t('history_priority_used', value=history_priority_value)} · "
                                f"{t('assist_assignment_mode_used', mode=_assist_assignment_mode_label(week.get('assistAssignmentMode')))}"
                            ).classes(
                                "sy-roster-week-meta text-sm text-[var(--sy-muted)]"
                            )
                            if status == "published":
                                with ui.row().classes(
                                    "sy-mobile-actions w-full justify-end gap-2 mt-2"
                                ):
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
            document = capture_roster_document(workflow, roster_week_id)
            # UI-owned copies may change in place after saving; the document may not.
            week = dict(document.snapshot.week)
            assignments = [dict(item) for item in document.snapshot.assignments]
        except (WorkflowError, RosterPresentationError):
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
                version_label = ui.label(f"{t('version')} {week['version']}").classes("text-[var(--sy-muted)]")
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
                    publish_gate = {"enabled": True}
                    with semantic_dialog(
                        title=t("publish_conflict_title"),
                        description=t("publish_conflict_body", version=reviewed_version),
                        persistent=True,
                        presentation="alert",
                        test_id="publish-conflict-dialog",
                    ) as publish_conflict_dialog:
                        def reload_after_publish_conflict() -> None:
                            publish_conflict_dialog.close()
                            ui.navigate.reload()

                        with ui.row().classes("sy-mobile-actions w-full justify-end mt-5"):
                            ui.button(
                                t("publish_conflict_review_action"),
                                icon="refresh",
                                on_click=reload_after_publish_conflict,
                            ).props("color=primary")

                    with semantic_dialog(
                        title=t("confirm_publish"),
                        description=t("publish_warning"),
                        persistent=True,
                        presentation="alert",
                        test_id="publish-confirmation-dialog",
                    ) as publish_dialog:
                        publish_version_label = ui.label(t("publish_reviewed_version", version=reviewed_version)).classes(
                            "text-sm font-medium mt-3"
                        )

                        async def publish() -> None:
                            publish_dialog.close()
                            if not publish_gate["enabled"]:
                                return
                            expected_version = reviewed_version
                            command_id = publish_command_id
                            result = await _run_with_progress(
                                lambda: workflow.publish(
                                    roster_week_id,
                                    expected_week_version=expected_version,
                                    command_id=command_id,
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
                            publish_confirm = ui.button(t("confirm_publish_action"), icon="publish", on_click=publish).props("color=primary")
                    publish_open = ui.button(t("publish"), icon="publish", on_click=publish_dialog.open).props("color=primary")
                elif week["status"] == "published":
                    ui.button(t("adjust_roster"), icon="swap_horiz", on_click=lambda: navigate_to(f"/rosters/{roster_week_id}/adjustments")).props("outline color=primary")
                    _render_withdraw_action(workflow, week, roster_week_id)
                if week["status"] != "withdrawn":
                    ui.button(
                        t("export_pdf"),
                        icon="ios_share",
                        on_click=lambda: _open_roster_export_dialog(roster_week_id),
                    ).props(
                        "outline color=primary data-testid=open-roster-export"
                    )
        if week["status"] == "draft":
            ui.label(t("draft_export_warning")).classes("sy-fg-attention font-medium")
        if week["status"] != "withdrawn":
            ui.label(t("export_pdf_notice")).classes("text-sm text-[var(--sy-muted)]")
        if week["status"] == "draft":
            ui.label(t("draft_preview")).classes("text-xl font-semibold mt-2")
            ui.label(t("draft_preview_notice")).classes("text-sm text-[var(--sy-muted)]")
            def draft_saved(updated: dict[str, object]) -> None:
                nonlocal reviewed_version, publish_command_id
                reviewed_version = int(updated["version"])
                publish_command_id = f"roster-publish-ui:{uuid4().hex}"
                version_label.set_text(f"{t('version')} {reviewed_version}")
                publish_version_label.set_text(t("publish_reviewed_version", version=reviewed_version))

            def draft_state_changed(view: _DraftCommitView) -> None:
                publish_gate["enabled"] = view.can_publish
                _sync_draft_publish_controls(view, (publish_open, publish_confirm), publish_dialog)
                if view.refresh_failed:
                    title, _ = _draft_commit_notice(view, current_locale())
                    version_label.set_text(title)

            _render_draft_grid_editor(
                workflow,
                roster_week_id,
                schedule_snapshot=(week, assignments),
                on_saved=draft_saved,
                on_state_change=draft_state_changed,
            )
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
            _render_roster_table(document.presentation)


@ui.page("/adjustments")
def adjustments_page() -> None:
    navigate_to("/rosters")


@ui.page("/rosters/{roster_week_id}/adjustments")
def adjustment_detail_page(roster_week_id: int) -> None:
    _install_roster_mobile_styles()
    workflow = get_workflow()
    with page_shell("/rosters"):
        try:
            document = capture_roster_document(workflow, roster_week_id)
            week = document.snapshot.week
        except (WorkflowError, RosterPresentationError):
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
        adjustment_targets = _published_adjustment_targets(document)
        adjustment_settled = False
        options = {key: _adjustment_target_label(item) for key, item in adjustment_targets.items()}
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
                    label=t("select_assignment"),
                    options=options,
                    value=None,
                    with_input=True,
                    clearable=True,
                ).props(
                    "use-input input-debounce=120 data-testid=adjustment-assignment"
                ).classes("w-full")

            with ui.element("section").classes("sy-adjustment-step"):
                replacement_heading = ui.label(t("adjustment_step_replacement")).classes("sy-adjustment-step-title")
                replacement_select = ui.select(
                    label=t("replacement"),
                    options={},
                    value=None,
                    with_input=True,
                    clearable=True,
                ).props(
                    "use-input input-debounce=120 data-testid=adjustment-replacement"
                ).classes("w-full")
                replacement_select.disable()
                loaded_substitutes: dict[str, dict[str, object]] = {}

                def clear_loaded_substitutes() -> None:
                    loaded_substitutes.clear()
                    replacement_select.options = {}
                    replacement_select.value = None
                    replacement_select.disable()
                    replacement_select.update()

            def load_substitutes() -> None:
                if adjustment_settled:
                    return
                clear_loaded_substitutes()
                target = adjustment_targets.get(str(assignment_select.value or ""))
                replacement_heading.set_text(t("adjustment_step_fill_vacancy" if target and target["status"] == "vacant" else "adjustment_step_replacement"))
                if target is None:
                    update_adjustment_state()
                    return

                def action() -> None:
                    candidates = workflow.recommend_substitutes(roster_week_id, int(assignment_select.value))
                    loaded_substitutes.clear()
                    loaded_substitutes.update({str(item["id"]): item for item in candidates})
                    replacement_select.options = (
                        {} if target["status"] == "vacant" else {"__vacant__": t("leave_vacant")}
                    )
                    replacement_select.options.update({str(item["id"]): f"{item['nameZh']} ({item['form']} {item['className']}; {item['historyWeight']:.1f})" for item in candidates})
                    replacement_select.value = None
                    replacement_select.enable()
                    replacement_select.update()
                    ui.notify(t("eligible_substitutes") if candidates else t("no_substitutes"), type="info")

                _safe_read_action(action, action_name="load_adjustment_candidates")
                update_adjustment_state()

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
                ui.link(t("adjustment_restore_path"), f"/rosters/{roster_week_id}/adjustments").classes(
                    "min-h-11 inline-flex items-center underline text-sm mt-2"
                ).props("data-testid=adjustment-review-again")
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
            # Its export action launches a separate page-owned sheet, so closing
            # this receipt cannot hide or detach PNG/PDF delivery controls.

            async def apply_adjustment() -> None:
                nonlocal adjustment_settled
                if adjustment_settled:
                    return
                target = adjustment_targets.get(str(assignment_select.value or ""))
                if not _adjustment_selection_complete(target, replacement_select.value, loaded_substitutes):
                    ui.notify(t("adjustment_selection_incomplete"), type="warning")
                    update_adjustment_state()
                    return
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
                    # This form represents the old version. No later field event
                    # may re-enable it while revocation or the receipt is pending.
                    adjustment_settled = True
                    for control in (assignment_select, replacement_select, reason_input, save_adjustment_button):
                        control.disable()
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
                    elif target["status"] == "vacant":
                        adjustment_receipt_summary.set_text(t(
                            "adjustment_receipt_filled",
                            replacement=result.replacement_prefect_name or "—",
                            weight=f"{result.weight:g}",
                        ))
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
            adjustment_summary = ui.label(t("adjustment_selection_incomplete")).classes(
                "sy-adjustment-selection-summary text-sm leading-6 text-[var(--sy-muted)]"
            ).props("role=status aria-live=polite data-testid=adjustment-selection-summary")
            with ui.row().classes("sy-adjustment-actions sy-adjustment-submit-dock w-full gap-3"):
                save_adjustment_button = ui.button(
                    t("apply_adjustment"), icon="save", on_click=apply_adjustment
                ).props("color=primary data-testid=apply-adjustment")
                save_adjustment_button.disable()

            def update_adjustment_state() -> None:
                assignment_value = str(assignment_select.value or "")
                replacement_value = str(replacement_select.value or "")
                complete = not adjustment_settled and _adjustment_selection_complete(
                    adjustment_targets.get(assignment_value), replacement_value, loaded_substitutes,
                )
                if complete:
                    adjustment_summary.set_text(
                        t(
                            "adjustment_selection_summary",
                            assignment=options.get(assignment_value, assignment_value),
                            replacement=replacement_select.options.get(
                                replacement_value, replacement_value
                            ),
                        )
                    )
                    save_adjustment_button.enable()
                else:
                    adjustment_summary.set_text(t("adjustment_selection_incomplete"))
                    save_adjustment_button.disable()

            assignment_select.on_value_change(lambda _event: load_substitutes())
            replacement_select.on_value_change(lambda _event: update_adjustment_state())
            update_adjustment_state()
