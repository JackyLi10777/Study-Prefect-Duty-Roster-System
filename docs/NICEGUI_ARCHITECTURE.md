# NiceGUI Runtime Architecture

## rc44 SQLite performance contract

- SQLite remains the sole roster, fairness, audit and backup truth for one active NiceGUI origin. PostgreSQL is a future migration target only if the deployment requires more than one active origin or measured write-lock pressure persists after optimisation; Redis, MongoDB, MySQL and Oracle are not runtime dependencies.
- Alembic `0012` adds measured composite indexes for active roster-week lookup, fairness and leave-adjustment history, descending backup lookup, and a partial unique fixed-weekday rule for active Assistant Head Study Prefects. Migration preflight stops safely when legacy fixed weekdays conflict and never rewrites school data.
- `latest_roster_week()` and bounded `roster_week_history()` are the ordinary read APIs. Bulk prefect import preloads names, fixed weekdays and availability; reporting uses a subquery; withdrawal preloads compensation inputs; outbox workers use bounded batches.
- `SING_YIN_SQL_DIAGNOSTICS=1` enables SQLAlchemy timing. `SING_YIN_SLOW_SQL_MS` defaults to `100`. Diagnostics record only operation class, stable fingerprint, duration, row count and request reference—never bound parameters, names, leave reasons or roster contents.
- Startup runs one controlled `PRAGMA optimize` after migration. Request handlers do not run `ANALYZE`. WAL, foreign keys, busy timeout, `BEGIN IMMEDIATE`, optimistic versions, command receipts, backup obligations and the maintenance lock remain unchanged.
- Backup overview is one bounded inventory snapshot with an evidence timestamp. Checksum, manifest and integrity work is dispatched with `run.io_bound`, so loading Settings or Handover does not block other browser sessions.

<!-- SING_YIN_CURRENT_STATUS:START -->
> **Verified production truth (2026-08-09):** the live Windows origin is clean annotated `v1.2.0-rc.54` at `f027628c5a0045d8a946be9a3453e041d03367d1` and runs an immutable bundle. Its 316-file fingerprint `738c45917fdcbeeb84a523a1f1cc3179adee693b07e156bdb74fa6f8748b3ef8` passed 15/15 gates. SQLite is at Alembic `0014`; verified backup `20260809-093349-010387-manual_verified_backup.sqlite3` with SHA-256 `65e2d9c086b0aa4e9495f17d55ad2d62ea238c049d046debba7b124205166a29`, isolated restore, health, `writeReady=true`, `maintenance=false`, `recoveryRequired=false`, and `pendingBackups=0` passed. Worker source changed and was promoted; canonical Worker `053b8f6e-c5ed-4259-ac34-aaefa4dfb23d` remains healthy at 100% traffic. `v1.2.0-rc.52` is historical source evidence, not a code-only rollback after migration `0014`; recovery requires the controlled compatible database restore. Supervised human acceptance remains `pending`, and the physical off-site BitLocker recovery drill remains `pending`. See [current system status](status/CURRENT_STATUS.md) for the exact state and update contract.
<!-- SING_YIN_CURRENT_STATUS:END -->

> **Source-only candidate:** production already includes the shared draft-grid and additive Alembic revision `0013_roster_day_closures` recorded above. The protected-main rc53 merge plus rc54 integration candidate adds source-only revision `0014_roster_slot_exceptions`, per-cell unavailability, extended spreadsheet interaction, typed UI edit sessions and atomic multi-row prefect save. Production remains exactly as recorded in the generated status block above; revision `0014` and these candidate interactions are not deployed evidence until formal release, backup, isolated restore, and controlled rollout complete.
>
## Purpose

`nicegui_app/` is the sole official local runtime for the Sing Yin Study Prefect Duty Roster System. The earlier `frontend/`, `backend/`, `demo_code/`, and `demo_code2/` runtime trees are absent from the active release.

> **Historical clean v1.2 rc30 evidence:** the controlled Windows origin used
> `v1.2.0-rc.30`／`74b84f43786b00feb15b51a6270ff71c9430773f`; the canonical Worker is
> `11763f08-d40d-46d5-93dc-5ca2599d4154`. The 296-input runtime release passed all 14 formal gates
> with fingerprint `15d155d8d745b14b574b08d793150c93aa77946e7d17a63030844c44adededbc`.
> At that time, first-level origin rollback was rc27／`c4c728aa41c9b0122aaa2c015b3cc38e246db43d`;
> Worker `d7b51f21-7692-418d-866c-034c2c57292d` was the immediately previous edge version.
> A fresh production backup, checksum, fairness reconciliation and isolated
> restore passed before cutover. Worker version
> `11763f08-d40d-46d5-93dc-5ca2599d4154` passed zero-percent version smoke before
> promotion to 100%; canonical root, capability health and rendered checks passed.
> Supervised human acceptance remains required.
>
> **Historical rc31 pre-deployment record (not yet deployed at that time):** branch `codex/rc31-unified-theme-controls`
> now combines the binary Light／Dark control with deterministic complete
> room-schedule solving and strict coverage／weight validation, bounded
> access-mode-and-session-bound Admin／Guest generated-file delivery,
> rendered-state mobile-drawer focus synchronization, universal business-write
> admission, diagnostic-only recovery-marker startup, exact-byte staged
> backup／handover／restore verification, migration-provenance guards, and an
> Alembic-to-application logging boundary that preserves the privacy-safe logger. Earlier
> theme-only rc31 results predate the final rollout and remain historical rather
> than current-source evidence. At the time of this record, origin／Worker
> provenance was still drifted, clean rc30＋`11763f08…` was the last verified
> recovery baseline, and rc31 rollout plus canonical checks remained pending.
>
> **Historical rc21 boundary (now the secondary verified baseline):** annotated tag `v1.2.0-rc.21` points to commit
> `f7df4d0170e6bacd65340cc893992a17b5ed4aed`. Its 291-source-file fingerprint
> `e7b2a52a004968b899a76de583ca86cb1d575d2a9bbba4cedd5e0e7ab67361b1`
> passed all 14 formal gates, including the complete Python suite, 3 motion, and 40 Worker tests.
> At that rollout, the protected Windows origin switched to this exact commit. Pre-switch backup
> `20260726-003841-844011-manual_verified_backup.sqlite3`／SHA-256
> `fed7b02a82265477a19c9be675d7fd14e8d4b259055af5331e2f76f40b8ee777` passed isolated
> restore. Worker source and configuration were unchanged, so Worker version
> `f780feb2-671a-4feb-b6f6-b7f9d5b31e89` was retained without a new Worker
> rollout. rc21 is now a historical secondary recovery baseline; rc26 later replaced it,
> while rc27 was the first-level origin rollback beneath rc30 at that time. Current production and its migration-aware controlled-restore boundary are generated at the top of this document.

The current Head Study Prefect is the normal write operator. The teacher advisor mainly reviews published rosters, fairness, recovery, and handover evidence after completion; the release does not create a second daily-operating workflow for that reviewer role.

## Product, Team Responsibilities, and Solution Architecture

### Canonical page and navigation catalogue

`nicegui_app/ui/page_catalog.py` is the only catalogue for workbench route identity, title key, icon, page kind, music context, minimum capability, visible access modes and mobile-primary status. Desktop and mobile navigation must derive from this catalogue; a page handler must not invent a translated route, a second Guest menu or an independent access rule.

Routine navigation follows the operator's actual work in this order: **Getting Started → Weekly Operations → People & Fairness → Handover & Governance → Administration → Contextual Help**. `/platform`, `/engineering` and `/system-architecture` form a separate **Trust & Documentation** portal. They remain fully available to Admin and Guest, but do not compete with the weekly task sequence. Public entrance and the read-only `/view#…` surface remain outside the workbench shell.

`PageKind` is presentation metadata, not authorization. Every route, callback, service and download must still enforce the server-verified `PageContext` and capability policy. Admin and Guest therefore share page structure without sharing a persistence adapter or write authority.

The presentation is deliberately split across three routes. `/platform` owns the non-sensitive product, real team responsibilities, solution, culture, resources, and co-creation story. `/engineering` turns documented release quality into a five-layer blueprint, the fingerprint-bound verification gates, reliability capabilities, and a build narrative. `/system-architecture` owns the service lifecycle, technical ownership, trust evidence, recovery boundaries, and operator FAQ. This is information architecture, not a second business-logic layer, and the ordinary dashboard remains the first route for weekly work.

The Study Prefect Team model preserves official school roles and describes their real responsibilities directly:

- Head Study Prefect — weekly decisions, publishing, exceptions, fairness explanation, and handover;
- Assistant Head Study Prefect — coordination and `Assist. in charge` duty;
- Study Prefect — service in Rooms 302, 303, and 202 on open days;
- Teacher Advisor — post-completion review and advice.

The page groups platform work into four plain work areas—weekly rostering and publishing, fairness review and explanation, guidance and support, and backup/recovery/handover—and four outcome-led solutions linked to the real workspaces. These are content groupings only, not departments, offices, ranks, or additional staff.

The Platform & Team page uses `nicegui_app.ui.platform_summary.load_platform_summary` to combine only the existing `handover_readiness()` counts and display-safe release evidence. Its public interface contains active-prefect count, roster-week count, a verified-backup boolean, and release state/check totals. It deliberately omits names, class, leave, roster content, audit payload, database paths, and backup paths. A read failure is logged through the existing payload-free support reference and produces a neutral bilingual fallback while the rest of the page remains available.

NiceGUI owns the rendering and navigation. The read model introduces no schema, policy, write, backup, or restore change. `/system-architecture` links back to `/platform` rather than duplicating its team-responsibility overview, work-area summary, solution portfolio, and co-creation close.

