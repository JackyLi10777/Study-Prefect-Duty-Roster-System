"""Local access-control console route."""

from nicegui_app.ui.page_shared import *  # noqa: F403
from nicegui_app.ui.access_control import render_access_control_console


@ui.page("/access-control")
def access_control_page() -> None:
    with page_shell("access_control", "/access-control"):
        ui.label(t("access_control")).classes("text-2xl font-semibold")
        render_access_control_console(get_workflow())
