# Repository-Wide Code Audit — R2

**Audit date:** 2026-07-26

**Repository:** `D:\code_v3`

**Audit kind:** evidence-led, read-only code and release review

**Finding set:** 5 findings — P0: 0, P1: 0, P2: 3, P3: 2

**Important boundary:** this report does not change, stage, commit, push, release, or deploy application source. The two Deepseek reports dated 2026-07-26 remain unmodified and are treated as hypotheses, not authority.

## Remediation addendum — 2026-07-27

This addendum records a later release-candidate remediation branch; it does not rewrite the audit baseline or convert this report into release/deployment evidence. The implementation branch is `codex/r2-audit-remediation` at baseline `fcb4defee723eb478a92ff052f02329cf9749f21` (`origin/main` when work began).

| Finding | Current remediation status | Evidence added in the remediation branch |
|---|---|---|
| R2-001 | Implemented | Formal SQLite and browser-only Guest workflows now select the latest earlier active draft/published roster; both have cross-gap regression tests. |
| R2-002 | Implemented upstream | PR #32 established rc26 release truth before this branch was created; this batch also corrected the remaining 14-gate operator-guide count. |
| R2-003 | Implemented | Eight wildcard imports and both dynamic `__all__` surfaces were replaced with explicit imports/exports; repository hygiene now rejects workflow wildcard imports. |
| R2-004 | Implemented | Repair attempts every pending obligation, preserves the first error for fail-closed reporting, and proves a later obligation can complete while the failing record remains pending. |
| R2-005 | Implemented | The nonexistent `backend` pytest path was removed and a configuration regression test now requires every declared path to exist. |

Deepseek R3/R4 were also rechecked against the current branch. Their FastAPI mismatch was a system-interpreter observation rather than the project `.venv` (0.139.0), and Wrangler 4.110.0 strict dry-run explicitly recognized the VPC and both rate-limit bindings. The claimed repeated availability scans occur once in separate use cases, not three or four times in one generation. The alleged missing post-commit recovery path is the durable backup-obligation path already exercised by recovery tests. Useful supplemental fixes were retained: Guest import has a non-assert fail-closed guard, same-client page-context composition is atomic, operator-facing environment overrides are documented, empty-state test IDs are explicit, the DP comparison intent is documented, read-only weekly previews surface failures through the support-reference boundary, and rc25/rc26 changelog history is explicit.

## 1. Executive summary

The inspected source tree is materially stronger than the original Deepseek report suggests. The clean detached release-candidate verifier passed all 14 gates over the exact inspected tree, including 884 Python tests, 3 motion tests, 41 Worker tests, browser write/publish/adjust/withdraw/export/handover/restore flows, Admin/Guest separation, mobile layouts, runtime resource cleanup, security gates, repository hygiene, dependency integrity, and committed-without-backup recovery. No P0 or P1 defect was confirmed.

Five actionable root causes remain:

1. Flexible Assist rotation asks for the exact calendar week `T-7`, while architecture text promises the previous **active** week. A disposable cross-gap reproduction confirmed the mismatch.
2. Release truth is copied into many prose sections; several files simultaneously call rc20, rc21, and rc24 “live” or “current,” creating operator and rollback ambiguity.
3. The workflow dependency facade dynamically exports 83 names through eight wildcard-import sites. No harmful runtime collision was found, but one module currently overwrites five explicit imports with equivalent wildcard bindings, and future changes have an unnecessarily broad blast radius.
4. Backup repair intentionally stops at the first failure. It remains fail-closed and data-safe, but a record-specific failure prevents later independently repairable obligations from being attempted or diagnosed in the same run.
5. Pytest still adds a nonexistent `backend` directory to `sys.path`, contradicting the declared NiceGUI-only architecture.

The original `AUDIT-001` and `AUDIT-002` P0 claims were not reproduced. Normal withdrawal and adjustment paths are idempotent/versioned and reconcile the fairness ledger before commit. Even after deliberate anchor corruption, both transactions raised `WorkflowError` and rolled back; no negative value was persisted. Adding `max(0, …)` to `history_weight` would weaken the invariant by hiding corruption.

The current checkout commit is not the annotated rc26 commit, but both resolve to the same Git tree. Therefore the code-content findings apply to the rc26 tagged source. During the final handoff wait, the separate controlled-deployment task reported that the Windows origin had switched to `v1.2.0-rc.26`／`248955c…` after 14/14 gates; Worker source was unchanged from rc24, so the existing formal Worker version remained in service. R2 did not perform or independently authenticate that deployment and does not convert the separate task's evidence into an R2 command pass. Public read-only GETs showed the canonical Worker root and `/healthz` responding, while `/readyz` redirected to the authenticated flow.

## 2. Repository snapshot and scope

### 2.1 Baseline

