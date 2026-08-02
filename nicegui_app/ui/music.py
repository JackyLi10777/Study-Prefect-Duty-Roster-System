"""Accessible page-specific music controls and local library management."""

from __future__ import annotations

import json

from nicegui import events, run, ui

from nicegui_app.access_context import AccessMode
from nicegui_app.runtime import current_page_context
from nicegui_app.services.music_library import (
    MAX_AUDIO_BYTES,
    MUSIC_CONTEXTS,
    MUSIC_PROFILE_PREFERENCES,
    MusicLibrary,
    MusicLibraryError,
    MusicTrack,
    builtin_tracks_for_context,
    next_track_id,
    resolve_music_profile,
)
from nicegui_app.services.online_music import YouTubeSettings
from nicegui_app.services.youtube_audio_import import (
    YouTubeAudioImportError,
    YouTubeAudioImporter,
    youtube_import_ready,
)
from nicegui_app.ui.youtube_music import render_youtube_panel, render_youtube_settings
from nicegui_app.ui.html_safety import attr
from nicegui_app.ui.i18n import t
from nicegui_app.ui.preferences import preference_get, preference_set
from nicegui_app.ui.sound import (
    music_autoplay_enabled,
    play_interface_sound,
    preferred_music_volume,
    preferred_sound_volume,
    set_music_autoplay,
    set_music_volume,
    set_sound_volume,
)
from nicegui_app.ui.theme import current_theme, set_sound_feedback, sound_feedback_enabled


def music_context_label(context: str) -> str:
    return t(f"music_context_{context}")


def music_track_label(track: MusicTrack) -> str:
    arrangement = t(f"music_arrangement_{track.arrangement}")
    timing = f" · {track.duration}" if track.duration else ""
    return f"{track.title} — {track.artist} · {arrangement}{timing}"


def _tracks_for_page(
    context: str,
    *,
    profile: str,
    guest_mode: bool,
) -> list[MusicTrack]:
    """Resolve a playlist without exposing the persistent custom catalogue to guests."""

    if guest_mode:
        return builtin_tracks_for_context(context, profile=profile)
    return MusicLibrary().tracks_for_context(context, profile=profile)


def _music_state_script(state: str) -> str:
    """Keep the trigger, live status, and page state in sync in one place."""
    label = t(f"music_status_{state}")
    accessible_name = f'{t("page_music")} — {label}'
    return (
        "(() => {"
        f"const state = {json.dumps(state)};"
        f"const label = {json.dumps(label, ensure_ascii=False)};"
        f"const accessibleName = {json.dumps(accessible_name, ensure_ascii=False)};"
        "document.body.dataset.syMusicAutoplay = state;"
        "const trigger = document.querySelector('[data-testid=page-music-button]');"
        "if (trigger) {"
        "trigger.dataset.musicState = state;"
        "trigger.setAttribute('aria-label', accessibleName);"
        "trigger.setAttribute('title', label);"
        "window.__syIconMotion?.setPersistentGlyph(trigger, state === 'playing' ? 'graphic_eq' : 'headphones', {animate:true});"
        "}"
        "const status = document.querySelector('[data-testid=music-playback-status]');"
        "if (status) { status.dataset.musicState = state; status.textContent = label; }"
        "})();"
    )


_MUSIC_PLAYBACK_STATES = (
    "starting",
    "loading",
    "playing",
    "paused",
    "blocked",
    "transport",
    "decoding",
    "lifecycle",
    "error",
    "off",
)


def _music_state_callback_script() -> str:
    """Return one localised callback used by the shared browser controller."""
    labels = {state: t(f"music_status_{state}") for state in _MUSIC_PLAYBACK_STATES}
    page_music = t("page_music")
    return (
        "(state) => {"
        f"const labels = {json.dumps(labels, ensure_ascii=False)};"
        f"const pageMusic = {json.dumps(page_music, ensure_ascii=False)};"
        "const label = labels[state] || labels.error;"
        "document.body.dataset.syMusicAutoplay = state;"
        "const trigger = document.querySelector('[data-testid=page-music-button]');"
        "if (trigger) { trigger.dataset.musicState = state; trigger.setAttribute('aria-label', pageMusic + ' — ' + label); trigger.setAttribute('title', label); window.__syIconMotion?.setPersistentGlyph(trigger, state === 'playing' ? 'graphic_eq' : 'headphones', {animate:true}); }"
        "const status = document.querySelector('[data-testid=music-playback-status]');"
        "if (status) { status.dataset.musicState = state; status.textContent = label; }"
        "}"
    )


