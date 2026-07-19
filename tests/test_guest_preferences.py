from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from nicegui_app.access_context import AccessMode, PageContext, Principal
from nicegui_app.services.guest_preferences import GuestPreferenceRegistry
from nicegui_app.ui import preferences


def _guest_context(store) -> PageContext:  # type: ignore[no-untyped-def]
    return PageContext.create(
        Principal(
            mode=AccessMode.GUEST,
            subject="guest-demo",
            session_id="guest-preference-session",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
        ),
        preference_store=store,
    )


def test_guest_preferences_survive_new_mapping_views_for_the_same_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = GuestPreferenceRegistry()
    first = registry.store_for("guest-preference-session")
    monkeypatch.setattr(preferences, "current_page_context", lambda: _guest_context(first))
    preferences.preference_set("locale", "en")
    preferences.preference_set("theme", "dark")

    reloaded = registry.store_for("guest-preference-session")
    monkeypatch.setattr(preferences, "current_page_context", lambda: _guest_context(reloaded))

    assert preferences.preference_get("locale") == "en"
    assert preferences.preference_get("theme") == "dark"


def test_guest_preference_cleanup_is_idempotent_and_does_not_affect_other_sessions() -> None:
    registry = GuestPreferenceRegistry()
    registry.store_for("guest-a")["locale"] = "en"
    registry.store_for("guest-b")["locale"] = "zh-HK"

    registry.cleanup_session("guest-a")
    registry.cleanup_session("guest-a")

    assert registry.store_for("guest-a").get("locale") is None
    assert registry.store_for("guest-b")["locale"] == "zh-HK"


def test_guest_preferences_reject_unbounded_or_unknown_values() -> None:
    store = GuestPreferenceRegistry().store_for("guest-preference-session")

    with pytest.raises(ValueError):
        store["unapproved_setting"] = "value"
    with pytest.raises(ValueError):
        store["music_track_dashboard"] = "x" * 257
    with pytest.raises(ValueError):
        store["locale"] = {"unexpected": "mapping"}
