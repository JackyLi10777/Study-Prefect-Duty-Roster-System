from __future__ import annotations

import pytest

from scripts.verify_nicegui_write_pipeline import _fixture_leave_prefect, isolated_paths
from scripts.verify_nicegui_ui import prepare_invalid_backup_fixture


def test_write_pipeline_requires_explicit_isolation(monkeypatch) -> None:
    for name in ("SING_YIN_E2E_ISOLATED", "SING_YIN_DATABASE_PATH", "SING_YIN_BACKUP_DIR", "SING_YIN_LOG_DIR"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="SING_YIN_E2E_ISOLATED"):
        isolated_paths()


def test_write_pipeline_accepts_distinct_temporary_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SING_YIN_E2E_ISOLATED", "1")
    monkeypatch.setenv("SING_YIN_DATABASE_PATH", str(tmp_path / "live.sqlite3"))
    monkeypatch.setenv("SING_YIN_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("SING_YIN_LOG_DIR", str(tmp_path / "logs"))

    database_path, backup_dir, log_dir = isolated_paths()

    assert database_path == (tmp_path / "live.sqlite3").resolve()
    assert backup_dir == (tmp_path / "backups").resolve()
    assert log_dir == (tmp_path / "logs").resolve()


def test_write_pipeline_rejects_the_canonical_school_storage(monkeypatch) -> None:
    from scripts.verify_nicegui_write_pipeline import CANONICAL_BACKUP_DIRECTORY, CANONICAL_LIVE_DATABASE

    monkeypatch.setenv("SING_YIN_E2E_ISOLATED", "1")
    monkeypatch.setenv("SING_YIN_DATABASE_PATH", str(CANONICAL_LIVE_DATABASE))
    monkeypatch.setenv("SING_YIN_BACKUP_DIR", str(CANONICAL_BACKUP_DIRECTORY))
    monkeypatch.setenv("SING_YIN_LOG_DIR", "D:\\temporary-test-logs")

    with pytest.raises(RuntimeError, match="default school database"):
        isolated_paths()


def test_invalid_backup_ui_fixture_requires_explicit_isolation(monkeypatch) -> None:
    monkeypatch.setenv("SING_YIN_EXPECT_INVALID_BACKUP_COUNT", "1")
    monkeypatch.delenv("SING_YIN_E2E_ISOLATED", raising=False)

    with pytest.raises(RuntimeError, match="explicitly isolated"):
        prepare_invalid_backup_fixture()


def test_write_pipeline_fixture_uses_stable_role_codes() -> None:
    prefect_id, prefect_name = _fixture_leave_prefect()

    assert prefect_id
    assert prefect_name
