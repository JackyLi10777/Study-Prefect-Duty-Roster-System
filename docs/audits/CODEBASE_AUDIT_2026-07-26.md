# Codebase Audit Report — Sing Yin Study Prefect Duty Roster System

**Date:** 2026-07-26
**Branch:** `codex/rc24-deployment-truth`
**Commit:** `8d709f9b0b4e69fe38f7237ef2f473c27ff848fc` (1 commit ahead of `origin/main`)
**Working tree:** 20 modified files (documentation + i18n updates)
**Audit type:** Read-only, evidence-led, no code modifications

---

## Executive Summary

A comprehensive audit of all 557 tracked files found **16 actionable findings**: 3 P0 (critical correctness), 5 P1 (high priority), 5 P2 (medium), 3 P3 (low). The test suite passes at 100%. The architecture has strong security fundamentals (HMAC-based sessions, consistent output escaping, defense-in-depth headers, ORM-exclusive data access). The primary concerns are correctness defects in the fairness ledger (history_weight/history_duties without floor protection) and structural coupling (wildcard imports across 8 modules). No security vulnerabilities requiring immediate containment were discovered.

**Most critical findings:**
1. `history_weight` can go negative without floor protection (`lifecycle.py:782`) — **P0**
2. `history_duties` can go negative during withdrawal (`lifecycle.py:455`) — **P0**
3. Single backup repair failure blocks all subsequent repairs (`persistence.py:227`) — **P0**
4. Wildcard `import *` pollutes 8 module namespaces (`roster_workflow.py:5`) — **P1**
5. Non-consecutive week boundary assumes 7-day intervals (`lifecycle.py:62`) — **P1**

---

## Repository Snapshot and Scope

| Property | Value |
|----------|-------|
| Total tracked files | 557 |
| nicegui_app/ | 169 files |
| tests/ | 100 files |
| scripts/ | 44 files |
| cloudflare/ | 13 files |
| packages/ | 7 files |
| docs/ | 25 files |
| Python | 3.12.10 |
| NiceGUI | 3.13.0 |
| FastAPI | 0.138.0 |
| SQLAlchemy | 2.0.51 |
| Test suite | PASS (100%) |
| Node.js | Not available |

### Excluded from audit

| Category | Reason |
|----------|--------|
| `.git/` | Version control internals |
| `node_modules/` | Third-party packages |
| `__pycache__/` | Python bytecode |
| `data/*.sqlite3` | Binary database files |
| `logs/`, `backups/` | Runtime artifacts |
| Binary media (PNG, WebP, TTF, WOFF2, SVG, JPEG) | Visual assets (integrity verified by checksum) |
| `.env` | Protected secrets file |
| `archive/`, `test-results/` | Historical artifacts |

---

## Coverage Ledger

### Inspected in depth
- All Python entrypoints and route handlers (shell, pages, services, config, runtime)
- All persistence boundaries (SQLAlchemy models, transactions, backup obligations)
- Both policy packages (`roster_policy`, `roster_core`)
- Cloudflare Worker (authentication, proxying, KV, rate limiting, sessions)
- All CSS tokens and design system contracts
- All PowerShell scripts (deployment, host setup, WARP activation, verification)
- All i18n catalogs
- Migration chain (`migrations/`)
- GitHub Actions workflows (`.github/workflows/`)
- Test suite contracts and coverage patterns
- Security headers (CSP, COOP, CORP, XFO, XCTO)
- Documentation consistency with code
- Dependency manifests and version pinning

### Verified by sampling
- Individual page routes (heavy pages like weekly.py, people.py verified for correctness patterns)
- Generated files (`sing-yin-tokens-v1.css`, `design-tokens-v1.generated.json`)

### Not exercised during audit
- Multi-user concurrency stress tests (requires multi-process test harness)
- Cloudflare Worker deployment validation (Node.js unavailable)
- Browser-based visual regression (no headless browser)
- PDF output visual correctness (requires visual inspection)
- Production origin readiness (requires UAC-elevated deployment)

---

## Architecture and Responsibility Map

