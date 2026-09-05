from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from nicegui_app.config import POLICY_VERSION
from nicegui_app.release_evidence import (
    PROJECT_ID,
    RELEASE_REPORT_SCHEMA_VERSION,
    RELEASE_BYTE_EXACT_SUFFIXES,
    RELEASE_EXCLUDED_DIRECTORY_NAMES,
    RELEASE_EXCLUDED_RELATIVE_GLOBS,
    RELEASE_EXCLUDED_RELATIVE_PREFIXES,
    RELEASE_SOURCE_FILES,
    RELEASE_SOURCE_ROOTS,
    RELEASE_SUFFIXES,
    load_release_evidence,
    release_source_fingerprint,
)
from nicegui_app import release_evidence
from nicegui_app.release_gates import GATE_MANIFEST_BINDING, REQUIRED_CHECK_IDENTITIES
from scripts import verify_release_candidate


def _report(*, fingerprint: str, status: str = "pass") -> dict[str, object]:
    report = {
        "schemaVersion": RELEASE_REPORT_SCHEMA_VERSION,
        "project": PROJECT_ID,
        "policyVersion": POLICY_VERSION,
        "sourceFingerprint": fingerprint,
        "sourceFileCount": 2,
        "sourceCommit": "a" * 40,
        "sourceTree": "b" * 40,
        "sourceDirty": False,
        "plannedReleaseTag": "v1.2.0-rc.32",
        "immutableReleaseReference": "refs/tags/v1.2.0-rc.32",
        "requiredCheckIdentities": list(REQUIRED_CHECK_IDENTITIES),
        "gateManifest": dict(GATE_MANIFEST_BINDING),
        "toolVersions": {"python": "3.12.10", "git": "git version 2.50.0"},
        "status": status,
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "finishedAt": datetime.now(timezone.utc).isoformat(),
        "humanAcceptanceRequired": True,
        "humanAcceptanceGuide": "docs/ACCEPTANCE_EVIDENCE.md",
        "checks": [
            {"name": name, "status": "pass", "durationMs": 10} for name in REQUIRED_CHECK_IDENTITIES
        ],
    }
    report["postVerificationSource"] = {
        "sourceFingerprint": report["sourceFingerprint"],
        "sourceFileCount": report["sourceFileCount"],
        "sourceCommit": report["sourceCommit"],
        "sourceTree": report["sourceTree"],
        "sourceDirty": False,
    }
    return report


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


def test_release_source_fingerprint_normalizes_windows_text_line_endings(tmp_path: Path) -> None:
    source = tmp_path / ".env.example"
    source.write_bytes(b"FIRST=one\nSECOND=two\n")
    lf_fingerprint, lf_count = release_source_fingerprint((source,))

    source.write_bytes(b"FIRST=one\r\nSECOND=two\r\n")
    crlf_fingerprint, crlf_count = release_source_fingerprint((source,))

    assert lf_count == crlf_count == 1
    assert lf_fingerprint == crlf_fingerprint


def test_release_text_normalization_preserves_bom_and_lone_carriage_return(tmp_path: Path) -> None:
    source = tmp_path / "settings.txt"
    source.write_bytes(b"value=one\r\n")
    original, _ = release_source_fingerprint((source,))

    source.write_bytes(b"\xef\xbb\xbfvalue=one\r\n")
    bom_changed, _ = release_source_fingerprint((source,))
    source.write_bytes(b"value=one\r")
    lone_cr_changed, _ = release_source_fingerprint((source,))

    assert bom_changed != original
    assert lone_cr_changed != original


def test_release_binary_inputs_remain_byte_exact(tmp_path: Path) -> None:
    assert RELEASE_BYTE_EXACT_SUFFIXES <= RELEASE_SUFFIXES
    for suffix in sorted(RELEASE_BYTE_EXACT_SUFFIXES):
        source = tmp_path / f"asset{suffix}"
        source.write_bytes(b"binary\r\nbytes")
        original, original_count = release_source_fingerprint((source,))
        source.write_bytes(b"binary\nbytes")
        changed, changed_count = release_source_fingerprint((source,))

        assert original_count == changed_count == 1
        assert changed != original, suffix


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


def test_release_verifier_can_refresh_a_cached_fingerprint_at_the_final_boundary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "candidate.py"
    source.write_text("value = 1\n", encoding="utf-8")
    monkeypatch.setattr(release_evidence, "RELEASE_SOURCE_ROOTS", (tmp_path,))
    monkeypatch.setattr(release_evidence, "RELEASE_SOURCE_FILES", ())
    release_evidence._cached_release_source_fingerprint.cache_clear()
    cached, _ = release_source_fingerprint()

    source.write_text("value = 2\n", encoding="utf-8")

    assert release_source_fingerprint()[0] == cached
    assert release_source_fingerprint(refresh=True)[0] != cached
    release_evidence._cached_release_source_fingerprint.cache_clear()


