"""Local, non-sensitive music catalogue and operator-managed playlist links."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath
import random
import re
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from nicegui_app.config import MUSIC_DIR


MUSIC_CONTEXTS = (
    "dashboard",
    "devotional",
    "getting_started",
    "guide",
    "architecture",
    "handover",
)
PLAYBACK_MODES = ("sequential", "shuffle")
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
    custom: bool = False

    @property
    def asset_url(self) -> str:
        encoded = "/".join(quote(part, safe="") for part in PurePosixPath(self.filename).parts)
        return f"/assets/music/{encoded}"

    @property
    def display_label(self) -> str:
        return f"{self.title} — {self.artist} · {self.duration}" if self.duration else f"{self.title} — {self.artist}"


BUILTIN_TRACKS = (
    MusicTrack("ambre", "Nils Frahm - Ambre.m4a", "Ambre", "Nils Frahm", "3:47", ("dashboard", "guide")),
    MusicTrack("near-light", "Ólafur Arnalds - Near Light.m4a", "Near Light", "Ólafur Arnalds", "3:28", ("dashboard", "guide")),
    MusicTrack("glass", "Hania Rani - Glass.m4a", "Glass", "Hania Rani", "4:30", ("dashboard", "architecture")),
    MusicTrack("ubi-caritas", "Taizé - Topic - Ubi caritas (Accompaniment).m4a", "Ubi caritas", "Taizé", "3:20", ("devotional", "handover")),
    MusicTrack("bless-the-lord", "Taizé - Topic - Bless the Lord (Accompaniment).m4a", "Bless the Lord", "Taizé", "4:48", ("devotional", "getting_started")),
    MusicTrack("wait-for-the-lord", "Taizé - Topic - Wait for the Lord (Accompaniment).m4a", "Wait for the Lord", "Taizé", "5:00", ("devotional", "handover")),
    MusicTrack("laudate-omnes-gentes", "Taizé - Topic - Laudate omnes gentes (Accompaniment).m4a", "Laudate omnes gentes", "Taizé", "3:34", ("devotional", "getting_started")),
    MusicTrack("spiegel-im-spiegel", "Benjamin Hudson - Topic - Spiegel im Spiegel, for Viola & Piano.m4a", "Spiegel im Spiegel", "Benjamin Hudson & Jürgen Kruse", "10:05", ("devotional", "architecture")),
    MusicTrack("be-thou-my-vision", "bHp Music - Be Thou My Vision ｜ Piano Instrumental with Lyrics.m4a", "Be Thou My Vision", "bHp Music", "3:17", ("getting_started", "architecture")),
    MusicTrack("servant-king", "Maranatha! Music - Topic - The Servant King (Instrumental).m4a", "The Servant King", "Maranatha! Music", "4:12", ("architecture", "handover")),
    MusicTrack("it-is-well", "bHp Music - It Is Well with My Soul ｜ Piano Instrumental with Lyrics.m4a", "It Is Well with My Soul", "bHp Music", "4:34", ("devotional", "handover")),
    MusicTrack("abide-with-me", "Kaleb Brasee - Abide with Me - piano instrumental hymn with lyrics.m4a", "Abide with Me", "Kaleb Brasee", "4:21", ("devotional", "handover")),
    MusicTrack("we-move-lightly", "Dustin O_Halloran - We Move Lightly.m4a", "We Move Lightly", "Dustin O'Halloran", "3:10", ("getting_started", "guide", "handover")),
)


class MusicLibrary:
    """Own optional local audio outside roster persistence."""

    def __init__(self, root: Path = MUSIC_DIR) -> None:
        self.root = Path(root)
        self.custom_dir = self.root / "custom"
        self.state_path = self.root / "custom-library.json"

    def tracks_for_context(self, context: str) -> list[MusicTrack]:
        self._require_context(context)
        tracks = [track for track in BUILTIN_TRACKS if context in track.contexts and (self.root / track.filename).is_file()]
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

        state = self._state()
        state["localTracks"].append(
            {
                "id": track_id,
                "filename": relative_name,
                "title": title,
                "artist": "Local library",
                "duration": "",
                "context": context,
            }
        )
        try:
            self._write_state(state)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return MusicTrack(track_id, relative_name, title, "Local library", "", (context,), custom=True)

    def remove_local_audio(self, track_id: str) -> None:
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
        if not self.state_path.exists():
            return {"localTracks": []}
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise MusicLibraryError("library") from error
        return {"localTracks": list(raw.get("localTracks", []))}

    def _write_state(self, state: dict[str, list[dict[str, Any]]]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        payload = {"version": 2, **state}
        temporary = self.state_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, self.state_path)

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
