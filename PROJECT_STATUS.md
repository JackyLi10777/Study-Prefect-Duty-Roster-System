# Sing Yin Study Prefect Duty Roster System - Project Status

**Last Updated:** 2026-07-12  
**Project Root:** `D:\code_v3`  
**Current Phase:** First-release feature completion; ready for formal supervised acceptance testing  
**Primary Theme Color:** `#0F766E`

**Repository:** `JackyLi10777/Study-Prefect-Duty-Roster-System`  
**Branches:** `main` (current), `nicegui-self-hosted` (platform snapshot), `streamlit-cloud` (legacy reference)

**Co-creators:** LI Chuangjie Jacky（李創杰）and Codex only. `Study Prefect Systems & Stewardship Office` is their two-member project identity; no additional developer or contractor contributed to this NiceGUI rebuild and formal release.

## Project Overview

This is a fresh, local-first rebuild of the Sing Yin Study Prefect Duty Roster System. It runs on the local computer through NiceGUI. A future dedicated host may use Cloudflare Tunnel only after Cloudflare Access and a teacher-approved security decision; external exposure is not currently authorized or configured. It is not a migration of the Streamlit, `demo_code`, or `demo_code2` applications.

The current Head Study Prefect is the normal daily operator. The teacher advisor mainly reviews published results, fairness, recovery, and handover evidence after completion rather than operating the weekly workflow day to day.

Guiding principle:

> **非以役人，乃役於人**  
> **Not to be served, but to serve**  
> Mark 10:45

The principle shapes the Dashboard devotional space, fairness ledger, leave-adjustment tone, and leadership language.

## Current Status

The NiceGUI application now has a durable roster workflow and a unified multi-page operating structure. The latest refinement adds a fully isolated Practice Mode so a successor can rehearse the complete workflow with fictional Chinese names without opening official SQLite, backup, log, or preference state.

## Completed Work

### Foundation

- Canonical devotional source: 121 polished entries in `data/devotional/daily-verses.seed.json`.
- Expanded 500-entry devotional export and legacy trace source retained.
- Mark 10:43-45 remains foundational with `dashboard-hero` and `roster-generation` special use.
- Realistic Traditional Chinese demo prefect data: 24 fictional Hong Kong boys' secondary-school prefects.
- Official school badge integrated into the Dashboard devotional space.

### NiceGUI Application

- Created official runtime package: `nicegui_app/`.
- Added multi-page navigation: Dashboard, Roster workspace, Prefects, Fairness Audit, Daily Verse, Settings.
- Consolidated Roster into two tabs: Generate & View, and Adjust & Edit.
- Consolidated Prefects into two tabs: Directory and AI Import.
- Added Traditional-Chinese-first i18n registry with English counterpart labels.
- Standardized official Hong Kong written role terms across the interface, PDF, import template, and handover material: 首席導學風紀 / Head Study Prefect, 助理首席導學風紀 / Assistant Head Study Prefect, and 導學風紀 / Study Prefect.
- Added persistent light/dark preference through NiceGUI user storage.
- Replaced display-string language detection with explicit locale state and added a registry test requiring every interface key to provide Traditional Chinese and English text.
- Added a dignified teal-and-gold Daily Verse hero using the canonical `dashboard-hero` daily rotation.
- Added a persistent bilingual Practice Mode identity in both themes and at phone width. The state is textual and semantic rather than colour-only, and remains visible across every page.

### Prompt and Skill Governance

- Rewrote `CODEX_PROMPTS.md` around the current NiceGUI runtime, real Head Study Prefect operating moments, adaptive decision scaffolding, and handover evidence.
- Updated all four active `sy-*` skills to remove stale Streamlit/reference-app guidance and align them with SQLite persistence, verified restore, pre-generation leave, bilingual UI, and successor handover.
- Consolidated the absent `sing-yin-coach-*` concepts into named work modes rather than creating overlapping skills.
- Added `docs/SKILLS_OVERVIEW.md` and a current-runtime skill drift audit for repeatable maintenance.

### Professional Design Direction

- Added `Professional_Design_System.md` as the active source of truth for the original Apple-inspired, non-liquid-glass visual language. It records the current design diagnosis, Weekly Pulse signature, token roles, type, surfaces, motion, accessibility gates, implementation phases, and governance for future UI work.
- Added two original, non-identifying atmosphere assets for the Daily Verse and Weekly Pulse workbench only. Solid readability layers, dark-mode opacity rules, and no-table/no-button/no-PDF restrictions keep imagery supportive rather than template-like or distracting.
- Refined interaction feedback across primary buttons, active workflow cards, Daily Verse, and the workbench: brief hover/press responses, one-time current-step entry, and reduced-motion support provide tactile polish without persistent animation.
- Added a calm bilingual progress treatment for long local operations. Generate, publish, manual draft changes, published-duty leave adjustment, import, PDF export, handover packaging, and restore now make the safe processing stage visible, block duplicate clicks, and keep SQLite/fairness work off the UI event loop.
- Extended that nonblocking boundary to pre-generation leave declaration/cancellation and prefect creation/update/archive. Predictable missing prefect fields are repaired before any transaction starts, while archive now requires a bilingual confirmation explaining historical retention and the absence of immediate undo.
- Expanded the original local atmosphere system with paired light/dark assets rather than one-size-fits-all backgrounds. Daily Verse now has an intentionally distinct sacred reading language—deep indigo, parchment/gold, serif scripture, protected reading space, and theme-specific window atmosphere—while Handover uses a separate quiet archive language and first-use onboarding uses a prepared-study-desk language. Generated artwork contains no people, student data, text, logos, or school crest and is limited to non-sensitive contextual surfaces.

