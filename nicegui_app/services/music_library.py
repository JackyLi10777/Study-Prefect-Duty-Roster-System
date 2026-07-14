"""Local, non-sensitive music catalogue and operator-managed playlist links."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath
import random
import re
import shutil
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from nicegui_app.config import MUSIC_DIR
from nicegui_app.services.json_catalog import locked_json_catalog, write_json_atomically


MUSIC_CONTEXTS = (
    "dashboard",
    "devotional",
    "getting_started",
    "guide",
    "architecture",
    "handover",
)
PLAYBACK_MODES = ("sequential", "shuffle")
MUSIC_PROFILES = ("bright", "quiet")
MUSIC_PROFILE_PREFERENCES = ("auto", *MUSIC_PROFILES)
ALLOWED_AUDIO_EXTENSIONS = {".m4a", ".mp3", ".ogg", ".wav"}
MAX_AUDIO_BYTES = 25 * 1024 * 1024


class MusicLibraryError(ValueError):
    """A safe, code-addressable music-library validation failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class MusicTrack:
    id: str
    filename: str
    title: str
    artist: str
    duration: str
    contexts: tuple[str, ...]
    profiles: tuple[str, ...] = MUSIC_PROFILES
    arrangement: str = "instrumental"
    custom: bool = False

    @property
    def asset_url(self) -> str:
        encoded = "/".join(quote(part, safe="") for part in PurePosixPath(self.filename).parts)
        return f"/assets/music/{encoded}"

    @property
    def display_label(self) -> str:
        return f"{self.title} — {self.artist} · {self.duration}" if self.duration else f"{self.title} — {self.artist}"


