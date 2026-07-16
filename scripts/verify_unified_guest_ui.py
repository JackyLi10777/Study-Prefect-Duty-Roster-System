"""Verify the unified NiceGUI operator/guest product on disposable local data.

The release orchestrator starts two loopback origins:

* an isolated local-maintenance origin representing the operator renderer;
* an isolated guest origin using the guarded E2E guest principal override.

This verifier compares the shared route shell, exercises one complete guest
draft action across two tabs, proves that the guest SQLite database did not
change, and verifies browser/session cleanup.  It never accepts a non-loopback
URL or the canonical school database.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from playwright.sync_api import BrowserContext, Error as PlaywrightError, Page, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DATABASE = (PROJECT_ROOT / "data" / "runtime" / "sing-yin-roster.sqlite3").resolve()
DEFAULT_EVIDENCE_DIR = PROJECT_ROOT / "logs" / "unified-guest-verification"
E2E_RUN_ID_PATTERN = re.compile(r"^E2E-[A-F0-9]{12}$")

SHARED_ROUTES = (
    "/",
    "/rosters",
    "/prefects",
    "/handover",
    "/settings",
    "/access-control",
    "/platform",
    "/engineering",
    "/system-architecture",
    "/getting-started",
    "/guide",
    "/devotional",
)

EDITORIAL_PARITY_ROUTES = (
    "/platform",
    "/engineering",
    "/system-architecture",
    "/getting-started",
    "/guide",
    "/devotional",
)

ROUTE_MARKERS = {
    "/": ("[data-testid='dashboard-history']",),
    "/handover": (
        "[data-testid='school-year-rollover']",
        "[data-testid='handover-readiness-grid']",
        "[data-testid='acceptance-status']",
    ),
    "/platform": ("[data-testid='platform-hero']", "[data-testid='capability-map']"),
    "/engineering": ("[data-testid='engineering-hero']", "[data-testid='engineering-gates']"),
    "/system-architecture": (
        "[data-testid='architecture-lifeline-visual']",
        "[data-testid='trust-evidence']",
    ),
    "/getting-started": ("#start-intro", "[data-testid='reference-index']"),
    "/guide": ("[data-testid='guide-troubleshooting']",),
}


class UnifiedGuestVerificationError(RuntimeError):
    """Raised when a unified guest release invariant is not satisfied."""


def isolated_inputs() -> tuple[str, str, Path, Path]:
    """Return validated loopback URLs and disposable evidence/database paths."""

    if os.getenv("SING_YIN_E2E_ISOLATED") != "1":
        raise UnifiedGuestVerificationError("Set SING_YIN_E2E_ISOLATED=1 before unified guest verification.")
    run_id = os.getenv("SING_YIN_E2E_RUN_ID", "").strip()
    if E2E_RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise UnifiedGuestVerificationError("SING_YIN_E2E_RUN_ID must identify one disposable E2E run.")
    if os.getenv("SING_YIN_E2E_ACCESS_MODE", "").strip().lower() != "guest":
        raise UnifiedGuestVerificationError("SING_YIN_E2E_ACCESS_MODE must be guest.")
    if os.getenv("SING_YIN_UNIFIED_GUEST", "").strip().lower() not in {"1", "true", "yes", "on"}:
        raise UnifiedGuestVerificationError("SING_YIN_UNIFIED_GUEST must be enabled.")

    admin_url = os.getenv("SING_YIN_ADMIN_TEST_URL", "").rstrip("/")
    guest_url = os.getenv("SING_YIN_GUEST_TEST_URL", "").rstrip("/")
    for label, value in (("admin", admin_url), ("guest", guest_url)):
        parsed = urlparse(value)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise UnifiedGuestVerificationError(f"The {label} verifier target must be a loopback HTTP URL.")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise UnifiedGuestVerificationError(f"The {label} verifier target must not contain a route or query.")

    database_path = Path(os.getenv("SING_YIN_DATABASE_PATH", "")).expanduser().resolve()
    if database_path == CANONICAL_DATABASE:
        raise UnifiedGuestVerificationError("Unified guest verification refused the canonical school database.")
    if not database_path.is_file():
        raise UnifiedGuestVerificationError("The disposable guest database is not ready.")

    evidence_dir = Path(
        os.getenv("SING_YIN_UNIFIED_GUEST_EVIDENCE_DIR", str(DEFAULT_EVIDENCE_DIR))
    ).expanduser().resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    return admin_url, guest_url, database_path, evidence_dir


def _json_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"bytes": value.hex()}
    if isinstance(value, (str, int, float)) or value is None:
        return value
    return str(value)


def logical_database_fingerprint(database_path: Path) -> tuple[str, dict[str, int]]:
    """Hash logical table content so SQLite bookkeeping cannot hide a guest write."""

    payload: list[dict[str, object]] = []
    counts: dict[str, int] = {}
    with sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True, timeout=5) as connection:
        connection.execute("PRAGMA query_only = ON")
        tables = [
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        for table in tables:
            escaped_table = table.replace('"', '""')
            columns = [
                str(row[1])
                for row in connection.execute(f'PRAGMA table_info("{escaped_table}")')
            ]
            escaped_columns = [column.replace('"', '""') for column in columns]
            select_columns = ", ".join(f'"{column}"' for column in escaped_columns)
            order_columns = ", ".join(f'"{column}"' for column in escaped_columns)
            query = f'SELECT {select_columns} FROM "{escaped_table}"'
            if order_columns:
                query += f" ORDER BY {order_columns}"
            rows = [
                [_json_value(value) for value in row]
                for row in connection.execute(query)
            ]
            counts[table] = len(rows)
            payload.append({"table": table, "columns": columns, "rows": rows})
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), counts


def _request_json(url: str) -> tuple[int, dict[str, Any], dict[str, str]]:
    request = Request(url, headers={"Accept": "application/json"})  # noqa: S310 - validated loopback URL
    try:
        with urlopen(request, timeout=3) as response:  # noqa: S310 - validated loopback URL
            body = json.loads(response.read().decode("utf-8"))
            return response.status, body, {key.lower(): value for key, value in response.headers.items()}
    except HTTPError as error:
        try:
            body = json.loads(error.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            body = {}
        return error.code, body, {key.lower(): value for key, value in error.headers.items()}


def _assert_ready(base_url: str, *, expected_guest_sessions: int | None = None) -> dict[str, Any]:
    status, payload, headers = _request_json(f"{base_url}/readyz")
    if status != 200 or payload.get("status") != "ready" or payload.get("writeReady") is not True:
        raise UnifiedGuestVerificationError(f"Origin readiness failed: status={status}, payload={payload}")
    if "no-store" not in headers.get("cache-control", "").lower():
        raise UnifiedGuestVerificationError("/readyz must be non-cacheable.")
    if expected_guest_sessions is not None and int(payload.get("guestSessions") or 0) != expected_guest_sessions:
        raise UnifiedGuestVerificationError(
            f"Unexpected active guest-session count: {payload.get('guestSessions')!r}"
        )
    return payload


def _wait_for_guest_sessions(base_url: str, expected: int, timeout: float = 8.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        try:
            latest = _assert_ready(base_url)
        except (URLError, TimeoutError, UnifiedGuestVerificationError):
            time.sleep(0.1)
            continue
        if int(latest.get("guestSessions") or 0) == expected:
            return latest
        time.sleep(0.1)
    raise UnifiedGuestVerificationError(
        f"Guest-session cleanup did not reach {expected}; latest={latest.get('guestSessions')!r}"
    )


def _install_gateway_stubs(context: BrowserContext) -> None:
    """Model gateway-only auth endpoints while testing the direct loopback origin."""

    expires_at = int(datetime.now(timezone.utc).timestamp()) + 1_800

    def status_route(route) -> None:  # type: ignore[no-untyped-def]
        route.fulfill(
            status=200,
            content_type="application/json",
            headers={"Cache-Control": "no-store"},
            body=json.dumps(
                {
                    "authenticated": True,
                    "mode": "guest",
                    "expiresAt": expires_at,
                }
            ),
        )

    context.route("**/auth/status", status_route)
    context.route(
        "**/auth/logout",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            headers={"Cache-Control": "no-store"},
            body='{"ok":true}',
        ),
    )


def _wait_for_app(page: Page) -> None:
    page.wait_for_selector("main#main-content", timeout=15_000)
    page.wait_for_selector(".sy-header-title", timeout=10_000)
    page.wait_for_function(
        "() => sessionStorage.getItem('__nicegui_tab_closed') !== 'true'",
        timeout=10_000,
    )
    page.evaluate("document.fonts?.ready || Promise.resolve()")
    page.wait_for_timeout(180)
    overflow = page.evaluate(
        "() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)"
    )
    if int(overflow) > 1:
        raise UnifiedGuestVerificationError(f"Horizontal overflow detected at {page.url}: {overflow}px")


def _open_route(page: Page, base_url: str, route: str) -> None:
    response = None
    try:
        response = page.goto(f"{base_url}{route}", wait_until="domcontentloaded", timeout=20_000)
    except PlaywrightError as error:
        if "ERR_ABORTED" not in str(error):
            raise
    if response is None or response.status != 200:
        # The stable-tab bootstrap may intentionally perform one immediate
        # reload when a duplicated tab is assigned a fresh workspace. In that
        # case Playwright can lose the first navigation response even though
        # the final route and a direct loopback probe are healthy.
        page.wait_for_url(re.compile(rf".*{re.escape(route)}(?:[?#].*)?$"), timeout=10_000)
        probe = page.request.get(f"{base_url}{route}")
        if probe.status != 200:
            raise UnifiedGuestVerificationError(
                f"{route} did not return HTTP 200 (navigation={getattr(response, 'status', None)}, "
                f"probe={probe.status})."
            )
    _wait_for_app(page)
    for marker in ROUTE_MARKERS.get(route, ()):
        page.locator(marker).first.wait_for(state="visible", timeout=10_000)


def _shell_sample(page: Page) -> dict[str, Any]:
    return page.evaluate(
        r"""
        () => {
          const main = document.querySelector('main#main-content');
          const normalize = value => String(value || '').replace(/\s+/g, ' ').trim();
          const navLabels = [...document.querySelectorAll('#main-navigation-drawer button.w-full.justify-start')]
            .map(button => normalize(button.textContent))
            .filter(Boolean);
          const skeleton = [...main.querySelectorAll('section, article, nav, aside')]
            .map(element => {
              const classes = [...element.classList]
                .filter(name => name.startsWith('sy-'))
                .map(name => name.split('--')[0])
                .sort();
              return [
                element.tagName.toLowerCase(),
                /^c[0-9]+$/.test(element.id || '') ? '' : (element.id || ''),
                element.dataset.testid || '',
                [...new Set(classes)].join('.'),
              ].join('|');
            });
          return {
            headerTitle: normalize(document.querySelector('.sy-header-title')?.textContent),
            navLabels,
            skeleton,
          };
        }
        """
    )


def _assert_route_parity(
    admin_page: Page,
    guest_page: Page,
    admin_url: str,
    guest_url: str,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for route in SHARED_ROUTES:
        _open_route(admin_page, admin_url, route)
        _open_route(guest_page, guest_url, route)
        admin = _shell_sample(admin_page)
        guest = _shell_sample(guest_page)
        if admin["headerTitle"] != guest["headerTitle"]:
            raise UnifiedGuestVerificationError(f"Header-title parity failed for {route}.")
        if admin["navLabels"] != guest["navLabels"]:
            raise UnifiedGuestVerificationError(f"Navigation parity failed for {route}.")
        if route in EDITORIAL_PARITY_ROUTES and admin["skeleton"] != guest["skeleton"]:
            admin_only = sorted(set(admin["skeleton"]) - set(guest["skeleton"]))[:5]
            guest_only = sorted(set(guest["skeleton"]) - set(admin["skeleton"]))[:5]
            raise UnifiedGuestVerificationError(
                f"Editorial DOM skeleton parity failed for {route}: "
                f"adminOnly={admin_only}, guestOnly={guest_only}"
            )
        if guest_page.get_by_test_id("guest-mode-banner").count() != 1:
            raise UnifiedGuestVerificationError(f"Guest mode is not explicit on {route}.")
        if admin_page.get_by_test_id("guest-mode-banner").count() != 0:
            raise UnifiedGuestVerificationError(f"Operator route was mislabeled as guest on {route}.")
        results.append(
            {
                "route": route,
                "header": admin["headerTitle"],
                "navigationItems": len(admin["navLabels"]),
                "exactEditorialSkeleton": route in EDITORIAL_PARITY_ROUTES,
            }
        )
    return results


def _assert_guest_restrictions(page: Page, guest_url: str) -> None:
    _open_route(page, guest_url, "/prefects")
    page.get_by_text(re.compile(r"資料匯入|Data import"), exact=True).click()
    page.get_by_test_id("guest-restricted-state").first.wait_for(state="visible", timeout=10_000)

    _open_route(page, guest_url, "/settings")
    page.get_by_test_id("guest-audio-settings").wait_for(state="visible", timeout=10_000)
    page.get_by_test_id("guest-restricted-state").first.wait_for(state="visible", timeout=10_000)

    _open_route(page, guest_url, "/access-control")
    page.get_by_test_id("guest-restricted-state").wait_for(state="visible", timeout=10_000)
    if page.get_by_test_id("operator-access-card").count() or page.get_by_test_id("viewer-access-card").count():
        raise UnifiedGuestVerificationError("Guest access-control route exposed operator controls.")


def _history_count(page: Page) -> int:
    return page.locator("[data-testid='dashboard-history'] .sy-dashboard-history-item").count()


def _tab_storage_keys(page: Page) -> dict[str, str]:
    return page.evaluate(
        "() => Object.fromEntries([...Array(sessionStorage.length)].map((_, index) => {"
        "const key=sessionStorage.key(index); return [key, sessionStorage.getItem(key)]; }))"
    )


def _exercise_cross_tab_isolation(first: Page, second: Page, guest_url: str) -> None:
    _open_route(first, guest_url, "/")
    _open_route(second, guest_url, "/")
    if _history_count(first) != 0 or _history_count(second) != 0:
        raise UnifiedGuestVerificationError("A fresh guest tab did not start from the fixture baseline.")

    _open_route(first, guest_url, "/rosters")
    first.get_by_test_id("history-priority-multiplier").wait_for(state="visible", timeout=10_000)
    first.get_by_role(
        "button",
        name=re.compile(r"生成並儲存草稿|Generate and save draft"),
    ).click()
    first.wait_for_url(re.compile(r".*/rosters/[0-9]+$"), timeout=20_000)
    first.locator("main#main-content").wait_for(state="visible", timeout=10_000)

    _open_route(first, guest_url, "/")
    _open_route(second, guest_url, "/")
    if _history_count(first) != 1:
        raise UnifiedGuestVerificationError(
            "The generating guest tab did not retain its own in-memory draft: "
            f"firstStorage={_tab_storage_keys(first)}, secondStorage={_tab_storage_keys(second)}"
        )
    if _history_count(second) != 0:
        raise UnifiedGuestVerificationError("A guest draft leaked into another tab workspace.")


def _exercise_broadcast_cleanup(first: Page, second: Page) -> None:
    for page in (first, second):
        page.evaluate(
            """
            () => {
              sessionStorage.setItem('sing-yin-e2e-temporary', 'must-disappear');
              const audio = document.createElement('audio');
              audio.id = 'sing-yin-e2e-audio';
              audio.src = 'data:audio/wav;base64,UklGRgQAAABXQVZF';
              document.body.appendChild(audio);
            }
            """
        )
    first.evaluate("() => { window.__syInvalidateAuthSession?.(); return true; }")
    for page in (first, second):
        page.wait_for_function(
            "() => sessionStorage.getItem('sing-yin-e2e-temporary') === null",
            timeout=10_000,
        )


def _assert_clean_browser(
    console_errors: list[str],
    page_errors: list[str],
) -> None:
    if console_errors or page_errors:
        raise UnifiedGuestVerificationError(
            f"Browser errors detected: console={len(console_errors)}, page={len(page_errors)}"
        )


def main() -> int:
    admin_url, guest_url, database_path, evidence_dir = isolated_inputs()
    before_fingerprint, before_counts = logical_database_fingerprint(database_path)
    admin_ready = _assert_ready(admin_url, expected_guest_sessions=0)
    guest_ready = _assert_ready(guest_url, expected_guest_sessions=0)
    console_errors: list[str] = []
    page_errors: list[str] = []
    parity: list[dict[str, object]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        admin_context = browser.new_context(
            viewport={"width": 1440, "height": 1024},
            color_scheme="light",
        )
        guest_context = browser.new_context(
            viewport={"width": 1440, "height": 1024},
            color_scheme="light",
            accept_downloads=True,
        )
        _install_gateway_stubs(guest_context)
        admin_page = admin_context.new_page()
        guest_page = guest_context.new_page()
        second_guest_page = guest_context.new_page()
        for page in (admin_page, guest_page, second_guest_page):
            page.on(
                "console",
                lambda message: console_errors.append(message.text)
                if message.type == "error"
                else None,
            )
            page.on("pageerror", lambda error: page_errors.append(str(error)))

        parity = _assert_route_parity(admin_page, guest_page, admin_url, guest_url)
        _assert_guest_restrictions(guest_page, guest_url)
        _exercise_cross_tab_isolation(guest_page, second_guest_page, guest_url)
        _wait_for_guest_sessions(guest_url, 1)

        _open_route(guest_page, guest_url, "/")
        guest_page.screenshot(path=str(evidence_dir / "unified-guest-desktop-light.png"), full_page=True)
        guest_page.locator(".sy-desktop-header-controls .sy-icon-control").last.click()
        guest_page.locator("body.body--dark").wait_for(state="attached", timeout=10_000)
        guest_page.screenshot(path=str(evidence_dir / "unified-guest-desktop-dark.png"), full_page=True)

        mobile_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            color_scheme="dark",
            is_mobile=True,
            has_touch=True,
        )
        _install_gateway_stubs(mobile_context)
        mobile_page = mobile_context.new_page()
        mobile_page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        mobile_page.on("pageerror", lambda error: page_errors.append(str(error)))
        _open_route(mobile_page, guest_url, "/platform")
        mobile_page.screenshot(path=str(evidence_dir / "unified-guest-mobile-dark.png"), full_page=True)
        mobile_context.close()

        _exercise_broadcast_cleanup(guest_page, second_guest_page)
        guest_context.close()
        _wait_for_guest_sessions(guest_url, 0)
        admin_context.close()
        browser.close()

    after_fingerprint, after_counts = logical_database_fingerprint(database_path)
    if after_fingerprint != before_fingerprint or after_counts != before_counts:
        raise UnifiedGuestVerificationError("Guest browsing changed the disposable official SQLite content.")
    _assert_clean_browser(console_errors, page_errors)

    report = {
        "schemaVersion": 1,
        "status": "pass",
        "verifiedAt": datetime.now(timezone.utc).isoformat(),
        "routes": parity,
        "routeCount": len(parity),
        "editorialParityRouteCount": len(EDITORIAL_PARITY_ROUTES),
        "databaseFingerprintUnchanged": True,
        "databaseTableCount": len(before_counts),
        "crossTabIsolation": True,
        "broadcastCleanup": True,
        "serverWorkspaceCleanup": True,
        "readyz": {
            "admin": {
                "status": admin_ready["status"],
                "writeReady": admin_ready["writeReady"],
            },
            "guest": {
                "status": guest_ready["status"],
                "writeReady": guest_ready["writeReady"],
            },
        },
        "consoleErrorCount": len(console_errors),
        "pageErrorCount": len(page_errors),
        "screenshots": {
            "desktopLight": str(evidence_dir / "unified-guest-desktop-light.png"),
            "desktopDark": str(evidence_dir / "unified-guest-desktop-dark.png"),
            "mobileDark": str(evidence_dir / "unified-guest-mobile-dark.png"),
        },
    }
    report_path = evidence_dir / "verification.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
