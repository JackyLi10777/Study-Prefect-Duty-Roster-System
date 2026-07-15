"""Calm, modern system-interface tokens for NiceGUI pages."""

from __future__ import annotations

from nicegui import app, ui

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

QUASAR_LIGHT_PALETTE = {
    "primary": "#35647C",
    "secondary": "#0F766E",
    "accent": "#0F766E",
    "positive": "#0F766E",
    "negative": "#963C35",
    "info": "#35647C",
    # Quasar renders warning notifications with dark text, so the framework
    # fill must stay pale; the darker amber remains a CSS foreground token.
    "warning": "#F0C96A",
}

QUASAR_DARK_PALETTE = {
    # These values are framework FILLS (white text), not dark-mode foregrounds.
    # Lighter action/stable/coral foregrounds remain in the CSS role tokens.
    "primary": "#47758B",
    "secondary": "#0F766E",
    "accent": "#0F766E",
    "dark": "#1C1C1E",
    "dark_page": "#0D1117",
    "positive": "#0F766E",
    "negative": "#9A4A43",
    "info": "#35647C",
    "warning": "#F0C96A",
}


def current_theme() -> str:
    return app.storage.user.get("theme", "light")


def toggle_theme() -> None:
    app.storage.user["theme"] = "dark" if current_theme() == "light" else "light"


def sound_feedback_enabled() -> bool:
    """Sound is always opt-in so shared school computers remain quiet by default."""
    return bool(app.storage.user.get("sound_feedback", False))


def toggle_sound_feedback() -> None:
    app.storage.user["sound_feedback"] = not sound_feedback_enabled()


def set_sound_feedback(enabled: bool) -> None:
    app.storage.user["sound_feedback"] = bool(enabled)


def apply_quasar_palette(is_dark: bool) -> None:
    """Keep Quasar utility classes aligned with the semantic CSS token system."""

    ui.colors(**(QUASAR_DARK_PALETTE if is_dark else QUASAR_LIGHT_PALETTE))


def apply_theme():  # type: ignore[no-untyped-def]
    """Inject one restrained theme system for every page before content renders."""
    is_dark = current_theme() == "dark"
    dark_mode = ui.dark_mode(value=is_dark)
    # Quasar utilities and the CSS tokens must share every semantic role;
    # otherwise framework defaults can leak into danger and dark-mode controls.
    apply_quasar_palette(is_dark)
    ui.add_head_html(THEME_HEAD_HTML)
    ui.add_head_html(MOTION_HEAD_HTML)
    return dark_mode