### Persistence and Workflow

- Added SQLAlchemy 2 and Alembic migration `0001` for SQLite storage.
- Added persistent prefects, availability, roster weeks, assignments, fairness ledger, leave adjustments, audit events, and backup runs.
- Added automatic seed import on first startup.
- Added a GitHub handover model that preserves the original Streamlit Cloud commit on `streamlit-cloud`, publishes the maintained NiceGUI release on `main` and `nicegui-self-hosted`, and documents the mapping in both README languages. A guarded archive builder includes fictional SQLite, privacy-safe release logs, screenshots, built-in music, and checksums while refusing any operational roster, leave, fairness, publication, or adjustment rows.
- Added an outer application-mode boundary and two Windows entry points: `START_PRACTICE_MODE.cmd` opens a fully isolated fictional workspace, while `RESET_PRACTICE_MODE.cmd` safely clears only `data/practice/` after refusing a live practice service. Practice PDFs repeat their non-official identity in the filename, document body, and page footer; `/healthz` lets launchers distinguish official and practice processes without exposing roster content.
- Generate workflow automatically saves or replaces a weekly draft; it does not change fairness weights.
- Added a compact, expandable data-lifecycle explanation directly above the roster workspace: it makes the draft-not-posted, publish-once, audited leave-transfer, and verified-backup boundaries visible without crowding the operational form.
- Publish workflow validates again, posts assignment weights exactly once, and updates persistent `history_weight`.
- Post-publication leave adjustment transfers or removes assignment weight transactionally and records audit evidence.
- Pre-generation leave declarations are persistent weekly constraints: the generator excludes the declared prefect on that day, and drafts can be regenerated safely.
- Publish revalidates current pre-generation leave declarations. A draft made before a new leave declaration is rejected until regenerated.
- A published week rejects pre-generation leave changes so the existing post-publication adjustment and fairness-ledger workflow remains authoritative.
- Every generate, publish, and adjustment creates a SQLite online-backup snapshot plus manifest.
- Backup manifests include SHA-256 checksums; the service verifies SQLite integrity and required schema tables before a snapshot is trusted.
- Backup verification now also compares the actual snapshot SHA-256 against its manifest, so a missing, unreadable, or tampered manifest cannot be presented for managed restore.
- Fixed the post-commit backup-failure boundary across every durable write. The workflow now raises `CommittedWriteBackupError` only when SQLite data is already durable; NiceGUI shows a persistent bilingual no-retry recovery dialog, records a privacy-safe partial outcome, and offers reload/review or Settings. Settings can now create an operator-requested snapshot that is checksum- and SQLite-verified without changing roster or fairness data.
- Settings can create a confirmation-gated, memory-only verified handover ZIP containing exactly the latest verified SQLite snapshot, its manifest, and bilingual recovery notes. It is never uploaded, automatically encrypted, or retained as a second local data copy.
- A persistence test proves a generated snapshot can bootstrap an independent workflow with its draft and assignments intact.
- Settings now offers guided restore from verified managed snapshots. Restore creates a `pre_restore` safety snapshot, replaces the live database atomically, reconnects the runtime, and records an audit event.
- Added Prefect CRUD: create, update, and archive without deleting historical roster evidence.
- Added local AI-prepared JSON/CSV import preview and validation; student data is not sent to an external model.
- Reworked local PDF export around the approved group-sharing layout: one horizontal A4 weekly matrix with duty positions at left, weekdays above, and Chinese prefect names in the cells. Separate Chinese and English schedule downloads change labels only; prefect names remain Chinese in both. The named fairness ledger is now a clearly marked, portrait A4 internal-audit PDF rather than a second page sent by default.
- Centralized Professional Teal visual tokens were tightened for the final workflow: calmer surface hierarchy, consistent card radii, keyboard focus visibility, and explicit light/dark table and export-option contrast.
- Added a publish-confirmation dialog so a Head Study Prefect must acknowledge the fairness-ledger consequence before releasing a roster.
- Added a Fairness Audit explanation and a live Handover Guide that shows active prefect, roster-history, and verified-backup readiness for a successor.
- Added a novice-friendly start path: `START_SING_YIN_ROSTER.cmd` launches the local app and opens a browser; the dashboard and a persistent 「開始使用」 page give the first three safe steps and direct links to Prefects, Rosters, and the Handover Guide.
- Hardened the double-click start path with a dedicated PowerShell launcher and Windows mutex: it reuses an existing Sing Yin service, serializes simultaneous launches, chooses a free localhost port when 8080 is occupied, waits for an HTTP readiness response before opening the browser, and avoids slow HTTP timeouts on unrelated TCP listeners.
- Added concise bilingual 「操作提示」 at the decision point for roster generation, published-duty absence adjustment, draft changes, directory management, bulk import, fairness review, and system settings. Each prompt states its purpose and the safe action sequence without creating a crowded separate tutorial layer.
- Added operator-facing workflow completion inspired by the reference application's useful operating ideas: one-click verse refresh, a local fictional CSV template download, generation-time post/vacancy preview, a complete bilingual in-app Operator Guide, safe auditable manual draft changes, and an explicit post-publication leave-adjustment callout. These preserve the NiceGUI/SQLite workflow rather than copying the old Streamlit code.
- Redesigned the Dashboard as a human-centered weekly workbench: its primary visual hierarchy is now the real operational pipeline—Generate draft, Review/export, then published-duty absence adjustment—while the Daily Verse remains a compact dignified companion. The active next step is highlighted from current roster state.
- Replaced generated workflow imagery in the active interface with one consistent local Material icon system: the navigation, three-stage workflow, onboarding, and PDF choice now use mature semantic symbols with shared sizing, stroke weight, and state treatment. The prior original raster studies remain local project assets only and are no longer used as interface icons.
- Reoriented the visual layer to a modern Apple-inspired system language: grouped neutral surfaces, system-blue primary actions, solid navigation surfaces, generous rounded cards, restrained depth, and clear light/dark hierarchy. Teal remains the school theme colour for identity and stable/success states rather than being applied to every interaction. It is an original implementation and does not use Apple trademarks, assets, copied screens, or liquid-glass effects.
- Reordered the Dashboard around one current action: its three workflow stages are now an accessible ordered list, with the active stage visibly grouped and the completed/future stages quieter. Icons are decorative while text buttons remain the only duplicate-free action target; the devotional reflection is available in an accessible disclosure so the Daily Verse remains prominent without making the home page crowded.
- Added `.env.example` (loaded at startup) and `docs/RELEASE_HANDOVER.md` for managed localhost session-secret behavior, future server-only environment secrets, CJK PDF font fallback, backup procedure, Cloudflare Access decision gate, and formal acceptance testing.
- Added privacy-conscious rotating local support logs in `logs/app.log`. Consequential UI actions now record only a generated support reference, controlled action name, outcome, duration, exception type, and code location—never form values, Chinese names, leave reasons, roster rows, or PDF content. Operator-facing failures remain bilingual and provide the reference without exposing a raw implementation exception.
- Fixed NiceGUI favicon delivery by supplying the real local logo file rather than a static URL. Isolated HTTP verification now proves both `/` and `/favicon.ico` return 200, and browser smoke coverage guards the favicon response.
- Repaired stale browser assertions left from the earlier devotional component and added a mobile layout assertion requiring Daily Verse to appear before the weekly workbench. Refreshed 390px evidence confirms the intended reflection-first workflow order.
- Rebuilt `README.md` as a bilingual operator-and-advisor entry point, with safe daily launch, first setup, workflow summary, documentation map, verification boundary, and an explicit distinction between local use, Cloudflare Access remote access, and true cloud hosting. Added `docs/DEPLOYMENT_DECISION.md` so an external-access decision is documented before any connector, DNS, or student data changes.
- Added `scripts/verify_nicegui_write_pipeline.py`, a release-level browser workflow that refuses to run without explicit temporary database, backup, and log paths. It drives fictional Chinese data through import, leave, draft generation, a safely rejected missing-reason change, audited manual correction, publish-once ledger posting, both schedule PDF downloads, eligible post-publication substitution, verified handover package, and restore into a second isolated database. The flow uncovered and fixed an error-reference formatting bug that previously masked a safe `OP-...` failure message with `KeyError: 'reference'`.
- Replaced the phone-width roster's clipped desktop table with a calm, day-grouped duty-card presentation. Each card keeps the post, time, Chinese name, status, and workload together; desktop retains the full verification table. Both are built from one localized display model, so responsive presentation cannot silently show a different roster.
- Extended the same responsive rule to the Prefect Directory: phone-width identity cards now retain Chinese name, form/class, role, availability, workload, and duty count together, while the desktop comparison table remains intact. Reworked published-duty leave adjustment into visible assignment, substitute, and reason steps with full-width mobile controls; an empty reason receives a local, focused correction prompt before any workflow write is requested.
- Upgraded local diagnostics beyond the demo reference: `logs/app.log` now has privacy-safe event records, configurable local retention, optional live console feedback, `OP-...` operation references, generated `REQ-...` HTTP traces returned as `X-Request-ID`, process/thread/asyncio exception capture, and a read-only `scripts/inspect_support_log.py` lookup tool. Windows browser-transport reset codes 64/10054 are recorded as informational local disconnects; all other uncaught asyncio failures remain critical and are delegated instead of hidden. HTTP entries record only method, safe route category, status, duration, and exception type—never paths with user input, query strings, names, leave reasons, roster rows, or PDF content.
- Added a fuller first-use and handover layer without weakening the operating workflow: the expanded bilingual in-app guide now covers safe startup, directory/import, pre-generation leave, draft edits, publish/PDF, published-duty absence, support references, backup, and handover. A new non-sensitive 「系統架構與共創 / System architecture & co-creation」 page explains the real UI → policy/core → transactional workflow → verified recovery → handover boundaries, and records the collaboration between 李創杰 and Codex as the Study Prefect Systems & Stewardship Office project team.
- Added two original light/dark paired atmosphere sets for only the sidebar and system-architecture header. Solid readability veils, explicit mobile crops, and browser assertions keep the images contextual; tables, forms, warnings, names, fairness records, controls, and PDFs remain image-free.
- Retained the three user-supplied crest masters at project root and created semantic delivery assets under `nicegui_app/assets/brand/`: a 512×512 favicon, the supplied 545×524 navigation crest, a 640-pixel web display crest, and the full 5983×5751 print crest. Browser UI no longer decodes a print master for a small mark; PDF export still uses the full source.
- Unified fine-pointer hover feedback across the interface: buttons rise by 1px, navigation and expansion headers shift by at most 3px, and selected non-sensitive contextual surfaces rise by 2px with a restrained pointer-local light. The enhancement is hydrated safely for dynamic NiceGUI content, leaves tables/names/warnings/fairness data still, uses real pointer/not-allowed cursors, and removes transforms plus pointer light under `prefers-reduced-motion`.
- Rebuilt atmosphere theme selection around seven semantic light/dark image slots. Every enabled background uses the same component selector, crop, mask, and DOM position in both themes; only a `--sy-image-*` variable changes from its `*-light-v1.webp` file to the matching `*-dark-v1.webp` file. The 14 active files now total about 1.13 MB instead of about 27 MB of PNG data.
- Added a formal localhost deployment profile, fail-closed future server profile, `/healthz` readiness endpoint, SQLite integrity signal, and `scripts/check_deployment_readiness.py`. Both modes refuse non-loopback binding; future server mode represents a same-host Cloudflare Tunnel origin and refuses startup until explicit remote authorization, Protect with Access, a valid Access team domain, audience, public hostname, independent secret, and Host allow-list exist.
- Fixed the managed NiceGUI storage-secret read race found during Practice Mode verification. Both the exclusive-create loser and the already-visible-file path now wait through the same bounded write/fsync window; corrupt persistent state still fails closed. The 24-reader concurrency test passed five consecutive focused runs before the final suite.
- Added opt-in semantic interface sounds and local page music with operator-controlled volume, sequential/shuffle progression, first-use guidance, and no autoplay. Sounds confirm state rather than decoration and do not enter roster data or audit records.
- Added the chosen online-music path: a fully visible, privacy-enhanced YouTube control window for saved public playlists. Public playback needs no login, payment, or API key; optional `SING_YIN_YOUTUBE_API_KEY` adds public search only. With no saved playlist, no iframe or third-party request is created. Playlist state is local, ignored by Git, and excluded from roster, fairness, PDF, backup, and advisor-review data.
- Rebuilt the non-sensitive system-architecture page as a truthful product showcase rather than a vanity dashboard. A six-stage service lifeline explains prepare → draft → publish → export → adjust → handover; the existing five ownership layers are now framed by four durable trust-evidence cards, nine bilingual FAQ items, and a complete Codex co-creation closing note. Desktop, tablet, and phone use different readable grid arrangements without changing content order.
- Added an original same-composition architecture-lifeline image pair under the atmosphere asset contract. Both 1600×900 files show the same six archival stations and crop; light mode uses morning paper/wood while dark mode changes lighting and palette only. They contain no people, text, student data, logo, crest, trademark, or fake interface, and the HTML service explanation remains independently readable.
- Expanded `README.md` with current NiceGUI → workflow → core/policy → SQLite/recovery Mermaid diagrams, a real roster lifecycle state machine, five-layer responsibility/evidence table, nine operational FAQs, and a bilingual co-creation conclusion. Legacy Streamlit, GitHub student-data, PDF-embedded-backup, and AI-service claims were deliberately not inherited.

