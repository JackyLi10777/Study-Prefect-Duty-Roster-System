from __future__ import annotations

import re

from nicegui_app.config import PROJECT_ROOT


def test_dashboard_keeps_one_primary_workbench_and_a_compact_review_rail() -> None:
    home = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "home.py").read_text(
        encoding="utf-8"
    )

    assert 'classes("sy-dashboard-grid w-full items-stretch")' in home
    assert "sy-dashboard-grid sy-dashboard-grid--single" not in home
    assert 'ui.element("aside").classes("sy-dashboard-history")' in home
    assert "aria-labelledby=dashboard-history-title" in home
    assert "data-testid=dashboard-history" in home
    assert 'ui.element("ul").classes("sy-dashboard-history-list")' in home
    assert 'ui.element("li").classes("sy-dashboard-history-item")' in home
    assert "recent_weeks = weeks[:3]" in home
    assert re.search(r"^\s*weeks = weeks\[:3\]$", home, re.MULTILINE) is None

    verse_index = home.index('classes("sy-daily-start w-full")')
    workbench_index = home.index('classes("sy-workbench grow min-w-0")')
    history_index = home.index('classes("sy-dashboard-history")')
    assert verse_index < workbench_index < history_index


def test_dashboard_review_rail_uses_solid_surfaces_and_stacks_before_phone_width() -> None:
    theme = (
        PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-theme-v1.css"
    ).read_text(encoding="utf-8")

    history_rule = theme.split(".sy-dashboard-history {", 1)[1].split("}", 1)[0]
    assert "background: var(--sy-surface)" in history_rule
    assert "border: 1px solid var(--sy-line)" in history_rule
    assert "url(" not in history_rule
    assert ".sy-dashboard-history-item + .sy-dashboard-history-item" in theme
    history_action_rule = theme.split(".sy-dashboard-history-action {", 1)[1].split("}", 1)[0]
    assert "min-height: 44px" in history_action_rule
    assert "@media (max-width: 1280px) { .sy-dashboard-grid { grid-template-columns: minmax(0, 1fr) !important; } }" in theme
    phone_start = theme.index("@media (max-width: 600px) {")
    phone_end = theme.find("@media", phone_start + 1)
    phone_scope = theme[phone_start : phone_end if phone_end >= 0 else None]
    assert ".sy-dashboard-history" in phone_scope


def test_design_reference_protocol_rejects_template_dashboard_defaults() -> None:
    design = (PROJECT_ROOT / "Professional_Design_System.md").read_text(encoding="utf-8")

    for reference in ("ReactBits", "SuperDesign", "21st.dev", "Linear design analysis"):
        assert reference in design
    assert "Reference-led prompt and component protocol" in design
    assert "Operator moment:" in design
    assert "KPI-dashboard defaults" in design
    assert "Iterate with one delta at a time" in design