def test_release_fingerprint_tracks_deployed_artifacts_without_documentation_or_ci() -> None:
    assert {
        ".md",
        ".m4a",
        ".ico",
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
    assert any(path.name == "design_system" for path in RELEASE_SOURCE_ROOTS)
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
    assert "music/*(1).m4a" in RELEASE_EXCLUDED_RELATIVE_GLOBS


def test_release_fingerprint_ignores_untracked_downloader_duplicate_music(
    monkeypatch,
    tmp_path: Path,
) -> None:
    music_root = tmp_path / "music"
    music_root.mkdir()
    curated = music_root / "Ubi caritas.m4a"
    duplicate = music_root / "Ubi caritas(1).M4A"
    nested_duplicate = music_root / "archive" / "Ubi caritas(1).m4a"
    numbered_original = music_root / "Ubi caritas(11).m4a"
    nested_duplicate.parent.mkdir()
    curated.write_bytes(b"curated-release-track")
    duplicate.write_bytes(b"local-duplicate-a")
    nested_duplicate.write_bytes(b"nested-release-track-a")
    numbered_original.write_bytes(b"numbered-release-track-a")
    monkeypatch.setattr(release_evidence, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(release_evidence, "RELEASE_SOURCE_ROOTS", (music_root,))
    monkeypatch.setattr(release_evidence, "RELEASE_SOURCE_FILES", ())

    original, count = release_evidence._calculate_release_source_fingerprint()
    duplicate.write_bytes(b"local-duplicate-b")
    unchanged, unchanged_count = release_evidence._calculate_release_source_fingerprint()
    nested_duplicate.write_bytes(b"nested-release-track-b")
    nested_changed, nested_changed_count = release_evidence._calculate_release_source_fingerprint()
    numbered_original.write_bytes(b"numbered-release-track-b")
    numbered_changed, numbered_changed_count = release_evidence._calculate_release_source_fingerprint()

    assert count == unchanged_count == nested_changed_count == numbered_changed_count == 3
    assert original == unchanged
    assert nested_changed != original
    assert numbered_changed != nested_changed


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
    original_is_file = Path.is_file

    def guarded_is_file(path: Path) -> bool:
        if "node_modules" in path.parts:
            raise OSError("excluded dependency mount must not be inspected")
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", guarded_is_file)

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
    assert evidence.passed_checks == evidence.total_checks == len(REQUIRED_CHECK_IDENTITIES)
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


def test_release_report_rejects_dirty_or_mismatched_release_provenance(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    payload = _report(fingerprint="current")
    payload["sourceDirty"] = True
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_release_evidence(report_path, current_fingerprint="current").state == "unreadable"


def test_release_report_requires_matching_post_verification_source(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    payload = _report(fingerprint="current")
    del payload["postVerificationSource"]
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_release_evidence(report_path, current_fingerprint="current").state == "unreadable"

    payload = _report(fingerprint="current")
    payload["postVerificationSource"]["sourceDirty"] = True  # type: ignore[index]
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_release_evidence(report_path, current_fingerprint="current").state == "unreadable"

    payload = _report(fingerprint="current")
    payload["postVerificationSource"]["sourceDirty"] = 0  # type: ignore[index]
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_release_evidence(report_path, current_fingerprint="current").state == "unreadable"


def test_formal_verifier_fails_when_any_gate_changes_the_candidate_source(monkeypatch) -> None:
    states = iter(
        (
            {
                "sourceFingerprint": "a" * 64,
                "sourceFileCount": 10,
                "sourceCommit": "b" * 40,
                "sourceTree": "c" * 40,
                "sourceDirty": False,
            },
            {
                "sourceFingerprint": "a" * 64,
                "sourceFileCount": 10,
                "sourceCommit": "b" * 40,
                "sourceTree": "c" * 40,
                "sourceDirty": True,
            },
        )
    )
    initial = next(states)
    monkeypatch.setattr(verify_release_candidate, "_source_state", lambda **_kwargs: next(states))
    monkeypatch.setattr(verify_release_candidate, "_write_report", lambda _report: None)

    with pytest.raises(verify_release_candidate.ReleaseVerificationError, match="changed the source"):
        verify_release_candidate._record_post_verification_source(
            {},
            initial,
            require_stable=True,
        )


def test_browser_component_evidence_never_overwrites_tracked_visual_references() -> None:
    verifier = (release_evidence.PROJECT_ROOT / "scripts" / "verify_nicegui_ui.py").read_text(encoding="utf-8")

    assert 'PROJECT_ROOT / "logs" / "uiverse-components"' in verifier
    assert 'PROJECT_ROOT / "test-results" / "uiverse-components"' not in verifier


def test_release_report_requires_the_exact_complete_check_identity_sequence(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    payload = _report(fingerprint="current")
    payload["requiredCheckIdentities"].append("security")
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_release_evidence(report_path, current_fingerprint="current").state == "unreadable"


    payload = _report(fingerprint="current")
    payload["checks"].reverse()
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_release_evidence(report_path, current_fingerprint="current").state == "unreadable"

    payload = _report(fingerprint="current")
    payload["immutableReleaseReference"] = "refs/tags/v1.2.0-rc.31"
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_release_evidence(report_path, current_fingerprint="current").state == "unreadable"


def test_release_report_cannot_select_its_own_smaller_successful_checklist(tmp_path: Path) -> None:
    report_path = tmp_path / "reduced.json"
    payload = _report(fingerprint="current")
    payload["requiredCheckIdentities"] = ["automated_test_suite"]
    payload["checks"] = [{"name": "automated_test_suite", "status": "pass", "durationMs": 1}]
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_release_evidence(report_path, current_fingerprint="current").state == "unreadable"
