"""Source-bound D1 diagnostics, not the full route matrix or a release gate."""
from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "packages/roster_policy"), str(ROOT / "packages/roster_core")]

from playwright.sync_api import expect, sync_playwright
from scripts import verify_nicegui_mobile as mobile
from scripts.verify_export_workspace_integration import (
    _capture_runtime_footprint, _assert_runtime_growth_budget,
    RUNTIME_HEAP_GROWTH_BUDGET_BYTES, RUNTIME_DOM_GROWTH_BUDGET, RUNTIME_LISTENER_GROWTH_BUDGET,
)
from scripts.verify_rc31_theme_controls import _safe_environment
from scripts.verify_release_candidate import _source_state, _start_server, _stop_server, _wait_until_ready
from scripts.verify_unified_guest_ui import _install_gateway_stubs


def _ready(page):
    expect(page.locator("main#main-content")).to_be_visible(timeout=20_000)
    page.wait_for_function("document.querySelector('[data-testid=mobile-more]')?.dataset.syDrawerA11y === 'ready'")


def _record_growth(baseline, after, *, mode, results, persist):
    # Persist both raw endpoints BEFORE the fail-closed assertion can raise.
    results.append({"scenario": "cycle-final", "mode": mode, "cycles": 20,
                    "baseline": dict(baseline), "after": dict(after),
                    "limits": {"heapBytes": RUNTIME_HEAP_GROWTH_BUDGET_BYTES,
                               "domNodes": RUNTIME_DOM_GROWTH_BUDGET,
                               "listeners": RUNTIME_LISTENER_GROWTH_BUDGET}})
    persist()
    results.append(_assert_runtime_growth_budget(baseline, after, label=mode, cycles=20))
    persist()


def _collapse(page, preferences):
    header = preferences.locator(":scope > .q-expansion-item__container > .q-item")
    preferences.get_by_test_id("mobile-theme-control").focus()
    # Invoke Quasar's real hide method while focus is still inside the content;
    # clicking the header would move focus first and fail to test before-hide.
    preferences.evaluate("element => runMethod(Number(element.id.slice(1)), 'hide', [])")
    expect(header).to_have_attribute("aria-expanded", "false")
    expect(header).to_be_focused()


def _check_case(page, base_url, *, mode, results, persist):
    expected_controls = 4 if mode == "guest" else 3
    page.goto(base_url, wait_until="domcontentloaded")
    _ready(page)
    controls = page.locator(".sy-mobile-setting-tile")
    expect(controls).to_have_count(0)
    if mode == "guest":
        expect(page.get_by_test_id("guest-mode-banner")).to_have_count(1)
    session = page.context.new_cdp_session(page)
    baseline = _capture_runtime_footprint(page, session, label=mode)
    results.append({"scenario": "cold-page", "mode": mode, "controls": 0, "footprint": baseline})
    persist()
    for cycle in range(20):
        drawer = mobile._open_mobile_drawer(page)
        if cycle == 0:
            expect(controls).to_have_count(0)
            assert drawer.evaluate("""element => {
                const tools = element.querySelector('[data-testid=mobile-drawer-tools]');
                return [...element.querySelectorAll('.sy-nav-control')].every(link =>
                    Boolean(link.compareDocumentPosition(tools) & Node.DOCUMENT_POSITION_FOLLOWING));
            }"""), "All navigation must precede preferences"
            results.append({"scenario": "cold-drawer", "mode": mode, "controls": 0})
            persist()
        preferences = mobile._expand_mobile_preferences(page)
        expect(controls).to_have_count(expected_controls)
        if cycle == 0:
            page.evaluate("window.__d1Controls = [...document.querySelectorAll('.sy-mobile-setting-tile')]")
        assert page.evaluate("""[...document.querySelectorAll('.sy-mobile-setting-tile')]
            .every((node,index)=>node === window.__d1Controls[index])"""), "Controls were rebuilt"
        _collapse(page, preferences)
        expect(controls).to_have_count(expected_controls)
        page.keyboard.press("Escape")
        expect(drawer).to_be_hidden()
        expect(page.get_by_test_id("mobile-more")).to_be_focused()
        if cycle in {0, 9, 19}:
            sample = _capture_runtime_footprint(page, session, label=mode)
            results.append({"scenario": "cycle", "mode": mode, "cycle": cycle + 1, "footprint": sample})
            persist()
    after = _capture_runtime_footprint(page, session, label=mode)
    _record_growth(baseline, after, mode=mode, results=results, persist=persist)
    session.detach()
    persist()

    # Separate unmeasured reload: desktop choice first, late mobile control next.
    page.set_viewport_size({"width": 1440, "height": 960})
    page.reload(wait_until="domcontentloaded")
    _ready(page)
    expect(controls).to_have_count(0)
    header_theme = page.get_by_test_id("theme-control")
    old = page.evaluate("window.__syThemeControls.resolved()")
    target = "light" if old == "dark" else "dark"
    header_theme.click()
    expect(header_theme).to_have_attribute("data-theme-resolved", target)
    page.set_viewport_size({"width": 390, "height": 844})
    expect(page.get_by_test_id("mobile-more")).to_have_attribute("aria-expanded", "false")
    mobile._open_mobile_drawer(page)
    expect(controls).to_have_count(0)
    preferences = mobile._expand_mobile_preferences(page)
    theme = page.get_by_test_id("mobile-theme-control")
    expect(theme).to_have_attribute("data-theme-preference", target)
    expect(theme).to_have_attribute("data-theme-resolved", target)
    for _ in range(2):
        target = "light" if target == "dark" else "dark"
        theme.click()
        expect(theme).to_have_attribute("data-theme-resolved", target)
        expect(header_theme).to_have_attribute("data-theme-resolved", target)
        expect(theme.locator("[data-sy-theme-state]")).not_to_have_text("")
    sound = page.get_by_test_id("mobile-sound-control")
    prior = sound.get_attribute("aria-pressed")
    sound.click()
    expect(sound).to_have_attribute("aria-pressed", "false" if prior == "true" else "true")
    sound.click()
    expect(sound).to_have_attribute("aria-pressed", prior)
    results.append({"scenario": "late-theme-and-sound", "mode": mode, "status": "pass"})
    persist()

    for width, height in [(256, 760), (320, 760), (390, 844), (844, 390)]:
        page.set_viewport_size({"width": width, "height": height})
        overflow = page.evaluate("Math.max(0, document.documentElement.scrollWidth-document.documentElement.clientWidth)")
        assert overflow == 0, f"D1 horizontal overflow at {width}"
        for index in range(expected_controls):
            size = controls.nth(index).bounding_box()
            assert size and size["width"] >= 44 and size["height"] >= 44
        results.append({"scenario": "reflow", "mode": mode, "width": width, "height": height, "overflow": overflow})
    page.set_viewport_size({"width": 390, "height": 844})
    with page.expect_navigation(wait_until="domcontentloaded"):
        page.get_by_test_id("mobile-language-control").click()
    _ready(page)
    expect(controls).to_have_count(0)
    mobile._open_mobile_drawer(page)
    mobile._expand_mobile_preferences(page)
    expect(page.get_by_test_id("mobile-language-control")).to_contain_text("English")
    page.set_viewport_size({"width": 320, "height": 760})
    assert page.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth") == 0
    results.append({"scenario": "language-reload-lazy", "mode": mode, "status": "pass"})
    persist()
    if mode == "guest":
        with page.expect_navigation(wait_until="domcontentloaded"):
            with page.expect_request(lambda request: request.url.endswith("/auth/logout") and request.method == "POST"):
                page.get_by_test_id("mobile-administrator-logout").click()
        expect(page).to_have_url(base_url + "/")
        results.append({"scenario": "guest-exit-gateway-stub", "mode": mode, "status": "pass"})
        persist()


