"""Small, opt-in semantic sounds coordinated with the local music player."""

from __future__ import annotations

from nicegui import ui

from nicegui_app.ui.preferences import preference_get, preference_set
from nicegui_app.ui.theme import sound_feedback_enabled


SOUND_KINDS = {"navigation", "working", "success", "attention"}
VISUAL_FEEDBACK_KINDS = SOUND_KINDS | {"error"}
MUSIC_AUTOPLAY_STORAGE_KEY = "music_autoplay"
DEFAULT_MUSIC_AUTOPLAY = True


def music_autoplay_enabled() -> bool:
    """Return the browser-local preference from one canonical default."""
    return bool(preference_get(MUSIC_AUTOPLAY_STORAGE_KEY, DEFAULT_MUSIC_AUTOPLAY))


def set_music_autoplay(enabled: bool) -> None:
    preference_set(MUSIC_AUTOPLAY_STORAGE_KEY, bool(enabled))


def preferred_music_volume() -> float:
    return _bounded_float(preference_get("music_volume", 0.18), default=0.18, maximum=0.6)


def preferred_sound_volume() -> float:
    return _bounded_float(preference_get("sound_volume", 0.7), default=0.7, maximum=1.0)


def set_music_volume(value: float) -> None:
    preference_set("music_volume", _bounded_float(value, default=0.18, maximum=0.6))


def set_sound_volume(value: float) -> None:
    preference_set("sound_volume", _bounded_float(value, default=0.7, maximum=1.0))


def play_interface_sound(kind: str, *, force: bool = False) -> None:
    """Play one short confirmation; never use this for hover, page load, or errors."""
    if kind not in SOUND_KINDS:
        raise ValueError(f"Unknown interface sound: {kind}")
    sound_enabled = force or sound_feedback_enabled()
    volume = preferred_sound_volume()
    ui.run_javascript(
        f"""
        (() => {{
          const kind = {kind!r};
          const level = {volume!r};
          const soundEnabled = {str(sound_enabled).lower()};
          const forced = {str(force).lower()};
          window.dispatchEvent(new CustomEvent('sy:feedback', {{detail: {{kind}}}}));
          if (!soundEnabled || level <= 0) return;
          const now = performance.now();
          const lastPlayedAt = Number(window.__singYinSoundLastAt);
          if (!forced && Number.isFinite(lastPlayedAt) && now - lastPlayedAt < 140) return;
          window.__singYinSoundLastAt = now;
          const AudioContextClass = window.AudioContext || window.webkitAudioContext;
          if (!AudioContextClass) return;
          const context = window.__singYinAudioContext || new AudioContextClass();
          window.__singYinAudioContext = context;
          const sequences = {{
            navigation: [[440, 0.00, 0.11, 0.026, 'sine']],
            working: [[349.23, 0.00, 0.14, 0.030, 'triangle'], [440.00, 0.08, 0.17, 0.026, 'sine']],
            success: [[523.25, 0.00, 0.17, 0.050, 'sine'], [659.25, 0.10, 0.22, 0.058, 'triangle']],
            attention: [[392.00, 0.00, 0.16, 0.040, 'triangle'], [493.88, 0.11, 0.20, 0.044, 'sine']],
          }};
          const music = document.querySelector('audio.sy-page-music-audio');
          if (music && !music.paused) {{
            const base = Number(music.dataset.syBaseVolume || music.volume || 0.18);
            music.dataset.syBaseVolume = String(base);
            music.volume = Math.max(0.02, base * 0.55);
            clearTimeout(window.__singYinMusicRestoreTimer);
            window.__singYinMusicRestoreTimer = setTimeout(() => {{ music.volume = base; }}, 560);
          }}
          const play = () => {{
            for (const [frequency, offset, duration, peak, waveform] of sequences[kind]) {{
              const oscillator = context.createOscillator();
              const gain = context.createGain();
              const start = context.currentTime + offset;
              oscillator.type = waveform;
              oscillator.frequency.setValueAtTime(frequency, start);
              gain.gain.setValueAtTime(0.0001, start);
              gain.gain.exponentialRampToValueAtTime(Math.max(0.0002, peak * level), start + 0.025);
              gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
              oscillator.connect(gain).connect(context.destination);
              oscillator.addEventListener('ended', () => {{
                oscillator.disconnect();
                gain.disconnect();
              }}, {{once: true}});
              oscillator.start(start);
              oscillator.stop(start + duration + 0.01);
            }}
          }};
          const resume = context.resume();
          if (resume && typeof resume.then === 'function') {{
            resume.then(play).catch(() => {{}});
          }} else {{
            play();
          }}
        }})();
        """
    )


def emit_interface_feedback(kind: str) -> None:
    """Emit one visual-only state response, including silent error feedback."""
    if kind not in VISUAL_FEEDBACK_KINDS:
        raise ValueError(f"Unknown interface feedback: {kind}")
    ui.run_javascript(
        "window.dispatchEvent("
        f"new CustomEvent('sy:feedback', {{detail: {{kind: {kind!r}}}}})"
        ");"
    )


def _bounded_float(value: object, *, default: float, maximum: float) -> float:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return min(max(parsed, 0.0), maximum)