`/engineering` reads only `load_release_evidence()` and static, version-controlled structural facts. It never opens `RosterWorkflow`, a database session, a backup path, or an audit payload. The report badge may show passed, running, stale, failed, missing, or unreadable evidence; the page does not reinterpret a non-passing state as success. Its gate labels mirror `scripts/verify_release_candidate.py`: repository hygiene, supply-chain security, Cloudflare gateway Deno contracts, the independent icon-interaction state machine, automated Python tests, Python compilation, dependency integrity, desktop browser verification, runtime performance／memory stability, isolated write pipeline, adaptive-phone verification, strict deployment readiness, unified Guest isolation, and committed-without-backup recovery. The visible passed/total ratio comes from the fingerprint-matched report rather than a hard-coded test count.

## Canonical entry and local maintenance start

> **Unified Guest architecture contract:** The formal host enables this path
> through its protected `SING_YIN_UNIFIED_GUEST=1` configuration. Any later
> candidate must preserve the same deny-by-default boundary and pass fresh
> candidate-bound verification before the origin or Worker is switched; changing
> source files in `D:\code_v3` does not change the protected live installation.

The only URL distributed to users is
`https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/`.

| State | Owning layer | Data adapter |
|---|---|---|
| Public `/` | Identity-neutral Worker entry shell | No application capability |
| Guest `/` after `POST /auth/guest/start` | Worker session + signed origin principal + shared NiceGUI renderer | Bounded process-memory `GuestWorkspaceAdapter` with fictional data |
| Admin `/` after `/auth/admin/start` | Access JWT → Worker session → signed origin principal + shared NiceGUI renderer | Official `RosterWorkflow` and SQLite |
| `/view#…` | Worker viewer shell + KV ciphertext + browser Web Crypto | Read-only published snapshot; no NiceGUI or SQLite read |
| Local maintenance | Loopback-only origin | Official or isolated practice composition under host controls |

`/guest` and `/try` are compatibility redirects to the unified entry rather
than separate static products. Localhost and enrolled private WARP remain
maintenance fallbacks, not additional normal entry points.

For host maintenance:

```powershell
python -m pip install -r requirements.txt
python -X utf8 -m nicegui_app.launcher
```

Open `http://127.0.0.1:8080` locally only while diagnosing, recovering, or
maintaining the host. The origin remains loopback in every deployment state.

`nicegui_app.launcher` is the production composition edge. It resolves the
database identity first and sets `NICEGUI_STORAGE_PATH` to the sibling
`nicegui-storage` runtime directory before importing NiceGUI. Administrator UI
preferences therefore survive immutable release-bundle replacement without
writing into source; Guest preferences remain bounded session memory and never
enter this directory. Direct `nicegui_app.main` imports are reserved for tests
and module-level diagnostics, not managed host startup.

### Verified `PageContext` and Guest adapter

`nicegui_app.access_context` defines translation-independent `AccessMode`,
`Capability`, `Principal`, and `PageContext` contracts. The Worker removes
browser-supplied identity headers and injects an HMAC-signed principal carrying
`mode`, `subject`, `sid`, `exp`, `auth_epoch`, and `kid`. The origin verifies
the signature and lifecycle before resolving a workflow.

Admin and Guest use the same routes, components, and DOM structure. The
composition root returns a `PageContextWorkflowAdapter` around the official
workflow for Admin／local maintenance, or a `GuestWorkspaceAdapter` for Guest.

Every official workflow call passes through `PageContextWorkflowAdapter`, wrapped by the runtime identity guard. The captured method rechecks principal expiry, current `auth_epoch`, current `kid`, and process-local revocation at invocation time, not only when the page or WebSocket is composed. It then binds the request reference and audit actor in concurrency-safe context and fails closed when a retry-sensitive method exposes `command_id` but the caller did not supply one. The fallback UUID is therefore limited to callables without that durable-write contract.

An established NiceGUI transport is not treated as continuing authorization. The shared shell schedules browser invalidation just before the signed principal expires, clears temporary browser state, completes origin-backed logout, and navigates away; focus, visibility and periodic `/auth/status` checks catch earlier revocation or identity drift. Independently, `current_page_context()` and every captured workflow method apply the server-side checks above. A delayed or deliberately retained socket therefore cannot authorize domain work after expiry, revocation, epoch change or key rotation. Explicit protocol-level socket closure can remain defence in depth, but it is not the security boundary and must not become a second session-lifecycle owner.

Guest idempotency stores bounded `_CommandReceipt` metadata rather than a full `GuestWorkspaceView` per command. A duplicate ID with the same request digest does not reapply the mutation and returns the current copy-safe workspace with `replayed=true` plus the original applied revision; a different payload with the same ID is rejected. Per-workspace eviction, global count/metadata bounds, session expiry and tab isolation keep memory proportional to current state plus bounded receipts.
The capability matrix is deny-by-default; UI disabling is only a presentation
aid and every service boundary rechecks the capability.

Guest workspaces are bounded to 30 minutes, 24 concurrent sessions, four tabs
per session, 40 fictional prefects, four weeks, 256 KiB signed snapshot, 5 MiB
per generated file, and 60 commands per minute. The shared generated-file
registry separately permits bounded Admin files up to 64 MiB, caps total live
content at 128 MiB, and reserves 64 MiB plus 16 tickets for Admin so Guest load
cannot starve an official handover or report. Each NiceGUI client receives a separate
workspace ID. Guest data does not enter SQLAlchemy, official SQLite, backups,
files, KV, AI, upload, external delivery, or background jobs. Guest exports are
memory-only, `DEMO`-marked, single-use, and `Cache-Control: no-store`.

`nicegui_app.services.guest_preferences.GuestPreferenceRegistry` is a separate,
bounded, origin-memory store keyed only by the Worker-verified Guest session.
It retains locale, appearance, music and sound across reconnects without using
SQLite, user storage or browser persistence, and is cleared with the Guest
session. `nicegui_app.ui.downloads.GeneratedFile` defines filename, media type,
content, access mode, cache policy and support reference for both Admin and
Guest. The browser uses a credentialed fetch, validates status and MIME, then
creates and revokes a short-lived object URL. The bounded registry binds every
single-use ticket to the verified access mode and session, rejects cross-mode
replay without consuming the ticket, and reserves delivery capacity for Admin
so Guest load cannot starve official exports.

`nicegui_app.services.roster_presentation.RosterSchedulePresentation` is the
shared read model for the browser matrix and bilingual PDF. It owns display
ordering only; eligibility and generation policy remain in `roster_policy` and
`roster_core`. Published-week withdrawal remains a `RosterWorkflow` transaction:
optimistic version, idempotent command receipt, inverse net ledger entries,
audit, backup obligation and external-share revocation outbox.

### Local support and incident boundary

`/support` is a presentation and diagnostic boundary, not a roster workflow.
`nicegui_app.services.support_incidents.SupportInbox` accepts untrusted text and
bounded TXT／JSON／PNG evidence only after an Admin explicitly consents. It
redacts known secret patterns, enforces quotas and lifecycle limits, hashes the
stored files, and commits an incident directory through staging plus atomic
rename. The inbox path is configured outside the official SQLite database,
fairness ledger, roster backups, generated PDFs, and Git inputs.

Every persistence call rechecks the Admin capability below the UI. Guest uses
the same `/support` page structure but can only build a browser-local report;
Public and Viewer use the Worker `/support` route with the same non-persistent
contract. None of these paths invokes `RosterWorkflow`, retries an operation,
opens a background queue, or sends content to GitHub. Maintainers inspect the
host-local inbox with `scripts/inspect_support_inbox.py`; the optional
`scripts/collect_host_security_summary.ps1` records control presence and status,
never secret values.

The HMAC snapshot codec and browser bridge are implemented. After each
meaningful Guest mutation, the adapter publishes the latest signed revision to
the exact connected tab, whose bridge stores only that token in
`sessionStorage`. On refresh, `POST /api/guest/snapshot/restore` accepts the
token only when the Worker-verified Guest session, stable NiceGUI tab,
workspace, application boot, revision and per-connection nonce all match.
Duplicate tabs receive new workspace IDs; copied, tampered, expired, stale or
old-boot tokens are rejected and replaced by a newly signed token for the safe
fictional fixture. Logout, expiry and revocation clear the browser state and
process registry idempotently. The detailed contract is
[Unified guest security model](UNIFIED_GUEST_SECURITY_MODEL.md).

## Durable Data Contract

### Official/practice composition boundary

`nicegui_app.application_mode.ApplicationModeSettings` is an outer composition profile, not a roster-policy rule. `official` remains the default and accepts the established injected paths. Its workflow always receives `seed_path=None`: migration may create a structurally complete empty database, but official startup never inserts demonstration prefects. `practice` starts only when database, backup, and log paths are all explicit, distinct, and contained by `data/practice/`; the runtime then injects those paths and the fictional `PREFECT_SEED_PATH` into `RosterWorkflow`. The practice launcher also uses a separate port range and NiceGUI storage secret.

The persistent shell banner and PDF marker receive the resolved mode as presentation input. They do not change eligibility, generation, fairness, publication, adjustment, backup, or restore behavior. `/healthz` exposes only the non-sensitive `applicationMode` identity so the two Windows launchers cannot reuse the wrong process. `scripts/reset_practice_mode.py` verifies its fixed workspace boundary and refuses to reset while a practice service is running.

- Live data: `data/runtime/sing-yin-roster.sqlite3`
- Schema migrations: `migrations/` via Alembic
- Automatic backups: `data/backups/`
- Canonical devotionals: `data/devotional/daily-verses.seed.json`
- Practice-only fictional prefect seed: `data/demo/prefects.zh-HK.seed.json`

Before workflow bootstrap or migration, `nicegui_app.process_lock` acquires a
process-lifetime lock keyed by the resolved absolute database path. A second
NiceGUI origin targeting the same SQLite file exits safely rather than racing
Alembic or serving a second writer. This does not make SQLite a multi-origin
database; v1.2 supports one origin process with multiple users and tabs.

The workflow service is the only supported write path for roster operations:

