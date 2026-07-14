"""Process-local application services for the NiceGUI runtime."""

from __future__ import annotations

from nicegui_app.application_mode import current_application_mode
from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.services.roster_workflow import RosterWorkflow


_workflow: RosterWorkflow | None = None


def get_workflow() -> RosterWorkflow:
    global _workflow
    if _workflow is None:
        profile = current_application_mode()
        # Demonstration seed data belongs only to the fully isolated local
        # practice profile.  An official database must be allowed to remain
        # genuinely empty after a controlled first-use reset.
        _workflow = RosterWorkflow(
            database_path=profile.database_path,
            backup_dir=profile.backup_dir,
            seed_path=None if profile.mode == "official" else PREFECT_SEED_PATH,
        )
        _workflow.bootstrap()
    return _workflow