def _music_attempt_script(*, volume: float) -> str:
    callback = _music_state_callback_script()
    return (
        "(() => {"
        "const audio = document.querySelector('audio.sy-page-music-audio');"
        "const controller = window.SingYinMusicController;"
        f"const applyState = {callback};"
        "if (!audio || !controller) { applyState('error'); return; }"
        "controller.bind(audio, {onState: applyState});"
        f"void controller.attempt(audio, {{volume: {volume!r}, onState: applyState}});"
        "})();"
    )


def _music_retry_handler_script(*, volume: float) -> str:
    callback = _music_state_callback_script()
    return (
        "() => {"
        "const audio = document.querySelector('audio.sy-page-music-audio');"
        "const controller = window.SingYinMusicController;"
        f"const applyState = {callback};"
        "if (!audio || !controller) { applyState('error'); return; }"
        "controller.bind(audio, {onState: applyState});"
        f"void controller.attempt(audio, {{volume: {volume!r}, onState: applyState}});"
        "}"
    )


def _music_pause_handler_script() -> str:
    callback = _music_state_callback_script()
    return (
        "() => {"
        "const controller = window.SingYinMusicController;"
        f"const applyState = {callback};"
        "if (!controller) { applyState('error'); return; }"
        "controller.pauseAll({onState: applyState, state: 'paused'});"
        "}"
    )


def _music_continuity_script(context: str) -> str:
    """Resume the same local track across route changes without permanent storage."""
    return f"""
    (() => {{
      const audio = document.querySelector('audio.sy-page-music-audio');
      if (!audio || audio.dataset.syContinuityReady === 'true') return;
      audio.dataset.syContinuityReady = 'true';
      const storageKey = 'sing-yin:music-continuity:v1';
      const pageContext = {json.dumps(context)};
      const normalizedSource = () => {{
        try {{ return new URL(audio.currentSrc || audio.src, window.location.href).href; }}
        catch (_) {{ return audio.currentSrc || audio.src || ''; }}
      }};
      const readState = () => {{
        try {{
          const value = JSON.parse(sessionStorage.getItem(storageKey) || 'null');
          if (!value || typeof value !== 'object') return null;
          if (!Number.isFinite(Number(value.updatedAt)) || Date.now() - Number(value.updatedAt) > 43_200_000) return null;
          return value;
        }} catch (_) {{ return null; }}
      }};
      const previous = readState();
      const sameTrack = previous && previous.source === normalizedSource();
      audio.dataset.syContinuityPlaying = sameTrack && previous.playing === false ? 'false' : 'true';
      const restorePosition = () => {{
        if (!sameTrack) return;
        const position = Number(previous.position);
        if (!Number.isFinite(position) || position <= 0) return;
        const duration = Number(audio.duration);
        const safePosition = Number.isFinite(duration) && duration > 1
          ? Math.min(position, Math.max(0, duration - 0.75))
          : position;
        try {{ audio.currentTime = safePosition; }} catch (_) {{}}
      }};
      if (audio.readyState >= 1) restorePosition();
      else audio.addEventListener('loadedmetadata', restorePosition, {{once: true}});

      let lastWrittenSecond = -1;
      const saveState = (playing = !audio.paused) => {{
        const source = normalizedSource();
        if (!source) return;
        const position = Number(audio.currentTime || 0);
        try {{
          sessionStorage.setItem(storageKey, JSON.stringify({{
            source,
            position: Number.isFinite(position) ? position : 0,
            playing: Boolean(playing),
            context: pageContext,
            updatedAt: Date.now(),
          }}));
        }} catch (_) {{}}
      }};
      audio.addEventListener('timeupdate', () => {{
        const second = Math.floor(Number(audio.currentTime || 0));
        if (second === lastWrittenSecond || second % 2 !== 0) return;
        lastWrittenSecond = second;
        saveState(true);
      }});
      audio.addEventListener('play', () => saveState(true));
      audio.addEventListener('pause', () => saveState(false));
      audio.addEventListener('ended', () => saveState(false));
      window.addEventListener('pagehide', () => saveState(!audio.paused), {{once: true}});
    }})();
    """