1. Generate: accepts the stable Assist. assignment code `legacy_fixed_weekday` or `flexible_weekly`, validates school policy, and saves or replaces the Monday-based draft together with that mode. NiceGUI owns only the bilingual label-to-code mapping. Fixed-weekday mode keeps canonical AHP weekdays while the active AHP directory and availability remain unchanged, using a qualified substitute for the affected duty when leave is recorded and stopping with a controlled vacancy error if none exists. Flexible weekly mode uses the Monday date as a deterministic rotation key and the previous active week's Assist assignments as a secondary anti-repeat input; persistent history load remains the primary fairness cost. Both modes enforce AHP-only Assist. eligibility, selected weekday availability, declared leave, same-day uniqueness, and no-consecutive-duty constraints. Ordinary Study Prefects remain room-only in either mode. Their candidate order remains fairness-first, but a deterministic backtracking solver uses per-day bipartite-matching feasibility and failed-state pruning to recover when the locally preferred choice would block later coverage. A 50,000-node search budget prevents pathological availability combinations from holding the request indefinitely; budget exhaustion returns the same controlled review-availability／leave guidance and never saves a partial result. Final validation rejects an empty result, any missing／extra canonical weekday-seat pair, and any non-canonical duty weight; generation returns a complete valid roster or a controlled no-solution state, never a partial week.
2. Publish: validates again, posts every assignment to `fairness_ledger`, then updates persistent `history_weight`.
3. Leave adjustment: reverses the original weight, credits an eligible substitute when supplied, updates the published roster, and records an audit event.
4. Prefect management: creates, updates, or archives active roster members without erasing historical fairness records.
5. Pre-generation leave: records an auditable absence constraint for a Monday-based week; generation and validation exclude that prefect on the declared day. Publish validates the current declarations again, so a draft made before a new leave declaration must be regenerated. Published weeks must use post-publication adjustment instead.
6. Prefect data import: accepts bounded `.csv`／`.xlsx` files or pasted JSON／CSV, normalizes them locally, requires an operator-reviewed field mapping and data preview, then imports only after an explicit action through the ordinary workflow transaction.
7. PDF export: builds a bilingual A4 PDF in memory from durable roster reads; it is a local download and never a public upload. Versioned Noto Sans HK Regular/Medium/SemiBold files make output deterministic on a replacement host. The schedule export accepts presentation-only crest and supplementary-footer switches; clean group-sharing output is the default.
8. Period reporting: reads published roster weeks, final active assignment state, leave adjustments and the fairness ledger to build one immutable report model. Chinese preview, bilingual PDF and checksummed JSON are presentations of that same model; report generation performs no roster, ledger, backup or audit write.

`nicegui_app.persistence.database.database_readiness()` remains the schema-readiness contract used by `/healthz`. A SQLite file is healthy only when it opens read-only, passes `PRAGMA quick_check`, contains the complete table set derived from current SQLAlchemy metadata plus `alembic_version`, and reports the current Alembic head. `/readyz` adds runtime admission: real workflow sessions must have initialized, no active maintenance or recovery-required marker may exist, no backup obligation may remain pending, and startup repair must not have failed. Deployment and load admission must check both endpoints; `/healthz` alone is insufficient.

Alembic migration `0011_assist_assignment_mode` adds the roster-level mode field and backfills existing weeks to `legacy_fixed_weekday`, preserving the historical fixed-weekday rule. Every new or regenerated roster stores exactly one stable mode code, so a later UI preference change cannot silently reinterpret an existing draft or published week. Guest uses the same code and validation path through its in-memory adapter; only the persistence destination differs. A downgrade is permitted only while all persisted roster history remains `legacy_fixed_weekday`; the presence of any `flexible_weekly` history blocks downgrade so provenance cannot be silently discarded.

Migration `0011_assist_assignment_mode` is a documented provenance exception: the original rc20 migration identity is retained, the executed upgrade and schema are unchanged, and only the downgrade guard was corrected so any persisted `flexible_weekly` history blocks provenance loss. Future released migrations must not be silently edited; a semantic correction requires an explicit audit record, unchanged-upgrade proof, both downgrade branches, a linear-chain check, and isolated recovery evidence.

Published-duty substitute recommendations and the final leave-adjustment save share the same role, availability, declared-leave, same-day uniqueness, and no-consecutive-duty gates. A previously recorded absence cannot become eligible merely because the adjustment happens after publication.

Each interactive official write claims an `operation_commands` receipt inside the same transaction as its result and creates a `backup_obligations` row before commit. The command ID and normalized fingerprint make exact retries replayable while rejecting reuse with different content. The obligation is marked complete only after the SQLite online backup, manifest, SHA-256 and integrity verification succeed. On a normal safe startup, unfinished obligations are repaired before accepting work; a failed repair leaves `/readyz` degraded and the centralized workflow admission guard rejects every business write, including new-school-year rollover and external-share delivery. If a durable recovery marker already exists, bootstrap enters diagnostic-only mode before migrations, SQLAlchemy session creation or SQLite journal mutation. Data-free health/readiness remains available, but no business write can run until controlled recovery and a safe restart create real workflow sessions. Removing a marker alone cannot promote the already-running diagnostic-only process. This removes the crash window where the database commit succeeded but no durable recovery point was recorded without pretending that a marked database is writable.

Publication has a database-level single-winner claim: the `roster_weeks` row changes from `draft` to `published` only through a conditional update inside the same transaction that writes fairness-ledger entries. A second tab or concurrent local client is rejected before it can post duplicate workload points.

Prefect creation, update, archive, and bulk import follow the same backup rule. These writes, pre-generation leave changes, draft generation and draft-patch save enter SQLite through `BEGIN IMMEDIATE` before reading the state they intend to change; this serializes the read／validate／write window instead of relying on a duplicate-click guard. Prefect rows carry a stable integer version. Update and archive use an active-row plus version compare-and-swap. `patch_prefects_batch` validates every allowlisted patch, active record and expected version before mutation, supports a valid Assistant Head fixed-weekday swap by clearing only the targeted unique-index values inside the same transaction, then applies all updates, availability, audit and one command receipt atomically. A conflict or validation error rolls back the claim and returns zero updated rows. `apply_draft_patch` compares the reviewed roster-week version and validates the complete staged matrix; a stale browser receives a conflict with reload／compare／reapply choices rather than overwriting a newer save. Archive remains a soft delete because published rosters and fairness-ledger records must remain historically truthful. The page therefore requires a destructive-action confirmation which explicitly says that historical rosters, fairness records, and audit evidence are retained and that there is no immediate undo.

`fixed_general_duty`／`fixedGeneralDuty` remains stable compatibility metadata for canonical AHP weekday mapping. The prefect dialog exposes it only for Assistant Head Study Prefects as an optional fixed weekday in legacy mode; flexible mode ignores it. The first accepted automatic legacy mapping persists every one-person／one-day assignment into this field in the same draft transaction, so later directory additions cannot silently move existing owners. When the dialog edits an ordinary prefect or unrelated fields, it must round-trip any existing value rather than replace it with `NONE`. The visible availability selector is authoritative: a fixed weekday must also be selected as available, and unselected days are unavailable to both Assist. modes and room generation.

### Draft matrix, whole-day closures, and week-local slot exceptions

Alembic `0013_roster_day_closures` is the deployed additive whole-day migration. It introduces `roster_day_closures`, keyed by the roster week and stable weekday code with one row per week／day. Source-only additive migration `0014_roster_slot_exceptions` adds `roster_slot_exceptions`, uniquely keyed by roster week, stable weekday, post code, and slot index. Optional `reason_code` and `note` are audit context only; translated UI text is never a key. These tables are week-local override layers. They do not replace the permanent room-opening rules owned by `roster_policy` and do not create a school-wide holiday calendar.

`RosterSchedulePresentation` is the shared read model for NiceGUI draft／published views, the bilingual PDF, the public share whitelist, and the Guest adapter. It contains the roster week, version, status, weekday and date, stable post code and slot, English duty-post label, service time, Chinese display name, assignment／prefect identifiers, editability, and exactly one of these states:

- `assigned`: one eligible prefect is assigned;
- `vacant`: the post is open and requires a prefect;
- `room_closed`: the long-term room policy closes this post on this weekday;
- `unavailable`: the operator closes only this slot for the selected roster week;
- `day_closed`: the whole weekday is closed for this roster week.

Precedence is fixed: `day_closed` overrides `room_closed`, which overrides `unavailable`, which overrides `assigned`／`vacant`. An unavailable slot is excluded from generation, required coverage, and fairness denominators; reopening it produces a vacancy and never restores a previous assignment.

Blank editor input is not serialized as a state. The presentation builder, PDF exporter, Viewer/public-share serializer, and responsive day-card adapter must consume this same state model; they may change layout and localized labels but not derive a second interpretation of the roster.

The public draft-edit contract consists of `WeekScheduleOverrides`, `DraftCellEdit`, `DraftDayEdit`, `DraftSlotStateEdit`, and:

```text
apply_draft_patch(
    *,
    roster_week_id,
    expected_week_version,
    cell_edits=(),
    day_edits=(),
    slot_edits=(),
    reason=None,
    command_id=None,
)
```

`reason` and `command_id` are optional at the API boundary. The UI presents the reason as optional; the workflow normalizes a missing reason to an empty audit note while still requiring at least one explicit cell, weekday, or slot edit. Production callers should provide a unique `command_id` whenever an operation may be retried so the same decision remains idempotent. The UI retains that ID across a retry and creates a new one only after the local patch changes.

NiceGUI keeps cell, day, and slot edits local until the operator selects **Review and save**. Pointer drag, touch two-step move, keyboard move/exchange, undo, and redo only alter this local patch. The workflow then enters one `BEGIN IMMEDIATE` transaction, claims the idempotent command receipt, compares the expected roster version, constructs the final matrix, and revalidates role eligibility, selected availability, pre-generation leave, same-day uniqueness, non-consecutive duties, legacy fixed Assist ownership, and canonical slot coverage after applying whole-day and slot closures. A same-day two-cell swap is therefore atomic. The transaction updates the roster version and closure／slot rows, creates the audit and backup obligation, and commits all or none of the patch. Draft edits never post to the fairness ledger; publication remains the only initial fairness-posting boundary.

