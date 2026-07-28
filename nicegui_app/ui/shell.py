"""Shared navigation shell with persistent theme and language preferences."""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator
import json
from urllib.parse import quote

from nicegui import ui

from nicegui_app.access_context import AccessMode
from nicegui_app.application_mode import current_application_mode
from nicegui_app.contact import FEEDBACK_EMAIL, FEEDBACK_MAILTO_URL, GITHUB_REPOSITORY_URL
from nicegui_app.runtime import current_page_context, get_workflow
from nicegui_app.ui.brand import render_service_weave_mark
from nicegui_app.ui.html_safety import attr
from nicegui_app.ui.i18n import current_locale, language_switch_copy, t, toggle_locale
from nicegui_app.ui.navigation import navigate_to
from nicegui_app.ui.music import render_page_music_control
from nicegui_app.ui.page_catalog import (
    mobile_navigation_for,
    navigation_groups_for,
    navigation_item_tuples_for,
    page_definition,
    portal_pages_for,
)
from nicegui_app.ui.sound import play_interface_sound
from nicegui_app.ui.theme import (
    QUASAR_DARK_PALETTE,
    QUASAR_LIGHT_PALETTE,
    adopt_verified_theme_handoff,
    apply_quasar_palette,
    apply_theme,
    current_theme,
    next_explicit_theme,
    set_system_theme_resolution,
    set_theme_preference,
    sound_feedback_enabled,
    theme_preference,
    toggle_sound_feedback,
)


# Compatibility tuple views remain available to existing tests and extensions,
# but both desktop and mobile navigation now project one PageDefinition catalog.
NAVIGATION_GROUPS = navigation_item_tuples_for(AccessMode.ADMIN)
MOBILE_PRIMARY_NAVIGATION = tuple(
    (page.route, page.title_key, page.icon)
    for page in mobile_navigation_for(AccessMode.ADMIN)
)


def _navigation_context(active_path: str, access_mode: AccessMode) -> tuple[int, str, str]:
    """Return the stable narrative chapter, group key and route icon."""

    active_page = page_definition(active_path)
    if active_page is not None:
        for chapter, (group_key, _pages) in enumerate(
            navigation_groups_for(access_mode), start=1
        ):
            if group_key == active_page.navigation_group:
                return chapter, group_key, active_page.icon
        if active_page in portal_pages_for(access_mode):
            return 7, "nav_trust_resources", active_page.icon
    return 1, "nav_weekly_operations", "space_dashboard"


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
    navigate_to(path)


def _sync_preference_controls(
    controls, *, icon: str, label: str, pressed: bool
) -> None:  # type: ignore[no-untyped-def]
    for button, show_label, tooltip in controls:
        button.set_text(label if show_label else "")
        button.props(
            f'icon={icon} aria-label="{attr(label)}" title="{attr(label)}" '
            f'aria-pressed={"true" if pressed else "false"}'
        )
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
        pressed=enabled,
    )
    if enabled:
        play_interface_sound("success", force=True)
        ui.notify(t("sound_feedback_on"), type="positive", timeout=2_500)
    else:
        ui.notify(t("sound_feedback_off"), type="info", timeout=2_500)


def _current_theme_control(resolved_theme: str | None = None) -> tuple[str, str, bool]:
    """Describe current appearance while naming the button's next action."""

    resolved = resolved_theme if resolved_theme in {"light", "dark"} else current_theme()
    is_dark = resolved == "dark"
    return (
        "dark_mode" if is_dark else "light_mode",
        t("theme_switch_to_light") if is_dark else t("theme_switch_to_dark"),
        is_dark,
    )


def _sync_theme_controls(controls) -> None:  # type: ignore[no-untyped-def]
    icon, label, is_dark = _current_theme_control()
    for button, show_label, tooltip in controls["buttons"]:
        button.set_text(label if show_label else "")
        button.props(
            f'icon={icon} aria-label="{attr(label)}" title="{attr(label)}" '
            f'aria-pressed={"true" if is_dark else "false"} '
            f'data-theme-preference={theme_preference()} data-theme-resolved={"dark" if is_dark else "light"}'
        )
        if tooltip is not None:
            tooltip.set_text(label)
        button.update()


