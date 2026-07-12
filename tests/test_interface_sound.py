from __future__ import annotations

from pathlib import Path

import pytest

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.sound import _bounded_float
from tests.ui_source import combined_page_source


@pytest.mark.parametrize(
    ("value", "default", "maximum", "expected"),
    [(0.4, 0.2, 1.0, 0.4), (-2, 0.2, 1.0, 0.0), (5, 0.2, 1.0, 1.0), ("bad", 0.2, 1.0, 0.2)],
)
def test_audio_preferences_are_bounded(value: object, default: float, maximum: float, expected: float) -> None:
    assert _bounded_float(value, default=default, maximum=maximum) == expected


def test_interface_sound_is_semantic_opt_in_and_ducks_music() -> None:
    sound = (PROJECT_ROOT / "nicegui_app" / "ui" / "sound.py").read_text(encoding="utf-8")
    pages = combined_page_source()
    music = (PROJECT_ROOT / "nicegui_app" / "ui" / "music.py").read_text(encoding="utf-8")

    assert 'SOUND_KINDS = {"navigation", "working", "success", "attention"}' in sound
    assert "sound_enabled = force or sound_feedback_enabled()" in sound
    assert "new CustomEvent('sy:feedback'" in sound
    assert "music.volume = Math.max(0.02, base * 0.80)" in sound
    assert "setVolume" not in sound, "Visible YouTube volume remains under the operator's native controls"
    assert 'play_interface_sound("success")' in pages
    assert 'play_interface_sound("working")' in pages
    assert 'play_interface_sound("navigation")' in pages
    assert "mouseover" not in sound.lower()
    assert "pointerover" not in sound.lower()
    assert "audio_setup_seen" in music
    assert "test_interface_sound" in music
