# D2: retained first-use Access and Support details

Status: prelaunch; focused behavior checks only at this checkpoint. Browser,
full verification, required CI and real-device acceptance are pending.

Base: protected main `c1e16e7c5866bd7fe75c6e5bca710070c5b10731`.
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

No claim of zero first-screen resource bytes, complete role verification,
controlled p75, full route matrix, WebKit/device acceptance or production rollout.
No settings, export/transport, audio, Worker, schema or deployment changes.
