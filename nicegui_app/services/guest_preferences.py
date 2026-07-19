"""Bounded process-local preferences for one verified Guest session.

Guest interface preferences must survive a NiceGUI reconnect, but they must
never enter durable user storage.  This registry deliberately stores only a
small allow-list of JSON scalar values and is cleared with the authenticated
Guest session or when the origin restarts.
"""

from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from threading import RLock
from typing import Any


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
    }
)
_MUSIC_TRACK_PREFIX = "music_track_"
_MAX_KEY_LENGTH = 96
_MAX_STRING_LENGTH = 256


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


class GuestPreferenceStore(MutableMapping[str, Any]):
    """A mapping view whose reads and writes remain protected by one lock."""

    def __init__(self, registry: "GuestPreferenceRegistry", session_id: str) -> None:
        self._registry = registry
        self._session_id = session_id

    def __getitem__(self, key: str) -> Any:
        with self._registry._lock:
            return self._registry._sessions[self._session_id][key]

    def __setitem__(self, key: str, value: Any) -> None:
        if not _allowed_key(key) or not _safe_value(value):
            raise ValueError("guest preference is not an allowed bounded scalar")
        with self._registry._lock:
            self._registry._sessions.setdefault(self._session_id, {})[key] = value

    def __delitem__(self, key: str) -> None:
        with self._registry._lock:
            del self._registry._sessions[self._session_id][key]

    def __iter__(self) -> Iterator[str]:
        with self._registry._lock:
            return iter(tuple(self._registry._sessions.get(self._session_id, {})))

    def __len__(self) -> int:
        with self._registry._lock:
            return len(self._registry._sessions.get(self._session_id, {}))


class GuestPreferenceRegistry:
    """Own session-scoped preferences without files, SQLite, or browser storage."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = RLock()

    def store_for(self, session_id: str) -> GuestPreferenceStore:
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("guest preference session ID is required")
        with self._lock:
            self._sessions.setdefault(session_id, {})
        return GuestPreferenceStore(self, session_id)

    def cleanup_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    @property
    def active_session_count(self) -> int:
        with self._lock:
            return len(self._sessions)


__all__ = ["GuestPreferenceRegistry", "GuestPreferenceStore"]
