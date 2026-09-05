from __future__ import annotations

from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime
import json
from threading import Barrier

import pytest
from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.exc import PendingRollbackError
from sqlalchemy.orm import Session

from nicegui_app.persistence.models import AuditEventRecord, BackupObligationRecord, Base, OperationCommandRecord
from nicegui_app.services.operation_context import OperationActor, bind_operation_actor
from nicegui_app.services.sqlite_policy_repository import create_policy_revision_schema
from nicegui_app.services.transaction_policy_repository import TransactionPolicyRepository
from nicegui_app.services.workflow_parts.persistence import PersistenceWorkflowMixin
from roster_core.policy_settings import (
    PolicyCommandConflict, PolicySettings, PolicySettingsError, PolicyStorageError, PolicyVersionConflict,
)
from roster_policy.configurable import BusinessId, WeeklyPolicy, default_weekly_policy


class Helpers(PersistenceWorkflowMixin):
    @staticmethod
    def _now():
        return datetime(2026, 9, 7, 12)


@pytest.fixture
def storage(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'caller-transaction.sqlite3'}")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    with engine.begin() as connection:
        Base.metadata.create_all(connection)
        create_policy_revision_schema(connection)
    try:
        yield engine, Helpers()
    finally:
        engine.dispose()


@contextmanager
def actor(command):
    with bind_operation_actor(OperationActor("admin", "fictional-operator", "POLICY-TEST", command)):
        yield


def custom_policy(room="509"):
    return WeeklyPolicy(tuple(
        replace(post, room=room) if post.business is BusinessId.STUDY_ROOM else post
        for post in default_weekly_policy().businesses
    ))


def run_command(storage, command, action):
    """The test caller owns admission and the entire transaction lifetime."""
    engine, helpers = storage
    with Session(engine) as session:
        helpers._begin_serialized_write(session)
        settings = PolicySettings(TransactionPolicyRepository(session, helpers))
        try:
            with actor(command):
                result = action(settings)
            session.commit()
            return result
        except Exception:
            session.rollback()
            raise


def counts(engine):
    with engine.connect() as connection:
        return tuple(connection.scalar(text(f"SELECT COUNT(*) FROM {table}")) for table in (
            "school_year_policy_revisions", "school_year_policy_current", "operation_commands",
            "audit_events", "backup_obligations",
        ))


def test_policy_and_existing_operation_evidence_share_the_callers_transaction(storage):
    engine, helpers = storage
    with Session(engine) as session:
        helpers._begin_serialized_write(session)
        settings = PolicySettings(TransactionPolicyRepository(session, helpers))
        with actor("initialize"):
            result = settings.initialize(2026, command_id="initialize")
        assert result.revision == 1
        assert session.in_transaction()
        with engine.connect() as observer:
            assert observer.scalar(text("SELECT COUNT(*) FROM school_year_policy_revisions")) == 0
            assert observer.scalar(text("SELECT COUNT(*) FROM operation_commands")) == 0
        session.commit()
    with Session(engine) as session:
        receipt = session.scalars(select(OperationCommandRecord)).one()
        audit = session.scalars(select(AuditEventRecord)).one()
        obligation = session.scalars(select(BackupObligationRecord)).one()
        assert json.loads(receipt.result_json) == {"year_start": 2026, "revision": 1}
        assert receipt.operation_type == audit.event_type == obligation.operation_type == "policy_initialized"
        assert receipt.command_id == audit.command_id == obligation.command_id == "initialize"
        assert (audit.actor_subject, audit.actor_mode, audit.request_reference) == ("fictional-operator", "admin", "POLICY-TEST")
        assert obligation.status == "pending"
    assert "prelaunch_policy_commands" not in inspect(engine).get_table_names()


def test_raw_actor_command_cannot_disagree_with_canonical_receipt(storage):
    engine, helpers = storage
    with Session(engine) as session:
        helpers._begin_serialized_write(session)
        settings = PolicySettings(TransactionPolicyRepository(session, helpers))
        with actor(" initialize "), pytest.raises(PolicySettingsError):
            settings.initialize(2026, command_id=" initialize ")
        session.rollback()
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM operation_commands")) == 0


