# Changelog

This file records user-visible, operational and release-significant changes. The editable authority for observed deployment truth is `docs/status/current-release.json`; `docs/status/CURRENT_STATUS.md` is its generated, human-readable view and must not be edited by hand. Immutable historical evidence remains in `PROJECT_STATUS.md`, dated audits and generated release reports.

## Unreleased

- No release-significant changes are pending after the rc58 deployment closeout.

## v1.2.0-rc.58 — released, 2026-08-14

- Deployed protected-main commit `e90bb8fdb95ca874f668b5a7134853756471635f` as annotated `v1.2.0-rc.58`. Its 319-file source fingerprint `c57778ce438c1c23c824c444827db7eeb9166d20be3ba3e78f1bb1221fee5283` passed all 15 formal gates; the Windows task now runs immutable bundle `C:\SingYinRoster\releases\v1.2.0-rc.58-e90bb8fdb95c-5c891432a1d8` at Alembic `0014`, with database quick check, health and readiness green and `writeReady=true`.
- Created and isolated-restored rc57 rollback snapshot `20260813-161548-042930-manual_verified_backup.sqlite3` with SHA-256 `ff032d921f767e68dd77912cd80109c410beb83dd185e3ef85390e913b54912c`, then established the quiescent rc58 recovery baseline `20260813-161554-736678-manual_verified_backup.sqlite3` with SHA-256 `0e0ee9cc9a592eeea66055e107c461e859f3ccec2791cb06f051e7078c3febc2` and manifest SHA-256 `374af23dd050073e73a2fafeaf43120db542e3ed7236a630cf2c7aa88d1fb419`; checksum, SQLite integrity, schema, fairness, row counts and restore audit passed.
- Added the professional-source native motion substrate without changing NiceGUI／Quasar, identity, roster transactions, API or schema: licensed external-source evidence is fail closed; productive／expressive timing and one semantic `motion_pattern` owner now drive bounded Platform, Dashboard and roster-editor pilots; removed nodes clear timelines and motion flags before safe rehydration.
- Worker executable source, configuration, public assets, package and lock files did not change. The generated design-token contract is outside Wrangler upload inputs, so canonical Worker `7951ca55-ffda-4f16-b570-d37486311914` correctly remains at 100% without a redundant deployment. Canonical health, landing, Viewer, Support, Access redirect, browser-shaped Guest entry and public-entry music recovery were rechecked after the Origin switch.
- Automated release and online checks are complete. Final physical Android Chrome acceptance and the off-site BitLocker recovery drill remain explicit supervised-human tasks.

## v1.2.0-rc.57 — released, 2026-08-10

- Deployed protected-main commit `f83bbbb095e5fb2c029ac37add1308f33dd2eb9e` as annotated `v1.2.0-rc.57`. Its 317-file source fingerprint `33e77fb6cddc791b60e2b695db417f29d508b77bba71f143186c4f5591ba916a` passed all 15 formal gates; the Windows task now runs immutable bundle `C:\SingYinRoster\releases\v1.2.0-rc.57-f83bbbb095e5-5c891432a1d8` at Alembic `0014`, with health and readiness green and `writeReady=true`.
- Created and isolated-restored previous-version rollback snapshot `20260810-111736-505211-manual_verified_backup.sqlite3`, then established the quiescent rc57 recovery baseline `20260810-111743-227200-manual_verified_backup.sqlite3` with SHA-256 `d9603c329c995132d9955bcfbe74aafa46c5b5c6e0393e7f009b76bc2b746a29`; checksum, SQLite integrity, schema, fairness, row counts and restore audit passed.
- Staged Worker `7951ca55-ffda-4f16-b570-d37486311914` at 0%, passed version-specific health／entrance／Viewer smoke, and promoted it to 100%. Canonical health, landing, Viewer, Support, Admin redirect and browser-shaped Guest entry were then rechecked without a version override.
- Completed the mobile-first weekly workflow introduced through rc56: dedicated rectangular quick-setting tiles replace leaked desktop rotary styling, the drawer and bottom navigation now reconcile one authoritative state, and phone／tablet roster generation and draft editing retain the same versioned Admin／Guest transactions as desktop.
- Stabilized the public Viewer shell with a viewport-height reservation so its delayed content no longer creates layout shift. A real Chrome run across 320, 360, 390, 412 and 430 px phones, 768 and 820 px tablets, 844×390 landscape, 200% text, forced colours and reduced motion recorded CLS `0` on every measured route and no unexpected browser errors.
- Made the canonical mobile verifier compatible with the production CSP by loading intercepted same-origin Viewer CSS through the normal network path. The deliberate Support network-failure exercise now isolates and records its one expected `ERR_CONNECTION_FAILED` console event while continuing to reject every other console or page error; report input remains preserved and receives a tab-only fallback reference.
- Machine deployment and browser evidence are complete. Final physical Android Chrome acceptance and the off-site BitLocker recovery drill remain explicit supervised-human tasks rather than automated claims.

## v1.2.0-rc.54 — released, 2026-08-09

