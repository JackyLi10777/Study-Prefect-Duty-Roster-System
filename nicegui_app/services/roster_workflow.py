"""Stable facade for transactional roster use cases."""

from __future__ import annotations

from nicegui_app.services.policy_workflow import PolicyWorkflowMixin
from nicegui_app.services.dated_draft_workflow import DatedDraftWorkflowMixin
from nicegui_app.services.workflow_dependencies import (
    DEFAULT_BACKUP_DIR,
    DEFAULT_DATABASE_PATH,
    MaintenanceModeError,
    MaintenanceStatus,
    Path,
    PrefectRecord,
    RosterWeekRecord,
    Session,
    create_session_factory,
    func,
    maintenance_coordinator,
    select,
    sessionmaker,
)
from nicegui_app.services.workflow_parts import (
    ExternalShareOutboxMixin,
    PeopleWorkflowMixin,
    PersistenceWorkflowMixin,
    RecoveryWorkflowMixin,
    ReportingWorkflowMixin,
    RosterLifecycleMixin,
)
from nicegui_app.services.workflow_types import (
    BackupResult,
    CommittedWriteBackupError,
    FLEXIBLE_WEEKLY,
    LEGACY_FIXED_WEEKDAY,
    PeriodSummaryReport,
    PREFECT_PATCH_FIELDS,
    PrefectInput,
    PrefectPatch,
    WorkflowConflictError,
    WorkflowError,
    WorkflowMaintenanceError,
)


__all__ = [
    "BackupResult",
    "CommittedWriteBackupError",
    "FLEXIBLE_WEEKLY",
    "LEGACY_FIXED_WEEKDAY",
    "PeriodSummaryReport",
    "PREFECT_PATCH_FIELDS",
    "PrefectInput",
    "PrefectPatch",
    "RosterWorkflow",
    "WorkflowConflictError",
    "WorkflowError",
    "WorkflowMaintenanceError",
]


class RosterWorkflow(
    DatedDraftWorkflowMixin,
    PolicyWorkflowMixin,
    ExternalShareOutboxMixin,
    RosterLifecycleMixin,
    PeopleWorkflowMixin,
    ReportingWorkflowMixin,
    RecoveryWorkflowMixin,
    PersistenceWorkflowMixin,
):
    def __init__(
        self,
        *,
        database_path: Path = DEFAULT_DATABASE_PATH,
        backup_dir: Path = DEFAULT_BACKUP_DIR,
        seed_path: Path | None = None,
    ) -> None:
        self.database_path = database_path
        self.backup_dir = backup_dir
        self.seed_path = seed_path
        self.sessions: sessionmaker[Session] | None = None
        self.maintenance = maintenance_coordinator(database_path)
        self.backup_repair_error: str | None = None
        self.diagnostic_only = False

    def maintenance_status(self) -> MaintenanceStatus:
        return self.maintenance.status()

    def _assert_business_write_admitted(
        self,
        operation_name: str,
        arguments: tuple[object, ...] = (),
        keyword_arguments: dict[str, object] | None = None,
    ) -> None:
        """Fail closed before starting a new business mutation.

        A verified recovery snapshot is the admission boundary for every new
        business write, not merely methods which happen to use the workflow
        decorator. Recovery reconciliation and security cleanup use explicit
        paths and intentionally do not call this guard.
        """

        if self.sessions is None or self.maintenance.status().recovery_required:
            raise WorkflowMaintenanceError(
                "The system is in recovery maintenance mode and cannot accept writes."
            )
        if self.pending_backup_obligation_count() == 0:
            return
        self._raise_terminal_write_error(
            operation_name,
            arguments,
            keyword_arguments or {},
        )
        raise WorkflowMaintenanceError(
            "A committed operation still needs a verified recovery snapshot. "
            "The system is read-only until recovery repair succeeds."
        )

    def _raise_terminal_write_error(
        self,
        method_name: str,
        arguments: tuple[object, ...],
        keyword_arguments: dict[str, object],
    ) -> None:
        """Preserve an already-final business result while recovery is pending.

        A failed automatic snapshot correctly makes the application read-only,
        but retrying a publication which already committed is not a new write.
        Report that terminal roster state instead of implying that publication
        may be attempted again after recovery; the fairness ledger remains
        untouched either way.
        """

        if method_name != "publish":
            return
        raw_roster_id = arguments[0] if arguments else keyword_arguments.get("roster_week_id")
        try:
            roster_week_id = int(raw_roster_id)
        except (TypeError, ValueError):
            return
        with self._session() as session:
            week = session.get(RosterWeekRecord, roster_week_id)
            if week is not None and week.status == "published":
                raise WorkflowError("This roster is already published.")

    def bootstrap(self) -> None:
        # Any pre-existing maintenance marker freezes the database exactly as
        # it is.  A still-live peer may be changing or replacing the database,
        # while a stale marker requires recovery review; neither state permits
        # Alembic or SQLite journal mutations during this process's startup.
        if self.maintenance.status().active:
            self.sessions = None
            self.diagnostic_only = True
            self.backup_repair_error = None
            return
        try:
            # The lease closes the race between the status sample above and
            # migration startup.  A peer which wins maintenance admission is
            # observed here; a bootstrap which wins first remains visible to
            # that peer until migration, seeding, and recovery repair finish.
            with self.maintenance.operation():
                self.sessions = create_session_factory(self.database_path)
                self.diagnostic_only = False
                with self._session() as session:
                    if self.seed_path is not None and session.scalar(select(func.count()).select_from(PrefectRecord)) == 0:
                        self._seed_prefects(session)
                        self._audit(session, "prefects_seeded", None, {"source": str(self.seed_path)})
                        session.commit()
                try:
                    self.repair_pending_backup_obligations()
                    self.backup_repair_error = None
                except Exception as error:  # keep read-only diagnostics available
                    self.backup_repair_error = type(error).__name__
        except MaintenanceModeError:
            self.sessions = None
            self.diagnostic_only = True
            self.backup_repair_error = None
