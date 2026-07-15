"""Shared navigation shell with persistent theme and language preferences."""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator
import json
import re

from nicegui import ui

from nicegui_app.application_mode import current_application_mode
from nicegui_app.contact import FEEDBACK_EMAIL, FEEDBACK_MAILTO_URL, GITHUB_REPOSITORY_URL
from nicegui_app.runtime import get_workflow
from nicegui_app.ui.i18n import current_locale, t, toggle_locale
from nicegui_app.ui.music import render_page_music_control
from nicegui_app.ui.sound import play_interface_sound
from nicegui_app.ui.theme import (
    apply_quasar_palette,
    apply_theme,
    current_theme,
    sound_feedback_enabled,
    toggle_sound_feedback,
    toggle_theme,
)


NAVIGATION_GROUPS = (
    ("nav_weekly_work", (("/", "dashboard", "space_dashboard"), ("/rosters", "rosters", "calendar_month"))),
    ("nav_people_fairness", (("/prefects", "prefects", "groups"),)),
    ("nav_support_system", (("/handover", "handover", "handshake"), ("/access-control", "access_control", "admin_panel_settings"), ("/settings", "settings", "settings"))),
    ("nav_reference", (("/platform", "platform", "domain"), ("/system-architecture", "system_architecture", "account_tree"), ("/engineering", "engineering", "build_circle"), ("/getting-started", "getting_started", "play_circle"), ("/guide", "operator_guide", "help_outline"), ("/devotional", "devotional", "menu_book"))),
)

