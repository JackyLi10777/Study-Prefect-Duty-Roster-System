"""Accessible page-specific music controls and local library management."""

from __future__ import annotations

from nicegui import app, events, ui

from nicegui_app.services.music_library import (
    MAX_AUDIO_BYTES,
    MUSIC_CONTEXTS,
    MusicLibrary,
    MusicLibraryError,
    MusicTrack,
    next_track_id,
)
from nicegui_app.services.online_music import YouTubeSettings
from nicegui_app.ui.youtube_music import render_youtube_panel, render_youtube_settings
from nicegui_app.ui.i18n import t
from nicegui_app.ui.sound import (
    play_interface_sound,
    preferred_music_volume,
    preferred_sound_volume,
    set_music_volume,
    set_sound_volume,
)
from nicegui_app.ui.theme import set_sound_feedback, sound_feedback_enabled


def music_context_label(context: str) -> str:
    return t(f"music_context_{context}")


def render_page_music_control(context: str) -> None:
    """Render one manual, low-volume playlist control for an approved quiet page."""
    library = MusicLibrary()
    tracks = library.tracks_for_context(context)
    online_settings = YouTubeSettings.from_environment()
    if not tracks and not online_settings.enabled:
        return

    with ui.dialog() as dialog, ui.card().classes("sy-music-dialog w-full max-w-lg p-0").props("data-testid=page-music-dialog"):
        with ui.column().classes("w-full gap-0"):
            with ui.row().classes("sy-music-dialog-header w-full items-start justify-between gap-4"):
                with ui.row().classes("items-center gap-3 no-wrap"):
                    ui.icon("headphones").classes("sy-music-dialog-icon").props("aria-hidden=true")
                    with ui.column().classes("gap-0 min-w-0"):
                        ui.label(t("page_music")).classes("sy-music-dialog-title")
                        ui.label(music_context_label(context)).classes("sy-music-dialog-context")
                ui.button(icon="close", on_click=dialog.close).props(f'flat round aria-label="{t("close")}"')

            with ui.column().classes("w-full gap-4 p-5"):
                ui.label(t("music_optional_notice")).classes("text-sm leading-6 text-[var(--sy-muted)]")

                if not bool(app.storage.user.get("audio_setup_seen", False)):
                    with ui.column().classes("sy-audio-setup w-full gap-3 p-4") as audio_setup:
                        ui.label(t("audio_setup_title")).classes("font-semibold")
                        ui.label(t("audio_setup_notice")).classes("text-sm leading-6 text-[var(--sy-muted)]")

                        def enable_and_preview() -> None:
                            set_sound_feedback(True)
                            app.storage.user["audio_setup_seen"] = True
                            play_interface_sound("success", force=True)
                            audio_setup.set_visibility(False)

                        def keep_quiet() -> None:
                            set_sound_feedback(False)
                            app.storage.user["audio_setup_seen"] = True
                            audio_setup.set_visibility(False)

                        with ui.row().classes("w-full gap-3 flex-wrap"):
                            ui.button(t("enable_and_test_sound"), icon="volume_up", on_click=enable_and_preview)
                            ui.button(t("keep_quiet"), icon="volume_off", on_click=keep_quiet).props("flat")

                if tracks:
                    track_by_id = {track.id: track for track in tracks}
                    track_ids = list(track_by_id)
                    saved_track = str(app.storage.user.get(f"music_track_{context}", track_ids[0]))
                    selected_track_id = saved_track if saved_track in track_by_id else track_ids[0]
                    saved_mode = str(app.storage.user.get("music_playback_mode", "sequential"))
                    playback_mode = saved_mode if saved_mode in {"sequential", "shuffle"} else "sequential"

                    track_select = ui.select(
                        label=t("music_track"),
                        options={track.id: track.display_label for track in tracks},
                        value=selected_track_id,
                    ).props("name=music-track autocomplete=off").classes("sy-music-track-select w-full")
                    mode_select = ui.select(
                        label=t("music_playback_mode"),
                        options={"sequential": t("music_mode_sequential"), "shuffle": t("music_mode_shuffle")},
                        value=playback_mode,
                    ).props("name=music-playback-mode autocomplete=off").classes("sy-music-mode-select w-full")
                    now_playing = ui.label(track_by_id[selected_track_id].display_label).classes("sy-music-now-playing").props("aria-live=polite")
                    audio = ui.audio(track_by_id[selected_track_id].asset_url, controls=True, autoplay=False, muted=False, loop=False)
                    audio.classes("sy-page-music-audio w-full").props(f'preload=metadata aria-label="{t("page_music")}"')

                    def load_track(track_id: str, *, continue_playback: bool) -> None:
                        track = track_by_id.get(track_id)
                        if track is None:
                            return
                        app.storage.user[f"music_track_{context}"] = track.id
                        audio.pause()
                        audio.set_source(track.asset_url)
                        now_playing.set_text(track.display_label)
                        if continue_playback:
                            ui.timer(0.16, audio.play, once=True)

                    def choose_track(event: events.ValueChangeEventArguments) -> None:
                        load_track(str(event.value), continue_playback=False)

                    def choose_mode(event: events.ValueChangeEventArguments) -> None:
                        mode = str(event.value)
                        if mode in {"sequential", "shuffle"}:
                            app.storage.user["music_playback_mode"] = mode

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
                render_youtube_panel(context, online_settings)
    def open_dialog() -> None:
        dialog.open()
        ui.timer(
            0.12,
            lambda: ui.run_javascript(
                "document.querySelectorAll('audio.sy-page-music-audio').forEach(a => {"
                f"a.volume = {preferred_music_volume()!r}; a.dataset.syBaseVolume = String(a.volume);"
                "});"
            ),
            once=True,
        )

    ui.button(icon="headphones", on_click=open_dialog).props(f'flat round aria-label="{t("page_music")}" data-testid=page-music-button').classes("sy-music-trigger").style("color: var(--sy-nav-ink) !important").tooltip(t("page_music"))


