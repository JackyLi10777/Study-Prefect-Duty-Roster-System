from __future__ import annotations

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.i18n import EN, MESSAGES, ZH_HK
from nicegui_app.ui.page_catalog import PAGE_DEFINITIONS
from nicegui_app.ui.theme_markup import STYLE_LAYERS
from tests.ui_source import combined_page_source, combined_theme_source


def test_mobile_shell_is_an_adaptive_view_of_the_same_routes() -> None:
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")
    main = (PROJECT_ROOT / "nicegui_app" / "main.py").read_text(encoding="utf-8")
    pages = combined_page_source()

    assert (
        "mobile",
        "/assets/css/sing-yin-mobile-v1.css",
        "(max-width: 900px)",
    ) in STYLE_LAYERS
    assert "MOBILE_PRIMARY_NAVIGATION" in shell
    assert 'viewport="width=device-width, initial-scale=1, viewport-fit=cover"' in main
    assert 'data-testid=mobile-bottom-navigation' in shell
    assert 'data-testid=mobile-drawer-tools' in shell
    assert 'aria-controls=main-navigation-drawer' in shell
    assert "aria-expanded=false data-testid=mobile-more" in shell
    assert "_install_mobile_drawer_accessibility()" in shell
    assert "event.key === 'Escape'" in shell
    assert "button.focus({preventScroll: true})" in shell
    assert "event.key !== 'Tab'" in shell
    assert "const focusable = ()" in shell
    assert "const shell = drawer.closest('.q-drawer')" in shell
    assert "observer.observe(shell" in shell
    assert "event.target.closest('.q-drawer__backdrop')" in shell
    assert "window.__syDrawerA11yCleanup?.()" in shell
    assert "controller.abort()" in shell
    assert "show-if-above breakpoint=900" in shell
    assert shell.index('with ui.element("main")') < shell.index(
        "_render_mobile_tabbar(drawer, active_path, access_mode)"
    )
    assert '@ui.page("/mobile' not in pages
    assert {"/", "/rosters", "/prefects"} <= {
        page.route for page in PAGE_DEFINITIONS if page.mobile_primary
    }


def test_mobile_navigation_copy_is_complete_in_both_languages() -> None:
    for key in (
        "mobile_primary_navigation",
        "mobile_more",
        "mobile_quick_settings",
        "switch_to_english",
        "switch_to_chinese",
        "enable_sound_feedback",
        "disable_sound_feedback",
    ):
        assert MESSAGES[key][ZH_HK].strip()
        assert MESSAGES[key][EN].strip()


def test_phone_layout_has_safe_areas_touch_targets_and_scrollable_navigation() -> None:
    theme = combined_theme_source()

    assert "grid-template-columns: repeat(4, minmax(0, 1fr))" in theme
    assert "env(safe-area-inset-bottom)" in theme
    assert ".sy-sidebar { position: relative; isolation: isolate; overflow-x: hidden; overflow-y: auto;" in theme
    assert ".sy-header-bar { min-height: 56px; flex-wrap: nowrap !important;" in theme
    assert ".sy-main .q-btn { min-width: 44px; min-height: 44px; }" in theme
    assert ".sy-main .q-toggle, .sy-main .q-checkbox, .sy-main .q-radio { min-height: 44px; }" in theme
    assert ".sy-sidebar .q-btn__content { width: 100%; justify-content: flex-start; text-align: left; }" in theme
    assert ".sy-main .q-item.q-item--clickable { min-height: 48px; }" in theme
    assert ".sy-main .q-field__native, .sy-main .q-field__input { font-size: 16px; }" in theme
    assert "max-height: min(92dvh, 760px)" in theme
    assert ".sy-music-dialog-header { position: sticky;" in theme
    assert "@media (max-width: 900px) and (orientation: landscape)" in theme


def test_dense_operator_tables_switch_to_mobile_cards() -> None:
    pages = combined_page_source()
    components = (PROJECT_ROOT / "nicegui_app" / "ui" / "components.py").read_text(encoding="utf-8")

    assert pages.count("_render_responsive_table(") >= 6
    assert 'props("grid hide-header")' in components
    assert ':grid="$q.screen.lt.md"' not in pages
    assert "sy-fairness-trend-chart" in pages
    assert "sy-page-lead" in pages
    assert "sy-roster-detail-head" in pages
    assert "sy-roster-week-item" in pages
    assert "sy-mobile-field-row" in pages
    assert "sy-mobile-actions" in pages
    assert '"type": "scroll"' in pages
    assert 'chart_dark = current_theme() == "dark"' in pages
    assert '"hideOverlap": True' in pages


def test_mobile_dialog_actions_share_one_responsive_action_grammar() -> None:
    sources = {
        path: (PROJECT_ROOT / path).read_text(encoding="utf-8")
        for path in (
            "nicegui_app/ui/music.py",
            "nicegui_app/ui/page_shared.py",
            "nicegui_app/ui/page_routes/people.py",
            "nicegui_app/ui/page_routes/stewardship.py",
            "nicegui_app/ui/page_routes/weekly.py",
        )
    }

    for path, source in sources.items():
        assert '.classes("w-full justify-end' not in source, path
    assert sum(source.count("sy-mobile-actions") for source in sources.values()) >= 12


def test_validation_errors_use_theme_aware_semantic_danger_color() -> None:
    people = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "people.py").read_text(encoding="utf-8")

    assert "text-red-600" not in people
    assert people.count("sy-fg-danger") >= 4


def test_preferences_preserve_unfinished_forms_and_language_fails_safe() -> None:
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")

    assert "_toggle_theme_in_place" in shell
    assert "_toggle_sound_feedback_with_preview" in shell
    assert "document.body.dataset.syFormDirty" in shell
    assert "preference_reload_warning" in shell
    assert "_reload_after_preference_change(toggle_theme)" not in shell


def test_concurrent_statuses_share_one_non_overlapping_stack() -> None:
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")
    theme = combined_theme_source()

    assert "data-testid=system-status-stack" in shell
    assert ".sy-status-stack { position: sticky" in theme
    assert ".sy-practice-banner { position: relative" in theme
    assert ".sy-maintenance-banner { position: relative" in theme
