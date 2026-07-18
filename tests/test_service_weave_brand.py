from __future__ import annotations

import subprocess

from PIL import Image

from nicegui_app.config import PROJECT_ROOT, SERVICE_WEAVE_ASSET_DIR


PNG_SPECS = {
    "service-weave-mark-light-v1.png": ((1024, 1024), "RGBA"),
    "service-weave-mark-dark-v1.png": ((1024, 1024), "RGBA"),
    "service-weave-mark-ink-v1.png": ((1024, 1024), "RGBA"),
    "service-weave-mark-white-v1.png": ((1024, 1024), "RGBA"),
    "service-weave-app-light-v1.png": ((1024, 1024), "RGBA"),
    "service-weave-app-dark-v1.png": ((1024, 1024), "RGBA"),
    "service-weave-favicon-512-v1.png": ((512, 512), "RGBA"),
    "service-weave-navigation-light-256-v1.png": ((256, 256), "RGBA"),
    "service-weave-navigation-dark-256-v1.png": ((256, 256), "RGBA"),
    "service-weave-preview-v1.png": ((1800, 1360), "RGB"),
}


def _alpha_bytes(filename: str) -> bytes:
    with Image.open(SERVICE_WEAVE_ASSET_DIR / filename) as image:
        return image.getchannel("A").tobytes()


def test_service_weave_asset_pack_has_the_reviewed_delivery_contract() -> None:
    expected = {*PNG_SPECS, "service-weave-windows-v1.ico"}
    assert {path.name for path in SERVICE_WEAVE_ASSET_DIR.iterdir() if path.is_file()} == expected
    for filename, (size, mode) in PNG_SPECS.items():
        with Image.open(SERVICE_WEAVE_ASSET_DIR / filename) as image:
            assert image.size == size
            assert image.mode == mode


def test_service_weave_theme_and_monochrome_variants_keep_one_geometry() -> None:
    mark_alpha = _alpha_bytes("service-weave-mark-light-v1.png")
    for filename in (
        "service-weave-mark-dark-v1.png",
        "service-weave-mark-ink-v1.png",
        "service-weave-mark-white-v1.png",
    ):
        assert _alpha_bytes(filename) == mark_alpha
    assert _alpha_bytes("service-weave-app-light-v1.png") == _alpha_bytes(
        "service-weave-app-dark-v1.png"
    )
    assert _alpha_bytes("service-weave-navigation-light-256-v1.png") == _alpha_bytes(
        "service-weave-navigation-dark-256-v1.png"
    )


def test_service_weave_assets_keep_transparent_edges_and_no_chroma_key_residue() -> None:
    for filename, (_size, mode) in PNG_SPECS.items():
        if mode != "RGBA":
            continue
        with Image.open(SERVICE_WEAVE_ASSET_DIR / filename) as image:
            pixels = image.load()
            width, height = image.size
            corners = (
                (0, 0),
                (width - 1, 0),
                (0, height - 1),
                (width - 1, height - 1),
            )
            assert all(pixels[x, y][3] <= 1 for x, y in corners)
            assert not any(
                red > 245 and blue > 245 and green < 20 and alpha > 8
                for red, green, blue, alpha in image.get_flattened_data()
            )


def test_service_weave_monochrome_files_are_literal_production_colours() -> None:
    expected = {
        "service-weave-mark-ink-v1.png": (23, 38, 61),
        "service-weave-mark-white-v1.png": (255, 255, 255),
    }
    for filename, colour in expected.items():
        with Image.open(SERVICE_WEAVE_ASSET_DIR / filename) as image:
            visible = {
                pixel[:3] for pixel in image.get_flattened_data() if pixel[3]
            }
            assert visible == {colour}


def test_service_weave_windows_icon_contains_small_and_large_frames() -> None:
    with Image.open(SERVICE_WEAVE_ASSET_DIR / "service-weave-windows-v1.ico") as icon:
        assert icon.format == "ICO"
        assert icon.ico.sizes() == {
            (16, 16),
            (24, 24),
            (32, 32),
            (48, 48),
            (64, 64),
            (128, 128),
            (256, 256),
        }


def test_service_weave_white_mark_and_worker_delivery_are_reproducible() -> None:
    result = subprocess.run(
        [
            "python",
            "-X",
            "utf8",
            "scripts/generate_service_weave_delivery.py",
            "--check",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
