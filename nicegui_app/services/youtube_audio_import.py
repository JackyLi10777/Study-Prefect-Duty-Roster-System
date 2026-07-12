"""Controlled YouTube/YouTube Music audio import into the local music library.

This adapter owns no roster data. It accepts only public YouTube URLs, runs a
bounded yt-dlp job without cookies or account access, and registers validated
M4A results through ``MusicLibrary``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import parse_qs, urlparse

from nicegui_app.config import MUSIC_DIR
from nicegui_app.services.music_library import (
    MAX_AUDIO_BYTES,
    MUSIC_CONTEXTS,
    MusicLibrary,
    MusicLibraryError,
    MusicTrack,
)


MAX_YOUTUBE_IMPORT_TRACKS = 25
YOUTUBE_IMPORT_TOTAL_BYTES = 150 * 1024 * 1024
_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


class YouTubeAudioImportError(RuntimeError):
    """Safe, bilingual-code-addressable import failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class YouTubeAudioImportResult:
    tracks: tuple[MusicTrack, ...]
    skipped_duplicates: int = 0


DownloaderFactory = Callable[[dict[str, Any]], AbstractContextManager[Any]]


def validate_youtube_media_url(value: str) -> str:
    """Accept public video, short, or playlist share URLs from YouTube only."""
    clean = value.strip()
    parsed = urlparse(clean)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in _YOUTUBE_HOSTS:
        raise YouTubeAudioImportError("url")
    if host.endswith("youtu.be"):
        if not parsed.path.strip("/"):
            raise YouTubeAudioImportError("url")
        return clean
    query = parse_qs(parsed.query)
    is_video = parsed.path == "/watch" and bool(query.get("v"))
    is_playlist = parsed.path == "/playlist" and bool(query.get("list"))
    is_short = parsed.path.startswith("/shorts/") and len(parsed.path.split("/")) >= 3
    if not (is_video or is_playlist or is_short):
        raise YouTubeAudioImportError("url")
    return clean


def _default_downloader_factory(options: dict[str, Any]) -> AbstractContextManager[Any]:
    from yt_dlp import YoutubeDL

    return YoutubeDL(options)


class YouTubeAudioImporter:
    """Download bounded public audio and atomically add it to ``MusicLibrary``."""

    def __init__(
        self,
        root: Path = MUSIC_DIR,
        *,
        downloader_factory: DownloaderFactory = _default_downloader_factory,
    ) -> None:
        self.root = Path(root)
        self.library = MusicLibrary(self.root)
        self.staging_root = self.root / ".youtube-import-staging"
        self.downloader_factory = downloader_factory

    def import_url(self, *, url: str, context: str) -> YouTubeAudioImportResult:
        clean_url = validate_youtube_media_url(url)
        if context not in MUSIC_CONTEXTS:
            raise YouTubeAudioImportError("context")
        self.staging_root.mkdir(parents=True, exist_ok=True)
        tracks: list[MusicTrack] = []
        skipped_duplicates = 0
        try:
            with TemporaryDirectory(prefix="job-", dir=self.staging_root) as temporary:
                stage = Path(temporary).resolve()
                options = self._options(stage)
                try:
                    with self.downloader_factory(options) as downloader:
                        information = downloader.extract_info(clean_url, download=True)
                except Exception as error:
                    raise YouTubeAudioImportError("download") from error

                candidates = list(self._downloaded_entries(information, stage))[:MAX_YOUTUBE_IMPORT_TRACKS]
                if not candidates:
                    raise YouTubeAudioImportError("no_audio")
                total_bytes = sum(path.stat().st_size for _, path in candidates)
                if total_bytes > YOUTUBE_IMPORT_TOTAL_BYTES:
                    raise YouTubeAudioImportError("total_size")
                try:
                    for entry, path in candidates:
                        try:
                            track = self.library.add_downloaded_audio(
                                source_path=path,
                                context=context,
                                title=str(entry.get("title") or path.stem),
                                artist=str(entry.get("artist") or entry.get("uploader") or "YouTube local import"),
                                source_id=str(entry.get("id") or ""),
                            )
                        except MusicLibraryError as error:
                            if error.code == "duplicate":
                                skipped_duplicates += 1
                                continue
                            raise YouTubeAudioImportError(error.code) from error
                        tracks.append(track)
                except Exception:
                    for track in reversed(tracks):
                        try:
                            self.library.remove_local_audio(track.id)
                        except MusicLibraryError:
                            pass
                    tracks.clear()
                    raise
        finally:
            self._remove_empty_staging_root()

        if not tracks and skipped_duplicates:
            raise YouTubeAudioImportError("duplicate")
        if not tracks:
            raise YouTubeAudioImportError("no_audio")
        return YouTubeAudioImportResult(tuple(tracks), skipped_duplicates)

    @staticmethod
    def _options(stage: Path) -> dict[str, Any]:
        runtime = deno_runtime_path()
        return {
            "format": "bestaudio[ext=m4a]",
            "outtmpl": str(stage / "%(title).150B [%(id)s].%(ext)s"),
            "windowsfilenames": True,
            "playlistend": MAX_YOUTUBE_IMPORT_TRACKS,
            "max_filesize": MAX_AUDIO_BYTES,
            "socket_timeout": 20,
            "retries": 3,
            "fragment_retries": 3,
            "continuedl": True,
            "overwrites": False,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "ignoreerrors": False,
            "noplaylist": False,
            "extract_flat": False,
            "js_runtimes": {"deno": {"path": str(runtime)}} if runtime else {"deno": {}},
        }

    @classmethod
    def _downloaded_entries(cls, information: Any, stage: Path) -> Iterator[tuple[dict[str, Any], Path]]:
        seen: set[Path] = set()
        for entry in cls._flatten_entries(information):
            downloads = entry.get("requested_downloads") or []
            raw_paths = [item.get("filepath") for item in downloads if isinstance(item, dict)]
            raw_paths.append(entry.get("_filename"))
            for raw_path in raw_paths:
                if not raw_path:
                    continue
                path = Path(str(raw_path)).resolve()
                if path in seen or stage not in path.parents or not path.is_file():
                    continue
                seen.add(path)
                yield entry, path

    @classmethod
    def _flatten_entries(cls, information: Any) -> Iterator[dict[str, Any]]:
        if not isinstance(information, dict):
            return
        entries = information.get("entries")
        if entries is not None:
            for entry in entries:
                yield from cls._flatten_entries(entry)
            return
        yield information

    def _remove_empty_staging_root(self) -> None:
        try:
            if self.staging_root.is_dir() and not any(self.staging_root.iterdir()):
                self.staging_root.rmdir()
        except OSError:
            # A later import can safely reuse the private staging directory.
            pass


def youtube_import_ready() -> bool:
    """Report dependency readiness without making any network request."""
    return _yt_dlp_available() and deno_runtime_path() is not None


def deno_runtime_path() -> Path | None:
    """Find the locked Deno wheel even when the venv Scripts dir is not on PATH."""
    executable_name = "deno.exe" if sys.platform == "win32" else "deno"
    beside_python = Path(sys.executable).resolve().with_name(executable_name)
    if beside_python.is_file():
        return beside_python
    discovered = shutil.which("deno")
    return Path(discovered).resolve() if discovered else None


def _yt_dlp_available() -> bool:
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        return False
    return True
