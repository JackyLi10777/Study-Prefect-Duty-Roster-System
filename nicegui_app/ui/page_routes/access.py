"""Local access-control console route."""

from nicegui import ui

from nicegui_app.runtime import get_workflow
from nicegui_app.ui.access_control import render_access_control_console
from nicegui_app.ui.i18n import t
from nicegui_app.ui.page_access import (
    is_guest_mode as _is_guest_mode,
    render_restricted_capability as _render_restricted_capability,
)
from nicegui_app.ui.shell import page_shell


@ui.page("/access-control")
def access_control_page() -> None:
    with page_shell("/access-control"):
        ui.label(t("access_control")).classes("text-2xl font-semibold")
        if _is_guest_mode():
            ui.label(t("access_control_intro")).classes(
                "text-base leading-7 text-[var(--sy-muted)] max-w-4xl"
            )
            _render_restricted_capability(icon="admin_panel_settings")
        else:
            render_access_control_console(get_workflow())
