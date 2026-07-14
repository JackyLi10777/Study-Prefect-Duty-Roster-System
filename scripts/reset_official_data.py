"""One-off, fail-closed retirement of demonstration data from an official host.

This command is intentionally not exposed through the web UI.  It creates a
verified recovery snapshot, proves that snapshot can be restored in an
isolated database, revokes any configured public roster shares, quarantines
the old managed backups, and only then atomically installs a migrated empty
SQLite database.  A verified empty baseline snapshot is left in the active
backup directory.

The report contains table counts and opaque evidence only.  It never reads or
serializes prefect names, share identifiers, credentials, or snapshot rows.
All managed loopback ports must be stopped.  When no public-share gateway is
configured, the operator must explicitly attest that this host never issued
public roster links; that attestation is recorded in the sanitized report.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
from typing import Any
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui_app.config import DEFAULT_BACKUP_DIR, DEFAULT_DATABASE_PATH, PROJECT_ROOT
from nicegui_app.persistence.database import database_readiness, migrate_database
from nicegui_app.persistence.models import Base
from nicegui_app.services.public_roster_share import (
    PublicRosterShareGateway,
    PublicRosterShareService,
    PublicRosterShareSettings,
)
from nicegui_app.services.roster_workflow import RosterWorkflow


CONFIRMATION_PHRASE = "RESET-OFFICIAL-ROSTER-DATA"
DEFAULT_ARCHIVE_DIR = PROJECT_ROOT / "data" / "retired-demo-data"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "logs" / "official-data-reset-report.json"
DEFAULT_HEALTH_URL = "http://127.0.0.1:8080/healthz"
DEFAULT_HOST_PORT_RANGE = (8080, 8099)

_SQLITE_SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")
_MANAGED_BACKUP_SUFFIXES = (
    ".sqlite3",
    ".manifest.json",
    ".sqlite3-wal",
    ".sqlite3-shm",
    ".sqlite3-journal",
    ".sqlite3.tmp",
    ".sqlite3.tmp-wal",
    ".sqlite3.tmp-shm",
    ".sqlite3.tmp-journal",
)
_ALL_DATA_TABLES = tuple(sorted(Base.metadata.tables.keys()))
_RESTORE_COMPARISON_TABLES = (
    "prefects",
    "prefect_availability",
    "roster_weeks",
    "roster_assignments",
    "fairness_ledger",
    "leave_adjustments",
    "leave_declarations",
)


class OfficialDataResetError(RuntimeError):
    """A safe operator-facing refusal with a stable, non-sensitive code."""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


@dataclass(frozen=True)
class ResetPaths:
    database_path: Path
    backup_dir: Path
    archive_root: Path
    report_path: Path

    def resolved(self) -> "ResetPaths":
        return ResetPaths(
            database_path=self.database_path.expanduser().resolve(),
            backup_dir=self.backup_dir.expanduser().resolve(),
            archive_root=self.archive_root.expanduser().resolve(),
            report_path=self.report_path.expanduser().resolve(),
        )


HostProbe = Callable[[str], bool]
PermissionHardener = Callable[[Path], None]


def reset_official_data(
    paths: ResetPaths,
    *,
    confirmation: str,
    health_url: str = DEFAULT_HEALTH_URL,
    host_port_range: tuple[int, int] = DEFAULT_HOST_PORT_RANGE,
    host_probe: HostProbe | None = None,
    public_share_settings: PublicRosterShareSettings | None = None,
    public_share_gateway: PublicRosterShareGateway | None = None,
    attest_no_public_share_gateway: bool = False,
    permission_hardener: PermissionHardener | None = None,
) -> dict[str, Any]:
    """Replace one stopped official database with a verified empty database.

    Dependencies are injectable so the safety contract can be verified without
    network access, Task Scheduler, or production paths.
    """

    resolved = paths.resolved()
    if confirmation != CONFIRMATION_PHRASE:
        raise OfficialDataResetError(
            "confirmation_mismatch",
            f"Refused. Re-run with --confirm {CONFIRMATION_PHRASE} after checking the target paths.",
        )
    if os.getenv("SING_YIN_APP_MODE", "official").strip().lower() != "official":
        raise OfficialDataResetError(
            "not_official_mode",
            "Refused because this process is not configured in official application mode.",
        )
    _validate_paths(resolved)
    _preflight_report_path(resolved.report_path)

    probe = host_probe or _host_listener_is_running
    harden = permission_hardener or _restrict_archive_permissions
    share_settings = public_share_settings or PublicRosterShareSettings.from_environment()
    report: dict[str, Any] = {
        "status": "fail",
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "databaseFile": resolved.database_path.name,
        "sourceRowCounts": {},
        "emptyRowCounts": {},
        "isolatedRestoreVerified": False,
        "publicShares": {
            "status": "not_checked",
            "attestation": None,
            "discoveredCount": 0,
            "revokedCount": 0,
            "remainingCount": 0,
        },
        "quarantine": {
            "archiveId": None,
            "managedFilesMoved": 0,
            "restricted": False,
        },
        "sqliteSidecars": {"beforeCount": 0, "afterCount": 0},
        "rollback": {"available": False, "performed": False},
        "activeBaseline": {"verified": False, "snapshotCount": 0, "manifestCount": 0},
        "recoveryEvidence": {
            "recoverySnapshotSha256": None,
            "quarantineSnapshotSha256": None,
            "emptyBaselineSha256": None,
        },
        "failureReason": "not_started",
    }

    workflow: RosterWorkflow | None = None
    candidate_path: Path | None = None
    archive_dir: Path | None = None
    rollback_snapshot: Path | None = None
    moved_files: list[tuple[Path, Path]] = []
    installed_empty = False
    maintenance_stack = ExitStack()
    maintenance_active = False

    try:
        _validate_public_share_attestation(
            share_settings,
            attest_no_public_share_gateway=attest_no_public_share_gateway,
        )
        if _probe_host_port_range(health_url, host_port_range=host_port_range, probe=probe):
            raise OfficialDataResetError(
                "host_is_running",
                "Refused because a local roster host is listening on the managed port range. Stop and disable its startup task first.",
            )
        if database_readiness(resolved.database_path) != "ok":
            raise OfficialDataResetError(
                "database_not_ready",
                "Refused because the official database did not pass integrity, schema, and migration checks.",
            )

        workflow = RosterWorkflow(
            database_path=resolved.database_path,
            backup_dir=resolved.backup_dir,
            seed_path=None,
        )
        workflow.bootstrap()
        maintenance_stack.enter_context(workflow.maintenance.maintenance("official_data_reset"))
        maintenance_active = True
        # Close the start/check race after the durable cross-process marker
        # exists, before reading fairness or creating any recovery evidence.
        if _probe_host_port_range(health_url, host_port_range=host_port_range, probe=probe):
            raise OfficialDataResetError(
                "host_restarted_during_reset",
                "Refused because a local roster host restarted during the reset window.",
            )
        source_counts = _table_counts(resolved.database_path, _ALL_DATA_TABLES)
        report["sourceRowCounts"] = source_counts
        fairness = workflow.reconcile_fairness()
        if not fairness.balanced:
            raise OfficialDataResetError(
                "fairness_not_reconciled",
                "Refused because the fairness ledger did not reconcile; no official data was replaced.",
            )

        recovery_snapshot = workflow.create_verified_backup()
        verification = workflow.verify_backup(recovery_snapshot)
        if not verification.get("valid"):
            raise OfficialDataResetError(
                "backup_not_verified",
                "Refused because the new recovery snapshot did not pass checksum and SQLite verification.",
            )
        report["recoveryEvidence"]["recoverySnapshotSha256"] = _sha256(recovery_snapshot)
        _verify_isolated_restore(
            recovery_snapshot,
            source_database=resolved.database_path,
        )
        report["isolatedRestoreVerified"] = True

        report["publicShares"] = _revoke_all_public_shares(
            workflow,
            settings=share_settings,
            gateway=public_share_gateway,
            attest_no_public_share_gateway=attest_no_public_share_gateway,
        )

        archive_id = _archive_id()
        archive_dir = resolved.archive_root / archive_id
        archive_dir.mkdir(parents=True, exist_ok=False)
        harden(archive_dir)
        report["quarantine"]["archiveId"] = archive_id
        report["quarantine"]["restricted"] = True

        # The verified snapshot is the canonical rollback copy of the live
        # database.  Give it a stable name before moving the remaining legacy
        # managed inventory out of the active backup directory.
        rollback_snapshot = archive_dir / "pre-reset-live.sqlite3"
        rollback_manifest = rollback_snapshot.with_suffix(".manifest.json")
        shutil.copy2(recovery_snapshot, rollback_snapshot)
        shutil.copy2(recovery_snapshot.with_suffix(".manifest.json"), rollback_manifest)
        if not workflow.verify_backup(rollback_snapshot).get("valid"):
            raise OfficialDataResetError(
                "quarantine_snapshot_not_verified",
                "Refused because the quarantined rollback snapshot did not pass verification.",
            )
        report["recoveryEvidence"]["quarantineSnapshotSha256"] = _sha256(rollback_snapshot)
        report["rollback"]["available"] = True

        moved_files = _quarantine_managed_backups(resolved.backup_dir, archive_dir)
        report["quarantine"]["managedFilesMoved"] = len(moved_files)
        if _managed_backup_files(resolved.backup_dir):
            raise OfficialDataResetError(
                "active_backup_inventory_not_empty",
                "Refused because the old managed backup inventory could not be fully quarantined.",
            )

        candidate_path = resolved.database_path.with_name(
            f".{resolved.database_path.name}.empty-{secrets.token_hex(8)}.tmp.sqlite3"
        )
        migrate_database(candidate_path)
        candidate_counts = _verify_empty_database(candidate_path)

        workflow._dispose_database_connections()
        if not maintenance_active:
            raise OfficialDataResetError(
                "maintenance_lock_missing",
                "Refused because the exclusive maintenance lock is not active.",
            )
        _checkpoint_database(resolved.database_path)
        report["sqliteSidecars"]["beforeCount"] = len(_existing_sidecars(resolved.database_path))
        _remove_sidecars(resolved.database_path)
        os.replace(candidate_path, resolved.database_path)
        candidate_path = None
        installed_empty = True
        try:
            installed_counts = _verify_empty_database(resolved.database_path)
            if installed_counts != candidate_counts:
                raise OfficialDataResetError(
                    "installed_counts_changed",
                    "The installed empty database did not match its verified candidate.",
                )
            baseline_path = _create_empty_baseline_snapshot(
                resolved.database_path,
                resolved.backup_dir,
                workflow,
            )
            if not workflow.verify_backup(baseline_path).get("valid"):
                raise OfficialDataResetError(
                    "empty_baseline_not_verified",
                    "The empty baseline snapshot did not pass verification.",
                )
            report["recoveryEvidence"]["emptyBaselineSha256"] = _sha256(baseline_path)
            report["emptyRowCounts"] = _verify_empty_database(resolved.database_path)
            report["sqliteSidecars"]["afterCount"] = len(_existing_sidecars(resolved.database_path))
            if report["sqliteSidecars"]["afterCount"]:
                raise OfficialDataResetError(
                    "sqlite_sidecars_remain",
                    "The replacement left unexpected SQLite sidecars and was rolled back.",
                )
            active_files = _managed_backup_files(resolved.backup_dir)
            snapshot_count = len([path for path in active_files if path.suffix == ".sqlite3"])
            manifest_count = len([path for path in active_files if path.name.endswith(".manifest.json")])
            active_baseline = {
                "verified": snapshot_count == 1 and manifest_count == 1 and len(active_files) == 2,
                "snapshotCount": snapshot_count,
                "manifestCount": manifest_count,
            }
            if active_baseline != {"verified": True, "snapshotCount": 1, "manifestCount": 1}:
                raise OfficialDataResetError(
                    "active_baseline_inventory_invalid",
                    "The replacement baseline inventory was incomplete and the reset was rolled back.",
                )
            report["activeBaseline"] = active_baseline
        except Exception as error:
            try:
                if rollback_snapshot is None:
                    raise RuntimeError("rollback snapshot unavailable")
                _restore_quarantined_snapshot(
                    rollback_snapshot,
                    resolved.database_path,
                    expected_counts=source_counts,
                )
                installed_empty = False
                report["rollback"]["performed"] = True
                _remove_managed_backups(resolved.backup_dir)
                _restore_quarantined_backups(moved_files)
                moved_files = []
            except Exception as rollback_error:
                workflow.maintenance.require_recovery_review(reason_code="official_reset_rollback_failed")
                raise OfficialDataResetError(
                    "rollback_failed",
                    "The empty database could not be verified and automatic rollback failed. Recovery review is required.",
                ) from rollback_error
            if isinstance(error, OfficialDataResetError):
                raise error
            raise OfficialDataResetError(
                "post_install_verification_failed",
                "The empty database could not be verified; the original database was restored automatically.",
            ) from error

        report["status"] = "pass"
        report["failureReason"] = None
        _write_report(resolved.report_path, report)
        return report
    except OfficialDataResetError as error:
        report["failureReason"] = error.reason_code
        _write_report(resolved.report_path, report)
        raise
    except Exception as error:
        report["failureReason"] = "unexpected_failure"
        _write_report(resolved.report_path, report)
        raise OfficialDataResetError(
            "unexpected_failure",
            "The controlled reset stopped safely after an unexpected error. Review the sanitized report.",
        ) from error
    finally:
        try:
            if workflow is not None:
                workflow._dispose_database_connections()
            if candidate_path is not None:
                _remove_sidecars(candidate_path)
                candidate_path.unlink(missing_ok=True)
            if not installed_empty and moved_files:
                try:
                    _restore_quarantined_backups(moved_files)
                except OSError:
                    # The report remains fail-closed.  The verified rollback copy
                    # stays in the restricted quarantine for manual recovery.
                    pass
        finally:
            # Keep the cross-process lock through report writing and all local
            # recovery/cleanup work; release it only as the command returns.
            maintenance_stack.close()


def _validate_paths(paths: ResetPaths) -> None:
    if paths.database_path.suffix.lower() != ".sqlite3" or not paths.database_path.is_file():
        raise OfficialDataResetError(
            "invalid_database_path",
            "The target must be an existing .sqlite3 database file.",
        )
    if paths.report_path.suffix.lower() != ".json" or (
        paths.report_path.exists() and not paths.report_path.is_file()
    ):
        raise OfficialDataResetError(
            "invalid_report_path",
            "The sanitized report must be a .json file path.",
        )
    managed_report_containers = (paths.database_path.parent, paths.backup_dir, paths.archive_root)
    if paths.report_path == paths.database_path or any(
        paths.report_path == container or _path_contains(container, paths.report_path)
        for container in managed_report_containers
    ):
        raise OfficialDataResetError(
            "invalid_report_path",
            "The report must be outside the managed database, backup, and retired-data directories.",
        )
    if paths.backup_dir == paths.archive_root or _path_contains(paths.backup_dir, paths.archive_root) or _path_contains(
        paths.archive_root,
        paths.backup_dir,
    ):
        raise OfficialDataResetError(
            "archive_overlaps_backups",
            "The active backup directory and retired-data archive must be different paths.",
        )
    for container in (paths.backup_dir, paths.archive_root):
        try:
            paths.database_path.relative_to(container)
        except ValueError:
            continue
        raise OfficialDataResetError(
            "database_inside_managed_output",
            "The database cannot be stored inside the active backup or retired-data directory.",
        )


def _health_urls_for_port_range(
    health_url: str,
    *,
    host_port_range: tuple[int, int],
) -> list[str]:
    parsed = urlparse(health_url)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise OfficialDataResetError(
            "invalid_health_url",
            "The host check must use a credential-free loopback HTTP or HTTPS address.",
        )
    start, end = host_port_range
    if not (1 <= start <= end <= 65535) or end - start > 99:
        raise OfficialDataResetError(
            "invalid_host_port_range",
            "The host port range must contain between 1 and 100 valid TCP ports.",
        )
    host = f"[{parsed.hostname}]" if parsed.hostname == "::1" else parsed.hostname
    path = parsed.path or "/healthz"
    suffix = f"?{parsed.query}" if parsed.query else ""
    return [f"{parsed.scheme}://{host}:{port}{path}{suffix}" for port in range(start, end + 1)]


def _probe_host_port_range(
    health_url: str,
    *,
    host_port_range: tuple[int, int],
    probe: HostProbe,
) -> int | None:
    for candidate in _health_urls_for_port_range(health_url, host_port_range=host_port_range):
        if probe(candidate):
            parsed = urlparse(candidate)
            return parsed.port
    return None


def _host_listener_is_running(health_url: str) -> bool:
    parsed = urlparse(health_url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise OfficialDataResetError(
            "invalid_health_url",
            "The host check must use a loopback HTTP or HTTPS address.",
        )
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((parsed.hostname, port), timeout=1.0):
            return True
    except ConnectionRefusedError:
        return False
    except OSError as error:
        # Windows and POSIX use different fields for a refused loopback
        # connection.  Any other socket failure is ambiguous and must not be
        # treated as proof that the host is stopped.
        if getattr(error, "winerror", None) == 10061 or getattr(error, "errno", None) in {61, 111}:
            return False
        raise OfficialDataResetError(
            "host_state_unknown",
            "The local host state could not be verified. Stop the startup task and retry.",
        ) from error


def _path_contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def _table_counts(database_path: Path, tables: tuple[str, ...]) -> dict[str, int]:
    connection = sqlite3.connect(f"file:{database_path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        return {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in tables
        }
    finally:
        connection.close()


def _verify_empty_database(database_path: Path) -> dict[str, int]:
    if database_readiness(database_path) != "ok":
        raise OfficialDataResetError(
            "empty_database_not_ready",
            "The empty database candidate did not pass integrity, schema, and migration checks.",
        )
    connection = sqlite3.connect(f"file:{database_path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        integrity = connection.execute("PRAGMA quick_check").fetchone()
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        connection.close()
    if not integrity or integrity[0] != "ok" or foreign_keys:
        raise OfficialDataResetError(
            "empty_database_integrity_failed",
            "The empty database candidate failed SQLite or foreign-key verification.",
        )
    counts = _table_counts(database_path, _ALL_DATA_TABLES)
    if any(counts.values()):
        raise OfficialDataResetError(
            "empty_database_contains_rows",
            "The replacement database contains operational rows and was refused.",
        )
    return counts


def _verify_isolated_restore(snapshot: Path, *, source_database: Path) -> None:
    workspace = Path(tempfile.mkdtemp(prefix="sing-yin-reset-restore-"))
    restored: RosterWorkflow | None = None
    try:
        backups = workspace / "backups"
        backups.mkdir()
        copied_snapshot = backups / snapshot.name
        shutil.copy2(snapshot, copied_snapshot)
        shutil.copy2(snapshot.with_suffix(".manifest.json"), copied_snapshot.with_suffix(".manifest.json"))
        restored_database = workspace / "restored.sqlite3"
        restored = RosterWorkflow(
            database_path=restored_database,
            backup_dir=backups,
            seed_path=None,
        )
        restored.bootstrap()
        restored.restore_backup(copied_snapshot)
        if not restored.reconcile_fairness().balanced:
            raise OfficialDataResetError(
                "isolated_restore_fairness_failed",
                "The isolated recovery rehearsal failed fairness reconciliation.",
            )
        if _table_counts(source_database, _RESTORE_COMPARISON_TABLES) != _table_counts(
            restored_database,
            _RESTORE_COMPARISON_TABLES,
        ):
            raise OfficialDataResetError(
                "isolated_restore_counts_changed",
                "The isolated recovery rehearsal did not preserve operational row counts.",
            )
    finally:
        cleanup_error: Exception | None = None
        if restored is not None:
            try:
                restored._dispose_database_connections()
            except Exception as error:  # pragma: no cover - defensive fail-closed path
                cleanup_error = error
        try:
            shutil.rmtree(workspace)
        except Exception as error:
            cleanup_error = cleanup_error or error
        if workspace.exists() or cleanup_error is not None:
            raise OfficialDataResetError(
                "isolated_restore_cleanup_failed",
                "The isolated restore workspace or database engine could not be proven closed and removed.",
            ) from cleanup_error


def _validate_public_share_attestation(
    settings: PublicRosterShareSettings,
    *,
    attest_no_public_share_gateway: bool,
) -> None:
    configured_fields_present = settings.enabled or bool(settings.base_url) or bool(settings.admin_token)
    if not configured_fields_present:
        if not attest_no_public_share_gateway:
            raise OfficialDataResetError(
                "public_share_gateway_unattested",
                "Refused because no public-share gateway is configured. Re-run only after explicitly attesting that this host has never issued public roster links.",
            )
        return
    effective = PublicRosterShareSettings(
        enabled=True,
        base_url=settings.base_url,
        admin_token=settings.admin_token,
        timeout_seconds=settings.timeout_seconds,
    )
    if not effective.configured:
        raise OfficialDataResetError(
            "public_share_configuration_incomplete",
            "Refused because public-share settings are present but incomplete; old links cannot be checked safely.",
        )


def _revoke_all_public_shares(
    workflow: RosterWorkflow,
    *,
    settings: PublicRosterShareSettings,
    gateway: PublicRosterShareGateway | None,
    attest_no_public_share_gateway: bool,
) -> dict[str, Any]:
    _validate_public_share_attestation(
        settings,
        attest_no_public_share_gateway=attest_no_public_share_gateway,
    )
    configured_fields_present = settings.enabled or bool(settings.base_url) or bool(settings.admin_token)
    if not configured_fields_present:
        return {
            "status": "attested_not_configured",
            "attestation": "explicit_no_gateway",
            "discoveredCount": 0,
            "revokedCount": 0,
            "remainingCount": 0,
        }
    effective = PublicRosterShareSettings(
        enabled=True,
        base_url=settings.base_url,
        admin_token=settings.admin_token,
        timeout_seconds=settings.timeout_seconds,
    )
    if not effective.configured:
        raise OfficialDataResetError(
            "public_share_configuration_incomplete",
            "Refused because public-share settings are present but incomplete; old links cannot be checked safely.",
        )
    service = PublicRosterShareService(workflow, settings=effective, gateway=gateway)
    try:
        existing = service.list_shares()
        for share in existing:
            service.revoke_share(share.share_id)
        remaining = service.list_shares()
    except Exception as error:
        raise OfficialDataResetError(
            "public_share_revocation_failed",
            "Refused because every existing public roster link could not be revoked and verified.",
        ) from error
    if remaining:
        raise OfficialDataResetError(
            "public_shares_remain",
            "Refused because public roster links remain after the revocation pass.",
        )
    return {
        "status": "revoked" if existing else "configured_none_found",
        "attestation": None,
        "discoveredCount": len(existing),
        "revokedCount": len(existing),
        "remainingCount": 0,
    }


def _managed_backup_files(backup_dir: Path) -> list[Path]:
    if not backup_dir.is_dir():
        return []
    return sorted(
        [
            path
            for path in backup_dir.iterdir()
            if path.is_file() and path.name.endswith(_MANAGED_BACKUP_SUFFIXES)
        ],
        key=lambda path: path.name,
    )


def _quarantine_managed_backups(backup_dir: Path, archive_dir: Path) -> list[tuple[Path, Path]]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    moved: list[tuple[Path, Path]] = []
    try:
        for source in _managed_backup_files(backup_dir):
            destination = archive_dir / "managed-backups" / source.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, destination)
            moved.append((source, destination))
    except OSError as error:
        try:
            _restore_quarantined_backups(moved)
        except OSError:
            pass
        raise OfficialDataResetError(
            "backup_quarantine_failed",
            "Refused because the old managed backup inventory could not be quarantined safely.",
        ) from error
    return moved


def _restore_quarantined_backups(moved: list[tuple[Path, Path]]) -> None:
    for original, quarantined in reversed(moved):
        if not quarantined.exists():
            continue
        original.parent.mkdir(parents=True, exist_ok=True)
        os.replace(quarantined, original)


def _remove_managed_backups(backup_dir: Path) -> None:
    for path in _managed_backup_files(backup_dir):
        path.unlink(missing_ok=True)


def _create_empty_baseline_snapshot(
    database_path: Path,
    backup_dir: Path,
    verifier: RosterWorkflow,
) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    if _managed_backup_files(backup_dir):
        raise OfficialDataResetError(
            "baseline_directory_not_empty",
            "The active backup directory was not empty before baseline creation.",
        )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    snapshot = backup_dir / f"{stamp}-official-reset-empty-baseline.sqlite3"
    temporary = snapshot.with_suffix(".sqlite3.tmp")
    manifest = snapshot.with_suffix(".manifest.json")
    try:
        _copy_sqlite_database(database_path, temporary)
        os.replace(temporary, snapshot)
        manifest.write_text(
            json.dumps(
                {
                    "eventType": "official_reset_empty_baseline",
                    "rosterWeekId": None,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                    "database": database_path.name,
                    "sha256": _sha256(snapshot),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        if not verifier.verify_backup(snapshot).get("valid"):
            raise OfficialDataResetError(
                "empty_baseline_not_verified",
                "The empty baseline snapshot did not pass verification.",
            )
        return snapshot
    except Exception:
        snapshot.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)


def _restore_quarantined_snapshot(snapshot: Path, database_path: Path, *, expected_counts: dict[str, int]) -> None:
    candidate = database_path.with_name(f".{database_path.name}.rollback-{secrets.token_hex(8)}.tmp.sqlite3")
    try:
        _copy_sqlite_database(snapshot, candidate)
        migrate_database(candidate)
        if database_readiness(candidate) != "ok":
            raise RuntimeError("rollback candidate not ready")
        if _table_counts(candidate, _ALL_DATA_TABLES) != expected_counts:
            raise RuntimeError("rollback counts changed")
        _remove_sidecars(database_path)
        os.replace(candidate, database_path)
        if database_readiness(database_path) != "ok":
            raise RuntimeError("rollback installation not ready")
        if _table_counts(database_path, _ALL_DATA_TABLES) != expected_counts:
            raise RuntimeError("rollback installation counts changed")
    finally:
        _remove_sidecars(candidate)
        candidate.unlink(missing_ok=True)


def _copy_sqlite_database(source_path: Path, destination_path: Path) -> None:
    destination_path.unlink(missing_ok=True)
    source = sqlite3.connect(f"file:{source_path.resolve().as_posix()}?mode=ro", uri=True)
    destination = sqlite3.connect(str(destination_path))
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()


def _checkpoint_database(database_path: Path) -> None:
    connection = sqlite3.connect(str(database_path), timeout=5)
    try:
        result = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if result and int(result[0]) != 0:
            raise OfficialDataResetError(
                "database_busy",
                "Refused because another process still holds the SQLite database.",
            )
    finally:
        connection.close()


def _existing_sidecars(database_path: Path) -> list[Path]:
    return [Path(f"{database_path}{suffix}") for suffix in _SQLITE_SIDECAR_SUFFIXES if Path(f"{database_path}{suffix}").exists()]


def _remove_sidecars(database_path: Path) -> None:
    for sidecar in _existing_sidecars(database_path):
        sidecar.unlink(missing_ok=True)


def _restrict_archive_permissions(path: Path) -> None:
    if os.name != "nt":
        path.chmod(0o700)
        return
    user = getpass.getuser()
    result = subprocess.run(
        [
            "icacls",
            str(path),
            "/inheritance:r",
            "/grant:r",
            f"{user}:(OI)(CI)F",
            "*S-1-5-18:(OI)(CI)F",
            "*S-1-5-32-544:(OI)(CI)F",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode != 0:
        raise OfficialDataResetError(
            "archive_permissions_failed",
            "Refused because the retired-data archive could not be restricted to local administrators.",
        )


def _write_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = report_path.with_name(f".{report_path.name}.{secrets.token_hex(4)}.tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, report_path)


def _preflight_report_path(report_path: Path) -> None:
    """Prove sanitized evidence can be written before any reset mutation."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    probe = report_path.with_name(f".{report_path.name}.{secrets.token_hex(4)}.probe")
    try:
        probe.write_text("{}\n", encoding="utf-8")
        probe.unlink()
    except OSError as error:
        probe.unlink(missing_ok=True)
        raise OfficialDataResetError(
            "report_path_not_writable",
            "Refused because the sanitized reset report cannot be written at the configured path.",
        ) from error


