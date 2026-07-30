from __future__ import annotations

from pathlib import Path

import pytest

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.sound import _bounded_float
from nicegui_app.ui import theme
from tests.ui_source import combined_page_source


@pytest.mark.parametrize(
    ("value", "default", "maximum", "expected"),
    [(0.4, 0.2, 1.0, 0.4), (-2, 0.2, 1.0, 0.0), (5, 0.2, 1.0, 1.0), ("bad", 0.2, 1.0, 0.2)],
)
def test_audio_preferences_are_bounded(value: object, default: float, maximum: float, expected: float) -> None:
    assert _bounded_float(value, default=default, maximum=maximum) == expected


def test_interface_sound_is_semantic_action_feedback_and_ducks_music() -> None:
    sound = (PROJECT_ROOT / "nicegui_app" / "ui" / "sound.py").read_text(encoding="utf-8")
    pages = combined_page_source()
    music = (PROJECT_ROOT / "nicegui_app" / "ui" / "music.py").read_text(encoding="utf-8")

    assert 'SOUND_KINDS = {"navigation", "working", "success", "attention"}' in sound
    assert 'VISUAL_FEEDBACK_KINDS = SOUND_KINDS | {"error"}' in sound
    assert "sound_enabled = force or sound_feedback_enabled()" in sound
    assert "new CustomEvent('sy:feedback'" in sound
    assert "music.volume = Math.max(0.02, base * 0.55)" in sound
    assert "now - lastPlayedAt < 140" in sound
    assert "oscillator.disconnect()" in sound
    assert "gain.disconnect()" in sound
    assert "setVolume" not in sound, "Visible YouTube volume remains under the operator's native controls"
    assert 'play_interface_sound("success")' in pages
    assert 'play_interface_sound("working")' in pages
    assert 'play_interface_sound("navigation")' in pages
    assert 'emit_interface_feedback("error")' in pages
    assert 'emit_interface_feedback("attention")' in pages
    assert "mouseover" not in sound.lower()
    assert "pointerover" not in sound.lower()
    assert "audio_setup_seen" in music
    assert "test_interface_sound" in music


@pytest.mark.parametrize(
    ("stored", "expected"),
    [(None, True), (True, True), (False, False)],
)
def test_interface_sound_default_preserves_explicit_operator_choice(
    monkeypatch: pytest.MonkeyPatch,
    stored: bool | None,
    expected: bool,
) -> None:
    writes: list[tuple[str, object]] = []
    monkeypatch.setattr(theme, "preference_get", lambda key, default=None: stored)
    monkeypatch.setattr(theme, "preference_set", lambda key, value: writes.append((key, value)))

    assert theme.sound_feedback_enabled() is expected
    assert writes == [], "Resolving a missing default must not persist or overwrite an opt-out"


def test_shell_previews_and_updates_sound_without_reloading_unfinished_forms() -> None:
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")
    handler = shell.split("async def _toggle_sound_feedback_with_preview", 1)[1].split(
        "def _current_theme_control", 1
    )[0]

    assert "_sync_preference_controls" in handler
    assert 'play_interface_sound("success", force=True)' in handler
    assert "ui.navigate.reload" not in handler
    assert "_toggle_sound_feedback_with_preview(sound_controls)" in shell
    assert "sound_button.tooltip(sound_tooltip)" not in shell
    assert "sound_tooltip_element = ui.tooltip(sound_tooltip)" in shell
    assert 't("disable_sound_feedback")' in shell
    assert "pressed=enabled" in handler
    assert "aria-pressed" in shell


def test_settings_sound_switch_previews_the_enabled_state() -> None:
    music = (PROJECT_ROOT / "nicegui_app" / "ui" / "music.py").read_text(encoding="utf-8")
    handler = music.split("def change_sound_enabled", 1)[1].split("def change_sound_volume", 1)[0]

    assert 'play_interface_sound("success", force=True)' in handler
    assert 'ui.notify(t("sound_feedback_on")' in handler
    assert 'ui.notify(t("sound_feedback_off")' in handler
