"""Bounded, single-use file delivery for the in-memory guest workspace."""

from __future__ import annotations

from dataclasses import dataclass
import re
import secrets
from threading import RLock
import time


DEFAULT_DOWNLOAD_TTL_SECONDS = 90
DEFAULT_MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024
DEFAULT_MAX_DOWNLOADS = 128
DEFAULT_MAX_DOWNLOADS_PER_SESSION = 8
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
    session_id: str
    filename: str
    content: bytes
    media_type: str
    expires_at: int


class GuestDownloadRegistry:
    """Keep guest exports in process memory until one authenticated GET consumes them."""

    def __init__(
        self,
        *,
        ttl_seconds: int = DEFAULT_DOWNLOAD_TTL_SECONDS,
        max_download_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES,
        max_downloads: int = DEFAULT_MAX_DOWNLOADS,
        max_downloads_per_session: int = DEFAULT_MAX_DOWNLOADS_PER_SESSION,
    ) -> None:
        if min(
            ttl_seconds,
            max_download_bytes,
            max_downloads,
            max_downloads_per_session,
        ) <= 0:
            raise ValueError("guest download limits must be positive")
        self.ttl_seconds = ttl_seconds
        self.max_download_bytes = max_download_bytes
        self.max_downloads = max_downloads
        self.max_downloads_per_session = max_downloads_per_session
        self._records: dict[str, _DownloadRecord] = {}
        self._lock = RLock()

    def issue(
        self,
        *,
        session_id: str,
        filename: str,
        content: bytes,
        media_type: str,
        now: int | None = None,
    ) -> GuestDownloadTicket:
        self._validate_session(session_id)
        self._validate_filename(filename)
        if not isinstance(content, bytes) or not content or len(content) > self.max_download_bytes:
            raise GuestDownloadCapacityError("guest download content exceeds the limit")
        if not isinstance(media_type, str) or not _MEDIA_TYPE_PATTERN.fullmatch(media_type):
            raise GuestDownloadError("guest download media type is invalid")
        current = int(time.time()) if now is None else int(now)
        with self._lock:
            self._purge_expired(current)
            session_count = sum(
                record.session_id == session_id for record in self._records.values()
            )
            if (
                len(self._records) >= self.max_downloads
                or session_count >= self.max_downloads_per_session
            ):
                raise GuestDownloadCapacityError("guest download capacity is full")
            token = secrets.token_urlsafe(32)
            while token in self._records:  # pragma: no cover - cryptographic collision guard
                token = secrets.token_urlsafe(32)
            expires_at = current + self.ttl_seconds
            self._records[token] = _DownloadRecord(
                session_id=session_id,
                filename=filename,
                content=bytes(content),
                media_type=media_type,
                expires_at=expires_at,
            )
        return GuestDownloadTicket(token=token, expires_at=expires_at)

    def consume(
        self,
        *,
        token: str,
        session_id: str,
        now: int | None = None,
    ) -> GuestDownloadPayload:
        self._validate_session(session_id)
        if not isinstance(token, str) or not _TOKEN_PATTERN.fullmatch(token):
            raise GuestDownloadError("guest download token is invalid")
        current = int(time.time()) if now is None else int(now)
        with self._lock:
            record = self._records.get(token)
            if record is None:
                self._purge_expired(current)
                raise GuestDownloadError("guest download is unavailable")
            if record.expires_at <= current:
                self._records.pop(token, None)
                raise GuestDownloadError("guest download has expired")
            if not secrets.compare_digest(record.session_id, session_id):
                raise GuestDownloadError("guest download is unavailable")
            self._records.pop(token, None)
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
        return len(tokens)

    def _purge_expired(self, now: int) -> None:
        expired = [
            token for token, record in self._records.items() if record.expires_at <= now
        ]
        for token in expired:
            self._records.pop(token, None)

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
    "DEFAULT_MAX_DOWNLOAD_BYTES",
    "GuestDownloadCapacityError",
    "GuestDownloadError",
    "GuestDownloadPayload",
    "GuestDownloadRegistry",
    "GuestDownloadTicket",
    "guest_download_registry",
]
