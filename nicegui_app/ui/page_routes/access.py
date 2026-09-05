"""Local access-control console route."""

from nicegui import ui
from zoneinfo import ZoneInfo

from nicegui_app.access_context import Capability
from nicegui_app.runtime import current_page_context, get_workflow
from nicegui_app.ui.access_control import render_access_control_console
from nicegui_app.ui.i18n import t
from nicegui_app.ui.lazy_sections import lazy_expansion
from nicegui_app.ui.page_access import (
    is_guest_mode as _is_guest_mode,
    render_restricted_capability as _render_restricted_capability,
)
from nicegui_app.ui.shell import page_shell


@ui.page("/access-control")
def access_control_page() -> None:
    context = current_page_context()
    principal = context.principal
    session_value = (
        t("access_summary_expires_at", value=principal.expires_at.astimezone(
            ZoneInfo("Asia/Hong_Kong")).strftime("%Y-%m-%d %H:%M HKT"))
        if principal.expires_at is not None else t("access_summary_active")
    )
    with page_shell("/access-control"):
        ui.label(t("access_control")).classes("text-2xl font-semibold")
        ui.label(t("access_control_intro")).classes("text-base leading-7 text-[var(--sy-muted)] max-w-4xl")
        with ui.element("section").classes("sy-surface sy-operations-panel w-full max-w-4xl p-6").props(
            "data-testid=access-status-summary"
        ):
            ui.label(t("access_summary_title")).classes("text-xl font-semibold")
            with ui.element("dl").classes("w-full grid gap-4 mt-4"):
                for label_key, value in (
                    ("access_summary_identity", principal.subject),
                    ("access_summary_session", session_value),
                    ("access_summary_security", t("access_summary_capabilities", count=len(context.capabilities))),
                ):
                    with ui.element("div").classes("min-w-0 border-b border-[var(--sy-line)] pb-3"):
                        with ui.element("dt"):
                            ui.label(t(label_key)).classes("text-xs font-semibold text-[var(--sy-muted)]")
                        with ui.element("dd"):
                            ui.label(value).classes("text-sm break-all")
        if _is_guest_mode():
            _render_restricted_capability(icon="admin_panel_settings")
        else:
            def render_technical() -> None:
                current_page_context().require(Capability.EXTERNAL_DELIVERY)
                render_access_control_console(get_workflow())

            lazy_expansion(t("access_technical_controls"), icon="admin_panel_settings",
                           test_id="access-technical-controls", render=render_technical).classes(
                "sy-surface sy-operations-panel max-w-4xl"
            )
