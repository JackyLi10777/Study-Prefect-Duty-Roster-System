from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from nicegui_app.launcher import configure_nicegui_storage_path


def test_launcher_binds_nicegui_storage_to_database_runtime_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime" / "sing-yin-roster.sqlite3"
    environment_path = tmp_path / "empty.env"
    environment_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("SING_YIN_APP_MODE", "official")
    monkeypatch.setenv("SING_YIN_DATABASE_PATH", str(database_path))
    monkeypatch.setenv("NICEGUI_STORAGE_PATH", str(tmp_path / "wrong-location"))

    resolved = configure_nicegui_storage_path(environment_path=environment_path)

    assert resolved == (database_path.parent / "nicegui-storage").resolve()
    assert os.environ["NICEGUI_STORAGE_PATH"] == str(resolved)
    assert not resolved.exists(), "path binding must not invent a write during import"


def test_importing_launcher_does_not_import_nicegui_before_path_configuration() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-c",
            (
                "import sys; import nicegui_app.launcher; "
                "print('loaded' if 'nicegui' in sys.modules else 'deferred')"
            ),
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "deferred"


def test_launcher_configuration_precedes_nicegui_storage_class_resolution(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime" / "sing-yin-roster.sqlite3"
    expected = (database_path.parent / "nicegui-storage").resolve()
    environment = {
        **os.environ,
        "SING_YIN_APP_MODE": "official",
        "SING_YIN_DATABASE_PATH": str(database_path),
        "NICEGUI_STORAGE_PATH": str(tmp_path / "wrong-location"),
    }
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-c",
            (
                "from nicegui_app.launcher import configure_nicegui_storage_path; "
                "configure_nicegui_storage_path(); "
                "from nicegui.storage import Storage; print(Storage.path)"
            ),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert Path(result.stdout.strip()) == expected
