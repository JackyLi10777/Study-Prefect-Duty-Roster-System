"""Prepare mutable NiceGUI runtime storage before importing the application.

NiceGUI resolves ``NICEGUI_STORAGE_PATH`` when its package is imported.  The
formal Windows host runs from an immutable release bundle, so the production
entry point must bind that path to the database runtime directory before
``nicegui_app.main`` (and therefore NiceGUI) enters the process.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

from nicegui_app.application_mode import current_application_mode
from nicegui_app.config import PROJECT_ROOT


def configure_nicegui_storage_path(
    *,
    environment_path: Path | None = None,
) -> Path:
    """Bind NiceGUI preferences to mutable runtime data, never source files."""

    load_dotenv(environment_path or PROJECT_ROOT / ".env", override=False)
    application_mode = current_application_mode()
    storage_path = (application_mode.database_path.parent / "nicegui-storage").resolve()
    os.environ["NICEGUI_STORAGE_PATH"] = str(storage_path)
    return storage_path


def run() -> None:
    """Configure the runtime boundary, then hand control to the application."""

    configure_nicegui_storage_path()
    # NiceGUI must stay behind the storage-path assignment above.  Importing it
    # earlier would freeze the default ``.nicegui`` path inside the release.
    from nicegui_app.main import run as run_application

    run_application()


if __name__ in {"__main__", "__mp_main__"}:
    run()
