from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui import theme
from nicegui_app.access_context import AccessMode, PageContext, Principal


def test_theme_follows_system_by_default_and_uses_neutral_first_render(monkeypatch) -> None:
    monkeypatch.setattr(theme, "preference_get", lambda _key, default=None: default)

    assert theme.theme_preference() == "system"
    assert theme.current_theme() == "light"


def test_system_theme_uses_browser_resolution_hint_without_becoming_explicit(monkeypatch) -> None:
    saved = {"theme_system_resolved": "dark"}
    monkeypatch.setattr(theme, "preference_get", lambda key, default=None: saved.get(key, default))

    assert theme.theme_preference() == "system"
    assert theme.system_theme_resolution() == "dark"
    assert theme.current_theme() == "dark"


def test_explicit_theme_overrides_stale_system_resolution(monkeypatch) -> None:
    saved = {"theme": "light", "theme_system_resolved": "dark"}
    monkeypatch.setattr(theme, "preference_get", lambda key, default=None: saved.get(key, default))

    assert theme.current_theme() == "light"


def test_browser_resolution_is_validated_and_uses_existing_preference_adapter(monkeypatch) -> None:
    saved: dict[str, str] = {}
    monkeypatch.setattr(theme, "preference_set", lambda key, value: saved.__setitem__(key, value))

    theme.set_system_theme_resolution("dark")
    assert saved == {"theme_system_resolved": "dark"}

    with pytest.raises(ValueError, match="system theme resolution"):
        theme.set_system_theme_resolution("system")


def test_theme_choice_is_set_explicitly(monkeypatch) -> None:
    saved: dict[str, str] = {}

    monkeypatch.setattr(
        theme,
        "preference_get",
        lambda key, default=None: saved.get(key, default),
    )
    monkeypatch.setattr(theme, "preference_set", lambda key, value: saved.__setitem__(key, value))

    assert theme.theme_preference() == "system"
    for value in ("light", "dark", "system"):
        theme.set_theme_preference(value)
        assert saved["theme"] == value


def test_binary_theme_destination_never_enters_a_hidden_third_state() -> None:
    assert theme.next_explicit_theme("light") == "dark"
    assert theme.next_explicit_theme("dark") == "light"

    with pytest.raises(ValueError, match="resolved theme"):
        theme.next_explicit_theme("system")


def test_invalid_explicit_theme_choice_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(theme, "preference_set", lambda _key, _value: None)

    try:
        theme.set_theme_preference("sepia")
    except ValueError as error:
        assert "theme preference" in str(error)
    else:  # pragma: no cover - documents the validation boundary
        raise AssertionError("invalid theme preference was accepted")


def test_invalid_theme_choice_fails_closed_to_system(monkeypatch) -> None:
    monkeypatch.setattr(theme, "preference_get", lambda _key, _default=None: "unexpected")

    assert theme.theme_preference() == "system"
    assert theme.current_theme() == "light"


def test_verified_theme_handoff_initializes_only_an_unset_workspace(monkeypatch) -> None:
    saved: dict[str, str] = {}
    monkeypatch.setattr(theme, "preference_get", lambda key, default=None: saved.get(key, default))
    monkeypatch.setattr(theme, "preference_set", lambda key, value: saved.__setitem__(key, value))
    context = PageContext.create(
        Principal(
            mode=AccessMode.GUEST,
            subject="guest",
            session_id="guest-theme-session",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            theme_handoff="dark",
        )
    )

    assert theme.adopt_verified_theme_handoff(context) is True
    assert saved == {"theme": "dark"}
    saved["theme"] = "light"
    assert theme.adopt_verified_theme_handoff(context) is False
    assert saved == {"theme": "light"}


def test_missing_theme_handoff_preserves_system_default(monkeypatch) -> None:
    saved: dict[str, str] = {}
    monkeypatch.setattr(theme, "preference_get", lambda key, default=None: saved.get(key, default))
    monkeypatch.setattr(theme, "preference_set", lambda key, value: saved.__setitem__(key, value))
    context = PageContext.create(
        Principal(mode=AccessMode.LOCAL_MAINTENANCE, subject="local-console")
    )

    assert theme.adopt_verified_theme_handoff(context) is False
    assert saved == {}
    assert theme.theme_preference() == "system"


def test_initial_head_resolves_exactly_one_atmosphere_theme_before_stylesheets() -> None:
    dark_head = theme.initial_theme_head_html("dark")

    assert dark_head.index('data-sy-runtime="initial-theme"') < dark_head.index(
        'data-sy-initial-atmosphere-tokens="current-theme-only"'
    )
    assert "document.documentElement.dataset.syResolvedTheme=resolved" in dark_head
    assert "matchMedia('(prefers-color-scheme: dark)')" in dark_head
    assert dark_head.count(':root[data-sy-resolved-theme="light"]') == 1
    assert dark_head.count(':root[data-sy-resolved-theme="dark"]') == 1
    for slot, (light_asset, dark_asset) in theme.ATMOSPHERE_THEME_PAIRS.items():
        assert dark_head.count(f"--sy-image-{slot}:") == 2
        assert dark_head.count(light_asset) == 1
        assert dark_head.count(dark_asset) == 1

    with pytest.raises(ValueError, match="initial theme preference"):
        theme.initial_theme_head_html("sepia")


def test_theme_runtime_coalesces_body_mutations_and_cleans_the_frame() -> None:
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(
        encoding="utf-8"
    )

    assert "const scheduleThemeSync = () =>" in shell
    assert "const observer = new MutationObserver(scheduleThemeSync);" in shell
    assert "if (themeSyncFrame) cancelAnimationFrame(themeSyncFrame);" in shell
