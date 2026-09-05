# C1: policy-driven dated weekly drafts

## Source and activation

Base: protected main `f7686aa273754ee7ed3b4bca2b31de488995c8c6`.
Branch: `codex/dated-weekly-drafts-20260905`.
Original workspaces and databases are untouched. No deployment, UI activation,
CP generation, publication, reporting or export activation belongs to C1.

## Interface and ownership

The ordinary draft Module owns generation, validation, edits and a strict frozen
snapshot. The official workflow reads a caller-selected school-year revision,
executes the Module, and commits draft history plus the existing operation
receipt and backup obligation in one transaction. Guest uses the same Module
and its existing bounded workspace/receipt registry, never another database.

- A snapshot owns its policy reference, canonical policy document, actual dates,
  ordered rows, all cells, eligibility inputs and opening/service minutes.
- A seat is identified by actual date, stable business ID and one-based index.
  Room numbers are display settings, never qualification or accounting keys.
- Regeneration retains the saved policy. Explicit policy adoption is a separate
  CAS/idempotent command; it never silently replaces a reviewed draft's rules.
- Draft IDs are distinguished from old integer week IDs. Old publish, export,
  sharing and adjustment paths must reject them; negative tests prove this.
- Revisions are immutable. Retries return the original revision even after a
  later edit; backup failure reports committed/pending, not rolled back.
- Ordinary role, weekday, leave and no-consecutive-day restrictions remain hard
  rules. Vacancies have explicit reasons; a search limit never means proven
  infeasibility and never permits violating constraints.
- Assist capacity one preserves existing fixed/flexible mode behavior.
  Multiple Assist seats are explicitly unsupported in C1; do not ignore a mode
  or silently move a person's fixed weekday. This limitation must be removed
  with its own parity tests before full configurable UI activation.
- The Assist mode is fixed for a C1 draft; regeneration/adoption do not silently
  switch it. Successful fixed-mode generation retains the existing first-owner
  initialization behavior in the same transaction/workspace commit, including
  the prefect version increment. Rollback or failed Guest CAS/capacity admission
  must not retain that side effect. Exact replay never reinitializes ownership.
- Flexible-mode previous-week history chooses the latest actual week across
  legacy active rosters and dated drafts. Dated wins a same-week tie only; an
  older dated draft never overrides a newer legacy roster merely by type.
- At most twenty display rows/one hundred dated cells, including closed rows.
  All stored names are authoritative Chinese. No real names in automated tests.

## Acceptance checklist

- [ ] Rules -> generation -> save -> edit -> reopen works through official and
      Guest workflow Interfaces, not only an isolated repository test.
- [ ] Default 30 and maximum 100 cells preserve rooms, dates, states and integer
      minutes; no duplicate person/date or consecutive ordinary assignments.
- [ ] New policy edits do not mutate existing drafts. Explicit adoption changes
      the revision once under CAS and preserves the prior immutable snapshot.
- [ ] Invalid identity, stale version, malformed receipt and failed transaction
      produce no partial writes. Exact retries repair pending recovery safely.
- [ ] Empty initialization, readiness, backup verification and restore agree on
      the new schema and reject corrupt snapshot/policy references.
- [ ] Guest bounds, expiry, atomic replacement and receipt eviction remain valid.
- [ ] New snapshots cannot pass old publish/adjust/export/share entry points.
- [ ] Focused tests, independent review, full verification and required CI pass.

## Following dependencies

C2 must wire immutable publication, adjustments/restoration/withdrawal, report
minutes and every presentation consumer before custom rows are user-accessible.
CP then uses the common actual-date/seat transaction model, but has its own role,
availability and fairness rules. Temporary old workflow support is not permission
for dual writes or two permanent authorities. Final activation removes replaced
rule owners. Test-site deployment remains one integrated update after completion.

## Evidence

The backend draft Interface is implemented (not activated in UI). Migration
`0016` owns the dated draft history/current pointer, including a unique command
reference for each revision. Existing operation receipts/fences/recovery own
official commits; Guest retains only bounded result references in its existing
registry. Read-only command-result lookup handles lost delivery without rerunning
generation. No rows are copied to legacy roster/fairness tables.

Focused integration command (exit 0, 170 passed in 51.45 seconds):

```text
python -m pytest tests/test_dated_weekly_draft.py tests/test_dated_draft_workflow.py tests/test_guest_dated_drafts.py tests/test_dated_draft_schema.py tests/test_policy_workflow.py tests/test_guest_policy_workflow.py tests/test_school_year_policy_schema.py tests/test_guest_workspace.py tests/test_backup_restore.py tests/test_assist_mode_persistence.py tests/test_v12_persistence_schema.py --maxfail=1 --disable-warnings
```

Tested: real temporary SQLite and Guest generation/edit/reopen, default/maximum
matrices, policy pinning/adoption, live eligibility, original receipt replay and
lookup, redirected-receipt rejection, rollback, concurrent creation, pending
backup repair, isolated restore, malformed snapshots and policy references,
legacy export/publish/share/adjust rejection, bounded Guest capacity/CAS/reset
and receipt eviction, fixed ownership rollback/adoption/exact replay, and latest
prior-week selection across both sources (including a same-week tie).

The chronology review finding was reproduced red before correction: an older
dated draft incorrectly superseded a newer legacy roster. Both Adapters now
compare dates. A pure shared command fingerprint preserves the existing encoding
without making Guest state validation import the official SQL workflow.

Governance and whitespace checks pass. This is focused implementation evidence,
not exact-head full verification, required CI, a complete independent review,
performance certification, mobile acceptance or deployment. Those remain pending.
