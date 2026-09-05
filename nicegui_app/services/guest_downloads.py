"""Bounded, single-use file delivery for the in-memory guest workspace."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import secrets
from threading import RLock, Timer
import time

from nicegui_app.access_context import AccessMode


DEFAULT_DOWNLOAD_TTL_SECONDS = 90
DEFAULT_MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024
DEFAULT_MAX_ADMIN_DOWNLOAD_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_TOTAL_DOWNLOAD_BYTES = 128 * 1024 * 1024
DEFAULT_ADMIN_RESERVED_DOWNLOAD_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_DOWNLOADS = 128
DEFAULT_MAX_DOWNLOADS_PER_SESSION = 8
DEFAULT_ADMIN_RESERVED_DOWNLOADS = 16
_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,96}$")
_MEDIA_TYPE_PATTERN = re.compile(
    r"^[a-z][a-z0-9.+-]*/[a-z0-9][a-z0-9.+-]*(?:; charset=utf-8)?$"
)


class GuestDownloadError(LookupError):
    """A guest download is invalid, expired, unavailable, or already consumed."""


class GuestDownloadCapacityError(GuestDownloadError):
    """The bounded in-memory delivery registry has reached its limit."""


@dataclass(frozen=True)
class GuestDownloadTicket:
    token: str
    expires_at: int


@dataclass(frozen=True)
class GuestDownloadPayload:
    filename: str
    content: bytes
    media_type: str


@dataclass(frozen=True)
class _DownloadRecord:
    access_mode: AccessMode
    session_id: str
    filename: str
    content: bytes
    media_type: str
    expires_at: int
    retention_deadline: float


class GuestDownloadRegistry:
    """Keep bounded Admin and Guest exports until one authenticated GET consumes them.

    Guest traffic receives a strict share of the global registry so public demo
    sessions cannot consume the capacity reserved for an administrator export.
    Every record is also bound to the verified access mode used to issue it.
    """

    def __init__(
        self,
        *,
        ttl_seconds: int = DEFAULT_DOWNLOAD_TTL_SECONDS,
        max_download_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES,
        max_admin_download_bytes: int = DEFAULT_MAX_ADMIN_DOWNLOAD_BYTES,
        max_total_download_bytes: int = DEFAULT_MAX_TOTAL_DOWNLOAD_BYTES,
        reserved_admin_download_bytes: int = DEFAULT_ADMIN_RESERVED_DOWNLOAD_BYTES,
        max_downloads: int = DEFAULT_MAX_DOWNLOADS,
        max_downloads_per_session: int = DEFAULT_MAX_DOWNLOADS_PER_SESSION,
        reserved_admin_downloads: int = DEFAULT_ADMIN_RESERVED_DOWNLOADS,
    ) -> None:
        if min(
            ttl_seconds,
            max_download_bytes,
            max_admin_download_bytes,
            max_total_download_bytes,
            max_downloads,
            max_downloads_per_session,
        ) <= 0:
            raise ValueError("guest download limits must be positive")
        if not 0 <= reserved_admin_download_bytes < max_total_download_bytes:
            raise ValueError("admin reserved download byte capacity is invalid")
        if max_admin_download_bytes > max_total_download_bytes:
            raise ValueError("admin download byte limit exceeds total capacity")
        if max_download_bytes > max_total_download_bytes - reserved_admin_download_bytes:
            raise ValueError("guest download byte limit exceeds guest capacity")
        if not 0 <= reserved_admin_downloads < max_downloads:
            raise ValueError("admin reserved download capacity is invalid")
        self.ttl_seconds = ttl_seconds
        self.max_download_bytes = max_download_bytes
        self.max_admin_download_bytes = max_admin_download_bytes
        self.max_total_download_bytes = max_total_download_bytes
        self.reserved_admin_download_bytes = reserved_admin_download_bytes
        self.max_downloads = max_downloads
        self.max_downloads_per_session = max_downloads_per_session
        self.reserved_admin_downloads = reserved_admin_downloads
        self._records: dict[str, _DownloadRecord] = {}
        self._lock = RLock()
        self._cleanup_timer: Timer | None = None
        self._cleanup_deadline: float | None = None
        self._cleanup_generation = 0

    def issue(
        self,
        *,
        access_mode: AccessMode,
        session_id: str,
        filename: str,
        content: bytes,
        media_type: str,
        now: int | None = None,
    ) -> GuestDownloadTicket:
        self._validate_access_mode(access_mode)
        self._validate_session(session_id)
        self._validate_filename(filename)
        if not isinstance(content, bytes) or not content:
            raise GuestDownloadCapacityError("generated download content is empty or invalid")
        content_length = len(content)
        per_file_limit = (
            self.max_admin_download_bytes
            if access_mode is AccessMode.ADMIN
            else self.max_download_bytes
        )
        if content_length > per_file_limit:
            raise GuestDownloadCapacityError("generated download content exceeds the limit")
        if not isinstance(media_type, str) or not _MEDIA_TYPE_PATTERN.fullmatch(media_type):
            raise GuestDownloadError("guest download media type is invalid")
        current = int(time.time()) if now is None else int(now)
        with self._lock:
            self._purge_expired(current)
            session_count = sum(
                record.access_mode is access_mode and record.session_id == session_id
                for record in self._records.values()
            )
            guest_count = sum(
                record.access_mode is AccessMode.GUEST
                for record in self._records.values()
            )
            total_bytes = sum(len(record.content) for record in self._records.values())
            guest_bytes = sum(
                len(record.content)
                for record in self._records.values()
                if record.access_mode is AccessMode.GUEST
            )
            guest_capacity = self.max_downloads - self.reserved_admin_downloads
            guest_byte_capacity = (
                self.max_total_download_bytes - self.reserved_admin_download_bytes
            )
            if (
                len(self._records) >= self.max_downloads
                or session_count >= self.max_downloads_per_session
                or total_bytes + content_length > self.max_total_download_bytes
                or (
                    access_mode is AccessMode.GUEST
                    and (
                        guest_count >= guest_capacity
                        or guest_bytes + content_length > guest_byte_capacity
                    )
                )
            ):
                raise GuestDownloadCapacityError("generated download capacity is full")
            token = secrets.token_urlsafe(32)
            while token in self._records:  # pragma: no cover - cryptographic collision guard
                token = secrets.token_urlsafe(32)
            expires_at = current + self.ttl_seconds
            self._records[token] = _DownloadRecord(
                access_mode=access_mode,
                session_id=session_id,
                filename=filename,
                content=bytes(content),
                media_type=media_type,
                expires_at=expires_at,
                retention_deadline=time.monotonic() + self.ttl_seconds,
            )
            self._schedule_cleanup_locked()
        return GuestDownloadTicket(token=token, expires_at=expires_at)

    def consume(
        self,
        *,
        token: str,
        access_mode: AccessMode,
        session_id: str,
        now: int | None = None,
    ) -> GuestDownloadPayload:
        self._validate_access_mode(access_mode)
        self._validate_session(session_id)
        if not isinstance(token, str) or not _TOKEN_PATTERN.fullmatch(token):
            raise GuestDownloadError("guest download token is invalid")
        current = int(time.time()) if now is None else int(now)
        with self._lock:
            record = self._records.get(token)
            if record is None:
                self._purge_expired(current)
                raise GuestDownloadError("guest download is unavailable")
            if record.expires_at <= current or record.retention_deadline <= time.monotonic():
                self._records.pop(token, None)
                self._schedule_cleanup_locked()
                raise GuestDownloadError("guest download has expired")
            if record.access_mode is not access_mode:
                raise GuestDownloadError("guest download is unavailable")
            if not secrets.compare_digest(record.session_id, session_id):
                raise GuestDownloadError("guest download is unavailable")
            self._records.pop(token, None)
            self._schedule_cleanup_locked()
        return GuestDownloadPayload(
            filename=record.filename,
            content=record.content,
            media_type=record.media_type,
        )

    def cleanup_session(self, session_id: str) -> int:
        self._validate_session(session_id)
        with self._lock:
            tokens = [
                token
                for token, record in self._records.items()
                if secrets.compare_digest(record.session_id, session_id)
            ]
            for token in tokens:
                self._records.pop(token, None)
            self._schedule_cleanup_locked()
        return len(tokens)

    def _purge_expired(self, now: int | None = None) -> None:
        """Release expired bytes while the caller holds the registry lock.

        Explicit ``now`` values retain their existing ticket-validation meaning.
        Idle cleanup uses monotonic age, so synthetic test timestamps or a
        backwards wall-clock adjustment cannot retain a payload indefinitely.
        """

        monotonic_now = time.monotonic()
        expired = [
            token
            for token, record in self._records.items()
            if (now is not None and record.expires_at <= now)
            or record.retention_deadline <= monotonic_now
        ]
        for token in expired:
            self._records.pop(token, None)
        # Also reschedule on a failed issue after expiry freed only some slots.
        self._schedule_cleanup_locked()

    def _schedule_cleanup_locked(self) -> None:
        """Keep one daemon wakeup for the nearest deadline, or none when empty."""

        deadline = min(
            (record.retention_deadline for record in self._records.values()),
            default=None,
        )
        if self._cleanup_timer is not None and deadline == self._cleanup_deadline:
            return
        self._cleanup_generation += 1
        if self._cleanup_timer is not None:
            self._cleanup_timer.cancel()
        self._cleanup_timer = None
        self._cleanup_deadline = None
        if deadline is None:
            return
        timer: Timer | None = None
        try:
            timer = Timer(
                max(0.0, deadline - time.monotonic()),
                self._cleanup_expired,
                args=(self._cleanup_generation,),
            )
            timer.daemon = True
            self._cleanup_timer = timer
            self._cleanup_deadline = deadline
            timer.start()
        except Exception as error:
            # If a worker cannot be started, retain neither bytes nor a ticket
            # whose idle expiry cannot be guaranteed. No payload is logged.
            if timer is not None:
                timer.cancel()
            self._cleanup_timer = None
            self._cleanup_deadline = None
            self._cleanup_generation += 1
            self._records.clear()
            logging.getLogger(__name__).error("event=generated_download_cleanup_failed")
            raise GuestDownloadCapacityError("generated download cleanup is unavailable") from error

    def _cleanup_expired(self, generation: int) -> None:
        with self._lock:
            # Timer.cancel cannot stop a callback already waiting for this lock.
            # An old callback must never replace a newly scheduled wakeup.
            if generation != self._cleanup_generation:
                return
            self._cleanup_timer = None
            self._cleanup_deadline = None
            try:
                self._purge_expired()
            except GuestDownloadCapacityError:
                # Scheduling already released every payload and logged a fixed
                # failure event. There is no request to receive this exception.
                return

    @staticmethod
    def _validate_access_mode(access_mode: AccessMode) -> None:
        if access_mode not in {AccessMode.ADMIN, AccessMode.GUEST}:
            raise GuestDownloadError("generated download access mode is invalid")

    @staticmethod
    def _validate_session(session_id: str) -> None:
        if not isinstance(session_id, str) or not 1 <= len(session_id) <= 128:
            raise GuestDownloadError("guest download session is invalid")

    @staticmethod
    def _validate_filename(filename: str) -> None:
        if (
            not isinstance(filename, str)
            or not 1 <= len(filename) <= 180
            or filename != filename.strip()
            or any(ord(character) < 32 for character in filename)
            or "/" in filename
            or "\\" in filename
        ):
            raise GuestDownloadError("guest download filename is invalid")


_registry = GuestDownloadRegistry()


def guest_download_registry() -> GuestDownloadRegistry:
    return _registry


__all__ = [
    "DEFAULT_ADMIN_RESERVED_DOWNLOAD_BYTES",
    "DEFAULT_ADMIN_RESERVED_DOWNLOADS",
    "DEFAULT_MAX_ADMIN_DOWNLOAD_BYTES",
    "DEFAULT_MAX_DOWNLOAD_BYTES",
    "DEFAULT_MAX_TOTAL_DOWNLOAD_BYTES",
    "GuestDownloadCapacityError",
    "GuestDownloadError",
    "GuestDownloadPayload",
    "GuestDownloadRegistry",
    "GuestDownloadTicket",
    "guest_download_registry",
]
