from __future__ import annotations

from tests.ui_source import combined_theme_source

# Read/reflect/pray/return behavior is exercised with real NiceGUI elements in
# test_reading_routes_lifecycle, rather than requiring obsolete decorative cards.


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
