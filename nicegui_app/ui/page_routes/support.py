"""Local-first incident feedback for verified administrators and guests."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import sys
from urllib.parse import urlencode

from nicegui import events, ui

from nicegui_app.access_context import AccessMode, Capability
from nicegui_app.application_mode import current_application_mode
from nicegui_app.config import POLICY_VERSION
from nicegui_app.contact import FEEDBACK_EMAIL
from nicegui_app.observability import new_operation_reference, record_operator_failure
from nicegui_app.release_evidence import release_source_fingerprint
from nicegui_app.runtime import current_page_context
from nicegui_app.services.support_incidents import (
    ALLOWED_ROUTE_CATEGORIES,
    ALLOWED_WORKFLOW_ACTIONS,
    AttachmentInput,
    IncidentReportInput,
    IncidentNotFoundError,
    IncidentValidationError,
    INCIDENT_ID_PATTERN,
    MAX_ATTACHMENT_BYTES,
    MAX_ATTACHMENTS,
    OP_REFERENCE_PATTERN,
    REQ_REFERENCE_PATTERN,
    SupportInbox,
)
from nicegui_app.ui.components import action, status
from nicegui_app.ui.downloads import deliver_generated_download
from nicegui_app.ui.html_safety import attr, text
from nicegui_app.ui.i18n import current_locale, t
from nicegui_app.ui.page_shared import _OPERATION_FAILED, _run_with_progress
from nicegui_app.ui.shell import page_shell


_ATTACHMENT_MEDIA_TYPES = {
    ".txt": "text/plain",
    ".json": "application/json",
    ".png": "image/png",
}


def _option_label(value: str) -> str:
    key = f"support_option_{value}"
    translated = t(key)
    return translated if translated != key else value.replace("_", " ").title()


_ROUTE_CATEGORY_BY_PATH = {
    "/": "dashboard",
    "/rosters": "rosters",
    "/prefects": "prefects",
    "/handover": "handover",
    "/settings": "settings",
    "/access-control": "access_control",
    "/platform": "platform",
    "/engineering": "engineering",
    "/system-architecture": "system_architecture",
    "/getting-started": "getting_started",
    "/guide": "guide",
    "/devotional": "devotional",
    "/view": "viewer",
}


def _support_defaults(source_path: str) -> tuple[str, str]:
    """Infer safe, stable diagnostic metadata from the source route."""

    normalized = "/" + str(source_path or "").split("?", 1)[0].strip("/")
    if normalized == "//":
        normalized = "/"
    if normalized.startswith("/rosters/"):
        return "roster_workflow", "page_view"
    return _ROUTE_CATEGORY_BY_PATH.get(normalized, "other"), "page_view"


def _support_source_path() -> str:
    try:
        requested = str(ui.context.client.request.query_params.get("source", ""))
    except (AttributeError, RuntimeError):
        return ""
    normalized = "/" + requested.split("?", 1)[0].strip("/")
    return normalized if normalized in _ROUTE_CATEGORY_BY_PATH or normalized.startswith("/rosters/") else ""


def _safe_optional_reference(value: object, pattern: re.Pattern[str]) -> tuple[str, ...]:
    normalized = str(value or "").strip().upper()
    if not normalized:
        return ()
    if not pattern.fullmatch(normalized):
        raise IncidentValidationError("invalid support reference")
    return (normalized,)


def _guest_report_markup(source_path: str = "") -> str:
    required_fields = (
        ("expected", "support_expected", True),
        ("actual", "support_actual", True),
        ("steps", "support_reproduction", True),
    )
    optional_fields = (
        ("impact", "support_impact", False),
        ("frequency", "support_frequency", False),
        ("last-good", "support_last_good", False),
    )

    def render_fields(fields: tuple[tuple[str, str, bool], ...]) -> str:
        rendered: list[str] = []
        for identifier, label_key, required in fields:
            suffix = " *" if required else f" ({text(t('optional'))})"
            required_attribute = "required" if required else ""
            rendered.append(
                f'<label class="sy-support-browser-field" for="sy-support-{attr(identifier)}">'
                f'<span>{text(t(label_key))}{suffix}</span>'
                f'<textarea id="sy-support-{attr(identifier)}" maxlength="4000" '
                f'{required_attribute}></textarea></label>'
            )
        return "".join(rendered)

    route_default, action_default = _support_defaults(source_path)
    route_options = "".join(
        f'<option value="{attr(value)}" {"selected" if value == route_default else ""}>{text(_option_label(value))}</option>'
        for value in sorted(ALLOWED_ROUTE_CATEGORIES)
    )
    action_options = "".join(
        f'<option value="{attr(value)}" {"selected" if value == action_default else ""}>{text(_option_label(value))}</option>'
        for value in sorted(ALLOWED_WORKFLOW_ACTIONS)
    )
    return f"""
    <section class="sy-support-browser" data-testid="guest-browser-only-support"
      data-required-message="{attr(t('support_required_error'))}"
      data-copy-failed-message="{attr(t('support_guest_copy_failed'))}"
      data-email="{attr(FEEDBACK_EMAIL)}" data-locale="{attr(current_locale())}">
      <p class="sy-support-browser-status">{text(t('support_guest_nonpersistent'))}</p>
      <p class="sy-support-browser-copy">{text(t('support_guest_body'))}</p>
      <form id="sy-support-browser-form" novalidate>
        <div class="sy-support-browser-grid">
          {render_fields(required_fields)}
        </div>
        <details class="sy-support-details">
          <summary>{text(t('support_add_details'))}</summary>
          <div class="sy-support-browser-grid">
            <label class="sy-support-browser-field" for="sy-support-route"><span>{text(t('support_route_category'))}</span>
              <select id="sy-support-route">{route_options}</select></label>
            <label class="sy-support-browser-field" for="sy-support-action"><span>{text(t('support_workflow_action'))}</span>
              <select id="sy-support-action">{action_options}</select></label>
            {render_fields(optional_fields)}
          </div>
        </details>
        <p id="sy-support-browser-error" class="sy-field-error" role="alert" aria-live="polite"></p>
        <div class="sy-support-browser-actions">
          <button type="submit" class="sy-support-browser-primary">{text(t('support_guest_build'))}</button>
          <button type="reset" class="sy-support-browser-reset">{text(t('support_guest_reset'))}</button>
        </div>
        <output id="sy-support-browser-result" aria-live="polite"></output>
        <div id="sy-support-browser-result-actions" class="sy-support-browser-actions" hidden>
          <button type="button" id="sy-support-browser-download">{text(t('support_guest_download'))}</button>
          <button type="button" id="sy-support-browser-copy">{text(t('support_guest_copy'))}</button>
          <button type="button" id="sy-support-browser-email">{text(t('support_email_action'))}</button>
        </div>
      </form>
    </section>
    """


def _render_guest_support(source_path: str) -> None:
    ui.add_head_html('<script defer src="/assets/motion/support-feedback-v1.js"></script>')
    ui.html(_guest_report_markup(source_path), sanitize=False).classes("w-full")


def _render_admin_support(source_path: str) -> None:
    context = current_page_context()
    context.require(Capability.PERSISTENT_WRITE)
    attachments: list[AttachmentInput] = []
    route_default, action_default = _support_defaults(source_path)

    with ui.element("section").classes("sy-operations-panel sy-support-admin w-full"):
        status(t("support_local_first"), "stable")
        ui.label(t("support_admin_body")).classes("sy-reading-measure text-sm leading-6 text-[var(--sy-muted)]")
        with ui.element("div").classes("sy-support-form-grid w-full"):
            expected = ui.textarea(label=t("support_expected")).props("maxlength=4000 autogrow").classes("w-full")
            actual = ui.textarea(label=t("support_actual")).props("maxlength=4000 autogrow").classes("w-full")
            reproduction = ui.textarea(label=t("support_reproduction")).props("maxlength=6000 autogrow").classes("w-full")
        with ui.expansion(t("support_add_details"), icon="add_circle_outline").classes("sy-support-details w-full"):
            with ui.element("div").classes("sy-support-form-grid w-full"):
                route = ui.select(
                    label=t("support_route_category"),
                    options={value: _option_label(value) for value in sorted(ALLOWED_ROUTE_CATEGORIES)},
                    value=route_default,
                ).classes("w-full")
                workflow_action = ui.select(
                    label=t("support_workflow_action"),
                    options={value: _option_label(value) for value in sorted(ALLOWED_WORKFLOW_ACTIONS)},
                    value=action_default,
                ).classes("w-full")
                impact = ui.textarea(label=t("support_impact") + f" ({t('optional')})").props("maxlength=4000 autogrow").classes("w-full")
                frequency = ui.input(label=t("support_frequency") + f" ({t('optional')})").props("maxlength=500").classes("w-full")
                last_good = ui.input(label=t("support_last_good") + f" ({t('optional')})").props("maxlength=1000").classes("w-full")
                operation_reference = ui.input(label=t("support_operation_reference") + f" ({t('optional')})").props(
                    "maxlength=11 autocomplete=off"
                ).classes("w-full")
                request_reference = ui.input(label=t("support_request_reference") + f" ({t('optional')})").props(
                    "maxlength=12 autocomplete=off"
                ).classes("w-full")

            attachment_summary = ui.column().classes("w-full gap-1")

            async def accept_attachment(event: events.UploadEventArguments) -> None:
                suffix = Path(event.file.name).suffix.lower()
                media_type = _ATTACHMENT_MEDIA_TYPES.get(suffix)
                content = await event.file.read()
                if media_type is None or len(content) > MAX_ATTACHMENT_BYTES or len(attachments) >= MAX_ATTACHMENTS:
                    ui.notify(t("support_attachment_rejected"), type="negative")
                    return
                attachments.append(
                    AttachmentInput(
                        filename=event.file.name,
                        media_type=media_type,
                        content=content,
                        consent_at_utc=datetime.now(timezone.utc).isoformat(),
                    )
                )
                with attachment_summary:
                    ui.label(t("support_attachment_added", name=event.file.name)).classes(
                        "text-xs text-[var(--sy-muted)]"
                    )

            ui.label(t("support_attachments")).classes("font-semibold mt-2")
            ui.label(t("support_attachment_rules")).classes("sy-reading-measure text-xs leading-5 text-[var(--sy-muted)]")
            ui.upload(
                label=t("support_attachments"),
                multiple=True,
                max_file_size=MAX_ATTACHMENT_BYTES,
                max_total_size=MAX_ATTACHMENT_BYTES * MAX_ATTACHMENTS,
                max_files=MAX_ATTACHMENTS,
                on_upload=accept_attachment,
                on_rejected=lambda: ui.notify(t("support_attachment_rejected"), type="negative"),
                auto_upload=True,
            ).props("accept=.txt,.json,.png").classes("w-full")

        result_area = ui.column().classes("w-full")
        consent = ui.checkbox(t("support_consent"))
        with ui.dialog() as preview_dialog, ui.card().classes("sy-dialog w-full max-w-xl p-6"):
            ui.label(t("support_preview_title")).classes("sy-dialog-title")
            ui.label(t("support_preview_body")).classes("sy-dialog-description")
            preview_summary = ui.label().classes("text-sm leading-6")
            preview_consent = ui.checkbox(t("support_consent"))
            with ui.row().classes("w-full justify-end gap-3 mt-4"):
                action(t("cancel"), icon="close", on_click=preview_dialog.close, variant="quiet")
                save_button = action(t("support_save_action"), icon="save", variant="primary", test_id="save-support-incident")

        def validate_form() -> tuple[str, ...] | None:
            steps = tuple(line.strip() for line in str(reproduction.value or "").splitlines() if line.strip())
            if not str(expected.value or "").strip() or not str(actual.value or "").strip() or not steps:
                ui.notify(t("support_required_error"), type="negative")
                return None
            try:
                _safe_optional_reference(operation_reference.value, OP_REFERENCE_PATTERN)
                _safe_optional_reference(request_reference.value, REQ_REFERENCE_PATTERN)
            except IncidentValidationError:
                ui.notify(t("support_reference_error"), type="negative")
                return None
            return steps

        def open_preview() -> None:
            steps = validate_form()
            if steps is None:
                return
            characters = sum(len(str(value or "")) for value in (
                expected.value,
                actual.value,
                reproduction.value,
                impact.value,
                frequency.value,
                last_good.value,
            ))
            preview_summary.text = t(
                "support_preview_summary",
                route=_option_label(str(route.value)),
                action=_option_label(str(workflow_action.value)),
                characters=characters,
                attachments=len(attachments),
            )
            preview_consent.value = bool(consent.value)
            preview_dialog.open()

        async def save_incident() -> None:
            if not preview_consent.value:
                ui.notify(t("support_consent_error"), type="negative")
                return
            steps = validate_form()
            if steps is None:
                preview_dialog.close()
                return
            operation_id = new_operation_reference()
            try:
                active_context = current_page_context()
                active_context.require(Capability.PERSISTENT_WRITE)
                page_request_reference = active_context.request_reference.strip().upper()
                request_references = list(_safe_optional_reference(request_reference.value, REQ_REFERENCE_PATTERN))
                if REQ_REFERENCE_PATTERN.fullmatch(page_request_reference) and page_request_reference not in request_references:
                    request_references.append(page_request_reference)
                report = IncidentReportInput(
                    source="admin_ui",
                    actor_mode="admin",
                    route_category=str(route.value),
                    workflow_action=str(workflow_action.value),
                    expected_behavior=str(expected.value or ""),
                    actual_behavior=str(actual.value or ""),
                    reproduction_steps=steps,
                    impact=str(impact.value or ""),
                    frequency=str(frequency.value or ""),
                    last_known_good=str(last_good.value or ""),
                    operation_references=tuple({operation_id, *_safe_optional_reference(operation_reference.value, OP_REFERENCE_PATTERN)}),
                    request_references=tuple(request_references),
                    safe_error_type="operator_report",
                    safe_code_locations=(f"route:{route.value}",),
                )
            except PermissionError as error:
                reference = record_operator_failure(
                    error,
                    action="create_support_incident",
                    reference=operation_id,
                )
                preview_dialog.close()
                ui.notify(
                    t("support_save_failed", reference=reference),
                    type="negative",
                    timeout=8_000,
                )
                return

            application_mode = current_application_mode()
            active_locale = current_locale()
            attachment_snapshot = tuple(attachments)

            def create_incident():  # type: ignore[no-untyped-def]
                source_fingerprint, _ = release_source_fingerprint()
                return SupportInbox().create_incident(
                    report,
                    application_version=os.getenv("SING_YIN_RELEASE_VERSION", POLICY_VERSION),
                    source_fingerprint=source_fingerprint,
                    application_mode=application_mode.mode,
                    environment={
                        "platform_family": platform.system().lower(),
                        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
                        "locale": active_locale,
                    },
                    health_summary={"capture": "ok"},
                    events=({
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "category": "operator_report",
                        "outcome": "submitted",
                    },),
                    attachments=attachment_snapshot,
                )

            summary = await _run_with_progress(
                create_incident,
                title_key="progress_support_save_title",
                working_key="progress_support_save_working",
                icon="support_agent",
            )
            if summary is _OPERATION_FAILED:
                preview_dialog.close()
                return
            preview_dialog.close()
            consent.value = True
            attachments.clear()
            attachment_summary.clear()
            ui.notify(t("support_saved"), type="positive")
            result_area.clear()
            with result_area:
                with ui.element("section").classes("sy-support-result w-full").props("role=status aria-live=polite"):
                    status(t("support_saved"), "stable")
                    ui.label(t("support_incident_id")).classes("text-sm text-[var(--sy-muted)]")
                    ui.label(summary.incident_id).classes("text-xl font-semibold font-mono").props("data-testid=support-incident-id")
                    with ui.row().classes("w-full gap-3 flex-wrap"):
                        action(
                            t("support_copy_id"),
                            icon="content_copy",
                            variant="secondary",
                            on_click=lambda: ui.run_javascript(
                                f"navigator.clipboard.writeText({json.dumps(summary.incident_id)})"
                            ),
                        )
                        action(
                            t("support_download_bundle"),
                            icon="archive",
                            variant="secondary",
                            on_click=lambda: deliver_generated_download(
                                SupportInbox().export_bundle_bytes(summary.incident_id),
                                f"{summary.incident_id}.zip",
                                media_type="application/zip",
                            ),
                        )
                        subject = f"Incident {summary.incident_id} / 事件報告"
                        mailto = f"mailto:{FEEDBACK_EMAIL}?{urlencode({'subject': subject, 'body': summary.incident_id})}"
                        action(
                            t("support_email_action"),
                            icon="mail_outline",
                            variant="quiet",
                            motion_role="forward",
                            icon_story_to="forward_to_inbox",
                            icon_story_category="preview",
                            on_click=lambda: ui.run_javascript(f"window.location.href={json.dumps(mailto)}"),
                        )

        save_button.on("click", save_incident)
        action(
            t("support_preview_action"),
            icon="preview",
            on_click=open_preview,
            variant="primary",
            test_id="preview-support-incident",
        ).classes("mt-2")

    with ui.element("section").classes("sy-operations-panel sy-support-lookup w-full"):
        ui.label(t("support_lookup_title")).classes("text-lg font-semibold")
        ui.label(t("support_lookup_body")).classes(
            "sy-reading-measure text-sm leading-6 text-[var(--sy-muted)]"
        )
        lookup_id = ui.input(label=t("support_lookup_label")).props(
            "maxlength=21 autocomplete=off spellcheck=false data-testid=support-lookup-id"
        ).classes("w-full max-w-md font-mono")
        lookup_result = ui.column().classes("w-full")

        async def lookup_incident() -> None:
            incident_id = str(lookup_id.value or "").strip().upper()
            lookup_result.clear()
            if not INCIDENT_ID_PATTERN.fullmatch(incident_id):
                ui.notify(t("support_lookup_invalid"), type="warning")
                return

            def inspect_incident():  # type: ignore[no-untyped-def]
                try:
                    return SupportInbox().validate_bundle(incident_id)
                except IncidentNotFoundError:
                    return None

            summary = await _run_with_progress(
                inspect_incident,
                title_key="progress_support_lookup_title",
                working_key="progress_support_lookup_working",
                icon="manage_search",
            )
            if summary is _OPERATION_FAILED:
                return
            if summary is None:
                ui.notify(t("support_lookup_not_found"), type="warning")
                return
            with lookup_result:
                with ui.element("section").classes("sy-support-result w-full").props(
                    "role=status aria-live=polite data-testid=support-lookup-result"
                ):
                    status(t("support_lookup_verified"), "stable")
                    ui.label(summary.incident_id).classes("text-xl font-semibold font-mono")
                    ui.label(
                        t(
                            "support_lookup_summary",
                            page=_option_label(summary.route_category),
                            action=_option_label(summary.workflow_action),
                            state=summary.lifecycle_status,
                        )
                    ).classes("text-sm leading-6 text-[var(--sy-muted)]")
                    action(
                        t("support_download_bundle"),
                        icon="archive",
                        variant="secondary",
                        on_click=lambda incident_id=summary.incident_id: deliver_generated_download(
                            SupportInbox().export_bundle_bytes(incident_id),
                            f"{incident_id}.zip",
                            media_type="application/zip",
                        ),
                    )

        action(
            t("support_lookup_action"),
            icon="manage_search",
            on_click=lookup_incident,
            variant="secondary",
            test_id="lookup-support-incident",
        )


@ui.page("/support")
def support_page() -> None:
    context = current_page_context()
    source_path = _support_source_path()
    with page_shell("/support"):
        with ui.element("section").classes("sy-support-hero w-full").props(
            f'aria-label="{attr(t("support_hero_title"))}" data-testid=support-hero'
        ):
            with ui.column().classes("sy-support-hero-copy gap-3"):
                ui.label(t("support_hero_kicker")).classes("sy-support-hero-kicker")
                ui.label(t("support_hero_title")).classes("sy-support-hero-title")
                ui.label(t("support_hero_intro")).classes("sy-support-hero-intro")
                with ui.element("ol").classes("sy-support-hero-steps"):
                    for index, key in enumerate(
                        ("support_hero_step_one", "support_hero_step_two", "support_hero_step_three"),
                        start=1,
                    ):
                        with ui.element("li"):
                            ui.label(f"{index:02d}").classes("sy-support-hero-step-number")
                            ui.label(t(key))
                ui.label(
                    t("support_hero_guest_scope" if context.principal.mode is AccessMode.GUEST else "support_hero_admin_scope")
                ).classes("sy-support-hero-scope")
        with ui.element("div").classes("sy-support-layout w-full"):
            if context.principal.mode is AccessMode.GUEST:
                _render_guest_support(source_path)
            else:
                _render_admin_support(source_path)
            with ui.column().classes("sy-support-aside gap-4"):
                with ui.element("aside").classes("sy-developer-reference-card"):
                    ui.icon("privacy_tip").classes("sy-developer-reference-icon")
                    ui.label(t("support_exclusions_title")).classes("sy-developer-reference-title")
                    ui.label(t("support_exclusions_body")).classes("sy-developer-reference-copy")
