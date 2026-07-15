"""Process-wide admission control for destructive database maintenance."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import ctypes
import json
import os
from pathlib import Path
import sqlite3
from threading import Condition, get_ident
import time
from typing import Iterator
from uuid import uuid4


class MaintenanceModeError(RuntimeError):
    """Raised when a normal operation is attempted during maintenance."""


@dataclass(frozen=True)
class MaintenanceStatus:
    active: bool
    operation: str | None = None
    recovery_required: bool = False


class MaintenanceCoordinator:
    """Drain active workflow sessions across threads and host processes.

    Each normal operation owns a small payload-free lease file. Maintenance
    atomically creates a host-wide marker, then waits for every lease to drain.
    The local condition keeps the common single-process path fast and the
    marker remains a durable crash signal; neither artifact contains roster data.
    """

    _DRAIN_TIMEOUT_SECONDS = 30.0
    _SERIALIZED_OPERATION_TIMEOUT_SECONDS = 30.0

    def __init__(self, database_path: Path) -> None:
        self.marker_path = database_path.with_name(f".{database_path.name}.maintenance.json")
        self.operation_lease_dir = database_path.with_name(f".{database_path.name}.operations")
        self.serialized_operation_path = database_path.with_name(
            f".{database_path.name}.serialized-operations.sqlite3"
        )
        self._condition = Condition()
        self._active_operations = 0
        self._operation_depths: dict[int, int] = {}
        self._maintenance_owner: int | None = None
        self._maintenance_name: str | None = None
        self._preserve_marker = False
        self._serialized_owner: int | None = None
        self._serialized_depth = 0
        self._serialized_connection: sqlite3.Connection | None = None

    def status(self) -> MaintenanceStatus:
        with self._condition:
            marker_payload = self._read_json(self.marker_path)
            marker_exists = self.marker_path.exists()
            marker_pid = marker_payload.get("pid") if marker_payload else None
            explicit_recovery = bool(marker_payload and marker_payload.get("recoveryRequired"))
            external_owner_alive = isinstance(marker_pid, int) and self._process_exists(marker_pid)
            active = self._maintenance_owner is not None or marker_exists
            return MaintenanceStatus(
                active=active,
                operation=self._maintenance_name
                or (str(marker_payload.get("operation")) if marker_payload and marker_payload.get("operation") else None),
                recovery_required=marker_exists
                and self._maintenance_owner is None
                and (explicit_recovery or not external_owner_alive),
            )

    @contextmanager
    def operation(self) -> Iterator[None]:
        owner = get_ident()
        lease_path: Path | None = None
        with self._condition:
            if self._maintenance_owner == owner:
                operation_kind = "maintenance_owner"
            elif self._operation_depths.get(owner, 0) > 0:
                operation_kind = "nested"
                self._operation_depths[owner] += 1
            else:
                operation_kind = "outer"
                if self._maintenance_owner is not None or self.marker_path.exists():
                    raise MaintenanceModeError("The roster system is in maintenance mode.")
                self._active_operations += 1
                self._operation_depths[owner] = 1
        try:
            if operation_kind == "outer":
                lease_path = self._acquire_operation_lease(owner)
            yield
        finally:
            if operation_kind == "nested":
                with self._condition:
                    depth = self._operation_depths.get(owner, 0)
                    if depth < 2:
                        raise RuntimeError("Nested roster operation ownership was lost.")
                    self._operation_depths[owner] = depth - 1
            elif operation_kind == "outer":
                if lease_path is not None:
                    lease_path.unlink(missing_ok=True)
                    self._remove_empty_lease_directory()
                with self._condition:
                    self._operation_depths.pop(owner, None)
                    self._active_operations -= 1
                    self._condition.notify_all()

    @contextmanager
    def serialized_operation(self) -> Iterator[None]:
        """Run one database write-and-snapshot sequence at a time.

        The ordinary operation lease makes maintenance wait for the complete
        sequence.  A separate, payload-free SQLite database supplies a
        crash-safe host-wide mutex, so another process cannot commit a later
        roster change between this operation's commit and its recovery
        snapshot.  Nested calls from the same workflow thread are re-entrant;
        this is required when an already-fenced write creates and records its
        automatic backup.
        """

        owner = get_ident()
        with self.operation():
            with self._condition:
                reentrant = self._serialized_owner == owner
                if reentrant:
                    self._serialized_depth += 1

            connection: sqlite3.Connection | None = None
            if not reentrant:
                try:
                    self.serialized_operation_path.parent.mkdir(parents=True, exist_ok=True)
                    connection = sqlite3.connect(
                        str(self.serialized_operation_path),
                        timeout=self._SERIALIZED_OPERATION_TIMEOUT_SECONDS,
                    )
                    connection.execute(
                        f"PRAGMA busy_timeout = {int(self._SERIALIZED_OPERATION_TIMEOUT_SECONDS * 1000)}"
                    )
                    connection.execute("BEGIN IMMEDIATE")
                except sqlite3.Error as error:
                    if connection is not None:
                        connection.close()
                    raise MaintenanceModeError(
                        "Another roster write is still finishing its verified recovery snapshot."
                    ) from error
                with self._condition:
                    self._serialized_owner = owner
                    self._serialized_depth = 1
                    self._serialized_connection = connection

            try:
                yield
            finally:
                release_connection: sqlite3.Connection | None = None
                with self._condition:
                    if self._serialized_owner != owner or self._serialized_depth < 1:
                        raise RuntimeError("Serialized roster operation ownership was lost.")
                    self._serialized_depth -= 1
                    if self._serialized_depth == 0:
                        release_connection = self._serialized_connection
                        self._serialized_connection = None
                        self._serialized_owner = None
                        self._condition.notify_all()
                if release_connection is not None:
                    try:
                        release_connection.rollback()
                    finally:
                        release_connection.close()

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
            self._preserve_marker = False
            while self._active_operations:
                self._condition.wait(timeout=0.25)
            self.marker_path.parent.mkdir(parents=True, exist_ok=True)
            marker_created = False
            try:
                descriptor = os.open(self.marker_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                marker_created = True
                try:
                    payload = {
                        "operation": operation,
                        "pid": os.getpid(),
                        "startedAt": datetime.now(timezone.utc).isoformat(),
                    }
                    os.write(descriptor, json.dumps(payload, sort_keys=True).encode("utf-8"))
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                self._wait_for_external_operations()
            except Exception as error:
                # Another process may have won the O_EXCL race. Never remove a
                # marker unless this coordinator created it.
                if marker_created:
                    self.marker_path.unlink(missing_ok=True)
                self._maintenance_owner = None
                self._maintenance_name = None
                self._condition.notify_all()
                if isinstance(error, FileExistsError):
                    raise MaintenanceModeError("Another host process is already running maintenance.") from error
                raise
        try:
            yield
        finally:
            with self._condition:
                if not self._preserve_marker:
                    self.marker_path.unlink(missing_ok=True)
                self._maintenance_owner = None
                self._maintenance_name = None
                self._condition.notify_all()

    def require_recovery_review(self, *, reason_code: str) -> None:
        """Keep the durable marker when automatic rollback cannot be proven safe."""
        with self._condition:
            if self._maintenance_owner != get_ident():
                raise MaintenanceModeError("Only the active maintenance owner can require recovery review.")
            payload = {
                "operation": self._maintenance_name,
                "pid": os.getpid(),
                "recoveryRequired": True,
                "reasonCode": reason_code,
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            }
            self.marker_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            self._preserve_marker = True

    def _acquire_operation_lease(self, owner: int) -> Path:
        if self.marker_path.exists():
            raise MaintenanceModeError("The roster system is in maintenance mode.")
        self.operation_lease_dir.mkdir(parents=True, exist_ok=True)
        lease_path = self.operation_lease_dir / f"{os.getpid()}-{owner}-{uuid4().hex}.json"
        temporary_path = lease_path.with_suffix(".tmp")
        try:
            descriptor = os.open(temporary_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                payload = {
                    "pid": os.getpid(),
                    "thread": owner,
                    "startedAt": datetime.now(timezone.utc).isoformat(),
                }
                os.write(descriptor, json.dumps(payload, sort_keys=True).encode("utf-8"))
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            # Maintenance only scans .json leases, so a process can never
            # expose a partially-written lease as active admission evidence.
            os.replace(temporary_path, lease_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            lease_path.unlink(missing_ok=True)
            self._remove_empty_lease_directory()
            raise
        if self.marker_path.exists():
            lease_path.unlink(missing_ok=True)
            self._remove_empty_lease_directory()
            raise MaintenanceModeError("The roster system is in maintenance mode.")
        return lease_path

    def _wait_for_external_operations(self) -> None:
        deadline = time.monotonic() + self._DRAIN_TIMEOUT_SECONDS
        while True:
            active_leases = self._active_operation_leases()
            if not active_leases:
                self._remove_empty_lease_directory()
                return
            if time.monotonic() >= deadline:
                raise MaintenanceModeError(
                    "Maintenance could not start because another host process still has an active roster operation."
                )
            self._condition.wait(timeout=0.1)

    def _active_operation_leases(self) -> list[Path]:
        if not self.operation_lease_dir.is_dir():
            return []
        active: list[Path] = []
        for path in self.operation_lease_dir.glob("*.json"):
            payload = self._read_json(path)
            pid = payload.get("pid") if payload else self._lease_pid_from_filename(path)
            if isinstance(pid, int) and not self._process_exists(pid):
                path.unlink(missing_ok=True)
                continue
            active.append(path)
        return active

    @staticmethod
    def _lease_pid_from_filename(path: Path) -> int | None:
        """Recover the owner of a legacy half-written lease without reading it."""
        try:
            return int(path.name.split("-", 1)[0])
        except (TypeError, ValueError):
            return None

    def _remove_empty_lease_directory(self) -> None:
        try:
            self.operation_lease_dir.rmdir()
        except OSError:
            pass

    @staticmethod
    def _read_json(path: Path) -> dict[str, object] | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _process_exists(pid: int) -> bool:
        if pid <= 0:
            return False
        if pid == os.getpid():
            return True
        if os.name == "nt":
            process_query_limited_information = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[attr-defined]
                process_query_limited_information,
                False,
                pid,
            )
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]
                return True
            return ctypes.windll.kernel32.GetLastError() == 5  # type: ignore[attr-defined]
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True


_COORDINATORS: dict[Path, MaintenanceCoordinator] = {}


def maintenance_coordinator(database_path: Path) -> MaintenanceCoordinator:
    resolved = database_path.resolve()
    coordinator = _COORDINATORS.get(resolved)
    if coordinator is None:
        coordinator = MaintenanceCoordinator(resolved)
        _COORDINATORS[resolved] = coordinator
    return coordinator
