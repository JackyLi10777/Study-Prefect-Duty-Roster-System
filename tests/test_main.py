from __future__ import annotations

from PIL import Image

from nicegui_app.main import open_browser_on_startup
from nicegui_app.config import DISPLAY_PRINT_CREST_PATH, DISPLAY_WEB_CREST_PATH, FAVICON_CREST_PATH, NAVIGATION_CREST_PATH, PROJECT_ROOT
from nicegui_app.ui.theme import ATMOSPHERE_THEME_PAIRS
from tests.ui_source import combined_theme_source


def _image_dimensions(path) -> tuple[int, int]:  # type: ignore[no-untyped-def]
    with Image.open(path) as image:
        return image.size


def test_browser_opens_by_default_for_local_new_users(monkeypatch) -> None:
    monkeypatch.delenv("SING_YIN_OPEN_BROWSER", raising=False)
    assert open_browser_on_startup() is True


def test_browser_auto_open_can_be_disabled_for_managed_or_headless_runs(monkeypatch) -> None:
    monkeypatch.setenv("SING_YIN_OPEN_BROWSER", "false")
    assert open_browser_on_startup() is False


def test_original_atmosphere_assets_are_available_to_the_local_runtime() -> None:
    atmosphere = PROJECT_ROOT / "nicegui_app" / "assets" / "atmosphere"
    assert len(list(atmosphere.glob("*-light-v1.webp"))) == 11
    assert len(list(atmosphere.glob("*-dark-v1.webp"))) == 11


def test_every_enabled_atmosphere_uses_one_shared_slot_with_a_light_dark_pair() -> None:
    atmosphere = PROJECT_ROOT / "nicegui_app" / "assets" / "atmosphere"
    theme = combined_theme_source()

    assert set(ATMOSPHERE_THEME_PAIRS) == {"sidebar", "weekly-pulse", "devotional", "onboarding", "handover", "platform", "guide", "engineering", "architecture", "architecture-lifeline", "empty-ready"}
    for slot, (light_asset, dark_asset) in ATMOSPHERE_THEME_PAIRS.items():
        assert light_asset.endswith("-light-v1.webp")
        assert dark_asset.endswith("-dark-v1.webp")
        assert (atmosphere / light_asset).is_file()
        assert (atmosphere / dark_asset).is_file()
        assert _image_dimensions(atmosphere / light_asset) == _image_dimensions(atmosphere / dark_asset)
        assert (atmosphere / light_asset).stat().st_size < 250_000
        assert (atmosphere / dark_asset).stat().st_size < 250_000
        assert light_asset in theme and dark_asset in theme
        assert theme.count(f"--sy-image-{slot}") >= 3, f"{slot} must have light, dark, and component use"
    assert "weekly-pulse-paper.png" not in theme
    assert "devotional-morning-window.png" not in theme


def test_nicegui_favicon_is_a_real_local_file() -> None:
    assert FAVICON_CREST_PATH.is_file()
    assert FAVICON_CREST_PATH.stat().st_size > 0


def test_local_hong_kong_font_system_is_complete_and_offline() -> None:
    root = PROJECT_ROOT / "nicegui_app" / "assets" / "fonts"
    required = {
        "InterVariable.woff2",
        "NotoSansHK-Regular.woff2",
        "NotoSansHK-Medium.woff2",
        "NotoSansHK-SemiBold.woff2",
        "NotoSerifHK-Regular.woff2",
        "NotoSerifHK-SemiBold.woff2",
        "NotoSansHK-Regular.ttf",
        "NotoSansHK-Medium.ttf",
        "NotoSansHK-SemiBold.ttf",
        "OFL-Inter.txt",
        "OFL-Noto-CJK.txt",
    }
    assert required <= {path.name for path in root.iterdir() if path.is_file()}
    theme = combined_theme_source()
    assert 'font-family: "Inter", "Noto Sans HK"' in theme
    assert 'font-family: "Noto Serif HK"' in theme
    assert "font-display: swap" in theme
    assert "fonts.googleapis.com" not in theme


def test_school_crest_assets_cover_distinct_delivery_contexts() -> None:
    assert FAVICON_CREST_PATH.name == "sing-yin-crest-favicon.png"
    assert NAVIGATION_CREST_PATH.name == "sing-yin-crest-navigation.png"
    assert DISPLAY_PRINT_CREST_PATH.name == "sing-yin-crest-display-print.png"
    assert DISPLAY_WEB_CREST_PATH.name == "sing-yin-crest-display-web.png"
    assert _image_dimensions(FAVICON_CREST_PATH) == (512, 512)
    assert max(_image_dimensions(DISPLAY_WEB_CREST_PATH)) <= 640
    assert len({FAVICON_CREST_PATH.read_bytes(), NAVIGATION_CREST_PATH.read_bytes(), DISPLAY_PRINT_CREST_PATH.read_bytes(), DISPLAY_WEB_CREST_PATH.read_bytes()}) == 4
    assert not (PROJECT_ROOT / "logo.png").exists()


def test_pointer_hover_motion_is_scoped_and_reduced_motion_safe() -> None:
    theme = combined_theme_source()

    assert "@media (hover: hover) and (pointer: fine)" in theme
    assert ".sy-pointer-reactive" in theme
    assert ".sy-pointer-light" in theme
    assert "--sy-pointer-x" in theme and "--sy-pointer-y" in theme
    assert ".q-expansion-item .q-item { cursor: pointer; }" in theme
    assert "prefers-reduced-motion: reduce" in theme
    assert ".sy-pointer-reactive:hover { transform: none !important; }" in theme
    assert ".sy-pointer-light, .sy-feedback-pulse { display: none !important; }" in theme
    assert ".sy-table" not in theme.split("const pointerSurfaceSelector", 1)[1].split("].join", 1)[0]
