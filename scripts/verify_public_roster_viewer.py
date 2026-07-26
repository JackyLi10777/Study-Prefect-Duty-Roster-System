"""Verify the live public viewer with an isolated fictional roster only."""

from __future__ import annotations

from datetime import date, timedelta
import json
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


def _assert_browser_only_support(
    page: Page,
    *,
    base_url: str,
    source: str,
    verify_download: bool,
) -> dict[str, object]:
    """Exercise the public/viewer report without any network persistence."""

    if source not in {"public", "viewer"}:
        raise ValueError(f"Unsupported support source: {source}")
    response = page.goto(f"{base_url.rstrip('/')}/support#{source}", wait_until="networkidle")
    if response is None or response.status != 200:
        raise RuntimeError(f"{source} support route did not return HTTP 200.")
    if response.headers.get("cache-control") != "no-store":
        raise RuntimeError(f"{source} support route is not protected by Cache-Control: no-store.")
    form = page.locator("#publicSupportForm")
    form.wait_for(state="visible")
    if page.locator(".support-details").get_attribute("open") is not None:
        raise RuntimeError(f"{source} support optional details were expanded by default.")
    page.locator("#supportBuild").click()
    if not page.locator("#supportResult").is_hidden():
        raise RuntimeError(f"{source} support accepted missing required fields.")

    resources_before = page.evaluate("() => performance.getEntriesByType('resource').length")
    page.locator("#supportExpected").fill("The shared fictional roster should remain readable.")
    page.locator("#supportActual").fill("The fictional roster displayed an unexpected empty state.")
    page.locator("#supportSteps").fill("Open the shared link.\nReview the fictional roster.")
    page.locator("#supportBuild").click()
    result = page.locator("#supportResult")
    result.wait_for(state="visible")
    incident_id = page.locator("#supportIncidentId").inner_text().strip()
    if not incident_id.startswith("FB-"):
        raise RuntimeError(f"{source} support did not create a browser incident reference.")
    expected_source = "public_viewer" if source == "viewer" else "public_entrance"
    if verify_download:
        with page.expect_download() as download_info:
            page.locator("#supportDownload").click()
        download = download_info.value
        payload = json.loads(Path(download.path()).read_text(encoding="utf-8"))
        if payload.get("source") != expected_source or payload.get("incident_id") != incident_id:
            raise RuntimeError(f"{source} support download does not identify its browser context.")

    page.wait_for_timeout(150)
    resources_after = page.evaluate("() => performance.getEntriesByType('resource').length")
    if resources_after != resources_before:
        raise RuntimeError(f"{source} support interaction created a network resource.")
    storage = page.evaluate(
        """async () => ({
          local: localStorage.length,
          session: sessionStorage.length,
          indexed: typeof indexedDB.databases === 'function' ? (await indexedDB.databases()).length : 0,
          caches: 'caches' in window ? (await caches.keys()).length : 0,
        })"""
    )
    if any(storage.values()):
        raise RuntimeError(f"{source} support created persistent browser storage: {storage}")

    page.reload(wait_until="networkidle")
    if page.locator("#supportExpected").input_value() or not page.locator("#supportResult").is_hidden():
        raise RuntimeError(f"{source} support state survived reload.")
    return {
        "source": expected_source,
        "incidentReference": incident_id,
        "browserOnly": True,
        "downloadVerified": verify_download,
        "clearedOnReload": True,
    }


def _assert_welcome_audio_blocked_recovery(page: Page, *, base_url: str) -> None:
    """Prove an honest fresh-profile NotAllowedError and one-action recovery."""

    page.goto(base_url, wait_until="networkidle")
    page.wait_for_function(
        "() => document.querySelector('#welcomeAudioPlayer')?.dataset.autoplayState === 'blocked'"
    )
    recovery = page.locator("#welcomeAudioRecovery")
    if not recovery.is_visible():
        raise RuntimeError("Blocked welcome audio does not expose the recovery choice.")
    if "direct action" not in recovery.inner_text().lower():
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
    page.locator('a[data-entry-role="guest"]:visible').click()
    recovery = page.locator("#welcomeAudioRecovery")
    recovery.wait_for(state="visible")
    page.locator("#welcomeAudioQuiet").click()
    page.wait_for_url("**/guest", wait_until="domcontentloaded")
    if page.url.rstrip("/").split("?")[0] != f"{base_url.rstrip('/')}/guest":
        raise RuntimeError(f"Quiet welcome-audio continuation reached an unexpected URL: {page.url}")


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


def _assert_theme_cycle(page: Page) -> None:
    _set_theme_reliably(page, "system")
    for expected in ("light", "dark", "system"):
        _set_theme_reliably(page, expected)
        if _current_theme(page) != expected:
            raise RuntimeError(f"Appearance control failed to enter {expected!r} mode.")
        if expected in {"light", "dark"}:
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
        support_evidence: list[dict[str, object]] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)

            support_context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                color_scheme="light",
                accept_downloads=True,
            )
            support_page = support_context.new_page()
            support_websockets: list[str] = []
            support_page.on("websocket", lambda socket: support_websockets.append(socket.url))
            _attach_error_collectors(
                support_page,
                label="public-support",
                console_errors=console_errors,
                page_errors=page_errors,
            )
            support_evidence.append(
                _assert_browser_only_support(
                    support_page,
                    base_url=settings.base_url,
                    source="public",
                    verify_download=True,
                )
            )
            support_page.screenshot(
                path=str(GATEWAY_EVIDENCE_DIR / "public-support-browser-only.png"),
                full_page=True,
            )
            support_evidence.append(
                _assert_browser_only_support(
                    support_page,
                    base_url=settings.base_url,
                    source="viewer",
                    verify_download=False,
                )
            )
            if support_websockets:
                raise RuntimeError(f"Browser-only support opened WebSockets: {support_websockets}")
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
            browser.close()

        if console_errors or page_errors:
            details = "\n".join([*console_errors, *page_errors])
            raise RuntimeError(
                f"Browser errors: console={len(console_errors)} page={len(page_errors)}\n{details}"
            )

        service.revoke_share(receipt.share_id)
        receipt = None
        print(
            "PASS public gateway: browser-only public/viewer support, entrance/read-only share flow, system/light/dark themes, "
            "manual verse refresh, resolved/blocked welcome-audio paths, one-action recovery, quiet continuation navigation, "
            "48px CTAs, reduced motion, no page overflow, and no browser errors. "
            "Unified Guest behavior is verified separately by "
            "scripts/verify_unified_guest_ui.py."
        )
        print(f"Gateway evidence: {GATEWAY_EVIDENCE_DIR}")
        print(f"Viewer evidence: {EVIDENCE_DIR}")
        print(f"Support evidence: {support_evidence}")
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