- Deployed protected-main commit `f027628c5a0045d8a946be9a3453e041d03367d1` as annotated `v1.2.0-rc.54`. Its 316-file source fingerprint `738c45917fdcbeeb84a523a1f1cc3179adee693b07e156bdb74fa6f8748b3ef8` passed all 15 formal gates; the Windows task now runs immutable bundle `C:\SingYinRoster\releases\v1.2.0-rc.54-f027628c5a00-5c891432a1d8` at Alembic `0014`, with health and readiness green and `writeReady=true`.
- Created and isolated-restored the previous-schema rollback snapshot `20260809-093342-034683-manual_verified_backup.sqlite3` and the quiescent rc54 recovery baseline `20260809-093349-010387-manual_verified_backup.sqlite3` with SHA-256 `65e2d9c086b0aa4e9495f17d55ad2d62ea238c049d046debba7b124205166a29`; checksum, SQLite integrity, schema, fairness, row counts and restore audit passed. Recovery to rc52 requires its compatible 0013 snapshot and must never be a code-only switch.
- Staged Worker `053b8f6e-c5ed-4259-ac34-aaefa4dfb23d` at 0%, passed version-specific health／entrance／Viewer smoke, and promoted it to 100%. Canonical root, authenticated Guest workspace entry, Viewer, public `/support` theme control and the Admin redirect boundary were then rechecked without a version override.
- Added week-local, per-cell `unavailable` roster exceptions through additive Alembic revision `0014_roster_slot_exceptions`. The generator, shared presentation, web draft, bilingual PDF, public Viewer and Guest adapter now share the same five-state contract and never count a closed cell as required coverage or fairness capacity.
- Extended the existing Excel-style draft matrix with pointer-threshold move／swap, touch two-step movement, roving keyboard navigation, undo／redo, stable retry command IDs, unsaved-change protection and conflict comparison／reapply. Changes remain page-local until one atomic, version-checked save.
- Added Admin／Guest-parity prefect directory search, filters, stable sorting and allowlisted inline edits. One save now validates all targeted rows and versions as a single atomic batch: Admin uses one database transaction and Guest uses one workspace mutation. Any conflict or invalid field produces zero row writes while preserving the complete local edit session. Identity, role and archival changes remain confirmation-dialog operations.
- Introduced typed `DraftEditSession` and `PrefectEditSession` owners for pending values, dirty state, stable command IDs, undo／redo where applicable and conflict reapply, reducing route-local mutable-state duplication without moving policy or persistence into the UI.
- Removed the duplicate sidebar support card, divided the drawer into fixed brand／scrolling navigation／fixed footer regions, and gave the mobile drawer one authoritative requested-open state plus a dedicated fixed Close control. More/menu state, backdrop, focus trap, `inert`, ARIA and cleanup now reconcile together instead of depending on a hidden desktop trigger.
- Brought the public `/support` appearance control into exact entrance-family parity with the binary sun／moon control, current-state glyph, next-action label, bounded transition and reduced-motion fallback. Replaced invented operation percentages or fixed phases with delayed truthful indeterminate feedback; an AI-labelled wait indicator remains reserved for the optional schema-mapping operation only.

## v1.2.0-rc.52 — released, 2026-08-09

- Deployed protected-main commit `72621076f74caf9568fda1576d62311e0a26043c` as annotated `v1.2.0-rc.52`. Its 314-file fingerprint `c4f224140c3b2bb935f4d367bf0fccf55800fd28a6a697e66bd261b70e097b6f` passed all 15 formal gates; the Windows task now runs the immutable rc52 bundle at Alembic `0013`, with health and readiness green and `writeReady=true`.
- Created and isolated-restored the quiescent rc52 recovery baseline `20260808-164321-281874-manual_verified_backup.sqlite3` with SHA-256 `1d542f5aac6b25eff4abf5f79cddd295ebc04a6ef797a7ac8b8f88f22d13928a`; checksum, SQLite integrity, schema, fairness, row counts and restore audit passed. The previous rc51 bundle and its schema-compatible verified rollback snapshot remain the first controlled origin fallback.
- Staged Worker `3bac2eee-246f-4524-9725-4249770017b0` at 0%, passed version-specific health／entrance／Viewer smoke, and promoted it to 100%. Canonical Chromium then verified Guest workspace entry, Cloudflare Access redirection, Viewer, public-entry music behavior, `system`／light／dark continuity into `/support`, and a non-sensitive report persisted in the protected local inbox with a valid `INC-…` trace code.

- Unified the public entrance and Viewer support page with the same pre-paint `system`／light／dark preference as the public landing, then added a bounded same-origin submission path to the host-local redacted support inbox. Successful reports return a traceable `INC-…` reference; network or storage failure preserves the reporter's input and creates an explicit tab-only `FB-…` fallback. Public capability, principal lifetime, rate limit, streamed body limit and exact payload shape remain fail-closed; verified administrators can validate and export an exact incident by reference without exposing a public inbox.
- Corrected the migration-deployment preflight boundary. An immutable candidate bundle no longer runs its new-schema strict readiness check directly against the still-live old-schema database. Every deployment attempt now uses the bundle's own Python and safety helper to make a WAL-consistent online SQLite copy inside a protected, bounded workspace, migrate and verify only that copy, create and restore an isolated backup, run strict readiness with isolated paths, remove the proof data, and recheck the bundle fingerprint before any task stop. The rc50 source remains immutable; its safely failed pre-downtime deployment is superseded by the next candidate rather than retagged.
- Added one shared roster presentation contract for the editable draft, published view, bilingual PDF, public Viewer and Guest workspace. The desktop draft is now an Excel-style keyboard/touch matrix, while mobile uses the same data as weekday cards; Chinese-name suggestions, explicit vacancies, undo, atomic swaps and one batch save no longer drift from the printed schedule.
- Added week-local whole-day closures through additive migration `0013_roster_day_closures`. A closed day clears that draft day's assignments, reopening exposes explicit vacancies, zero-duty weeks remain valid, and published weeks must be withdrawn before closure changes; Guest exercises the same behavior only in isolated fictional memory.
- Aligned legacy Assistant fixed-weekday editing with generation: an eligible fixed owner remains required, while registered leave or unavailability permits a legal one-week substitute instead of making a generated draft impossible to save.
- Replaced artificial progress sleeps with immediate work execution and a truthful 140 ms reveal threshold. Slow operations retain the durable operation lease through cancellation or UI failure, and runtime verification now records TTFB, DOMContentLoaded, load and app-ready timings without invented percentages or minimum animation time.
- Raised the source candidate's security-sensitive Python and Worker dependency constraints to remediated releases after the audit identified vulnerable `aiohttp`, `cryptography` and `undici` ranges. Runtime and development locks, Worker tooling and their independent audit gates must agree before release; this source change does not claim deployment.
- Added a two-layer founding-conviction section to `/platform`: Mark 10:45 explains why authority serves, while Acts 24:16 grounds explainable and accountable decisions in resurrection hope and gospel grace. Direct Scripture, paraphrased principle, and platform interpretation are explicitly distinguished.
- Added curated canonical devotional `dv-0122` in verified RCUV 2010／NKJV form, with bilingual reflection, source hashes, theological review, and fixed roster／platform classifications. The canonical bank is now 122 entries while the historical expanded mapping remains exactly 500 records.
- Added `legacy | curated` devotional provenance validation, secure translation-specific Scripture links, compact two-line authenticated／public footers, and regression coverage that keeps the five-entry public landing rotation unchanged.
- Repaired the RCUV source extractor so presentation-only footnote superscripts cannot be mistaken for Scripture during external verification.
- Replaced page-bound music `ui.timer` callbacks with route-and-render-scoped, keyed browser deferrals. Rapid A→B→A navigation now invalidates stale autoplay, continuity, playlist-resume and dialog-focus work; manual track selection cancels queued auto-resume instead of letting old work reach a new source or deleted NiceGUI slot.

