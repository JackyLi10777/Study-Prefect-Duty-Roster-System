from __future__ import annotations

import re

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.i18n import EN, MESSAGES, ZH_HK
from nicegui_app.ui.page_catalog import PAGE_DEFINITIONS
from nicegui_app.ui.theme_markup import STYLE_LAYERS
from tests.ui_source import combined_page_source, combined_theme_source


def test_mobile_shell_is_an_adaptive_view_of_the_same_routes() -> None:
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")
    mobile_css = (PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-mobile-v1.css").read_text(
        encoding="utf-8"
    )
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
    assert "const currentBackdrop = ()" in shell
    assert "const backdropVisible = ()" in shell
    assert "bounds.right > Math.min(44, bounds.width * .25) && backdropVisible()" in shell
    assert "observer.observe(backdrop" in shell
    assert "event.target.closest('.q-drawer__backdrop')" in shell
    assert "const settle = (expectedOpen, focusDrawer = false)" in shell
    assert "const renderedState = isMobile() ? renderedOpen : renderedVisible" in shell
    assert "const transitionOpen = typeof requestedOpen === 'boolean'" in shell
    assert "const open = renderedState" in shell
    assert "return renderedState" in shell
    assert "def _install_mobile_drawer_accessibility" in shell
    drawer_accessibility = shell.split("def _install_mobile_drawer_accessibility", 1)[1].split(
        "def _install_mobile_viewport_accessibility", 1
    )[0]
    assert "let requestedOpen = null" in drawer_accessibility
    assert "let syncFrame = 0" in drawer_accessibility
    assert "drawerButtons().forEach(trigger =>" in drawer_accessibility
    assert 'data-testid=mobile-drawer-close data-sy-drawer-trigger=close' in shell
    assert "const closeOnly = trigger.matches('[data-sy-drawer-trigger=\"close\"]')" in shell
    assert "closeOnly || transitionOpen ? 'close' : 'menu'" in shell
    assert "settle(expectedOpen, trigger === button && expectedOpen)" in drawer_accessibility
    assert "const currentIntent = typeof requestedOpen === 'boolean'" in drawer_accessibility
    assert "settleFrame = requestAnimationFrame(tick)" in drawer_accessibility
    assert "const returnFocusTarget" in drawer_accessibility
    assert "returnFocusTarget.focus({preventScroll: true})" in drawer_accessibility
    assert "const reconcileBreakpoint = () =>" in drawer_accessibility
    assert "let mobileViewport = isMobile()" in drawer_accessibility
    assert "const enteredMobileViewport = nextMobileViewport && !mobileViewport" in drawer_accessibility
    assert "const setMobileDrawerIntent = open =>" in drawer_accessibility
    assert "if (viewportChanged) setMobileDrawerIntent(false)" in drawer_accessibility
    assert "setMobileDrawerIntent(expectedOpen)" in drawer_accessibility
    assert "if (close instanceof HTMLElement) close.click()" in drawer_accessibility
    assert "let breakpointFrame = 0" in drawer_accessibility
    assert "if (breakpointFrame) cancelAnimationFrame(breakpointFrame)" in drawer_accessibility
    assert 'ui.button(icon="close", on_click=drawer.hide)' in shell
    assert "requestedOpen = null" in drawer_accessibility
    assert "scheduleSync(false)" in drawer_accessibility
    assert "document.querySelector('.sy-desktop-drawer-trigger')?.click()" not in shell
    assert "window.addEventListener('resize', reconcileBreakpoint" in shell
    assert "if (syncFrame) cancelAnimationFrame(syncFrame)" in drawer_accessibility
    assert "performance.now() - startedAt >= 3000" in drawer_accessibility
    assert "setTimeout(() => sync(true), 220)" not in shell
    assert "setTimeout(() => sync(false), 260)" not in shell
    assert "window.__syDrawerA11yCleanup?.()" in shell
    assert "if (settleFrame) cancelAnimationFrame(settleFrame)" in shell
    assert "controller.abort()" in shell
    assert "show-if-above breakpoint=900" in shell
    assert "html:not(.sy-mobile-drawer-intent-open) #main-navigation-drawer" in mobile_css
    assert "html:not(.sy-mobile-drawer-intent-open) .q-drawer__backdrop" in mobile_css
    assert shell.index('with ui.element("main")') < shell.index(
        "_render_mobile_tabbar(drawer, active_path, access_mode)"
    )
    assert '@ui.page("/mobile' not in pages
    assert {"/", "/rosters", "/prefects"} <= {
        page.route for page in PAGE_DEFINITIONS if page.mobile_primary
    }

    verifier = (PROJECT_ROOT / "scripts" / "verify_nicegui_ui.py").read_text(encoding="utf-8")
    assert "mobile_viewport = page.evaluate" in verifier
    assert 'mobile_navigation.wait_for(state="attached"' in verifier
    assert 'more = page.get_by_test_id("mobile-more")' in verifier
    assert "dataset.syDrawerA11y === 'ready'" in verifier
    assert "more.click()" in verifier
    assert "main#main-content')?.inert === true" not in verifier
    assert "main#main-content')?.inert !== true" in verifier
    assert 'mobile_navigation.locator("button").last.click()' not in verifier

    mobile_verifier = (PROJECT_ROOT / "scripts" / "verify_nicegui_mobile.py").read_text(
        encoding="utf-8"
    )
    assert "getAttribute('aria-expanded') === 'true'" in mobile_verifier
    assert "Opening mobile navigation must move focus into the drawer." in mobile_verifier


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


