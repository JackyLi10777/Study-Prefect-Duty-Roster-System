"""One command identity for actor attribution and durable operation receipts."""

from __future__ import annotations

import hashlib
import json


class CommandIdentityError(ValueError):
    """An explicit command cannot identify a stable, storable user intent."""


def operation_fingerprint(operation_type: str, payload: dict[str, object]) -> str:
    """Preserve the existing receipt encoding without importing a SQL Adapter."""
    encoded = json.dumps({"operationType": operation_type, "payload": payload},
                         ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_command_id(value: object) -> str:
    """Trim once; retain valid Unicode, bounded by the official 64-char contract.

    Missing/invalid explicit values are errors, never requests to generate a new
    identity. Legacy callers which allow omission must generate before calling.
    """
    if type(value) is not str:
        raise CommandIdentityError("Command ID must be text.")
    normalized = value.strip()
    if not normalized or len(normalized) > 64:
        raise CommandIdentityError("Command ID must contain 1 to 64 characters.")
    try:
        normalized.encode("utf-8")
    except UnicodeEncodeError as error:
        raise CommandIdentityError("Command ID must contain valid Unicode text.") from error
    return normalized