MOBILE_PRIMARY_NAVIGATION = (
    ("/", "dashboard", "space_dashboard"),
    ("/rosters", "rosters", "calendar_month"),
    ("/prefects", "prefects", "groups"),
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


async def _reload_after_preference_change(change) -> None:
    dirty = await ui.run_javascript("document.body.dataset.syFormDirty === 'true'")
    if dirty:
        confirmed = await ui.run_javascript(
            f"window.confirm({json.dumps(t('preference_reload_warning'), ensure_ascii=False)})"
        )
        if not confirmed:
            return
    change()
    ui.navigate.reload()


def _navigate_with_sound(path: str) -> None:
    play_interface_sound("navigation")
    ui.navigate.to(path)


def _sync_preference_controls(controls, *, icon: str, label: str) -> None:  # type: ignore[no-untyped-def]
    for button, show_label, tooltip in controls:
        button.set_text(label if show_label else "")
        button.props(f'icon={icon} aria-label="{label}"')
        if tooltip is not None:
            tooltip.set_text(label)
        button.update()


async def _toggle_sound_feedback_with_preview(controls) -> None:  # type: ignore[no-untyped-def]
    """Update the preference in place so unfinished forms remain intact."""
    toggle_sound_feedback()
    enabled = sound_feedback_enabled()
    label = t("disable_sound_feedback") if enabled else t("enable_sound_feedback")
    _sync_preference_controls(
        controls,
        icon="volume_up" if enabled else "volume_off",
        label=label,
    )
    if enabled:
        play_interface_sound("success", force=True)
        ui.notify(t("sound_feedback_on"), type="positive", timeout=2_500)
    else:
        ui.notify(t("sound_feedback_off"), type="info", timeout=2_500)


def _toggle_theme_in_place(dark_mode, controls) -> None:  # type: ignore[no-untyped-def]
    """Switch appearance without discarding unfinished operator input."""
    toggle_theme()
    is_dark = current_theme() == "dark"
    dark_mode.set_value(is_dark)
    apply_quasar_palette(is_dark)
    label = t("light_mode") if is_dark else t("dark_mode")
    _sync_preference_controls(
        controls,
        icon="light_mode" if is_dark else "dark_mode",
        label=label,
    )


def _render_mobile_drawer_tools(
    gateway_identity: str,
    dark_mode,
    theme_controls,
    sound_controls,
) -> None:  # type: ignore[no-untyped-def]
    """Keep secondary preferences reachable without crowding the phone header."""
    with ui.element("section").classes("sy-mobile-drawer-tools").props(
        f'aria-label="{t("mobile_quick_settings")}" data-testid=mobile-drawer-tools'
    ):
        ui.label(t("mobile_quick_settings")).classes("sy-mobile-drawer-tools-title")
        with ui.element("div").classes("sy-mobile-drawer-tools-grid"):
            ui.button(
                t("switch_to_english") if current_locale() != "en" else t("switch_to_chinese"),
                icon="translate",
                on_click=lambda: _reload_after_preference_change(toggle_locale),
            ).props("flat no-caps").classes("sy-mobile-drawer-tool")
            sound_enabled = sound_feedback_enabled()
            sound_button = ui.button(
                t("disable_sound_feedback") if sound_enabled else t("enable_sound_feedback"),
                icon="volume_up" if sound_enabled else "volume_off",
                on_click=lambda: _toggle_sound_feedback_with_preview(sound_controls),
            ).props("flat no-caps").classes("sy-mobile-drawer-tool")
            sound_controls.append((sound_button, True, None))
            dark_target = current_theme() == "light"
            theme_button = ui.button(
                t("dark_mode") if dark_target else t("light_mode"),
                icon="dark_mode" if dark_target else "light_mode",
                on_click=lambda: _toggle_theme_in_place(dark_mode, theme_controls),
            ).props("flat no-caps").classes("sy-mobile-drawer-tool")
            theme_controls.append((theme_button, True, None))
            if gateway_identity:
                ui.button(
                    t("access_admin_logout"),
                    icon="logout",
                    on_click=lambda: ui.navigate.to("/logout"),
                ).props("flat no-caps data-testid=mobile-administrator-logout").classes(
                    "sy-mobile-drawer-tool"
                )


def _render_mobile_tabbar(drawer, active_path: str) -> None:  # type: ignore[no-untyped-def]
    """Expose the three weekly destinations while keeping secondary pages in the drawer."""
    primary_paths = {path for path, _key, _icon in MOBILE_PRIMARY_NAVIGATION}
    with ui.element("nav").classes("sy-mobile-tabbar").props(
        f'aria-label="{t("mobile_primary_navigation")}" data-testid=mobile-bottom-navigation'
    ):
        for path, key, icon in MOBILE_PRIMARY_NAVIGATION:
            button = ui.button(
                t(key),
                icon=icon,
                on_click=lambda target=path: _navigate_with_sound(target),
            ).props(f'flat no-caps aria-label="{t(key)}"').classes("sy-mobile-tab")
            if active_path == path:
                button.classes("sy-mobile-tab--active").props("aria-current=page")
        more = ui.button(t("mobile_more"), icon="menu", on_click=drawer.toggle).props(
            f'flat no-caps aria-label="{t("mobile_more")}" aria-controls=main-navigation-drawer '
            'aria-expanded=false data-testid=mobile-more'
        ).classes("sy-mobile-tab")
        if active_path not in primary_paths:
            more.classes("sy-mobile-tab--active").props("aria-current=page")


def _install_mobile_drawer_accessibility() -> None:
    """Synchronise drawer state, keyboard escape and focus in the rendered browser."""

    ui.run_javascript(
        """
        (() => {
          const button = document.querySelector('[data-testid="mobile-more"]');
          const currentDrawer = () => document.getElementById('main-navigation-drawer');
          if (!button || !currentDrawer()) return;
          if (button.dataset.syDrawerA11y === 'ready' && window.__syDrawerA11yOwner === button) return;
          window.__syDrawerA11yCleanup?.();
          const controller = new AbortController();
          button.dataset.syDrawerA11y = 'ready';
          window.__syDrawerA11yOwner = button;
          const isMobile = () => matchMedia('(max-width: 900px)').matches;
          const isOpen = () => {
            if (!isMobile()) return false;
            const drawer = currentDrawer();
            if (!drawer) return false;
            const bounds = drawer.getBoundingClientRect();
            const style = getComputedStyle(drawer);
            return style.visibility !== 'hidden' && bounds.width > 0 &&
              bounds.right > Math.min(44, bounds.width * .25);
          };
          const focusable = () => {
            const drawer = currentDrawer();
            if (!drawer) return [];
            return [...drawer.querySelectorAll(
              'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
            )].filter(element => element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden');
          };
          let observedShell = null;
          const observer = new MutationObserver(() => sync(false));
          const observeShell = () => {
            const drawer = currentDrawer();
            if (!drawer) return;
            const shell = drawer.closest('.q-drawer');
            if (!shell || shell === observedShell) return;
            observer.disconnect();
            observedShell = shell;
            observer.observe(shell, {attributes: true, attributeFilter: ['class', 'style', 'aria-hidden']});
          };
          const sync = (focusDrawer = false) => {
            observeShell();
            const wasOpen = button.getAttribute('aria-expanded') === 'true';
            const open = isOpen();
            button.setAttribute('aria-expanded', String(open));
            if (focusDrawer && open) {
              const first = focusable()[0];
              first?.focus({preventScroll: true});
            }
            if (wasOpen && !open) button.focus({preventScroll: true});
          };
          button.addEventListener('click', () => setTimeout(() => sync(true), 220), {signal: controller.signal});
          document.addEventListener('click', event => {
            if (!(event.target instanceof Element) || !event.target.closest('.q-drawer__backdrop')) return;
            setTimeout(() => sync(false), 260);
          }, {capture: true, signal: controller.signal});
          document.addEventListener('keydown', event => {
            if (!isOpen()) return;
            if (event.key === 'Escape') {
              event.preventDefault();
              button.click();
              setTimeout(() => sync(false), 260);
              return;
            }
            if (event.key !== 'Tab') return;
            const items = focusable();
            if (!items.length) return;
            const drawer = currentDrawer();
            if (!drawer) return;
            const first = items[0]; const last = items[items.length - 1];
            if (event.shiftKey && (document.activeElement === first || !drawer.contains(document.activeElement))) {
              event.preventDefault(); last.focus({preventScroll: true});
            } else if (!event.shiftKey && (document.activeElement === last || !drawer.contains(document.activeElement))) {
              event.preventDefault(); first.focus({preventScroll: true});
            }
          }, {signal: controller.signal});
          window.addEventListener('resize', () => sync(false), {passive: true, signal: controller.signal});
          window.__syDrawerA11yCleanup = () => {
            observer.disconnect();
            observedShell = null;
            controller.abort();
            if (window.__syDrawerA11yOwner === button) window.__syDrawerA11yOwner = null;
          };
          requestAnimationFrame(() => sync(false));
        })();
        """
    )


@contextmanager
def page_shell(title_key: str, active_path: str, *, music_context: str | None = None) -> Iterator[None]:
    dark_mode = apply_theme()
    document_language = "en" if current_locale() == "en" else "zh-Hant-HK"
    ui.run_javascript(f"document.documentElement.lang = {document_language!r};")
    ui.run_javascript(
        """
        (() => {
          if (window.__syDirtyGuardInstalled) return;
          window.__syDirtyGuardInstalled = true;
          const markDirty = event => {
            if (event.isTrusted && event.target?.closest?.('#main-content')) {
              document.body.dataset.syFormDirty = 'true';
            }
          };
          document.addEventListener('input', markDirty, true);
          document.addEventListener('change', markDirty, true);
        })();
        """
    )
    application_mode = current_application_mode()
    gateway_identity = _verified_gateway_identity()
    theme_controls = []
    sound_controls = []
    drawer = ui.left_drawer(value=False, bordered=False).props(
        f'show-if-above breakpoint=900 role=navigation id=main-navigation-drawer aria-label="{t("main_navigation")}"'
    ).classes("sy-sidebar bg-[var(--sy-surface)]")
    with drawer:
        with ui.column().classes("w-full gap-1 p-4"):
            with ui.row().classes("items-center gap-3 mb-2"):
                ui.image("/assets/brand/sing-yin-crest-navigation.png").classes("sy-brand-mark").props(
                    f'alt="{t("school_crest_alt")}" width=545 height=524 fetchpriority=high'
                )
                ui.label(t("app_name")).classes("text-base font-bold leading-tight sy-fg-stable")
            ui.label(t("service_principle")).classes("text-xs italic text-[var(--sy-muted)] mb-5")
            _render_mobile_drawer_tools(
                gateway_identity,
                dark_mode,
                theme_controls,
                sound_controls,
            )
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
    with ui.header(elevated=False).classes("sy-app-header bg-[var(--sy-surface)] border-b border-[var(--sy-line)] px-4"):
        skip_link = ui.link(t("skip_to_content"), "#main-content").classes("sy-skip-link")
        skip_link.on(
            "click",
            lambda: ui.run_javascript(
                "const main=document.getElementById('main-content'); if(main){main.focus({preventScroll:true}); main.scrollIntoView();}"
            ),
        )
        with ui.row().classes("sy-header-bar w-full items-center justify-between"):
            with ui.row().classes("sy-header-leading items-center gap-2"):
                ui.button(icon="menu", on_click=drawer.toggle).props(
                    f'flat round aria-label="{t("open_navigation")}" aria-controls=main-navigation-drawer'
                ).classes("sy-icon-control sy-desktop-drawer-trigger").style("color: var(--sy-nav-ink) !important").tooltip(t("open_navigation"))
                ui.label(t(title_key)).classes("sy-header-title text-lg font-semibold").props("role=heading aria-level=1")
            with ui.row().classes("sy-header-tools items-center gap-1"):
                if music_context:
                    render_page_music_control(music_context)
                with ui.row().classes("sy-desktop-header-controls items-center gap-1"):
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
                    ui.button("EN" if current_locale() != "en" else "中", on_click=lambda: _reload_after_preference_change(toggle_locale)).props("flat dense").classes("sy-language-control").style("color: var(--sy-nav-ink) !important")
                    sound_icon = "volume_up" if sound_feedback_enabled() else "volume_off"
                    sound_tooltip = (
                        t("disable_sound_feedback")
                        if sound_feedback_enabled()
                        else t("enable_sound_feedback")
                    )
                    sound_button = ui.button(
                        icon=sound_icon,
                        on_click=lambda: _toggle_sound_feedback_with_preview(sound_controls),
                    ).props(
                        f'flat round aria-label="{sound_tooltip}"'
                    ).classes("sy-icon-control").style("color: var(--sy-nav-ink) !important")
                    with sound_button:
                        sound_tooltip_element = ui.tooltip(sound_tooltip)
                    sound_controls.append((sound_button, False, sound_tooltip_element))
                    theme_icon = "dark_mode" if current_theme() == "light" else "light_mode"
                    tooltip = t("dark_mode") if current_theme() == "light" else t("light_mode")
                    theme_button = ui.button(
                        icon=theme_icon,
                        on_click=lambda: _toggle_theme_in_place(dark_mode, theme_controls),
                    ).props(
                        f'flat round aria-label="{tooltip}"'
                    ).classes("sy-icon-control").style("color: var(--sy-nav-ink) !important")
                    with theme_button:
                        theme_tooltip_element = ui.tooltip(tooltip)
                    theme_controls.append((theme_button, False, theme_tooltip_element))
    maintenance = get_workflow().maintenance_status()
    if application_mode.is_practice or maintenance.active:
        with ui.element("div").classes("sy-status-stack").props(
            f'role=region aria-label="{t("system_status")}" data-testid=system-status-stack'
        ):
            if application_mode.is_practice:
                with ui.element("section").props(
                    "data-testid=practice-mode-banner role=status aria-live=polite"
                ).classes("sy-practice-banner"):
                    ui.icon("science").classes("sy-practice-banner-icon").props("aria-hidden=true")
                    with ui.column().classes("gap-0 min-w-0"):
                        ui.label(t("practice_mode_title")).classes("sy-practice-banner-title")
                        ui.label(t("practice_mode_body")).classes("sy-practice-banner-copy")
            if maintenance.active:
                with ui.element("section").props(
                    "data-testid=maintenance-mode-banner role=alert aria-live=assertive"
                ).classes("sy-maintenance-banner"):
                    ui.icon("engineering").classes("sy-practice-banner-icon").props("aria-hidden=true")
                    with ui.column().classes("gap-0 min-w-0"):
                        ui.label(t("maintenance_mode_title")).classes("sy-practice-banner-title")
                        ui.label(
                            t("maintenance_recovery_body")
                            if maintenance.recovery_required
                            else t("maintenance_mode_body")
                        ).classes("sy-practice-banner-copy")
    with ui.element("main").props("id=main-content tabindex=-1").classes("sy-main w-full gap-6"):
        yield
    _render_mobile_tabbar(drawer, active_path)
    _install_mobile_drawer_accessibility()
