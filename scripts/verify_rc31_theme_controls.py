"""Verify the rc31 binary appearance control without touching school data.

This focused browser gate deliberately starts a fresh disposable NiceGUI
process for every access-mode, viewport, and operating-system colour-scheme
combination.  A fresh process is important for Guest evidence because the
isolated E2E principal intentionally has one stable session identifier per
run; reusing that process would turn an earlier explicit preference into the
next case's initial state.

All mutable paths, including NiceGUI's ``app.storage.user`` files, live below
one temporary evidence root.  The script never targets an already-running
server and never writes screenshots into the repository.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Literal
from urllib.error import URLError
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen

from playwright.sync_api import Browser, BrowserContext, Locator, Page, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui_app.ui.design_token_contract import quasar_palette
from scripts.verify_nicegui_mobile import _expand_mobile_preferences, _open_mobile_drawer
from scripts.verify_release_candidate import (
    _assert_server_console_clean,
    _free_loopback_port,
    _start_server,
    _stop_server,
    _wait_until_ready,
    isolated_environment,
)
from scripts.verify_unified_guest_ui import _install_gateway_stubs, _open_route


AccessMode = Literal["admin", "guest"]
ViewportMode = Literal["desktop", "mobile"]
ColourScheme = Literal["light", "dark"]
AccessibilityMode = Literal["standard", "reduced-motion", "forced-colours"]

EXPECTED_PRIMARY = {
    mode: str(quasar_palette(mode=mode)["primary"]).lower()
    for mode in ("light", "dark")
}

_GATEWAY_AUTH_EPOCH = "31"
_GATEWAY_ORIGIN_PRINCIPAL_KID = "theme-browser-origin-v31"
_THEME_HANDOFF_COOKIE = "__Host-SingYinThemeHandoff"
_ADMIN_SESSION_COOKIE = "__Host-SingYinAdminSession"
_GUEST_SESSION_COOKIE = "__Host-SingYinGuestSession"


class ThemeControlVerificationError(RuntimeError):
    """Raised when one browser-visible appearance contract is broken."""


def _safe_environment(case_root: Path, *, access_mode: AccessMode) -> dict[str, str]:
    """Return a fail-closed environment whose every mutable path is disposable."""

    environment = isolated_environment(case_root, _free_loopback_port())
    storage_path = (case_root / "nicegui-storage").resolve()
    storage_path.mkdir(parents=True, exist_ok=True)
    environment.update(
        {
            "NICEGUI_STORAGE_PATH": str(storage_path),
            "PYTHONDONTWRITEBYTECODE": "1",
            "SING_YIN_UNIFIED_GUEST": "1",
        }
    )
    if access_mode == "guest":
        environment["SING_YIN_E2E_ACCESS_MODE"] = "guest"

    mutable_paths = (
        Path(environment["SING_YIN_DATABASE_PATH"]),
        Path(environment["SING_YIN_BACKUP_DIR"]),
        Path(environment["SING_YIN_LOG_DIR"]),
        Path(environment["SING_YIN_SUPPORT_DIR"]),
        storage_path,
    )
    canonical_paths = {
        (PROJECT_ROOT / "data" / "runtime" / "sing-yin-roster.sqlite3").resolve(),
        (PROJECT_ROOT / "data" / "backups").resolve(),
        (PROJECT_ROOT / ".nicegui").resolve(),
    }
    for path in mutable_paths:
        resolved = path.resolve()
        if resolved in canonical_paths or PROJECT_ROOT == resolved or PROJECT_ROOT in resolved.parents:
            raise ThemeControlVerificationError(f"Mutable verifier path escaped the temporary root: {resolved}")
        if case_root.resolve() != resolved and case_root.resolve() not in resolved.parents:
            raise ThemeControlVerificationError(f"Mutable verifier path is outside its case root: {resolved}")
    return environment


def _gateway_test_secrets() -> dict[str, str]:
    """Create one-use credentials without placing them in source or artifacts."""

    return {
        "admin_session": secrets.token_urlsafe(48),
        "guest_session": secrets.token_urlsafe(48),
        "origin_principal": secrets.token_urlsafe(48),
    }


def _gateway_environment(
    case_root: Path,
    *,
    secret_values: dict[str, str],
) -> dict[str, str]:
    """Return an isolated origin environment that accepts only signed gateway principals."""

    environment = _safe_environment(case_root, access_mode="admin")
    environment.update(
        {
            "SING_YIN_E2E_ACCESS_MODE": "",
            "SING_YIN_LOCAL_MAINTENANCE": "0",
            "SING_YIN_REQUIRE_GATEWAY_PRINCIPAL": "1",
            "SING_YIN_UNIFIED_GUEST": "1",
            "ORIGIN_PRINCIPAL_SECRET": secret_values["origin_principal"],
            "AUTH_EPOCH": _GATEWAY_AUTH_EPOCH,
            "ORIGIN_PRINCIPAL_KID": _GATEWAY_ORIGIN_PRINCIPAL_KID,
        }
    )
    return environment


def _worker_harness_source(*, worker_port: int, origin_port: int) -> str:
    """Build a disposable Deno host around the real Worker module.

    Cloudflare Access itself cannot be reproduced locally.  The one test-only
    endpoint below therefore creates an Admin session with the production
    session constructor after the production landing page has staged its
    theme cookie.  Every other route, including Guest bootstrap, session
    validation, origin-principal signing, and origin proxying, runs through
    the unmodified Worker fetch handler.
    """

    worker_uri = (PROJECT_ROOT / "cloudflare" / "roster_viewer" / "worker.js").as_uri()
    return f"""import worker, {{ createAdminSessionToken }} from {json.dumps(worker_uri)};

const ADMIN_COOKIE = {json.dumps(_ADMIN_SESSION_COOKIE)};
const GUEST_COOKIE = {json.dumps(_GUEST_SESSION_COOKIE)};
const HANDOFF_COOKIE = {json.dumps(_THEME_HANDOFF_COOKIE)};
const ADMIN_EMAIL = 'admin@syss.edu.hk';
const requiredSecret = name => {{
  const value = Deno.env.get(name);
  if (!value) throw new Error(`Missing disposable verifier credential: ${{name}}`);
  return value;
}};

