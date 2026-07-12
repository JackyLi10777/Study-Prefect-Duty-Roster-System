"""Small, opt-in semantic sounds coordinated with the local music player."""

from __future__ import annotations

from nicegui import app, ui

from nicegui_app.ui.theme import sound_feedback_enabled


SOUND_KINDS = {"navigation", "success", "attention"}


def preferred_music_volume() -> float:
    return _bounded_float(app.storage.user.get("music_volume", 0.18), default=0.18, maximum=0.6)


def preferred_sound_volume() -> float:
    return _bounded_float(app.storage.user.get("sound_volume", 0.7), default=0.7, maximum=1.0)


def set_music_volume(value: float) -> None:
    app.storage.user["music_volume"] = _bounded_float(value, default=0.18, maximum=0.6)


def set_sound_volume(value: float) -> None:
    app.storage.user["sound_volume"] = _bounded_float(value, default=0.7, maximum=1.0)


def play_interface_sound(kind: str, *, force: bool = False) -> None:
    """Play one short confirmation; never use this for hover, page load, or errors."""
    if kind not in SOUND_KINDS:
        raise ValueError(f"Unknown interface sound: {kind}")
    if not force and not sound_feedback_enabled():
        return
    volume = preferred_sound_volume()
    ui.run_javascript(
        f"""
        (() => {{
          const kind = {kind!r};
          const level = {volume!r};
          const AudioContextClass = window.AudioContext || window.webkitAudioContext;
          if (!AudioContextClass) return;
          const context = window.__singYinAudioContext || new AudioContextClass();
          window.__singYinAudioContext = context;
          context.resume();
          const sequences = {{
            navigation: [[440, 0.00, 0.11, 0.020]],
            success: [[523.25, 0.00, 0.16, 0.030], [659.25, 0.10, 0.20, 0.038]],
            attention: [[392.00, 0.00, 0.15, 0.024], [493.88, 0.11, 0.18, 0.028]],
          }};
          const music = document.querySelector('audio.sy-page-music-audio');
          if (music && !music.paused) {{
            const base = Number(music.dataset.syBaseVolume || music.volume || 0.18);
            music.dataset.syBaseVolume = String(base);
            music.volume = Math.max(0.02, base * 0.80);
            clearTimeout(window.__singYinMusicRestoreTimer);
            window.__singYinMusicRestoreTimer = setTimeout(() => {{ music.volume = base; }}, 430);
          }}
          for (const [frequency, offset, duration, peak] of sequences[kind]) {{
            const oscillator = context.createOscillator();
            const gain = context.createGain();
            const start = context.currentTime + offset;
            oscillator.type = 'sine';
            oscillator.frequency.setValueAtTime(frequency, start);
            gain.gain.setValueAtTime(0.0001, start);
            gain.gain.exponentialRampToValueAtTime(Math.max(0.0002, peak * level), start + 0.025);
            gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
            oscillator.connect(gain).connect(context.destination);
            oscillator.start(start); oscillator.stop(start + duration + 0.01);
          }}
        }})();
        """
    )


def _bounded_float(value: object, *, default: float, maximum: float) -> float:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return min(max(parsed, 0.0), maximum)
