# R7 Codex Adjudication

**Adjudicated:** 2026-07-30
**Reviewed working source:** branch `codex/rc32-ui-command-id-fix`, HEAD `9831c69900eb0dd4a9246540b80c482314b518b7`
**Annotated candidate tag:** `v1.2.0-rc.35` peels to `570e29f745eef7c1995635d1b187021a8fec6ea4`
**Production truth at original review time:** the reviewed source was not live. Production subsequently advanced through a separate controlled release to Windows origin `v1.2.0-rc.35` / `570e29f745eef7c1995635d1b187021a8fec6ea4` and Worker `d7069f99-81b4-4388-aa28-383b58bfc68f`, as recorded authoritatively in `PROJECT_STATUS.md`.
**Working-tree preservation:** the pre-existing modifications to `scripts/verify_unified_guest_ui.py` and `test-results/uiverse-components/desktop-light-components.png`, and the pre-existing untracked audit/screenshot files, were left untouched.

## Decision

The short R7 report's **PASS** is not supportable as a release verdict. It audits important R5/R6 remediations but does not examine the later deployment, Worker, policy, migration and verification findings. It also says that 69 icon stories were “deployed” while its own closing statement says no deployment occurred; the repository's deployment record identifies an older live origin. The animation count is source coverage, not deployment or interaction-quality evidence.

The extended R7 report is valuable but overstates several severities and recommends unsafe or incomplete remedies. Its overall **BLOCKED** conclusion is directionally correct for the *next production release*, but not because both reported P0s are fully valid. Local audit and isolated design work may continue; production upload must not.

## Remediation addendum — reviewed working source on 2026-07-30

The original adjudication below remains the decision record. The working tree has since implemented the following source remediations; these are **not** commit, tag, deployment or supervised-acceptance evidence:

| R7 item | Working-source disposition | Verification evidence |
|---|---|---|
| S1, S2, S7 | Immutable release bundle with an independent locked virtual environment; scheduled-task target switches atomically; rollback restores the exact prior action; environment bytes and ACL SDDL are restored; port release fails closed | `tests/test_windows_release_deployment_script.py` and `tests/test_windows_host_scripts.py` |
| S3 | Strict `SING_YIN_` environment parsing rejects C0／DEL controls, malformed owned settings and duplicates | `tests/test_windows_host_scripts.py` |
| S5 | Verification reports use a same-directory unique, flushed and fsynced temporary file followed by atomic replacement with bounded Windows contention retries | `tests/test_update_verification.py` |
| W1 | Permanent no-digest share-revocation tombstones are checked by create, read and list paths; conflicting recreation is rejected | `cloudflare/roster_viewer/worker_gateway_test.js` |
| W2, W5 | Security-cookie comparison is consistent and the administrator session secret rejects obvious placeholders | Worker gateway contracts |
| P1, P2 | `ROOM_CAPACITY` is public policy data and the solver returns an explicit `(day, post, seat)` mapping | roster policy／generator integrity tests |
| P3, P8, P9 | Startup readiness fails closed on unreconciled fairness anchors; Alembic uses model metadata and an absolute SQLite URL, rejecting cwd-relative targets | database configuration and fairness reconciliation tests; Alembic drift check |
| A1, A4 | Process PATH refresh preserves the first case-insensitive entry without duplicates; bounded release-archive cleanup failures now emit an operator warning | Windows host and deployment-script tests |

Focused cross-layer verification on pre-merge commit `c32c01f` passed 79 tests covering workflow hierarchy, responsive layout, component contracts, Windows host preparation and release deployment. Fifty Worker gateway contracts and the isolated semantic-icon browser gate also passed across four access／viewport contexts and 20 route replacements. The complete 1,009-test Python collection passed. Integration commit `a331587` then merged the rc35 production baseline and passed a focused 125-test Python set plus 50 Worker contracts; those results are integration evidence, not a formal exact-source release report. The `.superdesign/init` references were normalized from fenced code into safe indented source outlines without dropping their source-grounded implementation detail. Remaining release blockers are deliberately narrow: a protected-main merge, a new clean annotated tag, a formal exact-source report, a verified backup and isolated restore, matched origin／Worker rollout evidence, and supervised human acceptance. R7-W6 remains a low-severity availability concern because KV read-after-write consistency can still produce a conservative conflict response; content-addressed keys preserve safety, so a Durable Object or revised response contract is deferred rather than introduced inside this remediation.

