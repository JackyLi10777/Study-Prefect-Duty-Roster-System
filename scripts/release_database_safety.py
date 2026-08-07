"""Prepare and install a schema-bound Windows release rollback snapshot.

The ``prepare`` command deliberately imports the application from the previous
immutable release bundle.  This prevents candidate code from migrating the
production database before the rollback snapshot exists.  The ``restore``
command uses only the Python standard library so it can reinstall the exact
verified bytes even when neither application revision can bootstrap the
currently migrated database.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
from typing import Any
from uuid import uuid4


SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")
COUNTED_TABLES = (
    "prefects",
    "prefect_availability",
    "roster_weeks",
    "roster_assignments",
    "fairness_ledger",
    "leave_adjustments",
    "leave_declarations",
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REVISION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ReleaseDatabaseSafetyError(RuntimeError):
    """A fail-closed release database safety check did not pass."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_plain_file(path: Path, *, label: str) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ReleaseDatabaseSafetyError(f"{label} must be an existing ordinary file.")
    return path.resolve(strict=True)


def _sidecar_paths(database_path: Path) -> tuple[Path, ...]:
    return tuple(Path(f"{database_path}{suffix}") for suffix in SIDECAR_SUFFIXES)


def _sqlite_inspection(path: Path, *, immutable: bool) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    immutable_flag = "&immutable=1" if immutable else ""
    connection = sqlite3.connect(
        f"file:{resolved.as_posix()}?mode=ro{immutable_flag}",
        uri=True,
    )
    try:
        integrity_rows = connection.execute("PRAGMA integrity_check").fetchall()
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        table_names = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        revisions = (
            {
                str(row[0])
                for row in connection.execute(
                    "SELECT version_num FROM alembic_version"
                ).fetchall()
            }
            if "alembic_version" in table_names
            else set()
        )
    finally:
        connection.close()
    integrity = "ok" if integrity_rows == [("ok",)] else "failed"
    return {
        "foreignKeyErrors": foreign_key_errors,
        "integrity": integrity,
        "revisions": revisions,
        "tableNames": table_names,
    }


def _require_database_revision(
    path: Path,
    *,
    expected_revision: str,
    immutable: bool,
    label: str,
) -> dict[str, Any]:
    inspection = _sqlite_inspection(path, immutable=immutable)
    if inspection["integrity"] != "ok":
        raise ReleaseDatabaseSafetyError(f"{label} failed SQLite integrity_check.")
    if inspection["foreignKeyErrors"]:
        raise ReleaseDatabaseSafetyError(f"{label} failed SQLite foreign_key_check.")
    if inspection["revisions"] != {expected_revision}:
        actual = ",".join(sorted(inspection["revisions"])) or "missing"
        raise ReleaseDatabaseSafetyError(
            f"{label} schema revision is {actual}; expected {expected_revision}."
        )
    return inspection


def _activate_release_root(release_root: Path) -> tuple[type[Any], Any]:
    root = release_root.resolve(strict=True)
    if not (root / "nicegui_app").is_dir() or not (root / "migrations").is_dir():
        raise ReleaseDatabaseSafetyError(
            "The requested release root does not contain the application and migrations."
        )
    sys.path.insert(0, str(root))
    os.chdir(root)

    from nicegui_app.persistence.database import current_migration_heads
    from nicegui_app.services.roster_workflow import RosterWorkflow

    module = sys.modules.get("nicegui_app")
    module_file = getattr(module, "__file__", None)
    if module_file is None or not Path(module_file).resolve().is_relative_to(root):
        raise ReleaseDatabaseSafetyError(
            "The application was not imported from the requested immutable release root."
        )
    return RosterWorkflow, current_migration_heads


def _release_heads(release_root: Path) -> list[str]:
    _workflow_type, current_migration_heads = _activate_release_root(release_root)
    heads = sorted(str(head) for head in current_migration_heads())
    if len(heads) != 1 or not REVISION_PATTERN.fullmatch(heads[0]):
        raise ReleaseDatabaseSafetyError(
            "The release must expose exactly one simple Alembic migration head."
        )
    return heads