const rateLimiter = {{ async limit() {{ return {{ success: true }}; }} }};
const records = new Map();
const shares = {{
  async get(key) {{ return records.has(key) ? records.get(key) : null; }},
  async put(key, value) {{ records.set(key, value); }},
  async delete(key) {{ records.delete(key); }},
  async list() {{ return {{ keys: [], list_complete: true }}; }},
}};
const env = {{
  ACCESS_TEAM_DOMAIN: 'https://theme-browser.cloudflareaccess.com',
  ACCESS_AUD: 'theme-browser-audience',
  ADMIN_IDENTITY_ALLOWLIST: JSON.stringify({{ emails: [ADMIN_EMAIL] }}),
  ADMIN_BEARER_TOKEN: 'theme-browser-admin-token',
  ADMIN_SESSION_SECRET: requiredSecret('SING_YIN_TEST_ADMIN_SESSION_SECRET'),
  GUEST_SESSION_SECRET: requiredSecret('SING_YIN_TEST_GUEST_SESSION_SECRET'),
  ORIGIN_PRINCIPAL_SECRET: requiredSecret('SING_YIN_TEST_ORIGIN_PRINCIPAL_SECRET'),
  AUTH_EPOCH: {_GATEWAY_AUTH_EPOCH},
  ORIGIN_PRINCIPAL_KID: {json.dumps(_GATEWAY_ORIGIN_PRINCIPAL_KID)},
  ORIGIN_PORT: {origin_port},
  GUEST_START_RATE_LIMITER: rateLimiter,
  PUBLIC_VIEW_RATE_LIMITER: rateLimiter,
  PUBLIC_SUPPORT_RATE_LIMITER: rateLimiter,
  ROSTER_SHARES: shares,
  ROSTER_ORIGIN: {{
    async fetch(request) {{
      const originPrincipal = request.headers.get('X-Sing-Yin-Origin-Principal') || '';
      const forwardedHost = request.headers.get('X-Forwarded-Host') || '';
      const headers = new Headers({{ 'Cache-Control': 'no-store' }});
      // Disposable browser-gate evidence only: capture the exact production
      // Worker signature and binding host without asking Deno to proxy the
      // NiceGUI WebSocket. The signed request is then verified by the real
      // loopback origin in a separate, hydrated browser context.
      if (originPrincipal) headers.set('X-Sing-Yin-Test-Origin-Principal', originPrincipal);
      if (forwardedHost) headers.set('X-Sing-Yin-Test-Forwarded-Host', forwardedHost);
      return new Response(null, {{ status: 204, headers }});
    }},
  }},
}};

function cookieValue(request, name) {{
  const cookie = request.headers.get('Cookie') || '';
  for (const part of cookie.split(';')) {{
    const [rawName, ...rawValue] = part.trim().split('=');
    if (rawName === name) return decodeURIComponent(rawValue.join('='));
  }}
  return '';
}}

function clearCookie(name) {{
  return `${{name}}=; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/; HttpOnly; Secure; SameSite=Lax`;
}}

async function createTestAdminSession(request) {{
  const handoff = cookieValue(request, HANDOFF_COOKIE);
  const themeHandoff = handoff === 'light' || handoff === 'dark' ? handoff : undefined;
  const nowSeconds = Math.floor(Date.now() / 1000);
  const session = await createAdminSessionToken(
    ADMIN_EMAIL,
    nowSeconds + 3600,
    env,
    {{ themeHandoff }},
  );
  const headers = new Headers({{ 'Content-Type': 'application/json; charset=utf-8' }});
  headers.append(
    'Set-Cookie',
    `${{ADMIN_COOKIE}}=${{encodeURIComponent(session.token)}}; Max-Age=3600; Path=/; HttpOnly; Secure; SameSite=Lax`,
  );
  headers.append('Set-Cookie', clearCookie(GUEST_COOKIE));
  headers.append('Set-Cookie', clearCookie(HANDOFF_COOKIE));
  return new Response(JSON.stringify({{ authenticated: true, mode: 'admin', theme: session.payload.theme || null }}), {{
    status: 201,
    headers,
  }});
}}

