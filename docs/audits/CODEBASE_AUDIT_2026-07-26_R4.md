# R4 Extended Audit — Frontend, Tests, Scripts, Edge Cases

**Round:** 4 of 4
**Date:** 2026-07-26
**Focus:** CSS/JS/ARIA quality, test quality, CI/scripts, error recovery, docs, edge cases

---

## Executive Summary

R4 audited 3,000+ lines of CSS, 700+ lines of JavaScript, 807 test functions, 7 PowerShell scripts, 11 Alembic migrations, 26 docs files, and traced all error recovery paths. Found **2 HIGH**, **7 MEDIUM**, **8 LOW**. The frontend has excellent accessibility (focus trap, skip link, 44px touch targets, ARIA coverage) but needs CSS variable consolidation. The test suite is notably strong — zero `unittest.mock.patch`, zero `assert True`, comprehensive security boundary testing.

---

## Findings

### HIGH (2)

**R4-H1: CHANGELOG.md stale — missing rc22-rc26 entries**
`CHANGELOG.md:5-43` — Last entry v1.2.0-rc.21. Git log has rc22, rc23, rc24, rc26. Key security and CSP changes undocumented.

**R4-H2: pyproject.toml incomplete**
`pyproject.toml` — Only 7 lines (pytest config only). Missing `[project]` metadata (name, version, dependencies), `[build-system]`, package entry points. Not a valid Python package declaration. `packages/roster_core` standalone import fails because it's not installed as editable.

---

### MEDIUM (7)

**R4-M1: Silent WorkflowError swallows in UI**
`weekly.py:435-436, 502-503` — `refresh_requirements()` and `refresh_leave_list()` catch `WorkflowError` and return `None` silently. User sees nothing change with no explanation.

**R4-M2: No SQLite BUSY/FULL error handling in workflow**
Throughout `lifecycle.py`, `persistence.py` — `BEGIN IMMEDIATE` raises `OperationalError` directly to caller on locked/full DB. No retry, no user-facing recovery message.

**R4-M3: Backup obligation gap after commit**
`lifecycle.py:382-390` — `session.commit()` succeeds but if `_fulfill_backup_obligation` fails (OSError), the write is durable but unrecoverable. Startup repair won't find it.

**R4-M4: README-EN.md not a translation**
`README-EN.md` vs `README.md` — Different structure and content. Some sections only in Chinese (music setup), some only in English (policy invariants). Claimed as bilingual parity but isn't.

**R4-M5: 10+ CSS hardcoded colors in `.sy-daily-start`**
`sing-yin-theme-v1.css:358-366` — Chapel, devotional companion, hero sections use hardcoded `#F5EEDC`, `#213047`, `#8B6A30` etc. Should use `--sy-daily-*` tokens.

**R4-M6: Fragile Quasar internal selectors**
`sing-yin-theme-v1.css:106,144` — `.q-img__image--with-transition` and extreme-specificity button selector `body .q-btn.q-btn--standard.bg-primary:not():not():not():not()`. Will break on Quasar upgrade.

**R4-M7: OPERATOR_GUIDE claims 8 release gates**
`OPERATOR_GUIDE.md:116` — Actual system has 14 gates. Count mismatch could confuse operators reviewing deployment safety.

---

### LOW (8)

| ID | Finding | Location |
|----|---------|----------|
| R4-L1 | 16 CSS/JS requests per page — no bundling | `theme_markup.py:11-22` |
| R4-L2 | Scrollbar hidden on mobile tab overflow — a11y | `sing-yin-mobile-v1.css:136-137` |
| R4-L3 | Music attempt/retry JS duplicated | `music.py:121-146` |
| R4-L4 | CODEX_PROMPTS.md stale (last update 2026-07-10) | `CODEX_PROMPTS.md:3` |
| R4-L5 | ~25 modules with zero direct test coverage | UI routes, deployment, sound, pdf_delivery |
| R4-L6 | No holiday calendar — holiday Monday = normal Monday | `roster_policy` |
| R4-L7 | Race conditions in maintenance lease — benign | `maintenance.py` |
| R4-L8 | clipboard/YouTube errors swallowed without detail | `access_control.py`, `youtube_music.py` |

---

## Test Quality Summary

| Metric | Result |
|--------|--------|
| Total test functions | 807+ |
| `unittest.mock.patch` usage | **Zero** — uses pytest `monkeypatch` only |
| `assert True` | **Zero** |
| `assert X is not None` | 37 instances (most followed by stronger assertions) |
| Guest boundary tests | 8 files, all excellent (crypto validation, AST audits, error paths) |
| PDF export tests | Parses actual PDFs with `pypdf`, verifies embedded fonts, bilingual content |
| Gateway identity tests | Cross-language (Python↔JS) token validation, HMAC, epoch rotation |
| HTML safety tests | Source-code AST scan for unescaped aria-labels |
| Design token tests | CSS variable resolution, Quasar palette, generated-file drift detection |

---

## CI / Scripts Summary

| Component | Assessment |
|-----------|-----------|
| GitHub Actions (2 workflows) | SHA-pinned actions, `contents: read` only, no secret exposure |
| `deploy_windows_release.ps1` (992 lines) | 14-gate evidence, rollback, secret redaction, admin-only, fingerprint verification |
| `windows_host_common.ps1` (576 lines) | Raw Win32 ACL hardening, SID-based verification, no hardcoded secrets |
| `prepare_windows_host.ps1` | `--require-hashes`, Python 3.12 verification, ACL-protected .env |
| `start_sing_yin_roster.ps1` | Mutex-enforced single instance, port fallback, cleanup in `finally` |
| `verify_update.py` | Fail-closed on unknown paths, risk-based profiles, atomic report writes |
| Alembic (11 migrations) | Unbroken chain, all have `downgrade()`, guarded downgrades (0009, 0011) |

---

## HTML Safety Complete Coverage

`html_safety.py` usage verified across entire codebase:
- `attr()` — 72+ calls (all `aria-label` and HTML attribute interpolations)
- `text()` — 30+ calls (all text content interpolations)
- `ui.html(sanitize=False)` — 1 occurrence (`support.py:179`), all values properly escaped
- `ui.run_javascript()` — 35 calls, all use `json.dumps()` / `repr()` / `.lower()` for safe injection
- **No raw user input in any HTML or JavaScript injection.** Zero XSS vectors found.

---

## Top 5 Actions (R4 context)

1. Update CHANGELOG.md with rc22-rc26 entries
2. Complete `pyproject.toml` with `[project]` metadata
3. Add SQLite error handling (`SQLITE_BUSY`, `SQLITE_FULL`) with user-visible recovery
4. Consolidate hardcoded CSS colors into `--sy-daily-*` tokens
5. Replace fragile Quasar internal selectors (`.q-img__image--with-transition`, extreme button specificity)

---

*R4 audit completed. No code modified. No deployment occurred.*
