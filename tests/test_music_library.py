from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import random
from pathlib import Path
from threading import Barrier
from time import sleep

import pytest

from nicegui_app.config import MUSIC_DIR, PROJECT_ROOT
from nicegui_app.services import music_library as music_library_module
from nicegui_app.ui import music as music_ui_module
from nicegui_app.ui import sound as sound_ui
from tests.ui_source import combined_page_source
from nicegui_app.services.music_library import (
    BUILTIN_TRACKS,
    MUSIC_CONTEXTS,
    MUSIC_PROFILES,
    MusicLibrary,
    MusicLibraryError,
    next_track_id,
    resolve_music_profile,
)


def test_music_volume_default_upgrade_preserves_an_explicit_operator_choice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store: dict[str, object] = {}
    monkeypatch.setattr(sound_ui, "preference_get", lambda key, default=None: store.get(key, default))
    monkeypatch.setattr(sound_ui, "preference_set", lambda key, value: store.__setitem__(key, value))

    store.clear()
    assert sound_ui.preferred_music_volume() == 0.50
    assert store["music_volume"] == 0.50
    assert store["music_volume_default_revision"] == 3

    store.clear()
    store.update({"music_volume": 0.24})
    assert sound_ui.preferred_music_volume() == 0.50
    assert store["music_volume_default_revision"] == 3

    store.clear()
    store.update({"music_volume": 0.35, "music_volume_default_revision": 2})
    assert sound_ui.preferred_music_volume() == 0.50
    assert store["music_volume_default_revision"] == 3

    store.clear()
    store.update({"music_volume": 0.42, "music_volume_default_revision": "invalid"})
    assert sound_ui.preferred_music_volume() == 0.42
    assert store["music_volume_default_revision"] == 3

    store.clear()
    store.update({"music_volume": 0.35, "music_volume_default_revision": 3})
    assert sound_ui.preferred_music_volume() == 0.35
    assert store["music_volume_default_revision"] == 3

    sound_ui.set_music_volume(0.24)
    assert store["music_volume"] == 0.24
    assert store["music_volume_default_revision"] == 3


def test_builtin_music_catalog_is_complete_local_and_page_categorised() -> None:
    assert len(BUILTIN_TRACKS) == 48
    assert len({track.id for track in BUILTIN_TRACKS}) == 48
    assert len({track.filename for track in BUILTIN_TRACKS}) == 48
    assert all((MUSIC_DIR / track.filename).is_file() for track in BUILTIN_TRACKS)
    assert all((MUSIC_DIR / track.filename).stat().st_size > 0 for track in BUILTIN_TRACKS)
    assert all("(1)" not in track.filename for track in BUILTIN_TRACKS)
    assert {context for track in BUILTIN_TRACKS for context in track.contexts} == set(MUSIC_CONTEXTS)
    assert {profile for track in BUILTIN_TRACKS for profile in track.profiles} == set(MUSIC_PROFILES)
    assert {track.arrangement for track in BUILTIN_TRACKS} == {"instrumental", "vocal"}
    assert all(sum(context in track.contexts for track in BUILTIN_TRACKS) >= 2 for context in MUSIC_CONTEXTS)
    for context in MUSIC_CONTEXTS:
        for profile in MUSIC_PROFILES:
            assert MusicLibrary().tracks_for_context(context, profile=profile), (
                f"{context} must keep a local {profile} playlist so appearance-based autoplay "
                "never removes the page music control"
            )


def test_new_welcome_recordings_are_classified_without_ambiguous_duplicate_files() -> None:
    tracks = {track.id: track for track in BUILTIN_TRACKS}
    expected_arrangements = {
        "come-fill-hearts": "instrumental",
        "in-lord-thankful": "instrumental",
        "in-lord-thankful-vocal": "vocal",
        "kingdom-of-god": "instrumental",
        "kingdom-of-god-vocal": "vocal",
        "tui-amoris-ignem": "instrumental",
        "tui-amoris-ignem-vocal": "vocal",
        "nada-te-turbe": "instrumental",
        "nada-te-turbe-vocal": "vocal",
        "mon-ame-se-repose": "instrumental",
        "mon-ame-se-repose-vocal": "vocal",
        "dona-la-pace": "instrumental",
        "dona-la-pace-vocal": "vocal",
        "da-pacem-cordium-violin": "instrumental",
        "da-pacem-cordium-vocal": "vocal",
        "el-senyor": "instrumental",
    }

    assert {track_id: tracks[track_id].arrangement for track_id in expected_arrangements} == expected_arrangements
    assert all("welcome" in tracks[track_id].contexts for track_id in expected_arrangements)
    assert not any(
        track.filename.endswith("The Kingdom of God (1).m4a")
        or track.filename.endswith("The kingdom of God (2).m4a")
        for track in BUILTIN_TRACKS
    )


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


