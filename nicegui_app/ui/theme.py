"""Calm, modern system-interface tokens for NiceGUI pages."""

from __future__ import annotations

from nicegui import app, ui

from nicegui_app.ui.theme_markup import THEME_HEAD_HTML


ATMOSPHERE_THEME_PAIRS = {
    "sidebar": ("sidebar-stewardship-light-v1.webp", "sidebar-stewardship-dark-v1.webp"),
    "weekly-pulse": ("weekly-pulse-light-v1.webp", "weekly-pulse-dark-v1.webp"),
    "devotional": ("devotional-sacred-light-v1.webp", "devotional-sacred-dark-v1.webp"),
    "onboarding": ("onboarding-desk-light-v1.webp", "onboarding-desk-dark-v1.webp"),
    "handover": ("handover-archive-light-v1.webp", "handover-archive-dark-v1.webp"),
    "platform": ("platform-stewardship-light-v1.webp", "platform-stewardship-dark-v1.webp"),
    "architecture": ("architecture-stewardship-light-v1.webp", "architecture-stewardship-dark-v1.webp"),
    "architecture-lifeline": ("architecture-lifeline-light-v1.webp", "architecture-lifeline-dark-v1.webp"),
    "empty-ready": ("empty-ready-light-v1.webp", "empty-ready-dark-v1.webp"),
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


def apply_theme() -> None:
    """Inject one restrained theme system for every page before content renders."""
    is_dark = current_theme() == "dark"
    ui.dark_mode(value=is_dark)
    # Quasar's semantic primary is the single source for actionable controls.
    # Named teal palette classes remain available for verified/stable badges.
    ui.colors(primary="#47758B" if is_dark else "#35647C")
    ui.add_head_html(THEME_HEAD_HTML)
