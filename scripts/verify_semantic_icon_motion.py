"""Verify semantic icon morphs in disposable Admin and Guest browsers.

This focused gate never targets canonical school storage. Screenshots and all
mutable runtime files are written below one temporary evidence directory.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from typing import Any

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.verify_nicegui_ui import assert_rendered_icon_semantics
from scripts.verify_rc31_theme_controls import _new_context, _safe_environment
from scripts.verify_release_candidate import (
    _assert_server_console_clean,
    _start_server,
    _stop_server,
    _wait_until_ready,
)
from scripts.verify_unified_guest_ui import _open_route


class SemanticIconVerificationError(RuntimeError):
    """Raised when a browser-visible semantic icon contract is broken."""


ICON_SELECTOR = (
    ".q-icon.material-icons,"
    ".q-icon.material-icons-outlined,"
    ".q-icon.material-symbols-outlined,"
    ".q-icon.material-symbols-rounded"
)


def _visible(locator: Locator) -> Locator:
    for index in range(locator.count()):
        candidate = locator.nth(index)
        icons = candidate.locator(ICON_SELECTOR)
        if candidate.is_visible() and any(icons.nth(icon_index).is_visible() for icon_index in range(icons.count())):
            return candidate
    raise SemanticIconVerificationError("No visible semantic icon host was rendered.")


def _icon(host: Locator) -> Locator:
    icons = host.locator(ICON_SELECTOR)
    for index in range(icons.count()):
        icon = icons.nth(index)
        if icon.is_visible():
            return icon
    raise SemanticIconVerificationError("The semantic icon host had no visible glyph.")


def _visible_preview_host(page: Page) -> Locator:
    candidates = page.locator(
        '[data-sy-icon-story-category="preview"][data-sy-icon-story-to]'
    )
    try:
        return _visible(candidates)
    except SemanticIconVerificationError:
        mobile_more = page.get_by_test_id("mobile-more")
        if not mobile_more.is_visible():
            raise
        mobile_more.click()
        page.get_by_test_id("mobile-drawer-tools").wait_for(state="visible", timeout=5_000)
        return _visible(candidates)


def _assert_stable_box(before: dict[str, float] | None, after: dict[str, float] | None) -> None:
    if before is None or after is None:
        raise SemanticIconVerificationError("The icon host lost its measurable slot.")
    for key in ("x", "y", "width", "height"):
        if abs(before[key] - after[key]) >= 0.6:
            raise SemanticIconVerificationError(f"Icon host moved or resized on {key}: {before} -> {after}")


def _preview_contract(page: Page) -> dict[str, Any]:
    host = _visible_preview_host(page)
    icon = _icon(host)
    source = icon.inner_text().strip()
    destination = host.get_attribute("data-sy-icon-story-to") or ""
    before = host.bounding_box()

    host.hover()
    page.wait_for_timeout(220)
    if icon.inner_text().strip() != destination:
        raise SemanticIconVerificationError(
            f"Pointer preview did not morph {source!r} to {destination!r}."
        )
    page.mouse.move(1, 1)
    page.wait_for_timeout(220)
    if icon.inner_text().strip() != source:
        raise SemanticIconVerificationError("Pointer preview did not restore its source glyph.")
    host.focus()
    page.wait_for_timeout(220)
    if icon.inner_text().strip() != destination:
        raise SemanticIconVerificationError("Keyboard focus did not reveal the preview outcome.")
    host.evaluate("element => element.blur()")
    page.wait_for_timeout(320)
    if icon.inner_text().strip() != source:
        raise SemanticIconVerificationError("Preview did not restore its source glyph after focus left.")

    for _ in range(3):
        host.hover()
        page.mouse.move(1, 1)
    page.wait_for_timeout(220)
    if icon.inner_text().strip() != source:
        raise SemanticIconVerificationError("Rapid pointer reversal left a temporary glyph behind.")
    _assert_stable_box(before, host.bounding_box())
    return {"source": source, "destination": destination}


def _persistent_contract(page: Page) -> dict[str, Any]:
    host = page.get_by_test_id("sound-control")
    host.wait_for(state="visible", timeout=10_000)
    if host.get_attribute("data-sy-icon-story-category") != "persistent":
        raise SemanticIconVerificationError("Sound state was not classified as persistent.")
    icon = _icon(host)
    source = icon.inner_text().strip()
    destination = "volume_up" if source == "volume_off" else "volume_off"
    before = host.bounding_box()
    host.click()
    page.wait_for_timeout(600)
    if icon.inner_text().strip() != destination:
        raise SemanticIconVerificationError(
            f"Persistent control did not morph {source!r} to {destination!r}."
        )
    _assert_stable_box(before, host.bounding_box())
    return {"source": source, "destination": destination}


def _sound_default_contract(page: Page) -> None:
    host = page.get_by_test_id("sound-control")
    host.wait_for(state="visible", timeout=10_000)
    icon = _icon(host)
    if host.get_attribute("aria-pressed") != "true" or icon.inner_text().strip() != "volume_up":
        raise SemanticIconVerificationError(
            "An unset interaction-sound preference did not resolve to the enabled truthful state."
        )


def _gear_contract(page: Page) -> dict[str, Any]:
    hosts = page.locator(".q-btn,.q-tab,.q-item.q-item--clickable").filter(
        has=page.locator('.q-icon[data-sy-icon-motion="gear"]')
    )
    host = _visible(hosts)
    icon = _icon(host)
    before = host.bounding_box()
    resting_transform = icon.evaluate("element => getComputedStyle(element).transform")
    host.hover()
    page.wait_for_timeout(120)
    preview_transform = icon.evaluate("element => getComputedStyle(element).transform")
    if preview_transform == "none":
        raise SemanticIconVerificationError("The Settings gear did not show its bounded intent preview.")
    page.mouse.move(1, 1)
    page.wait_for_timeout(240)
    host.dispatch_event("pointerdown", {"pointerType": "mouse", "button": 0})
    page.wait_for_timeout(80)
    activation_transform = icon.evaluate("element => getComputedStyle(element).transform")
    if activation_transform in {"none", resting_transform}:
        raise SemanticIconVerificationError("The Settings gear activation did not expose an intermediate rotation state.")
    page.wait_for_timeout(340)
    for _ in range(3):
        host.dispatch_event("pointerdown", {"pointerType": "mouse", "button": 0})
        page.wait_for_timeout(35)
    page.wait_for_timeout(420)
    if icon.evaluate("element => getComputedStyle(element).transform") != resting_transform:
        raise SemanticIconVerificationError("Rapid Settings activation accumulated rotation state.")
    _assert_stable_box(before, host.bounding_box())
    return {
        "role": icon.get_attribute("data-sy-icon-motion"),
        "previewTransform": preview_transform,
        "activationTransform": activation_transform,
    }


def _lifecycle_contract(page: Page) -> dict[str, str]:
    hosts = page.locator(".q-btn,.q-tab,.q-item.q-item--clickable").filter(
        has=page.locator('.q-icon[data-sy-icon-story-category="lifecycle"]')
    )
    host = _visible(hosts)
    icon = _icon(host)
    source = icon.get_attribute("data-sy-icon-story-from") or icon.inner_text().strip()
    host.focus()
    page.evaluate(
        "() => window.dispatchEvent(new CustomEvent('sy:feedback', {detail: {kind: 'working'}}))"
    )
    page.wait_for_timeout(220)
    working = icon.inner_text().strip()
    if working != "hourglass_top":
        raise SemanticIconVerificationError(f"Lifecycle working glyph was {working!r}, not hourglass_top.")
    page.evaluate(
        "() => window.dispatchEvent(new CustomEvent('sy:feedback', {detail: {kind: 'success'}}))"
    )
    page.wait_for_timeout(220)
    success = icon.inner_text().strip()
    if success in {source, "hourglass_top"}:
        raise SemanticIconVerificationError("Lifecycle success did not reveal a distinct truthful result glyph.")
    page.wait_for_timeout(900)
    if icon.inner_text().strip() != source:
        raise SemanticIconVerificationError("Lifecycle result did not settle back to its source glyph.")
    host.evaluate("element => element.blur()")
    return {"source": source, "working": working, "success": success}


def _guard_contract(page: Page) -> None:
    host = _visible_preview_host(page)
    icon = _icon(host)
    source = icon.inner_text().strip()
    host.evaluate("element => element.setAttribute('aria-disabled', 'true')")
    page.wait_for_timeout(80)
    host.hover()
    page.wait_for_timeout(240)
    if icon.inner_text().strip() != source:
        raise SemanticIconVerificationError("A disabled icon exposed a temporary preview.")
    host.evaluate("element => element.removeAttribute('aria-disabled')")


def _touch_contract(page: Page) -> dict[str, str]:
    host = _visible_preview_host(page)
    icon = _icon(host)
    source = icon.inner_text().strip()
    destination = host.get_attribute("data-sy-icon-story-to") or ""
    host.evaluate(
        "element => element.dispatchEvent(new PointerEvent('pointerdown', "
        "{bubbles:true, pointerType:'touch'}))"
    )
    page.wait_for_timeout(120)
    if icon.inner_text().strip() != destination:
        raise SemanticIconVerificationError("Touch preview did not reveal the action outcome.")
    page.wait_for_timeout(700)
    restored = icon.inner_text().strip()
    if restored != source:
        raise SemanticIconVerificationError(
            "Touch preview did not restore its source glyph: "
            f"source={source!r}, destination={destination!r}, restored={restored!r}, "
            f"story_from={icon.get_attribute('data-sy-icon-story-from')!r}, "
            f"story_active={icon.get_attribute('data-sy-icon-story-active')!r}."
        )
    return {"source": source, "destination": destination}


def _reduced_motion_contract(page: Page) -> None:
    host = _visible_preview_host(page)
    icon = _icon(host)
    source = icon.inner_text().strip()
    host.hover()
    page.wait_for_timeout(240)
    if icon.inner_text().strip() != source:
        raise SemanticIconVerificationError("Reduced motion did not suppress temporary icon preview.")
    if icon.evaluate("element => getComputedStyle(element).transform") != "none":
        raise SemanticIconVerificationError("Reduced motion left an icon transform active.")


def _exercise_context(
    browser: Browser,
    evidence_root: Path,
    *,
    access_mode: str,
    viewport: tuple[int, int],
    colour_scheme: str,
    reduced_motion: bool = False,
    forced_colours: bool = False,
) -> dict[str, Any]:
    case = f"{access_mode}-{viewport[0]}-{colour_scheme}"
    case_root = evidence_root / "runtime" / case
    environment = _safe_environment(case_root, access_mode=access_mode)  # type: ignore[arg-type]
    server_log = case_root / "server-console.log"
    process, output = _start_server(environment, server_log)
    context: BrowserContext | None = None
    try:
        _wait_until_ready(process, environment["SING_YIN_TEST_URL"], server_log)
        viewport_mode = "mobile" if viewport[0] <= 390 else "desktop"
        context = _new_context(
            browser,
            access_mode=access_mode,  # type: ignore[arg-type]
            viewport_mode=viewport_mode,
            colour_scheme=colour_scheme,  # type: ignore[arg-type]
            accessibility_mode=(
                "forced-colours" if forced_colours else
                "reduced-motion" if reduced_motion else "standard"
            ),
        )
        context.set_default_timeout(20_000)
        page = context.new_page()
        page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
        browser_errors: list[str] = []
        page.on("console", lambda message: browser_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: browser_errors.append(str(error)))
        _open_route(page, environment["SING_YIN_TEST_URL"], "/")
        page.wait_for_function("() => Boolean(window.__syIconMotion)")
        rendered = assert_rendered_icon_semantics(page)
        result: dict[str, Any] = {"case": case, "rendered": rendered}

        if forced_colours:
            result["forcedColours"] = True
        elif reduced_motion:
            _reduced_motion_contract(page)
        elif viewport[0] <= 390:
            result["touch"] = _touch_contract(page)
        else:
            _sound_default_contract(page)
            result["preview"] = _preview_contract(page)
            result["gear"] = _gear_contract(page)
            result["lifecycle"] = _lifecycle_contract(page)
            result["persistent"] = _persistent_contract(page)
            _guard_contract(page)

        if viewport[0] == 1440:
            for index in range(20):
                route = "/platform" if index % 2 else "/"
                try:
                    _open_route(page, environment["SING_YIN_TEST_URL"], route)
                except PlaywrightTimeoutError:
                    # NiceGUI can replace the visible <main> once more while a
                    # reconnect settles. A single bounded retry distinguishes
                    # that transient replacement from a persistent route fault.
                    _open_route(page, environment["SING_YIN_TEST_URL"], route)
                page.wait_for_function("() => Boolean(window.__syIconMotion)")
            result["routeCycles"] = 20
            result["afterCycles"] = assert_rendered_icon_semantics(page)
            page.evaluate("() => document.activeElement instanceof HTMLElement && document.activeElement.blur()")
            page.mouse.move(0, 0)
            page.wait_for_timeout(400)
            stale = page.locator('[data-sy-icon-story-active="true"]').count()
            if stale:
                raise SemanticIconVerificationError(f"{stale} temporary icon stories survived route replacement.")

        shot = evidence_root / f"{case}.png"
        page.screenshot(path=str(shot), full_page=False)
        result["screenshot"] = str(shot)
        if browser_errors:
            raise SemanticIconVerificationError(f"{case} emitted browser errors: {browser_errors!r}")
        return result
    finally:
        if context is not None:
            context.close()
        _stop_server(process, output)
        _assert_server_console_clean(server_log)


def main() -> int:
    evidence_root = Path(tempfile.mkdtemp(prefix="sing-yin-semantic-icons-")).resolve()
    report: dict[str, Any] = {"schemaVersion": 1, "evidenceRoot": str(evidence_root), "cases": []}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            report["cases"].append(_exercise_context(
                browser, evidence_root, access_mode="admin", viewport=(1440, 960), colour_scheme="light"
            ))
            report["cases"].append(_exercise_context(
                browser, evidence_root, access_mode="guest", viewport=(390, 844), colour_scheme="dark"
            ))
            report["cases"].append(_exercise_context(
                browser, evidence_root, access_mode="admin", viewport=(768, 1024), colour_scheme="dark",
                forced_colours=True,
            ))
            report["cases"].append(_exercise_context(
                browser, evidence_root, access_mode="guest", viewport=(320, 780), colour_scheme="light",
                reduced_motion=True,
            ))
            browser.close()
        report["status"] = "pass"
        return_code = 0
    except BaseException as error:
        report.update({"status": "fail", "failureType": type(error).__name__, "failure": str(error)})
        return_code = 1
    report_path = evidence_root / "verification.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Semantic icon evidence: {report_path}")
    if return_code == 0:
        print("Semantic icon browser verification passed (4 contexts, 20 route cycles).")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
