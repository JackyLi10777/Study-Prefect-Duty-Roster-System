"""Verify the official NiceGUI pages in real touch/mobile browser contexts.

The verifier is intentionally read-only.  It must run beside an already-started
NiceGUI instance whose SQLite database, backup directory, and log directory are
all disposable.  ``scripts/verify_release_candidate.py`` owns that isolated
server lifecycle for release evidence.
"""

from __future__ import annotations

import os
from pathlib import Path
import json
import re
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import Browser, BrowserContext, Error, Locator, Page, Playwright, sync_playwright


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
PERFORMANCE_EVIDENCE_PATH = SCREENSHOT_DIR / "nicegui-mobile-performance.json"
PERFORMANCE_EVIDENCE: list[dict[str, Any]] = []

PHONE_SMOKE_VIEWPORTS = (
    (360, 800, "mobile-360"),
    (412, 915, "mobile-412-forced-colours"),
    (430, 932, "mobile-430"),
)

PERFORMANCE_OBSERVER_SCRIPT = r"""
(() => {
  const evidence = {
    largestContentfulPaint: 0,
    cumulativeLayoutShift: 0,
    longestTask: 0,
    longTaskCount: 0,
  };
  window.__syMobilePerformanceEvidence = evidence;
  const observe = (type, callback) => {
    try {
      const observer = new PerformanceObserver((list) => callback(list.getEntries()));
      observer.observe({type, buffered: true});
    } catch (_) {
      // Older engines may not expose every entry type. Missing support is
      // reported in the collected evidence instead of breaking page startup.
    }
  };
  observe('largest-contentful-paint', entries => {
    for (const entry of entries) evidence.largestContentfulPaint = Math.max(
      evidence.largestContentfulPaint,
      entry.startTime || 0
    );
  });
  observe('layout-shift', entries => {
    for (const entry of entries) {
      if (!entry.hadRecentInput) evidence.cumulativeLayoutShift += entry.value || 0;
    }
  });
  observe('longtask', entries => {
    for (const entry of entries) {
      evidence.longTaskCount += 1;
      evidence.longestTask = Math.max(evidence.longestTask, entry.duration || 0);
    }
  });
})();
"""

VISUAL_VIEWPORT_TEST_DOUBLE = r"""
(() => {
  const target = new EventTarget();
  const state = {};
  const viewport = target;
  for (const [name, fallback] of Object.entries({
    width: () => window.innerWidth,
    height: () => window.innerHeight,
    offsetLeft: () => 0,
    offsetTop: () => 0,
    pageLeft: () => window.scrollX,
    pageTop: () => window.scrollY,
    scale: () => 1,
  })) {
    Object.defineProperty(viewport, name, {
      configurable: true,
      enumerable: true,
      get: () => state[name] ?? fallback(),
    });
  }
  Object.defineProperty(window, 'visualViewport', {configurable: true, value: viewport});
  window.__sySetTestVisualViewport = (values) => {
    Object.assign(state, values || {});
    viewport.dispatchEvent(new Event('resize'));
  };
  const nativeScrollIntoView = Element.prototype.scrollIntoView;
  Element.prototype.scrollIntoView = function (options) {
    window.__syLastScrollIntoView = {
      id: this.id || '',
      testId: this.getAttribute?.('data-testid') || '',
      block: typeof options === 'object' ? options.block || '' : '',
    };
    return nativeScrollIntoView.call(this, options);
  };
})();
"""

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


