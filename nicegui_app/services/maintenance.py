"""Process-wide admission control for destructive database maintenance."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from threading import Condition, get_ident
from typing import Iterator


class MaintenanceModeError(RuntimeError):
    """Raised when a normal operation is attempted during maintenance."""


@dataclass(frozen=True)
class MaintenanceStatus:
    active: bool
    operation: str | None = None
    recovery_required: bool = False


class MaintenanceCoordinator:
    """Drain active workflow sessions before an exclusive restore.

    The condition protects every workflow instance in this process.  The
    marker is an additional same-host guard and durable crash signal; it never
    contains roster data.
    """

    def __init__(self, database_path: Path) -> None:
        self.marker_path = database_path.with_name(f".{database_path.name}.maintenance.json")
        self._condition = Condition()
        self._active_operations = 0
        self._maintenance_owner: int | None = None
        self._maintenance_name: str | None = None

    def status(self) -> MaintenanceStatus:
        with self._condition:
            active = self._maintenance_owner is not None or self.marker_path.exists()
            return MaintenanceStatus(
                active=active,
                operation=self._maintenance_name,
                recovery_required=self.marker_path.exists() and self._maintenance_owner is None,
            )

    @contextmanager
    def operation(self) -> Iterator[None]:
        owner = get_ident()
        with self._condition:
            if self._maintenance_owner == owner:
                yield_as_owner = True
            else:
                yield_as_owner = False
                if self._maintenance_owner is not None or self.marker_path.exists():
                    raise MaintenanceModeError("The roster system is in maintenance mode.")
                self._active_operations += 1
        try:
            yield
        finally:
            if not yield_as_owner:
                with self._condition:
                    self._active_operations -= 1
                    self._condition.notify_all()

    @contextmanager
    def maintenance(self, operation: str) -> Iterator[None]:
        owner = get_ident()
        with self._condition:
            if self._maintenance_owner is not None:
                raise MaintenanceModeError("Another maintenance operation is already running.")
            if self.marker_path.exists():
                raise MaintenanceModeError("A previous maintenance operation needs recovery review.")
            self._maintenance_owner = owner
            self._maintenance_name = operation
            while self._active_operations:
                self._condition.wait(timeout=0.25)
            self.marker_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                descriptor = os.open(self.marker_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                try:
                    payload = {
                        "operation": operation,
                        "pid": os.getpid(),
                        "startedAt": datetime.now(timezone.utc).isoformat(),
                    }
                    os.write(descriptor, json.dumps(payload, sort_keys=True).encode("utf-8"))
                finally:
                    os.close(descriptor)
            except Exception:
                self._maintenance_owner = None
                self._maintenance_name = None
                self._condition.notify_all()
                raise
        try:
            yield
        finally:
            with self._condition:
                self.marker_path.unlink(missing_ok=True)
                self._maintenance_owner = None
                self._maintenance_name = None
                self._condition.notify_all()


_COORDINATORS: dict[Path, MaintenanceCoordinator] = {}


def maintenance_coordinator(database_path: Path) -> MaintenanceCoordinator:
    resolved = database_path.resolve()
    coordinator = _COORDINATORS.get(resolved)
    if coordinator is None:
        coordinator = MaintenanceCoordinator(resolved)
        _COORDINATORS[resolved] = coordinator
    return coordinator
