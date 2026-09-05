from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import sqlite3

from alembic import command
import pytest

from nicegui_app.persistence.database import (
    _alembic_config, create_session_factory, current_migration_heads,
    database_readiness, required_database_tables,
    policy_storage_is_valid,
)
from nicegui_app.persistence.models import Base
from nicegui_app.services.operation_context import OperationActor, bind_operation_actor
from nicegui_app.services.roster_workflow import RosterWorkflow
from nicegui_app.services.transaction_policy_repository import TransactionPolicyRepository
from roster_core.policy_settings import PolicySettings
from roster_policy.configurable import default_weekly_policy
from roster_policy.policy_codec import encode_weekly_policy


TABLES = {"school_year_policy_revisions", "school_year_policy_current"}


def _document(room="407"):
    policy = default_weekly_policy()
    posts = list(policy.businesses)
    posts[1] = replace(posts[1], room=room)
    return encode_weekly_policy(replace(policy, businesses=posts))


def _seed_history(path):
    with sqlite3.connect(path) as connection:
        connection.executemany(
            "INSERT INTO school_year_policy_revisions VALUES (?, ?, ?)",
            [(2026, 1, _document()), (2026, 2, _document("509"))],
        )
        connection.execute("INSERT INTO school_year_policy_current VALUES (2026, 2)")


