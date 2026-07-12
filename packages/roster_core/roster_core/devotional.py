from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SEED_PATH = PROJECT_ROOT / "data" / "devotional" / "daily-verses.seed.json"
EPOCH = date(1970, 1, 1)


@dataclass(frozen=True)
class DevotionalEntry:
    id: str
    reference_zh: str
    reference_en: str
    scripture_zh: str
    scripture_en: str
    reflection_zh: dict[str, str]
    reflection_en: dict[str, str]
    themes: tuple[str, ...]
    special_use: tuple[str, ...]
    is_foundational: bool

    @classmethod
    def from_seed(cls, raw: dict[str, Any]) -> "DevotionalEntry":
        return cls(
            id=raw["id"],
            reference_zh=raw["source"]["reference"]["zh"],
            reference_en=raw["source"]["reference"]["en"],
            scripture_zh=raw["scripture"]["zh"],
            scripture_en=raw["scripture"]["en"],
            reflection_zh=dict(raw["reflection"]["zh"]),
            reflection_en=dict(raw["reflection"]["en"]),
            themes=tuple(raw.get("themes", [])),
            special_use=tuple(raw.get("specialUse", [])),
            is_foundational=bool(raw.get("isFoundational", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "referenceZh": self.reference_zh,
            "referenceEn": self.reference_en,
            "scriptureZh": self.scripture_zh,
            "scriptureEn": self.scripture_en,
            "reflectionZh": self.reflection_zh,
            "reflectionEn": self.reflection_en,
            "themes": list(self.themes),
            "specialUse": list(self.special_use),
            "isFoundational": self.is_foundational,
        }


def load_devotional_seed(seed_path: Path = DEFAULT_SEED_PATH) -> list[DevotionalEntry]:
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    entries = [
        DevotionalEntry.from_seed(entry)
        for entry in data["entries"]
        if entry.get("quality", {}).get("status") == "polished"
    ]
    if not entries:
        raise ValueError("No polished devotional entries found.")
    return entries


def get_foundational_verse(seed_path: Path = DEFAULT_SEED_PATH) -> DevotionalEntry:
    for entry in load_devotional_seed(seed_path):
        if entry.is_foundational or entry.id == "dv-0001":
            return entry
    raise ValueError("Foundational devotional entry is missing.")


def select_daily_verse(
    target_date: date | None = None,
    *,
    special_use: str | None = None,
    seed_path: Path = DEFAULT_SEED_PATH,
) -> DevotionalEntry:
    target = target_date or date.today()
    entries = load_devotional_seed(seed_path)
    if special_use:
        filtered = [entry for entry in entries if special_use in entry.special_use]
        if filtered:
            entries = filtered
    index = (target - EPOCH).days % len(entries)
    return entries[index]

