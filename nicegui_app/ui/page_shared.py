"""Multi-page NiceGUI workflows for daily devotion, roster work, and handover."""

from __future__ import annotations

import asyncio
import weakref
from collections.abc import Callable
from datetime import date, timedelta
from time import perf_counter
from typing import TypeVar

from nicegui import app, events, run, ui

from nicegui_app.contact import FEEDBACK_EMAIL, FEEDBACK_MAILTO_URL, GITHUB_REPOSITORY_URL, INSTAGRAM_PROFILE_URL
from nicegui_app.runtime import get_workflow
from nicegui_app.observability import (
    new_operation_reference,
    record_operator_event,
    record_operator_failure,
    record_operator_partial_failure,
)
from nicegui_app.services.roster_export import RosterPdfExport, build_fairness_audit_pdf, build_roster_pdf
from nicegui_app.services.roster_presentation import DAY_ORDER, build_roster_schedule, roster_display_label
from nicegui_app.services.roster_workflow import (
    CommittedWriteBackupError,
    WorkflowConflictError,
)
from nicegui_app.ui.html_safety import attr
from nicegui_app.ui.i18n import EN, current_locale, day_label, role_label, t
from nicegui_app.ui.navigation import navigate_to
from nicegui_app.ui.components import (
    empty_state as render_empty_state_component,
    responsive_table as render_responsive_table_component,
    status as render_status_component,
    workflow_step as render_workflow_step_component,
)
from nicegui_app.ui.downloads import deliver_generated_download
from nicegui_app.ui.operation_gate import claim_durable_operation, release_durable_operation
from nicegui_app.ui.page_access import is_demo_export
from nicegui_app.ui.pdf_delivery import build_native_pdf_share_js, can_offer_native_pdf_share
from nicegui_app.ui.sound import emit_interface_feedback, play_interface_sound
from roster_policy import ROOM_OPENING_TIME_WINDOWS, DutyPost

_OPERATION_FAILED = object()
_OperationResult = TypeVar("_OperationResult")
_DIALOG_DISMISSAL_SECONDS = 0.35


def _operation_error_message(reference: str) -> str:
    return f"{t('operation_error')} {t('error_reference', reference=reference)}"


def _delete_dialog_after_close(dialog, *, delay_seconds: float = _DIALOG_DISMISSAL_SECONDS) -> None:  # type: ignore[no-untyped-def]
    """Remove a one-shot dialog after its close transition has finished.

    NiceGUI dialogs stay in the client element registry when ``close()`` only
    hides them. Runtime-created forms therefore need explicit deletion, while
    page-level dialogs which are intentionally reopened must not use this
    helper. A weak reference avoids making the change callback itself keep the
    dialog alive, and the short delay preserves Quasar's focus-return and close
    transition behaviour.
    """
    dialog_reference = weakref.ref(dialog)
    cleanup_scheduled = False

    def delete_dialog() -> None:
        target = dialog_reference()
        if target is not None and not target.is_deleted:
            target.delete()

    def handle_value_change(event) -> None:  # type: ignore[no-untyped-def]
        nonlocal cleanup_scheduled
        if bool(event.value) or cleanup_scheduled:
            return
        cleanup_scheduled = True
        asyncio.get_running_loop().call_later(max(0.0, delay_seconds), delete_dialog)

    dialog.on_value_change(handle_value_change)


def _show_committed_without_backup(reference: str, *, recovery_required: bool = False) -> None:
    """Explain a committed write accurately and give two safe recovery paths."""
    with ui.dialog().props("persistent data-testid=committed-without-backup-dialog") as dialog, ui.card().classes(
        "sy-partial-success-dialog w-full max-w-lg p-6"
    ):
        with ui.row().classes("items-start gap-3 no-wrap"):
            ui.icon("warning_amber").classes("sy-partial-success-icon").props("aria-hidden=true")
            with ui.column().classes("gap-1"):
                ui.label(
                    t("committed_recovery_lock_title")
                    if recovery_required
                    else t("committed_without_backup_title")
                ).classes("text-lg font-semibold")
                ui.label(
                    t("committed_recovery_lock_body")
                    if recovery_required
                    else t("committed_without_backup_body")
                ).classes("text-sm leading-6 text-[var(--sy-muted)]")
                ui.label(t("support_reference_only", reference=reference)).classes("text-xs text-[var(--sy-muted)] mt-2")
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
                ).props("data-testid=partial-backup-settings-action")
    _delete_dialog_after_close(dialog)
    dialog.open()


