from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import sqlite3

import pytest

from nicegui_app.application_mode import ApplicationModeSettings
from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.persistence.database import database_readiness
from nicegui_app.persistence.models import Base
from nicegui_app.services.public_roster_share import PublicRosterShareSettings
from nicegui_app.services.roster_workflow import RosterWorkflow
import nicegui_app.runtime as runtime
import scripts.reset_official_data as reset_module
from scripts.reset_official_data import (
    CONFIRMATION_PHRASE,
    OfficialDataResetError,
    ResetPaths,
    reset_official_data,
)


def _count(path: Path, table: str) -> int:
    with sqlite3.connect(path) as connection:
        return int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def _seeded_database(tmp_path: Path) -> tuple[Path, Path]:
    database = tmp_path / "runtime" / "official.sqlite3"
    backups = tmp_path / "backups"
    workflow = RosterWorkflow(database_path=database, backup_dir=backups, seed_path=PREFECT_SEED_PATH)
    workflow.bootstrap()
    assert _count(database, "prefects") > 0
    workflow._dispose_database_connections()
    return database, backups


def _paths(tmp_path: Path, database: Path, backups: Path) -> ResetPaths:
    return ResetPaths(
        database_path=database,
        backup_dir=backups,
        archive_root=tmp_path / "retired-demo-data",
        report_path=tmp_path / "logs" / "reset-report.json",
    )


def _disabled_public_shares() -> PublicRosterShareSettings:
    return PublicRosterShareSettings(False, "", "")


def test_runtime_bootstraps_official_empty_but_practice_with_fictitious_seed(tmp_path: Path, monkeypatch) -> None:
    original_workflow = runtime._workflow
    try:
        monkeypatch.setenv("SING_YIN_LOCAL_MAINTENANCE", "1")
        official_profile = ApplicationModeSettings(
            mode="official",
            database_path=tmp_path / "official" / "runtime.sqlite3",
            backup_dir=tmp_path / "official" / "backups",
            log_dir=tmp_path / "official" / "logs",
        )
        monkeypatch.setattr(runtime, "current_application_mode", lambda: official_profile)
        runtime._workflow = None
        official = runtime.get_workflow()
        assert _count(official_profile.database_path, "prefects") == 0
        assert _count(official_profile.database_path, "audit_events") == 0
        official._dispose_database_connections()

        practice_profile = ApplicationModeSettings(
            mode="practice",
            database_path=tmp_path / "practice" / "runtime.sqlite3",
            backup_dir=tmp_path / "practice" / "backups",
            log_dir=tmp_path / "practice" / "logs",
        )
        monkeypatch.setattr(runtime, "current_application_mode", lambda: practice_profile)
        runtime._workflow = None
        practice = runtime.get_workflow()
        assert _count(practice_profile.database_path, "prefects") > 0
        assert _count(practice_profile.database_path, "audit_events") == 1
        practice._dispose_database_connections()
    finally:
        runtime._workflow = original_workflow


def test_reset_requires_exact_confirmation_before_writing(tmp_path: Path) -> None:
    database, backups = _seeded_database(tmp_path)
    with pytest.raises(OfficialDataResetError, match="--confirm") as raised:
        reset_official_data(
            _paths(tmp_path, database, backups),
            confirmation="reset",
            host_probe=lambda _url: False,
            public_share_settings=_disabled_public_shares(),
            permission_hardener=lambda _path: None,
        )
    assert raised.value.reason_code == "confirmation_mismatch"
    assert _count(database, "prefects") > 0
    assert not backups.exists()


def test_reset_refuses_while_local_host_is_listening(tmp_path: Path) -> None:
    database, backups = _seeded_database(tmp_path)
    paths = _paths(tmp_path, database, backups)
    with pytest.raises(OfficialDataResetError) as raised:
        reset_official_data(
            paths,
            confirmation=CONFIRMATION_PHRASE,
            host_probe=lambda _url: True,
            public_share_settings=_disabled_public_shares(),
            attest_no_public_share_gateway=True,
            permission_hardener=lambda _path: None,
        )
    assert raised.value.reason_code == "host_is_running"
    assert _count(database, "prefects") > 0
    report = json.loads(paths.report_path.read_text(encoding="utf-8"))
    assert report["failureReason"] == "host_is_running"
    assert report["sourceRowCounts"] == {}


