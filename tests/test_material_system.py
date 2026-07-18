from __future__ import annotations

from pathlib import Path

from nicegui_app.config import PROJECT_ROOT


CSS_PATH = PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-material-v1.css"
MATERIAL_ROOT = PROJECT_ROOT / "nicegui_app" / "assets" / "materials"


def test_material_layer_is_paired_local_and_loaded_in_the_shared_shell() -> None:
    assert CSS_PATH.is_file()
    for stem in ("paper-fibre", "linen-weave"):
        light = MATERIAL_ROOT / f"{stem}-light-v1.svg"
        dark = MATERIAL_ROOT / f"{stem}-dark-v1.svg"
        assert light.is_file()
        assert dark.is_file()
        assert light.read_text(encoding="utf-8").startswith("<svg")
        assert dark.read_text(encoding="utf-8").startswith("<svg")

    head = (PROJECT_ROOT / "nicegui_app" / "ui" / "theme_markup.py").read_text(
        encoding="utf-8"
    )
    narrative = head.index("sing-yin-narrative-v1.css")
    material = head.index("sing-yin-material-v1.css")
    interaction = head.index("sing-yin-interaction-v1.css")
    assert material < narrative < interaction


def test_material_assets_are_exposed_by_the_local_static_server() -> None:
    main = (PROJECT_ROOT / "nicegui_app" / "main.py").read_text(encoding="utf-8")

    assert 'url_path="/assets/materials"' in main
    assert '"nicegui_app" / "assets" / "materials"' in main


def test_material_layer_is_bounded_away_from_sensitive_work_surfaces() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")

    for required in (
        "--sy-material-paper",
        "--sy-material-linen",
        "paper-fibre-light-v1.svg",
        "paper-fibre-dark-v1.svg",
        "linen-weave-light-v1.svg",
        "linen-weave-dark-v1.svg",
        ".sy-main",
        ".sy-sidebar::after",
        ".sy-workbench",
        ".sy-daily-start",
        ".sy-platform-hero::after",
        ".sy-architecture-hero::after",
    ):
        assert required in css

    for forbidden in (
        ".sy-table",
        ".q-table",
        ".q-field",
        ".q-form",
        ".sy-roster-mobile-card",
        ".sy-prefect-mobile-card",
        ".sy-operation-hint",
        ".sy-backup-integrity-warning",
        ".sy-export-option",
    ):
        assert forbidden not in css

    assert "> *:not(.sy-pointer-light)" in css
    assert "> * {" not in css