Closing a day clears every draft assignment for that weekday inside the same transaction. Reopening the day removes the override but deliberately returns open cells as `vacant`; it never restores assignments whose availability, leave, fairness context, or role may have changed. A completely closed week is a valid zero-assignment draft and may be published with zero fairness points and zero scheduled service time. Published rosters reject `apply_draft_patch`; the operator must use the audited withdrawal transaction before rebuilding a wrongly published week. A late individual absence continues to use the published-duty adjustment workflow instead.

A version conflict is a controlled result, not a last-write-wins update. The UI retains its local patch and offers reload, comparison, and reapplication against the latest presentation. Reapplication still passes the complete workflow validation. Guest implements the same API and states in its bounded in-memory workspace, but never opens the official SQLAlchemy session, creates official backup／audit／fairness rows, or calls external sharing. See [Draft grid and whole-day closure](ROSTER_DRAFT_EDITING.md) for the operator and maintainer contract.

### Read-only reporting and reviewed import boundaries

`ReportingWorkflowMixin.build_period_report()` is the only owner of period-report facts. It accepts whole roster-week boundaries represented by Monday dates and includes published weeks only. It resolves the final active assignments after published-duty adjustments, reconstructs the historical fairness distribution from persistent anchors plus immutable ledger entries, and records each source roster version and policy version. Drafts never enter the model, and asking for a preview cannot post or repeat workload.

The report deliberately calls service time **scheduled allocation**. `DUTY_SERVICE_TIME_WINDOWS` supplies the actual 15:40–17:00 duty duration for every post, while `ROOM_OPENING_TIME_WINDOWS` separately retains the longer 302／Assist. room-opening display. The application has no attendance or completion register, so the resulting hours cannot be interpreted as attendance, performance, completed service or a certificate. Likewise, `summary_report_export.py` produces a checksummed JSON evidence envelope for review and archiving, not a restorable database. Full recovery remains exclusively owned by a verified SQLite handover package. Neither exporter uploads a named report to GitHub or another service.

`prefect_file_import.py` is a bounded local parser. It accepts only `.csv` and plain `.xlsx`, limits size, rows and columns, rejects formulas and unsupported legacy／macro-enabled workbooks, and exposes a stable target schema. The NiceGUI page lets the operator select a worksheet, map each required target, validate a normalized preview and explicitly confirm the final import. Only that last action enters `RosterWorkflow.import_prefects()` and its normal transaction／backup boundary.

`prefect_import_assistant.py` is a replaceable, optional schema-assistance adapter, not a data-import owner. It is disabled by default and reads `SING_YIN_DEEPSEEK_ENABLED`, `SING_YIN_DEEPSEEK_MODEL` and `SING_YIN_DEEPSEEK_API_KEY` from the local environment at call time. After an explicit operator click, its request contains only exact column headings, anonymous value-kind labels and coarse non-empty-count buckets. It never receives raw rows, Chinese names, the workbook or the final import result. Returned mappings are restricted to the visible source headings and approved target codes, then remain untrusted suggestions until the operator reviews the selectors, builds the local preview and confirms import. Manual mapping is always available. A fresh API key belongs only in the ignored local `.env`; it must not enter source, documentation, logs, backups or Git history.

### Public roster share boundary

`nicegui_app.services.public_roster_share.PublicRosterShareService` is an outer application adapter, not a new policy or persistence owner. It can read only an existing `published` roster through the stable workflow facade. It composes a presentation-ready whitelist containing week/date, duty post, duty-service time, Chinese display name, and closed/vacant state. It rejects drafts, missing required slots, duplicate slots, unexpected assignment status, and any non-Chinese display name before an external request.

Each share receives a random identifier, independent 256-bit AES-GCM key and 96-bit nonce. The service encrypts the JSON snapshot locally with authenticated additional data bound to that identifier. `CloudflarePublicRosterShareGateway` sends only schema version, share identifier, week, created/expiry times, nonce and ciphertext to the authenticated Worker admin endpoint. The resulting URL places the key after `#`, so it is absent from the initial HTTP request and Worker/KV record. The complete link is displayed once and is not persisted in SQLite, backups, audit, or logs.

Workers KV is globally eventually consistent, so a successful administrator write is not by itself proof that a newly issued link is already readable at the public edge. After creation, the gateway polls anonymous `POST /api/view` without the administrator bearer token and accepts success only when the public response contains the exact expected schema, nonce, ciphertext and equivalent expiry instant. This bounded visibility fence runs outside the NiceGUI event loop through the existing progress workflow. If the exact record does not become readable within the configured window, no URL fragment or AES key is issued to the operator. New version-2 create receipts include the non-secret content digest, allowing the gateway to request deletion of that exact content-addressed KV key without depending on a possibly stale prefix listing; the UI still describes this accurately as a withdrawal request rather than claiming immediate global disappearance. `SING_YIN_PUBLIC_ROSTER_VIEWER_VISIBILITY_TIMEOUT_SECONDS` defaults to 75 seconds and is deliberately separate from the per-request HTTP timeout.

v1.2 adds `external_share_outbox` beside the operation command receipt. A
share intent is committed with the authoritative roster week, version and
content digest before the HTTP delivery begins. Delivery claims, successes and
categorical failures update that same record, so a lost response or retry does
not silently create an unrelated share. The outbox stores no AES key and does
not turn Worker delivery into a roster-policy write.

Published-duty correction and roster withdrawal use the same sharing-owned invalidation seam. Inside the roster transaction, every outbox row that could have reached the Worker and no longer matches the authoritative version becomes `revocation_pending`; a still-pending operation receipt is converted to compact revocation metadata so its queued delivery payload and decryption key cannot be replayed. The transaction returns stable share identifiers, and the UI immediately attempts idempotent Worker deletion outside that transaction. Edge failure therefore leaves a durable revocation obligation without rolling back, repeating or misreporting the already committed roster／fairness／backup result. Exact adjustment replay returns the same identifiers, while a share created for the corrected version is excluded by its roster version. `ExternalShareOutboxMixin` owns these state transitions; `RosterLifecycleMixin` only declares that a version became obsolete.

`cloudflare/roster_viewer/worker.js` is the canonical outer front door. Public `/` serves the identity-neutral entrance. Its same-composition light／dark editorial scene is deployed from `cloudflare/roster_viewer/public/assets/` through Wrangler static assets; the files carry no identity or roster data, while all meaning and accessibility remain in the Worker HTML. `POST /auth/guest/start` creates the bounded Guest session; `/auth/admin/start` enters Access; `/auth/status` rechecks mode, expiry and origin health; `/auth/logout` clears the application identity. `/guest` and `/try` redirect to the unified entry. `POST /api/support/incidents` is the only Public origin operation: the Worker enforces same-origin, body and rate limits, then injects a 60-second request-bound principal containing only `support.report.submit`. For verified Admin／Guest modes, the Worker strips browser identity headers, signs the origin principal and proxies HTTP／WebSocket through `ROSTER_ORIGIN`. The origin resolves the adapter; the Worker never accepts a browser-declared role.

`/view#…` is a separate public capability path, not the Guest workspace. New `ROSTER_SHARES` records use immutable `share:v2:<shareId>:<SHA-256>` keys whose digest covers the normalized encrypted payload; exact retries resolve to the same key, while different content can never overwrite another record that happens to carry the same share identifier. The Worker continues to read and revoke legacy `share:<id>` records without rewriting them. Because Workers KV offers no compare-and-swap, `view` and `list` fail closed whenever multiple digests, mixed legacy／v2 records, or an invalid digest become visible. Anonymous `/api/view` accepts only one validated share identifier; browser Web Crypto decrypts locally, and DOM rendering uses `textContent`. This path uses KV but still has no VPC, NiceGUI or SQLite access. The public HTML/CSS/JS are same-origin and dependency-free, with no-store, CSP, no-referrer, noindex, frame denial and permissions restrictions.

The administrator transition still enters the Cloudflare Access protected path. The Worker verifies the Access JWT signature, `aud`, `iss`, `exp`, and exact administrator email before issuing its bounded HttpOnly session. Guest and Admin cookies are mutually cleared during mode transitions. Neither cookie nor the Access assertion is forwarded to the origin; only the newly signed principal is injected. There is no application password table, hash or password-recovery flow.

The in-app access-control surface creates same-host links for published rosters and lists/revokes active KV records. Revocation deletes ciphertext; KV propagation may take about one minute. A share token never promotes a guest to OP. The canonical root, `POST /auth/guest/start`, `GET /auth/status`, `POST /auth/logout`, and `/auth/admin/start` remain public Worker routes; `/auth/admin/start` redirects into the only Access-protected callback, `/auth/login`. After login, the Worker verifies its signed first-party administrator session before every NiceGUI proxy request. Logout clears that cookie before continuing to Cloudflare Access logout.

## Recovery and Handover

Use **Settings -> Backup restore** only when the operator intends to return the live system to a known snapshot. The workflow accepts only a self-contained `.sqlite3` snapshot and same-name JSON-object manifest from `data/backups/`. It rejects adjacent `-wal`, `-shm` or `-journal` sidecars, invalid／mismatched manifests or digests, pending backup obligations, and unknown／future migration revisions. Before any live swap, it copies the exact database and manifest bytes to a private staging area, re-verifies both digests there, and performs all further work on that immutable candidate. Supported legacy snapshots from revision `0007` through the current chain are migrated in isolation to the current head; a current-head snapshot must already satisfy the full current table contract. The candidate then passes foreign-key and fairness reconciliation before the workflow creates a `pre_restore` safety snapshot, atomically replaces the SQLite database, rebuilds its connections, records an audit event, and creates a verified post-restore snapshot. If reconnect or audit fails after the swap, the workflow automatically reinstalls the safety snapshot; only an unproven rollback leaves the durable recovery-review marker. A successful restore finishes with no pending backup obligation and is write-ready only after all admission checks pass.

