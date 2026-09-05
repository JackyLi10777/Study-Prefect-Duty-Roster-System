# Mainline integration C: export workspace and native file sharing

Base: protected main `530ba88de0fe4e0f29135977d384d72b092d9c81` after B (#129).
Source: frozen `856d06c5cb7e1895d687020fcae2fa0f3bfc4cbe`. Adoption is by
explicit files/function/CSS/catalog segments, not by cherry-picking or merging
the old integration history. Original dirty and frozen evidence worktrees stay
unchanged. Business remains prelaunch; no deployment is part of this batch.

## Runtime boundary

- Adopt `roster_export_session`, native file share and PDF wrappers, and only
  the remaining export preparation/delivery/workspace functions in `page_shared`.
- Add the optional success-feedback control only for export preparation;
  preserve B's public canary-owner disposal, dialog semantics, action enablement,
  weekly final-state validation, history lookahead, and presentation seam.
- Add native action/select/check styles only, and the export segment of the
  stewardship language catalog. Other pages and preferences remain unchanged.
- Keep A's immutable document/renderers and #125 atomic fairness-audit snapshot.
  No configurable model, CP, 20-row integration, schema or migration changes.

## Download transport contract is preserved

Both existing routes remain unchanged: `GET /api/generated-download/{token}`
for Admin/Guest and Guest-only `GET /api/guest/download/{token}`. Existing
`deliver_generated_download` callers and local-maintenance fallback are retained.
This includes PDF, allocation/summary reports, Markdown acceptance worksheets,
ZIP support bundles and the 64 MiB Admin handover limit. The native-share
allowlist of PDF/PNG is not applied to generic delivery.

Review confirmed a native-top-layer feedback defect. Therefore `downloads.py`
adds optional UI feedback and an exact-generation DOM failure target; this is
an explicit revision of the initial file-level no-change boundary, not a
transport change. Existing callers use the same default notification path.
Scoped browser feedback uses JSON serialization and textContent, never HTML,
ticket URLs, raw exceptions or payload logging. Closing/reopening or options ABA
rejects late failure and pending-download completion without a background toast.

The frozen source's removal of GET and replacement by fixed-path POST is NOT
adopted. Its POST-only tests and pipeline matchers are not adopted either. The
PNG-02 POST-ticket subrequirement remains a separate undecided interface change,
not completed or waived by this batch. Existing URL logging risk is not newly
certified safe. No Worker runtime change is necessary for the retained protocol.

Keep 90-second session-plus-AccessMode-bound tickets, atomic one-time consumption,
idle expiry cleanup, rightful-ticket preservation after wrong-session/mode
attempts, quotas, exact MIME checks and no-store/nosniff. Native sharing instead
has a separate 15-second preparation lease and an explicit second user gesture;
an already-open OS sheet may complete after its start deadline.

## Review and diagnostic evidence

Initial targeted tests cover controller generations, close/reopen, stale source,
PDF wrappers, PNG semantics, native sharing and the unchanged Guest/download
contracts. Existing source tests are updated narrowly where the PDF modal became
a reusable native sheet; real lifecycle tests cover payload clearing and no stale
success. The old fixed read-call count did not express a write-safety invariant.

A red copy regression identified a premature device-download claim in the frozen
language catalog. Ready copy now asks the user to confirm the file was saved.

`verify_export_overlay.py` is a source-bound fictional-data diagnostic for a
review concern: a body-portal progress dialog may be behind a native modal top
layer. It holds only the disposable fixture DB lock and records a screenshot and
element hit test. A failing result is retained, not classified as a release pass.
The clean `cc1f43d` diagnostic failed with `inside=false`: progress was visible
in DOM but behind the native modal. Original evidence is preserved at
`sy-export-overlay-164yg6wo` (run `E2E-A4929AABF98E`) in the temporary evidence root.

The focused repair reuses the existing export explanation label as a sheet-owned
status/alert receipt; it does not add a global notification framework or replace
all dialogs. Capture/render and file/share callbacks receive generation-bound
feedback. A source-invalidated receipt deliberately uses the new current
generation, so stale-source warnings remain visible while late results are
rejected. Default non-export progress behavior and admitted-work claim lifetime
remain unchanged. Draft/audit PDF admission leaves the sheet open so a delayed
fetch error can be reported rather than disappearing with an automatic close.

## Bounded browser extraction

`scripts/verify_export_workspace_integration.py` extracts only these functions
from `856d06c:scripts/verify_nicegui_mobile.py`:

| Source function | Scope retained |
|---|---|
| `isolated_paths`, `_next_unused_monday`, `_ensure_dynamic_roster_route_fixtures` | Exact isolated paths, bundled fictional seed, real draft/publish service calls |
| `_capture_runtime_footprint` | Original 250 ms wait, collectGarbage, 100 ms wait, Runtime.getHeapUsage and Memory.getDOMCounters |
| `_assert_runtime_growth_budget` | Original 20 cycles and 10 MiB heap / 100 DOM nodes / 40 listeners limits |
| `_install_png_share_counter`, `_prepare_and_confirm_png_share` | One PNG, signature, first gesture cannot share, separate confirmation; reviewed `expect` handle fix retained |
| `_assert_export_dialog_png_cleanup_cycles` | Original cold baseline before first open, render/download/share/close each cycle, raw samples at 1/10/20, final footprint |
| `_assert_png_native_share_outcomes_and_download_fallback` | Shared, cancelled, failed, unsupported, downloaded fallback |
| `_assert_export_advanced_options_are_lazy` | Initially absent controls, expand/mount once and reuse |

Only baseline persistence is added before the unchanged loop, so early failures
retain it as well. Wait/GC behavior and metric fields are not replaced by mounted
DOM counts. The original notification-empty wait remains, even though inline
feedback now avoids those portals. No warm-up or threshold increase is added.

The narrow `_bind_isolated_admin_session` helper comes from the same frozen
write-pipeline script. It uses an ephemeral key and exact loopback request
binding. A **separate**, unmeasured Admin context verifies real GET MIME/headers,
replay, inline native failure, 15-second lease expiry and the real eight-ticket
session quota (abort fetches before consume; do not modify server limits).
Expected 410/abort console errors are recognized only for generated-file paths;
other errors still fail. Ticket URLs are matched in memory, never written into
the evidence. Generic POST-only matching is not adopted.

The driver records commit/tree/fingerprint/dirty before and after, fixture run ID,
Python/Playwright/NiceGUI/Pillow/browser versions, raw samples and explicit
functional-diagnostic/formalReleaseExecuted=false. Every invocation has a fresh
artifact directory; failures exit nonzero and keep raw evidence. Full route
matrix, F collector/assembly, D other pages and Worker gates are NOT extracted.

The overlay-specific driver additionally delays its disposable process's real
renderer by 1.5 seconds to observe a pending render beyond the reveal delay, then
waits for the real PNG download. This is not a production delay or a performance
measurement, and does not affect the original 20-cycle driver.

Same-checkpoint browser execution and full verification are pending.

No controlled p75, full WebKit, physical Android/iPhone, WhatsApp or supervised
encrypted-recovery acceptance is claimed by this batch.