| Item | Evidence |
|---|---|
| Branch | `codex/rc26-real-team-verifier` |
| HEAD | `2afddc7b71eaf28dd504aac3c68562f95469ef2d` |
| HEAD tree | `4df9075ab01d163c028f4047c682852441e23aec` |
| Remote `main` | `248955cb3300bfbe092b05036632991524d824cd` |
| Annotated tag | `v1.2.0-rc.26` → `248955cb3300bfbe092b05036632991524d824cd` |
| rc26 tree | `4df9075ab01d163c028f4047c682852441e23aec` |
| Content equivalence | `git diff --quiet HEAD 248955...` exit 0; zero changed files |
| Merge base | `5c2308694fea4d3dd6116037c6be1ef3765d3ffa` |
| Tracked files | 557 |
| Pre-existing tracked changes | none |
| Pre-existing non-ignored untracked files | the two original Deepseek reports only |
| Staged files | none |

The different commit IDs encode different histories, not different audited content. Findings and line numbers are bound to tree `4df9075a...`.

### 2.2 Tool and dependency baseline

| Interface | Installed/pinned evidence | Status |
|---|---|---|
| Python | 3.12.10 | Verified locally |
| NiceGUI | 3.13.0; `requirements.txt` constrains `>=3.13,<3.14` | Imported; 46 used `ui.*` names exist; browser gates passed |
| FastAPI | 0.139.0 | Imported; seven application API/health routes inspected and tested |
| Starlette | 1.3.1 | Dependency integrity and suite passed |
| SQLAlchemy | 2.0.51 | Real SQLite transaction, race, restore, and recovery tests passed |
| Alembic | 1.14.1 | One head, `0011`; linear `0001` → `0011` chain |
| ReportLab | 4.4.10 | Chinese/English PDF browser verification passed |
| Playwright | 1.61.0 | Desktop, mobile, Guest, write pipeline, restore, and console gates passed |
| pytest | 9.1.1 | 884 tests collected; full suite passed |
| Deno | 2.9.2 / TypeScript 6.0.3 | `deno check` and 41 Worker contracts passed |
| Wrangler | 4.110.0 | Bundled Node strict dry run passed; no upload/deploy |
| DeepSeek | `deepseek-v4-flash` and `deepseek-v4-pro` allowlist | Source and current official model/API docs agree; paid API not called |

The old report's FastAPI 0.138 statement is stale; the lock and installed runtime both use 0.139.0.

## 3. Coverage ledger

Every tracked file was assigned to exactly one coverage class. Counts sum to 557.

| Exclusive class | Files | Coverage method |
|---|---:|---|
| Runtime, policy, Worker, migrations | 143 | imports/AST, dependency tracing, targeted source review, compile/check, unit/contract/browser tests |
| Tests | 100 | test intent review, 884-test collection, full execution, focused concurrency/recovery review |
| Historical/generated evidence | 87 | provenance, tracking and current-vs-historical labels; not treated as live source |
| Binary media/fonts | 72 | tracked path/provenance, release inclusion and browser delivery; binary payloads not line-reviewed |
| Root config/launchers/miscellaneous | 53 | startup, dependency, environment, version and source-truth checks |
| Automation/CI/deployment | 51 | script boundary review, dry runs, source-fingerprint and release-gate execution; no deployment |
| Documentation | 34 | authority, contradictions, operator/recovery/release claims, link/contract tests |
| Seed/fixture data | 9 | schema/provenance and fictional-vs-official boundary checks; no real student data printed |
| Design sources | 8 | token/generation contract, asset ownership, UI/browser verification |

Relevant non-ignored untracked files at baseline were classified as prior audit evidence:

- `docs/audits/CODEBASE_AUDIT_2026-07-26.md`
- `docs/audits/CODEBASE_AUDIT_FINDINGS_2026-07-26.json`

They were read only to form and test hypotheses. They were not accepted as facts, overwritten, staged, or included as release source.

### Excluded from meaningful line review

| Category | Reason |
|---|---|
| `.git/` objects and logs | Git metadata, inspected only through Git commands |
| `.venv/` | installed environment, assessed through versions/imports/audit rather than source review |
| `node_modules/` | vendored dependencies, assessed through lockfile, dependency audit and declared command execution |
| caches (`__pycache__`, `.pytest_cache`, `.wrangler/cache`) | generated, non-authoritative |
| runtime logs | may contain operational metadata; only verifier summaries/failure markers were used |
| official databases, backups and uploads | operator/student data boundary; release checks used disposable fictional paths |
| `.env` values and credentials | secret values were never printed; only expected key names and source handling were reviewed |
| binary audio/image/font payload interiors | provenance/delivery checked; semantic line review is not meaningful |

## 4. Architecture and responsibility map

