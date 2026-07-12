from __future__ import annotations

from datetime import date

from roster_core import get_foundational_verse, load_devotional_seed, select_daily_verse


def test_foundational_entry_is_mark_10_and_special_use() -> None:
    verse = get_foundational_verse()
    assert verse.id == "dv-0001"
    assert verse.reference_en == "Mark 10:43-45"
    assert verse.reference_zh == "馬可福音 10:43-45"
    assert "dashboard-hero" in verse.special_use
    assert "roster-generation" in verse.special_use
    assert "非以役人，乃役於人" in verse.reflection_zh["title"]


def test_daily_selection_is_stable_epoch_modulo() -> None:
    entries = load_devotional_seed()
    selected = select_daily_verse(date(1970, 1, 1))
    assert selected.id == entries[0].id


def test_dashboard_hero_selection_uses_special_pool() -> None:
    selected = select_daily_verse(date(1970, 1, 1), special_use="dashboard-hero")
    assert "dashboard-hero" in selected.special_use


def test_daily_selection_can_filter_by_any_requested_theme() -> None:
    selected = select_daily_verse(date(1970, 1, 1), themes_any=("prayer-peace", "perseverance"))
    assert {"prayer-peace", "perseverance"}.intersection(selected.themes)