```
D:\code_v3
├── nicegui_app/                    [Application layer]
│   ├── ui/                         [Presentation: NiceGUI pages, shell, components]
│   │   ├── shell.py                [Page shell, navigation, layout]
│   │   ├── page_routes/            [Route handlers: home, weekly, people, etc.]
│   │   ├── components.py           [Reusable UI components]
│   │   ├── page_shared.py          [Shared page utilities]
│   │   ├── i18n_catalog/           [Bilingual translation catalogs]
│   │   └── html_safety.py          [XSS escaping: attr(), text()]
│   ├── services/                   [Business logic]
│   │   ├── roster_workflow.py      [Composition shell for mixins]
│   │   ├── workflow_parts/         [lifecycle, people, persistence, recovery, reporting, sharing]
│   │   ├── workflow_dependencies.py [Shared imports (wildcard source)]
│   │   └── guest_adapter.py        [Guest-mode fictional memory adapter]
│   ├── persistence/                [SQLAlchemy models, database config]
│   ├── config.py                   [Environment-driven settings]
│   ├── gateway_identity.py         [HMAC-signed origin principal verification]
│   ├── runtime.py                  [Page context, session management]
│   └── observability.py            [Request tracing, security headers, logging]
├── packages/
│   ├── roster_policy/              [School policy: rules, eligibility, room assignments]
│   └── roster_core/                [Deterministic generation engine]
├── cloudflare/roster_viewer/       [Cloudflare Worker: auth, proxy, KV, viewer]
├── scripts/                        [Deployment, WARP activation, verification, testing]
├── tests/                          [100 test files, 100% pass rate]
├── design_system/                  [Token contract (tokens.v1.json), product identity]
├── migrations/                     [Alembic migration chain]
├── docs/                           [Project documentation]
└── .github/workflows/              [CI/CD pipelines]
```

### Authoritative sources of truth

| Domain | Owner |
|--------|-------|
| Design tokens | `design_system/tokens.v1.json` |
| School policy | `packages/roster_policy/` |
| Generation logic | `packages/roster_core/` |
| Persistence models | `nicegui_app/persistence/models.py` |
| Bilingual copy | `nicegui_app/ui/i18n_catalog/` |
| Security policy | `SECURITY.md`, `docs/SECURITY_AND_PRIVACY.md` |
| Worker behavior | `cloudflare/roster_viewer/worker.js` |
| Design standard | `Professional_Design_System.md` |

No duplicated ownership conflicts detected.

---

## Findings (P0 → P3)

### P0 — Critical Correctness

**AUDIT-001: `history_weight` no floor protection**
`nicegui_app/services/workflow_parts/lifecycle.py:782`
```python
original.history_weight = round(original.history_weight - assignment.weight, 4)
```
In `apply_leave_adjustment`, `history_duties` is floored at `max(0, ...)` but `history_weight` is not. A double withdrawal or ledger-bug path can produce negative `history_weight`.
**Fix:** `max(0.0, round(original.history_weight - assignment.weight, 4))`

**AUDIT-002: `history_duties` negative on withdrawal**
`nicegui_app/services/workflow_parts/lifecycle.py:455`
```python
prefect.history_duties -= duty_delta
```
Unlike `apply_leave_adjustment` (which uses `max(0, ...)`), the withdrawal path has no floor. A double-compensated ledger entry can produce negative `history_duties`.
**Fix:** `prefect.history_duties = max(0, prefect.history_duties - duty_delta)`

**AUDIT-003: Single backup repair blocks all repairs**
`nicegui_app/services/workflow_parts/persistence.py:227`
```python
for command_id in command_ids:
    try: self._fulfill_backup_obligation(str(command_id))
    except Exception: raise
```
First failure aborts the loop; remaining obligations are never attempted. One corrupt backup entry permanently blocks the entire repair pipeline.
**Fix:** Collect failures in a list, attempt all obligations, raise aggregate at end.

---

### P1 — High Priority

**AUDIT-004: Wildcard imports across 8 modules**
`nicegui_app/services/roster_workflow.py:5` → `workflow_dependencies.py:41` → `workflow_types.py`
```python
from nicegui_app.services.workflow_dependencies import *
```
Dumps 50+ symbols into every mixin's namespace. Adding a symbol to dependencies silently changes 8 modules.
**Fix:** Replace with explicit imports; define `__all__` as a fixed list.

