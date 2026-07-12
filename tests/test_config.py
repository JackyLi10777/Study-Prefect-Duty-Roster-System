from __future__ import annotations

import importlib
from pathlib import Path

import nicegui_app.config as config


def test_local_database_and_backup_locations_can_be_isolated_for_safe_ui_verification(monkeypatch) -> None:
    database_path = Path("C:/temporary/sing-yin-ui-smoke.sqlite3")
    backup_path = Path("C:/temporary/sing-yin-ui-backups")
    monkeypatch.setenv("SING_YIN_DATABASE_PATH", str(database_path))
    monkeypatch.setenv("SING_YIN_BACKUP_DIR", str(backup_path))

    isolated = importlib.reload(config)
    assert isolated.DEFAULT_DATABASE_PATH == database_path
    assert isolated.DEFAULT_BACKUP_DIR == backup_path

    monkeypatch.delenv("SING_YIN_DATABASE_PATH")
    monkeypatch.delenv("SING_YIN_BACKUP_DIR")
    restored = importlib.reload(config)
    assert restored.DEFAULT_DATABASE_PATH.name == "sing-yin-roster.sqlite3"
    assert restored.DEFAULT_BACKUP_DIR.name == "backups"