def test_transaction_adapter_rejects_disabled_foreign_keys_without_enabling_them(storage):
    engine, helpers = storage
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
        with Session(bind=connection) as session:
            helpers._begin_serialized_write(session)
            with pytest.raises(PolicyStorageError, match="foreign"):
                TransactionPolicyRepository(session, helpers)
            assert connection.scalar(text("PRAGMA foreign_keys")) == 0
            session.rollback()


def test_all_three_operations_replay_immutable_versions_after_later_edits(storage):
    original = run_command(storage, "init", lambda settings: settings.initialize(2026, command_id="init"))
    saved = run_command(storage, "save", lambda settings: settings.save(
        2026, custom_policy(), expected_revision=1, command_id="save",
    ))
    preview = run_command(storage, "preview", lambda settings: settings.preview_reset(2026))
    assert preview.expected_revision == 2
    assert counts(storage[0]) == (2, 1, 2, 2, 2)
    restored = run_command(storage, "reset", lambda settings: settings.reset(preview, command_id="reset"))
    latest = run_command(storage, "later", lambda settings: settings.save(
        2026, custom_policy("600"), expected_revision=3, command_id="later",
    ))
    # A new Session/Adapter each time also proves receipts survive reopening.
    assert run_command(storage, "init", lambda settings: settings.initialize(2026, command_id="init")) == original
    assert run_command(storage, "save", lambda settings: settings.save(
        2026, custom_policy(), expected_revision=1, command_id="save",
    )) == saved
    assert run_command(storage, "reset", lambda settings: settings.reset(preview, command_id="reset")) == restored
    assert run_command(storage, "read", lambda settings: settings.current(2026)) == latest
    assert counts(storage[0]) == (4, 1, 4, 4, 4)
    with Session(storage[0]) as session:
        assert {row.status for row in session.scalars(select(BackupObligationRecord))} == {"pending"}


@pytest.mark.parametrize("difference", ["policy", "year", "revision", "operation"])
def test_shared_operation_receipt_rejects_changed_policy_intent(storage, difference):
    run_command(storage, "init", lambda settings: settings.initialize(2026, command_id="init"))
    preview = run_command(storage, "preview", lambda settings: settings.preview_reset(2026))
    run_command(storage, "save", lambda settings: settings.save(
        2026, default_weekly_policy(), expected_revision=1, command_id="save",
    ))
    with pytest.raises(PolicyCommandConflict):
        if difference == "operation":
            run_command(storage, "save", lambda settings: settings.reset(preview, command_id="save"))
        else:
            run_command(storage, "save", lambda settings: settings.save(
                2027 if difference == "year" else 2026,
                custom_policy() if difference == "policy" else default_weekly_policy(),
                expected_revision=2 if difference == "revision" else 1, command_id="save",
            ))
    assert counts(storage[0]) == (2, 1, 2, 2, 2)


def test_stale_cas_rolls_back_pending_claim_and_cannot_reuse_failed_adapter(storage):
    engine, helpers = storage
    run_command(storage, "init", lambda settings: settings.initialize(2026, command_id="init"))
    latest = run_command(storage, "save", lambda settings: settings.save(
        2026, custom_policy(), expected_revision=1, command_id="save",
    ))
    with Session(engine) as session:
        helpers._begin_serialized_write(session)
        repository = TransactionPolicyRepository(session, helpers)
        with actor("stale"), pytest.raises(PolicyVersionConflict):
            PolicySettings(repository).save(2026, custom_policy("600"), expected_revision=1, command_id="stale")
        with pytest.raises(PolicyStorageError, match="rollback"):
            repository.read(2026)
        assert session.in_transaction()  # Adapter never rolls back for its caller.
        session.rollback()
    assert counts(engine) == (2, 1, 2, 2, 2)
    assert run_command(storage, "read", lambda settings: settings.current(2026)) == latest
    assert run_command(storage, "stale", lambda settings: settings.save(
        2026, custom_policy("600"), expected_revision=2, command_id="stale",
    )).revision == 3


