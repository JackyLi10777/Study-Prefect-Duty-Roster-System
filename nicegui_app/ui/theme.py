"""Calm, modern system-interface tokens for NiceGUI pages."""

from __future__ import annotations

from nicegui import ui

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


def current_theme() -> str:
    return str(preference_get("theme", "light"))


def toggle_theme() -> None:
    preference_set("theme", "dark" if current_theme() == "light" else "light")


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
    is_dark = current_theme() == "dark"
    dark_mode = ui.dark_mode(value=is_dark)
    # Quasar utilities and the CSS tokens must share every semantic role;
    # otherwise framework defaults can leak into danger and dark-mode controls.
    apply_quasar_palette(is_dark)
    ui.add_head_html(THEME_HEAD_HTML)
    ui.add_head_html(MOTION_HEAD_HTML)
    return dark_mode
