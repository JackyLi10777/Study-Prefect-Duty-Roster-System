from __future__ import annotations

from nicegui_app.config import PROJECT_ROOT


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_visual_narrative_layer_loads_between_base_and_mobile_overrides() -> None:
    head = _read("nicegui_app/ui/theme_markup.py")

    tokens = head.index("/assets/css/sing-yin-tokens-v1.css")
    base = head.index("/assets/css/sing-yin-theme-v1.css")
    narrative = head.index("/assets/css/sing-yin-narrative-v1.css")
    mobile = head.index("/assets/css/sing-yin-mobile-v1.css")

    assert tokens < base < narrative < mobile


def test_shell_exposes_stable_non_translated_page_and_chapter_context() -> None:
    shell = _read("nicegui_app/ui/shell.py")

    assert "def _navigation_context(" in shell
    assert "def _page_slug(" in shell
    assert 'data-sy-page="{page_slug}"' in shell
    assert 'data-sy-mode="{access_mode.value}"' in shell
    assert "sy-page-context" in shell
    assert "sy-header-eyebrow" in shell
    assert "data-sy-section=" in shell


def test_narrative_layer_preserves_sensitive_work_surfaces() -> None:
    narrative = _read("nicegui_app/assets/css/sing-yin-narrative-v1.css")

    assert "This file does not decorate records, forms, tables, PDFs or policy states." in narrative
    for sensitive_selector in (
        ".q-table",
        ".q-field",
        ".sy-roster-table",
        ".sy-prefect-table",
        ".sy-pdf",
        ".sy-leave-form",
    ):
        assert sensitive_selector not in narrative

    assert "var(--sy-image-onboarding)" in narrative
    assert "@media (prefers-reduced-motion: reduce)" in narrative


def test_narrative_grammar_covers_work_reflection_and_reference_pages() -> None:
    narrative = _read("nicegui_app/assets/css/sing-yin-narrative-v1.css")
    motion = _read("nicegui_app/assets/motion/sing-yin-motion.js")

    for selector in (
        ".sy-page-context",
        ".sy-dashboard-history",
        ".sy-devotional-companion",
        ".sy-page-platform > .sy-architecture-section",
        ".sy-reference-index",
    ):
        assert selector in narrative

    for selector in (
        ".sy-page-context",
        ".sy-dashboard-history",
        ".sy-devotional-reading-grid",
        ".sy-reference-index",
    ):
        assert selector in motion

    assert "repeat: -1" not in motion
