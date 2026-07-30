from __future__ import annotations

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.icon_motion_contract import (
    ICON_MOTION_CONTRACTS,
    validate_icon_motion_contracts,
)


MANDATORY_CONTROLS = {
    "settings",
    "sound",
    "theme",
    "usage_instructions",
    "generate_draft",
    "review_publish",
    "published_leave",
    "history_withdraw",
    "data_import",
    "fairness",
    "add_prefect",
    "edit_prefect",
    "archive_prefect",
    "new_year_directory",
    "backup_restore",
    "acceptance_guide",
    "verified_snapshot",
    "change_verse",
    "temporary_report",
}


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_release_critical_controls_have_traceable_motion_contracts() -> None:
    assert validate_icon_motion_contracts() == []
    by_key = {contract.key: contract for contract in ICON_MOTION_CONTRACTS}
    assert set(by_key) == MANDATORY_CONTROLS
    assert all(contract.mobile for contract in by_key.values())
    assert all(contract.routes and contract.i18n_keys for contract in by_key.values())
    assert all(contract.callsite_hint for contract in by_key.values())
    assert all(contract.reduced_motion for contract in by_key.values())


def test_shared_runtime_owns_operation_lifecycle_without_fake_page_timelines() -> None:
    motion = _read("nicegui_app/assets/motion/sing-yin-motion.js")
    combined_pages = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes").glob("*.py")
    )

    assert "const operationLifecycleGlyphs = new Map" in motion
    for source in {
        contract.source_glyph
        for contract in ICON_MOTION_CONTRACTS
        if contract.category == "lifecycle"
    }:
        assert f"['{source}'," in motion
    assert "applyLifecycleGlyph(kind, target)" in motion
    assert "restoreLifecycleGlyph(target)" in motion
    assert "kind === 'working' ? 12_000 : 820" in motion
    assert "gsap.timeline" not in combined_pages


def test_settings_gear_is_the_only_bounded_rotation_exception() -> None:
    motion = _read("nicegui_app/assets/motion/sing-yin-motion.js")
    css = _read("nicegui_app/assets/css/sing-yin-interaction-v1.css")

    assert "['settings', 'gear']" in motion
    assert "['settings', 'settings_suggest']" not in motion
    assert "const animateGearActivation" in motion
    gear_scope = motion.split("const animateGearActivation", 1)[1].split(
        "const setPersistentGlyph", 1
    )[0]
    assert "rotation: 270" in gear_scope
    assert "killTweensOf(icon)" in gear_scope
    assert "clearProps: 'rotation,transform'" in gear_scope
    assert '.q-icon[data-sy-icon-motion="gear"]' in css
    assert "rotate(70deg)" in css
    assert "animation-iteration-count: infinite" not in css


def test_action_feedback_changes_tone_without_moving_button_footprint() -> None:
    css = _read("nicegui_app/assets/css/sing-yin-interaction-v1.css")
    lifecycle_scope = css.split("The button footprint never changes", 1)[1].split(
        "Editorial showcase cards", 1
    )[0]

    for state in ("working", "success", "attention", "error"):
        assert f'data-sy-feedback-state="{state}"' in lifecycle_scope
    assert "box-shadow:" in lifecycle_scope
    assert "translate" not in lifecycle_scope
    assert "rotate" not in lifecycle_scope
    assert "animation" not in lifecycle_scope


def test_reduced_motion_and_forced_colours_keep_static_non_colour_feedback() -> None:
    css = _read("nicegui_app/assets/css/sing-yin-interaction-v1.css")
    reduced = css.split("@media (prefers-reduced-motion: reduce)", 1)[1]
    forced = css.split("@media (forced-colors: active)", 1)[1]

    assert "animation: none !important" in reduced
    assert "transform: none !important" in reduced
    assert "transition: none !important" in reduced
    assert "outline: 2px solid CanvasText" in forced


def test_inventory_reports_contract_denominators_without_callsite_conflation() -> None:
    from scripts.audit_icon_semantics import build_inventory

    inventory = build_inventory()
    denominators = inventory["denominators"]
    assert denominators["mandatory_control_contracts"] == len(MANDATORY_CONTROLS)
    assert denominators["full_story_contracts"] > denominators["role_only_contracts"]
    assert len(inventory["mandatory_controls"]) == len(MANDATORY_CONTROLS)
    assert inventory["baseline"]["warning"] == "Source call sites are not rendered DOM instances."