def _next_monday() -> date:
    today = date.today()
    return today + timedelta(days=(-today.weekday()) % 7)


def _safe_read_action(action: Callable[[], None], *, action_name: str = "ui_read_action") -> None:
    """Run a short read-only UI action with a support reference on failure."""
    reference = new_operation_reference()
    started_at = perf_counter()
    record_operator_event(action=action_name, outcome="started", reference=reference)
    try:
        action()
    except Exception as error:
        record_operator_failure(error, action=action_name, reference=reference, started_at=started_at)
        emit_interface_feedback("error")
        ui.notify(_operation_error_message(reference), type="negative", timeout=8_000)
    else:
        record_operator_event(action=action_name, outcome="completed", reference=reference, started_at=started_at)


async def _run_with_progress(
    action: Callable[[], _OperationResult],
    *,
    title_key: str,
    working_key: str,
    icon: str,
    on_conflict: Callable[[WorkflowConflictError], None] | None = None,
) -> _OperationResult | object:
    """Run a durable local operation without leaving the operator guessing.

    The service action stays off the UI event loop.  This is intentionally a
    calm, short three-state indicator rather than a made-up percentage: the
    workflow owns the real transaction and backup timing, while the interface
    explains that the request has been received and is being processed safely.
    """
    operation_state = app.storage.client
    if not claim_durable_operation(operation_state, working_key):
        emit_interface_feedback("attention")
        ui.notify(t("operation_already_running"), type="warning", timeout=6_000)
        return _OPERATION_FAILED

    dialog = None
    reference = new_operation_reference()
    started_at = perf_counter()
    record_operator_event(action=working_key, outcome="started", reference=reference)
    try:
        with ui.dialog().props("persistent") as dialog, ui.card().classes("sy-progress-dialog w-full max-w-sm p-6"):
            with ui.row().classes("items-center gap-3"):
                ui.icon(icon).classes("sy-progress-dialog-icon").props("aria-hidden=true")
                with ui.column().classes("gap-0"):
                    ui.label(t(title_key)).classes("sy-progress-dialog-title")
                    status = ui.label(t("progress_preparing")).classes("sy-progress-dialog-status").props("aria-live=polite")
            progress = ui.linear_progress(value=0.14, show_value=False, color="primary").classes("w-full mt-6")
            ui.label(t("progress_keep_open")).classes("sy-progress-dialog-note mt-3")

        _delete_dialog_after_close(dialog)
        dialog.open()
        play_interface_sound("working")
        await asyncio.sleep(0.08)  # Allow the dialog to paint before work begins.
        status.set_text(t(working_key))
        progress.value = 0.56
        progress.update()
        result = await run.io_bound(action)
    except CommittedWriteBackupError as error:
        if dialog is not None:
            dialog.close()
        record_operator_partial_failure(error, action=working_key, reference=reference, started_at=started_at)
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
        emit_interface_feedback("attention")
        if on_conflict is None:
            ui.notify(t("roster_write_conflict"), type="warning", timeout=8_000)
        else:
            on_conflict(error)
        return _OPERATION_FAILED
    except Exception as error:
        record_operator_failure(error, action=working_key, reference=reference, started_at=started_at)
        emit_interface_feedback("error")
        ui.notify(_operation_error_message(reference), type="negative", timeout=8_000)
        return _OPERATION_FAILED
    else:
        status.set_text(t("progress_finalising"))
        progress.value = 1.0
        progress.update()
        await asyncio.sleep(0.13)
        record_operator_event(action=working_key, outcome="completed", reference=reference, started_at=started_at)
        play_interface_sound("success")
        return result
    finally:
        if dialog is not None:
            dialog.close()
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


