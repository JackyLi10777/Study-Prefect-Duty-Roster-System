# Changelog

This file records user-visible, operational and release-significant changes. The editable authority for observed deployment truth is `docs/status/current-release.json`; `docs/status/CURRENT_STATUS.md` is its generated, human-readable view and must not be edited by hand. Immutable historical evidence remains in `PROJECT_STATUS.md`, dated audits and generated release reports.

## Unreleased — maintainability and documentation governance

- Added a concise architecture overview and an executable import-direction contract for policy, core, persistence, workflow services and UI.
- Added one machine-readable current-release source plus deterministic Traditional Chinese／English status generation for all operator-facing guides, eliminating manual release-identity drift.
- Added a documentation lifecycle／ownership manifest, ADR register and decision-relevant iteration register; every maintained Markdown file now has a lifecycle class or declared collection.
- Added `scripts/project_governance.py --check／--write` and integrated the check into adaptive verification profiles. It validates status schema, generated blocks, local links, topic owners, document coverage and architecture boundaries.
- Kept secret scanning fail-closed while recognizing only the three schema-bound public provenance digests in the live status JSON; arbitrary high-entropy fields, paths or candidate states still fail review.
- Hardened review boundaries against relative-import bypasses, invalid-state generation, unresolved maintenance／recovery obligations, collection link drift and database snapshots incompatible with a rollback target's Alembic revision.
- Updated contributor, update-workflow, README and documentation-index routes so maintainers start from current status, architecture overview and the correct owning document.

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