@pytest.mark.parametrize("bound_actor", [
    None,
    OperationActor("guest", "fictional", "TEST", "init"),
    OperationActor("public", "fictional", "TEST", "init"),
    OperationActor("viewer", "fictional", "TEST", "init"),
    OperationActor("admin", "fictional", "TEST", "other"),
    OperationActor("admin", "fictional", "TEST", None),
])
def test_writes_require_bound_administrative_actor_with_the_same_command(storage, bound_actor):
    engine, helpers = storage
    with Session(engine) as session:
        helpers._begin_serialized_write(session)
        settings = PolicySettings(TransactionPolicyRepository(session, helpers))
        with bind_operation_actor(bound_actor), pytest.raises(PolicySettingsError):
            settings.initialize(2026, command_id="init")
        session.rollback()
    assert counts(engine) == (0, 0, 0, 0, 0)


@pytest.mark.parametrize("mode", ["admin", "local_maintenance"])
def test_canonical_actor_and_whitespace_input_produce_one_canonical_receipt(storage, mode):
    engine, helpers = storage
    with Session(engine) as session:
        helpers._begin_serialized_write(session)
        settings = PolicySettings(TransactionPolicyRepository(session, helpers))
        with bind_operation_actor(OperationActor(mode, "fictional", "TEST", "init")):
            settings.initialize(2026, command_id=" init\t")
        session.commit()
    with Session(engine) as session:
        audit = session.scalars(select(AuditEventRecord)).one()
        assert (audit.actor_mode, audit.command_id) == (mode, "init")
        assert session.scalars(select(OperationCommandRecord)).one().command_id == "init"


@pytest.mark.parametrize("setup", ["none", "autobegin", "logical-begin"])
def test_constructor_does_not_turn_a_logical_transaction_into_a_real_one(storage, setup):
    engine, helpers = storage
    with Session(engine) as session:
        if setup == "autobegin":
            session.execute(text("SELECT 1"))
        elif setup == "logical-begin":
            session.begin()
        with pytest.raises(PolicyStorageError):
            TransactionPolicyRepository(session, helpers)
        if setup != "none":
            assert not session.connection().connection.driver_connection.in_transaction
        session.rollback()
    assert counts(engine) == (0, 0, 0, 0, 0)


@pytest.mark.parametrize("finish", ["commit", "rollback", "close", "new-transaction", "nested"])
def test_adapter_cannot_escape_original_transaction_lifetime(storage, finish):
    engine, helpers = storage
    with Session(engine) as session:
        helpers._begin_serialized_write(session)
        repository = TransactionPolicyRepository(session, helpers)
        if finish == "new-transaction":
            session.rollback()
            helpers._begin_serialized_write(session)
        elif finish == "nested":
            session.begin_nested()
        else:
            getattr(session, finish)()
        with pytest.raises(PolicyStorageError):
            repository.read(2026)
        with actor("init"), pytest.raises(PolicyStorageError):
            PolicySettings(repository).initialize(2026, command_id="init")
        session.rollback()
    assert counts(engine) == (0, 0, 0, 0, 0)


def test_failed_read_cannot_be_reused_after_leaving_nested_transaction(storage):
    engine, helpers = storage
    with Session(engine) as session:
        helpers._begin_serialized_write(session)
        repository = TransactionPolicyRepository(session, helpers)
        nested = session.begin_nested()
        with pytest.raises(PolicyStorageError):
            repository.read(2026)
        nested.rollback()
        with pytest.raises(PolicyStorageError):
            repository.read(2026)
        session.rollback()


