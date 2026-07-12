# NiceGUI Runtime Architecture

## Purpose

`nicegui_app/` is the official local runtime for the Sing Yin Study Prefect Duty Roster System. It is deliberately separate from the earlier `frontend/` and `backend/` scaffolds, which are retained only as non-runtime reference material.

The current Head Study Prefect is the normal write operator. The teacher advisor mainly reviews published rosters, fairness, recovery, and handover evidence after completion; the release does not create a second daily-operating workflow for that reviewer role.

## Product, Organisation, and Solution Architecture

The presentation is deliberately split across three routes. `/platform` owns the non-sensitive product, organisation, solution, culture, resources, and co-creation story. `/engineering` turns documented release quality into a five-layer blueprint, eight verification gates, reliability capabilities, and a build narrative. `/system-architecture` owns the service lifecycle, technical ownership, trust evidence, recovery boundaries, and operator FAQ. This is information architecture, not a second business-logic layer, and the ordinary dashboard remains the first route for weekly work.

The Study Prefect Team model preserves official roles while adding explanatory functional titles:

- Head Study Prefect — `Service Governance Lead`;
- Assistant Head Study Prefect — `Duty Coordination Lead`;
- Study Prefect — `Room Service Steward`;
- Teacher Advisor — `Oversight & Assurance Advisor`.

These labels never become database values, roster-policy inputs, or replacement school titles. The page also groups platform work into four capability lanes—Weekly Operations, Fairness Assurance, Service Experience, and Systems Continuity—and four outcome-led solutions linked to the real workspaces. The groups do not imply additional staff. Their purpose is to make ownership and handover easier to understand.

The Platform & Team page uses `nicegui_app.ui.platform_summary.load_platform_summary` to combine only the existing `handover_readiness()` counts and display-safe release evidence. Its public interface contains active-prefect count, roster-week count, a verified-backup boolean, and release state/check totals. It deliberately omits names, class, leave, roster content, audit payload, database paths, and backup paths. A read failure is logged through the existing payload-free support reference and produces a neutral bilingual fallback while the rest of the page remains available.

NiceGUI owns the rendering and navigation. The read model introduces no schema, policy, write, backup, or restore change. `/system-architecture` links back to `/platform` rather than duplicating its organisation chart, capability map, solution portfolio, and co-creation close.

`/engineering` reads only `load_release_evidence()` and static, version-controlled structural facts. It never opens `RosterWorkflow`, a database session, a backup path, or an audit payload. The report badge may show passed, running, stale, failed, missing, or unreadable evidence; the page does not reinterpret a non-passing state as success. Its nine gate labels mirror `scripts/verify_release_candidate.py`: repository hygiene, supply-chain security, automated tests, compilation, dependency integrity, browser verification, isolated write pipeline, strict deployment readiness, and committed-without-backup recovery.

## Start Locally

```powershell
python -m pip install -r requirements.txt
python -X utf8 -m nicegui_app.main
```

Open `http://127.0.0.1:8080`. Cloudflare Tunnel should point to this local address after Cloudflare Access is configured.

## Durable Data Contract

### Official/practice composition boundary

`nicegui_app.application_mode.ApplicationModeSettings` is an outer composition profile, not a roster-policy rule. `official` remains the default and accepts the established injected paths. `practice` starts only when database, backup, and log paths are all explicit, distinct, and contained by `data/practice/`; the runtime then injects those paths into `RosterWorkflow`. The practice launcher also uses a separate port range and NiceGUI storage secret.

The persistent shell banner and PDF marker receive the resolved mode as presentation input. They do not change eligibility, generation, fairness, publication, adjustment, backup, or restore behavior. `/healthz` exposes only the non-sensitive `applicationMode` identity so the two Windows launchers cannot reuse the wrong process. `scripts/reset_practice_mode.py` verifies its fixed workspace boundary and refuses to reset while a practice service is running.

