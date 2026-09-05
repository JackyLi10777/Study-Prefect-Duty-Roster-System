"""Multi-page NiceGUI workflows for daily devotion, roster work, and handover."""

from __future__ import annotations

import asyncio
import base64
import math
import weakref
from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
from datetime import date, timedelta
from functools import partial
from time import perf_counter
from typing import TYPE_CHECKING, Any, TypeVar

from nicegui import app, context, events, run, ui

from nicegui_app.contact import FEEDBACK_EMAIL, FEEDBACK_MAILTO_URL, GITHUB_REPOSITORY_URL, INSTAGRAM_PROFILE_URL
from nicegui_app.runtime import get_workflow
from nicegui_app.observability import (
    new_operation_reference,
    record_operator_event,
    record_operator_failure,
    record_operator_partial_failure,
)
from nicegui_app.services.roster_export import RosterPdfExport, build_fairness_audit_pdf, build_roster_pdf, render_roster_pdf
from nicegui_app.services.roster_document import RosterDocument, capture_roster_document
from nicegui_app.services.roster_export_session import (
    ExportOptions, ExportRequest, NativeShareLease, NATIVE_SHARE_LEASE_SECONDS, RosterExportSession,
)
from nicegui_app.services.roster_presentation import (
    RosterCellState,
    RosterSchedulePresentation,
    build_roster_presentation,
    roster_display_label,
)
from nicegui_app.services.roster_workflow import (
    CommittedWriteBackupError,
    WorkflowConflictError,
)
from nicegui_app.ui.html_safety import attr, text as html_text
from nicegui_app.ui.i18n import EN, current_locale, day_label, role_label, t
from nicegui_app.ui.navigation import navigate_to
from nicegui_app.ui.components import (
    dialog as semantic_dialog,
    empty_state as render_empty_state_component,
    responsive_table as render_responsive_table_component,
    status as render_status_component,
    native_dialog as semantic_native_dialog,
    workflow_step as render_workflow_step_component,
)
from nicegui_app.ui.downloads import DownloadFailureTarget, deliver_generated_download
from nicegui_app.ui.operation_gate import claim_durable_operation, release_durable_operation
from nicegui_app.ui.page_access import is_demo_export
from nicegui_app.ui.native_file_share import (
    build_native_file_share_from_data_url_js,
    build_native_file_share_js,
    can_offer_native_file_share,
)
from nicegui_app.ui.pdf_delivery import can_offer_native_pdf_share
from nicegui_app.ui.sound import emit_interface_feedback, play_interface_sound
from roster_policy import ROOM_OPENING_TIME_WINDOWS, DutyPost

if TYPE_CHECKING:
    from nicegui_app.services.roster_image_export import RosterPngBundle, RosterPngFile

_OPERATION_FAILED = object()
_OperationResult = TypeVar("_OperationResult")
_ReadResult = TypeVar("_ReadResult")


@dataclass(frozen=True)
class _ExportFeedback:
    notify: Callable[..., None]
    download_target: DownloadFailureTarget


def _notify_export(feedback: _ExportFeedback | None, message: str, **options) -> None:
    (feedback.notify if feedback is not None else ui.notify)(message, **options)


def _deliver_export_file(content: bytes, filename: str, *, media_type: str,
                         feedback: _ExportFeedback | None = None) -> bool:
    options = {} if feedback is None else {
        "feedback": feedback.notify, "failure_target": feedback.download_target,
    }
    try:
        return deliver_generated_download(content, filename, media_type=media_type, **options)
    except Exception as error:
        reference = new_operation_reference()
        record_operator_failure(error, action="roster_export_delivery", reference=reference,
                                started_at=perf_counter())
        _notify_export(feedback, _operation_error_message(reference), type="negative")
        return False
_DIALOG_DISMISSAL_SECONDS = 0.35
_PROGRESS_REVEAL_DELAY_SECONDS = 0.14


def _operation_error_message(reference: str) -> str:
    return f"{t('operation_error')} {t('error_reference', reference=reference)}"


def _delete_dialog_after_close(
    dialog,
    *,
    delay_seconds: float = _DIALOG_DISMISSAL_SECONDS,
    lifetime_owner=None,
) -> None:  # type: ignore[no-untyped-def]
    """Remove a one-shot dialog after its close transition has finished.

    NiceGUI dialogs stay in the client element registry when ``close()`` only
    hides them. Runtime-created forms therefore need explicit deletion, while
    page-level dialogs which are intentionally reopened must not use this
    helper. A weak reference avoids making the change callback itself keep the
    dialog alive, and the short delay preserves Quasar's focus-return and close
    transition behaviour.
    """
    dialog_reference = weakref.ref(dialog)
    owner_reference = weakref.ref(lifetime_owner) if lifetime_owner is not None else lambda: None
    cleanup_scheduled = False

    def delete_dialog() -> None:
        target = dialog_reference()
        if target is not None and not target.is_deleted:
            target.delete()
        owner = owner_reference()
        if owner is not None and not owner.is_deleted:
            owner.delete()

    def handle_value_change(event) -> None:  # type: ignore[no-untyped-def]
        nonlocal cleanup_scheduled
        if bool(event.value) or cleanup_scheduled:
            return
        cleanup_scheduled = True
        asyncio.get_running_loop().call_later(max(0.0, delay_seconds), delete_dialog)

    dialog.on_value_change(handle_value_change)


def _release_operation_after_task_settles(
    operation_task: asyncio.Task[object],
    *,
    operation_state: MutableMapping[str, object],
) -> None:
    """Release a client operation claim only after its worker task is terminal.

    ``run.io_bound`` work can keep running in its executor after the page
    callback is cancelled or fails while constructing progress UI.  Retrieving
    the task exception prevents a detached failure from becoming an unhandled
    task warning; the workflow's transaction and audit log remain the durable
    source of the operation outcome.
    """
    try:
        operation_task.exception()
    except asyncio.CancelledError:
        pass
    finally:
        release_durable_operation(operation_state)


def _show_committed_without_backup(reference: str, *, recovery_required: bool = False) -> None:
    """Explain a committed write accurately and give two safe recovery paths."""
    title = (
        t("committed_recovery_lock_title")
        if recovery_required
        else t("committed_without_backup_title")
    )
    body = (
        t("committed_recovery_lock_body")
        if recovery_required
        else t("committed_without_backup_body")
    )
    with semantic_dialog(
        title=title,
        description=body,
        consequence=t("support_reference_only", reference=reference),
        persistent=True,
        presentation="alert",
        test_id="committed-without-backup-dialog",
    ) as dialog:
        with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5 flex-wrap"):
            ui.button(
                t("reload_and_review"),
                icon="refresh",
                on_click=ui.navigate.reload,
            ).props("outline data-testid=partial-review-action")
            if recovery_required:
                ui.button(
                    t("operator_guide"),
                    icon="menu_book",
                    on_click=lambda: (dialog.close(), navigate_to("/guide")),
                ).props("data-testid=partial-recovery-guide-action")
            else:
                ui.button(
                    t("open_backup_settings"),
                    icon="settings_backup_restore",
                    on_click=lambda: (dialog.close(), navigate_to("/settings")),
                ).props(
                    "data-testid=partial-backup-settings-action "
                    "data-sy-icon-motion-mode=rotary-navigation"
                )
    _delete_dialog_after_close(dialog)
    dialog.open()


def _next_monday() -> date:
    today = date.today()
    return today + timedelta(days=(-today.weekday()) % 7)


def _safe_read_action(
    action: Callable[[], _ReadResult],
    *,
    action_name: str = "ui_read_action",
    feedback: _ExportFeedback | None = None,
) -> _ReadResult | None:
    """Run a short read-only UI action with a support reference on failure."""
    reference = new_operation_reference()
    started_at = perf_counter()
    record_operator_event(action=action_name, outcome="started", reference=reference)
    try:
        result = action()
    except Exception as error:
        record_operator_failure(error, action=action_name, reference=reference, started_at=started_at)
        if feedback is None:
            emit_interface_feedback("error")
        _notify_export(feedback, _operation_error_message(reference), type="negative", timeout=8_000)
    else:
        record_operator_event(action=action_name, outcome="completed", reference=reference, started_at=started_at)
        return result


