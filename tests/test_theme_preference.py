from __future__ import annotations

from nicegui_app.ui import theme


def test_theme_follows_system_by_default_and_uses_dark_server_fallback(monkeypatch) -> None:
    monkeypatch.setattr(theme, "preference_get", lambda _key, default=None: default)

    assert theme.theme_preference() == "system"
    assert theme.current_theme() == "dark"


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
    assert theme.current_theme() == "dark"
