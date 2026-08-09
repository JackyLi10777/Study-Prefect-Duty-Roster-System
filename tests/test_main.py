from __future__ import annotations

import hashlib

from PIL import Image

from nicegui_app.main import open_browser_on_startup
from nicegui_app.config import DISPLAY_PRINT_CREST_PATH, DISPLAY_WEB_CREST_PATH, FAVICON_CREST_PATH, NAVIGATION_CREST_PATH, PROJECT_ROOT
from nicegui_app.ui.theme import ATMOSPHERE_THEME_PAIRS
from nicegui_app.ui.product_identity import PRODUCT_IDENTITY
from tests.ui_source import combined_theme_source


def _image_dimensions(path) -> tuple[int, int]:  # type: ignore[no-untyped-def]
    with Image.open(path) as image:
        return image.size


def _css_blocks(source: str, header: str) -> tuple[str, ...]:
    blocks: list[str] = []
    cursor = 0
    while (start := source.find(header, cursor)) >= 0:
        opening = source.find("{", start + len(header))
        if opening < 0:
            break
        depth = 0
        for index in range(opening, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(source[opening + 1:index])
                    cursor = index + 1
                    break
        else:
            break
    return tuple(blocks)


def test_browser_opens_by_default_for_local_new_users(monkeypatch) -> None:
    monkeypatch.delenv("SING_YIN_OPEN_BROWSER", raising=False)
    assert open_browser_on_startup() is True


def test_browser_auto_open_can_be_disabled_for_managed_or_headless_runs(monkeypatch) -> None:
    monkeypatch.setenv("SING_YIN_OPEN_BROWSER", "false")
    assert open_browser_on_startup() is False


def test_active_atmosphere_assets_exactly_match_the_runtime_registry() -> None:
    atmosphere = PROJECT_ROOT / "nicegui_app" / "assets" / "atmosphere"
    registered = {
        asset
        for pair in ATMOSPHERE_THEME_PAIRS.values()
        for asset in pair
    }
    available = {path.name for path in atmosphere.glob("*.webp")}

    assert available == registered
    assert len(registered) == 30
    assert "devotional-sacred-light-v1.webp" not in available
    assert "devotional-sacred-dark-v1.webp" not in available


def test_every_enabled_atmosphere_uses_one_shared_slot_with_a_light_dark_pair() -> None:
    atmosphere = PROJECT_ROOT / "nicegui_app" / "assets" / "atmosphere"
    theme = combined_theme_source()

    assert set(ATMOSPHERE_THEME_PAIRS) == {
        "sidebar",
        "weekly-pulse",
        "devotional",
        "weekly-operations",
        "people-fairness",
        "administration-recovery",
        "support-lifeline",
        "onboarding",
        "handover",
        "platform",
        "guide",
        "engineering",
        "architecture",
        "architecture-lifeline",
        "empty-ready",
    }
    for slot, (light_asset, dark_asset) in ATMOSPHERE_THEME_PAIRS.items():
        assert "-light-v" in light_asset and light_asset.endswith(".webp")
        assert "-dark-v" in dark_asset and dark_asset.endswith(".webp")
        assert (atmosphere / light_asset).is_file()
        assert (atmosphere / dark_asset).is_file()
        assert _image_dimensions(atmosphere / light_asset) == _image_dimensions(atmosphere / dark_asset)
        assert (atmosphere / light_asset).stat().st_size < 250_000
        assert (atmosphere / dark_asset).stat().st_size < 250_000
        assert light_asset in theme and dark_asset in theme
        assert theme.count(f"--sy-image-{slot}") >= 2, f"{slot} must have light and dark token values"
    assert "weekly-pulse-paper.png" not in theme
    assert "devotional-morning-window.png" not in theme


def test_new_route_family_assets_are_normalized_and_within_budget() -> None:
    atmosphere = PROJECT_ROOT / "nicegui_app" / "assets" / "atmosphere"
    new_slots = {
        "weekly-operations",
        "people-fairness",
        "administration-recovery",
        "support-lifeline",
        "devotional",
    }

    for slot in new_slots:
        for asset in ATMOSPHERE_THEME_PAIRS[slot]:
            path = atmosphere / asset
            assert _image_dimensions(path) == (1600, 900)
            assert path.stat().st_size <= 180_000


def test_generated_atmosphere_manifest_matches_assets_and_strips_private_metadata() -> None:
    atmosphere = PROJECT_ROOT / "nicegui_app" / "assets" / "atmosphere"
    manifest = (
        PROJECT_ROOT / "docs" / "design" / "ATMOSPHERE_ASSET_MANIFEST.md"
    ).read_text(encoding="utf-8")
    generated_slots = {
        "weekly-operations",
        "people-fairness",
        "administration-recovery",
        "support-lifeline",
        "devotional",
    }

    for slot in generated_slots:
        for asset in ATMOSPHERE_THEME_PAIRS[slot]:
            path = atmosphere / asset
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            assert f"`{asset}`" in manifest
            assert f"| {path.stat().st_size:,} |" in manifest
            assert f"`{digest}`" in manifest
            with Image.open(path) as image:
                assert not image.getexif()
                assert not ({"exif", "xmp"} & set(image.info))


def test_nicegui_favicon_is_a_real_local_file() -> None:
    assert FAVICON_CREST_PATH.is_file()
    assert FAVICON_CREST_PATH.stat().st_size > 0


def test_nicegui_runtime_uses_the_manifest_selected_product_favicon() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "main.py").read_text(encoding="utf-8")
    favicon = PRODUCT_IDENTITY.product_asset(
        PRODUCT_IDENTITY.delivery["faviconVariant"]
    )

    assert favicon.path.is_file()
    assert "PRODUCT_IDENTITY.delivery[\"faviconVariant\"]" in source
    assert "favicon=str(favicon_asset.path)" in source
    assert "SERVICE_WEAVE_FAVICON_PATH" not in source