def test_mobile_canvas_reflows_below_320_without_locking_document_scroll() -> None:
    """Zoomed and narrow viewports must reflow instead of forcing a 320px canvas."""

    mobile = (
        PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-mobile-v1.css"
    ).read_text(encoding="utf-8")
    theme = combined_theme_source()

    assert "min-width: 320px" not in theme
    assert "overscroll-behavior-y: none" not in mobile
    assert "@media (max-width: 320px)" in mobile
    narrow_scope = mobile.split("@media (max-width: 320px)", 1)[1]
    assert "--sy-mobile-gutter:" in narrow_scope
    assert ".sy-main > * { min-width: 0; max-width: 100%; }" in mobile
    assert "overflow-wrap: anywhere" in mobile


def test_mobile_keyboard_uses_visual_viewport_and_disposes_route_listeners() -> None:
    """The fixed tab bar must not hide fields when a phone keyboard opens."""

    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")

    assert "window.visualViewport" in shell
    assert "window.__syMobileViewportCleanup?.()" in shell
    assert "window.__syMobileViewportCleanup =" in shell
    assert "visualViewport.addEventListener('resize'" in shell
    assert "visualViewport.addEventListener('scroll'" in shell
    assert "const controller = new AbortController()" in shell
    assert "signal: controller.signal" in shell
    assert "controller.abort()" in shell
    assert "sy-mobile-keyboard-open" in shell
    assert "const effectiveUnavailable = unavailable || drawerOwnsTabbar" in shell
    assert "tabbar.inert = effectiveUnavailable" in shell
    assert "tabbar.setAttribute('aria-hidden', 'true')" in shell
    assert "setTabbarUnavailable(false)" in shell
    assert "window.clearTimeout(revealTimer)" in shell


def test_tablet_keeps_reading_grids_but_operator_workflows_stay_single_column() -> None:
    """Medium screens can compare evidence while task forms retain one clear path."""

    layout = (
        PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-layout-v1.css"
    ).read_text(encoding="utf-8")

    tablet_marker = "@media (min-width: 640px) and (max-width: 900px)"
    assert tablet_marker in layout
    tablet_scope = layout.split(tablet_marker, 1)[1]
    assert ".sy-evidence-summary-grid" in tablet_scope
    assert ".sy-developer-reference-grid" in tablet_scope
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in tablet_scope

    mobile_scope = layout.split("@media (max-width: 900px)", 1)[1].split(tablet_marker, 1)[0]
    operations_rule = mobile_scope.split(".sy-operations-grid", 1)[1].split("}", 1)[0]
    assert "grid-template-columns: minmax(0, 1fr)" in operations_rule


