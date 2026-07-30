# R7 Extended — Post-RC35 Deep Audit: Scripts, Worker, Packages

**Date:** 2026-07-29
**Baseline:** `9831c69` (rc35 production-truth merged)
**Scope:** 3 sub-audits covering previously unexamined code areas
**Test suite:** 100% pass (0 failures)

---

## New Findings Summary

| Severity | Count | Categories |
|----------|-------|------------|
| P0 | 2 | Rollback leaves host unbootable if pip fails; env backup missing for pre-line-975 failures |
| P1 | 5 | Control chars in .env parsing, case-sensitive SID, shared .tmp race, unpinned winget, silent port-release failure |
| P2 | 8 | Worker KV delete race, policy export gap, implicit ordering contract, anchor backfill trust-on-first-use, etc. |
| P3 | 15 | Cookie case inconsistency, HTML interpolation fragility, JWT exp boundary, dead code, relative DB path, etc. |

---

## P0 — Critical

### R7-S1: Rollback leaves host unbootable if pip install fails
**File:** `scripts/deploy_windows_release.ps1:1228-1235`
**Classification:** Deployment reliability defect

During rollback, the script switches to the previous commit (`line 1222`), then runs `pip install --require-hashes -r requirements.lock` (`line 1228`). If pip install fails, the rollback marks `$rollbackError` but the host is ALREADY on the old commit without matching dependencies. The system boots in a broken state with no matching Python packages.

**Impact:** A failed deployment attempting to rollback can permanently break the production origin, requiring manual recovery.

**Disposition after adjudication:** Superseded and resolved. The controlled deployer now builds an independent immutable source＋virtual-environment bundle, verifies it before downtime, atomically changes the scheduled-task action, and retains the prior bundle unchanged for rollback. Pre-installing into the running shared environment would not have been atomic.

### R7-S2: Environment backup missing for failures before line 975
**File:** `scripts/deploy_windows_release.ps1:1238-1242`
**Classification:** Deployment reliability defect

`$environmentBytes` is captured at `line 975`. If deployment fails between lines 837-974 (repository hygiene, tag verification, task inspection, env overlay read), rollback has NO original `.env` bytes to restore. The silent `$null -ne $environmentBytes` guard skips restore, leaving the mutated `.env` in place.

**Impact:** After a failed deployment, the origin may have a corrupted `.env` with no backup to restore.

**Fix:** Capture environment backup at the earliest safe point (immediately after parameter validation at line ~550).

---

## P1 — High

### R7-S3: .env value regex passes embedded control characters
**File:** `scripts/windows_host_common.ps1:30-33`
**Classification:** Input validation defect

```powershell
^\s*(?<name>SING_YIN_[A-Z0-9_]+)\s*=\s*(?<value>.*)$
```

`(?<value>.*)` accepts null bytes, newlines, tabs. `.Trim()` only strips surrounding whitespace, not embedded control characters.

**Fix:** Add a character denylist to the value capture group.

### R7-S4: Case-sensitive SID comparison produces false negatives
**File:** `scripts/windows_host_common.ps1:548`
**Classification:** ACL verification defect

```powershell
if ($sid -ceq $RequiredIdentitySid) {
```

Windows SIDs are case-insensitive. A lowercase SID (`s-1-5-18`) would fail `-ceq` against uppercase (`S-1-5-18`).

**Fix:** Use `-eq` (case-insensitive) instead of `-ceq`.

### R7-S5: Shared temp file TOCTOU under concurrency
**File:** `scripts/verify_update.py:537-539`
**Classification:** Concurrency defect

```python
temporary = REPORT_PATH.with_suffix(".tmp")
temporary.write_text(...)
temporary.replace(REPORT_PATH)
```

Two concurrent instances write to the same `.tmp` file, producing interleaved JSON.

**Fix:** Use a random temp filename (e.g., `.tmp.<uuid>`) instead of fixed `.tmp`.

### R7-S6: Winget installs unpinned versions
**File:** `scripts/prepare_windows_host.ps1:35-36,71`
**Classification:** Supply chain risk

Neither `Git.Git` nor `Python.Python.3.12` has version pins. Future releases with breaking changes are installed silently.

**Fix:** Add `--version` pin for Git and Python packages.

### R7-S7: Rollback swallows port-release failure silently
**File:** `scripts/deploy_windows_release.ps1:1217-1219`
**Classification:** Error handling defect

```powershell
try { Wait-PortReleased -Port $deploymentPort -TimeoutSeconds 15 } catch { }
```

Empty catch masks port-not-released condition. Subsequent restart fails silently.

**Fix:** Log the error and retry or abort.

---

## P2 — Medium

### R7-W1: deleteShare TOCTOU race with concurrent createShare
**File:** `cloudflare/roster_viewer/worker.js:4085-4089`
**Classification:** Concurrency defect

Between `listKvKeys` and batch `delete`, a concurrent `createShare` can write new keys that survive deletion. No post-delete verification or idempotency token.

**Disposition after adjudication:** Superseded and resolved. Permanent no-digest revocation tombstones are checked by create, read and list paths; conflicting recreation is rejected. A post-delete list alone would still be unsafe under eventual consistency.

### R7-P1: ROOM_CAPACITY policy rule not exported
**File:** `packages/roster_policy/roster_policy/rules.py:109`
**Classification:** Module boundary defect

`ROOM_CAPACITY` is a first-class policy constant used in `required_posts_for_day` but absent from `__init__.py` exports.

**Fix:** Add to `__all__` in `roster_policy/__init__.py`.

