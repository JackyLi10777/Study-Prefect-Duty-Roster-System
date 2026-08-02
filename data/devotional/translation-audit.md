# Daily Verse Translation Audit

## Current Verification Status

Status: **completed for the current canonical corpus**.

The devotional scripture strings have now been checked and synchronized against external source pages/APIs for the two project translations:

- Traditional Chinese: Bible Gateway `RCU17TS` page text, corresponding to Revised Chinese Union Version Traditional Script Shen Edition.
- English: Bolls Bible API `NKJV`.

The project stores verification statuses and hashes in `daily-verses.seed.json` and source-specific verification reports. The reports intentionally avoid storing a second fetched Bible corpus.

## Verified Locally

The local validator `scripts/devotional/validate_devotional_data.py` currently verifies:

- 122 canonical seed entries exist: 121 legacy-derived records and one reviewed curated record.
- 500 legacy entries exist.
- All 500 legacy entries are covered by seed `legacyIds`.
- The generated expanded export contains 500 entries.
- All canonical seed entries are marked `polished`.
- Every reflection has Traditional Chinese and English `title`, `body`, and `prayer` fields.
- English reflections contain no CJK characters.
- `source.bookZh` metadata is repaired from the Traditional Chinese reference.
- Translation metadata is present as:
  - Chinese: `RCUV 2010`
  - English: `NKJV`
- Translation verification status is:
  - `zh:verified-exact = 122`
  - `en:verified-exact = 122`
- No validation issues remain.

Latest generated report:

```text
data/devotional/validation-report.json
```

## Source Verification Reports

- `translation-verification-rcuv-biblegateway.json`
  - Source: Bible Gateway `RCU17TS`
  - Checked canonical entries: 122
  - Result: 122 `verified-exact`
- `translation-verification-nkjv-bolls.json`
  - Source: Bolls Bible API `NKJV`
  - Checked canonical entries: 122
  - Result: 122 `verified-exact`

## Applied Corrections

The original converted seed text was not exact against the selected external sources in several places.

### 2026-08-03 curated Acts 24:16 and footnote extraction repair

`dv-0122` adds Acts 24:16 as the first `origin: curated` entry. It has no fabricated legacy ID and therefore does not change the 500-record historical expansion. Its RCUV 2010 and NKJV text, source URLs, normalized source/local hashes, bilingual reflection, classifications and theological-review marker are all required before the validator accepts the record.

A fresh 122-entry RCUV verification found that Bible Gateway now exposes some footnote markers through `<sup>` presentation markup. The extractor now removes all superscript presentation metadata—including verse numbers and footnote markers—before reading passage text. No local Scripture wording was silently broadened to absorb a source-page footnote. The complete RCUV and NKJV corpus then returned `122 verified-exact`.

### 2026-07-18 chapter-opening extraction repair

A mobile screenshot exposed a literal chapter number in `提摩太前書 3:1-7`.
It was not an Arabic-script letter: Bible Gateway's section heading and
chapter-number markup had been mistaken for verse text, which also removed
verse 1. A complete 121-entry recheck found the same extraction class in 14
canonical records. The corrected extractor now removes heading, chapter-number
and verse-number markup before reading passage spans. Those records were
resynchronized from `RCU17TS`, the full corpus then returned
`121 verified-exact`, and the local validator found no Arabic-script
characters in Traditional Chinese Scripture.

The affected references were:

- 雅各書 3:1、2:1、1:19-20
- 提摩太前書 3:1-7
- 箴言 15:1
- 羅馬書 13:8-10、15:1-2
- 馬太福音 18:15、5:13-14（兩個獨立 devotional records）
- 希伯來書 12:1-2
- 以弗所書 6:10
- 詩篇 27:1、1:1-3

English examples corrected during verification included:

- One wording mismatch in Titus 1:7-9.
- A truncated Hebrews 12:1-2 passage.
- Psalm 27:1 capitalization/superscription differences.
- Multiple punctuation and quotation differences.

Chinese verification found broader RCU17TS wording differences, so `scripture.zh` was synchronized from Bible Gateway RCU17TS across the canonical seed entries.

After synchronization, both language fields verify exactly under the project normalizer.

## Data Model Notes

`daily-verses.legacy.json` remains unchanged. It is the 500-record historical source trace, not the runtime devotional source. Existing canonical records default to `origin: legacy`; a reviewed future addition may use `origin: curated` only with no `legacyIds` and with complete bilingual source, hash and theological-review evidence.

Runtime and future editing should use:

- `daily-verses.seed.json` for canonical records.
- `daily-verses.expanded.json` when a literal 500-entry export is needed.
- `translation-checklist.csv` for human review or external audit. Regenerate
  it from the canonical seed with
  `python -X utf8 scripts/devotional/build_translation_checklist.py`.

## Verification Boundary

The current verification proves exact agreement with:

- Bible Gateway `RCU17TS` page text as fetched by `verify_rcuv_with_biblegateway.py`.
- Bolls Bible API `NKJV` text as fetched by `verify_nkjv_with_bolls.py`.

If the school later requires a different official source, such as a direct Hong Kong Bible Society export or a licensed API.Bible account, rerun verification against that source and update the `translationVerification` metadata accordingly.