def _remember_system_theme_resolution(value: str) -> None:
    """Accept a browser media-query result only while the preference is unset."""

    if theme_preference() != "system" or value not in {"light", "dark"}:
        return
    if current_theme() == value:
        return
    set_system_theme_resolution(value)


def _render_system_theme_resolver() -> None:
    """Expose a hidden, validated bridge from browser resolution to Python."""

    if theme_preference() != "system":
        return
    with ui.element("div").classes("hidden").props(
        f"aria-hidden=true data-sy-theme-resolver data-server-resolved={current_theme()}"
    ):
        for value in ("light", "dark"):
            ui.button(
                on_click=lambda resolved=value: _remember_system_theme_resolution(resolved)
            ).props(
                f"tabindex=-1 aria-hidden=true data-sy-theme-resolve={value}"
            )


async def _toggle_theme_in_place(dark_mode, controls) -> None:  # type: ignore[no-untyped-def]
    """Persist the opposite of the browser-resolved appearance in one click."""

    if controls["busy"]:
        return
    controls["busy"] = True
    try:
        try:
            resolved = await ui.run_javascript(
                "window.__syThemeControls?.resolved?.() || "
                "(document.body.classList.contains('body--dark') || "
                "matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')"
            )
        except Exception:  # pragma: no cover - browser disconnect fallback
            resolved = current_theme()
        if resolved not in {"light", "dark"}:
            resolved = current_theme()
        target = next_explicit_theme(str(resolved))
        set_theme_preference(target)
        is_dark = target == "dark"
        dark_mode.set_value(is_dark)
        apply_quasar_palette(is_dark)
        _sync_theme_controls(controls)
        ui.run_javascript(
            f"window.__syThemeControls?.applyExplicit?.({json.dumps(target)}, "
            "{animate:true,broadcast:true});"
        )
    finally:
        controls["busy"] = False


def _install_theme_control_runtime() -> None:
    """Synchronise system resolution, state semantics and open browser tabs."""

    script = """
        (() => {
          window.__syThemeControlsCleanup?.();
          const controller = new AbortController();
          const signal = controller.signal;
          const media = matchMedia('(prefers-color-scheme: dark)');
          const palettes = {
            light: __QUASAR_LIGHT_PALETTE__,
            dark: __QUASAR_DARK_PALETTE__,
          };
          const applyQuasarPalette = theme => {
            const palette = palettes[theme];
            if (!palette) return;
            for (const [name, value] of Object.entries(palette)) {
              const cssName = name.replaceAll('_', '-');
              if (typeof window.Quasar?.setCssVar === 'function') {
                window.Quasar.setCssVar(cssName, value, document.body);
              } else {
                document.body.style.setProperty(`--q-${cssName}`, value);
              }
            }
          };
          const channel = typeof BroadcastChannel === 'function'
            ? new BroadcastChannel('sing-yin:appearance:v1') : null;
          const buttons = () => [...document.querySelectorAll('[data-sy-theme-toggle]')];
          const resolver = () => document.querySelector('[data-sy-theme-resolver]');
          const explicitPreference = () => {
            const value = buttons()[0]?.dataset.themePreference;
            return value === 'light' || value === 'dark' ? value : 'system';
          };
          const resolved = () => (document.body.classList.contains('body--dark') ||
            document.documentElement.classList.contains('body--dark') ||
            (explicitPreference() === 'system' && media.matches)) ? 'dark' : 'light';
          const sync = ({animate = false} = {}) => {
            const current = resolved();
            const isDark = current === 'dark';
            for (const button of buttons()) {
              const label = (isDark ? button.dataset.actionLight : button.dataset.actionDark) || '';
              button.dataset.themeResolved = current;
              button.setAttribute('aria-pressed', String(isDark));
              button.setAttribute('aria-label', label);
              button.title = label;
              const icon = button.querySelector('.q-icon');
              if (icon) icon.textContent = isDark ? 'dark_mode' : 'light_mode';
              const content = button.dataset.syThemeShowLabel === 'true'
                ? button.querySelector('.q-btn__content') : null;
              const text = content?.querySelector('[data-sy-theme-label], span:not(.q-icon)');
              if (text) text.textContent = label;
              else if (content) {
                const textNode = [...content.childNodes].find(node =>
                  node.nodeType === Node.TEXT_NODE && node.textContent.trim());
                if (textNode) textNode.textContent = label;
              }
              if (animate && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
                button.dataset.syIconChanging = 'true';
                setTimeout(() => delete button.dataset.syIconChanging, 220);
              }
            }
          };
          const reconcileSystemResolution = () => {
            const host = resolver();
            if (!host || explicitPreference() !== 'system' || host.dataset.resolving === 'true') return;
            const browserResolved = media.matches ? 'dark' : 'light';
            if (host.dataset.serverResolved === browserResolved) return;
            applyQuasarPalette(browserResolved);
            if (window.Quasar?.Dark) window.Quasar.Dark.set(browserResolved === 'dark');
            host.dataset.serverResolved = browserResolved;
            sync({animate: true});
            const trigger = host.querySelector(`[data-sy-theme-resolve="${browserResolved}"]`);
            if (!trigger) return;
            host.dataset.resolving = 'true';
            trigger.click();
          };
          const applyExplicit = (theme, {animate = true, broadcast = false} = {}) => {
            if (theme !== 'light' && theme !== 'dark') return;
            for (const button of buttons()) button.dataset.themePreference = theme;
            applyQuasarPalette(theme);
            if (window.Quasar?.Dark) window.Quasar.Dark.set(theme === 'dark');
            sync({animate});
            if (broadcast) channel?.postMessage({type: 'appearance', theme});
          };
          const observer = new MutationObserver(() => sync());
          observer.observe(document.body, {attributes: true, attributeFilter: ['class']});
          media.addEventListener('change', () => {
            if (explicitPreference() === 'system') {
              sync();
              reconcileSystemResolution();
            }
          }, {signal});
          channel?.addEventListener('message', event => {
            if (event.data?.type === 'appearance') {
              applyExplicit(event.data.theme, {animate: true, broadcast: false});
            }
          }, {signal});
          window.__syThemeControls = {resolved, sync, applyExplicit, reconcileSystemResolution};
          window.__syThemeControlsCleanup = () => {
            observer.disconnect();
            controller.abort();
            channel?.close();
            delete window.__syThemeControls;
          };
          sync({animate: false});
          reconcileSystemResolution();
        })();
        """
    script = script.replace(
        "__QUASAR_LIGHT_PALETTE__", json.dumps(QUASAR_LIGHT_PALETTE)
    ).replace("__QUASAR_DARK_PALETTE__", json.dumps(QUASAR_DARK_PALETTE))
    ui.run_javascript(script)


