from __future__ import annotations

from pathlib import Path

import pytest

from nicegui_app.utils.prefect_import import parse_prefect_import_text
from scripts.verify_nicegui_write_pipeline import _fixture_import_csv, _fixture_leave_prefect, isolated_paths
from scripts.verify_nicegui_ui import prepare_invalid_backup_fixture


def test_write_pipeline_requires_explicit_isolation(monkeypatch) -> None:
    for name in (
        "SING_YIN_E2E_ISOLATED",
        "SING_YIN_E2E_RUN_ID",
        "SING_YIN_DATABASE_PATH",
        "SING_YIN_BACKUP_DIR",
        "SING_YIN_LOG_DIR",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="SING_YIN_E2E_ISOLATED"):
        isolated_paths()


def test_write_pipeline_accepts_distinct_temporary_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SING_YIN_E2E_ISOLATED", "1")
    monkeypatch.setenv("SING_YIN_E2E_RUN_ID", "E2E-ABCDEF123456")
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
    monkeypatch.setenv("SING_YIN_E2E_RUN_ID", "E2E-123456ABCDEF")
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


def test_write_pipeline_rejects_missing_or_malformed_server_identity(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SING_YIN_E2E_ISOLATED", "1")
    monkeypatch.setenv("SING_YIN_DATABASE_PATH", str(tmp_path / "live.sqlite3"))
    monkeypatch.setenv("SING_YIN_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("SING_YIN_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("SING_YIN_E2E_RUN_ID", "not-a-valid-run")

    with pytest.raises(RuntimeError, match="SING_YIN_E2E_RUN_ID"):
        isolated_paths()


def test_write_pipeline_fixture_uses_stable_role_codes() -> None:
    prefect_id, prefect_name = _fixture_leave_prefect()

    assert prefect_id
    assert prefect_name


def test_write_pipeline_imports_a_complete_fictional_directory_through_the_ui() -> None:
    _, leave_prefect_name = _fixture_leave_prefect()

    preview = parse_prefect_import_text(_fixture_import_csv())

    assert preview.issues == ()
    assert len(preview.rows) >= 15
    assert leave_prefect_name in {item.name_zh for item in preview.rows}
    assert {item.role_code for item in preview.rows} == {"assistant_head", "study_prefect"}


def test_write_pipeline_uses_current_reviewed_import_label() -> None:
    script = (Path(__file__).parents[1] / "scripts" / "verify_nicegui_write_pipeline.py").read_text(encoding="utf-8")

    assert 'get_by_text("資料匯入", exact=True)' in script
    assert 'get_by_text("AI 匯入", exact=True)' not in script


def test_partial_backup_drill_uses_the_stable_action_name_instead_of_an_icon() -> None:
    script = (Path(__file__).parents[1] / "scripts" / "verify_nicegui_partial_backup.py").read_text(encoding="utf-8")

    assert 'get_by_role("button", name="生成並儲存草稿")' in script
    assert 'has_text="auto_awesome"' not in script
