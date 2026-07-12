from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from nicegui_app.services.youtube_audio_import import (
    MAX_YOUTUBE_IMPORT_TRACKS,
    YouTubeAudioImportError,
    YouTubeAudioImporter,
    validate_youtube_media_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=video_123",
        "https://music.youtube.com/watch?v=video_123&list=PL_123456",
        "https://youtu.be/video_123?si=share",
        "https://www.youtube.com/playlist?list=PL_123456",
        "https://www.youtube.com/shorts/video_123",
    ],
)
def test_youtube_media_url_accepts_video_music_playlist_and_share_links(url: str) -> None:
    assert validate_youtube_media_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "http://youtube.com/watch?v=video_123",
        "https://example.com/watch?v=video_123",
        "https://youtube.com/channel/channel_123",
        "not a url",
    ],
)
def test_youtube_media_url_rejects_non_https_non_media_and_non_youtube_values(url: str) -> None:
    with pytest.raises(YouTubeAudioImportError, match="url"):
        validate_youtube_media_url(url)


def test_youtube_import_is_bounded_cookie_free_and_registers_local_m4a(tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    class FakeDownloader:
        def __init__(self, options: dict[str, Any]) -> None:
            captured.update(options)

        def __enter__(self) -> "FakeDownloader":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def extract_info(self, _url: str, *, download: bool) -> dict[str, Any]:
            assert download is True
            target = Path(captured["outtmpl"]).parent / "Quiet hymn [video_123].m4a"
            target.write_bytes(b"\x00\x00\x00\x18ftypM4A " + b"\x00" * 12)
            return {
                "id": "video_123",
                "title": "Quiet hymn",
                "uploader": "Choir",
                "requested_downloads": [{"filepath": str(target)}],
            }

    importer = YouTubeAudioImporter(tmp_path / "music", downloader_factory=FakeDownloader)
    result = importer.import_url(url="https://youtu.be/video_123", context="devotional")

    assert len(result.tracks) == 1
    assert result.tracks[0].filename.startswith("youtube-imports/")
    assert captured["playlistend"] == MAX_YOUTUBE_IMPORT_TRACKS
    assert captured["max_filesize"] == 25 * 1024 * 1024
    assert captured["format"] == "bestaudio[ext=m4a]"
    assert captured["js_runtimes"]["deno"]["path"].lower().endswith(("deno", "deno.exe"))
    assert not {"cookiefile", "username", "password"}.intersection(captured)
    assert not (tmp_path / "music" / ".youtube-import-staging").exists()


def test_youtube_import_returns_safe_error_without_leaking_downloader_details(tmp_path: Path) -> None:
    class FailingDownloader:
        def __init__(self, _options: dict[str, Any]) -> None:
            pass

        def __enter__(self) -> "FailingDownloader":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def extract_info(self, _url: str, *, download: bool) -> dict[str, Any]:
            raise RuntimeError("private upstream details")

    importer = YouTubeAudioImporter(tmp_path / "music", downloader_factory=FailingDownloader)
    with pytest.raises(YouTubeAudioImportError, match="^download$"):
        importer.import_url(url="https://youtube.com/watch?v=video_123", context="dashboard")


def test_youtube_playlist_import_rolls_back_earlier_tracks_if_a_later_file_is_invalid(tmp_path: Path) -> None:
    class PartlyInvalidDownloader:
        def __init__(self, options: dict[str, Any]) -> None:
            self.stage = Path(options["outtmpl"]).parent

        def __enter__(self) -> "PartlyInvalidDownloader":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def extract_info(self, _url: str, *, download: bool) -> dict[str, Any]:
            valid = self.stage / "Valid [one].m4a"
            invalid = self.stage / "Invalid [two].mp3"
            valid.write_bytes(b"\x00\x00\x00\x18ftypM4A " + b"\x00" * 12)
            invalid.write_bytes(b"not an mp3")
            return {
                "entries": [
                    {"id": "one", "title": "Valid", "requested_downloads": [{"filepath": str(valid)}]},
                    {"id": "two", "title": "Invalid", "requested_downloads": [{"filepath": str(invalid)}]},
                ]
            }

    root = tmp_path / "music"
    importer = YouTubeAudioImporter(root, downloader_factory=PartlyInvalidDownloader)
    with pytest.raises(YouTubeAudioImportError, match="^content$"):
        importer.import_url(url="https://youtube.com/playlist?list=PL_123456", context="devotional")

    assert importer.library.all_custom_tracks() == []
    assert not list((root / "youtube-imports").glob("*"))
