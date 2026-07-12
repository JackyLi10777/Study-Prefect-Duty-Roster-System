---
name: "Sing Yin Study Prefect Duty Roster"
version: "1.0"
description: >
  A servant-leadership design system for a Hong Kong secondary school study prefect duty roster platform.
  Built on NASA-inspired teal (#0F766E) + gold (#D4AF37) accents, warm parchment surfaces,
  biblical verse enclosures, and a dual light/dark mode design optimized for Streamlit Cloud.
  Dark mode uses boosted pure-white text for readability; light mode uses warm paper tones.
  All UIs are bilingual (Traditional Chinese + Professional English) with student names permanently in Chinese.
---

## Visual Theme & Atmosphere

A **servant-leadership platform** for a Hong Kong Catholic secondary school. The design conveys:

- **Quiet authority** — teal (#0F766E) headers, not aggressive corporate blue
- **Warm trust** — gold (#D4AF37) accents on verse enclosures and KPI cards, not trendy gradients
- **Scholarly calm** — warm parchment backgrounds (#F7F6F3) in light mode, deep charcoal (#1F2526) in dark mode
- **Biblical reverence** — daily verse enclosures with 3px gold borders, the signature visual anchor
- **Dense utility** — tables, data editors, and audit charts dominate; no hero sections or marketing cards

**Density**: High — the primary screen is a duty roster table with 30+ rows × 5 days, plus audit charts and KPI cards. The design prioritizes scannability and repeated-action efficiency over editorial breathing room.

**Design Philosophy**: "Gold and teal, not neon. Servant leadership, not corporate dashboard."

## Color Palette & Roles

### Brand Colors

| Token | Hex | Role |
|-------|-----|------|
| `primary-blue` | `#0F766E` | Headers, primary buttons, KPI values, tab underlines, table header backgrounds |
| `accent-gold` | `#D4AF37` | Verse enclosure borders, Assist-in-charge cell borders, KPI card accents |
| `verse-gold-light` | `#A68B3D` | Verse title in light mode |
| `verse-gold-dark` | `#B8972E` | Verse title in dark mode |
| `verse-title-accent` | `#ffeb3b` | Verse title accent highlight |

### Surface Colors

| Token | Hex | Role |
|-------|-----|------|
| `light-bg` | `#F7F6F3` | Light mode page background (warm parchment) |
| `light-surface` | `#EFEEEB` | Light mode card/section backgrounds |
| `light-surface-2` | `#E6E5E1` | Light mode secondary surfaces |
| `light-text` | `#1C1C26` | Light mode primary text |
| `light-text-secondary` | `#4A4A5A` | Light mode secondary text |
| `light-text-tertiary` | `#6B6B7B` | Light mode captions and placeholders |
| `dark-bg` | `#1F2526` | Dark mode page background (deep charcoal) |
| `dark-surface` | `#2A3033` | Dark mode card/section backgrounds |
| `dark-surface-2` | `#343B3F` | Dark mode secondary surfaces |
| `dark-surface-3` | `#3D4549` | Dark mode tertiary surfaces |

### Room Colors (Duty Roster Cells)

| Token | Hex | Role |
|-------|-----|------|
| `room302` | `#E0F7FA` bg / `#00ACC1` border / `#006064` text | Room 302 (Study Room) — cyan |
| `room303` | `#FFF3E0` bg / `#FF9800` border / `#E65100` text | Room 303 (HW Completion) — amber |
| `room202` | `#E3F2FD` bg / `#2196F3` border / `#0D47A1` text | Room 202 (F1 Study Group) — blue |
| `assist` | `#FFF8E1` bg / `#D4AF37` border / `#4E342E` text | Assist-in-charge (leadership) — gold |

### Status & Alert Colors

| Token | Hex | Role |
|-------|-----|------|
| `danger-bg` / `danger-text` | `#FEF2F2` / `#991B1B` | Error messages, leave-conflict warnings |
| `warning-bg` / `warning-text` | `#FFFBEB` / `#92400E` | Fairness gap warnings, backup reminders |
| `closed-bg` | `#ECEFF1` | Closed-day cells (Room 202 Tue/Fri) |
| `x-bg` / `x-text` | `#FFEBEE` / `#C62828` | Blocked/closed slots (X marker) |
| `empty-bg` | `#FAFAFA` | Unassigned roster cells |

**Usage rule**: `primary-blue` is for headers and functional UI chrome. `accent-gold` is reserved for the verse enclosure and leadership-related highlights — never used for general buttons or text.

## Typography Rules

The app uses Streamlit's default system font stack. No custom font imports — the design relies on careful sizing, weight, and color contrast rather than a proprietary typeface.

### Hierarchy

| Level | Size | Weight | Usage |
|-------|------|--------|-------|
| Subheader | 1.25rem | 600 | Section titles (e.g., "This Week's Roster", "Post-Duty Leave Adjustment") |
| Metric value | 1.5rem | 700 | KPI card numbers |
| Metric label | 0.75rem | 400 | KPI card labels |
| Body | 1rem | 400 | Standard text, captions, form labels |
| Small caption | 0.8rem | 400 | Footer, hint text, backup reminders |
| Verse title | 1rem | 600 | Daily verse reference (e.g., "Mark 10:43") |
| Verse body | 0.9rem | 400 | Daily verse text in the verse enclosure |

**Rules**:
- Body text uses Streamlit default (Inter/system sans-serif)
- Headers and subheaders use `st.subheader()` / `st.caption()` — never custom HTML headings that bypass the component hierarchy
- KPI card values use custom HTML divs with explicit font-weight and font-size
- Never scale font size with viewport width
- Letter-spacing must be 0 (no negative tracking)

## Component Stylings

### Button: Primary

```css
/* Filled teal button — the main call-to-action */
background-color: #0F766E;
color: #ffffff;
border: none;
border-radius: 6px;
padding: 8px 20px;
font-weight: 600;
```

**States**:
- **Hover**: brightness(1.1) or slightly lighter teal variant
- **Pressed**: darker teal (#0D6B63)
- **Disabled**: opacity 0.5

**Usage**: "Generate Roster", "Execute Leave Adjustment", "Apply Changes"

### Button: Secondary

```css
/* Outlined or lighter button for secondary actions */
background-color: transparent;
color: #0F766E;
border: 1px solid #0F766E;
border-radius: 6px;
padding: 8px 20px;
```

**Usage**: "Download PDF Summary", "Discard Changes"

### Card: KPI Card

```css
/* Small metric cards in the Management Dashboard */
background-color: var(--light-surface); /* or var(--dark-surface) in dark mode */
border: 1px solid #e2e8f0;
border-radius: 8px;
padding: 16px;
text-align: center;
```

Structure:
```html
<div class="kpi-card">
  <div class="label">Total Prefects</div>
  <div class="value">30</div>
</div>
```

### Card: Verse Enclosure (Signature Component)

The verse enclosure is the **signature visual anchor** of the platform. It must appear at the top of every page.

```css
.verse-card {
    border: 3px solid #D4AF37;  /* gold — non-negotiable */
    border-radius: 8px;
    padding: var(--verse-card-padding, 16px 4px);
    margin-bottom: 16px;
    overflow: hidden;
    /* Light mode: warm background; dark mode: inherited dark surface */
}
.verse-inner {
    /* Inner container for the verse text */
}
```

**Rules**:
- The gold border must always render — in both light and dark modes
- The verse text color adapts: `#7B6914` (warm dark gold) in light mode, `#B8972E` (bright gold) in dark mode
- The verse title (e.g., "Mark 10:43") uses gold accent color
- Never remove or hide the verse enclosure — it's the platform's identity element

### Data Table: Roster Grid

The main duty roster uses `st.dataframe()` with styled cells:

- **Header row**: Teal (#0F766E) background, white text
- **Room cells**: Colored by room type (cyan/amber/blue/gold per room)
- **Closed cells** (Room 202 Tue/Fri): Light gray `#ECEFF1` with "⬜"
- **Blocked cells** (X): Red-tinted `#FFEBEE` with bold "X"
- **Leave-revoked cells**: Pink-tinted `#FFCDD2` with "請假撤銷"
- **Empty cells**: `#FAFAFA` background
- **Mentoring pair cells**: Left border `4px solid #0F766E` with slight teal background tint

### Data Editor: Manual Edit

Uses `st.data_editor()` with:
- `width="stretch"` for full-width editing
- `key` attribute for session state tracking
- Unsaved changes trigger a warning banner with "Apply Changes" (primary) and "Discard Changes" (secondary) buttons

### Form: Leave Adjustment

Uses `st.form()` with:
- Step indicators: "Step 1: Select date/position", "Step 2: Choose substitute"
- `clear_on_submit=True` to reset after submission
- Submit button: primary type, full width (`width="stretch"`)
- Success message includes PDF re-export reminder

### Expander: Adjustment History

Collapsible by default (`expanded=False`):
- Shows a table of past adjustments (Time, Day, Position, Original, Replacement, Points)
- Bilingual column headers via `_t()`

### Tab: Visual Board / Manual Edit

Uses `st.tabs()` with:
- Active tab underline in gold (#D4AF37)
- Tab labels: "📅 Visual Board" / "✏️ Manual Edit Mode" (bilingual)

### Sidebar

- Contains: student roster management, leave registration, AI parse buttons, backup/restore controls
- Language toggle: Chinese / English
- Theme toggle: Light / Dark mode
- All controls use `st.sidebar.*` components
- Backup reminder appears as a warning banner at the top when triggered

### Notification: Backup Reminder

```css
background-color: var(--warning-bg);
border: 1px solid var(--warning-border);
color: var(--warning-text);
```

Triggered after: roster generation, manual edits, leave adjustments, PDF exports.

## Layout Principles

### Spacing Scale

All spacing uses multiples of 4px:

| Token | Value | Usage |
|-------|-------|-------|
| `xs` | 4px | Icon padding, tight gaps |
| `sm` | 8px | Card padding, button internal |
| `md` | 12px | Section gaps |
| `lg` | 16px | Card padding, column gaps |
| `xl` | 24px | Major section separators |
| `xxl` | 32px | Page header spacing |

### Grid

The app uses Streamlit's default single-column layout with `st.columns()` for side-by-side content:

- **5-column KPI row**: Equal-width columns for metrics
- **2-column forms**: Date picker + position selector side by side
- **3:1 split**: Main content + sidebar (Streamlit default)

### Whitespace Philosophy

- **Tight but not cramped**: Tables and forms are dense for utility; sections are separated by `---` dividers
- **No hero sections**: The first screen shows the daily verse enclosure, then the roster table. No marketing banners.
- **Captions over walls of text**: Use `st.caption()` for explanatory text; use `st.info()` / `st.warning()` sparingly for important notices
- **Expanders for secondary content**: Adjustment history, mentoring pair details, and architecture diagrams live in collapsed expanders

## Depth & Elevation

The design uses a flat, low-elevation approach suitable for a data-dense utility:

- **Level 0**: Page background (no shadow)
- **Level 1**: Cards, KPI cards — `1px solid` border, slight background differentiation, no box-shadow
- **Level 2**: Verse enclosure — `3px solid gold` border for prominence
- **Level 3**: Modals, expander content — Streamlit default styling

**No drop shadows** on cards or containers. The design relies on borders and background-color contrast for layering, consistent with the quiet, utilitarian aesthetic.

## Do's and Don'ts

### Do
- Use `#0F766E` for headers, primary buttons, and KPI values
- Use `#D4AF37` only for the verse enclosure border and leadership-related highlights
- Always render the verse enclosure at the top of the page with its 3px gold border
- Use `st.caption()` for explanatory text — keep the interface light on prose
- Place secondary content in collapsed expanders
- Use `_t()` or `get_text()` for all user-facing strings (bilingual support)
- Preserve Chinese student names — never translate them
- Keep the two-tier documentation structure: simple daily use first, advanced technical details in expanders/READMES
- Use `width="stretch"` for data editors and tables
- Set `key=` on all interactive widgets for session state stability

### Don't
- Don't use gold (#D4AF37) for general-purpose buttons or body text
- Don't add drop shadows or floating cards — flat borders define the visual hierarchy
- Don't create hero sections or marketing-style banners — the first screen is the roster
- Don't use gradient backgrounds or decorative orbs
- Don't scale font size with viewport width
- Don't use negative letter-spacing
- Don't place cards inside other cards
- Don't hardcode school rules — always go through `roster/config/`
- Don't translate student names, role names, or school-specific terms
- Don't remove the verse enclosure — it's the platform's visual identity

## Responsive Behavior

### Breakpoints

| Name | Width | Key Changes |
|------|-------|-------------|
| Desktop | ≥ 992px | Full 5-column KPI row; full roster table; sidebar expanded |
| Tablet | 768–991px | 5-column KPI compresses; roster table scrolls horizontally |
| Mobile | < 768px | KPI cards stack vertically; roster table scrolls; sidebar collapses |

### Touch Targets
- Buttons maintain ≥ 44px height for touch accessibility
- Data editor cells are large enough for finger tap selection

### Collapsing Strategy
- KPI cards stack from 5-column to 2-column to 1-column
- The roster table uses horizontal scroll (native Streamlit behavior)
- The verse enclosure remains fully visible at all breakpoints

## Agent Prompt Guide

### Quick Color Reference

```
Primary teal: #0F766E
Accent gold:  #D4AF37
Light bg:     #F7F6F3
Dark bg:      #1F2526
```

### Ready-to-Use Prompts

**"Add a new section matching the existing style"**:
> Use `st.subheader()` with no extra styling. Use `st.caption()` for explanatory text. Use `st.info()` only for important notices. Follow the color palette: teal `#0F766E` for headers, warm paper `#F7F6F3` for light backgrounds, gold `#D4AF37` only for verse/leadership accents. All text must be bilingual via `_t()` or `get_text()`.

**"Add a new button"**:
> Primary buttons: filled teal `#0F766E`, white text, 6px border-radius. Secondary buttons: outlined teal, transparent background. Use Streamlit's `st.button()` with `type="primary"` or `type="secondary"`.

**"Fix dark mode"**:
> Dark mode uses `#1F2526` background with `#ffffff` text, `#e5e7eb` secondary text. Gold accents brighten to `#B8972E`. The verse enclosure must keep its 3px gold border. Cards use `#2A3033` surface color. All changes go in `roster/ui/theme.py` via CSS custom properties.

### File Locations

| Concern | File |
|---------|------|
| CSS theme (colors, modes) | `roster/ui/theme.py` |
| UI text (bilingual) | `roster/ui/messages.py` |
| Sidebar & components | `roster/ui/components.py` |
| Main app orchestration | `app.py` |
| School rules & colors | `roster/config/constants.py` |
| PDF generation | `roster/utils/pdf.py` |
