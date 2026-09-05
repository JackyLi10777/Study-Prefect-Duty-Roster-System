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
        "space_dashboard": {"navigation"},
        "calendar_month": {"navigation"},
        "groups": {"navigation"},
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


def test_story_icons_change_glyphs_instead_of_only_translating() -> None:
    motion = _read("nicegui_app/assets/motion/sing-yin-motion.js")

    expected_stories = {
        "space_dashboard": "dashboard_customize",
        "calendar_month": "event_available",
        "help_outline": "lightbulb",
        "menu_book": "auto_stories",
        "save": "task_alt",
        "translate": "language",
        "logout": "exit_to_app",
        "headphones": "graphic_eq",
    }
    for source, destination in expected_stories.items():
        assert f"['{source}', '{destination}']" in motion
    assert "const animateIconStory" in motion
    assert "icon.textContent = next" in motion
    story = motion.split("const animateIconStory", 1)[1].split("const iconStoryHost", 1)[0]
    assert "rotate:" not in story
    assert "back.out" not in story
    assert "power3.out" in motion
    assert "prefers-reduced-motion: reduce" in motion
    assert "new AbortController()" in motion


def test_story_icon_state_survives_rapid_reversal_and_pointer_focus_overlap() -> None:
    motion = _read("nicegui_app/assets/motion/sing-yin-motion.js")
    state_machine = _read("nicegui_app/assets/motion/sing-yin-icon-story-state.js")
    story = motion.split("const cancelIconTimeline", 1)[1].split("const hydratePointers", 1)[0]

    cancel = story.index("const previousTimeline = iconStoryTimelines.get(icon)")
    decide = story.index("const next = active ?")
    assert cancel < decide
    assert "previousTimeline.kill()" in story
    assert "window.gsap?.set(icon, { clearProps:" in story
    assert "window.SingYinIconStoryState?.create?.()" in motion
    assert "iconStoryState?.transition(host, input, true)" in story
    assert "iconStoryState?.transition(host, input, false)" in story
    assert "const previewActive = state => state.pointer || state.focus" in state_machine
    assert "return wasActive === isActive ? null : isActive" in state_machine
    assert "setPersistent(host, glyph)" in state_machine
    assert "persistentGlyph" in state_machine


def test_disabled_or_busy_story_icon_is_restored_without_animating() -> None:
    motion = _read("nicegui_app/assets/motion/sing-yin-motion.js")
    story = motion.split("const animateIconStory", 1)[1].split("const iconStoryHost", 1)[0]

    icon_lookup = story.index("const icon = host.querySelector")
    disabled_guard = motion.index("host.matches('.disabled")
    assert icon_lookup < disabled_guard
    assert "const original = icon.dataset.syIconStoryFrom" in story
    assert "icon.textContent = original" in story
    assert "icon.dataset.syIconStoryActive = 'false'" in story


def test_persistent_controls_do_not_use_temporary_hover_stories() -> None:
    motion = _read("nicegui_app/assets/motion/sing-yin-motion.js")
    shell = _read("nicegui_app/ui/shell.py")
    music = _read("nicegui_app/ui/music.py")

    preview_registry = motion.split("const iconStoryGlyphs", 1)[1].split(");", 1)[0]
    for persistent_source in ("volume_off", "dark_mode", "menu", "play_arrow", "pause"):
        assert f"['{persistent_source}'," not in preview_registry
    for pair in (
        "['volume_off', 'volume_up']",
        "['dark_mode', 'light_mode']",
        "['menu', 'close']",
        "['play_arrow', 'pause']",
    ):
        assert pair in motion
    assert "setPersistentGlyph" in motion
    assert "data-sy-icon-story-category=persistent" in shell
    assert "data-sy-sound-toggle" in shell
    assert "data-sy-icon-story-category=persistent" in music


def test_intentionally_static_category_blocks_registry_preview() -> None:
    motion = _read("nicegui_app/assets/motion/sing-yin-motion.js")
    static_scope = motion.split("if (category === 'static')", 1)[1].split(
        "const storyGlyph", 1
    )[0]

    assert "deleteDataset(icon, 'syIconStoryFrom')" in static_scope
    assert "deleteDataset(icon, 'syIconStoryTo')" in static_scope
    assert "iconStoryState?.clear(host)" in static_scope


