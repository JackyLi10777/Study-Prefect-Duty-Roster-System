"""Visible, policy-compliant YouTube player and public-playlist management."""

from __future__ import annotations

from typing import Any

from nicegui import events, run, ui

from nicegui_app.services.music_library import MUSIC_CONTEXTS, MusicLibraryError
from nicegui_app.services.online_music import (
    YouTubePlaylistLibrary,
    YouTubeSettings,
    search_youtube,
    youtube_embed_url,
)
from nicegui_app.ui.i18n import t


def render_youtube_settings() -> None:
    settings = YouTubeSettings.from_environment()
    library = YouTubePlaylistLibrary()
    context_options = {context: t(f"music_context_{context}") for context in MUSIC_CONTEXTS}
    with ui.card().classes("sy-surface sy-settings-section sy-online-music-settings w-full max-w-3xl p-6").props("data-testid=online-music-settings"):
        with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
            with ui.column().classes("gap-1 max-w-2xl"):
                ui.label(t("youtube_player_title")).classes("text-lg font-semibold")
                ui.label(t("youtube_player_intro")).classes("text-sm leading-6 text-[var(--sy-muted)]")
            ui.icon("smart_display").classes("sy-settings-section-icon").props("aria-hidden=true")
        if not settings.enabled:
            ui.label(t("youtube_disabled")).classes("sy-online-music-status mt-4")
            return
        ui.label(t("youtube_free_ready")).classes("sy-online-music-status sy-online-music-status--ready mt-4")
        ui.label(t("youtube_api_ready") if settings.search_enabled else t("youtube_api_optional")).classes(
            "text-sm leading-6 text-[var(--sy-muted)]"
        )
        title = ui.input(label=t("playlist_title")).props(
            "name=youtube-playlist-title autocomplete=off"
        ).classes("w-full max-w-2xl mt-4")
        url = ui.input(label=t("youtube_playlist_url")).props(
            "name=youtube-playlist-url type=url autocomplete=off inputmode=url"
        ).classes("w-full max-w-2xl")
        context = ui.select(label=t("music_page_category"), options=context_options, value="devotional").classes("w-full max-w-md")

        def save() -> None:
            try:
                library.add(title=str(title.value or ""), url_or_id=str(url.value or ""), context=str(context.value))
            except MusicLibraryError as error:
                ui.notify(t(f"music_error_{error.code}"), type="negative")
                return
            ui.notify(t("youtube_playlist_saved"), type="positive")
            ui.navigate.reload()

        ui.button(t("youtube_playlist_save"), icon="playlist_add", on_click=save).props("outline").classes("mt-2")
        playlists = library.all()
        if playlists:
            with ui.column().classes("w-full gap-2 mt-5"):
                for playlist in playlists:
                    with ui.row().classes("sy-music-library-item w-full items-center justify-between gap-3"):
                        with ui.column().classes("gap-0"):
                            ui.label(playlist.title).classes("font-medium")
                            ui.label(t(f"music_context_{playlist.context}")).classes("text-xs text-[var(--sy-muted)]")
                        ui.button(
                            icon="delete_outline",
                            on_click=lambda playlist_id=playlist.id: _remove_playlist(library, playlist_id),
                        ).props(f'flat round color=negative aria-label="{t("remove_music_item")}"')
        else:
            with ui.element("aside").classes("sy-inline-empty w-full mt-5").props(
                f'role=status aria-label="{t("youtube_library_empty_title")}"'
            ):
                ui.icon("playlist_add").classes("sy-inline-empty-icon").props("aria-hidden=true")
                with ui.column().classes("gap-0 min-w-0"):
                    ui.label(t("youtube_library_empty_title")).classes("sy-inline-empty-title")
                    ui.label(t("youtube_library_empty_body")).classes("sy-inline-empty-copy")