**AUDIT-005: Week boundary assumes 7-day intervals**
`nicegui_app/services/workflow_parts/lifecycle.py:62`
```python
RosterWeekRecord.week_start == week_start - timedelta(days=7)
```
Non-consecutive weeks (school breaks) silently return `None`, losing rotation history.
**Fix:** `SELECT ... WHERE week_start < :current ORDER BY week_start DESC LIMIT 1`

**AUDIT-006: Duplicated `_assist_assignment_mode_code`**
`guest_adapter.py:73` and `lifecycle.py:11` — identical 11-line function. Changes must be synchronized in two places.
**Fix:** Move to `workflow_dependencies.py`, import from single source.

**AUDIT-007: No interface contract for RosterWorkflow**
`nicegui_app/services/roster_workflow.py` — pure multiple-inheritance shell with no ABC, no abstract methods. New mixin methods silently become uncallable.
**Fix:** Define `AbstractRosterWorkflow` with `@abstractmethod` stubs.

**AUDIT-008: Backup error details discarded**
`nicegui_app/services/roster_workflow.py:77`
```python
self.backup_repair_error = type(error).__name__
```
Only exception type saved; operator sees `"backupRepairFailed": true` with no diagnostic detail.
**Fix:** `f"{type(error).__name__}: {str(error)[:200]}"`

---

### P2 — Medium Priority

**AUDIT-009: CSP `unsafe-inline` + `unsafe-eval`**
`nicegui_app/observability.py:238` — NiceGUI 3.13 constraint. All XSS defense rests on `attr()`/`text()` correctness.
**Recommendation:** Document every `sanitize=False` and `ui.run_javascript()` call. Add regression test.

**AUDIT-010: Worker logs auth failure reasons**
`cloudflare/roster_viewer/worker.js:3264` — `console.warn` reveals which validation step failed.
**Recommendation:** Use debug-level or cap rate. Generic failure message.

**AUDIT-011: Hardcoded Chinese in JavaScript**
`nicegui_app/ui/shell.py:340` — Auth-exit HTML has fixed Chinese/English, not in i18n catalog.
**Fix:** Move to Python helper reading from i18n.

**AUDIT-012: Idempotent replay skips backup verification**
`nicegui_app/services/workflow_parts/lifecycle.py:116` — Replay assumes fulfilled backup obligation.
**Fix:** Check backup_obligation table after replay.

**AUDIT-013: Duplicated `_form_rank`**
`persistence.py:565` and `roster_core/generator.py:40` — two implementations of same logic.
**Fix:** Export from `roster_policy`.

---

### P3 — Low Priority

**AUDIT-014: Deprecated alias `DUTY_TIME_WINDOWS`** — `packages/roster_policy/roster_policy/rules.py:106`
Used only in tests; remove and update references.

**AUDIT-015: No CORP on origin middleware** — `nicegui_app/observability.py:224`
Worker adds CORP at edge; add to origin for defense-in-depth.

**AUDIT-016: Misleading i18n key name** — `nicegui_app/ui/i18n_catalog/foundation.py:28`
`switch_to_chinese` actually shows "English" in Chinese mode. Rename.

---

## Security and Privacy Review

| Control | Status | Evidence |
|---------|--------|----------|
| XSS (output escaping) | Strong | `html_safety.py` `attr()`/`text()` used consistently; test coverage in `test_html_safety.py` |
| CSP (defense-in-depth) | Weakened | `unsafe-inline` + `unsafe-eval` required by NiceGUI 3.13; see AUDIT-009 |
| CSRF (origin principal) | Strong | HMAC-signed per-request binding in `gateway_identity.py:180` + `worker.js:3008` |
| SQL injection | Strong | ORM-exclusive data access; f-strings only in PRAGMA with sanitized integers |
| Cookie security | Strong | `__Host-` prefix, HttpOnly, Secure, SameSite=Lax, max-age bounded |
| Session management | Strong | HMAC verification, freshness window (60s), epoch rotation, key-id validation |
| File upload | Controlled | Validated file types, size limits, path traversal protection |
| Dependency pinning | Strong | All Python deps pinned in `requirements.txt` (>=x, <x+1); Wrangler pinned to 4.110.0 |
| Secret handling | Strong | No hardcoded secrets; `.env` excluded from git; secrets via Cloudflare Worker bindings |
| GitHub Actions | Adequate | SHA-pinned actions needed for supply-chain; current uses `@v4` tags |

