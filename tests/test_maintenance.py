from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
from threading import Event, Timer
import time

import pytest

from nicegui_app.services.maintenance import MaintenanceCoordinator, MaintenanceModeError


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_maintenance_waits_for_active_operation_and_blocks_new_work(tmp_path) -> None:
    coordinator = MaintenanceCoordinator(tmp_path / "roster.sqlite3")
    operation_started = Event()
    release_operation = Event()
    maintenance_started = Event()

    def normal_operation() -> None:
        with coordinator.operation():
            operation_started.set()
            assert release_operation.wait(timeout=5)

    def maintenance() -> None:
        assert operation_started.wait(timeout=5)
        with coordinator.maintenance("restore"):
            maintenance_started.set()
            with pytest.raises(MaintenanceModeError):
                with ThreadPoolExecutor(max_workers=1) as nested:
                    nested.submit(lambda: _try_operation(coordinator)).result(timeout=5)

    with ThreadPoolExecutor(max_workers=2) as executor:
        normal = executor.submit(normal_operation)
        exclusive = executor.submit(maintenance)
        assert operation_started.wait(timeout=5)
        assert not maintenance_started.wait(timeout=0.1)
        release_operation.set()
        normal.result(timeout=5)
        exclusive.result(timeout=5)

    assert coordinator.status().active is False
    assert not coordinator.marker_path.exists()


def _try_operation(coordinator: MaintenanceCoordinator) -> None:
    with coordinator.operation():
        raise AssertionError("operation unexpectedly entered maintenance window")


def test_stale_marker_blocks_operations_and_is_reported_for_recovery(tmp_path) -> None:
    coordinator = MaintenanceCoordinator(tmp_path / "roster.sqlite3")
    coordinator.marker_path.write_text('{"operation":"restore"}', encoding="utf-8")

    status = coordinator.status()

    assert status.active is True
    assert status.recovery_required is True
    with pytest.raises(MaintenanceModeError):
        with coordinator.operation():
            pass


def test_failed_maintenance_can_preserve_a_recovery_required_marker(tmp_path) -> None:
    coordinator = MaintenanceCoordinator(tmp_path / "roster.sqlite3")

    with coordinator.maintenance("restore"):
        coordinator.require_recovery_review(reason_code="restore_rollback_failed")

    status = coordinator.status()
    assert status.active is True
    assert status.recovery_required is True
    assert "restore_rollback_failed" in coordinator.marker_path.read_text(encoding="utf-8")


def test_losing_maintenance_contender_never_removes_the_winners_marker(tmp_path) -> None:
    database_path = tmp_path / "roster.sqlite3"
    winner = MaintenanceCoordinator(database_path)
    contender = MaintenanceCoordinator(database_path)
    winner_started = Event()
    contender_finished = Event()
    release_winner = Event()

    def hold_winning_maintenance() -> None:
        with winner.maintenance("restore"):
            winner_started.set()
            assert release_winner.wait(timeout=5)

    def attempt_competing_maintenance() -> None:
        assert winner_started.wait(timeout=5)
        with pytest.raises(MaintenanceModeError):
            with contender.maintenance("restore"):
                raise AssertionError("competing maintenance unexpectedly acquired the marker")
        contender_finished.set()

    with ThreadPoolExecutor(max_workers=2) as executor:
        winning = executor.submit(hold_winning_maintenance)
        competing = executor.submit(attempt_competing_maintenance)
        assert contender_finished.wait(timeout=5)
        assert winner.marker_path.exists(), "the losing contender removed the active host-wide marker"
        release_winner.set()
        competing.result(timeout=5)
        winning.result(timeout=5)

    assert not winner.marker_path.exists()


def test_maintenance_waits_for_an_operation_in_another_process(tmp_path) -> None:
    database_path = tmp_path / "roster.sqlite3"
    ready_path = tmp_path / "operation-ready"
    release_path = tmp_path / "operation-release"
    child_code = """
import sys
import time
from pathlib import Path
from nicegui_app.services.maintenance import MaintenanceCoordinator

database_path, ready_path, release_path = map(Path, sys.argv[1:4])
coordinator = MaintenanceCoordinator(database_path)
with coordinator.operation():
    ready_path.write_text('ready', encoding='utf-8')
    while not release_path.exists():
        time.sleep(0.02)
"""
    process = subprocess.Popen(
        [sys.executable, "-X", "utf8", "-c", child_code, str(database_path), str(ready_path), str(release_path)],
        cwd=PROJECT_ROOT,
    )
    try:
        deadline = time.monotonic() + 5
        while not ready_path.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert ready_path.exists(), "child operation did not acquire its host-wide lease"
        timer = Timer(0.35, lambda: release_path.write_text("release", encoding="utf-8"))
        timer.start()
        started = time.monotonic()
        with MaintenanceCoordinator(database_path).maintenance("restore"):
            elapsed = time.monotonic() - started
        timer.join(timeout=2)
        assert elapsed >= 0.2
        assert process.wait(timeout=5) == 0
    finally:
        release_path.write_text("release", encoding="utf-8")
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


def test_stale_cross_process_operation_lease_is_pruned(tmp_path) -> None:
    coordinator = MaintenanceCoordinator(tmp_path / "roster.sqlite3")
    coordinator.operation_lease_dir.mkdir()
    stale = coordinator.operation_lease_dir / "stale.json"
    stale.write_text('{"pid": 2147483647}', encoding="utf-8")

    with coordinator.maintenance("restore"):
        assert not stale.exists()

    assert not coordinator.operation_lease_dir.exists()


def test_half_written_lease_from_dead_process_is_pruned_by_filename_owner(tmp_path) -> None:
    coordinator = MaintenanceCoordinator(tmp_path / "roster.sqlite3")
    coordinator.operation_lease_dir.mkdir()
    stale = coordinator.operation_lease_dir / "2147483647-1-interrupted.json"
    stale.write_text("{", encoding="utf-8")

    with coordinator.maintenance("restore"):
        assert not stale.exists()

    assert not coordinator.operation_lease_dir.exists()
