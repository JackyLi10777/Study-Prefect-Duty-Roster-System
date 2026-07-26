from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from nicegui_app.access_context import AccessMode, Capability, CapabilityDeniedError, PageContext, Principal
from nicegui_app.services.support_incidents import (
    AttachmentInput,
    InboxLimits,
    IncidentReportInput,
    IncidentValidationError,
    SupportInbox,
    SupportStorageError,
    new_incident_id,
    sanitize_untrusted_text,
)


NOW = datetime(2026, 7, 26, 1, 2, 3, tzinfo=timezone.utc)


def report(**overrides: object) -> IncidentReportInput:
    values: dict[str, object] = {
        "source": "synthetic_test",
        "actor_mode": "synthetic",
        "route_category": "rosters",
        "workflow_action": "generate_draft",
        "expected_behavior": "A fictional draft should appear.",
        "actual_behavior": "A safe synthetic error appeared.",
        "reproduction_steps": ("Open the fictional roster.", "Generate a draft."),
        "impact": "Testing only.",
        "frequency": "once",
        "last_known_good": "v1.2.0-rc.21",
        "operation_references": ("OP-1234ABCD",),
        "request_references": ("REQ-89ABCDEF",),
        "safe_error_type": "SyntheticError",
        "safe_code_locations": ("support_incidents.py:create_incident",),
    }
    values.update(overrides)
    return IncidentReportInput(**values)  # type: ignore[arg-type]


def create(inbox: SupportInbox, **kwargs: object):
    return inbox.create_incident(
        report(**kwargs),
        application_version="v1.2.0-test",
        source_fingerprint="a" * 64,
        application_mode="test",
        environment={"platform": "windows", "python": "3.13"},
        health_summary={"ready": True, "backup": "ok"},
        events=({"timestamp_utc": "2026-07-26T01:02:03Z", "category": "workflow", "outcome": "failed"},),
        now=NOW,
    )


def test_incident_id_is_non_identifying_and_unique() -> None:
    identifiers = {new_incident_id(NOW) for _ in range(100)}
    assert len(identifiers) == 100
    assert all(value.startswith("INC-20260726-") and len(value) == 21 for value in identifiers)


def test_redaction_removes_credentials_email_user_path_and_query() -> None:
    cleaned, summary = sanitize_untrusted_text(
        "Authorization: Bearer abcdefghijklmnop\r\n"
        "email=user@example.com path=C:\\Users\\person\\secret.txt "
        "url=https://example.invalid/path?token=secret"
    )
    assert "abcdefghijklmnop" not in cleaned
    assert "user@example.com" not in cleaned
    assert "person" not in cleaned
    assert "token=secret" not in cleaned
    assert sum(summary.values()) >= 4