Restore is protected by a host-wide maintenance admission protocol, not only a Python-thread flag. Every ordinary workflow operation owns one payload-free lease file beside the database, including the full commit-to-snapshot fence. Maintenance obtains an exclusive marker with `O_EXCL`, waits up to 30 seconds for leases from this and other host processes to drain, and rejects new work while the marker exists. This means restore cannot enter while a verified snapshot is still being built. A process that loses the marker race never removes the winner's marker. Stale lease files are removed only when the recorded process is no longer alive; the explicit recovery marker is preserved for human review. The same-process condition remains an efficiency aid, while the filesystem marker, leases and payload-free serialized-operation database are the cross-process safety boundary.

**Settings -> Create handover backup package** remains the human handover download. Immediately before ZIP creation, the workflow privately stages and re-verifies the selected database／manifest pair; the in-memory download contains that exact pair plus notes and is never uploaded. It is useful for a controlled successor transfer, but downloading it does not by itself prove off-site disaster recovery.

`nicegui_app.services.offsite_recovery` is the host-loss deep module. Its two public operations export a fresh verified handover package with a path-free receipt, then inspect and restore only from the copied bundle in a temporary replacement workspace. The receipt binds target-evidence digest, immutable release／commit／tree, schema, timestamps, package／snapshot／manifest SHA-256 and measured RPO. Inspection rejects reparse points, unsafe names, size changes, duplicate／unexpected／encrypted／traversal／symlink ZIP members, digest drift and unsupported application verification; the drill requires row-count parity, balanced fairness and exactly one restore audit. `scripts/offsite_recovery.py` is the bounded CLI. `scripts/export_offsite_recovery.ps1` is the outer Windows adapter and must itself run from the active immutable bundle; it alone validates Administrator ownership, scheduled-task identity, external USB／SD topology, non-system disk, NTFS, BitLocker fully encrypted／protection on and stable volume identity. No internal-disk or host-bound encryption fallback exists.

The current source capability does not claim a real off-site copy or deployed support. RPO／RTO, retention, key custody, safe removal and replacement-host steps are owned only by [`OFFSITE_DISASTER_RECOVERY.md`](OFFSITE_DISASTER_RECOVERY.md). Managed installation still occurs through the existing restore workflow; never overwrite `data/runtime/sing-yin-roster.sqlite3` manually.

Both handover packaging and managed restore depend on `workflow.backups()` returning at least one snapshot whose current checksum, manifest, SQLite integrity, and required tables verify successfully. If none exists, NiceGUI renders a bilingual recovery empty state, exposes **Create verified snapshot now** as the only productive action, and keeps package/restore controls disabled with `aria-disabled`. It does not open a confirmation that cannot succeed or send an expected empty-state condition into the support-error path. The ordinary browser smoke proves this no-write state; the full write pipeline proves the controls become enabled after real verified snapshots exist.

`verify_backup` also returns a stable `reasonCode` alongside maintainer diagnostics. `backup_inventory` counts only the recently checked managed snapshots and groups failures as file, manifest, checksum, SQLite integrity, sidecar presence, unsupported migration, pending obligation, schema, or unknown. A manifest whose top level is not a JSON object is classified as `manifest_invalid` rather than crashing inventory. NiceGUI translates those codes and counts but never renders the raw `error`, a database row, or file contents. Invalid snapshots remain visible as a trust warning while valid snapshots continue to power package/restore actions; the two states are not mutually exclusive.

Recent snapshot verification is parallel but never cached. `backups()` captures each candidate's modification time once, preserves newest-first order, and verifies at most four independent read-only SQLite files concurrently. A file that disappears during candidate scanning is skipped; one removed before checksum becomes the controlled `missing_file` result instead of a Settings 500. Every Settings visit still recomputes manifest checksum, SQLite integrity, migration support, pending-obligation state and the required-table contract. Handover-package creation uses a different newest-first lazy scan: it verifies one candidate at a time, stops at the first valid snapshot, then privately re-stages and re-verifies the selected database／manifest bytes immediately before packaging. Old invalid history therefore cannot turn into trust, and a path substitution between inventory and packaging cannot alter the trusted payload.

## Long-operation feedback

Roster generation, publication, manual draft changes, published-duty leave adjustment, pre-generation leave declaration/cancellation, prefect creation/update/archive, bulk import, PDF/report creation, verified snapshot/handover packaging, restore, and host-local support persistence run through one bilingual progress coordinator. The coordinator waits 140ms before constructing a loading surface: faster operations finish with press／glyph acknowledgement only, while longer operations whose progress cannot be measured use an honest indeterminate state. Phase names appear only when the backend supplies actual operation events; determinate progress is valid only for real monotonic `completed／total` data. Results render as soon as they are available, with no fake minimum delay or fixed 14%／56% values. The durable work runs outside the NiceGUI UI event loop; the existing workflow service remains the sole owner of transactions, fairness changes, and snapshot timing. `_safe_read_action` is reserved for short, bounded, read-only candidate and preview lookups and must not become a write path.

`nicegui_app.ui.navigation` owns a separate route-progress runtime. Navigation records the existing focus intent immediately but reveals the top track only after 150ms, then clears timer, ARIA and visual state on `pageshow`, `pagehide` or replacement. It never supplies a percentage and does not compete with a consequential-operation dialog. The public Worker has an independent but equivalent Admin／Guest entry controller: role-specific `starting／navigating／slow／error` states drive both desktop and mobile duplicates, while a delayed eight-second slow state invalidates late playback settlement and unlocks an explicit retry. Welcome audio remains a trusted-click enhancement and cannot gate navigation.

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
| Workflow | `nicegui_app/services/roster_workflow.py`, `nicegui_app/services/workflow_parts/` | Stable facade plus separated transactions, fairness ledger, people, backups, adjustments, recovery, and read-only period-report composition |
| Access composition | `nicegui_app/access_context.py`, `gateway_identity.py`, `runtime.py`, `operation_context.py` | Verify signed principals, resolve deny-by-default capabilities and bind one request/client to the official or Guest adapter |
| Guest workspace | `nicegui_app/services/guest_workspace.py`, `guest_adapter.py` | Bounded fictional memory state, signed snapshot codec and per-tab revision; no official persistence or external integration |
| Generated-file delivery | `nicegui_app/services/guest_downloads.py`, `nicegui_app/ui/downloads.py` | Bounded Admin／Guest registry with verified access-mode and session binding, reserved Admin capacity, one-shot Guest no-store semantics, credentialed fetch and status／MIME validation before browser save |
| Presentation | `nicegui_app/ui/page_routes/`, `page_shared.py`, `i18n_catalog/`, `theme_markup.py`, `assets/css/sing-yin-*.css`, `motion.py` | NiceGUI routes, shared components, domain-grouped bilingual copy, versioned design-system layers, canonical command-centre composition, paired local material textures, local motion bootstrap, page shell, accessible fairness-weight chart, anonymous platform summary, and non-sensitive operating／architecture explanation |
| Import adapters | `nicegui_app/utils/prefect_import.py`, `prefect_file_import.py`, `nicegui_app/services/prefect_import_assistant.py` | Bounded local normalization and optional heading-only mapping suggestions; no policy or direct persistence writes |
| Export | `nicegui_app/services/roster_export.py`, `summary_report_export.py` | Local-only bilingual roster／report PDF and report-JSON composition; no persistence or upload writes |
| Public share adapter | `nicegui_app/services/public_roster_share.py`, `nicegui_app/ui/access_control.py` | Explicit minimum-data snapshot, local AES-GCM encryption, same-host link receipt, active-link listing and revocation; one exact create body may be replayed once after transport loss and returns the original receipt, while conflicting reuse is rejected; Worker-owned public paths never become NiceGUI editing sessions |
| Canonical edge runtime | `cloudflare/roster_viewer/worker.js`, Cloudflare Access, Workers VPC, KV `ROSTER_SHARES` | Serve the public entrance and Viewer; create verified Guest/Admin sessions; strip forged identity; inject signed origin principals; proxy authenticated modes through VPC／Tunnel to loopback NiceGUI |
| Observability | `nicegui_app/observability.py`, `nicegui_app/persistence/migrations/env.py` | Payload-free local operation evidence and rotating support logs; Alembic preserves existing application loggers and local logging defensively re-enables its logger after migration |
| Optional media | `nicegui_app/services/online_music.py`, `music_library.py`, `json_catalog.py`, `youtube_audio_import.py`, `nicegui_app/ui/music.py` | Public YouTube playlist validation/search, visible playback, appearance-recommended local playlists, and bounded local audio import; a re-entrant Windows named mutex／POSIX `flock` protects the complete cross-process read／modify／write window, while a unique fsynced temporary file and atomic replace protect the JSON bytes; strictly separate from roster persistence |

Business rules must never be implemented in UI event handlers. UI translation keys must never be used as database values or policy inputs.

Frontend composition has its own maintained seam. [`FRONTEND_ARCHITECTURE.md`](FRONTEND_ARCHITECTURE.md) maps shell, route-family, CSS-layer, responsive-runtime and public-entry ownership; `Professional_Design_System.md` remains the design-language owner. `nicegui_app/assets/css/sing-yin-command-center-v2.css` is the single terminal composition layer loaded last by `theme_markup.py`. It resets the mature interface around a task-first Quiet Command Center without becoming a second source for identity, capability, workflow or data behaviour. New page-local visual grammars and a second terminal override layer are prohibited. Stable v2 rules should move down to their canonical token／layout／component owner only in a bounded migration with rendered evidence and removal of the superseded compatibility rule.

### Local motion and interaction-sound boundary