### Policy Coverage

- AHPs can only be assigned to `Assist. in charge`.
- Room 302: one prefect, Monday-Friday, 15:45-18:00.
- Room 303: two prefects, Monday-Friday, 15:45-17:00.
- Room 202: two prefects, Monday/Wednesday/Thursday only, 15:45-17:00.
- No duplicate same-day duty and no consecutive-day duty.
- Weights: Assist. in charge and Room 302 = 1.0; Room 303 and Room 202 = 1.5.
- Lower persistent `history_weight` receives higher priority.

### Verification

- `pytest`: 193 passing tests, including official/practice path isolation, guarded single-file public-archive generation, fictional SQLite zero-row enforcement, current GitHub branch/documentation contracts, launcher/reset contracts, bilingual semantic mode identity, practice PDF marking, mode-aware health, and the established policy, workflow, persistence, PDF, backup, i18n, responsive, logging, deployment, repository-hygiene, music, architecture, and accessibility coverage.
- Practice Mode browser verification passed against `data/practice/e2e/` only. It verified `applicationMode=practice`, a persistent bilingual text banner, distinct readable light/dark treatments, 390px normal-flow layout, clean console, and refreshed screenshots under `output/playwright/practice-mode/`; the isolated database, backups, logs, and storage secret were then removed after a resolved-path boundary check.
- Release candidate passed all 8/8 gates across the complete release-sensitive source set: repository hygiene, 193 tests, Python compilation, dependency integrity, full NiceGUI browser smoke, fictional-data write/PDF/restore pipeline, strict deployment readiness, and partial-backup recovery. The current fingerprint and file count are recorded in `logs/release-candidate-report.json`; both Practice Mode launch wrappers are included in that staleness boundary.
- Double-click launcher verification passed: the real `.cmd` entry point returned exit code 0 while reusing an existing local service; an occupied test port moved the application to the next free port, reached HTTP 200, opened the exact URL, and a second launch reused that port without creating another NiceGUI process. Test processes were stopped after verification.
- Full write-pipeline browser verification passed against temporary SQLite, backup, and log paths. It verified fictional Chinese import, Tuesday week-start repair, no-write missing leave/draft reasons, declared leave exclusion, auditable manual draft change without fairness mutation, one-time 34.0 workload publication, Chinese/English landscape single-page PDFs with Chinese names, eligible published-duty replacement, audit/manifest evidence, verified handover ZIP, managed restore into a second isolated database, console cleanliness, and fresh desktop light/dark/mobile screenshots. At 390px it confirms roster cards, phone-directory identity cards, no clipped desktop tables, and full-width adjustment actions.
- Browser smoke check verified HTTP 200 favicon delivery, paired Daily Verse, Handover, and onboarding light/dark background selection, sacred Scripture contrast, concise operation hints, the roster data-lifecycle disclosure, confirmation-gated handover backup package, pre-generation leave and backup restore, bilingual switching, light/dark mode, console cleanliness, refreshed screenshots, and a measured mobile assertion that Daily Verse precedes the weekly workbench. The visible progress dialog remains covered through an isolated temporary SQLite database.
- The isolated browser smoke check additionally verified the new system-architecture route and five real system layers, detailed bilingual guide entry, light/dark paired sidebar and architecture backgrounds, dark-mode contrast, stacked architecture layers at 390px, favicon delivery, and a clean browser console. It ran against a temporary SQLite database, backup folder, and log folder; the temporary server was stopped after the check.
- The crest browser check verifies byte-for-byte favicon delivery from the 512×512 browser asset, the 545px navigation PNG at its actual 60×58 mark, and the 640px web display PNG in the co-creation area; the separate 5983px print master remains covered by PDF tests.
- The 2026-07-12 isolated browser smoke passed after the YouTube integration. It verified the visible music panel and guidance, proved an empty setup creates no iframe, checked the online settings status, reran Traditional Chinese/English, light/dark, desktop/mobile, reduced-motion, theme-paired imagery, favicon, local audio, and console gates, and used only temporary SQLite, backup, and log paths.
- The 2026-07-12 complete write-pipeline browser run also passed in the same isolated environment after the media changes: fictional Chinese import, pre-generation leave, auditable draft correction, single fairness posting, both landscape PDFs with Chinese names, published-duty adjustment, verified manifest/handover package, and managed restore into a second isolated database remained correct.
- The 2026-07-12 architecture-showcase browser run passed against fresh temporary SQLite, backup, and log paths. It verified six ordered service stages, five ownership layers, four trust-evidence cards, nine FAQ disclosures including one real expanded answer, the Codex closing note, same-position light/dark lifeline artwork, three-column 1440px composition, vertical 390px sequence, paired theme imagery, English parity, reduced motion, clean console, and refreshed desktop light/dark plus architecture-mobile screenshots.
- The isolated committed-without-backup browser drill passed with a deliberately blocked backup path. It proved the draft and all 26 assignments were committed once, the failed backup run was recorded, the UI said not to retry and displayed one OP reference, the Settings recovery action was discoverable, and a repaired path produced one verified manual snapshot and success record without console errors.
- All active `sy-*` skills pass frontmatter validation; the current skill drift audit reports `OK`.
- Persistence tests cover draft replacement, automatic backups, publish-once fairness posting, and leave-adjustment weight transfer.
- Prefect tests cover create, update, archive, and Traditional Chinese CSV import normalization.
- Browser smoke check verifies core routes, Roster/Prefects tabs, AI import preview, bilingual switching, dark mode, console errors, and screenshots.