def render_page_music_control(context: str) -> None:
    """Render one low-volume playlist with an explicit, persisted autoplay preference."""
    guest_mode = current_page_context().principal.mode is AccessMode.GUEST
    autoplay_enabled = music_autoplay_enabled()
    profile_preference = str(preference_get("music_profile", "auto"))
    if profile_preference not in MUSIC_PROFILE_PREFERENCES:
        profile_preference = "auto"
    resolved_profile = resolve_music_profile(profile_preference, current_theme())
    tracks = _tracks_for_page(
        context,
        profile=resolved_profile,
        guest_mode=guest_mode,
    )
    online_settings = YouTubeSettings.from_environment()
    if not tracks and (guest_mode or not online_settings.enabled):
        return

    def close_panel() -> None:
        panel.set_visibility(False)
        ui.run_javascript("document.querySelector('[data-testid=page-music-button]')?.focus()")

    with ui.card().classes("sy-music-dialog w-full max-w-lg p-0").props(
        f'role=region aria-label="{attr(t("page_music"))}" tabindex=-1 data-testid=page-music-dialog'
    ) as panel:
        with ui.column().classes("w-full gap-0"):
            with ui.row().classes("sy-music-dialog-header w-full items-start justify-between gap-4"):
                with ui.row().classes("items-center gap-3 no-wrap"):
                    ui.icon("headphones").classes("sy-music-dialog-icon").props("aria-hidden=true")
                    with ui.column().classes("gap-0 min-w-0"):
                        ui.label(t("page_music")).classes("sy-music-dialog-title")
                        ui.label(music_context_label(context)).classes("sy-music-dialog-context")
                ui.button(icon="close", on_click=close_panel).props(
                    f'flat round aria-label="{attr(t("close"))}"'
                )

            with ui.column().classes("w-full gap-4 p-5"):
                ui.label(t("music_optional_notice")).classes("text-sm leading-6 text-[var(--sy-muted)]")
                initial_state = "starting" if autoplay_enabled and tracks else "off"
                with ui.row().classes("sy-music-playback-status items-center gap-2").props(
                    "role=status aria-live=polite"
                ):
                    ui.icon("circle").classes("sy-music-status-dot").props("aria-hidden=true")
                    ui.label(t(f"music_status_{initial_state}")).props(
                        f"data-testid=music-playback-status data-music-state={initial_state}"
                    )
                autoplay_switch = ui.switch(
                    t("music_autoplay"),
                    value=autoplay_enabled,
                ).props("name=music-autoplay data-testid=music-autoplay-switch").classes(
                    "sy-tactile-toggle"
                )
                ui.label(t("music_autoplay_hint")).classes("text-xs leading-5 text-[var(--sy-muted)] -mt-3")

                def change_autoplay(event: events.ValueChangeEventArguments) -> None:
                    enabled = bool(event.value)
                    set_music_autoplay(enabled)
                    if enabled:
                        ui.run_javascript(_music_attempt_script(volume=preferred_music_volume()))
                        ui.notify(t("music_autoplay_on"), type="positive", timeout=2_500)
                    else:
                        ui.run_javascript(
                            "document.querySelectorAll('audio.sy-page-music-audio').forEach(audio => audio.pause());"
                            + _music_state_script("off")
                        )
                        ui.notify(t("music_autoplay_off"), type="info", timeout=2_500)

                autoplay_switch.on_value_change(change_autoplay)
                profile_select = ui.select(
                    label=t("music_profile"),
                    options={
                        "auto": t("music_profile_auto"),
                        "bright": t("music_profile_bright"),
                        "quiet": t("music_profile_quiet"),
                    },
                    value=profile_preference,
                ).props("name=music-profile autocomplete=off").classes("w-full")

                def choose_profile(event: events.ValueChangeEventArguments) -> None:
                    preference = str(event.value)
                    if preference not in MUSIC_PROFILE_PREFERENCES:
                        return
                    preference_set("music_profile", preference)
                    ui.navigate.reload()

                profile_select.on_value_change(choose_profile)
                ui.label(t("music_profile_auto_hint")).classes("text-xs leading-5 text-[var(--sy-muted)]")

                if not bool(preference_get("audio_setup_seen", False)):
                    with ui.column().classes("sy-audio-setup w-full gap-3 p-4") as audio_setup:
                        ui.label(t("audio_setup_title")).classes("font-semibold")
                        ui.label(t("audio_setup_notice")).classes("text-sm leading-6 text-[var(--sy-muted)]")

                        def enable_and_preview() -> None:
                            set_sound_feedback(True)
                            preference_set("audio_setup_seen", True)
                            play_interface_sound("success", force=True)
                            audio_setup.set_visibility(False)

                        def keep_quiet() -> None:
                            set_sound_feedback(False)
                            preference_set("audio_setup_seen", True)
                            audio_setup.set_visibility(False)

                        with ui.row().classes("w-full gap-3 flex-wrap"):
                            ui.button(t("enable_and_test_sound"), icon="volume_up", on_click=enable_and_preview)
                            ui.button(t("keep_quiet"), icon="volume_off", on_click=keep_quiet).props("flat")

                if tracks:
                    track_by_id = {track.id: track for track in tracks}
                    track_ids = list(track_by_id)
                    saved_track = str(preference_get(f"music_track_{context}", track_ids[0]))
                    selected_track_id = saved_track if saved_track in track_by_id else track_ids[0]
                    saved_mode = str(preference_get("music_playback_mode", "sequential"))
                    playback_mode = saved_mode if saved_mode in {"sequential", "shuffle"} else "sequential"

                    track_select = ui.select(
                        label=t("music_track"),
                        options={track.id: music_track_label(track) for track in tracks},
                        value=selected_track_id,
                    ).props("name=music-track autocomplete=off").classes("sy-music-track-select w-full")
                    mode_select = ui.select(
                        label=t("music_playback_mode"),
                        options={"sequential": t("music_mode_sequential"), "shuffle": t("music_mode_shuffle")},
                        value=playback_mode,
                    ).props("name=music-playback-mode autocomplete=off").classes("sy-music-mode-select w-full")
                    now_playing = ui.label(music_track_label(track_by_id[selected_track_id])).classes("sy-music-now-playing").props("aria-live=polite")
                    audio = ui.audio(track_by_id[selected_track_id].asset_url, controls=True, autoplay=False, muted=False, loop=False)
                    audio.classes("sy-page-music-audio w-full").props(
                        f'preload=metadata aria-label="{attr(t("page_music"))}"'
                    )

                    audio.on("play", lambda: ui.run_javascript(_music_state_script("playing")))
                    audio.on(
                        "pause",
                        lambda: ui.run_javascript(
                            _music_state_script("paused" if music_autoplay_enabled() else "off")
                        ),
                    )

                    def load_track(track_id: str, *, continue_playback: bool) -> None:
                        track = track_by_id.get(track_id)
                        if track is None:
                            return
                        preference_set(f"music_track_{context}", track.id)
                        audio.pause()
                        audio.set_source(track.asset_url)
                        now_playing.set_text(music_track_label(track))
                        if continue_playback:
                            ui.timer(0.16, audio.play, once=True)

                    def choose_track(event: events.ValueChangeEventArguments) -> None:
                        load_track(str(event.value), continue_playback=False)

                    def choose_mode(event: events.ValueChangeEventArguments) -> None:
                        mode = str(event.value)
                        if mode in {"sequential", "shuffle"}:
                            preference_set("music_playback_mode", mode)

                    def advance_playlist() -> None:
                        current = str(track_select.value or track_ids[0])
                        mode = str(mode_select.value or "sequential")
                        following = next_track_id(track_ids, current, mode)
                        track_select.value = following
                        track_select.update()
                        load_track(following, continue_playback=True)

                    track_select.on_value_change(choose_track)
                    mode_select.on_value_change(choose_mode)
                    audio.on("ended", advance_playlist)
                    ui.label(t("music_loop_notice")).classes("text-xs leading-5 text-[var(--sy-muted)]")
                    with ui.row().classes("sy-music-recovery-actions w-full gap-3 flex-wrap"):
                        retry_button = ui.button(t("music_retry_playback"), icon="play_arrow").props(
                            "outline data-testid=music-play-retry"
                        )
                        retry_button.on(
                            "click",
                            js_handler=_music_retry_handler_script(volume=preferred_music_volume()),
                        )
                        pause_button = ui.button(t("music_pause_now"), icon="pause").props(
                            "flat data-testid=music-pause-now"
                        )
                        pause_button.on("click", js_handler=_music_pause_handler_script())
                    ui.timer(
                        0.12,
                        lambda: ui.run_javascript(_music_continuity_script(context)),
                        once=True,
                    )
                if not guest_mode:
                    render_youtube_panel(context, online_settings)
    panel.set_visibility(False)
    panel.on("keydown.escape", close_panel)

    if tracks and autoplay_enabled:
        ui.timer(
            0.35,
            lambda: ui.run_javascript(
                "(() => {"
                "const audio = document.querySelector('audio.sy-page-music-audio');"
                "if (!audio) return;"
                "if (audio.dataset.syContinuityPlaying === 'false') {"
                f"{_music_state_script('paused')}"
                "return;"
                "}"
                f"{_music_attempt_script(volume=preferred_music_volume())}"
                "})()"
            ),
            once=True,
        )

    def open_dialog() -> None:
        panel.set_visibility(True)
        ui.timer(
            0.12,
            lambda: ui.run_javascript(
                "document.querySelector('[data-testid=page-music-dialog]')?.focus();"
                "document.querySelectorAll('audio.sy-page-music-audio').forEach(a => {"
                f"a.volume = {preferred_music_volume()!r}; a.dataset.syBaseVolume = String(a.volume);"
                "});"
            ),
            once=True,
        )

    initial_trigger_state = "starting" if autoplay_enabled and tracks else "off"
    ui.button(icon="headphones", on_click=open_dialog).props(
        f'flat round aria-label="{attr(t("page_music"))} — '
        f'{attr(t(f"music_status_{initial_trigger_state}"))}" '
        f'data-testid=page-music-button data-music-state={initial_trigger_state} '
        'data-sy-icon-motion-role=play data-sy-icon-story-category=persistent'
    ).classes("sy-music-trigger").style("color: var(--sy-nav-ink) !important").tooltip(t("page_music"))


