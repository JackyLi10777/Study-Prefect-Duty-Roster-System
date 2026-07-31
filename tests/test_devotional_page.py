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


def test_daily_verse_has_distinct_accessible_light_and_dark_reading_surfaces() -> None:
    theme = combined_theme_source()

    assert "--sy-devotional-ground: #FFF9E8" in theme
    assert "--sy-devotional-control: #FFFDF7" in theme
    assert "--sy-devotional-ink: #213047" in theme
    assert "--sy-devotional-muted: #4E5D6A" in theme
    assert "--sy-devotional-gold: #755A2B" in theme
    assert ".sy-chapel {" in theme
    assert ".body--dark .sy-chapel {" in theme
    light_scope = theme.split(".sy-chapel {", 1)[1].split("}", 1)[0]
    dark_scope = theme.split(".body--dark .sy-chapel {", 1)[1].split("}", 1)[0]
    assert "var(--sy-devotional-ground)" in light_scope
    assert "#101A2C" not in light_scope
    assert "#101A2C" in dark_scope
    assert ".sy-chapel:after { width: 100%; opacity: .16" in theme
    assert ".body--dark .sy-chapel:after { opacity: .20; }" in theme
