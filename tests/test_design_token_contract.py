from __future__ import annotations

import json
import re

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.design_token_contract import (
    NICEGUI_CSS_PATH,
    SOURCE_PATH,
    WORKER_CONTRACT_PATH,
    WORKER_RUNTIME_PATH,
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
    assert contract["contractVersion"] == "1.1.0"
    assert contract["name"] == "Sing Yin Luminous Sacred Precision"
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

    css = NICEGUI_CSS_PATH.read_text(encoding="utf-8")
    light_block, dark_block = css.split(".body--dark", maxsplit=1)
    assert "--q-primary: #35647C;" in light_block
    assert "--q-primary: #47758B;" in dark_block
    assert "--q-dark-page: #0D1117;" in dark_block


def test_cloudflare_inline_tokens_match_generated_contract_without_runtime_imports() -> None:
    assert worker_runtime_drift() == []
    assert WORKER_RUNTIME_PATH.name == "worker.js"

    worker_runtime = WORKER_RUNTIME_PATH.read_text(encoding="utf-8")
    assert "design-tokens-v1.generated.json" not in worker_runtime
    assert "const VIEWER_CSS" in worker_runtime
    assert "export const TRIAL_CSS" not in worker_runtime


def test_every_service_weave_custom_property_reference_is_defined() -> None:
    css_root = PROJECT_ROOT / "nicegui_app" / "assets" / "css"
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(css_root.glob("*.css"))
    )
    definitions = set(re.findall(r"(?m)(--sy-[a-z0-9-]+)\s*:", source))
    references = set(re.findall(r"var\((--sy-[a-z0-9-]+)", source))

    assert references - definitions == set()
