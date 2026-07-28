# R6 focused code audit — bounded state, authorization, release provenance and host policy

**Date:** 2026-07-29
**Audited baseline:** `v1.2.0-rc.31` / `ba129a4931d11e844649e8ff356f5bf2ab048459`
**Remediation branch:** `codex/r5-r6-integrated-remediation`
**Scope:** the R6 claims supplied in the execution brief, checked against current source, tests and read-only host evidence.

This is the missing immutable R6 record. The supplied R6 review did **not** deeply complete the music, PDF-export or showcase-route paths. Those omissions were reviewed separately during Codex adjudication; they are not silently counted as part of the original audit.

## Executive result

R6 identified four confirmed or partly valid release-relevant defects: unbounded Guest receipt growth, incomplete release-report provenance, unstable retry intent at adapter boundaries, and write-time principal expiry. IPv6 loopback configuration and method-name workflow fencing were also real defects. Several other claims proposed fixes that would add complexity without protecting a secret or a trust boundary and were rejected.

## Finding record

| ID | Claim checked | Current decision | Evidence / required disposition |
|---|---|---|---|
| R6-001 | Guest command receipts retain full workspace views and grow with commands × state × tabs | **confirmed** | `_CommandReceipt` retained state-sized results. Remediation stores bounded digest/revision metadata, evicts per workspace, enforces a global receipt bound and returns current truth with replay metadata. Deterministic `tracemalloc` coverage proves the configured bound without allocating production-scale memory. |
| R6-002 | Formal release report is insufficiently bound to immutable source | **partially valid** | The fingerprint gate already existed, but the report did not bind commit, tree, clean state, planned annotated tag, ordered check identities and tool versions. Schema 2 now records and validates all of them; deployment verifies report, tag, `origin/main`, tree and fingerprint together. |
| R6-003 | Retry-sensitive UI intents can receive a new command ID | **partially valid** | Domain writes were idempotent, but the PageContext fallback could mint a new UUID on a retried call. Official Guest mutations now accept and reuse intent IDs; a persistent workflow exposing `command_id` fails closed when one is omitted. Independent deliberate actions still receive new IDs. |
| R6-004 | `SING_YIN_HOST=::1` is accepted although installed TrustedHost handling rejects bracketed IPv6 Host headers | **confirmed** | Configuration now fails fast for `::1` and `[::1]`; canonical origin remains `127.0.0.1`. |
| R6-005 | Cache drift needs a detector | **unproven** | No measured stale-content or source-attribution failure was reproduced. Existing bounded cache rules remain; no second cache state machine was added. |
| R6-006 | Public source fingerprint comparisons require constant-time equality | **rejected by product contract** | The fingerprint is public integrity metadata, not an authentication secret. Constant-time comparison would not close a trust boundary. |
| R6-007 | Local secret/data ACL inheritance may be too broad | **partially valid** | Read-only inspection found inherited broad permissions on the installed root and `.env`. The Windows PowerShell 5.1 deployment path already protects and re-reads `.env`; all sensitive runtime paths must pass the existing ACL helper before production completion. No secret value was read. |
| R6-008 | Secret generation / weak placeholder handling needs strengthening | **partially valid** | Generation already uses OS CSPRNG. Origin and Worker now reject a small explicit set of obvious example placeholders and repeated-character values. The code does not claim to infer entropy from one supplied string. |
| R6-009 | A page/WebSocket can outlive the verified principal and still invoke a workflow | **confirmed** | `PageContextWorkflowAdapter` now retains the verified principal and calls `require_active()` immediately before every workflow invocation. Client polling remains UX only. |
| R6-010 | `PageContext` capability equality can be bypassed | **already fixed** | Current composition requires exact equality with central capability policy. No competing capability merge was found. |
| R6-011 | Workflow fencing bypasses by method name | **confirmed** | The name-based backup exemption was replaced by explicit `@fenced_workflow_write(internal_backup=True)` metadata. |
| R6-012 | Download filename fallback enables header injection | **rejected by product contract** | Fixed ASCII fallback plus percent-encoded `filename*` already prevents the claimed injection. No client interoperability defect was reproduced. |

## Omitted-path review

| Path | Callers/tests examined | Result |
|---|---|---|
| `nicegui_app/services/music_library.py` | local catalog, controlled online import and `tests/test_music_library.py` / `tests/test_online_music.py` | A concrete source-mutation window existed between downloaded-file validation and final placement. The copied staging file is now revalidated before atomic replace. |
| `nicegui_app/services/roster_export.py` | PDF delivery and `tests/test_pdf_delivery.py` | Font loading fails closed, names remain Chinese and generated-file delivery owns response policy. No evidence-supported code change required. |
| `nicegui_app/ui/page_routes/showcase.py` | public platform evidence and `tests/test_showcase_truth.py` | Data comes from verified release/test summaries and failure is surfaced with an operator reference. No hidden write or student-data path was found. |

## Release boundary

This report is source-review evidence, not proof of protected-main merge, annotated-tag parity, formal release gates, Windows deployment, canonical Worker traffic or supervised human acceptance. Those identities must be recorded after they are observed.
