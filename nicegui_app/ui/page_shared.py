"""Multi-page NiceGUI workflows for daily devotion, roster work, and handover."""

from __future__ import annotations

import asyncio
import weakref
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from time import perf_counter
from typing import TypeVar
from uuid import uuid4

from nicegui import app, events, run, ui

from nicegui_app.contact import FEEDBACK_EMAIL, FEEDBACK_MAILTO_URL, GITHUB_REPOSITORY_URL
from nicegui_app.release_evidence import load_release_evidence
from nicegui_app.runtime import get_workflow
from nicegui_app.observability import (
    new_operation_reference,
    record_operator_event,
    record_operator_failure,
    record_operator_partial_failure,
)
from nicegui_app.services.roster_export import RosterPdfExport, build_fairness_audit_pdf, build_roster_pdf
from nicegui_app.services.summary_report_export import (
    build_duty_allocation_statement_pdf,
    build_summary_report_json,
    build_summary_report_pdf,
)
from nicegui_app.services.prefect_import_assistant import (
    ImportAssistantError,
    import_assistant_status,
    suggest_deepseek_column_mapping,
)
from nicegui_app.application_mode import current_application_mode
from nicegui_app.services.roster_workflow import (
    CommittedWriteBackupError,
    PrefectInput,
    PeriodSummaryReport,
    WorkflowConflictError,
    WorkflowError,
)
from nicegui_app.ui.i18n import ZH_HK, current_locale, day_label, post_label, role_label, t
from nicegui_app.ui.music import render_music_library_settings
from nicegui_app.ui.operation_gate import claim_durable_operation, release_durable_operation
from nicegui_app.ui.pdf_delivery import build_native_pdf_share_js, can_offer_native_pdf_share
from nicegui_app.ui.platform_summary import PlatformSummary, load_platform_summary
from nicegui_app.ui.shell import page_shell
from nicegui_app.ui.sound import play_interface_sound
from nicegui_app.ui.theme import current_theme
from nicegui_app.utils.prefect_file_import import (
    MAX_IMPORT_BYTES,
    ParsedImportFile,
    PrefectFileImportError,
    TARGET_FIELDS,
    parse_prefect_file,
    suggest_local_column_mapping,
    validate_target_mapping,
)
from nicegui_app.utils.prefect_import import (
    ImportPreview,
    parse_prefect_import_rows,
    parse_prefect_import_text,
    prefect_import_template_csv,
)
from roster_core import (
    HISTORY_PRIORITY_MULTIPLIER_MAX,
    HISTORY_PRIORITY_MULTIPLIER_MIN,
    select_daily_verse,
)
from roster_policy import ROOM_OPENING_TIME_WINDOWS, DutyPost, SchoolDay, required_posts_for_day

_OPERATION_FAILED = object()
_OperationResult = TypeVar("_OperationResult")
_DEVOTIONAL_GUIDANCE_THEMES = ("servant-leadership", "justice-fairness", "wisdom-discernment", "witness-light")
_DEVOTIONAL_COMFORT_THEMES = ("prayer-peace", "mercy-care", "perseverance", "faithfulness", "spiritual-formation")
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


def _show_committed_without_backup(reference: str) -> None:
    """Explain a committed write accurately and give two safe recovery paths."""
    with ui.dialog().props("persistent data-testid=committed-without-backup-dialog") as dialog, ui.card().classes(
        "sy-partial-success-dialog w-full max-w-lg p-6"
    ):
        with ui.row().classes("items-start gap-3 no-wrap"):
            ui.icon("warning_amber").classes("sy-partial-success-icon").props("aria-hidden=true")
            with ui.column().classes("gap-1"):
                ui.label(t("committed_without_backup_title")).classes("text-lg font-semibold")
                ui.label(t("committed_without_backup_body")).classes("text-sm leading-6 text-[var(--sy-muted)]")
                ui.label(t("support_reference_only", reference=reference)).classes("text-xs text-[var(--sy-muted)] mt-2")
        with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5 flex-wrap"):
            ui.button(
                t("reload_and_review"),
                icon="refresh",
                on_click=ui.navigate.reload,
            ).props("outline data-testid=partial-review-action")
            ui.button(
                t("open_backup_settings"),
                icon="settings_backup_restore",
                on_click=lambda: (dialog.close(), ui.navigate.to("/settings")),
            ).props("data-testid=partial-backup-settings-action")
    _delete_dialog_after_close(dialog)
    dialog.open()


