"""Shared navigation shell with persistent theme and language preferences."""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator
import json

from nicegui import ui

from nicegui_app.access_context import AccessMode
from nicegui_app.application_mode import current_application_mode
from nicegui_app.contact import FEEDBACK_EMAIL, FEEDBACK_MAILTO_URL, GITHUB_REPOSITORY_URL
from nicegui_app.runtime import current_page_context, get_workflow
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


def _navigation_context(active_path: str) -> tuple[int, str, str]:
    """Return the stable narrative chapter, group key and route icon."""

    for chapter, (group_key, items) in enumerate(NAVIGATION_GROUPS, start=1):
        for path, _key, icon in items:
            if path == active_path:
                return chapter, group_key, icon
    return 1, "nav_weekly_work", "space_dashboard"


def _page_slug(active_path: str) -> str:
    """Translate a known route into a CSS-safe, non-translated page identity."""

    return active_path.strip("/").replace("/", "-") or "dashboard"


def _sign_out() -> None:
    ui.run_javascript(
        """
        (() => {
          if (typeof window.__syInvalidateAuthSession === 'function') {
            window.__syInvalidateAuthSession();
            return;
          }
          try { sessionStorage.clear(); } catch {}
          try {
            const channel = new BroadcastChannel('sing-yin-guest-session-v1');
            channel.postMessage({type: 'session-ended'});
            channel.close();
          } catch {}
          document.querySelectorAll('audio, video').forEach(media => {
            try { media.pause(); } catch {}
          });
          (async () => {
            try {
              await fetch('/api/guest/downloads/cleanup', {
                method: 'POST',
                credentials: 'same-origin',
                cache: 'no-store',
                keepalive: true,
                headers: {'Accept': 'application/json'},
              });
            } catch {}
            try {
              const response = await fetch('/auth/logout', {
                method: 'POST',
                credentials: 'same-origin',
                cache: 'no-store',
                keepalive: true,
                headers: {'Accept': 'application/json'},
              });
              if (!response.ok) throw new Error(`logout ${response.status}`);
            } catch {
              document.body.dataset.syLogout = 'retry-required';
              window.alert('未能安全完成登出，請稍後再試。\\nSecure sign-out could not be completed. Please retry.');
              return;
            }
            window.location.replace('/');
          })();
        })();
        """
    )


def _install_guest_snapshot_bridge(access_mode: AccessMode) -> None:
    """Keep the guest demo's signed state in this tab's sessionStorage only."""

    if access_mode is not AccessMode.GUEST:
        return
    ui.run_javascript(
        r"""
        (() => {
          const STORAGE_KEY = 'sing-yin-guest-workspace-snapshot-v1';
          const MAX_TOKEN_CHARS = 262144;
          window.__syGuestSnapshotBridge?.destroy?.();

          const controller = new AbortController();
          let active = null;
          let retryTimer = 0;
          let restoreGeneration = 0;

          const validText = (value, maximum = 256) =>
            typeof value === 'string' && value.length > 0 && value.length <= maximum;

          const readStored = () => {
            try {
              const parsed = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null');
              if (
                parsed?.version !== 1 ||
                !validText(parsed.workspaceId) ||
                !validText(parsed.tabId) ||
                !Number.isInteger(parsed.revision) ||
                parsed.revision < 0 ||
                !validText(parsed.token, MAX_TOKEN_CHARS)
              ) return null;
              return parsed;
            } catch {
              return null;
            }
          };

          const accept = payload => {
            if (
              !active ||
              payload?.workspaceId !== active.workspaceId ||
              payload?.tabId !== active.tabId ||
              (payload?.nonce && payload.nonce !== active.nonce) ||
              !Number.isInteger(payload?.revision) ||
              payload.revision < 0 ||
              !validText(payload?.token, MAX_TOKEN_CHARS)
            ) return false;
            const previous = readStored();
            if (
              previous?.workspaceId === payload.workspaceId &&
              previous?.tabId === payload.tabId &&
              previous.revision > payload.revision
            ) return false;
            try {
              sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
                version: 1,
                workspaceId: payload.workspaceId,
                tabId: payload.tabId,
                revision: payload.revision,
                token: payload.token,
              }));
              document.body.dataset.syGuestSnapshot = `saved-r${payload.revision}`;
              return true;
            } catch {
              document.body.dataset.syGuestSnapshot = 'storage-unavailable';
              return false;
            }
          };

          const restore = async (binding, attempt = 0) => {
            const generation = ++restoreGeneration;
            const stored = readStored();
            const candidate = stored?.token || binding.token;
            try {
              const response = await fetch('/api/guest/snapshot/restore', {
                method: 'POST',
                credentials: 'same-origin',
                cache: 'no-store',
                signal: controller.signal,
                headers: {
                  'Accept': 'application/json',
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                  workspaceId: binding.workspaceId,
                  tabId: binding.tabId,
                  nonce: binding.nonce,
                  token: candidate,
                }),
              });
              if (generation !== restoreGeneration || active !== binding) return;
              if (!response.ok) throw new Error(`snapshot restore ${response.status}`);
              const result = await response.json();
              if (
                result?.workspaceId !== binding.workspaceId ||
                result?.tabId !== binding.tabId
              ) throw new Error('snapshot restore binding mismatch');
              accept({...result, nonce: binding.nonce});
              document.body.dataset.syGuestSnapshotRestore =
                result.accepted === true ? 'accepted' : 'safe-fixture';
              if (
                result.restored === true &&
                Number(result.revision) !== Number(binding.revision)
              ) {
                window.location.reload();
              }
            } catch (error) {
              if (error?.name === 'AbortError' || generation !== restoreGeneration) return;
              document.body.dataset.syGuestSnapshotRestore = 'temporarily-unavailable';
              if (attempt < 2) {
                clearTimeout(retryTimer);
                retryTimer = window.setTimeout(() => restore(binding, attempt + 1), 350 * (attempt + 1));
              } else if (!stored) {
                accept(binding);
              }
            }
          };

          const bind = payload => {
            if (
              !validText(payload?.workspaceId) ||
              !validText(payload?.tabId) ||
              !validText(payload?.nonce, 128) ||
              !Number.isInteger(payload?.revision) ||
              payload.revision < 0 ||
              !validText(payload?.token, MAX_TOKEN_CHARS)
            ) return;
            clearTimeout(retryTimer);
            active = payload;
            restore(payload);
          };

          const destroy = () => {
            clearTimeout(retryTimer);
            controller.abort();
            active = null;
          };

          window.__syGuestSnapshotBridge = {accept, bind, destroy};
          const pendingBind = window.__syPendingGuestSnapshotBind;
          const pendingAccept = window.__syPendingGuestSnapshotAccept;
          window.__syPendingGuestSnapshotBind = null;
          window.__syPendingGuestSnapshotAccept = null;
          if (pendingBind) bind(pendingBind);
          if (pendingAccept) accept(pendingAccept);
        })();
        """
    )