- Live data: `data/runtime/sing-yin-roster.sqlite3`
- Schema migrations: `migrations/` via Alembic
- Automatic backups: `data/backups/`
- Canonical devotionals: `data/devotional/daily-verses.seed.json`
- Demo prefect seed: `data/demo/prefects.zh-HK.seed.json`

The workflow service is the only supported write path for roster operations:

1. Generate: validates school policy and saves or replaces the Monday-based draft.
2. Publish: validates again, posts every assignment to `fairness_ledger`, then updates persistent `history_weight`.
3. Leave adjustment: reverses the original weight, credits an eligible substitute when supplied, updates the published roster, and records an audit event.
4. Prefect management: creates, updates, or archives active roster members without erasing historical fairness records.
5. Pre-generation leave: records an auditable absence constraint for a Monday-based week; generation and validation exclude that prefect on the declared day. Publish validates the current declarations again, so a draft made before a new leave declaration must be regenerated. Published weeks must use post-publication adjustment instead.
6. AI-prepared import: accepts pasted JSON/CSV, validates it locally, previews it, and imports only after an explicit action.
7. PDF export: builds a bilingual A4 PDF in memory from durable roster reads; it is a local download and never a public upload. Versioned Noto Sans HK Regular/Medium/SemiBold files make output deterministic on a replacement host. The schedule export accepts presentation-only crest and supplementary-footer switches; clean group-sharing output is the default.

Published-duty substitute recommendations and the final leave-adjustment save share the same role, availability, declared-leave, same-day uniqueness, and no-consecutive-duty gates. A previously recorded absence cannot become eligible merely because the adjustment happens after publication.

Every successful generate, publish, adjustment, leave declaration, and prefect-management write creates a SQLite online-backup snapshot and manifest. A backup failure is surfaced as an action failure; it is never silently ignored. Each manifest includes a SHA-256 checksum; the service validates the manifest checksum against the actual file, `PRAGMA integrity_check`, and required tables before a snapshot is trusted, packaged, or restored.

Publication has a database-level single-winner claim: the `roster_weeks` row changes from `draft` to `published` only through a conditional update inside the same transaction that writes fairness-ledger entries. A second tab or concurrent local client is rejected before it can post duplicate workload points.

Prefect creation, update, archive, and bulk import follow the same backup rule. Archive is a soft delete because published rosters and fairness-ledger records must remain historically truthful. The page therefore requires a destructive-action confirmation which explicitly says that historical rosters, fairness records, and audit evidence are retained and that there is no immediate undo.

## Recovery and Handover

Use **Settings -> Backup restore** only when the operator intends to return the live system to a known snapshot. The workflow accepts only verified snapshots from `data/backups/`, creates a `pre_restore` safety snapshot of the current state, atomically replaces the SQLite database, rebuilds its database connections, records an audit event, and creates a post-restore snapshot. This provides a recoverable path in both directions.

For an off-device copy, use **Settings -> Create handover backup package** after a verified snapshot exists. The local download contains exactly one verified SQLite snapshot, its manifest, and offline recovery notes; it is generated in memory and is not uploaded or retained as another local copy. Save it only to a school-approved encrypted location. To restore it later, extract both files into `data/backups/` and use the managed restore screen. Do not manually overwrite `data/runtime/sing-yin-roster.sqlite3` while the application is running.

Both handover packaging and managed restore depend on `workflow.backups()` returning at least one snapshot whose current checksum, manifest, SQLite integrity, and required tables verify successfully. If none exists, NiceGUI renders a bilingual recovery empty state, exposes **Create verified snapshot now** as the only productive action, and keeps package/restore controls disabled with `aria-disabled`. It does not open a confirmation that cannot succeed or send an expected empty-state condition into the support-error path. The ordinary browser smoke proves this no-write state; the full write pipeline proves the controls become enabled after real verified snapshots exist.

`verify_backup` also returns a stable `reasonCode` alongside maintainer diagnostics. `backup_inventory` counts only the recently checked managed snapshots and groups failures as file, manifest, checksum, SQLite integrity, schema, or unknown. NiceGUI translates those codes and counts but never renders the raw `error`, a database row, or file contents. Invalid snapshots remain visible as a trust warning while valid snapshots continue to power package/restore actions; the two states are not mutually exclusive.

