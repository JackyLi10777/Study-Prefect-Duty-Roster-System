# Mobile preflight checkpoint — 2026-09-05

Status: development checkpoint, **not deployed, not a release approval**.

## Source inventory and ownership

The new work starts at protected-main source `12d6732`, after a fresh fetch,
in an isolated `codex/mobile-verification-contract-20260905` worktree.
The original checkout and the earlier mixed-stage scratch worktree remain
untouched. Historical deployment evidence is not rewritten as formal adoption.

| Earlier changes | Disposition | Reason and acceptance owner |
|---|---|---|
| Unified policy hours and policy-version regeneration | Retain main implementation; regression-test | Already integrated independently; ordinary duty display/service mappings remain separate |
| Dashboard, shell, theme, styles, progressive content, quiet media | Refactor/adopt by behavior | Mobile first-paint and all-route evidence remain required; peer UI work owns overlapping styles |
| Prefect directory, filters, edit session | Refactor in isolated person-editor branch | Reusable component must reject stale generations and preserve final input; no whole-file scratch transplant |
| Draft, adjustment, export and candidate handling | Integration-owned | Shared draft controller/document/export session must preserve atomic save, CAS and receipts |
| Scratch deletions of PNG renderer/native share and their tests | Reject for integration | Preserve peer PNG/native-share implementation and its accepted delivery tests |
| Generated CSS, utilities and icon subset | Retain only with source/manifest consistency checks | Source-controlled generated output and required release identity; do not copy an untracked bundle alone |
| Browser verifiers and source-string tests | Replace obsolete assertions with behavior evidence | Old full-test success does not certify current browser states or throttled performance |
| Release registry and Windows/Worker consumers | Peer release-gate workstream owns implementation | One trusted registry; no independently maintained required lists |
| New database, configurable posts, CP and annual report | Integration task owns model | This checkpoint adds no database/API migration or competing domain model |

## Implemented contract

`scripts/mobile_verification_contract.py` defines source-owned scenarios,
eight viewports, Chromium/WebKit profiles and progressive-state requirements.
Static page routes come from the page catalog, with explicit audit/history,
aliases, dynamic roster states, Public and Viewer additions. Recursive AST
registration checks reject uncovered or unresolvable routes without starting
the application. Coverage here certifies presentation scenarios, **not** the
separate Admin/Guest/Public/Viewer authorization matrix.

The consumer is `validate_mobile_release_report(report, fingerprint=...)`.
It requires the current contract fingerprint, clean source, fixed cold profile,
tool/browser identity, complete coverage, all performance targets and complete
core interaction sequences. Reports cannot replace raw samples with green
summaries or remove expected cases. The helper itself is in the runtime source
fingerprint.

Each performance target requires at least five independent context/navigation
samples. The applied profile includes cache disabled, 390x844, DPR 2, 150ms
latency, 200000 B/s down, 93750 B/s up and 4x CPU. Observer support, observed LCP
and interaction entries, semantic completion and successful navigation are
required. Budgets are recomputed from raw values; zero CLS/TBT/long-task work
is legitimate, but missing paints/events are not.

Core windows require both open and close actions, true candidate/person/date
selections, raw task intervals and complete semantic results. The consumer
recomputes long tasks and carry-in instead of trusting a summary. Contaminated
windows remain evidence and fail; they are not silently dropped.

`collect_case_results` continues independent assertion failures and produces
explicit not-run results for missing engines/fixtures. Any failure to establish
source or fixture integrity stops further gestures, retaining all expected
rows. The aggregate does not copy exception messages containing page data.

## Evidence and remaining integration

The contract has focused positive and negative unit tests. These use fabricated
records to test the **validator**, not to claim browser observations. The
browser runners and release-registry workstream must integrate their measured
results through this consumer before any final mobile gate can pass.

Remaining work includes full producer integration, reusable editor browser
testing, final-model integration, controlled cold/core performance, the complete
browser/access matrix, and physical Android/iPhone plus supervised encrypted
restore acceptance. No test-site update occurs until the entire implementation
and automated acceptance are complete. Technical deployment and formal use
remain separate states.
