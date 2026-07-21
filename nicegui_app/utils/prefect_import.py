"""Safe local parsing for AI-prepared or CSV prefect imports."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import io
import json
import re
from typing import Any

from nicegui_app.services.roster_workflow import PrefectInput
from nicegui_app.utils.prefect_import_limits import (
    PrefectImportLimitError,
    check_import_bytes,
    check_import_cell,
    check_import_column_count,
    check_import_row_count,
    check_json_nesting,
    validate_import_headers,
)
from roster_policy import is_chinese_display_name


@dataclass(frozen=True)
class ImportPreview:
    rows: tuple[PrefectInput, ...]
    issues: tuple[str, ...]


FIELD_ALIASES = {
    "name_zh": ("name_zh", "name", "姓名", "中文姓名", "風紀姓名"),
    "form": ("form", "級別", "年級"),
    "class_name": ("class", "class_name", "班別", "班級"),
    "role": ("role", "職務", "職位"),
    "available_days": ("available_days", "available", "可值班日", "可用日"),
    "remarks": ("remarks", "備註"),
}

DAY_ALIASES = {
    "MONDAY": "MONDAY",
    "星期一": "MONDAY",
    "週一": "MONDAY",
    "TUESDAY": "TUESDAY",
    "星期二": "TUESDAY",
    "週二": "TUESDAY",
    "WEDNESDAY": "WEDNESDAY",
    "星期三": "WEDNESDAY",
    "週三": "WEDNESDAY",
    "THURSDAY": "THURSDAY",
    "星期四": "THURSDAY",
    "週四": "THURSDAY",
    "FRIDAY": "FRIDAY",
    "星期五": "FRIDAY",
    "週五": "FRIDAY",
}


def prefect_import_template_csv() -> bytes:
    """Return a fictional, Traditional-Chinese CSV example for safe local import practice."""
    return (
        "\ufeff姓名,級別,班別,職務,可值班日,備註\n"
        "範例風紀甲,F.3,3A,導學風紀,星期一、星期三、星期五,請以本校資料取代此示例\n"
        "範例風紀乙,F.5,5B,助理首席導學風紀,星期二、星期四,助理首席只可安排 Assist. in charge\n"
    ).encode("utf-8")


def parse_prefect_import_text(raw_text: str) -> ImportPreview:
    """Parse an AI-prepared JSON array/object or a header-based CSV without network access."""
    try:
        check_import_bytes(raw_text.encode("utf-8"))
    except (PrefectImportLimitError, UnicodeError) as error:
        return ImportPreview((), (f"Import format could not be read: {error}",))
    source = raw_text.strip().lstrip("\ufeff")
    if not source:
        return ImportPreview((), ("Import text is empty.",))
    try:
        if source.startswith(("[", "{")):
            check_json_nesting(source)
            raw_rows = _load_json_rows(source)
        else:
            raw_rows = _load_csv_rows(source)
    except (json.JSONDecodeError, csv.Error, PrefectImportLimitError, RecursionError, ValueError) as error:
        return ImportPreview((), (f"Import format could not be read: {error}",))
    return parse_prefect_import_rows(raw_rows)


def parse_prefect_import_rows(
    raw_rows: list[dict[str, Any]],
    *,
    target_to_source: dict[str, str] | None = None,
) -> ImportPreview:
    """Normalize locally parsed rows after an operator-reviewed column mapping."""
    try:
        _check_raw_rows(raw_rows)
    except (PrefectImportLimitError, ValueError) as error:
        return ImportPreview((), (f"Import format could not be read: {error}",))
    rows: list[PrefectInput] = []
    issues: list[str] = []
    for index, raw_row in enumerate(raw_rows, start=1):
        try:
            normalized_input = (
                {target: raw_row.get(source) for target, source in target_to_source.items()}
                if target_to_source is not None
                else raw_row
            )
            rows.append(_normalize_row(normalized_input))
        except ValueError as error:
            issues.append(f"Row {index}: {error}")
    return ImportPreview(tuple(rows), tuple(issues))


def _load_json_rows(source: str) -> list[dict[str, Any]]:
    payload = json.loads(source)
    if isinstance(payload, dict):
        payload = payload.get("prefects", [])
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError("JSON must be an array of prefects or an object with a prefects array.")
    return payload


def _load_csv_rows(source: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(source))
    raw_headers = reader.fieldnames
    if not raw_headers:
        return []
    headers = validate_import_headers(raw_headers)
    reader.fieldnames = list(headers)
    raw_rows: list[dict[str, Any]] = []
    for index, row in enumerate(reader, start=1):
        check_import_row_count(index)
        overflow = row.pop(None, None)
        if overflow and any(str(value or "").strip() for value in overflow):
            raise PrefectImportLimitError(
                "too_many_columns",
                "A CSV row contains values beyond the 50-column import boundary.",
            )
        check_import_column_count(len(row))
        for value in row.values():
            check_import_cell(value)
        raw_rows.append(row)
    return raw_rows


def _check_raw_rows(raw_rows: list[dict[str, Any]]) -> None:
    check_import_row_count(len(raw_rows))
    for raw_row in raw_rows:
        if not isinstance(raw_row, dict):
            raise ValueError("Every imported row must be an object with named fields.")
        check_import_column_count(len(raw_row))
        for key, value in raw_row.items():
            check_import_cell(key)
            check_import_cell(value)


def _normalize_row(row: dict[str, Any]) -> PrefectInput:
    name_zh = _value(row, "name_zh")
    form = _normalize_form(_value(row, "form"))
    class_name = _value(row, "class_name")
    role_code = _normalize_role(_value(row, "role"))
    available_days = _normalize_days(_value(row, "available_days"))
    if not name_zh:
        raise ValueError("Chinese name is required.")
    if not is_chinese_display_name(name_zh):
        raise ValueError("The authoritative prefect display name must be Chinese.")
    if not form:
        raise ValueError("Form is required.")
    if not class_name:
        raise ValueError("Class is required.")
    if not available_days:
        raise ValueError("At least one available day is required.")
    return PrefectInput(
        name_zh=name_zh,
        form=form,
        class_name=class_name,
        role_code=role_code,
        available_days=available_days,
        remarks=_value(row, "remarks"),
    )


def _value(row: dict[str, Any], field: str) -> str:
    for alias in FIELD_ALIASES[field]:
        if alias in row and row[alias] is not None:
            value = row[alias]
            if isinstance(value, list):
                return "、".join(str(item) for item in value)
            return str(value).strip()
    return ""


def _normalize_form(value: str) -> str:
    candidate = value.strip().upper().replace("FORM", "F.").replace("F", "F.")
    candidate = re.sub(r"F\.\.+", "F.", candidate)
    if candidate in {"F.3", "F.4", "F.5", "F.6"}:
        return candidate
    raise ValueError("Form must be F.3, F.4, F.5, or F.6.")


def _normalize_role(value: str) -> str:
    normalized = value.strip().casefold()
    if normalized in {"assistant_head", "ahp"} or "assistant head study prefect" in normalized or "助理首席導學風紀" in value:
        return "assistant_head"
    if normalized in {"study_prefect", "prefect"} or "study prefect" in normalized or "導學風紀" in value:
        return "study_prefect"
    raise ValueError("Role must identify a Study Prefect or Assistant Head Study Prefect.")


def _normalize_days(value: str) -> tuple[str, ...]:
    pieces = [piece.strip().upper() for piece in re.split(r"[,;、/|\s]+", value) if piece.strip()]
    normalized: list[str] = []
    for piece in pieces:
        mapped = DAY_ALIASES.get(piece, DAY_ALIASES.get(piece.replace("週", "星期")))
        if mapped is None:
            raise ValueError(f"Unknown available day: {piece}")
        if mapped not in normalized:
            normalized.append(mapped)
    return tuple(normalized)