def _next_monday() -> date:
    today = date.today()
    return today + timedelta(days=(-today.weekday()) % 7)


def _devotional_tone() -> str:
    preference = str(app.storage.user.get("devotional_tone", "auto"))
    if preference == "auto":
        return "comfort" if current_theme() == "dark" else "guidance"
    return preference if preference in {"guidance", "comfort"} else "guidance"


def _set_devotional_tone(value: str) -> None:
    if value not in {"auto", "guidance", "comfort"}:
        return
    app.storage.user["devotional_tone"] = value
    app.storage.user["dashboard_verse_offset"] = 0
    ui.navigate.reload()


def _dashboard_verse() -> object:
    offset = int(app.storage.user.get("dashboard_verse_offset", 0))
    themes = _DEVOTIONAL_COMFORT_THEMES if _devotional_tone() == "comfort" else _DEVOTIONAL_GUIDANCE_THEMES
    return select_daily_verse(date.today() + timedelta(days=offset), themes_any=themes)


def _refresh_dashboard_verse() -> None:
    app.storage.user["dashboard_verse_offset"] = int(app.storage.user.get("dashboard_verse_offset", 0)) + 1
    ui.navigate.reload()


def _safe_read_action(action: Callable[[], None], *, action_name: str = "ui_read_action") -> None:
    """Run a short read-only UI action with a support reference on failure."""
    reference = new_operation_reference()
    started_at = perf_counter()
    record_operator_event(action=action_name, outcome="started", reference=reference)
    try:
        action()
    except Exception as error:
        record_operator_failure(error, action=action_name, reference=reference, started_at=started_at)
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
        _show_committed_without_backup(reference)
        return _OPERATION_FAILED
    except WorkflowConflictError as error:
        if dialog is not None:
            dialog.close()
        record_operator_event(action=working_key, outcome="conflict", reference=reference, started_at=started_at)
        if on_conflict is None:
            ui.notify(t("roster_write_conflict"), type="warning", timeout=8_000)
        else:
            on_conflict(error)
        return _OPERATION_FAILED
    except Exception as error:
        record_operator_failure(error, action=working_key, reference=reference, started_at=started_at)
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
    ui.navigate.to(path)


