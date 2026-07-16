# Theme and Design Tokens

## Design direction

The active thesis is a quiet school operations desk: one clear responsibility at a time, with enough evidence to act confidently. The complete product rationale and governance live in [`Professional_Design_System.md`](../../Professional_Design_System.md).

The weekly workflow uses restrained operational surfaces. Daily Verse uses a separate sacred-reading language. Onboarding and handover use a gentle archive language. Risk and recovery use plain, high-contrast safety surfaces.

## Sources of truth

| Layer | Canonical source | Responsibility |
|---|---|---|
| Machine token contract | [`design_system/tokens.v1.json`](../../design_system/tokens.v1.json) | Primitive, semantic, and component layers for light and dark modes |
| Contract loader and generator | [`nicegui_app/ui/design_token_contract.py`](../../nicegui_app/ui/design_token_contract.py) | Resolves references and supplies the Quasar palette bridge |
| Generated variables | [`sing-yin-tokens-v1.css`](../../nicegui_app/assets/css/sing-yin-tokens-v1.css) | Versioned `--sy-*` variables |
| Base and component styles | [`sing-yin-theme-v1.css`](../../nicegui_app/assets/css/sing-yin-theme-v1.css) | Quasar integration, controls, tables, page components, responsive rules |
| Editorial narrative | [`sing-yin-narrative-v1.css`](../../nicegui_app/assets/css/sing-yin-narrative-v1.css) | Page spine, introductions, reference cards, and trust narratives |
| Adaptive composition | [`sing-yin-mobile-v1.css`](../../nicegui_app/assets/css/sing-yin-mobile-v1.css) | Phone header, bottom navigation, safe areas, and compact action layout |
| Theme runtime | [`nicegui_app/ui/theme.py`](../../nicegui_app/ui/theme.py) | Appearance preference, semantic atmosphere slots, and Quasar palette |
| Head markup | [`nicegui_app/ui/theme_markup.py`](../../nicegui_app/ui/theme_markup.py) | Stylesheet order |
| Motion runtime | [`nicegui_app/assets/motion/sing-yin-motion.js`](../../nicegui_app/assets/motion/sing-yin-motion.js) | One-shot entry, selected pointer response, and semantic feedback pulse |

## Core semantic palette

| Role | Light | Dark | Meaning |
|---|---|---|---|
| Ground | `#F2F2F7` | `#0D1117` | Application canvas |
| Surface | `#FFFFFF` | `#1C1C1E` | Working surfaces and raised sheets |
| Ink | `#1C1C1E` | `#F5F5F7` | Primary text |
| Muted | `#5F6065` | `#C7C7CC` | Supporting text |
| Action | `#35647C` | `#9BC2D2` | Primary action and current workflow stage |
| Stable | `#0F766E` | `#72D6C7` | Verified or completed state |
| Attention | `#8A5A00` | `#F0C96A` | Review or incomplete state |
| Danger | `#963C35` | `#D98F87` | Destructive or failed state |

Status colours are not interchangeable with brand identity. Primary action uses slate blue; teal is reserved for stability and verification.

## Type

- Primary interface: Inter with Hong Kong Chinese system fallbacks.
- Devotional and reflective passages: Noto Serif HK-style serif stack.
- Technical references and numeric evidence: restrained monospace stack.
- Traditional Chinese is primary; English preserves the same hierarchy and component geometry.
- Local font files are runtime assets and are not copied into design context.

## Geometry and density

- Shared surfaces generally use 16 to 20 pixel radii.
- Raised devotional and editorial hero surfaces may use a 28 pixel radius.
- Header controls use a compact 12 to 16 pixel dock grammar.
- Primary content max width is 1440 pixels.
- Adaptive shell breakpoint is 900 pixels.
- Main-content touch targets are at least 44 pixels; important mobile actions generally use 48 pixels.
- Routine scanning stays compact. Publication, restore, archive, and fairness consequences receive more space and explanation.

## Motion

- Press acknowledgement: `90ms`.
- State change: `180ms`.
- Layer or entry transition: `260ms`.
- Entry effects use transform and opacity, run once, and remain interruptible.
- Exit is faster than entry.
- Reduced-motion mode removes decorative movement and pointer lighting.
- Pointer lighting is reserved for real action containers and selected non-sensitive editorial surfaces.

## Atmosphere

[`nicegui_app/ui/theme.py`](../../nicegui_app/ui/theme.py) owns semantic light and dark pairs for the sidebar, Weekly Pulse, devotional, onboarding, handover, platform, guide, engineering, architecture, architecture lifeline, and shared ready-empty state.

Drafts should reference the semantic slot, not copy or reinterpret a runtime image file. The same slot, crop rule, mask, and purpose must remain stable across appearances. Context imagery is optional, low-opacity, and never carries required information.

## Component grammar

- Solid material hierarchy: ground, quiet group, working surface, raised decision layer.
- Borders and restrained shadows communicate elevation; blur is unnecessary.
- Buttons have clear primary, outline, flat, and danger consequences.
- Status badges combine text and colour.
- Navigation uses weight and a slim position rail.
- Tables preserve factual density on desktop and switch to equivalent labelled cards on phones.
- Forms keep validation and repair near the failing field.

## Context bundle for a visual draft

Use the relevant page source plus:

- [`nicegui_app/ui/shell.py`](../../nicegui_app/ui/shell.py)
- [`nicegui_app/ui/page_shared.py`](../../nicegui_app/ui/page_shared.py)
- [`design_system/tokens.v1.json`](../../design_system/tokens.v1.json)
- All four stylesheets listed above
- [`nicegui_app/ui/theme.py`](../../nicegui_app/ui/theme.py)
- The relevant translation catalogue under [`nicegui_app/ui/i18n_catalog`](../../nicegui_app/ui/i18n_catalog)

Runtime media, generated exports, operator records, and secret-bearing configuration are outside design context.