def test_header_theme_uses_one_bounded_shared_morph_and_rotation() -> None:
    theme = _read("nicegui_app/assets/css/sing-yin-theme-v1.css")
    shell = _read("nicegui_app/ui/shell.py")

    assert "sy-header-icon-state" not in theme
    assert "syIconChanging" not in shell
    assert "window.__syIconMotion?.setPersistentGlyph" in shell

    worker = _read("cloudflare/roster_viewer/worker.js")
    theme_scope = worker.split(".theme-toggle-icon", 1)[1].split(".skip-link", 1)[0]
    keyframes = worker.split("@keyframes theme-icon-state", 1)[1].split(".skip-link", 1)[0]
    assert "animation: theme-icon-state 180ms" in theme_scope
    assert "rotate(-90deg)" in keyframes
    assert "scale(.72)" in keyframes
    assert "infinite" not in keyframes


def test_public_entry_icons_do_not_rotate_or_loop_decoratively() -> None:
    worker = _read("cloudflare/roster_viewer/worker.js")

    verse_refresh = worker.split(".verse-refresh svg", 1)[1].split(".service-note", 1)[0]
    assert "rotate(" not in verse_refresh

    access_icon = worker.split(".access-panel-icon svg", 1)[1].split(
        ".guest-enter:hover", 1
    )[0]
    assert "rotate(" not in access_icon

    secure_indicator = worker.split(".sy-secure-pulse", 1)[1].split(
        ".state-icon", 1
    )[0]
    assert "infinite" not in secure_indicator


def test_rotary_motion_is_allowlisted_exclusive_bounded_and_cleaned_up() -> None:
    motion = _read("nicegui_app/assets/motion/sing-yin-motion.js")
    interaction = _read("nicegui_app/assets/css/sing-yin-interaction-v1.css")

    for mode, preview, activation in (
        ("rotary-only", "70", "270"),
        ("persistent-rotary", "0", "90"),
        ("rotary-navigation", "60", "180"),
        ("rotary-history", "-55", "-180"),
        ("rotary-action", "0", "-180"),
    ):
        assert f"'{mode}': Object.freeze({{" in motion
        contract = motion.split(f"'{mode}': Object.freeze({{", 1)[1].split("})", 1)[0]
        assert f"preview: {preview}" in contract
        assert f"activation: {activation}" in contract

    assert "Object.freeze(['settings', 'light_mode', 'dark_mode', 'settings_backup_restore', 'history', 'undo'])" in motion
    assert "if (rotaryContract && motionMode !== 'persistent-rotary') category = 'role'" in motion
    assert "cancelIconTimeline(icon);" in motion
    assert "cancelRotaryTimeline(icon);" in motion
    assert "iconRotaryTimelines.clear()" in motion
    assert "clearProps: 'rotation,transform'" in motion
    for mode in (
        "rotary-only",
        "rotary-navigation",
        "rotary-history",
        "rotary-action",
        "persistent-rotary",
    ):
        assert f'[data-sy-icon-motion-mode="{mode}"]' in interaction


def test_theme_rotation_only_runs_for_a_real_user_state_change() -> None:
    motion = _read("nicegui_app/assets/motion/sing-yin-motion.js")
    shell = _read("nicegui_app/ui/shell.py")
    worker = _read("cloudflare/roster_viewer/worker.js")

    assert "host.dataset.syIconMotionMode === 'persistent-rotary'" in motion
    assert "morphGlyph(icon, next, { active: false, rotation })" in motion
    assert "data-sy-icon-motion-mode=persistent-rotary" in shell
    assert "sync({animate: false})" in shell
    assert "applyTheme(savedTheme(), { persist: false, animate: false })" in worker
    assert "applyTheme('system', { persist: false, animate: false })" in worker
    assert "applyTheme(next, { persist: true, animate: true })" in worker


def test_tactile_preference_switches_have_a_pressed_shape_without_layout_shift() -> None:
    music = _read("nicegui_app/ui/music.py")
    theme = _read("nicegui_app/assets/css/sing-yin-theme-v1.css")

    assert music.count("sy-tactile-toggle") >= 4
    tactile = theme.split(".sy-tactile-toggle", 1)[1]
    assert "inset" in tactile
    assert "scale(.92)" in tactile
    assert "width:" not in tactile.split(".sy-tactile-toggle:active", 1)[1].split("}", 1)[0]
    assert "height:" not in tactile.split(".sy-tactile-toggle:active", 1)[1].split("}", 1)[0]
    assert "@media (forced-colors: active)" in theme


