"""Current prefect schema adapter; the editor protocol itself has no role rules."""

from collections.abc import Mapping

from roster_policy import SchoolDay
from nicegui_app.ui.person_editor_state import EditorSnapshotRejected


PREFECT_EDITOR_SCHEMA = "prefect-inline-v1"
INLINE_FIELDS = ("nameEn", "form", "className", "availableDays", "needsMentoring", "remarks")


def prefect_editor_values(row: Mapping[str, object]) -> dict[str, object]:
    fields = (*INLINE_FIELDS, "fixedGeneralDuty") if row["roleCode"] == "assistant_head" else INLINE_FIELDS
    return {field: row[field] for field in fields}


def validate_prefect_editor_values(values: Mapping[str, object]) -> dict[str, object]:
    """Validate packet shape, not all business rules; incomplete input stays buffered."""
    result = dict(values)
    allowed = {*INLINE_FIELDS, "fixedGeneralDuty"}
    if set(values) - allowed or not set(INLINE_FIELDS).issubset(values):
        raise EditorSnapshotRejected("Unknown editable field.")
    for key in ("form", "className", "remarks", "fixedGeneralDuty"):
        if key in values and not isinstance(values[key], str):
            raise EditorSnapshotRejected("Invalid text value.")
    if not isinstance(values["nameEn"], (str, type(None))):
        raise EditorSnapshotRejected("Invalid name value.")
    if type(values["needsMentoring"]) is not bool:
        raise EditorSnapshotRejected("Invalid support value.")
    days = values["availableDays"]
    valid_days = {day.name for day in SchoolDay}
    if not isinstance(days, list) or any(not isinstance(day, str) or day not in valid_days for day in days):
        raise EditorSnapshotRejected("Invalid weekday value.")
    result["nameEn"] = result["nameEn"] or None
    result["availableDays"] = [day.name for day in SchoolDay if day.name in days]
    return result
