from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
from threading import Barrier
from time import monotonic, sleep

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


def test_parallel_youtube_playlist_updates_preserve_every_catalog_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "music"
    libraries = [YouTubePlaylistLibrary(root) for _ in range(4)]
    start = Barrier(len(libraries))
    original_write = YouTubePlaylistLibrary._write

    def delayed_write(library: YouTubePlaylistLibrary, playlists) -> None:  # type: ignore[no-untyped-def]
        sleep(0.03)
        original_write(library, playlists)

    monkeypatch.setattr(YouTubePlaylistLibrary, "_write", delayed_write)

    def add(index_and_library):  # type: ignore[no-untyped-def]
        index, library = index_and_library
        start.wait(timeout=5)
        return library.add(
            title=f"Quiet hymns {index}",
            url_or_id=f"PL_TEST-{index:03d}",
            context="devotional",
        )

    with ThreadPoolExecutor(max_workers=len(libraries)) as executor:
        playlists = list(executor.map(add, enumerate(libraries)))

    catalog = YouTubePlaylistLibrary(root).all()
    assert {item.id for item in catalog} == {item.id for item in playlists}
    assert not [path for path in root.iterdir() if path.name.endswith(".tmp")]


def test_parallel_python_processes_preserve_every_youtube_playlist_entry(tmp_path: Path) -> None:
    root = tmp_path / "music"
    go = tmp_path / "go"
    process_count = 8
    child = """
import sys
import time
from pathlib import Path
from nicegui_app.services.online_music import YouTubePlaylistLibrary

root, go, ready, index = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4])
library = YouTubePlaylistLibrary(root)
original_write = library._write

def delayed_write(playlists):
    time.sleep(0.08)
    original_write(playlists)

library._write = delayed_write
ready.write_text('ready', encoding='utf-8')
while not go.exists():
    time.sleep(0.005)
library.add(
    title=f'Process playlist {index}',
    url_or_id=f'PL_PROCESS-{index:04d}',
    context='devotional',
)
"""
    processes: list[subprocess.Popen[str]] = []
    ready_paths = [tmp_path / f"ready-{index}" for index in range(process_count)]
    try:
        for index, ready in enumerate(ready_paths):
            processes.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        "-X",
                        "utf8",
                        "-c",
                        child,
                        str(root),
                        str(go),
                        str(ready),
                        str(index),
                    ],
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                )
            )
        deadline = monotonic() + 15
        while not all(path.exists() for path in ready_paths) and monotonic() < deadline:
            sleep(0.02)
        assert all(path.exists() for path in ready_paths), "child processes did not reach the write barrier"
        go.write_text("go", encoding="utf-8")

        failures: list[str] = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=20)
            if process.returncode != 0:
                failures.append(f"exit={process.returncode}\n{stdout}\n{stderr}")
        assert not failures, "\n".join(failures)
    finally:
        go.write_text("go", encoding="utf-8")
        for process in processes:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)

    catalog = YouTubePlaylistLibrary(root).all()
    assert len(catalog) == process_count
    assert {item.title for item in catalog} == {
        f"Process playlist {index}" for index in range(process_count)
    }


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
    assert 'data-testid=youtube-player-panel' in source
    assert 'ui.label(t("youtube_disabled"))' in source
    assert "enablejsapi" not in youtube_embed_url(video_id="video_123")
    assert ".sy-youtube-frame-wrap" in theme
    assert "Apple Music" not in source


def test_youtube_embed_requires_exactly_one_resource() -> None:
    with pytest.raises(ValueError):
        youtube_embed_url()