def test_reset_scans_every_port_in_configured_host_range(tmp_path: Path) -> None:
    database, backups = _seeded_database(tmp_path)
    observed: list[str] = []

    def probe(url: str) -> bool:
        observed.append(url)
        return ":9002/healthz" in url

    with pytest.raises(OfficialDataResetError) as raised:
        reset_official_data(
            _paths(tmp_path, database, backups),
            confirmation=CONFIRMATION_PHRASE,
            health_url="http://127.0.0.1:9000/healthz",
            host_port_range=(9000, 9004),
            host_probe=probe,
            public_share_settings=_disabled_public_shares(),
            attest_no_public_share_gateway=True,
            permission_hardener=lambda _path: None,
        )
    assert raised.value.reason_code == "host_is_running"
    assert observed == [
        "http://127.0.0.1:9000/healthz",
        "http://127.0.0.1:9001/healthz",
        "http://127.0.0.1:9002/healthz",
    ]


def test_reset_requires_explicit_attestation_when_share_gateway_is_absent(tmp_path: Path) -> None:
    database, backups = _seeded_database(tmp_path)
    paths = _paths(tmp_path, database, backups)
    original_count = _count(database, "prefects")
    with pytest.raises(OfficialDataResetError) as raised:
        reset_official_data(
            paths,
            confirmation=CONFIRMATION_PHRASE,
            host_probe=lambda _url: False,
            public_share_settings=_disabled_public_shares(),
            permission_hardener=lambda _path: None,
        )
    assert raised.value.reason_code == "public_share_gateway_unattested"
    assert _count(database, "prefects") == original_count
    assert not backups.exists()
    report = json.loads(paths.report_path.read_text(encoding="utf-8"))
    assert report["failureReason"] == "public_share_gateway_unattested"
    assert report["publicShares"]["status"] == "not_checked"


@pytest.mark.parametrize("location", ["runtime", "backups", "archive", "wrong_suffix"])
def test_reset_report_must_be_json_outside_managed_data_paths(tmp_path: Path, location: str) -> None:
    database, backups = _seeded_database(tmp_path)
    base = _paths(tmp_path, database, backups)
    report_paths = {
        "runtime": database.parent / "reset-report.json",
        "backups": backups / "reset-report.json",
        "archive": base.archive_root / "reset-report.json",
        "wrong_suffix": tmp_path / "logs" / "reset-report.txt",
    }
    paths = ResetPaths(database, backups, base.archive_root, report_paths[location])
    with pytest.raises(OfficialDataResetError) as raised:
        reset_official_data(
            paths,
            confirmation=CONFIRMATION_PHRASE,
            host_probe=lambda _url: False,
            public_share_settings=_disabled_public_shares(),
            attest_no_public_share_gateway=True,
            permission_hardener=lambda _path: None,
        )
    assert raised.value.reason_code == "invalid_report_path"
    assert _count(database, "prefects") > 0
    assert not report_paths[location].exists()


def test_reset_quarantines_demo_inventory_and_leaves_verified_empty_baseline(tmp_path: Path) -> None:
    database, backups = _seeded_database(tmp_path)
    before = RosterWorkflow(database_path=database, backup_dir=backups)
    before.bootstrap()
    legacy_snapshot = before.create_verified_backup()
    assert before.verify_backup(legacy_snapshot)["valid"] is True
    before._dispose_database_connections()
    legacy_sidecars = [
        Path(f"{legacy_snapshot}-wal"),
        Path(f"{legacy_snapshot}-shm"),
        legacy_snapshot.with_suffix(".sqlite3.tmp"),
        Path(f"{legacy_snapshot.with_suffix('.sqlite3.tmp')}-journal"),
    ]
    for sidecar in legacy_sidecars:
        sidecar.write_bytes(b"retired-demo-sentinel")

    paths = _paths(tmp_path, database, backups)
    report = reset_official_data(
        paths,
        confirmation=CONFIRMATION_PHRASE,
        host_probe=lambda _url: False,
        public_share_settings=_disabled_public_shares(),
        attest_no_public_share_gateway=True,
        permission_hardener=lambda _path: None,
    )

    assert report["status"] == "pass"
    assert report["isolatedRestoreVerified"] is True
    assert report["publicShares"]["status"] == "attested_not_configured"
    assert report["publicShares"]["attestation"] == "explicit_no_gateway"
    assert report["rollback"] == {"available": True, "performed": False}
    assert database_readiness(database) == "ok"
    assert all(_count(database, table) == 0 for table in Base.metadata.tables)
    assert report["emptyRowCounts"] == {table: 0 for table in sorted(Base.metadata.tables)}
    assert all(
        len(str(digest)) == 64 and int(str(digest), 16) >= 0
        for digest in report["recoveryEvidence"].values()
    )

    active_snapshots = list(backups.glob("*.sqlite3"))
    active_manifests = list(backups.glob("*.manifest.json"))
    assert len(active_snapshots) == 1
    assert len(active_manifests) == 1
    assert sorted(path.name for path in backups.iterdir()) == sorted(
        [active_snapshots[0].name, active_manifests[0].name]
    )
    verifier = RosterWorkflow(database_path=database, backup_dir=backups, seed_path=None)
    assert verifier.verify_backup(active_snapshots[0])["valid"] is True
    verifier._dispose_database_connections()

    archive_dirs = list(paths.archive_root.glob("reset-*"))
    assert len(archive_dirs) == 1
    assert (archive_dirs[0] / "pre-reset-live.sqlite3").is_file()
    assert (archive_dirs[0] / "pre-reset-live.manifest.json").is_file()
    assert list((archive_dirs[0] / "managed-backups").glob("*.sqlite3"))
    for sidecar in legacy_sidecars:
        assert (archive_dirs[0] / "managed-backups" / sidecar.name).read_bytes() == b"retired-demo-sentinel"

    report_text = paths.report_path.read_text(encoding="utf-8")
    assert "shareId" not in report_text
    assert "adminToken" not in report_text
    assert "nameZh" not in report_text