@pytest.mark.parametrize("failure_point", ["policy", "audit", "obligation"])
def test_caller_rollback_removes_every_partial_state_and_releases_command(storage, monkeypatch, failure_point):
    engine, helpers = storage
    original = run_command(storage, "init", lambda settings: settings.initialize(2026, command_id="init"))
    method = "_commit_operation_command" if failure_point == "obligation" else "_audit"
    real_method = getattr(helpers, method)

    def fail(*args, **kwargs):
        if failure_point != "policy":
            real_method(*args, **kwargs)
            args[0].flush()
        raise RuntimeError("injected interruption after " + failure_point)

    with monkeypatch.context() as patch:
        patch.setattr(helpers, method, fail)
        with Session(engine) as session:
            helpers._begin_serialized_write(session)
            repository = TransactionPolicyRepository(session, helpers)
            with actor("save"), pytest.raises(RuntimeError, match="injected interruption"):
                PolicySettings(repository).save(2026, custom_policy(), expected_revision=1, command_id="save")
            assert session.in_transaction()
            with pytest.raises(PolicyStorageError):
                repository.read(2026)
            session.rollback()
    assert counts(engine) == (1, 1, 1, 1, 1)
    assert run_command(storage, "read", lambda settings: settings.current(2026)) == original
    assert run_command(storage, "save", lambda settings: settings.save(
        2026, custom_policy(), expected_revision=1, command_id="save",
    )).revision == 2


def test_real_integrity_failure_leaves_session_rollback_only_and_no_partial_commit(storage, monkeypatch):
    engine, helpers = storage
    real_commit = helpers._commit_operation_command

    def duplicate_obligation(session, **kwargs):
        real_commit(session, **kwargs)
        # The table's UNIQUE command_id constraint fails during the Adapter's
        # real ORM flush, after policy rows and the operation claim exist.
        session.add(BackupObligationRecord(
            command_id=kwargs["record"].command_id, operation_type="policy_initialized",
            status="pending", created_at=helpers._now(),
        ))

    with monkeypatch.context() as patch:
        patch.setattr(helpers, "_commit_operation_command", duplicate_obligation)
        with Session(engine) as session:
            helpers._begin_serialized_write(session)
            settings = PolicySettings(TransactionPolicyRepository(session, helpers))
            with actor("init"), pytest.raises(PolicyStorageError):
                settings.initialize(2026, command_id="init")
            with pytest.raises(PendingRollbackError):
                session.commit()
            session.rollback()
    assert counts(engine) == (0, 0, 0, 0, 0)
    assert run_command(storage, "init", lambda settings: settings.initialize(2026, command_id="init")).revision == 1


@pytest.mark.parametrize("receipt", [
    {"year_start": True, "revision": 1}, {"year_start": 2026, "revision": True},
    {"year_start": 2027, "revision": 1}, {"year_start": 2026, "revision": 2},
    {"year_start": 2026, "revision": 1, "unexpected": "field"},
])
def test_corrupt_operation_receipt_cannot_replay_another_policy_revision(storage, receipt):
    engine, _ = storage
    run_command(storage, "init", lambda settings: settings.initialize(2026, command_id="init"))
    with engine.begin() as connection:
        connection.execute(text("UPDATE operation_commands SET result_json=:receipt"), {"receipt": json.dumps(receipt)})
    with pytest.raises(PolicyStorageError):
        run_command(storage, "init", lambda settings: settings.initialize(2026, command_id="init"))
    assert counts(engine) == (1, 1, 1, 1, 1)


def test_concurrent_callers_with_one_expected_revision_commit_one_complete_operation(storage):
    run_command(storage, "init", lambda settings: settings.initialize(2026, command_id="init"))
    barrier = Barrier(2)

    def save(index):
        barrier.wait(timeout=5)
        command = f"save-{index}"
        try:
            return run_command(storage, command, lambda settings: settings.save(
                2026, custom_policy(str(600 + index)), expected_revision=1, command_id=command,
            ))
        except PolicyVersionConflict as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(save, (1, 2)))
    assert sum(isinstance(result, PolicyVersionConflict) for result in results) == 1
    assert next(result for result in results if not isinstance(result, PolicyVersionConflict)).revision == 2
    assert counts(storage[0]) == (2, 1, 2, 2, 2)
