# D4a Settings restore safety

Base: protected main `17d43f6cb199b706c74069724181ca0b43d29c90`.
Scope: Settings restore only; no schema, model, ledger, publication, deployment,
or release-state changes. Original dirty workspace and D3b evidence stay untouched.

## Contract

- No default backup selection. Review a selected verified managed backup before
  entering an exact translated confirmation phrase in an alertdialog.
- Freeze reviewed choice and verification identity. Clear consent on selection
  change, cancellation, close, and reopening. Prevent duplicate submissions.
- Admin restore accepts optional `expected_sha256`, strictly validates it, and
  compares it to the verification of staged bytes before pre-restore backup or
  installation. Preserve maintenance, write fence, preflight and rollback.
- Guest does not verify files. Its existing workspace-ID-derived simulated SHA
  must never be presented or passed as a checkpoint content digest. Non-None
  `expected_sha256` is rejected. Guest review captures checkpoint presence and
  existing workspace revision from one view; optional `expected_workspace_revision`
  is checked on the same view passed to existing registry CAS. Missing/stale
  reviewed checkpoints fail, without falling back to the initial demo fixture.
- Strict parameter types and access-mode separation. Legacy non-UI callers that
  omit optional guards retain existing behavior. No filesystem/hash operations
  are introduced for Guest.
- Progress, success receipts and recovery errors reflect actual workflow results.
  No optimistic success. Guest outcomes explicitly say memory-only practice.

## Verification

Start with failing behavior tests: no default selection, phrase mismatch,
close/reopen/reset of consent, reviewed choice change, double submit, staged hash
mismatch before mutations, Guest stale revision and validation/commit races,
missing checkpoint, invalid types/modes and legacy omitted parameters.

Then run focused restore/integrity/Guest/UI tests. Browser verification uses only
isolated fictional data: 20 dialog cycles, keyboard/focus, mobile reflow,
real success and failure receipts. Coordinate browser/full windows; root owns
CI and merge. Full regression evidence must name the exact tested source.

Physical-device and supervised encrypted recovery acceptance remain pending;
this batch does not enable production or certify the entire mobile matrix.

## Implementation checkpoint evidence

- The initial 19 server guard tests failed against the old restore signatures;
  all passed after the staged checksum and Guest CAS guards were added.
- Six real NiceGUI control tests pass, including 20 retained confirmation loops,
  stale async review suppression and duplicate submission prevention. These are
  not browser, focus, heap, or physical-device evidence.
- The focused restore/integrity/Guest/handover set passed 74 tests before later
  mode/reset negatives and accessibility checks were added. Final exact-source
  counts and browser/full results remain to be recorded externally.
- Guest review returns the existing revision and checkpoint presence from one
  view, with no SHA field. Reviewed restore requires that revision and checkpoint;
  the existing registry CAS catches a change between validation and commit.