BUILTIN_TRACKS = (
    # Bright focus: gentle forward movement for starting and understanding work.
    MusicTrack("ambre", "Nils Frahm - Ambre.m4a", "Ambre", "Nils Frahm", "3:47", ("dashboard", "guide"), ("bright", "quiet")),
    MusicTrack("near-light", "Ólafur Arnalds - Near Light.m4a", "Near Light", "Ólafur Arnalds", "3:28", ("dashboard", "guide"), ("bright", "quiet")),
    MusicTrack("glass", "Hania Rani - Glass.m4a", "Glass", "Hania Rani", "4:30", ("dashboard", "architecture"), ("bright", "quiet")),
    MusicTrack("we-move-lightly", "Dustin O_Halloran - We Move Lightly.m4a", "We Move Lightly", "Dustin O'Halloran", "3:10", ("getting_started", "guide", "handover"), ("bright",)),
    MusicTrack("fairytale", "Ludovico Einaudi - Einaudi： Fairytale.m4a", "Fairytale", "Ludovico Einaudi", "", ("dashboard", "guide"), ("bright",)),
    MusicTrack("earth-prelude", "Ludovico Einaudi - The Earth Prelude.m4a", "The Earth Prelude", "Ludovico Einaudi", "", ("dashboard", "architecture"), ("bright",)),
    MusicTrack("canon-piano", "Music Lab Collective - Canon in D Major (Arr. for Piano).m4a", "Canon in D Major", "Music Lab Collective", "", ("dashboard", "getting_started"), ("bright",)),
    MusicTrack("morning-has-broken", "Relaxing Piano - Topic - Morning ⧸ Morning Has Broken.m4a", "Morning Has Broken", "Relaxing Piano", "", ("dashboard", "getting_started"), ("bright",)),
    MusicTrack("bach-prelude-fugue-1", "Sviatoslav Richter - Topic - Prelude and Fugue： No. 1 in C Major, BWV 846.m4a", "Prelude and Fugue No. 1", "Sviatoslav Richter", "", ("guide", "architecture"), ("bright",)),
    MusicTrack("be-thou-my-vision", "bHp Music - Be Thou My Vision ｜ Piano Instrumental with Lyrics.m4a", "Be Thou My Vision", "bHp Music", "3:17", ("getting_started", "architecture"), ("bright",)),
    MusicTrack("servant-king", "Maranatha! Music - Topic - The Servant King (Instrumental).m4a", "The Servant King", "Maranatha! Music", "4:12", ("architecture", "handover"), ("bright", "quiet")),
    MusicTrack("bless-the-lord", "Taizé - Topic - Bless the Lord (Accompaniment).m4a", "Bless the Lord", "Taizé", "4:48", ("devotional", "getting_started"), ("bright",), "instrumental"),
    MusicTrack("bless-the-lord-vocal", "Taizé - Topic - Bless The Lord.m4a", "Bless the Lord", "Taizé", "", ("devotional", "getting_started"), ("bright",), "vocal"),
    MusicTrack("laudate-omnes-gentes", "Taizé - Topic - Laudate omnes gentes (Accompaniment).m4a", "Laudate omnes gentes", "Taizé", "3:34", ("devotional", "getting_started"), ("bright",), "instrumental"),
    MusicTrack("laudate-omnes-gentes-vocal", "Taizé - Topic - Laudate omnes gentes (Sung Quickly).m4a", "Laudate omnes gentes", "Taizé", "", ("devotional", "getting_started"), ("bright",), "vocal"),
    MusicTrack("jubilate-deo", "The Cambridge Singers - Topic - Jubilate Deo.m4a", "Jubilate Deo", "The Cambridge Singers", "", ("devotional", "getting_started"), ("bright",), "vocal"),
    # Quiet reflection: slower, prayerful and reassuring material for reading and handover.
    MusicTrack("good-night-day", "Hildur Guðnadóttir - Jóhannsson： Good Night, Day.m4a", "Good Night, Day", "Hildur Guðnadóttir & Jóhann Jóhannsson", "", ("dashboard", "handover"), ("quiet",)),
    MusicTrack("fur-alina", "Jürgen Kruse - Topic - Für Alina, for Piano Solo.m4a", "Für Alina", "Jürgen Kruse", "", ("devotional", "guide"), ("quiet",)),
    MusicTrack("le-onde", "Ludovico Einaudi - Einaudi： Le Onde.m4a", "Le Onde", "Ludovico Einaudi", "", ("dashboard", "handover"), ("quiet",)),
    MusicTrack("hands-be-still", "Ólafur Arnalds - Hands, Be Still.m4a", "Hands, Be Still", "Ólafur Arnalds", "", ("devotional", "guide"), ("quiet",)),
    MusicTrack("only-the-winds", "Ólafur Arnalds - Only The Winds.m4a", "Only The Winds", "Ólafur Arnalds", "", ("handover", "architecture"), ("quiet",)),
    MusicTrack("spiegel-im-spiegel", "Benjamin Hudson - Topic - Spiegel im Spiegel, for Viola & Piano.m4a", "Spiegel im Spiegel", "Benjamin Hudson & Jürgen Kruse", "10:05", ("devotional", "architecture"), ("quiet",)),
    MusicTrack("serenity", "Serenity (O Magnum Mysterium) — Tenebrae.m4a", "Serenity (O Magnum Mysterium)", "Tenebrae", "", ("devotional", "handover"), ("quiet",), "vocal"),
    MusicTrack("the-spheres", "Tenebrae - Topic - Gjeilo： The Spheres.m4a", "The Spheres", "Tenebrae", "", ("devotional", "architecture"), ("quiet",), "vocal"),
    MusicTrack("ubi-caritas", "Taizé - Topic - Ubi caritas (Accompaniment).m4a", "Ubi caritas", "Taizé", "3:20", ("devotional", "handover"), ("quiet",), "instrumental"),
    MusicTrack("ubi-caritas-vocal", "Taizé - Topic - Ubi caritas.m4a", "Ubi caritas", "Taizé", "", ("devotional", "handover"), ("quiet",), "vocal"),
    MusicTrack("wait-for-the-lord", "Taizé - Topic - Wait for the Lord (Accompaniment).m4a", "Wait for the Lord", "Taizé", "5:00", ("devotional", "handover"), ("quiet",), "instrumental"),
    MusicTrack("wait-for-the-lord-vocal", "Taizé - Topic - Wait for The Lord.m4a", "Wait for the Lord", "Taizé", "", ("devotional", "handover"), ("quiet",), "vocal"),
    MusicTrack("in-manus-tuas", "Taizé - Topic - In manus tuas pater (Accompaniment).m4a", "In manus tuas, Pater", "Taizé", "", ("devotional", "handover"), ("quiet",), "instrumental"),
    MusicTrack("in-manus-tuas-vocal", "Taizé - Topic - In manus tuas, Pater.m4a", "In manus tuas, Pater", "Taizé", "", ("devotional", "handover"), ("quiet",), "vocal"),
    MusicTrack("it-is-well", "bHp Music - It Is Well with My Soul ｜ Piano Instrumental with Lyrics.m4a", "It Is Well with My Soul", "bHp Music", "4:34", ("devotional", "handover"), ("quiet",)),
    MusicTrack("abide-with-me", "Kaleb Brasee - Abide with Me - piano instrumental hymn with lyrics.m4a", "Abide with Me", "Kaleb Brasee", "4:21", ("devotional", "handover"), ("quiet",)),
)


