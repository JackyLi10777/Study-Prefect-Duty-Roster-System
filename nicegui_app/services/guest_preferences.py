"""Bounded process-local preferences for one verified Guest session.

Guest interface preferences must survive a NiceGUI reconnect, but they must
never enter durable user storage.  This registry deliberately stores only a
small allow-list of JSON scalar values and is cleared with the authenticated
Guest session or when the origin restarts.
"""

from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
import time
from typing import Any, Callable

from nicegui_app.services.guest_workspace import GuestCapacityError


_ALLOWED_KEYS = frozenset(
    {
        "audio_setup_seen",
        "dashboard_verse_offset",
        "devotional_tone",
        "locale",
        "music_autoplay_enabled",
        "music_playback_mode",
        "music_profile",
        "music_volume",
        "music_volume_default_revision",
        "sound_feedback",
        "sound_volume",
        "theme",
        "theme_system_resolved",
    }
)
_MUSIC_TRACK_PREFIX = "music_track_"
_MAX_KEY_LENGTH = 96
_MAX_STRING_LENGTH = 256
DEFAULT_GUEST_PREFERENCE_TTL_SECONDS = 30 * 60
DEFAULT_GUEST_PREFERENCE_MAX_SESSIONS = 24


@dataclass
class _PreferenceRecord:
    expires_at: int
    values: dict[str, Any] = field(default_factory=dict)


def _allowed_key(key: object) -> bool:
    return (
        isinstance(key, str)
        and 0 < len(key) <= _MAX_KEY_LENGTH
        and (key in _ALLOWED_KEYS or key.startswith(_MUSIC_TRACK_PREFIX))
    )


def _safe_value(value: object) -> bool:
    return value is None or isinstance(value, (bool, int, float)) or (
        isinstance(value, str) and len(value) <= _MAX_STRING_LENGTH
    )


def _safe_preference(key: str, value: object) -> bool:
    """Validate bounded scalars plus the tighter browser-theme hint domain."""

    if key == "theme_system_resolved":
        return isinstance(value, str) and value in {"light", "dark"}
    return _safe_value(value)


class GuestPreferenceStore(MutableMapping[str, Any]):
    """A mapping view whose reads and writes remain protected by one lock."""

    def __init__(self, registry: "GuestPreferenceRegistry", session_id: str) -> None:
        self._registry = registry
        self._session_id = session_id

    def __getitem__(self, key: str) -> Any:
        with self._registry._lock:
            return self._registry._values_locked(self._session_id)[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if not _allowed_key(key) or not _safe_preference(key, value):
            raise ValueError("guest preference is not an allowed bounded scalar")
        with self._registry._lock:
            self._registry._values_locked(self._session_id)[key] = value

    def __delitem__(self, key: str) -> None:
        with self._registry._lock:
            del self._registry._values_locked(self._session_id)[key]

    def __iter__(self) -> Iterator[str]:
        with self._registry._lock:
            try:
                values = self._registry._values_locked(self._session_id)
            except KeyError:
                values = {}
            return iter(tuple(values))

    def __len__(self) -> int:
        with self._registry._lock:
            try:
                return len(self._registry._values_locked(self._session_id))
            except KeyError:
                return 0


class GuestPreferenceRegistry:
    """Own session-scoped preferences without files, SQLite, or browser storage."""

    def __init__(
        self,
        *,
        ttl_seconds: int = DEFAULT_GUEST_PREFERENCE_TTL_SECONDS,
        max_sessions: int = DEFAULT_GUEST_PREFERENCE_MAX_SESSIONS,
        clock: Callable[[], int] | None = None,
    ) -> None:
        if ttl_seconds <= 0 or max_sessions <= 0:
            raise ValueError("guest preference limits must be positive")
        self.ttl_seconds = int(ttl_seconds)
        self.max_sessions = int(max_sessions)
        self._clock = clock or (lambda: int(time.time()))
        self._sessions: dict[str, _PreferenceRecord] = {}
        self._lock = RLock()

    def store_for(
        self,
        session_id: str,
        *,
        expires_at: datetime | int | None = None,
    ) -> GuestPreferenceStore:
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("guest preference session ID is required")
        current = self._clock()
        requested_expiry = self._expiry_epoch(expires_at, current=current)
        with self._lock:
            self._purge_expired_locked(current)
            record = self._sessions.get(session_id)
            if record is None:
                if len(self._sessions) >= self.max_sessions:
                    # Match the bounded workspace service: an admitted,
                    # unexpired session keeps its state until cleanup or
                    # expiry.  A later arrival must never silently evict it.
                    raise GuestCapacityError("guest session capacity is full")
                self._sessions[session_id] = _PreferenceRecord(requested_expiry)
            else:
                record.expires_at = requested_expiry
        return GuestPreferenceStore(self, session_id)

    def cleanup_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    @property
    def active_session_count(self) -> int:
        with self._lock:
            self._purge_expired_locked(self._clock())
            return len(self._sessions)

    def purge_expired(self, *, now: int | None = None) -> int:
        with self._lock:
            return self._purge_expired_locked(self._clock() if now is None else int(now))

    def _values_locked(self, session_id: str) -> dict[str, Any]:
        self._purge_expired_locked(self._clock())
        record = self._sessions.get(session_id)
        if record is None:
            raise KeyError(session_id)
        return record.values

    def _purge_expired_locked(self, current: int) -> int:
        expired = [
            session_id
            for session_id, record in self._sessions.items()
            if record.expires_at <= current
        ]
        for session_id in expired:
            del self._sessions[session_id]
        return len(expired)

    def _expiry_epoch(self, expires_at: datetime | int | None, *, current: int) -> int:
        if isinstance(expires_at, datetime):
            requested = int(expires_at.timestamp())
        elif expires_at is None:
            requested = current + self.ttl_seconds
        else:
            requested = int(expires_at)
        if requested <= current:
            raise ValueError("guest preference session has already expired")
        return min(requested, current + self.ttl_seconds)


__all__ = [
    "DEFAULT_GUEST_PREFERENCE_MAX_SESSIONS",
    "DEFAULT_GUEST_PREFERENCE_TTL_SECONDS",
    "GuestPreferenceRegistry",
    "GuestPreferenceStore",
]
