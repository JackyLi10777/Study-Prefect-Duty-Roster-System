from __future__ import annotations

from pathlib import Path

import pytest

from nicegui_app.application_mode import ApplicationModeSettings
from nicegui_app.config import PRACTICE_DATA_DIR, PROJECT_ROOT
from nicegui_app.release_evidence import RELEASE_SOURCE_FILES


def test_official_mode_is_default_and_keeps_existing_path_injection(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SING_YIN_APP_MODE", raising=False)
    monkeypatch.setenv("SING_YIN_DATABASE_PATH", str(tmp_path / "official.sqlite3"))
    monkeypatch.setenv("SING_YIN_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("SING_YIN_LOG_DIR", str(tmp_path / "logs"))

    settings = ApplicationModeSettings.from_environment()

    assert settings.mode == "official"
    assert settings.is_practice is False
    assert settings.database_path == (tmp_path / "official.sqlite3").resolve()


def test_practice_mode_requires_every_isolated_path(monkeypatch) -> None:
    monkeypatch.setenv("SING_YIN_APP_MODE", "practice")
    for name in ("SING_YIN_DATABASE_PATH", "SING_YIN_BACKUP_DIR", "SING_YIN_LOG_DIR"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="requires explicit isolated"):
        ApplicationModeSettings.from_environment()


def test_practice_mode_accepts_only_distinct_paths_inside_practice_root(monkeypatch) -> None:
    monkeypatch.setenv("SING_YIN_APP_MODE", "practice")
    monkeypatch.setenv("SING_YIN_DATABASE_PATH", str(PRACTICE_DATA_DIR / "runtime" / "practice.sqlite3"))
    monkeypatch.setenv("SING_YIN_BACKUP_DIR", str(PRACTICE_DATA_DIR / "backups"))
    monkeypatch.setenv("SING_YIN_LOG_DIR", str(PRACTICE_DATA_DIR / "logs"))

    settings = ApplicationModeSettings.from_environment()

    assert settings.is_practice is True
    assert all(str(path).startswith(str(PRACTICE_DATA_DIR.resolve())) for path in (
        settings.database_path,
        settings.backup_dir,
        settings.log_dir,
    ))


def test_practice_mode_refuses_a_path_outside_its_workspace(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SING_YIN_APP_MODE", "practice")
    monkeypatch.setenv("SING_YIN_DATABASE_PATH", str(tmp_path / "practice.sqlite3"))
    monkeypatch.setenv("SING_YIN_BACKUP_DIR", str(PRACTICE_DATA_DIR / "backups"))
    monkeypatch.setenv("SING_YIN_LOG_DIR", str(PRACTICE_DATA_DIR / "logs"))

    with pytest.raises(RuntimeError, match="inside data/practice"):
        ApplicationModeSettings.from_environment()


def test_practice_launch_and_reset_adapters_are_explicitly_isolated() -> None:
    launcher = (PROJECT_ROOT / "START_PRACTICE_MODE.cmd").read_text(encoding="utf-8")
    reset_wrapper = (PROJECT_ROOT / "RESET_PRACTICE_MODE.cmd").read_text(encoding="utf-8")
    reset_script = (PROJECT_ROOT / "scripts" / "reset_practice_mode.py").read_text(encoding="utf-8")

    assert "SING_YIN_APP_MODE=practice" in launcher
    for path in ("data\\practice\\runtime", "data\\practice\\backups", "data\\practice\\logs"):
        assert path in launcher
    assert "reset_practice_mode.py" in reset_wrapper
    assert "PRACTICE_ROOT.parent" in reset_script
    assert 'payload.get("applicationMode") == "practice"' in reset_script
    release_files = {path.name for path in RELEASE_SOURCE_FILES}
    assert {"START_PRACTICE_MODE.cmd", "RESET_PRACTICE_MODE.cmd"} <= release_files
