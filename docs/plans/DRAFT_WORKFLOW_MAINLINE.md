# Mainline integration B: draft final-state workflow

## Scope and adoption

Base: protected main `caac0a0073eacac9e1cde3ca098a9ff7aeb902bc` (document
core PR #128). Source: frozen, previously reviewed integration checkpoint
`856d06c5cb7e1895d687020fcae2fa0f3bfc4cbe`. Adoption is by explicit files and
function/CSS hunks, not by merging the old integration branch or cherry-picking
its scratch history. Frozen `933bb39`, `856d06c`, `55cffb1` and their original
reports remain untouched. The original dirty working directory is not used.

This batch introduces the existing final-state DraftEditor, shared rule
validation, formal/Guest adapters and weekly UI callers together. It retains
the current policy, database schema and migrations; configurable persistence,
CP allocation and the separate 20-row model are not part of this batch.

## File and hunk ownership

| B owns | Boundary |
|---|---|
| `services/draft_editor.py`, `draft_rules.py` | Local intent, pending-overlay candidates, undo/redo, frozen save command and settlement |
| `guest_adapter.py`, `workflow_parts/lifecycle.py`, `workflow_types.py` | Both adapters validate and commit one final matrix; reopen plus assignment increments version once |
| `ui/edit_sessions.py` | Remove the old draft controller; preserve non-draft edit sessions |
| `ui/page_routes/weekly.py`, weekly language catalog | Generation disclosure, draft editor, history, explicit adjustment and receipts |
| `ui/components.py` | Public semantic/native dialogs and server-side enabled-state transitions needed by weekly controls |
| `ui/page_shared.py` | Only `_delete_dialog_after_close`, `_show_committed_without_backup`, `_run_with_progress` status/owner cleanup, `_render_roster_table`, and their minimal imports |
| CSS | Native sheet shell, semantic status/alert placement, adjustment controls, lazy rule disclosure and accessible lightweight history meter |

**Dependency correction:** initial inspection incorrectly attributed
`success_feedback=False` to the draft save caller. The actual caller in the
source is `_prepare_export_document`. Therefore B does **not** add that keyword
or conditional: they remain with export integration C. Existing progress
success-sound behaviour stays unchanged. Only admitted work can settle a save;
working feedback is not a success receipt.

B does not take the exporter controller, PNG/download/native-share bridge,
export-specific imports or functions, or export lifecycle source assertions.
The existing main PDF dialog remains intact. C will start from B's subsequently
merged main and adopt only the remaining export hunks, not duplicate the shared
cleanup changes. The export-session withdrawal regression remains with C.

The public lifetime-owner container disposes NiceGUI's hidden dialog canary
through public element deletion. No private NiceGUI lifecycle is modified.
Global people-editor styles and unrelated disclosure refinements are excluded.

## Behavioural verification

Required B checks include formal/Guest reopen-plus-assignment in one version,
pending-state candidates, cross-day/reciprocal changes, undo/redo, command replay,
conflict/reapply, admitted-write cancellation and committed-but-backup-failed
settlement. UI tests cover frozen intent before awaits, restored request
context, authoritative refresh failures, read-only publish guards, selection
retention, re-enabling controls, one-shot owner cleanup, and responsive progress
with success feedback only after completion.

Accessibility source assertions referring to the removed private pending
dictionaries/ECharts internals are replaced by current accessible markup checks
and callable save-seam behaviour. Existing PDF/people assertions are retained.
The Guest disk-backup case remains explicitly inapplicable because Guest has
no disk backups; formal backup-failure behaviour is still tested.

This branch needs its own clean-source full verification, independent diff
review, corresponding isolated browser checks and required CI. Prior source
reports are not substitutes. No deployment or formal release acceptance is
claimed; missing release adapters and physical acceptance stay pending.

## Defects found during this batch's review

- Semantic Quasar dialogs had roles/headings but no accessible-name binding.
  Unique source-owned title/description IDs now bind `aria-labelledby` and
  `aria-describedby` for modal, sheet, alert and status variants. Native-dialog
  title binding remains intact. The pre-fix real-browser check `e5e1a36` failed
  to find the working dialog by its visible title; that failure is retained in
  isolated fixture `sy-draft-mainline-eoknx43i`. Unit tests cover all variants.
- History already had a baseline defect on the parent main: display stride 12
  was passed to the adapters as page size 13 to detect a following page. Rows
  13, 26, etc. disappeared between pages. Optional `lookahead=True` now adds one
  to the query limit, not the offset stride; ordinary API shape/semantics and
  URLs are unchanged. The formal query remains bounded and the Guest adapter
  projects only the selected slice. Formal/Guest 25/26/27-record fixtures
  reproduce the old UI mismatch and verify complete, unique new pagination.

`fd16eac` passed the original bounded Chromium check: one-version reopen and
assignment, 20 same-sheet open/close cycles with focus restoration, and
256/320/390px lazy-rule expansion without overflow. `ec4b81c` additionally
passed named status/alert dialogs. Reports are source-bound functional
diagnostics in isolated fictional temporary fixtures, not p75/release gates.
The status probe holds only the disposable database's write lock long enough
to inspect the real progress dialog; production timing and gates are unchanged.
