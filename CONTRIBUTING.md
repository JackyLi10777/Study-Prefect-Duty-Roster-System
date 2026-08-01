# Contributing / 協作與交接

Thank you for helping maintain the Sing Yin Study Prefect Duty Roster System.
Changes should make the weekly operator workflow safer, clearer, or easier to
hand over—not merely add visible complexity.

## Before editing

Read:

- `docs/status/CURRENT_STATUS.md`
- `docs/ARCHITECTURE_OVERVIEW.md`
- `docs/DOCUMENTATION_SYSTEM.md`
- `Professional_Design_System.md`
- `docs/NICEGUI_ARCHITECTURE.md`
- `docs/RELEASE_HANDOVER.md`
- `docs/BRANCH_STRATEGY.md`

The active runtime is NiceGUI. `demo_code/`, `demo_code2/`, and the
`streamlit-cloud` branch are reference material only.

## Ownership boundaries

- `roster_policy`: duty posts, opening days, capacities, role gates, weights.
- `roster_core`: pure generation and validation.
- `RosterWorkflow`: transactions, fairness ledger, audit, backup, restore.
- `nicegui_app/ui`: bilingual presentation, navigation, guidance and feedback.
- `docs/status/current-release.json`: mutable production, migration, Worker,
  recovery and human-acceptance identifiers.

Do not derive rules from translated labels or place fairness decisions in page
handlers. Do not hand-copy mutable current-release values into ordinary guides;
run the status generator. Cross-module dependency directions are executable in
`docs/architecture/module-boundaries.json`.

## Required checks

```powershell
python -X utf8 scripts\project_governance.py --check
python -X utf8 scripts\verify_update.py --plan
python -X utf8 -m pytest -q <focused-tests>
python -X utf8 scripts\verify_update.py --staged
```

Use `verify_update.py --release` only for a real release candidate. When
observed deployment, recovery, Worker or human-acceptance truth changes, update
`docs/status/current-release.json`, then run
`python -X utf8 scripts\project_governance.py --write`; generated status blocks
must not be edited by hand.

UI changes also require browser evidence for Traditional Chinese/English,
light/dark mode, phone width, keyboard focus, console output, and paired theme
imagery. Browser writes must use isolated SQLite, backup, and log directories.

## Commit style

Use focused Conventional Commit messages such as:

- `feat: add isolated practice mode`
- `fix: prevent duplicate fairness posting`
- `docs: align self-hosted deployment guide`
- `test: cover published leave adjustment recovery`

Do not commit credentials, session secrets, `node_modules`, `.next`, Python
caches, or temporary performance fixtures. The repository may include the
explicitly generated fictional-data and release-evidence archive described in
`archive/README.md`; it must never be replaced with operational school data.
