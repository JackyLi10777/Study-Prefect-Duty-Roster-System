from __future__ import annotations

import hashlib

from nicegui_app.config import PROJECT_ROOT


def test_gsap_runtime_is_versioned_local_and_integrity_pinned() -> None:
    vendor = PROJECT_ROOT / "nicegui_app" / "assets" / "vendor"
    gsap = vendor / "gsap-3.13.0.min.js"
    package = (vendor / "gsap-package.json").read_text(encoding="utf-8")

    assert gsap.is_file() and gsap.stat().st_size > 70_000
    assert hashlib.sha256(gsap.read_bytes()).hexdigest() == "96c01b81f44a3290e2b4532f55e2c9534b2adc43273a19f3756b2cb41f0fd0b6"
    assert '"version": "3.13.0"' in package
    assert "Standard 'no charge' license" in package


def test_motion_runtime_is_purposeful_interruptible_and_reduced_motion_safe() -> None:
    motion = (PROJECT_ROOT / "nicegui_app" / "assets" / "motion" / "sing-yin-motion.js").read_text(encoding="utf-8")

    assert "window.gsap.fromTo" in motion
    assert "window.gsap.timeline" in motion
    assert "IntersectionObserver" in motion
    assert "MutationObserver" in motion
    assert "prefers-reduced-motion: reduce" in motion
    assert "clearProps: 'transform,opacity,visibility'" in motion
    assert "bootAttempts < 120" in motion
    assert "syMotion = 'unavailable'" in motion
    assert "repeat: -1" not in motion
    assert "ScrollTrigger" not in motion


def test_motion_assets_are_loaded_from_same_origin_only() -> None:
    motion_module = (PROJECT_ROOT / "nicegui_app" / "ui" / "motion.py").read_text(encoding="utf-8")
    main = (PROJECT_ROOT / "nicegui_app" / "main.py").read_text(encoding="utf-8")

    assert '/assets/vendor/gsap-3.13.0.min.js' in motion_module
    assert '/assets/motion/sing-yin-motion.js' in motion_module
    assert "http://" not in motion_module and "https://" not in motion_module
    assert 'url_path="/assets/motion"' in main
    assert 'url_path="/assets/vendor"' in main
