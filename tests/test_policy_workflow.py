from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import event, text

from nicegui_app.access_context import AccessMode, PageContext, Principal, PrincipalExpiredError
from nicegui_app.services.operation_context import PageContextWorkflowAdapter
from nicegui_app.services.roster_workflow import RosterWorkflow
from nicegui_app.services.workflow_types import BackupResult, WorkflowMaintenanceError
from roster_core.policy_settings import PolicyCommandConflict, PolicyVersionConflict
from roster_policy.configurable import BusinessId, WeeklyPolicy, default_weekly_policy


def admin(workflow, *, expires_at=None):
    return PageContextWorkflowAdapter(workflow, PageContext.create(Principal(
        mode=AccessMode.ADMIN, subject="fictional-operator", session_id="fictional-session",
        expires_at=expires_at,
    )))


@pytest.fixture
def workflow(tmp_path):
    result = RosterWorkflow(database_path=tmp_path / "policy.sqlite3", backup_dir=tmp_path / "backups")
    result.bootstrap()
    return result


def custom(room="509"):
    return WeeklyPolicy(tuple(
        replace(post, room=room) if post.business is BusinessId.STUDY_ROOM else post
        for post in default_weekly_policy().businesses
    ))


def counts(workflow):
    with workflow._session() as session:
        return tuple(session.scalar(text(f"SELECT COUNT(*) FROM {table}")) for table in (
            "school_year_policy_revisions", "school_year_policy_current", "operation_commands",
            "backup_obligations",
        ))


def test_settings_save_reopen_reset_and_original_command_replay(workflow):
    ui = admin(workflow)
    first = ui.initialize_policy(2026, command_id="initialize")
    assert (first.policy_revision.revision, first.backup_status, first.replayed) == (1, "verified", False)
    saved = ui.save_policy(2026, custom(), expected_revision=1, command_id=" save ")
    assert saved.command_id == "save"
    assert saved.policy_revision.policy == custom()
    reopened = RosterWorkflow(database_path=workflow.database_path, backup_dir=workflow.backup_dir)
    reopened.bootstrap()
    other = admin(reopened)
    assert other.policy_current(2026) == saved.policy_revision
    preview = other.policy_reset_preview(2026)
    assert any(change.field == "room" for change in preview.changes)
    reset = other.reset_policy(preview, command_id="reset")
    assert reset.policy_revision.revision == 3
    assert reset.policy_revision.policy == default_weekly_policy()
    replay = other.save_policy(2026, custom(), expected_revision=1, command_id="save")
    assert replay.policy_revision == saved.policy_revision
    assert replay.replayed
    assert other.policy_current(2026) == reset.policy_revision
    assert other.reset_policy(preview, command_id="reset").policy_revision == reset.policy_revision
    assert other.policy_command_result(command_id="save").policy_revision == saved.policy_revision
    assert other.policy_command_result(command_id="unknown") is None
    assert counts(workflow) == (3, 1, 3, 3)


def test_committed_backup_failure_is_recoverable_without_new_policy_write(workflow, monkeypatch):
    ui = admin(workflow)
    create_backup = workflow._create_and_record_backup
    monkeypatch.setattr(workflow, "_create_and_record_backup", lambda *_: BackupResult(False, None, "fictional disk failure"))
    result = ui.initialize_policy(2026, command_id="first")
    assert result.backup_status == "pending"
    assert ui.policy_current(2026) == result.policy_revision
    assert ui.policy_command_result(command_id="first").backup_status == "pending"
    retry = ui.initialize_policy(2026, command_id="first")
    assert retry.replayed and retry.policy_revision == result.policy_revision
    assert retry.backup_status == "pending"
    with pytest.raises(WorkflowMaintenanceError, match="read-only"):
        ui.save_policy(2026, custom(), expected_revision=1, command_id="new-save")
    assert counts(workflow) == (1, 1, 1, 1)
    monkeypatch.setattr(workflow, "_create_and_record_backup", create_backup)
    repaired = ui.initialize_policy(2026, command_id="first")
    assert repaired.backup_status == "verified" and repaired.replayed
    assert ui.policy_command_result(command_id="first").backup_status == "verified"
    assert workflow.pending_backup_obligation_count() == 0
    assert counts(workflow) == (1, 1, 1, 1)