def _header_control_classes(kind: str, *, mobile: bool = False) -> str:
    """Return one shared visual anatomy plus a restrained semantic variant."""

    classes = f"sy-header-control sy-header-control--{kind}"
    return f"{classes} sy-mobile-drawer-tool" if mobile else classes


def _render_mobile_drawer_tools(
    access_mode: AccessMode,
    dark_mode,
    theme_controls,
    sound_controls,
) -> None:  # type: ignore[no-untyped-def]
    """Keep secondary preferences reachable without crowding the phone header."""
    with ui.element("section").classes("sy-mobile-drawer-tools").props(
        f'aria-label="{attr(t("mobile_quick_settings"))}" data-testid=mobile-drawer-tools'
    ):
        ui.label(t("mobile_quick_settings")).classes("sy-mobile-drawer-tools-title")
        with ui.element("div").classes("sy-mobile-drawer-tools-grid"):
            language_text, language_action = language_switch_copy(compact=False)
            ui.button(
                language_text,
                icon="translate",
                on_click=lambda: _reload_after_preference_change(toggle_locale),
            ).props(
                f'flat no-caps aria-label="{attr(language_action)}" title="{attr(language_action)}" '
                'data-testid=mobile-language-control'
            ).classes(_header_control_classes("language", mobile=True))
            sound_enabled = sound_feedback_enabled()
            sound_label = t("disable_sound_feedback") if sound_enabled else t("enable_sound_feedback")
            sound_button = ui.button(
                sound_label,
                icon="volume_up" if sound_enabled else "volume_off",
                on_click=lambda: _toggle_sound_feedback_with_preview(sound_controls),
            ).props(
                f'flat no-caps aria-label="{attr(sound_label)}" title="{attr(sound_label)}" '
                f'aria-pressed={"true" if sound_enabled else "false"} data-testid=mobile-sound-control'
            ).classes(_header_control_classes("sound", mobile=True))
            sound_controls.append((sound_button, True, None))
            theme_icon, theme_label, is_dark = _current_theme_control()
            theme_button = ui.button(
                theme_label,
                icon=theme_icon,
                on_click=lambda: _toggle_theme_in_place(dark_mode, theme_controls),
            ).props(
                f'flat no-caps aria-label="{attr(theme_label)}" title="{attr(theme_label)}" '
                f'aria-pressed={"true" if is_dark else "false"} data-testid=mobile-theme-control '
                f'data-sy-theme-toggle data-sy-theme-show-label=true data-theme-preference={theme_preference()} '
                f'data-action-light="{attr(t("theme_switch_to_light"))}" '
                f'data-action-dark="{attr(t("theme_switch_to_dark"))}"'
            ).classes(_header_control_classes("theme", mobile=True))
            theme_controls["buttons"].append((theme_button, True, None))
            if access_mode in {AccessMode.ADMIN, AccessMode.GUEST}:
                ui.button(
                    t("access_admin_logout"),
                    icon="logout",
                    on_click=_sign_out,
                ).props(
                    f'flat no-caps aria-label="{attr(t("access_admin_logout"))}" '
                    f'title="{attr(t("access_admin_logout"))}" data-testid=mobile-administrator-logout'
                ).classes(_header_control_classes("logout", mobile=True))


