from __future__ import annotations

import random
from pathlib import Path

import pytest

from nicegui_app.config import MUSIC_DIR, PROJECT_ROOT
from tests.ui_source import combined_page_source
from nicegui_app.services.music_library import (
    BUILTIN_TRACKS,
    MUSIC_CONTEXTS,
    MusicLibrary,
    MusicLibraryError,
    next_track_id,
)


def test_builtin_music_catalog_is_complete_local_and_page_categorised() -> None:
    assert len(BUILTIN_TRACKS) == 13
    assert len({track.id for track in BUILTIN_TRACKS}) == 13
    assert len({track.filename for track in BUILTIN_TRACKS}) == 13
    assert all((MUSIC_DIR / track.filename).is_file() for track in BUILTIN_TRACKS)
    assert all((MUSIC_DIR / track.filename).stat().st_size > 0 for track in BUILTIN_TRACKS)
    assert {context for track in BUILTIN_TRACKS for context in track.contexts} == set(MUSIC_CONTEXTS)
    assert all(sum(context in track.contexts for track in BUILTIN_TRACKS) >= 2 for context in MUSIC_CONTEXTS)


def test_local_music_import_is_validated_and_kept_inside_custom_directory(tmp_path: Path) -> None:
    library = MusicLibrary(tmp_path / "music")
    m4a = b"\x00\x00\x00\x18ftypM4A " + b"\x00" * 12

    track = library.add_local_audio(original_name="My quiet hymn.m4a", content=m4a, context="devotional")

    assert track.custom is True
    assert track.title == "My quiet hymn"
    assert track.filename.startswith("custom/custom-")
    target = (library.root / track.filename).resolve()
    assert target.is_file()
    assert library.root.resolve() in target.parents
    assert [item.id for item in library.tracks_for_context("devotional") if item.custom] == [track.id]

    library.remove_local_audio(track.id)
    assert not target.exists()
    assert not library.all_custom_tracks()


@pytest.mark.parametrize(
    ("name", "content", "code"),
    [
        ("track.exe", b"MZ", "format"),
        ("track.m4a", b"not an audio file", "content"),
        ("track.mp3", b"", "size"),
    ],
)
def test_local_music_import_rejects_unsafe_or_mismatched_files(tmp_path: Path, name: str, content: bytes, code: str) -> None:
    library = MusicLibrary(tmp_path / "music")
    with pytest.raises(MusicLibraryError, match=code):
        library.add_local_audio(original_name=name, content=content, context="dashboard")


def test_music_library_ignores_removed_youtube_transition_state(tmp_path: Path) -> None:
    root = tmp_path / "music"
    root.mkdir()
    (root / "custom-library.json").write_text(
        '{"version": 1, "localTracks": [], "youtubeLinks": [{"id": "old-link"}]}',
        encoding="utf-8",
    )
    library = MusicLibrary(root)
    assert library.all_custom_tracks() == []
    assert "youtube" not in library._state()  # noqa: SLF001 - verifies safe legacy-state migration


def test_playlist_next_track_supports_sequential_loop_and_no_immediate_shuffle_repeat() -> None:
    tracks = ["a", "b", "c"]
    assert next_track_id(tracks, "a", "sequential") == "b"
    assert next_track_id(tracks, "c", "sequential") == "a"
    assert next_track_id(tracks, "missing", "sequential") == "a"
    assert next_track_id(tracks, "b", "shuffle", rng=random.Random(7)) in {"a", "c"}


def test_music_ui_is_manual_and_absent_from_sensitive_workflows() -> None:
    music_ui = (PROJECT_ROOT / "nicegui_app" / "ui" / "music.py").read_text(encoding="utf-8")
    pages = combined_page_source()
    main = (PROJECT_ROOT / "nicegui_app" / "main.py").read_text(encoding="utf-8")

    assert "autoplay=False" in music_ui
    assert "loop=False" in music_ui
    assert 'audio.on("ended", advance_playlist)' in music_ui
    assert '"sequential": t("music_mode_sequential")' in music_ui
    assert '"shuffle": t("music_mode_shuffle")' in music_ui
    assert 'music_context="devotional"' in pages
    assert 'music_context="handover"' in pages
    assert 'with page_shell("adjustments", "/rosters")' in pages
    assert 'with page_shell("settings", "/settings")' in pages
    assert 'url_path="/assets/music"' in main
    assert "YoutubeMusicLink" not in music_ui
    assert "add_youtube_link" not in music_ui
