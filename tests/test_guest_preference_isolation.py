from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from nicegui_app.access_context import AccessMode, PageContext, Principal
from nicegui_app.ui import preferences


def test_only_access_aware_preference_module_may_use_persistent_user_storage() -> None:
    project_root = Path(__file__).resolve().parents[1]
    python_sources = (project_root / "nicegui_app").rglob("*.py")
    offenders = []
    for source in python_sources:
        text = source.read_text(encoding="utf-8")
        if "app.storage.user" in text and source.name != "preferences.py":
            offenders.append(source.relative_to(project_root).as_posix())
    assert offenders == []


def _context(mode: AccessMode) -> PageContext:
    return PageContext.create(
        Principal(
            mode=mode,
            subject="guest" if mode is AccessMode.GUEST else "operator@syss.edu.hk",
            session_id="session",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            auth_epoch=1,
            key_id="key-v1",
        )
    )


def test_guest_preference_branch_is_connection_local(monkeypatch: pytest.MonkeyPatch) -> None:
    client_store: dict[str, object] = {}
    user_store: dict[str, object] = {}
    monkeypatch.setattr(
        preferences,
        "app",
        SimpleNamespace(storage=SimpleNamespace(client=client_store, user=user_store)),
    )
    monkeypatch.setattr(preferences, "current_page_context", lambda: _context(AccessMode.GUEST))

    preferences.preference_set("theme", "dark")

    assert client_store == {"theme": "dark"}
    assert user_store == {}


def test_missing_expired_or_revoked_context_never_falls_through_to_user_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_store: dict[str, object] = {}
    user_store: dict[str, object] = {}
    monkeypatch.setattr(
        preferences,
        "app",
        SimpleNamespace(storage=SimpleNamespace(client=client_store, user=user_store)),
    )

    def denied_context() -> PageContext:
        raise PermissionError("session expired or revoked")

    monkeypatch.setattr(preferences, "current_page_context", denied_context)
    preferences.preference_set("music_autoplay", True)

    assert client_store == {"music_autoplay": True}
    assert user_store == {}