| Boundary | Owner | Inputs and outputs | Main invariants / failure controls |
|---|---|---|---|
| Application entry | `nicegui_app/main.py` | configuration, FastAPI/NiceGUI routes, health/readiness | loopback-first runtime, readiness separates health from write readiness |
| Identity context | `access_context.py`, `gateway_identity.py`, `runtime.py` | Worker principal/session → `PageContext` | exact mode/capability checks, expiry/revocation, browser headers are not trusted |
| UI/routes | `nicegui_app/ui/page_routes/` | 19 NiceGUI page routes | common Admin/Guest route skeleton, server-side capability selection |
| Policy | `packages/roster_policy/` | roles, eligibility, required posts, duty weights/windows | AHP-only Assist; ordinary prefect room duties; canonical school rules |
| Generation | `packages/roster_core/` | prefects, leave, fairness history, Assist mode | deterministic assignment, no same-day duplicate/consecutive duty |
| Durable workflow | `services/roster_workflow.py` + `workflow_parts/` | imports/generation/publication/adjustment/withdrawal/handover | serialized writes, optimistic version, receipts, audit, fairness reconciliation, backup obligation |
| Guest workflow | `services/guest_adapter.py`, `guest_workspace.py` | fictional, bounded in-memory state | no official SQLite/backups/uploads/AI/share; session/tab binding and cleanup |
| Persistence | `persistence/`, migrations `0001`–`0011` | SQLite records and backups | foreign keys, active-week uniqueness, command receipts, recovery obligations |
| Support | `support_incidents.py`, `/support` route, Worker browser report | redacted incident/attachment metadata | Admin explicit consent and host-local persistence; Guest/Public/Viewer browser-only |
| Public edge | `cloudflare/roster_viewer/worker.js` | Public/Admin/Guest/Viewer HTTP and WebSocket | Access JWT + exact allowlist, signed origin principal, epoch/key rotation, same-origin unsafe requests, rate limits |
| Viewer | Worker `/view#…` flow | encrypted fragment/session storage → read-only display | no fragment sent to server, expiry/revocation, no Admin/Guest authority |
| External optional adapters | DeepSeek mapping, YouTube import/search | bounded metadata or allowlisted public URL | disabled by default/configured locally, fixed/allowlisted hosts, size/time/model validation |
| Release | `verify_update.py`, `verify_release_candidate.py`, deployment scripts | exact source fingerprint and disposable evidence | verification is not deployment; formal backup/restore before controlled switch |
| CI/governance | `.github/workflows`, CODEOWNERS, Dependabot | tests, CodeQL, dependencies | action refs pinned to full SHAs in the inspected workflow files |

### Entrypoints and interfaces

- Python entry: `python -m nicegui_app.main`; `nicegui_app/main.py:317-376` owns launch configuration.
- FastAPI surface: `/healthz`, `/readyz`, Guest snapshot restore/download/cleanup, generated download, and session revoke.
- NiceGUI surface: 19 page routes, including `/`, `/rosters`, `/prefects`, `/audit`, `/handover`, `/settings`, `/support`, and evidence/documentation routes.
- Worker surface: public entrance, Admin Access bridge, Guest start, authenticated proxy, support routing, encrypted Viewer, share lifecycle, public health.
- Storage seams: official SQLite/backup directories only through the formal workflow; Guest registry and browser storage are separate adapters.
- No Python parse failure, missing used NiceGUI `ui.*` symbol, or circular internal import strongly-connected component was found.

## 5. Findings (P0 → P3)

### R2-001 — Flexible Assist rotation does not use the documented previous active week

- **Priority:** P2
- **Category:** Correctness / policy contract / test gap
- **Confidence:** Confirmed
- **Location:** `nicegui_app/services/workflow_parts/lifecycle.py:54-66`; `docs/NICEGUI_ARCHITECTURE.md:182`
- **Owner:** `_previous_assist_weekday_assignments`, `generate_and_save_draft`
- **Evidence:** the query requires `week_start == current - timedelta(days=7)`, while the architecture promises the “previous active week's Assist assignments.” A disposable workflow generated 2026-09-07 and then 2026-09-21; five earlier active Assist owners existed, but both generator calls observed an empty previous map for the second generation.
- **Trigger:** flexible-week generation after at least one skipped Monday, such as a school holiday or exam break.
- **Impact:** the secondary same-weekday anti-repeat input is lost across the gap. Eligibility, persistent history-weight fairness, and deterministic generation remain enforced, so this is not roster corruption or an authority defect; it can nevertheless repeat an AHP on the same weekday contrary to the documented rotation policy.
- **Root cause:** “previous week” was implemented as a calendar offset while product documentation later strengthened the term to “previous active week.”
- **Smallest correction:** first obtain a product/policy decision. If active-week semantics are intended, select the latest draft/published week with `week_start < current`, ordered descending with a deterministic limit. If exact calendar adjacency is intended, revise the architecture/operator wording instead.
- **Broader correction:** none required; keep the query behind the existing helper.
- **Regression risk:** medium; the selected AHP can change for every post-break flexible roster.
- **Verification:** add formal Admin and Guest tests for consecutive, one-gap, multi-gap, withdrawn-only, and future-week exclusion cases; rerun Assist-mode, policy, persistence and release-browser gates.
- **Effort / radius:** small, approximately 0.5–1 day; lifecycle helper, Guest equivalent/adapter behavior, two test modules, architecture/operator wording.
- **Uncertainty / false-positive note:** severity depends on the policy owner's intended meaning. The behavior is confirmed; the desired semantics require a human decision.

### R2-002 — Current/live release truth is contradictory inside authoritative documents

