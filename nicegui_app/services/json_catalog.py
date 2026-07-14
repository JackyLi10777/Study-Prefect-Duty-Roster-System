"""Small concurrency-safe primitives for local JSON catalogues."""

from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
from threading import Lock, RLock
from typing import Any, BinaryIO, Iterator, Mapping
from uuid import uuid4


_LOCKS_GUARD = Lock()
_LOCKS: dict[str, "_InterprocessCatalogLock"] = {}
_LOCK_TIMEOUT_SECONDS = 30.0


class _InterprocessCatalogLock:
    """Re-entrant lock backed by a crash-safe OS interprocess primitive."""

    def __init__(self, catalog_path: Path) -> None:
        self._thread_lock = RLock()
        self._depth = 0
        self._handle: BinaryIO | int | None = None
        self._lock_path = catalog_path.with_name(f".{catalog_path.name}.lock")
        lock_identity = os.path.normcase(str(catalog_path.resolve(strict=False)))
        self._windows_mutex_name = f"Global\\SingYinJsonCatalog-{sha256(lock_identity.encode('utf-8')).hexdigest()}"

    @contextmanager
    def hold(self) -> Iterator[None]:
        self._thread_lock.acquire()
        acquired_outer_lock = False
        try:
            if self._depth == 0:
                self._handle = self._acquire_interprocess_lock()
                acquired_outer_lock = True
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
                if acquired_outer_lock:
                    handle = self._handle
                    self._handle = None
                    if handle is not None:
                        if isinstance(handle, int):
                            self._release_interprocess_lock(handle)
                        else:
                            try:
                                self._release_interprocess_lock(handle)
                            finally:
                                handle.close()
        finally:
            self._thread_lock.release()

    def _acquire_interprocess_lock(self) -> BinaryIO | int:
        if os.name == "nt":
            return self._acquire_windows_mutex()
        return self._acquire_posix_file_lock()

    def _acquire_windows_mutex(self) -> int:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_mutex = kernel32.CreateMutexW
        create_mutex.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
        create_mutex.restype = wintypes.HANDLE
        wait_for_single_object = kernel32.WaitForSingleObject
        wait_for_single_object.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        wait_for_single_object.restype = wintypes.DWORD
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (wintypes.HANDLE,)
        close_handle.restype = wintypes.BOOL

        handle = create_mutex(None, False, self._windows_mutex_name)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        result = wait_for_single_object(handle, int(_LOCK_TIMEOUT_SECONDS * 1000))
        if result in (0x00000000, 0x00000080):  # WAIT_OBJECT_0 or WAIT_ABANDONED
            return int(handle)
        close_handle(handle)
        if result == 0x00000102:  # WAIT_TIMEOUT
            raise TimeoutError(f"Timed out waiting for the local catalogue lock: {self._lock_path.name}")
        raise ctypes.WinError(ctypes.get_last_error())

    def _acquire_posix_file_lock(self) -> BinaryIO:
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = self._lock_path.open("a+b")
        try:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
                os.fsync(handle.fileno())
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            return handle
        except Exception:
            handle.close()
            raise

    def _release_interprocess_lock(self, handle: BinaryIO | int) -> None:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            release_mutex = kernel32.ReleaseMutex
            release_mutex.argtypes = (wintypes.HANDLE,)
            release_mutex.restype = wintypes.BOOL
            close_handle = kernel32.CloseHandle
            close_handle.argtypes = (wintypes.HANDLE,)
            close_handle.restype = wintypes.BOOL
            if not release_mutex(handle):
                error = ctypes.WinError(ctypes.get_last_error())
                close_handle(handle)
                raise error
            close_handle(handle)
            return
        assert not isinstance(handle, int)
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _catalog_lock(path: Path) -> _InterprocessCatalogLock:
    key = os.path.normcase(str(Path(path).resolve(strict=False)))
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, _InterprocessCatalogLock(Path(key)))


@contextmanager
def locked_json_catalog(path: Path) -> Iterator[None]:
    """Serialize one complete read-modify-write across threads and processes."""

    with _catalog_lock(path).hold():
        yield


def write_json_atomically(path: Path, payload: Mapping[str, Any]) -> None:
    """Replace a JSON document from a unique, fully flushed temporary file."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            # The primary write error is more useful than a best-effort cleanup
            # error; a unique temp name also cannot corrupt a later operation.
            pass