def test_policy_cas_and_command_conflicts_do_not_leave_partial_evidence(workflow):
    ui = admin(workflow)
    ui.initialize_policy(2026, command_id="first")
    ui.save_policy(2026, custom(), expected_revision=1, command_id="save")
    before = counts(workflow)
    with pytest.raises(PolicyVersionConflict):
        ui.save_policy(2026, custom("510"), expected_revision=1, command_id="stale")
    with pytest.raises(PolicyCommandConflict):
        ui.save_policy(2026, custom("510"), expected_revision=1, command_id="save")
    assert counts(workflow) == before


def test_policy_calls_require_live_administrative_identity(workflow):
    before = set(workflow.database_path.parent.iterdir())
    with pytest.raises(PermissionError):
        workflow.initialize_policy(2026, command_id="raw")
    assert set(workflow.database_path.parent.iterdir()) == before
    with pytest.raises(PermissionError):
        workflow.policy_current(2026)
    expired = admin(workflow, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    with pytest.raises(PrincipalExpiredError):
        expired.initialize_policy(2026, command_id="expired")


@pytest.mark.parametrize("failure_stage", ["audit", "receipt", "commit"])
def test_transaction_failure_rolls_back_the_entire_settings_command(workflow, monkeypatch, failure_stage):
    ui = admin(workflow)
    if failure_stage == "commit":
        from sqlalchemy.orm import Session

        def fail_commit(_session):
            raise RuntimeError("fictional pre-commit failure")

        event.listen(Session, "before_commit", fail_commit)
    else:
        method = "_audit" if failure_stage == "audit" else "_commit_operation_command"
        original = getattr(workflow, method)

        def fail_after_write(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError("fictional transactional failure")

        monkeypatch.setattr(workflow, method, fail_after_write)
    try:
        with pytest.raises(RuntimeError, match="fictional"):
            ui.initialize_policy(2026, command_id="failed")
    finally:
        if failure_stage == "commit":
            event.remove(Session, "before_commit", fail_commit)
    assert counts(workflow) == (0, 0, 0, 0)
    with workflow._session() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM audit_events WHERE event_type LIKE 'policy_%'")) == 0


def test_settings_reads_use_consistent_read_without_writer_lock(workflow):
    ui = admin(workflow)
    ui.initialize_policy(2026, command_id="init")
    statements = []

    def observe(_connection, _cursor, statement, *_args):
        statements.append(statement)

    engine = workflow.sessions.kw["bind"]
    event.listen(engine, "before_cursor_execute", observe)
    try:
        ui.policy_current(2026)
        ui.policy_revision(2026, 1)
        ui.policy_reset_preview(2026)
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    assert sum(statement == "BEGIN DEFERRED" for statement in statements) == 3
    assert not any("IMMEDIATE" in statement for statement in statements)
    assert not any(statement.startswith(("INSERT", "UPDATE", "DELETE")) for statement in statements)


def test_receipt_backup_verification_does_not_hold_a_live_database_connection(workflow, monkeypatch):
    ui = admin(workflow)
    ui.initialize_policy(2026, command_id="init")
    engine = workflow.sessions.kw["bind"]
    original = workflow.verify_backup
    calls = []

    def verify_without_live_reader(path):
        assert engine.pool.checkedout() == 0
        calls.append(path)
        return original(path)

    monkeypatch.setattr(workflow, "verify_backup", verify_without_live_reader)
    assert ui.policy_command_result(command_id="init").backup_status == "verified"
    assert len(calls) == 1


def test_concurrent_policy_writers_keep_one_new_revision(workflow):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    admin(workflow).initialize_policy(2026, command_id="init")
    barrier = Barrier(2)

    def write(index):
        barrier.wait(timeout=10)
        try:
            return admin(workflow).save_policy(2026, custom(str(508 + index)), expected_revision=1, command_id=f"save-{index}")
        except PolicyVersionConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, (1, 2)))
    assert sum(result is not None for result in results) == 1
    assert counts(workflow) == (2, 1, 2, 2)