- **Priority:** P2
- **Category:** Claim integrity / documentation / operations
- **Confidence:** Confirmed
- **Locations:** `README.md:70,84,453`; `README-EN.md:93-100,149`; `PROJECT_STATUS.md:5,55`; `docs/NICEGUI_ARCHITECTURE.md:7-17,394-400`
- **Owner:** release documentation and handover truth
- **Evidence:** the same inspected tree calls rc24 the current formal baseline, rc21 the live source/origin, and rc20 the live `main`/production origin. Several older passages are not labelled historical at the sentence where they make the claim. The package manifest also remains at `1.2.0-rc.24`, while the exact tree is tagged rc26.
- **Trigger:** a successor, advisor, deployment script reviewer, or incident responder reads a lower section instead of the newest banner.
- **Impact:** the operator can select the wrong source/host/Worker pair, misunderstand rollback order, or repeat stale verification. This does not prove that production is on the wrong version; it proves the documentation cannot uniquely answer the question.
- **Root cause:** release facts are copied into many prose sections and new banners are appended without mechanically expiring earlier “current/live” wording.
- **Smallest correction:** after the controlled rc26 outcome is known, update every active current/live statement in one documentation-only change and mark retained older sections as historical evidence.
- **Broader correction:** create one machine-readable release-truth manifest consumed by README/status/verification tests; prose should link to it rather than repeat commit, fingerprint, Worker and rollback tuples.
- **Regression risk:** low for application behavior, medium for operator handover if corrected incompletely.
- **Verification:** repository test that rejects more than one active current/live tuple; documentation links and release-evidence tests; compare manifest with tag, deployment report and read-only live endpoints.
- **Effort / radius:** small-to-medium, 1–2 days; README pair, project status, architecture, deployment/operator/remote-access docs, release evidence tests.
- **Uncertainty / false-positive note:** the contradiction is bound to the audited tree. During final handoff, the separate deployment task reported rc26 live and began a post-baseline documentation correction in its isolated worktree; that follow-up does not alter the R2 baseline or erase the reproduced contradiction.

### R2-003 — Dynamic wildcard dependency facade creates an 83-name hidden workflow interface

- **Priority:** P2
- **Category:** Architecture / coupling / maintainability
- **Confidence:** Confirmed
- **Locations:** `nicegui_app/services/workflow_dependencies.py:41,59`; `workflow_types.py:226`; wildcard sites at `roster_workflow.py:5`, `workflow_parts/lifecycle.py:7`, `people.py:5`, `persistence.py:5`, `recovery.py:5`, `reporting.py:16`, and `sharing.py:14`
- **Owner:** workflow composition and mixin imports
- **Evidence:** runtime inspection counted 83 dynamic exports. Eight modules participate in the wildcard chain. `reporting.py` explicitly imports `defaultdict`, `date`, `datetime`, and `select` before the wildcard import, which then rebinds those names to currently equivalent objects. Compilation, full tests, 482 internal import-edge analysis, and cycle detection found no present runtime break.
- **Trigger:** adding any non-underscore global/import to either dependency facade, changing import order, or introducing a same-named helper in a mixin.
- **Impact:** dependencies and symbol ownership are hidden from review/static tooling; unrelated changes expand every mixin namespace; collision risk and refactor radius are larger than the behavior requires.
- **Root cause:** a temporary extraction convenience became a dynamic public interface rather than a fixed compatibility facade.
- **Smallest correction:** freeze `__all__` to an explicit compatibility list, then replace wildcard imports one module at a time with names actually used.
- **Broader correction:** split data types, persistence primitives, policy/generator APIs, and utility dependencies into narrow owning modules only if the explicit-import migration demonstrates a stable seam.
- **Regression risk:** medium because missing implicit imports can surface only on less-used paths.
- **Verification:** `py_compile`, AST undefined-name/static checks, import smoke, all workflow/persistence/restore/share/report tests, then full release verifier.
- **Effort / radius:** medium, 2–4 days; about ten workflow facade/mixin files.
- **Uncertainty / false-positive note:** this is a verified interface burden, not evidence of a current symbol-confusion defect. The existing same-object rebindings do not change behavior today.

### R2-004 — One record-specific backup repair failure prevents later repair attempts

- **Priority:** P3
- **Category:** Recovery / operability / diagnostics
- **Confidence:** Confirmed
- **Location:** `nicegui_app/services/workflow_parts/persistence.py:212-230`; startup state at `roster_workflow.py:67-78`
- **Owner:** `repair_pending_backup_obligations`
- **Evidence:** with two disposable pending obligations and an injected failure limited to the first command ID, the call sequence contained only the first ID and raised immediately. Existing tests prove that startup remains read-only after a persistent repair failure.
- **Trigger:** two or more pending obligations plus a failure specific to an earlier record rather than a globally unavailable backup device.
- **Impact:** later repairable obligations receive no attempt/evidence in that run, and the operator sees a coarse failure class. The service remains fail-closed, so this is an availability/diagnostic limitation, not a false safety guarantee or data-loss finding.
- **Root cause:** the loop re-raises the first exception and couples “attempt all repairs” to “permit writes only if all repairs succeed.” Those decisions need not be identical.
- **Smallest correction:** attempt every pending obligation, retain per-command sanitized results/support references, then keep maintenance/read-only state and raise an aggregate error if any remain incomplete.
- **Broader correction:** not justified. Do not quarantine a failed obligation or re-enable writes automatically.
- **Regression risk:** medium; repeated backup work can increase startup I/O and aggregate error handling must not clear the fence early.
- **Verification:** multi-obligation tests for first/middle/last failure, global device failure, later success, restart, pending count, readiness, and proof that writes remain blocked until zero obligations remain.
- **Effort / radius:** small, approximately 1 day; persistence loop, readiness/diagnostic representation and backup-obligation tests.
- **Uncertainty / false-positive note:** if every practical failure is device-wide, the operational gain is limited. The original report's “permanently blocks all repairs” and P0 rating are unsupported.

