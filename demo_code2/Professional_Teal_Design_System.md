# Professional Teal Design System

**Version:** 4.0 (HyperOS Native)  
**Date:** 2026-06-27  
**Status:** Official Reference Document -- NiceGUI Edition  
**Project:** Sing Yin Secondary School Study Prefect Duty Roster System (NiceGUI Version)

---

## 0. How to Use This Document

This document is the **single source of truth** for all visual and interaction design decisions in the Sing Yin Study Prefect Duty Roster System. It serves two audiences:

| Audience | What to read | Why |
|----------|-------------|-----|
| **Developers (including AI agents)** | Sections 1–7 (Design Tokens + Components + Patterns) + Section 8 (NiceGUI Implementation Guide) | To know exactly what code to write and which classes/colors to use |
| **Designers & Decision Makers** | Philosophy + Tokens + Patterns + Section 11 (Governance) | To understand the design rationale and approval process |

**Quick Navigation:**
- Need a button color? → Section 4.1 (Buttons)
- Need a form input style? → Section 4.4 (Form Inputs)
- Need NiceGUI code for a card? → Section 4.2 (Cards)
- Need dark mode hex codes? → Section 7.1 (Dark Mode)
- Need the project structure? → Section 8.2 (Recommended Project Structure)
- Need the spacing scale? → Section 3.3 (Spacing System)

All future UI changes, new features, page redesigns, or component modifications **must follow this document**. Any deviation requires explicit approval and an update to this document.

---

## 1. Purpose of This Document

This document defines the official visual design language for the Sing Yin Study Prefect Duty Roster System.

All future UI changes, new features, page redesigns, or component modifications **must follow this document** as the single source of truth. Any deviation requires explicit approval and an update to this document.

**Core Principle:**  
Consistency > Individual preference. All interfaces must feel like they belong to the same professional system.

---

## 2. Design Philosophy — HyperOS Native

### 2.0 The HyperOS Spirit

This design system is built on Xiaomi HyperOS core principles. Every visual decision — from corner radius to animation curve — must answer: "Does this feel natural, fluid, and restrained?"

**The Six Pillars of HyperOS:**

| Pillar | Chinese | Meaning for This System |
|--------|---------|------------------------|
| **Natural** | 自然 | Organic, not mechanical. Rounded corners echo natural forms. Shadows mimic natural light. |
| **Fluid** | 流暢 | Motion that breathes. Every transition has purpose. 150-300ms easings as default. |
| **Restrained** | 克制 | Minimal but warm. Show what matters. White space is a feature. |
| **Premium** | 高級感 | Quality through micro-interactions, precise spacing, considered typography. |
| **Content-First** | 內容優先 | The roster table, the prefect name, the scripture verse — these are the heroes. |
| **Breathing Room** | 呼吸感 | Generous, purposeful spacing. Cards have room to breathe. Nothing feels cramped. |

### 2.1 What HyperOS Means for a School Duty Roster

This is a leadership tool used daily by student prefects. HyperOS principles apply differently:

- **Calm, not exciting** — Like entering a quiet library, not opening social media.
- **Trustworthy, not trendy** — Soft corners convey approachability; professional tone remains.
- **Comfortable for long sessions** — Roster planning takes 20-30 min. No visual fatigue.
- **Modern but timeless** — Looks current in 2027 without chasing design fads.

### 2.2 Visual Signature