## In Progress

- Continuous refinement Round 13 completed: the operator guidance, non-sensitive contextual imagery, readable school mark, and architecture/co-creation explanation now make the system easier to approach and hand over without turning the roster workspace into a decorated dashboard. The next highest-value internal task is a release-readiness audit of documentation consistency, startup/recovery evidence, and accessibility acceptance criteria before formal supervised acceptance testing.
- Continuous refinement Round 14 completed: official school identity assets now have explicit favicon, navigation, display, and print ownership, and the obsolete universal root logo has been removed. The next highest-value internal task remains the release-readiness audit of documentation consistency, startup/recovery evidence, and accessibility acceptance criteria before formal supervised acceptance testing.
- Continuous refinement Round 15 completed: mouse hover, pointer glow, navigation response, disabled cursor, keyboard focus, touch behavior, and reduced-motion fallback now form one restrained interaction language. The next highest-value internal task remains the release-readiness audit of documentation consistency, startup/recovery evidence, and accessibility acceptance criteria before formal supervised acceptance testing.
- Continuous refinement Round 16 completed: all enabled contextual backgrounds now obey one semantic-slot/two-theme-assets contract, including the newly paired Weekly Pulse workbench. The next highest-value internal task remains the release-readiness audit of documentation consistency, startup/recovery evidence, and accessibility acceptance criteria before formal supervised acceptance testing.
- Continuous refinement Round 17 completed: localhost deployment now fails safely, health and readiness can be checked without opening the UI, and remote-host prerequisites are documented but not enabled.
- Continuous refinement Round 18 completed: the chosen YouTube experience is a free, visible, operator-controlled playlist window with optional API search, bilingual guidance, responsive styling, no autoplay, and no roster-data coupling. The documented role split keeps the Head Study Prefect as the routine operator and the teacher advisor as the main post-completion reviewer.
- Continuous refinement Round 19 completed: the architecture/brand showcase now exceeds the useful information depth of the reference README while describing only the active NiceGUI system. Its signature service lifeline, paired imagery, trust evidence, FAQ, responsive layouts, and co-creation closing form one coherent, inspectable handover story rather than copied technical spectacle.
- Continuous refinement Round 20 completed: five successive passes covered accessibility, repeated-operation safety, image delivery performance, external-content privacy, and maintainability. The final isolated browser smoke and full fictional-data write pipeline passed after all five passes.
- Continuous refinement Round 21 completed: post-commit snapshot failure is now a first-class recoverable state rather than a misleading generic error. Fault injection covers both snapshot creation and backup-evidence recording failures; UI recovery, normal smoke, the full write pipeline, logs, docs, and 101 automated tests agree on the same no-retry contract.
- Continuous refinement Round 22 completed: five passes inventoried every UI write, moved remaining prefect and pre-generation-leave writes off the event loop, added archive consequence confirmation, repaired expected form omissions before transaction start, expanded smoke/E2E evidence, and aligned handover/design/architecture documents. The final suite has 106 tests and both isolated browser verifiers pass.
- Continuous refinement Round 23 completed: roster preparation and manual draft forms now repair invalid week starts, missing selections, and missing reasons before any durable-operation claim. `RosterWorkflow` remains the Monday-rule owner, event handlers snapshot visible values before yielding, and a fresh isolated browser run proved the corrected no-write states through the complete publish/PDF/adjust/restore pipeline. The suite has 111 tests.
- Continuous refinement Round 24 completed: settings now treats a verified snapshot as an explicit dependency for handover packaging and managed restore. A fresh no-backup browser run proved both dead-end actions are disabled and the verified-snapshot action is visible; the complete isolated write pipeline then proved both controls activate after verified backups exist. A browser-found helper-signature `NameError` was fixed and guarded at signature level. The suite has 115 tests.
- Continuous refinement Round 25 completed: `verify_backup` now emits stable trust reason codes and `backup_inventory` summarizes recent verified/invalid snapshots. Settings shows only bilingual category counts, never raw errors, and a mixed-state browser run proved one manifest-less snapshot stays excluded while valid handover and restore remain available. The full pipeline, docs, and 120-test suite share this contract.
- Continuous refinement Round 26 completed: recent snapshot verification now uses at most four read-only workers while preserving newest-first results and recomputing trust on every visit. Measured twelve current snapshots improved from about 99 to 83 ms; twelve 10 MB snapshots from about 279 to 136 ms. Candidate/checksum file-removal races are contained, and the mixed valid/invalid browser pipeline plus 124 tests remain green.
- Continuous refinement Round 27 completed: stale roster identifiers are no longer silent empty assignment results, and detail/adjustment URLs now share a bilingual, keyboard-accessible recovery state. Direct draft adjustment URLs expose no writable form and return the operator to review/publish; published adjustments remain unchanged. Fresh isolated smoke and full fictional-data write-pipeline runs passed with 127 tests and a new recovery screenshot.
- Continuous refinement Round 28 completed: `.env` is now loaded before durable path constants, deployment readiness no longer mistakes any SQLite filename for a verified backup, and invalid-only snapshot sets fail readiness. A new fail-closed release-candidate orchestrator runs 132 tests, compilation, dependency integrity, full UI smoke, the complete fictional write/PDF/restore pipeline, strict verified-snapshot readiness, and an independent committed-without-backup recovery server in disposable paths. Its complete run passed all seven gates and wrote a non-sensitive JSON report; `requirements-dev.txt` makes the evidence reproducible on a replacement computer.
- Continuous refinement Round 29 completed: the formal acceptance checklist now has a requirement-by-requirement evidence matrix separating direct machine proof from Head Study Prefect and teacher-advisor decisions. Published Chinese and English PDFs are parsed for every weekday, status, authoritative Chinese names, room labels, and exactly four Room 202 closed cells. Starlette's current `httpx2` TestClient backend removes the final suite warning, and the release report explicitly says human acceptance remains required. A direct-script import regression found by the full orchestrator was fixed and guarded; the final 135-test seven-gate rerun passed without warnings.
- Continuous refinement Round 30 completed: the Handover page's empty responsive-row bug is fixed, so the three readiness states now form a compact desktop grid and a readable phone sequence. A new release-evidence boundary fingerprints 74 release-sensitive files, rejects stale/malformed/unsafe reports, and presents machine state beside—not above—human responsibility in bilingual, non-colour-only UI. The in-app four-priority checklist, 44px actions, dark/light styling, and browser evidence make formal acceptance discoverable without pretending software can approve real school practice.
- Continuous refinement Round 31 completed: the support boundary now includes asyncio failures. A Windows localhost browser transport reset is classified as a payload-free informational disconnect instead of an alarming uncaught terminal error, while every other asynchronous exception is recorded as critical and delegated to the prior/default loop handler. The release verifier now audits both isolated NiceGUI server consoles after shutdown and fails closed on error/critical levels, tracebacks, or uncollected task exceptions without copying raw console payloads into its report. Focused tests prove privacy, idempotent installation, no masking of unexpected failures, and the former server-side verification blind spot.
- Continuous refinement Round 32 completed: the hard-coded NiceGUI development secret is removed. Localhost now creates one persistent 64-character managed secret with exclusive creation and restart reuse, fails closed on corrupt state, and exposes only a read-only readiness category. Explicit environment configuration still takes priority, while future server mode refuses the local managed file and requires its own environment secret. The secret remains outside Git, PDFs, logs, roster backups, and release reports.
- Continuous refinement Round 33 completed: the future Cloudflare profile no longer asks NiceGUI to bind directly to `0.0.0.0`. Both modes are loopback-only; server mode now models a same-host Tunnel and requires explicit remote approval, Protect with Access, Access identifiers, a validated public hostname, an independent secret, and a Trusted Host allow-list. The running NiceGUI smoke proves an unapproved Host receives HTTP 400. Server readiness deliberately remains warning-level until live Access and bypass tests are signed off, so configuration presence cannot impersonate completed security acceptance.
- Continuous refinement Round 34 completed: release verification now begins with a privacy-safe Git hygiene gate. It rejects force-tracked environment files, runtime databases, backups, logs, generated documents, operator imports, and operator music; verifies the ignore contract; preserves `.env.example` as trackable; and reports only categories/counts. The project currently passes hygiene with zero tracked sensitive files while honestly reporting `history: missing`; no commit, remote, or push was created.
- Continuous refinement Round 35 completed: Practice Mode is now a real isolated application profile rather than a visual demo. Dedicated start/reset entry points, fail-closed `data/practice/` boundaries, separate preferences/logs/backups, mode-aware service reuse, persistent bilingual identity, and triple-marked non-official PDFs let a successor rehearse the full production workflow without opening official state. The release candidate passed 8/8 gates after the change.