Recent snapshot verification is parallel but never cached. `backups()` captures each candidate's modification time once, preserves newest-first order, and verifies at most four independent read-only SQLite files concurrently. A file that disappears during candidate scanning is skipped; one removed before checksum becomes the controlled `missing_file` result instead of a Settings 500. The four-worker limit measured about 83 ms for twelve current ~85 KB snapshots and 136 ms for twelve artificial ~10 MB snapshots, versus roughly 99 ms and 279 ms sequentially. Every page visit still recomputes the manifest checksum and SQLite integrity, so performance cannot turn stale evidence into trust.

## Long-operation feedback

Roster generation, publication, manual draft changes, published-duty leave adjustment, pre-generation leave declaration/cancellation, prefect creation/update/archive, bulk import, PDF creation, verified snapshot/handover packaging, and restore run through one bilingual progress dialog. It gives an honest three-stage message—preparing, safely processing, and finalising—instead of presenting an invented estimate. The durable work runs outside the NiceGUI UI event loop; the existing workflow service remains the sole owner of transactions, fairness changes, and snapshot timing. `_safe_read_action` is reserved for the two short, read-only candidate-list lookups and must not become a write path.

`nicegui_app/ui/operation_gate.py` gives each connected browser client one short-lived admission claim before the handler reaches its first `await`. A rapid second request is rejected with a bilingual next step, and the claim is always released on success, failure, or cancellation. This is an operator-experience guard only: workflow transactions, conditional publication, constraints, and validation remain the final correctness boundary.

Predictable form repair happens before that admission claim. Missing leave/draft reasons, missing selections, invalid dates, and non-Monday week starts receive a bilingual warning and keyboard focus without creating a transaction or support incident. The Monday rule is still owned by `RosterWorkflow.validate_week_start`; the page calls that public domain-facing validation instead of duplicating the rule. Once an action is accepted, the handler snapshots every visible identifier and reason before its first `await`, so the background transaction cannot observe a later UI value.

### Committed write with failed snapshot

SQLite commit and online snapshot are deliberately separate stages because a snapshot must copy committed state. Therefore a disk or backup-directory failure can happen after the roster change is durable. `CommittedWriteBackupError` is the explicit workflow contract for this partial-success boundary. It is used by generation, publication, manual draft changes, published-duty adjustment, prefect writes, pre-generation leave writes, and post-restore snapshot creation; the pre-restore safety snapshot remains a normal pre-commit failure.

NiceGUI must never map this exception to the generic retry message. It closes the progress state, records `event=operator_action_partial` with `durable_state=committed backup=failed`, and opens a persistent bilingual recovery dialog saying not to repeat the write. The operator may reload to review the committed state or open Settings and use **Create verified snapshot now**. That action changes no roster or fairness data; it creates a new snapshot, manifest, checksum and SQLite integrity result.

Snapshot creation and the secondary `backup_runs` evidence write are both contained by this contract. If the snapshot is valid but its evidence row cannot be committed, the workflow still returns a conservative partial state instead of leaking a generic database exception or inviting the roster write to run twice.

`scripts/verify_nicegui_partial_backup.py` proves the boundary end to end with an isolated database and a backup path intentionally occupied by a file. It verifies the committed draft and 26 assignments, failed backup-run evidence, the visible OP reference and no-retry copy, then repairs the temporary path and creates a verified manual recovery snapshot. No production test branch is used.

For automated browser checks that must exercise a real write, use an isolated database and backup directory through `SING_YIN_DATABASE_PATH`, `SING_YIN_BACKUP_DIR`, and `SING_YIN_EXERCISE_PROGRESS=1`. Do not set these for normal operator use, and never use a real school database for a mutation test.

### Full write-pipeline browser evidence

