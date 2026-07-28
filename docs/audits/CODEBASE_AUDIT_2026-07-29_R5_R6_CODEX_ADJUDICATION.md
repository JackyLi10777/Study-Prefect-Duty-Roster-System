# Codex adjudication — R5 and R6 integrated remediation

**Date:** 2026-07-29
**Baseline:** annotated `v1.2.0-rc.31`, commit `ba129a4931d11e844649e8ff356f5bf2ab048459`
**Working branch:** `codex/r5-r6-integrated-remediation`
**Rule:** audit findings are claims. A source change is made only when current evidence shows a defect and the proposed remedy preserves the product and trust-boundary contracts.

## R5 decisions

| ID | Decision | Resolution |
|---|---|---|
| R5-001 | **confirmed** | Removed OS-theme full-page reload. In-place Quasar/CSS/control synchronization preserves edits, focus, scroll and dialogs. |
| R5-002 | **already fixed** | Current Worker contract and tests agree on the unset-system plus explicit Light/Dark model. The former two failures do not reproduce on the rc31 baseline. |
| R5-003 | **rejected by product contract** | “System” stays the unset initial preference; the visible control remains one Light↔Dark button. No three-state selector/cycle was restored. |
| R5-004 | **rejected by product contract** | Public/Worker and verified Admin/Guest stores remain separate. Bounded verified handoff is safer than an uncontrolled shared cookie. |
| R5-005 | **unproven** | The observer watches one body-class attribute and no visible flicker or event storm has been reproduced. No speculative debounce was added; browser evidence remains required. |
| R5-006 | **confirmed** | PNG support attachments now undergo bounded parsing and sanitized RGB/RGBA re-encoding; malformed, truncated, polyglot and oversized decoded images fail closed. |
| R5-007 | **confirmed provenance exception; semantics already fixed** | The executed upgrade is unchanged. The corrected downgrade permits all-legacy history and blocks any `flexible_weekly` history. The exception and future immutable-migration rule are documented. |
| R5-008 | **unproven** | A search branch cannot name one failed room as a proven cause. No fabricated solver diagnostic was added. |
| R5-009 | **already fixed** | Public and NiceGUI controls expose the next action in `aria-label`, current resolved state in `aria-pressed`, and matching icon/title. |
| R5-010 | **confirmed** | Six definition-only appearance keys were removed after repository-wide caller search. |
| R5-011 | **confirmed** | Clipboard denial, unavailable API and timeout now fall back to a manual-selection prompt with honest bilingual feedback. |
| R5-012 | **confirmed** | Operational documents are reconciled around explicit source candidate, reviewed release, live origin, live Worker, rollback pair and human acceptance states. Historical claims are labelled as historical/at that time. |
| R5-013 | **unproven pending rendered measurement** | The data-theme bootstrap predates paint and the server no longer reloads. A cold-cache light/dark browser check is required before claiming there was or is no visible FOUC. |

## R6 decisions

The complete R6 table and omitted music/PDF/showcase review are frozen in [the R6 record](CODEBASE_AUDIT_2026-07-29_R6.md). R6-001, 004, 009 and 011 are confirmed; R6-002, 003, 007 and 008 are partly valid; R6-010 is already fixed; R6-005 is unproven; R6-006 and 012 are rejected because their suggested remedies do not protect the claimed boundary.

## Material implementation

- Guest receipts are bounded metadata, not repeated workspace snapshots; replay is truthful and copy-safe.
- Stable intent IDs cross the Guest adapter boundary, while retry-sensitive workflow calls without an explicit ID fail closed.
- Principal activity is checked exactly at every workflow invocation.
- Support PNGs are parsed, bounded, stripped of nonessential metadata and re-encoded.
- `::1` is rejected before the application can enter an always-400 configuration.
- Formal reports are source-bound to commit/tree/clean state/planned tag/check order/tool versions; deployment verifies the same immutable identity.
- Backup fencing uses explicit metadata rather than a method-name escape hatch.
- Clipboard failure has a manual recovery path.
- Downloaded music is revalidated after local copying and before atomic publication.
- Obvious secret placeholders are rejected consistently by Worker and origin without pretending to estimate entropy.

## Migration 0011 provenance exception

The rc20-era source identity contained the same `0011` upgrade that writes the Assist assignment-mode column and default. Only downgrade guard behavior was later corrected: downgrade is allowed when all stored rows are `legacy_fixed_weekday` and refused when any `flexible_weekly` history exists. Because production had executed upgrade only, its schema/data effect did not change. Future released Alembic files are immutable; a semantic correction after release must use a new additive migration or an explicit provenance exception with upgrade/downgrade/recovery tests.

## Evidence and remaining gates

### Classified full-review reuse and delta closure

The exact rc31 baseline is covered by
`PRE_DEPLOYMENT_FULL_CODE_REVIEW_2026-07-28.md`, which classifies all 570 tracked
paths and records the reviewed code-bearing tree. This remediation does not
pretend to repeat line-by-line review of unchanged fonts, music, images, or
third-party artifacts. Instead, every delta from `ba129a4` was classified and
reviewed against its owning boundary:

| Delta class | Paths | Review focus | Result |
|---|---:|---|---|
| NiceGUI runtime／services／UI | 15 | authorization at write time, Guest memory and replay, PNG decode boundary, backup fencing, theme and clipboard state | no unresolved P0／P1／release-critical P2 |
| Cloudflare Worker and contracts | 2 | secret placeholders, identity parity and gateway compatibility | paired origin／Worker release required |
| Verification／deployment scripts | 3 | immutable source, report schema, ordered gate identity, IPv4-only host and fail-before-mutation behavior | fail-closed contracts retained |
| Focused tests | 10 | causal regression and stale documentation-contract replacement | evidence matches current runtime truth |
| Dependency／environment contract | 3 | pinned Pillow, reproducible lock and rejected IPv6 example | no unrelated dependency added |
| Status／security／architecture／operator documentation | 16 | current versus historical release identity, migration provenance and handover procedure | current rc31, rc30 rollback and rc32 candidate separated |
| Immutable audit records | 3 | R5 source preservation, R6 omissions and Codex adjudication | retained as separate records |

The deliberately omitted R6 music／PDF／showcase paths were reviewed through
their callers and tests as recorded in the R6 report. The final frozen-source
security, dependency, repository-hygiene, browser, recovery and deployment
gates remain authoritative over this classified review.

The untracked Public-support browser screenshot was preserved outside the release source at `D:\code_v3-evidence\r5-r6-preserved\public-support-browser-only-20260727.png` before repository cleanup. Its SHA-256 is `A00BE06A01BAEB9243D3C408FDFDBE3E05339A3F4A6A1980060C3E6706DF028E` and its size is 209,501 bytes. It contains virtual browser-only support evidence, is not a source input, and is not used as deployment or human-acceptance proof.

Focused regression suites are recorded in the release work. Remaining blockers before deployment are: complete focused reruns after final edits, classified delta review, staged verification, protected PR/CI/review, frozen protected-main formal verification, annotated tag, verified production backup and isolated restore, Windows origin switch, canonical Worker deployment if Worker source remains changed, and online route/rollback verification. Supervised Head Study Prefect and teacher-advisor acceptance remains separate.
