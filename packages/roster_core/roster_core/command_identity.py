"""One command identity for actor attribution and durable operation receipts."""

from __future__ import annotations


class CommandIdentityError(ValueError):
    """An explicit command cannot identify a stable, storable user intent."""


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
