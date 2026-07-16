from __future__ import annotations

import json

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.design_token_contract import (
    NICEGUI_CSS_PATH,
    SOURCE_PATH,
    WORKER_CONTRACT_PATH,
    generated_file_drift,
    load_design_token_contract,
    quasar_palette,
    resolved_token_map,
    theme_integration_drift,
    worker_runtime_drift,
)


def test_versioned_contract_uses_primitive_semantic_component_order() -> None:
    contract = load_design_token_contract()

    assert SOURCE_PATH.name == "tokens.v1.json"
    assert contract["contractVersion"] == "1.0.0"
    assert contract["layerOrder"] == ["primitive", "semantic", "component"]
    assert contract["layers"]["primitive"]["color"]
    for platform in ("nicegui", "worker"):
        assert contract["platforms"][platform]["layers"]["semantic"]
        assert contract["platforms"][platform]["layers"]["component"]


def test_generated_nicegui_and_worker_artifacts_are_current() -> None:
    assert generated_file_drift() == []
    assert NICEGUI_CSS_PATH.is_file()
    assert WORKER_CONTRACT_PATH.is_file()

    worker_contract = json.loads(WORKER_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert worker_contract["generatedFrom"] == "design_system/tokens.v1.json"
    assert worker_contract["themes"]["light"] == resolved_token_map(
        load_design_token_contract(), "worker", "light"
    )
    assert worker_contract["themes"]["dark"] == resolved_token_map(
        load_design_token_contract(), "worker", "dark"
    )


def test_nicegui_loads_generated_tokens_before_compatibility_css() -> None:
    assert theme_integration_drift() == []

    markup = (
        PROJECT_ROOT / "nicegui_app" / "ui" / "theme_markup.py"
    ).read_text(encoding="utf-8")
    assert markup.index("sing-yin-tokens-v1.css") < markup.index(
        "sing-yin-theme-v1.css"
    )
    assert "@layer sy.tokens" in NICEGUI_CSS_PATH.read_text(encoding="utf-8")


def test_quasar_fill_bridge_resolves_from_the_same_contract() -> None:
    assert quasar_palette(mode="light") == {
        "primary": "#35647C",
        "secondary": "#0F766E",
        "accent": "#0F766E",
        "positive": "#0F766E",
        "negative": "#963C35",
        "info": "#35647C",
        "warning": "#F0C96A",
    }
    assert quasar_palette(mode="dark") == {
        "primary": "#47758B",
        "secondary": "#0F766E",
        "accent": "#0F766E",
        "dark": "#1C1C1E",
        "dark_page": "#0D1117",
        "positive": "#0F766E",
        "negative": "#9A4A43",
        "info": "#35647C",
        "warning": "#F0C96A",
    }


def test_cloudflare_inline_tokens_match_generated_contract_without_runtime_imports() -> None:
    assert worker_runtime_drift() == []

    worker_runtime = (
        PROJECT_ROOT / "cloudflare" / "roster_viewer" / "guest_trial.js"
    ).read_text(encoding="utf-8")
    assert "design-tokens-v1.generated.json" not in worker_runtime
