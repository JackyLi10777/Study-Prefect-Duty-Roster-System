"""Produce a deterministic source inventory for the semantic icon system.

This deliberately does not call source locations "rendered instances": loops,
conditionals, access modes and DOM replacement change the runtime denominator.
Browser verification owns that second measurement.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui_app.ui.icon_motion_contract import ICON_MOTION_CONTRACTS


UI_ROOT = PROJECT_ROOT / "nicegui_app"
MOTION_PATH = UI_ROOT / "assets" / "motion" / "sing-yin-motion.js"


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Attribute):
        try:
            return f"{ast.unparse(node.func.value)}.{node.func.attr}"
        except (AttributeError, ValueError):
            return node.func.attr
    return node.func.id if isinstance(node.func, ast.Name) else ""


def _icon_argument(node: ast.Call, call_name: str) -> ast.expr | None:
    if call_name.endswith("ui.icon") and node.args:
        return node.args[0]
    return next((keyword.value for keyword in node.keywords if keyword.arg == "icon"), None)


def _python_inventory() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    literal: list[dict[str, object]] = []
    dynamic: list[dict[str, object]] = []
    for path in sorted(UI_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            call_name = _call_name(node)
            if not call_name.endswith(("ui.button", "ui.icon", "action")):
                continue
            icon = _icon_argument(node, call_name)
            if icon is None:
                continue
            record: dict[str, object] = {
                "file": path.relative_to(PROJECT_ROOT).as_posix(),
                "line": node.lineno,
                "call": call_name,
                "kind": "informational" if call_name.endswith("ui.icon") else "interactive_source",
            }
            if isinstance(icon, ast.Constant) and isinstance(icon.value, str):
                record["glyph"] = icon.value
                literal.append(record)
            else:
                record["expression"] = ast.unparse(icon)
                dynamic.append(record)
    return literal, dynamic


def _map_pairs(source: str, declaration: str) -> list[tuple[str, str]]:
    scope = source.split(f"const {declaration}", 1)[1].split(");", 1)[0]
    return re.findall(r"\['([^']+)',\s*'([^']+)'\]", scope)


def build_inventory(*, include_locations: bool = False) -> dict[str, object]:
    literal, dynamic = _python_inventory()
    motion = MOTION_PATH.read_text(encoding="utf-8")
    preview_pairs = _map_pairs(motion, "iconStoryGlyphs")
    persistent_pairs = _map_pairs(motion, "persistentIconPairs")
    glyph_counts = Counter(str(record["glyph"]) for record in literal)
    result: dict[str, object] = {
        "baseline": {
            "scope": "NiceGUI Python source plus shared motion registry",
            "warning": "Source call sites are not rendered DOM instances.",
        },
        "denominators": {
            "unique_literal_glyph_names": len(glyph_counts),
            "literal_interactive_source_call_sites": sum(
                record["kind"] == "interactive_source" for record in literal
            ),
            "literal_informational_source_call_sites": sum(
                record["kind"] == "informational" for record in literal
            ),
            "dynamic_icon_expressions": len(dynamic),
            "preview_story_sources": len(preview_pairs),
            "preview_story_destinations": len({destination for _, destination in preview_pairs}),
            "persistent_pair_directions": len(persistent_pairs),
            "mandatory_control_contracts": len(ICON_MOTION_CONTRACTS),
            "full_story_contracts": sum(
                contract.category in {"persistent", "preview", "lifecycle"}
                for contract in ICON_MOTION_CONTRACTS
            ),
            "role_only_contracts": sum(
                contract.category == "role" for contract in ICON_MOTION_CONTRACTS
            ),
            "intentionally_static_contracts": sum(
                contract.category == "static" for contract in ICON_MOTION_CONTRACTS
            ),
        },
        "glyph_counts": dict(sorted(glyph_counts.items())),
        "preview_story_pairs": preview_pairs,
        "persistent_pair_directions": persistent_pairs,
        "mandatory_controls": [
            {
                "key": contract.key,
                "routes": contract.routes,
                "i18n_keys": contract.i18n_keys,
                "callsite_hint": contract.callsite_hint,
                "access_modes": contract.access_modes,
                "mobile": contract.mobile,
                "source": contract.source_glyph,
                "destination": contract.destination_glyph,
                "role": contract.role,
                "category": contract.category,
                "states": contract.states,
                "reduced_motion": contract.reduced_motion,
                "static_rationale": contract.static_rationale,
            }
            for contract in ICON_MOTION_CONTRACTS
        ],
    }
    if include_locations:
        result["literal_locations"] = literal
        result["dynamic_locations"] = dynamic
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--locations", action="store_true", help="include source locations")
    args = parser.parse_args()
    print(json.dumps(build_inventory(include_locations=args.locations), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
