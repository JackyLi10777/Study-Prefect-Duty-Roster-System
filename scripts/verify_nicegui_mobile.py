"""Verify the official NiceGUI pages in real touch/mobile browser contexts.

The verifier is intentionally read-only.  It must run beside an already-started
NiceGUI instance whose SQLite database, backup directory, and log directory are
all disposable.  ``scripts/verify_release_candidate.py`` owns that isolated
server lifecycle for release evidence.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from playwright.sync_api import Browser, BrowserContext, Locator, Page, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.getenv("SING_YIN_TEST_URL", "http://127.0.0.1:8080").rstrip("/")
CANONICAL_DATABASE = (PROJECT_ROOT / "data" / "runtime" / "sing-yin-roster.sqlite3").resolve()
CANONICAL_BACKUPS = (PROJECT_ROOT / "data" / "backups").resolve()
SCREENSHOT_DIR = PROJECT_ROOT / "logs"
PORTRAIT_SCREENSHOT = SCREENSHOT_DIR / "nicegui-mobile-390.png"
COMPACT_SCREENSHOT = SCREENSHOT_DIR / "nicegui-mobile-320-drawer.png"
LANDSCAPE_SCREENSHOT = SCREENSHOT_DIR / "nicegui-mobile-landscape.png"

PORTRAIT_ROUTES = (
    "/",
    "/rosters",
    "/prefects",
    "/handover",
    "/settings",
    "/access-control",
    "/getting-started",
    "/guide",
    "/devotional",
    "/platform",
    "/engineering",
    "/system-architecture",
)
COMPACT_ROUTES = {
    "/": "Dashboard",
    "/rosters": "Rosters",
    "/prefects": "Prefects",
    "/handover": "Handover guide",
    "/settings": "Settings",
}
LANDSCAPE_ROUTES = ("/", "/rosters", "/prefects", "/guide")


def isolated_paths() -> tuple[Path, Path, Path]:
    """Fail closed unless every durable location belongs to an E2E run."""
    if os.getenv("SING_YIN_E2E_ISOLATED") != "1":
        raise RuntimeError("Set SING_YIN_E2E_ISOLATED=1 before mobile browser verification.")
    run_id = os.getenv("SING_YIN_E2E_RUN_ID", "").strip()
    if not re.fullmatch(r"E2E-[A-F0-9]{12}", run_id):
        raise RuntimeError("Set a unique, valid SING_YIN_E2E_RUN_ID before mobile browser verification.")
    required = ("SING_YIN_DATABASE_PATH", "SING_YIN_BACKUP_DIR", "SING_YIN_LOG_DIR")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing isolated path configuration: {', '.join(missing)}")

    database_path = Path(os.environ["SING_YIN_DATABASE_PATH"]).resolve()
    backup_dir = Path(os.environ["SING_YIN_BACKUP_DIR"]).resolve()
    log_dir = Path(os.environ["SING_YIN_LOG_DIR"]).resolve()
    if database_path == CANONICAL_DATABASE or backup_dir == CANONICAL_BACKUPS:
        raise RuntimeError("Mobile verification must not use the canonical school database or backup directory.")

    endpoint = urlsplit(BASE_URL)
    if endpoint.scheme != "http" or endpoint.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("Mobile verification requires an isolated loopback HTTP endpoint.")
    return database_path, backup_dir, log_dir


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


def _assert_no_horizontal_overflow(page: Page, *, label: str) -> None:
    metrics = page.evaluate(
        """() => ({
          viewport: window.innerWidth,
          document: document.documentElement.scrollWidth,
          body: document.body.scrollWidth,
          offenders: [...document.querySelectorAll('body *')]
            .filter((element) => {
              const style = getComputedStyle(element);
              if (style.display === 'none' || style.visibility === 'hidden') return false;
              const bounds = element.getBoundingClientRect();
              return bounds.right > window.innerWidth + 1 && bounds.left < window.innerWidth;
            })
            .slice(0, 8)
            .map((element) => ({
              tag: element.tagName.toLowerCase(),
              className: String(element.className || '').slice(0, 100),
              right: Math.round(element.getBoundingClientRect().right),
            })),
        })"""
    )
    if metrics["document"] > metrics["viewport"] + 1 or metrics["body"] > metrics["viewport"] + 1:
        raise AssertionError(f"{label} has horizontal overflow: {metrics}")


def _assert_touch_targets(page: Page, *, label: str, root: str = "body") -> None:
    target_selector = ", ".join(
        f"{root} {selector}:visible"
        for selector in (".q-btn", ".q-toggle", ".q-checkbox", ".q-radio", ".q-item--clickable")
    )
    failures = page.locator(target_selector).evaluate_all(
        """(elements) => elements
          .map((element) => {
            const bounds = element.getBoundingClientRect();
            return {
              label: (element.getAttribute('aria-label') || element.textContent || '').trim().slice(0, 80),
              width: Math.round(bounds.width * 10) / 10,
              height: Math.round(bounds.height * 10) / 10,
            };
          })
          .filter((item) => item.width < 44 || item.height < 44)"""
    )
    if failures:
        raise AssertionError(f"{label} has touch targets smaller than 44 CSS pixels: {failures[:8]}")


def _assert_bottom_navigation(page: Page, *, label: str) -> None:
    navigation = page.get_by_test_id("mobile-bottom-navigation")
    navigation.wait_for(state="visible", timeout=10_000)
    tabs = navigation.locator(".sy-mobile-tab")
    if tabs.count() != 4:
        raise AssertionError(f"{label} expected four bottom-navigation actions, found {tabs.count()}.")
    active = navigation.locator('[aria-current="page"]')
    if active.count() != 1:
        raise AssertionError(f"{label} expected one current bottom-navigation action, found {active.count()}.")
    for index in range(tabs.count()):
        box = tabs.nth(index).bounding_box()
        if box is None or box["width"] < 44 or box["height"] < 44:
            raise AssertionError(f"{label} bottom-navigation action {index} is not a 44px touch target: {box}")
    viewport_height = int(page.evaluate("window.innerHeight"))
    navigation_box = navigation.bounding_box()
    if navigation_box is None or navigation_box["y"] + navigation_box["height"] > viewport_height + 1:
        raise AssertionError(f"{label} bottom navigation is outside the visual viewport: {navigation_box}")


def _assert_shell_not_obscured(page: Page, *, label: str) -> None:
    metrics = page.evaluate(
        """() => {
          const header = document.querySelector('.sy-app-header');
          const main = document.querySelector('main#main-content');
          const navigation = document.querySelector('[data-testid="mobile-bottom-navigation"]');
          if (!header || !main || !navigation) return null;
          const headerBounds = header.getBoundingClientRect();
          const mainBounds = main.getBoundingClientRect();
          const navigationBounds = navigation.getBoundingClientRect();
          return {
            headerBottom: headerBounds.bottom,
            mainTop: mainBounds.top,
            mainPaddingBottom: parseFloat(getComputedStyle(main).paddingBottom) || 0,
            navigationHeight: navigationBounds.height,
          };
        }"""
    )
    if metrics is None:
        raise AssertionError(f"{label} is missing the mobile shell regions.")
    if metrics["mainTop"] + 1 < metrics["headerBottom"]:
        raise AssertionError(f"{label} main content is obscured by the header: {metrics}")
    if metrics["mainPaddingBottom"] + 1 < metrics["navigationHeight"]:
        raise AssertionError(f"{label} main content does not reserve the bottom-navigation safe area: {metrics}")

    page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
    page.wait_for_timeout(60)
    bottom_metrics = page.evaluate(
        """() => {
          const main = document.querySelector('main#main-content');
          const navigation = document.querySelector('[data-testid="mobile-bottom-navigation"]');
          const last = main?.lastElementChild;
          if (!last || !navigation) return null;
          return {
            lastBottom: last.getBoundingClientRect().bottom,
            navigationTop: navigation.getBoundingClientRect().top,
          };
        }"""
    )
    if bottom_metrics is None or bottom_metrics["lastBottom"] > bottom_metrics["navigationTop"] + 1:
        raise AssertionError(f"{label} final content is obscured by bottom navigation: {bottom_metrics}")
    page.evaluate("window.scrollTo(0, 0)")


def _assert_mobile_page(page: Page, route: str, *, label: str) -> None:
    response = page.goto(f"{BASE_URL}{route}", wait_until="domcontentloaded")
    if response is None or response.status != 200:
        raise AssertionError(f"{label} returned an unexpected response for {route}: {response}")
    page.locator("main#main-content").wait_for(state="visible", timeout=10_000)
    page.locator('[role="heading"][aria-level="1"]').wait_for(state="visible", timeout=10_000)
    if "Sing Yin Study Prefect Duty Roster" not in page.title():
        raise AssertionError(f"{label} opened an unexpected page title: {page.title()!r}")
    _assert_bottom_navigation(page, label=label)
    _assert_no_horizontal_overflow(page, label=label)
    _assert_touch_targets(page, label=label)
    _assert_shell_not_obscured(page, label=label)


def _open_mobile_drawer(page: Page) -> Locator:
    more = page.get_by_test_id("mobile-more")
    if more.get_attribute("aria-expanded") != "false":
        raise AssertionError("Mobile More must expose its initial collapsed state.")
    more.click()
    drawer = page.locator("#main-navigation-drawer")
    drawer.wait_for(state="visible", timeout=5_000)
    page.wait_for_function(
        "document.querySelector('[data-testid=mobile-more]')?.getAttribute('aria-expanded') === 'true'"
    )
    if not page.evaluate("document.activeElement?.closest?.('#main-navigation-drawer') !== null"):
        raise AssertionError("Opening mobile navigation must move focus into the drawer.")
    return drawer


def _assert_drawer_scrolls(page: Page, *, label: str) -> None:
    drawer = _open_mobile_drawer(page)
    focusables = drawer.locator('a[href]:visible, button:visible, [tabindex]:not([tabindex="-1"]):visible')
    if focusables.count() < 2:
        raise AssertionError(f"{label} drawer does not expose enough keyboard destinations.")
    first = focusables.first
    last = focusables.last
    first.focus()
    page.keyboard.press("Shift+Tab")
    if not last.evaluate("element => document.activeElement === element"):
        raise AssertionError(f"{label} drawer did not cycle Shift+Tab to its last control.")
    page.keyboard.press("Tab")
    if not first.evaluate("element => document.activeElement === element"):
        raise AssertionError(f"{label} drawer did not cycle Tab to its first control.")
    # NiceGUI applies the requested id/classes to Quasar's scrollable drawer
    # content node itself, rather than to an extra wrapper around that node.
    metrics = drawer.evaluate(
        """(element) => {
          const before = element.scrollTop;
          element.scrollTop = element.scrollHeight;
          return {
            before,
            after: element.scrollTop,
            clientHeight: element.clientHeight,
            scrollHeight: element.scrollHeight,
            overflowY: getComputedStyle(element).overflowY,
          };
        }"""
    )
    if metrics["scrollHeight"] <= metrics["clientHeight"] or metrics["after"] <= metrics["before"]:
        raise AssertionError(f"{label} drawer cannot reach its lower navigation items: {metrics}")
    if metrics["overflowY"] not in {"auto", "scroll"}:
        raise AssertionError(f"{label} drawer does not expose a scrollable overflow mode: {metrics}")
    _assert_touch_targets(page, label=label, root="#main-navigation-drawer")
    backdrop = page.locator(".q-drawer__backdrop:visible")
    backdrop_box = backdrop.bounding_box()
    if backdrop_box is None:
        raise AssertionError(f"{label} drawer did not expose a closable backdrop.")
    backdrop.click(position={"x": backdrop_box["width"] - 2, "y": 8})
    drawer.wait_for(state="hidden", timeout=5_000)
    page.wait_for_function(
        "document.querySelector('[data-testid=mobile-more]')?.getAttribute('aria-expanded') === 'false'"
    )
    if page.evaluate("document.activeElement?.getAttribute('data-testid')") != "mobile-more":
        raise AssertionError("Backdrop-closing mobile navigation must restore focus to More.")
    _open_mobile_drawer(page)
    page.keyboard.press("Escape")
    drawer.wait_for(state="hidden", timeout=5_000)
    page.wait_for_function(
        """() => {
          const button = document.querySelector('[data-testid="mobile-more"]');
          return button?.getAttribute('aria-expanded') === 'false' && document.activeElement === button;
        }""",
        timeout=5_000,
    )


def _assert_responsive_table_cards(page: Page) -> None:
    """Prove dense fairness data uses the phone grid without duplicating its data source."""
    _assert_mobile_page(page, "/prefects", label="390px responsive fairness table")
    tabs = page.locator(".q-tab")
    if tabs.count() < 3:
        raise AssertionError("Prefect workspace is missing the fairness tab.")
    tabs.nth(2).click()
    mobile_tables = page.locator(".sy-responsive-table-mobile:visible")
    mobile_tables.first.wait_for(state="visible", timeout=10_000)
    if mobile_tables.count() < 1:
        raise AssertionError("Fairness data did not expose a mobile grid-card table.")
    if page.locator(".sy-responsive-table-desktop:visible").count() != 0:
        raise AssertionError("Desktop fairness table remained visible in the phone composition.")


def _new_mobile_page(
    browser: Browser,
    *,
    width: int,
    height: int,
    label: str,
    console_errors: list[str],
    page_errors: list[str],
    reduced_motion: str = "no-preference",
) -> tuple[Page, BrowserContext]:
    context = browser.new_context(
        viewport={"width": width, "height": height},
        is_mobile=True,
        has_touch=True,
        device_scale_factor=2,
        reduced_motion=reduced_motion,  # type: ignore[arg-type]
    )
    page = context.new_page()
    _attach_error_collectors(
        page,
        label=label,
        console_errors=console_errors,
        page_errors=page_errors,
    )
    return page, context


def main() -> int:
    isolated_paths()
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        portrait_page, portrait = _new_mobile_page(
            browser,
            width=390,
            height=844,
            label="mobile-390",
            console_errors=console_errors,
            page_errors=page_errors,
        )
        if portrait_page.evaluate("matchMedia('(hover: hover) and (pointer: fine)').matches"):
            raise AssertionError("390px mobile context unexpectedly exposes a fine hover pointer.")
        for route in PORTRAIT_ROUTES:
            _assert_mobile_page(portrait_page, route, label=f"390px {route}")
        _assert_responsive_table_cards(portrait_page)
        _assert_mobile_page(portrait_page, "/", label="390px dashboard screenshot")
        portrait_page.screenshot(path=str(PORTRAIT_SCREENSHOT), full_page=False)
        # Prove that the real fixed actions navigate to the shared routes rather
        # than a second mobile-only application.
        portrait_page.get_by_test_id("mobile-bottom-navigation").locator(".sy-mobile-tab").nth(1).click()
        portrait_page.wait_for_url("**/rosters", timeout=10_000)
        portrait_page.get_by_test_id("mobile-bottom-navigation").locator(".sy-mobile-tab").nth(2).click()
        portrait_page.wait_for_url("**/prefects", timeout=10_000)
        portrait.close()

        compact_page, compact = _new_mobile_page(
            browser,
            width=320,
            height=760,
            label="mobile-320-reduced",
            console_errors=console_errors,
            page_errors=page_errors,
            reduced_motion="reduce",
        )
        _assert_mobile_page(compact_page, "/", label="320px initial dashboard")
        compact_drawer = _open_mobile_drawer(compact_page)
        compact_tools = compact_drawer.get_by_test_id("mobile-drawer-tools").locator(".sy-mobile-drawer-tool")
        if compact_tools.count() < 3:
            raise AssertionError("320px drawer does not expose language, sound, and appearance controls.")
        compact_tools.nth(0).click()
        compact_page.wait_for_function(
            """() => {
              const button = document.querySelector('[data-testid="mobile-more"]');
              return button?.getAttribute('aria-label') === 'More' &&
                button?.getAttribute('aria-expanded') === 'false' &&
                button?.dataset.syDrawerA11y === 'ready';
            }""",
            timeout=10_000,
        )
        compact_page.locator('[role="heading"][aria-level="1"]').filter(has_text="Dashboard").wait_for(
            state="visible",
            timeout=10_000,
        )
        compact_drawer = _open_mobile_drawer(compact_page)
        compact_drawer.get_by_test_id("mobile-drawer-tools").locator(".sy-mobile-drawer-tool").nth(2).click()
        compact_page.wait_for_function("document.body.classList.contains('body--dark')", timeout=10_000)
        for route, expected_heading in COMPACT_ROUTES.items():
            _assert_mobile_page(compact_page, route, label=f"320px English dark {route}")
            compact_page.locator('[role="heading"][aria-level="1"]').filter(has_text=expected_heading).wait_for(
                state="visible",
                timeout=10_000,
            )
            if compact_page.locator("body.body--dark").count() != 1:
                raise AssertionError(f"320px English route {route} did not retain dark appearance.")
        _assert_mobile_page(compact_page, "/", label="320px drawer")
        _assert_drawer_scrolls(compact_page, label="320px drawer")
        compact_page.screenshot(path=str(COMPACT_SCREENSHOT), full_page=False)
        compact.close()

        landscape_page, landscape = _new_mobile_page(
            browser,
            width=844,
            height=390,
            label="mobile-landscape",
            console_errors=console_errors,
            page_errors=page_errors,
        )
        for route in LANDSCAPE_ROUTES:
            _assert_mobile_page(landscape_page, route, label=f"844x390 {route}")
        _assert_mobile_page(landscape_page, "/guide", label="844x390 guide screenshot")
        landscape_page.screenshot(path=str(LANDSCAPE_SCREENSHOT), full_page=False)
        landscape.close()
        browser.close()

    if console_errors or page_errors:
        details = "\n".join([*console_errors, *page_errors])
        raise RuntimeError(
            f"Mobile browser errors: console={len(console_errors)} page={len(page_errors)}\n{details}"
        )
    print(
        "Mobile browser verification passed: 390px, 320px reduced-motion, and 844x390 touch contexts; "
        f"screenshots: {PORTRAIT_SCREENSHOT}, {COMPACT_SCREENSHOT}, {LANDSCAPE_SCREENSHOT}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
