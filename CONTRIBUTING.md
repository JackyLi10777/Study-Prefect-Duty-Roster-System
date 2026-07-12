# Contributing / 協作與交接

Thank you for helping maintain the Sing Yin Study Prefect Duty Roster System.
Changes should make the weekly operator workflow safer, clearer, or easier to
hand over—not merely add visible complexity.

## Before editing

Read:

- `PROJECT_STATUS.md`
- `Professional_Design_System.md`
- `docs/NICEGUI_ARCHITECTURE.md`
- `docs/RELEASE_HANDOVER.md`
- `docs/BRANCH_STRATEGY.md`

The active runtime is NiceGUI. `demo_code/`, `demo_code2/`, and the
`streamlit-cloud` branch are reference material only.

## Ownership boundaries

- `roster_policy`: duty posts, opening days, capacities, role gates, weights.
- `roster_core`: pure generation and validation.
- `roster_workflow`: transactions, fairness ledger, audit, backup, restore.
- `nicegui_app/ui`: bilingual presentation, navigation, guidance and feedback.

Do not derive rules from translated labels or place fairness decisions in page
handlers.

## Required checks

```powershell
python -X utf8 -m pytest -q
python -X utf8 scripts\verify_release_candidate.py
```

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
