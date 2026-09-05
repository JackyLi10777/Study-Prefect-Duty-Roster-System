# D2: retained first-use Access and Support details

Status: prelaunch. Scoped browser diagnostics and full pre-push verification
exist for the earlier D2 source below; they do not constitute formal acceptance.
The main-synchronized checkpoint requires its own browser/full/CI results.

Initial base: protected main `c1e16e7c5866bd7fe75c6e5bca710070c5b10731`.
Normally merged protected main `0efd5ae656adea6226edd88664f2d609066d4907`
after PR #133; no frozen-donor cherry-pick or historical report relabeling.
The original dirty workspace and frozen donor branches remain untouched.

## Adopted boundaries

- Access renders current identity/session/capability summary without constructing
  the sharing workflow. Technical controls mount on the first deliberate opening;
  Guest has no technical expansion. Existing share operation checks remain.
- Support's three required fields stay live. Optional values are initialized from
  the existing sanitized source defaults independently of optional controls.
  Preview/save therefore works before advanced details are opened.
- Advanced controls and exact-ID history lookup mount once and remain retained.
  Reopening does not reset input, attachments or lookup state, or add handlers.
  Native before-hide focus returns to the section header when necessary.
- Guest optional markup is an inert template, not live form controls. The first
  native details toggle moves it into the live form entirely in the browser.
  Unmounted route/action values use the same server-sanitized, non-sensitive
  defaults; no entered Guest report field is server-bound or persisted.
  Editing invalidates the previously prepared browser report so download cannot
  silently deliver stale input. Native reset/reload semantics remain.
- Admin reports still use SupportInbox, opt-in consent, existing validation and
  attachment limits, worker progress, persistent receipts and safe downloads.
  Failed save retains input/attachments; success clears consumed attachment
  summaries only if mounted. Deferred entry checks supplement operation checks.

## Evidence and limits

Regression tests first reproduced eager control construction and missing Guest
source defaults. Real NiceGUI element tests cover unopened submit, first-use
state, 20 reopen cycles, failed-save retry with fictional attachments, receipt,
history retention and revoked permission at retained operation boundaries.
Guest Node tests execute the runtime; an HTML parser separately distinguishes
inert blueprint controls from the live form. These are not browser evidence.

### Preserved earlier-source evidence

Clean source `dd9cebc14d943a5033fc34ac82203145d6975d4e` (tree
`06a43d487b6daba715b0b6ebbee5828b55dd9a8d`) passed 52 focused tests and all
six full pre-push checks; the automated suite took 352625 ms. Its full report is
preserved separately as `logs/change-verification-report-dd9cebc.json`, SHA256
`48A1E2CC82D8C52455EB0ABF588184BBFCB3FFB81FD877F7BECE855544DF8AFC`.

The same source has scoped Chromium diagnostics in the isolated run artifact
`sy-mobile-access-support-tocfm5ns/report.json`, SHA256
`41EBB1D3BABF9432FA59F986F26FAB9ED211B88F6028CB9180374524A0B28163`.
Contexts were local-maintenance `E2E-F6E2776FCBC7` and isolated Guest
`E2E-17D491FC5407`, not signed production Admin. The browser exercised unopened
advanced submission with a persisted local receipt, source defaults, empty
attachments, exact-ID lookup, retained input/focus over 20 cycles, Access first
use/reopen, Guest inert/live controls, JSON download/reset/reload and no report
transmission. It checked 256/320/390/844px reflow and recorded zero browser errors.

First materialization added 993784 heap bytes, **294 DOM nodes and 131 listeners**.
Subsequent 20 retained cycles added 525692 heap bytes, with DOM/listener counts
decreasing by 45/4. Both raw endpoints remain recorded separately. Retention
diagnostics do not replace a cold formal gate; no cold budget has been passed or
waived. The new main-synchronized source must be rerun, not assigned these results.

Earlier harness failure artifacts remain `sy-mobile-access-support-hs7s4gpz`
(native input locator) and `sy-mobile-access-support-yadne5rh` (observer expression
accidentally invoked `fetch(null)`). Neither was resolved by changing a product
threshold or deleting a failing measurement.

No claim of zero first-screen resource bytes, complete role verification,
controlled p75, full route matrix, WebKit/device acceptance or production rollout.
No settings, export/transport, audio, Worker, schema or deployment changes.

## Follow-up F, not implemented by D2

The main mobile release-report validator currently requires coverage, core
interactions and performance, but does not require lifecycle before/after samples,
20 cycles or the 10MiB/100-DOM/40-listener budgets. CORE_REPETITIONS task windows
do not prove those lifecycle limits. F must version the contract to require that
evidence and define a source-owned baseline; missing evidence must fail formal
acceptance. D2's retained-not-cold diagnostic must not be promoted to a cold gate
by a report producer. No release-contract change or formal-pass claim occurs here.