def _launch_real_chrome(playwright: Playwright) -> Browser:
    """Prefer installed Google Chrome; bundled Chromium requires explicit CI opt-in."""

    channel = os.getenv("SING_YIN_PLAYWRIGHT_CHANNEL", "chrome").strip() or "chrome"
    try:
        return playwright.chromium.launch(headless=True, channel=channel)
    except Error as exc:
        if os.getenv("SING_YIN_PLAYWRIGHT_ALLOW_BUNDLED_CHROMIUM") == "1":
            return playwright.chromium.launch(headless=True)
        raise RuntimeError(
            f"Mobile verification requires the Playwright {channel!r} browser channel. "
            "Install/repair Chrome, set SING_YIN_PLAYWRIGHT_CHANNEL to another installed "
            "Chrome channel, or explicitly allow bundled Chromium only in isolated CI with "
            "SING_YIN_PLAYWRIGHT_ALLOW_BUNDLED_CHROMIUM=1."
        ) from exc


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


def _collect_performance_evidence(page: Page, *, label: str) -> dict[str, Any]:
    """Collect honest navigation/render evidence without adding artificial delay."""

    page.wait_for_timeout(120)
    evidence = page.evaluate(
        """() => {
          const navigation = performance.getEntriesByType('navigation')[0];
          const resources = performance.getEntriesByType('resource');
          const paints = Object.fromEntries(
            performance.getEntriesByType('paint').map(entry => [entry.name, entry.startTime])
          );
          const observed = window.__syMobilePerformanceEvidence || {};
          return {
            ttfb: navigation ? navigation.responseStart - navigation.requestStart : null,
            domContentLoaded: navigation ? navigation.domContentLoadedEventEnd : null,
            loadEvent: navigation ? navigation.loadEventEnd : null,
            firstContentfulPaint: paints['first-contentful-paint'] || null,
            largestContentfulPaint: observed.largestContentfulPaint || null,
            cumulativeLayoutShift: observed.cumulativeLayoutShift || 0,
            longestTask: observed.longestTask || 0,
            longTaskCount: observed.longTaskCount || 0,
            resourceCount: resources.length,
            resourceBytes: resources.reduce(
              (total, entry) => total + (entry.transferSize || entry.encodedBodySize || 0),
              0
            ),
            motionState: document.documentElement.dataset.syMotion || '',
          };
        }"""
    )
    evidence["label"] = label
    for key in ("ttfb", "firstContentfulPaint", "largestContentfulPaint"):
        value = evidence[key]
        if value is not None and (not isinstance(value, (int, float)) or value < 0):
            raise AssertionError(f"{label} produced invalid performance timing {key}={value!r}.")
    if evidence["cumulativeLayoutShift"] > 0.15:
        raise AssertionError(f"{label} exceeds the mobile CLS contract: {evidence}")
    if evidence["longestTask"] > 1_000:
        raise AssertionError(f"{label} contains a blocking task longer than one second: {evidence}")
    if evidence["resourceBytes"] > 25 * 1024 * 1024:
        raise AssertionError(f"{label} transferred more than the 25 MiB safety ceiling: {evidence}")
    PERFORMANCE_EVIDENCE.append(evidence)
    return evidence


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


def _assert_text_reflow_contract(page: Page, *, label: str, root: str = "body") -> None:
    """Reject clipped labels and the single-glyph columns hidden by global wrapping."""

    failures = page.evaluate(
        r"""({rootSelector}) => {
          const root = document.querySelector(rootSelector);
          if (!root) return [{reason: 'missing-root', selector: rootSelector}];
          const candidates = [...root.querySelectorAll([
            'button', '[role="button"]', '[role="heading"]', '.q-item__label',
            '.sy-page-lead', '.sy-support-browser-field > span', 'p'
          ].join(','))];
          return candidates.flatMap((element) => {
            const style = getComputedStyle(element);
            const bounds = element.getBoundingClientRect();
            const text = (element.textContent || '').replace(/\s+/g, ' ').trim();
            if (
              !text || bounds.width <= 0 || bounds.height <= 0 ||
              style.display === 'none' || style.visibility === 'hidden' ||
              element.closest('[aria-hidden="true"],[inert]')
            ) return [];
            const fontSize = Number.parseFloat(style.fontSize) || 16;
            const lineHeight = Number.parseFloat(style.lineHeight) || fontSize * 1.25;
            const estimatedLines = Math.max(1, Math.round(bounds.height / lineHeight));
            const clipped = element.scrollWidth > element.clientWidth + 2 ||
              element.scrollHeight > element.clientHeight + 2;
            const glyphColumn = text.length >= 4 && bounds.width < fontSize * 2.2 && estimatedLines >= 4;
            if (!clipped && !glyphColumn) return [];
            return [{
              reason: clipped ? 'clipped' : 'single-glyph-column',
              tag: element.tagName.toLowerCase(),
              testId: element.getAttribute('data-testid') || '',
              text: text.slice(0, 80),
              width: Math.round(bounds.width * 10) / 10,
              height: Math.round(bounds.height * 10) / 10,
              estimatedLines,
            }];
          }).slice(0, 10);
        }""",
        {"rootSelector": root},
    )
    if failures:
        raise AssertionError(f"{label} clips text or collapses it into a glyph column: {failures}")


