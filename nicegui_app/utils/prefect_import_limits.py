"""Shared resource limits for every local prefect-directory import path."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any


MAX_IMPORT_BYTES = 2 * 1024 * 1024
MAX_IMPORT_ROWS = 2_000
MAX_IMPORT_COLUMNS = 50
MAX_IMPORT_CELL_CHARACTERS = 4_096
MAX_IMPORT_JSON_DEPTH = 8


class PrefectImportLimitError(ValueError):
    """Describe a stable, operator-actionable import resource violation."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def check_import_bytes(content: bytes) -> None:
    if len(content) > MAX_IMPORT_BYTES:
        raise PrefectImportLimitError(
            "too_large",
            "The import is larger than 2 MB; split it into smaller batches.",
        )


def check_import_row_count(row_count: int) -> None:
    if row_count > MAX_IMPORT_ROWS:
        raise PrefectImportLimitError(
            "too_many_rows",
            "The import contains more than 2,000 data rows; split it into smaller batches.",
        )


def check_import_column_count(column_count: int) -> None:
    if column_count > MAX_IMPORT_COLUMNS:
        raise PrefectImportLimitError(
            "too_many_columns",
            "The import contains more than 50 columns; remove unrelated fields.",
        )


def check_import_cell(value: Any) -> None:
    """Bound a logical cell, including JSON list values, before normalisation."""

    if value is None:
        return
    if isinstance(value, str):
        rendered = value
    else:
        try:
            rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError, RecursionError):
            rendered = str(value)
    if len(rendered) > MAX_IMPORT_CELL_CHARACTERS:
        raise PrefectImportLimitError(
            "cell_too_long",
            "An imported heading or cell is longer than 4,096 characters; shorten it and retry.",
        )


def validate_import_headers(headers: Iterable[Any]) -> tuple[str, ...]:
    """Normalize and validate headings before a row dictionary can discard data.

    ``csv.DictReader`` silently overwrites duplicate headings and accepts blank
    keys.  Every local import path therefore calls this shared guard before it
    materialises rows.
    """

    normalized = tuple(str(header or "").strip() for header in headers)
    if not normalized or not any(normalized):
        raise PrefectImportLimitError(
            "headings_required",
            "The first row must contain column headings.",
        )
    check_import_column_count(len(normalized))
    for header in normalized:
        check_import_cell(header)
    if any(not header for header in normalized):
        raise PrefectImportLimitError(
            "blank_heading",
            "Every imported column must have a heading.",
        )
    if len(normalized) != len(set(normalized)):
        raise PrefectImportLimitError(
            "duplicate_headings",
            "Column headings must be unique.",
        )
    return normalized


def check_json_nesting(source: str) -> None:
    """Reject excessive object/array nesting before ``json.loads`` allocates it."""

    depth = 0
    in_string = False
    escaped = False
    for character in source:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > MAX_IMPORT_JSON_DEPTH:
                raise PrefectImportLimitError(
                    "json_too_deep",
                    "The JSON structure is nested too deeply; use a flat array of prefect rows.",
                )
        elif character in "]}":
            depth = max(depth - 1, 0)


__all__ = [
    "MAX_IMPORT_BYTES",
    "MAX_IMPORT_CELL_CHARACTERS",
    "MAX_IMPORT_COLUMNS",
    "MAX_IMPORT_JSON_DEPTH",
    "MAX_IMPORT_ROWS",
    "PrefectImportLimitError",
    "check_import_bytes",
    "check_import_cell",
    "check_import_column_count",
    "check_import_row_count",
    "check_json_nesting",
    "validate_import_headers",
]
