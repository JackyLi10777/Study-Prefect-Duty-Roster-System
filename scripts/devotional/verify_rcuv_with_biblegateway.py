"""Verify local RCUV scripture strings against Bible Gateway RCU17TS pages.

The script stores verification statuses and hashes. It can optionally sync the
local Traditional Chinese scripture field from the fetched passage text.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "data" / "devotional" / "daily-verses.seed.json"
REPORT_PATH = ROOT / "data" / "devotional" / "translation-verification-rcuv-biblegateway.json"
BIBLEGATEWAY_URL = "https://www.biblegateway.com/passage/"

SPAN_RE = re.compile(r"<span[^>]+class=\"[^\"]*\btext\b[^\"]*\"[^>]*>(.*?)</span>", re.DOTALL)
HEADING_RE = re.compile(r"<h[1-6]\b[^>]*>.*?</h[1-6]>", re.DOTALL | re.IGNORECASE)
CHAPTER_RE = re.compile(
    r"<span[^>]*class=(?:\"[^\"]*\bchapternum\b[^\"]*\"|'[^']*\bchapternum\b[^']*')[^>]*>.*?</span>",
    re.DOTALL | re.IGNORECASE,
)
SUP_RE = re.compile(
    r"<sup[^>]*class=(?:\"[^\"]*\bversenum\b[^\"]*\"|'[^']*\bversenum\b[^']*')[^>]*>.*?</sup>",
    re.DOTALL | re.IGNORECASE,
)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[\s，。；：！？、,.!?;:\"'“”‘’「」『』（）()\[\]{}—–\\-]+")


def load_seed() -> dict[str, Any]:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def clean_html(text: str) -> str:
    text = SUP_RE.sub("", text)
    text = TAG_RE.sub("", text)
    return html.unescape(text)


def normalize_basic(text: str) -> str:
    text = clean_html(text)
    text = text.replace("\u00a0", " ")
    return SPACE_RE.sub(" ", text).strip()


def normalize_loose(text: str) -> str:
    return PUNCT_RE.sub("", normalize_basic(text)).casefold()


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_passage(reference: str) -> str:
    query = urllib.parse.urlencode({"search": reference, "version": "RCU17TS"})
    req = urllib.request.Request(
        f"{BIBLEGATEWAY_URL}?{query}",
        headers={
            "User-Agent": "Mozilla/5.0 devotional-verifier/1.0",
            "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read().decode("utf-8", "replace")


def extract_passage_text(page_html: str) -> str:
    # Prefer passage spans over meta descriptions so verse numbers and unrelated
    # navigation text do not enter the comparison.
    start = page_html.find('<div class="passage-text">')
    if start == -1:
        start = page_html.find("<div class='passage-content")
    end = page_html.find('<a class="full-chap-link"', start)
    if start != -1 and end != -1:
        page_html = page_html[start:end]
    elif start != -1:
        page_html = page_html[start:]

    # Bible Gateway renders section headings with the same ``text`` class used
    # by verses.  At the start of a chapter it also nests a chapter-number span
    # inside verse 1.  Remove both before matching passage spans; otherwise the
    # heading and chapter number replace the actual first verse in local data.
    page_html = HEADING_RE.sub("", page_html)
    page_html = CHAPTER_RE.sub("", page_html)
    spans = SPAN_RE.findall(page_html)
    cleaned = [normalize_basic(span) for span in spans]
    cleaned = [item for item in cleaned if item]
    return normalize_basic(" ".join(cleaned))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply-source-text",
        action="store_true",
        help="Replace local scripture.zh with normalized Bible Gateway RCU17TS passage text.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.15,
        help="Delay between unique Bible Gateway passage requests.",
    )
    args = parser.parse_args()

    seed = load_seed()
    entries = seed["entries"]
    cache: dict[str, str] = {}
    report_entries: list[dict[str, Any]] = []

    for entry in entries:
        reference = entry["source"]["reference"]["en"]
        if reference not in cache:
            page = fetch_passage(reference)
            cache[reference] = extract_passage_text(page)
            time.sleep(args.delay_seconds)

        source_basic = cache[reference]
        local_basic = normalize_basic(entry["scripture"]["zh"])

        if not source_basic:
            status = "source-unavailable"
        else:
            if args.apply_source_text:
                entry["scripture"]["zh"] = source_basic
                local_basic = normalize_basic(entry["scripture"]["zh"])
            if local_basic == source_basic:
                status = "verified-exact"
            elif normalize_loose(local_basic) == normalize_loose(source_basic):
                status = "verified-minor-punctuation-difference"
            else:
                status = "needs-correction"

        checked_at = datetime.now(timezone.utc).isoformat()
        item = {
            "id": entry["id"],
            "reference": entry["source"]["reference"]["zh"],
            "status": status,
            "localNormalizedHash": sha256(local_basic),
            "sourceNormalizedHash": sha256(source_basic) if source_basic else None,
            "localNormalizedLength": len(local_basic),
            "sourceNormalizedLength": len(source_basic) if source_basic else None,
            "source": "Bible Gateway RCU17TS",
            "sourceUrl": "https://www.biblegateway.com/",
            "checkedAt": checked_at,
        }
        report_entries.append(item)

        verification = entry.setdefault("translationVerification", {})
        verification["zh"] = {
            "status": status,
            "expectedTranslation": "RCUV 2010",
            "source": "Bible Gateway RCU17TS",
            "sourceUrl": "https://www.biblegateway.com/",
            "checkedAt": checked_at,
            "localNormalizedHash": item["localNormalizedHash"],
            "sourceNormalizedHash": item["sourceNormalizedHash"],
            "notes": (
                "Verified against Bible Gateway RCU17TS after normalizing whitespace."
                if status == "verified-exact"
                else "Content matches after punctuation/quotation normalization; review punctuation if exact display fidelity is required."
                if status == "verified-minor-punctuation-difference"
                else "Local text does not match Bible Gateway RCU17TS normalized content; review required."
                if status == "needs-correction"
                else "Requested source passage was unavailable from Bible Gateway."
            ),
        }

    counts: dict[str, int] = defaultdict(int)
    for item in report_entries:
        counts[item["status"]] += 1

    report = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "name": "Bible Gateway",
            "translation": "RCU17TS",
            "url": "https://www.biblegateway.com/",
            "apiDocumentation": "https://www.biblegateway.com/api/documentation",
        },
        "summary": {
            "checkedEntryCount": len(report_entries),
            "uniquePassageRequestCount": len(cache),
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
