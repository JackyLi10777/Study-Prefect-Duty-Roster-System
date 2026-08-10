"""Verify the live public viewer with an isolated fictional roster only."""

from __future__ import annotations

from datetime import date, timedelta
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import Any, Final
from urllib.parse import urlparse

from playwright.sync_api import Browser, Error, Page, Playwright, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui_app.config import PROJECT_ROOT  # noqa: E402
from nicegui_app.config import PREFECT_SEED_PATH  # noqa: E402
from nicegui_app.services.public_roster_share import PublicRosterShareService, PublicRosterShareSettings
from nicegui_app.services.roster_workflow import RosterWorkflow


EVIDENCE_DIR = PROJECT_ROOT / "test-results" / "public-roster-viewer"
GATEWAY_EVIDENCE_DIR = PROJECT_ROOT / "test-results" / "unified-access-gateway"
EXPLICIT_THEME_STATES: Final = ("light", "dark")
PERFORMANCE_EVIDENCE_PATH = GATEWAY_EVIDENCE_DIR / "public-mobile-performance.json"
PERFORMANCE_EVIDENCE: list[dict[str, Any]] = []
PERFORMANCE_OBSERVER_SCRIPT = r"""
(() => {
  const evidence = {largestContentfulPaint: 0, cumulativeLayoutShift: 0, longestTask: 0, longTaskCount: 0};
  window.__syPublicPerformanceEvidence = evidence;
  const observe = (type, callback) => {
    try {
      const observer = new PerformanceObserver(list => callback(list.getEntries()));
      observer.observe({type, buffered: true});
    } catch (_) {}
  };
  observe('largest-contentful-paint', entries => entries.forEach(entry => {
    evidence.largestContentfulPaint = Math.max(evidence.largestContentfulPaint, entry.startTime || 0);
  }));
  observe('layout-shift', entries => entries.forEach(entry => {
    if (!entry.hadRecentInput) evidence.cumulativeLayoutShift += entry.value || 0;
  }));
  observe('longtask', entries => entries.forEach(entry => {
    evidence.longTaskCount += 1;
    evidence.longestTask = Math.max(evidence.longestTask, entry.duration || 0);
  }));
})();
"""


def _launch_real_chrome(playwright: Playwright) -> Browser:
    channel = os.getenv("SING_YIN_PLAYWRIGHT_CHANNEL", "chrome").strip() or "chrome"
    try:
        return playwright.chromium.launch(headless=True, channel=channel)
    except Error as exc:
        if os.getenv("SING_YIN_PLAYWRIGHT_ALLOW_BUNDLED_CHROMIUM") == "1":
            return playwright.chromium.launch(headless=True)
        raise RuntimeError(
            f"Public mobile verification requires the Playwright {channel!r} browser channel; "
            "bundled Chromium is allowed only when isolated CI explicitly sets "
            "SING_YIN_PLAYWRIGHT_ALLOW_BUNDLED_CHROMIUM=1."
        ) from exc


def _new_mobile_context(
    browser: Browser,
    *,
    width: int,
    height: int,
    color_scheme: str = "light",
    reduced_motion: str = "no-preference",
    forced_colors: str = "none",
    accept_downloads: bool = False,
):  # type: ignore[no-untyped-def]
    context = browser.new_context(
        viewport={"width": width, "height": height},
        color_scheme=color_scheme,  # type: ignore[arg-type]
        reduced_motion=reduced_motion,  # type: ignore[arg-type]
        forced_colors=forced_colors,  # type: ignore[arg-type]
        is_mobile=True,
        has_touch=True,
        device_scale_factor=2,
        accept_downloads=accept_downloads,
    )
    context.add_init_script(PERFORMANCE_OBSERVER_SCRIPT)
    return context


def _collect_performance_evidence(page: Page, *, label: str) -> None:
    page.wait_for_timeout(120)
    evidence = page.evaluate(
        """() => {
          const navigation = performance.getEntriesByType('navigation')[0];
          const resources = performance.getEntriesByType('resource');
          const paints = Object.fromEntries(performance.getEntriesByType('paint').map(e => [e.name, e.startTime]));
          const observed = window.__syPublicPerformanceEvidence || {};
          return {
            ttfb: navigation ? navigation.responseStart - navigation.requestStart : null,
            firstContentfulPaint: paints['first-contentful-paint'] || null,
            largestContentfulPaint: observed.largestContentfulPaint || null,
            cumulativeLayoutShift: observed.cumulativeLayoutShift || 0,
            longestTask: observed.longestTask || 0,
            longTaskCount: observed.longTaskCount || 0,
            resourceCount: resources.length,
            resourceBytes: resources.reduce((total, e) => total + (e.transferSize || e.encodedBodySize || 0), 0),
          };
        }"""
    )
    evidence["label"] = label
    PERFORMANCE_EVIDENCE.append(evidence)
    if evidence["cumulativeLayoutShift"] > 0.15:
        raise RuntimeError(f"{label} exceeds the mobile CLS contract: {evidence}")
    if evidence["longestTask"] > 1_000:
        raise RuntimeError(f"{label} contains a blocking task longer than one second: {evidence}")
    if evidence["resourceBytes"] > 25 * 1024 * 1024:
        raise RuntimeError(f"{label} transferred more than the 25 MiB ceiling: {evidence}")