## Concise current-state brief

- **Current state:** the original audit examined dirty source at `9831c69`; its fixes were later committed and integrated with the rc35 production baseline. Candidate source, protected main, tagged release, live origin／Worker and human acceptance remain distinct states.
- **Operator problem:** a visually broad motion system is present, but current-state fidelity, Daily Verse light-theme quality, button state completeness and release truth are not yet established in one evidence chain.
- **Highest risks:** non-atomic shared-venv rollback, swallowed rollback port failure, concurrent verification-report writes, share-revocation races, stale Superdesign project context and misleading deployment language.
- **Approach:** preserve the tree; adjudicate code paths first; refresh design context; reproduce the rendered product before proposing alternatives; do not implement a selected redesign or perform release actions before approval.

## Finding-by-finding adjudication

| ID | Classification | Effective severity | Evidence and decision |
|---|---|---:|---|
| R7-S1 rollback dependency mismatch | **Confirmed** | **P0 release blocker** | The host switches commits at lines 1222–1226 and then mutates the same `.venv` at 1228–1235. A failed install can leave old source with a partially changed environment. “Pre-verify pip before switching” is not atomic because installing into the live venv would mutate the running release. Use a staged immutable source + venv bundle, verify it, then atomically switch the task target; retain the prior bundle unchanged for rollback. |
| R7-S2 environment backup timing | **Partially confirmed** | P2 | Read-only validation occurs through line 967. `Protect-SingYinSensitivePath` can change ACL state at 968 before file bytes are captured at 975, but content mutation begins only with the overlay at 986. The report's claim that an earlier failure can leave a corrupted `.env` is not established. Preserve bytes and an ACL descriptor before the first mutation if exact rollback is required. |
| R7-S3 `.env` control characters | **Partially confirmed** | **P1 release blocker** | A direct PowerShell experiment on the exact regex showed embedded TAB and NUL are accepted; an embedded newline does not match. Replace permissive skipping with explicit validation of every `SING_YIN_` line and reject C0 controls (with a deliberate policy for surrounding whitespace). Add TAB/NUL/malformed-line tests. |
| R7-S4 SID case comparison | **Rejected** as P1 | P3 hardening | Both relevant values are canonical `.Value` strings from `SecurityIdentifier`; Windows emits the canonical uppercase `S-...` representation. A case-only false negative is not demonstrated. Comparing `SecurityIdentifier` objects is clearer future hardening, but this is not a release blocker. |
| R7-S5 shared verification temp file | **Confirmed** | **P1 release blocker** | Every process writes the same `release-verification.tmp`, so concurrent verification can overwrite or replace another process's evidence. Use a same-directory unique temporary file, flush it, then atomically replace; clean up only the creator's file. |
| R7-S6 unpinned Winget installs | **Partially confirmed** | P2 | Git is unbounded and Python is constrained only to the 3.12 line after install. Exact patch pinning may make recovery impossible when Winget removes a version. Prefer an allowlisted supported range plus post-install version/publisher/source verification, and document an offline installer recovery path. |
| R7-S7 swallowed rollback port failure | **Confirmed** | **P1 release blocker** | The empty catch at line 1219 permits commit/venv mutation while the previous process may still own the port. Fail closed, record the protected error, retry only within a bounded policy, and do not mutate the host until release is confirmed. |
| R7-W1 `deleteShare` race | **Confirmed** | **P2 release blocker** | Digest-specific deletion is exact. The no-digest path lists keys and then deletes that snapshot; a concurrent new digest may survive under KV eventual consistency. A post-delete list alone is insufficient. Use a revocation generation/tombstone checked by create/view, or move mutable share identity to a transactional Durable Object. |
| R7-P1 `ROOM_CAPACITY` export | **Confirmed** | P2 | It is a first-class policy mapping used by `required_posts_for_day` but absent from the package's public exports. Export it or replace external capacity knowledge with one public policy projection. |
| R7-P2 generator ordering contract | **Partially confirmed** | P2 | `_solve_regular_schedule` creates and returns assignments in its `slots` index order, and the caller currently consumes the same policy order. It is correct today but implicit. Return a keyed `(day, post, seat)` projection or assert the expected slot before appending. |
| R7-P3 migration anchor check | **Confirmed** | P2 | Migration 0003 backfills anchors without a reconciliation assertion. Git history shows the file was introduced once, not later rewritten. Do **not** edit the historical migration; add a runtime integrity gate and, if needed, a forward additive migration that records/reconciles discrepancies. |
| R7-A1 PATH refresh duplicates | **Confirmed** | P3 | Machine and user PATH values can contain duplicate entries. Normalize only within the process and preserve first occurrence; this is hygiene, not a release blocker. |
| R7-A2 password lifetime | **Needs more evidence** | P3/platform limitation | `GetNetworkCredential().Password` necessarily creates a managed string for the ScheduledTasks API and setting the variable to null does not zero it. Minimize scope and avoid logging; replacing the Windows API or account model needs a separate operational decision. |
| R7-A3 token generator input validation | **Rejected** | — | The CLI delegates to `validate_design_token_contract`, which is the owning validator and already emits a bounded drift list. A top-level exception message could improve operator UX, but the report did not demonstrate missing semantic validation. |
| R7-A4 release temp cleanup | **Partially confirmed** | P3 | `ignore_errors=True` can leave a locked successful workspace. Failed evidence is intentionally retained. Log failed cleanup and schedule bounded later cleanup; do not erase diagnostic evidence on failure. |
| R7-W2 cookie case handling | **Confirmed** | P3 | Cookie names are case-sensitive by common HTTP practice, but treating all security-cookie names consistently avoids alternate-spelling ambiguity. Normalize the comparison policy and test it. |
| R7-W3 support reference interpolation | **Rejected** as vulnerability | P3 defense in depth | `gatewayReference()` creates a fixed uppercase alphanumeric `GW-...` token; user input does not reach the interpolation. HTML escaping is still desirable if the helper is generalized. |
| R7-W4 JWT `exp` boundary | **Rejected** | — | `now >= exp` / `exp <= now` is standard expiration semantics: the token is invalid at the `exp` instant. Changing it to `<` would incorrectly extend validity. |
| R7-W5 admin secret placeholder check | **Confirmed** | P2 | Admin session secret validates length and trim but, unlike guest and origin secrets, does not reject obvious placeholders. Apply the same fail-closed configuration rule and tests. |
| R7-W6 post-write KV read | **Confirmed** | P3 | Immediate reads may be stale and cause a spurious 409. Content-addressed keys preserve safety; improve response semantics or remove the misleading read-after-write assumption. |
| R7-W7 raw-header intermediate objects | **Needs more evidence** | P3 | The origin request path calls `stripAccessCredentials` before forwarding and injects its own signed principal. No leak to origin was demonstrated. Retain a direct boundary test for every proxy/revocation path. |
| R7-P4 `is_ahp_role` public export | **Rejected** | — | It is an internal helper used by `can_assign_role`; helpers do not need to be public merely because they exist. |
| R7-P5 `DUTY_TIME_WINDOWS` mapping | **Rejected** | — | The code explicitly marks it as a backward-compatible display alias and provides separate opening and service mappings. Removal requires deprecation, not a defect fix. |
| R7-P6 legacy fallback multiplier | **Rejected** | — | `0.0` deliberately makes legacy Assist. weekday ownership stable. Applying fairness would violate the preserved fixed-weekday policy. Flexible mode owns weekly variation. |
| R7-P7 maximum weekly days | **Rejected** | — | Product policy requires no same-day duplicate and no consecutive generated duties; it does not define a separate maximum-days rule. Adding one would be an unauthorized policy change. |
| R7-P8 Alembic metadata | **Confirmed** | P3 tooling gap | `target_metadata` is absent, so autogenerate is unavailable. Migrations are currently manual; document this or wire the model metadata with drift tests before claiming autogenerate support. |
| R7-P9 relative Alembic URL | **Partially confirmed** | P2 | Direct Alembic CLI use from another directory can target an unintended relative database. Application migration code normally supplies the configured path. Make direct CLI behavior fail closed or derive an absolute configured URL. |