def test_theme_runtime_keeps_the_prepaint_asset_selector_in_sync() -> None:
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")

    assert shell.count("document.documentElement.dataset.syResolvedTheme") >= 2
    assert "document.documentElement.dataset.syResolvedTheme = theme" in shell
    assert "document.documentElement.dataset.syResolvedTheme = current" in shell


def test_persistent_preference_updates_cannot_cross_contaminate_controls() -> None:
    shell = _read("nicegui_app/ui/shell.py")
    sound_scope = shell.split("async def _sync_preference_controls", 1)[1].split(
        "async def _toggle_sound_feedback_with_preview", 1
    )[0]
    theme_scope = shell.split("async def _sync_theme_controls", 1)[1].split(
        "def _remember_system_theme_resolution", 1
    )[0]

    assert "[data-sy-sound-toggle]" in sound_scope
    assert "[data-sy-theme-toggle]" not in sound_scope
    assert "[data-sy-theme-toggle]" in theme_scope
    assert "[data-sy-sound-toggle]" not in theme_scope
    assert "await ui.run_javascript" in sound_scope
    assert "await ui.run_javascript" in theme_scope


def test_isolated_browser_verifier_exercises_story_reversal_and_input_overlap() -> None:
    verifier = _read("scripts/verify_nicegui_ui.py")

    assert 'data-sy-icon-story-to' in verifier
    assert "story_host.hover()" in verifier
    assert "story_host.focus()" in verifier
    assert 'element => element.blur()' in verifier
    assert "story_icon.inner_text().strip() == story_to" in verifier
    assert "story_icon.inner_text().strip() == story_from" in verifier


def test_language_verifier_reads_the_visible_label_not_the_material_icon_ligature() -> None:
    verifier = _read("scripts/verify_nicegui_ui.py")

    assert 'get_by_text("中文", exact=True)' in verifier
    assert "chinese_label.count() == 1 and chinese_label.is_visible()" in verifier
    assert 'inner_text().strip() == "中文"' not in verifier
    assert 'get_attribute("aria-label") == "Switch to 中文"' in verifier


def test_mobile_verifier_checks_the_persistent_drawer_story_contract() -> None:
    verifier = _read("scripts/verify_nicegui_mobile.py")
    story = verifier.split("def _assert_coarse_pointer_icon_story", 1)[1].split(
        "def _assert_responsive_table_cards", 1
    )[0]

    assert 'locator(".q-icon").first' in story
    assert 'data-sy-icon-story-category") != "persistent"' in story
    assert "more.click()" in story
    assert "page.keyboard.press(\"Escape\")" in story
    assert "arrow_back" not in story


def test_icon_hydration_uses_observation_and_delegation_not_per_button_listeners() -> None:
    motion = _read("nicegui_app/assets/motion/sing-yin-motion.js")

    assert "MutationObserver" in motion
    assert "mutationObserver?.disconnect()" in motion
    assert "hydrateIconMotion()" in motion or "hydrateIconMotion(document)" in motion

    hydration = motion.split("const hydrateIconMotion", 1)[1].split("const guardStateFor", 1)[0]
    assert "setDataset(icon, 'syIconStoryCategory', category)" in hydration
    assert "setDataset(icon, 'syIconStoryTo', storyGlyph)" in hydration
    assert "icon.dataset.syIconStoryCategory = category" not in hydration
    assert "icon.dataset.syIconStoryTo = storyGlyph" not in hydration
    assert "const persistentGlyph = iconStoryState?.current(host).persistentGlyph" in hydration
    assert "persistentGlyph !== name && !iconStoryTimelines.has(icon)" in hydration

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
    for state in ("navigation", "working", "success", "attention", "error"):
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
    for state in ("navigation", "working", "success", "attention", "error"):
        assert f'[{state_attribute}="{state}"]' in css

    assert "var(--sy-motion-press)" in css
    assert "var(--sy-motion-state)" in css
    assert not re.search(r"animation-iteration-count\s*:\s*infinite", css, re.I)

    reduced = css.split("@media (prefers-reduced-motion: reduce)", 1)[1]
    assert "[data-sy-icon-motion]" in reduced
    assert "animation: none" in reduced
    assert "transform: none" in reduced