def _render_mobile_tabbar(
    drawer,
    active_path: str,
    access_mode: AccessMode,
) -> None:  # type: ignore[no-untyped-def]
    """Expose the three weekly destinations while keeping secondary pages in the drawer."""
    mobile_pages = mobile_navigation_for(access_mode)
    primary_paths = {page.route for page in mobile_pages}
    with ui.element("nav").classes("sy-mobile-tabbar").props(
        f'aria-label="{attr(t("mobile_primary_navigation"))}" data-testid=mobile-bottom-navigation'
    ):
        for page in mobile_pages:
            button = ui.button(
                t(page.title_key),
                icon=page.icon,
                on_click=lambda target=page.route: _navigate_with_sound(target),
            ).props(
                f'flat no-caps aria-label="{attr(t(page.title_key))}"'
            ).classes("sy-mobile-tab")
            if active_path == page.route:
                button.classes("sy-mobile-tab--active").props("aria-current=page")
        active_definition = page_definition(active_path)
        more_label = t("mobile_more")
        if active_path not in primary_paths and active_definition is not None:
            more_label = f'{more_label}: {t(active_definition.title_key)}'
        more = ui.button(t("mobile_more"), icon="menu", on_click=drawer.toggle).props(
            f'flat no-caps aria-label="{attr(more_label)}" aria-controls=main-navigation-drawer '
            'aria-expanded=false data-testid=mobile-more'
        ).classes("sy-mobile-tab")
        if active_path not in primary_paths:
            more.classes("sy-mobile-tab--active")