## v1.2.0-rc.49 — released, 2026-08-02

- Deployed protected-main commit `21928e38a0df6fd217a8ba449eb675b94a282f01` as annotated `v1.2.0-rc.49`. The 312-file source fingerprint `e350497ba121e2420f00cbae3725334e8c45267e140388bbd0b5530e84135878` passed 15／15 gates; Windows Origin now runs the immutable rc49 bundle through `nicegui_app.launcher`, with health／readiness green and Alembic `0012` unchanged.
- Migrated the one validated 54-byte rc47 NiceGUI administrator-preference JSON to protected runtime storage before switching bundles. The rc47 rollback bundle was restored to its full marker fingerprint, the external file retained its exact SHA-256, and no runtime preference remains inside either immutable bundle.
- Created verified backup `20260802-091628-350429-manual_verified_backup.sqlite3` with SHA-256 `f827c8932bd78ca2b2528728e6770c539c6f2ad8adfa64a3ec85cd69485e8fd9`; checksum, SQLite integrity, schema, fairness, row counts, restore audit and isolated restore passed.
- Staged Worker `99ed9a4e-8167-44bd-b478-562ff8f4d17e` at 0%, passed version-override smoke and promoted it to 100%. The previous Worker `a7218f51-ec6c-4002-a9be-9dfbb691136c` remains the exact edge rollback identity; canonical Admin redirect, Guest desktop／mobile workbench, Viewer, theme persistence and browser error checks passed.

- Kept annotated `v1.2.0-rc.48` source-only: all 15 source gates passed, but the Windows deployer stopped before downtime when rc47 contained one post-marker NiceGUI administrator-preference file. The new production launcher resolves `NICEGUI_STORAGE_PATH` to mutable runtime data before importing NiceGUI; deployment accepts only bounded, post-marker `storage-general.json` or `storage-user-<uuid>.json` deltas whose exclusion reconstructs the original bundle fingerprint, then stops the old process, validates and migrates those JSON objects, removes them from source, and re-verifies the complete immutable bundle. Every other bundle delta remains fail-closed.
- Refined Quiet Command Center into the `Woven Clarity` product-finish pass without adding a second CSS layer or frontend dependency: the desktop rail is narrower, shared surfaces use quieter radii／shadows, route atmosphere is shallower and the weekly stages gain bounded wide-screen sequence connectors.
- Reworked the public mobile entrance into one concise decision-first stack with exactly one visible Admin and Guest action pair. Daily Verse, welcome music, sign-in recovery and sharing now follow in a deliberate order instead of repeating the administrator narrative in a second visible panel; Cloudflare Access, Guest isolation and entry-state behaviour are unchanged.
- Reordered Settings so handover readiness appears before preferences, then assigned shared preference, continuity and recovery section roles. This changes scanning and hierarchy only; callbacks, verification, persistence, confirmation and capability boundaries remain unchanged.
- Updated the canonical public-entry browser verifier to complete intercepted Admin／Guest navigation with HTTP 204. This preserves the entrance DOM for loading-state inspection without creating a Guest session or entering Cloudflare Access; aborting the top-level request made current Chromium replace the page with `chrome-error://chromewebdata`.
- Replaced a CSP-incompatible bare `wait_for_function` expression with a function predicate and added a regression test for the no-content interception contract. Production behavior, security policy and release assets are unchanged.
- Closed the stale post-rc47 `ITR-002` release item: the host-local support inbox and durable Viewer withdrawal are live code whose remaining evidence belongs to supervised acceptance (`ITR-001`), not another deployment claim.
- Extended project governance so every actionable non-conditional iteration must be referenced by a tracked project risk. This prevents completed release work from lingering as an orphaned active queue item while preserving genuinely conditional maintainability work.
- Replaced the handover page's stale four-priority／13-check summary with seven supervised work sessions that cover every H-01–H-21 operator check and A-01–A-04 advisor decision, link to the relevant workspace, and provide an unchecked bilingual Markdown record without pretending the application can approve human evidence.
- Added a test-enforced contract between the UI acceptance catalog and the authoritative evidence matrix, and removed copied live release identifiers from the design standard so mutable production truth remains owned by the generated current-status system.

## v1.2.0-rc.47 — released, 2026-08-02

