"""roster.data - Data layer.

- Demo data
- Session state initialization (Cloud hibernation guard)
- Validation
- Models / schemas / reindex utilities

All original functions from data.py are re-exported for compatibility.
"""

from .demo import get_demo_dataframe, get_sample_format_dataframe
from .state import get_empty_students_df, initialize_session_state
from .validators import validate_students_dataframe
from .models import (
    reindex_roster_df,
    get_roster_index,
    get_days,
    STUDENT_COLUMNS,
)

# For backward compatibility with code that did "from data import ROWS_ROSTER" etc.
# (these now come via roster.config, but we can re-export here too if needed)
from roster.config import ROWS_ROSTER, DAYS, DEFAULT_GLOBAL_LOAD_MULTIPLIER
