import hashlib
import json
import sqlite3

from alembic import command
import pytest

from nicegui_app.persistence.database import _alembic_config, database_readiness
from nicegui_app.persistence.dated_drafts import dated_drafts_are_valid
from nicegui_app.services.roster_workflow import RosterWorkflow
from tests.test_policy_workflow import admin, workflow
from tests.test_dated_weekly_draft import MONDAY


@pytest.mark.parametrize("corruption", ["document", "policy", "pointer", "orphan", "gap", "command", "date"])
def test_readiness_and_backup_reject_invalid_draft_snapshot(workflow, corruption, tmp_path):
    operator = admin(workflow)
    operator.initialize_policy(2026, command_id="init")
    created = operator.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    snapshot_path = workflow.create_verified_backup()
    # Corrupt a copied rehearsal artifact only, never a real/active database.
    damaged = tmp_path / "fictional-corrupt.sqlite3"
    import shutil
    shutil.copy2(snapshot_path, damaged)
    with sqlite3.connect(damaged) as connection:
        if corruption == "document":
            connection.execute("UPDATE dated_draft_revisions SET document='{}'")
        elif corruption == "policy":
            connection.execute("UPDATE dated_draft_revisions SET policy_revision=99")
        elif corruption == "pointer":
            connection.execute("UPDATE dated_draft_current SET version=99")
        elif corruption == "orphan":
            connection.execute("DELETE FROM dated_draft_current")
        elif corruption == "gap":
            connection.execute("UPDATE dated_draft_revisions SET version=2")
            connection.execute("UPDATE dated_draft_current SET version=2")
        elif corruption == "command":
            connection.execute("UPDATE dated_draft_revisions SET command_id='missing'")
        else:
            connection.execute("UPDATE dated_draft_current SET week_start='2026-09-08'")
    damaged.with_suffix(".manifest.json").write_text(json.dumps({"sha256": hashlib.sha256(damaged.read_bytes()).hexdigest()}), encoding="utf-8")
    before = damaged.read_bytes()
    assert database_readiness(damaged) == "dated_draft_invalid"
    result = workflow.verify_backup(damaged)
    assert result["valid"] is False and result["reasonCode"] == "dated_draft_invalid"
    assert damaged.read_bytes() == before
    assert operator.dated_draft_snapshot(created.snapshot.schedule_id) == created.snapshot


def test_backup_restore_preserves_all_draft_and_policy_revisions(workflow):
    operator = admin(workflow)
    operator.initialize_policy(2026, command_id="init")
    first = operator.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    second = operator.regenerate_dated_draft(first.snapshot.schedule_id, expected_version=1, command_id="regen")
    snapshot = workflow.create_verified_backup()
    operator.regenerate_dated_draft(first.snapshot.schedule_id, expected_version=2, command_id="later")
    workflow.restore_backup(snapshot)
    assert database_readiness(workflow.database_path) == "ok"
    assert operator.dated_draft_snapshot(first.snapshot.schedule_id) == second.snapshot
    assert operator.dated_draft_snapshot(first.snapshot.schedule_id, version=1) == first.snapshot
    assert operator.dated_draft_command_result(command_id="later") is None
    assert operator.dated_draft_command_result(command_id="create").snapshot == first.snapshot
    assert operator.regenerate_dated_draft(first.snapshot.schedule_id, expected_version=1, command_id="regen").replayed


def test_old_policy_only_backup_remains_a_valid_historical_format(tmp_path):
    path = tmp_path / "old-fictional.sqlite3"
    command.upgrade(_alembic_config(path), "0015")
    path.with_suffix(".manifest.json").write_text(json.dumps({"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}), encoding="utf-8")
    unused = RosterWorkflow(database_path=tmp_path / "unused.sqlite3", backup_dir=tmp_path)
    result = unused.verify_backup(path)
    assert result["valid"] is True and result["migrationRequired"] is True
    command.upgrade(_alembic_config(path), "head")
    assert database_readiness(path) == "ok"
    command.check(_alembic_config(path))
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM dated_draft_revisions").fetchone() == (0,)
        assert dated_drafts_are_valid(connection)