- Reset the NiceGUI workbench as a task-first Quiet Command Center: a wider institutional navigation rail, compact utility header, solid operational surfaces and contextual route bands replace the accumulated provisional composition without changing routes, identity, Guest, workflow, SQLite or recovery contracts.
- Reordered the Dashboard so the current weekly workflow precedes recent-history review and Daily Verse, retained truthful empty／busy states and rejected synthetic KPIs, fake progress and decorative alerts.
- Added one concise three-step product explanation to the desktop public entrance while preserving one visible Admin and Guest action per viewport, the existing login lifecycle, music fallback and Cloudflare security boundary.
- Added `docs/FRONTEND_ARCHITECTURE.md` as the owner for composition, CSS layers, route families, viewport runtime and migration. `sing-yin-command-center-v2.css` is the only terminal composition layer; a contract test rejects parallel terminal override systems.
- Corrected the adaptive viewport runtime so keyboard mode requires both a focused editable control and material visual-viewport reduction. It now exports complete visual viewport geometry, preserves the 256 CSS-pixel reflow and keeps mobile navigation available when only browser chrome changes.
- Rebuilt the sidebar brand lockup and 284px rail geometry to prevent bilingual identity overlap, kept 44px interaction targets and added light/dark, desktop/mobile, forced-colour and reduced-motion composition coverage without adding a frontend or animation dependency.
- Added a concise architecture overview and an executable import-direction contract for policy, core, persistence, workflow services and UI.
- Added one machine-readable current-release source plus deterministic Traditional Chinese／English status generation for all operator-facing guides, eliminating manual release-identity drift.
- Added a documentation lifecycle／ownership manifest, ADR register and decision-relevant iteration register; every maintained Markdown file now has a lifecycle class or declared collection.
- Added `scripts/project_governance.py --check／--write` and integrated the check into adaptive verification profiles. It validates status schema, generated blocks, local links, topic owners, document coverage and architecture boundaries.
- Kept secret scanning fail-closed while recognizing only the three schema-bound public provenance digests in the live status JSON; arbitrary high-entropy fields, paths or candidate states still fail review.
- Hardened review boundaries against relative-import bypasses, invalid-state generation, unresolved maintenance／recovery obligations, collection link drift and database snapshots incompatible with a rollback target's Alembic revision.
- Updated contributor, update-workflow, README and documentation-index routes so maintainers start from current status, architecture overview and the correct owning document.
- A published-duty adjustment now atomically queues every older or possibly delivered Viewer snapshot for revocation, erases any still-queued delivery envelope and decryption key, and returns stable share identifiers for an immediate withdrawal attempt.
- Exact adjustment retries preserve the original revocation receipt and never revoke a newly created current-version share. If edge revocation fails, the committed adjustment remains truthful and the UI tells the operator not to resubmit it; Access control exposes the durable pending count and retries only those withdrawals.
- Clarified that a successful Worker delete receipt is not proof of instantaneous Cloudflare edge invalidation. Zero-overlap handover now uses a fail-closed private-browser check every five seconds for at most ninety seconds, with an independent published-roster withdrawal scenario.
- Updated the Viewer, operator, architecture, security, acceptance, handover and project-status owners for the same lifecycle. Production truth remains the generated live status above until this source candidate is formally released and deployed.
- Made active-risk governance executable: every `Tracked` project risk now resolves to an existing L1／L2／L3 iteration with an owner and closure evidence, while managed／resolved／historical risks cannot masquerade as active work.
- Corrected the stale established-WebSocket risk description. Browser expiry logout is UX and cleanup; server-side page and captured-workflow guards independently reject expiry, revocation, auth-epoch changes and signing-key rotation without introducing a second session owner.
- Promoted encrypted off-device recovery and actual Worker／WebSocket mixed-load evidence into the decision queue instead of burying them in narrative status text.
- Added a narrow off-site recovery service and administrator wrapper that accept only an approved external BitLocker USB／SD target, bind a fresh verified SQLite／manifest handover package to immutable release and path-free digest evidence, publish atomically, and drill an isolated restore from the copied bundle.
- Added fail-closed tests for target evidence, tampering, unsafe archive members, RPO evidence, mandatory release identity, active immutable-bundle execution and the absence of internal-disk／host-bound encryption fallbacks. Export and drill now reject a missing／null release marker instead of emitting or accepting `release: null`.
- Removed the obsolete manual download／copy／rename ZIP path from the Windows host guide; the UI handover package remains available for successor handover but cannot be presented as off-site disaster-recovery evidence. This remains source capability: no real external medium, deployment or replacement-host drill is claimed.
- Split complete-host-loss recovery into one bilingual owner runbook with explicit RPO／RTO, retention, key custody and failure boundaries; release, host, operator, security, architecture and acceptance documents now link to that owner instead of maintaining competing procedures.
- Added a local-only mixed gateway verifier that runs the actual Worker source under Miniflare／workerd, proxies through the real signed-principal and WebSocket path, and exercises fictional Guest／Admin reads, one Admin write, PDFs, backups, outbox and encrypted Viewer delivery without accepting production URLs, data paths or account credentials.
- Pinned Miniflare as an explicit dev-only dependency because the verifier directly owns its API; frozen offline installation, environment scrubbing, loopback validation, structured failure evidence and process-tree cleanup keep it reproducible without changing the production runtime.
- Clean commit `a9ffc9777bcd48fff6e0cfbe21650d5e547750a9` passed 10 simultaneous Guest sessions × 2 waves and 2 Admin sessions; the report observed 22 connected WebSockets and backup `0 → 2`, with balanced fairness, no Guest database write, no cross-session leak, no unhandled lock／5xx and cleanup memory within the bounded stop condition. The launcher validates arguments before loading its optional workerd dependency, reserves distinct loopback ports as one batch, disposes an active runtime on startup failure and closes the SQLite inspection handle. The dated audit closes `ITR-005` while explicitly excluding Cloudflare-edge soak, production SLO and deployment claims.
- Reviewed the existing GSAP Core, timeline, framework, performance, plugin, React, ScrollTrigger and utility choices. No animation dependency or UI rewrite was added because the current single-Core runtime already satisfies the product's motion lifecycle and cleanup contracts; extra frameworks/plugins had no measured product benefit.
- Rejected an initially green formal report after the post-run audit found three tracked component screenshots had been rewritten. Routine browser evidence now goes to ignored `logs/uiverse-components` instead of mutating reviewed visual references.
- Upgraded formal release evidence to schema 3. A candidate must begin clean and preserve the same refreshed runtime fingerprint, file count, commit, tree and clean Git state at every gate boundary and at completion; the first verifier-induced mutation now fails the release even when the functional gate itself passed.
- Windows and Worker deployment preflights now reject old／missing post-check evidence and require both top-level and nested `sourceDirty` values to be actual JSON Booleans. The Worker path also recalculates the current release fingerprint and file count rather than trusting a mutable ignored JSON report.
- The first exact protected-main replay exposed a clock-dependent PDF assertion when the legitimate report-generation timestamp was `18:30`. The regression now fixes that collision explicitly and validates each rendered allocation window and occurrence count instead of searching unrelated document metadata.
- Annotated `v1.2.0-rc.46` at `311ea3d13f67995164fc19f30bb49e0ea5225ae1`／tree `9a6efc028eb42e1f0e67e2f1578e51f1613e771e` produced the 310-file fingerprint `7a5f15830e01a69268bfc366c78cef4c985b6eb861e0248872ecd8ed43174508` and passed all 15 source gates. It remains immutable but undeployed: Windows preflight stopped before any production mutation when 14 post-marker Python cache files made the otherwise healthy rc45 bundle's original full-file marker appear stale.
- Kept executable Python bytecode inside the immutable bundle hash. The rc47 deployer repairs only a legacy post-marker `__pycache__/*.pyc` delta whose exact exclusion reconstructs the original hash and count, removes only that proven set, then reruns the ordinary full fingerprint. New task, rollback and off-site recovery Python invocations use `-B`, preventing recurrence without creating an integrity blind spot.

## v1.2.0-rc.45 — released, 2026-08-01