- Soft rounding (buttons 14px, cards 20px, modals 24px)
- Layered elevation — surfaces float at different depths
- Precise typography — consistent scale, high contrast
- Purposeful color — teal (#0F766E) as single accent; gold reserved for scripture
- Generous white space — content is never crammed

### 2.3 Interaction Signature

- Every interactive element responds with subtle transformation (scale 0.97-1.02)
- Default easing: cubic-bezier(0.0, 0.0, 0.2, 1)
- Duration: 150ms for micro, 250ms for cards, 300ms for pages
- prefers-reduced-motion: all animations disabled when requested

## 3. Color System

### 3.1 Primary Brand Color

| Token                    | Hex Code    | Usage                                      |
|--------------------------|-------------|--------------------------------------------|
| `color-primary`          | `#0F766E`   | Primary buttons, headings, icons, emphasis |
| `color-primary-dark`     | `#0D5C57`   | Primary button hover / active state        |
| `color-primary-light`    | `#14B8A6`   | Subtle highlights, selected states         |

### 3.2 Neutral Colors (Light Mode)

| Token                    | Hex Code    | Usage                                      |
|--------------------------|-------------|--------------------------------------------|
| `color-background`       | `#F8FAFC`   | Page background                            |
| `color-surface`          | `#FFFFFF`   | Cards, panels, modals                      |
| `color-border`           | `#E2E8F0`   | Borders, dividers, table lines             |
| `color-text-primary`     | `#1E293B`   | Main headings and important text           |
| `color-text-secondary`   | `#64748B`   | Secondary text, descriptions               |
| `color-text-disabled`    | `#94A3B8`   | Disabled text                              |

### 3.3 Semantic Colors

| Token                    | Hex Code    | Usage                                      |
|--------------------------|-------------|--------------------------------------------|
| `color-success`          | `#10B981`   | Success states, completed duties           |
| `color-warning`          | `#F59E0B`   | Warnings, attention needed                 |
| `color-error`            | `#EF4444`   | Errors, delete actions, critical alerts    |
| `color-info`             | `#3B82F6`   | Informational messages                     |

### 3.4 Color Usage Rules

- Primary color (`#0F766E`) should be used sparingly for emphasis only.
- Neutral colors form the majority of the interface.
- Semantic colors should only be used for their intended meaning.
- Avoid using bright or saturated colors outside of the defined palette.

---

## 4. Typography

| Token             | Font Size | Font Weight | Line Height | Usage                        |
|-------------------|-----------|-------------|-------------|------------------------------|
| `text-h1`         | 28px      | 700         | 1.3         | Page main title              |
| `text-h2`         | 22px      | 600         | 1.3         | Section titles               |
| `text-h3`         | 18px      | 600         | 1.4         | Subsection titles            |
| `text-body`       | 15px      | 400         | 1.6         | Body text                    |
| `text-body-sm`    | 13px      | 400         | 1.5         | Small text, helper text      |
| `text-label`      | 14px      | 500         | 1.4         | Form labels                  |

**Font Recommendations:**
- Primary: Inter (English) / Noto Sans TC (Chinese)
- Fallback: System UI fonts

---

## 5. Spacing System

All spacing must follow the **8px grid system**:

| Token        | Value   | Common Usage                          |
|--------------|---------|---------------------------------------|
| `space-xs`   | 4px     | Tight spacing                         |
| `space-sm`   | 8px     | Component internal spacing            |
| `space-md`   | 16px    | Default spacing between elements      |
| `space-lg`   | 24px    | Spacing between sections              |
| `space-xl`   | 32px    | Large section spacing                 |
| `space-2xl`  | 48px    | Page-level spacing                    |

**Rule:** Never use arbitrary spacing values. Always use one of the tokens above.

---

## 6. Elevation & Shadows

**Light Mode Shadow Scale:**

| Level     | Shadow Value                                      | Usage                     |
|-----------|---------------------------------------------------|---------------------------|
| None      | None                                              | Flat elements             |
| Low       | `0 1px 3px rgba(0, 0, 0, 0.08)`                   | Cards, panels (default)   |
| Medium    | `0 4px 6px -1px rgba(0, 0, 0, 0.1)`               | Dropdowns, popovers       |
| High      | `0 10px 15px -3px rgba(0, 0, 0, 0.1)`             | Modals, important dialogs |

**Guideline:** Use shadows sparingly. Most cards should use **Low** elevation only.

---

## 7. Component Guidelines

### 7.1 Buttons

- **Primary Button**
  - Background: `#0F766E`
  - Text: White
  - Border-radius: 8px
  - Hover: `#0D5C57`

- **Secondary Button**
  - Background: White
  - Border: `#0F766E`
  - Text: `#0F766E`
  - Border-radius: 8px

- **Danger Button**
  - Background: `#EF4444`
  - Text: White


#### NiceGUI Implementation Example

```python
from nicegui import ui

# === Primary Button ===
ui.button("Generate Roster", on_click=generate_roster) \ \
    .props("color=teal-7") \ \
    .classes("rounded-lg font-semibold")

# Primary button with loading state
async def on_generate():
    btn.props("loading")
    # ... perform generation ...
    btn.props(remove="loading")
    ui.notify("Roster generated!", type="positive")

btn = ui.button("Generate Roster", on_click=on_generate) \ \
    .props("color=teal-7") \ \
    .classes("rounded-lg font-semibold")

# === Secondary Button ===
ui.button("Cancel", on_click=cancel) \ \
    .props("outline color=teal-7") \ \
    .classes("rounded-lg font-semibold")

# === Danger Button ===
ui.button("Delete Roster", on_click=confirm_delete) \ \
    .props("color=red-6") \ \
    .classes("rounded-lg font-semibold")

# === Disabled Button ===
ui.button("Submit").props("color=teal-7 disable").classes("rounded-lg")

# === Button Group ===
with ui.row().classes("gap-2"):
    ui.button("Save", on_click=save).props("color=teal-7").classes("rounded-lg")
    ui.button("Discard", on_click=discard).props("outline color=teal-7").classes("rounded-lg")
```

**Best Practice:** Always pair a primary action (Save/Generate) with a secondary exit (Cancel/Discard). The primary action goes on the right. Use `type="loading"` for async operations that take >500ms.

### 7.2 Cards

- Background: `#FFFFFF`
- Border-radius: 12px
- Shadow: Low elevation (`0 1px 3px rgba(0, 0, 0, 0.08)`)
- Padding: 20px (`space-lg`)
- Border: Optional, use `#E2E8F0` when needed


#### NiceGUI Implementation Example

```python
from nicegui import ui

# === Basic Card ===
with ui.card().classes("w-full max-w-md rounded-xl shadow-sm p-5"):
    ui.label("Duty Summary").classes("text-h2 mb-2")
    ui.label("Total duties this week: 35").classes("text-body text-secondary")
    ui.separator().classes("my-3")
    ui.button("View Details").props("flat color=teal-7")

# === KPI Stats Card ===
with ui.card().classes("rounded-xl shadow-sm p-5 text-center"):
    ui.label("28").classes("text-h2 text-primary")
    ui.label("Total Prefects").classes("text-body-sm text-secondary")

# === KPI Card Row ===
with ui.row().classes("gap-4 w-full"):
    with ui.card().classes("flex-1 rounded-xl shadow-sm p-4"):
        ui.label("12.5").classes("text-h2 text-primary")
        ui.label("Avg Load (pts)").classes("text-body-sm text-secondary")
    with ui.card().classes("flex-1 rounded-xl shadow-sm p-4"):
        ui.label("3.2").classes("text-h2 text-primary")
        ui.label("Fairness Index").classes("text-body-sm text-secondary")

# === Card with Header + Content + Footer ===
with ui.card().classes("w-full rounded-xl shadow-sm"):
    with ui.row().classes("w-full items-center justify-between p-5 pb-0"):
        ui.label("Roster Management").classes("text-h3")
        ui.button(icon="add").props("flat round color=teal-7")
    ui.separator().classes("my-3")
    with ui.column().classes("px-5"):
        ui.label("No rosters generated yet.").classes("text-body text-secondary py-8 text-center")
    ui.separator().classes("my-3")
    with ui.row().classes("w-full justify-end px-5 pb-3 gap-2"):
        ui.button("Import").props("outline color=teal-7")
        ui.button("Generate").props("color=teal-7")
```

**Best Practice:** Cards are the primary content container. Use the Header+Content+Footer pattern for complex cards. Keep KPI cards simple — one big number, one small label. Never nest cards inside cards.

### 7.3 Tables

- Clear borders using `color-border`
- Even rows: `#F1F5F9` (very light gray)
- Adequate row height for readability
- Header row: Bold + slightly darker background


#### NiceGUI Implementation Example

```python
from nicegui import ui

# === Duty Roster Table ===
columns = [
    {"name": "name", "label": "Prefect Name", "field": "name", "align": "left"},
    {"name": "role", "label": "Role", "field": "role", "align": "left"},
    {"name": "mon", "label": "Monday", "field": "mon", "align": "center"},
    {"name": "tue", "label": "Tuesday", "field": "tue", "align": "center"},
    {"name": "wed", "label": "Wednesday", "field": "wed", "align": "center"},
    {"name": "thu", "label": "Thursday", "field": "thu", "align": "center"},
    {"name": "fri", "label": "Friday", "field": "fri", "align": "center"},
    {"name": "load", "label": "Cumulative Load", "field": "load", "align": "right"},
]

rows = [
    {"name": "LI Chuang Jie", "role": "Head Prefect", "mon": "", "tue": "Room 302", "wed": "", "thu": "Room 303", "fri": "", "load": 3.5},
    {"name": "CHAN Tai Man", "role": "AHP", "mon": "Assist", "tue": "", "wed": "", "thu": "", "fri": "", "load": 8.0},
]

# === Basic Table with Pagination ===
table = ui.table(
    columns=columns,
    rows=rows,
    row_key="name",
    pagination={"rowsPerPage": 10, "sortBy": "load"},
).classes("w-full rounded-lg")

# === Table with Selection (for batch operations) ===
def on_selection(selection):
    ui.notify(f"{len(selection)} row(s) selected", type="info")

table = ui.table(
    columns=columns,
    rows=rows,
    row_key="name",
    selection="multiple",
).on("selection", on_selection).classes("w-full").props("flat bordered")
```

**Best Practice:** Always set `row_key` for stable row identity. Use `pagination` for tables with >20 rows. Set meaningful `align` values (left for text, right for numbers, center for status).

### 7.4 Form Inputs

- Background: White
- Border: `#E2E8F0`
- Focus state: Border becomes `#0F766E`
- Border-radius: 8px
- Consistent padding

#### NiceGUI Implementation Example

```python
from nicegui import ui
from datetime import date

# === Text Input with Validation ===
name_input = ui.input(
    label="Prefect Name *",
    placeholder="Enter full name as registered",
    validation={"Please enter a name": lambda v: len(v.strip()) > 0},
).classes("w-full max-w-md").props("outlined color=teal-7")

# === Select / Dropdown ===
ui.select(
    label="Role *",
    options=["Study Prefect", "Assistant Head Study Prefect"],
).classes("w-full max-w-md").props("outlined color=teal-7")

# === Date Picker ===
ui.date(label="Duty Date", value=date.today()).props("outlined color=teal-7")

# === Checkbox ===
ui.label("Available Days:").classes("text-label mt-4")
with ui.row().classes("gap-4"):
    ui.checkbox("Monday", value=True).props("color=teal-7")
    ui.checkbox("Tuesday", value=True).props("color=teal-7")
    ui.checkbox("Wednesday").props("color=teal-7")

# === Radio Group ===
ui.radio(["Room 302", "Room 303", "Room 202"], value="Room 302").props("color=teal-7")

# === Textarea ===
ui.textarea(label="Remarks", placeholder="Optional notes...").classes("w-full max-w-md").props("outlined color=teal-7 rows=4")

# === Complete Form ===
async def submit_prefect_form():
    if not name_input.value:
        ui.notify("Name is required.", type="negative")
        return
    ui.notify(f"Added {name_input.value}.", type="positive")

with ui.card().classes("w-full max-w-lg rounded-xl shadow-sm p-6"):
    ui.label("Add New Prefect").classes("text-h2 mb-4")
    name_input = ui.input(label="Full Name *", placeholder="Enter full name").classes("w-full mb-4").props("outlined color=teal-7")
    role_select = ui.select(label="Role *", options=["Study Prefect", "Assistant Head Study Prefect"]).classes("w-full mb-4").props("outlined color=teal-7")
    form_select = ui.select(label="Form *", options=["F.3", "F.4", "F.5", "F.6"]).classes("w-full mb-6").props("outlined color=teal-7")
    with ui.row().classes("gap-2"):
        ui.button("Add Prefect", on_click=submit_prefect_form).props("color=teal-7").classes("rounded-lg")
        ui.button("Clear", on_click=lambda: [name_input.set_value(""), role_select.set_value(None)]).props("outline color=teal-7").classes("rounded-lg")
```

**Best Practice:** Validate inputs early (on blur or on submit). Show clear error messages below the field. Use `outlined` for all inputs for consistent visual style. Group related inputs in a `ui.card()` with clear section hierarchy.

### 7.5 Tabs

- Active tab: `#0F766E` text + underline
- Inactive tab: `#64748B` text
- Clean separation between tabs

#### NiceGUI Implementation Example

```python
from nicegui import ui

# === Basic Tabs ===
with ui.tabs().classes("w-full") as tabs:
    tab_view = ui.tab("My Duties", icon="assignment_ind")
    tab_all = ui.tab("All Duties", icon="group")
    tab_stats = ui.tab("Statistics", icon="bar_chart")

with ui.tab_panels(tabs, value=tab_view).classes("w-full"):
    with ui.tab_panel(tab_view):
        ui.label("Your assigned duties appear here.").classes("text-body")
    with ui.tab_panel(tab_all):
        ui.label("Full team roster appears here.").classes("text-body")
    with ui.tab_panel(tab_stats):
        ui.label("Fairness metrics appear here.").classes("text-body")

# === Tabs with Badge Counts ===
with ui.tabs().classes("w-full bg-teal-50 dark:bg-teal-900 rounded-lg p-1") as tabs2:
    ui.tab("Pending (3)", icon="pending")
    ui.tab("Confirmed (12)", icon="check_circle")
    ui.tab("Completed (45)", icon="task_alt")
```

**Best Practice:** Tabs work best with 2-5 options. Use icons to reinforce meaning, not as decoration. Badge counts in tab labels help users scan quickly. For responsive layouts, tabs may need to wrap or collapse on mobile.

### 7.6 Iconography Guidelines

**General Rules:**
- Use simple, line-style icons (stroke weight ≈ 2px)
- Preferred icon library: Heroicons, Lucide, or Tabler Icons (consistent style)
- Icon color should follow text color tokens (`color-text-primary` or `color-primary`)
- Avoid colorful or overly decorative icons unless semantically necessary

**Size Scale:**
| Size     | Pixel Size | Usage                        |
|----------|------------|------------------------------|
| Small    | 16px       | Inline with text             |
| Medium   | 20–24px    | Buttons, menu items (default)|
| Large    | 32px       | Empty states, feature icons  |

**Do:**
- Use icons to support meaning, not replace text
- Keep icon style consistent across the entire system
- Use `color-primary` for interactive icons

**Don't:**
- Mix different icon styles (e.g., filled + outline)
- Use icons purely for decoration
- Use very thin or very bold icons inconsistently

---

### 7.7 Form Validation & Error States

**Input States:**

| State          | Border Color     | Background     | Helper Text Color | Icon (if any)      |
|----------------|------------------|----------------|-------------------|--------------------|
| Default        | `#E2E8F0`        | White          | `#64748B`         | None               |
| Focus          | `#0F766E`        | White          | `#64748B`         | None               |
| Error          | `#EF4444`        | `#FEF2F2`      | `#EF4444`         | Red error icon     |
| Success        | `#10B981`        | `#F0FDF4`      | `#10B981`         | Green check icon   |
| Disabled       | `#E2E8F0`        | `#F8FAFC`      | `#94A3B8`         | None               |

**Error Message Rules:**
- Always show clear, actionable error messages
- Place error message directly below the input field
- Use `color-error` (`#EF4444`) for error text
- Example: “請輸入有效的學號” 而非 “輸入錯誤”

**Validation Timing:**
- Show error immediately after user leaves the field (on blur)
- Or show error when form is submitted

---

### 7.8 Feedback Components

#### Alerts / Banners
- Use colored left border or background tint
- Success: Light green background (`#F0FDF4`) + green text
- Warning: Light yellow background + warning text
- Error: Light red background (`#FEF2F2`) + red text
- Info: Light blue background + blue text

#### Toast Notifications
- Appear at top-right or bottom-right
- Auto-dismiss after 3–5 seconds (unless critical)
- Use the same semantic colors as above
- Keep message concise (1–2 lines max)

#### NiceGUI Implementation Example

```python
# === Basic Toasts ===
ui.notify("Roster generated!", type="positive", position="top")
ui.notify("Failed to save.", type="negative", position="top")
ui.notify("Unsaved changes.", type="warning", position="top", timeout=5000)
ui.notify("Update available.", type="info", position="top")

# === Persistent Toast ===
ui.notify("Fairness gap is large.", type="warning", timeout=0, close_button="Dismiss")

# === Success Banner ===
with ui.element("div").classes("w-full bg-green-50 dark:bg-green-900/20 border-l-4 border-green-500 p-4 mb-4 rounded-r-lg"):
    with ui.row().classes("items-center gap-3"):
        ui.icon("check_circle").classes("text-green-600")
        ui.label("Roster generated and saved.").classes("text-body text-green-800 dark:text-green-200")
```

**Best Practice:** Use `type="positive"` for success (auto-dismiss), `type="negative"` for errors (persistent), and `type="warning"` for reminders. Banners are for persistent contextual messages; Toasts are for transient feedback. Never show more than 3 toasts simultaneously.

#### Modal / Dialog
- Background overlay: `rgba(0, 0, 0, 0.4)`
- Modal container: White background, 12px radius, medium shadow
- Always include clear title and action buttons
- Primary action on the right, secondary/cancel on the left


#### NiceGUI Implementation Example

```python
from nicegui import ui

# === Confirmation Modal (Delete Roster) ===
with ui.dialog() as delete_dialog, ui.card().classes("rounded-xl p-6 max-w-md"):
    ui.label("Delete Roster").classes("text-h2 mb-2")
    ui.label("Are you sure you want to delete this roster? This action cannot be undone.") \ \
    .classes("text-body text-secondary mb-6")
    with ui.row().classes("gap-2 justify-end"):
        ui.button("Cancel", on_click=delete_dialog.close) \ \
    .props("outline color=teal-7").classes("rounded-lg")
        ui.button("Delete", on_click=lambda: [perform_delete(), delete_dialog.close()]) \ \
    .props("color=red-6").classes("rounded-lg")

# Trigger button
ui.button("Delete Roster", on_click=delete_dialog.open) \ \
    .props("color=red-6").classes("rounded-lg")

# === Form Modal (Leave Request) ===
with ui.dialog() as leave_dialog, ui.card().classes("rounded-xl p-6 max-w-lg"):
    ui.label("Post-Duty Leave Adjustment").classes("text-h2 mb-3")
    ui.label("Select the date and position for the leave adjustment.") \ \
    .classes("text-body text-secondary mb-4")
    
    day_input = ui.select(
        label="Day",
        options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    ).classes("w-full mb-3").props("outlined color=teal-7")
    
    role_input = ui.select(
        label="Position",
        options=["Room 302", "Room 303 - 1", "Room 303 - 2"],
    ).classes("w-full mb-3").props("outlined color=teal-7")
    
    has_replace = ui.checkbox("Assign a substitute").props("color=teal-7")
    
    with ui.row().classes("gap-2 justify-end mt-4"):
        ui.button("Cancel", on_click=leave_dialog.close) \ \
    .props("outline color=teal-7").classes("rounded-lg")
        ui.button("Apply Adjustment", on_click=lambda: [apply_leave(), leave_dialog.close()]) \ \
    .props("color=teal-7").classes("rounded-lg")

# Open modal button
ui.button("Adjust Leave", on_click=leave_dialog.open) \ \
    .props("color=teal-7").classes("rounded-lg")
```

**Modal Behavior Rules:**
- Background overlay: `rgba(0, 0, 0, 0.4)` (automatic with NiceGUI `ui.dialog()`)
- Modal card: white background, 12px radius, medium shadow (applied via `.classes("rounded-xl")`)
- Primary action always on the **right**, secondary/cancel on the **left**
- Use `delete_dialog.close()` to dismiss, or `delete_dialog.open()` to show

---

### 7.9 Empty States

**When to use:**
- No data available (e.g., no duty records yet)
- Search returns no results
- First-time user experience

**Design Rules:**
- Use a simple illustration or large icon (32–48px)
- Clear heading (e.g., “目前沒有值班記錄”)
- Helpful description (1–2 sentences)
- Optional: Primary action button (e.g., “新增值班”)
- Keep tone calm and helpful, not negative

#### NiceGUI Implementation Example

```python
# === No Data Empty State ===
with ui.column().classes("w-full items-center justify-center py-16"):
    ui.icon("inbox").classes("text-6xl text-slate-300 mb-4")
    ui.label("No Duty Records Yet").classes("text-h3 text-slate-400 mb-2")
    ui.label("Generate your first roster to see duty assignments.").classes("text-body text-secondary mb-6")
    ui.button("Generate First Roster", on_click=generate_roster).props("color=teal-7").classes("rounded-lg")

# === Search No Results ===
with ui.column().classes("w-full items-center justify-center py-12"):
    ui.icon("search_off").classes("text-5xl text-slate-300 mb-3")
    ui.label("No Results Found").classes("text-h3 text-slate-400 mb-1")
    ui.label("Try adjusting your search terms.").classes("text-body-sm text-secondary")
```

**Best Practice:** Empty states should always provide a clear next action. Use large icons (48-64px) in muted colors. The tone should be helpful and positive, never negative. Always include a primary CTA button when applicable.

---

### 7.10 Loading States

**Types:**
- **Page Loading**: Full-screen subtle spinner or skeleton screen
- **Component Loading**: Spinner inside the card or button
- **Button Loading**: Replace button text with spinner + disable button

**Guidelines:**
- Use a consistent spinner style across the system
- Never show multiple loading indicators at the same time if possible
- For long operations, show progress text when helpful

#### NiceGUI Implementation Example

```python
import asyncio

# === Page Loading Spinner ===
with ui.row().classes("w-full justify-center py-24"):
    ui.spinner(size="lg", color="teal-7")

# === Button Loading State ===
async def generate_with_loading():
    btn.props("loading")
    await asyncio.sleep(2)
    btn.props(remove="loading")
    ui.notify("Roster generated!", type="positive")

btn = ui.button("Generate Roster", on_click=generate_with_loading).props("color=teal-7").classes("rounded-lg")

# === Table Skeleton Loader ===
def skeleton_card():
    with ui.card().classes("w-full rounded-xl shadow-sm p-5"):
        ui.element("div").classes("h-6 bg-slate-200 dark:bg-slate-700 rounded w-1/3 mb-4 animate-pulse")
        ui.element("div").classes("h-8 bg-slate-100 dark:bg-slate-700 rounded w-full mb-2 animate-pulse")
        for _ in range(5):
            ui.element("div").classes("h-6 bg-slate-50 dark:bg-slate-700/50 rounded w-full mb-2 animate-pulse")

# === Progress Bar ===
ui.linear_progress(value=0.4).props("color=teal-7").classes("w-full")
ui.label("Allocating duties... 40% complete").classes("text-body-sm text-secondary mt-1")
```

**Best Practice:** Prefer skeleton screens over spinners for content that takes >1s to load. Use button loading state (`props("loading")`) for form submissions. Always show progress text for operations lasting >3s. Use `animate-pulse` Tailwind class for skeleton animations.

---

### 7.11 Language Toggle / Internationalization Controls

**Design Principle:** Language switching must be discoverable by users who only understand ONE of the available languages. A bare icon (e.g., globe or translate symbol) is insufficient ? the button must show bilingual text.

#### Visual Specification

| Property | Value | Rationale |
|----------|-------|-----------|
| **Button text** | `ZH / EN` (always shows both language codes) | A user who only reads Chinese can find "ZH"; a user who only reads English can find "EN" |
| **Icon** | `translate` (Material icon) | Supplementary visual cue alongside text |
| **Style** | `flat color=teal-7` | Matches theme toggle; understated, not a primary action |
| **Font size** | `text-xs` (12px) | Compact ? this is a utility control, not a hero action |
| **Font weight** | `font-medium` (500) | Enough to be readable without competing with the title |
| **Placement** | Header, right-aligned, next to Theme toggle | Consistent with other utility controls |

#### HyperOS Alignment

- **Natural**: The bilingual text is self-explanatory ? no guesswork needed.
- **Fluid**: Instant language switch with a brief confirmation notification.
- **Restrained**: Compact, minimal visual footprint. Not a primary CTA.
- **Inclusive**: Works for users who only understand one of the two languages.

#### NiceGUI Implementation

```python
# In components/header.py
lang_label = "ZH / EN"  # Always bilingual, always recognizable
ui.button(lang_label, icon="translate", on_click=switch_language) \
    .props("flat color=teal-7").classes("text-xs font-medium")
```

#### Accessibility

- The button text is always visible (no hover-to-reveal)
- The `translate` icon provides a secondary visual cue
- The notification after switching confirms the action in both languages
- Keyboard accessible (standard button behavior)

---

## 5.6 Layout Principles

1. **Strong Visual Hierarchy** — Use typography and spacing to create clear reading order.
2. **Consistent Alignment** — Align elements to the 8px grid.
3. **Breathing Room** — Avoid cramped layouts. Use `space-md` or larger between major sections.
4. **Card-Based Organization** — Group related content inside cards.
5. **Responsive Mindset** — Design should work well on both desktop and tablet.

---

## 7.3 Accessibility Guidelines (WCAG 2.1)

本系統致力於符合 **WCAG 2.1 Level AA** 標準，讓所有使用者（包括有視覺、聽覺、行動或認知障礙的使用者）都能有效使用。

### 9.1 核心原則（POUR）

| 原則          | 說明                                      | 本系統要求 |
|---------------|-------------------------------------------|------------|
| **Perceivable**   | 資訊必須能被感知                          | 提供足夠對比、替代文字、清晰排版 |
| **Operable**      | 介面必須可操作                            | 支援鍵盤操作、避免內容閃爍 |
| **Understandable** | 資訊與操作必須可理解                      | 清楚的標籤、錯誤訊息、說明文字 |
| **Robust**        | 內容必須能在不同裝置與輔助工具上運作      | 使用語義化標記、相容性測試 |

### 9.2 必須遵守的 WCAG 2.1 具體標準（Level AA）

| 成功標準                  | 等級 | 具體要求                                                                 | 本系統實作方式 |
|---------------------------|------|--------------------------------------------------------------------------|----------------|
| **1.4.3 Contrast (Minimum)** | AA   | 一般文字對比至少 **4.5:1**，大文字至少 **3:1**                           | 使用 `color-text-primary` (`#1E293B`) 與背景色，確保通過測試 |
| **1.4.11 Non-text Contrast** | AA   | UI 元件（按鈕、輸入框、圖示）邊界或狀態對比至少 **3:1**                  | Primary 按鈕、輸入框邊框、圖示顏色需符合 |
| **2.4.3 Focus Order**        | A    | 鍵盤操作時焦點順序必須合理                                               | 確保 Tab 鍵順序符合視覺閱讀順序 |
| **2.4.7 Focus Visible**      | AA   | 鍵盤焦點必須有明顯視覺指示                                               | 所有可互動元件 focus 時必須有明顯 outline 或顏色變化 |
| **3.3.1 Error Identification** | A  | 表單錯誤必須清楚指出是哪個欄位錯誤                                       | 錯誤時同時顯示紅色邊框 + 錯誤訊息 |
| **3.3.2 Labels or Instructions** | A | 每個輸入欄位必須有清楚的標籤或說明                                       | 所有 input 必須有 `<label>` 或 aria-label |
| **4.1.2 Name, Role, Value**  | A    | 所有 UI 元件必須有正確的名稱、角色與狀態                                 | NiceGUI 元件需正確設定 aria 屬性 |
| **2.1.1 Keyboard**           | A    | 所有功能必須能用鍵盤完成                                                 | 避免只靠滑鼠才能操作的功能 |
| **1.3.1 Info and Relationships** | A | 資訊與元件之間的關係必須能被程式判讀                                     | 正確使用 heading、list、table 語義 |

### 9.3 實務建議（本系統）

- 所有互動元件（按鈕、連結、輸入框）必須支援鍵盤操作。
- 顏色不能作為唯一傳達資訊的方式（例如錯誤必須同時有文字說明）。
- 所有圖示如果帶有意義，必須有替代文字（`aria-label`）。
- 表單提交後，焦點應自動移到第一個錯誤欄位。
- 重要操作（例如刪除值班記錄）應有確認機制。

---

## 7.2 Responsive Design Principles

- 主要以 **Desktop / Tablet** 為設計目標（學校內部使用情境）。
- 最小支援寬度：**1024px**（建議在 1280px 以上有最佳體驗）。
- 使用 **Responsive Grid** 或 **Flexbox** 確保元件在不同寬度下仍保持良好排列。
- 重要操作按鈕在小尺寸螢幕上應保持足夠點擊區域（至少 44×44px）。
- 表格在窄螢幕時可考慮 horizontal scroll 或轉為卡片式呈現。

---

## 11. Do's and Don'ts

### Do's（建議這樣做）

- 使用系統定義的顏色、間距與元件規範。
- 保持介面乾淨、層次分明。
- 錯誤訊息要清楚且具行動性（例如「請輸入 6 位學號」而非「格式錯誤」）。
- 重要操作提供確認或 Undo 機制。
- 在空狀態提供有幫助的引導文字與操作按鈕。
- 確保鍵盤操作順暢且焦點可見。

### Don'ts（避免這樣做）

- 不要使用未定義在設計系統中的顏色或間距。
- 不要只靠顏色來傳達重要資訊（例如只用紅色表示錯誤而無文字）。
- 不要讓按鈕太小或太接近（避免誤觸）。
- 不要在同一個畫面使用過多不同風格的元件。
- 不要忽略 loading 與 empty state 的設計。
- 不要在沒有明確標籤的情況下使用圖示。

---

## 7.1 Dark Mode Color System

Dark Mode 為可選模式，預設為 Light Mode。使用者可透過右上角切換按鈕切換深淺色模式。

### 12.1 Dark Mode 顏色規範（具體 Hex Code）

| Token                        | Hex Code    | 用途                                      | 備註 |
|------------------------------|-------------|-------------------------------------------|------|
| `color-primary`              | `#0F766E`   | Primary buttons, headings, icons          | 與淺色模式相同 |
| `color-primary-dark`         | `#0D5C57`   | Primary hover / active                    | 與淺色模式相同 |
| `color-primary-light`        | `#14B8A6`   | Subtle highlights                         | 與淺色模式相同 |
| `color-background`           | `#0F172A`   | 頁面背景                                  | 深色背景 |
| `color-surface`              | `#1E293B`   | 卡片、面板、彈窗背景                      | 比背景稍亮 |
| `color-surface-2`            | `#334155`   | 次要卡片、hover 區域                      | - |
| `color-border`               | `#475569`   | 邊框、分割線                              | 較明顯邊框 |
| `color-text-primary`         | `#F1F5F9`   | 主要標題與重要文字                        | 淺色文字 |
| `color-text-secondary`       | `#94A3B8`   | 次要文字、說明文字                        | - |
| `color-text-disabled`        | `#64748B`   | 禁用狀態文字                              | - |
| `color-success`              | `#10B981`   | 成功狀態                                  | 維持原色 |
| `color-warning`              | `#F59E0B`   | 警告狀態                                  | 維持原色 |
| `color-error`                | `#EF4444`   | 錯誤狀態                                  | 維持原色 |

### 12.2 Dark Mode 設計原則

- Primary 顏色（`#0F766E`）在深色模式下保持不變，確保品牌一致性。
- 背景使用深色系（`#0F172A` → `#1E293B`），減少眼睛疲勞。
- 文字顏色使用淺色系，確保足夠對比度（符合 WCAG AA）。
- 卡片與面板使用 `color-surface`（`#1E293B`），與背景形成層次。
- 避免在深色模式下使用過亮的顏色，保持專業穩重的感覺。
- 陰影在深色模式下可適度加強，以增加立體感。

### 12.3 切換機制建議

- 右上角提供深淺色切換開關（Toggle）。
- 使用者選擇應儲存在 localStorage 或使用者設定中。
- 系統應記住使用者上次選擇的模式，下次登入時自動套用。

---

## 11. Rules & Governance

### Mandatory Rules

1. All UI development must follow the color, typography, spacing, and component rules defined in this document.
2. New components must be added to this document before being used in production.
3. Deviations from this system require written justification and approval.
4. When in doubt, choose clarity and consistency over visual flair.

### Update Process

- Any proposed changes to this design system must be documented.
- Version number must be incremented.
- All team members (including Codex) must be notified of updates.

---

## 7.4 Motion Design Principles

本系統的動畫設計遵循「**專業、克制、有目的**」的原則。動畫應該幫助使用者理解介面變化，而不是分散注意力。

### 14.1 核心原則

- **Subtle（克制）**：動畫要輕微、自然，不要誇張或花俏。
- **Purposeful（有目的）**：只在有意義的地方使用動畫（例如狀態變化、回饋、層級轉換）。
- **Consistent（一致）**：全系統使用相同的動畫時長與 easing 曲線。
- **Accessible（無障礙）**：尊重使用者的 `prefers-reduced-motion` 設定。

### 14.2 Easing Scale（推薦緩動曲線）

| Token              | Cubic Bezier 值                  | 推薦用途                              | 建議時長     |
|--------------------|----------------------------------|---------------------------------------|--------------|
| `ease-standard`    | `cubic-bezier(0.0, 0.0, 0.2, 1)` | **主要使用**：按鈕、卡片、hover、一般 UI 變化 | 150–200ms    |
| `ease-emphasized`  | `cubic-bezier(0.2, 0.0, 0.0, 1)` | Modal、Drawer、重要內容出現           | 250–300ms    |
| `ease-decelerate`  | `cubic-bezier(0.0, 0.0, 0.2, 1)` | 從畫面外進入的元素                    | 200–250ms    |
| `ease-linear`      | `linear`                         | Loading Spinner、Progress             | 依需求       |

**最常用曲線**：`ease-standard`（適用於系統中約 80% 的動畫）

### 14.3 推薦動畫時長（Duration）

| 用途                     | 時長       | Easing            | 說明 |
|--------------------------|------------|-------------------|------|
| Hover / Focus            | 150ms      | `ease-standard`   | 按鈕、連結、卡片 |
| 小型 UI 變化             | 150–200ms  | `ease-standard`   | 展開、收合、切換 |
| Modal / Dialog           | 250ms      | `ease-emphasized` | 開啟與關閉 |
| Dropdown / Popover       | 150ms      | `ease-standard`   | 快速回應 |
| Toast 出現               | 200ms      | `ease-standard`   | 輕快提示 |
| 頁面 / 大區塊切換        | 200–250ms  | `ease-standard`   | 清晰但不拖沓 |

### 14.4 特定場景動畫建議

**Modal / Dialog**
- 開啟：使用 `ease-emphasized`，250ms，從輕微縮放 + 淡入
- 關閉：同樣使用 `ease-emphasized`，較快結束（200ms）
- 背景遮罩：同時淡入淡出

**Table 互動**
- 排序切換：使用 `ease-standard`，150ms
- 新增 / 刪除行：使用 `ease-standard`，200ms（建議搭配淡入淡出）
- 避免對整張表格使用複雜動畫

**Dashboard / 統計數據**
- 數據更新：使用 `ease-standard`，200–250ms
- 數字計數動畫（count up）：可使用，但需保持簡潔
- 圖表更新：建議使用較短的 `ease-standard`（150–200ms）

**Form 互動**
- 錯誤訊息顯示：`ease-standard`，150ms，淡入
- 成功狀態切換：`ease-standard`，200ms
- 避免在輸入時使用動畫（會干擾使用者）

**Card Hover**
- 推薦輕微上浮（`translateY(-2px)`）+ 陰影加強
- 時長 200ms，使用 `ease-standard`

### 14.5 技術實作建議（NiceGUI）

- 優先使用 CSS `transition` 而非 JavaScript 動畫。
- 動畫屬性優先使用 `transform` 和 `opacity`（效能較好）。
- 重要動畫應支援 `prefers-reduced-motion` media query。
- 保持動畫時長短且一致。

---

## 15. Data Visualization Guidelines

資料視覺化應保持**清晰、專業、易讀**，避免過度裝飾。

### 15.1 圖表類型推薦

| 用途               | 推薦圖表類型     | 顏色使用                     | 備註 |
|--------------------|------------------|------------------------------|------|
| 單一數值比較       | Bar Chart        | Primary + Neutral            | 最常用 |
| 時間趨勢           | Line Chart       | Primary 主線                 | 適合 duty 趨勢 |
| 比例分布           | Pie / Donut      | 使用語義色（最多 5 種）      | 避免過多顏色 |
| 狀態分布           | Donut Chart      | Success / Warning / Error    | 適合 duty 完成率 |

### 15.2 設計原則

- 優先使用 **Bar Chart** 和 **Line Chart**（最清晰）。
- 顏色應使用設計系統定義的語義色。
- 圖表應有清楚的標題、圖例和數值標示。
- 避免 3D 效果、過多陰影或漸層。
- 重要數據可使用強調色（Primary）。
- 圖表區域應有足夠的留白。

### 15.3 Stats Card 設計

- 使用卡片包裝單一或多個統計數據。
- 主要數字使用較大字體（`text-h2` 或以上）。
- 可搭配小圖示（使用 Primary 色）。
- 變化趨勢可用小箭頭 + 顏色表示（綠色上升、紅色下降）。

#### NiceGUI Implementation Example

```python
from nicegui import ui

# === Bar Chart: Duties by Day (using ui.echart) ===
ui.echart({
    "title": {"text": "Duties by Day", "left": "center"},
    "xAxis": {"type": "category", "data": ["Mon", "Tue", "Wed", "Thu", "Fri"]},
    "yAxis": {"type": "value"},
    "series": [{
        "data": [8, 10, 7, 9, 6],
        "type": "bar",
        "itemStyle": {"color": "#0F766E"},
        "barWidth": "50%",
    }],
    "grid": {"top": 40, "right": 20, "bottom": 30, "left": 40},
}).classes("w-full h-64")

# === Pie Chart: Duties by Role ===
ui.echart({
    "title": {"text": "Duty Distribution by Role", "left": "center"},
    "tooltip": {"trigger": "item"},
    "series": [{
        "type": "pie",
        "radius": ["40%", "70%"],
        "data": [
            {"value": 25, "name": "Study Prefect"},
            {"value": 8, "name": "AHP"},
            {"value": 2, "name": "Head Prefect"},
        ],
        "itemStyle": {"borderRadius": 4, "borderColor": "#fff", "borderWidth": 2},
    }],
}).classes("w-full h-64")

# === Line Chart: Load Trend ===
ui.echart({
    "title": {"text": "Avg Load Trend", "left": "center"},
    "xAxis": {"type": "category", "data": ["Wk1", "Wk2", "Wk3", "Wk4"]},
    "yAxis": {"type": "value", "name": "pts"},
    "series": [{
        "data": [10.5, 9.8, 11.2, 8.9],
        "type": "line",
        "smooth": True,
        "lineStyle": {"color": "#0F766E", "width": 2},
        "itemStyle": {"color": "#0F766E"},
    }],
    "grid": {"top": 40, "right": 20, "bottom": 30, "left": 50},
}).classes("w-full h-64")
```

**Best Practice:** Keep charts simple and focused. Use the design system's teal (`#0F766E`) as the primary chart color. Always include clear titles and labels. Avoid 3D effects or excessive decoration. For duty roster data, bar charts and line charts are the most effective choices.

---

## 16. Role & Permission Visual Distinction

不同角色應有清楚的視覺區分，幫助使用者快速識別權限等級。

### 16.1 角色顏色建議（Sing Yin Study Prefect 系統）

| 角色                        | 標籤顏色          | 文字顏色     | 用途 |
|-----------------------------|-------------------|--------------|------|
| **Head Study Prefect**      | `#0F766E` (Primary) | White        | 最高權限 |
| **Assistant Head Prefect**  | `#14B8A6`         | Dark         | 重要角色 |
| **Study Prefect**           | `#64748B`         | White        | 一般值班 prefect |
| **F.3 / F.4 Prefect**       | `#94A3B8`         | Dark         | 較低年級 |

### 16.2 視覺區分方式

- **Badge / Tag**：最推薦的方式（清晰且不佔空間）。
- **表格欄位**：可在名字旁邊顯示角色 Badge。
- **權限提示**：重要操作按鈕應根據角色顯示或隱藏。
- **顏色使用**：僅用於 Badge，不建議整行或整卡片變色（避免視覺干擾）。


#### NiceGUI Implementation Example

```python
from nicegui import ui

# === Role Badge Factory ===
def role_badge(role: str):
    """Render a colored badge for the given prefect role."""
    color_map = {
        "Head Study Prefect": ("bg-teal-700", "text-white"),
        "Assistant Head Study Prefect": ("bg-teal-500", "text-white"),
        "Study Prefect": ("bg-slate-500", "text-white"),
        "F.3 Prefect": ("bg-slate-300", "text-slate-700"),
        "F.4 Prefect": ("bg-slate-300", "text-slate-700"),
        "F.5 Prefect": ("bg-slate-300", "text-slate-700"),
    }
    bg_class, text_class = color_map.get(role, ("bg-slate-200", "text-slate-600"))
    ui.label(role).classes(f"px-2 py-1 rounded-full text-xs font-medium {bg_class} {text_class}")

# === Status Badge ===
def status_badge(status: str):
    """Render a colored badge for prefect status."""
    status_map = {
        "Active": ("bg-green-100", "text-green-800", "Active"),
        "On Leave": ("bg-yellow-100", "text-yellow-800", "On Leave"),
        "Inactive": ("bg-slate-100", "text-slate-500", "Inactive"),
        "Blocked": ("bg-red-100", "text-red-700", "Blocked"),
    }
    bg, text, display = status_map.get(status, ("bg-slate-100", "text-slate-500", status))
    ui.label(display).classes(f"px-2 py-1 rounded-full text-xs font-medium {bg} {text}")

# === Usage in a row ===
with ui.row().classes("gap-2 items-center"):
    ui.label("LI Chuang Jie").classes("text-body font-medium")
    role_badge("Head Study Prefect")
    status_badge("Active")

# === Tag/Chip for Duty Rooms ===
with ui.row().classes("gap-2 flex-wrap"):
    ui.chip("Room 302", removable=False).props("color=teal-7 text-white")
    ui.chip("Room 303", removable=False).props("color=orange-7 text-white")
    ui.chip("Room 202", removable=False).props("color=blue-7 text-white")
    ui.chip("Monday", icon="event", removable=True).props("color=teal-1")
```

### 16.3 權限視覺提示原則

- 無權限的操作應顯示為 **Disabled** 狀態（而非隱藏）。
- 重要操作（例如刪除、調整全體值班）應有額外確認。
- 使用者應能清楚知道自己目前的角色與權限範圍。

---

## 17. Sidebar & Navigation Guidelines

### 17.1 Sidebar 設計原則

- 寬度建議：**240px – 280px**。
- 背景色：使用 `color-surface`（深色模式則使用較深 surface）。
- 目前頁面應有清楚的 **Active 狀態**（使用 Primary 色左邊框或背景強調）。
- 圖示 + 文字並排，圖示使用 `ease-standard` hover 效果。
- 分組之間使用細分隔線。

### 17.2 Navigation 項目設計

- Hover 時輕微背景變化（使用 `color-surface-2`）。
- Active 項目使用 Primary 色作為視覺錨點。
- 重要或常用功能可置頂。
- 較少使用的功能可收納在「更多」或次級選單。

### 17.3 響應式考量

- 在較小螢幕上可收納為漢堡選單（Hamburger Menu）。
- 行動版 Sidebar 建議使用 Drawer 形式從側邊滑出。

#### NiceGUI Implementation Example

```python
from nicegui import ui

# === Main Sidebar ===
with ui.left_drawer(value=True, bordered=True).classes("bg-white dark:bg-slate-800") as sidebar:
    with ui.column().classes("w-full"):
        ui.label("SY Study Prefect").classes("text-h3 text-primary px-4 py-6")
        ui.separator()
        nav_items = [
            ("Dashboard", "dashboard", True),
            ("Roster", "calendar_month", False),
            ("Prefects", "people", False),
            ("Leave Adjustment", "edit_calendar", False),
            ("Audit Log", "history", False),
        ]
        with ui.column().classes("w-full gap-1 px-2 py-2"):
            for label, icon_name, is_active in nav_items:
                active_class = "bg-teal-50 dark:bg-teal-900" if is_active else ""
                text_class = "text-primary font-medium" if is_active else "text-secondary"
                with ui.row().classes(f"w-full items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-100 cursor-pointer {active_class}"):
                    ui.icon(icon_name).classes(f"{'text-primary' if is_active else 'text-secondary'} text-xl")
                    ui.label(label).classes(f"text-body {text_class}")

# === Responsive Toggle ===
ui.button(icon="menu", on_click=lambda: sidebar.toggle()).props("flat round").classes("lg:hidden")

# === Top Navigation Bar ===
with ui.header(elevated=True).classes("bg-white dark:bg-slate-800"):
    with ui.row().classes("w-full items-center justify-between px-4"):
        ui.button(icon="menu", on_click=lambda: sidebar.toggle()).props("flat round").classes("lg:hidden")
        ui.label("Duty Roster System").classes("text-h3 text-primary")
        ui.space()
        ui.button(icon="dark_mode", on_click=toggle_theme).props("flat round")
```

**Best Practice:** Keep the sidebar width between 240-280px. Use clear active state indicators (teal background or left border). Group nav items logically with separators. On mobile, collapse the sidebar and show a hamburger toggle. Never put more than 8-10 primary nav items.

---

## 18. Form Design Guidelines

表單是系統中最頻繁使用的介面之一，應保持**清晰、一致、易操作**。

### 18.1 表單欄位設計原則

- 每個輸入欄位必須有清楚的 **Label**（使用 `text-label` 樣式）。
- 必填欄位應在 Label 後加上紅色星號（*）。
- 使用 Placeholder 作為輔助說明，而非主要提示。
- 相關欄位可使用 **Group** 或 **Section** 進行分組。
- 表單寬度建議控制在 **400px – 600px** 以內，避免過寬。

### 18.2 輸入類型建議

| 輸入類型         | 推薦元件                  | 備註 |
|------------------|---------------------------|------|
| 文字輸入         | Text Input                | 單行文字 |
| 多行文字         | Textarea                  | 備註、說明 |
| 日期選擇         | Date Picker               | 值班日期 |
| 下拉選單         | Select / Combobox         | 角色、年級、房間 |
| 核取方塊         | Checkbox                  | 多選項目 |
| 單選按鈕         | Radio Group               | 單一選擇 |
| 開關             | Switch / Toggle           | 啟用 / 停用 |

### 18.3 表單驗證與回饋

- 即時驗證（on blur）優於提交後才驗證。
- 錯誤訊息必須清楚指出問題與解決方式。
- 成功提交後應有明確的成功提示（Toast 或頁面訊息）。
- 提交按鈕在處理中應顯示 Loading 狀態並禁用。

#### NiceGUI Implementation Example

```python
from nicegui import ui
from datetime import date

# === Full Leave Request Form ===
async def submit_leave():
    errors = []
    if not name.value:
        errors.append("Prefect name is required.")
    if not date_val.value:
        errors.append("Date is required.")
    if errors:
        for e in errors:
            ui.notify(e, type="negative", position="top")
        return

    btn.props("loading")
    # ... process submission ...
    await asyncio.sleep(1)  # simulate API call
    btn.props(remove="loading")
    ui.notify(f"Leave approved for {name.value} on {date_val.value}.", type="positive")

with ui.card().classes("w-full max-w-lg rounded-xl shadow-sm"):
    ui.label("Leave Request").classes("text-h2 p-6 pb-0")
    ui.separator()

    with ui.column().classes("p-6 gap-4"):
        name = ui.input(label="Prefect *", placeholder="Select prefect") \ \
    .classes("w-full").props("outlined color=teal-7")
        date_val = ui.date(label="Leave Date *", value=date.today()) \ \
    .props("outlined color=teal-7")
        role = ui.select(label="Position to Cover",
            options=["Room 302", "Room 303 - 1", "Room 303 - 2"]) \ \
    .classes("w-full").props("outlined color=teal-7")
        reason = ui.textarea(label="Reason",
            placeholder="Briefly explain the reason...") \ \
    .classes("w-full").props("outlined color=teal-7 rows=3")
        has_sub = ui.checkbox("Assign substitute").props("color=teal-7")

    ui.separator()
    with ui.row().classes("w-full justify-end p-4 gap-2"):
        ui.button("Cancel", on_click=lambda: ui.notify("Cancelled.", type="info")) \ \
    .props("outline color=teal-7").classes("rounded-lg")
        btn = ui.button("Submit", on_click=submit_leave) \ \
    .props("color=teal-7").classes("rounded-lg")
```

---

## 19. Error Handling & Feedback Flow

良好的錯誤處理能大幅提升使用者體驗與信任感。

### 19.1 錯誤類型與處理方式

| 錯誤類型           | 顯示位置         | 處理方式 |
|--------------------|------------------|----------|
| 欄位驗證錯誤       | 欄位下方         | 紅色邊框 + 清楚錯誤訊息 |
| 表單提交失敗       | 表單頂部或 Toast | 顯示具體原因與建議操作 |
| 系統錯誤           | Toast + Console  | 顯示友善訊息，記錄詳細錯誤 |
| 權限不足           | Modal 或 Toast   | 清楚說明無權限原因 |
| 網路 / 連線錯誤    | Toast            | 提示使用者檢查網路並重試 |

### 19.2 錯誤訊息撰寫原則

- 使用正面、行動導向的語言（例如：「請輸入有效的學號」而非「學號格式錯誤」）。
- 避免技術術語（例如不要出現 "500 Internal Server Error"）。
- 重要錯誤應提供「重試」或「聯絡管理員」等行動按鈕。

### 19.3 成功回饋

- 新增 / 修改 / 刪除成功後，應顯示明確的成功 Toast。
- 重要操作可搭配短暫的頁面提示或動畫。
- 盡量讓使用者知道「接下來會發生什麼」。

---

## 20. Print & PDF Export Guidelines

PDF 輸出是值班排班系統的重要功能，應確保輸出的文件**清晰、專業、實用**。

### 20.1 PDF 設計原則

- 使用 **A4 直向** 作為主要格式。
- 保留足夠的邊界（至少 1.5cm）。
- 使用清晰的字體與足夠的字體大小（正文建議 11–12pt）。
- 標題使用較大字體並加粗。
- 表格應有清楚的標題列與適當的行高。
- 避免使用淺色背景或低對比顏色（列印時可能看不清）。

### 20.2 推薦內容結構（值班表 PDF）

1. **頁首**：系統名稱 + 標題 + 日期範圍
2. **摘要資訊**（選填）：總值班人次、負責人等
3. **主要表格**：值班日期、時間、負責人、備註
4. **頁尾**：產生日期 + 頁碼 + 「Sing Yin Secondary School Study Prefect Team」

### 20.3 技術建議

- 使用專業的 PDF 產生庫（例如 WeasyPrint、ReportLab、或 NiceGUI 內建 PDF 功能）。
- 確保中英文混排時字體正確嵌入。
- 提供「預覽」功能，讓使用者在下載前確認內容。
- 重要文件可加上浮水印或頁首頁尾資訊。

---

## 21. User Onboarding & First-Time Experience

新使用者（尤其是新任值班 prefect）初次使用系統時，應有良好的引導體驗。

### 21.1 Onboarding 原則

- **漸進式揭露**：不要一次顯示所有功能，先讓使用者完成核心任務（查看 / 申請值班）。
- ** contextual 提示**：在功能旁邊提供輕量提示，而非強制教學。
- **Empty State 引導**：當沒有數據時，提供清楚的下一步建議。
- **可跳過**：新手引導應可隨時跳過或關閉。

### 21.2 推薦 Onboarding 元素

- 首次登入時顯示簡短歡迎訊息 + 核心功能介紹。
- 在重要功能旁邊使用 **Tooltip** 或 **Help Icon**。
- 提供「快速開始」卡片（例如「如何申請值班」）。
- 在設定頁面提供「重新觀看引導」選項。

### 21.3 空狀態（Empty State）設計

當沒有數據時，應提供：
- 清楚的說明文字
- 建議的下一步行動（按鈕）
- 輕鬆、正面的語氣

範例：「目前沒有值班記錄。點擊「申請值班」開始你的第一次值班。」

---

## 22. Permission Management Guidelines

權限管理應讓管理者清楚、使用者安心。

### 22.1 權限設計原則

- **最小權限原則**：使用者只擁有完成工作所需的最小權限。
- **清楚的視覺回饋**：使用者應能清楚知道自己有哪些權限。
- **重要操作需確認**：刪除、修改全體設定等高風險操作應有確認步驟。
- **權限變更需通知**：當使用者權限被調整時，建議通知相關使用者。

### 22.2 角色層級建議（Sing Yin Study Prefect）

| 角色                        | 可查看          | 可申請值班     | 可管理自己值班 | 可管理他人值班 | 可設定系統     |
|-----------------------------|-----------------|----------------|----------------|----------------|----------------|
| **Head Study Prefect**      | 全部            | ✓              | ✓              | ✓              | ✓              |
| **Assistant Head Prefect**  | 全部            | ✓              | ✓              | 部分           | -              |
| **Study Prefect**           | 自己 + 公開     | ✓              | ✓              | -              | -              |

### 22.3 權限視覺呈現

- 使用 **Badge** 清楚顯示目前角色。
- 無權限的功能應顯示為 Disabled（而非直接隱藏）。
- 重要頁面或功能可加上權限說明文字。

---

## 23. Notification System Guidelines

通知系統應幫助使用者及時掌握重要資訊，而不造成干擾。

### 23.1 通知類型與使用時機

| 通知類型       | 元件          | 使用時機                           | 持續時間     |
|----------------|---------------|------------------------------------|--------------|
| 成功           | Toast         | 操作成功（新增、修改、刪除）       | 3–4 秒       |
| 錯誤           | Toast         | 操作失敗或系統錯誤                 | 直到關閉     |
| 警告           | Toast / Banner| 重要提醒（例如值班即將到期）       | 5 秒或手動   |
| 資訊           | Banner        | 系統公告、維護通知                 | 手動關閉     |

### 23.2 Toast 設計原則

- 位置：畫面右上角（桌面）或底部（行動裝置）。
- 最多同時顯示 3 則通知。
- 重要通知（錯誤、警告）應可手動關閉。
- 成功通知可自動消失。
- 使用語義色（綠色成功、紅色錯誤、黃色警告、藍色資訊）。

### 23.3 Banner 設計原則

- 用於較重要且持久的訊息（例如系統維護公告）。
- 應有清楚的關閉按鈕。
- 可使用不同背景色區分重要程度。

---

## 24. Audit Log & Activity History Design

Audit Log 讓管理者能追蹤系統中的重要操作，提升透明度與 accountability。

### 24.1 Audit Log 設計原則

- 記錄應清楚、易讀、不可篡改。
- 重要操作（新增、修改、刪除值班、權限變更）必須記錄。
- 記錄應包含：時間、操作者、操作類型、影響對象、詳細內容。
- 提供搜尋與篩選功能（依日期、使用者、操作類型）。

### 24.2 視覺呈現建議

- 使用 **Timeline** 樣式呈現（由新到舊）。
- 每筆記錄使用卡片或列表項目。
- 重要操作可使用不同顏色或圖示區分（例如刪除使用紅色）。
- 提供「查看詳細」功能（展開顯示完整資訊）。

### 24.3 推薦欄位

| 欄位           | 說明                     |
|----------------|--------------------------|
| 時間           | 操作發生的精確時間       |
| 使用者         | 執行操作的使用者名稱     |
| 角色           | 執行者的角色（Badge）    |
| 操作類型       | 新增 / 修改 / 刪除 / 登入 |
| 目標對象       | 被影響的值班 / 使用者    |
| 詳細內容       | 變更前後的摘要           |
| IP / 裝置      | 可選（提升安全性）       |

---

## 25. Multi-language & Localization Guidelines

雖然本系統主要使用繁體中文，但仍需考慮基本的多語言與在地化支援。

### 25.1 語言策略

- **主要語言**：繁體中文（香港常用字詞）
- **次要語言**：英文（用於技術術語、按鈕、系統訊息）
- **目前不支援**：簡體中文、日文等其他語言（除非未來有明確需求）

### 25.2 設計原則

- 所有使用者介面文字應支援中英文切換（即使目前只提供繁體中文）。
- 技術名詞建議保留英文（例如 "Dashboard", "Audit Log"），並在首次出現時提供中文說明。
- 日期、時間、數字格式應遵循香港習慣（例如日期格式 DD/MM/YYYY）。
- 錯誤訊息與系統提示應提供清晰的繁體中文。

### 25.3 實作建議

- 使用語言檔案（JSON / YAML）管理文字內容。
- 元件文字應從語言檔案讀取，而非硬編碼。
- 預留空間給較長的英文翻譯（英文通常比中文長）。

---

## 26. Help & Documentation Center

提供使用者自助查詢的功能，能大幅降低支援需求。

### 26.1 推薦內容

- **快速開始指南**：新使用者如何申請值班、查看自己的值班記錄。
- **常見問題（FAQ）**：最常遇到的問題與解答。
- **功能說明**：各主要功能的詳細操作說明。
- **角色權限說明**：不同角色可以做什麼事情。
- **聯絡支援**：當無法解決問題時的聯絡方式（例如電郵給 Head Study Prefect）。

### 26.2 呈現方式

- 在 Sidebar 或頂部導航提供「幫助」入口。
- 使用 **Accordion** 或 **Searchable List** 呈現 FAQ。
- 重要頁面可直接連結到相關說明文件。
- 提供「回報問題」按鈕，直接開啟回饋表單。

---

## 27. Loading States & Skeleton Screens

良好的 Loading 體驗能讓使用者感覺系統快速且專業。

### 27.1 Loading 類型

| 類型               | 使用時機                     | 推薦元件          |
|--------------------|------------------------------|-------------------|
| 全頁 Loading       | 初始頁面載入                 | Spinner + 文字    |
| 區塊 Loading       | 特定區域數據更新             | Spinner + 遮罩    |
| 按鈕 Loading       | 表單提交、重要操作           | Button 內 Spinner |
| Skeleton Screen    | 內容即將出現（推薦）         | Skeleton 結構     |

### 27.2 Skeleton Screen 設計原則

- 使用與最終內容相似的灰色區塊模擬真實內容。
- 優先使用 Skeleton 而非純 Spinner（使用者能預期內容形狀）。
- 動畫應輕微（使用 `ease-standard`）。
- 避免過度使用 Skeleton（只在必要時使用）。

### 27.3 技術建議

- NiceGUI 可使用 `ui.skeleton()` 或自訂 HTML/CSS 實現。
- 重要操作的 Loading 應顯示在按鈕上（而非全頁）。
- 長時間 Loading 應提供取消或重試選項。

---

## 12. Version History

| Version | Date       | Author      | Changes                                                                 |
|---------|------------|-------------|-------------------------------------------------------------------------|
| **4.0** | **2026-06-27** | **Codex + User** | **HyperOS Native: Deep realignment around six HyperOS pillars. Expanded Design Philosophy from 1 paragraph to full section. 5-level layered elevation system. Comprehensive Motion Design with HyperOS easing curves and duration scale. Component specs updated throughout for unmistakable HyperOS feel.** |
| **3.1** | **2026-06-24** | **Codex + User** | **HyperOS Refined: softer button rounding (14px), card rounding (20px), layered elevation, fluid motion, premium spacing.** |
| **3.0** | **2026-06-24** | **Codex + User** | **Major rewrite for NiceGUI migration. Added Phase 1 NiceGUI implementation examples for Buttons, Cards, Tables, Badges/Tags, and Modals/Dialogs. Restructured document. Fixed section numbering.** |
| 2.0     | 2026-06-20 | Grok + User | Added Multi-language, Help & Documentation Center, and enhanced Loading & Skeleton Screens (Final major version) |
| 1.9     | 2026-06-20 | Grok + User | Added Notification System Guidelines and Audit Log & Activity History Design |
| 1.8     | 2026-06-20 | Grok + User | Added User Onboarding & First-Time Experience and Permission Management Guidelines |
| 1.7     | 2026-06-20 | Grok + User | Added Form Design Guidelines, Error Handling & Feedback Flow, and Print & PDF Export Guidelines |
| 1.6     | 2026-06-20 | Grok + User | Added Data Visualization, Role & Permission Visual Distinction, and Sidebar & Navigation Guidelines |
| 1.5     | 2026-06-20 | Grok + User | Enhanced Motion Design Principles with Easing Scale + specific scene recommendations |
| 1.4     | 2026-06-20 | Grok + User | Added Motion Design Principles section                                  |
| 1.3     | 2026-06-20 | Grok + User | Added complete Dark Mode Color System with specific hex codes           |
| 1.2     | 2026-06-20 | Grok + User | Added Accessibility (WCAG 2.1 specific standards), Responsive Design, and Do's and Don'ts |
| 1.1     | 2026-06-20 | Grok + User | Added Iconography, Form Validation & Error States, Feedback Components, Empty States, and Loading States |
| 1.0     | 2026-06-20 | Grok + User | Initial release                                                         |

---

**Document Owner:** Project Lead (Li Chuang Jie)  
**Last Updated:** 2026-06-24

---

*This document is the official design reference for the Sing Yin Study Prefect Duty Roster System. All future UI work must align with it.*