def _archive_id() -> str:
    return f"reset-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(4)}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_host_port_range(value: str) -> tuple[int, int]:
    try:
        start_text, separator, end_text = value.partition("-")
        start = int(start_text)
        end = int(end_text if separator else start_text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use PORT or START-END, for example 8080-8099.") from error
    if not (1 <= start <= end <= 65535) or end - start > 99:
        raise argparse.ArgumentTypeError("The range must contain between 1 and 100 valid TCP ports.")
    return start, end


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--health-url", default=DEFAULT_HEALTH_URL)
    parser.add_argument(
        "--host-port-range",
        type=_parse_host_port_range,
        default=DEFAULT_HOST_PORT_RANGE,
        metavar="START-END",
        help="Loopback roster-host ports that must all be stopped (default: 8080-8099).",
    )
    parser.add_argument(
        "--attest-no-public-share-gateway",
        action="store_true",
        help="Record an explicit operator attestation that this host has never issued public roster links.",
    )
    parser.add_argument("--confirm", required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = reset_official_data(
            ResetPaths(args.database, args.backup_dir, args.archive_dir, args.report),
            confirmation=args.confirm,
            health_url=args.health_url,
            host_port_range=args.host_port_range,
            attest_no_public_share_gateway=args.attest_no_public_share_gateway,
        )
    except OfficialDataResetError as error:
        print(f"RESET REFUSED [{error.reason_code}]: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