## Next Steps

1. Ask the next Head Study Prefect to complete the documented Practice Mode rehearsal, including reset, before formal acceptance.
2. Define encrypted, off-device backup retention before using real data beyond the local computer.
3. Configure Cloudflare Access and authenticated role boundaries only after a teacher-approved security decision; otherwise retain localhost-only use.
4. Perform the documented release-readiness audit, then review responsive controls with operators during acceptance testing and make only evidence-backed refinements.

## Key Decisions and Architecture

| Layer | Current Decision |
|---|---|
| Runtime UI | NiceGUI 3.13, Python 3.12 |
| Persistent storage | Local SQLite with WAL, foreign keys, transactions, online backups |
| Schema evolution | SQLAlchemy 2 + Alembic migrations |
| Policy | `packages/roster_policy/` is the policy source of truth |
| Core generation | `packages/roster_core/` remains UI-independent |
| Localization | Traditional Chinese default; English is a full UI counterpart |
| Theme | Professional Teal `#0F766E`, restrained gold, light/dark support |
| External access | Same-host loopback Cloudflare Tunnel planned; Protect with Access and live teacher-approved bypass testing required before exposure |
| Optional online music | Visible YouTube public-playlist player; no sign-in/payment/API key for playback, optional local-environment API key for search |
| PDF export | Local-memory ReportLab generation with a Traditional Chinese CJK font; no public upload |

