# Frontend product-finish evidence — 2026-08-02

**State:** released and deployed as `v1.2.0-rc.49`; supervised acceptance remains pending

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

Protected-main rc49 adds `nicegui_app.launcher` as the managed composition edge. It binds NiceGUI storage to the official database runtime directory before importing the framework. The deployer keeps complete bundle hashing fail-closed, recognizes only a post-marker, at-most-64-KiB NiceGUI `general` or UUID-bound user JSON delta whose exact exclusion reconstructs the marker, waits until the old process is stopped, validates and atomically migrates the JSON to protected runtime storage, removes the source delta, then requires the ordinary full fingerprint again. Invalid names, arrays, malformed JSON, oversized files, reparse points and every unrelated source change remain deployment blockers.

## Production closure

Annotated `v1.2.0-rc.49` resolves to protected-main commit `21928e38a0df6fd217a8ba449eb675b94a282f01` and tree `4e75e0c767dac7b2136a62162d3d5abaf84461b3`. Its 312-file release fingerprint `e350497ba121e2420f00cbae3725334e8c45267e140388bbd0b5530e84135878` passed all 15 formal gates. The controlled Windows deployment completed at 2026-08-02 17:16 HKT and switched the owned task to `-B -X utf8 -m nicegui_app.launcher` in `C:\SingYinRoster\releases\v1.2.0-rc.49-21928e38a0df-5c891432a1d8`.

The deployer migrated exactly one 54-byte rc47 preference file to `C:\SingYinRoster\data\runtime\nicegui-storage`; its SHA-256 remained `ab7e541b1f3a5328b4d8e02e0e56a31d9bdbb1d650c79c62b3765e1b77829e55` and the runtime ACL check reported no weak, unprotected, missing or insufficient identity entries. Both the new rc49 bundle and rollback rc47 bundle then matched their complete marker fingerprints and contained no `.nicegui` storage file.

Fresh backup `20260802-091628-350429-manual_verified_backup.sqlite3`／SHA-256 `f827c8932bd78ca2b2528728e6770c539c6f2ad8adfa64a3ec85cd69485e8fd9` passed checksum, SQLite integrity, schema, fairness, row-count, restore-audit and isolated-restore evidence. Origin returned `status=ok`, `writeReady=true`, `maintenance=false`, `recoveryRequired=false`, `pendingBackupObligations=0`, and Alembic `0012`.

Worker `99ed9a4e-8167-44bd-b478-562ff8f4d17e` passed 0% version-override health／entrance／Viewer smoke before promotion to 100%; `a7218f51-ec6c-4002-a9be-9dfbb691136c` remains the exact edge rollback version. Canonical browser checks then passed all 13 public-entry lifecycle cases, real Guest workbench rendering at desktop and 390px reduced-motion, one visible Admin／Guest pair per viewport, Admin Cloudflare Access redirect, Light→Dark persistence and zero console／page errors.

## Verification ledger

| Gate | Result |
|---|---|
| Focused Python component／IA／accessibility／navigation contracts | Passed: 90 tests |
| Worker Deno contracts | Passed: 53 tests |
| Python compilation of changed modules | Passed |
| Complete Python collection | Passed: 1,150 tests |
| Admin／Guest theme continuity | Passed: 16 browser cases across viewport, appearance and accessibility modes |
| Public entry music／navigation lifecycle | Passed: 13 browser cases including rejection, exception, slow retry, double activation and `pageshow` reset |
| Exact-source release gate | rc49 protected-main source passed all 15 gates; 312 files; fingerprint `e350497ba121e2420f00cbae3725334e8c45267e140388bbd0b5530e84135878` |
| Production deployment and canonical smoke | Origin rc49 and Worker `99ed9a4e-8167-44bd-b478-562ff8f4d17e` at 100% passed deployment, recovery, health and rendered canonical checks |

The technical deployment is complete. Supervised Head Study Prefect／teacher-advisor acceptance and the physical off-site BitLocker recovery drill remain independent pending obligations and are not implied by the automated result.
