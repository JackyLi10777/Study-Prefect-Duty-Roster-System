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
    assert "recent_weeks = workflow.roster_week_history(page=1, page_size=1)" in home
    assert "latest = recent_weeks[0] if recent_weeks else None" in home
    assert "workflow.roster_weeks()" not in home
    dashboard = home.split("def dashboard_page()", 1)[1].split('@ui.page("/dashboard")', 1)[0]
    assert "workflow.roster_week_for_start(week_start)" in dashboard
    assert "resolve_dashboard_next_action(" in dashboard
    assert dashboard.index("dashboard-current-week") < dashboard.index('classes("sy-dashboard-history")')
    assert "_dashboard_verse(" not in dashboard
    assert "_render_flow_step(" not in dashboard
    assert "sy-mobile-next-action" not in dashboard


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


def test_command_center_layer_owns_the_reset_composition_after_mobile_compatibility() -> None:
    markup = (PROJECT_ROOT / "nicegui_app" / "ui" / "theme_markup.py").read_text(
        encoding="utf-8"
    )
    command_center = (
        PROJECT_ROOT
        / "nicegui_app"
        / "assets"
        / "css"
        / "sing-yin-command-center-v2.css"
    ).read_text(encoding="utf-8")

    assert markup.index('("mobile",') < markup.index('("command-center-v2",')
    assert "--sy-v2-canvas" in command_center
    assert ".sy-dashboard-grid" in command_center
    assert "grid-template-columns: minmax(0, 1fr) minmax(280px, 320px)" in command_center
    assert ".sy-nav-control.sy-nav-active" in command_center
    atmosphere_rule = re.search(
        r"\.sy-page-atmosphere\s*\{(?P<body>.*?)\}",
        command_center,
        re.DOTALL,
    )
    assert atmosphere_rule is not None
    assert "min-height: 90px" in atmosphere_rule.group("body")
    arrow_rule = re.search(
        r"\.sy-flow-step:not\(:last-child\)::after\s*\{(?P<body>.*?)\}",
        command_center,
        re.DOTALL,
    )
    assert arrow_rule is not None
    assert 'content: "→"' in arrow_rule.group("body")
    assert "prefers-reduced-motion" in command_center
    assert "forced-colors" in command_center


def test_settings_leads_with_readiness_then_groups_preferences_and_recovery() -> None:
    stewardship = (
        PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "stewardship.py"
    ).read_text(encoding="utf-8")
    music = (PROJECT_ROOT / "nicegui_app" / "ui" / "music.py").read_text(
        encoding="utf-8"
    )
    command_center = (
        PROJECT_ROOT
        / "nicegui_app"
        / "assets"
        / "css"
        / "sing-yin-command-center-v2.css"
    ).read_text(encoding="utf-8")

    overview = stewardship.index("sy-settings-overview")
    music_dispatch = stewardship.index("render_music_library_settings()")
    persistence = stewardship.index('t("persistence_notice")')
    recovery = stewardship.index('t("backup_restore")')

    assert overview < music_dispatch < persistence < recovery
    assert stewardship.count("sy-settings-continuity") >= 3
    assert "sy-settings-recovery" in stewardship
    assert music.count("sy-settings-preference") == 3
    assert ".sy-page-settings .sy-settings-preference" in command_center
    assert ".sy-page-settings .sy-settings-continuity" in command_center
    assert ".sy-page-settings .sy-settings-recovery" in command_center


def test_design_reference_protocol_rejects_template_dashboard_defaults() -> None:
    design = (PROJECT_ROOT / "Professional_Design_System.md").read_text(encoding="utf-8")

    for reference in ("ReactBits", "SuperDesign", "21st.dev", "Linear design analysis"):
        assert reference in design
    assert "Reference-led prompt and component protocol" in design
    assert "Operator moment:" in design
    assert "KPI-dashboard defaults" in design
    assert "Iterate with one delta at a time" in design