def _install_mobile_drawer_accessibility() -> None:
    """Synchronise drawer state, keyboard escape and focus in the rendered browser."""

    ui.run_javascript(
        """
        (() => {
          const button = document.querySelector('[data-testid="mobile-more"]');
          const currentDrawer = () => document.getElementById('main-navigation-drawer');
          if (!button || !currentDrawer()) return;
          window.__syDrawerA11yCleanup?.();
          const controller = new AbortController();
          let settleFrame = 0;
          button.dataset.syDrawerA11y = 'ready';
          window.__syDrawerA11yOwner = button;
          const isMobile = () => matchMedia('(max-width: 900px)').matches;
          const currentBackdrop = () => document.querySelector('.q-drawer__backdrop');
          const backdropVisible = () => {
            const backdrop = currentBackdrop();
            if (!(backdrop instanceof HTMLElement)) return false;
            const style = getComputedStyle(backdrop);
            return backdrop.getClientRects().length > 0 && style.display !== 'none' &&
              style.visibility !== 'hidden' && Number.parseFloat(style.opacity || '1') > .01;
          };
          const isOpen = () => {
            if (!isMobile()) return false;
            const drawer = currentDrawer();
            if (!drawer) return false;
            const bounds = drawer.getBoundingClientRect();
            const style = getComputedStyle(drawer);
            return style.visibility !== 'hidden' && bounds.width > 0 &&
              bounds.right > Math.min(44, bounds.width * .25) && backdropVisible();
          };
          const focusable = () => {
            const drawer = currentDrawer();
            if (!drawer) return [];
            return [...drawer.querySelectorAll(
              'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
            )].filter(element => element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden');
          };
          const backgroundElements = () => [
            document.querySelector('.sy-app-header'),
            document.getElementById('main-content'),
            document.querySelector('.sy-page-footer'),
            document.querySelector('.sy-mobile-tabbar'),
            document.querySelector('.sy-status-stack')
          ].filter(element => element instanceof HTMLElement && !currentDrawer()?.contains(element));
          const setBackgroundInert = inert => {
            backgroundElements().forEach(element => {
              if (inert) {
                element.inert = true;
                element.setAttribute('aria-hidden', 'true');
              } else {
                element.inert = false;
                element.removeAttribute('aria-hidden');
              }
            });
          };
          let observedShell = null;
          let observedBackdrop = null;
          const observer = new MutationObserver(() => sync(false));
          const observeShell = () => {
            const drawer = currentDrawer();
            if (!drawer) return;
            const shell = drawer.closest('.q-drawer');
            const backdrop = currentBackdrop();
            if (!shell || (shell === observedShell && backdrop === observedBackdrop)) return;
            observer.disconnect();
            observedShell = shell;
            observedBackdrop = backdrop;
            observer.observe(shell, {attributes: true, attributeFilter: ['class', 'style', 'aria-hidden']});
            if (backdrop instanceof HTMLElement) {
              observer.observe(backdrop, {attributes: true, attributeFilter: ['class', 'style', 'aria-hidden']});
            }
          };
          const sync = (focusDrawer = false) => {
            observeShell();
            const wasOpen = button.getAttribute('aria-expanded') === 'true';
            const open = isOpen();
            button.setAttribute('aria-expanded', String(open));
            setBackgroundInert(open);
            if (focusDrawer && open) {
              const first = focusable()[0];
              first?.focus({preventScroll: true});
            }
            if (wasOpen && !open) button.focus({preventScroll: true});
            return open;
          };
          const settle = (expectedOpen, focusDrawer = false) => {
            if (settleFrame) cancelAnimationFrame(settleFrame);
            const startedAt = performance.now();
            const tick = () => {
              if (controller.signal.aborted) return;
              const open = sync(focusDrawer && expectedOpen === true);
              if (expectedOpen === undefined || open === expectedOpen || performance.now() - startedAt >= 3000) {
                settleFrame = 0;
                return;
              }
              settleFrame = requestAnimationFrame(tick);
            };
            settleFrame = requestAnimationFrame(tick);
          };
          button.addEventListener('click', () => {
            const expectedOpen = button.getAttribute('aria-expanded') !== 'true';
            settle(expectedOpen, expectedOpen);
          }, {signal: controller.signal});
          document.addEventListener('click', event => {
            if (!(event.target instanceof Element) || !event.target.closest('.q-drawer__backdrop')) return;
            settle(false, false);
          }, {capture: true, signal: controller.signal});
          document.addEventListener('keydown', event => {
            if (!isOpen()) return;
            if (event.key === 'Escape') {
              event.preventDefault();
              button.click();
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
            if (settleFrame) cancelAnimationFrame(settleFrame);
            settleFrame = 0;
            observer.disconnect();
            observedShell = null;
            observedBackdrop = null;
            controller.abort();
            setBackgroundInert(false);
            if (window.__syDrawerA11yOwner === button) window.__syDrawerA11yOwner = null;
          };
          settle(undefined, false);
        })();
        """
    )


