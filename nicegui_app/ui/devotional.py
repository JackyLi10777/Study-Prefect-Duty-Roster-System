"""Daily-verse selection and browser-local devotional preferences."""

from __future__ import annotations

from datetime import date, timedelta

from nicegui import ui

from nicegui_app.ui.preferences import preference_get, preference_set
from nicegui_app.ui.theme import current_theme
from roster_core import select_daily_verse


_DEVOTIONAL_GUIDANCE_THEMES = (
    "servant-leadership",
    "justice-fairness",
    "wisdom-discernment",
    "witness-light",
)
_DEVOTIONAL_COMFORT_THEMES = (
    "prayer-peace",
    "mercy-care",
    "perseverance",
    "faithfulness",
    "spiritual-formation",
)


def devotional_tone() -> str:
    preference = str(preference_get("devotional_tone", "auto"))
    if preference == "auto":
        return "comfort" if current_theme() == "dark" else "guidance"
    return preference if preference in {"guidance", "comfort"} else "guidance"


def set_devotional_tone(value: str) -> None:
    if value not in {"auto", "guidance", "comfort"}:
        return
    preference_set("devotional_tone", value)
    preference_set("dashboard_verse_offset", 0)
    ui.navigate.reload()


def dashboard_verse() -> object:
    offset = int(preference_get("dashboard_verse_offset", 0))
    themes = (
        _DEVOTIONAL_COMFORT_THEMES
        if devotional_tone() == "comfort"
        else _DEVOTIONAL_GUIDANCE_THEMES
    )
    return select_daily_verse(date.today() + timedelta(days=offset), themes_any=themes)


def refresh_dashboard_verse() -> None:
    preference_set("dashboard_verse_offset", int(preference_get("dashboard_verse_offset", 0)) + 1)
    ui.navigate.reload()


__all__ = ("dashboard_verse", "devotional_tone", "refresh_dashboard_verse", "set_devotional_tone")
