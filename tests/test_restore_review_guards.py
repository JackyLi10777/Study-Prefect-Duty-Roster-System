"""Reviewed restore intent, using isolated databases and fictional Guest data."""

from pathlib import Path

import pytest

from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.services.roster_workflow import RosterWorkflow, WorkflowError
from nicegui_app.services.workflow_types import WorkflowConflictError
from tests.test_guest_adapter import _adapter


@pytest.mark.parametrize("digest", [True, 12, "", "a" * 63, "G" * 64])
def test_admin_rejects_invalid_review_digest_before_maintenance(tmp_path, monkeypatch, digest):
    workflow = RosterWorkflow(database_path=tmp_path / "live.db", backup_dir=tmp_path / "backups",
                              seed_path=PREFECT_SEED_PATH)
    monkeypatch.setattr(workflow, "_stage_restore_source", lambda *_: pytest.fail("must not stage"))
    with pytest.raises(WorkflowError, match="checksum"):
        workflow.restore_backup(tmp_path / "backups/a.db", expected_sha256=digest)


def test_admin_review_digest_checked_against_staged_bytes_before_mutations(tmp_path, monkeypatch):
    workflow = RosterWorkflow(database_path=tmp_path / "live.db", backup_dir=tmp_path / "backups",
                              seed_path=PREFECT_SEED_PATH)
    workflow.bootstrap()
    source = workflow.create_verified_backup()
    digest = workflow.verify_backup(source)["sha256"]
    assert isinstance(digest, str)
    monkeypatch.setattr(workflow, "_prepare_restore_candidate", lambda *_args, **_kwargs: pytest.fail("must not prepare"))
    monkeypatch.setattr(workflow, "_create_and_record_backup", lambda *_args: pytest.fail("must not mutate"))
    with pytest.raises(WorkflowError, match="changed"):
        workflow.restore_backup(source, expected_sha256="0" * 64)
    assert not list(tmp_path.glob(".*.restore-source-*"))
    assert not workflow.maintenance_status().active


def test_admin_matching_review_digest_restores(tmp_path):
    workflow = RosterWorkflow(database_path=tmp_path / "live.db", backup_dir=tmp_path / "backups",
                              seed_path=PREFECT_SEED_PATH)
    workflow.bootstrap()
    source = workflow.create_verified_backup()
    result = workflow.restore_backup(source, expected_sha256=workflow.verify_backup(source)["sha256"])
    assert result["restoredFrom"] == source
    assert result["preRestoreBackup"].exists()


def test_admin_rejects_guest_revision_keyword(tmp_path):
    workflow = RosterWorkflow(database_path=tmp_path / "live.db", backup_dir=tmp_path / "backups",
                              seed_path=PREFECT_SEED_PATH)
    with pytest.raises(TypeError, match="expected_workspace_revision"):
        workflow.restore_backup(tmp_path / "backups/a.db", expected_workspace_revision=1)


def test_guest_review_is_memory_revision_not_simulated_sha():
    guest = _adapter()
    checkpoint = guest.create_verified_backup()
    review = guest.review_demo_backup(checkpoint)
    assert review["demo"] is True and type(review["workspaceRevision"]) is int
    assert "sha256" not in review
    assert guest.restore_backup(checkpoint, expected_workspace_revision=review["workspaceRevision"])["demo"] is True


@pytest.mark.parametrize("digest", [True, "a" * 64, "", 1])
def test_guest_rejects_any_file_checksum_without_reading_a_path(monkeypatch, digest):
    guest = _adapter()
    checkpoint = guest.create_verified_backup()
    monkeypatch.setattr(Path, "resolve", lambda *_args, **_kwargs: pytest.fail("Guest must not inspect paths"))
    monkeypatch.setattr(guest, "_commit", lambda *_args, **_kwargs: pytest.fail("must not commit"))
    with pytest.raises(WorkflowError, match="checksum"):
        guest.restore_backup(checkpoint, expected_sha256=digest)


@pytest.mark.parametrize("revision", [True, -1, 1.0, "1"])
def test_guest_rejects_invalid_review_revision(revision):
    guest = _adapter()
    checkpoint = guest.create_verified_backup()
    with pytest.raises(WorkflowError, match="revision"):
        guest.restore_backup(checkpoint, expected_workspace_revision=revision)


def test_guest_new_checkpoint_invalidates_review():
    guest = _adapter()
    checkpoint = guest.create_verified_backup()
    review = guest.review_demo_backup(checkpoint)
    guest.create_verified_backup()
    with pytest.raises(WorkflowConflictError, match="changed"):
        guest.restore_backup(checkpoint, expected_workspace_revision=review["workspaceRevision"])


def test_guest_reset_invalidates_review_and_legacy_restore_still_works():
    guest = _adapter()
    checkpoint = guest.create_verified_backup()
    review = guest.review_demo_backup(checkpoint)
    guest.reset_demo_fixture()
    with pytest.raises(WorkflowConflictError, match="changed"):
        guest.restore_backup(checkpoint, expected_workspace_revision=review["workspaceRevision"])
    assert guest.restore_backup(checkpoint, expected_sha256=None)["demo"] is True


def test_guest_missing_reviewed_checkpoint_never_falls_back():
    guest = _adapter()
    checkpoint = guest.create_verified_backup()
    view = guest._view()
    view.state.pop("demoBackupState")
    updated = guest._commit(view, view.state, "test-remove-checkpoint")
    with pytest.raises(WorkflowError, match="checkpoint"):
        guest.review_demo_backup(checkpoint)
    with pytest.raises(WorkflowError, match="checkpoint"):
        guest.restore_backup(checkpoint, expected_workspace_revision=updated.revision)


def test_guest_change_between_validation_and_commit_uses_existing_cas(monkeypatch):
    guest = _adapter()
    checkpoint = guest.create_verified_backup()
    review = guest.review_demo_backup(checkpoint)
    commit = guest._commit

    def concurrent_commit(view, state, operation, **kwargs):
        changed = guest._view()
        commit(changed, changed.state, "test-concurrent-update")
        return commit(view, state, operation, **kwargs)

    monkeypatch.setattr(guest, "_commit", concurrent_commit)
    with pytest.raises(WorkflowConflictError, match="changed"):
        guest.restore_backup(checkpoint, expected_workspace_revision=review["workspaceRevision"])