def _manifest(path):
    path.with_suffix(".manifest.json").write_text(
        json.dumps({"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}), encoding="utf-8",
    )


def test_current_schema_owns_policy_tables_and_empty_database_is_ready(tmp_path):
    path = tmp_path / "empty.sqlite3"
    sessions = create_session_factory(path)
    try:
        assert current_migration_heads() == {"0015"}
        assert TABLES <= Base.metadata.tables.keys()
        assert TABLES <= required_database_tables()
        assert "prelaunch_policy_commands" not in required_database_tables()
        assert database_readiness(path) == "ok"
        command.check(_alembic_config(path))
    finally:
        sessions.kw["bind"].dispose()


def test_0015_adds_empty_policy_tables_without_copying_rehearsal_data(tmp_path):
    path = tmp_path / "legacy-fixture.sqlite3"
    config = _alembic_config(path)
    command.upgrade(config, "0014")
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE prelaunch_policy_revisions (document TEXT)")
        connection.execute("INSERT INTO prelaunch_policy_revisions VALUES (?)", (_document("REHEARSAL"),))
        connection.execute(
            "INSERT INTO audit_events(event_type,metadata_json,occurred_at) VALUES ('legacy_fixture','{}','2026-09-07')"
        )
    command.upgrade(config, "head")
    assert database_readiness(path) == "ok"
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0015",)
        assert connection.execute("SELECT COUNT(*) FROM school_year_policy_revisions").fetchone() == (0,)
        assert connection.execute("SELECT COUNT(*) FROM school_year_policy_current").fetchone() == (0,)
        assert connection.execute("SELECT document FROM prelaunch_policy_revisions").fetchone() == (_document("REHEARSAL"),)
        assert connection.execute("SELECT event_type FROM audit_events").fetchone() == ("legacy_fixture",)
    command.downgrade(config, "0014")
    with sqlite3.connect(path) as connection:
        assert TABLES.isdisjoint(row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'"))
        assert connection.execute("SELECT event_type FROM audit_events").fetchone() == ("legacy_fixture",)


@pytest.mark.parametrize("corruption,expected", [
    ("missing_table", "schema_incomplete"),
    ("missing_target", "policy_invalid"),
    ("stale_pointer", "policy_invalid"),
    ("orphan_history", "policy_invalid"),
    ("orphan_pointer", "policy_invalid"),
    ("missing_first", "policy_invalid"),
    ("history_gap", "policy_invalid"),
    ("noninteger_year", "policy_invalid"),
    ("noninteger_revision", "policy_invalid"),
    ("invalid_document", "policy_invalid"),
    ("noncanonical_document", "policy_invalid"),
])
def test_readiness_and_backup_reject_invalid_policy_history(tmp_path, corruption, expected):
    path = tmp_path / "snapshot.sqlite3"
    command.upgrade(_alembic_config(path), "head")
    _seed_history(path)
    assert database_readiness(path) == "ok"
    with sqlite3.connect(path) as connection:
        if corruption == "missing_table":
            connection.execute("DROP TABLE school_year_policy_current")
        elif corruption == "missing_target":
            connection.execute("UPDATE school_year_policy_current SET revision=99")
        elif corruption == "stale_pointer":
            connection.execute("UPDATE school_year_policy_current SET revision=1")
        elif corruption == "orphan_history":
            connection.execute("DELETE FROM school_year_policy_current")
        elif corruption == "orphan_pointer":
            connection.execute("DELETE FROM school_year_policy_revisions")
        elif corruption == "missing_first":
            connection.execute("DELETE FROM school_year_policy_revisions WHERE revision=1")
        elif corruption == "history_gap":
            connection.execute("UPDATE school_year_policy_revisions SET revision=3 WHERE revision=2")
            connection.execute("UPDATE school_year_policy_current SET revision=3")
        elif corruption == "invalid_document":
            connection.execute("UPDATE school_year_policy_revisions SET document='{}' WHERE revision=1")
        elif corruption == "noninteger_year":
            connection.execute("PRAGMA ignore_check_constraints=ON")
            connection.execute("UPDATE school_year_policy_revisions SET year_start=2026.5")
        elif corruption == "noninteger_revision":
            connection.execute("PRAGMA ignore_check_constraints=ON")
            connection.execute("UPDATE school_year_policy_revisions SET revision=2.5 WHERE revision=2")
            connection.execute("UPDATE school_year_policy_current SET revision=2.5")
        else:
            connection.execute("UPDATE school_year_policy_revisions SET document=document || ' ' WHERE revision=1")
    _manifest(path)
    before = path.read_bytes()
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as connection:
        assert policy_storage_is_valid(connection) is False
    assert database_readiness(path) == expected
    workflow = RosterWorkflow(database_path=tmp_path / "unused.sqlite3", backup_dir=tmp_path)
    verification = workflow.verify_backup(path)
    assert verification["valid"] is False
    assert verification["reasonCode"] == expected
    assert path.read_bytes() == before


def test_0014_backup_keeps_its_historical_table_contract(tmp_path):
    path = tmp_path / "old-format.sqlite3"
    command.upgrade(_alembic_config(path), "0014")
    _manifest(path)
    workflow = RosterWorkflow(database_path=tmp_path / "unused.sqlite3", backup_dir=tmp_path)
    verification = workflow.verify_backup(path)
    assert verification["valid"] is True
    assert verification["schemaRevision"] == "0014"
    assert verification["migrationRequired"] is True


def test_readiness_pins_current_pointer_and_history_to_one_snapshot(tmp_path, monkeypatch):
    import nicegui_app.persistence.database as module

    path = tmp_path / "concurrent.sqlite3"
    sessions = create_session_factory(path)
    sessions.kw["bind"].dispose()
    _seed_history(path)
    original_connect = sqlite3.connect
    raced = False

    class ObservedConnection:
        def __init__(self, connection):
            self.connection = connection

        def execute(self, statement, *args):
            nonlocal raced
            if statement.startswith("SELECT year_start,revision,document") and not raced:
                raced = True
                with original_connect(path) as writer:
                    writer.execute("INSERT INTO school_year_policy_revisions VALUES (2026,3,?)", (_document("510"),))
                    writer.execute("UPDATE school_year_policy_current SET revision=3")
            return self.connection.execute(statement, *args)

        def close(self):
            self.connection.close()

    monkeypatch.setattr(module.sqlite3, "connect", lambda *args, **kwargs: ObservedConnection(original_connect(*args, **kwargs)))
    assert module.database_readiness(path) == "ok"
    assert raced
    with original_connect(path) as connection:
        assert connection.execute("SELECT revision FROM school_year_policy_current").fetchone() == (3,)


def test_verified_backup_restore_preserves_policy_history_and_operation_evidence(tmp_path):
    workflow = RosterWorkflow(database_path=tmp_path / "live.sqlite3", backup_dir=tmp_path / "backups")
    workflow.bootstrap()

    def policy_write(command_id, action):
        with workflow.maintenance.serialized_operation():
            with workflow._session() as session:
                workflow._begin_serialized_write(session)
                with bind_operation_actor(OperationActor("admin", "fictional-operator", "SCHEMA-TEST", command_id)):
                    result = action(PolicySettings(TransactionPolicyRepository(session, workflow)))
                session.commit()
            workflow._fulfill_backup_obligation(command_id)
        return result

    try:
        initial = policy_write("policy-init", lambda settings: settings.initialize(2026, command_id="policy-init"))
        policy = initial.policy
        posts = list(policy.businesses)
        posts[1] = replace(posts[1], room="509")
        custom = replace(policy, businesses=posts)
        saved = policy_write("policy-save", lambda settings: settings.save(2026, custom, expected_revision=1, command_id="policy-save"))
        snapshot = workflow.create_verified_backup()
        assert workflow.verify_backup(snapshot)["valid"] is True
        policy_write("policy-later", lambda settings: settings.save(2026, policy, expected_revision=2, command_id="policy-later"))
        workflow.restore_backup(snapshot)
        assert database_readiness(workflow.database_path) == "ok"
        with sqlite3.connect(workflow.database_path) as connection:
            assert connection.execute("SELECT revision FROM school_year_policy_current").fetchone() == (2,)
            assert connection.execute("SELECT revision,document FROM school_year_policy_revisions ORDER BY revision").fetchall() == [
                (1, encode_weekly_policy(initial.policy)), (2, encode_weekly_policy(saved.policy)),
            ]
            for table in ("operation_commands", "audit_events", "backup_obligations"):
                assert set(row[0] for row in connection.execute(f"SELECT command_id FROM {table} WHERE command_id LIKE 'policy-%'")) == {
                    "policy-init", "policy-save",
                }
            assert connection.execute("SELECT DISTINCT status FROM backup_obligations").fetchall() == [("completed",)]
    finally:
        workflow._dispose_database_connections()