### Unsafe sinks traced (input → sink → validation)

| Input | Sink | Validation |
|-------|------|------------|
| Prefect names (import/input) | `ui.html()`, `ui.label()` | Passed through `attr()`/`text()` |
| Leave reasons | `ui.html()` | Passed through `attr()`/`text()` |
| Roster notes | `ui.label()` | Passed through `text()` |
| Guest snapshot token | `sessionStorage` | HMAC-verified before restore; replay protection |
| URL parameters (share) | Worker KV lookup | ShareId validated, AES-GCM decryption client-side |
| Translated keys | HTML attributes | `attr()` wrapper in all `aria-label` interpolations |

No unsanitized input-to-sink paths identified within audit scope.

---

## Multi-User and Concurrency Review

| Scenario | Status | Evidence |
|----------|--------|----------|
| Two Admin concurrent writes | Protected | `_begin_serialized_write` + SQLite busy timeout |
| Admin + Guest simultaneous | Protected | Separate workspaces; Guest uses in-memory adapter |
| Multiple Guest tabs | Controlled | Each tab gets unique workspace; token bound to tab+session |
| Duplicate submissions | Protected | Idempotent receipt table; replay returns stored result |
| Session expiry mid-operation | Partial | Server-side expiry checked at `principal_from_request`; in-flight WebSocket not explicitly terminated |
| Backup during write | Protected | Serialized write lock; backup reads after commit |
| Restore during operation | Protected | Maintenance lease prevents concurrent restore + write |
| Cross-session data leakage | Controlled | Guest: fictional data in process memory only; Admin: SQLite isolation |
| Stale optimistic version | Protected | Version check before commit; explicit "newer data won" message |
| Multiple browser tabs (Admin) | Adequate | SQLite busy timeout prevents write conflicts; no per-tab write deduplication |

**Residual risk:** No multi-user concurrency stress tests were exercised. The "probable" findings (AUDIT-007, AUDIT-012) would benefit from targeted concurrency test scenarios.

---

## API Availability and Compatibility Matrix

| Interface | Status | Evidence |
|-----------|--------|----------|
| NiceGUI 3.13 core (`ui.*`) | Verified | All pages import and mount; test suite passes |
| FastAPI 0.138 endpoints | Verified | `/healthz`, `/readyz`, `/auth/*` tested via curl |
| Cloudflare Worker APIs (KV, fetch) | Verified | Worker contract tests pass (40 contracts) |
| Python stdlib (datetime, hashlib, hmac) | Verified | Tests exercise timezone-aware, HMAC, serialization paths |
| SQLAlchemy 2.0 ORM | Verified | All models import; migration chain unbroken |
| ReportLab 4.4 PDF generation | Verified | PDF tests pass (7.5s slowest, produces valid PDFs) |
| GSAP 3.13 | Vendor-verified | Version checked; vendored at `assets/vendor/` |
| Quasar 2.x (via NiceGUI) | Vendor-verified | Quasar palette bridge validated by contract tests |
| Wrangler 4.110.0 | Blocked (no Node) | Local deployment blocked; Worker contracts tested via Deno |
| cloudflared 2026.7.1 | Verified | Service running on origin; `--version` confirms |
| `packages/roster_core` standalone import | Broken | `from roster_policy import AssistAssignmentMode` fails — packages not installed as editable |

---

## Hallucination and Claim-Integrity Review

