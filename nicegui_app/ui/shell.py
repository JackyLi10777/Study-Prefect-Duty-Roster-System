"""Shared navigation shell with persistent theme and language preferences."""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator
import re

from nicegui import ui

from nicegui_app.application_mode import current_application_mode
from nicegui_app.contact import FEEDBACK_EMAIL, FEEDBACK_MAILTO_URL, GITHUB_REPOSITORY_URL
from nicegui_app.runtime import get_workflow
from nicegui_app.ui.i18n import current_locale, t, toggle_locale
from nicegui_app.ui.music import render_page_music_control
from nicegui_app.ui.sound import play_interface_sound
from nicegui_app.ui.theme import apply_theme, current_theme, sound_feedback_enabled, toggle_sound_feedback, toggle_theme


NAVIGATION_GROUPS = (
    ("nav_weekly_work", (("/", "dashboard", "space_dashboard"), ("/rosters", "rosters", "calendar_month"))),
    ("nav_people_fairness", (("/prefects", "prefects", "groups"),)),
    ("nav_support_system", (("/handover", "handover", "handshake"), ("/access-control", "access_control", "admin_panel_settings"), ("/settings", "settings", "settings"))),
    ("nav_reference", (("/platform", "platform", "domain"), ("/engineering", "engineering", "build_circle"), ("/system-architecture", "system_architecture", "account_tree"), ("/getting-started", "getting_started", "play_circle"), ("/guide", "operator_guide", "help_outline"), ("/devotional", "devotional", "menu_book"))),
)

_ACCESS_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _verified_gateway_identity() -> str:
    """Read only the trusted identity header injected by the loopback-only gateway."""
    try:
        request = ui.context.client.request
        value = request.headers.get("x-sing-yin-access-email", "").strip().lower()
    except (AttributeError, RuntimeError):
        return ""
    return value if _ACCESS_EMAIL.fullmatch(value) else ""


def _reload_after_preference_change(change) -> None:
    change()
    ui.navigate.reload()


def _navigate_with_sound(path: str) -> None:
    play_interface_sound("navigation")
    ui.navigate.to(path)


