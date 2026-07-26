from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (PROJECT_ROOT / relative).read_text(encoding="utf-8")


def test_shell_owned_page_heading_is_not_repeated_by_routine_routes() -> None:
    home = _read("nicegui_app/ui/page_routes/home.py")
    weekly = _read("nicegui_app/ui/page_routes/weekly.py")
    people = _read("nicegui_app/ui/page_routes/people.py")
    stewardship = _read("nicegui_app/ui/page_routes/stewardship.py")

    assert 'ui.label(t("getting_started")).classes("sy-page-title")' not in home
    assert 'ui.label(t("operator_guide")).classes("sy-page-title")' not in home
    assert 'ui.html(t("rosters"), tag="h2")' not in weekly
    assert 'ui.label(t("prefects")).classes("text-2xl font-semibold")' not in people
    assert 'ui.label(t("settings")).classes("text-2xl font-semibold")' not in stewardship


def test_story_and_evidence_heroes_do_not_stack_generic_kickers_and_titles() -> None:
    showcase = _read("nicegui_app/ui/page_routes/showcase.py")

    for redundant_key in (
        'ui.label(t("platform_kicker"))',
        'ui.label(t("engineering_kicker"))',
        'ui.label(t("architecture_kicker"))',
        'ui.label(t("platform_principle"))',
        'ui.label(t("architecture_reading_note"))',
        'ui.label(t("architecture_platform_link_note"))',
    ):
        assert redundant_key not in showcase


def test_design_system_and_audit_define_the_content_review_boundary() -> None:
    design_system = _read("Professional_Design_System.md")
    audit = _read("docs/CONTENT_DESIGN_AUDIT.md")

    assert "### Executable content-design contract" in design_system
    assert "## Inventory and disposition" in audit
    assert "Guest restrictions remain enforced below the UI" in design_system
    assert "Required consequences" in design_system


def test_public_github_reports_require_redacted_fictional_evidence() -> None:
    issue_form = _read(".github/ISSUE_TEMPLATE/bug_report.yml")
    issue_config = _read(".github/ISSUE_TEMPLATE/config.yml")
    security_policy = _read("SECURITY.md")

    assert "I removed names, leave details, roster content" in issue_form
    assert "I used fictional data for reproduction" in issue_form
    assert "Private security vulnerability report" in issue_config
    assert "host-local incident bundles out of Issues" in security_policy
