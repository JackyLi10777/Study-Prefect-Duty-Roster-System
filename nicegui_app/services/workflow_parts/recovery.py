"""Focused RosterWorkflow behavior extracted without changing its public API."""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache

from alembic.config import Config
from alembic.script import ScriptDirectory

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.persistence.database import current_migration_heads
from nicegui_app.services.workflow_dependencies import (
    BackupResult,
    BackupRunRecord,
    BytesIO,
    CommittedWriteBackupError,
    HandoverBackupPackage,
    MaintenanceModeError,
    Path,
    PrefectRecord,
    RosterWeekRecord,
    Session,
    ThreadPoolExecutor,
    WorkflowError,
    WorkflowMaintenanceError,
    ZIP_DEFLATED,
    ZipFile,
    create_session_factory,
    datetime,
    defaultdict,
    func,
    hashlib,
    json,
    required_database_tables,
    select,
    sessionmaker,
    sqlite3,
    uuid4,
)
from nicegui_app.services.workflow_fencing import fenced_workflow_write


_REQUIRED_DATABASE_TABLES = required_database_tables()
_RESTORABLE_CORE_TABLES = frozenset(
    {
        "alembic_version",
        "prefects",
        "prefect_availability",
        "roster_weeks",
        "roster_assignments",
        "fairness_ledger",
        "leave_adjustments",
        "leave_declarations",
        "audit_events",
        "backup_runs",
    }
)
_MINIMUM_RESTORABLE_REVISION = "0007"
_V12_PERSISTENCE_TABLES = _RESTORABLE_CORE_TABLES | frozenset(
    {
        "operation_commands",
        "backup_obligations",
        "external_share_outbox",
    }
)
# A backup must satisfy the table contract of the revision it claims to be.
# Keeping the map explicit forces future table-creating migrations to state
# which historical revisions legitimately predate the new table.
_REQUIRED_TABLES_BY_REVISION: dict[str, frozenset[str]] = {
    "0007": _RESTORABLE_CORE_TABLES,
    "0008": _V12_PERSISTENCE_TABLES,
    "0009": _V12_PERSISTENCE_TABLES,
    "0010": _V12_PERSISTENCE_TABLES,
    "0011": _V12_PERSISTENCE_TABLES,
}


@lru_cache(maxsize=1)
def _restorable_migration_revisions() -> frozenset[str]:
    """Return the supported linear migration chain from the current head to 0007."""

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    scripts = ScriptDirectory.from_config(config)
    heads = current_migration_heads()
    if len(heads) != 1:
        return frozenset()

    revisions: set[str] = set()
    revision: str | None = next(iter(heads))
    while revision is not None:
        script = scripts.get_revision(revision)
        if script is None:
            return frozenset()
        revisions.add(script.revision)
        if script.revision == _MINIMUM_RESTORABLE_REVISION:
            return frozenset(revisions)
        if not isinstance(script.down_revision, str):
            return frozenset()
        revision = script.down_revision
    return frozenset()


