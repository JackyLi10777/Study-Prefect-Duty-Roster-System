"""Stable facade for transactional roster use cases."""

from __future__ import annotations

from nicegui_app.services.workflow_dependencies import *
from nicegui_app.services.workflow_parts import (
    PeopleWorkflowMixin,
    PersistenceWorkflowMixin,
    RecoveryWorkflowMixin,
    ReportingWorkflowMixin,
    RosterLifecycleMixin,
)

class RosterWorkflow(
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

    def maintenance_status(self) -> MaintenanceStatus:
        return self.maintenance.status()

    def bootstrap(self) -> None:
        self.sessions = create_session_factory(self.database_path)
        with self._session() as session:
            if self.seed_path is not None and session.scalar(select(func.count()).select_from(PrefectRecord)) == 0:
                self._seed_prefects(session)
                self._audit(session, "prefects_seeded", None, {"source": str(self.seed_path)})
                session.commit()
