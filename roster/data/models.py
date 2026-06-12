# roster/data/models.py
"""
Data models, schemas, and utility helpers for DataFrames.

Centralizes reindexing logic (per AGENTS.md and project-structure-advisor) to enforce the invariant:
"Roster is always indexed by get_roster_rows() and columns DAYS".

Provides bilingual helpers for UI (Chinese) vs Export (professional English) per strict user requirements:
- Streamlit UI remains fully in Chinese for student usability.
- All exported files (PDF, Excel, Markdown, Audit) use professional English.
- Student name *values* remain in original Chinese in exports.

Added comprehensive type hints and docstrings for code-documentation and testability.
"""

import pandas as pd
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


def get_days() -> list[str]:
    """Return the canonical list of days."""
    return list(DAYS)


def create_empty_roster_df() -> pd.DataFrame:
    """Create a fresh empty roster DataFrame with proper index/columns (for resets, tests, etc.).
    Uses declarative get_roster_rows for maintainability.
    """
    return pd.DataFrame(index=get_roster_rows(), columns=get_days()).fillna("")


# Bilingual column mapping for UI (Chinese) vs Exports (professional English)
# Per project rules: UI keeps Chinese for students; exports use English but preserve Chinese student names as values.
UI_REPORT_COLUMNS = ["學生姓名", "年級", "班別", "職級", "當週新增 (點)", "累計加權負荷 (點)"]
EXPORT_REPORT_COLUMNS = ["Student Name", "Form", "Class", "Role", "This Week Added (points)", "Cumulative Weighted Load (points)"]


def get_ui_report_df(report_df):
    """Return a copy with Chinese columns for Streamlit UI display (keeps Chinese interface)."""
    if report_df.empty:
        return pd.DataFrame(columns=UI_REPORT_COLUMNS)
    display = report_df.copy()
    if len(display.columns) == len(UI_REPORT_COLUMNS):
        display.columns = UI_REPORT_COLUMNS
    return display


def get_export_report_df(report_df):
    """Return a copy with professional English columns for PDF/Excel/MD exports.
    Student name values remain in original Chinese (as per rules)."""
    if report_df.empty:
        return pd.DataFrame(columns=EXPORT_REPORT_COLUMNS)
    export = report_df.copy()
    if len(export.columns) == len(EXPORT_REPORT_COLUMNS):
        export.columns = EXPORT_REPORT_COLUMNS
    return export
