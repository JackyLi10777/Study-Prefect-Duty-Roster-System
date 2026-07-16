from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from nicegui_app.process_lock import acquire_origin_process_lock


def test_origin_lock_is_reentrant_inside_one_process(tmp_path: Path) -> None:
    database = tmp_path / "runtime.sqlite3"
    first = acquire_origin_process_lock(database)
    second = acquire_origin_process_lock(database)
    assert first.lock_path == second.lock_path

    second.release()
    first.release()
    with acquire_origin_process_lock(database):
        assert first.lock_path.is_file()


def test_second_process_cannot_own_the_same_database_origin(tmp_path: Path) -> None:
    database = tmp_path / "runtime.sqlite3"
    child_code = """
import sys
from pathlib import Path
from nicegui_app.process_lock import OriginAlreadyRunningError, acquire_origin_process_lock
try:
    acquire_origin_process_lock(Path(sys.argv[1]))
except OriginAlreadyRunningError:
    raise SystemExit(42)
raise SystemExit(0)
"""
    with acquire_origin_process_lock(database):
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "-c", child_code, str(database)],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    assert result.returncode == 42, result.stderr


def test_different_database_paths_can_have_separate_origins(tmp_path: Path) -> None:
    with (
        acquire_origin_process_lock(tmp_path / "first.sqlite3"),
        acquire_origin_process_lock(tmp_path / "second.sqlite3"),
    ):
        pass