def _prefect_directory_rows(prefects: list[dict[str, object]]) -> list[dict[str, object]]:
    """Create one localized directory model for desktop columns and phone cards."""
    return [
        {
            "name": item["nameZh"],
            "form": item["form"],
            "class": item["className"],
            "role": role_label(item["roleCode"]),
            "availability": " / ".join(day_label(day) for day in item["availableDays"]),
            "weight": item["historyWeight"],
            "duties": item["historyDuties"],
            "supportCodes": _prefect_support_codes(item),
        }
        for item in prefects
    ]


def _prefect_support_codes(item: dict[str, object]) -> tuple[str, ...]:
    codes: list[str] = []
    if float(item["historyWeight"]) == 0 and int(item["historyDuties"]) == 0:
        codes.append("new_prefect")
    if bool(item["needsMentoring"]):
        codes.append("needs_mentoring")
    return tuple(codes)


def _render_mobile_prefect_cards(rows: list[dict[str, object]]) -> None:
    """Keep a person's identity and availability readable without clipped columns."""
    with ui.element("section").classes("sy-prefect-mobile").props(f'aria-label="{attr(t("directory"))}"'):
        ui.label(t("mobile_directory_notice")).classes("sy-prefect-mobile-notice")
        for row in rows:
            card_label = f"{row['name']} · {row['form']} {row['class']} · {row['role']}"
            with ui.element("article").classes("sy-prefect-mobile-card").props(
                f'aria-label="{attr(card_label)}" data-testid="mobile-prefect-card"'
            ):
                with ui.row().classes("w-full items-start justify-between gap-3"):
                    with ui.column().classes("gap-0 min-w-0"):
                        ui.label(str(row["name"])).classes("sy-prefect-mobile-name")
                        ui.label(f"{row['form']} {row['class']}").classes("sy-prefect-mobile-class")
                    ui.label(str(row["role"])).classes("sy-prefect-mobile-role")
                ui.label(f"{t('availability')} · {row['availability']}").classes("sy-prefect-mobile-availability")
                ui.label(f"{t('support_status')} · {row['supportStatus']}").classes("sy-prefect-mobile-availability")
                with ui.row().classes("w-full items-center justify-between gap-3"):
                    ui.label(f"{t('history_weight')} · {row['weight']}").classes("sy-prefect-mobile-metric")
                    ui.label(f"{t('history_duties')} · {row['duties']}").classes("sy-prefect-mobile-metric")


