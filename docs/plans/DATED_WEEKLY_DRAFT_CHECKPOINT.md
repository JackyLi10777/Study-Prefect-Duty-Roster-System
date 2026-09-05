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

Contract checkpoint only; implementation and tests are not complete.
