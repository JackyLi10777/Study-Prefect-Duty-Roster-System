# Theme — executable current token contract

Source of truth: `design_system/tokens.v1.json`, contract `1.1.0`, name `Sing Yin Luminous Sacred Precision`.

## Layer order

Source outline (text):
    primitive → semantic → component
    tokens → base → layout → components → material → interaction → narrative/pages → motion → mobile

## Primitive source values

Source outline (json):
    {
      "actionFillLight": "#35647C",
      "actionStrongLight": "#284C60",
      "actionSoftLight": "#E8F0F3",
      "actionForegroundDark": "#9BC2D2",
      "actionFillDark": "#47758B",
      "actionSoftDark": "#1A2B34",
      "stableFillLight": "#0F766E",
      "stableForegroundDark": "#72D6C7",
      "attentionForegroundLight": "#8A5A00",
      "attentionForegroundDark": "#F0C96A",
      "dangerFillLight": "#963C35",
      "dangerForegroundDark": "#D98F87",
      "inkLight": "#1C1C1E",
      "inkDark": "#F5F5F7",
      "surfaceLight": "#FFFFFF",
      "surfaceDark": "#1C1C1E",
      "groundLight": "#F2F2F7",
      "groundDark": "#0D1117",
      "ease": "cubic-bezier(.2, .8, .2, 1)",
      "easeEnter": "cubic-bezier(.16, 1, .3, 1)",
      "easeExit": "cubic-bezier(.4, 0, 1, 1)",
      "press": "90ms",
      "state": "180ms",
      "layer": "260ms"
    }

## Semantic roles

| Role | Light | Dark | Use |
|---|---|---|---|
| action | `#35647C` | `#9BC2D2` | primary operation/current step |
| stable | `#0F766E` | `#72D6C7` | verified/completed |
| attention | `#8A5A00` | `#F0C96A` | needs review/incomplete |
| danger | `#963C35` | `#D98F87` | destructive/failed |
| ink | `#1C1C1E` | `#F5F5F7` | primary text |
| muted | `#5F6065` | `#C7C7CC` | supporting text |

Teal is not a generic accent. It is reserved for stable identity and verification. Slate blue owns actions and current workflow position.

## Type and surfaces

- UI: Inter + Noto Sans HK fallbacks.
- Sacred reading only: Noto Serif HK.
- Code/evidence: restrained monospace.
- Operational forms/tables: matte opaque surfaces without illustrations.
- Sacred surface: deep indigo + parchment/gold language, generous leading.
- Story/reference surfaces may use paired local light/dark imagery with explicit veils.

## Theme runtime source

`nicegui_app/ui/theme.py` defines `theme_preference`, `current_theme`, `set_theme_preference`, `apply_quasar_palette`, and `apply_theme`. Default preference is `system`; explicit light/dark selection is preserved. Quasar colours are generated from the same token contract, not independently chosen.

## Atmosphere pairs

`sidebar`, `weekly-pulse`, `devotional`, `onboarding`, `handover`, `platform`, `guide`, `engineering`, `architecture`, `architecture-lifeline`, and `empty-ready` each resolve to matched light/dark local WebP assets. No image is allowed behind names, forms, tables, fairness data, warnings, or PDF content.