### R7-P2: Implicit ordering contract in generate_weekly_roster
**File:** `packages/roster_core/roster_core/generator.py:828-841`
**Classification:** Correctness risk

`next(regular_assignments)` depends on `_solve_regular_schedule` and `required_posts_for_day` enumerating slots in identical `(day, post)` order. No assertion validates this.

**Fix:** Add an assertion or zip-based matching instead of `next()`.

### R7-P3: Anchor backfill has no post-computation integrity check
**File:** `migrations/versions/0003_role_and_fairness_integrity.py:48-56`
**Classification:** Data integrity risk

The anchor backfill SQL computes `current_weight - sum(ledger_deltas)` with no post-backfill reconciliation check. Silent corruption would propagate into all future fairness calculations.

**Disposition after adjudication:** Superseded and resolved without rewriting historical migration 0003. Runtime bootstrap／readiness and isolated restore preflight reconcile every fairness anchor against its ledger and fail closed on disagreement. Any future schema change must remain additive.

### R7-A1: prepare_windows_host PATH refresh can duplicate entries
**File:** `scripts/prepare_windows_host.ps1:22`
**Classification:** Configuration hygiene

### R7-A2: register_windows_startup_task plaintext password in GC memory
**File:** `scripts/register_windows_startup_task.ps1:59,73`
**Classification:** Secret handling

`$plainPassword = $null` does not zero heap memory in .NET Framework. Password persists until overwritten by GC.

### R7-A3: generate_design_system_tokens no input validation
**File:** `scripts/generate_design_system_tokens.py:14-18`
**Classification:** Input validation

Malformed JSON produces confusing deep-stack traceback instead of clear parse error.

### R7-A4: verify_release_candidate leaks temp directories
**File:** `scripts/verify_release_candidate.py:476`
**Classification:** Resource leak

`shutil.rmtree(workspace, ignore_errors=True)` — locked files silently leave stale temp dirs.

---

## P3 — Low

### Worker.js

| ID | Finding | Line(s) | Description |
|----|---------|---------|-------------|
| R7-W2 | Cookie strip case inconsistency | 3487-3489 | 3 session cookies use exact case while ACCESS_COOKIE uses toLowerCase() |
| R7-W3 | HTML interpolation fragile | 2787 | `${reference}` interpolated without entity escaping |
| R7-W4 | JWT exp uses <= instead of < | 3198,3247,3422 | Off-by-one second; token invalidated early |
| R7-W5 | adminSessionSecret missing placeholder check | 2935-2941 | `isObviousSecretPlaceholder` not called (guest + origin secrets do call it) |
| R7-W6 | Post-write KV read stale under eventual consistency | 4023-4027 | May return spurious 409 conflict |
| R7-W7 | Revocation reuses unsanitized client headers | 3539 | Passes through stripAccessCredentials but intermediate objects carry raw headers |

### Packages + Migrations

| ID | Finding | Line(s) | Description |
|----|---------|---------|-------------|
| R7-P4 | is_ahp_role dead at API boundary | rules.py:129-134 | Not exported, not used in generator |
| R7-P5 | DUTY_TIME_WINDOWS aliases wrong mapping | rules.py:106 | Name suggests duty service times but points to room opening times |
| R7-P6 | Fallback schedule ignores fairness history | generator.py:428-437 | Sets history_priority_multiplier=0.0 |
| R7-P7 | No max-days-per-week enforcement | generator.py:48-49 | Prefect could be assigned 3+ days |
| R7-P8 | env.py missing target_metadata | env.py:37 | autogenerate silently broken |
| R7-P9 | alembic.ini relative DB path | alembic.ini:4 | Run from wrong directory = migrate wrong database |

---

## Cross-Round Consolidated Status

| Round | P0 | P1 | P2 | P3 | Total | Fixed/Accepted in rc35 |
|-------|------|------|------|------|-------|----------------------|
| R1 | 3 | 5 | 5 | 3 | 16 | 3 |
| R2 | 0 | 0 | 3 | 2 | 5 | 2 |
| R3 | 3 | 4 | 6 | 4 | 17 | 4 |
| R4 | 0 | 2 | 7 | 8 | 17 | 5 |
| R5 | 0 | 2 | 5 | 6 | 13 | 6 |
| R6 | 0 | 1 | 3 | 8 | 12 | 4 |
| **R7** | **2** | **5** | **8** | **15** | **30** | **0** (new round) |
| **Total** | **8** | **19** | **37** | **46** | **110** | **24 fixed**

---

## Post-rc35 Pre-Deployment Verdict

**BLOCKED** — 2 new P0 findings in deployment rollback script (`deploy_windows_release.ps1`)

### Immediate blockers (for rc36):
1. **R7-S1** — Fix rollback pip-install failure path (pre-verify pip before switching git)
2. **R7-S2** — Capture environment backup at earliest safe point (line ~550)

### Next-release (rc36):
3. **R7-S3** — Denylist control chars in .env value regex
4. **R7-S4** — Case-insensitive SID comparison
5. **R7-S5** — Randomize temp filename in verify_update
6. **R7-S6** — Pin winget package versions
7. **R7-S7** — Log (don't swallow) port-release failure

### Optional cleanup:
8. **R7-W1** — Add post-delete verification for share deletion
9. **R7-P1** — Export ROOM_CAPACITY from policy package
10. **R7-P2** — Add ordering assertion in generate_weekly_roster
11. **R7-P3** — Add anchor backfill integrity check

---

*Audit completed 2026-07-29. No code modified. No production state changed. Report: `docs/audits/CODEBASE_AUDIT_2026-07-29_R7.md`*