### R2-005 — Pytest configuration still declares the removed `backend` runtime tree

- **Priority:** P3
- **Category:** Configuration / hallucination-like stale path
- **Confidence:** Confirmed
- **Location:** `pyproject.toml:3-7`; architecture statement at `docs/NICEGUI_ARCHITECTURE.md:5`
- **Owner:** pytest import configuration
- **Evidence:** `pythonpath` contains `backend`, but no `backend/` directory exists and the architecture explicitly says the obsolete backend runtime is absent. The actual application bootstraps `packages/roster_policy` and `packages/roster_core` from `nicegui_app/__init__.py`.
- **Trigger:** every pytest invocation.
- **Impact:** currently negligible at runtime; it misstates dependency topology, can confuse a successor, and can silently make a newly created accidental `backend/` importable in tests.
- **Root cause:** incomplete cleanup after the NiceGUI-only architecture migration.
- **Smallest correction:** remove `backend` from the pytest path.
- **Broader correction:** add a small repository-hygiene assertion that retired runtime roots remain absent and are not referenced by active import configuration.
- **Regression risk:** low; a hidden test dependency on the ghost path would correctly fail.
- **Verification:** import/collection, full pytest, direct launcher smoke, and repository documentation tests.
- **Effort / radius:** less than half a day; one configuration line plus optional hygiene assertion.
- **Uncertainty / false-positive note:** no broken import was observed, so this is a confirmed stale configuration defect, not a functional outage.

## 6. Deepseek finding disposition and false-positive ledger

| Original ID | R2 result | Rationale |
|---|---|---|
| AUDIT-001 | Not confirmed; P0 rejected | Adjustment subtraction is version-claimed, receipt-bound and ledger-reconciled. Injected corruption caused rollback; no negative anchor persisted. Clamping weight would hide corruption. |
| AUDIT-002 | Not confirmed; P0 rejected | Withdrawal compensates net ledger entries once, rejects repeat/stale state and reconciles before commit. Injected corruption rolled back the withdrawal. |
| AUDIT-003 | Behavior confirmed, downgraded to R2-004 P3 | Later attempts stop, but startup stays safely read-only. Permanent/global blockage and P0 impact were not shown. |
| AUDIT-004 | Confirmed as R2-003 P2 | Eight wildcard-chain modules and 83 exports exist. No current harmful collision or import failure was found. |
| AUDIT-005 | Contract mismatch confirmed as R2-001 P2 | Exact `T-7` behavior reproduced; severity is limited because fairness history and eligibility remain active. |
| AUDIT-006 | Maintenance note, not standalone P1 | Admin and Guest mode normalizers are duplicated and currently identical; parity tests cover both. Consolidate during R2-003 work. |
| AUDIT-007 | Rejected | `RosterWorkflow` is an intentional concrete composition facade. An ABC would add declarations but would not by itself prove mixin completeness. Public API/browser tests and import analysis are stronger evidence. |
| AUDIT-008 | Partly true observation; unsafe proposed fix | Startup exposes only the error class in memory, while obligation error data is retained. Raw exception strings can leak paths. Add sanitized references as part of R2-004, not raw detail. |
| AUDIT-009 | Accepted framework residual risk, not a new defect | NiceGUI 3.13 requires inline/eval for its bootstrap/compiler; the exception is explicitly scoped/documented and external script hosts remain blocked. Security/browser tests passed. |
| AUDIT-010 | Rejected as vulnerability | Worker logs structured server-side phase/reason and credential-presence booleans, but returns only a generic failure page plus support reference. No token, email or assertion body is logged. |
| AUDIT-011 | Rejected | The sign-out failure is deliberately fixed bilingual fallback HTML for a security-critical recovery state; it is not Chinese-only and does not depend on a possibly failing i18n runtime. |
| AUDIT-012 | Rejected | Receipt replay reaches `_fulfill_backup_obligation`; the write fence also blocks any new write while a pending obligation exists. Recovery tests passed. |
| AUDIT-013 | Low-value duplication note | The two `_form_rank` helpers have different invalid-input fallback semantics; validated persisted forms keep production behavior aligned. No reachable failure was found. |
| AUDIT-014 | Rejected | `DUTY_TIME_WINDOWS` is an exported, test-asserted compatibility alias, not dead code. Removal would be an API change. |
| AUDIT-015 | Residual defense-in-depth note | The public Worker sets `Cross-Origin-Resource-Policy: same-origin`; the origin is loopback/private behind the gateway and already sets COOP/frame/CSP controls. No cross-origin leak path was shown. |
| AUDIT-016 | Rejected | `switch_to_chinese` is displayed while English is active and correctly labels the destination language; the inverse path uses `switch_to_english`. |