Deno.serve({{ hostname: '127.0.0.1', port: {worker_port} }}, async request => {{
  const url = new URL(request.url);
  if (url.pathname === '/__theme_test__/admin/session') {{
    if (request.method !== 'POST') return new Response('Method not allowed', {{ status: 405 }});
    return await createTestAdminSession(request);
  }}
  return await worker.fetch(request, env, {{ waitUntil(promise) {{ promise.catch(() => undefined); }} }});
}});
"""


def _start_worker_harness(
    case_root: Path,
    *,
    origin_port: int,
    secret_values: dict[str, str],
) -> tuple[subprocess.Popen[str], Any, str, Path]:
    deno = shutil.which("deno")
    if deno is None:
        raise ThemeControlVerificationError("Deno is required for the real Worker browser gate.")
    worker_port = _free_loopback_port()
    harness_path = case_root / "worker-theme-harness.mjs"
    harness_path.write_text(
        _worker_harness_source(worker_port=worker_port, origin_port=origin_port),
        encoding="utf-8",
    )
    worker_log = case_root / "worker-console.log"
    output = worker_log.open("w", encoding="utf-8")
    worker_environment = os.environ.copy()
    worker_environment.update(
        {
            "SING_YIN_TEST_ADMIN_SESSION_SECRET": secret_values["admin_session"],
            "SING_YIN_TEST_GUEST_SESSION_SECRET": secret_values["guest_session"],
            "SING_YIN_TEST_ORIGIN_PRINCIPAL_SECRET": secret_values["origin_principal"],
        }
    )
    process = subprocess.Popen(
        [
            deno,
            "run",
            "--allow-net=127.0.0.1",
            "--allow-read",
            "--allow-env=SING_YIN_TEST_ADMIN_SESSION_SECRET,SING_YIN_TEST_GUEST_SESSION_SECRET,SING_YIN_TEST_ORIGIN_PRINCIPAL_SECRET",
            str(harness_path),
        ],
        cwd=PROJECT_ROOT,
        env=worker_environment,
        stdout=output,
        stderr=subprocess.STDOUT,
        text=True,
    )
    # Chromium treats ``localhost`` as a potentially trustworthy origin, which
    # is required for the production ``Secure`` + ``__Host-`` gateway cookies.
    # The server remains bound to loopback-only 127.0.0.1.
    worker_url = f"http://localhost:{worker_port}"
    readiness_url = f"http://127.0.0.1:{worker_port}/healthz"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        try:
            with urlopen(readiness_url, timeout=1) as response:  # noqa: S310 - loopback only
                if response.status == 200:
                    return process, output, worker_url, worker_log
        except (URLError, TimeoutError):
            pass
        time.sleep(0.25)
    output.flush()
    tail = worker_log.read_text(encoding="utf-8", errors="replace")[-4_000:]
    _stop_server(process, output)
    raise ThemeControlVerificationError(f"Disposable Worker did not become ready.\n{tail}")


def _signed_payload_from_cookie(value: str) -> dict[str, Any]:
    token = unquote(value)
    payload_segment = token.split(".", 1)[0]
    padding = "=" * ((4 - len(payload_segment) % 4) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_segment + padding).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ThemeControlVerificationError("Gateway session cookie payload is malformed.") from error
    if not isinstance(payload, dict):
        raise ThemeControlVerificationError("Gateway session cookie payload is not an object.")
    return payload


def _captured_origin_principal(
    context: BrowserContext,
    *,
    worker_url: str,
    method: Literal["GET", "POST"] = "GET",
    path: str,
) -> tuple[str, str]:
    request_headers = {"Accept": "text/html"}
    request_data: str | None = None
    if method == "POST":
        request_headers.update(
            {
                "Content-Type": "application/json",
                "Origin": worker_url,
                "Sec-Fetch-Site": "same-origin",
            }
        )
        request_data = "{}"
    response = context.request.fetch(
        worker_url + path,
        method=method,
        headers=request_headers,
        data=request_data,
        timeout=20_000,
    )
    try:
        if response.status != 204:
            raise ThemeControlVerificationError(
                f"Worker did not sign {method} {path!r} for the origin: HTTP {response.status}."
            )
        headers = {name.lower(): value for name, value in response.headers.items()}
        token = headers.get("x-sing-yin-test-origin-principal", "")
        forwarded_host = headers.get("x-sing-yin-test-forwarded-host", "")
        if not token or not forwarded_host:
            raise ThemeControlVerificationError(
                "Disposable Worker did not expose the signed origin-principal evidence."
            )
        return token, forwarded_host
    finally:
        response.dispose()


def _new_context(
    browser: Browser,
    *,
    access_mode: AccessMode,
    viewport_mode: ViewportMode,
    colour_scheme: ColourScheme,
    accessibility_mode: AccessibilityMode = "standard",
) -> BrowserContext:
    options: dict[str, Any] = {
        "viewport": {"width": 1440, "height": 960}
        if viewport_mode == "desktop"
        else {"width": 390, "height": 844},
        "color_scheme": colour_scheme,
        "reduced_motion": "reduce" if accessibility_mode == "reduced-motion" else "no-preference",
        "forced_colors": "active" if accessibility_mode == "forced-colours" else "none",
    }
    if viewport_mode == "mobile":
        options.update({"is_mobile": True, "has_touch": True})
    context = browser.new_context(**options)
    if access_mode == "guest":
        _install_gateway_stubs(context)
    return context


def _theme_control(page: Page, *, viewport_mode: ViewportMode) -> Locator:
    if viewport_mode == "desktop":
        control = page.get_by_test_id("theme-control")
        if control.count() != 1:
            raise ThemeControlVerificationError("Desktop appearance control is not unique.")
        control.wait_for(state="visible", timeout=10_000)
        if page.get_by_test_id("desktop-theme-menu").count() != 0:
            raise ThemeControlVerificationError("Obsolete desktop appearance menu is still rendered.")
        return control

    drawer = _open_mobile_drawer(page)
    _expand_mobile_preferences(page)
    control = drawer.get_by_test_id("mobile-theme-control")
    if control.count() != 1:
        raise ThemeControlVerificationError("Mobile appearance control is not unique.")
    control.wait_for(state="visible", timeout=10_000)
    return control


def _normalise_hex(value: str) -> str:
    return value.strip().lower().replace(" ", "")


def _close_mobile_drawer(page: Page) -> None:
    """Close the mobile drawer and prove its visual and accessible state agree."""

    button = page.get_by_test_id("mobile-more")
    was_open = button.get_attribute("aria-expanded") == "true"
    if was_open:
        page.keyboard.press("Escape")
    page.locator("#main-navigation-drawer").wait_for(state="hidden", timeout=5_000)
    page.wait_for_function(
        """requireFocus => {
          const button = document.querySelector('[data-testid="mobile-more"]');
          return button?.getAttribute('aria-expanded') === 'false' &&
            (!requireFocus || document.activeElement === button);
        }""",
        arg=was_open,
        timeout=5_000,
    )


def _exercise_mobile_drawer_route_cycles(
    page: Page,
    base_url: str,
    *,
    expected_theme: ColourScheme,
    expected_preference: Literal["system", "light", "dark"],
) -> None:
    """Catch route-replacement races between Quasar visibility and ARIA state."""

    _close_mobile_drawer(page)
    for _cycle in range(4):
        for route in ("/", "/platform"):
            _open_route(page, base_url, route)
            page.wait_for_function("() => Boolean(window.__syThemeControls)", timeout=10_000)
            control = _theme_control(page, viewport_mode="mobile")
            _assert_theme_state(
                page,
                control,
                expected_theme=expected_theme,
                expected_preference=expected_preference,
            )
            if not page.evaluate(
                """() => window.__syDrawerA11yOwner ===
                  document.querySelector('[data-testid="mobile-more"]')"""
            ):
                raise ThemeControlVerificationError(
                    "Mobile drawer accessibility owner drifted after a route replacement."
                )
            _close_mobile_drawer(page)


def _assert_theme_state(
    page: Page,
    control: Locator,
    *,
    expected_theme: ColourScheme,
    expected_preference: Literal["system", "light", "dark"],
) -> dict[str, Any]:
    expected_dark = expected_theme == "dark"
    test_id = (
        "mobile-theme-control"
        if control.get_attribute("data-testid") == "mobile-theme-control"
        else "theme-control"
    )
    page.wait_for_function(
        """([testId, expectedTheme, expectedPreference]) => {
          const control = document.querySelector(`[data-testid="${testId}"]`);
          if (!control) return false;
          const rendered = document.body.classList.contains('body--dark') ? 'dark' : 'light';
          const pressedStateIsValid = testId === 'mobile-theme-control'
            ? !control.hasAttribute('aria-pressed')
            : control.getAttribute('aria-pressed') === String(expectedTheme === 'dark');
          return rendered === expectedTheme &&
            control.dataset.themeResolved === expectedTheme &&
            control.dataset.themePreference === expectedPreference &&
            pressedStateIsValid;
        }""",
        arg=[test_id, expected_theme, expected_preference],
        timeout=10_000,
    )

    state = page.evaluate(
        """testId => {
          const control = document.querySelector(`[data-testid="${testId}"]`);
          const icon = control?.querySelector('.q-icon');
          return {
            bodyDark: document.body.classList.contains('body--dark'),
            quasarDark: Boolean(window.Quasar?.Dark?.isActive),
            qPrimary: getComputedStyle(document.body).getPropertyValue('--q-primary'),
            preference: control?.dataset.themePreference || '',
            resolved: control?.dataset.themeResolved || '',
            pressed: control?.getAttribute('aria-pressed') || '',
            label: control?.getAttribute('aria-label') || '',
            title: control?.getAttribute('title') || '',
            actionLight: control?.dataset.actionLight || '',
            actionDark: control?.dataset.actionDark || '',
            icon: (icon?.textContent || '').trim(),
          };
        }""",
        control.get_attribute("data-testid"),
    )
    expected_label = state["actionLight"] if expected_dark else state["actionDark"]
    expected_icon = "dark_mode" if expected_dark else "light_mode"
    failures: list[str] = []
    if state["bodyDark"] is not expected_dark:
        failures.append("body--dark")
    if state["quasarDark"] is not expected_dark:
        failures.append("Quasar.Dark.isActive")
    if _normalise_hex(str(state["qPrimary"])) != EXPECTED_PRIMARY[expected_theme]:
        failures.append(
            f"--q-primary={state['qPrimary']!r}, expected {EXPECTED_PRIMARY[expected_theme]!r}"
        )
    if state["preference"] != expected_preference:
        failures.append(f"preference={state['preference']!r}")
    if state["resolved"] != expected_theme:
        failures.append(f"resolved={state['resolved']!r}")
    expected_pressed = "" if test_id == "mobile-theme-control" else str(expected_dark).lower()
    if state["pressed"] != expected_pressed:
        failures.append(f"aria-pressed={state['pressed']!r}")
    if not expected_label or state["label"] != expected_label or state["title"] != expected_label:
        failures.append("aria-label/title action semantics")
    if state["icon"] != expected_icon:
        failures.append(f"icon={state['icon']!r}, expected {expected_icon!r}")
    if failures:
        raise ThemeControlVerificationError(
            f"Theme state mismatch for {expected_theme}/{expected_preference}: {', '.join(failures)}"
        )
    return state


def _exercise_accessibility_case(
    browser: Browser,
    evidence_root: Path,
    *,
    access_mode: AccessMode,
    accessibility_mode: Literal["reduced-motion", "forced-colours"],
) -> dict[str, Any]:
    case_id = f"{access_mode}-desktop-{accessibility_mode}"
    case_root = (evidence_root / "runtime" / case_id).resolve()
    environment = _safe_environment(case_root, access_mode=access_mode)
    server_log = case_root / "server-console.log"
    process, output = _start_server(environment, server_log)
    context: BrowserContext | None = None
    case_error: BaseException | None = None
    console_errors: list[str] = []
    page_errors: list[str] = []
    try:
        _wait_until_ready(process, environment["SING_YIN_TEST_URL"], server_log)
        context = _new_context(
            browser,
            access_mode=access_mode,
            viewport_mode="desktop",
            colour_scheme="light",
            accessibility_mode=accessibility_mode,
        )
        page = context.new_page()
        page.on(
            "console",
            lambda message: console_errors.append(message.text) if message.type == "error" else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        _open_route(page, environment["SING_YIN_TEST_URL"], "/")
        page.wait_for_function("() => Boolean(window.__syThemeControls)", timeout=10_000)
        control = _theme_control(page, viewport_mode="desktop")
        initial = _assert_theme_state(
            page,
            control,
            expected_theme="light",
            expected_preference="system",
        )

        if accessibility_mode == "reduced-motion":
            page.wait_for_function(
                "() => matchMedia('(prefers-reduced-motion: reduce)').matches && "
                "document.documentElement.dataset.syMotion === 'reduced'",
                timeout=10_000,
            )
            page.evaluate(
                """() => {
                  const control = document.querySelector('[data-testid="theme-control"]');
                  window.__syThemeAnimationObserved = false;
                  window.__syThemeAnimationObserver = new MutationObserver(records => {
                    if (records.some(record => record.attributeName === 'data-sy-icon-changing')) {
                      window.__syThemeAnimationObserved = true;
                    }
                  });
                  window.__syThemeAnimationObserver.observe(control, {attributes: true});
                }"""
            )
        else:
            page.wait_for_function(
                "() => matchMedia('(forced-colors: active)').matches",
                timeout=10_000,
            )
            control.focus()
            if not control.evaluate("element => document.activeElement === element"):
                raise ThemeControlVerificationError("Forced-colours appearance control is not focusable.")

        control.click()
        control = page.get_by_test_id("theme-control")
        toggled = _assert_theme_state(
            page,
            control,
            expected_theme="dark",
            expected_preference="dark",
        )
        if accessibility_mode == "reduced-motion":
            animation_observed = page.evaluate(
                """() => {
                  window.__syThemeAnimationObserver?.disconnect();
                  return Boolean(window.__syThemeAnimationObserved);
                }"""
            )
            if animation_observed:
                raise ThemeControlVerificationError(
                    "Reduced-motion mode still triggered the theme icon animation marker."
                )

        bounds = control.bounding_box()
        if bounds is None or bounds["width"] < 40 or bounds["height"] < 40:
            raise ThemeControlVerificationError(
                f"{accessibility_mode} appearance control lost its minimum target size: {bounds!r}"
            )
        screenshot = _screenshot(page, evidence_root / "screenshots", case_id)
        if console_errors or page_errors:
            raise ThemeControlVerificationError(
                f"{case_id} emitted browser errors: console={console_errors!r}; page={page_errors!r}"
            )
        return {
            "case": case_id,
            "accessMode": access_mode,
            "accessibilityMode": accessibility_mode,
            "initial": initial,
            "toggled": toggled,
            "targetBounds": bounds,
            "screenshot": screenshot,
            "serverLog": str(server_log),
        }
    except BaseException as error:
        case_error = error
        raise
    finally:
        if context is not None:
            context.close()
        _stop_server(process, output)
        try:
            _assert_server_console_clean(server_log)
        except Exception:
            if case_error is None:
                raise


def _screenshot(page: Page, evidence_dir: Path, name: str) -> str:
    path = (evidence_dir / f"{name}.png").resolve()
    page.screenshot(path=str(path), full_page=False)
    return str(path)


def _exercise_case(
    browser: Browser,
    evidence_root: Path,
    *,
    access_mode: AccessMode,
    viewport_mode: ViewportMode,
    colour_scheme: ColourScheme,
) -> dict[str, Any]:
    case_id = f"{access_mode}-{viewport_mode}-os-{colour_scheme}"
    case_root = (evidence_root / "runtime" / case_id).resolve()
    environment = _safe_environment(case_root, access_mode=access_mode)
    server_log = case_root / "server-console.log"
    process, output = _start_server(environment, server_log)
    context: BrowserContext | None = None
    console_errors: list[str] = []
    page_errors: list[str] = []
    case_error: BaseException | None = None
    try:
        _wait_until_ready(process, environment["SING_YIN_TEST_URL"], server_log)
        context = _new_context(
            browser,
            access_mode=access_mode,
            viewport_mode=viewport_mode,
            colour_scheme=colour_scheme,
        )
        page = context.new_page()
        page.on(
            "console",
            lambda message: console_errors.append(message.text) if message.type == "error" else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        _open_route(page, environment["SING_YIN_TEST_URL"], "/")
        page.wait_for_function("() => Boolean(window.__syThemeControls)", timeout=10_000)

        control = _theme_control(page, viewport_mode=viewport_mode)
        initial = _assert_theme_state(
            page,
            control,
            expected_theme=colour_scheme,
            expected_preference="system",
        )
        initial_shot = _screenshot(page, evidence_root / "screenshots", f"{case_id}-initial")

        first_target: ColourScheme = "dark" if colour_scheme == "light" else "light"
        control.click()
        control = page.get_by_test_id(
            "theme-control" if viewport_mode == "desktop" else "mobile-theme-control"
        )
        first_click = _assert_theme_state(
            page,
            control,
            expected_theme=first_target,
            expected_preference=first_target,
        )
        first_click_shot = _screenshot(
            page,
            evidence_root / "screenshots",
            f"{case_id}-first-click-{first_target}",
        )

        _open_route(page, environment["SING_YIN_TEST_URL"], "/platform")
        page.wait_for_function("() => Boolean(window.__syThemeControls)", timeout=10_000)
        control = _theme_control(page, viewport_mode=viewport_mode)
        persisted = _assert_theme_state(
            page,
            control,
            expected_theme=first_target,
            expected_preference=first_target,
        )

        if viewport_mode == "mobile":
            _exercise_mobile_drawer_route_cycles(
                page,
                environment["SING_YIN_TEST_URL"],
                expected_theme=first_target,
                expected_preference=first_target,
            )
            control = _theme_control(page, viewport_mode="mobile")

        control.click()
        control = page.get_by_test_id(
            "theme-control" if viewport_mode == "desktop" else "mobile-theme-control"
        )
        reversed_state = _assert_theme_state(
            page,
            control,
            expected_theme=colour_scheme,
            expected_preference=colour_scheme,
        )
        reverse_shot = _screenshot(
            page,
            evidence_root / "screenshots",
            f"{case_id}-reverse-{colour_scheme}",
        )

        page.reload(wait_until="domcontentloaded", timeout=20_000)
        page.wait_for_selector("main#main-content", timeout=15_000)
        page.wait_for_function("() => Boolean(window.__syThemeControls)", timeout=10_000)
        control = _theme_control(page, viewport_mode=viewport_mode)
        reverse_persisted = _assert_theme_state(
            page,
            control,
            expected_theme=colour_scheme,
            expected_preference=colour_scheme,
        )
        if console_errors or page_errors:
            raise ThemeControlVerificationError(
                f"{case_id} emitted browser errors: console={console_errors!r}; page={page_errors!r}"
            )
        return {
            "case": case_id,
            "accessMode": access_mode,
            "viewport": viewport_mode,
            "osColourScheme": colour_scheme,
            "initial": initial,
            "firstClick": first_click,
            "routePersistence": persisted,
            "reverseToggle": reversed_state,
            "reverseReloadPersistence": reverse_persisted,
            "screenshots": [initial_shot, first_click_shot, reverse_shot],
            "databasePath": environment["SING_YIN_DATABASE_PATH"],
            "niceguiStoragePath": environment["NICEGUI_STORAGE_PATH"],
            "serverLog": str(server_log),
        }
    except BaseException as error:
        case_error = error
        raise
    finally:
        if context is not None:
            context.close()
        _stop_server(process, output)
        try:
            _assert_server_console_clean(server_log)
        except Exception:
            # Preserve the browser-visible contract failure when it caused the
            # matching server exception; otherwise the report would replace
            # the actionable root cause with a generic console marker.
            if case_error is None:
                raise


def _public_theme_state(
    page: Page,
    *,
    expected_theme: ColourScheme,
    expected_preference: Literal["system", "light", "dark"],
) -> dict[str, Any]:
    expected_label = "深色 · Dark" if expected_theme == "dark" else "淺色 · Light"
    page.wait_for_function(
        """([expectedTheme, expectedPreference, expectedLabel]) => {
          const control = document.querySelector('[data-testid="public-theme-control"]');
          if (!control) return false;
          const resolved = control.dataset.resolvedTheme || '';
          const preference = control.dataset.themePreference || '';
          const label = document.getElementById('themeToggleLabel')?.textContent?.trim() || '';
          const rootTheme = document.documentElement.dataset.theme || 'system';
          const rendered = rootTheme === 'system'
            ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
            : rootTheme;
          return resolved === expectedTheme
            && preference === expectedPreference
            && rendered === expectedTheme
            && label === expectedLabel
            && !label.includes('Auto');
        }""",
        arg=[expected_theme, expected_preference, expected_label],
        timeout=10_000,
    )
    return page.evaluate(
        """() => {
          const control = document.querySelector('[data-testid="public-theme-control"]');
          return {
            preference: control?.dataset.themePreference || '',
            resolved: control?.dataset.resolvedTheme || '',
            pressed: control?.getAttribute('aria-pressed') || '',
            label: document.getElementById('themeToggleLabel')?.textContent?.trim() || '',
            rootTheme: document.documentElement.dataset.theme || 'system',
          };
        }"""
    )


def _is_expected_gateway_handoff_request_failure(
    failure: str,
    *,
    worker_url: str,
    origin_url: str,
) -> bool:
    """Classify disposable transport noise after the handoff is proven.

    The Admin callback returns to an HTTPS public root while the disposable
    Worker harness intentionally listens on plain HTTP.  Route replacement can
    also cancel a redundant, already-fulfilled ``/auth/status`` poll after the
    hydrated workbench and its theme persistence have been verified.  These
    failures are safe to suppress only at the end of the successful handoff
    case; every other browser transport failure remains release-blocking.
    """

    disposable_edge = f"https://{urlsplit(worker_url).netloc}/"
    disposable_http_root = f"{worker_url}/"
    origin_status = f"{origin_url.rstrip('/')}/auth/status"
    return (
        failure.startswith(f"public: GET {disposable_edge}: net::ERR_")
        or failure == f"public: GET {disposable_http_root}: net::ERR_ABORTED"
        or failure == f"origin: GET {origin_status}: net::ERR_ABORTED"
        or (
            failure.startswith(f"public: GET {worker_url}/welcome-audio/")
            and failure.endswith(": net::ERR_ABORTED")
        )
    )


def _exercise_gateway_handoff_case(
    browser: Browser,
    evidence_root: Path,
    *,
    access_mode: AccessMode,
    colour_scheme: ColourScheme,
) -> dict[str, Any]:
    """Prove Public -> signed session -> signed origin principal -> workbench adoption."""

    case_id = f"public-to-{access_mode}-os-{colour_scheme}"
    case_root = (evidence_root / "runtime" / case_id).resolve()
    secret_values = _gateway_test_secrets()
    environment = _gateway_environment(case_root, secret_values=secret_values)
    origin_log = case_root / "origin-console.log"
    origin_process, origin_output = _start_server(environment, origin_log)
    worker_process: subprocess.Popen[str] | None = None
    worker_output: Any | None = None
    worker_log: Path | None = None
    context: BrowserContext | None = None
    origin_context: BrowserContext | None = None
    case_error: BaseException | None = None
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []

    def record_request_failure(request: Any, *, source: str) -> None:
        failure = request.failure or "request_failed"
        if failure == "net::ERR_ABORTED" and "/assets/music/" in urlsplit(request.url).path:
            # NiceGUI route replacement intentionally cancels the previous page's
            # streaming ambience request.  It is neither a transport failure nor
            # a leaked listener, so keep it out of the error ledger.
            return
        request_failures.append(f"{source}: {request.method} {request.url}: {failure}")

    try:
        _wait_until_ready(origin_process, environment["SING_YIN_TEST_URL"], origin_log)
        worker_process, worker_output, worker_url, worker_log = _start_worker_harness(
            case_root,
            origin_port=int(environment["SING_YIN_PORT"]),
            secret_values=secret_values,
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 960},
            color_scheme=colour_scheme,
            reduced_motion="no-preference",
        )
        context.route(
            "**/welcome-audio/**",
            lambda route: route.fulfill(status=204, body=""),
        )
        if access_mode == "admin":
        # The production click must stage the bounded handoff before Cloudflare
            # Access takes over.  The disposable harness cannot complete the real
            # Access challenge, so stop only that navigation after the real entry
            # listener has run; the test-only endpoint below then represents the
            # verified Access callback without weakening production Worker code.
            context.route(
                worker_url + "/auth/login",
                lambda route: route.fulfill(
                    status=200,
                    content_type="text/html; charset=utf-8",
                    body="<!doctype html><title>Access test boundary</title>",
                ),
            )
        page = context.new_page()
        page.on(
            "console",
            lambda message: console_errors.append(message.text) if message.type == "error" else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "requestfailed",
            lambda request: record_request_failure(request, source="public"),
        )
        page.goto(worker_url + "/", wait_until="domcontentloaded", timeout=20_000)
        public_control = page.get_by_test_id("public-theme-control")
        public_control.wait_for(state="visible", timeout=10_000)
        initial = _public_theme_state(
            page,
            expected_theme=colour_scheme,
            expected_preference="system",
        )

        target: ColourScheme = "dark" if colour_scheme == "light" else "light"
        public_control.click()
        explicit = _public_theme_state(
            page,
            expected_theme=target,
            expected_preference=target,
        )
        public_shot = _screenshot(
            page,
            evidence_root / "screenshots",
            f"{case_id}-public-{target}",
        )

        if access_mode == "guest":
            page.locator("#guestEnter").click()
            guest_deadline = time.monotonic() + 20
            while time.monotonic() < guest_deadline:
                if any(
                    cookie["name"] == _GUEST_SESSION_COOKIE
                    for cookie in context.cookies(worker_url)
                ):
                    break
                page.wait_for_timeout(100)
            else:
                raise ThemeControlVerificationError(
                    "Guest entry did not establish a signed session through the real button flow."
                )
        else:
            admin_target = page.locator("#adminLogin").get_attribute("href") or ""
            if urlsplit(admin_target).path not in {"/auth/login", "/auth/admin/start"}:
                raise ThemeControlVerificationError("Public Admin entry no longer targets Cloudflare Access.")
            page.locator("#adminLogin").click()
            page.wait_for_url(worker_url + "/auth/login", timeout=20_000)
            response = context.request.post(
                worker_url + "/__theme_test__/admin/session",
                headers={"Accept": "application/json"},
                timeout=20_000,
            )
            try:
                result = {"status": response.status, "body": response.json()}
            finally:
                response.dispose()
            if result.get("status") != 201 or result.get("body", {}).get("theme") != target:
                raise ThemeControlVerificationError(
                    f"Admin harness did not preserve the staged theme: {result!r}"
                )

        cookies = {cookie["name"]: cookie for cookie in context.cookies(worker_url)}
        session_cookie_name = (
            _ADMIN_SESSION_COOKIE if access_mode == "admin" else _GUEST_SESSION_COOKIE
        )
        session_cookie = cookies.get(session_cookie_name)
        if session_cookie is None:
            raise ThemeControlVerificationError(
                f"{access_mode} session cookie was not established by the real gateway flow."
            )
        if _THEME_HANDOFF_COOKIE in cookies:
            raise ThemeControlVerificationError(
                "One-use theme handoff cookie remained after the signed session was established."
            )
        session_payload = _signed_payload_from_cookie(str(session_cookie["value"]))
        if session_payload.get("theme") != target:
            raise ThemeControlVerificationError(
                f"Signed {access_mode} session omitted the expected theme handoff."
            )

        root_token, forwarded_host = _captured_origin_principal(
            context,
            worker_url=worker_url,
            path="/",
        )
        root_payload = _signed_payload_from_cookie(root_token)
        if root_payload.get("theme") != target or root_payload.get("mode") != access_mode:
            raise ThemeControlVerificationError(
                "Worker-signed origin principal did not carry the authenticated theme."
            )
        platform_token, platform_host = _captured_origin_principal(
            context,
            worker_url=worker_url,
            path="/platform",
        )
        principal_tokens: dict[tuple[str, str], tuple[str, str]] = {
            ("GET", "/"): (root_token, forwarded_host),
            ("GET", "/platform"): (platform_token, platform_host),
        }
        if access_mode == "guest":
            snapshot_token, snapshot_host = _captured_origin_principal(
                context,
                worker_url=worker_url,
                method="POST",
                path="/api/guest/snapshot/restore",
            )
            principal_tokens[("POST", "/api/guest/snapshot/restore")] = (
                snapshot_token,
                snapshot_host,
            )

        origin_context = browser.new_context(
            viewport={"width": 1440, "height": 960},
            color_scheme=colour_scheme,
            reduced_motion="no-preference",
        )

        def route_origin_request(route: Any) -> None:
            request = route.request
            parsed = urlsplit(request.url)
            path_and_query = parsed.path + (f"?{parsed.query}" if parsed.query else "")
            if parsed.path == "/auth/status":
                route.fulfill(
                    status=200,
                    content_type="application/json; charset=utf-8",
                    body=json.dumps(
                        {
                            "status": "ok",
                            "gateway": "ok",
                            "access": "ok",
                            "origin": "ok",
                            "authenticated": True,
                            "mode": access_mode,
                            "expiresAt": session_payload.get("exp"),
                            "reference": "GW-THEME-E2E",
                        }
                    ),
                )
                return
            if "/welcome-audio/" in parsed.path:
                route.fulfill(status=204, body="")
                return
            headers = dict(request.headers)
            for name in (
                "x-sing-yin-origin-principal",
                "x-forwarded-host",
                "x-forwarded-proto",
            ):
                headers.pop(name, None)
            evidence = principal_tokens.get((request.method.upper(), path_and_query))
            if evidence is not None:
                token, public_host = evidence
                headers["X-Sing-Yin-Origin-Principal"] = token
                headers["X-Forwarded-Host"] = public_host
                headers["X-Forwarded-Proto"] = "https"
            route.continue_(headers=headers)

        origin_context.route("**/*", route_origin_request)
        workbench_page = origin_context.new_page()
        websocket_urls: list[str] = []
        workbench_page.on("websocket", lambda socket: websocket_urls.append(socket.url))
        workbench_page.on(
            "console",
            lambda message: console_errors.append(message.text) if message.type == "error" else None,
        )
        workbench_page.on("pageerror", lambda error: page_errors.append(str(error)))
        workbench_page.on(
            "requestfailed",
            lambda request: record_request_failure(request, source="origin"),
        )
        _open_route(workbench_page, environment["SING_YIN_TEST_URL"], "/")
        workbench_page.wait_for_function(
            "() => Boolean(window.__syThemeControls) && "
            "Boolean(window.socket?.connected) && window.did_handshake === true",
            timeout=15_000,
        )
        if not websocket_urls or any(
            urlsplit(url).netloc != urlsplit(environment["SING_YIN_TEST_URL"]).netloc
            for url in websocket_urls
        ):
            raise ThemeControlVerificationError(
                f"Hydrated workbench sockets did not stay on the isolated origin: {websocket_urls!r}"
            )
        workbench_control = _theme_control(workbench_page, viewport_mode="desktop")
        adopted = _assert_theme_state(
            workbench_page,
            workbench_control,
            expected_theme=target,
            expected_preference=target,
        )
        callback_target: ColourScheme = "light" if target == "dark" else "dark"
        workbench_control.click()
        _assert_theme_state(
            workbench_page,
            workbench_page.get_by_test_id("theme-control"),
            expected_theme=callback_target,
            expected_preference=callback_target,
        )
        workbench_page.get_by_test_id("theme-control").click()
        _assert_theme_state(
            workbench_page,
            workbench_page.get_by_test_id("theme-control"),
            expected_theme=target,
            expected_preference=target,
        )
        _open_route(workbench_page, environment["SING_YIN_TEST_URL"], "/platform")
        workbench_page.wait_for_function("() => Boolean(window.__syThemeControls)", timeout=15_000)
        persisted = _assert_theme_state(
            workbench_page,
            _theme_control(workbench_page, viewport_mode="desktop"),
            expected_theme=target,
            expected_preference=target,
        )
        workbench_shot = _screenshot(
            workbench_page,
            evidence_root / "screenshots",
            f"{case_id}-workbench-{target}",
        )
        expected_harness_failures = [
            failure
            for failure in request_failures
            if _is_expected_gateway_handoff_request_failure(
                failure,
                worker_url=worker_url,
                origin_url=environment["SING_YIN_TEST_URL"],
            )
        ]
        if expected_harness_failures and len(expected_harness_failures) == len(request_failures):
            # Establishing the Admin session makes the real Worker return to its
            # public HTTPS root.  This disposable harness intentionally exposes
            # only plain HTTP, so Chromium's failed TLS retry is harness noise.
            # Replacing the hydrated origin route may also abort a redundant
            # status poll after the acceptance assertions have already passed.
            # The signed session/principal and hydrated origin assertions above
            # remain the acceptance boundary.
            request_failures.clear()
            if all(
                message.startswith("Failed to load resource: net::ERR_")
                for message in console_errors
            ):
                console_errors.clear()
        if console_errors or page_errors or request_failures:
            raise ThemeControlVerificationError(
                f"{case_id} emitted browser errors: console={console_errors!r}; "
                f"page={page_errors!r}; requests={request_failures!r}"
            )
        return {
            "case": case_id,
            "accessMode": access_mode,
            "osColourScheme": colour_scheme,
            "initialPublic": initial,
            "explicitPublic": explicit,
            "sessionTheme": session_payload.get("theme"),
            "handoffCookieCleared": True,
            "gatewayEvidenceScope": "real Worker session and principal plus hydrated NiceGUI origin",
            "originPrincipalTheme": root_payload.get("theme"),
            "workbenchAdopted": adopted,
            "routePersistence": persisted,
            "screenshots": [public_shot, workbench_shot],
            "originLog": str(origin_log),
            "workerLog": str(worker_log),
            "databasePath": environment["SING_YIN_DATABASE_PATH"],
        }
    except BaseException as error:
        case_error = error
        raise
    finally:
        if origin_context is not None:
            origin_context.close()
        if context is not None:
            context.close()
        if worker_process is not None and worker_output is not None:
            _stop_server(worker_process, worker_output)
        _stop_server(origin_process, origin_output)
        try:
            _assert_server_console_clean(origin_log)
        except Exception:
            if case_error is None:
                raise


def main() -> int:
    evidence_root = Path(tempfile.mkdtemp(prefix="sing-yin-rc31-theme-")).resolve()
    (evidence_root / "screenshots").mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schemaVersion": 2,
        "status": "running",
        "verifiedAt": datetime.now(timezone.utc).isoformat(),
        "evidenceRoot": str(evidence_root),
        "cases": [],
    }
    report_path = evidence_root / "verification.json"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for access_mode in ("admin", "guest"):
                    for viewport_mode in ("desktop", "mobile"):
                        for colour_scheme in ("light", "dark"):
                            report["cases"].append(
                                _exercise_case(
                                    browser,
                                    evidence_root,
                                    access_mode=access_mode,
                                    viewport_mode=viewport_mode,
                                    colour_scheme=colour_scheme,
                                )
                            )
                            report_path.write_text(
                                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8",
                            )
                for access_mode in ("admin", "guest"):
                    for accessibility_mode in ("reduced-motion", "forced-colours"):
                        report["cases"].append(
                            _exercise_accessibility_case(
                                browser,
                                evidence_root,
                                access_mode=access_mode,
                                accessibility_mode=accessibility_mode,
                            )
                        )
                        report_path.write_text(
                            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8",
                        )
                for access_mode in ("admin", "guest"):
                    for colour_scheme in ("light", "dark"):
                        report["cases"].append(
                            _exercise_gateway_handoff_case(
                                browser,
                                evidence_root,
                                access_mode=access_mode,
                                colour_scheme=colour_scheme,
                            )
                        )
                        report_path.write_text(
                            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8",
                        )
            finally:
                browser.close()
        report["status"] = "pass"
        report["completedAt"] = datetime.now(timezone.utc).isoformat()
    except Exception as error:
        report["status"] = "fail"
        report["completedAt"] = datetime.now(timezone.utc).isoformat()
        report["failureType"] = type(error).__name__
        report["failure"] = str(error)
        raise
    finally:
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"RC31 theme evidence: {report_path}", flush=True)
    print(f"RC31 binary appearance verification passed ({len(report['cases'])} cases).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
