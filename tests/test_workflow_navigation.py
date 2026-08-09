from __future__ import annotations

import re

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.i18n import EN, MESSAGES, ZH_HK


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_roster_child_routes_have_explicit_hierarchy_and_return_destinations() -> None:
    weekly = _read("nicegui_app/ui/page_routes/weekly.py")
    navigation = _read("nicegui_app/ui/workflow_navigation.py")

    assert 'render_back_action(t("back_to_roster_hub"), "/rosters"' in weekly
    assert 'test_id="back-to-roster-detail"' in weekly
    assert "render_route_trail(" in weekly
    assert weekly.count("render_workflow_navigation(") >= 3
    assert "from nicegui_app.ui.navigation import ROUTE_FOCUS_JAVASCRIPT, navigate_to" in navigation
    assert "navigate_to(route)" in navigation
    assert "window.history" not in navigation
    assert "aria-current=page" in navigation
    assert 'WorkflowStep(t("roster_workflow_history"), "/rosters/history"' in weekly
    assert '"id=roster-history data-testid=roster-history"' in weekly
    current_branch = navigation.split("if is_current:", 1)[1].split("else:", 1)[0]
    assert 'ui.element("div").props("aria-current=step")' in current_branch
    assert "ui.button" not in current_branch
    assert 'data-design-direction="B-A-C"' in navigation
    assert "--sy-workflow-position" in navigation
    assert "data-state={semantic_state}" in navigation
    assert "aria-disabled=true" in navigation


def test_selected_design_composition_keeps_operational_rhythm_primary() -> None:
    layout = _read("nicegui_app/assets/css/sing-yin-layout-v1.css")
    design_system = _read("Professional_Design_System.md")

    assert ".sy-workflow-navigation--operational-rhythm::before" in layout
    assert "width: var(--sy-workflow-position, 25%)" in layout
    assert "@media (prefers-reduced-motion: reduce)" in layout
    assert "B → A → C" in design_system
    assert "Operational Rhythm" in design_system
    assert "Quiet Editorial Continuity" in design_system
    assert "Sacred Service Narrative" in design_system


def test_internal_navigation_uses_one_focus_preserving_gateway() -> None:
    """Every in-app route transition marks the next main landmark for focus."""

    ui_root = PROJECT_ROOT / "nicegui_app" / "ui"
    navigation = _read("nicegui_app/ui/navigation.py")
    assert "sessionStorage.setItem" in navigation
    assert "ui.navigate.to(route)" in navigation

    direct_calls: list[str] = []
    for path in ui_root.rglob("*.py"):
        if path.name == "navigation.py":
            continue
        source = path.read_text(encoding="utf-8")
        if "ui.navigate.to(" in source:
            direct_calls.append(str(path.relative_to(PROJECT_ROOT)))
    assert direct_calls == []


def test_roster_workflow_copy_is_complete_in_both_languages() -> None:
    for key in (
        "back_to_roster_hub",
        "back_to_week_detail",
        "roster_workflow_label",
        "roster_workflow_generate",
        "roster_workflow_review",
        "roster_workflow_adjust",
        "roster_workflow_history",
    ):
        assert MESSAGES[key][ZH_HK].strip()
        assert MESSAGES[key][EN].strip()


def test_fairness_deep_link_preserves_intent_and_has_an_explicit_return_destination() -> None:
    people = _read("nicegui_app/ui/page_routes/people.py")

    assert '@ui.page("/audit")' in people
    assert 'test_id="back-to-prefect-directory"' in people
    assert 'render_route_trail(' in people
    assert '_render_fairness_panel(workflow)' in people
    assert 'ui.navigate.to("/prefects")' not in people.split('@ui.page("/audit")', 1)[1]
    for key in ("back_to_prefect_directory", "people_route_hierarchy"):
        assert MESSAGES[key][ZH_HK].strip()
        assert MESSAGES[key][EN].strip()


def test_operation_workspaces_fill_available_width_and_collapse_on_mobile() -> None:
    layout = _read("nicegui_app/assets/css/sing-yin-layout-v1.css")
    weekly = _read("nicegui_app/ui/page_routes/weekly.py")
    stewardship = _read("nicegui_app/ui/page_routes/stewardship.py")
    people = _read("nicegui_app/ui/page_routes/people.py")
    music = _read("nicegui_app/ui/music.py")
    online_music = _read("nicegui_app/ui/youtube_music.py")

    assert ".sy-operations-panel" in layout
    assert "max-width: none" in layout
    assert ".sy-operations-grid" in layout
    mobile = layout.split("@media (max-width: 900px)", 1)[1]
    assert ".sy-operations-grid" in mobile
    assert "grid-template-columns: minmax(0, 1fr)" in mobile
    assert weekly.count("sy-operations-panel") >= 3
    assert stewardship.count("sy-operations-panel") >= 4
    assert "sy-operations-panel" in people
    assert 'classes("w-full max-w-3xl")' not in people
    assert music.count("sy-operations-panel") >= 3
    assert "sy-operations-panel" in online_music
    assert "sy-settings-section sy-audio-settings w-full max-w-3xl" not in music
    assert "sy-online-music-settings w-full max-w-3xl" not in online_music


def test_header_controls_share_one_visible_surface_contract() -> None:
    shell = _read("nicegui_app/ui/shell.py")
    theme = _read("nicegui_app/assets/css/sing-yin-theme-v1.css")

    assert "data-testid=language-control" in shell
    for kind in ("language", "sound", "theme", "logout"):
        assert f'_header_control_classes("{kind}"' in shell
    control = re.search(r"^\.sy-header-control\s*\{(?P<body>[^}]*)\}", theme, re.MULTILINE)
    assert control is not None
    declarations = control.group("body")
    assert "background:" in declarations
    assert "border:" in declarations
    assert "min-width: 44px" in declarations
    assert ".sy-header-control--language" in theme
    assert ".sy-header-control--logout:hover" in theme


def test_existing_week_generation_uses_an_exact_bounded_week_query() -> None:
    weekly = _read("nicegui_app/ui/page_routes/weekly.py")

    roster_page = weekly.split('@ui.page("/rosters")', 1)[1].split(
        '@ui.page("/rosters/new")', 1
    )[0]
    assert "roster_week_history(page=1, page_size=100)" not in roster_page
    assert "workflow.roster_week_for_start(" in roster_page
    assert 'current_week["version"]' in roster_page
    assert "published_weeks" not in roster_page