def _assert_no_interactive_overlap(page: Page, *, label: str, root: str) -> None:
    failures = page.evaluate(
        r"""({rootSelector}) => {
          const root = document.querySelector(rootSelector);
          if (!root) return [{reason: 'missing-root'}];
          const visible = [...root.querySelectorAll('button, a[href]')].filter(element => {
            const style = getComputedStyle(element);
            const box = element.getBoundingClientRect();
            return style.display !== 'none' && style.visibility !== 'hidden' && box.width > 0 && box.height > 0;
          });
          const overlaps = [];
          for (let i = 0; i < visible.length; i += 1) {
            const a = visible[i].getBoundingClientRect();
            for (let j = i + 1; j < visible.length; j += 1) {
              const b = visible[j].getBoundingClientRect();
              const width = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
              const height = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
              if (width * height <= 4) continue;
              if (visible[i].contains(visible[j]) || visible[j].contains(visible[i])) continue;
              overlaps.push({
                first: visible[i].getAttribute('data-testid') || visible[i].textContent?.trim().slice(0, 32),
                second: visible[j].getAttribute('data-testid') || visible[j].textContent?.trim().slice(0, 32),
                area: Math.round(width * height),
              });
            }
          }
          return overlaps.slice(0, 8);
        }""",
        {"rootSelector": root},
    )
    if failures:
        raise AssertionError(f"{label} has overlapping interactive controls: {failures}")


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
    _assert_text_reflow_contract(page, label=label)
    _assert_shell_not_obscured(page, label=label)
    _collect_performance_evidence(page, label=label)


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


