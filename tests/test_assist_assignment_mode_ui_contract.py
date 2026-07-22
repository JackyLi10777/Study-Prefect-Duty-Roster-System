from __future__ import annotations

import ast
from pathlib import Path

from nicegui_app.ui.i18n_catalog.people import MESSAGES as PEOPLE_MESSAGES
from nicegui_app.ui.i18n_catalog.weekly import MESSAGES as WEEKLY_MESSAGES


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEEKLY_ROUTE = PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "weekly.py"
PEOPLE_ROUTE = PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "people.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_roster_generation_uses_stable_mode_code_and_preserves_existing_mode() -> None:
    source = _source(WEEKLY_ROUTE)
    tree = ast.parse(source, filename=str(WEEKLY_ROUTE))

    generation_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "generate_and_save_draft"
    ]
    assert generation_calls
    mode_keywords = [
        keyword
        for call in generation_calls
        for keyword in call.keywords
        if keyword.arg == "assist_assignment_mode"
    ]
    assert len(mode_keywords) == 1
    assert isinstance(mode_keywords[0].value, ast.Call)
    assert isinstance(mode_keywords[0].value.func, ast.Name)
    assert mode_keywords[0].value.func.id == "_assist_assignment_mode_code"

    assert 'week.get("assistAssignmentMode")' in source
    assert "initial_week.isoformat(),\n                        LEGACY_FIXED_WEEKDAY" in source
    assert "LEGACY_FIXED_WEEKDAY: t(\"assist_assignment_mode_legacy\")" in source
    assert "FLEXIBLE_WEEKLY: t(\"assist_assignment_mode_flexible\")" in source
    assert "aria-describedby=assist-mode-description" in source
    assert "id=assist-mode-description aria-live=polite" in source


def test_prefect_dialog_exposes_fixed_assist_mapping_and_explains_availability() -> None:
    source = _source(PEOPLE_ROUTE)

    assert 'existing.get("fixedGeneralDuty", "NONE")' in source
    assert "fixed_general_duty=(" in source
    assert 't("availability_assignment_help")' in source
    assert 'label=t("fixed_assist_day")' in source
    assert 't("fixed_assist_day_help")' in source
    assert "fixed_assist_day.set_visibility" in source
    assert "aria-describedby=fixed-assist-day-help" in source
    assert "id=fixed-assist-day-help" in source


def test_assist_mode_and_availability_copy_is_complete_in_both_languages() -> None:
    weekly_keys = {
        "assist_assignment_mode_title",
        "assist_assignment_mode_detail",
        "assist_assignment_mode_label",
        "assist_assignment_mode_legacy",
        "assist_assignment_mode_legacy_detail",
        "assist_assignment_mode_flexible",
        "assist_assignment_mode_flexible_detail",
        "assist_assignment_mode_constraints",
        "assist_assignment_mode_used",
    }
    for key in weekly_keys:
        assert set(WEEKLY_MESSAGES[key]) == {"zh-HK", "en"}
        assert all(value.strip() for value in WEEKLY_MESSAGES[key].values())

    legacy_copy = WEEKLY_MESSAGES["assist_assignment_mode_legacy_detail"]
    assert "該次當值" in legacy_copy["zh-HK"]
    assert "substitute for that duty this week" in legacy_copy["en"]
    assert "generation stops" in legacy_copy["en"]

    flexible_copy = WEEKLY_MESSAGES["assist_assignment_mode_flexible_detail"]
    assert "可值班日" in flexible_copy["zh-HK"]
    assert "上週相同星期" in flexible_copy["zh-HK"]
    assert "availability" in flexible_copy["en"]
    assert "previous-week weekday" in flexible_copy["en"]

    availability_copy = PEOPLE_MESSAGES["availability_assignment_help"]
    assert "未選星期視為不可值班" in availability_copy["zh-HK"]
    assert "Unselected weekdays are unavailable" in availability_copy["en"]

    fixed_help = PEOPLE_MESSAGES["fixed_assist_day_help"]
    assert "助理首席導學風紀" in fixed_help["zh-HK"]
    assert "flexible weekly mode ignores" in fixed_help["en"]


def test_operator_and_architecture_docs_publish_one_mode_contract() -> None:
    policy_doc = _source(PROJECT_ROOT / "docs" / "ROSTER_POLICY_MODES.md")
    readme = _source(PROJECT_ROOT / "README.md")
    architecture = _source(PROJECT_ROOT / "docs" / "NICEGUI_ARCHITECTURE.md")
    handover = _source(PROJECT_ROOT / "docs" / "RELEASE_HANDOVER.md")
    design = _source(PROJECT_ROOT / "Professional_Design_System.md")

    for document in (policy_doc, readme, architecture, handover, design):
        assert "固定星期模式" in document or "fixed-weekday" in document.lower()
        assert "每週靈活模式" in document or "flexible" in document

    for stable_code in ("legacy_fixed_weekday", "flexible_weekly"):
        assert stable_code in policy_doc
        assert stable_code in architecture
        assert stable_code in design

    assert "該次當值" in policy_doc
    assert "translated labels" in policy_doc
    assert "ROSTER_POLICY_MODES.md" in readme
    assert "ROSTER_POLICY_MODES.md" in handover
