# Policy workflow closure checkpoint

## Source and delivery boundary

- Base: protected `origin/main@0efd5ae656adea6226edd88664f2d609066d4907`.
- Isolated branch: `codex/policy-workflow-closure-20260905`.
- No original database/workspace changes, deployment, UI activation, solver,
  dynamic-row exports, or CP activation in this slice.
- Develop, test, review, and integrate each slice independently. Update the test
  site together only after the complete requested implementation is ready.

## Ownership and Interface

1. Persistence/recovery: canonical `school_year_policy_revisions` and
   `school_year_policy_current` belong to application metadata and an explicit
   Alembic revision. Empty initialization, readiness, backup verification and
   restore must agree. Preparatory data is not copied into formal policy history.
2. Official workflow: `policy_current`, `policy_revision`,
   `policy_reset_preview`, `initialize_policy`, `save_policy`, `reset_policy`,
   and `policy_command_result` hide transaction, identity, CAS, receipt and backup
   coordination. The existing operation registry remains authoritative.
3. Guest Adapter: same rule/Interface with one atomic workspace update; policy
   history is part of isolated bounded state, not a separate memory repository.
4. Write results bind command ID and immutable policy revision to a backup state:
   `verified`, `pending` (already committed, recovery required), or
   `not_applicable` (Guest). Replaying must recover the original revision.

## Acceptance gates

- [x] Temporary empty DB initializes; saved settings survive reopen.
- [x] Invalid/expired identity and Guest cannot mutate official storage.
- [x] CAS and transaction failure leave no partial revision/audit/receipt.
- [x] Same command replays its original revision after subsequent edits;
      different intent using the same command is rejected.
- [x] Post-commit backup failure returns a durable pending receipt; repair/retry
      does not append another policy revision.
- [x] Missing policy tables, invalid pointers or invalid documents fail backup
      validation; complete restore preserves history and operation evidence.
- [x] Guest changes are atomic, bounded and expire with their workspace;
      oversized UTF-8 command IDs fail before mutation without raising quotas.
- [ ] Focused tests, independent review, exact-head full verification and required
      CI pass before integration. No deployment or UI activation is implied.

## Implementation status

The backend Interface is implemented; no UI or scheduling consumer is activated.
Alembic `0015` owns the canonical policy tables. This is the policy part of the
prelaunch schema, not completion of the future dated-seat/publication model.

Focused suite: 218 passing tests (official/Guest workflow, policy schema/rules,
transaction Adapter, backup obligations, page identity). The final authorization
ordering change was rechecked with all 16 official workflow tests passing.
Guest regression review also covered workspace/Adapter/codec/command validation;
schema review covered original backup restore, persistence and Assist behavior.
Governance and whitespace checks pass. Exact-head full and required CI are pending.

Independent review fixed receipt lookup accepting a different existing revision:
lookup now checks the shared canonical request fingerprint and rejects duplicate
JSON keys. Backup file verification runs after releasing the live read Session.
Authorization precedes acquisition of a filesystem lease/write fence.

## Shared-runtime recovery correction

This slice also changes the existing `_fulfill_backup_obligation` helper, not
only the new policy Interface. If an already-completed backup is unusable, the
obligation is reopened before generating its replacement. Failure remains an
explicit recovery obligation; success points to the newly verified snapshot.
Regression tests exercise original publish and withdraw commands, failed
replacement, repair, exact replay, unchanged fairness/command counts, and restore.

## Guest limits and lifecycle

- New policy commands obey both the shared 64-character limit and existing
  128 UTF-8 byte Guest limit. IDs are not hashed, truncated or silently expanded.
- Policy revision references use the existing bounded receipt registry; an
  evicted receipt returns no result rather than pretending the latest is old.
- Explicit demo reset/restore replaces practice history and clears its old
  policy receipt references atomically. Ordinary edits and reconnect snapshots
  cannot rewrite retained history. Guest results are expiring practice state,
  never a claim of a formal database commit or verified backup.