def test_tablet_portrait_cards_and_landscape_desktop_shell_use_intermediate_density() -> None:
    layout = (
        PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-layout-v1.css"
    ).read_text(encoding="utf-8")
    mobile = (
        PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-mobile-v1.css"
    ).read_text(encoding="utf-8")
    theme = combined_theme_source()

    portrait_marker = "@media (min-width: 640px) and (max-width: 900px)"
    landscape_marker = "@media (min-width: 901px) and (max-width: 1180px)"
    assert portrait_marker in mobile
    assert portrait_marker in theme
    assert landscape_marker in layout
    assert landscape_marker in theme

    portrait_mobile = mobile.split(portrait_marker, 1)[1]
    assert ".sy-table .q-table__grid-content" in portrait_mobile
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in portrait_mobile
    portrait_theme = theme.split(portrait_marker, 1)[1]
    assert ".sy-roster-mobile" in portrait_theme
    assert ".sy-prefect-mobile" in portrait_theme
    assert ".sy-download-options" in portrait_theme

    landscape_layout = layout.split(landscape_marker, 1)[1]
    assert ".sy-operations-grid" in landscape_layout
    assert ".sy-document-layout" in landscape_layout
    assert ".sy-evidence-toolbar" in landscape_layout
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in landscape_layout


def test_adaptive_footer_reserves_bottom_navigation_and_safe_area() -> None:
    mobile = (
        PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-mobile-v1.css"
    ).read_text(encoding="utf-8")

    footer_rule = mobile.split(".sy-page-footer", 1)[1].split("}", 1)[0]
    assert "--sy-mobile-tabbar-height" in footer_rule
    assert "env(safe-area-inset-bottom)" in footer_rule


def test_coarse_pointer_desktop_shell_retains_touch_sized_links_and_items() -> None:
    theme = combined_theme_source()

    coarse_scope = theme.split("@media (hover: none) and (pointer: coarse)", 1)[1]
    assert "a[href]:not(.sy-skip-link)" in coarse_scope
    assert ".q-toggle" in coarse_scope
    assert ".q-checkbox" in coarse_scope
    assert ".q-radio" in coarse_scope
    assert ".q-item.q-item--clickable" in coarse_scope
    assert ".q-expansion-item > .q-expansion-item__container > .q-item" in coarse_scope
    assert ".q-uploader__header .q-btn" in coarse_scope
    assert "min-height: 44px" in coarse_scope
    assert "min-width: 44px" in coarse_scope


def test_sidebar_uses_fixed_brand_scrollable_navigation_and_compact_footer() -> None:
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")
    verifier = (PROJECT_ROOT / "scripts" / "verify_nicegui_ui.py").read_text(encoding="utf-8")
    command_center = (
        PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-command-center-v2.css"
    ).read_text(encoding="utf-8")

    assert "sy-sidebar-brand" in shell
    assert "sy-sidebar-navigation" in shell
    assert "sy-sidebar-footer" in shell
    assert not re.search(
        r'''data-testid\s*=\s*[\'\"]?sidebar-feedback[\'\"]?''',
        shell,
    )
    assert 'page.get_by_test_id("sidebar-feedback").count() == 0' in verifier
    assert "sidebar_feedback_links" not in verifier
    assert 'page.goto(f"{BASE_URL}/support"' in verifier
    body_rule = re.search(r"\.sy-sidebar-body\s*\{([^}]*)\}", command_center, re.DOTALL)
    fixed_rule = re.search(
        r"\.sy-sidebar-brand,\s*\.sy-sidebar-footer\s*\{([^}]*)\}",
        command_center,
        re.DOTALL,
    )
    navigation_rule = re.search(
        r"\.sy-sidebar-navigation\s*\{([^}]*)\}", command_center, re.DOTALL
    )
    assert body_rule is not None
    assert fixed_rule is not None
    assert navigation_rule is not None
    assert "display: flex !important" in body_rule.group(1)
    assert "flex-direction: column" in body_rule.group(1)
    assert "height: 100%" in body_rule.group(1)
    assert "max-height: 100%" in body_rule.group(1)
    assert "flex: 0 0 auto" in fixed_rule.group(1)
    assert "flex: 1 1 auto" in navigation_rule.group(1)
    assert "overflow-y: auto" in navigation_rule.group(1)