def render_youtube_panel(context: str, settings: YouTubeSettings) -> None:
    if not settings.enabled:
        return
    library = YouTubePlaylistLibrary()
    playlists = library.for_context(context)
    with ui.column().classes("sy-youtube-panel w-full gap-4").props("data-testid=youtube-player-panel"):
        ui.separator()
        ui.label(t("youtube_player_title")).classes("font-semibold")
        ui.label(t("youtube_visible_notice")).classes("text-xs leading-5 text-[var(--sy-muted)]")
        player = ui.column().classes("sy-youtube-frame-wrap w-full")

        def show(*, playlist_id: str | None = None, video_id: str | None = None) -> None:
            source = youtube_embed_url(playlist_id=playlist_id, video_id=video_id)
            player.clear()
            with player:
                ui.html(
                    f'<iframe class="sy-youtube-player" src="{source}" title="YouTube" '
                    'allow="encrypted-media; picture-in-picture" allowfullscreen '
                    'loading="lazy" referrerpolicy="no-referrer"></iframe>'
                ).classes("w-full")

        if playlists:
            playlist_by_id = {item.id: item for item in playlists}
            select = ui.select(
                label=t("youtube_saved_playlist"),
                options={item.id: item.title for item in playlists},
                value=playlists[0].id,
            ).classes("w-full")

            def choose(event: events.ValueChangeEventArguments) -> None:
                selected = playlist_by_id.get(str(event.value))
                if selected:
                    show(playlist_id=selected.playlist_id)

            select.on_value_change(choose)
            show(playlist_id=playlists[0].playlist_id)
        else:
            with ui.element("aside").classes("sy-inline-empty w-full").props("role=status"):
                ui.icon("queue_music").classes("sy-inline-empty-icon").props("aria-hidden=true")
                ui.label(t("youtube_no_playlist")).classes("sy-inline-empty-copy")

        if settings.search_enabled:
            search_input = ui.input(label=t("youtube_search"), placeholder=t("youtube_search_example")).props(
                "name=youtube-search autocomplete=off"
            ).classes("w-full")
            search_button = ui.button(t("youtube_search_action"), icon="search")
            results = ui.column().classes("w-full gap-2")

            async def search() -> None:
                term = str(search_input.value or "").strip()
                if len(term) < 2:
                    ui.notify(t("youtube_search_needed"), type="warning")
                    return
                search_button.disable()
                try:
                    items = await run.io_bound(search_youtube, term, settings)
                except Exception:
                    ui.notify(t("youtube_search_error"), type="negative")
                    return
                finally:
                    search_button.enable()
                results.clear()
                with results:
                    if not items:
                        ui.label(t("youtube_no_results")).classes("text-sm text-[var(--sy-muted)]")
                    for item in items:
                        _render_search_result(item, show)

            search_button.on_click(search)
            search_input.on("keydown.enter", search)
        else:
            ui.label(t("youtube_search_setup_hint")).classes("text-xs leading-5 text-[var(--sy-muted)]")


def _render_search_result(item: dict[str, Any], show) -> None:  # type: ignore[no-untyped-def]
    with ui.row().classes("sy-youtube-result w-full items-center gap-3 no-wrap"):
        thumbnail = str(item.get("thumbnail") or "")
        if thumbnail:
            ui.image(thumbnail).classes("sy-youtube-thumbnail").props('alt="" loading=lazy width=320 height=180')
        with ui.column().classes("gap-0 min-w-0 grow"):
            ui.label(str(item["title"])).classes("font-medium")
            ui.label(str(item["channel"])).classes("text-xs text-[var(--sy-muted)]")
        if item["kind"] == "playlist":
            ui.button(icon="play_arrow", on_click=lambda: show(playlist_id=str(item["id"]))).props(
                f'flat round aria-label="{t("youtube_search_action")}"'
            )
        else:
            ui.button(icon="play_arrow", on_click=lambda: show(video_id=str(item["id"]))).props(
                f'flat round aria-label="{t("youtube_search_action")}"'
            )


def _remove_playlist(library: YouTubePlaylistLibrary, playlist_id: str) -> None:
    try:
        library.remove(playlist_id)
    except MusicLibraryError as error:
        ui.notify(t(f"music_error_{error.code}"), type="negative")
        return
    ui.notify(t("music_item_removed"), type="positive")
    ui.navigate.reload()
