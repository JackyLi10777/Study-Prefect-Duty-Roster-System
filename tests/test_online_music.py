from __future__ import annotations

from pathlib import Path

import pytest

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.services.music_library import MusicLibraryError
from nicegui_app.services.online_music import (
    YouTubePlaylistLibrary,
    YouTubeSettings,
    extract_youtube_playlist_id,
    parse_youtube_search,
    youtube_embed_url,
)
from tests.ui_source import combined_theme_source


def test_youtube_public_player_is_enabled_without_paid_account(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SING_YIN_YOUTUBE_ENABLED", raising=False)
    monkeypatch.delenv("SING_YIN_YOUTUBE_API_KEY", raising=False)
    settings = YouTubeSettings.from_environment()
    assert settings.enabled is True
    assert settings.search_enabled is False


def test_youtube_playlist_urls_are_validated_and_stored_by_context(tmp_path: Path) -> None:
    library = YouTubePlaylistLibrary(tmp_path / "music")
    playlist = library.add(
        title="Quiet hymns",
        url_or_id="https://www.youtube.com/playlist?list=PL_TEST-123",
        context="devotional",
    )
    assert playlist.playlist_id == "PL_TEST-123"
    assert library.for_context("devotional") == [playlist]
    assert "youtube-nocookie.com/embed/videoseries" in playlist.embed_url
    library.remove(playlist.id)
    assert library.all() == []


def test_youtube_rejects_non_youtube_or_missing_playlist() -> None:
    with pytest.raises(MusicLibraryError, match="youtube_url"):
        extract_youtube_playlist_id("https://example.com/playlist?list=PL_TEST")
    with pytest.raises(MusicLibraryError, match="youtube_url"):
        extract_youtube_playlist_id("https://youtube.com/watch?v=abc123")


def test_youtube_search_parser_keeps_only_safe_video_and_playlist_ids() -> None:
    payload = {
        "items": [
            {"id": {"videoId": "video_123"}, "snippet": {"title": "Song", "channelTitle": "Choir", "thumbnails": {"medium": {"url": "https://i.ytimg.com/vi/video_123/mqdefault.jpg"}}}},
            {"id": {"playlistId": "PL_456789"}, "snippet": {"title": "Hymns", "channelTitle": "Church", "thumbnails": {"medium": {"url": "https://img.example/untrusted.jpg"}}}},
            {"id": {}, "snippet": {"title": "Invalid"}},
        ]
    }
    results = parse_youtube_search(payload)
    assert [item["kind"] for item in results] == ["video", "playlist"]
    assert results[0]["thumbnail"].startswith("https://i.ytimg.com/")
    assert results[1]["thumbnail"] == ""


def test_youtube_ui_is_visible_controlled_and_never_autoplays() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "youtube_music.py").read_text(encoding="utf-8")
    theme = combined_theme_source()
    assert "www.youtube-nocookie.com" not in source  # URLs are produced only by the validated service.
    assert 'class="sy-youtube-player"' in source
    assert 'allow="encrypted-media; picture-in-picture"' in source
    assert 'loading="lazy" referrerpolicy="no-referrer"' in source
    assert "autoplay" not in source.lower()
    assert "enablejsapi" not in youtube_embed_url(video_id="video_123")
    assert ".sy-youtube-frame-wrap" in theme
    assert "Apple Music" not in source


def test_youtube_embed_requires_exactly_one_resource() -> None:
    with pytest.raises(ValueError):
        youtube_embed_url()
