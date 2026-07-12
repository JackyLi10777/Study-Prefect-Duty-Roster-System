# Daily Verse Translation Audit

## Current Verification Status

Status: **completed for the current canonical corpus**.

The devotional scripture strings have now been checked and synchronized against external source pages/APIs for the two project translations:

- Traditional Chinese: Bible Gateway `RCU17TS` page text, corresponding to Revised Chinese Union Version Traditional Script Shen Edition.
- English: Bolls Bible API `NKJV`.

The project stores verification statuses and hashes in `daily-verses.seed.json` and source-specific verification reports. The reports intentionally avoid storing a second fetched Bible corpus.

## Verified Locally

The local validator `scripts/devotional/validate_devotional_data.py` currently verifies:

- 121 canonical seed entries exist.
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
  - `zh:verified-exact = 121`
  - `en:verified-exact = 121`
- No validation issues remain.

Latest generated report:

```text
data/devotional/validation-report.json
```

## Source Verification Reports

- `translation-verification-rcuv-biblegateway.json`
  - Source: Bible Gateway `RCU17TS`
  - Checked canonical entries: 121
  - Result: 121 `verified-exact`
- `translation-verification-nkjv-bolls.json`
  - Source: Bolls Bible API `NKJV`
  - Checked canonical entries: 121
  - Result: 121 `verified-exact`

## Applied Corrections

The original converted seed text was not exact against the selected external sources in several places.

English examples corrected during verification included:

- One wording mismatch in Titus 1:7-9.
- A truncated Hebrews 12:1-2 passage.
- Psalm 27:1 capitalization/superscription differences.
- Multiple punctuation and quotation differences.

Chinese verification found broader RCU17TS wording differences, so `scripture.zh` was synchronized from Bible Gateway RCU17TS across the canonical seed entries.

After synchronization, both language fields verify exactly under the project normalizer.

## Data Model Notes

`daily-verses.legacy.json` remains unchanged. It is the historical source trace, not the runtime devotional source.

Runtime and future editing should use:

- `daily-verses.seed.json` for canonical records.
- `daily-verses.expanded.json` when a literal 500-entry export is needed.
- `translation-checklist.csv` for human review or external audit.

## Verification Boundary

The current verification proves exact agreement with:

- Bible Gateway `RCU17TS` page text as fetched by `verify_rcuv_with_biblegateway.py`.
- Bolls Bible API `NKJV` text as fetched by `verify_nkjv_with_bolls.py`.

If the school later requires a different official source, such as a direct Hong Kong Bible Society export or a licensed API.Bible account, rerun verification against that source and update the `translationVerification` metadata accordingly.
