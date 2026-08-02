from __future__ import annotations

from datetime import date
import re

from roster_core import get_foundational_verse, load_devotional_seed, select_daily_verse


def test_foundational_entry_is_mark_10_and_special_use() -> None:
    verse = get_foundational_verse()
    entries = load_devotional_seed()
    assert verse.id == "dv-0001"
    assert verse.reference_en == "Mark 10:43-45"
    assert verse.reference_zh == "馬可福音 10:43-45"
    assert "dashboard-hero" in verse.special_use
    assert "roster-generation" in verse.special_use
    assert "非以役人，乃役於人" in verse.reflection_zh["title"]
    assert verse.translation_zh == "RCUV 2010"
    assert verse.translation_en == "NKJV"
    assert sum(entry.is_foundational for entry in entries) == 1


def test_every_release_devotional_uses_the_verified_required_translations() -> None:
    entries = load_devotional_seed()

    assert len(entries) == 122
    assert all(entry.translation_zh == "RCUV 2010" for entry in entries)
    assert all(entry.translation_en == "NKJV" for entry in entries)
    assert all(entry.scripture_zh.strip() for entry in entries)
    assert all(entry.scripture_en.strip().endswith("(NKJV)") for entry in entries)


def test_acts_24_16_is_the_curated_how_we_serve_conviction() -> None:
    entry = next(item for item in load_devotional_seed() if item.id == "dv-0122")

    assert entry.reference_zh == "使徒行傳 24:16"
    assert entry.reference_en == "Acts 24:16"
    assert entry.scripture_zh == "因此，我勉勵自己，對　神對人，時常存着無虧的良心。"
    assert entry.scripture_en == (
        "This being so, I myself always strive to have a conscience without offense toward God and men. (NKJV)"
    )
    assert entry.reflection_zh["title"] == "對神對人，常存無虧的良心"
    assert entry.reflection_en["title"] == "A Conscience Without Offense"
    assert "不是靠行為換取救恩" in entry.reflection_zh["body"]
    assert "neither salvation earned by works" in entry.reflection_en["body"]
    assert set(entry.themes) == {"justice-fairness", "faithfulness", "spiritual-formation"}
    assert set(entry.special_use) == {"roster-generation", "platform-conviction"}
    assert not entry.is_foundational


def test_release_devotional_scripture_has_no_scraped_chapter_or_arabic_script_artifacts() -> None:
    entries = load_devotional_seed()
    arabic_script = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]")
    leading_chapter = re.compile(r"^(?:(?:[^。！？]{1,48})\s+)?\d{1,3}(?:\s+|$)")
    footnote_marker = re.compile(r"\[[a-zA-Z]\]")

    assert not {
        entry.id: entry.scripture_zh
        for entry in entries
        if (
            arabic_script.search(entry.scripture_zh)
            or leading_chapter.search(entry.scripture_zh)
            or footnote_marker.search(entry.scripture_zh)
            or footnote_marker.search(entry.scripture_en)
        )
    }


def test_first_timothy_3_includes_verse_one_without_page_heading() -> None:
    entry = next(item for item in load_devotional_seed() if item.id == "dv-0038")

    assert entry.scripture_zh.startswith("「若有人想望監督的職分")
    assert "監督的資格" not in entry.scripture_zh


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
