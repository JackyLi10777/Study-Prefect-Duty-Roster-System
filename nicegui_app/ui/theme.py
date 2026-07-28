"""Calm, modern system-interface tokens for NiceGUI pages."""

from __future__ import annotations

from nicegui import ui

from nicegui_app.access_context import PageContext
from nicegui_app.ui.design_token_contract import quasar_palette
from nicegui_app.ui.preferences import preference_get, preference_set
from nicegui_app.ui.theme_markup import THEME_HEAD_HTML
from nicegui_app.ui.motion import MOTION_HEAD_HTML


ATMOSPHERE_THEME_PAIRS = {
    "sidebar": ("sidebar-stewardship-light-v1.webp", "sidebar-stewardship-dark-v1.webp"),
    "weekly-pulse": ("weekly-pulse-light-v1.webp", "weekly-pulse-dark-v1.webp"),
    "devotional": ("devotional-sacred-light-v1.webp", "devotional-sacred-dark-v1.webp"),
    "onboarding": ("onboarding-desk-light-v1.webp", "onboarding-desk-dark-v1.webp"),
    "handover": ("handover-archive-light-v1.webp", "handover-archive-dark-v1.webp"),
    "platform": ("platform-stewardship-light-v1.webp", "platform-stewardship-dark-v1.webp"),
    "guide": ("guide-handbook-light-v1.webp", "guide-handbook-dark-v1.webp"),
    "engineering": ("engineering-workbench-light-v1.webp", "engineering-workbench-dark-v1.webp"),
    "architecture": ("architecture-stewardship-light-v1.webp", "architecture-stewardship-dark-v1.webp"),
    "architecture-lifeline": ("architecture-lifeline-light-v1.webp", "architecture-lifeline-dark-v1.webp"),
    "empty-ready": ("empty-ready-light-v1.webp", "empty-ready-dark-v1.webp"),
}

# Quasar is a framework-fill bridge, not a second palette. Both dictionaries
# resolve from the same versioned contract that generates the CSS variables.
QUASAR_LIGHT_PALETTE = quasar_palette(mode="light")
QUASAR_DARK_PALETTE = quasar_palette(mode="dark")


def theme_preference() -> str:
    """Return the operator's stable appearance choice.

    A missing or invalid preference follows the client operating system.
    ``system`` is an unset state; the browser supplies a short resolved hint
    through the same Admin/Guest preference adapter before theme-dependent
    server content is kept on screen.
    """

    value = str(preference_get("theme", "system"))
    return value if value in {"system", "light", "dark"} else "system"


def system_theme_resolution() -> str:
    """Return the last browser-resolved system appearance for this session.

    A neutral light hint is used only for the first render.  The shell compares
    it with ``prefers-color-scheme`` and performs one early reload when they do
    not match, so charts, devotional tone and music all use the browser result.
    """

    value = str(preference_get("theme_system_resolved", "light"))
    return value if value in {"light", "dark"} else "light"


def current_theme() -> str:
    value = theme_preference()
    return value if value in {"light", "dark"} else system_theme_resolution()


def set_system_theme_resolution(value: str) -> None:
    """Remember one verified browser result without changing the preference."""

    if value not in {"light", "dark"}:
        raise ValueError("system theme resolution must be light or dark")
    preference_set("theme_system_resolved", value)


def set_theme_preference(value: str) -> None:
    """Persist one explicit appearance choice without hidden cycling."""

    if value not in {"system", "light", "dark"}:
        raise ValueError("theme preference must be system, light, or dark")
    preference_set("theme", value)


def adopt_verified_theme_handoff(context: PageContext) -> bool:
    """Adopt the Public entrance choice once when this workspace is unset.

    The hint is authenticated by the gateway and can only be light or dark.
    Existing Admin or Guest preferences always win, preserving their separate
    durable and process-local storage boundaries.
    """

    if preference_get("theme", None) in {"system", "light", "dark"}:
        return False
    handoff = context.principal.theme_handoff
    if handoff not in {"light", "dark"}:
        return False
    preference_set("theme", handoff)
    return True


def next_explicit_theme(resolved_theme: str) -> str:
    """Return the one-click destination for the binary appearance control.

    ``system`` is deliberately not part of the click cycle.  Callers resolve
    the browser's current appearance first, then persist the opposite explicit
    value.  Keeping this small rule here prevents desktop, mobile and public
    surfaces from inventing different theme cycles.
    """

    if resolved_theme not in {"light", "dark"}:
        raise ValueError("resolved theme must be light or dark")
    return "dark" if resolved_theme == "light" else "light"


def sound_feedback_enabled() -> bool:
    """Sound is always opt-in so shared school computers remain quiet by default."""
    return bool(preference_get("sound_feedback", False))


def toggle_sound_feedback() -> None:
    preference_set("sound_feedback", not sound_feedback_enabled())


def set_sound_feedback(enabled: bool) -> None:
    preference_set("sound_feedback", bool(enabled))


def apply_quasar_palette(is_dark: bool) -> None:
    """Keep Quasar utility classes aligned with the semantic CSS token system."""

    ui.colors(**(QUASAR_DARK_PALETTE if is_dark else QUASAR_LIGHT_PALETTE))


def apply_theme():  # type: ignore[no-untyped-def]
    """Inject one restrained theme system for every page before content renders."""
    appearance = theme_preference()
    is_dark = current_theme() == "dark"
    dark_mode = ui.dark_mode(value=None if appearance == "system" else is_dark)
    # Quasar utilities and the CSS tokens must share every semantic role;
    # otherwise framework defaults can leak into danger and dark-mode controls.
    apply_quasar_palette(is_dark)
    ui.add_head_html(THEME_HEAD_HTML)
    ui.add_head_html(MOTION_HEAD_HTML)
    return dark_mode