Important boundaries:

- Policy and fairness logic must never be placed in NiceGUI page handlers.
- Translated labels must never become database keys or policy inputs.
- `history_weight` changes only at publish time or through a published leave adjustment.
- Existing `frontend/` and `backend/` are no longer runtime targets; keep them as temporary reference only.

## Known Issues and Risks

| Risk | Status | Mitigation |
|---|---|---|
| Cloudflare Tunnel is not configured | Open | Keep localhost-only; later require same-host loopback Tunnel, Protect with Access, school allow-list, exact public Host, and live bypass testing |
| NiceGUI session-signing secret | Managed | Localhost creates and reuses an ignored managed secret; future server mode requires an explicit independent environment secret |
| Backups are local only | Open | Restore is safe and guided; define encrypted off-device retention before real deployment |
| PDF CJK font is unavailable on a replacement PC | Managed | Install Noto Sans TC or set `SING_YIN_PDF_FONT`; procedure is in `docs/RELEASE_HANDOVER.md` |
| Pre-generation leave enforcement | Resolved | Draft generation and publishing both validate persistent weekly declarations |
| Earlier Next/FastAPI scaffold remains | Managed | Do not run it as the official system; NiceGUI is now the runtime |
| Local support logs may be needed for troubleshooting | Managed | `logs/app.log` rotates locally; quote only the `OP-...` reference and never upload the log to a public service |
| Effective Git history is not available in this project copy | Open | The eighth release gate proves the index/ignore boundary is safe; teacher advisor or IT must still create or restore a school-approved private/offline history without using blanket `git add .` |

