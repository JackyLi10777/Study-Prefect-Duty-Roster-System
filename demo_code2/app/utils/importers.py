"""
Import Pipeline for the Sing Yin Study Prefect Duty Roster System.

Supports CSV/Excel file import with optional AI column mapping.
Integrates with the existing dual-write persistence layer (Sheets + CSV).
"""

import csv
import io
from typing import List, Dict, Optional


def parse_csv(content: str) -> tuple:
    """Parse CSV content into rows and detected column names.

    Args:
        content: Raw CSV string.

    Returns:
        (column_names: List[str], rows: List[Dict[str, str]])
    """
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        return [], []
    return list(reader.fieldnames), list(reader)


def get_sample_rows(content: str, n: int = 8) -> str:
    """Return first n rows of CSV content as a string, for AI column mapping."""
    _, rows = parse_csv(content)
    if not rows:
        return ""
    # Format as a simple text table
    lines = []
    if rows:
        cols = list(rows[0].keys())
        lines.append(",".join(cols))
        for row in rows[:n]:
            lines.append(",".join(str(row.get(c, "")) for c in cols))
    return "\n".join(lines)


def map_columns(raw_rows: List[Dict], mapping: Dict[str, str]) -> List[Dict]:
    """Apply a column mapping to raw rows, producing standardized prefect dicts.

    Args:
        raw_rows: Rows from CSV reader (raw column names).
        mapping: Dict mapping standard fields -> actual column names.
                 e.g. {"name": "Student Name", "form": "Grade"}

    Returns:
        List of standardized dicts ready for Prefect.from_dict().
    """
    # Invert mapping: actual_col -> standard_col
    inv = {v.strip().lower(): k for k, v in mapping.items() if v}
    result = []
    for row in raw_rows:
        std_row = {}
        for actual_col, value in row.items():
            std_key = inv.get(actual_col.strip().lower(), actual_col.strip().lower())
            std_row[std_key] = value
        result.append(std_row)
    return result


def smart_import(content: str) -> Optional[List[Dict]]:
    """AI-powered import: detect columns, map, and return standardized rows.

    Args:
        content: Raw CSV string.

    Returns:
        List of standardized dicts, or None if AI is unavailable.
    """
    from services.ai_parser import get_column_mapping_from_ai, is_available
    if not is_available():
        return None
    sample = get_sample_rows(content)
    if not sample:
        return None
    mapping = get_column_mapping_from_ai(sample)
    if not mapping:
        return None
    _, raw_rows = parse_csv(content)
    return map_columns(raw_rows, mapping)


def validate_import_rows(rows: List[Dict]) -> tuple:
    """Validate imported rows and return (valid_rows, errors).

    Checks: name is required, form is valid, role is valid.
    """
    valid = []
    errors = []
    valid_forms = {"F3", "F4", "F5", "F6"}
    valid_roles = {"STUDY_PREFECT", "ASSISTANT_HEAD_PREFECT", "ASSISTANT HEAD PREFECT",
                   "HEAD_STUDY_PREFECT", "HEAD STUDY PREFECT"}
    for i, row in enumerate(rows):
        name = str(row.get("name", "")).strip()
        if not name:
            errors.append(f"Row {i+1}: missing name, skipped.")
            continue
        form_raw = str(row.get("form", "")).strip().upper()
        if form_raw not in valid_forms:
            errors.append(f"Row {i+1} ({name}): invalid form '{form_raw}', set to F4.")
            row["form"] = "F4"
        role_raw = str(row.get("role", "")).strip().upper()
        # Validate class_name
        if not str(row.get("class_name", "")).strip():
            errors.append(f"Row {i+1} ({name}): missing class, set to '-'.")
            row["class_name"] = "-"

        if "ASSISTANT" in role_raw or "AHP" in role_raw:
            row["role"] = "ASSISTANT_HEAD_PREFECT"
        elif "HEAD" in role_raw:
            row["role"] = "HEAD_STUDY_PREFECT"
        else:
            row["role"] = "STUDY_PREFECT"
        # Set defaults
        row.setdefault("history_weight", 0.0)
        row.setdefault("active", True)
        row.setdefault("remarks", "")
        row.setdefault("available", "")
        valid.append(row)

    # Detect duplicate names (case-insensitive) and keep only first occurrence
    seen = set()
    deduped = []
    dedup_errors = []
    for v in valid:
        name_lower = v["name"].strip().lower()
        if name_lower in seen:
            dedup_errors.append(f"Duplicate name '{v["name"]}' skipped (first occurrence kept).")
        else:
            seen.add(name_lower)
            deduped.append(v)
    valid[:] = deduped
    errors = dedup_errors + errors

    return valid, errors


COLUMN_ALIASES = {
    "name": ["name", "full name", "student name", "prefect name"],
    "name_zh": ["name_zh", "chinese name"],
    "form": ["form", "grade", "year"],
    "class_name": ["class_name", "class", "classroom"],
    "role": ["role", "position"],
    "available": ["available", "available_days", "available days"],
    "history_weight": ["history_weight", "weight", "load", "points"],
    "remarks": ["remarks", "notes"],
    "fixed_general_duty": ["fixed_duty", "fixed"],
    "active": ["active", "status"],
}


def normalize_column_name(col: str) -> str:
    """Map a column name to a standard field name using alias matching."""
    col_lower = col.strip().lower()
    for std_name, aliases in COLUMN_ALIASES.items():
        if col_lower in [a.lower() for a in aliases]:
            return std_name
    return col


def auto_detect_columns(raw_columns: list) -> dict:
    """Auto-detect column mapping without AI (alias-based fallback)."""
    mapping = {}
    for col in raw_columns:
        std = normalize_column_name(col)
        if std != col:
            mapping[std] = col
    return mapping



def compute_mapping_with_confidence(raw_columns: list, sample_text: str = "") -> list:
    ai_mapping = {}
    if sample_text:
        try:
            from services.ai_parser import get_column_mapping_with_confidence
            ai_mapping = get_column_mapping_with_confidence(sample_text)
        except Exception:
            ai_mapping = {}
    alias_mapping = auto_detect_columns(raw_columns)
    alias_inv = {v.strip().lower(): k for k, v in alias_mapping.items()}
    result = []
    for col in raw_columns:
        col_stripped = col.strip()
        entry = {"source_col": col_stripped, "target": None, "confidence": "none", "source": "none"}
        ai_target = None
        for std_field, mapped_col in ai_mapping.items():
            if mapped_col.strip().lower() == col_stripped.lower():
                ai_target = std_field
                break
        if ai_target:
            entry["target"] = ai_target
            entry["confidence"] = "ai"
            entry["source"] = "ai"
        elif col_stripped.lower() in alias_inv:
            entry["target"] = alias_inv[col_stripped.lower()]
            entry["confidence"] = "alias"
            entry["source"] = "alias"
        result.append(entry)
    return result


def get_preview_rows(content: str, mapping: dict, n: int = 5) -> list:
    _, raw_rows = parse_csv(content)
    return map_columns(raw_rows[:n], mapping)