def _render_feedback_channel(*, compact: bool = False) -> None:
    classes = "sy-feedback-channel sy-feedback-channel--compact" if compact else "sy-feedback-channel"
    with ui.element("section").classes(classes).props(
        f'aria-label="{t("feedback_channel_title")}" data-testid=feedback-channel'
    ):
        ui.icon("alternate_email").classes("sy-feedback-channel-icon").props("aria-hidden=true")
        with ui.column().classes("gap-1 min-w-0"):
            ui.label(t("feedback_channel_title")).classes("sy-feedback-channel-title")
            ui.label(t("feedback_channel_body")).classes("sy-feedback-channel-copy")
            with ui.row().classes("sy-feedback-channel-actions gap-4 flex-wrap"):
                ui.link(t("feedback_email_action"), FEEDBACK_MAILTO_URL).classes("sy-feedback-channel-action").props(
                    f'aria-label="{t("feedback_email_action")}: {FEEDBACK_EMAIL}"'
                )
                ui.link(t("github_repository_action"), GITHUB_REPOSITORY_URL).classes(
                    "sy-feedback-channel-action"
                ).props(f'target=_blank rel="noopener noreferrer" aria-label="{t("github_repository_action")}"')
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
                "post": post_label(assignment["postCode"]),
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

    with ui.element("section").classes("sy-roster-mobile").props(f'aria-label="{t("week_roster")}"'):
        ui.label(t("mobile_roster_notice")).classes("sy-roster-mobile-notice")
        for day_rows in grouped_rows.values():
            with ui.element("section").classes("sy-roster-mobile-day").props(f'aria-label="{day_rows[0]["day"]}"'):
                ui.label(str(day_rows[0]["day"])).classes("sy-roster-mobile-day-title")
                for row in day_rows:
                    card_label = f"{row['post']} · {row['time']} · {row['prefect']}"
                    with ui.element("article").classes("sy-roster-mobile-card").props(
                        f'aria-label="{card_label}" data-testid="mobile-roster-card"'
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
    with ui.element("section").classes("sy-prefect-mobile").props(f'aria-label="{t("directory")}"'):
        ui.label(t("mobile_directory_notice")).classes("sy-prefect-mobile-notice")
        for row in rows:
            card_label = f"{row['name']} · {row['form']} {row['class']} · {row['role']}"
            with ui.element("article").classes("sy-prefect-mobile-card").props(
                f'aria-label="{card_label}" data-testid="mobile-prefect-card"'
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
    workflow = get_workflow()
    rows = _roster_display_rows(workflow.assignments(roster_week_id))
    columns = [
        {"name": "day", "label": t("day"), "field": "day", "align": "left"},
        {"name": "post", "label": t("post"), "field": "post", "align": "left"},
        {"name": "time", "label": t("time"), "field": "time", "align": "left"},
        {"name": "prefect", "label": t("prefect"), "field": "prefect", "align": "left"},
        {"name": "weight", "label": t("weight"), "field": "weight", "align": "right"},
        {"name": "status", "label": t("status"), "field": "status", "align": "left"},
    ]
    ui.table(rows=rows, columns=columns, row_key="day").classes("sy-table sy-roster-desktop w-full")
    _render_mobile_roster_cards(rows)


async def _prepare_roster_pdf(
    roster_week_id: int,
    language: str,
    *,
    include_audit: bool = False,
    show_crest: bool = True,
    show_footer_note: bool = False,
) -> RosterPdfExport | None:
    """Create an in-memory local export rather than writing student data to a public URL."""
    export = await _run_with_progress(
        lambda: (
            build_fairness_audit_pdf(
                get_workflow(), roster_week_id, language=language, practice=current_application_mode().is_practice
            )  # type: ignore[arg-type]
            if include_audit
            else build_roster_pdf(
                get_workflow(),
                roster_week_id,
                language=language,
                practice=current_application_mode().is_practice,
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
    ui.download(export.content, export.filename)
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
                ui.download(export.content, export.filename)
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
    """Render one status vocabulary whose colour meaning is stable across pages."""
    # NiceGUI otherwise adds Quasar's ``bg-primary`` class.  Leaving that
    # default in place makes its ``background`` shorthand win over the
    # semantic tone token in some browsers, producing amber-on-blue pills.
    badge = ui.badge(text, color=None).classes(f"sy-status-badge sy-tone-{tone}")
    if props:
        badge.props(props)
    return badge


def _render_responsive_table(
    *,
    rows: list[dict[str, object]],
    columns: list[dict[str, object]],
    row_key: str,
    classes: str = "",
    test_id: str | None = None,
) -> None:
    """Render one data model as a desktop table and a labelled phone card grid.

    Quasar's ``$q.screen`` binding is not available while NiceGUI converts
    dynamic props.  Two presentation-only QTables avoid console errors without
    branching routes, persistence, policy, or localized display data.
    """
    props = f"data-testid={test_id}" if test_id else ""
    with ui.element("div").classes(f"sy-responsive-table w-full {classes}".strip()).props(props):
        ui.table(rows=rows, columns=columns, row_key=row_key).classes(
            "sy-table sy-responsive-table-desktop w-full"
        )
        ui.table(rows=rows, columns=columns, row_key=row_key).props("grid hide-header").classes(
            "sy-table sy-responsive-table-mobile w-full"
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
    """Render one ordered stage of the operator's weekly workflow."""
    with ui.element("li").classes(f"sy-flow-step sy-flow-step--{state}"):
        with ui.row().classes("w-full items-start justify-between gap-3"):
            ui.label(f"{number:02d}").classes("sy-flow-index")
            ui.icon(icon).classes("sy-flow-symbol").props("aria-hidden=true")
            _tone_badge(t(state_key), {"active": "action", "done": "stable"}.get(state, "neutral"))
        ui.label(t(title_key)).classes("sy-flow-title mt-5")
        ui.label(t(detail_key)).classes("sy-flow-copy mt-2")
        if action_key and action:
            props = "color=primary" if state == "active" else "outline color=primary"
            ui.button(t(action_key), icon="arrow_forward", on_click=action).props(props).classes("sy-flow-action mt-5")
        elif state == "pending":
            ui.label(t("flow_unavailable")).classes("sy-flow-disabled mt-5")


def _render_storage_lifecycle(workflow) -> None:  # type: ignore[no-untyped-def]
    """Explain the draft-to-ledger boundary at the point the operator acts on it."""
    status = workflow.backup_status()
    verification = status["latestVerification"]
    backup_verified = bool(verification and verification.get("valid"))
    with ui.element("section").classes("sy-storage-lifecycle w-full").props(f'aria-label="{t("storage_lifecycle_title")}"'):
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
            ui.button(t("open_backup_settings"), icon="settings_backup_restore", on_click=lambda: ui.navigate.to("/settings")).props("flat").classes("mt-2")


def _render_operation_hint(body_key: str, *, icon: str = "tips_and_updates") -> None:
    """Place one concise purpose-and-method cue immediately before an operator decision."""
    with ui.element("aside").classes("sy-operation-hint w-full").props(f'aria-label="{t("operation_hint")}"'):
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
    """Turn an empty result into one clear next action; reserve imagery for orientation moments."""
    variant = " sy-empty-state--illustrated" if illustrated else ""
    with ui.element("section").classes(f"sy-empty-state{variant} w-full").props(f'aria-label="{t(title_key)}"'):
        ui.icon(icon).classes("sy-empty-state-icon").props("aria-hidden=true")
        with ui.column().classes("items-center gap-1 max-w-lg"):
            ui.label(t(title_key)).classes("sy-empty-state-title")
            ui.label(t(body_key)).classes("sy-empty-state-copy")
        if action_key and action:
            ui.button(t(action_key), icon="arrow_forward", on_click=action).props(action_props).classes("mt-2")


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
        f'role=status aria-live=polite aria-label="{t(title_key)}" data-testid={test_id}'
    ):
        ui.icon(icon).classes("sy-empty-state-icon").props("aria-hidden=true")
        with ui.column().classes("items-center gap-1 max-w-lg"):
            ui.label(t(title_key)).classes("sy-empty-state-title")
            ui.label(t(body_key)).classes("sy-empty-state-copy")
        with ui.row().classes("justify-center gap-3 mt-2 flex-wrap"):
            ui.button(
                t(primary_key),
                icon="arrow_back",
                on_click=lambda: ui.navigate.to(primary_path),
            ).props(f"color=primary data-testid={test_id}-primary")
            ui.button(
                t(secondary_key),
                icon=secondary_icon,
                on_click=lambda: ui.navigate.to(secondary_path),
            ).props(f"outline color=primary data-testid={test_id}-secondary")

def _render_co_creation() -> None:
    """Render the shared, non-sensitive co-creation closing panel."""

    with ui.element("section").classes("sy-co-creation w-full").props(f'aria-label="{t("co_creation_title")}"'):
        ui.image("/assets/brand/sing-yin-crest-display-web.png").classes("sy-co-creation-crest").props(
            f'alt="{t("school_crest_alt")}" width=640 height=615 loading=lazy decoding=async'
        )
        ui.label(t("co_creation_title")).classes("sy-co-creation-title")
        ui.label(t("co_creation_team")).classes("sy-co-creation-team")
        ui.label(t("co_creation_body")).classes("sy-co-creation-copy")
        ui.label(t("co_creation_quote")).classes("sy-co-creation-quote")
        ui.label(t("co_creation_signature")).classes("sy-co-creation-signature")
        with ui.element("div").classes("sy-codex-closing"):
            ui.label(t("co_creation_codex_title")).classes("sy-codex-closing-title")
            ui.label(t("co_creation_codex_body")).classes("sy-codex-closing-copy")


# Route modules intentionally import private shared helpers through this explicit export.
__all__ = [name for name in globals() if not name.startswith('__')]