@contextmanager
def page_shell(title_key: str, active_path: str, *, music_context: str | None = None) -> Iterator[None]:
    apply_theme()
    application_mode = current_application_mode()
    drawer = ui.left_drawer(value=False, bordered=False).props(
        f'show-if-above role=navigation aria-label="{t("main_navigation")}"'
    ).classes("sy-sidebar bg-[var(--sy-surface)]")
    with drawer:
        with ui.column().classes("w-full gap-1 p-4"):
            with ui.row().classes("items-center gap-3 mb-2"):
                ui.image("/assets/brand/sing-yin-crest-navigation.png").classes("sy-brand-mark").props(
                    f'alt="{t("school_crest_alt")}" width=545 height=524 fetchpriority=high'
                )
                ui.label(t("app_name")).classes("text-base font-bold leading-tight sy-fg-stable")
            ui.label(t("service_principle")).classes("text-xs italic text-[var(--sy-muted)] mb-5")
            for group_key, items in NAVIGATION_GROUPS:
                ui.label(t(group_key)).classes("sy-nav-section")
                for path, key, icon in items:
                    button = ui.button(t(key), icon=icon, on_click=lambda target=path: _navigate_with_sound(target)).props("flat align=left").classes("w-full justify-start").style("color: var(--sy-nav-ink) !important")
                    if path == active_path:
                        button.classes("sy-nav-active").props("aria-current=page")
            with ui.element("aside").classes("sy-sidebar-feedback").props(
                f'aria-label="{t("feedback_channel_title")}" data-testid=sidebar-feedback'
            ):
                with ui.row().classes("items-center gap-2 no-wrap"):
                    ui.icon("mail_outline").classes("sy-sidebar-feedback-icon").props("aria-hidden=true")
                    ui.label(t("feedback_channel_short")).classes("sy-sidebar-feedback-title")
                ui.label(t("feedback_channel_sidebar_body")).classes("sy-sidebar-feedback-copy")
                ui.link(FEEDBACK_EMAIL, FEEDBACK_MAILTO_URL).classes("sy-sidebar-feedback-link").props(
                    f'aria-label="{t("feedback_email_action")}: {FEEDBACK_EMAIL}"'
                )
                ui.link(t("github_repository_short"), GITHUB_REPOSITORY_URL).classes("sy-sidebar-feedback-link").props(
                    f'target=_blank rel="noopener noreferrer" aria-label="{t("github_repository_action")}"'
                )
    gateway_identity = _verified_gateway_identity()
    with ui.header(elevated=False).classes("sy-app-header bg-[var(--sy-surface)] border-b border-[var(--sy-line)] px-4"):
        skip_link = ui.link(t("skip_to_content"), "#main-content").classes("sy-skip-link")
        skip_link.on(
            "click",
            lambda: ui.run_javascript(
                "const main=document.getElementById('main-content'); if(main){main.focus({preventScroll:true}); main.scrollIntoView();}"
            ),
        )
        with ui.row().classes("sy-header-bar w-full items-center justify-between"):
            with ui.row().classes("items-center gap-2"):
                ui.button(icon="menu", on_click=drawer.toggle).props(
                    f'flat round aria-label="{t("open_navigation")}"'
                ).classes("sy-icon-control").style("color: var(--sy-nav-ink) !important").tooltip(t("open_navigation"))
                ui.label(t(title_key)).classes("sy-header-title text-lg font-semibold").props("role=heading aria-level=1")
            with ui.row().classes("sy-header-tools items-center gap-1"):
                if gateway_identity:
                    ui.badge(t("access_admin_signed_in"), color="positive").props(
                        f'outline aria-label="{t("access_admin_mode")}" data-testid=administrator-mode'
                    ).classes("sy-status-badge")
                    ui.button(
                        icon="logout",
                        on_click=lambda: ui.navigate.to("/logout"),
                    ).props(
                        f'flat round aria-label="{t("access_admin_logout")}" data-testid=administrator-logout'
                    ).classes("sy-admin-logout").tooltip(t("access_admin_logout"))
                if music_context:
                    render_page_music_control(music_context)
                ui.button("EN" if current_locale() != "en" else "中", on_click=lambda: _reload_after_preference_change(toggle_locale)).props("flat dense").classes("sy-language-control").style("color: var(--sy-nav-ink) !important")
                sound_icon = "volume_up" if sound_feedback_enabled() else "volume_off"
                sound_tooltip = t("sound_feedback_on") if sound_feedback_enabled() else t("sound_feedback_off")
                ui.button(icon=sound_icon, on_click=lambda: _reload_after_preference_change(toggle_sound_feedback)).props(
                    f'flat round aria-label="{sound_tooltip}"'
                ).classes("sy-icon-control").style("color: var(--sy-nav-ink) !important").tooltip(sound_tooltip)
                theme_icon = "dark_mode" if current_theme() == "light" else "light_mode"
                tooltip = t("dark_mode") if current_theme() == "light" else t("light_mode")
                ui.button(icon=theme_icon, on_click=lambda: _reload_after_preference_change(toggle_theme)).props(
                    f'flat round aria-label="{tooltip}"'
                ).classes("sy-icon-control").style("color: var(--sy-nav-ink) !important").tooltip(tooltip)
    if application_mode.is_practice:
        with ui.element("section").props(
            "data-testid=practice-mode-banner role=status aria-live=polite"
        ).classes("sy-practice-banner"):
            ui.icon("science").classes("sy-practice-banner-icon").props("aria-hidden=true")
            with ui.column().classes("gap-0 min-w-0"):
                ui.label(t("practice_mode_title")).classes("sy-practice-banner-title")
                ui.label(t("practice_mode_body")).classes("sy-practice-banner-copy")
    maintenance = get_workflow().maintenance_status()
    if maintenance.active:
        with ui.element("section").props(
            "data-testid=maintenance-mode-banner role=alert aria-live=assertive"
        ).classes("sy-maintenance-banner"):
            ui.icon("engineering").classes("sy-practice-banner-icon").props("aria-hidden=true")
            with ui.column().classes("gap-0 min-w-0"):
                ui.label(t("maintenance_mode_title")).classes("sy-practice-banner-title")
                ui.label(
                    t("maintenance_recovery_body") if maintenance.recovery_required else t("maintenance_mode_body")
                ).classes("sy-practice-banner-copy")
    with ui.element("main").props("id=main-content tabindex=-1").classes("sy-main w-full gap-6"):
        yield
