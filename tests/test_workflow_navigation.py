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
    assert "ui.navigate.to(route)" in navigation
    assert "window.history" not in navigation
    assert "aria-current=page" in navigation


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


def test_operation_workspaces_fill_available_width_and_collapse_on_mobile() -> None:
    layout = _read("nicegui_app/assets/css/sing-yin-layout-v1.css")
    weekly = _read("nicegui_app/ui/page_routes/weekly.py")
    stewardship = _read("nicegui_app/ui/page_routes/stewardship.py")
    people = _read("nicegui_app/ui/page_routes/people.py")

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


def test_language_control_has_an_independent_visible_surface() -> None:
    shell = _read("nicegui_app/ui/shell.py")
    theme = _read("nicegui_app/assets/css/sing-yin-theme-v1.css")

    assert "data-testid=language-control" in shell
    assert "sy-language-control" in shell
    control = re.search(r"^\.sy-language-control\s*\{(?P<body>[^}]*)\}", theme, re.MULTILINE)
    assert control is not None
    declarations = control.group("body")
    assert "background:" in declarations
    assert "border:" in declarations
    assert "min-width: 50px" in declarations
