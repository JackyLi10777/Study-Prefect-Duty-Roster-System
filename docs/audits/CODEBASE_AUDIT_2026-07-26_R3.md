# R3 Deep Code Audit — Beyond R1/R2 Coverage

**Round:** 3 of 3
**Date:** 2026-07-26
**Focus:** API hallucination, code quality, architecture, performance — issues R1/R2 did not find

---

## Executive Summary

R3 found **17 new findings** (3 P0, 4 P1, 6 P2, 4 P3) across three deep-dive areas. R3 confirmed many of R2's structural observations while uncovering new issues in API version mismatches, Wrangler configuration validity, code-level no-ops, race conditions, and missing comments at critical algorithm boundaries.

**New critical findings R1/R2 missed:**

1. `fastapi>=0.139` constraint violated (0.138.0 installed) — `requirements.txt`
2. `vpc_services` and `ratelimits` keys in `wrangler.jsonc` may be silently ignored by Wrangler 4.x
3. `except Exception: raise` no-op in backup repair loop — `persistence.py:226`
4. `AssertionError` for control flow in guest adapter (stripped by `python -O`)
5. TOCTOU race in `current_page_context()` — `runtime.py:562`
6. `_availability_by_prefect()` full-table scan 3-4x per generation — `persistence.py:364`

---

## Findings

### P0 — Critical

**R3-001: fastapi version constraint violated**
`requirements.txt:2` — Requires `fastapi>=0.139,<0.140` but `pip show fastapi` reports `0.138.0`. `pip install -r requirements.txt` would reject the installed version.

**R3-002: `vpc_services` key unrecognized in Wrangler 4.x**
`cloudflare/roster_viewer/wrangler.jsonc:61` — Wrangler 4.x uses `services` for service bindings, not `vpc_services`. This may be silently ignored. The Worker may deploy without VPC connectivity.

**R3-003: `ratelimits` key unrecognized in Wrangler 4.x**
`cloudflare/roster_viewer/wrangler.jsonc:37` — Rate limits are API/Dashboard-managed in Wrangler 4.x, not declared in `wrangler.jsonc`. May be silently ignored.

---

### P1 — High

**R3-004: `AssertionError` for production control flow**
`nicegui_app/services/guest_adapter.py:329` — `raise AssertionError(...)` can be stripped with `python -O`. Replace with `WorkflowError` or `CapabilityDeniedError`.

**R3-005: No-op `except: raise` in backup repair loop**
`nicegui_app/services/workflow_parts/persistence.py:226-229` — The `try/except Exception/raise` catches everything and re-raises. `repaired += 1` at line 229 is unreachable after any exception. Either dead debugging code or intended skip-on-failure.

**R3-006: TOCTOU race in `current_page_context()`**
`nicegui_app/runtime.py:562-607` — Cache read outside lock, computation outside lock, write inside lock. Two concurrent loads from same client_id both miss cache, both compute, second silently overwrites.

**R3-007: `_availability_by_prefect()` full scan 3-4x per generation**
`nicegui_app/services/workflow_parts/persistence.py:364-368` — Called from `_active_prefects()`, `prefects()`, `generation_requirements()`, `_eligible_assignment_candidates()`. Single `generate_and_save_draft()` triggers 3-4 full availability table scans.

---

### P2 — Medium

**R3-008: 16 HTTP requests per page cold load**
`nicegui_app/ui/theme_markup.py:11-22` — 10 CSS `<link>` tags + 1 font preload + 3-4 JS scripts. No bundling. Each CSS file forces separate style recalculation.

**R3-009: ~200 LOC duplicated between Admin and Guest adapter**
`guest_adapter.py` copies 7 utility/validation functions from `workflow_parts/*.py` identically. Any rule change must be made in two places.

**R3-010: Critical algorithm comment missing in DP scheduler**
`packages/roster_core/roster_core/generator.py:358` — `candidate_state[:2] < current[:2]` deliberately excludes rotation_rank from state comparison. No comment explaining why — maintainer could "fix" and break stability.

**R3-011: `_render_period_report` is 170-line monolith**
`nicegui_app/ui/page_routes/people.py:329-556` — One function with 4 inner functions, 10+ UI sections. Cannot be tested in isolation.

**R3-012: Fragile string parsing for `data-testid` extraction**
`nicegui_app/ui/page_shared.py:737-744` — Parses `action_props` string with mini-tokenizer. Future values with embedded `=` silently break.

**R3-013: `workflow_dependencies.py` hub anti-pattern**
Imports from ALL layers and re-exports via `globals()`. Every mixin transitively depends on everything.

---

### P3 — Low

**R3-014: 7 missing `.env.example` entries** — Private WARP, APP_MODE, DATABASE_PATH, BACKUP_DIR, PUBLIC_URL, SLOW_REQUEST_MS
**R3-015: Misleading function name `_safe_read_action`** — synchronous, not async
**R3-016: `_page_contexts` dict unbounded growth** — no TTL cleanup
**R3-017: Fragile lambda closure in download_options loop** — `selected=kind` pattern

---

## Cross-Round Consolidated Summary

| Round | P0 | P1 | P2 | P3 | Total |
|-------|----|----|----|----|-------|
| R1 (opencode) | 3 | 5 | 5 | 3 | 16 |
| R2 (Codex) | 0 | 0 | 3 | 2 | 5 |
| R3 (opencode deep) | 3 | 4 | 6 | 4 | 17 |
| **Combined unique** | **5** | **8** | **12** | **8** | **33** |

### Top 10 Root Causes (All 3 Rounds Combined)

| # | Finding | Round | Priority |
|---|---------|-------|----------|
| 1 | `fastapi` version mismatch (0.138 vs >=0.139) | R3 | P0 |
| 2 | `wrangler.jsonc` unrecognized keys (vpc_services, ratelimits) | R3 | P0 |
| 3 | `history_weight` no floor → R2 disproved (rollback safe) | R1→R2 | **Retracted** |
| 4 | `history_duties` no floor → R2 disproved (rollback safe) | R1→R2 | **Retracted** |
| 5 | `AssertionError` as control flow (stripped by `-O`) | R3 | P1 |
| 6 | No-op `except: raise` in backup repair | R3 | P1 |
| 7 | TOCTOU race in `current_page_context()` | R3 | P1 |
| 8 | 83 wildcard symbols across 8 modules (import *) | R1/R2 | P1 |
| 9 | Week boundary assumes 7-day intervals | R1/R2 | P1 |
| 10 | `_availability_by_prefect` redundant full scans | R3 | P1 |

### Strongest Controls Confirmed

- Guest isolation: watertight, zero real-data exposure
- Dependency direction: clean (no upward violations)
- No async blocking calls in request paths
- NiceGUI 3.13.0 API: all 30+ imports verified present
- DeepSeek API: endpoint + model ID confirmed against official docs
- Capability system: enforced at all boundaries

### Recommended First Batch (R3 context, unaddressed)

1. Fix `requirements.txt` fastapi constraint or upgrade to 0.139
2. Validate `wrangler.jsonc` with `--dry-run --strict` (needs Node.js)
3. Replace `AssertionError` → `WorkflowError` in guest adapter (5 min)
4. Fix or remove no-op `except: raise` in backup repair (5 min)
5. Cache `_availability_by_prefect` per session (1h)
6. Add missing algorithm comment at `generator.py:358`

---

*R3 audit completed. No code modified. No deployment occurred.*