The motion layer is presentation-only. `nicegui_app/ui/motion.py` conditionally loads the versioned, same-origin GSAP core at `nicegui_app/assets/vendor/gsap-3.13.0.min.js` only when the browser has not requested reduced motion. `nicegui_app/assets/motion/sing-yin-motion.js` then discovers approved non-sensitive narrative surfaces and hydrates Material icons into stable action-intent roles; the reduced-motion branch reaches the same readable static state without fetching GSAP. It performs one-shot transform/opacity entry, capped evidence-card stagger, pointer-light smoothing, semantic icon hover／focus／press／navigation states, and a short operation feedback pulse. `nicegui_app/assets/css/sing-yin-interaction-v1.css` owns the visual states, including busy, disabled and reduced-motion fallbacks, so no per-button listener or page-specific animation policy is required. The Platform operating map uses the same bounded group reveal and 2px fine-pointer response to explain operator intent → UI → policy → workflow → evidence → output; it is not a second policy implementation. The motion layer does not read or receive prefect, roster, leave, fairness, audit, backup, PDF, database, or translated policy values; it does not own navigation or transaction timing.

The history-priority chart is also presentation-only. It visualises the existing ranking formula as two horizontal factors: persisted historical workload multiplied by the selected 0.8–2.0 value, and current generated-week workload fixed at 1.0. It uses the same ISO week key as the slider, updates in place, exposes an ECharts ARIA description, and never changes post weights, eligibility, policy validation, publication or the fairness ledger.

The runtime uses `IntersectionObserver` instead of scroll handlers and fails open to a fully visible static page if GSAP is unavailable. The shared `MutationObserver` also hydrates icons created later by NiceGUI without registering control-local listeners. `gsap.matchMedia()` owns fine-pointer branches when GSAP is present; an earlier loader check and an immediate local hydrator own the no-GSAP reduced-motion path. An idempotent disposer disconnects the intersection/mutation observers, aborts pointer listeners, clears semantic-feedback timers and attributes, removes generated pointer lights, and detaches global feedback handling. `prefers-reduced-motion: reduce` bypasses the GSAP download plus entry, stagger, pulse, icon intent transforms, hover translation, and cursor-light rendering. ScrollTrigger, pinned sections, parallax, repeating timelines, and decorative loops are not part of the application.

The material layer is also presentation-only. Four small local SVG tiles form two same-geometry theme pairs: paper fibre for the page ground and bounded editorial surfaces, and linen weave for the sidebar identity structure. They repeat locally, remain pointer-transparent and carry no text or application data. CSS placement is deliberately allowlisted; form controls, tables, mobile roster／prefect records, fairness data, warnings, export controls and PDF composition are excluded. Light／dark and phone opacity are independent tokens, while the semantic DOM and layout stay identical.

NiceGUI browser identity is deliberately resolved before work crosses a thread boundary. Guest snapshot publication captures the connected `Client` and invokes that client's JavaScript bridge rather than the ambient `ui.run_javascript`, so a memory-workspace commit can safely finish in `run.io_bound`. PDF preparation similarly resolves the verified `WorkspacePort` and DEMO/export mode on the UI thread before the local renderer runs in a worker thread. Focused tests execute both paths from real worker threads and fail if they attempt to rediscover page identity there.

Pointer light is deliberately narrower than narrative entry. Only real link/action containers and the non-sensitive co-creation surface may receive it. Static workflow steps, architecture layers, onboarding, handover, storage explanations, tables, forms, warnings and evidence cards remain visually static so a hover treatment cannot imply an unavailable action.

`nicegui_app/ui/sound.py` owns the separate action-triggered Web Audio cues. An unset preference resolves to enabled without writing a value; an explicit Admin or bounded-Guest true／false choice is preserved. Navigation, an accepted long operation, and successful completion have distinct short tones; page load, hover, form error, and background ambience remain silent. Every eligible cue also dispatches a non-audio `sy:feedback` event, so sound-off operation retains visual acknowledgement. Music remains a separate operator-started media layer and is never synchronized to UI sound.

### Optional YouTube boundary

The official integration uses a visible `youtube-nocookie.com` iframe with native controls and no autoplay. A public playlist needs neither sign-in nor an API key. `SING_YIN_YOUTUBE_API_KEY` only unlocks public Data API search and is read from the local environment; it is never persisted by the roster workflow. Saved public playlist IDs live in the ignored local file `music/youtube-playlists.json`.

The embed does not enable the unused JavaScript control API, sends no referrer, and lazy-loads only after the operator opens the music window. Search-result images are accepted only from official YouTube thumbnail hosts. Dynamic HTTP responses carry `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, clickjacking/content-sniffing protection, and a camera/microphone/geolocation deny policy; static assets and NiceGUI internals are not forced into the no-store policy.

The media layer may receive page context (`dashboard`, `devotional`, `getting_started`, `guide`, `architecture`, or `handover`) but never a prefect, roster, leave, fairness, audit, backup, or PDF payload. No music control appears on sensitive roster tables or settings recovery actions. With no saved playlist, the UI renders guidance but creates no iframe, avoiding an unnecessary third-party connection.

`MusicLibrary` also owns two stable profile codes: `bright` and `quiet`. The stored preference is `auto`, `bright`, or `quiet`; `auto` resolves light appearance to Bright focus and dark appearance to Quiet reflection. An explicit operator selection overrides appearance. Profile changes affect only the next locally selected catalogue and never autoplay audio. The 32-track catalogue stores human-readable title/artist plus stable arrangement codes, so vocal and instrumental editions remain distinct while byte-identical `(1)` files are never registered twice.

`YouTubeAudioImporter` is a separate, replaceable adapter around the hash-locked `yt-dlp` Python wheel. It accepts only HTTPS YouTube/YouTube Music video, Shorts, or public-playlist URLs; it supplies no cookie, username, password, browser-login, or roster value. One isolated staging job is limited to 25 entries, 25 MB per file, and 150 MB total. Only signature-valid M4A results are atomically registered under ignored local storage `music/youtube-imports/`; source IDs prevent accidental duplicate imports, and failed staging is removed. The UI invokes the adapter with `run.io_bound`, shows an honest indeterminate bilingual state, and keeps the existing visible iframe as the preferred no-copy option. The evidence and rejected GUI alternatives are recorded in `docs/MUSIC_IMPORT_DECISION.md`.

Dashboard devotion uses the polished seed themes owned by `roster_core`. The UI persists only `auto`, `guidance`, or `comfort`; `auto` resolves from the current appearance while an explicit choice overrides it. `roster_core.select_daily_verse(..., themes_any=...)` performs the deterministic theme filtering, so translation labels and CSS never become devotional-selection inputs.

Official crest files are local presentation assets under `nicegui_app/assets/brand/`. Their semantic paths are centralized in `nicegui_app/config.py`: a 512-pixel derivative owns favicon delivery, the compact source owns navigation, a 640-pixel derivative owns architecture display, and the full source is reserved for PDF export. The user-supplied masters remain at project root; the old ambiguous `logo.png` is intentionally removed.

### Responsive roster presentation

`nicegui_app/ui/page_shared.py` creates one localized roster display model from the workflow's durable assignments; `nicegui_app/ui/pages.py` is now only the stable route-registration facade. Wide screens render that model as the inspection table; screens at phone width render the same model as day-grouped duty cards. Each card retains post, time, Chinese prefect name, status, and workload, so mobile review never depends on horizontal table scrolling. This is a presentation-only adaptation: it does not change policy inputs, workflow writes, PDF layout, or fairness calculations.

The same presentation boundary applies to the prefect directory: one localized display model drives the desktop table and phone identity cards. `nicegui_app/ui/edit_sessions.py` is the typed owner for unsaved page intent. `PrefectEditSession` merges originals and allowlisted pending fields before filtering／sorting, maintains one command ID for the exact batch and preserves every local edit across a zero-write conflict. `DraftEditSession` owns pending cells／days／slots, selection, move source, undo／redo, dirty count and reviewed-version reapply; it refuses assignments or moves on closed days and unavailable slots before the workflow repeats authoritative validation. These objects do not authorize or persist anything. The leave-adjustment page remains a workflow client, but its responsive form groups the original assignment, eligible-substitute decision, and optional reason into visible UI steps. Draft-change, published-duty adjustment, withdrawal, and pre-generation leave reasons are optional operator context; blank input is normalized consistently while version checks, command receipts, audit records, fairness reconciliation, and backup obligations remain mandatory safety evidence.

`nicegui_app/ui/workflow_navigation.py` owns the explicit route hierarchy for operational child pages. The roster workspace is the stable hub; week detail and published-duty adjustment pages render a bilingual route trail, an explicit return action, and the same generate → review/export → adjust → history sequence. This does not use browser history, so an externally opened or refreshed child URL still has a deterministic safe return path. Full-width operational surfaces use `sy-operations-panel`; only the inner reading or form measure is constrained.

#### Adaptive shell contract

Mobile is an adaptive presentation of the canonical NiceGUI application, not a second site. Desktop, tablet and phone share the same URL, Cloudflare authentication/session, route handlers, SQLite database, workflow transactions, policy rules, audit trail and PDF pipeline. Viewport composition may change substantially, but user-agent detection must never select a different data or authorization path.

Desktop retains the grouped sidebar and full utility row. At adaptive-shell width (`<= 900px`), the Quasar drawer breakpoint, CSS and the rendered shell all change together to a one-line top bar plus persistent `Dashboard / Rosters / Prefects / More` bottom navigation. **More** opens the shared secondary-route and utility groups in a scrollable navigation drawer; safe-area insets and matching content padding prevent navigation from covering the final action. A secondary route makes **More** visually active and includes the page title in its accessible label, but the menu trigger does not claim `aria-current=page`; the exact current item in the drawer owns that semantic state. The bottom navigation is rendered after `<main>` in DOM order even though CSS fixes it visually, so keyboard and assistive-technology reading order reaches page content before repeated navigation. Shared-route actions place a bounded `sessionStorage` focus-intent marker before navigation, and the new page focuses `main#main-content` with `preventScroll` after rendering; direct visits, reloads and fragment navigation are not focus-stolen. Dense table views must offer card or row-detail representations built from the same localized display model as desktop, preserving Chinese names and all decision-relevant fields. Phone landscape remains within this adaptive shell rather than reintroducing the desktop sidebar solely because width increases.

