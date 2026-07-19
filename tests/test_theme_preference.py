from __future__ import annotations

from nicegui_app.ui import theme


def test_theme_follows_system_by_default_and_uses_dark_server_fallback(monkeypatch) -> None:
    monkeypatch.setattr(theme, "preference_get", lambda _key, default=None: default)

    assert theme.theme_preference() == "system"
    assert theme.current_theme() == "dark"


def test_theme_choice_cycles_system_dark_light(monkeypatch) -> None:
    saved: dict[str, str] = {}

    monkeypatch.setattr(
        theme,
        "preference_get",
        lambda key, default=None: saved.get(key, default),
    )
    monkeypatch.setattr(theme, "preference_set", lambda key, value: saved.__setitem__(key, value))

    assert theme.theme_preference() == "system"
    theme.toggle_theme()
    assert saved["theme"] == "dark"
    theme.toggle_theme()
    assert saved["theme"] == "light"
    theme.toggle_theme()
    assert saved["theme"] == "system"


def test_invalid_theme_choice_fails_closed_to_system(monkeypatch) -> None:
    monkeypatch.setattr(theme, "preference_get", lambda _key, _default=None: "unexpected")

    assert theme.theme_preference() == "system"
    assert theme.current_theme() == "dark"
