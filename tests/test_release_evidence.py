from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from nicegui_app.config import POLICY_VERSION
from nicegui_app.release_evidence import (
    PROJECT_ID,
    RELEASE_EXCLUDED_DIRECTORY_NAMES,
    RELEASE_EXCLUDED_RELATIVE_PREFIXES,
    RELEASE_SOURCE_FILES,
    RELEASE_SOURCE_ROOTS,
    RELEASE_SUFFIXES,
    load_release_evidence,
    release_source_fingerprint,
)
from nicegui_app import release_evidence


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


def test_runtime_source_fingerprint_is_cached_for_repeated_showcase_reads(monkeypatch) -> None:
    release_evidence._cached_release_source_fingerprint.cache_clear()
    calls = 0

    def calculate(_paths=None):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        return ("a" * 64, 12)

    monkeypatch.setattr(release_evidence, "_calculate_release_source_fingerprint", calculate)

    assert release_source_fingerprint() == ("a" * 64, 12)
    assert release_source_fingerprint() == ("a" * 64, 12)
    assert calls == 1
    release_evidence._cached_release_source_fingerprint.cache_clear()


def test_release_fingerprint_tracks_deployed_artifacts_without_documentation_or_ci() -> None:
    assert {
        ".md",
        ".m4a",
        ".css",
        ".js",
        ".json",
        ".jsonc",
        ".png",
        ".svg",
        ".webp",
        ".woff2",
        ".ttf",
        ".yml",
    } <= RELEASE_SUFFIXES
    assert not any(path.name in {"docs", "tests", ".github"} for path in RELEASE_SOURCE_ROOTS)
    assert any(path.name == "cloudflare" for path in RELEASE_SOURCE_ROOTS)
    assert any(path.name == "music" for path in RELEASE_SOURCE_ROOTS)
    tracked_relative_files = {
        path.relative_to(release_evidence.PROJECT_ROOT).as_posix().lower()
        for path in RELEASE_SOURCE_FILES
    }
    assert {
        ".env.example",
        ".gitattributes",
        ".gitignore",
        "daily_verses.py",
        "data/demo/prefects.zh-hk.seed.json",
        "data/devotional/daily-verses.seed.json",
        "scripts/deploy_windows_release.ps1",
        "scripts/start_sing_yin_roster.ps1",
        "scripts/verify_release_candidate.py",
        "scripts/run_security_checks.py",
    } <= tracked_relative_files
    assert {
        "readme.md",
        "project_status.md",
        "professional_design_system.md",
    }.isdisjoint(tracked_relative_files)
    assert "music/custom/" in RELEASE_EXCLUDED_RELATIVE_PREFIXES
    assert "music/youtube-imports/" in RELEASE_EXCLUDED_RELATIVE_PREFIXES


def test_release_fingerprint_tracks_package_manifest_but_not_dependency_cache(monkeypatch, tmp_path: Path) -> None:
    worker_root = tmp_path / "cloudflare" / "roster_viewer"
    worker_root.mkdir(parents=True)
    manifest = worker_root / "package.json"
    manifest.write_text('{"version":"1"}\n', encoding="utf-8")
    dependency_manifest = worker_root / "node_modules" / "dependency" / "package.json"
    dependency_manifest.parent.mkdir(parents=True)
    dependency_manifest.write_text('{"version":"private-cache"}\n', encoding="utf-8")
    monkeypatch.setattr(release_evidence, "RELEASE_SOURCE_ROOTS", (tmp_path / "cloudflare",))
    monkeypatch.setattr(release_evidence, "RELEASE_SOURCE_FILES", ())

    original, count = release_evidence._calculate_release_source_fingerprint()
    manifest.write_text('{"version":"2"}\n', encoding="utf-8")
    changed, changed_count = release_evidence._calculate_release_source_fingerprint()

    assert {"node_modules", ".wrangler"} <= RELEASE_EXCLUDED_DIRECTORY_NAMES
    assert count == changed_count == 1
    assert original != changed


def test_release_fingerprint_changes_with_cloudflare_worker_content(monkeypatch, tmp_path: Path) -> None:
    worker_root = tmp_path / "cloudflare"
    worker_root.mkdir()
    worker = worker_root / "worker.js"
    worker.write_text("export default { version: 1 };\n", encoding="utf-8")
    monkeypatch.setattr(release_evidence, "RELEASE_SOURCE_ROOTS", (worker_root,))
    monkeypatch.setattr(release_evidence, "RELEASE_SOURCE_FILES", ())

    original, count = release_evidence._calculate_release_source_fingerprint()
    worker.write_text("export default { version: 2 };\n", encoding="utf-8")
    changed, changed_count = release_evidence._calculate_release_source_fingerprint()

    assert count == changed_count == 1
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