## Resources and References

| Path | Purpose |
|---|---|
| `nicegui_app/main.py` | Official application entry point |
| `nicegui_app/services/roster_workflow.py` | Generate, publish, leave-adjustment, fairness, backup transactions |
| `nicegui_app/ui/` | Shared shell, bilingual messages, theme, pages |
| `nicegui_app/utils/prefect_import.py` | Local JSON/CSV normalization for AI-prepared imports |
| `migrations/` | Alembic SQLite schema history |
| `data/runtime/sing-yin-roster.sqlite3` | Local live database, generated at startup and ignored by Git |
| `data/backups/` | Automatic SQLite snapshots and manifests |
| `data/devotional/daily-verses.seed.json` | Canonical devotional source |
| `data/demo/prefects.zh-HK.seed.json` | Traditional Chinese demo prefect seed |
| `docs/NICEGUI_ARCHITECTURE.md` | Runtime, layer boundaries, backup, and verification guide |
| `docs/SKILLS_OVERVIEW.md` | Active prompt/skill governance and maintenance guide |
| `Professional_Design_System.md` | Active UI/UX design source of truth, token roles, implementation phases, and quality gates |
| `docs/RELEASE_HANDOVER.md` | Local launch, PDF, backup, external-access gate, and final acceptance procedure |
| `docs/ACCEPTANCE_EVIDENCE.md` | Requirement-by-requirement automated evidence and remaining human sign-off |
| `docs/QUICKSTART.md` | Double-click startup, duplicate launch, and port-conflict instructions |
| `docs/DEPLOYMENT_DECISION.md` | Approved local mode, Cloudflare Access decision gates, and true-cloud architecture boundary |
| `START_SING_YIN_ROSTER.cmd` | Windows double-click launcher for a non-technical operator |
| `START_PRACTICE_MODE.cmd` / `RESET_PRACTICE_MODE.cmd` | Isolated fictional rehearsal and safe clean restart |
| `scripts/start_sing_yin_roster.ps1` | Port-safe local launcher and HTTP readiness gate |
| `nicegui_app/application_mode.py` | Fail-closed official/practice storage composition boundary |
| `scripts/verify_practice_mode.py` | Bilingual, theme, mobile, console, and health browser evidence for Practice Mode |
| `README.md` | Immediate first-time opening and setup instructions |
| `docs/OPERATOR_GUIDE.md` | Complete daily operator guide: import, preview, manual draft changes, publication, late leave, recovery |
| `/system-architecture` | Non-sensitive in-app architecture explanation, project-team attribution, and co-creation conclusion |
| `CODEX_PROMPTS.md` | Codex user-centered delivery scaffold and work modes |
| `scripts/verify_nicegui_ui.py` | Browser smoke test |
| `scripts/verify_nicegui_write_pipeline.py` | Isolated end-to-end fictional-data write pipeline and restore verification |
| `scripts/check_repository_hygiene.py` | Filename-free Git index and ignore-boundary audit before any initial commit |
| `nicegui_app/observability.py` | Privacy-safe local operation references, rotating logs, and uncaught-failure capture |
| `nicegui_app/release_evidence.py` | Release-report fingerprint, staleness, and display-safe acceptance state |

## Local Run and Verification

```powershell
python -m pip install -r requirements.txt
python -X utf8 -m nicegui_app.main
```

Open `http://127.0.0.1:8080`.

```powershell
python -X utf8 -m pytest -q
python C:\Users\lichu\.codex\skills\webapp-testing\scripts\with_server.py --server "python -X utf8 -m nicegui_app.main" --port 8080 -- python -X utf8 scripts\verify_nicegui_ui.py
```

## Maintenance Rule

Update this document after every meaningful workflow, persistence, security, or deployment milestone. It must describe current truth, not merely intended plans.
