"""Verify the unified NiceGUI operator/guest product on disposable local data.

The release orchestrator starts two loopback origins:

* an isolated local-maintenance origin representing the operator renderer;
* an isolated guest origin using the guarded E2E guest principal override.

This verifier compares the shared route shell, drives the real guest product
through the weekly operational lifecycle, proves signed same-tab restoration
and duplicated-tab isolation, checks bounded DEMO downloads, proves that the
guest SQLite database did not change, and verifies browser/session cleanup.
It never accepts a non-loopback URL or the canonical school database.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from io import BytesIO
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

from playwright.sync_api import (
    BrowserContext,
    Download,
    Error as PlaywrightError,
    Locator,
    Page,
    sync_playwright,
)
from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DATABASE = (PROJECT_ROOT / "data" / "runtime" / "sing-yin-roster.sqlite3").resolve()
DEFAULT_EVIDENCE_DIR = PROJECT_ROOT / "logs" / "unified-guest-verification"
E2E_RUN_ID_PATTERN = re.compile(r"^E2E-[A-F0-9]{12}$")
GUEST_SNAPSHOT_STORAGE_KEY = "sing-yin-guest-workspace-snapshot-v1"
FIXTIONAL_PREFECT_NAMES = (
    "陳樂言",
    "林頌恩",
    "黃善行",
    "李思澄",
    "何頌謙",
    "周恩言",
    "張樂晴",
    "郭善恩",
    "謝頌賢",
    "鄭思朗",
    "梁樂謙",
    "吳善晴",
    "許頌言",
    "馬思賢",
    "杜樂恩",
    "葉善澄",
    "馮頌朗",
    "羅思言",
)

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
    "/support",
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


def isolated_inputs() -> tuple[str, str, Path, Path, Path]:
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
    admin_support_dir = Path(os.getenv("SING_YIN_ADMIN_SUPPORT_DIR", "")).expanduser().resolve()
    if not admin_support_dir.is_dir() or PROJECT_ROOT in admin_support_dir.parents:
        raise UnifiedGuestVerificationError("Admin support verification requires an external disposable directory.")
    return admin_url, guest_url, database_path, evidence_dir, admin_support_dir


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


def _wait_for_app_once(page: Page) -> None:
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


def _is_navigation_context_reset(error: PlaywrightError) -> bool:
    message = str(error).lower()
    return "execution context was destroyed" in message and "navigation" in message


def _wait_for_app(page: Page) -> None:
    for attempt in range(3):
        try:
            _wait_for_app_once(page)
            return
        except PlaywrightError as error:
            if not _is_navigation_context_reset(error) or attempt == 2:
                raise
            # A duplicated guest tab intentionally reloads once after receiving
            # a fresh workspace binding. Allow that safe navigation to settle,
            # then repeat the complete shell/font/overflow verification.
            page.wait_for_timeout(120)


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


def _exercise_support_flows(
    admin_page: Page,
    guest_page: Page,
    admin_url: str,
    guest_url: str,
    admin_support_dir: Path,
) -> dict[str, object]:
    """Prove opt-in local Admin storage and non-persistent Guest reporting."""

    existing_admin_incidents = set((admin_support_dir / "inbox").glob("INC-*"))
    _open_route(admin_page, admin_url, "/support?source=/rosters")
    admin_panel = admin_page.locator(".sy-support-admin")
    admin_panel.wait_for(state="visible", timeout=10_000)
    admin_textareas = admin_panel.locator("textarea")
    if admin_textareas.count() < 3:
        raise UnifiedGuestVerificationError("Admin support form does not expose its three core fields.")
    for index, value in enumerate((
        "The fictional draft should remain visible.",
        "The fictional draft was not visible.",
        "Open the roster page.\nGenerate the fictional draft.\nOpen support.",
    )):
        admin_textareas.nth(index).fill(value)
    admin_page.get_by_test_id("preview-support-incident").click()
    admin_dialog = admin_page.locator(".q-dialog")
    admin_dialog.wait_for(state="visible", timeout=10_000)
    admin_dialog.locator(".q-checkbox").click()
    admin_page.get_by_test_id("save-support-incident").click()
    incident_node = admin_page.get_by_test_id("support-incident-id")
    incident_node.wait_for(state="visible", timeout=10_000)
    admin_incident_id = incident_node.inner_text().strip()
    incident_path = admin_support_dir / "inbox" / admin_incident_id
    if not incident_path.is_dir() or not (incident_path / "manifest.json").is_file():
        raise UnifiedGuestVerificationError("Admin support report was not stored in the isolated host inbox.")
    if incident_path in existing_admin_incidents:
        raise UnifiedGuestVerificationError("Admin support verification reused an existing incident bundle.")

    _open_route(guest_page, guest_url, "/support?source=/rosters")
    guest_root = guest_page.get_by_test_id("guest-browser-only-support")
    guest_root.wait_for(state="visible", timeout=10_000)
    if guest_root.locator("input[type=file]").count():
        raise UnifiedGuestVerificationError("Guest support unexpectedly exposes attachments.")
    guest_page.evaluate(
        """() => {
          window.__sySupportFetchCount = 0;
          const original = window.fetch.bind(window);
          window.fetch = (...args) => { window.__sySupportFetchCount += 1; return original(...args); };
        }"""
    )
    guest_root.locator("#sy-support-browser-form button[type=submit]").click()
    if not guest_root.locator("#sy-support-browser-result-actions").is_hidden():
        raise UnifiedGuestVerificationError("Guest support produced a report without required fields.")
    guest_root.locator("#sy-support-expected").fill("The demo roster should remain browser-only.")
    guest_root.locator("#sy-support-actual").fill("The demo roster displayed a fictional vacancy.")
    guest_root.locator("#sy-support-steps").fill("Open the demo roster.\nReview the fictional vacancy.")
    guest_root.locator("#sy-support-browser-form button[type=submit]").click()
    result_actions = guest_root.locator("#sy-support-browser-result-actions")
    result_actions.wait_for(state="visible", timeout=10_000)
    temporary_reference = guest_root.locator("#sy-support-browser-result").inner_text().strip()
    if not temporary_reference.startswith("GUEST-"):
        raise UnifiedGuestVerificationError("Guest support did not create a temporary browser reference.")
    with guest_page.expect_download() as download_info:
        guest_root.locator("#sy-support-browser-download").click()
    download = download_info.value
    payload = json.loads(Path(download.path()).read_text(encoding="utf-8"))
    if payload.get("persistence") != "browser-only" or payload.get("temporary_reference") != temporary_reference:
        raise UnifiedGuestVerificationError("Guest support download does not preserve the browser-only contract.")
    if guest_page.evaluate("() => window.__sySupportFetchCount") != 0:
        raise UnifiedGuestVerificationError("Guest support transmitted the report through fetch.")

    guest_page.reload(wait_until="networkidle")
    refreshed_root = guest_page.get_by_test_id("guest-browser-only-support")
    refreshed_root.wait_for(state="visible", timeout=10_000)
    if refreshed_root.locator("#sy-support-expected").input_value():
        raise UnifiedGuestVerificationError("Guest support survived reload instead of clearing browser state.")
    if not refreshed_root.locator("#sy-support-browser-result-actions").is_hidden():
        raise UnifiedGuestVerificationError("Guest support result survived reload.")
    return {
        "adminHostLocalIncident": admin_incident_id,
        "adminManifestPresent": True,
        "guestTemporaryReference": temporary_reference,
        "guestBrowserOnlyDownload": True,
        "guestFetchCount": 0,
        "guestClearedOnReload": True,
    }


def _history_count(page: Page) -> int:
    return page.locator("[data-testid='dashboard-history'] .sy-dashboard-history-item").count()


def _tab_storage_keys(page: Page) -> dict[str, str]:
    return page.evaluate(
        "() => Object.fromEntries([...Array(sessionStorage.length)].map((_, index) => {"
        "const key=sessionStorage.key(index); return [key, sessionStorage.getItem(key)]; }))"
    )


def _snapshot_record(page: Page) -> dict[str, Any]:
    page.wait_for_function(
        f"() => Boolean(sessionStorage.getItem({json.dumps(GUEST_SNAPSHOT_STORAGE_KEY)}))",
        timeout=10_000,
    )
    value = page.evaluate(
        f"() => JSON.parse(sessionStorage.getItem({json.dumps(GUEST_SNAPSHOT_STORAGE_KEY)}))"
    )
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("workspaceId"), str)
        or not isinstance(value.get("tabId"), str)
        or not isinstance(value.get("revision"), int)
        or not isinstance(value.get("token"), str)
    ):
        raise UnifiedGuestVerificationError("The signed guest snapshot record is malformed.")
    return value


def _select_option(
    page: Page,
    select: Locator,
    *,
    text: re.Pattern[str] | None = None,
    exclude: re.Pattern[str] | None = None,
) -> str:
    select.click()
    menu_items = page.locator(".q-menu .q-item:visible")
    menu_items.first.wait_for(state="visible", timeout=10_000)
    for index in range(menu_items.count()):
        item = menu_items.nth(index)
        label = " ".join(item.inner_text().split())
        if text is not None and text.search(label) is None:
            continue
        if exclude is not None and exclude.search(label) is not None:
            continue
        item.click()
        return label
    raise UnifiedGuestVerificationError(
        f"No eligible select option was visible (text={text!r}, exclude={exclude!r})."
    )


def _selected_text(select: Locator) -> str:
    return " ".join(select.locator(".q-field__native").inner_text().split())


def _wait_for_draft_version(page: Page, version: int) -> None:
    page.wait_for_function(
        r"""
        (expectedVersion) => {
          const text = document.querySelector('.sy-roster-detail-head')?.innerText || '';
          const match = text.match(/(?:版本|Version)\s*(\d+)/);
          return match !== null && Number(match[1]) === expectedVersion;
        }
        """,
        arg=version,
        timeout=30_000,
    )


def _wait_for_enabled_test_control(page: Page, test_id: str) -> None:
    """Wait until a websocket-staged edit has enabled its durable action."""
    page.wait_for_function(
        r"""
        (expectedTestId) => {
          const control = document.querySelector(`[data-testid="${expectedTestId}"]`);
          return Boolean(
            control
            && !control.disabled
            && control.getAttribute('aria-disabled') !== 'true'
          );
        }
        """,
        arg=test_id,
        timeout=10_000,
    )


def _download_bytes(page: Page, trigger: Locator) -> tuple[str, bytes]:
    with page.expect_download(timeout=30_000) as download_info:
        trigger.click()
    download: Download = download_info.value
    path = download.path()
    if path is None:
        raise UnifiedGuestVerificationError("The browser did not expose the generated download.")
    content = Path(path).read_bytes()
    if not content:
        raise UnifiedGuestVerificationError(f"The generated download {download.suggested_filename!r} is empty.")
    return download.suggested_filename, content


def _pdf_text(content: bytes) -> str:
    if not content.startswith(b"%PDF-"):
        raise UnifiedGuestVerificationError("A generated PDF does not begin with a PDF header.")
    try:
        return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
    except Exception as error:  # pragma: no cover - release verifier diagnostic
        raise UnifiedGuestVerificationError("A generated PDF could not be parsed.") from error


def _demo_download_evidence(
    *,
    filename: str,
    content: bytes,
    kind: str,
    language: str | None = None,
) -> dict[str, object]:
    if kind == "json":
        try:
            payload = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise UnifiedGuestVerificationError("The DEMO JSON download is invalid.") from error
        if (
            "DEMO" not in filename
            or payload.get("demo") is not True
            or payload.get("fictional") is not True
            or "demo" not in str(payload.get("evidenceType", "")).lower()
        ):
            raise UnifiedGuestVerificationError("The JSON evidence is not explicitly marked as fictional DEMO data.")
    elif kind in {"roster-pdf", "summary-pdf"}:
        text = _pdf_text(content)
        if kind == "roster-pdf":
            expected_filename_marker = "PRACTICE_"
            expected_document_marker = (
                "練習版本" if language == "zh" else "PRACTICE VERSION"
            )
        else:
            expected_filename_marker = "SYSS_DEMO"
            expected_document_marker = "DEMO"
        if expected_filename_marker not in filename or expected_document_marker not in text:
            raise UnifiedGuestVerificationError(
                f"The {kind} download is not visibly marked as a fictional demonstration."
            )
        title = (
            "聖言中學導學風紀"
            if language == "zh"
            else (
                "Sing Yin Secondary School"
                if kind == "roster-pdf"
                else "Sing Yin Study Prefect"
            )
        )
        if title not in text:
            raise UnifiedGuestVerificationError(
                f"The {language} {kind} does not contain its expected bilingual title."
            )
        if not any(name in text for name in FIXTIONAL_PREFECT_NAMES):
            raise UnifiedGuestVerificationError(
                f"The {language} {kind} did not preserve a fictional Chinese prefect name."
            )
    else:  # pragma: no cover - programming guard
        raise ValueError(f"Unsupported DEMO download kind: {kind}")
    return {
        "filename": filename,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "kind": kind,
        "language": language,
    }


def _assert_fixture_directory(page: Page, guest_url: str) -> None:
    _open_route(page, guest_url, "/prefects")
    for name in FIXTIONAL_PREFECT_NAMES[:3]:
        page.get_by_text(name, exact=True).first.wait_for(state="visible", timeout=10_000)


def _download_roster_pdfs(page: Page) -> list[dict[str, object]]:
    page.get_by_role(
        "button",
        name=re.compile(r"下載列印版 PDF|Download print-ready PDF"),
    ).click()
    evidence: list[dict[str, object]] = []
    for language, prepare_pattern, filename_pattern in (
        ("zh", r"準備中文週表 PDF|Prepare Chinese schedule PDF", r"_中文\.pdf$"),
        ("en", r"準備英文週表 PDF|Prepare English schedule PDF", r"_EN\.pdf$"),
    ):
        page.get_by_role("button", name=re.compile(prepare_pattern)).click()
        ready = page.get_by_test_id("pdf-delivery-ready")
        ready.wait_for(state="visible", timeout=30_000)
        ready.get_by_text(re.compile(filename_pattern)).wait_for(state="visible", timeout=10_000)
        filename, content = _download_bytes(
            page,
            ready.get_by_test_id("download-prepared-pdf"),
        )
        evidence.append(
            _demo_download_evidence(
                filename=filename,
                content=content,
                kind="roster-pdf",
                language=language,
            )
        )
    page.get_by_role("button", name=re.compile(r"取消|Cancel")).last.click()
    return evidence


def _exercise_weekly_workflow(page: Page, guest_url: str) -> dict[str, object]:
    """Drive the same guest renderer through the real weekly operational flow."""

    _assert_fixture_directory(page, guest_url)
    _open_route(page, guest_url, "/rosters")
    page.get_by_test_id("history-priority-multiplier").wait_for(state="visible", timeout=10_000)
    # NiceGUI keeps the page-level music dialog mounted while it is closed, and
    # the Assist assignment mode adds another visible select.  Target the
    # operational field by its stable contract instead of DOM position.
    leave_prefect = page.get_by_test_id("pre-generation-leave-prefect")
    chosen_leave_prefect = _select_option(page, leave_prefect)
    if not any(name in chosen_leave_prefect for name in FIXTIONAL_PREFECT_NAMES):
        raise UnifiedGuestVerificationError(
            "The pre-generation leave selector did not offer a fictional prefect."
        )
    leave_reason = "示範請假（不會長期儲存）"
    page.locator("input[name='pre-generation-leave-reason']").fill(leave_reason)
    page.get_by_role("button", name=re.compile(r"登記請假|Record leave")).click()
    page.locator("main#main-content .sy-mobile-list-action").filter(
        has_text=leave_reason,
    ).wait_for(
        state="visible",
        timeout=20_000,
    )

    page.get_by_role(
        "button",
        name=re.compile(r"生成並儲存草稿|Generate and save draft"),
    ).click()
    page.wait_for_url(re.compile(r".*/rosters/[0-9]+$"), timeout=30_000)
    _wait_for_app(page)
    roster_week_id = int(page.url.rstrip("/").rsplit("/", 1)[-1])

    draft_grid = page.get_by_test_id("draft-grid-editor")
    draft_grid.wait_for(state="visible", timeout=10_000)
    editable_cells = draft_grid.locator('[data-cell-key].sy-draft-grid-cell--assigned')
    editable_cells.first.wait_for(state="visible", timeout=10_000)
    if editable_cells.count() < 1:
        raise UnifiedGuestVerificationError("The draft matrix exposed no editable assigned cells.")

    original_monday_cells = draft_grid.locator(
        '[data-cell-key^="MONDAY:"].sy-draft-grid-cell--assigned'
    )
    original_monday_cells.first.wait_for(state="visible", timeout=10_000)
    original_monday: list[tuple[str, str]] = []
    for index in range(original_monday_cells.count()):
        cell = original_monday_cells.nth(index)
        cell_key = cell.get_attribute("data-cell-key")
        prefect_name = " ".join(cell.locator(".sy-draft-cell-name").inner_text().split())
        if not cell_key or prefect_name not in FIXTIONAL_PREFECT_NAMES:
            raise UnifiedGuestVerificationError(
                "The original Monday matrix did not expose a stable fictional assignment."
            )
        original_monday.append((cell_key, prefect_name))

    day_toggle = page.get_by_test_id("draft-day-toggle-monday")
    day_toggle.wait_for(state="visible", timeout=10_000)
    day_toggle.click()
    day_confirm = page.get_by_test_id("draft-day-confirm-close-monday")
    day_confirm.wait_for(state="visible", timeout=10_000)
    day_confirm.click()
    _wait_for_enabled_test_control(page, "draft-save-all")
    page.get_by_test_id("draft-save-all").click()
    _wait_for_draft_version(page, 2)
    page.locator(".sy-draft-grid-day-closed").wait_for(state="visible", timeout=10_000)

    # A full reload in the same authenticated Guest session must restore the
    # signed in-memory snapshot, including the persisted closed-day override.
    page.reload(wait_until="domcontentloaded")
    _wait_for_app(page)
    page.get_by_test_id("draft-grid-editor").wait_for(state="visible", timeout=10_000)
    page.locator(".sy-draft-grid-day-closed").wait_for(state="visible", timeout=10_000)
    # The confirmation dialog is created only after the operator asks to
    # reopen the persisted closed day.  The closed column above is the durable
    # state proof; requiring an unopened dialog here would test an impossible
    # DOM state rather than snapshot restoration.
    page.get_by_test_id("draft-day-toggle-monday").click()
    reopen_monday = page.get_by_test_id("draft-day-confirm-reopen-monday")
    reopen_monday.wait_for(state="visible", timeout=10_000)
    reopen_monday.click()
    _wait_for_enabled_test_control(page, "draft-save-all")
    page.get_by_test_id("draft-save-all").click()
    _wait_for_draft_version(page, 3)
    monday_vacancies = page.locator(
        '[data-cell-key^="MONDAY:"].sy-draft-grid-cell--vacant'
    )
    if monday_vacancies.count() != len(original_monday):
        raise UnifiedGuestVerificationError(
            "Reopening the Guest closed day did not reset every removed assignment to vacancy."
        )

    # Compact tablet evidence uses the same underlying cells and editor. Enter
    # the documented X alias from a touch-sized day card, prove that it becomes
    # an explicit pending vacancy, then undo it so the publish flow remains
    # complete. Blank input is covered separately and must never clear a cell.
    page.set_viewport_size({"width": 768, "height": 1024})
    page.locator(".q-drawer__backdrop").wait_for(state="hidden", timeout=5_000)
    mobile_day = page.locator(".sy-draft-mobile-day:visible").first
    mobile_day.wait_for(state="visible", timeout=10_000)
    mobile_assignment = page.locator(".sy-draft-mobile-cell--assigned:visible").first
    mobile_assignment.wait_for(state="visible", timeout=10_000)
    mobile_cell_key = mobile_assignment.get_attribute("data-cell-key")
    if not mobile_cell_key:
        raise UnifiedGuestVerificationError(
            "The compact draft card did not expose a stable cell key."
        )
    mobile_assignment.click()
    mobile_candidate_search = page.locator(
        f'[data-testid="draft-candidate-search-mobile"][data-cell-key="{mobile_cell_key}"]'
    )
    mobile_candidate_search.wait_for(state="visible", timeout=10_000)
    mobile_candidate_search.click()
    # Quasar creates and replaces the searchable input as the select gains
    # focus.  Typing through the focused control exercises the real keyboard
    # contract without retaining a locator to a transient input node.
    page.keyboard.type("X")
    vacancy_option = page.locator(".q-menu .q-item:visible").filter(
        has_text=re.compile(r"X\s*/\s*×", re.IGNORECASE)
    ).first
    vacancy_option.wait_for(state="visible", timeout=10_000)
    vacancy_option.click()
    page.locator(
        ".sy-draft-mobile-cell--vacant.sy-draft-mobile-cell--pending:visible"
    ).first.wait_for(
        state="visible",
        timeout=10_000,
    )
    page.get_by_test_id("draft-mobile-editor-close").click()
    page.get_by_test_id("draft-undo-mobile").click()
    page.set_viewport_size({"width": 1440, "height": 1024})

    # Restore the removed assignments through the same browser editor before
    # publishing. This keeps the verifier honest: reopening creates vacancies,
    # while a complete schedule only returns after an explicit batch save.
    for cell_key, prefect_name in original_monday:
        page.locator(
            f'[data-cell-key="{cell_key}"].sy-draft-grid-cell:visible'
        ).click()
        restore_candidate = page.locator(
            f'[data-testid="draft-candidate-search"][data-cell-key="{cell_key}"]'
        )
        restore_candidate.wait_for(state="visible", timeout=10_000)
        _select_option(
            page,
            restore_candidate,
            text=re.compile(rf"^{re.escape(prefect_name)}(?:\s|·|$)"),
        )
        # NiceGUI applies the select change over its websocket and refreshes
        # the shared editor panel.  Wait for the durable pending-cell render
        # before opening the next cell; otherwise the previous refresh can
        # replace the next selector after it has been clicked.
        page.locator(
            f'[data-cell-key="{cell_key}"].sy-draft-grid-cell--pending:visible'
        ).wait_for(state="visible", timeout=10_000)
    page.get_by_test_id("draft-save-all").click()
    _wait_for_draft_version(page, 4)
    restored_monday = page.locator(
        '[data-cell-key^="MONDAY:"].sy-draft-grid-cell--assigned'
    )
    if restored_monday.count() != len(original_monday):
        raise UnifiedGuestVerificationError(
            "The Guest browser did not restore every Monday assignment before publish."
        )

    draft_grid = page.get_by_test_id("draft-grid-editor")
    editable_cells = draft_grid.locator('[data-cell-key].sy-draft-grid-cell--assigned')
    editable_cell = editable_cells.first
    draft_cell_key = editable_cell.get_attribute("data-cell-key")
    if not draft_cell_key:
        raise UnifiedGuestVerificationError("The selected Guest draft cell has no stable key.")
    original_draft_name = " ".join(
        editable_cell.locator(".sy-draft-cell-name").inner_text().split()
    )
    editable_cell.click()
    candidate_search = page.locator(
        f'[data-testid="draft-candidate-search"][data-cell-key="{draft_cell_key}"]'
    )
    candidate_search.wait_for(state="visible", timeout=10_000)
    chosen_draft_candidate = _select_option(
        page,
        candidate_search,
        exclude=re.compile(
            rf"^{re.escape(original_draft_name)}(?:\s|·|\(|$)"
            r"|目前安排|Current assignment|空缺|Vacant|unassigned",
            re.IGNORECASE,
        ),
    )
    replacement_draft_name = next(
        (
            name
            for name in FIXTIONAL_PREFECT_NAMES
            if re.search(
                rf"^{re.escape(name)}(?:\s|·|\(|$)",
                chosen_draft_candidate,
            )
        ),
        "",
    )
    if not replacement_draft_name or replacement_draft_name == original_draft_name:
        raise UnifiedGuestVerificationError(
            "The Guest draft verifier did not choose a different prefect."
        )
    draft_reason = page.locator("textarea[name='draft-batch-reason']")
    if draft_reason.input_value() != "":
        raise UnifiedGuestVerificationError("The optional draft-batch reason did not start blank.")
    page.get_by_test_id("draft-save-all").click()
    _wait_for_draft_version(page, 5)
    changed_draft_cell = page.locator(
        f'[data-cell-key="{draft_cell_key}"].sy-draft-grid-cell--assigned:visible'
    ).first
    changed_draft_cell.wait_for(state="visible", timeout=10_000)
    changed_draft_name = " ".join(
        changed_draft_cell.locator(".sy-draft-cell-name").inner_text().split()
    )
    if (
        changed_draft_name != replacement_draft_name
        or changed_draft_name == original_draft_name
    ):
        raise UnifiedGuestVerificationError(
            "The saved Guest draft cell did not display the selected replacement prefect."
        )

    page.get_by_role("button", name=re.compile(r"發布週表|Publish roster")).click()
    page.get_by_role(
        "button",
        name=re.compile(r"確認發布並入帳|Publish and post to ledger"),
    ).click()
    page.get_by_role(
        "button",
        name=re.compile(r"處理請假調整|Handle leave adjustment"),
    ).first.wait_for(state="visible", timeout=30_000)
    roster_downloads = _download_roster_pdfs(page)

    _open_route(page, guest_url, f"/rosters/{roster_week_id}/adjustments")
    adjustment_selects = page.locator("main#main-content .q-select:visible")
    original_assignment = _selected_text(adjustment_selects.nth(0))
    page.get_by_role(
        "button",
        name=re.compile(r"載入合資格替補|Load eligible substitutes"),
    ).click()
    replacement = _select_option(
        page,
        adjustment_selects.nth(1),
        exclude=re.compile(r"保留空缺|Keep vacancy|Vacant", re.IGNORECASE),
    )
    adjustment_reason = page.locator("textarea[name='leave-adjustment-reason']")
    if adjustment_reason.input_value() != "":
        raise UnifiedGuestVerificationError("The optional leave-adjustment reason did not start blank.")
    page.get_by_role(
        "button",
        name=re.compile(r"儲存請假調整|Save leave adjustment"),
    ).click()
    adjustment_receipt = page.get_by_test_id("export-updated-roster")
    adjustment_receipt.wait_for(state="visible", timeout=30_000)
    receipt_text = " ".join(
        adjustment_receipt.locator("xpath=ancestor::*[@role='dialog'][1]").inner_text().split()
    )
    original_name = next((name for name in FIXTIONAL_PREFECT_NAMES if name in original_assignment), "")
    replacement_name = next((name for name in FIXTIONAL_PREFECT_NAMES if name in replacement), "")
    if not original_name or not replacement_name or original_name not in receipt_text or replacement_name not in receipt_text:
        raise UnifiedGuestVerificationError("The published-duty adjustment receipt did not prove its fairness transfer.")
    page.get_by_role(
        "button",
        name=re.compile(r"核對更新後週表|Review updated roster"),
    ).click()
    page.wait_for_url(re.compile(rf".*/rosters/{roster_week_id}$"), timeout=20_000)

    return {
        "rosterWeekId": roster_week_id,
        "preGenerationLeave": True,
        "manualDraftChange": {
            "reasonOptional": True,
            "candidate": chosen_draft_candidate,
            "originalName": original_draft_name,
            "replacementName": replacement_draft_name,
        },
        "dayClosure": {
            "saved": True,
            "sameSessionReloaded": True,
            "reopenedAsVacant": True,
            "restoredForPublish": True,
            "tabletDayCardEdited": True,
            "vacancyAliasEntered": "X",
        },
        "demoPublish": True,
        "rosterDownloads": roster_downloads,
        "publishedDutyAdjustment": {
            "original": original_name,
            "replacement": replacement_name,
            "reasonOptional": True,
            "fairnessTransferReceipt": True,
        },
    }


def _exercise_summary_downloads(page: Page, guest_url: str) -> dict[str, object]:
    _open_route(page, guest_url, "/prefects")
    page.get_by_role("tab", name=re.compile(r"公平審核|Audit|Fairness")).click()
    metrics = page.get_by_test_id("summary-report-metrics")
    metrics.wait_for(state="visible", timeout=20_000)
    metrics_text = " ".join(metrics.inner_text().split())
    if not re.search(r"一致|Balanced", metrics_text):
        raise UnifiedGuestVerificationError("The demo fairness ledger did not reconcile after its adjustment.")

    downloads: list[dict[str, object]] = []
    for test_id, language in (
        ("download-summary-zh", "zh"),
        ("download-summary-en", "en"),
    ):
        filename, content = _download_bytes(page, page.get_by_test_id(test_id))
        downloads.append(
            _demo_download_evidence(
                filename=filename,
                content=content,
                kind="summary-pdf",
                language=language,
            )
        )
    json_filename, json_content = _download_bytes(
        page,
        page.get_by_test_id("download-summary-json"),
    )
    downloads.append(
        _demo_download_evidence(
            filename=json_filename,
            content=json_content,
            kind="json",
        )
    )
    return {
        "ledgerBalanced": True,
        "downloads": downloads,
    }


def _reload_and_verify_signed_snapshot(page: Page) -> dict[str, object]:
    before = _snapshot_record(page)
    before_history = _history_count(page)
    if before_history != 1:
        raise UnifiedGuestVerificationError("The completed guest workflow was not visible before refresh.")
    try:
        page.reload(wait_until="domcontentloaded", timeout=20_000)
    except PlaywrightError as error:
        if "ERR_ABORTED" not in str(error):
            raise
    _wait_for_app(page)
    page.wait_for_function(
        "() => document.body.dataset.syGuestSnapshotRestore === 'accepted'",
        timeout=15_000,
    )
    after = _snapshot_record(page)
    if (
        after["workspaceId"] != before["workspaceId"]
        or after["tabId"] != before["tabId"]
        or int(after["revision"]) < int(before["revision"])
        or _history_count(page) != before_history
    ):
        raise UnifiedGuestVerificationError("Same-tab refresh did not preserve the signed guest workspace.")
    return {
        "accepted": True,
        "workspaceStable": True,
        "revisionBefore": int(before["revision"]),
        "revisionAfter": int(after["revision"]),
        "historyPreserved": True,
    }


def _exercise_handover_reset_restore(page: Page, guest_url: str) -> dict[str, object]:
    _open_route(page, guest_url, "/settings")
    create_backup = page.get_by_test_id("create-verified-backup-action").first
    create_backup.wait_for(state="visible", timeout=10_000)
    create_backup.click()
    package_action = page.get_by_test_id("handover-package-ready-action")
    package_action.wait_for(state="visible", timeout=30_000)
    package_action.click()
    handover_filename, handover_content = _download_bytes(
        page,
        page.get_by_role(
            "button",
            name=re.compile(r"建立並下載交接備份包|Create and download handover package"),
        ),
    )
    try:
        handover_payload = json.loads(handover_content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UnifiedGuestVerificationError("The in-memory DEMO handover package is invalid.") from error
    if (
        "DEMO" not in handover_filename
        or handover_payload.get("demo") is not True
        or handover_payload.get("fictional") is not True
    ):
        raise UnifiedGuestVerificationError("The handover package is not explicitly marked as DEMO data.")

    _open_route(page, guest_url, "/handover")
    page.get_by_test_id("open-school-year-rollover").click()
    confirmation = page.locator(
        "[data-testid='school-year-rollover-confirmation'] input,"
        "input[data-testid='school-year-rollover-confirmation']"
    )
    confirmation.fill("新學年重置")
    page.get_by_test_id("confirm-school-year-rollover").click()
    page.wait_for_url(re.compile(r".*/prefects$"), timeout=30_000)
    page.get_by_test_id("empty-prefect-directory").wait_for(state="visible", timeout=20_000)

    _open_route(page, guest_url, "/settings")
    page.get_by_test_id("restore-ready-action").wait_for(state="visible", timeout=20_000)
    page.get_by_test_id("restore-ready-action").click()
    # The handover action already exists before restore, so it cannot be used
    # as a completion signal. Wait for the intentional settings-page reload;
    # otherwise a following route change can race the restore callback and be
    # overwritten by its late ``ui.navigate.reload()``.
    with page.expect_navigation(
        url=re.compile(r".*/settings(?:[?#].*)?$"),
        wait_until="domcontentloaded",
        timeout=30_000,
    ):
        page.get_by_test_id("confirm-restore-action").click()
    _wait_for_app(page)
    page.get_by_test_id("handover-package-ready-action").wait_for(state="visible", timeout=30_000)
    _assert_fixture_directory(page, guest_url)
    _open_route(page, guest_url, "/")
    if _history_count(page) != 1:
        raise UnifiedGuestVerificationError("The in-memory DEMO restore did not recover the completed roster.")
    return {
        "checkpointCreated": True,
        "handoverDownload": {
            "filename": handover_filename,
            "bytes": len(handover_content),
            "sha256": hashlib.sha256(handover_content).hexdigest(),
        },
        "schoolYearReset": True,
        "emptyDirectoryObserved": True,
        "controlledRestore": True,
        "completedRosterRecovered": True,
    }


def _exercise_true_duplicate_and_tamper(
    source: Page,
    guest_url: str,
    *,
    register_page,
) -> tuple[Page, dict[str, object]]:
    _open_route(source, guest_url, "/")
    # Once another guest workspace exists (for example the mobile evidence
    # context), the first HTTP composition deliberately uses a neutral
    # fixture until the websocket supplies this tab's stable identity. Binding
    # then triggers one safe reload. Wait for that real workspace DOM before
    # taking the source snapshot or asserting cross-tab isolation.
    source.locator(
        "[data-testid='dashboard-history'] .sy-dashboard-history-item"
    ).first.wait_for(state="visible", timeout=20_000)
    source_snapshot = _snapshot_record(source)
    if _history_count(source) != 1:
        raise UnifiedGuestVerificationError("The source tab lost its completed DEMO workflow.")
    with source.expect_popup(timeout=15_000) as popup_info:
        source.evaluate("() => window.open(window.location.href, '_blank')")
    duplicate = popup_info.value
    register_page(duplicate)
    _wait_for_app(duplicate)
    duplicate.wait_for_function(
        f"""sourceWorkspace => {{
          try {{
            const record = JSON.parse(sessionStorage.getItem({json.dumps(GUEST_SNAPSHOT_STORAGE_KEY)}));
            return record?.workspaceId && record.workspaceId !== sourceWorkspace;
          }} catch {{ return false; }}
        }}""",
        arg=source_snapshot["workspaceId"],
        timeout=20_000,
    )
    duplicate_snapshot = _snapshot_record(duplicate)
    _open_route(duplicate, guest_url, "/")
    if _history_count(duplicate) != 0 or _history_count(source) != 1:
        raise UnifiedGuestVerificationError("A truly duplicated browser tab shared mutable guest state.")

    encoded_payload, encoded_signature = str(duplicate_snapshot["token"]).rsplit(".", 1)
    tampered_signature = (
        ("A" if encoded_signature[0] != "A" else "B") + encoded_signature[1:]
    )
    tampered_token = f"{encoded_payload}.{tampered_signature}"
    duplicate.evaluate(
        f"""record => {{
          record.token = {json.dumps(tampered_token)};
          sessionStorage.setItem({json.dumps(GUEST_SNAPSHOT_STORAGE_KEY)}, JSON.stringify(record));
        }}""",
        duplicate_snapshot,
    )
    try:
        duplicate.reload(wait_until="domcontentloaded", timeout=20_000)
    except PlaywrightError as error:
        if "ERR_ABORTED" not in str(error):
            raise
    _wait_for_app(duplicate)
    duplicate.wait_for_function(
        "() => document.body.dataset.syGuestSnapshotRestore === 'safe-fixture'",
        timeout=15_000,
    )
    if _history_count(duplicate) != 0:
        raise UnifiedGuestVerificationError("A tampered snapshot replaced the duplicated tab's safe fixture.")
    fresh_duplicate_snapshot = _snapshot_record(duplicate)
    if fresh_duplicate_snapshot["token"] == tampered_token:
        raise UnifiedGuestVerificationError("The rejected tampered snapshot was not rotated.")
    return duplicate, {
        "copiedSessionStorageDetected": True,
        "workspaceIsolated": True,
        "sourceHistoryCount": 1,
        "duplicateHistoryCount": 0,
        "tamperedSnapshotRejected": True,
        "safeFixtureRetained": True,
        "tokenRotated": True,
    }


def _exercise_broadcast_cleanup(first: Page, second: Page) -> None:
    pages = (first, second)
    for index, page in enumerate(pages, start=1):
        try:
            page.wait_for_function(
                "typeof window.__syInvalidateAuthSession === 'function' "
                "&& document.body.dataset.syAuthStatus === 'verified'",
                timeout=15_000,
            )
        except PlaywrightError as error:
            state = page.evaluate(
                """
                () => ({
                  url: location.href,
                  lang: document.documentElement.lang,
                  authStatus: document.body.dataset.syAuthStatus || null,
                  controller: typeof window.__syInvalidateAuthSession,
                })
                """
            )
            raise UnifiedGuestVerificationError(
                f"Guest cleanup controller was not ready in tab {index}: {state}."
            ) from error
        page.evaluate(
            """
            () => {
              sessionStorage.setItem('sing-yin-e2e-temporary', 'must-disappear');
              const audio = document.createElement('audio');
              audio.id = 'sing-yin-e2e-audio';
              document.body.appendChild(audio);
            }
            """
        )
    first.evaluate("() => { window.__syInvalidateAuthSession?.(); return true; }")
    for index, page in enumerate(pages, start=1):
        try:
            page.wait_for_function(
                """
                () => sessionStorage.getItem('sing-yin-e2e-temporary') === null
                  && document.querySelector('#sing-yin-e2e-audio')?.getAttribute('src') === null
                """,
                timeout=15_000,
            )
        except PlaywrightError as error:
            state = page.evaluate(
                """
                () => ({
                  temporary: sessionStorage.getItem('sing-yin-e2e-temporary'),
                  authStatus: document.body.dataset.syAuthStatus || null,
                  controller: typeof window.__syInvalidateAuthSession,
                })
                """
            )
            raise UnifiedGuestVerificationError(
                f"Guest broadcast cleanup did not reach tab {index}: {state}."
            ) from error


def _assert_clean_browser(
    console_errors: list[str],
    page_errors: list[str],
) -> None:
    if console_errors or page_errors:
        details = [
            *(f"console: {message}" for message in console_errors[:10]),
            *(f"page: {message}" for message in page_errors[:10]),
        ]
        raise UnifiedGuestVerificationError(
            "Browser errors detected: "
            f"console={len(console_errors)}, page={len(page_errors)}; "
            + " | ".join(details)
        )


def main() -> int:
    admin_url, guest_url, database_path, evidence_dir, admin_support_dir = isolated_inputs()
    before_fingerprint, before_counts = logical_database_fingerprint(database_path)
    admin_ready = _assert_ready(admin_url, expected_guest_sessions=0)
    guest_ready = _assert_ready(guest_url, expected_guest_sessions=0)
    console_errors: list[str] = []
    page_errors: list[str] = []
    parity: list[dict[str, object]] = []
    workflow_evidence: dict[str, object] = {}
    summary_evidence: dict[str, object] = {}
    snapshot_evidence: dict[str, object] = {}
    handover_evidence: dict[str, object] = {}
    duplicate_evidence: dict[str, object] = {}
    support_evidence: dict[str, object] = {}

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

        def register_browser_page(page: Page) -> None:
            page.on(
                "console",
                lambda message: console_errors.append(message.text)
                if message.type == "error"
                else None,
            )
            page.on("pageerror", lambda error: page_errors.append(str(error)))

        for page in (admin_page, guest_page):
            register_browser_page(page)

        parity = _assert_route_parity(admin_page, guest_page, admin_url, guest_url)
        _assert_guest_restrictions(guest_page, guest_url)
        support_evidence = _exercise_support_flows(
            admin_page,
            guest_page,
            admin_url,
            guest_url,
            admin_support_dir,
        )
        workflow_evidence = _exercise_weekly_workflow(guest_page, guest_url)
        summary_evidence = _exercise_summary_downloads(guest_page, guest_url)
        _open_route(guest_page, guest_url, "/")
        snapshot_evidence = _reload_and_verify_signed_snapshot(guest_page)
        handover_evidence = _exercise_handover_reset_restore(guest_page, guest_url)
        _wait_for_guest_sessions(guest_url, 1)

        _open_route(guest_page, guest_url, "/")
        guest_page.screenshot(path=str(evidence_dir / "unified-guest-desktop-light.png"), full_page=True)
        if guest_page.locator("body.body--dark").count() != 1:
            guest_page.get_by_test_id("theme-control").click()
        guest_page.locator("body.body--dark").wait_for(state="attached", timeout=10_000)
        if admin_page.locator("body.body--dark").count():
            raise UnifiedGuestVerificationError("Guest appearance leaked into the Admin browser context.")
        guest_page.screenshot(path=str(evidence_dir / "unified-guest-desktop-dark.png"), full_page=True)

        with guest_page.expect_navigation(wait_until="domcontentloaded", timeout=15_000):
            guest_page.get_by_test_id("language-control").click()
        _open_route(guest_page, guest_url, "/")
        guest_page.locator(
            "[data-testid='dashboard-history'] .sy-dashboard-history-item"
        ).first.wait_for(state="visible", timeout=20_000)
        guest_page.locator('[role="heading"][aria-level="1"]').filter(has_text="Dashboard").wait_for(
            state="visible", timeout=10_000
        )
        guest_page.wait_for_function("document.documentElement.lang === 'en'", timeout=15_000)
        if _history_count(guest_page) != 1:
            raise UnifiedGuestVerificationError("Guest locale switching lost the source workspace.")
        if admin_page.evaluate("document.documentElement.lang") != "zh-Hant-HK":
            raise UnifiedGuestVerificationError("Guest locale leaked into the Admin browser context.")

        duplicate_guest_page, duplicate_evidence = _exercise_true_duplicate_and_tamper(
            guest_page,
            guest_url,
            register_page=register_browser_page,
        )

        # Keep the source and true duplicate stable while proving their copied
        # sessionStorage is isolated. Mobile evidence is composed afterwards,
        # then the same authenticated-session revocation clears all three
        # workspaces immediately. Closing the mobile context first would enter
        # the deliberate 12-second disconnect grace period and race a forced
        # source navigation against safe workspace recovery.
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

        _exercise_broadcast_cleanup(guest_page, duplicate_guest_page)
        mobile_context.close()
        guest_context.close()
        _wait_for_guest_sessions(guest_url, 0)
        admin_context.close()
        browser.close()

    after_fingerprint, after_counts = logical_database_fingerprint(database_path)
    if after_fingerprint != before_fingerprint or after_counts != before_counts:
        raise UnifiedGuestVerificationError("Guest browsing changed the disposable official SQLite content.")
    day_closure_evidence = workflow_evidence.get("dayClosure")
    if isinstance(day_closure_evidence, dict):
        day_closure_evidence["officialSqliteUnchanged"] = True
    _assert_clean_browser(console_errors, page_errors)

    report = {
        "schemaVersion": 2,
        "status": "pass",
        "verifiedAt": datetime.now(timezone.utc).isoformat(),
        "routes": parity,
        "routeCount": len(parity),
        "editorialParityRouteCount": len(EDITORIAL_PARITY_ROUTES),
        "databaseFingerprintUnchanged": True,
        "databaseTableCount": len(before_counts),
        "fictionalFixtureDirectory": True,
        "weeklyWorkflow": workflow_evidence,
        "fairnessAndReports": summary_evidence,
        "sameTabSnapshotRefresh": snapshot_evidence,
        "handoverResetRestore": handover_evidence,
        "supportReporting": support_evidence,
        "duplicateTab": duplicate_evidence,
        "crossTabIsolation": bool(duplicate_evidence.get("workspaceIsolated")),
        "tamperedSnapshotFallback": bool(duplicate_evidence.get("safeFixtureRetained")),
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
