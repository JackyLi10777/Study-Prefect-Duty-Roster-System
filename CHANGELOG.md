# Changelog

This file records user-visible, operational and release-significant changes. Exact deployment evidence remains in `PROJECT_STATUS.md` and the generated release reports.

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