## 7. Security and privacy review

No additional exploitable security issue was found within the inspected paths and executed gates. That statement is bounded; it is not a claim that the system is vulnerability-free.

### Preserved controls

- Browser-supplied identity headers are stripped at the Worker; only a verified, expiring, request-bound signed origin principal is injected.
- Admin requires Cloudflare Access JWT verification, exact email allowlist, bounded gateway session and origin capability enforcement.
- Guest uses fictional, bounded memory state and capability checks below the UI. Official SQLite, backups, shares, uploads and paid/expensive adapters remain denied.
- Guest snapshot restore binds signed state to workspace/tab/connection context; copied/tampered/stale tokens fail closed in contract and browser tests.
- Viewer state remains read-only, encrypted and fragment/session-storage based; it does not inherit Admin/Guest authority.
- Unsafe methods and WebSocket upgrades require same-origin proof; public entry and view rate-limit bindings fail closed when absent.
- Support attachments use size/type/layout limits, safe relative paths, reparse-point rejection, hashing and atomic lifecycle moves. Public/Viewer/Guest support data remains browser-only; Admin host persistence requires consent.
- DeepSeek column assistance is disabled by default, sends only schema/coarse metadata, uses a fixed HTTPS endpoint, approved models, timeout/response caps, and validates every returned mapping.
- YouTube import accepts exact HTTPS hosts, applies item/byte/time limits and stages outside official roster storage. External download was not exercised.
- GitHub workflow action refs are full-SHA pinned in the two inspected workflows; security gates reported no high/critical dependency issue, no medium/high static finding and no secret candidates.
- CSP's `unsafe-inline`/`unsafe-eval` is a documented NiceGUI 3.13 compatibility exception. This keeps XSS prevention dependent on the central HTML-safety contract and regression tests; it remains a residual risk to revisit with framework upgrades.

### Residual boundaries

- Authenticated Admin, Viewer decryption with a real shared link, Cloudflare Dashboard configuration, KV consistency and Access policy were not exercised live; they require credentials and/or state-changing production access.
- Browser storage remains exposed to any same-origin XSS; CSP compatibility prevents a strict nonce-only posture in NiceGUI 3.13.
- Optional YouTube/DeepSeek integrations were contract-reviewed and locally tested, not called with real credentials.
- Host ACLs, Windows service identity, UAC deployment and production backup media are outside this audit's mutation authority.

## 8. Multi-user and concurrency review

| Scenario | Evidence | Result / limitation |
|---|---|---|
| Two Admin stale writes | optimistic version claims, concurrent adjustment winner test | one winner; loser receives conflict |
| Duplicate/retry command | command fingerprint/receipt tests across adjustment/withdraw/share | same payload replays; changed payload rejected |
| SQLite contention | busy timeout, serialized workflow/process lock tests | covered locally; not a multi-host database design |
| Admin + Guest | separate official workflow vs in-memory adapter; release browser gate | no database fingerprint change from Guest |
| Multiple Guest tabs/sessions | copied-tab, tamper, cross-tab, cleanup and capacity tests | isolated; same-tab signed refresh supported |
| Session expiry/revocation | Worker and origin session tests, logout origin confirmation | fails closed; long-lived real WebSocket revocation remains a live acceptance item |
| Backup immediately after commit | atomic obligation + fenced write + crash-window tests | committed write becomes read-only until verified recovery snapshot exists |
| Multiple pending backup failures | R2 disposable probe | safe but later attempts skipped; R2-004 |
| Restore concurrency | maintenance serialized operation and release restore gate | local evidence passed; real operator/UAC environment not mutated |
| One-shot downloads | generated/Guest token tests | bounded and isolated; canonical authenticated live path not exercised |

Passing individual tests is not treated as blanket concurrency proof. The strongest evidence is the combination of database claims, fences, real parallel tests, restart/recovery tests and browser session isolation.

## 9. API availability and compatibility matrix

| Interface | Classification | Evidence | Limitation |
|---|---|---|---|
| 46 NiceGUI `ui.*` symbols | Verified locally | installed 3.13.0 attribute inspection, imports, release browser gates | framework internals still require permissive CSP clauses |
| 19 NiceGUI pages + 7 FastAPI endpoints | Verified locally | AST/source inventory, full tests, live disposable servers | authenticated production routes not live-tested here |
| SQLAlchemy/SQLite/Alembic | Verified locally | installed versions, linear head, transactions, restore and corruption probes | Windows production media not touched |
| Worker Fetch/Crypto/KV/VPC/Access contracts | Contract verified | Deno check, 41 tests, strict Wrangler dry run | real Dashboard bindings/credentials not read |
| Wrangler `deploy --dry-run --strict` | Verified locally and against official docs | 4.110.0 dry run exit 0; official docs define both flags | no upload/deploy performed |
| DeepSeek Chat Completions models | Source + official docs verified | fixed endpoint; official model list contains both approved IDs | paid/authenticated call not performed |
| YouTube/yt-dlp import | Configured and locally contract-tested | URL allowlist, quotas, 12 focused tests, dependency import | network/download/copyright outcome not exercised |
| Public Worker root and `/healthz` | Verified by safe live GET | 200 HTML; 200 capability-only JSON | does not prove origin, Admin, Guest or Viewer end to end |
| Public `/readyz` | Configured but authenticated | 302 redirect | private readiness intentionally not claimed |
| Windows deployment/UAC | Reported by separate task, not exercised by R2 | task reported rc26 origin and 14/14 gates | R2 did not elevate, deploy or independently authenticate the protected report |
| GitHub branch/tag remote refs | Verified read-only | `ls-remote`; rc26 tag dereferences to remote main | protection/ruleset UI not re-queried |