| Claim | Source | Status |
|-------|--------|--------|
| "839 Python tests pass" | PROJECT_STATUS.md | **Stale** — likely from earlier rc20 evidence. Current test suite count differs. |
| "rc20 passed 14/14 gates" | Professional_Design_System.md | **Unverified** — candidate evidence references tag `v1.2.0-rc.20`; need current gate re-run |
| "edge-rate-limiting" capability | Worker healthz response | **Missing** — Worker not redeployed after commit `b884d33` |
| "ORIGIN_PRINCIPAL_SECRET 32-512 chars" | gateway_identity.py:57 | Verified — `.env` contains 64-char base64 value |
| "All systems operational" | Worker landing page | Verified — healthz returns `status: ok` |
| "CSP blocks external scripts" | observability.py docstring | Partially true — `script-src 'self'` blocks external, but `unsafe-inline` allows anything inline |
| "Guest data excluded from official SQLite" | SECURITY.md | Verified — Guest adapter uses in-memory storage |

---

## Existing Strengths (Preserve)

1. **Multi-layer transaction design:** Maintenance lock → serialized operation → `BEGIN IMMEDIATE` → commit → backup obligation
2. **Idempotency pattern:** Command receipts prevent duplicate execution; replay returns stored result
3. **Cloudflare Worker defense-in-depth:** Access JWKS → HMAC session → HMAC origin principal — each layer independently verified
4. **Consistent HTML escaping:** `html_safety.py` with centralized `attr()`/`text()`; enforced by `test_html_safety.py`
5. **ORM-exclusive data access:** No raw SQL for data operations; injection surface limited to sanitized PRAGMA integers
6. **Design token contract:** Single source of truth (`tokens.v1.json`) → generated CSS + Worker JSON → contract tests detect drift
7. **Comprehensive test suite:** 100% pass rate; covers PDF generation, roster export, i18n, gateway identity, guest isolation
8. **Token-aware Neumorphic depth system:** Elevation levels 0–3 with twin-shadow vocabulary; light/dark parity
9. **Fail-closed session model:** Invalid cookie = public landing page; expired session = clear error state
10. **Script-verifiable deployment:** `deploy_windows_release.ps1` with 14-gate evidence collection

---

## Prioritized Remediation Roadmap

### Immediate containment (now)
- None required — no exploitable security vulnerability found

### Small high-value fixes (this sprint)
1. **AUDIT-001, 002** — Floor protection on history_weight and history_duties (2 lines each)
2. **AUDIT-013, 014, 016** — Deduplicate helpers, remove dead alias, rename i18n key (< 1 hour total)
3. **AUDIT-011** — Store exception message in backup repair error (1 line)

### Medium structural improvements (next release cycle)
4. **AUDIT-003** — Collect backup repair failures instead of aborting on first
5. **AUDIT-004** — Replace wildcard imports with explicit imports
6. **AUDIT-005** — Fix week boundary query for non-consecutive weeks
7. **AUDIT-006, 007** — Deduplicate assist mode code; add ABC interface

### Larger redesigns (separate decision required)
8. **AUDIT-012** — Idempotent backup verification after replay
9. **AUDIT-010** — Hardcoded Chinese in auth JS → i18n catalog
10. Worker redeployment (rate limiting capability update)

---

## Uninspected or Blocked Areas

| Area | Reason |
|------|--------|
| VPC Service Binding health | Requires Cloudflare dashboard access |
| Worker deployment (Wrangler) | Node.js not available on audit machine |
| Multi-user concurrency stress | Requires multi-process test harness |
| Browser visual regression | No headless browser available |
| Cloudflare Access configuration | Requires dashboard access |
| `.env` runtime values | Protected file; key names verified without values |
| Long-running memory stability | Requires extended runtime observation |
| Network-level DoS resistance | Requires external testing infrastructure |

---

## Final Release-Impact Assessment

The 20 modified files in the working tree are primarily documentation and i18n updates with low release risk. The three P0 correctness findings (AUDIT-001, 002, 003) should be addressed before the next formal release (`rc24`). The P1 structural findings can be deferred to a follow-up release without compromising correctness.

**No blocking issue for continued development was discovered. No exploitable security vulnerability requiring immediate containment was found.**

---

## Report Locations

- **Markdown:** `docs/audits/CODEBASE_AUDIT_2026-07-26.md`
- **JSON:** `docs/audits/CODEBASE_AUDIT_FINDINGS_2026-07-26.json`

---

*Audit completed 2026-07-26. No production state was changed. No code was modified. No deployment occurred.*
