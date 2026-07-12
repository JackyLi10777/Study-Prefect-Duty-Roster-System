"""Verify local NKJV scripture strings against Bolls Bible API.

The script does not store fetched NKJV text. It records comparison statuses,
hashes, and lengths so the project can audit accuracy without copying an
external Bible corpus into the repository.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
import argparse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "data" / "devotional" / "daily-verses.seed.json"
REPORT_PATH = ROOT / "data" / "devotional" / "translation-verification-nkjv-bolls.json"
BOLLS_GET_VERSES_URL = "https://bolls.life/get-verses/"

BOOK_IDS = {
    "Genesis": 1,
    "Exodus": 2,
    "Leviticus": 3,
    "Numbers": 4,
    "Deuteronomy": 5,
    "Joshua": 6,
    "Judges": 7,
    "Ruth": 8,
    "1 Samuel": 9,
    "2 Samuel": 10,
    "1 Kings": 11,
    "2 Kings": 12,
    "1 Chronicles": 13,
    "2 Chronicles": 14,
    "Ezra": 15,
    "Nehemiah": 16,
    "Esther": 17,
    "Job": 18,
    "Psalm": 19,
    "Psalms": 19,
    "Proverbs": 20,
    "Ecclesiastes": 21,
    "Song of Solomon": 22,
    "Isaiah": 23,
    "Jeremiah": 24,
    "Lamentations": 25,
    "Ezekiel": 26,
    "Daniel": 27,
    "Hosea": 28,
    "Joel": 29,
    "Amos": 30,
    "Obadiah": 31,
    "Jonah": 32,
    "Micah": 33,
    "Nahum": 34,
    "Habakkuk": 35,
    "Zephaniah": 36,
    "Haggai": 37,
    "Zechariah": 38,
    "Malachi": 39,
    "Matthew": 40,
    "Mark": 41,
    "Luke": 42,
    "John": 43,
    "Acts": 44,
    "Romans": 45,
    "1 Corinthians": 46,
    "2 Corinthians": 47,
    "Galatians": 48,
    "Ephesians": 49,
    "Philippians": 50,
    "Colossians": 51,
    "1 Thessalonians": 52,
    "2 Thessalonians": 53,
    "1 Timothy": 54,
    "2 Timothy": 55,
    "Titus": 56,
    "Philemon": 57,
    "Hebrews": 58,
    "James": 59,
    "1 Peter": 60,
    "2 Peter": 61,
    "1 John": 62,
    "2 John": 63,
    "3 John": 64,
    "Jude": 65,
    "Revelation": 66,
}


TAG_RE = re.compile(r"<[^>]+>")
NKJV_MARKER_RE = re.compile(r"\s*\(?NKJV\)?\s*$", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[\s.,;:!?\"'“”‘’()\[\]{}—–\\-]+")


def load_seed() -> dict[str, Any]:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def clean_html(text: str) -> str:
    return html.unescape(TAG_RE.sub("", text))


def normalize_basic(text: str) -> str:
    text = clean_html(text)
    text = NKJV_MARKER_RE.sub("", text)
    text = text.replace("\u00a0", " ")
    return SPACE_RE.sub(" ", text).strip()


def normalize_loose(text: str) -> str:
    text = normalize_basic(text)
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    return PUNCT_RE.sub("", text).casefold()


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_verses(verses: str) -> list[int]:
    parsed: list[int] = []
    for part in verses.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = [int(x.strip()) for x in part.split("-", 1)]
            parsed.extend(range(start, end + 1))
        else:
            parsed.append(int(part))
    return parsed


def fetch_bolls(groups: dict[tuple[int, int], set[int]]) -> dict[tuple[int, int, int], str]:
    body = [
        {
            "translation": "NKJV",
            "book": book_id,
            "chapter": chapter,
            "verses": sorted(verses),
        }
        for (book_id, chapter), verses in sorted(groups.items())
    ]
    req = urllib.request.Request(
        BOLLS_GET_VERSES_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        fetched = json.load(response)

    verse_text: dict[tuple[int, int, int], str] = {}
    for result_group in fetched:
        for verse in result_group:
            verse_text[(verse["book"], verse["chapter"], verse["verse"])] = verse["text"]
    return verse_text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply-source-text",
        action="store_true",
        help="Replace local scripture.en with normalized Bolls NKJV text plus the local (NKJV) marker.",
    )
    args = parser.parse_args()

    seed = load_seed()
    entries = seed["entries"]

    groups: dict[tuple[int, int], set[int]] = defaultdict(set)
    entry_refs: dict[str, tuple[int, int, list[int]]] = {}
    report_entries: list[dict[str, Any]] = []

    for entry in entries:
        source = entry["source"]
        book = source["book"]
        book_id = BOOK_IDS.get(book)
        if book_id is None:
            raise SystemExit(f"Unsupported book name for {entry['id']}: {book}")
        chapter = int(source["chapter"])
        verses = parse_verses(str(source["verses"]))
        entry_refs[entry["id"]] = (book_id, chapter, verses)
        groups[(book_id, chapter)].update(verses)

    fetched = fetch_bolls(groups)

    for entry in entries:
        book_id, chapter, verses = entry_refs[entry["id"]]
        missing = [verse for verse in verses if (book_id, chapter, verse) not in fetched]
        if missing:
            status = "source-unavailable"
            source_basic = ""
        else:
            source_basic = " ".join(normalize_basic(fetched[(book_id, chapter, verse)]) for verse in verses)
            source_basic = normalize_basic(source_basic)
            if args.apply_source_text:
                entry["scripture"]["en"] = f"{source_basic} (NKJV)"
            local_basic = normalize_basic(entry["scripture"]["en"])
            if local_basic == source_basic:
                status = "verified-exact"
            elif normalize_loose(local_basic) == normalize_loose(source_basic):
                status = "verified-minor-punctuation-difference"
            else:
                status = "needs-correction"

        local_basic = normalize_basic(entry["scripture"]["en"])
        item = {
            "id": entry["id"],
            "reference": entry["source"]["reference"]["en"],
            "status": status,
            "localNormalizedHash": sha256(local_basic),
            "sourceNormalizedHash": sha256(source_basic) if source_basic else None,
            "localNormalizedLength": len(local_basic),
            "sourceNormalizedLength": len(source_basic) if source_basic else None,
            "source": "Bolls Bible API NKJV",
            "sourceUrl": "https://bolls.life/",
            "checkedAt": datetime.now(timezone.utc).isoformat(),
        }
        report_entries.append(item)

        verification = entry.setdefault("translationVerification", {})
        verification["en"] = {
            "status": status,
            "expectedTranslation": "NKJV",
            "source": "Bolls Bible API NKJV",
            "sourceUrl": "https://bolls.life/",
            "checkedAt": item["checkedAt"],
            "localNormalizedHash": item["localNormalizedHash"],
            "sourceNormalizedHash": item["sourceNormalizedHash"],
            "notes": (
                "Verified against Bolls NKJV after removing local translation marker and normalizing whitespace."
                if status == "verified-exact"
                else "Content matches after punctuation/quotation normalization; review punctuation if exact display fidelity is required."
                if status == "verified-minor-punctuation-difference"
                else "Local text does not match Bolls NKJV normalized content; review required."
                if status == "needs-correction"
                else "Requested source verse was unavailable from Bolls."
            ),
        }

    counts: dict[str, int] = defaultdict(int)
    for item in report_entries:
        counts[item["status"]] += 1

    report = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "name": "Bolls Bible API",
            "translation": "NKJV",
            "url": "https://bolls.life/",
            "apiDocumentation": "https://github.com/Bolls-Bible/bain/blob/master/docs/API.md",
        },
        "summary": {
            "checkedEntryCount": len(report_entries),
            "statusCounts": dict(sorted(counts.items())),
        },
        "entries": report_entries,
    }

    SEED_PATH.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report written to {REPORT_PATH}")
    return 0 if not counts.get("needs-correction") and not counts.get("source-unavailable") else 1


if __name__ == "__main__":
    raise SystemExit(main())