def test_music_profile_follows_appearance_until_operator_overrides_it() -> None:
    assert resolve_music_profile("auto", "light") == "bright"
    assert resolve_music_profile("auto", "dark") == "quiet"
    assert resolve_music_profile("quiet", "light") == "quiet"
    assert resolve_music_profile("bright", "dark") == "bright"


def test_youtube_downloaded_audio_is_kept_in_dedicated_directory_and_deduplicated(tmp_path: Path) -> None:
    root = tmp_path / "music"
    source = tmp_path / "download.m4a"
    source.write_bytes(b"\x00\x00\x00\x18ftypM4A " + b"\x00" * 12)
    library = MusicLibrary(root)

    track = library.add_downloaded_audio(
        source_path=source,
        context="devotional",
        title="Quiet hymn",
        artist="Choir",
        source_id="video_123",
    )

    assert track.filename.startswith("youtube-imports/youtube-")
    assert track.arrangement == "youtube"
    assert (root / track.filename).is_file()
    with pytest.raises(MusicLibraryError, match="duplicate"):
        library.add_downloaded_audio(
            source_path=source,
            context="devotional",
            title="Quiet hymn",
            artist="Choir",
            source_id="video_123",
        )


def test_downloaded_audio_revalidates_the_copied_file_before_admission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "download.m4a"
    source.write_bytes(b"\x00\x00\x00\x18ftypM4A " + b"\x00" * 12)
    library = MusicLibrary(tmp_path / "music")

    def corrupt_copy(_source: Path, destination: Path) -> None:
        Path(destination).write_bytes(b"not-an-audio-file")

    monkeypatch.setattr(music_library_module.shutil, "copyfile", corrupt_copy)

    with pytest.raises(MusicLibraryError, match="content"):
        library.add_downloaded_audio(
            source_path=source,
            context="devotional",
            title="Quiet hymn",
            artist="Choir",
            source_id="changed-during-copy",
        )
    assert not list((tmp_path / "music" / "youtube-imports").glob("*"))


def test_parallel_local_music_imports_preserve_every_catalog_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "music"
    libraries = [MusicLibrary(root) for _ in range(4)]
    start = Barrier(len(libraries))
    original_write = MusicLibrary._write_state

    def delayed_write(library: MusicLibrary, state) -> None:  # type: ignore[no-untyped-def]
        sleep(0.03)
        original_write(library, state)

    monkeypatch.setattr(MusicLibrary, "_write_state", delayed_write)
    m4a = b"\x00\x00\x00\x18ftypM4A " + b"\x00" * 12

    def add(index_and_library):  # type: ignore[no-untyped-def]
        index, library = index_and_library
        start.wait(timeout=5)
        return library.add_local_audio(
            original_name=f"Quiet hymn {index}.m4a",
            content=m4a,
            context="devotional",
        )

    with ThreadPoolExecutor(max_workers=len(libraries)) as executor:
        tracks = list(executor.map(add, enumerate(libraries)))

    catalog_tracks = [track for track in MusicLibrary(root).all_custom_tracks() if track.custom]
    assert {track.id for track in catalog_tracks} == {track.id for track in tracks}
    assert len(list((root / "custom").glob("*.m4a"))) == len(libraries)
    assert not [path for path in root.iterdir() if path.name.endswith(".tmp")]


