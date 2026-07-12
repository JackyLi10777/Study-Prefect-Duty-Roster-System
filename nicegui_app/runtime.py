"""Process-local application services for the NiceGUI runtime."""

from __future__ import annotations

from nicegui_app.application_mode import current_application_mode
from nicegui_app.services.roster_workflow import RosterWorkflow


_workflow: RosterWorkflow | None = None


def get_workflow() -> RosterWorkflow:
    global _workflow
    if _workflow is None:
        profile = current_application_mode()
        _workflow = RosterWorkflow(database_path=profile.database_path, backup_dir=profile.backup_dir)
        _workflow.bootstrap()
    return _workflow
