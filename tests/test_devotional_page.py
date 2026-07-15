from __future__ import annotations

from tests.ui_source import combined_page_source, combined_theme_source


def test_full_daily_verse_page_has_a_complete_read_reflect_pray_work_journey() -> None:
    pages = combined_page_source()
    theme = combined_theme_source()

    devotional = pages.split('@ui.page("/devotional")', 1)[1]
    assert "verse = _dashboard_verse()" in devotional
    assert 't("devotional_page_intro")' in devotional
    assert 't("refresh_verse")' in devotional
    assert 't("devotional_tone_label")' in devotional
    assert 't("devotional_reflection_title")' in devotional
    assert 't("devotional_prayer_title")' in devotional
    assert 't("devotional_prepare_title")' in devotional
    assert 't("devotional_return_work")' in devotional
    assert "sy-devotional-reading-grid" in devotional
    assert "var(--sy-image-devotional)" in theme
    assert ".sy-devotional-companion" in theme