def render_music_library_settings() -> None:
    """Render audio preferences and guided local-import management in Settings."""
    library = MusicLibrary()
    context_options = {context: music_context_label(context) for context in MUSIC_CONTEXTS}
    render_youtube_settings()

    with ui.card().classes("sy-surface sy-settings-section sy-audio-settings w-full max-w-3xl p-6").props("data-testid=audio-settings"):
        with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
            with ui.column().classes("gap-1 max-w-2xl"):
                ui.label(t("audio_preferences")).classes("text-lg font-semibold")
                ui.label(t("audio_preferences_intro")).classes("text-sm leading-6 text-[var(--sy-muted)]")
            ui.icon("graphic_eq").classes("sy-settings-section-icon").props("aria-hidden=true")

        sound_switch = ui.switch(t("interface_sounds"), value=sound_feedback_enabled()).props("name=interface-sounds").classes("mt-4")
        sound_slider = ui.slider(min=0, max=100, value=round(preferred_sound_volume() * 100)).props(
            f'label aria-label="{t("interface_sound_volume")}"'
        ).classes("w-full max-w-md")
        ui.label(t("interface_sound_volume")).classes("text-xs text-[var(--sy-muted)]")
        music_slider = ui.slider(min=0, max=60, value=round(preferred_music_volume() * 100)).props(
            f'label aria-label="{t("music_volume")}"'
        ).classes("w-full max-w-md mt-2")
        ui.label(t("music_volume")).classes("text-xs text-[var(--sy-muted)]")

        def change_sound_enabled(event: events.ValueChangeEventArguments) -> None:
            set_sound_feedback(bool(event.value))
            app.storage.user["audio_setup_seen"] = True

        def change_sound_volume(event: events.ValueChangeEventArguments) -> None:
            set_sound_volume(float(event.value) / 100)

        def change_music_volume(event: events.ValueChangeEventArguments) -> None:
            set_music_volume(float(event.value) / 100)
            ui.run_javascript(
                f"document.querySelectorAll('audio.sy-page-music-audio').forEach(a => {{ a.volume = {preferred_music_volume()!r}; a.dataset.syBaseVolume = String(a.volume); }});"
            )

        sound_switch.on_value_change(change_sound_enabled)
        sound_slider.on_value_change(change_sound_volume)
        music_slider.on_value_change(change_music_volume)
        ui.button(t("test_interface_sound"), icon="volume_up", on_click=lambda: play_interface_sound("success", force=True)).props("outline").classes("mt-3")

    with ui.card().classes("sy-surface sy-settings-section sy-music-settings w-full max-w-3xl p-6").props("data-testid=music-library-settings"):
        with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
            with ui.column().classes("gap-1 max-w-2xl"):
                ui.label(t("music_library")).classes("text-lg font-semibold")
                ui.label(t("music_library_intro")).classes("text-sm leading-6 text-[var(--sy-muted)]")
            ui.icon("library_music").classes("sy-settings-section-icon").props("aria-hidden=true")

        with ui.expansion(t("music_usage_guide"), icon="help_outline").classes("w-full mt-4"):
            ui.label(t("music_usage_steps")).classes("text-sm leading-7 text-[var(--sy-muted)]")
            ui.label(t("music_rights_notice")).classes("text-sm leading-7 text-[var(--sy-muted)] mt-2")

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

        custom_tracks = library.all_custom_tracks()
        if custom_tracks:
            ui.separator().classes("my-5")
            ui.label(t("custom_music_items")).classes("font-semibold")
            with ui.column().classes("w-full gap-2 mt-2"):
                for track in custom_tracks:
                    _render_removable_music_item(
                        title=track.display_label,
                        context=track.contexts[0],
                        remove=lambda track_id=track.id: library.remove_local_audio(track_id),
                    )
        else:
            with ui.element("aside").classes("sy-inline-empty w-full mt-5").props(
                f'role=status aria-label="{t("music_no_custom_tracks_title")}"'
            ):
                ui.icon("queue_music").classes("sy-inline-empty-icon").props("aria-hidden=true")
                with ui.column().classes("gap-0 min-w-0"):
                    ui.label(t("music_no_custom_tracks_title")).classes("sy-inline-empty-title")
                    ui.label(t("music_no_custom_tracks_body")).classes("sy-inline-empty-copy")


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

            with ui.row().classes("w-full justify-end gap-3 mt-5"):
                ui.button(t("cancel"), on_click=confirm_dialog.close).props("flat")
                ui.button(t("remove"), icon="delete_outline", on_click=confirm_remove).props("color=negative")
        ui.button(icon="delete_outline", on_click=confirm_dialog.open).props(f'flat round color=negative aria-label="{t("remove_music_item")}"')
