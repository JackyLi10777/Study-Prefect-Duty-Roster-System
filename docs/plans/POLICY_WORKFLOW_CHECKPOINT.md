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

- [ ] Temporary empty DB initializes; saved settings survive reopen.
- [ ] Invalid/expired identity and Guest cannot mutate official storage.
- [ ] CAS and transaction failure leave no partial revision/audit/receipt.
- [ ] Same command replays its original revision after subsequent edits;
      different intent using the same command is rejected.
- [ ] Post-commit backup failure returns a durable pending receipt; repair/retry
      does not append another policy revision.
- [ ] Missing policy tables, invalid pointers or invalid documents fail backup
      validation; complete restore preserves history and operation evidence.
- [ ] Guest changes are atomic, bounded and expire with their workspace;
      oversized UTF-8 command IDs fail before mutation without raising quotas.
- [ ] Focused tests, independent review, exact-head full verification and required
      CI pass before integration. No deployment or UI activation is implied.

## Implementation status

Planned; no implementation or validation completion claimed at this checkpoint.