def _install_auth_status_monitor(access_mode: AccessMode, expires_at) -> None:  # type: ignore[no-untyped-def]
    """Revalidate long-lived pages and remove temporary browser state on revocation."""

    if access_mode not in {AccessMode.ADMIN, AccessMode.GUEST}:
        return
    expiry_epoch = int(expires_at.timestamp()) if expires_at is not None else None
    script = r"""
        (() => {
          const expectedMode = __EXPECTED_MODE__;
          const principalExpiresAt = __EXPIRES_AT__;
          window.__syAuthStatusCleanup?.();

          const controller = new AbortController();
          const tabId = globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2);
          const channel = 'BroadcastChannel' in window
            ? new BroadcastChannel('sing-yin-guest-session-v1')
            : null;
          let intervalId = 0;
          let initialTimer = 0;
          let expiryTimer = 0;
          let checking = false;
          let invalidating = false;

          const stop = () => {
            clearInterval(intervalId);
            clearTimeout(initialTimer);
            clearTimeout(expiryTimer);
            controller.abort();
            document.removeEventListener('visibilitychange', onVisibility);
            window.removeEventListener('focus', check);
            window.removeEventListener('pageshow', onPageShow);
            channel?.close();
            if (window.__syAuthStatusCleanup === stop) {
              window.__syAuthStatusCleanup = null;
            }
            if (window.__syInvalidateAuthSession === invalidate) {
              window.__syInvalidateAuthSession = null;
            }
          };

          const clearTemporaryState = (broadcast = true) => {
            try { sessionStorage.clear(); } catch {}
            document.querySelectorAll('audio, video').forEach(media => {
              try {
                media.pause();
                media.removeAttribute('src');
                media.load();
              } catch {}
            });
            if (broadcast) {
              try { channel?.postMessage({type: 'session-ended', source: tabId}); } catch {}
            }
          };

          const showLogoutRetry = () => {
            document.body.dataset.syLogout = 'retry-required';
            const main = document.getElementById('main-content');
            if (main) {
              main.setAttribute('inert', '');
              main.setAttribute('aria-hidden', 'true');
            }
            let state = document.getElementById('sy-auth-exit-state');
            if (!state) {
              state = document.createElement('section');
              state.id = 'sy-auth-exit-state';
              state.setAttribute('role', 'alert');
              state.setAttribute('aria-live', 'assertive');
              state.innerHTML = `
                <div class="sy-guest-capacity-card">
                  <span class="sy-guest-capacity-mark" aria-hidden="true">安</span>
                  <p class="sy-guest-capacity-kicker">SECURE SIGN-OUT · 安全登出</p>
                  <h1>登出尚未安全完成</h1>
                  <p>系統未能確認伺服器已撤銷這個工作階段，因此沒有假裝完成登出。請保持此頁開啟並重新嘗試。</p>
                  <p lang="en">The server could not confirm that this session was revoked, so sign-out was not falsely reported as complete. Keep this page open and retry.</p>
                  <div class="sy-guest-capacity-actions">
                    <button id="sy-auth-exit-retry" type="button">重新登出 · Retry sign-out</button>
                  </div>
                </div>`;
              document.body.appendChild(state);
            }
            document.getElementById('sy-auth-exit-retry')?.addEventListener(
              'click',
              () => {
                state.remove();
                if (main) {
                  main.removeAttribute('inert');
                  main.removeAttribute('aria-hidden');
                }
                invalidating = false;
                invalidate({broadcast: false});
              },
              {once: true},
            );
            document.getElementById('sy-auth-exit-retry')?.focus();
          };

          const invalidate = async ({broadcast = true} = {}) => {
            if (invalidating) return;
            invalidating = true;
            clearTemporaryState(broadcast);
            stop();
            if (expectedMode === 'guest') {
              try {
                await fetch('/api/guest/downloads/cleanup', {
                  method: 'POST',
                  credentials: 'same-origin',
                  cache: 'no-store',
                  keepalive: true,
                  headers: {'Accept': 'application/json'},
                });
              } catch {}
            }
            try {
              const response = await fetch('/auth/logout', {
                method: 'POST',
                credentials: 'same-origin',
                cache: 'no-store',
                keepalive: true,
                headers: {'Accept': 'application/json'},
              });
              if (!response.ok) throw new Error(`logout ${response.status}`);
            } catch {
              showLogoutRetry();
              return;
            }
            window.location.replace('/');
          };

          const scheduleExpiry = expiresAt => {
            clearTimeout(expiryTimer);
            if (!Number.isFinite(expiresAt)) return;
            // Start cleanup just before the gateway principal expires so the
            // authenticated origin can still erase the in-memory workspace.
            const delay = Math.max(0, (expiresAt * 1000) - Date.now() - 250);
            expiryTimer = window.setTimeout(() => invalidate(), delay);
          };

          async function check() {
            if (checking || invalidating) return;
            checking = true;
            try {
              const response = await fetch('/auth/status', {
                method: 'GET',
                credentials: 'same-origin',
                cache: 'no-store',
                headers: {'Accept': 'application/json'},
                signal: controller.signal,
              });
              if (response.status === 401 || response.status === 403) {
                await invalidate();
                return;
              }
              let status = null;
              try { status = await response.json(); } catch {}
              if (!response.ok || !status) return;
              const expiresAt = Number(status.expiresAt);
              const expired = Number.isFinite(expiresAt) && expiresAt <= Math.floor(Date.now() / 1000);
              if (status.authenticated !== true || status.mode !== expectedMode || expired) {
                await invalidate();
                return;
              }
              scheduleExpiry(expiresAt);
              document.body.dataset.syAuthStatus = 'verified';
              document.body.dataset.syAuthMode = expectedMode;
            } catch (error) {
              if (error?.name !== 'AbortError') {
                document.body.dataset.syAuthStatus = 'temporarily-unavailable';
              }
            } finally {
              checking = false;
            }
          }

          function onVisibility() {
            if (document.visibilityState === 'visible') check();
          }

          function onPageShow(event) {
            if (event.persisted) check();
          }

          channel?.addEventListener('message', event => {
            if (event.data?.type === 'session-ended' && event.data?.source !== tabId) {
              invalidate({broadcast: false});
            }
          });
          document.addEventListener('visibilitychange', onVisibility);
          window.addEventListener('focus', check);
          window.addEventListener('pageshow', onPageShow);
          intervalId = window.setInterval(check, 45_000);
          initialTimer = window.setTimeout(check, 1_200);
          scheduleExpiry(principalExpiresAt);
          window.__syAuthStatusCleanup = stop;
          window.__syInvalidateAuthSession = invalidate;
        })();
    """
    script = script.replace("__EXPECTED_MODE__", json.dumps(access_mode.value))
    script = script.replace("__EXPIRES_AT__", json.dumps(expiry_epoch))
    ui.run_javascript(script)


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
    access_mode: AccessMode,
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
            if access_mode in {AccessMode.ADMIN, AccessMode.GUEST}:
                ui.button(
                    t("access_admin_logout"),
                    icon="logout",
                    on_click=_sign_out,
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
    page_context = current_page_context()
    access_mode = page_context.principal.mode
    chapter, navigation_group_key, active_icon = _navigation_context(active_path)
    page_slug = _page_slug(active_path)
    _install_guest_snapshot_bridge(access_mode)
    _install_auth_status_monitor(access_mode, page_context.principal.expires_at)
    theme_controls = []
    sound_controls = []
    drawer = ui.left_drawer(value=False, bordered=False).props(
        f'show-if-above breakpoint=900 role=navigation id=main-navigation-drawer aria-label="{t("main_navigation")}"'
    ).classes("sy-sidebar bg-[var(--sy-surface)]")
    with drawer:
        with ui.column().classes("w-full gap-1 p-4"):
            with ui.row().classes("sy-brand-lockup items-center gap-3 mb-2"):
                ui.image("/assets/brand/sing-yin-crest-navigation.png").classes("sy-brand-mark").props(
                    f'alt="{t("school_crest_alt")}" width=545 height=524 fetchpriority=high'
                )
                with ui.column().classes("sy-brand-copy gap-0 min-w-0"):
                    ui.label("STUDY PREFECT OPERATIONS").classes("sy-brand-eyebrow")
                    ui.label(t("app_name")).classes("text-base font-bold leading-tight sy-fg-stable")
            ui.label(t("service_principle")).classes("sy-brand-principle text-xs italic text-[var(--sy-muted)] mb-5")
            _render_mobile_drawer_tools(
                access_mode,
                dark_mode,
                theme_controls,
                sound_controls,
            )
            for group_index, (group_key, items) in enumerate(NAVIGATION_GROUPS, start=1):
                ui.label(t(group_key)).classes("sy-nav-section").props(
                    f'data-sy-section="{group_index:02d}"'
                )
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
                with ui.column().classes("sy-header-context gap-0 min-w-0"):
                    ui.label(f"{chapter:02d} · {t(navigation_group_key)}").classes("sy-header-eyebrow")
                    ui.label(t(title_key)).classes("sy-header-title text-lg font-semibold").props("role=heading aria-level=1")
            with ui.row().classes("sy-header-tools items-center gap-1"):
                if music_context:
                    render_page_music_control(music_context)
                with ui.row().classes("sy-desktop-header-controls items-center gap-1"):
                    if access_mode is AccessMode.ADMIN:
                        ui.badge(t("access_admin_signed_in"), color="positive").props(
                            f'outline aria-label="{t("access_admin_mode")}" data-testid=administrator-mode'
                        ).classes("sy-status-badge")
                        ui.button(
                            icon="logout",
                            on_click=_sign_out,
                        ).props(
                            f'flat round aria-label="{t("access_admin_logout")}" data-testid=administrator-logout'
                        ).classes("sy-admin-logout").tooltip(t("access_admin_logout"))
                    elif access_mode is AccessMode.GUEST:
                        ui.badge(t("access_guest_signed_in"), color="warning").props(
                            f'outline aria-label="{t("access_guest_mode")}" data-testid=guest-mode'
                        ).classes("sy-status-badge")
                        ui.button(
                            icon="logout",
                            on_click=_sign_out,
                        ).props(
                            f'flat round aria-label="{t("access_admin_logout")}" data-testid=guest-logout'
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
    if application_mode.is_practice or access_mode is AccessMode.GUEST or maintenance.active:
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
            if access_mode is AccessMode.GUEST:
                with ui.element("section").props(
                    "data-testid=guest-mode-banner role=status aria-live=polite"
                ).classes("sy-practice-banner sy-guest-banner"):
                    ui.icon("science").classes("sy-practice-banner-icon").props("aria-hidden=true")
                    with ui.column().classes("gap-0 min-w-0"):
                        ui.label(t("access_guest_mode")).classes("sy-practice-banner-title")
                        ui.label(t("access_guest_mode_body")).classes("sy-practice-banner-copy")
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
    with ui.element("main").props("id=main-content tabindex=-1").props(
        f'data-sy-page="{page_slug}" data-sy-mode="{access_mode.value}"'
    ).classes(
        f"sy-main sy-page-shell sy-page-{page_slug} "
        f"sy-page-domain-{chapter:02d} sy-mode-{access_mode.value} w-full gap-6"
    ):
        with ui.element("div").classes("sy-page-context").props("aria-hidden=true"):
            ui.label(f"{chapter:02d}").classes("sy-page-context-index")
            ui.icon(active_icon).classes("sy-page-context-icon")
            ui.label(t(navigation_group_key)).classes("sy-page-context-label")
            ui.element("span").classes("sy-page-context-line")
        yield
    _render_mobile_tabbar(drawer, active_path)
    _install_mobile_drawer_accessibility()
