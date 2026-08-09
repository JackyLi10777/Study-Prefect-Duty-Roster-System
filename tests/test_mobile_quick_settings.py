from __future__ import annotations

import re

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.i18n import EN, MESSAGES, ZH_HK


def _source(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_mobile_quick_settings_use_state_tiles_not_desktop_header_controls() -> None:
    shell = _source("nicegui_app/ui/shell.py")
    renderer = shell.split("def _render_mobile_drawer_tools", 1)[1].split(
        "def _render_mobile_tabbar", 1
    )[0]

    assert "class MobileSettingTile" in shell
    assert "def _render_mobile_setting_tile" in shell
    assert renderer.count("_render_mobile_setting_tile(") == 4
    assert "_header_control_classes" not in renderer
    assert "sy-header-control" not in renderer
    assert "sy-mobile-setting-tile" in shell

    sound = renderer.split('kind="sound"', 1)[1].split(
        "theme_icon, theme_label", 1
    )[0]
    theme = renderer.split('kind="theme"', 1)[1].split(
        "if access_mode", 1
    )[0]
    assert "pressed=sound_enabled" in sound
    assert "pressed=" not in theme
    assert "data-sy-theme-pressed" not in theme
    assert "button.removeAttribute('aria-pressed')" in shell
    assert "data-sy-theme-pressed=true" in shell


def test_mobile_setting_tiles_own_shape_focus_and_narrow_reflow() -> None:
    mobile = _source("nicegui_app/assets/css/sing-yin-mobile-v1.css")
    tile_rule = re.search(
        r"\.sy-mobile-setting-tile\s*\{([^}]*)\}", mobile, re.DOTALL
    )

    assert tile_rule is not None
    tile_css = tile_rule.group(1)
    assert "min-height: 74px" in tile_css
    assert "border-radius: 14px" in tile_css
    assert "box-shadow: none" in tile_css
    assert "transform: none" in tile_css
    assert "border-radius: 50%" not in tile_css
    assert "border-radius: 999px" not in tile_css
    assert "var(--sy-rotary-shadow)" not in tile_css
    assert ".sy-mobile-setting-tile:focus-visible" in mobile
    assert ".sy-mobile-setting-tile .q-icon[data-sy-icon-motion]::after" in mobile
    assert "content: none !important" in mobile
    assert "container-type: inline-size" in mobile
    assert "@container (max-width: 16rem)" in mobile

    narrow = mobile.split("@media (max-width: 320px)", 1)[1].split("}", 3)
    assert any(
        "grid-template-columns: minmax(0, 1fr)" in rule for rule in narrow
    )


def test_drawer_open_state_visually_and_semantically_removes_bottom_navigation() -> None:
    shell = _source("nicegui_app/ui/shell.py")
    mobile = _source("nicegui_app/assets/css/sing-yin-mobile-v1.css")
    page_shell = shell.split("drawer = ui.left_drawer", 1)[1]

    assert page_shell.index('classes("sy-sidebar-navigation")') < page_shell.index(
        "_render_mobile_drawer_tools("
    )
    assert "setBackgroundInert(modalOpen)" in shell
    assert "keyboardOwnsTabbar" in shell
    assert "drawerOwnsTabbar" in shell
    assert "effectiveUnavailable = unavailable || drawerOwnsTabbar" in shell
    assert "classList.toggle('sy-mobile-drawer-open', modalOpen)" in shell
    assert "classList.remove('sy-mobile-drawer-open')" in shell
    assert ".sy-mobile-drawer-open .sy-mobile-tabbar" in mobile
    assert "returnFocusTarget.focus({preventScroll: true})" in shell
    assert "data-testid=mobile-drawer-close data-sy-drawer-trigger=close" in shell


def test_mobile_setting_state_copy_is_complete_in_both_languages() -> None:
    keys = (
        "mobile_setting_language",
        "mobile_setting_sound",
        "mobile_setting_appearance",
        "mobile_setting_account",
        "mobile_setting_value_chinese",
        "mobile_setting_value_english",
        "mobile_setting_on",
        "mobile_setting_off",
        "mobile_theme_auto_light",
        "mobile_theme_auto_dark",
        "mobile_theme_light",
        "mobile_theme_dark",
        "mobile_setting_account_admin",
        "mobile_setting_account_guest",
    )

    for key in keys:
        assert MESSAGES[key][ZH_HK].strip()
        assert MESSAGES[key][EN].strip()

    assert "登出" in MESSAGES["mobile_setting_account_admin"][ZH_HK]
    assert "登出" in MESSAGES["mobile_setting_account_guest"][ZH_HK]
    assert "Sign out" in MESSAGES["mobile_setting_account_admin"][EN]
    assert "Sign out" in MESSAGES["mobile_setting_account_guest"][EN]