- Keeps SQLite as the sole local-first roster truth while adding measured composite indexes, bounded history reads, N+1 removal, privacy-safe optional SQL timing and non-blocking backup evidence.
- Adds the bilingual diagnostic-support hero, expanded operator guidance and semantic leave/fairness icon lifecycles without changing policy or Guest isolation.
- Passed all 15 exact-source gates at commit `90777345ea9ed5652c73873edb3c8c846a9ceac5` with 308-file fingerprint `032bf3d5d41a74e6ad50090ab7ffb13af6e5cca43a23c24adb3f8506d6d29a83`.
- Deployed immutable Windows bundle `v1.2.0-rc.45-90777345ea9e-5c891432a1d8`; Alembic `0012`, verified backup `20260801-064628-279309-manual_verified_backup.sqlite3` (`bdf8366aa7b2d3b91d6754dc58d9ec0b6725bf29f7fe3e7d5bf3592b223f69e8`), isolated restore, health, write-readiness and canonical browser smoke passed. Worker source was unchanged and its existing 100% gateway remained healthy.
- Rc43 is not a code-only rollback after migration `0012`; recovery must restore a compatible pre-0012 database through the controlled restore procedure. Supervised human acceptance remains open.

## Historical — post-rc43 release-evidence correction

- Derives the previous origin identity from the scheduled task's actual immutable bundle and verifies its complete content fingerprint before recording a predecessor or rollback commit. Because the identity marker is intentionally outside that content digest, its release, commit, tree and environment fields are now independently bound to the annotated tag published on `origin`, the tag-resolved Git tree, the pre-overlay protected host-environment SHA-256 and the deterministic bundle directory name. A legacy task that still runs directly from `HostRoot` remains supported explicitly.
- Adds `previousReleaseRef` and `previousReleaseSource` to future Windows deployment reports. The already-issued rc43 report remains immutable and retains its known stale `previousCommit`; direct task and marker evidence prove rc41 was the real predecessor and captured rollback target.
- Removes stale rc35／rc39 "current rollback" wording and the obsolete direct-checkout host update instructions from operator documentation. Current production remains rc43 with rc41／Worker `610092f6-59d4-4fd4-ab3a-3fbf1dd2c64e` as the first paired rollback.

## v1.2.0-rc.43 — released, 2026-07-31

- Adds four paired route-family atmosphere systems for weekly work, people/fairness, administration/recovery, and support, plus a same-composition Daily Verse v2 pair. All ten local WebPs are 1600×900, at most 180 KB, stripped of metadata, and governed by an exact prompt/hash/placement manifest.
- Extends `PageDefinition` with one registered atmosphere slot and `embedded | shell` presentation contract. Shared shell bands remain non-interactive and outside tables, forms, names, fairness data, warnings, dialogs, controls, and PDFs; mature heroes do not receive a duplicate image.
- Rebuilds the Daily Verse light surface with warm parchment, dark readable ink, restrained gold, a left reading veil, and 16–20% mobile image strength while preserving the indigo night composition.
- Replaces indiscriminate rotation with a five-control allowlist: Settings, explicit appearance changes, Backup Settings navigation, History, and Undo. Actual restore and other task controls retain truthful lifecycle morphs; verified snapshots use `add_to_drive → arrow_forward → verified` feedback.
- Deepens the tactile inset response for sound and music-autoplay switches without layout movement, and keeps Admin/Guest parity, routes, identity, Session, SQLite, capabilities, and data formats unchanged.
- Passed all 15 exact-source gates at protected-main commit `c8201f33e454d9120c73386642cbf9d737391466`, tree `11f759908218aee64c9d49024759beadf8ff9f5b`, 306-file fingerprint `699dc436c69e02f3b9062a04500715929ba35f78f48e14a3d80a0ac33c18640b`, and annotated tag `v1.2.0-rc.43`.
- Deployed immutable Windows bundle `v1.2.0-rc.43-c8201f33e454-5c891432a1d8` after verified backup `20260731-013103-079514-manual_verified_backup.sqlite3` (SHA-256 `f07306c89e79a610b40105627620c1603b707c39a7ab4cc537217df61c358e1c`) and isolated restore; health and write-readiness passed with no pending obligation.
- Staged Worker `394e2205-ae8f-4eef-a13a-e701931e6f0d` at 0%, passed version-specific health／entrance／Viewer smoke, promoted it to 100%, and repeated independent canonical checks. Rc41 origin and Worker `610092f6-59d4-4fd4-ab3a-3fbf1dd2c64e` are the first paired rollback. Supervised human acceptance remains open.

## v1.2.0-rc.42 — source-only tag, never deployed, 2026-07-31

- Protected tag `v1.2.0-rc.42` points to the same commit and tree later released as rc43, but it was created before the final formal verifier selected and bound `v1.2.0-rc.43`.
- No Windows origin or Worker deployment used rc42. Rc43 is the sole authoritative release identity for this source; rc42 is not a production or rollback target.

## v1.2.0-rc.41 — released, 2026-07-31

- Fixed Admin support submission after the waiting-experience refactor by capturing the browser locale before host-local incident persistence moves to a worker thread.
- Gives the public Admin and Guest entries one shared `idle → starting → navigating → slow／error` lifecycle across desktop and mobile, with role-specific copy, duplicate suppression, delayed progress, safe retry, back-navigation cleanup, and a privacy-safe support reference.
- Adds the truthful Cloudflare sign-in assistance path without a local password database or email-enumeration copy; welcome audio remains a non-blocking trusted-click enhancement.
- Replaces invented 14%／56% operation progress with one phased indeterminate coordinator and a bounded completion morph; measured progress remains available only for real `completed／total` data.
- Adds a delayed, self-cleaning route progress track and moves host-local support-report persistence off the UI event loop while rejecting Guest persistence before loading begins.
- Extends the executable design-token, bilingual, reduced-motion, forced-colour, Worker, accessibility, support and dialog-lifecycle contracts.
- Passed all 15 formal gates against the 298-file fingerprint `cd4344d33f78ba160500a5921382d65e5aece8574a3c0edd1a30b4088ad10186` at annotated tag `v1.2.0-rc.41`／commit `74072b0175ff64807312a8cc5b9cd016b6628210`.
- Deployed the immutable Windows bundle after verified backup `20260730-160630-793049-manual_verified_backup.sqlite3` (SHA-256 `21feb26a1c7ffad17bfd9b74192a8917dfee910f1cbd1e6fa20e0a4c4ffc525f`) and isolated restore; `/healthz` and `/readyz` passed with `writeReady=true` and no pending backup obligation.
- Staged Worker `610092f6-59d4-4fd4-ab3a-3fbf1dd2c64e` at 0%, passed version-specific health／entrance／Viewer smoke, then promoted it to 100% and repeated canonical smoke. Rc40 origin and Worker `2cb38b05-6091-43be-86d3-d9f3ccae1ceb` are the first paired rollback. Supervised human acceptance remains open.

