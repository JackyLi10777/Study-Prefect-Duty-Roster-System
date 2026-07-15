from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from datetime import date
import json
import os
from pathlib import Path
import sqlite3
from threading import Event, Lock
from time import sleep
from zipfile import ZipFile

import pytest

from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.services.roster_workflow import CommittedWriteBackupError, RosterWorkflow, WorkflowError


WEEK_START = date(2026, 9, 7)


def _roster_version_in_snapshot(snapshot_path: Path, roster_week_id: int) -> int:
    connection = sqlite3.connect(snapshot_path)
    try:
        row = connection.execute(
            "SELECT version FROM roster_weeks WHERE id = ?",
            (roster_week_id,),
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    return int(row[0])


def test_concurrent_workflows_return_the_recovery_point_for_their_own_commit(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "live.sqlite3"
    backup_dir = tmp_path / "backups"
    first_workflow = RosterWorkflow(
        database_path=database_path,
        backup_dir=backup_dir,
        seed_path=PREFECT_SEED_PATH,
    )
    second_workflow = RosterWorkflow(
        database_path=database_path,
        backup_dir=backup_dir,
        seed_path=PREFECT_SEED_PATH,
    )
    first_workflow.bootstrap()
    second_workflow.bootstrap()
    first_backup_started = Event()
    release_first_backup = Event()
    original_create_backup = first_workflow._create_and_record_backup

    def delay_first_backup(event_type: str, roster_week_id: int | None):  # type: ignore[no-untyped-def]
        if event_type == "draft_generated":
            first_backup_started.set()
            assert release_first_backup.wait(timeout=5)
        return original_create_backup(event_type, roster_week_id)

    monkeypatch.setattr(first_workflow, "_create_and_record_backup", delay_first_backup)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_write = executor.submit(first_workflow.generate_and_save_draft, WEEK_START)
        assert first_backup_started.wait(timeout=5)
        second_write = executor.submit(second_workflow.generate_and_save_draft, WEEK_START)
        sleep(0.15)
        assert not second_write.done(), "the later commit crossed the first commit-to-snapshot fence"
        release_first_backup.set()
        first_result = first_write.result(timeout=10)
        second_result = second_write.result(timeout=10)

    assert first_result.version == 1
    assert second_result.version == 2
    assert _roster_version_in_snapshot(first_result.backup_path, first_result.id) == first_result.version
    assert _roster_version_in_snapshot(second_result.backup_path, second_result.id) == second_result.version


def test_restore_waits_for_an_in_progress_verified_backup(monkeypatch, tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    restore_source = workflow.generate_and_save_draft(WEEK_START).backup_path
    backup_verification_started = Event()
    release_backup_verification = Event()
    original_sha256 = workflow._sha256
    should_block = True

    def blocking_sha256(path: Path) -> str:
        nonlocal should_block
        if should_block:
            should_block = False
            backup_verification_started.set()
            assert release_backup_verification.wait(timeout=5)
        return original_sha256(path)

    monkeypatch.setattr(workflow, "_sha256", blocking_sha256)

    with ThreadPoolExecutor(max_workers=2) as executor:
        backup = executor.submit(workflow.create_verified_backup)
        assert backup_verification_started.wait(timeout=5)
        restore = executor.submit(workflow.restore_backup, restore_source)
        sleep(0.15)
        assert not restore.done(), "restore entered maintenance while a verified snapshot was still being built"
        release_backup_verification.set()
        assert backup.result(timeout=10).exists()
        restore_result = restore.result(timeout=15)

    assert restore_result["restoredFrom"] == restore_source
    assert workflow.verify_backup(restore_result["restoredBackup"])["valid"] is True


def test_publish_backup_failure_is_reported_as_committed_and_cannot_post_fairness_twice(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(WEEK_START)
    before = workflow.prefect_loads()
    blocked_backup_path = tmp_path / "blocked-backup-path"
    blocked_backup_path.write_text("not a directory", encoding="utf-8")
    workflow.backup_dir = blocked_backup_path

    with pytest.raises(CommittedWriteBackupError) as captured:
        workflow.publish(draft.id, expected_week_version=draft.version)

    after = workflow.prefect_loads()
    assert captured.value.event_type == "roster_published"
    assert workflow.roster_week(draft.id)["status"] == "published"
    assert sum(after.values()) - sum(before.values()) == pytest.approx(34.0)
    with pytest.raises(WorkflowError, match="already published"):
        workflow.publish(draft.id, expected_week_version=draft.version)
    assert workflow.prefect_loads() == after

    workflow.backup_dir = tmp_path / "recovered-backups"
    recovery_snapshot = workflow.create_verified_backup()

    assert recovery_snapshot.exists()
    assert workflow.verify_backup(recovery_snapshot)["valid"] is True
    assert workflow.roster_week(draft.id)["status"] == "published"
    assert workflow.prefect_loads() == after


def test_backup_evidence_failure_cannot_hide_a_committed_publish(monkeypatch, tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(WEEK_START)
    before = workflow.prefect_loads()

    def fail_to_record_backup(*_args, **_kwargs) -> None:
        raise sqlite3.OperationalError("simulated evidence write failure")

    monkeypatch.setattr(workflow, "_record_backup_result", fail_to_record_backup)
    with pytest.raises(CommittedWriteBackupError) as captured:
        workflow.publish(draft.id, expected_week_version=draft.version)

    after = workflow.prefect_loads()
    assert captured.value.event_type == "roster_published"
    assert captured.value.error_message == "Backup evidence recording failed: OperationalError"
    assert workflow.roster_week(draft.id)["status"] == "published"
    assert sum(after.values()) - sum(before.values()) == pytest.approx(34.0)
    assert any(path.name.endswith("-roster_published.sqlite3") for path in workflow.backup_dir.glob("*.sqlite3"))

def test_automatic_backup_is_verified_and_can_bootstrap_a_fresh_workflow(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()

    draft = workflow.generate_and_save_draft(WEEK_START)

    verification = workflow.verify_backup(draft.backup_path)
    manifest = json.loads(draft.backup_path.with_suffix(".manifest.json").read_text(encoding="utf-8"))
    recovered = RosterWorkflow(
        database_path=draft.backup_path,
        backup_dir=tmp_path / "recovered-backups",
    )
    recovered.bootstrap()

    assert verification["valid"] is True
    assert verification["integrity"] == "ok"
    assert manifest["sha256"] == verification["sha256"]
    assert recovered.roster_week(draft.id)["status"] == "draft"
    assert len(recovered.assignments(draft.id)) == draft.assignment_count


def test_backup_verification_rejects_a_tampered_manifest_checksum(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(WEEK_START)
    manifest_path = draft.backup_path.with_suffix(".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    verification = workflow.verify_backup(draft.backup_path)

    assert verification["valid"] is False
    assert verification["reasonCode"] == "checksum_mismatch"
    assert "checksum" in verification["error"].lower()


def test_backup_inventory_counts_safe_invalid_reason_codes(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    first = workflow.generate_and_save_draft(WEEK_START).backup_path
    second = workflow.create_verified_backup()
    third = workflow.create_verified_backup()

    first_manifest = first.with_suffix(".manifest.json")
    tampered = json.loads(first_manifest.read_text(encoding="utf-8"))
    tampered["sha256"] = "0" * 64
    first_manifest.write_text(json.dumps(tampered), encoding="utf-8")
    second.with_suffix(".manifest.json").unlink()

    inventory = workflow.backup_inventory()

    assert inventory["checkedCount"] == 3
    assert inventory["verifiedCount"] == 1
    assert inventory["invalidCount"] == 2
    assert inventory["invalidReasonCounts"] == {
        "checksum_mismatch": 1,
        "manifest_missing": 1,
    }
    assert workflow.verify_backup(third)["reasonCode"] == "verified"


def test_backup_listing_verifies_concurrently_and_preserves_recency_order(monkeypatch, tmp_path) -> None:
    workflow = RosterWorkflow(database_path=tmp_path / "live.sqlite3", backup_dir=tmp_path / "backups")
    workflow.backup_dir.mkdir(parents=True)
    snapshots = []
    for index in range(6):
        snapshot = workflow.backup_dir / f"snapshot-{index}.sqlite3"
        snapshot.write_bytes(b"fixture")
        os.utime(snapshot, (1_700_000_000 + index, 1_700_000_000 + index))
        snapshots.append(snapshot)

    lock = Lock()
    active = 0
    maximum_active = 0

    def verify(path: Path) -> dict[str, object]:
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        sleep(0.03)
        with lock:
            active -= 1
        return {"valid": True, "reasonCode": "verified", "pathName": path.name}

    monkeypatch.setattr(workflow, "verify_backup", verify)
    listed = workflow.backups()

    assert maximum_active >= 2
    assert [item["path"] for item in listed] == list(reversed(snapshots))
    assert [item["verification"]["pathName"] for item in listed] == [path.name for path in reversed(snapshots)]


def test_backup_listing_skips_a_file_that_disappears_during_candidate_scan(monkeypatch, tmp_path) -> None:
    workflow = RosterWorkflow(database_path=tmp_path / "live.sqlite3", backup_dir=tmp_path / "backups")
    workflow.backup_dir.mkdir(parents=True)
    stable = workflow.backup_dir / "stable.sqlite3"
    disappearing = workflow.backup_dir / "disappearing.sqlite3"
    stable.write_bytes(b"stable")
    disappearing.write_bytes(b"gone")
    original_stat = Path.stat

    def guarded_stat(path: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
        if path == disappearing:
            raise FileNotFoundError(path)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", guarded_stat)
    monkeypatch.setattr(workflow, "verify_backup", lambda _path: {"valid": True, "reasonCode": "verified"})

    listed = workflow.backups()

    assert [item["path"] for item in listed] == [stable]


def test_backup_verification_contains_a_file_removed_before_checksum(monkeypatch, tmp_path) -> None:
    workflow = RosterWorkflow(database_path=tmp_path / "live.sqlite3", backup_dir=tmp_path / "backups")
    workflow.bootstrap()
    snapshot = workflow.create_verified_backup()

    def missing_checksum_file(_path: Path) -> str:
        raise FileNotFoundError("simulated removal before checksum")

    monkeypatch.setattr(workflow, "_sha256", missing_checksum_file)

    verification = workflow.verify_backup(snapshot)

    assert verification["valid"] is False
    assert verification["reasonCode"] == "missing_file"
    assert "checksum" in verification["error"].lower()


def test_verified_handover_package_contains_only_a_verified_snapshot_and_manifest(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(WEEK_START)

    package = workflow.build_verified_handover_package()

    with ZipFile(BytesIO(package.content)) as archive:
        assert set(archive.namelist()) == {
            draft.backup_path.name,
            draft.backup_path.with_suffix(".manifest.json").name,
            "README.txt",
        }
        manifest = json.loads(archive.read(draft.backup_path.with_suffix(".manifest.json").name))
    assert package.filename.endswith(".zip")
    assert package.source_backup_path == draft.backup_path
    assert manifest["sha256"] == workflow.verify_backup(draft.backup_path)["sha256"]


def test_handover_package_stops_verifying_after_the_latest_valid_snapshot(monkeypatch, tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    workflow.backup_dir.mkdir(parents=True)
    oldest = workflow.backup_dir / "oldest.sqlite3"
    selected = workflow.backup_dir / "selected.sqlite3"
    newest = workflow.backup_dir / "newest.sqlite3"
    for index, snapshot in enumerate((oldest, selected, newest)):
        snapshot.write_bytes(b"fixture")
        snapshot.with_suffix(".manifest.json").write_text("{}", encoding="utf-8")
        os.utime(snapshot, (1_700_000_000 + index, 1_700_000_000 + index))

    verified_paths: list[Path] = []

    def verify(path: Path) -> dict[str, object]:
        verified_paths.append(path)
        return {"valid": path != newest, "reasonCode": "verified" if path != newest else "checksum_mismatch"}

    monkeypatch.setattr(workflow, "verify_backup", verify)

    package = workflow.build_verified_handover_package()

    assert package.source_backup_path == selected
    assert verified_paths == [newest, selected, selected]
    assert oldest not in verified_paths


def test_handover_package_requires_a_verified_snapshot(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    workflow.bootstrap()

    with pytest.raises(WorkflowError, match="No verified backup"):
        workflow.build_verified_handover_package()