class MusicLibrary:
    """Own optional local audio outside roster persistence."""

    def __init__(self, root: Path = MUSIC_DIR) -> None:
        self.root = Path(root)
        self.custom_dir = self.root / "custom"
        self.state_path = self.root / "custom-library.json"

    def tracks_for_context(self, context: str, *, profile: str | None = None) -> list[MusicTrack]:
        self._require_context(context)
        if profile is not None and profile not in MUSIC_PROFILES:
            raise MusicLibraryError("profile")
        tracks = [
            track
            for track in BUILTIN_TRACKS
            if context in track.contexts
            and (profile is None or profile in track.profiles)
            and (self.root / track.filename).is_file()
        ]
        for item in self._state()["localTracks"]:
            if item.get("context") != context:
                continue
            relative_name = str(item.get("filename", ""))
            if not self._safe_relative_file(relative_name).is_file():
                continue
            tracks.append(
                MusicTrack(
                    id=str(item["id"]),
                    filename=relative_name,
                    title=str(item["title"]),
                    artist=str(item.get("artist") or "Local library"),
                    duration=str(item.get("duration") or ""),
                    contexts=(context,),
                    arrangement=str(item.get("arrangement") or "local"),
                    custom=True,
                )
            )
        return tracks

    def all_custom_tracks(self) -> list[MusicTrack]:
        tracks: list[MusicTrack] = []
        for context in MUSIC_CONTEXTS:
            tracks.extend(track for track in self.tracks_for_context(context) if track.custom)
        return tracks

    def add_local_audio(self, *, original_name: str, content: bytes, context: str) -> MusicTrack:
        self._require_context(context)
        extension = Path(original_name).suffix.lower()
        if extension not in ALLOWED_AUDIO_EXTENSIONS:
            raise MusicLibraryError("format")
        if not content or len(content) > MAX_AUDIO_BYTES:
            raise MusicLibraryError("size")
        if not _matches_audio_signature(extension, content[:16]):
            raise MusicLibraryError("content")

        title = _clean_title(Path(original_name).stem)
        track_id = f"custom-{uuid4().hex}"
        relative_name = f"custom/{track_id}{extension}"
        target = self._safe_relative_file(relative_name)
        self.custom_dir.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(f"{target.suffix}.tmp")
        temporary.write_bytes(content)
        os.replace(temporary, target)

        try:
            with locked_json_catalog(self.state_path):
                state = self._state()
                state["localTracks"].append(
                    {
                        "id": track_id,
                        "filename": relative_name,
                        "title": title,
                        "artist": "Local library",
                        "duration": "",
                        "context": context,
                        "arrangement": "local",
                    }
                )
                self._write_state(state)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return MusicTrack(track_id, relative_name, title, "Local library", "", (context,), custom=True)

    def add_downloaded_audio(
        self,
        *,
        source_path: Path,
        context: str,
        title: str,
        artist: str,
        source_id: str,
    ) -> MusicTrack:
        """Move a validated downloader result into the dedicated local import area."""
        self._require_context(context)
        source = Path(source_path)
        extension = source.suffix.lower()
        if extension not in ALLOWED_AUDIO_EXTENSIONS:
            raise MusicLibraryError("format")
        try:
            size = source.stat().st_size
            with source.open("rb") as handle:
                header = handle.read(16)
        except OSError as error:
            raise MusicLibraryError("missing") from error
        if size <= 0 or size > MAX_AUDIO_BYTES:
            raise MusicLibraryError("size")
        if not _matches_audio_signature(extension, header):
            raise MusicLibraryError("content")

        track_id = f"youtube-{uuid4().hex}"
        relative_name = f"youtube-imports/{track_id}{extension}"
        target = self._safe_relative_file(relative_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(f"{target.suffix}.tmp")
        shutil.copyfile(source, temporary)
        os.replace(temporary, target)
        clean_title = _clean_title(title or source.stem)
        clean_artist = _clean_title(artist or "YouTube local import")
        try:
            with locked_json_catalog(self.state_path):
                state = self._state()
                if source_id and any(item.get("sourceId") == source_id for item in state["localTracks"]):
                    raise MusicLibraryError("duplicate")
                state["localTracks"].append(
                    {
                        "id": track_id,
                        "filename": relative_name,
                        "title": clean_title,
                        "artist": clean_artist,
                        "duration": "",
                        "context": context,
                        "arrangement": "youtube",
                        "source": "youtube",
                        "sourceId": source_id,
                    }
                )
                self._write_state(state)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return MusicTrack(
            track_id,
            relative_name,
            clean_title,
            clean_artist,
            "",
            (context,),
            arrangement="youtube",
            custom=True,
        )

    def remove_local_audio(self, track_id: str) -> None:
        with locked_json_catalog(self.state_path):
            state = self._state()
            item = next((entry for entry in state["localTracks"] if entry.get("id") == track_id), None)
            if item is None:
                raise MusicLibraryError("missing")
            state["localTracks"] = [entry for entry in state["localTracks"] if entry.get("id") != track_id]
            self._write_state(state)
        self._safe_relative_file(str(item["filename"])).unlink(missing_ok=True)

    def _safe_relative_file(self, relative_name: str) -> Path:
        candidate = (self.root / Path(relative_name)).resolve()
        root = self.root.resolve()
        if candidate != root and root not in candidate.parents:
            raise MusicLibraryError("path")
        return candidate

    def _state(self) -> dict[str, list[dict[str, Any]]]:
        with locked_json_catalog(self.state_path):
            if not self.state_path.exists():
                return {"localTracks": []}
            try:
                raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise MusicLibraryError("library") from error
            return {"localTracks": list(raw.get("localTracks", []))}

    def _write_state(self, state: dict[str, list[dict[str, Any]]]) -> None:
        with locked_json_catalog(self.state_path):
            write_json_atomically(self.state_path, {"version": 2, **state})

    @staticmethod
    def _require_context(context: str) -> None:
        if context not in MUSIC_CONTEXTS:
            raise MusicLibraryError("context")


def next_track_id(track_ids: list[str], current_id: str, mode: str, *, rng: random.Random | None = None) -> str:
    """Choose the next playlist entry without repeating immediately in shuffle mode."""
    if not track_ids:
        raise MusicLibraryError("empty")
    if mode not in PLAYBACK_MODES:
        raise MusicLibraryError("mode")
    if len(track_ids) == 1:
        return track_ids[0]
    if mode == "shuffle":
        choices = [track_id for track_id in track_ids if track_id != current_id]
        return (rng or random).choice(choices)
    try:
        current_index = track_ids.index(current_id)
    except ValueError:
        return track_ids[0]
    return track_ids[(current_index + 1) % len(track_ids)]


def resolve_music_profile(preference: str, theme: str) -> str:
    """Resolve an operator override or the appearance-based recommendation."""
    if preference == "auto":
        return "quiet" if theme == "dark" else "bright"
    return preference if preference in MUSIC_PROFILES else "bright"


def _clean_title(value: str) -> str:
    title = re.sub(r"[_-]+", " ", value)
    title = re.sub(r"\s+", " ", title).strip()
    return title[:120] or "Local track"


def _matches_audio_signature(extension: str, header: bytes) -> bool:
    if extension == ".m4a":
        return len(header) >= 8 and header[4:8] == b"ftyp"
    if extension == ".mp3":
        return header.startswith(b"ID3") or (len(header) >= 2 and header[0] == 0xFF and header[1] & 0xE0 == 0xE0)
    if extension == ".ogg":
        return header.startswith(b"OggS")
    if extension == ".wav":
        return len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WAVE"
    return False