def test_music_ui_has_operator_controlled_autoplay_on_every_workspace_page() -> None:
    music_ui = (PROJECT_ROOT / "nicegui_app" / "ui" / "music.py").read_text(encoding="utf-8")
    controller = (
        PROJECT_ROOT / "nicegui_app" / "assets" / "music" / "sing-yin-music-controller.js"
    ).read_text(encoding="utf-8")
    sound_ui = (PROJECT_ROOT / "nicegui_app" / "ui" / "sound.py").read_text(encoding="utf-8")
    pages = combined_page_source()
    page_catalog = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_catalog.py").read_text(
        encoding="utf-8"
    )
    main = (PROJECT_ROOT / "nicegui_app" / "main.py").read_text(encoding="utf-8")

    assert "autoplay=False" in music_ui, "The audio element starts conservatively before the saved preference is applied"
    assert 'DEFAULT_MUSIC_AUTOPLAY = True' in sound_ui
    assert 'DEFAULT_MUSIC_VOLUME = 0.50' in sound_ui
    assert 'LEGACY_DEFAULT_MUSIC_VOLUMES = (0.24, 0.35)' in sound_ui
    assert "element.volume >= 0.48 && element.volume <= 0.52" in (
        PROJECT_ROOT / "scripts" / "verify_nicegui_ui.py"
    ).read_text(encoding="utf-8")
    assert 'MUSIC_AUTOPLAY_STORAGE_KEY = "music_autoplay"' in sound_ui
    assert 'app.storage.user.get("music_autoplay"' not in music_ui
    assert music_ui.count("music_autoplay_enabled()") >= 3
    assert music_ui.count("set_music_autoplay(enabled)") == 2
    assert 'data-testid=music-autoplay-switch' in music_ui
    assert 'data-testid=music-playback-status' in music_ui
    assert 'data-music-state=' in music_ui
    assert 'data-testid=music-play-retry' in music_ui
    assert 'data-testid=music-pause-now' in music_ui
    assert "js_handler=_music_retry_handler_script" in music_ui
    assert "window.SingYinMusicController" in music_ui
    assert "audio.play().then" not in music_ui
    assert "audio.pause()" in music_ui
    assert "playResult = audio.play()" in controller
    assert "name === 'NotAllowedError'" in controller
    assert "name === 'NotSupportedError'" in controller
    assert "audio?.error?.code === 2" in controller
    assert "audio?.error?.code === 3 || audio?.error?.code === 4" in controller
    assert "navigator.onLine === false" in controller
    assert "const boundAudio = new WeakSet()" in controller
    assert "setTimeout" not in controller
    assert "ui.timer(" not in music_ui
    assert "window.__syMusicDeferredScripts" in music_ui
    assert "window.__syMusicRenderToken" in music_ui
    assert "window.location.pathname !== pathname" in music_ui
    assert "if not continue_playback:" in music_ui
    assert '_cancel_deferred_music_script(' in music_ui
    assert 'key="track-resume"' in music_ui
    assert 'key="continuity"' in music_ui
    assert 'key="autoplay"' in music_ui
    assert 'key="dialog-focus"' in music_ui
    assert "loop=False" in music_ui
    assert 'audio.on("ended", advance_playlist)' in music_ui
    assert '"sequential": t("music_mode_sequential")' in music_ui
    assert '"shuffle": t("music_mode_shuffle")' in music_ui
    for context in ("devotional", "handover", "weekly", "people", "settings"):
        assert f'music_context="{context}"' in page_catalog
    assert "music_context=" not in pages
    assert 'url_path="/assets/music"' in main
    assert "YoutubeMusicLink" not in music_ui
    assert "add_youtube_link" not in music_ui


def test_deferred_music_work_is_bound_to_one_render_and_can_be_cancelled() -> None:
    render_token = "music-render-a"
    scope = music_ui_module._music_render_scope_script(render_token)
    deferred = music_ui_module._deferred_music_script(
        "window.__musicProbe = true;",
        delay_ms=160,
        key="track-resume",
        render_token=render_token,
    )
    cancelled = music_ui_module._cancel_deferred_music_script(
        key="track-resume",
        render_token=render_token,
    )

    assert 'window.__syMusicRenderToken = "music-render-a"' in scope
    assert "window.__syMusicDeferredScripts = Object.create(null)" in scope
    assert deferred.count("window.__syMusicRenderToken !== renderToken") == 2
    assert "window.location.pathname !== pathname" in deferred
    assert "window.setTimeout" in deferred
    assert "}, 160);" in deferred
    assert 'delete registry["track-resume"]' in cancelled


def test_same_track_continues_across_page_navigation_without_permanent_storage() -> None:
    music_ui = (PROJECT_ROOT / "nicegui_app" / "ui" / "music.py").read_text(encoding="utf-8")

    assert "sing-yin:music-continuity:v1" in music_ui
    assert "sessionStorage.setItem(storageKey" in music_ui
    assert "previous.source === normalizedSource()" in music_ui
    assert "audio.currentTime = safePosition" in music_ui
    assert "audio.dataset.syContinuityPlaying === 'false'" in music_ui
    assert "localStorage" not in music_ui