def test_create_validate_and_export_bundle(tmp_path: Path) -> None:
    inbox = SupportInbox(tmp_path / "support")
    summary = create(inbox)
    validated = inbox.validate_bundle(summary.incident_id)
    archive = inbox.export_bundle_bytes(summary.incident_id)

    assert validated.integrity_valid is True
    assert validated.error_fingerprint == summary.error_fingerprint
    assert archive.startswith(b"PK")
    manifest = json.loads((inbox.inbox / summary.incident_id / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert "status.jsonl" not in manifest["integrity_hashes"]


def test_allowed_text_json_and_png_attachments_are_sanitized(tmp_path: Path) -> None:
    inbox = SupportInbox(tmp_path / "support")
    attachments = (
        AttachmentInput("notes.txt", "text/plain", b"token=abcdefghijklmnop", "2026-07-26T01:00:00Z"),
        AttachmentInput("context.json", "application/json", b'{"email":"user@example.com"}', "2026-07-26T01:00:00Z"),
        AttachmentInput("screen.png", "image/png", b"\x89PNG\r\n\x1a\nfictional", "2026-07-26T01:00:00Z"),
    )
    summary = inbox.create_incident(
        report(),
        application_version="test",
        source_fingerprint="b" * 64,
        application_mode="test",
        attachments=attachments,
        now=NOW,
    )
    bundle = inbox.inbox / summary.incident_id
    assert "abcdefghijklmnop" not in (bundle / "attachments" / "attachment-01.txt").read_text(encoding="utf-8")
    assert "user@example.com" not in (bundle / "attachments" / "attachment-02.json").read_text(encoding="utf-8")
    assert (bundle / "attachments" / "attachment-03.png").read_bytes().startswith(b"\x89PNG")


@pytest.mark.parametrize(
    "attachment",
    (
        AttachmentInput("run.exe", "application/octet-stream", b"MZ", "2026-07-26T01:00:00Z"),
        AttachmentInput("fake.png", "image/png", b"not-a-png", "2026-07-26T01:00:00Z"),
        AttachmentInput("bad.txt", "text/plain", b"\xff", "2026-07-26T01:00:00Z"),
    ),
)
def test_unsafe_attachment_is_rejected(tmp_path: Path, attachment: AttachmentInput) -> None:
    with pytest.raises(IncidentValidationError):
        SupportInbox(tmp_path / "support").create_incident(
            report(),
            application_version="test",
            source_fingerprint="c" * 64,
            application_mode="test",
            attachments=(attachment,),
            now=NOW,
        )


def test_invalid_references_and_nul_are_rejected(tmp_path: Path) -> None:
    inbox = SupportInbox(tmp_path / "support")
    with pytest.raises(IncidentValidationError):
        create(inbox, operation_references=("OP-not-safe",))
    with pytest.raises(IncidentValidationError):
        create(inbox, actual_behavior="bad\x00value")


def test_concurrent_reports_have_distinct_atomic_bundles(tmp_path: Path) -> None:
    inbox = SupportInbox(
        tmp_path / "support",
        limits=InboxLimits(50 * 1024 * 1024, 50, 100, 1024),
    )
    with ThreadPoolExecutor(max_workers=8) as pool:
        summaries = list(pool.map(lambda _: create(inbox), range(16)))
    assert len({item.incident_id for item in summaries}) == 16
    assert len(list(inbox.inbox.glob("INC-*"))) == 16
    assert not list((inbox.root / "staging").iterdir())


def test_write_failure_leaves_no_partial_inbox_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inbox = SupportInbox(tmp_path / "support")
    original = inbox._write_file
    calls = 0

    def fail_after_first(path: Path, payload: bytes) -> None:
        nonlocal calls
        calls += 1
        if calls > 1:
            raise SupportStorageError("synthetic disk failure")
        original(path, payload)

    monkeypatch.setattr(inbox, "_write_file", fail_after_first)
    with pytest.raises(SupportStorageError):
        create(inbox)
    assert not list(inbox.inbox.iterdir())
    assert not list((inbox.root / "staging").iterdir())


def test_quota_failure_is_isolated_from_roster_capabilities(tmp_path: Path) -> None:
    inbox = SupportInbox(tmp_path / "support", limits=InboxLimits(1024, 1, 1, 1024))
    with pytest.raises((SupportStorageError, IncidentValidationError)):
        create(inbox)
    principal = Principal(
        mode=AccessMode.GUEST,
        subject="guest",
        session_id="session",
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )
    context = PageContext.create(principal)
    with pytest.raises(CapabilityDeniedError):
        context.require(Capability.PERSISTENT_WRITE)


def test_tampered_bundle_is_detected_and_quarantined(tmp_path: Path) -> None:
    inbox = SupportInbox(tmp_path / "support")
    summary = create(inbox)
    (inbox.inbox / summary.incident_id / "report.md").write_text("tampered", encoding="utf-8")
    with pytest.raises(IncidentValidationError):
        inbox.validate_bundle(summary.incident_id)
    destination = inbox.quarantine(summary.incident_id)
    assert destination.parent.name == "quarantined"
    assert not (inbox.inbox / summary.incident_id).exists()


def test_inspector_output_contains_no_report_or_secret(tmp_path: Path) -> None:
    inbox = SupportInbox(tmp_path / "support")
    summary = create(inbox, actual_behavior="password=verysecretvalue")
    result = subprocess.run(
        [
            "python",
            "-X",
            "utf8",
            "scripts/inspect_support_inbox.py",
            "--root",
            str(inbox.root),
            "--incident",
            summary.incident_id,
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0
    assert summary.incident_id in result.stdout
    assert "verysecretvalue" not in result.stdout
    assert "A safe synthetic error" not in result.stdout


def test_lifecycle_status_is_effective_and_moves_between_safe_buckets(tmp_path: Path) -> None:
    inbox = SupportInbox(tmp_path / "support")
    summary = create(inbox)
    inbox.append_status(summary.incident_id, status_value="triaged", note_code="review_started")
    assert (inbox.root / "triaged" / summary.incident_id).is_dir()
    assert inbox.validate_bundle(summary.incident_id).lifecycle_status == "triaged"

    inbox.append_status(summary.incident_id, status_value="closed", note_code="verified_complete")
    assert (inbox.root / "resolved" / summary.incident_id).is_dir()
    assert inbox.validate_bundle(summary.incident_id).lifecycle_status == "closed"


def test_unindexed_or_mismatched_attachment_is_rejected(tmp_path: Path) -> None:
    inbox = SupportInbox(tmp_path / "support")
    summary = inbox.create_incident(
        report(),
        application_version="test",
        source_fingerprint="d" * 64,
        application_mode="test",
        attachments=(
            AttachmentInput("notes.txt", "text/plain", b"safe", "2026-07-26T01:00:00Z"),
        ),
        now=NOW,
    )
    bundle = inbox.inbox / summary.incident_id
    (bundle / "attachments" / "not-indexed.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(IncidentValidationError):
        inbox.validate_bundle(summary.incident_id)


@pytest.mark.parametrize("relative", ("unexpected.txt", "evidence/unindexed.json"))
def test_unindexed_bundle_files_are_rejected(tmp_path: Path, relative: str) -> None:
    inbox = SupportInbox(tmp_path / "support")
    summary = create(inbox)
    bundle = inbox.inbox / summary.incident_id
    target = bundle / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("unexpected", encoding="utf-8")

    with pytest.raises(IncidentValidationError):
        inbox.validate_bundle(summary.incident_id)


def test_cleanup_only_removes_stale_staging_quarantine_and_closed_records(tmp_path: Path) -> None:
    inbox = SupportInbox(tmp_path / "support")
    active = create(inbox)
    resolved = create(inbox)
    inbox.append_status(resolved.incident_id, status_value="closed", note_code="complete")
    quarantined = create(inbox)
    inbox.quarantine(quarantined.incident_id)
    staging = inbox.root / "staging" / ".stale-synthetic"
    staging.mkdir()
    old_timestamp = NOW.timestamp() - (365 * 24 * 60 * 60)
    for path in (
        staging,
        inbox.root / "resolved" / resolved.incident_id,
        inbox.root / "quarantined" / quarantined.incident_id,
    ):
        os.utime(path, (old_timestamp, old_timestamp))

    removed = inbox.cleanup_expired(now=NOW)
    assert removed == {"staging": 1, "quarantined": 1, "resolved": 1}
    assert (inbox.inbox / active.incident_id).is_dir()


def test_cleanup_isolates_removal_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inbox = SupportInbox(tmp_path / "support")
    inbox.initialize()
    staging = inbox.root / "staging" / ".stale-synthetic"
    staging.mkdir()
    old_timestamp = NOW.timestamp() - (365 * 24 * 60 * 60)
    os.utime(staging, (old_timestamp, old_timestamp))

    def fail_remove(path: Path, *, ignore_errors: bool) -> None:
        raise OSError("synthetic cleanup failure")

    monkeypatch.setattr(shutil, "rmtree", fail_remove)
    assert inbox.cleanup_expired(now=NOW) == {"staging": 0, "quarantined": 0, "resolved": 0}
    assert staging.is_dir()


def test_cleanup_is_best_effort_when_storage_is_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inbox = SupportInbox(tmp_path / "support")

    def fail_initialize() -> None:
        raise OSError("storage unavailable")

    monkeypatch.setattr(inbox, "initialize", fail_initialize)

    assert inbox.cleanup_expired(now=NOW) == {"staging": 0, "quarantined": 0, "resolved": 0}