Drawer accessibility follows the actual rendered Quasar state, not a fixed animation delay. One cancellable `requestAnimationFrame` settle loop confirms open／closed state before synchronizing `aria-expanded`, drawer focus, background `inert`／`aria-hidden`, and focus return to **More** after a confirmed close. Route cleanup aborts listeners and cancels any pending frame loop, so repeated route cycles cannot accumulate stale transition owners.

The document no longer enforces a 320px minimum canvas. A 256 CSS-pixel viewport, including the narrow CSS viewport produced by 200% zoom, reflows the shared header, page, surfaces, footer and bottom navigation without body-level horizontal overflow. Only a deliberately bounded data region or the ordered phone workflow strip may scroll locally. Standalone links, buttons, summaries, bottom-navigation actions and Quasar clickable controls are measured at 44 CSS pixels in both dimensions; inline links inside running text retain the standards-defined exception.

`_install_mobile_viewport_accessibility()` treats the software keyboard as a visual-viewport constraint rather than a layout mode. It exports the visual viewport height, width, top/left offsets and bottom inset as shared CSS properties. Only a material viewport reduction while an editable control is actually focused may set `sy-mobile-keyboard-open`; a small browser-chrome resize or narrow 256px reflow cannot hide the fixed tab bar by itself. Keyboard mode moves the tab bar out of the interaction path and scrolls the focused field toward the centre. Resize, visual-viewport scroll, focus and orientation listeners share one `AbortController`; route replacement calls the disposer and removes every temporary class and property. Reduced motion uses immediate field reveal and removes the tab-bar transition.

Medium touch screens are not stretched phones. From 640–900px, consequential operational forms remain one column, workflow navigation becomes a two-column overview, and evidence/developer-reference grids may use two columns. Below 640px, workflow steps retain order through a contained scroll-snap strip. Mobile forced-colour rules use `Canvas`, `CanvasText` and `Highlight`; light and dark appearances retain identical content/control order and state meaning. The motion runtime gives a coarse-pointer press one bounded semantic glyph story and restores the source glyph after 460ms using opacity/scale only—no drift, translation or rotation—and clears all timers on disposal. Busy, disabled and reduced-motion controls remain static.

The rc20 intermediate-density rules distinguish portrait and landscape tablets without user-agent branching. Both 768×1024 and 820×1180 portrait adaptive shells can use two-column roster, directory, evidence and download cards while forms remain a single decision column. At 901–1180px, including 1024×768 touch landscape, the desktop shell remains visible but `sy-operations-grid` and document layouts collapse before their columns become cramped; evidence indexes, toolbars and download options are capped at two columns. At 1440×1024 the full desktop shell and reading measure remain intact. CSS changes composition only—the same semantic DOM, `PageContext`, capability policy and workflow callback remain authoritative.

The existing roster and prefect card renderers remain the implementation baseline. Historical rc18 evidence covers 390×844 Traditional Chinese/light, 320×760 English/dark with reduced motion, and 844×390 landscape touch contexts. The last verified clean rc30 source-matched report covers the isolated device matrix containing 256×700 reflow, 320×760 reduced motion, 390×844 phone, 768×1024 and 820×1180 adaptive touch tablets, 1024×768 desktop-shell touch tablet, 1440×1024 full desktop and 844×390 phone landscape. `verify_nicegui_mobile.py` owns the phone／tablet members and `verify_nicegui_ui.py` owns the full-desktop member; together they proved a single visible navigation shell, route-focus transfer, More/current-page semantics, `visualViewport` keyboard clearance, footer/safe-area clearance, comprehensive 44px standalone targets, touch icon stories, forced colours and zero document overflow/console/page errors for the deployed source. Controlled origin cutover and canonical smoke have succeeded; physical iPhone Safari and Android Chrome 200% zoom, keyboard, rotation and notch/home-indicator checks remain open human acceptance evidence.

The same preflight contract covers roster preparation and manual draft correction: a missing candidate or invalid week start is repaired in place. Blank operator reasons are valid and never weaken the durable version, command, audit, fairness, or backup checks. `scripts/verify_nicegui_write_pipeline.py` asserts that invalid states create neither a progress dialog nor a `progress_*_working` log event, while also proving that an optional reason can be omitted safely.

Write concurrency is owned below the route layer. Draft generation obtains SQLite `BEGIN IMMEDIATE` before reading the next weekly version, so two clients receive distinct versions instead of colliding after policy work. Prefect edits carry integer optimistic versions; one multi-row intent serializes, validates every row, and applies every compare-and-swap in one transaction. Two concurrent batches therefore cannot leave a mixed winner: one complete transaction may win and the stale batch returns structured zero-write conflicts. Guest uses the same all-or-none contract in one locked workspace revision and binds retry to the request digest without storing historical state copies. Managed restore operates on the privately staged exact database／manifest pair, migrates only a supported legacy revision, runs current-head foreign-key and fairness reconciliation, and only then creates the `pre_restore` snapshot and swaps the live file. If post-swap reconnect or audit fails, the workflow installs the safety snapshot automatically; only rollback failure leaves the durable maintenance marker in recovery-review state.

Shell preferences preserve working context. Appearance exposes one binary Light／Dark control on desktop and adaptive shells. `system` is not a visible choice: it exists only while the preference is missing or unset. In that state the resolved appearance follows the operating system; the first activation stores the opposite resolved mode, and later activations alternate explicit Light and Dark. The icon reports the current resolved mode while the accessible label names the next action. Appearance and interface-sound changes update all desktop／mobile controls in place; enabling sound plays one short success preview and neither action reloads the route. Language controls name the destination by autonym—English／EN from Chinese and 繁體中文／繁中 from English. Language changes still require a translated page reload, so a delegated trusted `input`／`change` guard marks edits inside `<main>` and asks for confirmation before leaving a dirty form. Admin persists through the encrypted user preference adapter, Guest through the bounded session-only adapter, and Public／Viewer through a browser-local adapter. Public／Viewer never reads or continuously synchronizes Admin／Guest preferences. Only when a person deliberately enters Admin or Guest may the Worker stage an explicit normalized `light`／`dark` hint for at most 120 seconds in a bounded cookie (`Secure; SameSite=Lax; Path=/`). The Worker validates it, carries it inside the signed session and request-bound signed origin principal, then clears the staging cookie when the session is minted. NiceGUI adopts that handoff only when the destination preference is unset; an existing Admin／Guest preference always wins. Practice and maintenance banners share one ordered `sy-status-stack`, preventing two valid global states from overlapping. Dialog actions share the `sy-mobile-actions` grammar: desktop keeps a concise action row, while the adaptive shell stacks full-width 48px controls in consequence order.

Roster identity is also a workflow read contract, not an empty-table convention. `RosterWorkflow.assignments()` first verifies that the roster week exists, so a stale bookmark after a managed restore cannot be mistaken for a real roster with no assignments. Both roster-detail routes render the same bilingual live recovery state with routes to the current roster list and verified-backup settings. The adjustment route additionally reads the durable roster status before rendering any form; a draft receives a return-to-review state, while only a published roster can expose substitute and reason controls.

`nicegui_app/config.py` loads the project `.env` before resolving database and backup path constants. Explicit process variables still take priority, which preserves isolated browser runs while making documented `.env` paths effective on a replacement computer. Deployment readiness delegates snapshot trust to `RosterWorkflow.backup_inventory`; a `.sqlite3` filename is never sufficient evidence. No snapshots is a first-run warning, at least one fully verified recent self-contained pair is a pass, and snapshots with no valid JSON-object manifest／checksum／integrity／supported-migration／zero-obligation／schema result are a failure. `/readyz` is write-ready only when storage health is ok, `workflowInitialized=true`, no maintenance or recovery marker exists, pending backup obligations are zero, and startup backup repair has not failed. Diagnostic-only startup deliberately reports `workflowInitialized=false`, `writeReady=false` and HTTP 503; removing a marker alone cannot make that process writable because controlled recovery and a safe restart must create real workflow sessions.

`nicegui_app/deployment.py` also owns the NiceGUI session-signing secret. A valid explicit `SING_YIN_STORAGE_SECRET` always wins. In localhost mode only, an absent or known placeholder value causes one 64-character random secret to be created with exclusive file creation at `data/runtime/.nicegui-storage-secret`; restarts reuse it, and concurrent starters cannot overwrite the winner. A present but malformed file stops startup rather than silently invalidating sessions. Readiness inspects this state without creating data. Future `server` mode never accepts the managed-local file and requires a separate environment secret of at least 32 characters. The secret is ignored by Git, excluded from roster backups/PDFs/reports, and must never be logged.

Network exposure is fail-closed. NiceGUI always binds to loopback; neither the canonical Worker nor `server` mode means the app listens on `0.0.0.0`. The canonical edge topology is Worker → remote VPC Service `sing-yin-roster-nicegui` (`localhost:8080`) → named Tunnel `sing-yin-roster-windows-private` → Windows loopback origin. The Worker binding is `ROSTER_ORIGIN`; proxy code must return the VPC `fetch()` Response directly so the WebSocket handle survives.

The Access application destination is exactly `/auth/login`, not `/auth/*`, the entire Worker, or a management prefix. The public root and Guest identity routes therefore remain usable until a person deliberately starts administrator sign-in. Access uses Cloudflare One-time PIN, an eight-hour limit, and the same bounded exact-email list as the Worker and WARP maintenance policy. The exact list is private operator configuration: the Worker receives it through the `ADMIN_IDENTITY_ALLOWLIST` Cloudflare Secret, never through public `vars` or documentation. An approved user enters an allowed address and the code sent by Cloudflare; no Cloudflare Dashboard membership is required or granted. Worker-side JWT validation uses the Cloudflare team JWK only at `/auth/login`, then creates the separately signed first-party administrator session described above. Every subsequent NiceGUI request rechecks the session and current allowlist. Worker deployment requires `ADMIN_BEARER_TOKEN`, `ADMIN_IDENTITY_ALLOWLIST`, `ADMIN_SESSION_SECRET`, `GUEST_SESSION_SECRET`, and `ORIGIN_PRINCIPAL_SECRET` in Cloudflare secret storage; `AUTH_EPOCH` and `ORIGIN_PRINCIPAL_KID` must match the Windows origin. The Windows server setting `SING_YIN_REQUIRE_GATEWAY_PRINCIPAL=1` rejects requests that reach an application route without that signed Worker principal; only explicit local maintenance mode may use the local-console fallback. Access audience, JWT, cookies, Tunnel token, secret values and management credentials never enter source, logs, backups, screenshots or documentation. Local/private-WARP mode remains available as a maintenance fallback and must continue to fail for WARP-off or unapproved devices.

