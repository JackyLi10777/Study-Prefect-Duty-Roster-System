"""Build a 500-entry polished devotional file from canonical seed records."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "data" / "devotional" / "daily-verses.seed.json"
LEGACY_PATH = ROOT / "data" / "devotional" / "daily-verses.legacy.json"
OUTPUT_PATH = ROOT / "data" / "devotional" / "daily-verses.expanded.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    seed = load_json(SEED_PATH)
    legacy = load_json(LEGACY_PATH)

    seed_by_legacy_id: dict[str, dict[str, Any]] = {}
    for entry in seed["entries"]:
        for legacy_id in entry["legacyIds"]:
            seed_by_legacy_id[legacy_id] = entry

    expanded_entries: list[dict[str, Any]] = []
    missing: list[str] = []

    for legacy_entry in legacy["entries"]:
        legacy_id = legacy_entry["legacyId"]
        seed_entry = seed_by_legacy_id.get(legacy_id)
        if seed_entry is None:
            missing.append(legacy_id)
            continue

        expanded_entries.append(
            {
                "legacyId": legacy_id,
                "canonicalId": seed_entry["id"],
                "duplicateGroup": legacy_entry["duplicateGroup"],
                "isCanonicalForGroup": legacy_entry["isCanonicalForGroup"],
                "legacySource": legacy_entry["source"],
                "source": seed_entry["source"],
                "scripture": seed_entry["scripture"],
                "reflection": seed_entry["reflection"],
                "themes": seed_entry["themes"],
                "audience": seed_entry["audience"],
                "specialUse": seed_entry.get("specialUse", []),
                "quality": seed_entry["quality"],
                "translationVerification": seed_entry.get("translationVerification", {}),
            }
        )

    if missing:
        raise SystemExit(f"Missing seed coverage for legacy IDs: {', '.join(missing)}")

    output = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceSeed": SEED_PATH.relative_to(ROOT).as_posix(),
        "sourceLegacy": LEGACY_PATH.relative_to(ROOT).as_posix(),
        "stats": {
            "expandedEntryCount": len(expanded_entries),
            "canonicalSeedEntryCount": len(seed["entries"]),
            "legacyEntryCount": len(legacy["entries"]),
        },
        "entries": expanded_entries,
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(expanded_entries)} expanded devotional entries to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
