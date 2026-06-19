# ADR 0001: Introduce School Policy Module

**Date:** 2026-06-19
**Status:** Accepted

## Context

The Sing Yin Study Prefect Duty Roster System must enforce specific Sing Yin Secondary School
rules during roster generation. These include:

- AHP (Assistant Head Study Prefect) restrictions: only AHPs may staff "Assist. in charge" slots,
  and AHPs are forbidden from all other rooms.
- Room 202 closure: Room 202 is closed on Tuesday and Friday (F.1 students have other activities).
- Weight system: Room 302 = 1.0, Room 303/202 = 1.5, Assist = 1.0.
- Mentoring thresholds: students with history_weight <= 2.0 are auto-tagged as mentees;
  students with history_weight > 5.0 qualify as mentors.
- No consecutive days: a student cannot be scheduled on back-to-back days.
- AHP load bonus: AHP students receive -8.0 bonus for Assist slots, prioritizing them for
  leadership positions.

Prior to this refactoring, these rules were scattered across multiple files:
- `roster/config/constants.py` contained room configurations, weights, and availability.
- `roster/core/engine.py` contained mentoring thresholds (`_MENTEE_THRESHOLD`, `_MENTOR_THRESHOLD`,
  `_MENTORING_PAIR_BONUS`) as private module-level constants.
- Some rules (like no-consecutive-days) were only documented in comments, not as named constants.

This scattering created risk: a future maintainer could modify a rule in one location without
realizing it was also referenced elsewhere, or hardcode a rule value in a new function without
knowing the canonical definition exists.

## Decision

We created `roster/config/school_policy.py` as the **Single Source of Truth (SSOT)** for all
Sing Yin school-specific scheduling rules.

The module centralizes:
- Room configurations (capacity, weight, available weekdays, AHP-only flag)
- Mentoring thresholds (MENTEE_THRESHOLD, MENTOR_THRESHOLD, MENTORING_PAIR_BONUS)
- AHP_LOAD_BONUS
- NO_CONSECUTIVE_DAYS flag
- Helper functions: `get_weight()`, `is_assistant_head_only_role()`,
  `is_room_open_on_weekday()`, `get_daily_slots()`

Each rule includes a documented rationale explaining its origin (e.g., "Room 202 is closed
on Tue/Fri because F.1 students have other scheduled activities").

`roster/config/constants.py` now imports and re-exports everything from `school_policy.py`,
preserving backward compatibility for all existing `from roster.config import ...` statements.

## Consequences

**Positive:**
- Any future rule change requires editing only one file (`school_policy.py`).
- Each rule has a documented rationale, reducing ambiguity for future Head Study Prefects.
- New developers can discover all school rules by reading one ~75-line module.
- The mentoring thresholds are now importable constants rather than private module-level variables.

**Negative:**
- Introduces a new module in the `roster/config/` package — slight increase in project surface area.
- `school_policy.py` has a lazy import of `get_base_role` from `constants.py` inside
  `get_daily_slots()` to avoid circular imports. This pattern must be maintained.

**Neutral:**
- `constants.py` remains 300+ lines due to NASA_COLORS, GEMINI_MODEL, verse data, and
  legacy shims. Future work could further extract non-policy config into separate modules.

