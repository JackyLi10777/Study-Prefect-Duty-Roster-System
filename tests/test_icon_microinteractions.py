from __future__ import annotations

import re

from nicegui_app.config import PROJECT_ROOT


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_interaction_layer_loads_after_narrative_and_before_mobile_overrides() -> None:
    interaction_path = (
        PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-interaction-v1.css"
    )
    assert interaction_path.is_file(), "Semantic icon motion belongs in its own maintainable CSS layer"

    head = _read("nicegui_app/ui/theme_markup.py")
    narrative = head.index("/assets/css/sing-yin-narrative-v1.css")
    interaction = head.index("/assets/css/sing-yin-interaction-v1.css")
    mobile = head.index("/assets/css/sing-yin-mobile-v1.css")

    assert narrative < interaction < mobile


def test_material_icon_names_map_to_stable_semantic_motion_roles() -> None:
    motion = _read("nicegui_app/assets/motion/sing-yin-motion.js")

    assert re.search(r"(?:const|let)\s+iconMotionRoles\s*=", motion, re.I)
    assert "data-sy-icon-motion" in motion or "dataset.syIconMotion" in motion
    assert re.search(r"(?:new\s+Map|Object\.freeze)\s*\(", motion)

    expected_roles = {
        "arrow_forward": {"forward"},
        "arrow_back": {"back"},
        "refresh": {"refresh"},
        "save": {"save", "confirm"},
        "download": {"download"},
        "upload": {"upload"},
        "swap_horiz": {"swap", "exchange"},
        "person_add": {"create"},
        "edit": {"edit"},
        "manage_accounts": {"settings", "toggle"},
        "delete_outline": {"danger"},
    }
    for icon_name, roles in expected_roles.items():
        role_alternation = "|".join(re.escape(role) for role in sorted(roles))
        direct_mapping = (
            rf"['\"]{re.escape(icon_name)}['\"]\s*(?:,|:)\s*"
            rf"['\"](?:{role_alternation})['\"]"
        )
        grouped_mapping = (
            rf"\[[^\]]*['\"]{re.escape(icon_name)}['\"][^\]]*\]\s*"
            rf"\.map\(\s*\(name\)\s*=>\s*\[name,\s*['\"](?:{role_alternation})['\"]\]\s*\)"
        )
        assert re.search(direct_mapping, motion) or re.search(
            grouped_mapping,
            motion,
            re.DOTALL,
        ), f"{icon_name} must resolve to one stable semantic role"

    assert re.search(r"(?:const|function)\s+hydrateIconMotion\b", motion)
    added_node_scope = motion.split("mutation.addedNodes.forEach", 1)[1]
    assert "hydrateIconMotion(node)" in added_node_scope


def test_icon_hydration_uses_observation_and_delegation_not_per_button_listeners() -> None:
    motion = _read("nicegui_app/assets/motion/sing-yin-motion.js")

    assert "MutationObserver" in motion
    assert "mutationObserver?.disconnect()" in motion
    assert "hydrateIconMotion()" in motion or "hydrateIconMotion(document)" in motion

    for per_button_listener in (
        r"querySelectorAll\(\s*['\"][^'\"]*(?:\.q-btn|\bbutton\b)",
        r"(?:button|btn)\.addEventListener\(",
        r"queryWithin\([^,]+,\s*['\"][^'\"]*(?:\.q-btn|\bbutton\b)",
    ):
        assert re.search(per_button_listener, motion, re.I) is None


def test_feedback_states_are_targeted_bounded_and_cleaned_up() -> None:
    motion = _read("nicegui_app/assets/motion/sing-yin-motion.js")

    timer_match = re.search(
        r"(?:const|let)\s+((?:feedback|interaction)(?:State)?Timers)\s*=\s*new Map\(\)",
        motion,
        re.I,
    )
    assert timer_match
    timer_name = timer_match.group(1)
    state_attribute = (
        "data-sy-feedback-state"
        if "data-sy-feedback-state" in motion
        else "data-sy-interaction-state"
    )
    assert state_attribute in motion
    assert "document.activeElement" in motion
    assert ".closest(interactiveIconHostSelector)" in motion
    assert "rememberActionHost" in motion
    assert "operationFeedbackHost" in motion
    assert "ACTION_MEMORY_MS" in motion
    assert "new AbortController()" in motion
    assert "interactionAbortController?.abort()" in motion
    assert "document.addEventListener('pointerdown', rememberActionHost" in motion
    assert "document.addEventListener('keydown', rememberActionHost" in motion
    for state in ("working", "success", "attention", "error"):
        assert re.search(rf"['\"]{state}['\"]", motion)

    assert (
        re.search(rf"setAttribute\(\s*['\"]{state_attribute}['\"]", motion)
        or "dataset.syFeedbackState =" in motion
        or "dataset.syInteractionState =" in motion
    )
    assert (
        re.search(rf"removeAttribute\(\s*['\"]{state_attribute}['\"]", motion)
        or "delete active.dataset.syFeedbackState" in motion
        or "delete target.dataset.syFeedbackState" in motion
        or "delete active.dataset.syInteractionState" in motion
        or "delete target.dataset.syInteractionState" in motion
    )
    assert "window.setTimeout" in motion

    dispose_scope = motion.split("const dispose =", 1)[1].split("window.__disposeSingYinMotion", 1)[0]
    assert "clearTimeout" in dispose_scope
    assert f"{timer_name}.clear()" in dispose_scope
    assert state_attribute in dispose_scope