## Audit of the short R7 report

| Claim | Classification | Decision |
|---|---|---|
| “100% pass, 0 failures” proves the reviewed dirty tree | **Needs more evidence** | No command, report digest or exact dirty-tree fingerprint is attached. Historical passing evidence cannot establish this working tree. |
| “69 icon story pairs deployed across all surfaces” | **Rejected** | The source contains broad story-map coverage, but deployment records identify rc31 as live. Pair count also does not prove rendered state completeness or quality. |
| “No unresolved P0/P1” | **Rejected** | S1, S3, S5 and S7 are independently confirmed release blockers. |
| R5/R6 remediations named in the report | **Mostly already fixed** | Spot inspection supports the command-id, guest-receipt and release-evidence direction; they remain source facts until an exact release evidence chain is produced. |

## Classified first-party behavior inventory

This inventory defines the minimum review boundary before a future production upload; generated files and third-party runtime directories are excluded.

| Domain | Owning surfaces | Principal risks to review |
|---|---|---|
| Access and capability | `nicegui_app/access_context.py`, `nicegui_app/services/guest_workspace.py`, `nicegui_app/services/operation_context.py`, `cloudflare/roster_viewer/worker.js` | signed identity, expiry/revocation, Guest denial, replay/idempotency, proxy-header stripping |
| Roster policy and generation | `packages/roster_policy/`, `packages/roster_core/` | role/post eligibility, availability, fixed/flexible Assist. modes, no duplicates/consecutive duty, explicit slot contracts |
| Persistence and workflow | `nicegui_app/services/roster_workflow*.py`, model/repository modules, `migrations/` | transaction boundaries, fairness reconciliation, backup obligations, withdrawal/outbox, maintenance lock |
| UI and routing | `nicegui_app/ui/`, `nicegui_app/pages.py`, `nicegui_app/shell.py` | route ownership, Admin/Guest parity, bilingual state, focus/navigation, responsive hierarchy |
| Motion and design | `nicegui_app/assets/motion/`, `nicegui_app/assets/styles/`, design-token contracts | semantic whole-button states, stable footprint, listener disposal, reduced motion, light/dark contrast |
| Daily Verse | devotional route, verse catalogue/service and sacred styles | approved translations, editorial-marker stripping, reading contrast, refresh/error behavior |
| PDF and delivery | roster/report export services and download endpoints | Chinese names, bilingual copy, in-memory Guest delivery, no-store, bounded files |
| Host and release | `scripts/deploy_windows_release.ps1`, `scripts/windows_host_common.ps1`, host preparation/task scripts | immutable source, atomic runtime switch, environment/ACL recovery, port ownership, source-to-live evidence |
| Verification | `scripts/verify_update.py`, release candidate/browser scripts, `tests/` | isolated data, unique evidence files, real rendered paths, no historical-result substitution |

## Required disposition before production release

1. Run the implemented immutable-bundle, strict-environment, atomic-report, tombstone and fairness-readiness controls on the exact clean tagged tree.
2. Merge through protected main and create a new immutable annotated tag.
3. Produce the exact source fingerprint, verified backup＋isolated restore, origin／Worker version evidence and supervised human acceptance as separate claims.

## Status of this adjudication

This document began as a review-only decision record. The remediation addendum now records working-source fixes for the confirmed release-critical paths, but it still does not certify rc35 or any later candidate and does not authorize commit, push, upload or deployment. A future release remains blocked until the exact clean tagged tree passes the formal source, backup／restore, origin／Worker and supervised-acceptance gates.