def render_music_library_settings() -> None:
    """Render audio preferences and guided local-import management in Settings."""
    library = MusicLibrary()
    context_options = {context: music_context_label(context) for context in MUSIC_CONTEXTS}
    render_youtube_settings()

    with ui.card().classes(
        "sy-surface sy-settings-section sy-settings-preference "
        "sy-audio-settings sy-operations-panel w-full p-6"
    ).props("data-testid=audio-settings"):
        with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
            with ui.column().classes("gap-1 max-w-2xl"):
                ui.label(t("audio_preferences")).classes("text-lg font-semibold")
                ui.label(t("audio_preferences_intro")).classes("text-sm leading-6 text-[var(--sy-muted)]")
            ui.icon("graphic_eq").classes("sy-settings-section-icon").props("aria-hidden=true")

        sound_switch = ui.switch(t("interface_sounds"), value=sound_feedback_enabled()).props("name=interface-sounds").classes("mt-4 sy-tactile-toggle")
        autoplay_switch = ui.switch(
            t("music_autoplay"),
            value=music_autoplay_enabled(),
        ).props("name=settings-music-autoplay data-testid=settings-music-autoplay").classes(
            "sy-tactile-toggle"
        )
        ui.label(t("music_autoplay_hint")).classes("text-xs leading-5 text-[var(--sy-muted)]")
        sound_slider = ui.slider(min=0, max=100, value=round(preferred_sound_volume() * 100)).props(
            f'label aria-label="{attr(t("interface_sound_volume"))}"'
        ).classes("w-full max-w-md")
        ui.label(t("interface_sound_volume")).classes("text-xs text-[var(--sy-muted)]")
        music_slider = ui.slider(min=0, max=60, value=round(preferred_music_volume() * 100)).props(
            f'label aria-label="{attr(t("music_volume"))}"'
        ).classes("w-full max-w-md mt-2")
        ui.label(t("music_volume")).classes("text-xs text-[var(--sy-muted)]")

        def change_sound_enabled(event: events.ValueChangeEventArguments) -> None:
            enabled = bool(event.value)
            set_sound_feedback(enabled)
            preference_set("audio_setup_seen", True)
            if enabled:
                play_interface_sound("success", force=True)
                ui.notify(t("sound_feedback_on"), type="positive", timeout=2_500)
            else:
                ui.notify(t("sound_feedback_off"), type="info", timeout=2_500)

        def change_sound_volume(event: events.ValueChangeEventArguments) -> None:
            set_sound_volume(float(event.value) / 100)

        def change_music_autoplay(event: events.ValueChangeEventArguments) -> None:
            enabled = bool(event.value)
            set_music_autoplay(enabled)
            if enabled:
                ui.run_javascript(_music_attempt_script(volume=preferred_music_volume()))
                ui.notify(t("music_autoplay_on"), type="positive", timeout=2_500)
            else:
                ui.run_javascript(
                    "document.querySelectorAll('audio.sy-page-music-audio').forEach(audio => audio.pause());"
                    + _music_state_script("off")
                )
                ui.notify(t("music_autoplay_off"), type="info", timeout=2_500)

        def change_music_volume(event: events.ValueChangeEventArguments) -> None:
            set_music_volume(float(event.value) / 100)
            ui.run_javascript(
                f"document.querySelectorAll('audio.sy-page-music-audio').forEach(a => {{ a.volume = {preferred_music_volume()!r}; a.dataset.syBaseVolume = String(a.volume); }});"
            )

        sound_switch.on_value_change(change_sound_enabled)
        autoplay_switch.on_value_change(change_music_autoplay)
        sound_slider.on_value_change(change_sound_volume)
        music_slider.on_value_change(change_music_volume)
        ui.button(t("test_interface_sound"), icon="volume_up", on_click=lambda: play_interface_sound("success", force=True)).props("outline").classes("mt-3")

    with ui.card().classes(
        "sy-surface sy-settings-section sy-settings-preference "
        "sy-music-settings sy-operations-panel w-full p-6"
    ).props("data-testid=music-library-settings"):
        with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
            with ui.column().classes("gap-1 max-w-2xl"):
                ui.label(t("music_library")).classes("text-lg font-semibold")
                ui.label(t("music_library_intro")).classes("text-sm leading-6 text-[var(--sy-muted)]")
            ui.icon("library_music").classes("sy-settings-section-icon").props("aria-hidden=true")

        with ui.expansion(t("music_usage_guide"), icon="help_outline").classes("w-full mt-4"):
            ui.label(t("music_usage_steps")).classes("text-sm leading-7 text-[var(--sy-muted)]")
            ui.label(t("music_rights_notice")).classes("text-sm leading-7 text-[var(--sy-muted)] mt-2")

        profile_preference = str(preference_get("music_profile", "auto"))
        if profile_preference not in MUSIC_PROFILE_PREFERENCES:
            profile_preference = "auto"
        profile_select = ui.select(
            label=t("music_profile"),
            options={
                "auto": t("music_profile_auto"),
                "bright": t("music_profile_bright"),
                "quiet": t("music_profile_quiet"),
            },
            value=profile_preference,
        ).props("name=settings-music-profile autocomplete=off").classes("w-full max-w-md mt-4")

        def save_profile(event: events.ValueChangeEventArguments) -> None:
            preference = str(event.value)
            if preference in MUSIC_PROFILE_PREFERENCES:
                preference_set("music_profile", preference)

        profile_select.on_value_change(save_profile)
        ui.label(t("music_profile_auto_hint")).classes("text-xs leading-5 text-[var(--sy-muted)] max-w-2xl")

        ui.separator().classes("my-5")
        ui.label(t("import_local_music")).classes("font-semibold")
        ui.label(t("import_local_music_notice")).classes("text-sm leading-6 text-[var(--sy-muted)]")
        upload_context = ui.select(
            label=t("music_page_category"),
            options=context_options,
            value="dashboard",
        ).props("name=music-page-category autocomplete=off").classes("w-full max-w-md mt-3")

        async def import_audio(event: events.UploadEventArguments) -> None:
            try:
                content = await event.file.read()
                library.add_local_audio(original_name=event.file.name, content=content, context=str(upload_context.value))
            except MusicLibraryError as error:
                ui.notify(t(f"music_error_{error.code}"), type="negative", timeout=7_000)
                return
            ui.notify(t("music_imported"), type="positive")
            ui.navigate.reload()

        ui.upload(
            label=t("choose_audio_files"),
            multiple=True,
            max_file_size=MAX_AUDIO_BYTES,
            max_total_size=150 * 1024 * 1024,
            max_files=12,
            on_upload=import_audio,
            on_rejected=lambda: ui.notify(t("music_error_size"), type="negative"),
            auto_upload=True,
        ).props("accept=.m4a,.mp3,.ogg,.wav").classes("w-full max-w-2xl mt-3")

        ui.separator().classes("my-5")
        ui.label(t("youtube_local_import_title")).classes("font-semibold")
        ui.label(t("youtube_local_import_intro")).classes("text-sm leading-6 text-[var(--sy-muted)]")
        ui.label(t("youtube_local_import_rights")).classes("text-xs leading-5 text-[var(--sy-muted)] mt-1")
        if youtube_import_ready():
            import_url = ui.input(label=t("youtube_local_import_url")).props(
                "name=youtube-local-import-url type=url autocomplete=off inputmode=url"
            ).classes("w-full max-w-2xl mt-3")
            import_context = ui.select(
                label=t("music_page_category"),
                options=context_options,
                value="devotional",
            ).props("name=youtube-local-import-context autocomplete=off").classes("w-full max-w-md")
            import_status = ui.label(t("youtube_local_import_working")).classes(
                "sy-inline-progress text-sm leading-6 text-[var(--sy-muted)]"
            ).props("role=status aria-live=polite")
            import_status.set_visibility(False)

            async def import_from_youtube() -> None:
                download_button.disable()
                import_status.set_visibility(True)
                try:
                    result = await run.io_bound(
                        YouTubeAudioImporter().import_url,
                        url=str(import_url.value or ""),
                        context=str(import_context.value),
                    )
                except YouTubeAudioImportError as error:
                    key = (
                        f"youtube_import_error_{error.code}"
                        if error.code in {"url", "download", "no_audio", "total_size", "duplicate"}
                        else f"music_error_{error.code}"
                    )
                    ui.notify(t(key), type="negative", timeout=8_000)
                    return
                finally:
                    import_status.set_visibility(False)
                    download_button.enable()
                ui.notify(t("youtube_local_import_done").format(count=len(result.tracks)), type="positive")
                ui.navigate.reload()

            download_button = ui.button(
                t("youtube_local_import_action"),
                icon="download_for_offline",
                on_click=import_from_youtube,
            ).classes("mt-2")
        else:
            with ui.element("aside").classes("sy-inline-empty w-full mt-3").props("role=status"):
                ui.icon("download_for_offline").classes("sy-inline-empty-icon").props("aria-hidden=true")
                ui.label(t("youtube_local_import_unavailable")).classes("sy-inline-empty-copy")

        custom_tracks = library.all_custom_tracks()
        if custom_tracks:
            ui.separator().classes("my-5")
            ui.label(t("custom_music_items")).classes("font-semibold")
            with ui.column().classes("w-full gap-2 mt-2"):
                for track in custom_tracks:
                    _render_removable_music_item(
                        title=music_track_label(track),
                        context=track.contexts[0],
                        remove=lambda track_id=track.id: library.remove_local_audio(track_id),
                    )
        else:
            with ui.element("aside").classes("sy-inline-empty w-full mt-5").props(
                f'role=status aria-label="{attr(t("music_no_custom_tracks_title"))}"'
            ):
                ui.icon("queue_music").classes("sy-inline-empty-icon").props("aria-hidden=true")
                with ui.column().classes("gap-0 min-w-0"):
                    ui.label(t("music_no_custom_tracks_title")).classes("sy-inline-empty-title")
                    ui.label(t("music_no_custom_tracks_body")).classes("sy-inline-empty-copy")


