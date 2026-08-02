# Daily Verse Review Notes

## Dual Foundational Convictions

**為何服事／Why we serve — 馬可福音 10:45／Mark 10:45**

`非以役人，乃役於人／Not to be served, but to serve` is a service principle drawn from the passage, not a verbatim quotation.

**如何服事／How we serve — 使徒行傳 24:16／Acts 24:16**

Decisions should remain truth-bound before God and explainable, traceable, and accountable before people. A conscience without offense is faithful discipline arising from resurrection hope and gospel grace, not salvation earned by works or a claim of sinless perfection.

Together these convictions shape the Sing Yin Study Prefect Duty Roster System. The Daily Verse module, roster generation, fairness audit, leave adjustment, publication, recovery, and handover should quietly reinforce servant leadership: authority exists to care for others, maintain order, act honestly, and create peace after the pattern of Christ.

## Conversion Summary

- Source: `D:\code_v3\daily_verses.py`
- Legacy entries preserved: 500
- Unique exact legacy devotional entries promoted to seed: 121
- Reviewed curated entries added without a legacy ID: 1
- Duplicate extra entries detected: 379
- Current polished seed entries: 122

The old bank has complete fields but heavy repetition. The seed stores 121 unique legacy-derived devotional records with all original IDs for traceability, plus one independently sourced curated record that must not invent a legacy mapping.

## Files

- `daily-verses.legacy.json`: all 500 original records, unchanged in source content, with duplicate grouping metadata.
- `daily-verses.seed.json`: normalized active seed records, one per unique exact devotional entry.
- `daily-verses.expanded.json`: generated 500-entry polished export, one record per original legacy ID, using canonical seed scripture/reflection content.
- `translation-checklist.csv`: checklist for authorized exact-text verification against RCUV 2010 and NKJV.
- `translation-audit.md`: local verification status and external source verification plan.
- `review-notes.md`: editorial and theological review notes.

## Duplicate Handling

Duplicates are detected by exact signature:

```text
reference_zh + reference_en + zh + en + reflection_zh + reflection_en
```

Each exact duplicate group receives a stable `duplicateGroup` such as `dup-0001`. The seed entry keeps all old IDs in `legacyIds`, while `daily-verses.legacy.json` records whether each old entry is canonical for its duplicate group.

## Quality Status

- `raw`: structurally converted but not yet polished.
- `reviewed`: structurally valid and acceptable after content review.
- `polished`: reflection rewritten or refined for final dashboard use.
- `deprecated`: reserved for legacy records or entries later excluded from active rotation.

Current status: all 122 canonical seed entries are `polished`. The 121 `origin: legacy` records preserve their `legacyIds` and cover all 500 original legacy records; `dv-0122` is `origin: curated`, has `legacyIds: []`, and does not alter that historical mapping.

## Editorial Pass: Servant Leadership

Status: completed.

All 27 entries tagged `servant-leadership` have been polished using the approved evangelical theological and pastoral review lens. Each polished entry now has:

- A Traditional Chinese title, devotional reflection, and short prayer or response line.
- A natural English title, reflection, and prayer or response line.
- No Chinese role titles inside English prose.
- Clearer biblical grounding and less formulaic application.
- A stronger connection to humility, fairness, sacrificial service, responsibility, and care for others.

### Polished Entries

| ID | Reference | Editorial emphasis |
|---|---|---|
| `dv-0001` | Mark 10:43-45 | Foundational principle: 非以役人，乃役於人. |
| `dv-0002` | John 13:14-15 | Christ washing feet as the concrete pattern of humble leadership. |
| `dv-0006` | Matthew 20:26-28 | Greatness redefined through service and ransom-shaped sacrifice. |
| `dv-0007` | Luke 22:26-27 | Presence among the team as one who serves, not one who seeks status. |
| `dv-0008` | Galatians 5:13 | Freedom and discretion governed by love, not convenience. |
| `dv-0011` | Micah 6:8 | Justice, mercy, and humility applied to fairness audit and leave adjustment. |
| `dv-0013` | Ephesians 4:2-3 | Gentleness and patience as safeguards for team unity. |
| `dv-0017` | 1 Peter 4:10 | Rostering as stewardship of God-given gifts. |
| `dv-0030` | Matthew 23:11-12 | Warning against role privilege and self-exaltation. |
| `dv-0031` | Mark 9:35 | First by becoming servant of all. |
| `dv-0032` | John 12:26 | Service to Christ must follow the way of Christ. |
| `dv-0033` | 1 Corinthians 9:19 | Gospel freedom expressed through voluntary service. |
| `dv-0034` | 2 Corinthians 4:5 | Not self-display, but Christ-centred servant witness. |
| `dv-0035` | Ephesians 6:7 | Ordinary duties offered willingly before the Lord. |
| `dv-0036` | Colossians 3:23-24 | Wholehearted work under the lordship of Christ. |
| `dv-0041` | James 4:10 | Humility before God as protection against proud judgment. |
| `dv-0050` | Philippians 2:5-8 | The mind of Christ as the Christological foundation of servant leadership. |
| `dv-0059` | Hebrews 10:24-25 | Mutual care that stirs love and good works. |
| `dv-0069` | 2 Timothy 2:24-25 | Gentle, patient correction without quarrelsome authority. |
| `dv-0072` | Matthew 6:14-15 | Forgiveness applied to mistakes without weakening accountability. |
| `dv-0089` | Matthew 25:21 | Faithfulness in small duties as trustworthy service. |
| `dv-0097` | Matthew 5:13-14 | Salt and light through fair, non-abusive leadership. |
| `dv-0099` | Hebrews 6:10 | Hidden labour remembered by God. |
| `dv-0102` | Psalm 37:23-24 | Stumbling, correction, and grace-supported recovery. |
| `dv-0116` | Luke 6:38 | Generous measure without partiality. |
| `dv-0120` | Psalm 1:1-3 | Long-term servant leadership rooted in God's Word. |
| `dv-0121` | Matthew 5:13-14 | Visible witness through daily order and character. |

