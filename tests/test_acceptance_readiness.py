from __future__ import annotations

from pathlib import Path
import re

from nicegui_app.ui.acceptance_readiness import (
    ACCEPTANCE_SESSIONS,
    acceptance_check_counts,
    acceptance_check_ids,
    build_supervised_acceptance_worksheet,
)
from nicegui_app.ui.i18n_catalog import MESSAGES


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MATRIX_ID_PATTERN = re.compile(r"^\| ((?:H|A)-\d{2}) \|", re.MULTILINE)
ROUTE_PATTERN = re.compile(r"@ui\.page\([\"']([^\"']+)[\"']\)")


def test_acceptance_session_catalog_covers_the_authoritative_matrix_without_drift() -> None:
    matrix = (PROJECT_ROOT / "docs" / "ACCEPTANCE_EVIDENCE.md").read_text(encoding="utf-8")
    document_ids = tuple(MATRIX_ID_PATTERN.findall(matrix))
    catalog_ids = acceptance_check_ids()

    assert document_ids
    assert len(document_ids) == len(set(document_ids))
    assert len(catalog_ids) == len(set(catalog_ids))
    assert set(catalog_ids) == set(document_ids)
    assert acceptance_check_counts() == (22, 4)


def test_acceptance_sessions_only_link_to_registered_workspaces_and_translated_copy() -> None:
    route_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes").glob("*.py")
    )
    registered_routes = set(ROUTE_PATTERN.findall(route_source))

    assert len(ACCEPTANCE_SESSIONS) == 7
    for session in ACCEPTANCE_SESSIONS:
        assert session.check_ids
        assert all(check_id.startswith("H-") for check_id in session.operator_checks)
        assert all(check_id.startswith("A-") for check_id in session.advisor_checks)
        assert session.route in registered_routes
        assert session.title_key in MESSAGES
        assert session.body_key in MESSAGES
        assert session.destination_key in MESSAGES
        assert session.role_key in MESSAGES


def test_downloadable_worksheet_lists_every_human_check_once_and_never_self_signs() -> None:
    def translate(key: str, **values: object) -> str:
        suffix = " ".join(f"{name}={value}" for name, value in values.items())
        return f"{key} {suffix}".rstrip()

    worksheet = build_supervised_acceptance_worksheet(translate).decode("utf-8")

    for check_id in acceptance_check_ids():
        assert worksheet.count(f"- [ ] {check_id}") == 1
    assert "acceptance_worksheet_observer" in worksheet
    assert "acceptance_worksheet_result" in worksheet
    assert "acceptance_worksheet_final_note" in worksheet
    assert "[x]" not in worksheet.lower()


def test_handover_page_derives_counts_and_sessions_from_the_catalog() -> None:
    source = (
        PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "stewardship.py"
    ).read_text(encoding="utf-8")
    messages = (
        PROJECT_ROOT / "nicegui_app" / "ui" / "i18n_catalog" / "stewardship.py"
    ).read_text(encoding="utf-8")
    browser_verifier = (PROJECT_ROOT / "scripts" / "verify_nicegui_ui.py").read_text(
        encoding="utf-8"
    )

    assert "operator_check_count, advisor_check_count = acceptance_check_counts()" in source
    assert "for index, session in enumerate(ACCEPTANCE_SESSIONS, start=1)" in source
    assert "data-testid=acceptance-machine-status" in source
    assert "data-testid=acceptance-download-worksheet" in source
    assert "data-testid=acceptance-session-{session.key}" in source
    assert "13 operator checks" not in messages
    assert "13 項實務核對" not in messages
    assert "session_cards.count() == len(ACCEPTANCE_SESSIONS)" in browser_verifier
    assert 'session_cards.first.wait_for(state="visible", timeout=10_000)' in browser_verifier
    assert "for check_id in acceptance_check_ids()" in browser_verifier
