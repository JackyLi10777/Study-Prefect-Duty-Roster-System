# Changelog

This file records user-visible, operational and release-significant changes. Exact deployment evidence remains in `PROJECT_STATUS.md` and the generated release reports.

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
