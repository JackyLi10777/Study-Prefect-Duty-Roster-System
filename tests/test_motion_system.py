from __future__ import annotations

import hashlib
import re

from nicegui_app.config import PROJECT_ROOT


def test_gsap_runtime_is_versioned_local_and_integrity_pinned() -> None:
    vendor = PROJECT_ROOT / "nicegui_app" / "assets" / "vendor"
    gsap = vendor / "gsap-3.13.0.min.js"
    package = (vendor / "gsap-package.json").read_text(encoding="utf-8")
    attributes = (PROJECT_ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert gsap.is_file() and gsap.stat().st_size > 70_000
    assert hashlib.sha256(gsap.read_bytes()).hexdigest() == "96c01b81f44a3290e2b4532f55e2c9534b2adc43273a19f3756b2cb41f0fd0b6"
    assert '"version": "3.13.0"' in package
    assert "Standard 'no charge' license" in package
    assert "nicegui_app/assets/vendor/*.min.js -text" in attributes


def test_motion_runtime_is_purposeful_interruptible_and_reduced_motion_safe() -> None:
    motion = (PROJECT_ROOT / "nicegui_app" / "assets" / "motion" / "sing-yin-motion.js").read_text(encoding="utf-8")

    assert "window.gsap.fromTo" in motion
    assert "window.gsap.timeline" in motion
    assert "IntersectionObserver" in motion
    assert "MutationObserver" in motion
    assert "prefers-reduced-motion: reduce" in motion
    assert "window.gsap.matchMedia()" in motion
    assert "window.__disposeSingYinMotion = dispose" in motion
    assert "element.dataset.syMotionComplete = 'true'" in motion
    assert "onComplete: complete" in motion
    assert "mutationObserver?.disconnect()" in motion
    assert "intersectionObserver?.disconnect()" in motion
    assert "new AbortController()" in motion
    assert "clearProps: 'transform,opacity,visibility'" in motion
    assert "bootAttempts < 120" in motion
    assert "syMotion = 'unavailable'" in motion
    assert "repeat: -1" not in motion
    assert "ScrollTrigger" not in motion

    pointer_scope = motion.split("const pointerSurfaceSelector", 1)[1].split("].join", 1)[0]
    for static_surface in (".sy-flow-step", ".sy-architecture-layer", ".sy-storage-lifecycle"):
        assert static_surface not in pointer_scope
    ambient_scope = motion.split("const ambientPointerSurfaceSelector", 1)[1].split("].join", 1)[0]
    assert ".sy-team-role" in ambient_scope
    assert ".sy-devotional-companion" in ambient_scope
    assert 'data-sy-ambient-light="true"' in ambient_scope
    for static_surface in (".sy-flow-step", ".sy-architecture-layer", ".sy-storage-lifecycle"):
        assert static_surface not in ambient_scope
    assert "sy-pointer-ambient" in motion
    assert "enhancePointerSurface(surface, 'ambient')" in motion


def test_motion_assets_are_loaded_from_same_origin_only() -> None:
    motion_module = (PROJECT_ROOT / "nicegui_app" / "ui" / "motion.py").read_text(encoding="utf-8")
    main = (PROJECT_ROOT / "nicegui_app" / "main.py").read_text(encoding="utf-8")

    assert '/assets/vendor/gsap-3.13.0.min.js' in motion_module
    assert '/assets/motion/sing-yin-icon-story-state.js' in motion_module
    assert '/assets/motion/sing-yin-motion.js' in motion_module
    assert motion_module.index('sing-yin-icon-story-state.js') < motion_module.index('sing-yin-motion.js')
    assert "http://" not in motion_module and "https://" not in motion_module
    assert "prefers-reduced-motion: reduce" in motion_module
    assert "document.createElement('script')" in motion_module
    assert "script.async = false" in motion_module
    assert "if (!window.gsap && reducedMotion())" in (
        PROJECT_ROOT / "nicegui_app" / "assets" / "motion" / "sing-yin-motion.js"
    ).read_text(encoding="utf-8")
    assert "dataset.syMotion = 'reduced'" in (
        PROJECT_ROOT / "nicegui_app" / "assets" / "motion" / "sing-yin-motion.js"
    ).read_text(encoding="utf-8")
    assert 'url_path="/assets/motion"' in main
    assert 'url_path="/assets/vendor"' in main
    assert 'url_path="/assets/css"' in main


def test_component_transitions_use_the_shared_motion_tokens() -> None:
    css_root = PROJECT_ROOT / "nicegui_app" / "assets" / "css"
    theme = "\n".join(
        (css_root / filename).read_text(encoding="utf-8")
        for filename in ("sing-yin-tokens-v1.css", "sing-yin-theme-v1.css")
    )

    for token in ("--sy-motion-press: 90ms", "--sy-motion-state: 180ms", "--sy-motion-layer: 260ms"):
        assert token in theme
    for stray_duration in (".16s", ".18s", ".22s", ".24s", ".32s"):
        assert stray_duration not in theme
    assert "prefers-reduced-motion: reduce" in theme


def test_global_control_skin_hover_and_press_motion_stays_bounded() -> None:
    theme = (PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-theme-v1.css").read_text(
        encoding="utf-8"
    )

    fine_marker = "@media (hover: hover) and (pointer: fine)"
    fine_start = theme.index(fine_marker)
    fine_end = theme.find("@media", fine_start + len(fine_marker))
    fine_scope = theme[fine_start : fine_end if fine_end >= 0 else None]

    assert re.search(r"\.q-btn[^{}]*:hover\s*\{", fine_scope)
    assert ":not(.q-btn--round)" in fine_scope
    assert "--sy-control-shadow-hover" in fine_scope
    assert "--sy-motion-state" in fine_scope or "--sy-motion-layer" in fine_scope

    active_rules = " ".join(
        match.group("body")
        for match in re.finditer(
            r"(?P<selectors>[^{}]*\.q-btn[^{}]*:active[^{}]*)\{(?P<body>[^{}]*)\}",
            theme,
            re.DOTALL,
        )
    )
    assert active_rules
    assert "scale(" in active_rules
    assert "--sy-motion-press" in active_rules


def test_global_control_skin_reduced_motion_is_static_and_non_decorative() -> None:
    theme = (PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-theme-v1.css").read_text(
        encoding="utf-8"
    )
    motion = (PROJECT_ROOT / "nicegui_app" / "assets" / "motion" / "sing-yin-motion.js").read_text(
        encoding="utf-8"
    )

    reduced_marker = "@media (prefers-reduced-motion: reduce)"
    reduced_start = theme.index(reduced_marker)
    reduced_end = theme.find("@media", reduced_start + len(reduced_marker))
    reduced_scope = theme[reduced_start : reduced_end if reduced_end >= 0 else None]

    assert ".q-btn:hover" in reduced_scope
    assert ".sy-co-creation-social:hover" in reduced_scope
    assert "transform: none" in reduced_scope
    assert "animation-iteration-count: 1" in reduced_scope
    assert not re.search(r"animation(?:-iteration-count)?\s*:[^;}]*(?:infinite|forwards\s+infinite)", theme, re.I)
    assert "repeat: -1" not in motion

    # The shared skin is CSS-owned. Motion may listen on a bounded parent
    # surface, but it must never allocate a listener for every rendered button.
    for per_button_listener in (
        r"querySelectorAll\(\s*['\"][^'\"]*(?:\.q-btn|\bbutton\b)",
        r"(?:button|btn)\.addEventListener\(",
    ):
        assert re.search(per_button_listener, motion, re.I) is None


def test_semantic_icon_motion_is_clear_without_becoming_a_looping_effect() -> None:
    interaction = (
        PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-interaction-v1.css"
    ).read_text(encoding="utf-8")
    theme = (
        PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-theme-v1.css"
    ).read_text(encoding="utf-8")
    runtime = (
        PROJECT_ROOT / "nicegui_app" / "assets" / "motion" / "sing-yin-motion.js"
    ).read_text(encoding="utf-8")

    assert 'data-sy-icon-motion="menu"' in interaction
    menu_scope = interaction.split('data-sy-icon-motion="menu"', 1)[1].split("}", 1)[0]
    assert "rotate(" not in menu_scope
    assert 'data-sy-icon-motion="refresh"' in interaction
    refresh_scope = interaction.split('data-sy-icon-motion="refresh"', 1)[1].split("}", 1)[0]
    assert "scale(1.1)" in refresh_scope
    assert "rotate(" not in refresh_scope
    assert "translateX(5px) scale(1.015)" not in theme
    assert "translateY(-2px) scale(1.015)" not in theme
    assert "border-radius: 50%" in interaction
    assert "new AbortController()" in runtime
    assert "repeat: -1" not in runtime
    assert "prefers-reduced-motion: reduce" in theme


def test_coarse_pointer_gets_one_shot_icon_story_without_rotation_or_drift() -> None:
    """Touch users receive the same semantic story without hover or button travel."""

    runtime = (
        PROJECT_ROOT / "nicegui_app" / "assets" / "motion" / "sing-yin-motion.js"
    ).read_text(encoding="utf-8")

    assert "COARSE_POINTER_QUERY" in runtime
    assert "const onIconStoryPointerDown" in runtime
    assert "document.addEventListener('pointerdown', onIconStoryPointerDown" in runtime
    assert "event.pointerType" in runtime
    assert "window.matchMedia(COARSE_POINTER_QUERY).matches" in runtime
    assert "iconStoryTouchTimers" in runtime
    assert "iconStoryTouchTimers.forEach((timer) => window.clearTimeout(timer))" in runtime
    assert "iconStoryTouchTimers.clear()" in runtime

    touch_scope = runtime.split("const onIconStoryPointerDown", 1)[1].split(
        "const hydratePointers", 1
    )[0]
    assert "animateIconStory" in touch_scope
    assert "window.setTimeout" in touch_scope
    assert "const temporaryGlyph = icon.dataset.syIconStoryTo" in touch_scope
    assert "currentIcon.textContent?.trim() !== temporaryGlyph" in touch_scope
    assert "hydrateIconMotion(currentIcon)" in touch_scope
    assert "rotate" not in touch_scope
    assert "rotation" not in touch_scope
    assert "translate" not in touch_scope
