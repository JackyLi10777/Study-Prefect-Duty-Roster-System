# roster/data/models.py
"""
Data models, schemas, and utility helpers for DataFrames.

Centralizes reindexing logic (per plan) to enforce the invariant:
"Roster is always indexed by ROWS_ROSTER and columns DAYS".

Added during modularization; does not change existing behavior.
"""

from roster.config import get_roster_rows, DAYS


# Common column lists for reference / validation
STUDENT_COLUMNS = [
    "name", "form", "class", "role",
    "fixed_general_duty", "available",
    "history_duties", "history_weight", "remarks"
]


def reindex_roster_df(df):
    """Ensure roster DataFrame has correct index and columns (idempotent).
    Now uses declarative get_roster_rows() from config (Phase 2 declarative slot config).
    """
    return df.reindex(index=get_roster_rows(), columns=DAYS).fillna("")


def get_roster_index():
    """Return the canonical roster row index.
    Now uses declarative get_roster_rows() from config.
    """
    return list(get_roster_rows())


def get_days():
    """Return the canonical list of days."""
    return list(DAYS)
