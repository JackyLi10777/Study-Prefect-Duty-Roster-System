from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_motion_tokens_define_productive_and_expressive_budgets() -> None:
    contract = json.loads((ROOT / "design_system" / "tokens.v1.json").read_text(encoding="utf-8"))
    motion = contract["layers"]["primitive"]["motion"]

    assert [motion[key] for key in ("productiveFast", "productiveStandard", "productiveSlow")] == [
        "90ms",
        "150ms",
        "180ms",
    ]
    assert [motion[key] for key in ("expressiveFast", "expressiveStandard", "expressiveSlow")] == [
        "260ms",
        "320ms",
        "420ms",
    ]


def test_pages_request_motion_semantically_and_runtime_owns_implementation() -> None:
    components = (ROOT / "nicegui_app" / "ui" / "components.py").read_text(encoding="utf-8")
    runtime = (ROOT / "nicegui_app" / "assets" / "motion" / "sing-yin-motion.js").read_text(
        encoding="utf-8"
    )

    assert "def motion_pattern(" in components
    assert "data-sy-motion-pattern" in components
    assert "motionPatternContracts" in runtime
    assert "hydrateMotionPatterns" in runtime
    assert "new IntersectionObserver" in runtime
    assert "ScrollTrigger" not in runtime


def test_no_second_frontend_or_motion_runtime_is_added() -> None:
    manifest = json.loads(
        (ROOT / "design_system" / "external_design_sources.v1.json").read_text(encoding="utf-8")
    )
    imported = [source["id"] for source in manifest["sources"] if source["runtimeImport"]]

    assert imported == ["gsap"]
    package_files = list(ROOT.rglob("package.json"))
    product_manifests = [path for path in package_files if "cloudflare" not in path.parts]
    assert product_manifests == []


def test_semantic_motion_reuses_the_existing_runtime_lifecycle() -> None:
    runtime = (ROOT / "nicegui_app" / "assets" / "motion" / "sing-yin-motion.js").read_text(
        encoding="utf-8"
    )

    # One existing observer serves TOC position and one existing reveal observer now
    # also owns the semantic patterns; the pilot must not allocate a third observer.
    assert runtime.count("new IntersectionObserver") == 2
    assert "motionPatternObserver" not in runtime
    assert runtime.count("new MutationObserver") == 1
    assert ".slice(0, 8)" in runtime
    assert "motionPatternTimelines.forEach" in runtime
    assert "motionPatternTimelines.clear()" in runtime
    assert "intersectionObserver?.unobserve(element)" in runtime
    unavailable_fallback = runtime.split("syMotion = 'unavailable'", 1)[1].split(
        "return;", 1
    )[0]
    assert "hydrateMotionPatterns()" in unavailable_fallback
    assert "installMutationHydrator()" in unavailable_fallback
    reduced_context = runtime.split("if (reduce) {", 1)[1].split(
        "document.querySelectorAll(interactiveIconHostSelector)", 1
    )[0]
    assert "motionPatternTimelines.forEach" in reduced_context
    assert "completeMotionPattern(element)" in reduced_context


def test_external_reference_lab_never_enters_the_served_resource_graph() -> None:
    markup = (ROOT / "nicegui_app" / "ui" / "theme_markup.py").read_text(encoding="utf-8")
    source_ledger = (ROOT / "design_system" / "external_design_sources.v1.json").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "motion-primitives",
        "react-bits",
        "RotatingOnScrollAnimations",
        "motionsites.ai",
    ):
        assert forbidden not in markup
    assert '"quarantineRoot": "D:/SingYinDesignReferenceLab"' in source_ledger
