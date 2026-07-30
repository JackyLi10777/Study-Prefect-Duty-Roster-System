from __future__ import annotations

import hashlib
import json
from datetime import date
import os
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
import pytest

from nicegui_app import runtime
from nicegui_app.config import PREFECT_SEED_PATH, PROJECT_ROOT, SQLITE_BUSY_TIMEOUT_MS
from nicegui_app.deployment import health_snapshot
from nicegui_app.main import compose_readiness_payload
from nicegui_app.persistence.database import (
    _alembic_config,
    create_sqlite_engine,
    database_readiness,
    database_url,
)
from nicegui_app.services.maintenance import MaintenanceStatus
from nicegui_app.services.roster_workflow import RosterWorkflow, WorkflowMaintenanceError


def test_sqlite_engine_applies_the_configured_busy_timeout(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "configured.sqlite3")
    try:
        with engine.connect() as connection:
            configured_timeout = connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one()
        assert configured_timeout == SQLITE_BUSY_TIMEOUT_MS
        assert engine.url.get_backend_name() == "sqlite"
    finally:
        engine.dispose()


def test_alembic_uses_absolute_targets_and_model_metadata(tmp_path: Path) -> None:
    database_path = tmp_path / "autogenerate-contract.sqlite3"
    config = _alembic_config(database_path)
    assert Path(config.get_main_option("sqlalchemy.url").removeprefix("sqlite:///" )).is_absolute()

    command.upgrade(config, "head")
    command.check(config)


def test_alembic_rejects_a_relative_sqlite_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", "sqlite:///relative-target.sqlite3")

    with pytest.raises(RuntimeError, match="absolute SQLite URL"):
        command.current(config)
    assert not (tmp_path / "relative-target.sqlite3").exists()


def test_unreconciled_fairness_blocks_startup_and_health_readiness(tmp_path: Path) -> None:
    database_path = tmp_path / "unreconciled.sqlite3"
    workflow = RosterWorkflow(
        database_path=database_path,
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    workflow._dispose_database_connections()

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE prefects SET history_weight = history_weight + 1 WHERE id = "
            "(SELECT id FROM prefects ORDER BY id LIMIT 1)"
        )
        connection.commit()

    assert database_readiness(database_path) == "fairness_unreconciled"
    restarted = RosterWorkflow(database_path=database_path, backup_dir=tmp_path / "backups")
    with pytest.raises(RuntimeError, match="fairness_unreconciled"):
        restarted.bootstrap()


def test_recovery_marker_starts_diagnostics_without_migrating_or_mutating_database(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "recovery-frozen.sqlite3"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url(database_path))
    command.upgrade(config, "0010")
    before_digest = hashlib.sha256(database_path.read_bytes()).hexdigest()
    marker_path = database_path.with_name(f".{database_path.name}.maintenance.json")
    marker_path.write_text(
        json.dumps(
            {
                "operation": "restore",
                "pid": 999_999_999,
                "recoveryRequired": True,
                "reasonCode": "restore_install_failed",
            }
        ),
        encoding="utf-8",
    )

    workflow = RosterWorkflow(database_path=database_path, backup_dir=tmp_path / "backups")
    workflow.bootstrap()

    assert workflow.diagnostic_only is True
    assert workflow.sessions is None
    assert hashlib.sha256(database_path.read_bytes()).hexdigest() == before_digest
    with sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0010",)

    original_workflow = runtime._workflow
    runtime._workflow = workflow
    try:
        runtime_payload = runtime.runtime_readiness()
    finally:
        runtime._workflow = original_workflow
    payload, status = compose_readiness_payload(
        health_snapshot(database_path),
        runtime_payload,
    )
    assert status == 503
    assert payload["status"] == "degraded"
    assert payload["recoveryRequired"] is True
    assert payload["writeReady"] is False
    with pytest.raises(WorkflowMaintenanceError, match="maintenance mode"):
        workflow.generate_and_save_draft(date(2026, 10, 5))
    with pytest.raises(WorkflowMaintenanceError, match="maintenance mode"):
        workflow.prepare_new_school_year()


def test_live_peer_maintenance_marker_starts_data_free_diagnostics_without_mutating_database(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "peer-maintenance-frozen.sqlite3"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url(database_path))
    command.upgrade(config, "0010")
    before_digest = hashlib.sha256(database_path.read_bytes()).hexdigest()
    marker_path = database_path.with_name(f".{database_path.name}.maintenance.json")
    marker_path.write_text(
        json.dumps(
            {
                "operation": "restore",
                "pid": os.getpid(),
            }
        ),
        encoding="utf-8",
    )

    workflow = RosterWorkflow(database_path=database_path, backup_dir=tmp_path / "backups")
    workflow.bootstrap()

    assert workflow.diagnostic_only is True
    assert workflow.sessions is None
    assert hashlib.sha256(database_path.read_bytes()).hexdigest() == before_digest
    with sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0010",)

    original_workflow = runtime._workflow
    runtime._workflow = workflow
    try:
        runtime_payload = runtime.runtime_readiness()
    finally:
        runtime._workflow = original_workflow
    assert runtime_payload["maintenance"] is True
    assert runtime_payload["recoveryRequired"] is False
    assert runtime_payload["workflowInitialized"] is False
    assert runtime_payload["pendingBackupObligations"] == 0
    payload, status = compose_readiness_payload(
        health_snapshot(database_path),
        runtime_payload,
    )
    assert status == 503
    assert payload["status"] == "degraded"
    assert payload["writeReady"] is False
    with pytest.raises(WorkflowMaintenanceError, match="maintenance mode"):
        workflow.generate_and_save_draft(date(2026, 10, 5))

    marker_path.unlink()
    original_workflow = runtime._workflow
    runtime._workflow = workflow
    try:
        after_peer_exit = runtime.runtime_readiness()
    finally:
        runtime._workflow = original_workflow
    payload, status = compose_readiness_payload(
        health_snapshot(database_path),
        after_peer_exit,
    )
    assert after_peer_exit["maintenance"] is False
    assert after_peer_exit["workflowInitialized"] is False
    assert status == 503
    assert payload["status"] == "degraded"
    assert payload["writeReady"] is False


def test_maintenance_marker_winning_after_startup_status_check_blocks_migration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "maintenance-race-frozen.sqlite3"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url(database_path))
    command.upgrade(config, "0010")
    before_digest = hashlib.sha256(database_path.read_bytes()).hexdigest()
    marker_path = database_path.with_name(f".{database_path.name}.maintenance.json")

    workflow = RosterWorkflow(database_path=database_path, backup_dir=tmp_path / "backups")
    real_status = workflow.maintenance.status
    first_status = True

    def marker_arrives_after_inactive_status_sample() -> MaintenanceStatus:
        nonlocal first_status
        status = real_status()
        if first_status:
            first_status = False
            assert status.active is False
            marker_path.write_text(
                json.dumps({"operation": "restore", "pid": os.getpid()}),
                encoding="utf-8",
            )
        return status

    monkeypatch.setattr(
        workflow.maintenance,
        "status",
        marker_arrives_after_inactive_status_sample,
    )

    workflow.bootstrap()

    assert workflow.diagnostic_only is True
    assert workflow.sessions is None
    assert hashlib.sha256(database_path.read_bytes()).hexdigest() == before_digest
    with sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0010",)
    assert real_status().active is True