def test_feedback_keyframes_are_not_suppressed_by_hover_or_focus_importance() -> None:
    css = _read("nicegui_app/assets/css/sing-yin-interaction-v1.css")

    assert "transform: var(--sy-icon-intent-transform) !important" not in css
    assert "transform: translate3d(0, 1px, 0) scale(.9) !important" not in css


def test_interaction_css_covers_control_and_feedback_states() -> None:
    css = _read("nicegui_app/assets/css/sing-yin-interaction-v1.css")

    assert "[data-sy-icon-motion]" in css
    assert "@media (hover: hover) and (pointer: fine)" in css
    for state_pattern in (
        r"\.q-btn[^,{]*:hover[^,{]*\[data-sy-icon-motion",
        r"\.q-btn[^,{]*:focus-visible[^,{]*\[data-sy-icon-motion",
        r"\.q-btn[^,{]*:active[^,{]*\[data-sy-icon-motion",
        r"\.q-btn(?:\.q-btn--loading|--loading)[^,{]*\[data-sy-icon-motion",
    ):
        assert re.search(state_pattern, css), f"Missing interaction selector: {state_pattern}"

    for disabled_or_busy_selector in (
        ".q-btn.disabled",
        '.q-btn[aria-disabled="true"]',
        ".q-btn.q-btn--loading",
        '.q-btn[aria-busy="true"]',
    ):
        assert disabled_or_busy_selector in css
    disabled_scope = css.split(".q-btn.disabled", 1)[1].split("@media (hover: hover)", 1)[0]
    assert ".q-icon[data-sy-icon-motion]" in disabled_scope
    assert "animation: none" in disabled_scope
    assert "transform: none" in disabled_scope

    state_attribute = (
        "data-sy-feedback-state"
        if "data-sy-feedback-state" in css
        else "data-sy-interaction-state"
    )
    for state in ("working", "success", "attention", "error"):
        assert f'[{state_attribute}="{state}"]' in css

    assert "var(--sy-motion-press)" in css
    assert "var(--sy-motion-state)" in css
    assert not re.search(r"animation-iteration-count\s*:\s*infinite", css, re.I)

    reduced = css.split("@media (prefers-reduced-motion: reduce)", 1)[1]
    assert "[data-sy-icon-motion]" in reduced
    assert "animation: none" in reduced
    assert "transform: none" in reduced


def test_static_platform_and_team_surfaces_only_animate_their_internal_icons() -> None:
    css = _read("nicegui_app/assets/css/sing-yin-interaction-v1.css")

    static_icon_pairs = {
        ".sy-team-role": ".sy-team-role-icon",
        ".sy-capability-card": ".sy-capability-icon",
        ".sy-platform-metric": ".sy-platform-metric-icon",
    }
    for surface, icon in static_icon_pairs.items():
        assert re.search(
            rf"{re.escape(surface)}:hover\s+{re.escape(icon)}",
            css,
        ), f"{surface} should respond through {icon}, not pretend the whole card is clickable"
        assert re.search(
            rf"{re.escape(surface)}:hover\s*(?:,|\{{)",
            css,
        ) is None, f"{surface} is informational and must not lift or move as a clickable surface"


def test_browser_verifier_waits_for_motion_hydration_before_sampling_static_cards() -> None:
    verifier = _read("scripts/verify_nicegui_ui.py")

    assert "model?.dataset.syMotionComplete === 'true'" in verifier
    assert "getComputedStyle(role).transform === 'none'" in verifier
