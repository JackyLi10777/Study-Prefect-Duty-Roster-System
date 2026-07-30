# Sing Yin (聖言) Roster Platform — Superdesign context

## Product truth

- Product: Service Weave／服事經緯.
- Functional name: Sing Yin (聖言) Roster Platform／聖言值班表平台.
- Users: Head Study Prefect as daily operator; teacher advisor as occasional reviewer; Guest as isolated fictional demonstration.
- Primary sequence: generate draft → review → publish/export → published-duty absence → fairness explanation → backup/recovery → handover.
- Core principle: “Not to be served, but to serve.” The interface embodies fairness, clarity, responsibility, patience, and care.

## Design thesis

Quiet Editorial Operations: a precise school workbench with warm material honesty and deliberate evidence. Operational content is compact and direct; story pages can breathe; Daily Verse has a distinct sacred-reading language. Premium quality comes from hierarchy, rhythm, typography, complete states, and meaningful motion—not visual excess.

## Mandatory invariants

1. NiceGUI + Quasar is the only frontend runtime.
2. Traditional Chinese first; English complete; all prefect names remain Chinese.
3. Admin and Guest share route, layout, and component geometry. Guest remains deny-by-default and non-persistent.
4. No images behind forms, names, tables, PDF, fairness ledger, warnings, or destructive confirmation.
5. Do not copy ReactBits, 21st.dev, Apple, OpenAI, or other brand assets/code. Translate only useful interaction principles.
6. Light/dark versions share geometry. Default appearance follows system.
7. Reduced motion and forced colours reveal final content immediately.

## Colour grammar

- Slate blue `#35647C` / dark foreground `#9BC2D2`: primary action and current step.
- Teal `#0F766E` / `#72D6C7`: verified, stable, completed; not generic decoration.
- Amber `#8A5A00` / `#F0C96A`: attention and review.
- Muted red `#963C35` / `#D98F87`: destructive and failure.
- Neutral matte ground/surface/ink tokens build structure.

## Typography

- UI: Inter + Noto Sans HK.
- Daily Verse: Noto Serif HK with larger line height and calm measure.
- Evidence/code: restrained monospace only where content requires it.
- Use weight, size, spacing, and alignment before colour to establish hierarchy.

## Geometry and rhythm

- 8px base rhythm; main gaps 16/24/32; editorial separations 48/64.
- Controls at least 44px; important mobile actions 48px.
- Surfaces usually 16–20px radius; sacred/editorial hero up to 28px.
- Desktop content can reach 1440px; form reading measure remains bounded within full-width operational composition.
- Avoid card oceans. Lists/tables carry repeated evidence; cards separate distinct decisions.

## Motion grammar

- Press 90ms; state 180ms; layer 260ms.
- Operational Action Morph may animate icon geometry, label, progress and completion surface as one story, but must preserve hit-box and surrounding layout.
- Preview interactions reset. Persistent outcomes remain until state changes.
- Maximum two active motion groups in one viewport.
- No passive looping decoration, tilt, large rotation, parallax, cursor replacement, bounce, or layout-thrashing animation.
- Keyboard/touch get equivalent state feedback; hover is never the only explanation.

## Sacred reader

- Deep indigo, parchment and small antique-gold accents.
- Verse remains the focal content, followed by reference, reflection, prayer and return to service.
- Desktop and mobile may recompose, but reading order and wording remain identical.
- Specified translations remain 和合本修訂版 2010（神版） and NKJV; Chinese scripture footnote markers are cleaned from display text.

## External pattern adjudication

- 21st.dev morphing-button examples support state continuity, but their React/Framer code and expanding FAB menu do not belong in this app.
- React Bits spotlight/depth ideas support a restrained pointer-light on non-sensitive editorial surfaces. Reject strong perspective, large translation, shaders, auto-add lists and continuous animation.
- Superdesign branching is used to compare coherent systems, not accumulate unrelated decorations.

## Required proposal set

Create a faithful current-state multi-frame baseline first, then branch three materially different but compatible directions:

1. Quiet Editorial Continuity — stronger typographic hierarchy and restrained whole-button state transitions.
2. Operational Rhythm — clearer workflow rail, denser operational scanning, deliberate completion choreography.
3. Sacred Service — warmer human narrative and a more developed Daily Verse family while keeping operational areas plain.

Each direction must show:

- Operational Action Morph states.
- Daily Verse: desktop/mobile × light/dark.
- Shell consistency across Dashboard, Rosters and one reference/story page.
- Guest/Admin parity and reduced-motion notes.