def test_button_hosts_stay_stable_while_icons_tell_the_story() -> None:
    theme = _read("nicegui_app/assets/css/sing-yin-theme-v1.css")
    interaction = _read("nicegui_app/assets/css/sing-yin-interaction-v1.css")
    hover_scope = theme.split("@media (hover: hover) and (pointer: fine)", 1)[1].split(
        ".sy-flow-symbol",
        1,
    )[0]

    assert "translateX(5px)" not in hover_scope
    assert "scale(1.015)" not in hover_scope
    for selector in (
        ".sy-sidebar .q-btn:not(.disabled):hover",
        ".q-expansion-item > .q-expansion-item__container > .q-item:hover",
    ):
        declaration = hover_scope.split(selector, 1)[1].split("}", 1)[0]
        assert "transform:" not in declaration

    assert '.q-icon[data-sy-icon-motion="refresh"]' in interaction
    refresh = interaction.split(
        '.q-icon[data-sy-icon-motion="refresh"]',
        1,
    )[1].split("}", 1)[0]
    assert "scale(1.1)" in refresh
    assert "rotate(" not in refresh
    for non_rotating_role in ("create", "edit", "toggle", "menu", "search", "danger", "attention", "navigation"):
        declaration = interaction.split(
            f'.q-icon[data-sy-icon-motion="{non_rotating_role}"]',
            1,
        )[1].split("}", 1)[0]
        assert "rotate(" not in declaration


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


def test_platform_operating_map_has_bounded_motion_and_mobile_flow() -> None:
    css = _read("nicegui_app/assets/css/sing-yin-theme-v1.css")
    interaction = _read("nicegui_app/assets/css/sing-yin-interaction-v1.css")
    motion = _read("nicegui_app/assets/motion/sing-yin-motion.js")
    page = _read("nicegui_app/ui/page_routes/showcase.py")

    assert 'test_id="platform-operating-map"' in page
    # The route's actual first-use motion request and six list items are
    # covered by test_platform_operating_map_retains_its_semantic_motion_request.
    assert '"platform-operating-map-section"' in page
    assert "'.sy-platform-operating-map'" in motion
    assert ".sy-platform-map-node:hover" in css
    assert 'content: "arrow_downward"' in css
    assert ".sy-platform-map-node-icon" in interaction
    reduced = css.split("@media (prefers-reduced-motion: reduce)")[-1]
    assert ".sy-platform-map-node:hover" in reduced
    assert "transform: none" in reduced


def test_browser_verifier_waits_for_motion_hydration_before_sampling_static_cards() -> None:
    verifier = _read("scripts/verify_nicegui_ui.py")

    assert "model?.dataset.syMotionComplete === 'true'" in verifier
    assert "getComputedStyle(role).transform === 'none'" in verifier


def test_browser_verifier_keeps_navigation_button_stable_while_icon_tells_story() -> None:
    verifier = _read("scripts/verify_nicegui_ui.py")

    assert 'page.locator(".sy-desktop-drawer-trigger")' in verifier
    assert 'navigation_trigger = page.get_by_test_id("desktop-drawer-trigger")' in verifier
    assert '"關閉主要導覽" if navigation_expanded == "true" else "開啟主要導覽"' in verifier
    assert 'data-sy-icon-story-category="persistent"' in verifier
    assert ") == static_navigation_toggle_transform" in verifier
    assert "textContent.trim() === 'menu'" in verifier
    assert "textContent.trim() === 'close'" in verifier
    assert 'navigation_toggle_icon.text_content().strip() == "menu"' in verifier
    assert 'navigation_toggle_icon.text_content().strip() == "close"' in verifier


def test_browser_verifier_audits_every_rendered_interactive_icon() -> None:
    verifier = _read("scripts/verify_nicegui_ui.py")

    assert "def assert_rendered_icon_semantics" in verifier
    assert "window.__syIconMotion.classify(host)" in verifier
    assert 'assert audit["missing"] == []' in verifier
    assert 'dashboard_icon_categories["persistent"] >= 3' in verifier
