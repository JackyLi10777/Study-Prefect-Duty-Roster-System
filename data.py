# data.py (root shim / compatibility layer)
"""
Ultra-thin root-level compatibility shim.

Legacy `from data import ...` still work.

**Recommendation:** New code should use `from roster.data import ...` and `from roster.data.models import ...`.

Real implementation: roster/data/ (demo, state, models with bilingual export/UI helpers).
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

from roster.config import ROWS_ROSTER, DAYS, DEFAULT_GLOBAL_LOAD_MULTIPLIER

print("✅ [shim] root data.py → roster.data (thin compat)")