class _ShareGateway:
    def __init__(self, *, fail_revoke: bool = False) -> None:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        self.items = [
            {
                "shareId": "A" * 24,
                "weekStart": "2026-07-13",
                "createdAt": now.isoformat().replace("+00:00", "Z"),
                "expiresAt": (now + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
            },
            {
                "shareId": "B" * 24,
                "weekStart": "2026-07-20",
                "createdAt": now.isoformat().replace("+00:00", "Z"),
                "expiresAt": (now + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
            },
        ]
        self.fail_revoke = fail_revoke

    def create(self, payload):  # pragma: no cover - reset never creates shares
        raise AssertionError(payload)

    def list(self):
        return list(self.items)

    def revoke(self, share_id: str) -> None:
        if self.fail_revoke:
            raise RuntimeError("injected gateway failure")
        self.items = [item for item in self.items if item["shareId"] != share_id]


def _configured_public_shares() -> PublicRosterShareSettings:
    return PublicRosterShareSettings(
        enabled=True,
        base_url="https://viewer.example.test",
        admin_token="x" * 32,
        timeout_seconds=1,
    )


def test_reset_revokes_every_configured_public_share_before_replacement(tmp_path: Path) -> None:
    database, backups = _seeded_database(tmp_path)
    gateway = _ShareGateway()
    report = reset_official_data(
        _paths(tmp_path, database, backups),
        confirmation=CONFIRMATION_PHRASE,
        host_probe=lambda _url: False,
        public_share_settings=_configured_public_shares(),
        public_share_gateway=gateway,
        permission_hardener=lambda _path: None,
    )
    assert gateway.items == []
    assert report["publicShares"] == {
        "status": "revoked",
        "attestation": None,
        "discoveredCount": 2,
        "revokedCount": 2,
        "remainingCount": 0,
    }
    assert _count(database, "prefects") == 0


def test_public_share_revocation_failure_leaves_database_unchanged(tmp_path: Path) -> None:
    database, backups = _seeded_database(tmp_path)
    paths = _paths(tmp_path, database, backups)
    original_count = _count(database, "prefects")
    with pytest.raises(OfficialDataResetError) as raised:
        reset_official_data(
            paths,
            confirmation=CONFIRMATION_PHRASE,
            host_probe=lambda _url: False,
            public_share_settings=_configured_public_shares(),
            public_share_gateway=_ShareGateway(fail_revoke=True),
            permission_hardener=lambda _path: None,
        )
    assert raised.value.reason_code == "public_share_revocation_failed"
    assert _count(database, "prefects") == original_count
    report = json.loads(paths.report_path.read_text(encoding="utf-8"))
    assert report["failureReason"] == "public_share_revocation_failed"


def test_maintenance_lock_spans_fairness_backup_revoke_quarantine_and_report(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database, backups = _seeded_database(tmp_path)
    paths = _paths(tmp_path, database, backups)
    marker = database.with_name(f".{database.name}.maintenance.json")
    observed: list[tuple[str, bool]] = []

    original_reconcile = RosterWorkflow.reconcile_fairness
    original_backup = RosterWorkflow.create_verified_backup
    original_revoke = reset_module._revoke_all_public_shares
    original_write_report = reset_module._write_report

    def reconcile_with_evidence(self):
        if self.database_path.resolve() == database.resolve():
            observed.append(("fairness", marker.exists()))
        return original_reconcile(self)

    def backup_with_evidence(self):
        if self.database_path.resolve() == database.resolve():
            observed.append(("backup", marker.exists()))
        return original_backup(self)

    def revoke_with_evidence(workflow, **kwargs):
        observed.append(("revoke", marker.exists()))
        return original_revoke(workflow, **kwargs)

    def write_report_with_evidence(path, report):
        if Path(path).resolve() == paths.report_path.resolve():
            observed.append(("report", marker.exists()))
        return original_write_report(path, report)

    monkeypatch.setattr(RosterWorkflow, "reconcile_fairness", reconcile_with_evidence)
    monkeypatch.setattr(RosterWorkflow, "create_verified_backup", backup_with_evidence)
    monkeypatch.setattr(reset_module, "_revoke_all_public_shares", revoke_with_evidence)
    monkeypatch.setattr(reset_module, "_write_report", write_report_with_evidence)

    report = reset_official_data(
        paths,
        confirmation=CONFIRMATION_PHRASE,
        host_probe=lambda _url: False,
        public_share_settings=_disabled_public_shares(),
        attest_no_public_share_gateway=True,
        permission_hardener=lambda _path: observed.append(("quarantine", marker.exists())),
    )

    assert report["status"] == "pass"
    assert {label for label, _active in observed} >= {"fairness", "backup", "revoke", "quarantine", "report"}
    assert all(active for _label, active in observed)
    assert not marker.exists()


def test_isolated_restore_cleanup_failure_is_fail_closed(tmp_path: Path, monkeypatch) -> None:
    database, backups = _seeded_database(tmp_path)
    workflow = RosterWorkflow(database_path=database, backup_dir=backups, seed_path=None)
    workflow.bootstrap()
    snapshot = workflow.create_verified_backup()
    workflow._dispose_database_connections()

    workspace = tmp_path / "isolated-restore-workspace"
    real_rmtree = shutil.rmtree

    def fake_mkdtemp(**_kwargs) -> str:
        workspace.mkdir()
        return str(workspace)

    monkeypatch.setattr(reset_module.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(reset_module.shutil, "rmtree", lambda _path: None)
    with pytest.raises(OfficialDataResetError) as raised:
        reset_module._verify_isolated_restore(snapshot, source_database=database)
    assert raised.value.reason_code == "isolated_restore_cleanup_failed"
    assert workspace.exists()
    real_rmtree(workspace)


def test_isolated_restore_disposal_failure_removes_workspace_but_still_refuses(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database, backups = _seeded_database(tmp_path)
    workflow = RosterWorkflow(database_path=database, backup_dir=backups, seed_path=None)
    workflow.bootstrap()
    snapshot = workflow.create_verified_backup()
    workflow._dispose_database_connections()

    workspace = tmp_path / "isolated-disposal-workspace"
    original_dispose = RosterWorkflow._dispose_database_connections
    disposal_attempted = False

    def fake_mkdtemp(**_kwargs) -> str:
        workspace.mkdir()
        return str(workspace)

    def dispose_with_failure(self) -> None:
        nonlocal disposal_attempted
        if self.database_path.name == "restored.sqlite3":
            disposal_attempted = True
            original_dispose(self)
            raise RuntimeError("injected disposal evidence failure")
        original_dispose(self)

    monkeypatch.setattr(reset_module.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(RosterWorkflow, "_dispose_database_connections", dispose_with_failure)
    with pytest.raises(OfficialDataResetError) as raised:
        reset_module._verify_isolated_restore(snapshot, source_database=database)
    assert raised.value.reason_code == "isolated_restore_cleanup_failed"
    assert disposal_attempted is True
    assert not workspace.exists()


def test_failed_installed_verification_rolls_back_database_and_backup_inventory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database, backups = _seeded_database(tmp_path)
    original_count = _count(database, "prefects")
    legacy = RosterWorkflow(database_path=database, backup_dir=backups)
    legacy.bootstrap()
    original_backup = legacy.create_verified_backup()
    legacy._dispose_database_connections()

    original_verify = reset_module._verify_empty_database
    call_count = 0

    def fail_after_install(path: Path):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("injected post-install verification failure")
        return original_verify(path)

    monkeypatch.setattr(reset_module, "_verify_empty_database", fail_after_install)
    paths = _paths(tmp_path, database, backups)
    with pytest.raises(OfficialDataResetError) as raised:
        reset_official_data(
            paths,
            confirmation=CONFIRMATION_PHRASE,
            host_probe=lambda _url: False,
            public_share_settings=_disabled_public_shares(),
            attest_no_public_share_gateway=True,
            permission_hardener=lambda _path: None,
        )
    assert raised.value.reason_code == "post_install_verification_failed"
    assert database_readiness(database) == "ok"
    assert _count(database, "prefects") == original_count
    assert original_backup.exists()
    report = json.loads(paths.report_path.read_text(encoding="utf-8"))
    assert report["rollback"]["performed"] is True
    assert report["failureReason"] == "post_install_verification_failed"
