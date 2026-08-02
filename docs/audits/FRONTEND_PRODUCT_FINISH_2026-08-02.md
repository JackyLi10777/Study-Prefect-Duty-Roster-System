# Frontend product-finish evidence — 2026-08-02

**State:** source candidate; not production evidence

**Scope:** public Worker entrance, shared NiceGUI shell, Dashboard workflow composition and Settings information rhythm

**Production at audit start:** the exact live identity remains owned by [`../status/CURRENT_STATUS.md`](../status/CURRENT_STATUS.md)

## Problem and decision

The broad request allowed a full visual rewrite, but the current product already had a coherent Quiet Command Center architecture, mature route families and a single terminal composition layer. Browser review found two narrower, measurable gaps: the 390px public entrance repeated administrator explanation and produced an unnecessarily long path to help／sharing, while the Settings route placed preference controls before the handover state an operator must understand first.

The accepted direction is **Woven Clarity**: preserve the proven frontend architecture and atmosphere library, then improve hierarchy through shared geometry, reduced surface nesting, one-decision mobile entry, explicit weekly sequence and settings roles. No route, identity flow, Guest capability, SQLite contract, policy, API, generated asset or animation dependency changed.

## Implemented seams

| Seam | Change | Boundary retained |
|---|---|---|
| `cloudflare/roster_viewer/worker.js` | concise Admin-first lead; one visible mobile Admin／Guest pair; supporting content order | Access, Guest workspace and entry-state lifecycle |
| `sing-yin-command-center-v2.css` | 264px rail, 64px header, 90px-minimum atmosphere, quieter surfaces and bounded workflow connectors | sole terminal layer; no token redeclaration |
| `nicegui_app/ui/shell.py` | drawer constant aligned with rendered rail | route and viewport runtime |
| Settings route／music components | readiness first; preference, continuity and recovery section roles | callbacks, persistence, verification and permissions |
| Design／architecture contracts | versioned the composition and iteration rules | live release identity remains generated elsewhere |

## Rendered evidence

Isolated Chromium rendering covered desktop-light Dashboard, desktop-light Settings and 390px mobile-dark Dashboard. A local Wrangler rendering covered desktop-light and 390px mobile-dark public entrance. The inspected candidate showed no horizontal overflow, preserved one visible Admin and Guest action per viewport, placed both mobile actions within the first 844px viewport and reduced the public mobile document from the former approximately 3,000px presentation to approximately 1,895px without hiding Daily Verse, music, recovery or sharing.

The generated concept boards were used only to challenge hierarchy and material choices. They were not copied into production and no generated image was added because the existing paired atmosphere assets already serve the approved narrative zones.

## Review adjudication

Protected-main review correctly found that CSS `order` made welcome music appear before sign-in help on mobile while leaving the opposite DOM／assistive-technology order. The audio section now precedes help in the source DOM, the two semantic-reordering declarations are removed and a full supporting-content order contract prevents regression. The review also prompted selector-scoped CSS assertions instead of unrelated whole-file string matches.

A separate suggestion to hide handover readiness from Guest was rejected after source verification. Guest `/settings` resolves through `GuestWorkflowAdapter`; its `backup_overview()`, readiness counts, checkpoint and restore are fictional, session-local memory state and never inspect the formal SQLite database or managed backup paths. Preserving this bounded demonstration is required Admin／Guest experience parity, while durable storage and external operations remain denied by the adapter boundary.

The first protected-main rc48 formal gate then caught two release-blocking visual regressions that focused screenshots had not: the 54px desktop brand mark fell below the existing rendered minimum of 58px, and the 84px atmosphere band fell below its 90px rendered minimum. The candidate keeps the narrower 264px rail, restores the mark to 58px, aligns its lockup／caption geometry, restores the atmosphere minimum to 90px and adds selector-scoped static contracts before rerunning the rendered gate. No production switch occurred during the failed attempt.

Protected main commit `17cb2d0dcf575d1194dd2f9cf104886f6dadf0d5` then passed all 15 schema-3 source gates and was preserved as annotated source-only tag `v1.2.0-rc.48`. Its Windows deployment stopped before downtime or data mutation because the running rc47 bundle had gained one 54-byte `.nicegui/storage-user-<uuid>.json` preference file after its immutable marker was created. Investigation proved that NiceGUI resolves its default storage directory at import time; the managed task still entered through `nicegui_app.main`, so Admin theme／language／sound preferences were written into the release working directory.

The follow-up candidate adds `nicegui_app.launcher` as the managed composition edge. It binds NiceGUI storage to the official database runtime directory before importing the framework. The deployer keeps complete bundle hashing fail-closed, recognizes only a post-marker, at-most-64-KiB NiceGUI `general` or UUID-bound user JSON delta whose exact exclusion reconstructs the marker, waits until the old process is stopped, validates and atomically migrates the JSON to protected runtime storage, removes the source delta, then requires the ordinary full fingerprint again. Invalid names, arrays, malformed JSON, oversized files, reparse points and every unrelated source change remain deployment blockers.

## Verification ledger

| Gate | Result |
|---|---|
| Focused Python component／IA／accessibility／navigation contracts | Passed: 90 tests |
| Worker Deno contracts | Passed: 53 tests |
| Python compilation of changed modules | Passed |
| Complete Python collection | Passed: 1,150 tests |
| Admin／Guest theme continuity | Passed: 16 browser cases across viewport, appearance and accessibility modes |
| Public entry music／navigation lifecycle | Passed: 13 browser cases including rejection, exception, slow retry, double activation and `pageshow` reset |
| Exact-source release gate | rc48 passed all 15 gates; follow-up storage-boundary candidate requires a fresh protected-main replay |
| Production deployment and canonical smoke | rc48 stopped safely before downtime／mutation on the rc47 runtime-storage delta; production remained rc47 at this checkpoint |

This record must be updated with exact final gate and deployment evidence before any production-complete claim. Supervised Head Study Prefect／teacher-advisor acceptance and physical off-site recovery remain independent obligations.
