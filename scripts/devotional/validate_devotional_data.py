"""Validate the Sing Yin devotional seed and legacy data.

This script is intentionally local and dependency-free so future student
maintainers can run it before editing or publishing devotional data.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED = ROOT / "data" / "devotional" / "daily-verses.seed.json"
DEFAULT_LEGACY = ROOT / "data" / "devotional" / "daily-verses.legacy.json"
DEFAULT_EXPANDED = ROOT / "data" / "devotional" / "daily-verses.expanded.json"
DEFAULT_REPORT = ROOT / "data" / "devotional" / "validation-report.json"

CJK_RE = re.compile(r"[\u3400-\u9fff]")
CORRUPTED_PLACEHOLDER_RE = re.compile(r"\?{3,}")
ARABIC_SCRIPT_RE = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]")
LEADING_CHAPTER_ARTIFACT_RE = re.compile(r"^(?:(?:[^。！？]{1,48})\s+)?\d{1,3}(?:\s+|$)")
REQUIRED_REFLECTION_FIELDS = ("title", "body", "prayer")
VALID_ORIGINS = frozenset({"legacy", "curated"})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _report_path(path: Path) -> str:
    """Return a reproducible project-relative path for files in this checkout."""

    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def has_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text))


def has_placeholder_corruption(value: Any) -> bool:
    return bool(CORRUPTED_PLACEHOLDER_RE.search(json.dumps(value, ensure_ascii=False)))


def validate(seed_path: Path, legacy_path: Path, expanded_path: Path | None = DEFAULT_EXPANDED) -> dict[str, Any]:
    seed = load_json(seed_path)
    legacy = load_json(legacy_path)
    expanded = load_json(expanded_path) if expanded_path and expanded_path.exists() else None

    seed_entries: list[dict[str, Any]] = seed.get("entries", [])
    legacy_entries: list[dict[str, Any]] = legacy.get("entries", [])
    expanded_entries: list[dict[str, Any]] = expanded.get("entries", []) if expanded else []
    seed_by_id = {entry.get("id"): entry for entry in seed_entries}
    legacy_ids = {entry.get("legacyId") for entry in legacy_entries}

    issues: list[dict[str, str]] = []
    origin_counts: Counter[str] = Counter()

    def issue(level: str, code: str, location: str, message: str) -> None:
        issues.append(
            {
                "level": level,
                "code": code,
                "location": location,
                "message": message,
            }
        )

    if len(seed_by_id) != len(seed_entries):
        issue("error", "duplicate-seed-id", "entries", "Seed entry IDs are not unique.")

    covered_legacy_ids: set[str] = set()

    for entry in seed_entries:
        entry_id = str(entry.get("id"))
        source = entry.get("source", {})
        reflection = entry.get("reflection", {})
        quality = entry.get("quality", {})
        origin = str(entry.get("origin", "legacy"))
        origin_counts[origin] += 1
        legacy_for_entry = set(entry.get("legacyIds", []))

        if origin not in VALID_ORIGINS:
            issue(
                "error",
                "invalid-origin",
                entry_id,
                f"Seed entry origin must be one of: {', '.join(sorted(VALID_ORIGINS))}.",
            )
        elif origin == "legacy":
            covered_legacy_ids.update(legacy_for_entry)
            if not legacy_for_entry:
                issue("error", "missing-legacy-ids", entry_id, "Legacy seed entry has no legacy IDs.")

            missing_legacy = sorted(legacy_for_entry - legacy_ids)
            if missing_legacy:
                issue(
                    "error",
                    "unknown-legacy-id",
                    entry_id,
                    f"Seed entry refers to missing legacy IDs: {', '.join(missing_legacy)}.",
                )
        elif legacy_for_entry:
            issue(
                "error",
                "curated-has-legacy-ids",
                entry_id,
                "Curated seed entries must not claim historical legacy IDs.",
            )

        if has_placeholder_corruption(source.get("bookZh", "")):
            issue("error", "corrupted-book-zh", entry_id, "source.bookZh contains placeholder question marks.")

        for lang in ("zh", "en"):
            lang_reflection = reflection.get(lang, {})
            for field in REQUIRED_REFLECTION_FIELDS:
                if not str(lang_reflection.get(field, "")).strip():
                    issue("error", "missing-reflection-field", f"{entry_id}.reflection.{lang}.{field}", "Reflection field is blank.")

        english_reflection = " ".join(
            str(reflection.get("en", {}).get(field, "")) for field in REQUIRED_REFLECTION_FIELDS
        )
        if has_cjk(english_reflection):
            issue("error", "cjk-in-english-reflection", entry_id, "English reflection contains CJK characters.")

        if has_placeholder_corruption(reflection):
            issue("error", "placeholder-corruption", entry_id, "Reflection contains literal placeholder question marks.")

        scripture = entry.get("scripture", {})
        for lang in ("zh", "en"):
            if not str(scripture.get(lang, "")).strip():
                issue("error", "missing-scripture", f"{entry_id}.scripture.{lang}", "Scripture text is blank.")

        scripture_zh = str(scripture.get("zh", "")).strip()
        if ARABIC_SCRIPT_RE.search(scripture_zh):
            issue(
                "error",
                "arabic-script-in-chinese-scripture",
                f"{entry_id}.scripture.zh",
                "Chinese scripture contains Arabic-script characters.",
            )
        if LEADING_CHAPTER_ARTIFACT_RE.search(scripture_zh):
            issue(
                "error",
                "leading-chapter-artifact",
                f"{entry_id}.scripture.zh",
                "Chinese scripture begins with a scraped section heading or chapter number.",
            )

        if quality.get("status") != "polished":
            issue("warning", "not-polished", entry_id, "Entry is not yet marked polished.")

        translation = source.get("translation", {})
        if translation.get("en") != "NKJV":
            issue("error", "unexpected-en-translation", entry_id, "English translation metadata must be NKJV.")
        if translation.get("zh") != "RCUV 2010":
            issue("error", "unexpected-zh-translation", entry_id, "Chinese translation metadata must be RCUV 2010.")

        verification = entry.get("translationVerification", {})
        for lang in ("zh", "en"):
            lang_verification = verification.get(lang, {})
            status = lang_verification.get("status")
            if status != "verified-exact":
                issue(
                    "error",
                    "translation-not-verified-exact",
                    f"{entry_id}.translationVerification.{lang}",
                    "Release scripture must be verified-exact for the configured translation.",
                )

            if origin == "curated":
                for field in ("source", "sourceUrl", "checkedAt", "localNormalizedHash", "sourceNormalizedHash"):
                    if not str(lang_verification.get(field, "")).strip():
                        issue(
                            "error",
                            "curated-verification-incomplete",
                            f"{entry_id}.translationVerification.{lang}.{field}",
                            "Curated scripture requires complete source and hash evidence.",
                        )
                source_url = str(lang_verification.get("sourceUrl", ""))
                if source_url and not source_url.startswith("https://"):
                    issue(
                        "error",
                        "curated-verification-source-insecure",
                        f"{entry_id}.translationVerification.{lang}.sourceUrl",
                        "Curated verification source URLs must use HTTPS.",
                    )
                local_hash = str(lang_verification.get("localNormalizedHash", ""))
                source_hash = str(lang_verification.get("sourceNormalizedHash", ""))
                if local_hash and not SHA256_RE.fullmatch(local_hash):
                    issue(
                        "error",
                        "curated-verification-hash-invalid",
                        f"{entry_id}.translationVerification.{lang}.localNormalizedHash",
                        "Curated verification hashes must be lowercase SHA-256 values.",
                    )
                if source_hash and not SHA256_RE.fullmatch(source_hash):
                    issue(
                        "error",
                        "curated-verification-hash-invalid",
                        f"{entry_id}.translationVerification.{lang}.sourceNormalizedHash",
                        "Curated verification hashes must be lowercase SHA-256 values.",
                    )
                if local_hash and source_hash and local_hash != source_hash:
                    issue(
                        "error",
                        "curated-verification-hash-mismatch",
                        f"{entry_id}.translationVerification.{lang}",
                        "Curated local and source normalized hashes must match.",
                    )

        if origin == "curated" and not str(quality.get("theologicalReview", "")).strip():
            issue(
                "error",
                "curated-theological-review-missing",
                f"{entry_id}.quality.theologicalReview",
                "Curated scripture requires an explicit theological review record.",
            )

        scripture_en = str(entry.get("scripture", {}).get("en", ""))
        if "(NKJV)" not in scripture_en:
            issue("error", "missing-nkjv-marker", entry_id, "English scripture text must include the local NKJV marker.")

    uncovered_legacy = sorted(legacy_ids - covered_legacy_ids)
    if uncovered_legacy:
        issue(
            "error",
            "uncovered-legacy-entry",
            "legacy",
            f"{len(uncovered_legacy)} legacy entries are not covered by seed legacyIds.",
        )

    duplicate_groups = Counter(
        entry.get("quality", {}).get("duplicateGroup") for entry in seed_entries
    )
    repeated_groups = sorted(group for group, count in duplicate_groups.items() if group and count > 1)
    if repeated_groups:
        issue(
            "error",
            "duplicate-group-reused",
            "entries",
            f"Duplicate groups appear in more than one seed entry: {', '.join(repeated_groups)}.",
        )

    if expanded is not None:
        if len(expanded_entries) != len(legacy_entries):
            issue(
                "error",
                "expanded-count-mismatch",
                "expanded",
                "Expanded devotional entry count does not match legacy entry count.",
            )

        expanded_legacy_ids = {entry.get("legacyId") for entry in expanded_entries}
        if expanded_legacy_ids != legacy_ids:
            issue(
                "error",
                "expanded-legacy-coverage-mismatch",
                "expanded",
                "Expanded devotional legacy IDs do not exactly match legacy source IDs.",
            )

        for entry in expanded_entries:
            entry_id = str(entry.get("legacyId"))
            canonical_id = entry.get("canonicalId")
            if canonical_id not in seed_by_id:
                issue("error", "expanded-unknown-canonical-id", entry_id, "Expanded entry points to unknown canonical ID.")
            if entry.get("quality", {}).get("status") != "polished":
                issue("error", "expanded-not-polished", entry_id, "Expanded entry is not polished.")
            reflection = entry.get("reflection", {})
            for lang in ("zh", "en"):
                for field in REQUIRED_REFLECTION_FIELDS:
                    if not str(reflection.get(lang, {}).get(field, "")).strip():
                        issue(
                            "error",
                            "expanded-missing-reflection-field",
                            f"{entry_id}.reflection.{lang}.{field}",
                            "Expanded reflection field is blank.",
                        )
            english_reflection = " ".join(
                str(reflection.get("en", {}).get(field, "")) for field in REQUIRED_REFLECTION_FIELDS
            )
            if has_cjk(english_reflection):
                issue("error", "expanded-cjk-in-english-reflection", entry_id, "Expanded English reflection contains CJK characters.")

    status_counts = Counter(entry.get("quality", {}).get("status") for entry in seed_entries)
    theme_counts = Counter(theme for entry in seed_entries for theme in entry.get("themes", []))
    translation_verification_counts = Counter()
    for entry in seed_entries:
        verification = entry.get("translationVerification", {})
        translation_verification_counts[f"zh:{verification.get('zh', {}).get('status')}"] += 1
        translation_verification_counts[f"en:{verification.get('en', {}).get('status')}"] += 1
    level_counts = Counter(item["level"] for item in issues)

    return {
        "schemaVersion": 1,
        "seedPath": _report_path(seed_path),
        "legacyPath": _report_path(legacy_path),
        "summary": {
            "seedEntryCount": len(seed_entries),
            "legacyEntryCount": len(legacy_entries),
            "coveredLegacyEntryCount": len(covered_legacy_ids),
            "expandedEntryCount": len(expanded_entries) if expanded is not None else None,
            "originCounts": dict(origin_counts),
            "statusCounts": dict(status_counts),
            "themeCounts": dict(theme_counts),
            "translationVerificationCounts": dict(translation_verification_counts),
            "issueCounts": dict(level_counts),
        },
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--legacy", type=Path, default=DEFAULT_LEGACY)
    parser.add_argument("--expanded", type=Path, default=DEFAULT_EXPANDED)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--fail-on-warning", action="store_true")
    args = parser.parse_args()

    report = validate(args.seed, args.legacy, args.expanded)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = report["summary"]
    issue_counts = summary["issueCounts"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Report written to {args.report}")

    if issue_counts.get("error", 0):
        return 1
    if args.fail_on_warning and issue_counts.get("warning", 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