def _render_roster_table(roster_week_id: int) -> None:
    """Render the same post-by-week verification model used by the PDF."""

    workflow = get_workflow()
    schedule = build_roster_schedule(workflow.assignments(roster_week_id))
    use_english = current_locale() == EN

    def cell_text(cell) -> str:  # type: ignore[no-untyped-def]
        if cell.status == "closed":
            return t("closed")
        if cell.status == "vacant":
            return t("vacant")
        return cell.prefect_name or t("vacant")

    rows: list[dict[str, object]] = []
    for schedule_row in schedule:
        start, end = schedule_row.spec.opening_time
        rows.append(
            {
                "post": schedule_row.spec.display_label,
                "time": f"{start}–{end}",
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
            "field": "post",
            "align": "left",
            "classes": "sy-roster-matrix-post",
            "headerClasses": "sy-roster-matrix-post",
        },
        *[
            {
                "name": day.name.lower(),
                "label": day_label(day),
                "field": day.name.lower(),
                "align": "center",
            }
            for day in DAY_ORDER
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
        for day_index, day in enumerate(DAY_ORDER):
            with ui.element("section").classes("sy-roster-mobile-day").props(
                f'aria-label="{attr(day_label(day))}"'
            ):
                ui.label(day_label(day)).classes("sy-roster-mobile-day-title")
                for schedule_row in schedule:
                    cell = schedule_row.cells[day_index]
                    start, end = schedule_row.spec.opening_time
                    label = schedule_row.spec.display_label
                    with ui.element("article").classes(
                        f"sy-roster-mobile-card sy-roster-mobile-card--{cell.status}"
                    ).props('data-testid="mobile-roster-card"'):
                        with ui.row().classes("w-full items-start justify-between gap-3 no-wrap"):
                            with ui.column().classes("gap-1 min-w-0"):
                                ui.label(label).classes("sy-roster-mobile-post")
                                ui.label(f"{start}–{end}").classes("sy-roster-mobile-time")
                            ui.label(t(cell.status)).classes("sy-roster-mobile-status")
                        ui.label(cell_text(cell)).classes("sy-roster-mobile-prefect")


async def _prepare_roster_pdf(
    roster_week_id: int,
    language: str,
    *,
    include_audit: bool = False,
    show_crest: bool = True,
    show_footer_note: bool = False,
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
    )
    if export is _OPERATION_FAILED:
        return None
    return export


async def _download_roster_pdf(
    roster_week_id: int,
    language: str,
    *,
    include_audit: bool = False,
    show_crest: bool = True,
    show_footer_note: bool = False,
) -> bool:
    export = await _prepare_roster_pdf(
        roster_week_id,
        language,
        include_audit=include_audit,
        show_crest=show_crest,
        show_footer_note=show_footer_note,
    )
    if export is None:
        return False
    deliver_generated_download(
        export.content,
        export.filename,
        media_type="application/pdf",
    )
    ui.notify(t("pdf_ready"), type="positive")
    return True


def _render_pdf_delivery_ready(container, export: RosterPdfExport) -> None:
    """Offer native file sharing only for the share-safe group schedule."""
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
                deliver_generated_download(
                    export.content,
                    export.filename,
                    media_type="application/pdf",
                )
                ui.notify(t("pdf_ready"), type="positive")

            def report_share_result(event: events.GenericEventArguments) -> None:
                args = event.args if isinstance(event.args, dict) else {}
                status = str(args.get("status", "failed"))
                if status == "shared":
                    ui.notify(t("pdf_share_completed"), type="positive")
                elif status == "cancelled":
                    ui.notify(t("pdf_share_cancelled"), type="info")
                elif status == "unsupported":
                    ui.notify(t("pdf_share_unsupported"), type="warning", timeout=8000)
                else:
                    ui.notify(t("pdf_share_failed"), type="warning", timeout=8000)

            with ui.row().classes("sy-mobile-actions w-full gap-2 mt-3"):
                if can_offer_native_pdf_share(export.content):
                    share_button = ui.button(t("share_schedule_pdf"), icon="ios_share").props(
                        "color=primary data-testid=share-schedule-pdf"
                    )
                    share_button.on(
                        "click",
                        report_share_result,
                        js_handler=build_native_pdf_share_js(
                            content=export.content,
                            filename=export.filename,
                            title=t("pdf_share_title"),
                            text=t("pdf_share_text"),
                        ),
                    )
                ui.button(t("download_prepared_pdf"), icon="download", on_click=download_again).props(
                    "outline color=primary data-testid=download-prepared-pdf"
                )
            ui.label(t("pdf_share_fallback_notice")).classes("text-xs text-[var(--sy-muted)] mt-3")


def _open_roster_export_dialog(roster_week_id: int) -> None:
    """Keep the share-safe one-page roster distinct from named internal audit data."""
    is_published = get_workflow().roster_week(roster_week_id)["status"] == "published"
    with ui.dialog() as dialog, ui.card().classes("sy-surface w-full max-w-2xl p-6"):
        with ui.row().classes("w-full items-center gap-4"):
            ui.icon("picture_as_pdf").classes("sy-export-symbol").props("aria-hidden=true")
            with ui.column().classes("gap-1"):
                ui.label(t("choose_pdf_export")).classes("text-xl font-semibold")
                ui.label(t("export_pdf_notice")).classes("text-sm text-[var(--sy-muted)]")
        prepared_signature: list[tuple[bool, bool] | None] = [None]

        async def deliver(language: str, *, include_audit: bool = False) -> None:
            selected_options = (bool(show_crest.value), bool(show_footer_note.value))
            if include_audit or not is_published:
                if await _download_roster_pdf(
                    roster_week_id,
                    language,
                    include_audit=include_audit,
                    show_crest=selected_options[0],
                    show_footer_note=selected_options[1],
                ):
                    dialog.close()
                return

            export = await _prepare_roster_pdf(
                roster_week_id,
                language,
                show_crest=selected_options[0],
                show_footer_note=selected_options[1],
            )
            if export is not None:
                if selected_options != (bool(show_crest.value), bool(show_footer_note.value)):
                    delivery_area.clear()
                    prepared_signature[0] = None
                    ui.notify(t("pdf_options_changed"), type="warning")
                    return
                _render_pdf_delivery_ready(delivery_area, export)
                prepared_signature[0] = selected_options
                ui.notify(t("pdf_delivery_ready_title"), type="positive")

        with ui.card().classes("sy-export-option w-full mt-5 p-5"):
            ui.label(t("group_schedule_export")).classes("text-lg font-semibold")
            ui.label(t("group_schedule_export_notice")).classes("text-sm text-[var(--sy-muted)] mt-1")
            with ui.row().classes("w-full gap-6 mt-4 flex-wrap"):
                show_crest = ui.switch(t("pdf_show_crest"), value=True).props("color=primary")
                show_footer_note = ui.switch(t("pdf_show_footer_note"), value=False).props("color=primary")
            ui.label(t("pdf_clean_export_hint")).classes("text-xs text-[var(--sy-muted)] mt-2")
            with ui.row().classes("sy-mobile-actions w-full gap-2 mt-4"):
                ui.button(
                    t("prepare_schedule_zh") if is_published else t("export_schedule_zh"),
                    icon="picture_as_pdf",
                    on_click=lambda: deliver("zh"),
                ).props("color=primary")
                ui.button(
                    t("prepare_schedule_en") if is_published else t("export_schedule_en"),
                    icon="picture_as_pdf",
                    on_click=lambda: deliver("en"),
                ).props("outline color=primary")
            delivery_area = ui.column().classes("w-full gap-0")

            def invalidate_prepared_pdf() -> None:
                if prepared_signature[0] is None:
                    return
                delivery_area.clear()
                prepared_signature[0] = None
                ui.notify(t("pdf_options_changed"), type="info")

            show_crest.on_value_change(lambda _event: invalidate_prepared_pdf())
            show_footer_note.on_value_change(lambda _event: invalidate_prepared_pdf())
        with ui.card().classes("sy-export-option sy-export-option--internal w-full mt-3 p-5"):
            ui.label(t("internal_audit_export")).classes("text-lg font-semibold")
            ui.label(t("internal_audit_export_notice")).classes("text-sm text-[var(--sy-muted)] mt-1")
            with ui.row().classes("sy-mobile-actions w-full gap-2 mt-4"):
                ui.button(t("export_audit_zh"), icon="fact_check", on_click=lambda: deliver("zh", include_audit=True)).props("outline color=primary")
                ui.button(t("export_audit_en"), icon="fact_check", on_click=lambda: deliver("en", include_audit=True)).props("outline color=primary")
        with ui.row().classes("sy-mobile-actions w-full justify-end mt-5"):
            ui.button(t("cancel"), icon="close", on_click=dialog.close).props("flat")
    _delete_dialog_after_close(dialog)
    dialog.open()


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
            ui.button(t("open_backup_settings"), icon="settings_backup_restore", on_click=lambda: navigate_to("/settings")).props("flat").classes("mt-2")


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
    illustrated: bool = False,
) -> None:
    """Compatibility wrapper for the public empty-state component.

    The legacy ``action_props`` argument is translated deliberately so existing
    browser selectors and destructive-action semantics survive the migration.
    """
    action_test_id = next(
        (
            token.split("=", 1)[1].strip('"\'')
            for token in action_props.split()
            if token.startswith("data-testid=")
        ),
        None,
    )
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
            ui.button(
                t(secondary_key),
                icon=secondary_icon,
                on_click=lambda: navigate_to(secondary_path),
            ).props(f"outline color=primary data-testid={test_id}-secondary")

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
    "_prefect_directory_rows",
    "_render_co_creation",
    "_render_empty_state",
    "_render_feedback_channel",
    "_render_flow_step",
    "_render_mobile_prefect_cards",
    "_render_operation_hint",
    "_render_responsive_table",
    "_render_roster_route_state",
    "_render_roster_table",
    "_render_storage_lifecycle",
    "_run_with_progress",
    "_safe_read_action",
    "_tone_badge",
)
