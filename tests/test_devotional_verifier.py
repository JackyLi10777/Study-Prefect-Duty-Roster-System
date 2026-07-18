from __future__ import annotations

import json
from pathlib import Path

from scripts.devotional.build_translation_checklist import checklist_rows
from scripts.devotional.verify_rcuv_with_biblegateway import extract_passage_text


def test_biblegateway_extractor_excludes_heading_and_chapter_number_but_keeps_verse_one() -> None:
    page_html = """
    <div class="passage-text">
      <div class="passage-content">
        <h3><span class="text 1Tim-3-1">監督的資格</span></h3>
        <p><span class="text 1Tim-3-1"><span class="chapternum">3&nbsp;</span>「若有人想望監督的職分，他是在羨慕一件好事」，這話是可信的。</span>
        <span class="text 1Tim-3-2"><sup class="versenum">2&nbsp;</sup>監督必須無可指責。</span></p>
      </div>
      <a class="full-chap-link">Read full chapter</a>
    </div>
    """

    assert extract_passage_text(page_html) == (
        "「若有人想望監督的職分，他是在羨慕一件好事」，這話是可信的。 監督必須無可指責。"
    )


def test_translation_checklist_is_derived_from_corrected_canonical_scripture() -> None:
    root = Path(__file__).resolve().parents[1]
    seed = json.loads((root / "data" / "devotional" / "daily-verses.seed.json").read_text(encoding="utf-8"))
    row = next(item for item in checklist_rows(seed) if item["id"] == "dv-0038")

    assert row["scriptureZh"].startswith("「若有人想望監督的職分")
    assert row["verificationZh"] == "verified-exact"
