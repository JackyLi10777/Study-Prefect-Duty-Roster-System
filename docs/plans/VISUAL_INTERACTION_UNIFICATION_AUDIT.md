# Visual and Interaction Unification Audit

**Date:** 2026-07-29
**Candidate branches:** `codex/rc32-ui-command-id-fix`, followed by the focused `codex/rc32-drawer-state-fix`
**Scope:** Public entrance, Admin／Guest workbench, desktop header, sidebar, mobile drawer and tab bar, settings, support, public viewer, shared controls and responsive states.

## Decision brief

1. **Current state:** the rc31 production pair already provides a binary Light／Dark control, while the rc32 working source adds a shared semantic icon runtime and common header-control surface.
2. **Operator moment:** a Head Study Prefect must recognise the current appearance, sound and identity state without learning different controls on desktop, phone or Guest mode.
3. **Priority:** preserve policy and storage behaviour; repair only visible or accessible state drift, duplicated motion ownership and inconsistent control material.
4. **Approach:** design tokens and shared components own presentation; the preference adapters own persisted state; browser gates prove rendered parity before the immutable release workflow is allowed to switch production.

## Material findings and observable outcomes

| Finding | Evidence before change | Owning fix | Observable outcome |
|---|---|---|---|
| Header language, sound, theme and logout controls could read as separate component families. | Different content widths and page-local control styling made borders, surfaces and state feedback easier to drift. | One `.sy-header-control` component contract with semantic variants. | All four controls retain a 44px target, common surface, border, radius, focus and press response; language may be wider without looking unrelated. |
| Appearance must be one button, but `system` still needs to initialise an unset visit. | Stored preference and resolved appearance are different states and could be confused as a three-state click cycle. | `next_explicit_theme()` plus the shared browser resolver. | Unset follows the browser; the first click chooses the opposite explicit theme; every later click alternates only Light／Dark. No menu, select or hidden third click state is rendered. |
| Sound and appearance icons could become stale after an in-place state update. | Python, Quasar and DOM glyph state previously had separate update paths. | Persistent icon state through `window.__syIconMotion.setPersistentGlyph`. | Visible glyph, `aria-pressed`, accessible name and stored state change together without reloading the page. |
| Mobile drawer disclosure state could disagree with its icon. | The rendered drawer, backdrop and `aria-expanded` were not all treated as one state source. | Shared drawer reconciliation and persistent `menu ↔ close` morph. | Desktop and mobile triggers report and display the actual drawer state, including DOM replacement and reconnect. |
| Public entrance retained decorative motion outside the shared contract. | The verse refresh icon rotated and the secure-status decoration pulsed indefinitely. | Remove decorative rotation／loop; retain only bounded state feedback and the truthful sign-in busy spinner. | Public motion is quieter, reduced-motion-safe and no longer implies activity when nothing is happening. |
| Icon stories could move the host or leave stale timelines after rapid input and route replacement. | Competing hover／focus／touch events and replaced NiceGUI nodes can outlive the original element. | One state machine, fixed icon slot, cancellation, MutationObserver cleanup and disposer ownership. | Glyphs transform in place; hosts do not drift, tilt or resize; route cycles do not accumulate listeners, timers or detached animation state. |
| Some controls have no truthful destination glyph. | Forcing a morph can imply finance, cloud storage, completion or uncertainty that the operation does not provide. | Explicit `static` category and rejected-pair list. | Warnings, evidence, tables, names, scripture and misleading pairs remain semantically accurate instead of merely animated. |

## Audit result

No verified defect requires changes to roster policy, fairness, authentication, Guest capability isolation, backups, recovery, data retention or database schema. The release candidate is therefore limited to shared presentation, accessible state synchronisation, motion lifecycle, browser verification and matching documentation.

The first formal rc32 browser gate exposed one additional boundary case: the desktop drawer moved off-screen correctly, but its shared reconciliation loop stopped after checking the mobile-open condition and left `aria-expanded` and the persistent glyph stale. The focused follow-up binds both drawer triggers to the same cancellable reconciliation loop while selecting the real mobile-open or desktop-visible state for the current viewport. This is a release-blocking accessibility correction, not a relaxed assertion or a change to navigation behaviour.

The authoritative acceptance evidence is produced by:

- `python -X utf8 scripts/audit_icon_semantics.py`
- `python -X utf8 -m pytest -q`
- `deno test nicegui_app/assets/motion/sing-yin-icon-story-state_test.js`
- `deno test cloudflare/roster_viewer/worker_gateway_test.js`
- `python -X utf8 scripts/verify_semantic_icon_motion.py`
- `python -X utf8 scripts/verify_rc31_theme_controls.py`
- the repository formal release verifier and controlled Windows／Cloudflare deployment reports for the immutable release tag.

Passing source gates are not deployment evidence. Production completion additionally requires matching origin commit, Worker version, canonical rendered checks and preserved rollback identifiers.
