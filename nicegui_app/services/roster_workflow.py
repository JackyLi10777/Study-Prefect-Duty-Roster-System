"""Stable facade for transactional roster use cases."""

from __future__ import annotations

from nicegui_app.services.workflow_dependencies import *
from nicegui_app.services.workflow_parts import (
    ExternalShareOutboxMixin,
    PeopleWorkflowMixin,
    PersistenceWorkflowMixin,
    RecoveryWorkflowMixin,
    ReportingWorkflowMixin,
    RosterLifecycleMixin,
)

class RosterWorkflow(
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

    def maintenance_status(self) -> MaintenanceStatus:
        return self.maintenance.status()

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
        self.sessions = create_session_factory(self.database_path)
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