## v1.2.0-rc.40 — released, 2026-07-30

- Completes the semantic icon/action-motion contract and public-entry sound-state verification fixes while retaining the rc39 roster, identity, backup and Worker-runtime behavior.
- Passed all 15 formal gates against the 298-file fingerprint `e4e34ca75c422f823cfeb16e94c72705e1f73b8d56e6b2c6b953e102761a8f4c` at annotated tag `v1.2.0-rc.40`／commit `2ec900a5ef1c021183717dfa648ef76b55452ffb`.
- Deployed to the Windows origin after verified backup `20260730-135505-648220-manual_verified_backup.sqlite3` (SHA-256 `c397478a19e420fc85a22a23e0c245a44b1f59cc2b30cbe9fdfc0f196187b961`) and isolated restore; `/healthz` and `/readyz` passed with `writeReady=true` and no pending backup obligation.
- Retains Worker `2cb38b05-6091-43be-86d3-d9f3ccae1ceb` at 100% because the rc39→rc40 Worker runtime and configuration are unchanged. Canonical entry-music checks and a real Guest Dashboard browser flow passed without console errors.
- Records tagged `v1.2.0-rc.39`／commit `80b9de7ea8abce57b67c6041e580f915a819315e` as the first origin rollback. Supervised human acceptance remains open.

## v1.2.0-rc.39 — released, 2026-07-30

- Preserves the complete rc35 product behavior and R5／R6／R7 controls while correcting Windows scheduled-task credential handling for unattended origin deployment.
- Rotates the dedicated service-account password in memory, uses the same protected credential for task registration and rollback, disposes the secure value, and never writes the password to source, logs, reports or release bundles.
- Passed all 15 formal gates against the 297-file fingerprint `df4a2ecb84f242e24349570d209e95405d7251c85810450ce39cf957427b92b9` at annotated tag `v1.2.0-rc.39`／commit `80b9de7ea8abce57b67c6041e580f915a819315e`.
- Deployed to the Windows origin after verified backup `20260730-065635-724310-manual_verified_backup.sqlite3` (SHA-256 `5876a5ef4cbee6c5573852f454a734c466c5aa17c0bcee8b8faf5c4de8db668c`) and isolated restore; `/healthz` and `/readyz` passed with `writeReady=true` and no pending backup obligation.
- Promoted Worker `2cb38b05-6091-43be-86d3-d9f3ccae1ceb` from 0% staged smoke to 100% traffic. Canonical health, entrance, Viewer and Cloudflare Access fail-closed／OTP checks passed.
- Records tagged `v1.2.0-rc.35`／commit `570e29f745eef7c1995635d1b187021a8fec6ea4` and Worker `d7069f99-81b4-4388-aa28-383b58bfc68f` as the immediate paired rollback. Supervised human acceptance remains open.

## v1.2.0-rc.36–rc.38 — release-tool corrections, superseded by rc39, 2026-07-30

- Corrected the Windows deployment path in successive candidates; stopped each unsuccessful attempt before an unsafe production source or traffic change.
- `v1.2.0-rc.37` is a void protected tag and was never deployed. `v1.2.0-rc.38` passed source verification but stopped safely at the scheduled-task credential boundary and was never deployed.

## v1.2.0-rc.35 — released, 2026-07-29

- Ships the R5／R6 security and recovery controls, unified Light／Dark handoff, and one system-wide semantic icon morph grammar without layout drift, rotation, or competing animation systems.
- Keeps persistent truth ahead of temporary hover/focus previews; synchronizes mobile menu lifecycle with `aria-expanded`; preserves static, reduced-motion, forced-colour, disabled, busy, keyboard and touch behavior.
- Passed all 15 formal gates against the 297-file fingerprint `121302ae68946f43b7eedc93ed0dc9186574f5e42e06551d1fe120263c47e075` at annotated tag `v1.2.0-rc.35`／commit `570e29f745eef7c1995635d1b187021a8fec6ea4`.
- Deployed to the Windows origin after verified backup `20260729-073307-909072-manual_verified_backup.sqlite3` (SHA-256 `f3fb18b53a9f93129d42da71ba47c85c166caf8c9ae8c1289955bf5f103e9c7f`) and isolated restore; `/healthz` and `/readyz` passed with `writeReady=true`.
- Promoted Worker `d7069f99-81b4-4388-aa28-383b58bfc68f` from 0% staged smoke to 100% traffic. Cloudflare Access, rendered desktop/mobile Guest language and theme continuity, mobile menu lifecycle, and Viewer recovery passed with zero console/page errors.
- Records rc34 commit `8fd7ce46095f0b8ad8687bcb01ba60c6a8eab5d2` and Worker `7816b183-3edb-49ca-b39b-a91091ae794f` as the first origin and edge rollback targets. Supervised human acceptance remains open.

## v1.2.0-rc.33–rc.34 — release-tool corrections, superseded by rc35, 2026-07-29

- Made host/Worker release-gate identity comparisons order-independent and safe under Windows PowerShell 5.1 strict mode when no differences exist.
- Both failed attempts stopped before source switching or Worker upload; no production data or traffic was changed.

## v1.2.0-rc.32 — R5／R6 remediation source history, superseded by rc35, 2026-07-29

- Resolves OS-theme changes in place so unfinished forms, focus, scroll and dialogs are not discarded by a page reload.
- Rechecks the verified Admin／Guest principal immediately before every workflow write; an expired long-lived page or WebSocket cannot retain write authority.
- Bounds Guest idempotency receipts to compact metadata with truthful replay markers and explicit per-workspace／global limits instead of retaining full workspace copies per command.
- Parses and re-encodes support PNG files with bounded dimensions／pixels／chunks／output, removing nonessential metadata and rejecting malformed, truncated and polyglot payloads.
- Binds formal release-report schema 2 to clean Git commit／tree／planned annotated tag, exact checks and tool versions; deployment scripts reject stale or source-mismatched reports.
- Rejects unsupported `::1` NiceGUI origin binding and obvious secret placeholders, makes internal-backup workflow fencing explicit, revalidates staged local music before replacement, and adds manual clipboard recovery.
- This section records the earlier working-source stage. The completed protected-main, tag, formal report, backup／restore and paired origin／Worker evidence is recorded under rc35 above.

## v1.2.0-rc.31 — formal source candidate, not deployed, 2026-07-29