def _assert_drawer_quick_settings_contract(page: Page, *, label: str) -> None:
    """Catch the circular/vertical quick-setting regression seen on real phones."""

    drawer = _open_mobile_drawer(page)
    tools = drawer.get_by_test_id("mobile-drawer-tools")
    tools.wait_for(state="visible", timeout=5_000)
    metrics = tools.evaluate(
        r"""(root) => {
          const hiddenByAncestor = element => {
            for (let current = element; current instanceof Element; current = current.parentElement) {
              const style = getComputedStyle(current);
              if (current.inert || current.getAttribute('aria-hidden') === 'true' ||
                  style.display === 'none' || style.visibility === 'hidden' ||
                  Number(style.opacity || 1) === 0) return true;
            }
            return false;
          };
          const visible = element => {
            const style = getComputedStyle(element);
            const box = element.getBoundingClientRect();
            return !hiddenByAncestor(element) && style.display !== 'none' && style.visibility !== 'hidden' &&
              Number(style.opacity || 1) > 0 && box.width > 0 && box.height > 0;
          };
          const exposed = element => visible(element) && (
            typeof element.checkVisibility !== 'function' ||
            element.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})
          );
          const lineCount = element => {
            if (!element) return 0;
            const range = document.createRange();
            range.selectNodeContents(element);
            const tops = [...range.getClientRects()]
              .filter(rect => rect.width > 0 && rect.height > 0)
              .map(rect => Math.round(rect.top * 2) / 2);
            return new Set(tops).size;
          };
          const tiles = [...root.querySelectorAll('.sy-mobile-setting-tile')]
            .filter(visible)
            .map(tile => {
              const box = tile.getBoundingClientRect();
              const style = getComputedStyle(tile);
              const radius = Number.parseFloat(style.borderTopLeftRadius) || 0;
              const copy = tile.querySelector('.sy-mobile-setting-tile-copy');
              const title = tile.querySelector('.sy-mobile-setting-tile-title');
              const value = tile.querySelector('.sy-mobile-setting-tile-value');
              return {
                testId: tile.getAttribute('data-testid') || '',
                width: box.width,
                height: box.height,
                borderRadius: style.borderRadius,
                effectiveRadius: radius,
                copyWidth: copy?.getBoundingClientRect().width || 0,
                titleLines: lineCount(title),
                valueLines: lineCount(value),
                text: (copy?.textContent || '').replace(/\s+/g, ' ').trim(),
              };
            });
          const exposedCloseControls = [...document.querySelectorAll(
            '[aria-controls="main-navigation-drawer"]'
          )].filter(exposed).filter(control => {
            const glyph = control.querySelector('.q-icon')?.textContent?.trim();
            return glyph === 'close';
          }).map(control => control.getAttribute('data-testid') || 'unnamed');
          return {tiles, exposedCloseControls};
        }"""
    )
    tiles = metrics["tiles"]
    if len(tiles) < 3:
        raise AssertionError(f"{label} exposes fewer than three quick-setting tiles: {metrics}")
    failures = [
        tile
        for tile in tiles
        if tile["width"] < 44
        or tile["height"] < 44
        or tile["copyWidth"] < 56
        or tile["titleLines"] > 2
        or tile["valueLines"] > 2
        or "%" in tile["borderRadius"]
        or (
            tile["width"] > tile["height"] * 1.25
            and tile["effectiveRadius"] >= min(tile["width"], tile["height"]) * 0.45
        )
    ]
    if failures:
        raise AssertionError(
            f"{label} quick settings became circular, clipped, or vertically stacked: {failures}"
        )
    if len(metrics["exposedCloseControls"]) != 1:
        raise AssertionError(
            f"{label} must expose one unambiguous drawer close action, not duplicate bottom X controls: "
            f"{metrics['exposedCloseControls']}"
        )
    _assert_no_interactive_overlap(page, label=f"{label} quick settings", root=".sy-mobile-drawer-tools")

    theme = drawer.get_by_test_id("mobile-theme-control")
    for _ in range(8):
        if theme.evaluate("element => document.activeElement === element"):
            break
        page.keyboard.press("Tab")
    else:
        raise AssertionError(f"{label} cannot reach the theme setting by keyboard.")
    focus_style = theme.evaluate(
        """element => ({
          focusVisible: element.matches(':focus-visible'),
          outlineWidth: Number.parseFloat(getComputedStyle(element).outlineWidth) || 0,
          boxShadow: getComputedStyle(element).boxShadow,
        })"""
    )
    if not focus_style["focusVisible"] or (
        focus_style["outlineWidth"] < 2 and focus_style["boxShadow"] in {"", "none"}
    ):
        raise AssertionError(f"{label} keyboard focus is not visibly distinguishable: {focus_style}")
    page.evaluate("document.activeElement?.blur()")
    theme.tap()
    if theme.evaluate("element => element.matches(':focus-visible')"):
        raise AssertionError(f"{label} leaves a keyboard-style focus halo after a touch tap.")

    drawer.get_by_test_id("mobile-drawer-close").click()
    drawer.wait_for(state="hidden", timeout=5_000)