def render_guest_music_settings() -> None:
    """Expose session-only playback preferences without any guest file or URL input."""

    with ui.card().classes(
        "sy-surface sy-settings-section sy-settings-preference "
        "sy-audio-settings sy-operations-panel w-full p-6"
    ).props(
        "data-testid=guest-audio-settings"
    ):
        with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
            with ui.column().classes("gap-1 max-w-2xl"):
                ui.label(t("audio_preferences")).classes("text-lg font-semibold")
                ui.label(t("access_guest_mode_body")).classes(
                    "text-sm leading-6 text-[var(--sy-muted)]"
                )
            ui.icon("headphones").classes("sy-settings-section-icon").props("aria-hidden=true")

        sound_switch = ui.switch(
            t("interface_sounds"),
            value=sound_feedback_enabled(),
        ).props("name=guest-interface-sounds").classes("mt-4 sy-tactile-toggle")
        autoplay_switch = ui.switch(
            t("music_autoplay"),
            value=music_autoplay_enabled(),
        ).props("name=guest-music-autoplay data-testid=guest-music-autoplay").classes(
            "sy-tactile-toggle"
        )
        profile_select = ui.select(
            label=t("music_profile"),
            options={
                "auto": t("music_profile_auto"),
                "bright": t("music_profile_bright"),
                "quiet": t("music_profile_quiet"),
            },
            value=str(preference_get("music_profile", "auto")),
        ).props("name=guest-music-profile autocomplete=off").classes("w-full max-w-md")

        def change_sound(event: events.ValueChangeEventArguments) -> None:
            set_sound_feedback(bool(event.value))
            if event.value:
                play_interface_sound("success", force=True)

        def change_autoplay(event: events.ValueChangeEventArguments) -> None:
            set_music_autoplay(bool(event.value))

        def change_profile(event: events.ValueChangeEventArguments) -> None:
            value = str(event.value)
            if value in MUSIC_PROFILE_PREFERENCES:
                preference_set("music_profile", value)

        sound_switch.on_value_change(change_sound)
        autoplay_switch.on_value_change(change_autoplay)
        profile_select.on_value_change(change_profile)
        ui.label(t("access_restricted_body")).classes(
            "text-xs leading-5 text-[var(--sy-muted)] mt-2"
        )