Primary version-sensitive references used: DeepSeek's official model list and Chat Completion documentation, and Cloudflare's official Wrangler deploy command documentation. Repository tests and installed signatures remain the main evidence for local framework calls.

## 10. Hallucination and claim-integrity review

- **Confirmed stale/invented path:** `pyproject.toml` includes absent `backend` (R2-005).
- **Confirmed contradictory claims:** multiple active “current/live” version tuples (R2-002).
- **Rejected old hallucination:** FastAPI 0.138; installed/locked version is 0.139.0.
- **No missing used NiceGUI symbol:** all 46 statically detected `ui.*` names exist in 3.13.0 and changed routes rendered in release gates.
- **No circular internal import SCC:** 482 project import edges were parsed without a cycle.
- **No demo-as-official data flow found:** Guest fixtures remain fictional and separate; release tests assert the official database fingerprint is unchanged.
- **No deployment inferred from gates:** local release verification and live public health are reported separately from Windows/Worker version rollout.
- **Generated evidence:** design tokens/assets and historical test outputs were classified; current source tests enforce key generated-token/product-identity contracts. Binary evidence was not mistaken for current runtime truth.

## 11. Comment, docstring and knowledge-transfer gaps

- The Assist helper docstring says “immediately preceding school week,” while architecture says “previous active week.” Resolve the policy before adding explanatory comments.
- The backup loop docstring says “repair every” obligation, but the control flow means “until first failure.” Update it together with R2-004.
- The dynamic workflow facade's `__all__` gives no stable interface contract. A fixed export list is more useful than a comment restating wildcard behavior.
- Release sections need explicit `historical`, `candidate`, `verified source`, and `live` vocabulary backed by one manifest. More prose copies would worsen the problem.
- Existing non-obvious security comments around NiceGUI CSP, fixed DeepSeek endpoint, storage isolation, backup fences and fairness reconciliation are valuable and should remain.

## 12. Test, runtime, dependency and command evidence

### Material command ledger

| Exact command | Exit | Result | Core evidence / limitation |
|---|---:|---|---|
| `git status --short --branch; git rev-parse HEAD; git diff --stat; git diff --cached --stat; git ls-files; git ls-files --others --exclude-standard` | 0 | Pass | baseline captured; no tracked/staged change; two prior untracked reports |
| `.\.venv\Scripts\python.exe -X utf8 scripts\verify_update.py --plan` | 0 | Pass | repository selected docs profile for current untracked reports |
| `.\.venv\Scripts\python.exe -X utf8 scripts\run_security_checks.py` | 0 | Pass | dependency/static/secret gates passed |
| `.\.venv\Scripts\python.exe -X utf8 -m pytest -q` | 0 | Pass | full suite passed |
| `.\.venv\Scripts\python.exe -X utf8 -m pytest --collect-only -q` | 0 | Pass | 884 tests collected |
| `.\.venv\Scripts\python.exe -X utf8 -m pytest -q tests\test_roster_persistence.py tests\test_backup_obligations.py tests\test_assist_mode_persistence.py` | 0 | Pass | 31 focused persistence/recovery/Assist tests |
| `.\.venv\Scripts\python.exe -X utf8 -m compileall -q nicegui_app packages migrations scripts` | 0 | Pass | Python compilation passed |
| `deno check cloudflare\roster_viewer\worker.js` | 0 | Pass | Worker static/type check |
| `deno test cloudflare\roster_viewer\worker_gateway_test.js` | 0 | Pass | 41/41 gateway contracts |
| `.\.venv\Scripts\alembic.exe heads; .\.venv\Scripts\alembic.exe history` | 0 | Pass | single head `0011`, linear chain |
| `.\.venv\Scripts\python.exe -X utf8 scripts\check_repository_hygiene.py` | 1 | Expected fail | exactly two non-ignored prior audit reports; no sensitive tracked file or missing ignore |
| bundled Node + `wrangler.js deploy --dry-run --strict --config .\wrangler.jsonc` | 0 | Pass | compiled 265.98 KiB Worker/assets and validated bindings; did not deploy |
| AST/import/API inventory probe | 0 | Pass | 243 Python files, 0 parse errors, 482 internal edges, 0 circular SCCs, 46/46 NiceGUI symbols, 26 routes |
| disposable cross-gap Assist probe | 0 | Pass | prior active owners 5; observed previous maps `[0,0]` across skipped week |
| disposable two-obligation injected-failure probe | 0 | Pass | call sequence stopped after first command ID |
| disposable corrupted-anchor adjustment/withdraw probe | 0 | Pass | both raised fairness reconciliation error and rolled back; minimum persisted weight 0; week remained published |
| detached clean-worktree `scripts\verify_release_candidate.py` | 0 | Pass | all 14 gates passed against exact audited tree in 386.3 s; disposable data and servers only |
| `git ls-remote origin ...; git diff --quiet HEAD 248955...` | 0 | Pass | rc26 tag → remote main; audited and tagged trees identical |
| `Invoke-WebRequest` GET public root, `/healthz`, `/readyz` | 0 | Partial pass | 200/200/302; public capability health only, not private readiness |

