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
REFLOW_SCREENSHOT = SCREENSHOT_DIR / "nicegui-mobile-256-reflow.png"
TABLET_SCREENSHOT = SCREENSHOT_DIR / "nicegui-tablet-768.png"
TALL_TABLET_SCREENSHOT = SCREENSHOT_DIR / "nicegui-tablet-820x1180.png"
LANDSCAPE_TABLET_SCREENSHOT = SCREENSHOT_DIR / "nicegui-tablet-1024x768.png"
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
    "/support",
)
COMPACT_ROUTES = {
    "/": "Dashboard",
    "/rosters": "Rosters",
    "/prefects": "Prefects",
    "/handover": "Handover guide",
    "/settings": "Settings",
}
LANDSCAPE_ROUTES = ("/", "/rosters", "/prefects", "/guide")
TABLET_ROUTES = ("/", "/rosters", "/prefects", "/settings", "/system-architecture")
DESKTOP_TOUCH_ROUTES = ("/", "/rosters", "/prefects", "/engineering", "/settings")
REFLOW_ROUTES = ("/", "/rosters", "/guide")

SHELL_ATMOSPHERE_ASSETS = {
    "/rosters": (
        "weekly-operations",
        "weekly-operations-light-v1.webp",
        "weekly-operations-dark-v1.webp",
    ),
    "/prefects": (
        "people-fairness",
        "people-fairness-light-v1.webp",
        "people-fairness-dark-v1.webp",
    ),
    "/settings": (
        "administration-recovery",
        "administration-recovery-light-v1.webp",
        "administration-recovery-dark-v1.webp",
    ),
    "/access-control": (
        "administration-recovery",
        "administration-recovery-light-v1.webp",
        "administration-recovery-dark-v1.webp",
    ),
}
EMBEDDED_ATMOSPHERE_ASSETS = {
    "/support": ("support-lifeline-light-v1.webp", "support-lifeline-dark-v1.webp"),
}


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
    page.evaluate(
        """async () => {
          if (document.fonts?.ready) await document.fonts.ready;
          await new Promise((resolve) => requestAnimationFrame(
            () => requestAnimationFrame(resolve)
          ));
        }"""
    )
    failures = page.evaluate(
        r"""({rootSelector}) => {
          const root = document.querySelector(rootSelector);
          if (!root) return [{
            label: `missing root: ${rootSelector}`,
            className: '',
            testId: '',
            width: 0,
            height: 0,
          }];
          const selector = [
            'a[href]',
            'button',
            '[role="button"]',
            'summary',
            '.q-toggle',
            '.q-checkbox',
            '.q-radio',
            '.q-item--clickable'
          ].join(',');
          const candidates = [...new Set(root.querySelectorAll(selector))];
          const isNestedDuplicate = (element) => {
            const ancestor = element.parentElement?.closest?.(selector);
            return ancestor && root.contains(ancestor);
          };
          return candidates
            .filter((element) => {
              const style = getComputedStyle(element);
              const bounds = element.getBoundingClientRect();
              if (
                style.display === 'none'
                || style.visibility === 'hidden'
                || bounds.width <= 0
                || bounds.height <= 0
                || element.matches(':disabled,[aria-disabled="true"],[aria-hidden="true"],[tabindex="-1"]')
                || element.closest('[inert],[aria-hidden="true"]')
                || element.matches('.sy-skip-link')
                || isNestedDuplicate(element)
              ) return false;
              /* WCAG explicitly exempts inline links in running text.  Standalone
               * links, buttons, summaries, and Quasar controls still receive the
               * product's stronger 44px touch-target guarantee. */
              if (element.matches('a[href]') && style.display === 'inline') return false;
              return true;
            })
            .map((element) => {
              const bounds = element.getBoundingClientRect();
              return {
                tag: element.tagName.toLowerCase(),
                label: (element.getAttribute('aria-label') || element.textContent || '').trim().slice(0, 80),
                className: String(element.className || '').trim().replace(/\\s+/g, ' ').slice(0, 120),
                testId: element.getAttribute('data-testid') || '',
                width: Math.round(bounds.width * 10) / 10,
                height: Math.round(bounds.height * 10) / 10,
              };
            })
            .filter((item) => item.width < 44 || item.height < 44);
        }""",
        {"rootSelector": root},
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
    active_tabs = navigation.locator(".sy-mobile-tab--active")
    if active_tabs.count() != 1:
        raise AssertionError(f"{label} expected one visually active bottom-navigation action, found {active_tabs.count()}.")
    active_test_id = active_tabs.first.get_attribute("data-testid")
    if active_test_id == "mobile-more":
        if active.count() != 0:
            raise AssertionError(f"{label} must not describe the More menu trigger as the current page.")
    elif active.count() != 1:
        raise AssertionError(f"{label} expected one current primary route, found {active.count()}.")
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
          const footer = document.querySelector('[data-testid="page-copyright"]');
          const navigation = document.querySelector('[data-testid="mobile-bottom-navigation"]');
          const last = main?.lastElementChild;
          if (!last || !footer || !navigation) return null;
          const footerContentBottom = Math.max(
            ...[...footer.children].map((element) => element.getBoundingClientRect().bottom),
            footer.getBoundingClientRect().top
          );
          return {
            lastBottom: last.getBoundingClientRect().bottom,
            footerBottom: footer.getBoundingClientRect().bottom,
            footerContentBottom,
            navigationTop: navigation.getBoundingClientRect().top,
          };
        }"""
    )
    if bottom_metrics is None:
        raise AssertionError(f"{label} is missing its final content or copyright footer.")
    if bottom_metrics["lastBottom"] > bottom_metrics["navigationTop"] + 1:
        raise AssertionError(f"{label} final main content is obscured by bottom navigation: {bottom_metrics}")
    if bottom_metrics["footerContentBottom"] > bottom_metrics["navigationTop"] + 1:
        raise AssertionError(f"{label} copyright footer content is obscured by bottom navigation: {bottom_metrics}")
    page.evaluate("window.scrollTo(0, 0)")


def _assert_mobile_page(page: Page, route: str, *, label: str) -> None:
    response = page.goto(f"{BASE_URL}{route}", wait_until="domcontentloaded")
    if response is None or response.status != 200:
        raise AssertionError(f"{label} returned an unexpected response for {route}: {response}")
    page.locator("main#main-content").wait_for(state="visible", timeout=10_000)
    page.locator('[role="heading"][aria-level="1"]').wait_for(state="visible", timeout=10_000)
    if "Sing Yin Study Prefect Duty Roster" not in page.title():
        raise AssertionError(f"{label} opened an unexpected page title: {page.title()!r}")
    _assert_mobile_atmosphere(page, route=route, label=label)
    _assert_bottom_navigation(page, label=label)
    _assert_no_horizontal_overflow(page, label=label)
    _assert_touch_targets(page, label=label)
    _assert_shell_not_obscured(page, label=label)


def _assert_mobile_atmosphere(page: Page, *, route: str, label: str) -> None:
    """Keep current-route imagery decorative, theme-correct, and outside content."""

    shell_bands = page.locator(".sy-page-atmosphere:visible")
    expected = SHELL_ATMOSPHERE_ASSETS.get(route)
    embedded = EMBEDDED_ATMOSPHERE_ASSETS.get(route)
    if embedded is not None:
        if shell_bands.count() != 0:
            raise AssertionError(f"{label} duplicates an embedded hero with a shell atmosphere band.")
        hero = page.get_by_test_id("support-hero")
        if hero.count() != 1 or not hero.is_visible():
            raise AssertionError(f"{label} is missing its embedded support hero.")
        if hero.locator(".sy-support-hero-steps li").count() != 3:
            raise AssertionError(f"{label} support hero lost its three-step workflow.")
        visual = hero.evaluate(
            """element => ({
              backgroundImage: getComputedStyle(element, '::before').backgroundImage,
              dark: document.body.classList.contains('body--dark'),
            })"""
        )
        expected_asset = embedded[1] if visual["dark"] else embedded[0]
        if expected_asset not in visual["backgroundImage"]:
            raise AssertionError(
                f"{label} embedded support hero did not resolve the current theme asset: "
                f"{visual['backgroundImage']}"
            )
        return
    if expected is None:
        if shell_bands.count() != 0:
            raise AssertionError(f"{label} duplicates an embedded hero with a shell atmosphere band.")
    else:
        slot, light_asset, dark_asset = expected
        if shell_bands.count() != 1:
            raise AssertionError(f"{label} expected one shell atmosphere band, found {shell_bands.count()}.")
        band = shell_bands.first
        if band.get_attribute("aria-hidden") != "true":
            raise AssertionError(f"{label} atmosphere is exposed to assistive technology.")
        if band.get_attribute("data-sy-atmosphere-slot") != slot:
            raise AssertionError(f"{label} atmosphere uses the wrong route-family slot.")
        if band.get_attribute("data-sy-atmosphere-presentation") != "shell":
            raise AssertionError(f"{label} atmosphere lost its shell presentation contract.")
        if band.locator("button, a, input, select, textarea, table, [role=dialog]").count() != 0:
            raise AssertionError(f"{label} atmosphere contains interactive or sensitive content.")
        metrics = band.evaluate(
            """(element) => {
              const bounds = element.getBoundingClientRect();
              const nextContent = element.nextElementSibling?.getBoundingClientRect();
              return {
                backgroundImage: getComputedStyle(element, '::before').backgroundImage,
                dark: document.body.classList.contains('body--dark'),
                height: bounds.height,
                bottom: bounds.bottom,
                nextContentTop: nextContent?.top ?? null,
              };
            }"""
        )
        expected_asset = dark_asset if metrics["dark"] else light_asset
        if expected_asset not in metrics["backgroundImage"]:
            raise AssertionError(
                f"{label} did not resolve only the current theme asset {expected_asset}: "
                f"{metrics['backgroundImage']}"
            )
        if metrics["height"] < 90:
            raise AssertionError(f"{label} atmosphere collapsed below its reserved mobile height: {metrics}")
        if metrics["nextContentTop"] is None or metrics["nextContentTop"] + 1 < metrics["bottom"]:
            raise AssertionError(f"{label} atmosphere overlaps the following page content: {metrics}")

    if route == "/devotional":
        chapel = page.locator(".sy-chapel:visible")
        if chapel.count() != 1:
            raise AssertionError(f"{label} expected one Daily Verse reading surface.")
        devotional = chapel.evaluate(
            """(element) => ({
              backgroundImage: getComputedStyle(element, '::after').backgroundImage,
              opacity: Number.parseFloat(getComputedStyle(element, '::after').opacity),
              dark: document.body.classList.contains('body--dark'),
            })"""
        )
        expected_asset = (
            "devotional-sacred-dark-v2.webp"
            if devotional["dark"]
            else "devotional-sacred-light-v2.webp"
        )
        if expected_asset not in devotional["backgroundImage"]:
            raise AssertionError(f"{label} did not resolve the accepted Daily Verse v2 image.")
        if not 0.15 <= devotional["opacity"] <= 0.20:
            raise AssertionError(f"{label} Daily Verse image is too strong for mobile reading: {devotional}")


def _assert_desktop_touch_page(page: Page, route: str, *, label: str) -> None:
    """Verify the >900px desktop shell remains touch-safe on a landscape tablet."""

    response = page.goto(f"{BASE_URL}{route}", wait_until="domcontentloaded")
    if response is None or response.status != 200:
        raise AssertionError(f"{label} returned an unexpected response for {route}: {response}")
    page.locator("main#main-content").wait_for(state="visible", timeout=10_000)
    page.locator('[role="heading"][aria-level="1"]').wait_for(state="visible", timeout=10_000)
    if "Sing Yin Study Prefect Duty Roster" not in page.title():
        raise AssertionError(f"{label} opened an unexpected page title: {page.title()!r}")

    mobile_navigation = page.get_by_test_id("mobile-bottom-navigation")
    if mobile_navigation.is_visible():
        raise AssertionError(f"{label} exposed both desktop and mobile navigation shells.")
    drawer_trigger = page.locator(".sy-desktop-drawer-trigger")
    drawer_trigger.wait_for(state="visible", timeout=10_000)
    trigger_box = drawer_trigger.bounding_box()
    if trigger_box is None or trigger_box["width"] < 44 or trigger_box["height"] < 44:
        raise AssertionError(f"{label} desktop navigation trigger is not touch-safe: {trigger_box}")
    page.locator(".sy-desktop-header-controls").wait_for(state="visible", timeout=10_000)

    shell_metrics = page.evaluate(
        """() => {
          const header = document.querySelector('.sy-app-header');
          const main = document.querySelector('main#main-content');
          const drawer = document.querySelector('#main-navigation-drawer');
          const leading = document.querySelector('.sy-header-leading');
          if (!header || !main || !drawer || !leading) return null;
          const headerBounds = header.getBoundingClientRect();
          const mainBounds = main.getBoundingClientRect();
          const drawerBounds = drawer.getBoundingClientRect();
          const leadingBounds = leading.getBoundingClientRect();
          return {
            viewport: window.innerWidth,
            headerTop: headerBounds.top,
            headerBottom: headerBounds.bottom,
            drawerTop: drawerBounds.top,
            headerLeadingTop: leadingBounds.top,
            headerLeadingBottom: leadingBounds.bottom,
            headerLeadingLeft: leadingBounds.left,
            headerLeadingRight: leadingBounds.right,
            mainTop: mainBounds.top,
            mainLeft: mainBounds.left,
            mainRight: mainBounds.right,
            mainWidth: mainBounds.width,
          };
        }"""
    )
    if shell_metrics is None:
        raise AssertionError(f"{label} is missing the desktop touch shell regions.")
    if shell_metrics["mainTop"] + 1 < shell_metrics["headerBottom"]:
        raise AssertionError(f"{label} main content is obscured by the desktop header: {shell_metrics}")
    if shell_metrics["drawerTop"] + 1 < shell_metrics["headerBottom"]:
        raise AssertionError(f"{label} desktop drawer obscures the global header: {shell_metrics}")
    if (
        shell_metrics["headerLeadingTop"] + 1 < shell_metrics["headerTop"]
        or shell_metrics["headerLeadingBottom"] > shell_metrics["headerBottom"] + 1
        or shell_metrics["headerLeadingLeft"] < -1
        or shell_metrics["headerLeadingRight"] > shell_metrics["viewport"] + 1
    ):
        raise AssertionError(f"{label} header identity is clipped or outside the viewport: {shell_metrics}")
    if shell_metrics["mainWidth"] < 520 or shell_metrics["mainRight"] > shell_metrics["viewport"] + 1:
        raise AssertionError(f"{label} desktop shell leaves an unusable tablet workspace: {shell_metrics}")

    _assert_no_horizontal_overflow(page, label=label)
    _assert_touch_targets(page, label=label)


def _open_mobile_drawer(page: Page) -> Locator:
    more = page.get_by_test_id("mobile-more")
    page.wait_for_function(
        "document.querySelector('[data-testid=mobile-more]')?.dataset.syDrawerA11y === 'ready'",
        timeout=10_000,
    )
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
    scroll_region = drawer.locator(".sy-sidebar-navigation")
    scroll_region.wait_for(state="visible", timeout=5_000)
    navigation_focusables = scroll_region.locator(
        'a[href]:visible, button:visible, [tabindex]:not([tabindex="-1"]):visible'
    )
    if navigation_focusables.count() < 1:
        raise AssertionError(f"{label} drawer navigation has no keyboard destination.")
    final_navigation_control = navigation_focusables.last
    metrics = scroll_region.evaluate(
        """(element) => {
          element.scrollTop = 0;
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
    if metrics["scrollHeight"] > metrics["clientHeight"] and metrics["after"] <= metrics["before"]:
        raise AssertionError(f"{label} drawer cannot reach its lower navigation items: {metrics}")
    scroll_region_box = scroll_region.bounding_box()
    last_box = final_navigation_control.bounding_box()
    if (
        scroll_region_box is None
        or last_box is None
        or last_box["y"] < scroll_region_box["y"] - 1
        or last_box["y"] + last_box["height"]
        > scroll_region_box["y"] + scroll_region_box["height"] + 1
    ):
        raise AssertionError(f"{label} drawer clips its final navigation item: {metrics}")
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
    escape_drawer = _open_mobile_drawer(page)
    page.keyboard.press("Escape")
    escape_drawer.wait_for(state="hidden", timeout=5_000)
    page.wait_for_function(
        """() => {
          const button = document.querySelector('[data-testid="mobile-more"]');
          return button?.getAttribute('aria-expanded') === 'false' && document.activeElement === button;
        }""",
        timeout=5_000,
    )


def _assert_secondary_route_navigation(page: Page, *, route: str, label: str) -> None:
    """Keep the More action a menu trigger while the drawer owns route state."""

    _assert_mobile_page(page, route, label=label)
    more = page.get_by_test_id("mobile-more")
    if more.get_attribute("aria-current") is not None:
        raise AssertionError(f"{label} incorrectly exposes More as the current page.")
    if "sy-mobile-tab--active" not in (more.get_attribute("class") or ""):
        raise AssertionError(f"{label} does not visually associate the secondary route with More.")
    drawer = _open_mobile_drawer(page)
    current = drawer.locator('[aria-current="page"]')
    if current.count() != 1:
        raise AssertionError(f"{label} expected one current route in the drawer, found {current.count()}.")
    if not current.first.is_visible():
        raise AssertionError(f"{label} current drawer route is not visible.")
    page.keyboard.press("Escape")
    drawer.wait_for(state="hidden", timeout=5_000)


def _assert_route_focus_transfer(page: Page, *, label: str) -> None:
    """Shared-route navigation must announce the new page to keyboard and AT users."""

    _assert_mobile_page(page, "/", label=f"{label} focus origin")
    tabs = page.get_by_test_id("mobile-bottom-navigation").locator(".sy-mobile-tab")
    tabs.nth(1).click()
    page.wait_for_url("**/rosters", timeout=10_000)
    page.wait_for_function(
        "document.activeElement === document.getElementById('main-content')",
        timeout=10_000,
    )
    if page.locator("main#main-content:focus").count() != 1:
        raise AssertionError(f"{label} did not transfer focus to the shared main landmark.")
    tabs = page.get_by_test_id("mobile-bottom-navigation").locator(".sy-mobile-tab")
    tabs.nth(2).click()
    page.wait_for_url("**/prefects", timeout=10_000)
    page.wait_for_function(
        "document.activeElement === document.getElementById('main-content')",
        timeout=10_000,
    )
    if page.locator("main#main-content:focus").count() != 1:
        raise AssertionError(f"{label} lost main-landmark focus on the second shared-route navigation.")


def _assert_coarse_pointer_icon_story(page: Page, *, label: str) -> None:
    """A touch opens the drawer with a persistent menu-to-close state story."""

    _assert_mobile_page(page, "/", label=f"{label} icon-story origin")
    if page.evaluate("matchMedia('(hover: hover) and (pointer: fine)').matches"):
        raise AssertionError(f"{label} unexpectedly exposes a fine pointer.")
    more = page.get_by_test_id("mobile-more")
    icon = more.locator(".q-icon").first
    icon.wait_for(state="visible", timeout=10_000)
    if icon.inner_text().strip() != "menu":
        raise AssertionError(f"{label} icon story did not start from the menu glyph.")
    if icon.get_attribute("data-sy-icon-story-category") != "persistent":
        raise AssertionError(f"{label} menu icon is not governed by persistent drawer state.")
    more.click()
    page.wait_for_function(
        """() => {
          const host = document.querySelector('[data-testid="mobile-more"]');
          const icon = host?.querySelector('.q-icon');
          return host?.getAttribute('aria-expanded') === 'true' &&
            icon?.textContent?.trim() === 'close' &&
            icon?.dataset.syIconStoryCategory === 'persistent';
        }""",
        timeout=3_000,
    )
    page.keyboard.press("Escape")
    page.wait_for_function(
        """() => {
          const host = document.querySelector('[data-testid="mobile-more"]');
          const icon = host?.querySelector('.q-icon');
          return host?.getAttribute('aria-expanded') === 'false' &&
            icon?.textContent?.trim() === 'menu' &&
            icon?.dataset.syIconStoryCategory === 'persistent';
        }""",
        timeout=3_000,
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
        # Prove that the fixed actions navigate the shared application and
        # announce each new route through the main landmark.
        _assert_route_focus_transfer(portrait_page, label="390px shared-route navigation")
        _assert_coarse_pointer_icon_story(portrait_page, label="390px touch")
        portrait.close()

        tablet_page, tablet = _new_mobile_page(
            browser,
            width=768,
            height=1024,
            label="tablet-768",
            console_errors=console_errors,
            page_errors=page_errors,
        )
        for route in TABLET_ROUTES:
            _assert_mobile_page(tablet_page, route, label=f"768x1024 {route}")
        _assert_secondary_route_navigation(
            tablet_page,
            route="/settings",
            label="768x1024 secondary Settings route",
        )
        _assert_mobile_page(tablet_page, "/", label="768x1024 tablet screenshot")
        tablet_page.screenshot(path=str(TABLET_SCREENSHOT), full_page=False)
        tablet.close()

        tall_tablet_page, tall_tablet = _new_mobile_page(
            browser,
            width=820,
            height=1180,
            label="tablet-820x1180",
            console_errors=console_errors,
            page_errors=page_errors,
        )
        for route in TABLET_ROUTES:
            _assert_mobile_page(tall_tablet_page, route, label=f"820x1180 {route}")
        _assert_secondary_route_navigation(
            tall_tablet_page,
            route="/settings",
            label="820x1180 secondary Settings route",
        )
        _assert_mobile_page(tall_tablet_page, "/", label="820x1180 tablet screenshot")
        tall_tablet_page.screenshot(path=str(TALL_TABLET_SCREENSHOT), full_page=False)
        tall_tablet.close()

        landscape_tablet_page, landscape_tablet = _new_mobile_page(
            browser,
            width=1024,
            height=768,
            label="tablet-1024x768",
            console_errors=console_errors,
            page_errors=page_errors,
        )
        for route in DESKTOP_TOUCH_ROUTES:
            _assert_desktop_touch_page(landscape_tablet_page, route, label=f"1024x768 {route}")
        _assert_desktop_touch_page(
            landscape_tablet_page,
            "/",
            label="1024x768 tablet screenshot",
        )
        landscape_tablet_page.screenshot(path=str(LANDSCAPE_TABLET_SCREENSHOT), full_page=False)
        landscape_tablet.close()

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
        if compact_tools.count() < 2:
            raise AssertionError("320px drawer does not expose language, sound, and appearance controls.")
        if compact_drawer.get_by_test_id("mobile-theme-control").count() != 1:
            raise AssertionError("320px drawer does not expose the binary appearance control.")
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
        compact_theme_control = compact_drawer.get_by_test_id("mobile-theme-control")
        if compact_theme_control.count() != 1:
            raise AssertionError("320px appearance control is not unique.")
        if compact_page.locator("body.body--dark").count() != 1:
            compact_theme_control.click()
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

        reflow_page, reflow = _new_mobile_page(
            browser,
            width=256,
            height=700,
            label="mobile-256-reflow",
            console_errors=console_errors,
            page_errors=page_errors,
        )
        for route in REFLOW_ROUTES:
            _assert_mobile_page(reflow_page, route, label=f"256x700 reflow {route}")
        _assert_secondary_route_navigation(
            reflow_page,
            route="/guide",
            label="256x700 secondary Guide route",
        )
        reflow_page.screenshot(path=str(REFLOW_SCREENSHOT), full_page=False)
        reflow.close()

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
        "Mobile browser verification passed: 390px phone, 768x1024 and 820x1180 adaptive touch tablets, "
        "1024x768 desktop-shell touch tablet, "
        "320px reduced-motion, 256px reflow, and 844x390 landscape contexts; "
        f"screenshots: {PORTRAIT_SCREENSHOT}, {TABLET_SCREENSHOT}, {TALL_TABLET_SCREENSHOT}, "
        f"{LANDSCAPE_TABLET_SCREENSHOT}, {COMPACT_SCREENSHOT}, "
        f"{REFLOW_SCREENSHOT}, {LANDSCAPE_SCREENSHOT}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
