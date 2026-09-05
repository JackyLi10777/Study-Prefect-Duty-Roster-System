# D3a: reading routes, first-use content

Implementation base: protected main
`d639326dbd7e438747a78e50f4bb254eddea4a1c`.
Status: scoped Chromium functional evidence passed on the source below;
final-head browser/full and required CI remain separate evidence checkpoints.

Only `/getting-started`, `/guide` and `/devotional` are in this batch. Preserve
the Dashboard function and alias byte-for-byte. Do not adopt the frozen donor
file wholesale, touch showcase routes, Worker/Viewer, audio, global styles,
schemas, export transport or deployment. Coordinate the heavy test window with
the policy-closure batch; do not run competing browser/full checks.

## Accepted behavior

- Getting Started reuses the existing exact-week safe next-action resolver,
  shows a three-step checklist and one primary next action. Reference material
  mounts on first use, not inside an eagerly constructed hidden card.
- Guide searches a localized in-memory text index, including unmounted answers.
  This necessary search index is not a claim that text resources are zero bytes.
  Search and category stay mounted; only opened answer bodies mount, once, and
  retain identity/state. Empty results are explicit. Opening a deep-link target
  must reveal it without silently losing the current filter input.
- Devotional keeps the selected verse, refresh and return-to-work visible.
  Reflection/prayer and tone controls are first-use content. Each page uses the
  same verse snapshot. Late tone controls read the current saved preference;
  initialization cannot call preference writes or refresh. Existing manual
  refresh/tone semantics remain.
- Page-local navigation is opt-in. Known outer anchors remain mounted. TOC clicks,
  initial hash and browser history reveal/mount before scrolling and focus.
  Only source-owned allowlisted anchor identifiers can reach the server, never
  arbitrary fragments, URLs or Viewer keys. Repeated navigation must not leave
  duplicate handlers or let a late response steal focus from a newer request.

## Verification to build

Real NiceGUI tests: initially absent controls/content calls, current defaults,
20 retained opens, hidden-answer search and empty results, bilingual indexing,
exact-week onboarding states and Guest isolation, late tone without writes.
Execute navigation JavaScript against a deterministic harness for allowlisting,
request ordering and cleanup, then verify actual focus/deep links in a browser.
Scoped browser evidence follows a clean source checkpoint and heavy-window
coordination; full pre-push and required CI remain independent steps.

No formal mobile/cold lifecycle/p75, real-device, WhatsApp, recovery, all-D or
production completion is claimed by this batch.

## Local implementation checkpoint

The three pages use first-use retained sections. Getting Started's safe next
action precedes its single-column checklist. Guide keeps a localized text index
for search without constructing unopened answer bodies. Devotional details use
the page's existing verse snapshot and read tone only when opened.

Opt-in reading navigation validates source-owned anchors in both browser and
server. Unknown fragments invalidate pending focus without transmitting their
contents. Late requests cannot replace newer focus; pagehide/reinstall disposes
listeners and pending animation frames. Linked answers can be revealed while
retaining the filter text; the next deliberate filter change restores results.

Focused checks cover real NiceGUI lifecycle behavior and an executed Node
navigation harness. The old source-string requirements for an eager Guide table
and an onboarding decorative icon were removed with those obsolete structures.
The Dashboard and compatibility alias function bodies match the baseline exactly.

`scripts/verify_mobile_reading.py` is prepared for clean-source Chromium checks
with isolated fictional local-maintenance and Guest data: first-use controls,
20 retained cycles, eight reflow sizes, search, direct links, history and focus.
It records cold and first-materialization samples separately; a retained-cycle
pass is not a cold lifecycle or controlled performance pass.

## Verified functional source

Source `fe3c8a409d4a6c448cad7977461282eacc683d28`, tree
`b2ff53b991735836b5668d984c06e25f0d4f7fa8`, clean before and after the run.
Release-input fingerprint
`19fcadaeb57c84c152a0a0f9b08f4408c38182fd6074335cf419f8364c8ebbbc`
(339 files). Chromium `152.0.7977.76`, Playwright `1.60.0`.

Report: `C:/Users/lichu/AppData/Local/Temp/sy-mobile-reading-piam6b80/report.json`
with SHA256 `4711166ADBFA070C79321DE10A434368E698997C51F45BC6DFA292679B59BE17`.
Isolated run IDs: local maintenance `E2E-3CB26784F941`, Guest
`E2E-477EDEDF1F1F`. All scoped scenarios passed, zero browser errors.
This includes the eight width checks, 20 retained opens on each route, absent
unopened controls, search/reveal/filter preservation, direct anchors, same-anchor
history, back/forward and return from another page. Unknown test fragments were
not sent in the observed WebSocket frames. This is not signed-Admin or WebKit
evidence, a bfcache-specific guarantee, or the full theme/language/mobile matrix.

The first failed run `sy-mobile-reading-x6h3az5j` exposed custom anchor IDs
overwriting NiceGUI expansion IDs. Anchors now belong to stable outer sections;
expansion IDs and the existing shared close/focus helper remain unchanged.
`sy-mobile-reading-a5ct1t3p` exposed an incorrect verifier label-class selector;
the verifier now checks real direct body children. `sy-mobile-reading-ehnagsfv`
reproduced duplicate same-anchor history; only changed hashes now push entries.
Failed evidence directories remain intact. No thresholds were relaxed.

Existing three-page UI checks now explicitly assert cold absence before opening
details; Guest route readiness waits for permanent search/next-action controls,
not hidden reference content. No global prewarming was introduced. Dashboard,
other route assertions, audio, Worker and release/deployment state remain outside
this change. 91 targeted tests and governance/hygiene checks passed before the
functional run. Final clean-head evidence belongs in the PR, not retroactively
in the source-bound report above.

## Integration checkpoint after policy closure

Normal merge of protected main `f7686aa273754ee7ed3b4bca2b31de488995c8c6`
preserves the independently reviewed policy-closure batch. D3a does not introduce
or modify that batch's schema changes.

The six-check run on `67dc0187eb112dc25b899ecc44bade0d2e206418` completed with
five checks passing and the automated suite failing two obsolete source assertions:
the removed devotional intro/card structure and a minimum of 40 informational
icon call sites. The complete result is preserved as
`logs/change-verification-report-67dc018.json`, SHA256
`B7FD2140E0B909B01071461FC5692873C932910E2506E0C888D308183EE9254D`.
Actual reading/refresh/reflection/prayer/return behavior now belongs to the real
NiceGUI lifecycle test; the icon inventory must exactly match its enumerated
informational call sites rather than require a minimum amount of decoration.
No runtime performance or accessibility threshold changed. 94 focused tests
pass after this correction and the normal merge. Final-head browser/full/CI
verification remains pending and must be recorded against its own source.
