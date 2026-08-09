# rc54 integrated review and release ledger

**Status:** source candidate under verification; not production evidence.

**Review date:** 2026-08-09
**Protected-main baseline:** `f6d602131714bd356769cf6ca04c06eba69f12b1`
**Production truth:** remains owned by `docs/status/current-release.json` and fresh host／Worker evidence. At the start of this review, the generated status still identified `v1.2.0-rc.52`, Alembic `0013` and Worker `3bac2eee-246f-4524-9725-4249770017b0` as live. Nothing in this candidate section changes that claim.

## Parallel-work integration boundary

Another Codex task completed the rc53 source merge and then corrected the rendered browser verifier after the duplicate sidebar Support card was intentionally removed. Its PR #102 was squash-merged as `f6d6021`; this candidate was stashed, rebased onto that exact protected-main commit and restored without conflicts. The post-rebase focused suite passed. No production file was copied over source and no old branch was used as a deployment input.

Before merge or release, the candidate must fetch protected main again, rebase or merge through the repository-approved policy, rerun affected gates and compare the final release tree with the staged manifest. This is the anti-regression boundary for any later parallel task.

## Current change review

| Area | Finding and disposition | Evidence owner |
|---|---|---|
| Public Support theme | Confirmed visual parity gap. Fixed by using the entrance-family binary sun／moon control, current-state glyph, next-action label, bounded transition, storage sync and reduced-motion fallback. | Worker contracts and staged browser smoke |
| Mobile drawer | Confirmed race and geometry gap. Fixed with one requested-open state, a dedicated fixed top-right Close control, RAF-coalesced observer reconciliation, focus／inert／ARIA synchronization and complete teardown. | `test_mobile_layout.py`, accessibility tests and rendered mobile verifier |
| Prefect inline save | Confirmed partial-write architectural risk in the rc53 row loop. Replaced by `PrefectPatch` plus one Admin transaction and one Guest workspace mutation. Every target is prevalidated; stale or invalid input returns zero writes. Valid Assistant Head fixed-day swaps are supported inside the same transaction. | prefect workflow, Guest adapter, concurrency and UI contract tests |
| Buffered UI state | Confirmed maintainability gap. `DraftEditSession` and `PrefectEditSession` now own reviewed baseline, pending intent, dirty count, stable command ID and conflict reapply; draft additionally owns move／selection and local undo／redo. Closed-day／closed-slot guards live in the typed draft session, not only presentation code. | typed-session unit tests and route static contracts |
| Guest receipts | Rechecked against R6 memory-growth concern. Receipts retain bounded command metadata plus request／result digests and revision, never a full state snapshot per command. Exact command reuse with a different request digest fails closed. | `test_guest_workspace.py`, `test_guest_adapter.py` |
| Theme observer | The remaining non-debounced body-class observer was confirmed. It now coalesces through one RAF and cancels that frame during cleanup. System resolution updates in place; the head resolves `prefers-color-scheme` before external theme CSS. | theme-preference and lifecycle tests |

## R1-R7 audit adjudication against current source

The older reports are discovery inputs, not a current verdict. The following items were rechecked in present source or executable contract tests:

| Historical concern | Current disposition |
|---|---|
| OS theme change silently reloads and loses forms | Fixed: system resolution is applied and remembered in place; only language retains the dirty-form reload guard. |
| Hidden or drifting three-state theme controls | Resolved by product decision: `system` is initialization only; every visible control is binary Light／Dark. Public entrance, `/support` and NiceGUI share the same state semantics while retaining intentionally separate persistence adapters. |
| MutationObserver theme churn | Fixed in this candidate with RAF coalescing and teardown. |
| PNG EXIF／ancillary metadata | Fixed in current main: bounded PNG is decoded and re-encoded before persistence, then its container is revalidated. |
| Guest workspace holds full state per receipt | Fixed: bounded digest／revision receipts only. The global receipt budget is explicit and tested. |
| UI retries receive a new database command ID | Fixed: workflow calls exposing `command_id` fail if the UI did not provide a stable ID. The typed sessions keep the ID for the exact pending intent. |
| IPv6 loopback accepted but rejected by TrustedHostMiddleware | Fixed: deployment validation explicitly rejects `::1`／`[::1]`. |
| Release evidence can be detached from source | Fixed in the controlled release path: annotated immutable tag, protected-main ancestry, source commit／tree／fingerprint, post-verification source, complete gate identities and immutable bundle marker are cross-checked. |
| Rollback mutates a shared virtual environment | Fixed: candidate source, hash-locked venv, environment and marker are built in a private staging directory and atomically renamed to an immutable release bundle before the task target can switch. |
| Early deployment failure loses `.env` | Fixed: exact environment bytes and ACL SDDL are captured before the first mutation and are available to rollback. |
| Permissive `.env` parsing | Fixed: one shared parser rejects malformed `SING_YIN_` entries, duplicates and C0／DEL controls. |
| Concurrent verifier uses one `.tmp` file | Fixed: same-directory unique temporary file, flush／fsync and bounded atomic replacement. |
| Worker share deletion race | Safety property fixed with a per-share revocation tombstone checked by create／view resolution before digest objects are cleaned. KV convergence can delay cleanup, but cannot make a revoked share readable again. |
| Direct origin returns 500 without gateway principal | Accepted fail-closed behavior, not a public availability defect. The origin is loopback-only; controlled local maintenance is a separate declared mode and direct LAN access must not bypass the gateway. |
| Winget package version is not an exact patch pin | Accepted residual recovery trade-off. Host preparation uses exact package identity/source and runtime version checks; exact patch pinning may disappear from Winget. Any future change must add an offline trusted-installer path rather than only a brittle pin. |
| GSAP Core loads on every NiceGUI route | Confirmed performance opportunity, not a security or correctness blocker. No plugin or second runtime was added. Conditional loading should be pursued only with measured route traces because the shared shell and icon lifecycle exist on routine routes. |

Items not named above remain governed by their latest adjudication, current tests and live verification; their historical severity is not automatically carried forward. No audit row is considered fixed solely because a report says so.

## Verification recorded before formal release

- Post-rebase focused integration: 147 tests passed across draft grid, prefect directory／workflow, Guest adapter／workspace, Worker, mobile drawer and icon interaction contracts.
- Security／i18n／accessibility／documentation／release-script focused suite: passed after replacing three stale source-string assertions with typed-session and single-state equivalents.
- Additional typed-session checks cover filtering against pending values and refusal to mutate closed days or unavailable slots.
- `python -m compileall -q nicegui_app tests` and `git diff --check` passed at the earlier integrated checkpoint; both must be repeated on the final clean tree.

These are development findings, not the formal 15-gate release report.

## Release blockers and completion rule

The candidate remains blocked from a production-complete claim until all of the following are true:

1. latest protected main and all concurrent tasks are reconciled without dropping either tree;
2. exact staged and clean-source verification passes, followed by the complete formal release profile;
3. protected-main merge and immutable annotated release tag identify the same tree;
4. previous-schema backup, isolated restore, candidate migration/readiness and rollback evidence pass;
5. Origin deploy, health, readiness and exact immutable bundle identity pass;
6. changed Worker source is deployed as a 0% candidate, version-smoked and only then promoted;
7. canonical Public, Admin redirect, Guest, Viewer and `/support` states are checked without sensitive data;
8. `current-release.json`, generated status, changelog and release evidence are updated from observed results, not anticipated identifiers.

Supervised Head Study Prefect／teacher-advisor acceptance and the physical off-site recovery drill remain separate human evidence. They must remain visibly pending unless actually performed; they do not authorize fabricating a machine failure, and machine success does not fabricate their sign-off.