def _install_mobile_viewport_accessibility() -> None:
    """Keep focused mobile fields visible above the on-screen keyboard."""

    ui.run_javascript(
        """
        (() => {
          window.__syMobileViewportCleanup?.();
          const visualViewport = window.visualViewport;
          if (!visualViewport) return;
          const controller = new AbortController();
          const root = document.documentElement;
          let revealTimer = 0;
          const isMobile = () => matchMedia('(max-width: 900px)').matches;
          const keyboardOpen = () => isMobile() && (window.innerHeight - visualViewport.height) > 132;
          const activeField = () => {
            const target = document.activeElement;
            return target instanceof HTMLElement && target.matches('input, textarea, select, [contenteditable="true"]')
              ? target
              : null;
          };
          const setTabbarUnavailable = unavailable => {
            const tabbar = document.querySelector('.sy-mobile-tabbar');
            if (!(tabbar instanceof HTMLElement)) return;
            tabbar.inert = unavailable;
            if (unavailable) tabbar.setAttribute('aria-hidden', 'true');
            else tabbar.removeAttribute('aria-hidden');
          };
          const scheduleReveal = target => {
            window.clearTimeout(revealTimer);
            revealTimer = window.setTimeout(() => {
              if (!keyboardOpen() || !(target instanceof HTMLElement)) return;
              if (!target.isConnected || document.activeElement !== target) return;
              target.scrollIntoView({
                block: 'center',
                inline: 'nearest',
                behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
              });
            }, 120);
          };
          const sync = (reveal = false) => {
            const open = keyboardOpen();
            root.classList.toggle('sy-mobile-keyboard-open', open);
            root.style.setProperty('--sy-visual-viewport-height', `${Math.round(visualViewport.height)}px`);
            setTabbarUnavailable(open);
            if (open && reveal) scheduleReveal(activeField());
          };
          const revealFocusedField = event => {
            const target = event.target;
            if (!(target instanceof HTMLElement) || !target.matches('input, textarea, select, [contenteditable="true"]')) return;
            scheduleReveal(target);
          };
          visualViewport.addEventListener('resize', () => sync(true), {passive: true, signal: controller.signal});
          visualViewport.addEventListener('scroll', () => sync(false), {passive: true, signal: controller.signal});
          document.addEventListener('focusin', revealFocusedField, {signal: controller.signal});
          window.addEventListener('orientationchange', () => sync(true), {passive: true, signal: controller.signal});
          window.__syMobileViewportCleanup = () => {
            controller.abort();
            window.clearTimeout(revealTimer);
            setTabbarUnavailable(false);
            root.classList.remove('sy-mobile-keyboard-open');
            root.style.removeProperty('--sy-visual-viewport-height');
          };
          sync(false);
        })();
        """
    )


def _install_route_focus_management() -> None:
    """Move keyboard and screen-reader context to the new page after navigation."""

    ui.run_javascript(
        """
        (() => {
          window.__syRouteFocusCleanup?.();
          const key = 'sy:route-focus';
          const shouldFocus = sessionStorage.getItem(key) === 'main';
          sessionStorage.removeItem(key);
          window.__syRouteFocusCleanup = () => {};
          if (!shouldFocus || location.hash) return;
          requestAnimationFrame(() => requestAnimationFrame(() => {
            const main = document.getElementById('main-content');
            if (main) main.focus({preventScroll: true});
          }));
        })();
        """
    )


