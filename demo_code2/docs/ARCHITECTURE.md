"""
Architecture Decision Record for Sing Yin Study Prefect Duty Roster System
===========================================================================
This document records WHY key design decisions were made. For WHAT the system
does, see HANDOVER.md. For HOW to use it, see USER_GUIDE_ZH.md.

Intended audience: Future Head Study Prefects and system maintainers.
Reading time: 10 minutes.
"""

# Architecture Decision Record (ADR)

**Version:** 1.0
**Date:** 2026-07-01
**Author:** LI Chuangjie (Head Study Prefect 26-27)

---

## 1. Why 7 Layers (not 3 or 10)?

The system is organized into 7 distinct layers:

```
app/
├── main.py          ← Entry point + route registration
├── theme/           ← Design tokens + CSS generation + theme switching
├── i18n/            ← Hard rules (prefect names) + language helpers + switching
├── components/      ← Reusable UI pieces (sidebar, KPI cards, loading states)
├── pages/           ← Full-page compositions (Dashboard, Roster, Prefects...)
├── services/        ← Business logic (roster generation, leave, AI, fairness)
├── utils/           ← Infrastructure (Sheets, PDF, backup, audit, data)
└── models/          ← Data structures (enums, Prefect, WeeklyRoster)
```

**Decision:** 7 layers instead of a simpler 3-layer (MVC) or flatter structure.

**Rationale:**
- **services/ vs utils/** — Business logic (services/) changes when school rules change.
  Infrastructure (utils/) changes when external dependencies change. These have
  different change velocities, so separating them reduces regression risk.
- **components/ vs pages/** — Components (sidebar, KPI cards) are reused across
  pages. Pages are full compositions. Separating them prevents circular imports
  and keeps components independently testable.
- **theme/ and i18n/** — Extracted from a monolithic theme.py during Phase 1
  refactoring. Centralization prevents scattered color/text changes across 30+
  files. The hard rule in i18n/rules.py (prefect names always Chinese) is
  enforced at the module boundary — no page can accidentally bypass it.

**Trade-off:** More files = more navigation. Mitigated by consistent naming
conventions and this ADR document.

---

## 2. Why theme.py AND theme/ Coexist?

**Decision:** Keep both `app/theme.py` (legacy) and `app/theme/` (new package).

**Rationale:**
- All `@ui.page` handlers import from `theme` (the legacy module) using
  `from theme import apply_theme, ...`. Changing 5+ pages simultaneously
  would risk structural regressions (we had 3+ SyntaxErrors during previous
  edits).
- The new `app/theme/` package (tokens.py, css.py, provider.py) is the
  canonical source. The legacy module delegates to it.
- During Phase 2, we attempted to delete `app/theme/__init__.py` to resolve
  an import conflict — this proved that the dual structure is fragile and
  should be preserved until a coordinated migration.

**Future path:** When someone has time to update all 5 pages simultaneously
(with careful testing), `theme.py` can become a thin shim that re-exports
`from theme.provider import *`.

---

## 3. Why Prefect Names MUST Always Be Chinese?

**Decision:** `i18n/rules.py::prefect_display_name()` ALWAYS returns `name_zh`,
regardless of language mode. This is non-negotiable.

**Rationale:**
- School policy: prefects are known by their Chinese names within the school.
- The English name field exists for data management (matching with CSV/Sheets)
  but must never appear in the UI or PDF exports.
- During the Streamlit-to-NiceGUI migration, this rule was temporarily lost
  (names were switching between zh/en). Re-implementing it as a hard rule in
  a centralized module prevents future regression.

**Enforcement:** The rule is implemented in exactly ONE place (`i18n/rules.py`).
All pages call `prefect_display_name()` — never directly access `name` or
`name_zh`. This means if the rule needs to change in the future, only one
line of code needs to be modified.

---

## 4. Where Do School Rules Live?

**Decision:** School rules are centralized in `models/enums.py::SchoolRules`
and `models/enums.py::Room`. No other file defines capacity or closure rules.

**Rationale:**
- During the migration, room capacities appeared in 3 different files
  (engine.py, roster_service.py, models/enums.py). This caused a bug where
  Room 202 was sometimes open on Tuesdays.
- Centralizing all constraints in one class makes it easy to audit and modify.

**How to add a new room:**
1. Add to `Room` enum in `models/enums.py`
2. Set capacity in `Room.capacity` property
3. Set closed days in `Room.closed_days` property
4. Update `SchoolRules.TOTAL_ORDINARY_SLOTS_PER_DAY`
No other files need modification.

---

## 5. Why Google Sheets Has Retry Logic?

**Decision:** `utils/sheets.py::_retry_with_backoff()` wraps all API calls
with exponential backoff (1s/2s/4s, 3 retries).

**Rationale:**
- The school's WiFi can be unstable. Without retry, a transient network
  glitch would silently return None and the system would fall back to CSV,
  losing the Sheets sync advantage.
- Each retry is logged to the audit system, so future maintainers can see
  when and why retries occurred.

---

## 6. Why HyperOS v5.0 CSS Is Injected at Runtime?

**Decision:** CSS is generated by `theme/css.py::generate_hyperos_css()` and
injected via `ui.add_head_html()` on every page load.

**Rationale:**
- NiceGUI does not support external CSS files cleanly.
- Injecting at runtime allows the CSS to reference Python constants from
  `theme/tokens.py` (e.g., PRIMARY color, glass blur radius).
- The CSS is pure — no JavaScript, no external dependencies. This means it
  works even if the school network blocks CDN resources.

**Trade-off:** The CSS block is ~90 lines embedded in a Python string. This
makes it harder to edit than a standalone `.css` file. Mitigated by extracting
it to `theme/css.py` (Phase 3) so it's isolated from other theme logic.

---

## 7. Key Change Events (For Future Reference)

| Date | Event | Impact |
|------|-------|--------|
| 2026-06-24 | Streamlit → NiceGUI migration | Entire UI layer rewritten |
| 2026-06-27 | Theme tokens stabilized | Replaced fragile theme.xxx with direct Tailwind classes |
| 2026-06-27 | Multi-page architecture | Sidebar + 6 pages with shared layout |
| 2026-06-27 | i18n centralized | Hard rule for prefect names enforced |
| 2026-07-01 | 5-Phase refactoring | Created theme/, i18n/, components/ packages |
| 2026-07-01 | Sheets retry logic | Exponential backoff for API calls |
| 2026-07-01 | GROK_PROMPTS.md v2.6 | 4 iterations of prompt optimization |

---

*This ADR should be updated whenever a significant architectural decision is made.
Future Head Study Prefects: add your decisions here so the next person understands
why things are the way they are.*
