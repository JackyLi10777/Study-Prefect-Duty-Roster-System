"""Access-aware UI preferences.

Administrator preferences retain NiceGUI's encrypted user storage. Guest
preferences are deliberately connection-local and never enter the persistent
``storage-user`` files.
"""

from __future__ import annotations

from typing import Any

from nicegui import app

from nicegui_app.access_context import AccessMode
from nicegui_app.runtime import current_page_context


def _store():  # type: ignore[no-untyped-def]
    try:
        context = current_page_context()
    except (RuntimeError, PermissionError):
        # A late callback after Guest expiry/revocation must never be promoted
        # to durable administrator storage.  Client storage is the fail-closed
        # fallback for any page whose verified context is no longer available.
        return app.storage.client
    if context.preference_store is not None:
        return context.preference_store
    return (
        app.storage.client
        if context.principal.mode is AccessMode.GUEST
        else app.storage.user
    )


def preference_get(key: str, default: Any = None) -> Any:
    return _store().get(key, default)


def preference_set(key: str, value: Any) -> None:
    _store()[key] = value


def preference_delete(key: str) -> None:
    _store().pop(key, None)


__all__ = ["preference_delete", "preference_get", "preference_set"]
