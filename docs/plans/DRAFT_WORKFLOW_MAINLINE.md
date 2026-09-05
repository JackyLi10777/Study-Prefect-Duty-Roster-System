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
