"""Regenerate the human-review scripture translation checklist from the seed."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "data" / "devotional" / "daily-verses.seed.json"
OUTPUT_PATH = ROOT / "data" / "devotional" / "translation-checklist.csv"
FIELDNAMES = (
    "id",
    "origin",
    "legacyIds",
    "referenceZh",
    "referenceEn",
    "translationZh",
    "translationEn",
    "scriptureZh",
    "scriptureEn",
    "verificationZh",
    "verificationEn",
    "verificationSourceZh",
    "verificationSourceEn",
)


def checklist_rows(seed: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for entry in seed["entries"]:
        source = entry["source"]
        verification = entry.get("translationVerification", {})
        zh_verification = verification.get("zh", {})
        en_verification = verification.get("en", {})
        rows.append(
            {
                "id": str(entry["id"]),
                "origin": str(entry.get("origin", "legacy")),
                "legacyIds": ";".join(entry.get("legacyIds", [])),
                "referenceZh": str(source["reference"]["zh"]),
                "referenceEn": str(source["reference"]["en"]),
                "translationZh": str(source["translation"]["zh"]),
                "translationEn": str(source["translation"]["en"]),
                "scriptureZh": str(entry["scripture"]["zh"]),
                "scriptureEn": str(entry["scripture"]["en"]),
                "verificationZh": str(zh_verification.get("status", "")),
                "verificationEn": str(en_verification.get("status", "")),
                "verificationSourceZh": str(zh_verification.get("source", "")),
                "verificationSourceEn": str(en_verification.get("source", "")),
            }
        )
    return rows


def main() -> int:
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(checklist_rows(seed))
    print(f"Wrote {len(seed['entries'])} checklist rows to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
