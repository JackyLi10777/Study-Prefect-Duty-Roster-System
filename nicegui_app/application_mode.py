"""Application-profile boundary for official and fully isolated practice use."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Literal

from nicegui_app.config import (
    CANONICAL_BACKUP_DIR,
    CANONICAL_DATABASE_PATH,
    CANONICAL_LOG_DIR,
    PRACTICE_DATA_DIR,
)


ApplicationMode = Literal["official", "practice"]
_REQUIRED_PRACTICE_VARIABLES = (
    "SING_YIN_DATABASE_PATH",
    "SING_YIN_BACKUP_DIR",
    "SING_YIN_LOG_DIR",
)


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class ApplicationModeSettings:
    """Resolved storage identity for one running application process."""

    mode: ApplicationMode
    database_path: Path
    backup_dir: Path
    log_dir: Path

    @classmethod
    def from_environment(cls) -> "ApplicationModeSettings":
        raw_mode = os.getenv("SING_YIN_APP_MODE", "official").strip().lower()
        if raw_mode not in {"official", "practice"}:
            raise RuntimeError("SING_YIN_APP_MODE must be 'official' or 'practice'.")

        if raw_mode == "practice":
            missing = [name for name in _REQUIRED_PRACTICE_VARIABLES if not os.getenv(name, "").strip()]
            if missing:
                raise RuntimeError(
                    "Practice mode requires explicit isolated database, backup, and log paths: "
                    + ", ".join(missing)
                )

        settings = cls(
            mode=raw_mode,  # type: ignore[arg-type]
            database_path=_resolved(os.getenv("SING_YIN_DATABASE_PATH", CANONICAL_DATABASE_PATH)),
            backup_dir=_resolved(os.getenv("SING_YIN_BACKUP_DIR", CANONICAL_BACKUP_DIR)),
            log_dir=_resolved(os.getenv("SING_YIN_LOG_DIR", CANONICAL_LOG_DIR)),
        )
        settings.validate()
        return settings

    @property
    def is_practice(self) -> bool:
        return self.mode == "practice"

    def validate(self) -> None:
        if not self.is_practice:
            return
        practice_root = PRACTICE_DATA_DIR.resolve()
        paths = (self.database_path, self.backup_dir, self.log_dir)
        if any(not _is_within(path, practice_root) for path in paths):
            raise RuntimeError("Practice-mode database, backups, and logs must all stay inside data/practice.")
        official_paths = {
            CANONICAL_DATABASE_PATH.resolve(),
            CANONICAL_BACKUP_DIR.resolve(),
            CANONICAL_LOG_DIR.resolve(),
        }
        if any(path in official_paths for path in paths):
            raise RuntimeError("Practice mode refuses an official storage path.")
        if len(set(paths)) != len(paths):
            raise RuntimeError("Practice-mode database, backup, and log paths must be distinct.")


def current_application_mode() -> ApplicationModeSettings:
    """Resolve mode at the composition edge so tests and launchers can inject it."""
    return ApplicationModeSettings.from_environment()
