"""Single-origin process fencing for the local SQLite deployment.

The supported v1.2 topology is one NiceGUI origin process per database path,
with any number of browser clients and tabs inside that process.  Acquiring
this operating-system lock before migrations prevents a second launcher from
starting another origin against the same SQLite file.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from threading import RLock
from typing import BinaryIO


class OriginAlreadyRunningError(RuntimeError):
    """Raised when another process already owns the database origin lock."""


@dataclass
class OriginProcessLock:
    """A held, cross-platform advisory lock."""

    database_path: Path
    lock_path: Path
    _handle: BinaryIO
    _released: bool = False

    def release(self) -> None:
        if self._released:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self._handle.seek(0)
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._released = True

    def __enter__(self) -> "OriginProcessLock":
        return self

    def __exit__(self, *_: object) -> None:
        self.release()


_PROCESS_GUARD = RLock()
_HELD_LOCKS: dict[Path, tuple[OriginProcessLock, int]] = {}


class OriginProcessLease:
    """A re-entrant lease for callers in the same Python process."""

    def __init__(self, key: Path, lock: OriginProcessLock) -> None:
        self.database_path = key
        self.lock_path = lock.lock_path
        self._key = key
        self._released = False

    def release(self) -> None:
        if self._released:
            return
        with _PROCESS_GUARD:
            held = _HELD_LOCKS.get(self._key)
            if held is None:
                self._released = True
                return
            lock, count = held
            if count <= 1:
                lock.release()
                _HELD_LOCKS.pop(self._key, None)
            else:
                _HELD_LOCKS[self._key] = (lock, count - 1)
            self._released = True

    def __enter__(self) -> "OriginProcessLease":
        return self

    def __exit__(self, *_: object) -> None:
        self.release()


def _lock_file_for(database_path: Path) -> Path:
    resolved = database_path.expanduser().resolve()
    return resolved.with_name(f".{resolved.name}.origin.lock")


def _acquire_os_lock(database_path: Path) -> OriginProcessLock:
    lock_path = _lock_file_for(database_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, BlockingIOError) as error:
        handle.close()
        raise OriginAlreadyRunningError(
            f"Another Sing Yin origin already owns {database_path.expanduser().resolve()}."
        ) from error
    return OriginProcessLock(
        database_path=database_path.expanduser().resolve(),
        lock_path=lock_path,
        _handle=handle,
    )


def acquire_origin_process_lock(database_path: Path) -> OriginProcessLease:
    """Acquire the process-lifetime origin lock for ``database_path``.

    Calls from the same process are re-entrant so test fixtures and composition
    helpers can share the single origin.  A separate process fails immediately.
    """

    key = database_path.expanduser().resolve()
    with _PROCESS_GUARD:
        held = _HELD_LOCKS.get(key)
        if held is not None:
            lock, count = held
            _HELD_LOCKS[key] = (lock, count + 1)
            return OriginProcessLease(key, lock)
        lock = _acquire_os_lock(key)
        _HELD_LOCKS[key] = (lock, 1)
        return OriginProcessLease(key, lock)


__all__ = [
    "OriginAlreadyRunningError",
    "OriginProcessLease",
    "OriginProcessLock",
    "acquire_origin_process_lock",
]