### Dashboard Hero Candidates

The following servant-leadership entries are marked for `dashboard-hero` rotation:

- `dv-0001` Mark 10:43-45
- `dv-0002` John 13:14-15
- `dv-0006` Matthew 20:26-28
- `dv-0007` Luke 22:26-27
- `dv-0011` Micah 6:8
- `dv-0031` Mark 9:35
- `dv-0050` Philippians 2:5-8

`dv-0001` remains the foundational entry and keeps `specialUse: ["dashboard-hero", "roster-generation"]`.

## Curated Conviction Entry

`dv-0122` adds Acts 24:16 for ordinary Daily Verse and relevant theme rotation, with fixed `justice-fairness`, `faithfulness`, and `spiritual-formation` themes and `roster-generation`／`platform-conviction` special uses. It is deliberately **not** foundational, so `dv-0001` remains the only `isFoundational: true` entry. It is also excluded from the Worker's fixed five-entry public landing rotation.

The bilingual reflection applies the passage to drafting, adjustment, publication, and recovery decisions, including choices that may not be visible to others. Its theological review explicitly ties conscience to resurrection hope and gospel grace and rejects both works-righteousness and self-declared sinless perfection.

## Editorial Pass: Full Canonical Corpus

Status: completed locally.

After the servant-leadership pass, the remaining 94 raw canonical entries were polished in three general editorial batches:

- Batch 1: `dv-0003` to `dv-0046` where raw, covering humility, justice/fairness, witness, faithfulness, and spiritual formation.
- Batch 2: `dv-0047` to `dv-0088` where raw, covering speech, mercy, peace, correction, forgiveness, partiality, encouragement, and community care.
- Batch 3: `dv-0090` to `dv-0119` where raw, covering perseverance, courage, prayer, Scripture, renewal, and long-term faithfulness.

All polished reflections now include:

- Traditional Chinese title, devotional reflection, and short prayer/response.
- Natural English title, reflection, and prayer/response.
- No Chinese role titles in English prose.
- Project-specific application to Study Prefect leadership, fairness, care, responsibility, discipline, and spiritual formation.

The generated expanded devotional file now contains 500 entries, all with polished canonical reflections:

```powershell
python -X utf8 scripts\devotional\build_expanded_devotional.py
```

## Validation

Run:

```powershell
python -X utf8 scripts\devotional\validate_devotional_data.py
```

Latest result:

```text
seed entries: 122
legacy entries: 500
covered legacy entries: 500
origin counts: legacy = 121, curated = 1
status counts: polished = 122
issues: 0
expanded entries: 500
expanded polished entries: 500
```

The generated validation report is stored at:

```text
data/devotional/validation-report.json
```

## Translation Accuracy Boundary

Translation verification has now been completed against the selected external sources:

- Chinese: Bible Gateway `RCU17TS`
- English: Bolls Bible API `NKJV`

Both source-specific verification reports show all 122 canonical entries as `verified-exact`. See:

```text
data/devotional/translation-audit.md
data/devotional/translation-verification-rcuv-biblegateway.json
data/devotional/translation-verification-nkjv-bolls.json
```

## Reflection Review Lens

Use the approved evangelical theological and pastoral lens:

- Scripture is the highest authority.
- Interpret by historical-grammatical reading and orthodox evangelical theology.
- Avoid vague moralism.
- Connect biblical truth to servant leadership, humility, fairness, patience, and sacrificial service.
- Use natural English. Prefer `Head Study Prefect`, not Chinese role titles inside English prose.
- Keep Chinese reflections dignified, devotional, and suitable for a school leadership setting.
- Add a short prayer or response line for dashboard display.

## Priority Themes

Primary:

- `servant-leadership`
- `humility`
- `sacrificial-service`

Supporting:

- `justice-fairness`
- `mercy-care`
- `faithfulness`
- `prayer-peace`
- `wisdom-discernment`
- `perseverance`
- `witness-light`

## Daily Selection Policy

Runtime selection should use:

```text
daysSinceEpoch % activeVerseCount
```

Dashboard selection may prefer entries marked `specialUse: ["dashboard-hero"]`, especially polished servant-leadership entries. Roster-generation pages may prefer entries marked `specialUse: ["roster-generation"]`.

## Next Editorial Pass

1. If the school chooses a different official Bible source, rerun verification and update `translationVerification` metadata.
2. Continue future devotional improvements theme by theme as the system matures.
3. Keep duplicate groups intact so later edits remain traceable to legacy IDs.