def test_nicegui_runtime_uses_built_in_wind3_without_browser_tailwind() -> None:
    """The measured mobile startup path must not restore Tailwind's browser compiler."""

    source = (PROJECT_ROOT / "nicegui_app" / "main.py").read_text(encoding="utf-8")

    assert "tailwind=False" in source
    assert 'unocss="wind3"' in source
    assert 'unocss="mini"' not in source


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
    assert 'font-family: "Inter", "PingFang HK", "Microsoft JhengHei", "Noto Sans TC"' in theme
    assert 'font-family: "Noto Serif TC", "Songti TC", "PMingLiU"' in theme
    assert "font-display: swap" in theme
    assert "/assets/fonts/NotoSansHK" not in theme
    assert "/assets/fonts/NotoSerifHK" not in theme
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
    motion = (PROJECT_ROOT / "nicegui_app" / "assets" / "motion" / "sing-yin-motion.js").read_text(encoding="utf-8")

    assert "@media (hover: hover) and (pointer: fine)" in theme
    assert ".sy-pointer-reactive" in theme
    assert ".sy-pointer-light" in theme
    assert ".sy-pointer-ambient" in theme
    assert ".sy-pointer-light--ambient" in theme
    assert ".sy-pointer-reactive.sy-pointer-ambient:hover" in theme
    assert "transform: none" in theme.split(".sy-pointer-reactive.sy-pointer-ambient:hover", 1)[1][:120]
    assert "--sy-pointer-x" in theme and "--sy-pointer-y" in theme
    assert ".q-expansion-item .q-item { cursor: pointer; }" in theme
    assert "prefers-reduced-motion: reduce" in theme
    reduced_scope = "\n".join(_css_blocks(theme, "@media (prefers-reduced-motion: reduce)"))
    assert ".sy-pointer-reactive:hover" in reduced_scope
    assert ".sy-co-creation-social:hover" in reduced_scope
    assert "transform: none !important" in reduced_scope
    assert ".sy-pointer-light, .sy-feedback-pulse { display: none !important; }" in theme
    assert ".sy-table" not in motion.split("const pointerSurfaceSelector", 1)[1].split("].join", 1)[0]
    assert "pointerenter" in motion
    assert "const bounds = surface.getBoundingClientRect();" in motion
    assert "let bounds = null" not in motion
    assert "mutation.addedNodes" in motion
    assert "mutation.removedNodes" in motion