def _render_removable_music_item(*, title: str, context: str, remove) -> None:  # type: ignore[no-untyped-def]
    with ui.row().classes("sy-music-library-item w-full items-center justify-between gap-3"):
        with ui.column().classes("gap-0 min-w-0"):
            ui.label(title).classes("font-medium")
            ui.label(music_context_label(context)).classes("text-xs text-[var(--sy-muted)]")
        with ui.dialog() as confirm_dialog, ui.card().classes("sy-surface w-full max-w-sm p-6"):
            ui.label(t("remove_music_item")).classes("text-lg font-semibold")
            ui.label(t("remove_music_item_notice")).classes("text-sm leading-6 text-[var(--sy-muted)] mt-2")

            def confirm_remove() -> None:
                try:
                    remove()
                except MusicLibraryError as error:
                    ui.notify(t(f"music_error_{error.code}"), type="negative")
                    return
                confirm_dialog.close()
                ui.notify(t("music_item_removed"), type="positive")
                ui.navigate.reload()

            with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5"):
                ui.button(t("cancel"), on_click=confirm_dialog.close).props("flat")
                ui.button(t("remove"), icon="delete_outline", on_click=confirm_remove).props("color=negative")
        ui.button(icon="delete_outline", on_click=confirm_dialog.open).props(
            f'flat round color=negative aria-label="{attr(t("remove_music_item"))}"'
        )