@contextmanager
def page_shell(active_path: str) -> Iterator[None]:
    page_context = current_page_context()
    adopt_verified_theme_handoff(page_context)
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
    access_mode = page_context.principal.mode
    active_page = page_definition(active_path)
    if active_page is None:
        raise RuntimeError(f"Page shell route is missing from PageDefinition: {active_path}")
    if not active_page.is_visible_to(access_mode):
        raise PermissionError(f"Page shell route is not visible to {access_mode.value}: {active_path}")
    if active_page.required_capability is not None:
        page_context.require(active_page.required_capability)
    title_key = active_page.title_key
    chapter, navigation_group_key, active_icon = _navigation_context(active_path, access_mode)
    page_kind = active_page.page_kind.value
    resolved_music_context = active_page.music_context
    page_slug = _page_slug(active_path)
    _install_guest_snapshot_bridge(access_mode)
    _install_auth_status_monitor(access_mode, page_context.principal.expires_at)
    theme_controls = {"buttons": [], "busy": False}
    sound_controls = []
    drawer = ui.left_drawer(value=False, bordered=False).props(
        f'show-if-above breakpoint=900 role=navigation id=main-navigation-drawer aria-label="{attr(t("main_navigation"))}"'
    ).classes("sy-sidebar bg-[var(--sy-surface)]")
    with drawer:
        with ui.column().classes("w-full gap-1 p-4"):
            with ui.row().classes("sy-brand-lockup items-center gap-3 mb-2"):
                render_service_weave_mark(context="navigation", test_id="navigation-product-mark")
                with ui.column().classes("sy-brand-copy gap-0 min-w-0"):
                    ui.label(t("service_weave_name")).classes("sy-brand-eyebrow")
                    ui.label(t("app_name")).classes("text-base font-bold leading-tight sy-fg-stable")
            ui.label(t("service_principle")).classes("sy-brand-principle text-xs italic text-[var(--sy-muted)] mb-5")
            _render_mobile_drawer_tools(
                access_mode,
                dark_mode,
                theme_controls,
                sound_controls,
            )
            for group_index, (group_key, pages) in enumerate(
                navigation_groups_for(access_mode), start=1
            ):
                ui.label(t(group_key)).classes("sy-nav-section").props(
                    f'data-sy-section="{group_index:02d}"'
                )
                for page in pages:
                    button = ui.button(
                        t(page.title_key),
                        icon=page.icon,
                        on_click=lambda target=page.route: _navigate_with_sound(target),
                    ).props("flat align=left").classes(
                        "sy-nav-control w-full justify-start"
                    ).style("color: var(--sy-nav-ink) !important")
                    if page.route == active_path:
                        button.classes("sy-nav-active").props("aria-current=page")
            portal_pages = portal_pages_for(access_mode)
            if portal_pages:
                with ui.element("aside").classes("sy-sidebar-portals").props(
                    f'aria-label="{attr(t("nav_trust_resources"))}" data-testid=sidebar-portals'
                ):
                    ui.label(t("nav_trust_resources")).classes("sy-nav-section").props(
                        'data-sy-section="07"'
                    )
                    for page in portal_pages:
                        button = ui.button(
                            t(page.title_key),
                            icon=page.icon,
                            on_click=lambda target=page.route: _navigate_with_sound(target),
                        ).props("flat align=left").classes(
                            "sy-nav-control sy-nav-portal w-full justify-start"
                        ).style("color: var(--sy-nav-ink) !important")
                        if page.route == active_path:
                            button.classes("sy-nav-active").props("aria-current=page")
            with ui.element("aside").classes("sy-sidebar-feedback").props(
                f'aria-label="{attr(t("feedback_channel_title"))}" data-testid=sidebar-feedback'
            ):
                with ui.row().classes("items-center gap-2 no-wrap"):
                    ui.icon("mail_outline").classes("sy-sidebar-feedback-icon").props("aria-hidden=true")
                    ui.label(t("feedback_channel_short")).classes("sy-sidebar-feedback-title")
                ui.label(t("feedback_channel_sidebar_body")).classes("sy-sidebar-feedback-copy")
                feedback_email_label = f'{t("feedback_email_action")}: {FEEDBACK_EMAIL}'
                ui.link(FEEDBACK_EMAIL, FEEDBACK_MAILTO_URL).classes("sy-sidebar-feedback-link").props(
                    f'aria-label="{attr(feedback_email_label)}"'
                )
                ui.link(t("github_repository_short"), GITHUB_REPOSITORY_URL).classes("sy-sidebar-feedback-link").props(
                    f'target=_blank rel="noopener noreferrer" aria-label="{attr(t("github_repository_action"))}"'
                )
                support_href = f"/support?source={quote(active_path, safe='')}"
                ui.link(t("report_problem"), support_href).classes("sy-sidebar-feedback-link").props(
                    f'aria-label="{attr(t("report_problem"))}"'
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
                    f'flat round aria-label="{attr(t("open_navigation"))}" aria-controls=main-navigation-drawer'
                ).classes("sy-icon-control sy-desktop-drawer-trigger").style("color: var(--sy-nav-ink) !important").tooltip(t("open_navigation"))
                with ui.column().classes("sy-header-context gap-0 min-w-0"):
                    ui.label(f"{chapter:02d} · {t(navigation_group_key)}").classes("sy-header-eyebrow")
                    ui.label(t(title_key)).classes("sy-header-title text-lg font-semibold").props("role=heading aria-level=1")
            with ui.row().classes("sy-header-tools items-center gap-1"):
                if resolved_music_context:
                    render_page_music_control(resolved_music_context)
                with ui.row().classes("sy-desktop-header-controls items-center gap-1"):
                    if access_mode is AccessMode.ADMIN:
                        ui.badge(t("access_admin_signed_in"), color="positive").props(
                            f'outline aria-label="{attr(t("access_admin_mode"))}" data-testid=administrator-mode'
                        ).classes("sy-status-badge")
                        ui.button(
                            icon="logout",
                            on_click=_sign_out,
                        ).props(
                            f'flat round aria-label="{attr(t("access_admin_logout"))}" '
                            f'title="{attr(t("access_admin_logout"))}" data-testid=administrator-logout'
                        ).classes(_header_control_classes("logout")).tooltip(t("access_admin_logout"))
                    elif access_mode is AccessMode.GUEST:
                        ui.badge(t("access_guest_signed_in"), color="warning").props(
                            f'outline aria-label="{attr(t("access_guest_mode"))}" data-testid=guest-mode'
                        ).classes("sy-status-badge")
                        ui.button(
                            icon="logout",
                            on_click=_sign_out,
                        ).props(
                            f'flat round aria-label="{attr(t("access_admin_logout"))}" '
                            f'title="{attr(t("access_admin_logout"))}" data-testid=guest-logout'
                        ).classes(_header_control_classes("logout")).tooltip(t("access_admin_logout"))
                    language_text, language_action = language_switch_copy(compact=True)
                    ui.button(
                        language_text,
                        on_click=lambda: _reload_after_preference_change(toggle_locale),
                    ).props(
                        f'flat dense no-caps data-testid=language-control aria-label="{attr(language_action)}" '
                        f'title="{attr(language_action)}"'
                    ).classes(_header_control_classes("language"))
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
                        f'flat round aria-label="{attr(sound_tooltip)}" title="{attr(sound_tooltip)}" '
                        f'aria-pressed={"true" if sound_feedback_enabled() else "false"} data-testid=sound-control'
                    ).classes(_header_control_classes("sound"))
                    with sound_button:
                        sound_tooltip_element = ui.tooltip(sound_tooltip)
                    sound_controls.append((sound_button, False, sound_tooltip_element))
                    theme_icon, tooltip, is_dark = _current_theme_control()
                    theme_button = ui.button(
                        icon=theme_icon,
                        on_click=lambda: _toggle_theme_in_place(dark_mode, theme_controls),
                    ).props(
                        f'flat round aria-label="{attr(tooltip)}" title="{attr(tooltip)}" '
                        f'aria-pressed={"true" if is_dark else "false"} data-testid=theme-control '
                        f'data-sy-theme-toggle data-theme-preference={theme_preference()} '
                        f'data-action-light="{attr(t("theme_switch_to_light"))}" '
                        f'data-action-dark="{attr(t("theme_switch_to_dark"))}"'
                    ).classes(_header_control_classes("theme"))
                    theme_controls["buttons"].append((theme_button, False, None))
    _render_system_theme_resolver()
    _install_theme_control_runtime()
    maintenance = get_workflow().maintenance_status()
    if application_mode.is_practice or access_mode is AccessMode.GUEST or maintenance.active:
        with ui.element("div").classes("sy-status-stack").props(
            f'role=region aria-label="{attr(t("system_status"))}" data-testid=system-status-stack'
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
        f'data-sy-page="{page_slug}" data-sy-page-kind="{page_kind}" '
        f'data-sy-mode="{access_mode.value}"'
    ).classes(
        f"sy-main sy-page-shell sy-page-{page_slug} "
        f"sy-page-kind-{page_kind} sy-page-domain-{chapter:02d} "
        f"sy-mode-{access_mode.value} w-full gap-6"
    ):
        with ui.element("div").classes("sy-page-context").props("aria-hidden=true"):
            ui.label(f"{chapter:02d}").classes("sy-page-context-index")
            ui.icon(active_icon).classes("sy-page-context-icon")
            ui.label(t(navigation_group_key)).classes("sy-page-context-label")
            ui.element("span").classes("sy-page-context-line")
        yield
    with ui.element("footer").props("role=contentinfo data-testid=page-copyright").classes("sy-page-footer"):
        ui.label(t("service_principle")).classes("sy-page-footer-principle")
        ui.label(t("copyright_notice")).classes("sy-page-footer-copyright")
    _render_mobile_tabbar(drawer, active_path, access_mode)
    _install_mobile_drawer_accessibility()
    _install_mobile_viewport_accessibility()
    _install_route_focus_management()
