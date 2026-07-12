from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from nicegui_app.config import POLICY_VERSION
from nicegui_app.release_evidence import PROJECT_ID, load_release_evidence, release_source_fingerprint


def _report(*, fingerprint: str, status: str = "pass") -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "project": PROJECT_ID,
        "policyVersion": POLICY_VERSION,
        "sourceFingerprint": fingerprint,
        "sourceFileCount": 2,
        "status": status,
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "finishedAt": datetime.now(timezone.utc).isoformat(),
        "humanAcceptanceRequired": True,
        "humanAcceptanceGuide": "docs/ACCEPTANCE_EVIDENCE.md",
        "checks": [
            {"name": "tests", "status": "pass", "durationMs": 10},
            {"name": "browser", "status": "pass", "durationMs": 20},
        ],
    }


def test_release_source_fingerprint_changes_with_release_input_content(tmp_path: Path) -> None:
    first = tmp_path / "first.py"
    second = tmp_path / "second.txt"
    first.write_text("value = 1\n", encoding="utf-8")
    second.write_text("contract-a\n", encoding="utf-8")
    original, count = release_source_fingerprint((first, second))

    second.write_text("contract-b\n", encoding="utf-8")
    changed, changed_count = release_source_fingerprint((first, second))

    assert count == changed_count == 2
    assert original != changed


def test_current_release_report_is_displayed_as_machine_pass_but_still_requires_people(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(_report(fingerprint="current")), encoding="utf-8")

    evidence = load_release_evidence(report_path, current_fingerprint="current")

    assert evidence.state == "pass"
    assert evidence.passed_checks == evidence.total_checks == 2
    assert evidence.finished_at is not None
    assert evidence.human_acceptance_required is True


def test_release_report_becomes_stale_when_source_fingerprint_changes(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(_report(fingerprint="old")), encoding="utf-8")

    assert load_release_evidence(report_path, current_fingerprint="new").state == "stale"


def test_release_report_rejects_malformed_or_false_human_acceptance_claims(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("not-json", encoding="utf-8")
    unsafe = tmp_path / "unsafe.json"
    payload = _report(fingerprint="current")
    payload["humanAcceptanceRequired"] = False
    unsafe.write_text(json.dumps(payload), encoding="utf-8")

    assert load_release_evidence(tmp_path / "missing.json", current_fingerprint="current").state == "missing"
    assert load_release_evidence(malformed, current_fingerprint="current").state == "unreadable"
    assert load_release_evidence(unsafe, current_fingerprint="current").state == "unreadable"