def _write_performance_evidence() -> None:
    if not PERFORMANCE_EVIDENCE:
        return
    PERFORMANCE_EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PERFORMANCE_EVIDENCE_PATH.write_text(
        json.dumps(PERFORMANCE_EVIDENCE, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _attach_error_collectors(
    page: Page,
    *,
    label: str,
    console_errors: list[str],
    page_errors: list[str],
) -> None:
    page.on(
        "console",
        lambda message: console_errors.append(f"{label}: {message.text}")
        if message.type == "error"
        else None,
    )
    page.on("pageerror", lambda error: page_errors.append(f"{label}: {error}"))


def _current_theme(page: Page) -> str:
    return str(page.get_by_test_id("public-theme-control").get_attribute("data-resolved-theme"))


def _set_theme_reliably(page: Page, expected: str) -> None:
    """Use the public binary button without relying on internal JS APIs."""

    if expected not in EXPLICIT_THEME_STATES:
        raise ValueError(f"Unsupported theme state: {expected}")
    control = page.get_by_test_id("public-theme-control")
    if _current_theme(page) != expected:
        control.click()
    page.wait_for_function(
        "value => document.querySelector('[data-testid=public-theme-control]')?.dataset.resolvedTheme === value",
        arg=expected,
    )
    page.wait_for_timeout(250)


def _assert_page_identity(page: Page, *, label: str) -> None:
    if "Study Prefect Duty Roster" not in page.title():
        raise RuntimeError(f"{label} opened an unexpected page title: {page.title()!r}")
    for selector in ("nextjs-portal", "vite-error-overlay", "#webpack-dev-server-client-overlay"):
        overlay = page.locator(selector)
        if overlay.count() and overlay.first.is_visible():
            raise RuntimeError(f"{label} displays a framework error overlay: {selector}")


def _assert_document_fits_viewport(page: Page, *, label: str) -> None:
    metrics = page.evaluate(
        """() => ({
            viewport: window.innerWidth,
            document: document.documentElement.scrollWidth,
            body: document.body.scrollWidth,
            storyScrollLeft: document.querySelector('.portal-story')?.scrollLeft || 0,
        })"""
    )
    if (
        metrics["document"] > metrics["viewport"] + 1
        or metrics["body"] > metrics["viewport"] + 1
    ):
        raise RuntimeError(f"{label} has horizontal document overflow: {metrics}")
    if metrics["storyScrollLeft"] != 0:
        raise RuntimeError(f"{label} has a horizontally displaced landing story: {metrics}")


def _assert_mobile_touch_and_reflow(page: Page, *, label: str) -> None:
    failures = page.evaluate(
        r"""() => {
          const visible = element => {
            const style = getComputedStyle(element);
            const box = element.getBoundingClientRect();
            const clippedAway = style.clip === 'rect(0px, 0px, 0px, 0px)'
              || style.clipPath === 'inset(50%)';
            const intersectsHorizontally = box.right > 0 && box.left < window.innerWidth;
            return style.display !== 'none'
              && style.visibility !== 'hidden'
              && Number.parseFloat(style.opacity || '1') > 0
              && !clippedAway
              && box.width > 0
              && box.height > 0
              && intersectsHorizontally
              && box.bottom > 0;
          };
          const controls = [...document.querySelectorAll('button, a[href], summary, input, select, textarea')]
            .filter(visible).filter(element => !element.matches('a[href]') || getComputedStyle(element).display !== 'inline')
            .map(element => {
              const box = element.getBoundingClientRect();
              return {kind: 'target', text: (element.textContent || element.getAttribute('aria-label') || '').trim().slice(0, 60), width: box.width, height: box.height};
            }).filter(item => item.width < 44 || item.height < 44);
          const text = [...document.querySelectorAll('button, a[href], h1, h2, h3, label, p')]
            .filter(visible).flatMap(element => {
              const value = (element.textContent || '').replace(/\s+/g, ' ').trim();
              if (!value) return [];
              const box = element.getBoundingClientRect();
              const style = getComputedStyle(element);
              const size = Number.parseFloat(style.fontSize) || 16;
              const height = Number.parseFloat(style.lineHeight) || size * 1.25;
              const lines = Math.max(1, Math.round(box.height / height));
              const clipsOverflow = value => ['hidden', 'clip', 'scroll', 'auto'].includes(value);
              const clipped = (
                (element.scrollWidth > element.clientWidth + 2 && clipsOverflow(style.overflowX))
                || (element.scrollHeight > element.clientHeight + 2 && clipsOverflow(style.overflowY))
              );
              const glyphColumn = value.length >= 4 && box.width < size * 2.2 && lines >= 4;
              return clipped || glyphColumn ? [{kind: clipped ? 'clipped' : 'glyph-column', text: value.slice(0, 60), width: box.width, height: box.height, lines}] : [];
            });
          return [...controls, ...text].slice(0, 12);
        }"""
    )
    if failures:
        raise RuntimeError(f"{label} has undersized controls, clipped text, or glyph columns: {failures}")


def _assert_support_keyboard_flow(page: Page, *, label: str) -> None:
    """Required fields must remain keyboard reachable and visibly scrolled into view."""

    expected_order = ("supportExpected", "supportActual", "supportSteps")
    page.locator("#supportExpected").focus()
    for index, expected in enumerate(expected_order):
        active = page.evaluate("document.activeElement?.id")
        if active != expected:
            raise RuntimeError(f"{label} keyboard order expected {expected!r}, found {active!r}.")
        field = page.locator(f"#{expected}")
        field.scroll_into_view_if_needed()
        box = field.bounding_box()
        viewport_height = int((page.viewport_size or {}).get("height", 0))
        if box is None or box["y"] < 0 or box["y"] + min(box["height"], 44) > viewport_height:
            raise RuntimeError(f"{label} keyboard field is obscured outside the viewport: {expected} {box}")
        if index < len(expected_order) - 1:
            page.keyboard.press("Tab")


def _assert_viewer_horizontal_context(page: Page, *, label: str) -> None:
    """The phone viewer must support touch and keyboard access to every weekday."""

    table_scroll = page.locator(".table-scroll")
    table_scroll.wait_for(state="visible")
    metrics = table_scroll.evaluate(
        """element => ({
          clientWidth: element.clientWidth,
          scrollWidth: element.scrollWidth,
          tabIndex: element.tabIndex,
          before: element.scrollLeft,
        })"""
    )
    if metrics["scrollWidth"] <= metrics["clientWidth"] or metrics["tabIndex"] != 0:
        raise RuntimeError(f"{label} does not expose a focusable horizontal roster viewport: {metrics}")
    table_scroll.focus()
    focus_state = table_scroll.evaluate(
        """element => ({
          focusVisible: element.matches(':focus-visible'),
          outlineWidth: Number.parseFloat(getComputedStyle(element).outlineWidth) || 0,
          boxShadow: getComputedStyle(element).boxShadow,
        })"""
    )
    if not focus_state["focusVisible"] or (
        focus_state["outlineWidth"] < 1 and focus_state["boxShadow"] in {"", "none"}
    ):
        raise RuntimeError(f"{label} horizontal viewer lacks a visible keyboard focus state: {focus_state}")
    for _ in range(6):
        page.keyboard.press("ArrowRight")
    page.wait_for_timeout(80)
    after_keyboard = table_scroll.evaluate("element => element.scrollLeft")
    if after_keyboard <= 0:
        raise RuntimeError(f"{label} cannot reach later weekdays with the keyboard: {metrics}")
    table_scroll.evaluate("element => { element.scrollLeft = element.scrollWidth; }")
    sticky_overlaps = table_scroll.evaluate(
        """root => {
          const sticky = [...root.querySelectorAll('*')].filter(element => getComputedStyle(element).position === 'sticky');
          return sticky.flatMap((first, i) => sticky.slice(i + 1).flatMap(second => {
            const a = first.getBoundingClientRect(); const b = second.getBoundingClientRect();
            const w = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
            const h = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
            return w * h > 4 ? [{first: first.textContent?.trim().slice(0, 30), second: second.textContent?.trim().slice(0, 30), area: w * h}] : [];
          })).slice(0, 6);
        }"""
    )
    if sticky_overlaps:
        raise RuntimeError(f"{label} sticky roster context overlaps while scrolling: {sticky_overlaps}")


def _assert_200_percent_public_reflow(page: Page, *, url: str, label: str) -> None:
    stylesheet_was_rewritten = False

    def serve_200_percent_styles(route: Any) -> None:
        nonlocal stylesheet_was_rewritten
        response = route.fetch()
        if not response.ok:
            raise RuntimeError(
                f"{label} could not load the same-origin viewer stylesheet: HTTP {response.status}."
            )
        css = response.text()
        route.fulfill(
            response=response,
            body=f"{css}\nhtml {{ font-size: 200% !important; }}\n",
        )
        stylesheet_was_rewritten = True

    stylesheet = "**/viewer.css"
    page.route(stylesheet, serve_200_percent_styles)
    try:
        response = page.goto(url, wait_until="networkidle")
        if response is None or response.status != 200:
            raise RuntimeError(f"{label} returned an unexpected response: {response}")
        if not stylesheet_was_rewritten:
            raise RuntimeError(
                f"{label} did not request the same-origin viewer stylesheet; "
                "the 200% text contract was not applied."
            )
        page.evaluate(
            "new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )
        _assert_document_fits_viewport(page, label=label)
        _assert_mobile_touch_and_reflow(page, label=label)
    finally:
        page.unroute(stylesheet, serve_200_percent_styles)


def _assert_guest_landing(page: Page, *, label: str) -> None:
    page.locator("#guestState").wait_for(state="visible")
    _assert_page_identity(page, label=label)
    if page.locator("#rosterState").is_visible():
        raise RuntimeError(f"{label} exposed the roster state without a share link.")

    verse_refresh = page.locator("#refreshLandingVerse")
    if verse_refresh.count() != 1 or not verse_refresh.is_visible():
        raise RuntimeError(f"{label} does not expose the manual verse refresh action.")
    verse_refresh_box = verse_refresh.bounding_box()
    if (
        verse_refresh_box is None
        or verse_refresh_box["width"] < 44
        or verse_refresh_box["height"] < 44
    ):
        raise RuntimeError(
            f"{label} verse refresh is smaller than the 44 CSS pixel touch target: "
            f"{verse_refresh_box}"
        )

    login_link = page.locator('a[data-entry-role="admin"]:visible')
    if login_link.count() != 1 or not login_link.is_visible():
        raise RuntimeError(f"{label} does not expose exactly one visible administrator login.")
    login_box = login_link.bounding_box()
    if login_box is None or login_box["height"] < 48:
        raise RuntimeError(f"{label} administrator CTA is shorter than 48 CSS pixels: {login_box}")

    guest_link = page.locator('a[data-entry-role="guest"]:visible')
    if guest_link.count() != 1 or not guest_link.is_visible():
        raise RuntimeError(f"{label} does not expose exactly one visible guest-tour entrance.")
    guest_box = guest_link.bounding_box()
    if guest_box is None or guest_box["height"] < 48:
        raise RuntimeError(f"{label} guest-tour CTA is shorter than 48 CSS pixels: {guest_box}")

    share_button = page.locator("#shareSite")
    if share_button.count() != 1 or not share_button.is_visible():
        raise RuntimeError(f"{label} does not expose the website-entrance share action.")
    share_box = share_button.bounding_box()
    if share_box is None or share_box["height"] < 44:
        raise RuntimeError(f"{label} website-share action is shorter than 44 CSS pixels: {share_box}")
    share_explanation = page.locator("#shareSiteStatus").inner_text()
    if "不包含任何值班表" not in share_explanation or "never a roster" not in share_explanation:
        raise RuntimeError(f"{label} does not distinguish website sharing from roster sharing.")

    guest_help = page.locator(".guest-help").inner_text()
    if "read-only" not in guest_help.lower() or "只供查看" not in page.locator("#guestState").inner_text():
        raise RuntimeError(f"{label} does not explain that guest sharing is read-only.")
    translation = page.locator(".translation-label").inner_text()
    if "2010" not in translation or "NKJV" not in translation:
        raise RuntimeError(f"{label} does not identify the approved Chinese and English Bible versions.")

    welcome_player = page.locator("#welcomeAudioPlayer")
    if welcome_player.count() != 1 or not welcome_player.is_visible():
        raise RuntimeError(f"{label} does not expose the welcome-music control.")
    if page.locator("#welcomeAudioVolume").input_value() != "50":
        raise RuntimeError(f"{label} does not start from the documented 50% welcome volume.")
    for selector in ("#welcomeAudioToggle", "#welcomeAudioNext"):
        control_box = page.locator(selector).bounding_box()
        if control_box is None or control_box["width"] < 43.5 or control_box["height"] < 43.5:
            raise RuntimeError(f"{label} welcome-music control is smaller than the 44 CSS pixel target: {control_box}")
    _assert_document_fits_viewport(page, label=label)
    if int((page.viewport_size or {}).get("width", 0)) <= 900:
        _assert_mobile_touch_and_reflow(page, label=label)
    _collect_performance_evidence(page, label=label)


def _fill_support_report(page: Page) -> None:
    page.locator("#supportExpected").fill("The shared fictional roster should remain readable.")
    page.locator("#supportActual").fill("The fictional roster displayed an unexpected empty state.")
    page.locator("#supportSteps").fill("Open the shared link.\nReview the fictional roster.")


def _assert_public_support(
    page: Page,
    *,
    base_url: str,
    source: str,
    verify_download: bool,
) -> dict[str, object]:
    """Exercise persisted public/viewer support and its shared theme preference."""

    if source not in {"public", "viewer"}:
        raise ValueError(f"Unsupported support source: {source}")
    page.add_init_script(
        """(() => localStorage.setItem('sing-yin-roster-viewer-theme-v1', 'dark'))();"""
    )
    response = page.goto(f"{base_url.rstrip('/')}/support#{source}", wait_until="networkidle")
    if response is None or response.status != 200:
        raise RuntimeError(f"{source} support route did not return HTTP 200.")
    if response.headers.get("cache-control") != "no-store":
        raise RuntimeError(f"{source} support route is not protected by Cache-Control: no-store.")
    form = page.locator("#publicSupportForm")
    form.wait_for(state="visible")
    if int((page.viewport_size or {}).get("width", 0)) <= 900:
        _assert_mobile_touch_and_reflow(page, label=f"{source} support")
        _assert_support_keyboard_flow(page, label=f"{source} support")
    theme_state = page.evaluate(
        """() => ({
          preference: document.documentElement.dataset.themePreference,
          resolved: document.documentElement.dataset.theme,
          stored: localStorage.getItem('sing-yin-roster-viewer-theme-v1'),
        })"""
    )
    if theme_state != {"preference": "dark", "resolved": "dark", "stored": "dark"}:
        raise RuntimeError(f"{source} support did not inherit the entrance theme: {theme_state}")
    theme_button = page.locator("#supportTheme")
    for expected_preference in ("light", "dark"):
        theme_button.click()
        page.wait_for_function(
            """expected => {
              const root = document.documentElement;
              return root.dataset.themePreference === expected
                && root.dataset.theme === expected;
            }""",
            arg=expected_preference,
        )
    if page.evaluate("() => localStorage.getItem('sing-yin-roster-viewer-theme-v1')") != "dark":
        raise RuntimeError(f"{source} support theme changes were not stored under the shared key.")
    if page.locator(".support-details").get_attribute("open") is not None:
        raise RuntimeError(f"{source} support optional details were expanded by default.")
    page.locator("#supportBuild").click()
    if not page.locator("#supportResult").is_hidden():
        raise RuntimeError(f"{source} support accepted missing required fields.")

    _fill_support_report(page)
    page.locator("#supportBuild").click()
    result = page.locator("#supportResult")
    result.wait_for(state="visible")
    incident_id = page.locator("#supportIncidentId").inner_text().strip()
    if not re.fullmatch(r"INC-\d{8}-[A-F0-9]{8}", incident_id):
        raise RuntimeError(f"{source} support was not saved to the local incident inbox: {incident_id!r}")
    expected_source = "public_viewer" if source == "viewer" else "public_entrance"
    if verify_download:
        with page.expect_download() as download_info:
            page.locator("#supportDownload").click()
        download = download_info.value
        payload = json.loads(Path(download.path()).read_text(encoding="utf-8"))
        if payload.get("source") != expected_source or payload.get("incident_id") != incident_id:
            raise RuntimeError(f"{source} support download does not identify its browser context.")

    storage = page.evaluate(
        """async () => ({
          localKeys: Object.keys(localStorage),
          session: sessionStorage.length,
          indexed: typeof indexedDB.databases === 'function' ? (await indexedDB.databases()).length : 0,
          caches: 'caches' in window ? (await caches.keys()).length : 0,
        })"""
    )
    if storage["localKeys"] != ["sing-yin-roster-viewer-theme-v1"] or any(
        storage[key] for key in ("session", "indexed", "caches")
    ):
        raise RuntimeError(f"{source} support created persistent browser storage: {storage}")

    _collect_performance_evidence(page, label=f"{source} support")

    page.reload(wait_until="networkidle")
    if page.locator("#supportExpected").input_value() or not page.locator("#supportResult").is_hidden():
        raise RuntimeError(f"{source} support state survived reload.")
    if page.evaluate("() => document.documentElement.dataset.theme") != "dark":
        raise RuntimeError(f"{source} support theme did not survive reload.")
    return {
        "source": expected_source,
        "incidentReference": incident_id,
        "serverPersisted": True,
        "themeSynchronized": True,
        "downloadVerified": verify_download,
        "clearedOnReload": True,
    }


def _assert_public_support_network_fallback(page: Page, *, base_url: str) -> dict[str, object]:
    """Prove a failed submission preserves input and creates an explicit FB reference."""

    page.route("**/api/support/incidents", lambda route: route.abort("connectionfailed"))
    response = page.goto(f"{base_url.rstrip('/')}/support#public", wait_until="networkidle")
    if response is None or response.status != 200:
        raise RuntimeError("Public support fallback route did not return HTTP 200.")
    _fill_support_report(page)
    expected = page.locator("#supportExpected").input_value()
    page.locator("#supportBuild").click()
    page.locator("#supportResult").wait_for(state="visible")
    incident_id = page.locator("#supportIncidentId").inner_text().strip()
    if not re.fullmatch(r"FB-[A-F0-9]{16}", incident_id):
        raise RuntimeError(f"Network failure did not create an FB reference: {incident_id!r}")
    if page.locator("#supportExpected").input_value() != expected:
        raise RuntimeError("Network failure discarded the reporter's input.")
    if "Not stored on the server" not in page.locator("#supportStatus").inner_text():
        raise RuntimeError("Network failure did not explain the browser-only fallback state.")
    page.unroute("**/api/support/incidents")
    return {
        "source": "public_entrance",
        "incidentReference": incident_id,
        "serverPersisted": False,
        "inputPreserved": True,
    }


def _assert_only_expected_network_fallback_errors(
    *,
    console_errors: list[str],
    page_errors: list[str],
    failed_request_urls: list[str],
) -> int:
    """Keep the deliberately aborted request separate from real browser failures."""

    expected_suffix = "Failed to load resource: net::ERR_CONNECTION_FAILED"
    expected_console_errors = [
        error for error in console_errors if error.endswith(expected_suffix)
    ]
    unexpected_console_errors = [
        error for error in console_errors if not error.endswith(expected_suffix)
    ]
    incident_failures = [
        url for url in failed_request_urls if urlparse(url).path == "/api/support/incidents"
    ]
    unexpected_request_failures = [
        url for url in failed_request_urls if urlparse(url).path != "/api/support/incidents"
    ]
    count_mismatch = len(expected_console_errors) != len(incident_failures)
    if (
        unexpected_console_errors
        or unexpected_request_failures
        or page_errors
        or count_mismatch
        or not incident_failures
    ):
        mismatch = (
            [
                "Expected console/request failure counts differ: "
                f"{len(expected_console_errors)} != {len(incident_failures)}"
            ]
            if count_mismatch
            else []
        )
        missing = ["No failed /api/support/incidents request was recorded."] if not incident_failures else []
        details = "\n".join(
            [
                *unexpected_console_errors,
                *unexpected_request_failures,
                *page_errors,
                *mismatch,
                *missing,
            ]
        )
        raise RuntimeError(
            "Public support network-fallback emitted unexpected browser errors:\n" + details
        )
    return len(expected_console_errors)


def _assert_welcome_audio_blocked_recovery(page: Page, *, base_url: str) -> None:
    """Prove an honest fresh-profile NotAllowedError and one-action recovery."""

    page.goto(base_url, wait_until="networkidle")
    page.wait_for_function(
        "() => document.querySelector('#welcomeAudioPlayer')?.dataset.autoplayState === 'blocked'"
    )
    recovery = page.locator("#welcomeAudioRecovery")
    if not recovery.is_visible():
        raise RuntimeError("Blocked welcome audio does not expose the recovery choice.")
    if "direct action" not in page.locator("#welcomeAudioStatus").inner_text().lower():
        raise RuntimeError("Blocked welcome audio does not explain the browser policy.")

    page.evaluate(
        """() => {
            HTMLMediaElement.prototype.play = function () { return Promise.resolve(); };
        }"""
    )
    page.locator("#welcomeAudioEnter").click()
    page.wait_for_function(
        "() => document.querySelector('#welcomeAudioPlayer')?.dataset.autoplayState === 'playing'"
    )
    if recovery.is_visible():
        raise RuntimeError("Successful explicit welcome-audio recovery did not close the choice.")


def _assert_welcome_audio_quiet_navigation(page: Page, *, base_url: str) -> None:
    """Prove quiet continuation preserves the intercepted destination."""

    page.goto(base_url, wait_until="networkidle")
    page.wait_for_function(
        "() => document.querySelector('#welcomeAudioPlayer')?.dataset.autoplayState === 'blocked'"
    )
    recovery = page.locator("#welcomeAudioRecovery")
    recovery.wait_for(state="visible")
    page.locator("#welcomeAudioQuiet").click()
    try:
        recovery.wait_for(state="hidden")
    except Error as exc:
        raise RuntimeError(
            "Quiet welcome-audio choice did not close the recovery choice."
        ) from exc
    page.route(
        "**/guest",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html; charset=utf-8",
            body="<!doctype html><title>Guest destination</title><main id='guestDestination'>guest</main>",
        ),
    )
    page.locator('a[data-entry-role="guest"]:visible').click()
    page.wait_for_url("**/guest", wait_until="domcontentloaded")
    if (
        page.url.rstrip("/").split("?")[0] != f"{base_url.rstrip('/')}/guest"
        or page.locator("#guestDestination").count() != 1
    ):
        raise RuntimeError(f"Quiet welcome-audio continuation reached an unexpected URL: {page.url}")
    page.unroute("**/guest")


def _assert_welcome_audio_allowed(page: Page, *, base_url: str) -> None:
    """Prove the automatic path reports playing only after play() resolves."""

    page.goto(base_url, wait_until="networkidle")
    page.wait_for_function(
        "() => document.querySelector('#welcomeAudioPlayer')?.dataset.autoplayState === 'playing'"
    )
    if page.locator("#welcomeAudioRecovery").is_visible():
        raise RuntimeError("Allowed welcome audio incorrectly exposes blocked recovery.")


def _assert_mobile_entry_actions_in_first_viewport(page: Page, *, label: str) -> None:
    viewport = page.viewport_size or {}
    viewport_height = int(viewport.get("height", 0))
    if viewport_height <= 0:
        raise RuntimeError(f"{label} does not expose a measurable viewport.")
    for role in ("admin", "guest"):
        action = page.locator(f'a.mobile-entry-action[data-entry-role="{role}"]:visible')
        if action.count() != 1:
            raise RuntimeError(f"{label} does not expose one mobile {role} entry action.")
        box = action.bounding_box()
        if box is None or box["height"] < 48:
            raise RuntimeError(f"{label} mobile {role} action is not a 48px touch target: {box}")
        if box["y"] < 0 or box["y"] + box["height"] > viewport_height:
            raise RuntimeError(
                f"{label} mobile {role} action falls outside the first viewport: "
                f"{box}, viewport height={viewport_height}"
            )


def _assert_theme_selection(page: Page) -> None:
    page.evaluate("key => localStorage.removeItem(key)", "sing-yin-roster-viewer-theme-v1")
    page.reload(wait_until="networkidle")
    initial = _current_theme(page)
    if initial not in EXPLICIT_THEME_STATES:
        raise RuntimeError(f"Appearance did not resolve the browser scheme: {initial!r}")
    expected_sequence = ("light", "dark") if initial == "dark" else ("dark", "light")
    for expected in expected_sequence:
        _set_theme_reliably(page, expected)
        if _current_theme(page) != expected:
            raise RuntimeError(f"Appearance control failed to enter {expected!r} mode.")
        mark_opacity = page.evaluate(
            """theme => ({
                light: getComputedStyle(document.querySelector('.brand-mark-image--light')).opacity,
                dark: getComputedStyle(document.querySelector('.brand-mark-image--dark')).opacity,
                expected: theme,
            })""",
            expected,
        )
        expected_opacity = (
            {"light": "1", "dark": "0"}
            if expected == "light"
            else {"light": "0", "dark": "1"}
        )
        if any(mark_opacity[key] != value for key, value in expected_opacity.items()):
            raise RuntimeError(
                f"Entrance brand mark did not follow {expected!r} mode: {mark_opacity}"
            )
        expected_track = {"light": "Morning Has Broken", "dark": "Ubi caritas"}.get(expected)
        if expected_track:
            page.wait_for_function(
                "title => document.querySelector('#welcomeTrackTitle')?.textContent === title",
                arg=expected_track,
            )


def _assert_manual_verse_refresh(page: Page) -> None:
    devotional = page.locator(".devotional-prompt")
    before_id = devotional.get_attribute("data-verse-id")
    before_text = page.locator("#landingVerseZh").inner_text()
    page.locator("#refreshLandingVerse").click()
    page.wait_for_function(
        "before => document.querySelector('.devotional-prompt')?.dataset.verseId !== before",
        arg=before_id,
    )
    after_id = devotional.get_attribute("data-verse-id")
    after_text = page.locator("#landingVerseZh").inner_text()
    if not before_id or not after_id or before_id == after_id or before_text == after_text:
        raise RuntimeError("Manual verse refresh did not present a different canonical entry.")


def _assert_reduced_motion(page: Page) -> None:
    result = page.evaluate(
        """() => {
            const toMs = value => value.split(',').map(part => {
                const token = part.trim();
                const number = Number.parseFloat(token) || 0;
                return token.endsWith('ms') ? number : number * 1000;
            });
            const nodes = [...document.querySelectorAll(
                '.access-portal, .portal-story, .access-panel, .devotional-prompt, .admin-login, ' +
                '.guest-enter, .platform-hero, .hero-system, ' +
                '.platform-page .button, .platform-page .control-button, .capability-grid article, .trust-layout'
            )];
            const durations = nodes.flatMap(node => {
                const style = getComputedStyle(node);
                return [...toMs(style.animationDuration), ...toMs(style.transitionDuration)];
            });
            const iterations = nodes.flatMap(node =>
                getComputedStyle(node).animationIterationCount.split(',').map(value => value.trim())
            );
            return {
                mediaMatches: matchMedia('(prefers-reduced-motion: reduce)').matches,
                maxDurationMs: Math.max(0, ...durations),
                hasInfiniteAnimation: iterations.includes('infinite'),
            };
        }"""
    )
    if not result["mediaMatches"] or result["maxDurationMs"] > 1 or result["hasInfiniteAnimation"]:
        raise RuntimeError(f"Reduced-motion contract failed: {result}")


def _assert_read_only_roster(page: Page, *, expected_names: set[str], label: str) -> None:
    page.locator("#rosterState").wait_for(state="visible")
    _assert_page_identity(page, label=label)
    if page.locator("#guestState").is_visible():
        raise RuntimeError(f"{label} still displays the guest landing over a valid share.")
    rendered = page.locator("#rosterTable").inner_text()
    missing_names = sorted(name for name in expected_names if name not in rendered)
    if not expected_names or missing_names:
        raise RuntimeError(f"{label} did not render every fictional Chinese name: {missing_names}")
    if "READ ONLY" not in page.locator("#rosterState").inner_text().upper():
        raise RuntimeError(f"{label} does not visibly identify the roster as read-only.")
    editable_controls = page.locator(
        "#rosterState input, #rosterState textarea, #rosterState select, "
        "#rosterState button, #rosterState [contenteditable='true']"
    )
    if editable_controls.count() != 0:
        raise RuntimeError(f"{label} unexpectedly exposes {editable_controls.count()} editable controls.")
    viewport = page.viewport_size or {}
    if int(viewport.get("width", 0)) <= 900:
        scroll_hint = page.locator("#rosterScrollHint")
        if not scroll_hint.is_visible() or "SWIPE HORIZONTALLY" not in scroll_hint.inner_text().upper():
            raise RuntimeError(f"{label} does not explain how to reach every weekday on a phone.")
        if page.locator(".table-scroll").get_attribute("aria-describedby") != "rosterScrollHint":
            raise RuntimeError(f"{label} does not associate its mobile scroll instruction with the roster.")
        _assert_viewer_horizontal_context(page, label=label)
        _assert_mobile_touch_and_reflow(page, label=label)
    _assert_document_fits_viewport(page, label=label)
    _collect_performance_evidence(page, label=label)


def main() -> int:
    settings = PublicRosterShareSettings.from_environment()
    settings.require_configured()
    receipt = None
    workflow = None
    service = None
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    GATEWAY_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix="sing-yin-public-viewer-e2e-"))
    try:
        workflow = RosterWorkflow(
            database_path=temporary_root / "fictional.sqlite3",
            backup_dir=temporary_root / "backups",
            seed_path=PREFECT_SEED_PATH,
        )
        workflow.bootstrap()
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        draft = workflow.generate_and_save_draft(week_start)
        workflow.publish(draft.id, expected_week_version=draft.version)
        service = PublicRosterShareService(workflow, settings=settings)
        receipt = service.create_share(draft.id)
        expected_names = {
            str(item["prefectName"])
            for item in workflow.assignments(draft.id)
            if item["status"] in {"active", "replaced"}
        }

        console_errors: list[str] = []
        page_errors: list[str] = []
        support_evidence: list[dict[str, object]] = []
        with sync_playwright() as playwright:
            browser = _launch_real_chrome(playwright)

            support_context = _new_mobile_context(
                browser,
                width=390,
                height=844,
                color_scheme="light",
                accept_downloads=True,
            )
            support_websockets: list[str] = []
            for source, verify_download in (("public", True), ("viewer", False)):
                support_page = support_context.new_page()
                support_page.on("websocket", lambda socket: support_websockets.append(socket.url))
                _attach_error_collectors(
                    support_page,
                    label=f"{source}-support",
                    console_errors=console_errors,
                    page_errors=page_errors,
                )
                support_evidence.append(
                    _assert_public_support(
                        support_page,
                        base_url=settings.base_url,
                        source=source,
                        verify_download=verify_download,
                    )
                )
                if source == "public":
                    support_page.screenshot(
                        path=str(GATEWAY_EVIDENCE_DIR / "public-support-traceable-inbox.png"),
                        full_page=True,
                    )
                support_page.close()
            fallback_page = support_context.new_page()
            fallback_console_errors: list[str] = []
            fallback_page_errors: list[str] = []
            fallback_failed_request_urls: list[str] = []
            _attach_error_collectors(
                fallback_page,
                label="public-support-network-fallback",
                console_errors=fallback_console_errors,
                page_errors=fallback_page_errors,
            )
            fallback_page.on(
                "requestfailed",
                lambda request: fallback_failed_request_urls.append(request.url),
            )
            fallback_evidence = _assert_public_support_network_fallback(
                fallback_page,
                base_url=settings.base_url,
            )
            fallback_evidence["expectedNetworkConsoleErrorCount"] = (
                _assert_only_expected_network_fallback_errors(
                    console_errors=fallback_console_errors,
                    page_errors=fallback_page_errors,
                    failed_request_urls=fallback_failed_request_urls,
                )
            )
            support_evidence.append(fallback_evidence)
            fallback_page.close()
            if support_websockets:
                raise RuntimeError(f"Public support opened WebSockets: {support_websockets}")
            support_context.close()

            blocked_audio = browser.new_context(
                viewport={"width": 1280, "height": 900},
                color_scheme="light",
            )
            blocked_audio.add_init_script(
                """(() => {
                    HTMLMediaElement.prototype.play = function () {
                        return Promise.reject(new DOMException('fresh profile policy', 'NotAllowedError'));
                    };
                })();"""
            )
            blocked_page = blocked_audio.new_page()
            _attach_error_collectors(
                blocked_page,
                label="audio-blocked",
                console_errors=console_errors,
                page_errors=page_errors,
            )
            _assert_welcome_audio_blocked_recovery(blocked_page, base_url=settings.base_url)
            blocked_page.screenshot(
                path=str(GATEWAY_EVIDENCE_DIR / "welcome-audio-recovered.png"),
                full_page=True,
            )
            blocked_audio.close()

            quiet_audio = browser.new_context(
                viewport={"width": 1280, "height": 900},
                color_scheme="light",
            )
            quiet_audio.add_init_script(
                """(() => {
                    HTMLMediaElement.prototype.play = function () {
                        return Promise.reject(new DOMException('fresh profile policy', 'NotAllowedError'));
                    };
                })();"""
            )
            quiet_page = quiet_audio.new_page()
            _attach_error_collectors(
                quiet_page,
                label="audio-quiet-navigation",
                console_errors=console_errors,
                page_errors=page_errors,
            )
            _assert_welcome_audio_quiet_navigation(quiet_page, base_url=settings.base_url)
            quiet_audio.close()

            allowed_audio = browser.new_context(
                viewport={"width": 1280, "height": 900},
                color_scheme="dark",
            )
            allowed_audio.add_init_script(
                """(() => {
                    HTMLMediaElement.prototype.play = function () { return Promise.resolve(); };
                })();"""
            )
            allowed_page = allowed_audio.new_page()
            _attach_error_collectors(
                allowed_page,
                label="audio-allowed",
                console_errors=console_errors,
                page_errors=page_errors,
            )
            _assert_welcome_audio_allowed(allowed_page, base_url=settings.base_url)
            allowed_audio.close()

            desktop = browser.new_context(
                viewport={"width": 1440, "height": 1000},
                color_scheme="light",
            )
            desktop.add_init_script(PERFORMANCE_OBSERVER_SCRIPT)
            page = desktop.new_page()
            _attach_error_collectors(
                page,
                label="desktop",
                console_errors=console_errors,
                page_errors=page_errors,
            )
            page.goto(settings.base_url, wait_until="networkidle")
            _assert_guest_landing(page, label="desktop guest landing")
            _assert_manual_verse_refresh(page)
            _assert_theme_selection(page)

            _set_theme_reliably(page, "light")
            page.screenshot(path=str(GATEWAY_EVIDENCE_DIR / "desktop-light.png"), full_page=True)

            page.goto(settings.base_url, wait_until="networkidle")
            _assert_guest_landing(page, label="desktop dark guest landing")
            _set_theme_reliably(page, "dark")
            page.screenshot(path=str(GATEWAY_EVIDENCE_DIR / "desktop-dark.png"), full_page=True)

            page.goto(receipt.share_url, wait_until="networkidle")
            _assert_read_only_roster(page, expected_names=expected_names, label="desktop shared roster")
            _set_theme_reliably(page, "light")
            page.screenshot(path=str(EVIDENCE_DIR / "desktop-light.png"), full_page=True)
            _set_theme_reliably(page, "dark")
            page.screenshot(path=str(EVIDENCE_DIR / "desktop-dark.png"), full_page=True)
            desktop.close()

            mobile = _new_mobile_context(
                browser,
                width=390,
                height=844,
                color_scheme="light",
            )
            mobile_page = mobile.new_page()
            _attach_error_collectors(
                mobile_page,
                label="mobile-390",
                console_errors=console_errors,
                page_errors=page_errors,
            )
            mobile_page.goto(settings.base_url, wait_until="networkidle")
            _assert_guest_landing(mobile_page, label="390px guest landing")
            _assert_mobile_entry_actions_in_first_viewport(
                mobile_page,
                label="390px guest landing",
            )
            _set_theme_reliably(mobile_page, "light")
            mobile_page.screenshot(path=str(GATEWAY_EVIDENCE_DIR / "mobile-light.png"), full_page=True)

            mobile_page.goto(receipt.share_url, wait_until="networkidle")
            _assert_read_only_roster(
                mobile_page,
                expected_names=expected_names,
                label="390px shared roster",
            )
            mobile_page.screenshot(path=str(EVIDENCE_DIR / "mobile-light.png"), full_page=True)
            mobile.close()

            compact = _new_mobile_context(
                browser,
                width=320,
                height=760,
                color_scheme="dark",
                reduced_motion="reduce",
            )
            compact_page = compact.new_page()
            _attach_error_collectors(
                compact_page,
                label="mobile-320-reduced",
                console_errors=console_errors,
                page_errors=page_errors,
            )
            compact_page.goto(settings.base_url, wait_until="networkidle")
            _assert_guest_landing(compact_page, label="320px reduced-motion guest landing")
            _assert_mobile_entry_actions_in_first_viewport(
                compact_page,
                label="320px reduced-motion guest landing",
            )
            _set_theme_reliably(compact_page, "dark")
            _assert_reduced_motion(compact_page)
            compact_page.screenshot(
                path=str(GATEWAY_EVIDENCE_DIR / "mobile-320-dark-reduced.png"),
                full_page=True,
            )

            compact_page.goto(receipt.share_url, wait_until="networkidle")
            _assert_read_only_roster(
                compact_page,
                expected_names=expected_names,
                label="320px reduced-motion shared roster",
            )
            compact_page.screenshot(
                path=str(EVIDENCE_DIR / "mobile-320-dark-reduced.png"),
                full_page=True,
            )
            compact.close()

            for width, height, label in (
                (360, 800, "mobile-360"),
                (430, 932, "mobile-430"),
                (768, 1024, "tablet-768"),
                (820, 1180, "tablet-820"),
                (844, 390, "mobile-landscape-844x390"),
            ):
                context = _new_mobile_context(
                    browser,
                    width=width,
                    height=height,
                    color_scheme="light",
                )
                context_page = context.new_page()
                _attach_error_collectors(
                    context_page,
                    label=label,
                    console_errors=console_errors,
                    page_errors=page_errors,
                )
                context_page.goto(settings.base_url, wait_until="networkidle")
                _assert_guest_landing(context_page, label=f"{label} guest landing")
                context_page.goto(receipt.share_url, wait_until="networkidle")
                _assert_read_only_roster(
                    context_page,
                    expected_names=expected_names,
                    label=f"{label} shared roster",
                )
                context.close()

            forced = _new_mobile_context(
                browser,
                width=412,
                height=915,
                color_scheme="light",
                forced_colors="active",
            )
            forced_page = forced.new_page()
            _attach_error_collectors(
                forced_page,
                label="mobile-412-forced-colours",
                console_errors=console_errors,
                page_errors=page_errors,
            )
            forced_page.goto(settings.base_url, wait_until="networkidle")
            _assert_guest_landing(forced_page, label="412px forced-colours guest landing")
            if not forced_page.evaluate("matchMedia('(forced-colors: active)').matches"):
                raise RuntimeError("412px public page did not enter forced-colours mode.")
            theme_control = forced_page.get_by_test_id("public-theme-control")
            theme_control.focus()
            forced_focus = theme_control.evaluate(
                """element => ({
                  focusVisible: element.matches(':focus-visible'),
                  outlineWidth: Number.parseFloat(getComputedStyle(element).outlineWidth) || 0,
                  borderWidth: Number.parseFloat(getComputedStyle(element).borderWidth) || 0,
                })"""
            )
            if not forced_focus["focusVisible"] or max(
                forced_focus["outlineWidth"], forced_focus["borderWidth"]
            ) < 1:
                raise RuntimeError(f"Forced-colours theme control lost focus affordance: {forced_focus}")
            forced.close()

            zoom = _new_mobile_context(
                browser,
                width=360,
                height=800,
                color_scheme="light",
            )
            zoom_page = zoom.new_page()
            _attach_error_collectors(
                zoom_page,
                label="mobile-360-text-200",
                console_errors=console_errors,
                page_errors=page_errors,
            )
            for url, label in (
                (settings.base_url, "360px 200% public entrance"),
                (f"{settings.base_url.rstrip('/')}/support#public", "360px 200% public support"),
                (receipt.share_url, "360px 200% public viewer"),
            ):
                _assert_200_percent_public_reflow(zoom_page, url=url, label=label)
            zoom.close()
            browser.close()

        if console_errors or page_errors:
            details = "\n".join([*console_errors, *page_errors])
            raise RuntimeError(
                f"Browser errors: console={len(console_errors)} page={len(page_errors)}\n{details}"
            )

        service.revoke_share(receipt.share_id)
        receipt = None
        print(
            "PASS public gateway in a real Chrome channel: browser-only public/viewer support, entrance/read-only share flow, "
            "320/360/390/412/430px phones, 768/820px tablets, 844x390 landscape, 200% text, forced colours, "
            "focusable horizontal viewer context, performance evidence, system-resolved binary Light/Dark themes, "
            "manual verse refresh, resolved/blocked welcome-audio paths, one-action recovery, quiet continuation navigation, "
            "48px CTAs, reduced motion, no page overflow, and no browser errors. "
            "Unified Guest behavior is verified separately by "
            "scripts/verify_unified_guest_ui.py."
        )
        print(f"Gateway evidence: {GATEWAY_EVIDENCE_DIR}")
        print(f"Viewer evidence: {EVIDENCE_DIR}")
        print(f"Support evidence: {support_evidence}")
        print(f"Performance evidence: {PERFORMANCE_EVIDENCE_PATH}")
        return 0
    finally:
        _write_performance_evidence()
        if receipt is not None and workflow is not None and service is not None:
            try:
                service.revoke_share(receipt.share_id)
            except Exception:
                pass
        shutil.rmtree(temporary_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
