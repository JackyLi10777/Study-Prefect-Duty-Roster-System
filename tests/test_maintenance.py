from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from nicegui_app.services.maintenance import MaintenanceCoordinator, MaintenanceModeError


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