def _assert_drawer_cleanup_cycles(page: Page, *, label: str, cycles: int = 20) -> None:
    """Repeated open/close cycles must not accumulate overlays or route listeners."""

    more = page.get_by_test_id("mobile-more")
    for cycle in range(cycles):
        drawer = _open_mobile_drawer(page)
        if cycle % 2:
            page.keyboard.press("Escape")
        else:
            drawer.get_by_test_id("mobile-drawer-close").click()
        drawer.wait_for(state="hidden", timeout=5_000)
        page.wait_for_function(
            """() => {
              const more = document.querySelector('[data-testid="mobile-more"]');
              return more?.getAttribute('aria-expanded') === 'false' && document.activeElement === more;
            }""",
            timeout=5_000,
        )
        state = page.evaluate(
            """() => ({
              drawers: document.querySelectorAll('#main-navigation-drawer').length,
              moreButtons: document.querySelectorAll('[data-testid="mobile-more"]').length,
              closeButtons: document.querySelectorAll('[data-testid="mobile-drawer-close"]').length,
              tabbars: document.querySelectorAll('[data-testid="mobile-bottom-navigation"]').length,
              backdrops: document.querySelectorAll('.q-drawer__backdrop').length,
              pointerLights: document.querySelectorAll('.sy-pointer-light,[data-sy-pointer-ready]').length,
              icon: document.querySelector('[data-testid="mobile-more"] .q-icon')?.textContent?.trim(),
            })"""
        )
        if state["drawers"] != 1 or state["moreButtons"] != 1 or state["closeButtons"] != 1:
            raise AssertionError(f"{label} leaked drawer controls after cycle {cycle + 1}: {state}")
        if state["tabbars"] != 1 or state["backdrops"] > 1 or state["pointerLights"] > 1:
            raise AssertionError(f"{label} leaked overlays/listeners after cycle {cycle + 1}: {state}")
        if state["icon"] != "menu":
            raise AssertionError(f"{label} retained the close glyph after cycle {cycle + 1}: {state}")


def _assert_support_keyboard_visibility(page: Page, *, label: str) -> None:
    """Use a deterministic VisualViewport test double to exercise phone-keyboard state."""

    _assert_mobile_page(page, "/support", label=label)
    field = page.locator("main#main-content textarea:visible").first
    field.wait_for(state="visible", timeout=10_000)
    field.focus()
    page.evaluate("window.__sySetTestVisualViewport({height: window.innerHeight - 280})")
    page.wait_for_function("document.documentElement.classList.contains('sy-mobile-keyboard-open')")
    state = page.evaluate(
        """() => {
          const tabbar = document.querySelector('[data-testid="mobile-bottom-navigation"]');
          return {
            inert: tabbar?.inert === true,
            hidden: tabbar?.getAttribute('aria-hidden'),
            scroll: window.__syLastScrollIntoView || null,
            activeTag: document.activeElement?.tagName,
          };
        }"""
    )
    if not state["inert"] or state["hidden"] != "true" or state["activeTag"] != "TEXTAREA":
        raise AssertionError(f"{label} keyboard state obscures or deactivates the focused field: {state}")
    page.wait_for_timeout(220)
    scroll = page.evaluate("window.__syLastScrollIntoView || null")
    if not scroll or scroll.get("block") != "center":
        raise AssertionError(f"{label} did not reveal the focused field above the phone keyboard: {scroll}")
    page.evaluate("window.__sySetTestVisualViewport({height: window.innerHeight})")
    field.blur()
    page.wait_for_function("!document.documentElement.classList.contains('sy-mobile-keyboard-open')")
    restored = page.evaluate(
        """() => {
          const tabbar = document.querySelector('[data-testid="mobile-bottom-navigation"]');
          return {inert: tabbar?.inert === true, hidden: tabbar?.getAttribute('aria-hidden')};
        }"""
    )
    if restored["inert"] or restored["hidden"] == "true":
        raise AssertionError(f"{label} did not restore navigation after keyboard dismissal: {restored}")