`scripts/verify_nicegui_write_pipeline.py` is the release-level browser check. It refuses to run unless `SING_YIN_E2E_ISOLATED=1` and all of `SING_YIN_DATABASE_PATH`, `SING_YIN_BACKUP_DIR`, and `SING_YIN_LOG_DIR` are explicitly set away from the canonical school locations. It drives the real NiceGUI interface using fictional Chinese data through import, pre-generation leave, draft generation, a deliberately rejected empty-reason draft edit, a valid manual change, publication, both schedule PDFs, published-duty substitution, handover-package download, and a managed restore into a second isolated database.

The script reads the isolated workflow only after browser actions to verify ledger totals, audit events, backup manifests, PDF layout/text, and restored state. It never adds test branches to production pages and never reads or writes the live school database.

## Local support evidence

`nicegui_app/observability.py` configures the rotating UTF-8 log at `logs/app.log` before the workflow starts. A consequential UI action receives a short `OP-...` reference; success records the controlled action name and duration, while failure records the exception type and code location. `RequestTracingMiddleware` adds a generated `REQ-...` trace to every HTTP response as `X-Request-ID` and records only its request method, safe route category, status, and duration. The logger is deliberately payload-free: callers must never pass a name, leave reason, form value, roster row, PDF content, query string, or translated interface copy.

The UI does not append `WorkflowError` text to notifications. It displays the bilingual safe-retry message and support reference instead, while process, thread, and asyncio exception hooks keep a local code-location record for diagnosis. The asyncio hook treats only Windows browser-transport reset codes 64/10054 as an informational local-client disconnect; every other uncaught asynchronous failure remains critical and is delegated to the previous or default event-loop handler. Neither path records the exception message or asyncio context payload. `scripts/inspect_support_log.py` filters the local file by one validated `OP-...` or `REQ-...` token for safe handover investigation. `SING_YIN_LOG_DIR` may isolate logs during automated verification, while `SING_YIN_LOG_LEVEL`, `SING_YIN_LOG_CONSOLE`, `SING_YIN_LOG_MAX_BYTES`, and `SING_YIN_LOG_BACKUP_COUNT` control local diagnostics; normal operators should leave the defaults in place and must not point logs to a public or personal cloud-sync folder.

## Layer Boundaries

| Layer | Location | Responsibility |
|---|---|---|
| Policy | `packages/roster_policy/` | AHP gates, room capacity, closures, weights, opening times |
| Core | `packages/roster_core/` | Pure daily devotional selection and weekly roster generation/validation |
| Persistence | `nicegui_app/persistence/` | SQLite engine, Alembic schema, durable records |
| Workflow | `nicegui_app/services/roster_workflow.py`, `nicegui_app/services/workflow_parts/` | Stable facade plus separated transactions, fairness ledger, people, backups, adjustments, and recovery |
| Presentation | `nicegui_app/ui/page_routes/`, `page_shared.py`, `i18n_catalog/`, `theme_markup.py` | NiceGUI routes, shared components, domain-grouped bilingual copy, design-system markup, page shell, anonymous platform summary, and non-sensitive architecture explanation |
| Export | `nicegui_app/services/roster_export.py` | Local-only bilingual PDF composition; no persistence or network writes |
| Observability | `nicegui_app/observability.py` | Payload-free local operation evidence and rotating support logs |
| Optional media | `nicegui_app/services/online_music.py`, `nicegui_app/ui/music.py` | Public YouTube playlist validation/search and visible presentation; strictly separate from roster persistence |

Business rules must never be implemented in UI event handlers. UI translation keys must never be used as database values or policy inputs.

### Optional YouTube boundary

The official integration uses a visible `youtube-nocookie.com` iframe with native controls and no autoplay. A public playlist needs neither sign-in nor an API key. `SING_YIN_YOUTUBE_API_KEY` only unlocks public Data API search and is read from the local environment; it is never persisted by the roster workflow. Saved public playlist IDs live in the ignored local file `music/youtube-playlists.json`.

