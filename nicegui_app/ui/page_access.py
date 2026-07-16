"""Access-mode presentation helpers shared by official route renderers."""

from __future__ import annotations

from nicegui import ui

from nicegui_app.access_context import AccessMode, Capability
from nicegui_app.application_mode import current_application_mode
from nicegui_app.runtime import current_page_context
from nicegui_app.ui.i18n import t


def is_guest_mode() -> bool:
    """Return the server-verified access mode for the current page."""

    return current_page_context().principal.mode is AccessMode.GUEST


def allows(capability: Capability) -> bool:
    """Check a presentation capability without treating UI state as a security boundary."""

    return current_page_context().allows(capability)


def is_demo_export() -> bool:
    """Mark exports produced by either practice mode or a guest workspace."""

    return current_application_mode().is_practice or is_guest_mode()


def render_restricted_capability(*, icon: str = "lock") -> None:
    """Explain an unavailable action with the shared non-interrupting state."""

    with ui.element("aside").classes("sy-inline-empty sy-restricted-state w-full").props(
        "role=status data-testid=guest-restricted-state"
    ):
        ui.icon(icon).classes("sy-inline-empty-icon").props("aria-hidden=true")
        with ui.column().classes("gap-1 min-w-0"):
            ui.label(t("access_restricted_title")).classes("sy-inline-empty-title")
            ui.label(t("access_restricted_body")).classes("sy-inline-empty-copy")


__all__ = ("allows", "is_demo_export", "is_guest_mode", "render_restricted_capability")