def _assert_200_percent_text_reflow(page: Page, *, route: str, label: str) -> None:
    response = page.goto(f"{BASE_URL}{route}", wait_until="domcontentloaded")
    if response is None or response.status != 200:
        raise AssertionError(f"{label} returned an unexpected response: {response}")
    page.add_style_tag(content="html { font-size: 200% !important; }")
    page.locator("main#main-content").wait_for(state="visible", timeout=10_000)
    page.evaluate(
        """async () => {
          if (document.fonts?.ready) await document.fonts.ready;
          await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        }"""
    )
    _assert_no_horizontal_overflow(page, label=label)
    _assert_text_reflow_contract(page, label=label)
    _assert_touch_targets(page, label=label)


def _assert_forced_colours(page: Page, *, label: str) -> None:
    _assert_mobile_page(page, "/", label=label)
    if not page.evaluate("matchMedia('(forced-colors: active)').matches"):
        raise AssertionError(f"{label} did not enter forced-colours mode.")
    drawer = _open_mobile_drawer(page)
    current = drawer.locator('[aria-current="page"]')
    for _ in range(40):
        if current.first.evaluate("element => document.activeElement === element"):
            break
        page.keyboard.press("Tab")
    else:
        raise AssertionError(f"{label} cannot reach the current route by keyboard.")
    state = current.first.evaluate(
        """element => ({
          focusVisible: element.matches(':focus-visible'),
          outlineWidth: Number.parseFloat(getComputedStyle(element).outlineWidth) || 0,
          borderWidth: Number.parseFloat(getComputedStyle(element).borderWidth) || 0,
        })"""
    )
    if not state["focusVisible"] or max(state["outlineWidth"], state["borderWidth"]) < 1:
        raise AssertionError(f"{label} loses current/focus affordance in forced colours: {state}")
    page.keyboard.press("Escape")
    drawer.wait_for(state="hidden", timeout=5_000)