- Replaces the primary three-choice appearance selector with one binary **Light／Dark** control across the NiceGUI workbench and public Worker surfaces.
- Keeps `system` only as the missing／unset initialization state: an unset preference follows the operating system, the first activation stores the opposite resolved mode, and later activations alternate explicit Light and Dark.
- Uses the same framed header-control grammar at desktop, tablet and phone widths while preserving separate Admin, Guest and browser-local Worker preference adapters. On deliberate Admin／Guest entry only, the Worker validates an explicit public `light`／`dark` hint staged for at most 120 seconds, carries it inside the signed session and request-bound principal, and clears the staging cookie when the session is minted; NiceGUI adopts it only when the destination preference is unset, so an existing workspace choice always wins.
- Replaces one-pass greedy ordinary-room selection with fairness-ordered deterministic backtracking, daily matching feasibility pruning, and strict non-empty／required-slot／canonical-weight validation. An infeasible week now stops with a controlled no-solution result instead of persisting partial coverage.
- Unifies Admin and Guest generated-file delivery behind bounded, mode-and-session-bound tickets; Guest traffic cannot consume the reserved Admin capacity, and the browser verifies HTTP status and MIME before saving. Defaults keep Guest files at 5 MiB, allow bounded Admin／handover files up to 64 MiB, cap the registry at 128 MiB and reserve 64 MiB plus 16 ticket slots for Admin.
- Synchronizes the mobile navigation drawer, ARIA, inert background and focus return with the actual rendered Quasar state through a cancellable animation-frame settle loop instead of fixed transition delays.
- Makes every business write pass one workflow admission guard. An existing durable recovery marker starts the application in diagnostic-only mode before migrations or database sessions; unfinished backup obligations are repaired or keep all writes fail-closed. `/readyz` now also requires `workflowInitialized=true`, so removing a marker cannot make a diagnostic-only process falsely advertise writable readiness.
- Hardens backup, handover and restore around an exact privately staged database／JSON-manifest pair, rejects SQLite sidecars, malformed manifests, pending obligations and unsupported／future revisions, and migrates only the supported legacy chain from `0007` to the current head in isolation.
- Allows migration `0011_assist_assignment_mode` to downgrade only when persisted history remains legacy-only; any `flexible_weekly` history blocks downgrade.
- Prevents Alembic's logging configuration from disabling the existing privacy-safe application logger, defensively re-enables local logging after migration, and adds a migration-then-log regression test.
- Makes the Windows origin deployer perform a read-only prospective comparison of the protected host `SING_YIN_PORT`, `AUTH_EPOCH`, and `ORIGIN_PRINCIPAL_KID` with the immutable Worker configuration before it mutates the protected environment, stops the service, or switches source. It repeats the comparison after applying the environment and before stopping the service; either mismatch fails closed, and the deployment report records only the non-secret host／Worker identifiers plus `preflightMatched` and `postApplyMatched`.
- Removes fixed verifier credentials from generated Deno source: every gateway case now receives one-use test secrets only through an allowlisted subprocess environment, and the source guard prevents clear-text regression. The general UI verifier now owns theme rendering only, while the dedicated mobile verifier remains the single owner of drawer focus, ARIA, inert background and focus-return evidence.
- Earlier 901／929 Python and eight-case direct Admin／Guest Chromium results remain historical candidate slices. The final release-candidate run on 2026-07-29 passed all 15 gates for the 297-file source fingerprint `7f405269322e67ddc1fdfd5dde004af5079b315725487303fbecd8e1c0954042`, including the complete Python suite, 48 Worker contracts, 16 rendered Public→Admin／Guest theme-continuity cases, desktop／mobile／tablet, write／PDF／fairness／backup／restore, Guest isolation, runtime growth and security checks.
- Keeps the source gate, deployment and supervised acceptance as separate facts. The operational Windows origin／canonical Worker remain provenance-drifted until the protected-main tag and controlled paired rollout complete; the clean rc30＋Worker `11763f08-d40d-46d5-93dc-5ca2599d4154` pair remains the last fully verified rollback baseline.

## v1.2.0-rc.30 — released, 2026-07-27

- Historical deployment topology was the clean `v1.2.0-rc.30` Windows origin with Worker `11763f08-d40d-46d5-93dc-5ca2599d4154` at 100% traffic. On 2026-07-28 the operational origin was found source-drifted and canonical Worker `a2e3ad14-d191-4ffc-85e4-eda40e42e5ed` remained unattributed, so that historical pair is now the last fully verified clean baseline. `11763f08…` is the immediate known verified edge rollback; `d7b51f21…` and rc27 are older edge/origin recovery history.
- Replaced ambiguous language and appearance toggles with destination-language autonyms and explicit **System／Light／Dark** choices across the NiceGUI workbench and public Worker entrance; desktop uses a labelled menu while narrow screens use a full-width three-choice control.
- Kept Admin appearance in the encrypted user preference adapter, Guest appearance in the bounded session-only store, and Public／Viewer appearance in browser-local storage; changing appearance remains in-place and does not cross identity or storage boundaries.
- Added browser contracts for 256／320／390px phone reflow, 44px touch targets, keyboard and screen-reader state, locale／appearance isolation, reduced motion and rendered light／dark states.
- Added a clearly qualified **≈10B AI tokens processed** creator-level engineering fact, rounded from the supplied 2026-07-27 cross-tool screenshot (9.38B); it is not live product telemetry and does not imply that student data is sent to AI services.
- Carries the rc29 PowerShell 5.1 deployment-inventory correction and rc28 default-music entry behavior forward unchanged.
- Passed all 14 rc30 candidate gates against the 296-file source fingerprint `15d155d8d745b14b574b08d793150c93aa77946e7d17a63030844c44adededbc`: 894 Python tests, 3 motion contracts, 46 Worker contracts, adaptive browser matrices, isolation, write／PDF／backup／restore and partial-backup recovery.
- Deployed annotated tag `v1.2.0-rc.30`／commit `74b84f43786b00feb15b51a6270ff71c9430773f` to the controlled Windows origin after verified backup `20260727-023041-069097-manual_verified_backup.sqlite3` (SHA-256 `6e2f44d2e577389d19de2feb5dd0a36260794ef2188551d6f604e46b7ac74e1b`) and isolated restore, then promoted Worker `11763f08-d40d-46d5-93dc-5ca2599d4154` through 0% version smoke to 100% traffic and passed canonical rendered desktop／320px／Guest Engineering checks.