The embed does not enable the unused JavaScript control API, sends no referrer, and lazy-loads only after the operator opens the music window. Search-result images are accepted only from official YouTube thumbnail hosts. Dynamic HTTP responses carry `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, clickjacking/content-sniffing protection, and a camera/microphone/geolocation deny policy; static assets and NiceGUI internals are not forced into the no-store policy.

The media layer may receive page context (`dashboard`, `devotional`, `getting_started`, `guide`, `architecture`, or `handover`) but never a prefect, roster, leave, fairness, audit, backup, or PDF payload. No music control appears on sensitive roster tables or settings recovery actions. With no saved playlist, the UI renders guidance but creates no iframe, avoiding an unnecessary third-party connection.

Dashboard devotion uses the polished seed themes owned by `roster_core`. The UI persists only `auto`, `guidance`, or `comfort`; `auto` resolves from the current appearance while an explicit choice overrides it. `roster_core.select_daily_verse(..., themes_any=...)` performs the deterministic theme filtering, so translation labels and CSS never become devotional-selection inputs.

Official crest files are local presentation assets under `nicegui_app/assets/brand/`. Their semantic paths are centralized in `nicegui_app/config.py`: a 512-pixel derivative owns favicon delivery, the compact source owns navigation, a 640-pixel derivative owns architecture display, and the full source is reserved for PDF export. The user-supplied masters remain at project root; the old ambiguous `logo.png` is intentionally removed.

### Responsive roster presentation

`nicegui_app/ui/page_shared.py` creates one localized roster display model from the workflow's durable assignments; `nicegui_app/ui/pages.py` is now only the stable route-registration facade. Wide screens render that model as the inspection table; screens at phone width render the same model as day-grouped duty cards. Each card retains post, time, Chinese prefect name, status, and workload, so mobile review never depends on horizontal table scrolling. This is a presentation-only adaptation: it does not change policy inputs, workflow writes, PDF layout, or fairness calculations.

The same presentation boundary applies to the prefect directory: one localized display model drives the desktop table and phone identity cards. The leave-adjustment page remains a workflow client, but its responsive form groups the original assignment, eligible-substitute decision, and required reason into visible UI steps. A missing reason is rejected in the UI before the workflow call; the workflow remains the final validator for every write.

The same preflight contract covers roster preparation and manual draft correction: an absent leave reason, missing candidate, missing change reason, or invalid week start is repaired in place. `scripts/verify_nicegui_write_pipeline.py` asserts that these states create neither a progress dialog nor a `progress_*_working` log event before the valid submission.

Roster identity is also a workflow read contract, not an empty-table convention. `RosterWorkflow.assignments()` first verifies that the roster week exists, so a stale bookmark after a managed restore cannot be mistaken for a real roster with no assignments. Both roster-detail routes render the same bilingual live recovery state with routes to the current roster list and verified-backup settings. The adjustment route additionally reads the durable roster status before rendering any form; a draft receives a return-to-review state, while only a published roster can expose substitute and reason controls.

`nicegui_app/config.py` loads the project `.env` before resolving database and backup path constants. Explicit process variables still take priority, which preserves isolated browser runs while making documented `.env` paths effective on a replacement computer. Deployment readiness delegates snapshot trust to `RosterWorkflow.backup_inventory`; a `.sqlite3` filename is never sufficient evidence. No snapshots is a first-run warning, at least one fully verified recent snapshot is a pass, and snapshots with no valid manifest/checksum/integrity/schema result are a failure.

`nicegui_app/deployment.py` also owns the NiceGUI session-signing secret. A valid explicit `SING_YIN_STORAGE_SECRET` always wins. In localhost mode only, an absent or known placeholder value causes one 64-character random secret to be created with exclusive file creation at `data/runtime/.nicegui-storage-secret`; restarts reuse it, and concurrent starters cannot overwrite the winner. A present but malformed file stops startup rather than silently invalidating sessions. Readiness inspects this state without creating data. Future `server` mode never accepts the managed-local file and requires a separate environment secret of at least 32 characters. The secret is ignored by Git, excluded from roster backups/PDFs/reports, and must never be logged.

Network exposure is fail-closed in both deployment modes. NiceGUI always binds to loopback; `server` means a same-host `cloudflared` process may connect to that private origin, never that the app listens on `0.0.0.0`. Server startup additionally requires explicit remote approval, a declared **Protect with Access** route, Access audience/team-domain values, and one syntactically valid public hostname. `TrustedHostMiddleware` accepts only localhost addresses plus that approved hostname, which limits DNS-rebinding and unexpected proxy Host headers. These declarations do not prove the external policy works: server readiness therefore remains a warning until the teacher advisor performs unauthenticated-denial, authorized-login, direct-origin, and account-removal tests. No Tunnel, DNS record, token, or external request is created by the application.

## Verification

- `scripts/verify_practice_mode.py` checks the isolated health identity, bilingual persistent banner, light/dark styling, phone layout, console, and local screenshots without writing roster data.

```powershell
python -X utf8 -m pytest -q
python C:\Users\lichu\.codex\skills\webapp-testing\scripts\with_server.py --server "python -X utf8 -m nicegui_app.main" --port 8080 -- python -X utf8 scripts\verify_nicegui_ui.py
```

The browser check covers Dashboard, Roster, Prefects, Adjustments, Audit, language switching, dark mode, favicon delivery, console errors, captured light/dark screenshots, stale roster and adjustment URLs in both languages, and the mobile requirement that Daily Verse precedes the weekly workbench. The isolated release pipeline additionally asserts 26 visible phone roster cards, the absence of clipped desktop roster and directory tables at 390px, the persisted Chinese substitute name in both interface languages, a draft adjustment URL with no writable form, full-width 44px published-adjustment actions, and the safe missing-reason message before a write. With the isolated opt-in environment above, it also verifies the visible progress dialog for an actual generated draft.

For release evidence, run the smoke check and the full write-pipeline script independently. The latter is broader but intentionally remains separate so a normal visual smoke run does not write data.

For a final release candidate, install `requirements-dev.lock` with `--require-hashes`, install Playwright Chromium, and run `python -X utf8 scripts/verify_release_candidate.py`. The first gate, `repository_hygiene`, checks the Git index, true commit history, and ignore behavior before any browser starts. It fails if HEAD is missing or if secrets, runtime databases, backups, logs, generated PDF/ZIP files, operator imports, or operator music are tracked, and reports only categories/counts rather than file content. `scripts/run_security_checks.py` separately gates dependency vulnerabilities, medium/high Python static findings, and secret candidates without printing candidate values. The orchestrator then creates two disposable environments rather than accepting school-data paths: one runs normal UI/write/strict-readiness evidence, and the other deliberately blocks backup creation to prove the committed-without-backup recovery contract. After each server stops, its captured console is checked for error/critical levels, Python tracebacks, and uncollected task exceptions; any marker fails the candidate, while the report receives only a non-sensitive summary rather than raw console content. It writes only non-sensitive check names, status, timing, and timestamps to `logs/release-candidate-report.json`; any failed command leaves the overall report failed and retains its isolated diagnostic directory.

The verification dependency set includes Starlette's current `httpx2` TestClient backend, so a clean replacement-computer run does not normalize a deprecation warning as success. PDF evidence parses both downloaded schedule documents and checks their published state, five weekdays, authoritative Chinese names, landscape single-page geometry, and the four Room 202 closed cells. `docs/ACCEPTANCE_EVIDENCE.md` maps every formal checklist item to its direct automated proof and the remaining human decision; machine `pass` never sets human acceptance to complete.

`nicegui_app/release_evidence.py` owns the presentation-safe report contract. The verifier records a SHA-256 fingerprint over release-sensitive application code, policy/core packages, migrations, tests, verification scripts, launchers, and dependency/configuration files. Handover recomputes that fingerprint before showing a pass; missing, malformed, failed, running, or stale reports receive distinct bilingual states without exposing parse errors or local paths. The current 76-file calculation measured 53.35 ms median and 57.44 ms maximum across seven runs on the development computer, so it remains a live check rather than a cache. Documentation and generated logs are excluded from the machine fingerprint: documentation is governed separately by the acceptance matrix and document tests, while logs must never make their own report stale.
