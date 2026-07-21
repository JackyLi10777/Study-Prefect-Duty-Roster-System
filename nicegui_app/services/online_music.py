"""Official YouTube playlist settings and local non-sensitive catalogue."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from nicegui_app.config import MUSIC_DIR
from nicegui_app.services.json_catalog import locked_json_catalog, write_json_atomically
from nicegui_app.services.music_library import MUSIC_CONTEXTS, MusicLibraryError


_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{6,100}$")
_YOUTUBE_THUMBNAIL_HOSTS = {"i.ytimg.com", "img.youtube.com"}
YOUTUBE_SEARCH_TIMEOUT_SECONDS = 10
MAX_YOUTUBE_SEARCH_RESPONSE_BYTES = 256 * 1024


class YouTubeSearchError(RuntimeError):
    """Stable, operator-facing failure classification for remote search."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class YouTubeSettings:
    enabled: bool
    api_key: str

    @classmethod
    def from_environment(cls) -> "YouTubeSettings":
        return cls(
            enabled=os.getenv("SING_YIN_YOUTUBE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"},
            api_key=os.getenv("SING_YIN_YOUTUBE_API_KEY", "").strip(),
        )

    @property
    def search_enabled(self) -> bool:
        return self.enabled and bool(self.api_key)


@dataclass(frozen=True)
class YouTubePlaylist:
    id: str
    title: str
    playlist_id: str
    context: str

    @property
    def embed_url(self) -> str:
        return youtube_embed_url(playlist_id=self.playlist_id)


class YouTubePlaylistLibrary:
    def __init__(self, root: Path = MUSIC_DIR) -> None:
        self.root = Path(root)
        self.state_path = self.root / "youtube-playlists.json"

    def all(self) -> list[YouTubePlaylist]:
        return [self._playlist(item) for item in self._state()]

    def for_context(self, context: str) -> list[YouTubePlaylist]:
        _require_context(context)
        return [item for item in self.all() if item.context == context]

    def add(self, *, title: str, url_or_id: str, context: str) -> YouTubePlaylist:
        _require_context(context)
        clean_title = " ".join(title.split())[:120]
        if not clean_title:
            raise MusicLibraryError("title")
        playlist_id = extract_youtube_playlist_id(url_or_id)
        with locked_json_catalog(self.state_path):
            state = self._state()
            if any(item.get("playlistId") == playlist_id and item.get("context") == context for item in state):
                raise MusicLibraryError("duplicate")
            playlist = YouTubePlaylist(f"youtube-{uuid4().hex}", clean_title, playlist_id, context)
            state.append({"id": playlist.id, "title": playlist.title, "playlistId": playlist.playlist_id, "context": context})
            self._write(state)
        return playlist

    def remove(self, playlist_id: str) -> None:
        with locked_json_catalog(self.state_path):
            state = self._state()
            if not any(item.get("id") == playlist_id for item in state):
                raise MusicLibraryError("missing")
            self._write([item for item in state if item.get("id") != playlist_id])

    def _state(self) -> list[dict[str, Any]]:
        with locked_json_catalog(self.state_path):
            if not self.state_path.exists():
                return []
            try:
                payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise MusicLibraryError("library") from error
            return list(payload.get("playlists", []))

    def _write(self, playlists: list[dict[str, Any]]) -> None:
        with locked_json_catalog(self.state_path):
            write_json_atomically(self.state_path, {"version": 1, "playlists": playlists})

    @staticmethod
    def _playlist(item: dict[str, Any]) -> YouTubePlaylist:
        context = str(item.get("context", ""))
        _require_context(context)
        return YouTubePlaylist(str(item["id"]), str(item["title"]), extract_youtube_playlist_id(str(item["playlistId"])), context)


def extract_youtube_playlist_id(value: str) -> str:
    clean = value.strip()
    parsed = urlparse(clean)
    if parsed.scheme:
        host = (parsed.hostname or "").lower()
        if host not in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
            raise MusicLibraryError("youtube_url")
        clean = parse_qs(parsed.query).get("list", [""])[0]
    if not _YOUTUBE_ID.fullmatch(clean):
        raise MusicLibraryError("youtube_url")
    return clean


