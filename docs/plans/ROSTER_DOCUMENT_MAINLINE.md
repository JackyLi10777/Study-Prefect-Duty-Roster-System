# Mainline integration A: one immutable roster document

## Scope and source

This PR starts from protected main `97b0846c81afd54715a9a3249c5d108be5328b53`.
It adopts reviewed file-level changes from the clean integration checkpoint
`856d06c5cb7e1895d687020fcae2fa0f3bfc4cbe`, not its commit history or unrelated
working-tree changes. The frozen `933bb39` and `856d06c` worktrees and their
verification reports are preserved.

The source checkpoint's tests are historical evidence, not this PR's acceptance.
This PR must pass its own governance, tests and required CI before integration.
It does not deploy an origin or Worker and does not change business launch state.

## Adopted boundaries

| Responsibility | Source files |
|---|---|
| Atomic capture, immutable metadata and strict matrix | `roster_document.py`, `roster_presentation.py` |
| Pure PDF and two PNG renderers | `roster_export.py`, `roster_image_export.py` |
| Existing encrypted public projection | `public_roster_share.py` |
| Renderer/document regression coverage | `test_roster_document.py`, `test_roster_presentation.py`, `test_roster_export.py`, `test_roster_image_export.py` |
| Same-host PNG measurement tool and validation | `verify_roster_png_performance.py`, `test_roster_png_performance.py` |

The five service files and all listed tests/tools are adopted directly from the
source checkpoint, except the export-session withdrawal test in
`test_roster_document.py`: that test remains in the frozen source and belongs
with the later export-session controller PR. No controller exists in main yet;
adding an unrelated controller merely to satisfy its test would cross this scope.

## Preserved contracts

- `build_roster_pdf(workflow, week_id, ...)` remains usable by current main UI.
  It captures once and delegates to `render_roster_pdf(document, ...)`.
- `build_roster_png_bundle(...)` captures once; both PNGs render from the same
  document. Callers preparing multiple formats can capture once and pass that
  document to each pure renderer. The shared UI workspace is a later PR.
- PDF output now carries mandatory status/version provenance and a visible
  version. Internal fairness audit keeps PR #125's single
  `roster_fairness_audit_snapshot` read and remains separate from group output.
- Public projection retains its existing schema and allowlisted fields; no
  prefect ID, leave detail, fairness data or new Viewer contract is introduced.
- The current five-day/six-post contract, Chinese names, `15:40–17:00` times,
  closed/vacant/day-closed states, and source/render policy provenance remain.
- PNG uses existing local assets/Pillow, opaque RGB, bounded in-memory output,
  deterministic filenames and explicit fitting failure instead of truncation.
  No third-party upload, download endpoint or database migration is introduced.

The renderer lays out the rows supplied by the current document, but this PR
does **not** claim the separate configurable-model/20-row contract is integrated.
The existing policy remains authoritative; no new configurable policy is added.

## Remaining integration sequence (not delivered by this PR)

1. Draft final-state controller/adapters and their weekly UI callers together.
2. Export workspace, safe download/native-share UI and lifecycle verifiers,
   depending on this document core. Canary ownership and Playwright handle
   retention have separate fixes/evidence in the frozen integration source.
3. Remaining mobile pages, shell and quiet-by-default audio behaviour.
4. Public/Viewer Worker changes and the isolated Worker/browser harness.
5. Evidence collection/assembly and Windows release binding, depending on the
   corresponding UI/Worker producers. Missing adapters remain `not_run`; neither
   missing evidence nor prior failing p75 results become a release pass.

The configurable model/CP work is owned separately. Real phones, approved
WhatsApp usage and supervised recovery remain separate acceptance requirements.
