# ADR 0002: Session State Management Improvements

**Date:** 2026-06-19
**Status:** Accepted

## Context

The Sing Yin Study Prefect Duty Roster System is deployed on Streamlit Cloud, a stateless
environment where all application state lives in `st.session_state`. Prior to this refactoring:

- `st.session_state` was accessed directly across `app.py` (~107 unique line references)
  and `roster/ui/components.py` (~85 unique line references).
- 27 distinct keys were managed with no centralized listing, type validation, or accessor pattern.
- After PDF backup restore operations, there was no validation that the restored state was
  complete and correctly typed.
- Roster-dependent caches (PDF caches, search terms, version history) were cleared individually
  at different sites, creating risk of inconsistent state.
- A typo in a key name (e.g., `st.session_state.roster_d`) would silently create a new key
  with no error.

## Decision

We added four lightweight helper functions to `roster/data/state.py` rather than introducing
a full StateManager class or Pydantic-based state model.

The helpers are:

1. **`get_state(key, default=None)`** — Thin wrapper around `st.session_state.get()` that
   returns a specified default instead of `None` for missing keys. Does not silently create keys.

2. **`set_state(key, value)`** — Future-proofing single write point. Currently a thin wrapper
   around `st.session_state[key] = value`, but can be extended with type validation, change
   auditing, or mutation logging.

3. **`reset_roster_related_state()`** — Atomically clears all roster-dependent keys (roster_df,
   master_report_df, pdf_cache_zh/en, roster_search, roster_versions, _pdf_needs_generation).
   Does not clear persistent settings (students_df, theme, ui_language, logo_data).

4. **`validate_state_integrity()`** — Checks 12 required session_state keys exist and have
   expected types. Raises `StateIntegrityError` (from `roster/exceptions.py`) with a list of
   issues when problems are found. Called after PDF backup restore operations.

**Why thin helpers instead of a StateManager class:**
- Streamlit's `st.session_state` is already a dict-like object with session-scoped persistence.
  Wrapping it in a full class would add indirection without meaningful benefit at this project's
  scale (27 keys, 2 main files).
- Thin helpers are immediately usable without refactoring existing code. Migration is gradual.
- A full StateManager would require defining every key as a typed attribute, which would be
  valuable in a larger application but overkill here.

## Consequences

**Positive:**
- PDF backup restore now validates state integrity and warns users of issues.
- Clearing the roster also atomically clears all related caches.
- Future validation logic (type checking, change auditing) has a single insertion point.
- The 27-key state is now documented in `validate_state_integrity()`'s required dict.

**Negative:**
- Still maintains two patterns (direct `st.session_state` access + helper functions).
  Full migration to helpers-only was intentionally deferred to avoid risk.
- `get_state` and `set_state` import `streamlit` inside the function body to avoid
  module-level dependency — this is slightly unusual but matches the project's pattern.

**Neutral:**
- The direct `st.session_state` access pattern remains for ~90% of accesses. Gradual
  migration to helpers is expected over future iterations.