def youtube_embed_url(*, playlist_id: str | None = None, video_id: str | None = None) -> str:
    if bool(playlist_id) == bool(video_id):
        raise ValueError("Provide exactly one YouTube playlist or video ID.")
    if playlist_id:
        safe_id = extract_youtube_playlist_id(playlist_id)
        return f"https://www.youtube-nocookie.com/embed/videoseries?list={safe_id}&controls=1&playsinline=1&rel=0"
    if not video_id or not _YOUTUBE_ID.fullmatch(video_id):
        raise MusicLibraryError("youtube_url")
    return f"https://www.youtube-nocookie.com/embed/{video_id}?controls=1&playsinline=1&rel=0"


def search_youtube(
    term: str,
    settings: YouTubeSettings,
    *,
    opener: Any = urlopen,
) -> list[dict[str, str]]:
    clean_term = " ".join(term.split())[:80]
    if len(clean_term) < 2 or not settings.search_enabled:
        return []
    url = (
        "https://www.googleapis.com/youtube/v3/search?part=snippet&type=video%2Cplaylist&maxResults=8&safeSearch=strict"
        f"&q={quote_plus(clean_term)}&key={quote_plus(settings.api_key)}"
    )
    parsed_url = urlparse(url)
    if parsed_url.scheme != "https" or parsed_url.hostname != "www.googleapis.com":
        raise MusicLibraryError("youtube_url")
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "Sing-Yin-Roster/1.0"})
    try:
        # The scheme and host are fixed and checked immediately above. Reading is
        # deliberately capped so a faulty upstream cannot exhaust host memory.
        with opener(request, timeout=YOUTUBE_SEARCH_TIMEOUT_SECONDS) as response:  # nosec B310
            content_type = str(response.headers.get("Content-Type", "")).lower()
            if content_type and "application/json" not in content_type:
                raise YouTubeSearchError("invalid_response")
            body = response.read(MAX_YOUTUBE_SEARCH_RESPONSE_BYTES + 1)
            if len(body) > MAX_YOUTUBE_SEARCH_RESPONSE_BYTES:
                raise YouTubeSearchError("response_too_large")
    except YouTubeSearchError:
        raise
    except HTTPError as error:
        if error.code in {401, 403}:
            code = "unauthorized"
        elif error.code == 429:
            code = "rate_limited"
        elif 500 <= error.code < 600:
            code = "unavailable"
        else:
            code = "request_failed"
        raise YouTubeSearchError(code) from error
    except (URLError, TimeoutError, OSError) as error:
        raise YouTubeSearchError("network") from error

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise YouTubeSearchError("invalid_response") from error
    if not isinstance(payload, dict):
        raise YouTubeSearchError("invalid_response")
    return parse_youtube_search(payload)


def parse_youtube_search(payload: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    items = payload.get("items", [])
    if not isinstance(items, list):
        raise YouTubeSearchError("invalid_response")
    for item in items[:8]:
        if not isinstance(item, dict):
            continue
        identity = item.get("id", {})
        snippet = item.get("snippet", {})
        if not isinstance(identity, dict) or not isinstance(snippet, dict):
            continue
        kind = "playlist" if identity.get("playlistId") else "video"
        item_id = str(identity.get("playlistId") or identity.get("videoId") or "")
        if not _YOUTUBE_ID.fullmatch(item_id):
            continue
        thumbnails = snippet.get("thumbnails", {})
        medium = thumbnails.get("medium", {}) if isinstance(thumbnails, dict) else {}
        thumbnail = str(medium.get("url", "")) if isinstance(medium, dict) else ""
        results.append(
            {
                "kind": kind,
                "id": item_id,
                "title": str(snippet.get("title") or "YouTube")[:160],
                "channel": str(snippet.get("channelTitle") or "")[:120],
                "thumbnail": thumbnail if _is_safe_youtube_thumbnail(thumbnail) else "",
            }
        )
    return results


def _is_safe_youtube_thumbnail(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and (parsed.hostname or "").lower() in _YOUTUBE_THUMBNAIL_HOSTS


def _require_context(context: str) -> None:
    if context not in MUSIC_CONTEXTS:
        raise MusicLibraryError("context")