## v1.2.0-rc.29 — live Worker, 2026-07-27

- Corrected the controlled Worker deployer for Windows PowerShell 5.1, which represented Wrangler's top-level secret JSON array as one nested object and falsely reported every configured secret as missing.
- Added a direct Windows PowerShell 5.1 regression test for multi-entry secret inventory parsing. The deployer continues to validate names only and never reads or records secret values.
- Carries forward the rc28 default-music identity-entry fix unchanged. Worker `d7b51f21-7692-418d-866c-034c2c57292d` passed staged smoke and now serves 100% traffic; the source-identical `v1.2.0-rc.27` Windows origin remains live.
- Verifies the canonical public entrance, 12-case music／entry matrix, real Guest session and logout, Cloudflare Access Administrator handoff, silent Viewer and non-cacheable health response. rc26 is the first-level origin rollback; previous Worker `76a23134-8355-4e25-bbba-abf17c6918c5` remains the immediate gateway rollback.

## v1.2.0-rc.28 — candidate, 2026-07-27

- Made Administrator and Guest identity buttons the trusted default-music activation when no entry-sound preference was selected; users no longer need to choose a sound option before either route works.
- Added one shared visit-local `unset | music | quiet` entry controller with duplicate suppression, exact same-origin destinations, 450 ms fallback, truthful failure classification, late-settlement protection and `pageshow` reset.
- Kept **Default: Enter with music** and **Continue quietly** as optional recovery／preference controls, while preserving explicit volume values, silent encrypted Viewer pages, manual YouTube playback and existing authentication boundaries.
- Added deterministic Worker contracts and a real Chromium desktop／mobile interaction verifier for playback rejection, synchronous failure, pending startup, keyboard entry, explicit quiet, already-playing audio, rapid double activation and silent Viewer behavior.
- This entry records a candidate until protected-main release and canonical Worker deployment evidence are complete; rc27 remains the live rollback source during staging.

## v1.2.0-rc.27 — 2026-07-27

- Made flexible Assist rotation follow the latest earlier active roster across holiday or skipped-week gaps in both official and browser-only Guest workflows.
- Preserved fail-closed backup recovery while allowing later independent obligations to repair after one record-specific failure.
- Replaced the workflow wildcard dependency surface with explicit imports and exports, and removed the retired `backend` pytest path.
- Made same-client page-context composition atomic, retained an explicit Guest import denial, and surfaced weekly preview read failures through the existing bilingual support-reference boundary.
- Reconciled R2 findings with Deepseek R3/R4 evidence, documented operator-facing environment overrides, and corrected rc25/rc26 history and the 14-gate operator guide.
- Deployed the immutable rc27 origin after 14／14 source-matched gates, a verified backup and isolated restore; the unchanged rc24 Worker remains canonical and rc26 is the first-level origin rollback.

## v1.2.0-rc.26 — 2026-07-26

- Stabilized the release browser verifier on semantic platform-section and test-ID contracts in both languages.
- Recorded the exact rc26 Windows origin, unchanged rc24 Worker, backup, isolated restore, and canonical smoke evidence without implying supervised human acceptance.

## v1.2.0-rc.25 — 2026-07-26

- Replaced the invented “Study Prefect Systems & Stewardship Office” identity and corporate-style responsibility titles with the real `Study Prefect Team／導學風紀組`, plain work areas, and direct responsibility descriptions.
- Removed residual “organisation chart” and “capability map” language from current architecture and design documentation so presentation structure cannot be mistaken for a real school department.

## v1.2.0-rc.24 — 2026-07-26

- Kept Public and Viewer problem reports browser-only while routing authenticated Admin and Guest `/support` visits to the shared NiceGUI support workspace.
- Restored the Admin host-local, explicit-consent incident inbox on the canonical remote site without weakening Guest non-persistence or the public no-upload boundary.
- Added Worker regression coverage for Public, Admin, and Guest support routing through the signed origin-principal boundary.
- Deployed the immutable rc24 pair to the controlled Windows origin and canonical Worker after 14／14 exact-source gates, a verified backup, and an isolated restore.
- Verified Public browser-only support, Guest NiceGUI support, Viewer recovery, language switching, desktop and 390px mobile rendering without console or page errors; supervised human acceptance remains separate.

## v1.2.0-rc.23 — 2026-07-26

- Added one progressive `/support` flow for Admin, Guest, Public, and Viewer contexts.
- Added an explicit-consent, bounded, redacted, integrity-hashed host-local Admin support inbox with lifecycle cleanup and read-only inspection tooling.
- Kept Guest, Public, and Viewer reports browser-only, non-persistent, and outside roster transactions, official SQLite, fairness, backups, and external queues.
- Added a redacted Windows host-security summary for maintainers without exposing secret values.
- Distilled repeated page titles, generic introductions, nested explanations, and permanently visible secondary actions while retaining policy, consequence, recovery, and trust evidence.
- Added executable content-design, support-threat, repository-hygiene, bilingual, and Worker no-network/no-storage contracts.
- Updated the operator, architecture, security, Viewer, Guest, Cloudflare, acceptance, handover, and release documentation for the same support boundary.

## v1.2.0-rc.22 — 2026-07-26

- Versioned the design contract as Luminous Sacred Precision 1.3 while preserving opaque operational, roster, fairness, warning and PDF surfaces.
- Added governed luminous-edge, woven-line, transient-material and operational-material tokens for light and dark modes.
- Replaced hidden first-interaction audio retry with an explicit browser-policy recovery choice: **Enter with music** or **Continue quietly**.
- Added a shared workbench audio controller that reports resolved playback, browser blocking, loading, transport, decoding, lifecycle, paused and off states without duplicate listeners.
- Preserved the 50% browser-local default, every explicit operator-selected volume and exact-only migration of legacy 24%／35% workbench defaults.
- Kept encrypted Viewer pages silent and YouTube／imported media manual.
- Added focused Worker, Python and browser contracts for the new state and recovery behavior.
- Separated the workbench controller runtime from the local music catalogue URL space so the browser receives the controller instead of a 404 response.

## v1.2.0-rc.21 — 2026-07-26

- Deployed the four-zone product information architecture and centralized page catalog to the controlled Windows origin.
- Retained Worker `f780feb2-671a-4feb-b6f6-b7f9d5b31e89`; completed verified backup, isolated restore and canonical smoke. See `PROJECT_STATUS.md` for exact evidence and remaining supervised acceptance.
