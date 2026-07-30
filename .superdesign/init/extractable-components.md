# Extractable components — design menu

These are current or near-current NiceGUI patterns that can be explored without changing policy or data ownership.

## Operational Action Morph

Source: `nicegui_app/ui/components.py:37-76`, motion metadata in `nicegui_app/assets/motion/sing-yin-motion.js`.

Inputs: label, Material icon, semantic variant, busy/disabled state, story target, story category, completion feedback. Explore whole-button storytelling where icon, label, and surface move through `idle → intent → working → success/error` without geometry drift.

## Workflow rail

Source: `nicegui_app/ui/components.py:268-298` and `nicegui_app/ui/workflow_navigation.py`.

Inputs: ordered steps, current index, safe return/next route, explicit unavailable state. Explore desktop rail and mobile sticky progress with identical order.

## Daily Verse sacred reader

Source: `nicegui_app/ui/page_routes/home.py:309-369`, `nicegui_app/ui/devotional.py`, `--sy-image-devotional`.

Inputs: Chinese verse, NKJV English, reference, tone, reflection, prayer, refresh and return action. Explore desktop/mobile and light/dark as one family, never as four unrelated designs.

## Shared workbench shell

Source: `nicegui_app/ui/shell.py:1083-1329`, catalog in `nicegui_app/ui/page_catalog.py`.

Inputs: page kind, route, navigation group, access mode, music context, language, theme, copyright. Explore route clarity and responsive continuity without changing route identities.

## Roster matrix

Source: `nicegui_app/ui/page_shared.py` roster renderers and `nicegui_app/services/roster_presentation.py`.

Inputs: five weekdays, fixed English duty labels, Chinese names, closed/vacant states, time. Explore scanability only; never add background imagery behind the matrix.

## Evidence list

Source: `nicegui_app/ui/page_routes/showcase.py:271-572`.

Inputs: type, state, date, source reference and summary. Prefer filterable editorial list/table over decorative dashboard cards.

## Restricted / recovery state

Source: `nicegui_app/ui/components.py:203-246` and `nicegui_app/ui/page_access.py`.

Inputs: restriction reason, capability code, safe alternate action, retry/support reference. The UI must explain rather than disguise denial.
