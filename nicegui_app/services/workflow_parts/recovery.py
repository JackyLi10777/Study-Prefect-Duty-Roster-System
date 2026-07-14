"""Focused RosterWorkflow behavior extracted without changing its public API."""

from __future__ import annotations

from nicegui_app.services.workflow_dependencies import *


_REQUIRED_DATABASE_TABLES = required_database_tables()


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
        """Validate a snapshot without mutating the live database."""
        required_tables = _REQUIRED_DATABASE_TABLES
        if not backup_path.exists() or not backup_path.is_file():
            return {"valid": False, "reasonCode": "missing_file", "error": "Backup file was not found."}
        if backup_path.suffix != ".sqlite3":
            return {"valid": False, "reasonCode": "invalid_extension", "error": "Backup file must use the .sqlite3 extension."}

        try:
            connection = sqlite3.connect(f"file:{backup_path.resolve().as_posix()}?mode=ro", uri=True)
            try:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
                table_rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
            finally:
                connection.close()
        except sqlite3.Error as error:
            return {"valid": False, "reasonCode": "sqlite_unreadable", "error": f"SQLite could not open the backup: {error}"}

        table_names = {row[0] for row in table_rows}
        missing_tables = sorted(required_tables - table_names)
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
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            return {
                "valid": False,
                "reasonCode": "manifest_unreadable",
                "integrity": integrity,
                "sha256": checksum,
                "error": f"Backup manifest could not be read: {error}",
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
        if missing_tables:
            return {
                "valid": False,
                "reasonCode": "schema_incomplete",
                "integrity": integrity,
                "sha256": checksum,
                "error": f"Backup is missing required tables: {', '.join(missing_tables)}.",
            }
        return {
            "valid": True,
            "reasonCode": "verified",
            "integrity": integrity,
            "sha256": checksum,
            "tableCount": len(table_names),
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

                verification = self.verify_backup(requested_path)
                if not verification.get("valid"):
                    raise WorkflowError(f"Backup verification failed: {verification.get('error', 'unknown error')}")

                prepared_path = self._prepare_restore_candidate(requested_path)
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
                            },
                        )
                        self._assert_fairness_reconciled(session)
                        session.commit()
                    restored_backup = self._create_and_record_backup("backup_restored", None)
                    restored_backup_path = self._require_backup(restored_backup, committed_event="backup_restored")
                except Exception as error:
                    prepared_path.unlink(missing_ok=True)
                    try:
                        rollback_path = self._prepare_restore_candidate(pre_restore_path)
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
                finally:
                    prepared_path.unlink(missing_ok=True)
                return {
                    "restoredFrom": backup_path,
                    "preRestoreBackup": pre_restore_path,
                    "restoredBackup": restored_backup_path,
                }
        except MaintenanceModeError as error:
            raise WorkflowMaintenanceError(str(error)) from error

    def _prepare_restore_candidate(self, source_path: Path) -> Path:
        """Clone, migrate and reconcile a candidate without touching live data."""
        prepared_path = self.database_path.with_name(
            f".{self.database_path.name}.restore-{uuid4().hex}.tmp.sqlite3"
        )
        sessions: sessionmaker[Session] | None = None
        try:
            self._copy_sqlite_database(source_path, prepared_path)
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
                foreign_key_errors = session.connection().exec_driver_sql("PRAGMA foreign_key_check").fetchall()
                if foreign_key_errors:
                    raise WorkflowError("Backup preflight failed: foreign-key integrity is not valid.")
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
    def _copy_sqlite_database(source_path: Path, destination_path: Path) -> None:
        destination_path.unlink(missing_ok=True)
        source = sqlite3.connect(str(source_path))
        destination = sqlite3.connect(str(destination_path))
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()

    @staticmethod
    def _remove_sqlite_sidecars(database_path: Path) -> None:
        for sidecar in (Path(f"{database_path}-wal"), Path(f"{database_path}-shm")):
            sidecar.unlink(missing_ok=True)

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
        backup = self._create_and_record_backup("manual_verified_backup", None)
        return self._require_backup(backup)

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
        manifest_path = source_backup_path.with_suffix(".manifest.json")
        package = BytesIO()
        with ZipFile(package, mode="w", compression=ZIP_DEFLATED) as archive:
            archive.write(source_backup_path, arcname=source_backup_path.name)
            archive.write(manifest_path, arcname=manifest_path.name)
            archive.writestr("README.txt", self._handover_package_readme(source_backup_path.name))
        stamp = self._now().strftime("%Y%m%d-%H%M")
        return HandoverBackupPackage(
            filename=f"SYSS_Handover_Backup_{stamp}.zip",
            content=package.getvalue(),
            source_backup_path=source_backup_path,
        )

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
