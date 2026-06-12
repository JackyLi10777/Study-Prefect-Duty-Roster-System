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
from ..config import get_roster_rows, DAYS


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


def get_ui_report_df(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame suitable for UI display in Streamlit (Chinese column names).

    - Column headers are in Chinese for student/leader friendliness in the web UI.
    - Data content (including student names) is preserved as-is.
    - Columns are ordered for readability.
    - If input is empty (or None), returns an empty DataFrame with the UI columns.
    """
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame(columns=UI_REPORT_COLUMNS)

    # Internal engine always produces English keys; map to Chinese for display.
    # Using rename is robust to order / partial matches.
    ui_map = {
        "Student Name": "學生姓名",
        "Form": "年級",
        "Class": "班別",
        "Role": "職級",
        "This Week Added (points)": "當週新增 (點)",
        "Cumulative Weighted Load (points)": "累計加權負荷 (點)",
    }
    display = df.copy()
    display = display.rename(columns={k: v for k, v in ui_map.items() if k in display.columns})

    # Enforce desired column ordering (UI cols first, then any extras)
    ordered = [c for c in UI_REPORT_COLUMNS if c in display.columns]
    remaining = [c for c in display.columns if c not in ordered]
    if ordered:
        display = display[ordered + remaining]
    return display


def get_export_report_df(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame suitable for professional English exports (PDF/Excel/Markdown).

    - Column headers use clean professional English.
    - Student name *values* remain in their original Chinese (never translated).
    - Suitable for official reports and external sharing.
    - If input is empty (or None), returns an empty DataFrame with the export columns.
    """
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame(columns=EXPORT_REPORT_COLUMNS)

    # Source is typically already English (from engine.validate_and_compute).
    # Provide reverse map in case a Chinese-labeled DF is passed in (legacy/restore edge case).
    reverse_map = {
        "學生姓名": "Student Name",
        "年級": "Form",
        "班別": "Class",
        "職級": "Role",
        "當週新增 (點)": "This Week Added (points)",
        "累計加權負荷 (點)": "Cumulative Weighted Load (points)",
    }
    export = df.copy()
    export = export.rename(columns={k: v for k, v in reverse_map.items() if k in export.columns})

    # Enforce canonical export column order
    ordered = [c for c in EXPORT_REPORT_COLUMNS if c in export.columns]
    remaining = [c for c in export.columns if c not in ordered]
    if ordered:
        export = export[ordered + remaining]
    return export
