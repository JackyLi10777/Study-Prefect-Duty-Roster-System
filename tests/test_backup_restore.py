from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
import pytest

from nicegui_app.config import PREFECT_SEED_PATH, PROJECT_ROOT
from nicegui_app.persistence.database import database_url
from nicegui_app.services.roster_workflow import PrefectInput, RosterWorkflow, WorkflowError
from nicegui_app.services.workflow_parts import recovery as recovery_module


WEEK_START = date(2026, 9, 7)


def test_restore_candidate_wraps_generic_database_startup_failures(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    source = tmp_path / "candidate.sqlite3"
    source.write_bytes(b"isolated-candidate")
    expected_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()

    def fail_to_open(_path: Path):
        raise RuntimeError("migration_bootstrap_failed")

    monkeypatch.setattr(recovery_module, "create_session_factory", fail_to_open)

    with pytest.raises(WorkflowError, match="opening the isolated restore candidate") as error:
        workflow._prepare_restore_candidate(source, expected_sha256=expected_sha256)

    assert isinstance(error.value.__cause__, RuntimeError)
    assert list(tmp_path.glob(".*.restore-*.tmp.sqlite3")) == []


def test_restore_reverts_to_a_verified_snapshot_and_preserves_a_pre_restore_snapshot(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(WEEK_START)

    workflow.create_prefect(
        PrefectInput(
            name_zh="陳樂行",
            name_en="Chan Lok Hang",
            form="F.4",
            class_name="4B",
            role_code="study_prefect",
            available_days=("MONDAY", "WEDNESDAY", "FRIDAY"),
        )
    )
    assert any(prefect["nameZh"] == "陳樂行" for prefect in workflow.prefects())

    result = workflow.restore_backup(draft.backup_path)

    assert result["restoredFrom"] == draft.backup_path
    assert result["preRestoreBackup"].exists()
    assert workflow.verify_backup(result["preRestoreBackup"])["valid"] is True
    assert workflow.roster_week(draft.id)["status"] == "draft"
    assert not any(prefect["nameZh"] == "陳樂行" for prefect in workflow.prefects())


def test_restore_rejects_a_checksum_valid_but_unreconciled_candidate_before_swap(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(WEEK_START)
    live_before = workflow.prefect_loads()

    with sqlite3.connect(draft.backup_path) as connection:
        connection.execute(
            "UPDATE prefects SET history_weight = history_weight + 10 "
            "WHERE id = (SELECT id FROM prefects LIMIT 1)"
        )
        connection.commit()
    _refresh_manifest_checksum(draft.backup_path)
    assert workflow.verify_backup(draft.backup_path)["valid"] is True

    with pytest.raises(WorkflowError, match="Fairness"):
        workflow.restore_backup(draft.backup_path)

    assert workflow.prefect_loads() == live_before
    assert workflow.maintenance_status().active is False


def test_restore_rejects_a_checksum_valid_snapshot_missing_a_core_table_before_swap(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    snapshot = workflow.create_verified_backup()
    live_draft = workflow.generate_and_save_draft(WEEK_START)

    with sqlite3.connect(snapshot) as connection:
        connection.execute("DROP TABLE leave_declarations")
        connection.commit()
    _refresh_manifest_checksum(snapshot)

    verification = workflow.verify_backup(snapshot)
    assert verification["valid"] is False
    assert verification["reasonCode"] == "schema_incomplete"
    assert "leave_declarations" in str(verification["error"])

    with pytest.raises(WorkflowError, match="Backup verification failed"):
        workflow.restore_backup(snapshot)

    assert workflow.roster_week(live_draft.id)["status"] == "draft"
    assert workflow.pre_generation_leaves(WEEK_START) == []
    assert workflow.maintenance_status().active is False


def test_failed_post_swap_validation_rolls_back_to_the_original_database(tmp_path, monkeypatch) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(WEEK_START)
    created = workflow.create_prefect(
        PrefectInput(
            name_zh="測試風紀",
            form="F.4",
            class_name="4B",
            role_code="study_prefect",
            available_days=("MONDAY", "WEDNESDAY", "FRIDAY"),
        )
    )
    audit = workflow._audit

    def fail_restored_audit(session, event_type, roster_week_id, payload):
        if event_type == "backup_restored":
            raise RuntimeError("forced post-swap failure")
        return audit(session, event_type, roster_week_id, payload)

    monkeypatch.setattr(workflow, "_audit", fail_restored_audit)

    with pytest.raises(WorkflowError, match="original database was restored automatically"):
        workflow.restore_backup(draft.backup_path)

    assert workflow.prefect(str(created["id"]))["nameZh"] == "測試風紀"
    assert workflow.maintenance_status().active is False


@pytest.mark.parametrize("claimed_revision", ["0008", "0010"])
def test_backup_verification_rejects_a_mislabeled_revision_missing_its_table(
    claimed_revision: str,
    tmp_path,
) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    snapshot = workflow.create_verified_backup()
    with sqlite3.connect(snapshot) as connection:
        connection.execute("DROP TABLE backup_obligations")
        connection.execute(
            "UPDATE alembic_version SET version_num = ?",
            (claimed_revision,),
        )
        connection.commit()
    _refresh_manifest_checksum(snapshot)

    verification = workflow.verify_backup(snapshot)

    assert verification["valid"] is False
    assert verification["reasonCode"] == "schema_incomplete"
    assert f"revision {claimed_revision}" in str(verification["error"])
    assert "backup_obligations" in str(verification["error"])


def test_restore_accepts_a_verified_0007_snapshot_then_migrates_before_full_validation(tmp_path) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    legacy_snapshot = backup_dir / "legacy-0007.sqlite3"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url(legacy_snapshot))
    command.upgrade(config, "0007")
    _write_manifest(legacy_snapshot)

    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=backup_dir,
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()

    verification = workflow.verify_backup(legacy_snapshot)
    assert verification["valid"] is True
    assert verification["reasonCode"] == "verified_migration_required"
    assert verification["schemaRevision"] == "0007"

    workflow.restore_backup(legacy_snapshot)

    with sqlite3.connect(workflow.database_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0012",)
        assert connection.execute(
            "SELECT COUNT(*) FROM backup_obligations WHERE status <> 'completed'"
        ).fetchone() == (0,)
    created = workflow.create_prefect(
        PrefectInput(
            name_zh="遷移後測試",
            form="F.4",
            class_name="4B",
            role_code="study_prefect",
            available_days=("MONDAY", "WEDNESDAY", "FRIDAY"),
        )
    )
    assert workflow.prefect(str(created["id"]))["nameZh"] == "遷移後測試"


def test_restore_rejects_an_unknown_or_future_migration_revision(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    snapshot = workflow.create_verified_backup()
    with sqlite3.connect(snapshot) as connection:
        connection.execute("UPDATE alembic_version SET version_num = '9999'")
        connection.commit()
    _refresh_manifest_checksum(snapshot)

    verification = workflow.verify_backup(snapshot)

    assert verification["valid"] is False
    assert verification["reasonCode"] == "migration_unsupported"
    with pytest.raises(WorkflowError, match="Backup verification failed"):
        workflow.restore_backup(snapshot)


def test_restore_uses_the_exact_staged_bytes_and_audits_their_digest(
    tmp_path,
    monkeypatch,
) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    original_snapshot = workflow.create_verified_backup()
    original_digest = hashlib.sha256(original_snapshot.read_bytes()).hexdigest()
    workflow.create_prefect(
        PrefectInput(
            name_zh="路徑置換測試",
            form="F.4",
            class_name="4B",
            role_code="study_prefect",
            available_days=("MONDAY", "WEDNESDAY", "FRIDAY"),
        )
    )
    replacement_snapshot = workflow.create_verified_backup()
    stage_restore_source = workflow._stage_restore_source

    def stage_then_replace_requested_path(source_path: Path):
        staged_path, verification = stage_restore_source(source_path)
        source_path.write_bytes(replacement_snapshot.read_bytes())
        source_path.with_suffix(".manifest.json").write_bytes(
            replacement_snapshot.with_suffix(".manifest.json").read_bytes()
        )
        return staged_path, verification

    monkeypatch.setattr(workflow, "_stage_restore_source", stage_then_replace_requested_path)

    workflow.restore_backup(original_snapshot)

    assert not any(prefect["nameZh"] == "路徑置換測試" for prefect in workflow.prefects())
    with sqlite3.connect(workflow.database_path) as connection:
        row = connection.execute(
            "SELECT metadata_json FROM audit_events "
            "WHERE event_type = 'backup_restored' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    assert json.loads(row[0])["sha256"] == original_digest


def test_restore_stops_if_the_private_staged_source_changes_after_verification(
    tmp_path,
    monkeypatch,
) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    original_snapshot = workflow.create_verified_backup()
    workflow.create_prefect(
        PrefectInput(
            name_zh="暫存置換測試",
            form="F.4",
            class_name="4B",
            role_code="study_prefect",
            available_days=("MONDAY", "WEDNESDAY", "FRIDAY"),
        )
    )
    replacement_snapshot = workflow.create_verified_backup()
    stage_restore_source = workflow._stage_restore_source

    def stage_then_replace_staged_bytes(source_path: Path):
        staged_path, verification = stage_restore_source(source_path)
        staged_path.write_bytes(replacement_snapshot.read_bytes())
        return staged_path, verification

    monkeypatch.setattr(workflow, "_stage_restore_source", stage_then_replace_staged_bytes)

    with pytest.raises(WorkflowError, match="changed after verification"):
        workflow.restore_backup(original_snapshot)

    assert any(prefect["nameZh"] == "暫存置換測試" for prefect in workflow.prefects())
    assert workflow.maintenance_status().active is False


@pytest.mark.parametrize("sidecar_suffix", ["-wal", "-shm", "-journal"])
def test_backup_verification_rejects_sqlite_sidecars_not_covered_by_the_manifest(
    sidecar_suffix,
    tmp_path,
) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    snapshot = workflow.create_verified_backup()
    Path(f"{snapshot}{sidecar_suffix}").write_bytes(b"unmanifested journal bytes")

    verification = workflow.verify_backup(snapshot)

    assert verification["valid"] is False
    assert verification["reasonCode"] == "snapshot_sidecar_present"
    with pytest.raises(WorkflowError, match="journal sidecars"):
        workflow.restore_backup(snapshot)


def _refresh_manifest_checksum(backup_path) -> None:
    manifest_path = backup_path.with_suffix(".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sha256"] = hashlib.sha256(backup_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_manifest(backup_path: Path) -> None:
    backup_path.with_suffix(".manifest.json").write_text(
        json.dumps(
            {"sha256": hashlib.sha256(backup_path.read_bytes()).hexdigest()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