def _assert_gsap_failure_static_end_state(
    browser: Browser,
    *,
    console_errors: list[str],
    page_errors: list[str],
) -> None:
    """If the optional motion asset fails, readable content must render immediately."""

    page, context = _new_mobile_page(
        browser,
        width=390,
        height=844,
        label="mobile-gsap-unavailable",
        console_errors=console_errors,
        page_errors=page_errors,
        collect_console_errors=False,
    )
    page.route("**/assets/vendor/gsap-3.13.0.min.js", lambda route: route.abort())
    response = page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
    if response is None or response.status != 200:
        raise AssertionError(f"GSAP failure path returned an unexpected response: {response}")
    page.locator("main#main-content").wait_for(state="visible", timeout=10_000)
    page.wait_for_function(
        "document.documentElement.dataset.syMotion === 'unavailable'",
        timeout=6_000,
    )
    hidden = page.evaluate(
        """() => [...document.querySelectorAll(
          'main#main-content h1, main#main-content h2, main#main-content p, main#main-content a, main#main-content button'
        )].filter(element => {
          const box = element.getBoundingClientRect();
          const style = getComputedStyle(element);
          return box.width > 0 && box.height > 0 &&
            (Number.parseFloat(style.opacity) <= 0.01 || style.visibility === 'hidden');
        }).slice(0, 8).map(element => ({tag: element.tagName, text: element.textContent?.trim().slice(0, 60)}))"""
    )
    if hidden:
        raise AssertionError(f"GSAP failure leaves readable content hidden: {hidden}")
    context.close()


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
    """The drawer owns one close glyph; the bottom More action must not duplicate it."""

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
          const drawerClose = document.querySelector('[data-testid="mobile-drawer-close"] .q-icon');
          const tabbar = document.querySelector('[data-testid="mobile-bottom-navigation"]');
          const tabbarStyle = tabbar ? getComputedStyle(tabbar) : null;
          return host?.getAttribute('aria-expanded') === 'true' &&
            drawerClose?.textContent?.trim() === 'close' &&
            document.documentElement.classList.contains('sy-mobile-drawer-open') &&
            tabbar?.inert === true && tabbar?.getAttribute('aria-hidden') === 'true' &&
            tabbarStyle?.opacity === '0' && tabbarStyle?.pointerEvents === 'none';
        }""",
        timeout=3_000,
    )
    open_state = page.evaluate(
        """() => {
          const bottom = document.querySelector('[data-testid="mobile-more"]');
          const bottomBar = bottom?.closest('[data-testid="mobile-bottom-navigation"]');
          const bottomBarStyle = bottomBar ? getComputedStyle(bottomBar) : null;
          return {
          bottomGlyph: bottom?.querySelector('.q-icon')?.textContent?.trim(),
          bottomExposed: Boolean(bottom && bottomBar && !bottomBar.inert &&
            bottomBar.getAttribute('aria-hidden') !== 'true' &&
            bottomBarStyle?.display !== 'none' && bottomBarStyle?.visibility !== 'hidden' &&
            Number(bottomBarStyle?.opacity || 1) > 0),
          closeCount: [...document.querySelectorAll('[aria-controls="main-navigation-drawer"] .q-icon')]
            .filter(icon => icon.textContent?.trim() === 'close')
            .filter(icon => {
              const button = icon.closest('button');
              if (button?.closest('[aria-hidden="true"], [inert]')) return false;
              const box = button?.getBoundingClientRect();
              const style = button ? getComputedStyle(button) : null;
              return box && style && box.width > 0 && box.height > 0 &&
                style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity || 1) > 0 &&
                (typeof button.checkVisibility !== 'function' || button.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}));
            }).length,
          };
        }"""
    )
    if (
        open_state["bottomExposed"] and open_state["bottomGlyph"] == "close"
    ) or open_state["closeCount"] != 1:
        raise AssertionError(f"{label} exposes duplicate close glyphs while the drawer is open: {open_state}")
    page.get_by_test_id("mobile-drawer-close").click()
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
    more.click()
    page.locator("#main-navigation-drawer").wait_for(state="visible", timeout=3_000)
    page.keyboard.press("Escape")
    page.wait_for_function(
        """() => {
          const host = document.querySelector('[data-testid="mobile-more"]');
          const drawer = document.querySelector('#main-navigation-drawer');
          const hidden = !drawer || drawer.getAttribute('aria-hidden') === 'true' ||
            !drawer.checkVisibility?.({checkOpacity: true, checkVisibilityCSS: true});
          return hidden && host?.getAttribute('aria-expanded') === 'false' &&
            document.activeElement === host;
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
    forced_colors: str = "none",
    fake_visual_viewport: bool = False,
    collect_console_errors: bool = True,
    collect_page_errors: bool = True,
) -> tuple[Page, BrowserContext]:
    context = browser.new_context(
        viewport={"width": width, "height": height},
        is_mobile=True,
        has_touch=True,
        device_scale_factor=2,
        reduced_motion=reduced_motion,  # type: ignore[arg-type]
        forced_colors=forced_colors,  # type: ignore[arg-type]
    )
    context.add_init_script(PERFORMANCE_OBSERVER_SCRIPT)
    if fake_visual_viewport:
        context.add_init_script(VISUAL_VIEWPORT_TEST_DOUBLE)
    page = context.new_page()
    if collect_console_errors:
        page.on(
            "console",
            lambda message: console_errors.append(f"{label}: {message.text}")
            if message.type == "error"
            else None,
        )
    if collect_page_errors:
        page.on("pageerror", lambda error: page_errors.append(f"{label}: {error}"))
    return page, context


