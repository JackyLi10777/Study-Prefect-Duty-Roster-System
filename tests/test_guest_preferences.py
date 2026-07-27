from __future__ import annotations

from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

import pytest

from nicegui_app.access_context import AccessMode, PageContext, Principal
from nicegui_app.services.guest_preferences import GuestPreferenceRegistry
from nicegui_app.services.guest_workspace import GuestCapacityError
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
    with pytest.raises(ValueError):
        store["theme_system_resolved"] = "system"
    with pytest.raises(ValueError):
        store["theme_system_resolved"] = {"unexpected": "mapping"}
    with pytest.raises(ValueError):
        store["theme_system_resolved"] = ["dark"]


def test_guest_system_theme_resolution_is_session_only_and_domain_bounded() -> None:
    registry = GuestPreferenceRegistry()
    first = registry.store_for("guest-theme-a")
    second = registry.store_for("guest-theme-b")

    first["theme_system_resolved"] = "dark"

    assert registry.store_for("guest-theme-a")["theme_system_resolved"] == "dark"
    assert second.get("theme_system_resolved") is None


def test_guest_preferences_expire_without_durable_cleanup_callbacks() -> None:
    now = {"value": 1_000}
    registry = GuestPreferenceRegistry(ttl_seconds=30, clock=lambda: now["value"])
    store = registry.store_for("guest-expiring", expires_at=1_020)
    store["locale"] = "en"

    now["value"] = 1_020

    assert registry.active_session_count == 0
    assert len(store) == 0
    with pytest.raises(KeyError):
        store["locale"] = "zh-HK"


def test_guest_preference_registry_rejects_capacity_without_evicting_admitted_sessions() -> None:
    now = {"value": 2_000}
    registry = GuestPreferenceRegistry(
        ttl_seconds=60,
        max_sessions=24,
        clock=lambda: now["value"],
    )
    admitted = []
    for index in range(24):
        store = registry.store_for(f"guest-{index}", expires_at=2_050)
        store["locale"] = "en" if index % 2 else "zh-HK"
        admitted.append(store)

    with pytest.raises(GuestCapacityError, match="guest session capacity is full"):
        registry.store_for("guest-24", expires_at=2_050)

    assert registry.active_session_count == 24
    for index, store in enumerate(admitted):
        expected = "en" if index % 2 else "zh-HK"
        assert store["locale"] == expected
        store["theme"] = "dark"
        assert registry.store_for(f"guest-{index}", expires_at=2_050)["theme"] == "dark"


def test_verified_expiry_is_capped_by_the_process_local_ttl() -> None:
    registry = GuestPreferenceRegistry(ttl_seconds=30, clock=lambda: 3_000)
    registry.store_for("guest-long-token", expires_at=9_999)["theme"] = "dark"

    assert registry.purge_expired(now=3_029) == 0
    assert registry.purge_expired(now=3_030) == 1


def test_guest_preference_registry_isolated_and_bounded_under_concurrent_sessions() -> None:
    registry = GuestPreferenceRegistry(max_sessions=24, clock=lambda: 4_000)

    def write_session(index: int) -> None:
        store = registry.store_for(f"guest-{index}", expires_at=4_030)
        store["locale"] = "en" if index % 2 else "zh-HK"

    with ThreadPoolExecutor(max_workers=12) as executor:
        list(executor.map(write_session, range(24)))

    assert registry.active_session_count == 24
    for index in range(24):
        expected = "en" if index % 2 else "zh-HK"
        assert registry.store_for(f"guest-{index}", expires_at=4_030)["locale"] == expected