def test_compact_workflow_navigation_is_a_scroll_snap_sequence() -> None:
    """Workflow steps remain ordered and reachable without becoming a tall card stack."""

    layout = (
        PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-layout-v1.css"
    ).read_text(encoding="utf-8")
    mobile_scope = layout.split("@media (max-width: 900px)", 1)[1]

    workflow_rule = mobile_scope.split(".sy-workflow-navigation", 1)[1].split("}", 1)[0]
    step_rule = mobile_scope.split(".sy-workflow-navigation-step", 1)[1].split("}", 1)[0]
    assert "grid-template-columns: repeat(4, minmax(" in workflow_rule
    assert "overflow-x: auto" in workflow_rule
    assert "scroll-snap-type: x " in workflow_rule
    assert "overscroll-behavior-x: contain" in workflow_rule
    assert "scroll-snap-align: start" in step_rule


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
    assert "ui.radio(" not in shell
    assert "data-testid=mobile-theme-control" in shell
    assert "data-testid=desktop-theme-menu" not in shell
    assert "data-sy-theme-toggle" in shell
    assert "next_explicit_theme" in shell
    assert '"EN" if current_locale()' not in shell
    assert 'else "中"' not in shell
    assert "_toggle_sound_feedback_with_preview" in shell
    assert "document.body.dataset.syFormDirty" in shell
    assert "preference_reload_warning" in shell
    assert "_reload_after_preference_change(toggle_theme)" not in shell


def test_theme_browser_verifier_respects_mobile_three_state_semantics() -> None:
    source = (PROJECT_ROOT / "scripts" / "verify_rc31_theme_controls.py").read_text(
        encoding="utf-8"
    )

    assert "testId === 'mobile-theme-control'" in source
    assert "!control.hasAttribute('aria-pressed')" in source
    assert 'expected_pressed = "" if test_id == "mobile-theme-control"' in source


def test_concurrent_statuses_share_one_non_overlapping_stack() -> None:
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")
    theme = combined_theme_source()

    assert "data-testid=system-status-stack" in shell
    assert ".sy-status-stack { position: sticky" in theme
    assert ".sy-practice-banner { position: relative" in theme
    assert ".sy-maintenance-banner { position: relative" in theme


def test_mobile_browser_verifier_catches_quick_setting_shape_and_drawer_leaks() -> None:
    verifier = (PROJECT_ROOT / "scripts" / "verify_nicegui_mobile.py").read_text(
        encoding="utf-8"
    )

    for contract in (
        "_assert_drawer_quick_settings_contract",
        "borderTopLeftRadius",
        "single-glyph-column",
        "duplicate bottom X controls",
        "element.matches(':focus-visible')",
        "_assert_no_interactive_overlap",
        "_assert_drawer_cleanup_cycles",
        "cycles=20",
        "pointerLights",
        "mobile-drawer-close",
        "hiddenByAncestor",
        "current.inert || current.getAttribute('aria-hidden') === 'true'",
        "classList.contains('sy-mobile-drawer-open')",
        "tabbar?.inert === true",
        "tabbar?.getAttribute('aria-hidden') === 'true'",
        "tabbarStyle?.opacity === '0'",
        "button?.closest('[aria-hidden=\"true\"], [inert]')",
        'page.keyboard.press("Tab")',
        "cannot reach the theme setting by keyboard",
    ):
        assert contract in verifier
    assert "theme.focus()" not in verifier


