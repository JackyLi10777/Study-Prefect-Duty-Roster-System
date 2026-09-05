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
The bounded 20-cycle extraction and additional browser validation are pending.

No controlled p75, full WebKit, physical Android/iPhone, WhatsApp or supervised
encrypted-recovery acceptance is claimed by this batch.