def main():
    scratch = Path(tempfile.mkdtemp(prefix="sy-mobile-preferences-"))
    source = _source_state(refresh_fingerprint=True)
    assert not source["sourceDirty"], "A clean checkpoint is required"
    results, errors = [], []
    metadata = {**source, "evidenceKind": "functional-diagnostic", "formalReleaseExecuted": False,
                "controlledPerformance": False, "routeMatrixExecuted": False,
                "playwrightVersion": importlib.metadata.version("playwright"), "contexts": []}

    def persist():
        (scratch / "raw-samples.json").write_text(json.dumps({**metadata, "results": results}, indent=2), encoding="utf-8")

    print(f"ISOLATED {scratch}", flush=True)
    try:
        with sync_playwright() as playwright:
            browser = mobile._launch_real_chrome(playwright)
            metadata["browserVersion"] = browser.version
            try:
                for mode in ("local_maintenance", "guest"):
                    case = scratch / mode
                    case.mkdir()
                    environment = _safe_environment(case, access_mode="guest" if mode == "guest" else "admin")
                    environment["PYTHONPATH"] = os.pathsep.join(sys.path[:3])
                    os.environ.update(environment)
                    metadata["contexts"].append({"mode": "local-maintenance" if mode == "local_maintenance" else "isolated-guest",
                                                 "runId": environment["SING_YIN_E2E_RUN_ID"]})
                    from nicegui_app.services.guest_workspace import demo_fixture
                    from nicegui_app.services.roster_workflow import RosterWorkflow
                    seed = case / "fictional.json"
                    seed.write_text(json.dumps({"prefects": [dict(row, name=row["nameZh"], **{"class": row["className"]})
                        for row in demo_fixture()["prefects"]]}), encoding="utf-8")
                    RosterWorkflow(database_path=Path(environment["SING_YIN_DATABASE_PATH"]),
                                   backup_dir=Path(environment["SING_YIN_BACKUP_DIR"]), seed_path=seed).bootstrap()
                    process, output = _start_server(environment, case / "server.log")
                    try:
                        base_url = environment["SING_YIN_TEST_URL"].rstrip("/")
                        _wait_until_ready(process, base_url, case / "server.log")
                        page, context = mobile._new_mobile_page(browser, width=390, height=844,
                            label=mode, console_errors=errors, page_errors=errors,
                            reduced_motion="reduce" if mode == "guest" else "no-preference")
                        if mode == "guest":
                            _install_gateway_stubs(context)
                        try:
                            _check_case(page, base_url, mode=mode, results=results, persist=persist)
                        except Exception:
                            page.screenshot(path=str(case / "failure.png"), full_page=False)
                            raise
                        finally:
                            context.close()
                    finally:
                        _stop_server(process, output)
            finally:
                browser.close()
        assert not errors, "Unexpected browser errors"
        assert _source_state(refresh_fingerprint=True) == source, "Source changed during verification"
        (scratch / "report.json").write_text(json.dumps({**metadata, "status": "pass", "browserErrorCount": 0,
            "postVerificationSource": _source_state(refresh_fingerprint=True), "rawSamples": "raw-samples.json"}, indent=2), encoding="utf-8")
        print(f"PASS {scratch / 'report.json'}", flush=True)
    except Exception as error:
        (scratch / "failure.json").write_text(json.dumps({**metadata, "status": "fail", "errorType": type(error).__name__,
            "postVerificationSource": _source_state(refresh_fingerprint=True), "rawSamples": "raw-samples.json"}, indent=2), encoding="utf-8")
        raise
    finally:
        persist()


if __name__ == "__main__":
    main()