def test_mobile_verifiers_use_real_touch_chrome_and_collect_release_evidence() -> None:
    nicegui = (PROJECT_ROOT / "scripts" / "verify_nicegui_mobile.py").read_text(
        encoding="utf-8"
    )
    public = (PROJECT_ROOT / "scripts" / "verify_public_roster_viewer.py").read_text(
        encoding="utf-8"
    )

    for source in (nicegui, public):
        assert 'os.getenv("SING_YIN_PLAYWRIGHT_CHANNEL", "chrome")' in source
        assert "SING_YIN_PLAYWRIGHT_ALLOW_BUNDLED_CHROMIUM" in source
        assert "is_mobile=True" in source
        assert "has_touch=True" in source
        assert "device_scale_factor=2" in source
        assert "largest-contentful-paint" in source
        assert "layout-shift" in source
        assert "longtask" in source
        assert "resourceBytes" in source
        assert "forced_colors" in source
        assert "font-size: 200%" in source

    for width in (256, 320, 390, 768, 820, 844, 1024):
        assert re.search(rf"width\s*=\s*{width}\b", nicegui)
    for width, height in ((360, 800), (412, 915), (430, 932)):
        assert re.search(rf"\({width},\s*{height},\s*[\'\"]", nicegui)
    for width in (320, 360, 390, 412):
        assert re.search(rf"width\s*=\s*{width}\b", public)
    for width, height in ((430, 932), (768, 1024), (820, 1180), (844, 390)):
        assert re.search(rf"\({width},\s*{height},\s*[\'\"]", public)
    assert "VISUAL_VIEWPORT_TEST_DOUBLE" in nicegui
    assert "width: () => window.innerWidth" in nicegui
    assert "height: () => window.innerHeight" in nicegui
    assert "get: () => state[name] ?? fallback()" in nicegui
    assert "__sySetTestVisualViewport" in nicegui
    assert "sy-mobile-keyboard-open" in nicegui
    assert "_assert_gsap_failure_static_end_state" in nicegui
    assert "dataset.syMotion === 'unavailable'" in nicegui
    assert '"mobile-language-control"' in nicegui
    assert '"mobile-sound-control"' in nicegui
    assert '"mobile-theme-control"' in nicegui
    assert 'page.keyboard.press("Tab")' in nicegui
    assert "collect_page_errors: bool = True" in nicegui
    assert "if collect_page_errors:" in nicegui
    gsap_scope = nicegui.split("def _assert_gsap_failure_static_end_state", 1)[1].split(
        "def ", 1
    )[0]
    assert "collect_console_errors=False" in gsap_scope
    assert "collect_page_errors=False" not in gsap_scope


def test_public_mobile_verifier_exercises_support_keyboard_and_viewer_context() -> None:
    verifier = (PROJECT_ROOT / "scripts" / "verify_public_roster_viewer.py").read_text(
        encoding="utf-8"
    )

    for contract in (
        "_assert_support_keyboard_flow",
        "supportExpected",
        "supportActual",
        "supportSteps",
        "_assert_viewer_horizontal_context",
        "scrollWidth",
        "scrollLeft",
        "focus-visible",
        "sticky roster context overlaps",
        "_assert_200_percent_public_reflow",
        "desktop.add_init_script(PERFORMANCE_OBSERVER_SCRIPT)",
        "def _write_performance_evidence()",
    ):
        assert contract in verifier
    collection = verifier.split("def _collect_performance_evidence", 1)[1].split(
        "def _attach_error_collectors", 1
    )[0]
    assert collection.index("PERFORMANCE_EVIDENCE.append(evidence)") < collection.index(
        'if evidence["cumulativeLayoutShift"] > 0.15:'
    )
    finalizer = verifier.split("finally:", 1)[1]
    assert "_write_performance_evidence()" in finalizer
