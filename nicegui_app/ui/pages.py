"""Multi-page NiceGUI workflows for daily devotion, roster work, and handover."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from time import perf_counter
from typing import TypeVar
from uuid import uuid4

from nicegui import app, run, ui

from nicegui_app.contact import FEEDBACK_EMAIL, FEEDBACK_MAILTO_URL, GITHUB_REPOSITORY_URL
from nicegui_app.release_evidence import load_release_evidence
from nicegui_app.runtime import get_workflow
from nicegui_app.observability import (
    new_operation_reference,
    record_operator_event,
    record_operator_failure,
    record_operator_partial_failure,
)
from nicegui_app.services.roster_export import build_fairness_audit_pdf, build_roster_pdf
from nicegui_app.application_mode import current_application_mode
from nicegui_app.services.roster_workflow import (
    CommittedWriteBackupError,
    PrefectInput,
    WorkflowConflictError,
    WorkflowError,
)
from nicegui_app.ui.i18n import ZH_HK, current_locale, day_label, post_label, role_label, t
from nicegui_app.ui.music import render_music_library_settings
from nicegui_app.ui.operation_gate import claim_durable_operation, release_durable_operation
from nicegui_app.ui.platform_summary import PlatformSummary, load_platform_summary
from nicegui_app.ui.shell import page_shell
from nicegui_app.ui.sound import play_interface_sound
from nicegui_app.ui.theme import current_theme
from nicegui_app.utils.prefect_import import ImportPreview, parse_prefect_import_text, prefect_import_template_csv
from roster_core import select_daily_verse
from roster_policy import DUTY_TIME_WINDOWS, DutyPost, SchoolDay, required_posts_for_day

_OPERATION_FAILED = object()
_OperationResult = TypeVar("_OperationResult")
_DEVOTIONAL_GUIDANCE_THEMES = ("servant-leadership", "justice-fairness", "wisdom-discernment", "witness-light")
_DEVOTIONAL_COMFORT_THEMES = ("prayer-peace", "mercy-care", "perseverance", "faithfulness", "spiritual-formation")


def _operation_error_message(reference: str) -> str:
    return f"{t('operation_error')} {t('error_reference', reference=reference)}"


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
        with ui.row().classes("w-full justify-end gap-3 mt-5 flex-wrap"):
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

        dialog.open()
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
    except WorkflowConflictError:
        if dialog is not None:
            dialog.close()
        record_operator_event(action=working_key, outcome="conflict", reference=reference, started_at=started_at)
        ui.notify(t("roster_write_conflict"), type="warning", timeout=8_000)
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
        start, end = DUTY_TIME_WINDOWS[post]
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
        }
        for item in prefects
    ]


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


async def _download_roster_pdf(roster_week_id: int, language: str, *, include_audit: bool = False) -> bool:
    """Create an in-memory local export rather than writing student data to a public URL."""
    export = await _run_with_progress(
        lambda: (
            build_fairness_audit_pdf(
                get_workflow(), roster_week_id, language=language, practice=current_application_mode().is_practice
            )  # type: ignore[arg-type]
            if include_audit
            else build_roster_pdf(
                get_workflow(), roster_week_id, language=language, practice=current_application_mode().is_practice
            )  # type: ignore[arg-type]
        ),
        title_key="progress_export_title",
        working_key="progress_export_working",
        icon="picture_as_pdf",
    )
    if export is _OPERATION_FAILED:
        return False
    ui.download(export.content, export.filename)
    ui.notify(t("pdf_ready"), type="positive")
    return True


def _open_roster_export_dialog(roster_week_id: int) -> None:
    """Keep the share-safe one-page roster distinct from named internal audit data."""
    with ui.dialog() as dialog, ui.card().classes("sy-surface w-full max-w-2xl p-6"):
        with ui.row().classes("w-full items-center gap-4"):
            ui.icon("picture_as_pdf").classes("sy-export-symbol")
            with ui.column().classes("gap-1"):
                ui.label(t("choose_pdf_export")).classes("text-xl font-semibold")
                ui.label(t("export_pdf_notice")).classes("text-sm text-[var(--sy-muted)]")
        async def download(language: str, *, include_audit: bool = False) -> None:
            if await _download_roster_pdf(roster_week_id, language, include_audit=include_audit):
                dialog.close()

        with ui.card().classes("sy-export-option w-full mt-5 p-5"):
            ui.label(t("group_schedule_export")).classes("text-lg font-semibold")
            ui.label(t("group_schedule_export_notice")).classes("text-sm text-[var(--sy-muted)] mt-1")
            with ui.row().classes("w-full gap-2 mt-4"):
                ui.button(t("export_schedule_zh"), icon="picture_as_pdf", on_click=lambda: download("zh")).props("color=primary")
                ui.button(t("export_schedule_en"), icon="picture_as_pdf", on_click=lambda: download("en")).props("outline color=primary")
        with ui.card().classes("sy-export-option sy-export-option--internal w-full mt-3 p-5"):
            ui.label(t("internal_audit_export")).classes("text-lg font-semibold")
            ui.label(t("internal_audit_export_notice")).classes("text-sm text-[var(--sy-muted)] mt-1")
            with ui.row().classes("w-full gap-2 mt-4"):
                ui.button(t("export_audit_zh"), icon="fact_check", on_click=lambda: download("zh", include_audit=True)).props("outline color=primary")
                ui.button(t("export_audit_en"), icon="fact_check", on_click=lambda: download("en", include_audit=True)).props("outline color=primary")
        with ui.row().classes("w-full justify-end mt-5"):
            ui.button(t("cancel"), icon="close", on_click=dialog.close).props("flat")
    dialog.open()


def _tone_badge(text: str, tone: str, *, props: str = ""):
    """Render one status vocabulary whose colour meaning is stable across pages."""
    badge = ui.badge(text).classes(f"sy-status-badge sy-tone-{tone}")
    if props:
        badge.props(props)
    return badge


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
            ui.button(t(action_key), icon="arrow_forward", on_click=action).props(props).classes("mt-5")
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


@ui.page("/")
def dashboard_page() -> None:
    workflow = get_workflow()
    verse = _dashboard_verse()
    locale_is_zh = current_locale() == ZH_HK
    reference = verse.reference_zh if locale_is_zh else verse.reference_en
    scripture = verse.scripture_zh if locale_is_zh else verse.scripture_en
    reflection = verse.reflection_zh if locale_is_zh else verse.reflection_en
    with page_shell("dashboard", "/", music_context="dashboard"):
        with ui.element("section").classes("sy-daily-start w-full").props(f'aria-label="{t("daily_verse")}"'):
            with ui.row().classes("w-full items-start gap-4 flex-wrap"):
                ui.icon("menu_book").classes("sy-daily-start-icon").props("aria-hidden=true")
                with ui.column().classes("grow min-w-[240px] gap-1"):
                    ui.label(t("daily_verse")).classes("sy-daily-start-kicker")
                    ui.label(scripture).classes("sy-daily-start-verse")
                    ui.label(reference).classes("sy-daily-start-reference")
                with ui.column().classes("sy-devotional-controls gap-2 items-end"):
                    tone_preference = str(app.storage.user.get("devotional_tone", "auto"))
                    tone_select = ui.select(
                        label=t("devotional_tone_label"),
                        options={
                            "auto": t("devotional_tone_auto"),
                            "guidance": t("devotional_tone_guidance"),
                            "comfort": t("devotional_tone_comfort"),
                        },
                        value=tone_preference if tone_preference in {"auto", "guidance", "comfort"} else "auto",
                    ).props("dense outlined options-dense").classes("sy-devotional-tone-select")
                    tone_select.on_value_change(lambda event: _set_devotional_tone(str(event.value)))
                    ui.button(t("refresh_verse"), icon="refresh", on_click=_refresh_dashboard_verse).props("flat").classes("sy-daily-start-refresh")
            with ui.expansion(reflection.get("title", ""), icon="auto_stories").classes("sy-daily-start-reflection mt-3"):
                ui.label(reflection.get("body", "")).classes("text-sm leading-6 text-[var(--sy-muted)] p-1")
                if reflection.get("prayer"):
                    ui.label(f"{t('prayer')}: {reflection['prayer']}").classes("mt-3 text-sm italic text-[var(--sy-muted)]")
        weeks = workflow.roster_weeks()
        latest = weeks[0] if weeks else None
        with ui.row().classes("sy-dashboard-grid sy-dashboard-grid--single w-full items-stretch"):
            with ui.element("section").classes("sy-workbench grow min-w-[620px]"):
                with ui.row().classes("w-full items-start justify-between gap-5 flex-wrap"):
                    with ui.column().classes("gap-1"):
                        ui.label(t("workbench_title")).classes("sy-workbench-title")
                        ui.label(t("workbench_intro")).classes("sy-workbench-intro")
                    if latest is None:
                        _tone_badge(t("flow_no_roster"), "attention")
                    elif latest["status"] == "draft":
                        _tone_badge(t("flow_draft_ready"), "action")
                    else:
                        _tone_badge(t("flow_published_ready"), "stable")
                with ui.element("ol").classes("sy-flow mt-7").props(f'aria-label="{t("workbench_title")}"'):
                    if latest is None:
                        _render_flow_step(number=1, title_key="flow_generate", detail_key="flow_generate_detail", state="active", state_key="flow_current", icon="edit_calendar", action_key="create_draft", action=lambda: _navigate_with_feedback("/rosters"))
                        _render_flow_step(number=2, title_key="flow_review", detail_key="flow_review_detail", state="pending", state_key="flow_waiting", icon="fact_check")
                        _render_flow_step(number=3, title_key="flow_leave", detail_key="flow_leave_detail", state="pending", state_key="flow_waiting", icon="event_busy")
                    elif latest["status"] == "draft":
                        _render_flow_step(number=1, title_key="flow_generate", detail_key="flow_generate_detail", state="done", state_key="flow_done", icon="edit_calendar")
                        _render_flow_step(number=2, title_key="flow_review", detail_key="flow_review_detail", state="active", state_key="flow_current", icon="fact_check", action_key="flow_open_draft", action=lambda item=latest: _navigate_with_feedback(f"/rosters/{item['id']}"))
                        _render_flow_step(number=3, title_key="flow_leave", detail_key="flow_leave_detail", state="pending", state_key="flow_waiting", icon="event_busy")
                    else:
                        _render_flow_step(number=1, title_key="flow_generate", detail_key="flow_generate_detail", state="done", state_key="flow_done", icon="edit_calendar")
                        _render_flow_step(number=2, title_key="flow_review", detail_key="flow_review_detail", state="done", state_key="flow_done", icon="fact_check", action_key="flow_open_published", action=lambda item=latest: _navigate_with_feedback(f"/rosters/{item['id']}"))
                        _render_flow_step(number=3, title_key="flow_leave", detail_key="flow_leave_detail", state="active", state_key="flow_current", icon="event_busy", action_key="flow_open_adjustment", action=lambda item=latest: _navigate_with_feedback(f"/rosters/{item['id']}/adjustments"))
                ui.button(t("first_time_link"), icon="play_circle", on_click=lambda: ui.navigate.to("/getting-started")).props("flat").classes("mt-5")
        ui.label(t("current_rosters")).classes("text-xl font-semibold mt-3")
        weeks = weeks[:3]
        if not weeks:
            _render_empty_state(
                title_key="empty_roster_title",
                body_key="empty_roster_detail",
                icon="event_note",
                action_key="empty_start_action",
                action=lambda: _navigate_with_feedback("/rosters"),
                illustrated=True,
            )
        else:
            for week in weeks:
                with ui.row().classes("sy-surface w-full items-center justify-between px-5 py-4"):
                    with ui.column().classes("gap-0"):
                        ui.label(str(week["weekStart"])).classes("font-semibold")
                        ui.label(f"{t('version')} {week['version']}").classes("text-sm text-[var(--sy-muted)]")
                    _tone_badge(t("published") if week["status"] == "published" else t("draft"), "stable" if week["status"] == "published" else "action")
                    ui.button(t("view"), icon="arrow_forward", on_click=lambda item=week: ui.navigate.to(f"/rosters/{item['id']}")).props("flat")


@ui.page("/dashboard")
def dashboard_alias() -> None:
    ui.navigate.to("/")


@ui.page("/getting-started")
def getting_started_page() -> None:
    with page_shell("getting_started", "/getting-started", music_context="getting_started"):
        with ui.element("section").classes("sy-onboarding-intro w-full max-w-4xl"):
            with ui.column().classes("gap-2"):
                ui.label(t("getting_started")).classes("sy-page-title")
                ui.label(t("new_user_intro")).classes("text-[var(--sy-muted)] max-w-2xl")
            ui.icon("calendar_month").classes("sy-onboarding-symbol")
        steps = (
            ("new_user_step_start", "new_user_step_start_detail"),
            ("new_user_step_prepare", "new_user_step_prepare_detail"),
            ("new_user_step_week", "new_user_step_week_detail"),
        )
        for title_key, detail_key in steps:
            with ui.card().classes("sy-surface w-full max-w-3xl p-5"):
                ui.label(t(title_key)).classes("text-lg font-semibold")
                ui.label(t(detail_key)).classes("text-sm text-[var(--sy-muted)] mt-1")
                if title_key == "new_user_step_start":
                    ui.label(f"{t('local_address_label')}: http://127.0.0.1:8080").classes("font-mono text-sm font-semibold mt-3")
        with ui.row().classes("gap-3 flex-wrap"):
            ui.button(t("open_prefects"), icon="groups", on_click=lambda: ui.navigate.to("/prefects")).props("outline color=primary")
            ui.button(t("open_rosters"), icon="calendar_month", on_click=lambda: ui.navigate.to("/rosters")).props("color=primary")
            ui.button(t("operator_guide"), icon="help", on_click=lambda: ui.navigate.to("/guide")).props("flat")
            ui.button(t("open_handover_guide"), icon="handshake", on_click=lambda: ui.navigate.to("/handover")).props("flat")


@ui.page("/guide")
def operator_guide_page() -> None:
    sections = (
        ("guide_open_title", "guide_open_body"),
        ("guide_directory_title", "guide_directory_body"),
        ("guide_draft_title", "guide_draft_body"),
        ("guide_manual_title", "guide_manual_body"),
        ("guide_publish_title", "guide_publish_body"),
        ("guide_recovery_title", "guide_recovery_body"),
        ("guide_support_title", "guide_support_body"),
    )
    with page_shell("operator_guide", "/guide", music_context="guide"):
        ui.label(t("operator_guide")).classes("text-2xl font-semibold")
        ui.label(t("guide_intro")).classes("text-[var(--sy-muted)] max-w-3xl")
        for title_key, body_key in sections:
            with ui.expansion(t(title_key), icon="help").classes("sy-surface w-full max-w-4xl"):
                ui.label(t(body_key)).classes("p-4 text-sm leading-6 text-[var(--sy-muted)]")
        _render_feedback_channel(compact=True)
        ui.button(t("open_system_architecture"), icon="account_tree", on_click=lambda: ui.navigate.to("/system-architecture")).props("flat").classes("self-start")


@ui.page("/rosters")
def rosters_page() -> None:
    workflow = get_workflow()
    with page_shell("rosters", "/rosters"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(t("rosters")).classes("text-2xl font-semibold")
            ui.label(t("persistence_notice")).classes("text-sm text-[var(--sy-muted)]")
        _render_storage_lifecycle(workflow)
        with ui.tabs().classes("w-full sy-fg-action") as tabs:
            generate_tab = ui.tab("generate_view", label=t("generate_view"), icon="calendar_month")
            adjust_tab = ui.tab("adjust_edit", label=t("adjust_edit"), icon="edit_calendar")
        with ui.tab_panels(tabs, value="generate_view", animated=False, keep_alive=False).classes("w-full bg-transparent"):
            with ui.tab_panel("generate_view").classes("px-0"):
                with ui.card().classes("sy-surface w-full max-w-2xl p-6"):
                    ui.label(t("generate_roster")).classes("text-lg font-semibold")
                    _render_operation_hint("hint_generate_roster", icon="calendar_month")
                    week_input = ui.input(label=t("week_start"), value=_next_monday().isoformat()).props(
                        "type=date name=week-start autocomplete=off"
                    )

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

                    requirements_area = ui.column().classes("w-full gap-2 mt-4")

                    def refresh_requirements() -> None:
                        requirements_area.clear()
                        week_start = selected_week_start()
                        if week_start is None:
                            return
                        try:
                            requirements = workflow.generation_requirements(week_start)
                        except WorkflowError:
                            return
                        with requirements_area:
                            with ui.expansion(t("generation_requirements"), icon="assignment_late").classes("w-full"):
                                ui.label(t("generation_requirements_notice")).classes("p-4 pb-1 text-sm text-[var(--sy-muted)]")
                                rows = [
                                    {
                                        "id": index,
                                        "day": day_label(item["day"]),
                                        "post": post_label(item["postCode"]),
                                        "slot": item["slotIndex"],
                                        "eligible": item["eligibleCount"],
                                        "status": t("vacancy_risk") if item["hasVacancyRisk"] else t("awaiting_generation"),
                                    }
                                    for index, item in enumerate(requirements, start=1)
                                ]
                                ui.table(
                                    rows=rows,
                                    columns=[
                                        {"name": "day", "label": t("day"), "field": "day", "align": "left"},
                                        {"name": "post", "label": t("post"), "field": "post", "align": "left"},
                                        {"name": "slot", "label": "#", "field": "slot", "align": "right"},
                                        {"name": "eligible", "label": t("eligible_count"), "field": "eligible", "align": "right"},
                                        {"name": "status", "label": t("status"), "field": "status", "align": "left"},
                                    ],
                                    row_key="id",
                                ).classes("sy-table w-full p-4")
                    refresh_requirements()

                    ui.separator().classes("my-5")
                    ui.label(t("pre_generation_leave")).classes("text-base font-semibold")
                    ui.label(t("leave_generation_notice")).classes("text-sm text-[var(--sy-muted)]")
                    prefect_options = {
                        str(prefect["id"]): f"{prefect['nameZh']} ({prefect['form']} {prefect['className']})"
                        for prefect in workflow.prefects()
                    }
                    with ui.row().classes("w-full gap-3 flex-wrap"):
                        leave_prefect = ui.select(
                            label=t("select_prefect"),
                            options=prefect_options,
                            value=next(iter(prefect_options), None),
                        ).classes("grow min-w-[220px]")
                        leave_day = ui.select(
                            label=t("leave_day"),
                            options={day.name: day_label(day) for day in SchoolDay},
                            value=SchoolDay.MONDAY.name,
                        ).classes("grow min-w-[180px]")
                    leave_reason = ui.input(label=t("leave_reason")).props(
                        "name=pre-generation-leave-reason autocomplete=off"
                    ).classes("w-full")
                    leave_list = ui.column().classes("w-full gap-2 mt-3")

                    def refresh_leave_list() -> None:
                        leave_list.clear()
                        week_start = selected_week_start()
                        if week_start is None:
                            return
                        try:
                            declarations = workflow.pre_generation_leaves(week_start)
                        except WorkflowError:
                            return
                        with leave_list:
                            if declarations:
                                ui.label(t("declared_leaves")).classes("text-sm font-semibold")
                            for declaration in declarations:
                                with ui.row().classes("w-full items-center justify-between gap-3 py-1"):
                                    ui.label(
                                        f"{day_label(str(declaration['day']))} | {declaration['prefectName']} | {declaration['reason']}"
                                    ).classes("text-sm text-[var(--sy-muted)]")

                                    async def cancel_leave(leave_id: int = int(declaration["id"])) -> None:
                                        result = await _run_with_progress(
                                            lambda: workflow.cancel_pre_generation_leave(leave_id),
                                            title_key="progress_leave_cancel_title",
                                            working_key="progress_leave_cancel_working",
                                            icon="event_available",
                                        )
                                        if result is not _OPERATION_FAILED:
                                            ui.notify(t("leave_cancelled"), type="positive")
                                            refresh_leave_list()

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
                        if not reason:
                            ui.notify(t("leave_reason_required"), type="warning")
                            leave_reason.run_method("focus")
                            return
                        prefect_id = str(leave_prefect.value)
                        leave_day_value = str(leave_day.value)
                        result = await _run_with_progress(
                            lambda: workflow.declare_leave(
                                week_start=week_start,
                                prefect_id=prefect_id,
                                day=leave_day_value,
                                reason=reason,
                            ),
                            title_key="progress_leave_title",
                            working_key="progress_leave_working",
                            icon="event_busy",
                        )
                        if result is not _OPERATION_FAILED:
                            leave_reason.value = ""
                            leave_reason.update()
                            refresh_leave_list()
                            ui.notify(t("leave_declared"), type="positive")

                    ui.button(t("declare_leave"), icon="event_busy", on_click=declare_leave).props("outline color=primary").classes("mt-3")
                    week_input.on("change", lambda _event: (refresh_leave_list(), refresh_requirements()))
                    refresh_leave_list()

                    async def generate() -> None:
                        week_start = selected_week_start(announce_error=True)
                        if week_start is None:
                            return
                        result = await _run_with_progress(
                            lambda: workflow.generate_and_save_draft(week_start),
                            title_key="progress_generate_title",
                            working_key="progress_generate_working",
                            icon="auto_awesome",
                        )
                        if result is not _OPERATION_FAILED:
                            ui.notify(t("draft_saved"), type="positive")
                            ui.navigate.to(f"/rosters/{result.id}")

                    ui.button(t("create_draft"), icon="auto_awesome", on_click=generate).props("color=primary").classes("mt-4")
                ui.label(t("current_rosters")).classes("text-xl font-semibold mt-6")
                weeks = workflow.roster_weeks()
                if not weeks:
                    _render_empty_state(
                        title_key="empty_roster_title",
                        body_key="empty_roster_detail",
                        icon="event_note",
                        illustrated=True,
                    )
                for week in weeks:
                    with ui.row().classes("sy-surface w-full items-center justify-between px-5 py-4"):
                        with ui.column().classes("gap-0"):
                            ui.label(str(week["weekStart"])).classes("text-lg font-semibold")
                            ui.label(f"{t('version')} {week['version']}  |  {t('generated_at')}: {week['generatedAt']:%Y-%m-%d %H:%M}").classes("text-sm text-[var(--sy-muted)]")
                        _tone_badge(t("published") if week["status"] == "published" else t("draft"), "stable" if week["status"] == "published" else "action")
                        ui.button(t("view"), icon="arrow_forward", on_click=lambda item=week: ui.navigate.to(f"/rosters/{item['id']}")).props("flat")
            with ui.tab_panel("adjust_edit").classes("px-0"):
                ui.label(t("adjustments")).classes("text-lg font-semibold")
                _render_operation_hint("hint_adjust_roster", icon="event_busy")
                published_weeks = [week for week in workflow.roster_weeks() if week["status"] == "published"]
                if not published_weeks:
                    _render_empty_state(
                        title_key="empty_published_title",
                        body_key="empty_published_detail",
                        icon="fact_check",
                    )
                for week in published_weeks:
                    with ui.row().classes("sy-surface w-full items-center justify-between px-5 py-4 mt-4"):
                        with ui.column().classes("gap-0"):
                            ui.label(str(week["weekStart"])).classes("text-lg font-semibold")
                            ui.label(f"{t('version')} {week['version']}").classes("text-sm text-[var(--sy-muted)]")
                        ui.button(t("adjust_roster"), icon="swap_horiz", on_click=lambda item=week: ui.navigate.to(f"/rosters/{item['id']}/adjustments")).props("outline color=primary")


@ui.page("/rosters/new")
def generate_roster_page() -> None:
    ui.navigate.to("/rosters")


@ui.page("/rosters/{roster_week_id}")
def roster_detail_page(roster_week_id: int) -> None:
    workflow = get_workflow()
    with page_shell("rosters", "/rosters"):
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
        with ui.row().classes("w-full items-start justify-between gap-4"):
            with ui.column().classes("gap-1"):
                ui.label(str(week["weekStart"])).classes("text-2xl font-semibold")
                ui.label(f"{t('version')} {week['version']}").classes("text-[var(--sy-muted)]")
            with ui.row().classes("gap-2"):
                if week["status"] == "draft":
                    with ui.dialog() as publish_dialog, ui.card().classes("sy-surface w-full max-w-md p-6"):
                        ui.label(t("confirm_publish")).classes("text-lg font-semibold")
                        ui.label(t("publish_warning")).classes("text-sm text-[var(--sy-muted)] mt-2")

                        async def publish() -> None:
                            publish_dialog.close()
                            result = await _run_with_progress(
                                lambda: workflow.publish(roster_week_id),
                                title_key="progress_publish_title",
                                working_key="progress_publish_working",
                                icon="publish",
                            )
                            if result is not _OPERATION_FAILED:
                                ui.notify(t("published_success"), type="positive")
                                ui.navigate.reload()

                        with ui.row().classes("w-full justify-end gap-3 mt-5"):
                            ui.button(t("cancel"), icon="close", on_click=publish_dialog.close).props("flat")
                            ui.button(t("confirm_publish_action"), icon="publish", on_click=publish).props("color=primary")
                    ui.button(t("publish"), icon="publish", on_click=publish_dialog.open).props("color=primary")
                else:
                    ui.button(t("adjust_roster"), icon="swap_horiz", on_click=lambda: ui.navigate.to(f"/rosters/{roster_week_id}/adjustments")).props("outline color=primary")
                ui.button(t("export_pdf"), icon="picture_as_pdf", on_click=lambda: _open_roster_export_dialog(roster_week_id)).props("outline color=primary")
        if week["status"] == "draft":
            ui.label(t("draft_export_warning")).classes("sy-fg-attention font-medium")
        ui.label(t("export_pdf_notice")).classes("text-sm text-[var(--sy-muted)]")
        if week["status"] == "draft":
            ui.label(t("draft_preview")).classes("text-xl font-semibold mt-2")
            ui.label(t("draft_preview_notice")).classes("text-sm text-[var(--sy-muted)]")
            draft_assignments = workflow.assignments(roster_week_id)
            assignment_options = {
                str(item["id"]): f"{day_label(item['day'])} | {post_label(item['postCode'])} | {item['prefectName']}"
                for item in draft_assignments
                if item["status"] == "active"
            }
            with ui.card().classes("sy-surface w-full max-w-3xl p-6"):
                ui.label(t("manual_draft_change")).classes("text-lg font-semibold")
                _render_operation_hint("hint_draft_change", icon="edit_note")
                ui.label(t("manual_draft_change_notice")).classes("text-sm text-[var(--sy-muted)] mt-3")
                assignment_select = ui.select(
                    label=t("select_draft_assignment"),
                    options=assignment_options,
                    value=next(iter(assignment_options), None),
                ).classes("w-full mt-4")
                candidate_select = ui.select(label=t("replacement"), options={}).classes("w-full")
                reason_input = ui.textarea(label=t("draft_change_reason")).props(
                    "name=draft-change-reason autocomplete=off"
                ).classes("w-full")

                def load_draft_candidates() -> None:
                    def action() -> None:
                        if not assignment_select.value:
                            raise WorkflowError("No draft assignment was selected.")
                        candidates = workflow.draft_assignment_candidates(roster_week_id, int(assignment_select.value))
                        candidate_select.options = {
                            str(candidate["id"]): f"{candidate['nameZh']} ({candidate['form']} {candidate['className']}; {candidate['historyWeight']:.1f})"
                            for candidate in candidates
                        }
                        candidate_select.value = next(iter(candidate_select.options), None)
                        candidate_select.update()
                        ui.notify(t("eligible_substitutes") if candidates else t("no_substitutes"), type="info")

                    _safe_read_action(action, action_name="load_draft_candidates")

                async def save_draft_change() -> None:
                    if not assignment_select.value:
                        ui.notify(t("draft_assignment_required"), type="warning")
                        assignment_select.run_method("focus")
                        return
                    if not candidate_select.value:
                        ui.notify(t("draft_candidate_required"), type="warning")
                        candidate_select.run_method("focus")
                        return
                    reason = str(reason_input.value or "").strip()
                    if not reason:
                        ui.notify(t("draft_change_reason_required"), type="warning")
                        reason_input.run_method("focus")
                        return
                    assignment_id = int(assignment_select.value)
                    replacement_prefect_id = str(candidate_select.value)
                    result = await _run_with_progress(
                        lambda: workflow.update_draft_assignment(
                            roster_week_id=roster_week_id,
                            assignment_id=assignment_id,
                            replacement_prefect_id=replacement_prefect_id,
                            reason=reason,
                        ),
                        title_key="progress_draft_change_title",
                        working_key="progress_draft_change_working",
                        icon="edit_note",
                    )
                    if result is not _OPERATION_FAILED:
                        ui.notify(t("draft_changed"), type="positive")
                        ui.navigate.reload()

                with ui.row().classes("gap-3 mt-4"):
                    ui.button(t("load_draft_candidates"), icon="group_add", on_click=load_draft_candidates).props("outline color=primary")
                    ui.button(t("save_draft_change"), icon="save", on_click=save_draft_change).props("color=primary")
        else:
            with ui.card().classes("sy-surface sy-border-attention w-full max-w-3xl border-l-4 p-6"):
                ui.label(t("post_publication_leave")).classes("text-lg font-semibold")
                ui.label(t("post_publication_leave_notice")).classes("text-sm text-[var(--sy-muted)] mt-1")
                ui.button(t("adjust_roster"), icon="swap_horiz", on_click=lambda: ui.navigate.to(f"/rosters/{roster_week_id}/adjustments")).props("color=primary").classes("mt-4")
        declarations = workflow.pre_generation_leaves(week["weekStart"])
        if declarations:
            with ui.element("section").classes("sy-surface w-full px-5 py-4"):
                ui.label(t("declared_leaves")).classes("font-semibold")
                for declaration in declarations:
                    ui.label(
                        f"{day_label(str(declaration['day']))} | {declaration['prefectName']} | {declaration['reason']}"
                    ).classes("text-sm text-[var(--sy-muted)] mt-1")
        _render_roster_table(roster_week_id)


@ui.page("/adjustments")
def adjustments_page() -> None:
    ui.navigate.to("/rosters")


@ui.page("/rosters/{roster_week_id}/adjustments")
def adjustment_detail_page(roster_week_id: int) -> None:
    workflow = get_workflow()
    with page_shell("adjustments", "/rosters"):
        ui.label(t("adjustments")).classes("text-2xl font-semibold")
        _render_operation_hint("hint_leave_adjustment", icon="swap_horiz")
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
        adjustment_command_id = f"leave-ui:{uuid4().hex}"
        active_assignments = [item for item in workflow.assignments(roster_week_id) if item["status"] == "active"]
        options = {
            str(item["id"]): f"{day_label(item['day'])} | {post_label(item['postCode'])} | {item['prefectName']}"
            for item in active_assignments
        }
        if not options:
            _render_empty_state(
                title_key="empty_published_title",
                body_key="empty_published_detail",
                icon="fact_check",
                action_key="empty_review_action",
                action=lambda: ui.navigate.to("/rosters"),
            )
            return
        with ui.card().classes("sy-surface sy-adjustment-form w-full max-w-2xl p-6"):
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

            def load_substitutes() -> None:
                def action() -> None:
                    candidates = workflow.recommend_substitutes(roster_week_id, int(assignment_select.value))
                    replacement_select.options = {"__vacant__": t("leave_vacant")}
                    replacement_select.options.update({str(item["id"]): f"{item['nameZh']} ({item['form']} {item['className']}; {item['historyWeight']:.1f})" for item in candidates})
                    replacement_select.value = "__vacant__"
                    replacement_select.update()
                    ui.notify(t("eligible_substitutes") if candidates else t("no_substitutes"), type="info")

                _safe_read_action(action, action_name="load_adjustment_candidates")

            async def apply_adjustment() -> None:
                reason = str(reason_input.value or "").strip()
                if not reason:
                    ui.notify(t("reason_required"), type="negative")
                    reason_input.run_method("focus")
                    return
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
                    ui.notify(t("adjustment_saved"), type="positive")
                    ui.navigate.to(f"/rosters/{roster_week_id}")

            with ui.element("section").classes("sy-adjustment-step"):
                ui.label(t("adjustment_step_reason")).classes("sy-adjustment-step-title")
                reason_input = ui.textarea(label=t("reason")).props(
                    "name=leave-adjustment-reason autocomplete=off"
                ).classes("w-full")
            with ui.row().classes("sy-adjustment-actions w-full gap-3"):
                ui.button(t("load_substitutes"), icon="group_add", on_click=load_substitutes).props("outline color=primary")
                ui.button(t("apply_adjustment"), icon="save", on_click=apply_adjustment).props("color=primary")


def _show_prefect_dialog(existing: dict[str, object] | None = None) -> None:
    workflow = get_workflow()
    title_key = "edit_prefect" if existing else "add_prefect"
    day_options = {day.name: day_label(day) for day in SchoolDay}
    role_options = {"study_prefect": role_label("study_prefect"), "assistant_head": role_label("assistant_head")}
    with ui.dialog() as dialog, ui.card().classes("sy-surface w-full max-w-2xl p-6"):
        ui.label(t(title_key)).classes("text-xl font-semibold")
        with ui.row().classes("w-full gap-3 flex-wrap"):
            name_zh = ui.input(label=t("name_zh"), value=existing["nameZh"] if existing else "").props(
                "name=name-zh autocomplete=off"
            ).classes("grow")
            name_en = ui.input(label=t("name_en"), value=existing["nameEn"] if existing else "").props(
                "name=name-en autocomplete=off"
            ).classes("grow")
        with ui.row().classes("w-full gap-3 flex-wrap"):
            form = ui.select(label=t("form"), options=["F.3", "F.4", "F.5", "F.6"], value=existing["form"] if existing else "F.3").classes("grow")
            class_name = ui.input(label=t("class_name"), value=existing["className"] if existing else "").props(
                "name=class-name autocomplete=off"
            ).classes("grow")
            role = ui.select(label=t("role"), options=role_options, value=existing["roleCode"] if existing else "study_prefect").classes("grow")
        availability = ui.select(
            label=t("availability"),
            options=day_options,
            value=list(existing["availableDays"]) if existing else [],
            multiple=True,
        ).classes("w-full")
        mentoring = ui.switch(t("needs_mentoring"), value=bool(existing["needsMentoring"]) if existing else False)
        remarks = ui.textarea(label=t("remarks"), value=existing["remarks"] if existing else "").props(
            "name=prefect-remarks autocomplete=off"
        ).classes("w-full")

        async def save_prefect() -> None:
            if not str(name_zh.value or "").strip():
                ui.notify(t("prefect_name_required"), type="warning")
                name_zh.run_method("focus")
                return
            if not str(class_name.value or "").strip():
                ui.notify(t("prefect_class_required"), type="warning")
                class_name.run_method("focus")
                return
            if not availability.value:
                ui.notify(t("prefect_availability_required"), type="warning")
                availability.run_method("focus")
                return
            prefect_input = PrefectInput(
                name_zh=str(name_zh.value or ""),
                name_en=str(name_en.value or "") or None,
                form=str(form.value),
                class_name=str(class_name.value or ""),
                role_code=str(role.value),
                available_days=tuple(availability.value or []),
                needs_mentoring=bool(mentoring.value),
                remarks=str(remarks.value or ""),
            )
            save_action = (
                (lambda: workflow.update_prefect(str(existing["id"]), prefect_input))
                if existing
                else (lambda: workflow.create_prefect(prefect_input))
            )
            result = await _run_with_progress(
                save_action,
                title_key="progress_prefect_save_title",
                working_key="progress_prefect_save_working",
                icon="person_check",
            )
            if result is not _OPERATION_FAILED:
                dialog.close()
                ui.notify(t("prefect_saved"), type="positive")
                ui.navigate.reload()

        with ui.row().classes("w-full justify-end gap-3 mt-4"):
            ui.button(t("cancel"), icon="close", on_click=dialog.close).props("flat")
            ui.button(t("save"), icon="save", on_click=save_prefect).props("color=primary")
    dialog.open()


def _render_fairness_panel(workflow) -> None:  # type: ignore[no-untyped-def]
    """Keep people records and their fairness context in one operator workspace."""
    _render_operation_hint("hint_fairness", icon="balance")
    with ui.card().classes("sy-surface w-full p-5"):
        ui.label(t("fairness_explained")).classes("text-lg font-semibold")
        ui.label(t("fairness_explanation")).classes("text-sm text-[var(--sy-muted)] mt-1")
    rows = workflow.fairness_rows()
    columns = [
        {"name": "nameZh", "label": t("prefect"), "field": "nameZh", "align": "left"},
        {"name": "form", "label": t("form"), "field": "form", "align": "left"},
        {"name": "className", "label": t("class_name"), "field": "className", "align": "left"},
        {"name": "historyWeight", "label": t("history_weight"), "field": "historyWeight", "align": "right"},
        {"name": "historyDuties", "label": t("history_duties"), "field": "historyDuties", "align": "right"},
    ]
    ui.table(rows=rows, columns=columns, row_key="id").classes("sy-table w-full mt-4")


@ui.page("/prefects")
def prefects_page() -> None:
    workflow = get_workflow()
    with page_shell("prefects", "/prefects"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(t("prefects")).classes("text-2xl font-semibold")
            ui.button(t("add_prefect"), icon="person_add", on_click=lambda: _show_prefect_dialog()).props("color=primary")
        with ui.tabs().classes("w-full sy-fg-action") as tabs:
            directory_tab = ui.tab("directory", label=t("directory"), icon="groups")
            import_tab = ui.tab("ai_import", label=t("ai_import"), icon="smart_toy")
            fairness_tab = ui.tab("fairness", label=t("audit"), icon="balance")
        with ui.tab_panels(tabs, value="directory", animated=False, keep_alive=False).classes("w-full bg-transparent"):
            with ui.tab_panel("directory").classes("px-0"):
                prefects = workflow.prefects()
                _render_operation_hint("hint_prefect_directory", icon="groups")
                options = {item["id"]: f"{item['nameZh']} ({item['form']} {item['className']})" for item in prefects}
                with ui.row().classes("sy-directory-actions w-full items-end gap-3 flex-wrap mb-4"):
                    selected = ui.select(label=t("select_prefect"), options=options, value=next(iter(options), None)).classes("sy-directory-selector min-w-[300px]")

                    def edit_selected() -> None:
                        if selected.value:
                            _show_prefect_dialog(workflow.prefect(str(selected.value)))

                    with ui.dialog() as archive_dialog, ui.card().classes("sy-surface w-full max-w-md p-6"):
                        ui.label(t("confirm_archive_prefect")).classes("text-lg font-semibold")
                        ui.label(t("archive_prefect_warning")).classes("text-sm leading-6 text-[var(--sy-muted)] mt-2")

                        async def confirm_archive_selected() -> None:
                            if not selected.value:
                                archive_dialog.close()
                                ui.notify(t("operation_error"), type="negative")
                                return
                            prefect_id = str(selected.value)
                            archive_dialog.close()
                            result = await _run_with_progress(
                                lambda: workflow.archive_prefect(prefect_id),
                                title_key="progress_prefect_archive_title",
                                working_key="progress_prefect_archive_working",
                                icon="person_off",
                            )
                            if result is not _OPERATION_FAILED:
                                ui.notify(t("prefect_archived"), type="positive")
                                ui.navigate.reload()

                        with ui.row().classes("w-full justify-end gap-3 mt-5"):
                            ui.button(t("cancel"), icon="close", on_click=archive_dialog.close).props("flat")
                            ui.button(
                                t("confirm_archive"),
                                icon="archive",
                                on_click=confirm_archive_selected,
                            ).props("color=negative data-testid=confirm-archive-prefect")

                    def archive_selected() -> None:
                        if not selected.value:
                            ui.notify(t("operation_error"), type="negative")
                            return
                        archive_dialog.open()

                    ui.button(t("edit_prefect"), icon="edit", on_click=edit_selected).props("outline color=primary")
                    ui.button(t("archive_prefect"), icon="archive", on_click=archive_selected).props(
                        "flat color=negative data-testid=open-archive-prefect"
                    )
                rows = _prefect_directory_rows(prefects)
                columns = [
                    {"name": "name", "label": t("prefect"), "field": "name", "align": "left"},
                    {"name": "form", "label": t("form"), "field": "form", "align": "left"},
                    {"name": "class", "label": t("class_name"), "field": "class", "align": "left"},
                    {"name": "role", "label": t("role"), "field": "role", "align": "left"},
                    {"name": "availability", "label": t("availability"), "field": "availability", "align": "left"},
                    {"name": "weight", "label": t("history_weight"), "field": "weight", "align": "right"},
                    {"name": "duties", "label": t("history_duties"), "field": "duties", "align": "right"},
                ]
                ui.table(rows=rows, columns=columns, row_key="name").classes("sy-table sy-prefect-directory-desktop w-full")
                _render_mobile_prefect_cards(rows)
            with ui.tab_panel("ai_import").classes("px-0"):
                _render_operation_hint("hint_prefect_import", icon="upload_file")
                ui.label(t("ai_import_help")).classes("text-[var(--sy-muted)] max-w-3xl")
                ui.label(t("import_template_notice")).classes("text-sm text-[var(--sy-muted)] max-w-3xl mt-2")
                ui.button(
                    t("download_import_template"),
                    icon="download",
                    on_click=lambda: ui.download(prefect_import_template_csv(), "sing-yin-prefect-import-template.csv"),
                ).props("outline color=primary").classes("mt-3")
                import_text = ui.textarea(label=t("ai_import_input")).props(
                    "name=prefect-import autocomplete=off"
                ).classes("w-full max-w-3xl")
                preview_state: dict[str, ImportPreview | None] = {"value": None}
                preview_area = ui.column().classes("w-full max-w-4xl gap-3 mt-4")

                def preview_import() -> None:
                    preview = parse_prefect_import_text(str(import_text.value or ""))
                    preview_state["value"] = preview
                    preview_area.clear()
                    with preview_area:
                        if preview.issues:
                            ui.label(t("import_issues")).classes("font-semibold text-red-600")
                            for issue in preview.issues:
                                ui.label(issue).classes("text-sm text-red-600")
                        if preview.rows:
                            if not preview.issues:
                                ui.label(t("import_ready")).classes("font-semibold sy-fg-stable")
                            ui.table(
                                rows=[
                                    {
                                        "name": row.name_zh,
                                        "form": row.form,
                                        "class": row.class_name,
                                        "role": role_label(row.role_code),
                                        "availability": " / ".join(day_label(day) for day in row.available_days),
                                    }
                                    for row in preview.rows
                                ],
                                columns=[
                                    {"name": "name", "label": t("prefect"), "field": "name", "align": "left"},
                                    {"name": "form", "label": t("form"), "field": "form", "align": "left"},
                                    {"name": "class", "label": t("class_name"), "field": "class", "align": "left"},
                                    {"name": "role", "label": t("role"), "field": "role", "align": "left"},
                                    {"name": "availability", "label": t("availability"), "field": "availability", "align": "left"},
                                ],
                                row_key="name",
                            ).classes("sy-table w-full")

                async def import_preview() -> None:
                    preview = preview_state["value"]
                    if preview is None or preview.issues or not preview.rows:
                        ui.notify(t("operation_error"), type="negative")
                        return
                    result = await _run_with_progress(
                        lambda: workflow.import_prefects(preview.rows),
                        title_key="progress_import_title",
                        working_key="progress_import_working",
                        icon="upload_file",
                    )
                    if result is not _OPERATION_FAILED:
                        ui.notify(t("imported_success"), type="positive")
                        ui.navigate.reload()

                with ui.row().classes("gap-3 mt-4"):
                    ui.button(t("preview_import"), icon="fact_check", on_click=preview_import).props("outline color=primary")
                    ui.button(t("import_prefects"), icon="upload", on_click=import_preview).props("color=primary")
            with ui.tab_panel("fairness").classes("px-0"):
                _render_fairness_panel(workflow)


@ui.page("/audit")
def audit_page() -> None:
    """Keep former bookmarks valid while moving fairness beside the people directory."""
    ui.navigate.to("/prefects")


@ui.page("/handover")
def handover_page() -> None:
    workflow = get_workflow()
    readiness = workflow.handover_readiness()
    release_evidence = load_release_evidence()
    with page_shell("handover", "/handover", music_context="handover"):
        with ui.element("section").classes("sy-handover-hero w-full").props(f'aria-label="{t("handover")}"'):
            ui.icon("handshake").classes("sy-handover-hero-icon").props("aria-hidden=true")
            ui.label(t("handover")).classes("sy-handover-hero-title")
            ui.label(t("handover_intro")).classes("sy-handover-hero-copy")
        with ui.card().classes("sy-surface w-full max-w-3xl p-6"):
            for key in ("handover_step_one", "handover_step_two", "handover_step_three", "handover_step_four"):
                ui.label(t(key)).classes("text-sm leading-6")
        checks = (
            ("handover_prefects_ready", f"{readiness['activePrefectCount']}", readiness["activePrefectCount"] > 0),
            ("handover_rosters_ready", f"{readiness['rosterCount']}", readiness["rosterCount"] > 0),
            ("handover_backup_ready", t("verified") if readiness["verifiedBackup"] else t("handover_attention"), readiness["verifiedBackup"]),
        )
        with ui.element("section").classes("sy-handover-readiness-grid w-full").props(
            f'aria-label="{t("handover")}" data-testid=handover-readiness-grid'
        ):
            for label_key, value, ready in checks:
                with ui.element("article").classes("sy-surface sy-handover-readiness-card"):
                    ui.label(t(label_key)).classes("text-sm text-[var(--sy-muted)]")
                    ui.label(value).classes("text-xl font-semibold mt-1")
                    _tone_badge(t("handover_ready") if ready else t("handover_attention"), "stable" if ready else "attention").classes("mt-3")

        state_key = {
            "pass": "acceptance_status_pass",
            "running": "acceptance_status_running",
            "stale": "acceptance_status_stale",
            "fail": "acceptance_status_fail",
            "missing": "acceptance_status_missing",
            "unreadable": "acceptance_status_unreadable",
        }[release_evidence.state]
        state_body_key = f"acceptance_body_{release_evidence.state}"
        state_icon = {
            "pass": "verified_user",
            "running": "sync",
            "stale": "update",
            "fail": "error_outline",
            "missing": "pending_actions",
            "unreadable": "report_problem",
        }[release_evidence.state]
        state_tone = {
            "pass": "stable",
            "running": "action",
            "stale": "attention",
            "fail": "danger",
            "missing": "attention",
            "unreadable": "danger",
        }[release_evidence.state]
        with ui.element("section").classes("sy-acceptance-panel w-full").props(
            f'role=status aria-live=polite aria-label="{t("acceptance_title")}" data-testid=acceptance-status'
        ):
            with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
                with ui.row().classes("items-start gap-3 no-wrap"):
                    ui.icon("fact_check").classes("sy-acceptance-panel-icon").props("aria-hidden=true")
                    with ui.column().classes("gap-1"):
                        ui.label(t("acceptance_title")).classes("sy-acceptance-title")
                        ui.label(t("acceptance_intro")).classes("sy-acceptance-intro")
                _tone_badge(t(state_key), state_tone, props="data-testid=acceptance-state-badge")
            with ui.element("div").classes("sy-acceptance-grid"):
                with ui.element("article").classes("sy-acceptance-card"):
                    ui.icon(state_icon).classes(f"sy-acceptance-card-icon sy-fg-{state_tone}").props("aria-hidden=true")
                    ui.label(t("acceptance_machine_title")).classes("sy-acceptance-card-kicker")
                    ui.label(t(state_key)).classes("sy-acceptance-card-title")
                    ui.label(t(state_body_key)).classes("sy-acceptance-card-copy")
                    if release_evidence.total_checks:
                        ui.label(
                            t(
                                "acceptance_checks_summary",
                                passed=release_evidence.passed_checks,
                                total=release_evidence.total_checks,
                            )
                        ).classes("sy-acceptance-meta")
                    if release_evidence.finished_at:
                        ui.label(
                            t(
                                "acceptance_report_time",
                                time=release_evidence.finished_at.strftime("%Y-%m-%d %H:%M UTC"),
                            )
                        ).classes("sy-acceptance-meta")
                with ui.element("article").classes("sy-acceptance-card sy-acceptance-card--human"):
                    ui.icon("groups").classes("sy-acceptance-card-icon sy-fg-attention").props("aria-hidden=true")
                    ui.label(t("acceptance_human_title")).classes("sy-acceptance-card-kicker")
                    ui.label(t("acceptance_human_required")).classes("sy-acceptance-card-title")
                    ui.label(t("acceptance_human_body")).classes("sy-acceptance-card-copy")
                    ui.label(t("acceptance_role_summary")).classes("sy-acceptance-meta")
            with ui.expansion(t("acceptance_steps_title"), icon="checklist").classes(
                "sy-acceptance-steps w-full"
            ).props("data-testid=acceptance-human-steps"):
                with ui.element("ol").classes("sy-acceptance-step-list"):
                    for key in (
                        "acceptance_task_directory",
                        "acceptance_task_pdf",
                        "acceptance_task_successor",
                        "acceptance_task_advisor",
                    ):
                        with ui.element("li"):
                            ui.label(t(key))
            with ui.row().classes("sy-acceptance-actions w-full gap-3 flex-wrap"):
                ui.button(
                    t("acceptance_open_guide"),
                    icon="menu_book",
                    on_click=lambda: ui.navigate.to("/guide"),
                ).props("outline color=primary data-testid=acceptance-open-guide")
                ui.button(
                    t("open_backup_settings"),
                    icon="settings_backup_restore",
                    on_click=lambda: ui.navigate.to("/settings"),
                ).props("flat data-testid=acceptance-open-settings")
        ui.button(t("open_system_architecture"), icon="account_tree", on_click=lambda: ui.navigate.to("/system-architecture")).props("flat").classes("self-start")


def _render_co_creation() -> None:
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


@ui.page("/platform")
def platform_page() -> None:
    team_roles = (
        ("flag", "team_role_head", "team_role_head_function", "team_role_head_body", "lead"),
        ("hub", "team_role_assistant", "team_role_assistant_function", "team_role_assistant_body", "coordination"),
        ("meeting_room", "team_role_prefect", "team_role_prefect_function", "team_role_prefect_body", "service"),
        ("fact_check", "team_role_advisor", "team_role_advisor_function", "team_role_advisor_body", "assurance"),
    )
    capability_groups = (
        ("calendar_month", "capability_operations_title", "capability_operations_body", "capability_operations_output"),
        ("balance", "capability_fairness_title", "capability_fairness_body", "capability_fairness_output"),
        ("translate", "capability_experience_title", "capability_experience_body", "capability_experience_output"),
        ("shield", "capability_continuity_title", "capability_continuity_body", "capability_continuity_output"),
    )
    solutions = (
        ("event_available", "solution_weekly_title", "solution_weekly_body", "solution_weekly_outcome", "/rosters"),
        ("person_off", "solution_adjustment_title", "solution_adjustment_body", "solution_adjustment_outcome", "/adjustments"),
        ("query_stats", "solution_fairness_title", "solution_fairness_body", "solution_fairness_outcome", "/audit"),
        ("inventory_2", "solution_handover_title", "solution_handover_body", "solution_handover_outcome", "/handover"),
    )
    culture_values = (
        ("platform_value_service_title", "platform_value_service_body"),
        ("platform_value_fairness_title", "platform_value_fairness_body"),
        ("platform_value_clarity_title", "platform_value_clarity_body"),
        ("platform_value_responsibility_title", "platform_value_responsibility_body"),
        ("platform_value_continuity_title", "platform_value_continuity_body"),
    )

    summary = PlatformSummary.unavailable()
    summary_reference = ""
    started_at = perf_counter()
    try:
        summary = load_platform_summary(get_workflow())
    except Exception as error:
        summary_reference = new_operation_reference()
        record_operator_failure(
            error,
            action="load_platform_summary",
            reference=summary_reference,
            started_at=started_at,
        )

    release_labels = {
        "pass": "platform_release_pass",
        "running": "platform_release_running",
        "stale": "platform_release_stale",
        "fail": "platform_release_fail",
        "missing": "platform_release_missing",
        "unreadable": "platform_release_unreadable",
    }
    release_value = t(release_labels.get(summary.release_state, "platform_release_unreadable"))
    if summary.release_total_checks:
        release_value = t(
            "platform_release_checks",
            passed=summary.release_passed_checks,
            total=summary.release_total_checks,
        )

    with page_shell("platform", "/platform", music_context="architecture"):
        with ui.element("section").classes("sy-platform-hero w-full").props(
            f'aria-label="{t("platform")}" data-testid=platform-hero'
        ):
            with ui.column().classes("sy-platform-hero-copy gap-2"):
                ui.label(t("platform_kicker")).classes("sy-architecture-kicker")
                ui.label(t("platform")).classes("sy-architecture-title")
                ui.label(t("platform_intro")).classes("sy-architecture-copy")
                ui.label(t("platform_principle")).classes("sy-platform-principle")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading(
                "platform_snapshot_kicker", "platform_snapshot_title", "platform_snapshot_copy"
            )
            if summary.available:
                metrics = (
                    ("groups", str(summary.active_prefect_count), "platform_metric_prefects", "platform_metric_prefects_note"),
                    ("calendar_view_week", str(summary.roster_count), "platform_metric_rosters", "platform_metric_rosters_note"),
                    ("verified_user", t("verified") if summary.verified_backup else t("handover_attention"), "platform_metric_backup", "platform_metric_backup_note"),
                    ("fact_check", release_value, "platform_metric_release", "platform_metric_release_note"),
                )
                with ui.element("div").classes("sy-platform-snapshot").props(
                    "data-testid=platform-live-summary aria-live=polite"
                ):
                    for icon, value, label_key, note_key in metrics:
                        with ui.element("article").classes("sy-platform-metric"):
                            ui.icon(icon).classes("sy-platform-metric-icon").props("aria-hidden=true")
                            ui.label(value).classes("sy-platform-metric-value")
                            ui.label(t(label_key)).classes("sy-platform-metric-label")
                            ui.label(t(note_key)).classes("sy-platform-metric-note")
            else:
                with ui.element("div").classes("sy-platform-unavailable").props(
                    "role=status data-testid=platform-summary-unavailable"
                ):
                    ui.label(t("platform_snapshot_unavailable_title")).classes("font-semibold")
                    ui.label(t("platform_snapshot_unavailable_body")).classes("mt-2 text-sm leading-6 text-[var(--sy-muted)]")
                    if summary_reference:
                        ui.label(t("error_reference", reference=summary_reference)).classes(
                            "mt-3 text-xs text-[var(--sy-muted)]"
                        )

        with ui.element("section").classes("sy-architecture-section w-full").props(
            f'aria-label="{t("team_operating_model_title")}"'
        ):
            _render_architecture_section_heading(
                "team_operating_model_kicker", "team_operating_model_title", "team_operating_model_copy"
            )
            with ui.element("div").classes("sy-team-operating-model").props("data-testid=team-operating-model"):
                for icon, role_key, function_key, body_key, level in team_roles:
                    with ui.element("article").classes(f"sy-team-role sy-team-role--{level}"):
                        with ui.row().classes("items-center gap-3 no-wrap"):
                            ui.icon(icon).classes("sy-team-role-icon").props("aria-hidden=true")
                            with ui.column().classes("gap-0 min-w-0"):
                                ui.label(t(role_key)).classes("sy-team-role-title")
                                ui.label(t(function_key)).classes("sy-team-role-function")
                        ui.label(t(body_key)).classes("sy-team-role-copy")
            ui.label(t("team_operating_model_note")).classes("sy-team-operating-model-note")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading("capability_map_kicker", "capability_map_title", "capability_map_copy")
            with ui.element("div").classes("sy-capability-map").props("data-testid=capability-map"):
                for icon, title_key, body_key, output_key in capability_groups:
                    with ui.element("article").classes("sy-capability-card"):
                        ui.icon(icon).classes("sy-capability-icon").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-capability-title")
                        ui.label(t(body_key)).classes("sy-capability-copy")
                        ui.label(t(output_key)).classes("sy-capability-output")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading(
                "solutions_portfolio_kicker", "solutions_portfolio_title", "solutions_portfolio_copy"
            )
            with ui.element("div").classes("sy-solutions-grid").props("data-testid=solutions-portfolio"):
                for icon, title_key, body_key, outcome_key, route in solutions:
                    with ui.element("article").classes("sy-solution-card"):
                        with ui.row().classes("items-center gap-3 no-wrap"):
                            ui.icon(icon).classes("sy-solution-icon").props("aria-hidden=true")
                            ui.label(t(title_key)).classes("sy-solution-title")
                        ui.label(t(body_key)).classes("sy-solution-copy")
                        ui.label(t(outcome_key)).classes("sy-solution-outcome")
                        ui.button(
                            t("solution_open_workspace"),
                            icon="arrow_forward",
                            on_click=lambda destination=route: ui.navigate.to(destination),
                        ).props("flat").classes("sy-solution-action self-start")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading(
                "platform_culture_kicker", "platform_culture_title", "platform_culture_copy"
            )
            with ui.element("div").classes("sy-platform-culture").props("data-testid=platform-principles"):
                for index, (title_key, body_key) in enumerate(culture_values, start=1):
                    with ui.element("article").classes("sy-platform-value"):
                        ui.label(f"{index:02d}").classes("sy-platform-value-index").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-platform-value-title")
                        ui.label(t(body_key)).classes("sy-platform-value-copy")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading(
                "platform_resources_kicker", "platform_resources_title", "platform_resources_copy"
            )
            with ui.element("div").classes("sy-platform-resources").props("data-testid=platform-resources"):
                for icon, label_key, route in (
                    ("menu_book", "platform_resource_guide", "/guide"),
                    ("account_tree", "platform_resource_architecture", "/system-architecture"),
                    ("handshake", "platform_resource_handover", "/handover"),
                ):
                    with ui.element("article").classes("sy-platform-resource"):
                        ui.button(
                            t(label_key), icon=icon, on_click=lambda destination=route: ui.navigate.to(destination)
                        ).props("flat")

        _render_feedback_channel()
        _render_co_creation()


@ui.page("/engineering")
def engineering_page() -> None:
    facts = (
        ("208", "science", "engineering_fact_tests", "engineering_fact_tests_body"),
        ("08", "verified", "engineering_fact_gates", "engineering_fact_gates_body"),
        ("05", "layers", "engineering_fact_layers", "engineering_fact_layers_body"),
        ("02", "translate", "engineering_fact_languages", "engineering_fact_languages_body"),
    )
    blueprint = (
        ("desktop_windows", "engineering_layer_ui", "engineering_layer_ui_body"),
        ("rule", "engineering_layer_policy", "engineering_layer_policy_body"),
        ("schema", "engineering_layer_core", "engineering_layer_core_body"),
        ("receipt_long", "engineering_layer_workflow", "engineering_layer_workflow_body"),
        ("database", "engineering_layer_evidence", "engineering_layer_evidence_body"),
    )
    gates = (
        ("policy", "engineering_gate_repository"),
        ("science", "engineering_gate_tests"),
        ("code", "engineering_gate_compile"),
        ("inventory_2", "engineering_gate_dependencies"),
        ("web", "engineering_gate_browser"),
        ("conversion_path", "engineering_gate_workflow"),
        ("dns", "engineering_gate_deployment"),
        ("settings_backup_restore", "engineering_gate_recovery"),
    )
    pillars = (
        ("balance", "engineering_pillar_fairness", "engineering_pillar_fairness_body"),
        ("restore_page", "engineering_pillar_recovery", "engineering_pillar_recovery_body"),
        ("manage_search", "engineering_pillar_observability", "engineering_pillar_observability_body"),
        ("science", "engineering_pillar_practice", "engineering_pillar_practice_body"),
        ("accessibility_new", "engineering_pillar_experience", "engineering_pillar_experience_body"),
        ("laptop_windows", "engineering_pillar_delivery", "engineering_pillar_delivery_body"),
    )
    evolution = (
        ("engineering_evolution_domain", "engineering_evolution_domain_body"),
        ("engineering_evolution_durable", "engineering_evolution_durable_body"),
        ("engineering_evolution_experience", "engineering_evolution_experience_body"),
        ("engineering_evolution_release", "engineering_evolution_release_body"),
    )
    evidence = load_release_evidence()
    release_state_keys = {
        "pass": "platform_release_pass",
        "running": "platform_release_running",
        "stale": "platform_release_stale",
        "fail": "platform_release_fail",
        "missing": "platform_release_missing",
        "unreadable": "platform_release_unreadable",
    }
    evidence_label = (
        t("engineering_release_current", passed=evidence.passed_checks, total=evidence.total_checks)
        if evidence.state == "pass" and evidence.total_checks
        else t("engineering_release_state", state=t(release_state_keys.get(evidence.state, "platform_release_unreadable")))
    )
    evidence_tone = "stable" if evidence.state == "pass" else "attention"

    with page_shell("engineering", "/engineering", music_context="architecture"):
        with ui.element("section").classes("sy-engineering-hero w-full").props(
            f'aria-label="{t("engineering")}" data-testid=engineering-hero'
        ):
            with ui.column().classes("gap-2"):
                ui.label(t("engineering_kicker")).classes("sy-architecture-kicker")
                ui.label(t("engineering")).classes("sy-architecture-title")
                ui.label(t("engineering_intro")).classes("sy-architecture-copy")
                _tone_badge(t("engineering_badge"), "stable").classes("mt-3 self-start")

        with ui.element("section").classes("sy-architecture-section w-full"):
            ui.label(t("engineering_facts_title")).classes("sy-architecture-section-title")
            with ui.element("div").classes("sy-engineering-facts").props("data-testid=engineering-facts"):
                for value, icon, title_key, body_key in facts:
                    with ui.element("article").classes("sy-engineering-fact"):
                        with ui.row().classes("items-center justify-between no-wrap"):
                            ui.label(value).classes("sy-engineering-fact-value")
                            ui.icon(icon).classes("sy-engineering-fact-icon").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-engineering-fact-title")
                        ui.label(t(body_key)).classes("sy-engineering-fact-copy")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading(
                "engineering_blueprint_kicker", "engineering_blueprint_title", "engineering_blueprint_copy"
            )
            with ui.element("ol").classes("sy-engineering-blueprint").props("data-testid=engineering-blueprint"):
                for index, (icon, title_key, body_key) in enumerate(blueprint, start=1):
                    with ui.element("li").classes("sy-engineering-blueprint-layer"):
                        with ui.row().classes("items-center gap-3 no-wrap"):
                            ui.label(f"{index:02d}").classes("sy-engineering-blueprint-index").props("aria-hidden=true")
                            ui.icon(icon).classes("sy-engineering-blueprint-icon").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-engineering-blueprint-title")
                        ui.label(t(body_key)).classes("sy-engineering-blueprint-copy")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading(
                "engineering_pipeline_kicker", "engineering_pipeline_title", "engineering_pipeline_copy"
            )
            _tone_badge(evidence_label, evidence_tone).classes("self-start")
            with ui.element("ol").classes("sy-engineering-gates").props("data-testid=engineering-gates"):
                for index, (icon, title_key) in enumerate(gates, start=1):
                    with ui.element("li").classes("sy-engineering-gate"):
                        ui.label(f"{index:02d}").classes("sy-engineering-gate-index")
                        ui.icon(icon).classes("sy-engineering-gate-icon").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-engineering-gate-title")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading(
                "engineering_pillars_kicker", "engineering_pillars_title", "engineering_pillars_copy"
            )
            with ui.element("div").classes("sy-engineering-pillars").props("data-testid=engineering-pillars"):
                for icon, title_key, body_key in pillars:
                    with ui.element("article").classes("sy-engineering-pillar"):
                        ui.icon(icon).classes("sy-engineering-pillar-icon").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-engineering-pillar-title")
                        ui.label(t(body_key)).classes("sy-engineering-pillar-copy")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading(
                "engineering_evolution_kicker", "engineering_evolution_title", "engineering_evolution_copy"
            )
            with ui.element("ol").classes("sy-engineering-evolution").props("data-testid=engineering-evolution"):
                for title_key, body_key in evolution:
                    with ui.element("li").classes("sy-engineering-evolution-item"):
                        ui.label(t(title_key)).classes("sy-engineering-evolution-title")
                        ui.label(t(body_key)).classes("sy-engineering-evolution-copy")

        with ui.element("section").classes("sy-engineering-resources w-full"):
            ui.label(t("engineering_resources_title")).classes("sy-architecture-section-title")
            with ui.row().classes("gap-3 flex-wrap mt-4"):
                ui.link(t("engineering_open_github"), GITHUB_REPOSITORY_URL, new_tab=True).props(
                    'rel="noopener noreferrer"'
                ).classes("sy-engineering-resource-link")
                ui.button(
                    t("engineering_open_architecture"), icon="account_tree", on_click=lambda: ui.navigate.to("/system-architecture")
                ).props("outline")
                ui.button(
                    t("engineering_open_platform"), icon="domain", on_click=lambda: ui.navigate.to("/platform")
                ).props("flat")


@ui.page("/system-architecture")
def system_architecture_page() -> None:
    layers = (
        ("desktop_windows", "architecture_ui_title", "architecture_ui_body"),
        ("rule", "architecture_policy_title", "architecture_policy_body"),
        ("receipt_long", "architecture_workflow_title", "architecture_workflow_body"),
        ("shield", "architecture_safety_title", "architecture_safety_body"),
        ("archive", "architecture_handover_title", "architecture_handover_body"),
    )
    service_flow = (
        ("groups", "architecture_flow_prepare_title", "architecture_flow_prepare_body", "architecture_flow_prepare_result"),
        ("edit_calendar", "architecture_flow_draft_title", "architecture_flow_draft_body", "architecture_flow_draft_result"),
        ("verified", "architecture_flow_publish_title", "architecture_flow_publish_body", "architecture_flow_publish_result"),
        ("picture_as_pdf", "architecture_flow_export_title", "architecture_flow_export_body", "architecture_flow_export_result"),
        ("person_off", "architecture_flow_adjust_title", "architecture_flow_adjust_body", "architecture_flow_adjust_result"),
        ("inventory_2", "architecture_flow_handover_title", "architecture_flow_handover_body", "architecture_flow_handover_result"),
    )
    evidence = (
        ("gavel", "architecture_evidence_policy_title", "architecture_evidence_policy_body", "architecture_evidence_policy_label"),
        ("balance", "architecture_evidence_ledger_title", "architecture_evidence_ledger_body", "architecture_evidence_ledger_label"),
        ("restore_page", "architecture_evidence_recovery_title", "architecture_evidence_recovery_body", "architecture_evidence_recovery_label"),
        ("lock", "architecture_evidence_privacy_title", "architecture_evidence_privacy_body", "architecture_evidence_privacy_label"),
    )
    faq_items = (
        ("faq_draft_q", "faq_draft_a"),
        ("faq_publish_q", "faq_publish_a"),
        ("faq_leave_q", "faq_leave_a"),
        ("faq_names_q", "faq_names_a"),
        ("faq_storage_q", "faq_storage_a"),
        ("faq_restore_q", "faq_restore_a"),
        ("faq_remote_q", "faq_remote_a"),
        ("faq_support_q", "faq_support_a"),
        ("faq_music_q", "faq_music_a"),
    )
    with page_shell("system_architecture", "/system-architecture", music_context="architecture"):
        with ui.element("section").classes("sy-architecture-hero w-full").props(f'aria-label="{t("system_architecture")}"'):
            with ui.column().classes("gap-2"):
                ui.label(t("architecture_kicker")).classes("sy-architecture-kicker")
                ui.label(t("system_architecture")).classes("sy-architecture-title")
                ui.label(t("architecture_intro")).classes("sy-architecture-copy")
                _tone_badge(t("architecture_local_badge"), "stable").classes("mt-3 self-start")
                ui.label(t("architecture_reading_note")).classes("sy-architecture-reading-note")
                ui.label(t("architecture_platform_link_note")).classes("sy-architecture-reading-note")
                ui.button(t("open_platform"), icon="domain", on_click=lambda: ui.navigate.to("/platform")).props(
                    "outline data-testid=architecture-open-platform"
                ).classes("mt-2 self-start")

        with ui.element("section").classes("sy-architecture-section w-full").props(f'aria-label="{t("architecture_flow_title")}"'):
            _render_architecture_section_heading("architecture_flow_kicker", "architecture_flow_title", "architecture_flow_copy")
            ui.element("div").classes("sy-architecture-lifeline-visual w-full").props("aria-hidden=true data-testid=architecture-lifeline-visual")
            with ui.element("ol").classes("sy-service-lifeline").props("data-testid=service-lifeline"):
                for index, (icon, title_key, body_key, result_key) in enumerate(service_flow, start=1):
                    with ui.element("li").classes("sy-service-stage"):
                        with ui.row().classes("sy-service-stage-head items-center gap-3 no-wrap"):
                            ui.label(f"{index:02d}").classes("sy-service-stage-index").props("aria-hidden=true")
                            ui.icon(icon).classes("sy-service-stage-icon").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-service-stage-title")
                        ui.label(t(body_key)).classes("sy-service-stage-copy")
                        ui.label(t(result_key)).classes("sy-service-stage-result")

        with ui.element("section").classes("sy-architecture-section w-full").props(f'aria-label="{t("architecture_layers_title")}"'):
            _render_architecture_section_heading("architecture_layers_kicker", "architecture_layers_title", "architecture_layers_copy")
        with ui.element("section").classes("sy-architecture-grid w-full").props(f'aria-label="{t("architecture_layers_title")}"'):
            for icon, title_key, body_key in layers:
                with ui.element("article").classes("sy-architecture-layer"):
                    ui.icon(icon).classes("sy-architecture-layer-icon").props("aria-hidden=true")
                    ui.label(t(title_key)).classes("sy-architecture-layer-title")
                    ui.label(t(body_key)).classes("sy-architecture-layer-copy")

        with ui.element("section").classes("sy-architecture-section w-full").props(f'aria-label="{t("architecture_evidence_title")}"'):
            _render_architecture_section_heading("architecture_evidence_kicker", "architecture_evidence_title", "architecture_evidence_copy")
            with ui.element("div").classes("sy-trust-evidence-grid").props("data-testid=trust-evidence"):
                for icon, title_key, body_key, label_key in evidence:
                    with ui.element("article").classes("sy-trust-evidence-card"):
                        ui.icon(icon).classes("sy-trust-evidence-icon").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-trust-evidence-title")
                        ui.label(t(body_key)).classes("sy-trust-evidence-copy")
                        ui.label(t(label_key)).classes("sy-trust-evidence-label")

        with ui.element("section").classes("sy-architecture-faq w-full").props(f'aria-label="{t("architecture_faq_title")}" data-testid=architecture-faq'):
            _render_architecture_section_heading("architecture_faq_kicker", "architecture_faq_title", "architecture_faq_copy")
            with ui.column().classes("sy-architecture-faq-list w-full gap-2"):
                for question_key, answer_key in faq_items:
                    with ui.expansion(t(question_key), icon="help_outline").classes("sy-architecture-faq-item w-full"):
                        ui.label(t(answer_key)).classes("sy-architecture-faq-answer")
        _render_feedback_channel()


def _render_architecture_section_heading(kicker_key: str, title_key: str, copy_key: str) -> None:
    with ui.column().classes("sy-architecture-section-heading gap-1"):
        ui.label(t(kicker_key)).classes("sy-architecture-section-kicker")
        ui.label(t(title_key)).classes("sy-architecture-section-title")
        ui.label(t(copy_key)).classes("sy-architecture-section-copy")


@ui.page("/devotional")
def devotional_page() -> None:
    verse = select_daily_verse()
    locale_is_zh = current_locale() == ZH_HK
    reference = verse.reference_zh if locale_is_zh else verse.reference_en
    scripture = verse.scripture_zh if locale_is_zh else verse.scripture_en
    reflection = verse.reflection_zh if locale_is_zh else verse.reflection_en
    with page_shell("devotional", "/devotional", music_context="devotional"):
        with ui.element("section").classes("sy-chapel w-full"):
            ui.label(t("daily_verse")).classes("sy-kicker")
            ui.label(scripture).classes("sy-verse")
            ui.label(reference).classes("text-base font-medium text-[#F2D393]")
            ui.separator().classes("my-7 bg-[#F2D393]/50")
            ui.label(reflection.get("title", "")).classes("text-xl font-semibold")
            ui.label(reflection.get("body", "")).classes("sy-reflection")
            if reflection.get("prayer"):
                ui.label(f"{t('prayer')}: {reflection['prayer']}").classes("mt-3 text-sm italic text-[#F2D393]")


@ui.page("/settings")
def settings_page() -> None:
    workflow = get_workflow()
    status = workflow.backup_status()
    backup_inventory = workflow.backup_inventory()
    backups = list(backup_inventory["items"])
    backup_options = {
        str(item["path"]): f"{item['createdAt']:%Y-%m-%d %H:%M} | {item['path'].name}"
        for item in backups
        if item["verification"].get("valid")
    }
    readiness = workflow.handover_readiness()
    with page_shell("settings", "/settings"):
        ui.label(t("settings")).classes("text-2xl font-semibold")
        _render_operation_hint("hint_settings", icon="settings_backup_restore")
        render_music_library_settings()
        with ui.card().classes("sy-surface w-full max-w-3xl p-6"):
            with ui.row().classes("w-full items-center justify-between gap-4 flex-wrap"):
                with ui.column().classes("gap-1"):
                    ui.label(t("handover")).classes("text-lg font-semibold")
                    ui.label(t("handover_intro")).classes("text-sm text-[var(--sy-muted)]")
                ui.button(t("open_handover_guide"), icon="handshake", on_click=lambda: ui.navigate.to("/handover")).props("outline color=primary")
            with ui.row().classes("w-full gap-3 flex-wrap mt-4"):
                for label_key, value, ready in (
                    ("handover_prefects_ready", f"{readiness['activePrefectCount']}", readiness["activePrefectCount"] > 0),
                    ("handover_rosters_ready", f"{readiness['rosterCount']}", readiness["rosterCount"] > 0),
                    ("handover_backup_ready", t("verified") if readiness["verifiedBackup"] else t("handover_attention"), readiness["verifiedBackup"]),
                ):
                    with ui.element("div").classes("sy-status-summary"):
                        ui.label(t(label_key)).classes("text-xs text-[var(--sy-muted)]")
                        ui.label(value).classes("font-semibold")
                        ui.icon("check_circle" if ready else "priority_high").classes("sy-fg-stable" if ready else "sy-fg-attention")
        with ui.card().classes("sy-surface w-full max-w-3xl p-6"):
            ui.label(t("persistence_notice")).classes("text-lg font-semibold")
            ui.label(f"{t('database')}: {status['databasePath']}").classes("text-sm text-[var(--sy-muted)] mt-3")
            ui.label(f"{t('backup_directory')}: {status['backupDirectory']}").classes("text-sm text-[var(--sy-muted)]")
            if status["latestPath"]:
                ui.label(str(status["latestPath"])).classes("text-xs text-[var(--sy-muted)] mt-2")
            verification = status["latestVerification"]
            if verification and verification.get("valid"):
                _tone_badge(t("verified"), "stable").classes("mt-3")
            invalid_backup_count = int(backup_inventory["invalidCount"])
            if invalid_backup_count:
                reason_keys = {
                    "missing_file": "backup_issue_file",
                    "invalid_extension": "backup_issue_file",
                    "manifest_missing": "backup_issue_manifest",
                    "manifest_unreadable": "backup_issue_manifest",
                    "checksum_mismatch": "backup_issue_checksum",
                    "sqlite_unreadable": "backup_issue_database",
                    "integrity_failed": "backup_issue_database",
                    "schema_incomplete": "backup_issue_schema",
                    "unknown": "backup_issue_unknown",
                }
                with ui.element("section").classes("sy-backup-integrity-warning w-full mt-4").props(
                    'role=status aria-live=polite data-testid=invalid-backup-summary'
                ):
                    with ui.row().classes("items-start gap-3 no-wrap"):
                        ui.icon("gpp_maybe").classes("sy-backup-integrity-warning-icon").props("aria-hidden=true")
                        with ui.column().classes("gap-1 grow"):
                            ui.label(t("invalid_backup_summary_title", count=invalid_backup_count)).classes(
                                "font-semibold"
                            )
                            ui.label(t("invalid_backup_summary_body")).classes(
                                "text-sm leading-6 text-[var(--sy-muted)]"
                            )
                            with ui.row().classes("gap-2 flex-wrap mt-1"):
                                for reason_code, count in dict(backup_inventory["invalidReasonCounts"]).items():
                                    message_key = reason_keys.get(str(reason_code), "backup_issue_unknown")
                                    _tone_badge(f"{t(message_key)} × {count}", "attention")

        async def create_verified_backup() -> None:
            result = await _run_with_progress(
                workflow.create_verified_backup,
                title_key="progress_manual_backup_title",
                working_key="progress_manual_backup_working",
                icon="add_to_drive",
            )
            if result is not _OPERATION_FAILED:
                ui.notify(t("verified_backup_created"), type="positive")
                ui.navigate.reload()

        with ui.card().classes("sy-surface w-full max-w-3xl p-6"):
            ui.label(t("handover_backup_package")).classes("text-lg font-semibold")
            ui.label(t("handover_backup_package_notice")).classes("text-sm text-[var(--sy-muted)] mt-1")
            if backup_options:
                with ui.dialog() as handover_package_dialog, ui.card().classes("sy-surface w-full max-w-md p-6"):
                    ui.label(t("handover_backup_package")).classes("text-lg font-semibold")
                    ui.label(t("handover_backup_package_warning")).classes("text-sm leading-6 text-[var(--sy-muted)] mt-2")

                    async def download_handover_package() -> None:
                        package = await _run_with_progress(
                            workflow.build_verified_handover_package,
                            title_key="progress_handover_title",
                            working_key="progress_handover_working",
                            icon="archive",
                        )
                        if package is not _OPERATION_FAILED:
                            ui.download(package.content, package.filename)
                            ui.notify(t("handover_backup_package_ready"), type="positive")
                            handover_package_dialog.close()

                    with ui.row().classes("w-full justify-end gap-3 mt-5"):
                        ui.button(t("cancel"), icon="close", on_click=handover_package_dialog.close).props("flat")
                        ui.button(t("confirm_handover_backup_package"), icon="download", on_click=download_handover_package).props("color=primary")
                ui.button(
                    t("handover_backup_package"),
                    icon="archive",
                    on_click=handover_package_dialog.open,
                ).props("outline color=primary data-testid=handover-package-ready-action").classes("mt-4")
            else:
                _render_empty_state(
                    title_key="no_verified_backup_title",
                    body_key="no_verified_backup_handover_body",
                    icon="inventory_2",
                    action_key="create_verified_backup",
                    action=create_verified_backup,
                )
                ui.button(t("handover_backup_package"), icon="archive").props(
                    "outline disable aria-disabled=true data-testid=handover-package-disabled-no-backup"
                ).classes("mt-3")

        with ui.card().classes("sy-surface w-full max-w-3xl p-6"):
            ui.label(t("backup_restore")).classes("text-lg font-semibold")
            ui.label(t("restore_warning")).classes("text-sm text-[var(--sy-muted)] mt-1")
            ui.label(t("create_verified_backup_notice")).classes("text-sm leading-6 text-[var(--sy-muted)] mt-3")
            if backup_options:
                ui.button(
                    t("create_verified_backup"),
                    icon="add_to_drive",
                    on_click=create_verified_backup,
                ).props("outline data-testid=create-verified-backup-action").classes("mt-3")
                selected_backup = ui.select(
                    label=t("select_backup"),
                    options=backup_options,
                    value=next(iter(backup_options)),
                ).classes("w-full mt-4")

                with ui.dialog() as restore_dialog, ui.card().classes("sy-surface w-full max-w-md p-6"):
                    ui.label(t("confirm_restore")).classes("text-lg font-semibold")
                    ui.label(t("restore_warning")).classes("text-sm text-[var(--sy-muted)] mt-2")

                    async def restore_selected_backup() -> None:
                        backup_path = Path(str(selected_backup.value))
                        restore_dialog.close()
                        result = await _run_with_progress(
                            lambda: workflow.restore_backup(backup_path),
                            title_key="progress_restore_title",
                            working_key="progress_restore_working",
                            icon="restore",
                        )
                        if result is not _OPERATION_FAILED:
                            ui.notify(t("backup_restored"), type="positive")
                            ui.navigate.reload()

                    with ui.row().classes("w-full justify-end gap-3 mt-5"):
                        ui.button(t("cancel"), icon="close", on_click=restore_dialog.close).props("flat")
                        ui.button(t("confirm_restore"), icon="restore", on_click=restore_selected_backup).props(
                            "color=negative data-testid=confirm-restore-action"
                        )
                ui.button(
                    t("restore_selected_backup"),
                    icon="restore",
                    on_click=restore_dialog.open,
                ).props("outline data-testid=restore-ready-action").classes("sy-button-attention mt-4")
            else:
                _render_empty_state(
                    title_key="no_verified_backup_title",
                    body_key="no_verified_backup_restore_body",
                    icon="settings_backup_restore",
                    action_key="create_verified_backup",
                    action=create_verified_backup,
                    action_props="outline color=primary data-testid=create-verified-backup-action",
                )
                ui.button(t("restore_selected_backup"), icon="restore").props(
                    "outline disable aria-disabled=true data-testid=restore-disabled-no-backup"
                ).classes("mt-3")