def test_pending_backup_cannot_turn_different_intent_into_a_retry(workflow, monkeypatch):
    ui = admin(workflow)
    monkeypatch.setattr(workflow, "_create_and_record_backup", lambda *_: BackupResult(False, None, "offline"))
    ui.initialize_policy(2026, command_id="init")
    with pytest.raises(PolicyCommandConflict):
        ui.initialize_policy(2027, command_id="init")
    assert counts(workflow) == (1, 1, 1, 1)


def test_previously_verified_but_missing_snapshot_can_be_repaired(workflow, monkeypatch):
    ui = admin(workflow)
    ui.initialize_policy(2026, command_id="init")
    original = workflow.verify_backup
    with workflow._session() as session:
        previous = session.scalar(text("SELECT backup_path FROM backup_obligations WHERE command_id='init'"))
    # Simulate an unavailable recovery point without deleting any files.
    monkeypatch.setattr(workflow, "verify_backup", lambda path: {"valid": False} if str(path) == previous else original(path))
    assert ui.policy_command_result(command_id="init").backup_status == "pending"
    repaired = ui.initialize_policy(2026, command_id="init")
    assert repaired.backup_status == "verified"
    assert ui.policy_command_result(command_id="init").backup_status == "verified"
    assert counts(workflow) == (1, 1, 1, 1)


def test_actual_settings_restore_preserves_revision_history_and_operation_receipts(workflow):
    ui = admin(workflow)
    first = ui.initialize_policy(2026, command_id="init")
    saved = ui.save_policy(2026, custom(), expected_revision=1, command_id="save")
    with workflow._session() as session:
        snapshot = Path(session.scalar(text("SELECT backup_path FROM backup_obligations WHERE command_id='save'")))
        audit_before = session.execute(text(
            "SELECT event_type,command_id,actor_subject,actor_mode,metadata_json FROM audit_events "
            "WHERE event_type LIKE 'policy_%' ORDER BY id"
        )).all()
    ui.save_policy(2026, custom("510"), expected_revision=2, command_id="later")
    assert ui.policy_current(2026).revision == 3
    restored = ui.restore_backup(snapshot)
    assert restored["restoredFrom"] == snapshot
    assert ui.policy_current(2026) == saved.policy_revision
    assert ui.policy_revision(2026, 1) == first.policy_revision
    assert ui.policy_command_result(command_id="save").policy_revision == saved.policy_revision
    assert ui.policy_command_result(command_id="later") is None
    assert ui.save_policy(2026, custom(), expected_revision=1, command_id="save").replayed
    assert counts(workflow) == (2, 1, 2, 2)
    with workflow._session() as session:
        assert session.execute(text(
            "SELECT event_type,command_id,actor_subject,actor_mode,metadata_json FROM audit_events "
            "WHERE event_type LIKE 'policy_%' ORDER BY id"
        )).all() == audit_before


@pytest.mark.parametrize("receipt", [
    '{"year_start":2026,"revision":true}',
    '{"year_start":2026,"revision":2}',
    '{"year_start":2026,"revision":2,"revision":1}',
])
def test_unknown_or_malformed_policy_receipt_never_returns_latest_policy(workflow, receipt):
    from roster_core.policy_settings import PolicyStorageError

    ui = admin(workflow)
    ui.initialize_policy(2026, command_id="init")
    ui.save_policy(2026, custom(), expected_revision=1, command_id="save")
    with workflow._session() as session:
        session.execute(text("UPDATE operation_commands SET result_json=:receipt WHERE command_id='init'"),
                        {"receipt": receipt})
        session.commit()
    with pytest.raises(PolicyStorageError):
        ui.policy_command_result(command_id="init")
    with pytest.raises(PolicyStorageError):
        ui.initialize_policy(2026, command_id="init")
