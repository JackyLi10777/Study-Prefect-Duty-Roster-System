# D3a: reading routes, first-use content

Implementation base: protected main
`d639326dbd7e438747a78e50f4bb254eddea4a1c`.
Status: implementation and focused-test checkpoint; browser/full evidence pending.

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
pass is not a cold lifecycle or controlled performance pass. It is not yet run.