def main() -> int:
    isolated_paths()
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = _launch_real_chrome(playwright)

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
        _assert_mobile_page(portrait_page, "/", label="390px quick-settings origin")
        _assert_drawer_quick_settings_contract(portrait_page, label="390px drawer")
        _assert_drawer_cleanup_cycles(portrait_page, label="390px drawer", cycles=20)
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
        compact_tools = compact_drawer.get_by_test_id("mobile-drawer-tools").locator(
            ".sy-mobile-setting-tile"
        )
        required_tool_ids = (
            "mobile-language-control",
            "mobile-sound-control",
            "mobile-theme-control",
        )
        if any(compact_drawer.get_by_test_id(test_id).count() != 1 for test_id in required_tool_ids):
            raise AssertionError("320px drawer does not expose language, sound, and appearance controls.")
        account_tool_count = compact_drawer.get_by_test_id("mobile-administrator-logout").count()
        if compact_tools.count() != 3 + account_tool_count or account_tool_count not in {0, 1}:
            raise AssertionError("320px drawer exposes an unexpected quick-setting control set.")
        if compact_drawer.get_by_test_id("mobile-theme-control").count() != 1:
            raise AssertionError("320px drawer does not expose the binary appearance control.")
        compact_drawer.get_by_test_id("mobile-language-control").click()
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

        for width, height, viewport_label in PHONE_SMOKE_VIEWPORTS:
            phone_page, phone = _new_mobile_page(
                browser,
                width=width,
                height=height,
                label=viewport_label,
                console_errors=console_errors,
                page_errors=page_errors,
                forced_colors="active" if width == 412 else "none",
            )
            if width == 412:
                _assert_forced_colours(phone_page, label=f"{viewport_label} forced colours")
            else:
                for route in ("/", "/rosters", "/support"):
                    _assert_mobile_page(phone_page, route, label=f"{viewport_label} {route}")
            phone.close()

        zoom_page, zoom = _new_mobile_page(
            browser,
            width=360,
            height=800,
            label="mobile-360-text-200",
            console_errors=console_errors,
            page_errors=page_errors,
        )
        for route in ("/", "/rosters", "/support"):
            _assert_200_percent_text_reflow(
                zoom_page,
                route=route,
                label=f"360px 200% text {route}",
            )
        zoom.close()

        keyboard_page, keyboard = _new_mobile_page(
            browser,
            width=390,
            height=844,
            label="mobile-390-support-keyboard",
            console_errors=console_errors,
            page_errors=page_errors,
            fake_visual_viewport=True,
        )
        _assert_support_keyboard_visibility(
            keyboard_page,
            label="390px Support visual-keyboard proxy",
        )
        keyboard.close()

        _assert_gsap_failure_static_end_state(
            browser,
            console_errors=console_errors,
            page_errors=page_errors,
        )
        browser.close()

    if console_errors or page_errors:
        details = "\n".join([*console_errors, *page_errors])
        raise RuntimeError(
            f"Mobile browser errors: console={len(console_errors)} page={len(page_errors)}\n{details}"
        )
    PERFORMANCE_EVIDENCE_PATH.write_text(
        json.dumps(PERFORMANCE_EVIDENCE, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        "Mobile browser verification passed in a real Chrome channel: 320/360/390/412/430px phones, "
        "forced colours, 200% text, deterministic keyboard-state proxy, 20 drawer cycles, optional-GSAP failure, "
        "768x1024 and 820x1180 adaptive touch tablets, "
        "1024x768 desktop-shell touch tablet, "
        "320px reduced-motion, 256px reflow, and 844x390 landscape contexts; "
        f"screenshots: {PORTRAIT_SCREENSHOT}, {TABLET_SCREENSHOT}, {TALL_TABLET_SCREENSHOT}, "
        f"{LANDSCAPE_TABLET_SCREENSHOT}, {COMPACT_SCREENSHOT}, "
        f"{REFLOW_SCREENSHOT}, {LANDSCAPE_SCREENSHOT}; performance: {PERFORMANCE_EVIDENCE_PATH}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