Live transport evidence is recorded separately from final acceptance: a temporary Worker bound to VPC Service `019f5b30-d07c-7a63-a273-6b2ccb7318f8` received `/healthz` HTTP 200 and an Engine.IO open packet from `/_nicegui_ws/socket.io/?EIO=4&transport=websocket`. The probe script and workers.dev subdomain were deleted. This proves HTTP Upgrade/WebSocket transport, not the complete Access login/logout, long reconnect, upload, PDF, or fictional write workflow; those remain browser acceptance gates.

The only deliberate application-originated external request carrying roster-derived content is the explicitly enabled public-share adapter. It sends authenticated ciphertext and minimum metadata—not plaintext or OP state—to the fixed canonical Worker after confirmation.

## Semantic icon motion boundary

`nicegui_app/assets/motion/sing-yin-icon-story-state.js` owns the framework-neutral
state machine for pointer, focus, persistent glyph, guards and revision. The
NiceGUI runtime in `sing-yin-motion.js` owns DOM discovery, GSAP timelines,
touch timers, MutationObserver hydration and disposal. Page modules may declare
only semantic metadata through the shared component API; they must not create a
second timeline, rotate the host, or infer product state from translated labels.

The five rendered categories are persistent state, intent-to-outcome preview,
operation lifecycle, semantic role and intentionally static. Persistent state has priority over hover and
touch. Every interactive Material glyph receives a rendered category and role;
unknown or responsibility-sensitive actions remain static until a truthful pair
is reviewed. Reduced motion, disabled and busy controls cancel temporary stories
and immediately expose the truthful glyph. Removed DOM clears timers, timelines
and WeakMap state; reconnect hydration is idempotent so semantic attributes cannot
create a MutationObserver loop.

The public Worker uses the same fixed-slot, centred opacity/scale grammar with a
smaller implementation. It does not load a second animation runtime. The
deterministic state-machine tests, rendered semantic audit and disposable browser
verifier jointly cover reversal, pointer/focus overlap, touch restoration,
persistent controls, fixed geometry, forced colours and repeated route replacement.

`nicegui_app.ui.icon_motion_contract` is the executable traceability inventory for
the 21 required controls. It records route, label key, call site, access modes,
mobile behavior, source／destination glyph, role, category, motion mode, bounded
rotation parameters, states and static or reduced-motion rationale. Rotation is
restricted to Settings, real appearance changes, Backup Settings navigation,
History and Undo. Restore and every existing task story remain lifecycle/morph
only, while the host, label and active-route layout remain fixed. True
`sy:feedback` events drive lifecycle glyphs and fixed-footprint tonal states;
timeouts settle back to the source rather than inventing success. Source counts,
rendered counts and deployment truth are kept separate in
[`docs/audits/SEMANTIC_ICON_ACTION_MOTION_2026-07-30.md`](audits/SEMANTIC_ICON_ACTION_MOTION_2026-07-30.md).

## Verification

- `scripts/verify_practice_mode.py` checks the isolated health identity, bilingual persistent banner, light/dark styling, phone layout, console, and local screenshots without writing roster data.
- `tests/test_access_context.py`, `tests/test_gateway_identity.py`, `tests/test_guest_workspace.py`, `tests/test_guest_adapter.py`, `tests/test_guest_downloads.py`, `tests/test_guest_snapshot_bridge.py`, and Guest UI safety tests own the capability, signed-principal, bounded-workspace, browser snapshot and no-store download contracts.
- `scripts/verify_unified_guest_ui.py` launches an isolated Guest-mode NiceGUI origin with temporary paths and a bounded E2E principal. It is intended to prove same-route rendering, restriction states, fictional data, theme／locale／phone behavior, console cleanliness and no official persistence. The final release orchestrator must run it as a separate phase; a focused script pass is not deployment evidence.
- Worker Deno contracts own `/auth/admin/start`, `/auth/guest/start`, `/auth/status`, `/auth/logout`, compatibility redirects, principal signing, forged-header stripping, VPC proxying and Viewer isolation.
- `scripts/verify_mixed_gateway_load.py` is the bounded local cross-boundary check: it runs the actual gateway Worker source under Miniflare／workerd, opens browser WebSockets through the service-binding proxy, and combines isolated Guest／Admin reads, one Admin write, PDF delivery, backup, outbox and Viewer decryption against disposable fictional SQLite. The [2026-08-01 acceptance](audits/MIXED_GATEWAY_LOAD_ACCEPTANCE_2026-08-01.md) used 10 Guest × 2 waves and 2 Admin; its report observed 22 connected sessions／WebSockets and backup `0 → 2`, while the executable contract requires per-session WebSocket presence and an increase in recovery evidence rather than those exact future counts. It is not Cloudflare-network, long-soak, production-SLO, deployment or human-device evidence.

The complete Python suite, motion state-machine tests, Worker contracts, desktop
and adaptive browser checks, isolated write pipeline, unified Guest verifier,
backup-failure drill, and release-candidate orchestrator passed for exact rc26
commit `248955cb3300bfbe092b05036632991524d824cd`. The 14／14 report binds 296
source files to fingerprint
`5da902307e2d717a75c93e100ba9860eb7e6dd9c35dc42d4a1477bd3304de5e7`.

This paragraph records the historical state before the rc31 rollout. At that
time the running origin and canonical gateway were provenance-drifted, clean
rc30／`11763f08-d40d-46d5-93dc-5ca2599d4154` was the last verified pair, and
rc31 was an undeployed candidate. The current production identity and immediate
rollback pair are stated at the top of this document. Architecture text and
historical automated evidence never substitute for an exact-source release
report, matching origin／Worker deployment evidence, canonical online checks,
or supervised human acceptance.

```powershell
python -X utf8 -m pytest -q
python -X utf8 scripts\verify_release_candidate.py
```

The browser check covers Dashboard, Roster, Prefects, Adjustments, Audit, language switching, in-place dark/sound changes, the unsaved-form language guard, favicon delivery, console errors and uncaught `pageerror`, captured light/dark screenshots, stale roster and adjustment URLs in both languages, and the mobile requirement that Daily Verse precedes the weekly workbench. The isolated release pipeline additionally asserts 26 visible phone roster cards, the absence of clipped desktop roster and directory tables at 390px, the persisted Chinese substitute name in both interface languages, a draft adjustment URL with no writable form, full-width 44px published-adjustment actions, and the safe missing-reason message before a write. With the isolated opt-in environment above, it also verifies the visible progress dialog for an actual generated draft.

For release evidence, run the smoke check and the full write-pipeline script independently. The latter is broader but intentionally remains separate so a normal visual smoke run does not write data.

For a final release candidate, install `requirements-dev.lock` with `--require-hashes`, install Playwright Chromium, ensure Deno is available, and run `python -X utf8 scripts/verify_release_candidate.py`. The first gate, `repository_hygiene`, checks the Git index, true commit history, ignore behavior, and untracked release-sensitive source before any browser starts. It fails if HEAD is missing; if secrets, runtime databases, backups, logs, generated PDF/ZIP files, operator imports, or operator music are tracked; or if application／migration／Cloudflare／configuration／handover source would be omitted from a release. It reports only categories/counts rather than file content. `scripts/run_security_checks.py` separately gates dependency vulnerabilities, medium/high Python static findings, and secret candidates across Python and Cloudflare inputs without printing candidate values. Deno then runs the Worker gateway contracts as an independent gate and missing Deno fails clearly.

The normal isolated browser phase runs `verify_runtime_performance.py`: after fonts settle it measures cold transfer, largest resource, resource count, forced-GC heap growth, DOM nodes, JavaScript listeners and phone-width overflow. Repeated music-panel use and representative route navigation followed by return to the Dashboard must both remain bounded. The orchestrator also runs the full write flow, the independent adaptive-phone verifier, strict readiness and a separate blocked-backup environment. Browser scripts fail on both console errors and uncaught page errors. After each server stops, its captured console is checked for error/critical levels, Python tracebacks, and uncollected task exceptions; any marker fails the candidate, while the report receives only a non-sensitive summary rather than raw console content.

The verification dependency set includes Starlette's current `httpx2` TestClient backend, so a clean replacement-computer run does not normalize a deprecation warning as success. PDF evidence parses both downloaded schedule documents and checks their published state, five weekdays, authoritative Chinese names, landscape single-page geometry, and the four Room 202 closed cells. `docs/ACCEPTANCE_EVIDENCE.md` maps every formal checklist item to its direct automated proof and the remaining human decision; machine `pass` never sets human acceptance to complete.

`nicegui_app/release_evidence.py` owns the presentation-safe report contract. The verifier records a SHA-256 fingerprint over deployable NiceGUI and policy/core code, migrations, dependency/configuration files, built-in assets and music, selected Windows host-operation scripts, formal evidence gates, and the complete `cloudflare/` tree including `.js` and `.jsonc`. Ordinary documentation, tests, CI definitions, and the fast update classifier use focused verification but do not by themselves stale a proven runtime artifact. Production runs with `reload=False`, so this immutable source set is hashed once per process and reused by read-only Platform／Engineering requests; restarting after an update creates the new fingerprint. Missing, malformed, failed, running, or stale reports receive distinct bilingual states without exposing parse errors or local paths. Generated logs remain outside the fingerprint so a report cannot make itself stale.
