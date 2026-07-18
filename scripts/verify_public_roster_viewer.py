"""Verify the live public viewer with an isolated fictional roster only."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Final

from playwright.sync_api import Page, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui_app.config import PROJECT_ROOT  # noqa: E402
from nicegui_app.config import PREFECT_SEED_PATH  # noqa: E402
from nicegui_app.services.public_roster_share import PublicRosterShareService, PublicRosterShareSettings
from nicegui_app.services.roster_workflow import RosterWorkflow


EVIDENCE_DIR = PROJECT_ROOT / "test-results" / "public-roster-viewer"
GATEWAY_EVIDENCE_DIR = PROJECT_ROOT / "test-results" / "unified-access-gateway"
THEME_STATES: Final = ("system", "light", "dark")


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
    return str(page.evaluate("() => document.documentElement.dataset.theme || 'system'"))


def _set_theme_reliably(page: Page, expected: str) -> None:
    """Cycle the public three-state control without relying on internal JS APIs."""

    if expected not in THEME_STATES:
        raise ValueError(f"Unsupported theme state: {expected}")
    for _ in THEME_STATES:
        current = _current_theme(page)
        if current == expected:
            page.wait_for_timeout(250)
            return
        page.locator("#themeToggle").click()
        page.wait_for_function(
            "previous => (document.documentElement.dataset.theme || 'system') !== previous",
            arg=current,
        )
    raise RuntimeError(f"Theme toggle did not reach {expected!r}.")


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

    login_link = page.locator('a[href="/auth/login"]')
    if login_link.count() != 1 or not login_link.is_visible():
        raise RuntimeError(f"{label} does not expose exactly one visible administrator login.")
    login_box = login_link.bounding_box()
    if login_box is None or login_box["height"] < 48:
        raise RuntimeError(f"{label} administrator CTA is shorter than 48 CSS pixels: {login_box}")

    guest_link = page.locator('a#guestEnter[href="/guest"]')
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
    _assert_document_fits_viewport(page, label=label)


def _assert_theme_cycle(page: Page) -> None:
    _set_theme_reliably(page, "system")
    for expected in ("light", "dark", "system"):
        _set_theme_reliably(page, expected)
        if _current_theme(page) != expected:
            raise RuntimeError(f"Appearance control failed to enter {expected!r} mode.")


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
    _assert_document_fits_viewport(page, label=label)


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
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)

            desktop = browser.new_context(
                viewport={"width": 1440, "height": 1000},
                color_scheme="light",
            )
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
            _assert_theme_cycle(page)

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

            mobile = browser.new_context(viewport={"width": 390, "height": 844}, color_scheme="light")
            mobile_page = mobile.new_page()
            _attach_error_collectors(
                mobile_page,
                label="mobile-390",
                console_errors=console_errors,
                page_errors=page_errors,
            )
            mobile_page.goto(settings.base_url, wait_until="networkidle")
            _assert_guest_landing(mobile_page, label="390px guest landing")
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

            compact = browser.new_context(
                viewport={"width": 320, "height": 760},
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
            browser.close()

        if console_errors or page_errors:
            details = "\n".join([*console_errors, *page_errors])
            raise RuntimeError(
                f"Browser errors: console={len(console_errors)} page={len(page_errors)}\n{details}"
            )

        service.revoke_share(receipt.share_id)
        receipt = None
        print(
            "PASS public gateway: entrance/read-only share flow, system/light/dark themes, "
            "manual verse refresh, 48px CTAs, reduced motion, no page overflow, and no "
            "browser errors. Unified Guest behavior is verified separately by "
            "scripts/verify_unified_guest_ui.py."
        )
        print(f"Gateway evidence: {GATEWAY_EVIDENCE_DIR}")
        print(f"Viewer evidence: {EVIDENCE_DIR}")
        return 0
    finally:
        if receipt is not None and workflow is not None and service is not None:
            try:
                service.revoke_share(receipt.share_id)
            except Exception:
                pass
        shutil.rmtree(temporary_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