class RecoveryWorkflowMixin:
    def handover_readiness(self) -> dict[str, object]:
        """Return non-sensitive, practical checks for a successor's local handover."""
        with self._session() as session:
            prefect_count = session.scalar(
                select(func.count()).select_from(PrefectRecord).where(PrefectRecord.active.is_(True))
            ) or 0
            roster_count = session.scalar(select(func.count()).select_from(RosterWeekRecord)) or 0
        backup = self.backup_status()
        latest_verification = backup["latestVerification"] or {}
        return {
            "activePrefectCount": prefect_count,
            "rosterCount": roster_count,
            "verifiedBackup": bool(latest_verification.get("valid")),
            "backupPath": backup["latestPath"],
        }

    def backup_status(self) -> dict[str, object]:
        with self._session() as session:
            latest = session.scalar(select(BackupRunRecord).order_by(BackupRunRecord.created_at.desc()))
            latest_path = Path(latest.backup_path) if latest and latest.backup_path else None
            return {
                "databasePath": self.database_path,
                "backupDirectory": self.backup_dir,
                "latestSuccess": latest.success if latest else None,
                "latestPath": latest_path,
                "latestCreatedAt": latest.created_at if latest else None,
                "latestVerification": self.verify_backup(latest_path) if latest_path else None,
            }

    def verify_backup(self, backup_path: Path) -> dict[str, object]:
        """Validate a current or supported legacy snapshot without mutating it."""
        if not backup_path.exists() or not backup_path.is_file():
            return {"valid": False, "reasonCode": "missing_file", "error": "Backup file was not found."}
        if backup_path.suffix != ".sqlite3":
            return {"valid": False, "reasonCode": "invalid_extension", "error": "Backup file must use the .sqlite3 extension."}

        sqlite_sidecars = [sidecar for sidecar in self._sqlite_sidecar_paths(backup_path) if sidecar.exists()]
        if sqlite_sidecars:
            return {
                "valid": False,
                "reasonCode": "snapshot_sidecar_present",
                "error": "Backup is not self-contained because SQLite journal sidecars are present.",
            }

        try:
            connection = sqlite3.connect(
                f"file:{backup_path.resolve().as_posix()}?mode=ro&immutable=1",
                uri=True,
            )
            try:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
                table_rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
                table_names = {str(row[0]) for row in table_rows}
                revision_rows = (
                    connection.execute("SELECT version_num FROM alembic_version").fetchall()
                    if "alembic_version" in table_names
                    else []
                )
                pending_obligations = (
                    int(
                        connection.execute(
                            "SELECT COUNT(*) FROM backup_obligations WHERE status <> 'completed'"
                        ).fetchone()[0]
                    )
                    if "backup_obligations" in table_names
                    else 0
                )
            finally:
                connection.close()
        except sqlite3.Error as error:
            return {"valid": False, "reasonCode": "sqlite_unreadable", "error": f"SQLite could not open the backup: {error}"}

        try:
            checksum = self._sha256(backup_path)
        except OSError as error:
            return {
                "valid": False,
                "reasonCode": "missing_file",
                "integrity": integrity,
                "error": f"Backup file could not be read for checksum verification: {error}",
            }
        manifest_path = backup_path.with_suffix(".manifest.json")
        if not manifest_path.exists() or not manifest_path.is_file():
            return {
                "valid": False,
                "reasonCode": "manifest_missing",
                "integrity": integrity,
                "sha256": checksum,
                "error": "Backup is missing its checksum manifest.",
            }
        try:
            manifest_bytes = manifest_path.read_bytes()
            manifest = json.loads(manifest_bytes.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            return {
                "valid": False,
                "reasonCode": "manifest_unreadable",
                "integrity": integrity,
                "sha256": checksum,
                "error": f"Backup manifest could not be read: {error}",
            }
        if not isinstance(manifest, Mapping):
            return {
                "valid": False,
                "reasonCode": "manifest_invalid",
                "integrity": integrity,
                "sha256": checksum,
                "error": "Backup manifest must contain a JSON object.",
            }
        manifest_checksum = manifest.get("sha256")
        if not isinstance(manifest_checksum, str) or manifest_checksum != checksum:
            return {
                "valid": False,
                "reasonCode": "checksum_mismatch",
                "integrity": integrity,
                "sha256": checksum,
                "error": "Backup checksum does not match its manifest.",
            }
        if integrity != "ok":
            return {
                "valid": False,
                "reasonCode": "integrity_failed",
                "integrity": integrity,
                "sha256": checksum,
                "error": "SQLite integrity check failed.",
            }
        missing_core_tables = sorted(_RESTORABLE_CORE_TABLES - table_names)
        if missing_core_tables:
            return {
                "valid": False,
                "reasonCode": "schema_incomplete",
                "integrity": integrity,
                "sha256": checksum,
                "error": f"Backup is missing required core tables: {', '.join(missing_core_tables)}.",
            }
        revisions = {str(row[0]) for row in revision_rows}
        if len(revisions) != 1 or not revisions.issubset(_restorable_migration_revisions()):
            return {
                "valid": False,
                "reasonCode": "migration_unsupported",
                "integrity": integrity,
                "sha256": checksum,
                "error": "Backup migration revision is missing, unknown, or newer than this release.",
            }
        schema_revision = next(iter(revisions))
        required_revision_tables = _REQUIRED_TABLES_BY_REVISION.get(schema_revision)
        if required_revision_tables is None:
            return {
                "valid": False,
                "reasonCode": "migration_unsupported",
                "integrity": integrity,
                "sha256": checksum,
                "error": "Backup migration revision has no reviewed schema contract.",
            }
        missing_revision_tables = sorted(required_revision_tables - table_names)
        if missing_revision_tables:
            return {
                "valid": False,
                "reasonCode": "schema_incomplete",
                "integrity": integrity,
                "sha256": checksum,
                "error": (
                    f"Backup revision {schema_revision} is missing required tables: "
                    f"{', '.join(missing_revision_tables)}."
                ),
            }
        migration_required = revisions != current_migration_heads()
        if pending_obligations:
            return {
                "valid": False,
                "reasonCode": "backup_obligations_pending",
                "integrity": integrity,
                "sha256": checksum,
                "error": "Backup contains committed writes without a settled recovery snapshot.",
            }
        return {
            "valid": True,
            "reasonCode": "verified_migration_required" if migration_required else "verified",
            "integrity": integrity,
            "sha256": checksum,
            "manifestSha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "tableCount": len(table_names),
            "schemaRevision": schema_revision,
            "migrationRequired": migration_required,
        }

    def restore_backup(self, backup_path: Path) -> dict[str, object]:
        """Preflight a snapshot in isolation, then restore with automatic rollback."""
        try:
            with self.maintenance.maintenance("restore"):
                managed_directory = self.backup_dir.resolve()
                requested_path = backup_path.resolve()
                try:
                    requested_path.relative_to(managed_directory)
                except ValueError as error:
                    raise WorkflowError("Only snapshots in the managed backup directory can be restored.") from error

                staged_path: Path | None = None
                prepared_path: Path | None = None
                try:
                    staged_path, verification = self._stage_restore_source(requested_path)
                    prepared_path = self._prepare_restore_candidate(
                        staged_path,
                        expected_sha256=str(verification["sha256"]),
                    )
                    pre_restore = self._create_and_record_backup("pre_restore", None)
                    pre_restore_path = self._require_backup(pre_restore)
                    try:
                        self._install_prepared_database(prepared_path)
                        with self._session() as session:
                            self._audit(
                                session,
                                "backup_restored",
                                None,
                                {
                                    "restoredFrom": str(requested_path),
                                    "preRestoreBackup": str(pre_restore_path),
                                    "sha256": verification["sha256"],
                                    "sourceSchemaRevision": verification["schemaRevision"],
                                },
                            )
                            self._assert_fairness_reconciled(session)
                            session.commit()
                        restored_backup = self._create_and_record_backup("backup_restored", None)
                        restored_backup_path = self._require_backup(restored_backup, committed_event="backup_restored")
                    except Exception as error:
                        if prepared_path is not None:
                            prepared_path.unlink(missing_ok=True)
                        try:
                            rollback_verification = self.verify_backup(pre_restore_path)
                            if not rollback_verification.get("valid"):
                                raise WorkflowError("The pre-restore recovery snapshot is no longer valid.")
                            rollback_path = self._prepare_restore_candidate(
                                pre_restore_path,
                                expected_sha256=str(rollback_verification["sha256"]),
                            )
                            self._install_prepared_database(rollback_path)
                        except Exception as rollback_error:
                            self.maintenance.require_recovery_review(reason_code="restore_rollback_failed")
                            raise WorkflowError(
                                "Backup restore failed and automatic rollback could not be verified. "
                                "The system remains locked for recovery review."
                            ) from rollback_error
                        raise WorkflowError(
                            "Backup restore was not completed; the original database was restored automatically."
                        ) from error
                    return {
                        "restoredFrom": backup_path,
                        "preRestoreBackup": pre_restore_path,
                        "restoredBackup": restored_backup_path,
                    }
                finally:
                    if prepared_path is not None:
                        prepared_path.unlink(missing_ok=True)
                    if staged_path is not None:
                        staged_path.unlink(missing_ok=True)
                        staged_path.with_suffix(".manifest.json").unlink(missing_ok=True)
        except MaintenanceModeError as error:
            raise WorkflowMaintenanceError(str(error)) from error

    def _stage_restore_source(self, source_path: Path) -> tuple[Path, dict[str, object]]:
        """Copy one immutable source pair, then verify exactly the bytes used for restore."""

        if any(sidecar.exists() for sidecar in self._sqlite_sidecar_paths(source_path)):
            raise WorkflowError(
                "Backup verification failed: SQLite journal sidecars are not part of a managed snapshot."
            )
        staged_path = self.database_path.with_name(
            f".{self.database_path.name}.restore-source-{uuid4().hex}.sqlite3"
        )
        staged_manifest_path = staged_path.with_suffix(".manifest.json")
        try:
            self._copy_file_bytes(source_path, staged_path)
            self._copy_file_bytes(source_path.with_suffix(".manifest.json"), staged_manifest_path)
            verification = self.verify_backup(staged_path)
            if not verification.get("valid"):
                raise WorkflowError(
                    f"Backup verification failed: {verification.get('error', 'unknown error')}"
                )
            return staged_path, verification
        except Exception:
            staged_path.unlink(missing_ok=True)
            staged_manifest_path.unlink(missing_ok=True)
            raise

    def _prepare_restore_candidate(self, source_path: Path, *, expected_sha256: str) -> Path:
        """Clone, migrate and reconcile a candidate without touching live data."""
        prepared_path = self.database_path.with_name(
            f".{self.database_path.name}.restore-{uuid4().hex}.tmp.sqlite3"
        )
        sessions: sessionmaker[Session] | None = None
        try:
            self._copy_file_bytes(source_path, prepared_path)
            if self._sha256(prepared_path) != expected_sha256:
                raise WorkflowError(
                    "Backup source changed after verification; restore was stopped before migration."
                )
            sessions = create_session_factory(prepared_path)
            with sessions() as session:
                table_rows = session.connection().exec_driver_sql(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
                missing_tables = sorted(_REQUIRED_DATABASE_TABLES - {row[0] for row in table_rows})
                if missing_tables:
                    raise WorkflowError(
                        "Backup preflight failed: required schema tables are missing: "
                        f"{', '.join(missing_tables)}."
                    )
                revisions = {
                    str(row[0])
                    for row in session.connection().exec_driver_sql(
                        "SELECT version_num FROM alembic_version"
                    ).fetchall()
                }
                if revisions != current_migration_heads():
                    raise WorkflowError("Backup preflight failed: migration did not reach the current schema.")
                foreign_key_errors = session.connection().exec_driver_sql("PRAGMA foreign_key_check").fetchall()
                if foreign_key_errors:
                    raise WorkflowError("Backup preflight failed: foreign-key integrity is not valid.")
                pending_obligations = int(
                    session.connection().exec_driver_sql(
                        "SELECT COUNT(*) FROM backup_obligations WHERE status <> 'completed'"
                    ).scalar_one()
                )
                if pending_obligations:
                    raise WorkflowError(
                        "Backup preflight failed: recovery snapshot obligations are not settled."
                    )
                self._assert_fairness_reconciled(session)
            return prepared_path
        except Exception:
            if sessions is not None:
                engine = sessions.kw.get("bind")
                if engine is not None:
                    engine.dispose()
                sessions = None
            self._remove_sqlite_sidecars(prepared_path)
            prepared_path.unlink(missing_ok=True)
            raise
        finally:
            if sessions is not None:
                engine = sessions.kw.get("bind")
                if engine is not None:
                    engine.dispose()
            self._remove_sqlite_sidecars(prepared_path)

    def _install_prepared_database(self, prepared_path: Path) -> None:
        self._dispose_database_connections()
        self._remove_sqlite_sidecars(self.database_path)
        prepared_path.replace(self.database_path)
        self.sessions = create_session_factory(self.database_path)

    @staticmethod
    def _copy_file_bytes(source_path: Path, destination_path: Path) -> None:
        """Copy an immutable file through one open handle without reopening its path."""

        destination_path.unlink(missing_ok=True)
        with source_path.open("rb") as source, destination_path.open("xb") as destination:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                destination.write(block)

    @staticmethod
    def _remove_sqlite_sidecars(database_path: Path) -> None:
        for sidecar in RecoveryWorkflowMixin._sqlite_sidecar_paths(database_path):
            sidecar.unlink(missing_ok=True)

    @staticmethod
    def _sqlite_sidecar_paths(database_path: Path) -> tuple[Path, Path, Path]:
        return (
            Path(f"{database_path}-wal"),
            Path(f"{database_path}-shm"),
            Path(f"{database_path}-journal"),
        )

    def backups(self, limit: int = 12) -> list[dict[str, object]]:
        """List recent managed snapshots with current verification evidence."""
        if limit < 1:
            return []
        selected = self._managed_backup_candidates(limit=limit)
        if not selected:
            return []
        with ThreadPoolExecutor(max_workers=min(4, len(selected)), thread_name_prefix="backup-verify") as executor:
            verifications = list(executor.map(self.verify_backup, (path for path, _modified_at in selected)))
        return [
            {
                "path": path,
                "createdAt": datetime.fromtimestamp(modified_at),
                "verification": verification,
            }
            for (path, modified_at), verification in zip(selected, verifications, strict=True)
        ]

    def _managed_backup_candidates(self, *, limit: int | None = None) -> list[tuple[Path, float]]:
        """Return managed snapshots newest-first without performing expensive verification."""
        candidates: list[tuple[Path, float]] = []
        for path in self.backup_dir.glob("*.sqlite3"):
            try:
                modified_at = path.stat().st_mtime
            except OSError:
                continue
            candidates.append((path, modified_at))
        candidates.sort(key=lambda item: item[1], reverse=True)
        return candidates if limit is None else candidates[:limit]

    def backup_inventory(self, limit: int = 12) -> dict[str, object]:
        """Summarize recent snapshot trust without exposing raw verification errors."""
        items = self.backups(limit=limit)
        reason_counts: dict[str, int] = defaultdict(int)
        verified_count = 0
        for item in items:
            verification = item["verification"]
            if not isinstance(verification, dict):
                reason_counts["unknown"] += 1
                continue
            if verification.get("valid"):
                verified_count += 1
                continue
            reason_code = str(verification.get("reasonCode") or "unknown")
            reason_counts[reason_code] += 1
        return {
            "items": items,
            "checkedCount": len(items),
            "verifiedCount": verified_count,
            "invalidCount": len(items) - verified_count,
            "invalidReasonCounts": dict(sorted(reason_counts.items())),
        }

    def create_verified_backup(self) -> Path:
        """Create an operator-requested recovery snapshot without changing roster data."""
        with self.maintenance.serialized_operation():
            backup = self._create_and_record_backup("manual_verified_backup", None)
            backup_path = self._require_backup(backup)
            self._complete_backup_obligations_with_snapshot(backup_path)
            return backup_path

    def build_verified_handover_package(self) -> HandoverBackupPackage:
        """Package the latest verified managed snapshot for an operator-controlled handover copy."""
        source_backup_path: Path | None = None
        for candidate_path, _modified_at in self._managed_backup_candidates():
            if self.verify_backup(candidate_path).get("valid"):
                source_backup_path = candidate_path
                break
        if source_backup_path is None:
            raise WorkflowError("No verified backup is available for a handover package.")
        verification = self.verify_backup(source_backup_path)
        if not verification.get("valid"):
            raise WorkflowError(f"Backup verification failed: {verification.get('error', 'unknown error')}")
        staged_path: Path | None = None
        try:
            staged_path, verification = self._stage_restore_source(source_backup_path)
            staged_manifest_path = staged_path.with_suffix(".manifest.json")
            database_content = staged_path.read_bytes()
            manifest_content = staged_manifest_path.read_bytes()
            if hashlib.sha256(database_content).hexdigest() != verification["sha256"]:
                raise WorkflowError("Backup source changed after verification; handover packaging was stopped.")
            if hashlib.sha256(manifest_content).hexdigest() != verification["manifestSha256"]:
                raise WorkflowError("Backup manifest changed after verification; handover packaging was stopped.")

            manifest_name = source_backup_path.with_suffix(".manifest.json").name
            package = BytesIO()
            with ZipFile(package, mode="w", compression=ZIP_DEFLATED) as archive:
                archive.writestr(source_backup_path.name, database_content)
                archive.writestr(manifest_name, manifest_content)
                archive.writestr("README.txt", self._handover_package_readme(source_backup_path.name))
        finally:
            if staged_path is not None:
                staged_path.unlink(missing_ok=True)
                staged_path.with_suffix(".manifest.json").unlink(missing_ok=True)
        stamp = self._now().strftime("%Y%m%d-%H%M")
        return HandoverBackupPackage(
            filename=f"SYSS_Handover_Backup_{stamp}.zip",
            content=package.getvalue(),
            source_backup_path=source_backup_path,
        )

    @fenced_workflow_write(internal_backup=True)
    def _create_and_record_backup(self, event_type: str, roster_week_id: int | None) -> BackupResult:
        backup_path: Path | None = None
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = self._now().strftime("%Y%m%d-%H%M%S-%f")
            backup_path = self.backup_dir / f"{stamp}-{event_type}.sqlite3"
            temporary_path = backup_path.with_suffix(".sqlite3.tmp")
            source = sqlite3.connect(str(self.database_path))
            destination = sqlite3.connect(str(temporary_path))
            try:
                source.backup(destination)
            finally:
                destination.close()
                source.close()
            self._settle_snapshot_backup_obligations(temporary_path, backup_path)
            temporary_path.replace(backup_path)
            manifest_path = backup_path.with_suffix(".manifest.json")
            manifest_path.write_text(
                json.dumps(
                    {
                        "eventType": event_type,
                        "rosterWeekId": roster_week_id,
                        "createdAt": self._now().isoformat(),
                        "database": self.database_path.name,
                        "sha256": self._sha256(backup_path),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            verification = self.verify_backup(backup_path)
            if not verification.get("valid"):
                result = BackupResult(
                    False,
                    backup_path,
                    f"Snapshot verification failed: {verification.get('error', 'unknown error')}",
                )
            else:
                result = BackupResult(True, backup_path)
        except Exception as error:  # pragma: no cover - exercised by filesystem failures
            result = BackupResult(False, backup_path if backup_path and backup_path.exists() else None, str(error))
        try:
            self._record_backup_result(event_type, roster_week_id, result)
        except Exception as error:  # pragma: no cover - forced through a deterministic test seam
            return BackupResult(
                False,
                result.path,
                f"Backup evidence recording failed: {type(error).__name__}",
            )
        return result

    def _settle_snapshot_backup_obligations(self, snapshot_path: Path, recovery_path: Path) -> None:
        """Make a recovery snapshot independently write-ready without changing live state."""

        connection = sqlite3.connect(str(snapshot_path))
        normalized = False
        try:
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            if "backup_obligations" in tables:
                completed_at = self._now().strftime("%Y-%m-%d %H:%M:%S.%f")
                connection.execute(
                    """
                    UPDATE backup_obligations
                    SET status = 'completed', backup_path = ?, error = NULL, completed_at = ?
                    WHERE status <> 'completed'
                    """,
                    (str(recovery_path), completed_at),
                )
            connection.commit()
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            journal_mode = connection.execute("PRAGMA journal_mode = DELETE").fetchone()
            if journal_mode is None or str(journal_mode[0]).lower() != "delete":
                raise sqlite3.OperationalError(
                    "Recovery snapshot could not be finalized in DELETE journal mode."
                )
            connection.commit()
            normalized = True
        finally:
            connection.close()
        if normalized:
            self._remove_sqlite_sidecars(snapshot_path)

    def _record_backup_result(self, event_type: str, roster_week_id: int | None, result: BackupResult) -> None:
        """Persist snapshot evidence without allowing this secondary write to hide committed roster state."""
        with self._session() as session:
            session.add(
                BackupRunRecord(
                    event_type=event_type,
                    roster_week_id=roster_week_id,
                    backup_path=str(result.path) if result.path else None,
                    success=result.success,
                    error_message=result.error_message,
                    created_at=self._now(),
                )
            )
            session.commit()

    @staticmethod
    def _handover_package_readme(snapshot_name: str) -> str:
        return (
            "Sing Yin Study Prefect Duty Roster System — verified handover backup\n"
            "\n"
            "此封包只供學校批准的加密離機保存及交接使用，內含一份已驗證 SQLite 快照及其 SHA-256 manifest。"
            "請勿電郵、公開上載或傳送至未經批准的平台。\n"
            "\n"
            "還原方法：把此封包解壓至受控位置，將 SQLite 檔案及同名 manifest 放回系統的 data/backups/ 目錄，"
            "然後在「系統設定」選擇顯示為「已驗證」的快照。還原前系統會先建立安全快照。\n"
            "\n"
            "This package is for school-approved encrypted offline storage and handover only. It contains one verified SQLite snapshot and its SHA-256 manifest. Do not email, publicly upload, or share it through an unapproved service.\n"
            "\n"
            "Restore: extract both files to a controlled location, return the SQLite file and its matching manifest to data/backups/, then select a Verified snapshot in Settings. The system creates a safety snapshot before restore.\n"
            f"\nSnapshot included: {snapshot_name}\n"
        )

    @staticmethod
    def _require_backup(backup: BackupResult, *, committed_event: str | None = None) -> Path:
        if not backup.success or backup.path is None:
            if committed_event is not None:
                raise CommittedWriteBackupError(committed_event, backup.error_message)
            raise WorkflowError(f"Data was saved, but automatic backup failed: {backup.error_message or 'unknown error'}")
        return backup.path

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