def _dispose_workflow(workflow: Any | None) -> None:
    if workflow is None:
        return
    disposer = getattr(workflow, "_dispose_database_connections", None)
    if callable(disposer):
        disposer()


def _table_counts(path: Path) -> dict[str, int]:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        return {
            table: int(
                connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            )
            for table in COUNTED_TABLES
        }
    finally:
        connection.close()


def _audit_count(path: Path) -> int:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        return int(connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0])
    finally:
        connection.close()


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _bind_snapshot_manifest(snapshot_path: Path, *, schema_revision: str) -> None:
    """Bind the previous release's manifest to both exact bytes and schema."""

    manifest_path = _require_plain_file(
        snapshot_path.with_suffix(".manifest.json"),
        label="Rollback manifest",
    )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReleaseDatabaseSafetyError("Rollback manifest is unreadable.") from error
    snapshot_sha256 = _sha256(snapshot_path)
    if not isinstance(manifest, dict) or manifest.get("sha256") != snapshot_sha256:
        raise ReleaseDatabaseSafetyError(
            "Rollback manifest is not bound to the snapshot checksum."
        )
    recorded_revision = manifest.get("schemaRevision")
    if recorded_revision not in (None, schema_revision):
        raise ReleaseDatabaseSafetyError(
            "Rollback manifest is already bound to a different schema revision."
        )
    manifest["schemaRevision"] = schema_revision
    temporary = manifest_path.with_name(f".{manifest_path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, manifest_path)
    finally:
        temporary.unlink(missing_ok=True)


def _prepare(args: argparse.Namespace) -> dict[str, Any]:
    release_root = Path(args.release_root).resolve(strict=True)
    database_path = _require_plain_file(
        Path(args.database_path),
        label="Production database",
    )
    backup_dir = Path(args.backup_dir).resolve()
    report_path = Path(args.report_path).resolve()
    expected_revision = str(args.expected_revision)
    if not REVISION_PATTERN.fullmatch(expected_revision):
        raise ReleaseDatabaseSafetyError("Expected revision is not a simple Alembic revision.")

    workflow_type, current_migration_heads = _activate_release_root(release_root)
    release_heads = sorted(str(head) for head in current_migration_heads())
    if release_heads != [expected_revision]:
        raise ReleaseDatabaseSafetyError(
            "The previous immutable release code does not match the expected migration head."
        )
    _require_database_revision(
        database_path,
        expected_revision=expected_revision,
        immutable=False,
        label="Stopped production database",
    )

    official = None
    isolated = None
    workspace: Path | None = None
    try:
        official = workflow_type(
            database_path=database_path,
            backup_dir=backup_dir,
            seed_path=None,
        )
        official.bootstrap()
        if official.sessions is None or bool(getattr(official, "diagnostic_only", False)):
            raise ReleaseDatabaseSafetyError(
                "The previous immutable release could not open the production database write-ready."
            )
        _require_database_revision(
            database_path,
            expected_revision=expected_revision,
            immutable=False,
            label="Bootstrapped production database",
        )
        fairness = official.reconcile_fairness()
        if not fairness.balanced:
            raise ReleaseDatabaseSafetyError(
                "Rollback snapshot refused because fairness reconciliation failed."
            )

        snapshot_path = Path(official.create_verified_backup()).resolve(strict=True)
        try:
            snapshot_path.relative_to(backup_dir)
        except ValueError as error:
            raise ReleaseDatabaseSafetyError(
                "The previous release wrote its snapshot outside the controlled backup directory."
            ) from error
        _bind_snapshot_manifest(
            snapshot_path,
            schema_revision=expected_revision,
        )
        verification = official.verify_backup(snapshot_path)
        if not verification.get("valid"):
            raise ReleaseDatabaseSafetyError(
                "The previous release did not verify its new rollback snapshot."
            )
        if verification.get("schemaRevision") != expected_revision:
            raise ReleaseDatabaseSafetyError(
                "The rollback snapshot does not retain the previous release schema revision."
            )
        if verification.get("migrationRequired"):
            raise ReleaseDatabaseSafetyError(
                "The rollback snapshot unexpectedly requires a migration."
            )

        workspace = Path(tempfile.mkdtemp(prefix="sing-yin-release-rollback-proof-"))
        isolated_backups = workspace / "backups"
        isolated_backups.mkdir(parents=True)
        copied_snapshot = isolated_backups / snapshot_path.name
        copied_manifest = copied_snapshot.with_suffix(".manifest.json")
        shutil.copy2(snapshot_path, copied_snapshot)
        shutil.copy2(snapshot_path.with_suffix(".manifest.json"), copied_manifest)

        isolated_database = workspace / "restored.sqlite3"
        isolated = workflow_type(
            database_path=isolated_database,
            backup_dir=isolated_backups,
            seed_path=None,
        )
        isolated.bootstrap()
        isolated.restore_backup(copied_snapshot)
        isolated_fairness = isolated.reconcile_fairness()
        if not isolated_fairness.balanced:
            raise ReleaseDatabaseSafetyError(
                "The isolated rollback proof failed fairness reconciliation."
            )
        source_counts = _table_counts(database_path)
        restored_counts = _table_counts(isolated_database)
        if source_counts != restored_counts:
            raise ReleaseDatabaseSafetyError(
                "The isolated rollback proof has different operational row counts."
            )
        source_audits = _audit_count(database_path)
        restored_audits = _audit_count(isolated_database)
        if restored_audits != source_audits + 1:
            raise ReleaseDatabaseSafetyError(
                "The isolated rollback proof did not append exactly one restore audit event."
            )
        _require_database_revision(
            isolated_database,
            expected_revision=expected_revision,
            immutable=False,
            label="Isolated restored database",
        )

        payload: dict[str, Any] = {
            "checkedAt": datetime.now(timezone.utc).isoformat(),
            "fairnessBalanced": True,
            "integrity": str(verification.get("integrity")),
            "isolatedRestore": True,
            "manifestSha256": str(verification.get("manifestSha256")),
            "restoreAuditAppended": True,
            "rowCountsMatched": True,
            "schemaRevision": expected_revision,
            "sha256": str(verification.get("sha256")),
            "snapshotFile": snapshot_path.name,
            "status": "pass",
            "tableCount": int(verification.get("tableCount", 0)),
        }
        _write_report(report_path, payload)
        return payload
    finally:
        _dispose_workflow(isolated)
        _dispose_workflow(official)
        if workspace is not None:
            shutil.rmtree(workspace, ignore_errors=True)


def _validated_restore_source(args: argparse.Namespace) -> tuple[Path, Path, str, str]:
    snapshot_path = _require_plain_file(Path(args.snapshot_path), label="Rollback snapshot")
    manifest_path = _require_plain_file(Path(args.manifest_path), label="Rollback manifest")
    expected_manifest = snapshot_path.with_suffix(".manifest.json")
    if manifest_path != expected_manifest:
        raise ReleaseDatabaseSafetyError(
            "Rollback manifest must be the snapshot's matching .manifest.json file."
        )
    if snapshot_path.suffix != ".sqlite3":
        raise ReleaseDatabaseSafetyError("Rollback snapshot must use the .sqlite3 extension.")
    for sidecar in _sidecar_paths(snapshot_path):
        if sidecar.exists():
            raise ReleaseDatabaseSafetyError(
                "Rollback snapshot is not self-contained because a SQLite sidecar exists."
            )

    expected_sha256 = str(args.expected_sha256).lower()
    if not SHA256_PATTERN.fullmatch(expected_sha256):
        raise ReleaseDatabaseSafetyError("Expected rollback SHA-256 is malformed.")
    expected_revision = str(args.expected_revision)
    if not REVISION_PATTERN.fullmatch(expected_revision):
        raise ReleaseDatabaseSafetyError("Expected revision is not a simple Alembic revision.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReleaseDatabaseSafetyError("Rollback manifest is unreadable.") from error
    if not isinstance(manifest, dict) or manifest.get("sha256") != expected_sha256:
        raise ReleaseDatabaseSafetyError(
            "Rollback manifest is not bound to the expected snapshot checksum."
        )
    if manifest.get("schemaRevision") != expected_revision:
        raise ReleaseDatabaseSafetyError(
            "Rollback manifest is not bound to the expected schema revision."
        )
    if _sha256(snapshot_path) != expected_sha256:
        raise ReleaseDatabaseSafetyError(
            "Rollback snapshot does not match the expected SHA-256."
        )
    _require_database_revision(
        snapshot_path,
        expected_revision=expected_revision,
        immutable=True,
        label="Rollback snapshot",
    )
    return snapshot_path, manifest_path, expected_sha256, expected_revision


def _restore(args: argparse.Namespace) -> dict[str, Any]:
    snapshot_path, _manifest_path, expected_sha256, expected_revision = (
        _validated_restore_source(args)
    )
    database_argument = Path(args.database_path)
    database_parent = database_argument.parent.resolve(strict=True)
    database_path = database_parent / database_argument.name
    if database_path.suffix != ".sqlite3" or database_path.is_symlink():
        raise ReleaseDatabaseSafetyError(
            "Production database target must be a non-symlink .sqlite3 path."
        )
    if not database_path.exists() or not database_path.is_file():
        raise ReleaseDatabaseSafetyError(
            "Production database target must be an existing ordinary file."
        )
    if database_path.resolve() == snapshot_path:
        raise ReleaseDatabaseSafetyError(
            "Rollback snapshot and production database must be separate files."
        )

    target_sidecars = _sidecar_paths(database_path)
    for sidecar in target_sidecars:
        if sidecar.exists() and (sidecar.is_symlink() or not sidecar.is_file()):
            raise ReleaseDatabaseSafetyError(
                "Production SQLite sidecars must be ordinary files before rollback."
            )

    original_sha256 = _sha256(database_path)
    original_sidecar_sha256 = {
        sidecar: _sha256(sidecar) for sidecar in target_sidecars if sidecar.exists()
    }
    staged_path = database_parent / (
        f".{database_path.name}.release-rollback-{uuid4().hex}.tmp.sqlite3"
    )
    database_quarantine = database_parent / (
        f".{database_path.name}.release-rollback-{uuid4().hex}.quarantine"
    )
    sidecar_quarantines: list[tuple[Path, Path]] = []
    failed_install: Path | None = None
    original_quarantined = False
    installed = False
    committed = False

    def restore_original() -> None:
        """Undo every target mutation and prove the original bytes returned."""

        nonlocal failed_install, installed, original_quarantined
        if installed:
            if not database_path.is_file():
                raise ReleaseDatabaseSafetyError(
                    "Installed rollback database disappeared before recovery."
                )
            failed_install = database_parent / (
                f".{database_path.name}.release-rollback-{uuid4().hex}.failed"
            )
            os.replace(database_path, failed_install)
            installed = False
        if original_quarantined:
            if not database_quarantine.is_file():
                raise ReleaseDatabaseSafetyError(
                    "Original production database quarantine is missing."
                )
            os.replace(database_quarantine, database_path)
            original_quarantined = False
        for original, quarantine in reversed(sidecar_quarantines):
            if quarantine.exists():
                if original.exists():
                    raise ReleaseDatabaseSafetyError(
                        "A production SQLite sidecar reappeared during recovery."
                    )
                os.replace(quarantine, original)
        if not database_path.is_file() or _sha256(database_path) != original_sha256:
            raise ReleaseDatabaseSafetyError(
                "Original production database checksum was not restored."
            )
        for sidecar in target_sidecars:
            expected_sidecar_sha256 = original_sidecar_sha256.get(sidecar)
            if expected_sidecar_sha256 is None:
                if sidecar.exists():
                    raise ReleaseDatabaseSafetyError(
                        "An unexpected production SQLite sidecar appeared during recovery."
                    )
            elif not sidecar.is_file() or _sha256(sidecar) != expected_sidecar_sha256:
                raise ReleaseDatabaseSafetyError(
                    "Original production SQLite sidecar checksum was not restored."
                )
        if failed_install is not None:
            failed_install.unlink(missing_ok=True)
            failed_install = None

    try:
        with snapshot_path.open("rb") as source, staged_path.open("xb") as destination:
            shutil.copyfileobj(source, destination, length=1024 * 1024)
            destination.flush()
            os.fsync(destination.fileno())
        if _sha256(staged_path) != expected_sha256:
            raise ReleaseDatabaseSafetyError(
                "Staged rollback copy does not match the expected SHA-256."
            )
        _require_database_revision(
            staged_path,
            expected_revision=expected_revision,
            immutable=True,
            label="Staged rollback database",
        )

        for sidecar in target_sidecars:
            if not sidecar.exists():
                continue
            quarantine = database_parent / (
                f".{sidecar.name}.release-rollback-{uuid4().hex}.quarantine"
            )
            os.replace(sidecar, quarantine)
            sidecar_quarantines.append((sidecar, quarantine))
        os.replace(database_path, database_quarantine)
        original_quarantined = True
        os.replace(staged_path, database_path)
        installed = True

        installed_sha256 = _sha256(database_path)
        if installed_sha256 != expected_sha256:
            raise ReleaseDatabaseSafetyError(
                "Installed rollback database does not match the expected SHA-256."
            )
        inspection = _require_database_revision(
            database_path,
            expected_revision=expected_revision,
            immutable=True,
            label="Installed rollback database",
        )
        committed = True
        database_quarantine_removed = False
        try:
            database_quarantine.unlink()
            database_quarantine_removed = True
            original_quarantined = False
        except OSError:
            # The installed database has already passed checksum, schema, and
            # integrity verification.  A Windows scanner can still hold the
            # old quarantine briefly; that cleanup failure must not make the
            # proven rollback appear to have failed or trigger a second
            # database replacement.  Keep the outcome explicit so operators
            # can remove the stale quarantine after the lock is released.
            pass
        for _original, quarantine in sidecar_quarantines:
            quarantine.unlink(missing_ok=True)
        return {
            "atomicReplace": True,
            "databaseQuarantineRemoved": database_quarantine_removed,
            "integrity": str(inspection["integrity"]),
            "restored": True,
            "schemaRevision": expected_revision,
            "sha256": installed_sha256,
            "sidecarsRemoved": len(sidecar_quarantines),
            "status": "pass",
        }
    except BaseException as error:
        if not committed and (
            installed or original_quarantined or sidecar_quarantines
        ):
            try:
                restore_original()
            except Exception as recovery_error:
                raise ReleaseDatabaseSafetyError(
                    "Rollback failed and the original database transaction could not be restored."
                ) from recovery_error
        raise error
    finally:
        staged_path.unlink(missing_ok=True)
        if failed_install is not None:
            failed_install.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    head = subparsers.add_parser("head", help="Read one immutable release's Alembic head.")
    head.add_argument("--release-root", required=True, type=Path)

    prepare = subparsers.add_parser(
        "prepare",
        help="Create and prove a rollback snapshot with previous-release code.",
    )
    prepare.add_argument("--release-root", required=True, type=Path)
    prepare.add_argument("--database-path", required=True, type=Path)
    prepare.add_argument("--backup-dir", required=True, type=Path)
    prepare.add_argument("--report-path", required=True, type=Path)
    prepare.add_argument("--expected-revision", required=True)

    restore = subparsers.add_parser(
        "restore",
        help="Atomically install exact schema-bound rollback snapshot bytes.",
    )
    restore.add_argument("--database-path", required=True, type=Path)
    restore.add_argument("--snapshot-path", required=True, type=Path)
    restore.add_argument("--manifest-path", required=True, type=Path)
    restore.add_argument("--expected-sha256", required=True)
    restore.add_argument("--expected-revision", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "head":
            payload: dict[str, Any] = {
                "migrationHeads": _release_heads(args.release_root),
                "status": "pass",
            }
        elif args.command == "prepare":
            payload = _prepare(args)
        elif args.command == "restore":
            payload = _restore(args)
        else:  # pragma: no cover - argparse constrains this branch
            raise ReleaseDatabaseSafetyError("Unsupported command.")
    except Exception as error:
        failure = {
            "error": f"{type(error).__name__}: {error}",
            "status": "fail",
        }
        print(json.dumps(failure, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