async def _run_with_progress(
    action: Callable[[], _OperationResult],
    *,
    title_key: str,
    working_key: str,
    icon: str,
    wait_kind: str = "operation",
    on_conflict: Callable[[WorkflowConflictError], None] | None = None,
    success_feedback: bool = True,
    feedback: _ExportFeedback | None = None,
) -> _OperationResult | object:
    """Run a durable local operation without leaving the operator guessing.

    The service action stays off the UI event loop.  This is intentionally a
    calm, short three-state indicator rather than a made-up percentage: the
    workflow owns the real transaction and backup timing, while the interface
    explains that the request has been received and is being processed safely.
    """
    operation_state = app.storage.client
    if not claim_durable_operation(operation_state, working_key):
        if feedback is None:
            emit_interface_feedback("attention")
        _notify_export(feedback, t("operation_already_running"), type="warning", timeout=6_000)
        return _OPERATION_FAILED

    dialog = None
    status = None
    progress_shell = None
    progress = None
    operation_task: asyncio.Task[_OperationResult] | None = None
    task_owns_operation_claim = False
    reference = new_operation_reference()
    started_at = perf_counter()
    record_operator_event(action=working_key, outcome="started", reference=reference)
    try:
        operation_task = asyncio.create_task(run.io_bound(action))
        operation_task.add_done_callback(
            partial(
                _release_operation_after_task_settles,
                operation_state=operation_state,
            )
        )
        task_owns_operation_claim = True
        await asyncio.wait(
            {operation_task},
            timeout=_PROGRESS_REVEAL_DELAY_SECONDS,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if not operation_task.done():
            if feedback is not None:
                _notify_export(feedback, t(title_key) + "\n" + t(working_key), type="ongoing")
            else:
                normalized_wait_kind = "ai" if wait_kind == "ai" else "operation"
                # NiceGUI creates a hidden canary alongside each portal dialog.
                # Give that canary a disposable owner, otherwise deleting only the
                # dialog leaves it (and its finalizer's dialog reference) in this page.
                with ui.element("div").classes("hidden") as progress_owner, semantic_dialog(
                    title=t(title_key),
                    description=t(working_key),
                    persistent=True,
                    presentation="status",
                    test_id="operation-progress-dialog",
                ) as dialog:
                    with ui.element("section").classes(
                        "sy-progress-dialog w-full"
                    ).props(
                        f"aria-busy=true data-progress-mode=indeterminate data-phase=working "
                        f"data-wait-kind={normalized_wait_kind}"
                    ) as progress_shell:
                        with ui.row().classes("items-center gap-3"):
                            with ui.element("span").classes("sy-progress-dialog-icon").props("aria-hidden=true"):
                                if normalized_wait_kind == "ai":
                                    ui.spinner(size="sm", color="primary").classes(
                                        "sy-progress-dialog-thinking"
                                    )
                                else:
                                    ui.icon(icon).classes("sy-progress-dialog-icon-work")
                                ui.icon("task_alt").classes("sy-progress-dialog-icon-success")
                            status = ui.label(t(working_key)).classes(
                                "sy-progress-dialog-status"
                            ).props("aria-live=polite")
                        progress = ui.linear_progress(show_value=False, color="primary").classes("w-full mt-4").props(
                            f'indeterminate aria-label="{attr(t("progress_indeterminate"))}"'
                        )
                        ui.label(t("progress_keep_open")).classes("sy-progress-dialog-note mt-3")

                _delete_dialog_after_close(dialog, lifetime_owner=progress_owner)
                dialog.open()
                play_interface_sound("working")
        result = await asyncio.shield(operation_task)
    except CommittedWriteBackupError as error:
        if dialog is not None:
            dialog.close()
        record_operator_partial_failure(error, action=working_key, reference=reference, started_at=started_at)
        if feedback is None:
            emit_interface_feedback("attention")
        _show_committed_without_backup(
            reference,
            recovery_required=get_workflow().maintenance_status().recovery_required,
        )
        return _OPERATION_FAILED
    except WorkflowConflictError as error:
        if dialog is not None:
            dialog.close()
        record_operator_event(action=working_key, outcome="conflict", reference=reference, started_at=started_at)
        if feedback is None:
            emit_interface_feedback("attention")
        if on_conflict is None:
            _notify_export(feedback, t("roster_write_conflict"), type="warning", timeout=8_000)
        else:
            on_conflict(error)
        return _OPERATION_FAILED
    except Exception as error:
        record_operator_failure(error, action=working_key, reference=reference, started_at=started_at)
        if feedback is None:
            emit_interface_feedback("error")
        _notify_export(feedback, _operation_error_message(reference), type="negative", timeout=8_000)
        return _OPERATION_FAILED
    else:
        if status is not None and progress_shell is not None and progress is not None:
            status.set_text(t("progress_complete"))
            progress_shell.props("data-phase=complete aria-busy=false")
            progress.props(remove="indeterminate")
            progress.value = 1.0
            progress.update()
        record_operator_event(action=working_key, outcome="completed", reference=reference, started_at=started_at)
        if success_feedback:
            play_interface_sound("success")
        return result
    finally:
        if dialog is not None:
            dialog.close()
        if not task_owns_operation_claim:
            release_durable_operation(operation_state)


def _navigate_with_feedback(path: str) -> None:
    play_interface_sound("navigation")
    navigate_to(path)


def _render_feedback_channel(*, compact: bool = False) -> None:
    classes = "sy-feedback-channel sy-feedback-channel--compact" if compact else "sy-feedback-channel"
    with ui.element("section").classes(classes).props(
        f'aria-label="{attr(t("feedback_channel_title"))}" data-testid=feedback-channel'
    ):
        ui.icon("alternate_email").classes("sy-feedback-channel-icon").props("aria-hidden=true")
        with ui.column().classes("gap-1 min-w-0"):
            ui.label(t("feedback_channel_title")).classes("sy-feedback-channel-title")
            ui.label(t("feedback_channel_body")).classes("sy-feedback-channel-copy")
            with ui.row().classes("sy-feedback-channel-actions gap-4 flex-wrap"):
                ui.link(t("feedback_email_action"), FEEDBACK_MAILTO_URL).classes("sy-feedback-channel-action").props(
                    f'aria-label="{attr(t("feedback_email_action"))}: {attr(FEEDBACK_EMAIL)}"'
                )
                ui.link(t("github_repository_action"), GITHUB_REPOSITORY_URL).classes(
                    "sy-feedback-channel-action"
                ).props(
                    f'target=_blank rel="noopener noreferrer" '
                    f'aria-label="{attr(t("github_repository_action"))}"'
                )
            ui.label(FEEDBACK_EMAIL).classes("sy-feedback-channel-address")
            ui.label(GITHUB_REPOSITORY_URL).classes("sy-feedback-channel-address")
            ui.label(t("feedback_channel_safe_note")).classes("sy-feedback-channel-note")


def _roster_display_rows(assignments: list[dict[str, object]]) -> list[dict[str, object]]:
    """Build one localized display model for both wide and phone roster views.

    Names and policy values come from the workflow unchanged.  The two visual
    presentations deliberately share this model so a phone never omits a duty
    that appears in the desktop verification table.
    """
    rows: list[dict[str, object]] = []
    for assignment in assignments:
        post = DutyPost[assignment["postCode"]]
        start, end = ROOM_OPENING_TIME_WINDOWS[post]
        rows.append(
            {
                "dayCode": assignment["day"],
                "day": day_label(assignment["day"]),
                "post": roster_display_label(
                    str(assignment["postCode"]),
                    int(assignment.get("slotIndex", 1)),
                ),
                "time": f"{start}-{end}",
                "prefect": assignment["prefectName"] if assignment["status"] == "active" else t("vacant"),
                "weight": assignment["weight"],
                "status": t("active") if assignment["status"] == "active" else t("vacant"),
            }
        )
    return rows


def _render_mobile_roster_cards(rows: list[dict[str, object]]) -> None:
    """Make each duty independently readable on a phone without horizontal swiping."""
    grouped_rows: dict[object, list[dict[str, object]]] = {}
    for row in rows:
        grouped_rows.setdefault(row["dayCode"], []).append(row)

    with ui.element("section").classes("sy-roster-mobile").props(f'aria-label="{attr(t("week_roster"))}"'):
        ui.label(t("mobile_roster_notice")).classes("sy-roster-mobile-notice")
        for day_rows in grouped_rows.values():
            with ui.element("section").classes("sy-roster-mobile-day").props(
                f'aria-label="{attr(day_rows[0]["day"])}"'
            ):
                ui.label(str(day_rows[0]["day"])).classes("sy-roster-mobile-day-title")
                for row in day_rows:
                    card_label = f"{row['post']} · {row['time']} · {row['prefect']}"
                    with ui.element("article").classes("sy-roster-mobile-card").props(
                        f'aria-label="{attr(card_label)}" data-testid="mobile-roster-card"'
                    ):
                        with ui.row().classes("w-full items-start justify-between gap-3 no-wrap"):
                            with ui.column().classes("gap-1 min-w-0"):
                                ui.label(str(row["post"])).classes("sy-roster-mobile-post")
                                ui.label(str(row["time"])).classes("sy-roster-mobile-time")
                            ui.label(str(row["status"])).classes("sy-roster-mobile-status")
                        ui.label(str(row["prefect"])).classes("sy-roster-mobile-prefect")
                        with ui.row().classes("w-full items-center justify-between gap-3"):
                            ui.label(t("prefect")).classes("sy-roster-mobile-meta-label")
                            ui.label(f"{t('weight')} · {row['weight']}").classes("sy-roster-mobile-meta")


def _render_roster_table(presentation: RosterSchedulePresentation) -> None:
    """Render one already-snapshotted matrix shared with the export model."""

    def cell_text(cell) -> str:  # type: ignore[no-untyped-def]
        if cell.state is RosterCellState.DAY_CLOSED:
            return t("draft_day_closed")
        if cell.state is RosterCellState.ROOM_CLOSED:
            return t("closed")
        if cell.state is RosterCellState.UNAVAILABLE:
            return t("draft_slot_unavailable")
        if cell.state is RosterCellState.VACANT:
            return t("vacant")
        return cell.prefect_name or t("vacant")

    def state_text(cell) -> str:  # type: ignore[no-untyped-def]
        if cell.state is RosterCellState.ASSIGNED:
            return t("active")
        return cell_text(cell)

    def dated_day_label(day) -> str:  # type: ignore[no-untyped-def]
        if day.duty_date is None:
            return day_label(day.day)
        return f"{day_label(day.day)} · {day.duty_date:%Y-%m-%d}"

    rows: list[dict[str, object]] = []
    for schedule_row in presentation.rows:
        start, end = schedule_row.spec.service_time
        rows.append(
            {
                "post": schedule_row.spec.display_label,
                "time": f"{start}–{end}",
                "postDisplay": (
                    f"{schedule_row.spec.display_label} · {start}–{end}"
                ),
                **{
                    cell.day.name.lower(): cell_text(cell)
                    for cell in schedule_row.cells
                },
            }
        )
    columns = [
        {
            "name": "post",
            "label": t("duty_position"),
            "field": "postDisplay",
            "align": "left",
            "classes": "sy-roster-matrix-post",
            "headerClasses": "sy-roster-matrix-post",
        },
        *[
            {
                "name": day.day.name.lower(),
                "label": dated_day_label(day),
                "field": day.day.name.lower(),
                "align": "center",
            }
            for day in presentation.days
        ],
    ]
    with ui.element("section").classes("sy-roster-matrix sy-roster-desktop w-full").props(
        f'aria-label="{attr(t("week_roster"))}" data-testid=roster-schedule-matrix'
    ):
        ui.table(rows=rows, columns=columns, row_key="post").classes("sy-table w-full").props(
            "flat bordered hide-bottom separator=cell"
        )

    with ui.element("section").classes("sy-roster-mobile").props(
        f'aria-label="{attr(t("week_roster"))}"'
    ):
        ui.label(t("mobile_roster_notice")).classes("sy-roster-mobile-notice")
        for day_index, day in enumerate(presentation.days):
            with ui.element("section").classes("sy-roster-mobile-day").props(
                f'aria-label="{attr(dated_day_label(day))}"'
            ):
                ui.label(dated_day_label(day)).classes("sy-roster-mobile-day-title")
                for schedule_row in presentation.rows:
                    cell = schedule_row.cells[day_index]
                    start, end = schedule_row.spec.service_time
                    label = schedule_row.spec.display_label
                    with ui.element("article").classes(
                        f"sy-roster-mobile-card sy-roster-mobile-card--{cell.state.value}"
                    ).props('data-testid="mobile-roster-card"'):
                        with ui.row().classes("w-full items-start justify-between gap-3 no-wrap"):
                            with ui.column().classes("gap-1 min-w-0"):
                                ui.label(label).classes("sy-roster-mobile-post")
                                ui.label(f"{start}–{end}").classes("sy-roster-mobile-time")
                            ui.label(state_text(cell)).classes("sy-roster-mobile-status")
                        ui.label(cell_text(cell)).classes("sy-roster-mobile-prefect")


async def _prepare_export_document(
    roster_week_id: int, request: ExportRequest, *, feedback: _ExportFeedback | None = None,
) -> RosterDocument | None:
    """Reuse the workspace document; only a new or invalidated workspace reads."""
    if request.document is not None:
        return request.document
    workflow = get_workflow()
    result = await _run_with_progress(
        lambda: capture_roster_document(workflow, roster_week_id),
        title_key="progress_export_title", working_key="progress_export_working", icon="description",
        success_feedback=False, feedback=feedback,
    )
    return None if result is _OPERATION_FAILED else result


async def _prepare_roster_pdf(
    roster_week_id: int,
    language: str,
    *,
    include_audit: bool = False,
    show_crest: bool = True,
    show_footer_note: bool = False,
    document: RosterDocument | None = None,
    feedback: _ExportFeedback | None = None,
) -> RosterPdfExport | None:
    """Create an in-memory local export rather than writing student data to a public URL."""
    # Resolve the verified page-scoped adapter and export mode while the
    # NiceGUI client context is still available. The PDF renderer runs in a
    # worker thread and must not try to rediscover browser identity there.
    workflow = get_workflow()
    practice = is_demo_export()
    export = await _run_with_progress(
        lambda: (
            build_fairness_audit_pdf(
                workflow, roster_week_id, language=language, practice=practice
            )  # type: ignore[arg-type]
            if include_audit
            else render_roster_pdf(
                document,
                language=language,
                practice=practice,
                show_crest=show_crest,
                show_footer_note=show_footer_note,
            ) if document is not None
            else build_roster_pdf(
                workflow,
                roster_week_id,
                language=language,
                practice=practice,
                show_crest=show_crest,
                show_footer_note=show_footer_note,
            )  # type: ignore[arg-type]
        ),
        title_key="progress_export_title",
        working_key="progress_export_working",
        icon="picture_as_pdf",
        success_feedback=False, feedback=feedback,
    )
    if export is _OPERATION_FAILED:
        return None
    return export


def _deliver_prepared_roster_pdf(export: RosterPdfExport, *, feedback: _ExportFeedback | None = None) -> bool:
    """Deliver exactly the PDF whose snapshot provenance was already checked."""

    if not _deliver_export_file(
        export.content,
        export.filename,
        media_type="application/pdf", feedback=feedback,
    ):
        return False
    _notify_export(feedback, t("pdf_ready"), type="positive")
    return True


def _finish_direct_pdf_delivery(
    session: RosterExportSession, request: ExportRequest, export: RosterPdfExport,
    *, feedback: _ExportFeedback | None = None,
) -> bool:
    """A failed admission or expired identity must not strand the UI as busy."""
    if not session.accepts(request):
        return False
    try:
        delivered = _deliver_prepared_roster_pdf(export, **({} if feedback is None else {"feedback": feedback}))
    except Exception:
        session.fail(request)
        raise
    return session.finish_direct_delivery(request, delivered=delivered)


def _pdf_delivery_permissions(
    export: RosterPdfExport,
    *,
    practice: bool,
) -> tuple[bool, bool]:
    """Return download/native-share policy from the rendered snapshot itself.

    A missing or unfamiliar provenance value fails closed. Draft PDFs remain
    downloadable for the existing internal checking workflow, but never gain
    native group sharing; withdrawn PDFs cannot be delivered at all.
    """

    roster_status = export.roster_status.strip().lower()
    allow_download = roster_status in {"draft", "published"}
    allow_native_share = roster_status == "published" and not practice
    return allow_download, allow_native_share


async def _prepare_roster_png_bundle(
    roster_week_id: int,
    language: str,
    *,
    document: RosterDocument | None = None,
    feedback: _ExportFeedback | None = None,
) -> RosterPngBundle | None:
    """Build both roster images from one atomic, page-authorized snapshot."""

    # Import lazily so routes which never open this dialog avoid image-renderer
    # startup work. Capture the verified workflow and access mode before the
    # renderer enters a worker thread.
    from nicegui_app.services.roster_image_export import build_roster_png_bundle, render_roster_png_bundle

    workflow = get_workflow()
    practice = is_demo_export()
    bundle = await _run_with_progress(
        lambda: render_roster_png_bundle(document, language=language, practice=practice)
        if document is not None else build_roster_png_bundle(
            workflow,
            roster_week_id,
            language=language,
            practice=practice,
        ),
        title_key="progress_roster_image_title",
        working_key="progress_roster_image_working",
        icon="image",
        success_feedback=False, feedback=feedback,
    )
    if bundle is _OPERATION_FAILED:
        return None
    return bundle


def _png_data_url(image: RosterPngFile) -> str:
    """Return a non-persistent preview URL for one prepared PNG."""

    encoded = base64.b64encode(image.content).decode("ascii")
    return f"data:{image.media_type};base64,{encoded}"


def _download_roster_png(image: RosterPngFile, *, feedback: _ExportFeedback | None = None) -> bool:
    if image.media_type != "image/png" or not can_offer_native_file_share(
        image.content,
        media_type=image.media_type,
    ):
        raise ValueError("Roster image delivery requires a valid bounded image/png file.")
    if not _deliver_export_file(
        image.content,
        image.filename,
        media_type=image.media_type, feedback=feedback,
    ):
        return False
    _notify_export(feedback, t("roster_image_downloaded"), type="positive")
    return True


def _mount_native_share_confirmation(
    container,
    event: events.GenericEventArguments,
    *,
    test_id: str,
    generation: str,
    result_guard: Callable[[object], bool],
    build_handler: Callable[[NativeShareLease, float], str],
    report_result: Callable[[events.GenericEventArguments], None],
    feedback: _ExportFeedback | None = None,
) -> Callable[[], None] | None:
    """Mount one expiring second gesture; no file is shared by this server call."""
    args = event.args if isinstance(event.args, dict) else {}
    prepared_at = args.get("preparedAt")
    if type(prepared_at) not in {int, float} or prepared_at < 0:
        return None
    try:
        if not math.isfinite(prepared_at):
            return None
    except OverflowError:
        return None
    if not result_guard(generation):
        return None
    lease = NativeShareLease(generation=generation, expires_at=perf_counter() + NATIVE_SHARE_LEASE_SECONDS)
    timer = [None]
    cleaned = [False]

    def cleanup() -> None:
        if cleaned[0]:
            return
        cleaned[0] = True
        lease.cancel()
        if timer[0] is not None:
            timer[0].cancel()
        if not container.is_deleted:
            container.clear()

    def expired() -> None:
        if lease.expire(now=perf_counter()):
            cleanup()
            if not container.is_deleted and result_guard(generation):
                with container:
                    _notify_export(feedback, t("native_share_prepare_expired"), type="info")

    def receive_result(result: events.GenericEventArguments) -> None:
        if container.is_deleted:
            cleanup()
            return
        payload = result.args if isinstance(result.args, dict) else {}
        if not lease.active or payload.get("token") != generation or payload.get("lease") != lease.token or not result_guard(generation):
            return
        status = payload.get("status")
        if status == "started":
            if not lease.started and not lease.start(payload.get("lease"), now=perf_counter()):
                cleanup()
            return
        if status == "expired":
            if lease.active and not lease.started:
                with container:
                    cleanup()
                    _notify_export(feedback, t("native_share_prepare_expired"), type="info")
            return
        if status in {"shared", "cancelled"} and not lease.started:
            return
        if status in {"shared", "cancelled", "failed", "unsupported"} and lease.finish(payload.get("lease"), now=perf_counter()):
            # Clearing the confirmation deletes the event sender's slot. Its
            # persistent container remains the owner of the completion notice.
            with container:
                cleanup()
                report_result(result)

    with container:
        ui.label(t("native_share_prepare_notice")).classes("text-sm text-[var(--sy-muted)]")
        with ui.element("div").classes("sy-native-actions mt-2"):
            confirm = ui.element("button").classes("sy-native-action sy-native-action--primary").props(
                f'type=button data-testid="confirm-{attr(test_id)}"'
            )
            with confirm:
                ui.label(t("native_share_open_system"))
            confirm.on(
                "click", receive_result,
                js_handler=build_handler(lease, float(prepared_at) + NATIVE_SHARE_LEASE_SECONDS * 1000),
            )
            cancel = ui.element("button").classes("sy-native-action").props(
                f'type=button data-testid="cancel-{attr(test_id)}"'
            )
            with cancel:
                ui.label(t("cancel"))
            cancel.on("click", cleanup)
    timer[0] = ui.timer(NATIVE_SHARE_LEASE_SECONDS, expired, once=True)
    return cleanup


def _render_pdf_delivery_ready(
    container,
    export: RosterPdfExport,
    *,
    allow_native_share: bool = True,
    delivery_guard: Callable[[], bool] | None = None,
    share_result_token: str | None = None,
    share_result_guard: Callable[[object], bool] | None = None,
    feedback: _ExportFeedback | None = None,
) -> Callable[[], None]:
    """Offer native file sharing only for the share-safe group schedule."""
    allow_native_share = allow_native_share and export.roster_status == "published"
    share_cleanup: list[Callable[[], None] | None] = [None]

    def clear_confirmation() -> None:
        if share_cleanup[0] is not None:
            share_cleanup[0]()
            share_cleanup[0] = None

    container.clear()
    with container:
        with ui.element("section").classes("sy-export-ready w-full mt-4 p-4").props(
            'aria-live="polite" data-testid="pdf-delivery-ready"'
        ):
            with ui.row().classes("w-full items-start gap-3"):
                ui.icon("task_alt").classes("sy-fg-stable text-xl").props("aria-hidden=true")
                with ui.column().classes("gap-1 min-w-0"):
                    ui.label(t("pdf_delivery_ready_title")).classes("font-semibold")
                    ui.label(export.filename).classes("text-xs text-[var(--sy-muted)] break-all")
                    ui.label(t("pdf_delivery_ready_notice")).classes("text-sm text-[var(--sy-muted)]")

            def download_again() -> None:
                if delivery_guard is not None and not delivery_guard():
                    return
                if not _deliver_export_file(
                    export.content,
                    export.filename,
                    media_type="application/pdf", feedback=feedback,
                ):
                    return
                _notify_export(feedback, t("pdf_ready"), type="positive")

            def report_share_result(event: events.GenericEventArguments) -> None:
                args = event.args if isinstance(event.args, dict) else {}
                if share_result_guard is not None and not share_result_guard(args.get("token")):
                    return
                status = str(args.get("status", "failed"))
                if status == "shared":
                    _notify_export(feedback, t("pdf_share_completed"), type="positive")
                elif status == "cancelled":
                    _notify_export(feedback, t("pdf_share_cancelled"), type="info")
                elif status == "unsupported":
                    _notify_export(feedback, t("pdf_share_unsupported"), type="warning", timeout=8000)
                else:
                    _notify_export(feedback, t("pdf_share_failed"), type="warning", timeout=8000)

            with ui.row().classes("sy-mobile-actions w-full gap-2 mt-3"):
                if allow_native_share and can_offer_native_pdf_share(export.content):
                    share_button = ui.button(t("share_schedule_pdf"), icon="ios_share").props(
                        "color=primary data-testid=share-schedule-pdf"
                    )
                    def prepare_share(event: events.GenericEventArguments) -> None:
                        clear_confirmation()
                        if delivery_guard is None or not delivery_guard():
                            return
                        if share_result_token is None or share_result_guard is None:
                            return
                        share_cleanup[0] = _mount_native_share_confirmation(
                            confirmation_area, event, test_id="share-schedule-pdf",
                            generation=share_result_token, result_guard=share_result_guard,
                            build_handler=lambda lease, deadline: build_native_file_share_js(
                                content=export.content, filename=export.filename, media_type="application/pdf",
                                title=t("pdf_share_title"), text=t("pdf_share_text"), result_token=share_result_token,
                                lease_token=lease.token, lease_expires_at=deadline,
                            ),
                            report_result=report_share_result, feedback=feedback,
                        )
                    share_button.on("click", prepare_share, js_handler="() => emit({preparedAt: performance.now()})")
                ui.button(t("download_prepared_pdf"), icon="download", on_click=download_again).props(
                    "outline color=primary data-testid=download-prepared-pdf"
                )
            ui.label(t("pdf_share_fallback_notice")).classes("text-xs text-[var(--sy-muted)] mt-3")
            confirmation_area = ui.element("div").classes("w-full mt-3")
    return clear_confirmation


def _render_png_delivery_ready(
    container,
    bundle: RosterPngBundle | None,
    *,
    allow_download: bool,
    allow_native_share: bool,
    practice: bool,
    view: dict[str, Any] | None = None,
    delivery_guard: Callable[[], bool] | None = None,
    share_result_token: str | None = None,
    share_result_guard: Callable[[object], bool] | None = None,
    feedback: _ExportFeedback | None = None,
) -> dict[str, Any]:
    """Update one compact preview view without remounting image/share controls.

    The image bytes are assigned directly to native ``img`` elements only after
    generation.  They are removed again on close, while the small element tree
    stays available for the next open.  Native buttons keep this frequently used
    phone flow well below the Quasar portal/listener footprint.
    """

    if view is None:
        active_bundle: list[RosterPngBundle | None] = [None]
        delivery_allowed = [False]
        current_guard: list[Callable[[], bool] | None] = [None]
        current_share_guard: list[Callable[[object], bool] | None] = [None]
        current_share_token: list[str | None] = [None]
        share_cleanup: list[Callable[[], None] | None] = [None]
        current_feedback: list[_ExportFeedback | None] = [None]
        with container:
            root = ui.element("section").classes("sy-export-ready w-full mt-4 p-4").props(
                'aria-live="polite" data-testid="roster-images-ready"'
            )
            with root:
                ui.label(t("roster_images_ready_title")).classes("font-semibold")
                notice = ui.label("").classes("text-sm text-[var(--sy-muted)]")

                with ui.element("div").classes(
                    "sy-roster-image-previews w-full grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4"
                ):
                    with ui.element("figure").classes("m-0 min-w-0"):
                        ui.label(t("avatar_preview_title")).classes("text-sm font-semibold mb-2")
                        avatar_image = ui.element("img").classes(
                            "sy-roster-avatar-preview mx-auto rounded-full aspect-square w-full max-w-[20rem] object-cover"
                        ).props(
                            f'alt="{attr(t("avatar_preview_alt"))}" '
                            "data-testid=roster-avatar-preview"
                        )
                        avatar_filename = ui.label("").classes(
                            "text-xs text-[var(--sy-muted)] break-all mt-2"
                        )
                    with ui.element("figure").classes("m-0 min-w-0"):
                        ui.label(t("whatsapp_detail_preview_title")).classes("text-sm font-semibold mb-2")
                        detail_image = ui.element("img").classes(
                            "w-full max-h-[26rem] object-contain bg-[var(--sy-surface-soft)]"
                        ).props(
                            f'alt="{attr(t("whatsapp_detail_preview_alt"))}" '
                            "data-testid=roster-whatsapp-preview"
                        )
                        detail_filename = ui.label("").classes(
                            "text-xs text-[var(--sy-muted)] break-all mt-2"
                        ).props("data-testid=roster-whatsapp-filename")

                def download_avatar() -> None:
                    current = active_bundle[0]
                    if current is not None and delivery_allowed[0] and (current_guard[0] is None or current_guard[0]()):
                        _download_roster_png(current.avatar, feedback=current_feedback[0])

                def download_detail() -> None:
                    current = active_bundle[0]
                    if current is not None and delivery_allowed[0] and (current_guard[0] is None or current_guard[0]()):
                        _download_roster_png(current.whatsapp, feedback=current_feedback[0])

                def report_share_result(event: events.GenericEventArguments) -> None:
                    args = event.args if isinstance(event.args, dict) else {}
                    if current_share_guard[0] is None or not current_share_guard[0](args.get("token")):
                        return
                    status = str(args.get("status", "failed"))
                    if status == "shared":
                        _notify_export(current_feedback[0], t("roster_image_share_completed"), type="positive")
                    elif status == "cancelled":
                        _notify_export(current_feedback[0], t("roster_image_share_cancelled"), type="info")
                    elif status == "unsupported":
                        _notify_export(current_feedback[0], t("roster_image_share_unsupported"), type="warning", timeout=8000)
                    else:
                        _notify_export(current_feedback[0], t("roster_image_share_failed"), type="warning", timeout=8000)

                def native_action(
                    label: str,
                    *,
                    test_id: str,
                    on_click=None,  # type: ignore[no-untyped-def]
                    primary: bool = False,
                ):
                    button = ui.element("button").classes(
                        "sy-native-action sy-native-action--primary" if primary else "sy-native-action"
                    ).props(f'type=button data-testid="{attr(test_id)}"')
                    with button:
                        ui.label(label)
                    if on_click is not None:
                        button.on("click", on_click)
                    return button

                with ui.element("div").classes("sy-native-actions w-full mt-4") as actions:
                    avatar_button = native_action(
                        t("download_roster_avatar"),
                        test_id="download-roster-avatar",
                        on_click=download_avatar,
                    )
                    share_button = None
                    if not practice:
                        share_button = native_action(
                            t("share_roster_detail"),
                            test_id="share-roster-detail",
                            primary=True,
                        )
                        def prepare_share(event: events.GenericEventArguments) -> None:
                            if share_cleanup[0] is not None:
                                share_cleanup[0]()
                                share_cleanup[0] = None
                            current = active_bundle[0]
                            if current is None or current.roster_status != "published" or not delivery_allowed[0]:
                                return
                            if current_guard[0] is None or not current_guard[0]():
                                return
                            if current_share_token[0] is None or current_share_guard[0] is None:
                                return
                            share_cleanup[0] = _mount_native_share_confirmation(
                                confirmation_area, event, test_id="share-roster-detail",
                                generation=current_share_token[0], result_guard=current_share_guard[0],
                                build_handler=lambda lease, deadline: build_native_file_share_from_data_url_js(
                                    preview_selector=f"#c{detail_image.id}", filename_selector=f"#c{detail_filename.id}",
                                    media_type="image/png", title=t("roster_image_share_title"), text=t("roster_image_share_text"),
                                    result_token_selector=f"#c{detail_image.id}", lease_token=lease.token, lease_expires_at=deadline,
                                ),
                                report_result=report_share_result, feedback=current_feedback[0],
                            )
                        share_button.on("click", prepare_share, js_handler="() => emit({preparedAt: performance.now()})")
                    detail_button = native_action(
                        t("download_roster_detail"),
                        test_id="download-roster-detail",
                        on_click=download_detail,
                    )
                confirmation_area = ui.element("div").classes("w-full mt-3")

        view = {
            "root": root,
            "notice": notice,
            "avatar_image": avatar_image,
            "detail_image": detail_image,
            "avatar_filename": avatar_filename,
            "detail_filename": detail_filename,
            "actions": actions,
            "avatar_button": avatar_button,
            "detail_button": detail_button,
            "share_button": share_button,
            "active_bundle": active_bundle,
            "delivery_allowed": delivery_allowed,
            "delivery_guard": current_guard,
            "share_result_guard": current_share_guard,
            "share_result_token": current_share_token,
            "share_cleanup": share_cleanup,
            "feedback": current_feedback,
            "practice": practice,
        }
        _clear_png_delivery_view(view)

    if bundle is None:
        return view

    if view["share_cleanup"][0] is not None:
        view["share_cleanup"][0]()
        view["share_cleanup"][0] = None
    active_bundle = view["active_bundle"]
    delivery_allowed = view["delivery_allowed"]
    view["feedback"][0] = feedback
    active_bundle[0] = bundle
    delivery_allowed[0] = allow_download
    view["delivery_guard"][0] = delivery_guard
    view["share_result_guard"][0] = share_result_guard
    view["share_result_token"][0] = share_result_token
    view["detail_image"].run_method("setAttribute", "data-share-token", share_result_token or "")
    if not allow_download:
        notice_key = (
            "roster_image_unavailable_withdrawn"
            if bundle.roster_status == "withdrawn"
            else "roster_images_draft_notice"
        )
    elif practice:
        notice_key = "roster_images_practice_notice"
    else:
        notice_key = "roster_images_ready_notice"
    view["notice"].set_text(t(notice_key))
    view["avatar_image"].run_method("setAttribute", "src", _png_data_url(bundle.avatar))
    view["detail_image"].run_method("setAttribute", "src", _png_data_url(bundle.whatsapp))
    view["avatar_filename"].set_text(bundle.avatar.filename)
    view["detail_filename"].set_text(bundle.whatsapp.filename)
    view["actions"].set_visibility(allow_download)
    if allow_download:
        view["avatar_button"].props(remove="disabled")
        view["detail_button"].props(remove="disabled")
    share_button = view["share_button"]
    if share_button is not None:
        share_button.set_visibility(
            allow_download
            and allow_native_share
            and can_offer_native_file_share(bundle.whatsapp.content, media_type="image/png")
        )
    view["root"].set_visibility(True)
    return view


def _clear_png_delivery_view(view: dict[str, Any] | None) -> None:
    """Drop all generated bytes while retaining the stable preview component tree."""

    if view is None:
        return
    view["active_bundle"][0] = None
    view["feedback"][0] = None
    view["delivery_allowed"][0] = False
    view["delivery_guard"][0] = None
    view["share_result_guard"][0] = None
    view["share_result_token"][0] = None
    if view["share_cleanup"][0] is not None:
        view["share_cleanup"][0]()
        view["share_cleanup"][0] = None
    view["detail_image"].run_method("removeAttribute", "data-share-token")
    view["avatar_image"].run_method("removeAttribute", "src")
    view["detail_image"].run_method("removeAttribute", "src")
    view["avatar_filename"].set_text("")
    view["detail_filename"].set_text("")
    view["actions"].set_visibility(False)
    share_button = view["share_button"]
    if share_button is not None:
        share_button.set_visibility(False)
    view["root"].set_visibility(False)


def _open_roster_export_dialog(roster_week_id: int) -> None:
    # Receipt buttons execute in their owning dialog's slot. A native dialog
    # mounted there is hidden together with the Quasar receipt as it closes.
    # Keep the cached export sheet page-owned, regardless of its launch point.
    with context.client.content:
        _open_page_owned_roster_export_dialog(roster_week_id)


def _open_page_owned_roster_export_dialog(roster_week_id: int) -> None:
    """Lazily mount and then reuse one compact native export sheet per page.

    The first click is the only point where the core is mounted. Advanced PDF,
    language, and audit controls are mounted only if the operator expands them.
    Closing removes every generated byte and image ``src`` immediately, while
    retaining the small native shell so repeated mobile use has constant DOM and
    listener cost.
    """

    client = context.client
    registry = getattr(client, "_sy_roster_export_dialogs", None)
    if not isinstance(registry, dict):
        registry = {}
        setattr(client, "_sy_roster_export_dialogs", registry)
    cached = registry.get(roster_week_id)
    if isinstance(cached, dict):
        cached_dialog = cached.get("dialog")
        cached_open = cached.get("open")
        if cached_dialog is not None and not cached_dialog.is_deleted and callable(cached_open):
            cached_open()
            return

    week = _safe_read_action(
        lambda: get_workflow().roster_week(roster_week_id), action_name="roster_export_open"
    )
    if week is None:
        return
    roster_status = str(week["status"])
    if roster_status == "withdrawn":
        ui.notify(t("roster_image_unavailable_withdrawn"), type="warning")
        return

    opened_as_published = roster_status == "published"
    practice = is_demo_export()
    default_language = "en" if current_locale() == EN else "zh"
    language_state = [default_language]
    show_crest_state = [True]
    show_footer_note_state = [False]
    prepared_signature: list[tuple[str, bool, bool] | None] = [None]
    prepared_bundle: list[RosterPngBundle | None] = [None]
    png_delivery_view: list[dict[str, Any] | None] = [None]
    pdf_delivery_area: list[Any | None] = [None]
    pdf_share_cleanup: list[Callable[[], None] | None] = [None]
    advanced_built = [False]
    advanced_open = [False]
    export_session = RosterExportSession(ExportOptions(language=default_language))
    close_pending = [False]
    reopen_requested = [False]

    def sync_feedback_generation() -> None:
        feedback_label.run_method("setAttribute", "data-export-generation", str(export_session.generation))

    def show_feedback(message: str, *, type: str = "info", **_options) -> None:
        if not export_session.opened or feedback_label.is_deleted:
            return
        urgent = type in {"negative", "warning"}
        feedback_label.props(
            f"role={'alert' if urgent else 'status'} aria-live={'assertive' if urgent else 'polite'} "
            f"aria-busy={str(type == 'ongoing').lower()}"
        )
        feedback_label.set_text(message)
        feedback_label.run_method("scrollIntoView", {"block": "nearest"})

    def feedback_for_generation(generation: int | None = None) -> _ExportFeedback:
        expected = export_session.generation if generation is None else generation

        def guarded(message: str, **options) -> None:
            if export_session.opened and export_session.generation == expected:
                show_feedback(message, **options)

        return _ExportFeedback(guarded, DownloadFailureTarget(f"c{feedback_label.id}", str(expected)))

    def reset_feedback() -> None:
        sync_feedback_generation()
        feedback_label.props("role=status aria-live=polite aria-busy=false")
        feedback_label.set_text(t("roster_image_export_notice"))

    def native_action(
        label: str,
        *,
        test_id: str,
        on_click=None,  # type: ignore[no-untyped-def]
        primary: bool = False,
        extra_props: str = "",
    ):
        classes = "sy-native-action sy-native-action--primary" if primary else "sy-native-action"
        button = ui.element("button").classes(classes).props(
            f'type=button data-testid="{attr(test_id)}" {extra_props}'.strip()
        )
        with button:
            ui.label(label)
        if on_click is not None:
            button.on("click", on_click)
        return button

    def selected_signature() -> tuple[str, bool, bool]:
        return language_state[0], show_crest_state[0], show_footer_note_state[0]

    def reset_delivery_views() -> None:
        if pdf_share_cleanup[0] is not None:
            pdf_share_cleanup[0]()
            pdf_share_cleanup[0] = None
        _clear_png_delivery_view(png_delivery_view[0])
        if pdf_delivery_area[0] is not None:
            pdf_delivery_area[0].clear()

    def invalidate_prepared_export(*, notify: bool = True) -> None:
        had_prepared = prepared_signature[0] is not None or prepared_bundle[0] is not None
        export_session.change_options(ExportOptions(*selected_signature()))
        reset_feedback()
        reset_delivery_views()
        prepared_signature[0] = None
        prepared_bundle[0] = None
        if notify and had_prepared:
            show_feedback(t("roster_export_options_changed"), type="info")

    async def document_for_request(request: ExportRequest) -> RosterDocument | None:
        result = await _prepare_export_document(roster_week_id, request,
                                                feedback=feedback_for_generation(request.generation))
        if result is None:
            export_session.fail(request)
            return None
        return result if export_session.accepts(request) else None

    def validate_delivery_revision() -> bool:
        document = export_session.document
        if document is None or not export_session.opened:
            return False
        # Authorization is rechecked by the page-bound workflow and again by
        # the download ticket issuer. Never issue a ticket for an old revision.
        current_week = _safe_read_action(
            lambda: get_workflow().roster_week(roster_week_id), action_name="roster_export_revision_check",
            feedback=feedback_for_generation(),
        )
        if current_week is None or not export_session.validate_revision(current_week):
            export_session.invalidate_source()
            sync_feedback_generation()
            reset_delivery_views()
            prepared_bundle[0] = None
            prepared_signature[0] = None
            if current_week is not None:
                show_feedback(t("roster_write_conflict"), type="warning", timeout=8000)
            return False
        return True

    async def deliver_pdf(
        *,
        include_audit: bool = False,
        audit_language: str | None = None,
    ) -> None:
        if export_session.phase == "preparing":
            show_feedback(t("operation_already_running"), type="warning")
            return
        request = export_session.begin()
        sync_feedback_generation()
        request_feedback = feedback_for_generation(request.generation)
        show_feedback(t("progress_export_working"), type="ongoing")
        reset_delivery_views()
        selected_options = selected_signature()
        selected_language = audit_language or selected_options[0]
        document = None if include_audit else await document_for_request(request)
        if not include_audit and document is None:
            return
        export = await _prepare_roster_pdf(
            roster_week_id,
            selected_language,
            include_audit=include_audit,
            show_crest=selected_options[1],
            show_footer_note=selected_options[2],
            document=document, feedback=request_feedback,
        )
        if export is None:
            export_session.fail(request)
            return
        if not export_session.accepts(request):
            return
        if include_audit:
            _finish_direct_pdf_delivery(export_session, request, export, feedback=request_feedback)
            return
        assert document is not None
        if not export_session.complete(request, document) or not validate_delivery_revision():
            return

        allow_download, allow_native_share = _pdf_delivery_permissions(export, practice=practice)
        if not allow_download:
            invalidate_prepared_export(notify=False)
            show_feedback(t("roster_image_unavailable_withdrawn"), type="warning")
            return
        if export.roster_status != "published":
            _deliver_prepared_roster_pdf(export, feedback=request_feedback)
            return

        prepared_bundle[0] = None
        _clear_png_delivery_view(png_delivery_view[0])
        assert pdf_delivery_area[0] is not None
        pdf_share_cleanup[0] = _render_pdf_delivery_ready(
            pdf_delivery_area[0],
            export,
            allow_native_share=allow_native_share,
            delivery_guard=validate_delivery_revision,
            share_result_token=str(request.generation),
            share_result_guard=export_session.accepts_share_result,
            feedback=request_feedback,
        )
        prepared_signature[0] = selected_options
        show_feedback(t("pdf_delivery_ready_title"), type="positive")

    async def deliver_images() -> None:
        if export_session.phase == "preparing":
            show_feedback(t("operation_already_running"), type="warning")
            return
        request = export_session.begin()
        sync_feedback_generation()
        request_feedback = feedback_for_generation(request.generation)
        show_feedback(t("progress_export_working"), type="ongoing")
        reset_delivery_views()
        selected_options = selected_signature()
        document = await document_for_request(request)
        if document is None:
            return
        bundle = await _prepare_roster_png_bundle(roster_week_id, selected_options[0],
                                                 document=document, feedback=request_feedback)
        if bundle is None:
            export_session.fail(request)
            return
        if not export_session.complete(request, document) or not validate_delivery_revision():
            return

        bundle_is_formal_published = bundle.roster_status == "published" and not practice
        allow_download = bundle_is_formal_published or (
            practice and bundle.roster_status in {"draft", "published"}
        )
        prepared_bundle[0] = bundle
        if allow_download:
            _download_roster_png(bundle.avatar, feedback=request_feedback)
        if pdf_delivery_area[0] is not None:
            pdf_delivery_area[0].clear()
        png_delivery_view[0] = _render_png_delivery_ready(
            png_delivery_area,
            bundle,
            allow_download=allow_download,
            allow_native_share=bundle_is_formal_published,
            practice=practice,
            view=png_delivery_view[0],
            delivery_guard=validate_delivery_revision,
            share_result_token=str(request.generation),
            share_result_guard=export_session.accepts_share_result,
            feedback=request_feedback,
        )
        prepared_signature[0] = selected_options
        if not allow_download:
            show_feedback(t("roster_images_draft_notice"), type="info")

    def handle_language_change(event: events.GenericEventArguments) -> None:
        args = event.args if isinstance(event.args, dict) else {}
        value = str(args.get("value", ""))
        if value not in {"zh", "en"} or value == language_state[0]:
            return
        language_state[0] = value
        invalidate_prepared_export()

    def handle_checkbox_change(
        event: events.GenericEventArguments,
        target: list[bool],
    ) -> None:
        args = event.args if isinstance(event.args, dict) else {}
        value = bool(args.get("checked"))
        if value == target[0]:
            return
        target[0] = value
        invalidate_prepared_export()

    def build_advanced_options() -> None:
        if advanced_built[0]:
            return
        advanced_built[0] = True
        with advanced_area:
            ui.label(t("roster_export_language")).classes("text-sm font-medium")
            selected_zh = " selected" if language_state[0] == "zh" else ""
            selected_en = " selected" if language_state[0] == "en" else ""
            language = ui.html(
                f'<option value="zh"{selected_zh}>{html_text(t("roster_export_language_zh"))}</option>'
                f'<option value="en"{selected_en}>{html_text(t("roster_export_language_en"))}</option>',
                tag="select",
            ).classes("sy-native-select").props(
                f'data-testid=roster-export-language aria-label="{attr(t("roster_export_language"))}"'
            )
            language.on(
                "change",
                handle_language_change,
                js_handler="event => emit({value: event.target.value})",
            )

            ui.label(t("group_schedule_export")).classes("text-base font-semibold mt-3")
            ui.label(t("group_schedule_export_notice")).classes(
                "text-sm text-[var(--sy-muted)]"
            )

            def native_checkbox(
                label: str,
                *,
                checked: bool,
                test_id: str,
                on_change,  # type: ignore[no-untyped-def]
            ) -> None:
                checked_attribute = " checked" if checked else ""
                control = ui.html(
                    f'<input type="checkbox" data-testid="{attr(test_id)}"{checked_attribute}>'
                    f"<span>{html_text(label)}</span>",
                    tag="label",
                ).classes("sy-native-check")
                control.on(
                    "change",
                    on_change,
                    js_handler="event => emit({checked: Boolean(event.target.checked)})",
                )

            native_checkbox(
                t("pdf_show_crest"),
                checked=show_crest_state[0],
                test_id="pdf-show-crest",
                on_change=lambda event: handle_checkbox_change(event, show_crest_state),
            )
            native_checkbox(
                t("pdf_show_footer_note"),
                checked=show_footer_note_state[0],
                test_id="pdf-show-footer-note",
                on_change=lambda event: handle_checkbox_change(event, show_footer_note_state),
            )
            ui.label(t("pdf_clean_export_hint")).classes("text-xs text-[var(--sy-muted)]")
            native_action(
                t("prepare_selected_schedule_pdf"),
                test_id="prepare-roster-pdf",
                on_click=deliver_pdf,
            )

            ui.label(t("internal_audit_export")).classes("text-base font-semibold mt-4")
            ui.label(t("internal_audit_export_notice")).classes(
                "text-sm text-[var(--sy-muted)]"
            )
            with ui.element("div").classes("sy-native-actions"):
                native_action(
                    t("export_audit_zh"),
                    test_id="export-audit-zh",
                    on_click=lambda: deliver_pdf(include_audit=True, audit_language="zh"),
                )
                native_action(
                    t("export_audit_en"),
                    test_id="export-audit-en",
                    on_click=lambda: deliver_pdf(include_audit=True, audit_language="en"),
                )
            pdf_delivery_area[0] = ui.element("div").classes("w-full")

    def toggle_advanced_options() -> None:
        if not advanced_built[0]:
            build_advanced_options()
        advanced_open[0] = not advanced_open[0]
        advanced_area.set_visibility(advanced_open[0])
        advanced_button.props(f'aria-expanded={str(advanced_open[0]).lower()}')

    with semantic_native_dialog(
        title=t("choose_pdf_export"),
        description=t("export_pdf_notice"),
        presentation="sheet",
        test_id="roster-export-dialog",
    ) as dialog:
        with ui.element("section").classes("sy-export-option sy-native-export-core w-full p-4"):
            ui.label(t("roster_image_export_title")).classes("text-base font-semibold")
            feedback_label = ui.label(t("roster_image_export_notice")).classes(
                "text-sm text-[var(--sy-muted)] whitespace-pre-line"
            ).props("role=status aria-live=polite aria-atomic=true aria-busy=false data-testid=roster-export-feedback")
            with ui.element("div").classes("sy-native-actions mt-3"):
                prepare_images_button = native_action(
                    t("generate_download_avatar")
                    if opened_as_published or practice
                    else t("generate_draft_image_preview"),
                    test_id="prepare-roster-images",
                    on_click=deliver_images,
                    primary=True,
                )
                advanced_button = native_action(
                    t("pdf_advanced_options"),
                    test_id="pdf-advanced-options",
                    on_click=toggle_advanced_options,
                    extra_props='aria-expanded=false aria-controls="roster-export-advanced-panel"',
                )
        advanced_area = ui.element("section").classes(
            "sy-export-option sy-native-export-advanced w-full p-4"
        ).props('id="roster-export-advanced-panel" data-testid=roster-export-advanced')
        advanced_area.set_visibility(False)
        png_delivery_area = ui.element("div").classes("w-full")
        with ui.element("div").classes("sy-native-actions sy-native-dialog-footer mt-4"):
            native_action(
                t("cancel"),
                test_id="close-roster-export",
                on_click=lambda: close_export_dialog(),
            )

    def release_export_dialog_resources() -> None:
        prepared_signature[0] = None
        prepared_bundle[0] = None
        reset_feedback()
        reset_delivery_views()
        advanced_open[0] = False
        advanced_area.set_visibility(False)
        advanced_button.props("aria-expanded=false")

    def finish_export_dialog_close() -> None:
        if close_pending[0]:
            # The session was already closed by our action. Acknowledge before
            # honoring reopen, so this delayed event can never clear new work.
            close_pending[0] = False
            if reopen_requested[0]:
                reopen_requested[0] = False
                open_export_dialog()
                return
        elif export_session.opened:
            # Escape/native dismissal closes on the browser before the server.
            export_session.close()
            release_export_dialog_resources()
        else:
            return
        ui.run_javascript(
            "window.setTimeout(() => { const dialog = document.querySelector("
            f"'#c{dialog.id}'); if (dialog?.open) return; "
            "const target = dialog?.__syReturnFocus; "
            "if (target instanceof HTMLElement && target.isConnected) "
            "target.focus({preventScroll: true}); }, 0)"
        )

    def close_export_dialog() -> None:
        if dialog.is_deleted or not export_session.opened:
            return
        close_pending[0] = True
        export_session.close()
        release_export_dialog_resources()
        dialog.run_method("close")

    def open_export_dialog() -> None:
        if close_pending[0]:
            reopen_requested[0] = True
            return
        if dialog.is_deleted or export_session.opened:
            return
        current_week = _safe_read_action(
            lambda: get_workflow().roster_week(roster_week_id), action_name="roster_export_reopen"
        )
        if current_week is None:
            return
        if current_week["status"] == "withdrawn":
            ui.notify(t("roster_image_unavailable_withdrawn"), type="warning")
            return
        prepare_images_button.default_slot.children[0].set_text(
            t("generate_download_avatar") if current_week["status"] == "published" or practice
            else t("generate_draft_image_preview")
        )
        export_session.open()
        reset_feedback()
        ui.run_javascript(
            "(() => { const dialog = document.querySelector("
            f"'#c{dialog.id}'); "
            "if (dialog) dialog.__syReturnFocus = document.activeElement; })()"
        )
        dialog.run_method("showModal")

    dialog.on("close", lambda _event: finish_export_dialog_close())
    dialog.on(
        "click",
        lambda _event: close_export_dialog(),
        js_handler="event => { if (event.target === event.currentTarget) emit({dismissed: true}); }",
    )
    registry[roster_week_id] = {"dialog": dialog, "open": open_export_dialog}
    open_export_dialog()


def _tone_badge(text: str, tone: str, *, props: str = ""):
    """Compatibility wrapper for the public semantic status component."""
    return render_status_component(text, tone, props=props)


def _render_responsive_table(
    *,
    rows: list[dict[str, object]],
    columns: list[dict[str, object]],
    row_key: str,
    classes: str = "",
    test_id: str | None = None,
) -> None:
    """Compatibility wrapper for the public responsive table component."""
    render_responsive_table_component(
        rows=rows,
        columns=columns,
        row_key=row_key,
        classes=classes,
        test_id=test_id,
    )


def _render_flow_step(
    *,
    number: int,
    title_key: str,
    detail_key: str,
    state: str,
    state_key: str,
    icon: str,
    action_key: str | None = None,
    action=None,  # type: ignore[no-untyped-def]
) -> None:
    """Compatibility wrapper for the public workflow-step component."""
    render_workflow_step_component(
        number=number,
        title=t(title_key),
        detail=t(detail_key),
        state=state,
        state_text=t(state_key),
        icon=icon,
        action_text=t(action_key) if action_key else None,
        on_action=action,
    )


def _render_storage_lifecycle(workflow) -> None:  # type: ignore[no-untyped-def]
    """Explain the draft-to-ledger boundary at the point the operator acts on it."""
    status = workflow.backup_status()
    verification = status["latestVerification"]
    backup_verified = bool(verification and verification.get("valid"))
    with ui.element("section").classes("sy-storage-lifecycle w-full").props(
        f'aria-label="{attr(t("storage_lifecycle_title"))}"'
    ):
        with ui.row().classes("w-full items-center justify-between gap-3 flex-wrap"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("database").classes("sy-storage-lifecycle-icon").props("aria-hidden=true")
                with ui.column().classes("gap-0"):
                    ui.label(t("storage_lifecycle_title")).classes("sy-storage-lifecycle-title")
                    ui.label(t("storage_lifecycle_intro")).classes("sy-storage-lifecycle-intro")
            _tone_badge(t("verified") if backup_verified else t("handover_attention"), "stable" if backup_verified else "attention")
        with ui.expansion(t("fairness_explained"), icon="account_balance").classes("sy-storage-lifecycle-expand mt-3"):
            with ui.element("div").classes("sy-storage-lifecycle-grid"):
                for icon, title_key, detail_key in (
                    ("edit_note", "storage_draft_title", "storage_draft_detail"),
                    ("fact_check", "storage_publish_title", "storage_publish_detail"),
                    ("swap_horiz", "storage_adjust_title", "storage_adjust_detail"),
                ):
                    with ui.element("article").classes("sy-storage-lifecycle-step"):
                        ui.icon(icon).classes("sy-storage-step-icon").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-storage-step-title")
                        ui.label(t(detail_key)).classes("sy-storage-step-copy")
            ui.label(t("storage_backup_verified") if backup_verified else t("storage_backup_attention")).classes("sy-storage-backup-note")
            ui.button(t("open_backup_settings"), icon="settings_backup_restore", on_click=lambda: navigate_to("/settings")).props(
                "flat data-sy-icon-motion-mode=rotary-navigation"
            ).classes("mt-2")


def _render_operation_hint(body_key: str, *, icon: str = "tips_and_updates") -> None:
    """Place one concise purpose-and-method cue immediately before an operator decision."""
    with ui.element("aside").classes("sy-operation-hint w-full").props(
        f'aria-label="{attr(t("operation_hint"))}"'
    ):
        ui.icon(icon).classes("sy-operation-hint-icon").props("aria-hidden=true")
        with ui.column().classes("gap-1"):
            ui.label(t("operation_hint")).classes("sy-operation-hint-title")
            ui.label(t(body_key)).classes("sy-operation-hint-copy")


def _render_empty_state(
    *,
    title_key: str,
    body_key: str,
    icon: str,
    action_key: str | None = None,
    action=None,  # type: ignore[no-untyped-def]
    action_props: str = "outline color=primary",
    action_test_id: str | None = None,
    illustrated: bool = False,
) -> None:
    """Compatibility wrapper for the public empty-state component.

    The legacy ``action_props`` argument is translated deliberately so existing
    browser selectors and destructive-action semantics survive the migration.
    """
    if "color=negative" in action_props:
        action_variant = "danger"
    elif "color=warning" in action_props or "color=attention" in action_props:
        action_variant = "attention"
    elif "flat" in action_props:
        action_variant = "quiet"
    elif "color=primary" in action_props and "outline" not in action_props:
        action_variant = "primary"
    else:
        action_variant = "secondary"
    render_empty_state_component(
        title=t(title_key),
        body=t(body_key),
        icon=icon,
        action_text=t(action_key) if action_key else None,
        on_action=action,
        action_variant=action_variant,
        action_test_id=action_test_id,
        illustrated=illustrated,
    )


def _render_roster_route_state(
    *,
    title_key: str,
    body_key: str,
    icon: str,
    test_id: str,
    primary_key: str,
    primary_path: str,
    secondary_key: str,
    secondary_path: str,
    secondary_icon: str = "settings_backup_restore",
) -> None:
    """Give stale or premature roster URLs an explicit, safe recovery route."""
    with ui.element("section").classes("sy-empty-state w-full").props(
        f'role=status aria-live=polite aria-label="{attr(t(title_key))}" '
        f'data-testid="{attr(test_id)}"'
    ):
        ui.icon(icon).classes("sy-empty-state-icon").props("aria-hidden=true")
        with ui.column().classes("items-center gap-1 max-w-lg"):
            ui.label(t(title_key)).classes("sy-empty-state-title")
            ui.label(t(body_key)).classes("sy-empty-state-copy")
        with ui.row().classes("justify-center gap-3 mt-2 flex-wrap"):
            ui.button(
                t(primary_key),
                icon="arrow_back",
                on_click=lambda: navigate_to(primary_path),
            ).props(f"color=primary data-testid={test_id}-primary")
            secondary_props = f"outline color=primary data-testid={test_id}-secondary"
            if secondary_icon == "settings_backup_restore":
                secondary_props += " data-sy-icon-motion-mode=rotary-navigation"
            ui.button(
                t(secondary_key),
                icon=secondary_icon,
                on_click=lambda: navigate_to(secondary_path),
            ).props(secondary_props)

def _render_co_creation() -> None:
    """Render the shared, non-sensitive co-creation closing panel."""

    with ui.element("section").classes("sy-co-creation w-full").props(
        "aria-labelledby=co-creation-title data-testid=co-creation-profile"
    ):
        ui.image("/assets/brand/li-chuangjie-banner.png").classes("sy-co-creation-banner").props(
            f'alt="{t("co_creation_banner_alt")}" width=1536 height=1024 loading=lazy decoding=async'
        )
        with ui.element("div").classes("sy-co-creation-profile"):
            ui.image("/assets/brand/li-chuangjie-avatar.jpg").classes("sy-co-creation-avatar").props(
                f'alt="{t("co_creation_avatar_alt")}" width=1024 height=1024 loading=lazy decoding=async'
            )
            with ui.column().classes("sy-co-creation-identity gap-1 min-w-0"):
                ui.label(t("co_creation_creator_name")).classes("sy-co-creation-name")
                ui.label(t("co_creation_creator_role")).classes("sy-co-creation-role")
                with ui.link(target=INSTAGRAM_PROFILE_URL).classes("sy-co-creation-social").props(
                    f'target=_blank rel="noopener noreferrer" '
                    f'aria-label="{attr(t("co_creation_instagram_accessible"))}"'
                ):
                    ui.icon("photo_camera").props("aria-hidden=true")
                    ui.label(t("co_creation_instagram_action"))
                    ui.icon("open_in_new").classes("text-sm").props("aria-hidden=true")
            ui.image("/assets/brand/sing-yin-crest-display-web.png").classes("sy-co-creation-crest").props(
                f'alt="{t("school_crest_alt")}" width=640 height=615 loading=lazy decoding=async'
            )
        ui.label(t("co_creation_title")).classes("sy-co-creation-title").props(
            "id=co-creation-title role=heading aria-level=2"
        )
        ui.label(t("co_creation_team")).classes("sy-co-creation-team")
        ui.label(t("co_creation_body")).classes("sy-co-creation-copy")
        ui.label(t("co_creation_quote")).classes("sy-co-creation-quote")
        ui.label(t("co_creation_signature")).classes("sy-co-creation-signature")
        with ui.element("div").classes("sy-codex-closing"):
            ui.label(t("co_creation_codex_title")).classes("sy-codex-closing-title")
            ui.label(t("co_creation_codex_body")).classes("sy-codex-closing-copy")


# Stable route-facing boundary. Framework objects, workflow models, translations,
# and utility dependencies are imported by their owning route modules directly.
# This list is deliberately explicit so adding an import to page_shared cannot
# silently expand every page's dependency surface again.
__all__ = (
    "_OPERATION_FAILED",
    "_delete_dialog_after_close",
    "_navigate_with_feedback",
    "_next_monday",
    "_open_roster_export_dialog",
    "_render_co_creation",
    "_render_empty_state",
    "_render_feedback_channel",
    "_render_flow_step",
    "_render_operation_hint",
    "_render_responsive_table",
    "_render_roster_route_state",
    "_render_roster_table",
    "_render_storage_lifecycle",
    "_run_with_progress",
    "_safe_read_action",
    "_tone_badge",
)