### Diagnostic execution notes

- The packaged `rg.exe` could not start because Windows returned Access Denied; PowerShell `Get-ChildItem`/`Select-String` and AST probes were used instead.
- Calling `verify_release_candidate.py --help` is not supported; it began verification and correctly failed repository hygiene because of the two user-owned untracked reports. The authoritative run used a detached clean worktree and passed.
- An initial disposable SQLite probe returned exit 1 only because Windows still held the temporary database during automatic cleanup; the logical result had printed. It was rerun with safe cleanup handling and exit 0.
- A first hand-built obligation fixture violated its command foreign key before the intended probe; the corrected fixture flushed command rows first and passed. No repository file was written.
- Web browsing refused the workers.dev URL as unsafe-to-open; a direct read-only PowerShell GET was used and recorded above.

## 13. Existing strengths to preserve

- Fairness anchor + immutable ledger reconciliation is stronger than clamping counters. Corruption is surfaced and transactions roll back.
- Idempotency keys are payload-bound and combined with optimistic versions, database claims and a host-wide write fence.
- A committed write and its verified snapshot are separated by a durable obligation; any gap forces read-only recovery.
- Official and Guest data stores are different implementations behind the same page/workflow shape, with capabilities enforced below the UI.
- Worker authentication is layered: Access verification, exact identity allowlist, bounded sessions, signed origin principals, same-origin enforcement and rate limits.
- Support/reporting explicitly distinguish local Admin evidence from browser-only Guest/Public/Viewer content.
- Release verification uses disposable SQLite/backups/logs/fictional data, renders real pages and checks browser/server consoles rather than equating HTTP 200 with UI success.
- Migrations are additive and linear; restore checks include checksums, SQLite integrity, schema and fairness reconciliation.
- CI uses pinned actions; dependencies and browser/Worker runtimes are locked and exercised.
- Human acceptance remains distinct from machine gates in the newest release banners.

## 14. Prioritized remediation roadmap

### Immediate containment

No emergency containment is justified. Do not add counter clamps, disable backup fail-closed behavior, or alter production while rc26 deployment evidence is unresolved.

### First small high-value batch

1. Obtain the policy decision for “previous active week” and add the cross-gap tests before changing the query.
2. Establish one current-release manifest and remove/mark contradictory live/current prose after the controlled rc26 outcome is known.
3. Remove the ghost `backend` pytest path and add a retired-runtime hygiene assertion.

### Medium structural improvements

4. Freeze the workflow facade export list, then migrate one mixin at a time to explicit imports; include the duplicated Admin/Guest Assist normalizer only when ownership is clear.
5. Attempt all pending backup obligations for evidence while preserving the zero-pending write fence; return sanitized aggregate diagnostics.

### Larger redesigns requiring a separate decision

None is justified by this audit. A framework rewrite, repository split, new database, ABC hierarchy, or new queue would add risk without addressing the confirmed root causes.

## 15. Uninspected, blocked and residual uncertainty

- The separate rc26 task reported a successful controlled Windows-origin switch and then continued post-baseline documentation cleanup. R2 did not influence the deployment, elevate, or independently authenticate the protected deployment report.
- Cloudflare Dashboard bindings, Access policies, KV contents, Worker deployment version and protected-branch/ruleset UI were not authenticated or mutated.
- Real Admin identity, real Guest capacity under Internet load, Viewer decryption with a real share, long-lived WebSocket revocation, and external-device WARP behavior require supervised live acceptance.
- Real student/operator SQLite, backups, logs, incident attachments and uploaded files were deliberately not opened.
- Paid DeepSeek and networked YouTube operations were not called.
- Binary media quality, licensing and semantic content were not independently re-audited; repository provenance/manifest and delivery checks were used.
- The full suite is broad but cannot prove absence of every race, XSS gadget, browser-version regression or host failure.

## 16. Final release-impact assessment

The exact audited source tree matches the annotated rc26 tree and passed the complete local release-candidate verifier. The five findings do not justify blocking the source candidate as P0/P1 defects. R2-001 should be resolved or explicitly accepted before claiming “previous active week” behavior; R2-002 should be corrected as part of the next truthful deployment/documentation handoff. R2-003 through R2-005 are bounded maintainability/recovery improvements suitable for a subsequent tested batch.

This report is **not** deployment evidence and does not change production state. The separate deployment task reported the Windows origin live on rc26 with the unchanged formal Worker version; R2 independently confirmed only that the public Worker and capability health responded. Private readiness, protected deployment-report contents, rollback evidence and supervised human acceptance remain outside R2's confirmed scope.
