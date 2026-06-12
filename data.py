# data.py (root shim / compatibility layer)
"""
Temporary root-level shim for the modular refactor (see approved plan.md).

All existing `from data import get_demo_dataframe, initialize_session_state, ...`
continue to work unchanged.

The real data layer is now at:
    roster/data/
    (demo.py, state.py, validators.py, models.py)

initialize_session_state and demo data are 100% unchanged.
This file will be cleaned up in the final phase after full verification.
"""
from roster.data import (
    get_demo_dataframe,
    get_sample_format_dataframe,
    get_empty_students_df,
    initialize_session_state,
    validate_students_dataframe,
    reindex_roster_df,
    get_roster_index,
    get_days,
    STUDENT_COLUMNS,
)

# Re-export config constants that the original data.py exposed for convenience
from roster.config import ROWS_ROSTER, DAYS, DEFAULT_GLOBAL_LOAD_MULTIPLIER

print("✅ [shim] root data.py now forwards to roster.data (functionality identical)")
