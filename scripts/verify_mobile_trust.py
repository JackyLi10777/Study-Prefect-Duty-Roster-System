"""Source-bound D3b Trust diagnostics, not the complete mobile release gate."""
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
from scripts.verify_export_workspace_integration import _capture_runtime_footprint
from scripts.verify_mobile_access_support import _open, _close
from scripts.verify_mobile_preferences import _ready, _record_growth
from scripts.verify_rc31_theme_controls import _safe_environment
from scripts.verify_release_candidate import _source_state, _start_server, _stop_server, _wait_until_ready
from scripts.verify_unified_guest_ui import _install_gateway_stubs


def _header(panel):
    return panel.locator(":scope > .q-expansion-item__container > .q-item")


def _fit(page):
    for width, height in ((256, 760), (320, 760), (360, 800), (390, 844),
                          (430, 932), (844, 390), (768, 1024), (820, 1180)):
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(100)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Overflow at {width}"
    page.set_viewport_size({"width": 390, "height": 844})


SECTIONS = {
    "/platform": ("platform-summary-details", "platform-team-details",
        "platform-operating-map-details", "platform-capabilities-details",
        "platform-solutions-details", "platform-convictions-details",
        "platform-principles-details", "platform-resources-details", "platform-attribution-details"),
    "/engineering": ("engineering-facts-details", "engineering-coverage-details",
        "engineering-blueprint-details", "engineering-process-details", "engineering-pillars-details",
        "engineering-evolution-details", "engineering-resources-details"),
    "/system-architecture": ("architecture-flow-details", "architecture-layers-details",
        "architecture-evidence-details", "architecture-developer-details", "architecture-faq-details"),
}


def _check(page, base, case, mode, results, persist):
    requests = []
    page.on("request", lambda request: requests.append(request.url))
    for route, section_ids in SECTIONS.items():
        requests.clear()
        page.goto(base + route, wait_until="domcontentloaded")
        _ready(page)
        for panel_id in ("reading-contents", *section_ids):
            expect(_header(page.get_by_test_id(panel_id))).to_have_attribute("aria-expanded", "false")
            expect(page.get_by_test_id(panel_id + "-content").locator(":scope > *")).to_have_count(0)
        expect(page.get_by_test_id("co-creation-profile")).to_have_count(0)
        expect(page.get_by_test_id("engineering-evidence-type-filter")).to_have_count(0)
        expect(page.get_by_test_id("developer-health-command")).to_have_count(0)
        if route == "/platform":
            expect(page.get_by_test_id("platform-open-workspace")).to_be_visible()
            expect(page.get_by_test_id("platform-release-state")).to_have_count(0)
        if route == "/engineering":
            expect(page.get_by_test_id("engineering-release-state")).to_be_visible()
            expect(page.get_by_test_id("engineering-release-date")).to_be_visible()
            report_state = page.get_by_test_id("engineering-release-state").inner_text()
            report_date = page.get_by_test_id("engineering-release-date").inner_text()
        _fit(page)
        assert not any("li-chuangjie-" in url for url in requests), "Attribution fetched before first use"
        page.screenshot(path=str(case / (route[1:] + "-initial.png")))
        session = page.context.new_cdp_session(page)
        cold = _capture_runtime_footprint(page, session, label=route + "-cold")

        # Open every detail explicitly. This is not a cold-page readiness step.
        for panel_id in section_ids:
            panel = page.get_by_test_id(panel_id)
            _open(panel)
            expect(page.get_by_test_id(panel_id + "-content").locator(":scope > *").first).to_be_visible()
            if panel_id == "architecture-faq-details":
                expect(page.locator(".sy-architecture-faq-answer")).to_have_count(0)
            _fit(page)
        if route == "/platform":
            expect(page.get_by_test_id("platform-release-state")).to_be_visible()
            expect(page.get_by_test_id("co-creation-profile")).to_be_visible()
            retained_id = "platform-summary-details"
        elif route == "/engineering":
            expect(page.get_by_test_id("engineering-coverage-item")).to_have_count(13)
            expect(page.get_by_test_id("engineering-coverage-item").locator(".sy-status-badge")).to_have_count(0)
            category = page.get_by_test_id("engineering-evidence-type-filter")
            category.click()
            options = page.locator(".q-menu .q-item")
            options.nth(3).click()  # all, repository, access, quality
            selected = category.inner_text()
            expect(page.get_by_test_id("engineering-coverage-item")).to_have_count(5)
            page.locator(".sy-evidence-view-toggle button").nth(1).click()
            expect(page.get_by_test_id("engineering-evidence-table")).to_be_visible()
            retained_id = "engineering-coverage-details"
        else:
            question = page.get_by_test_id("architecture-faq-draft")
            _open(question)
            expect(page.locator(".sy-architecture-faq-answer")).to_have_count(1)
            retained_id = "architecture-faq-details"

        first = _capture_runtime_footprint(page, session, label=route + "-first-mount")
        results.append({"scenario": "first-materialization", "mode": mode, "route": route,
                        "cold": cold, "firstMounted": first, "coldBudgetClaimed": False})
        persist()
        panel = page.get_by_test_id(retained_id)
        panel.evaluate("node => { window.__d3bNodes = [...node.querySelectorAll('*')]; }")
        if route == "/engineering":
            panel.evaluate("""node => { window.__d3bControls = [...node.querySelectorAll(
                '[data-testid$="-filter"], input, [data-testid="engineering-evidence-table"]')]; }""")
        content = page.get_by_test_id(retained_id + "-content")
        content.evaluate("node => node.tabIndex = -1")
        for _ in range(20):
            _close(panel, content)
            _open(panel)
            disconnected = page.evaluate("""window.__d3bNodes.filter(node => !node.isConnected)
                .map(node => ({tag:node.tagName, classes:node.className}))""")
            if disconnected:
                results.append({"scenario": "disconnected-descendant-diagnostic", "mode": mode,
                                "route": route, "nodes": disconnected})
                persist()
            if route == "/engineering":
                assert page.evaluate("window.__d3bControls.every(node => node.isConnected)"), "Control or table root remounted"
            assert not disconnected, f"Retained descendants disconnected: {disconnected}"
        after = _capture_runtime_footprint(page, session, label=route + "-retained")
        _record_growth(first, after, mode=mode + route + "-retained-not-cold", results=results, persist=persist)
        session.detach()
        if route == "/engineering":
            assert category.inner_text() == selected
            expect(page.get_by_test_id("engineering-evidence-table")).to_be_visible()
            expect(page.get_by_test_id("engineering-release-state")).to_have_text(report_state)
            expect(page.get_by_test_id("engineering-release-date")).to_have_text(report_date)
            # Exercise callbacks again after retention, not just DOM/value identity.
            page.get_by_test_id("engineering-evidence-view-filter").locator("button").first.click()
            expect(page.get_by_test_id("engineering-coverage-item")).to_have_count(5)
            category.click()
            page.locator(".q-menu .q-item").first.click()
            expect(page.get_by_test_id("engineering-coverage-item")).to_have_count(13)
            date = page.get_by_test_id("engineering-evidence-date-filter").locator("input")
            date.fill("1900-01-01")
            expect(page.get_by_test_id("engineering-evidence-empty")).to_be_visible()
            date.fill("")
            expect(page.get_by_test_id("engineering-coverage-item")).to_have_count(13)
            state = page.get_by_test_id("engineering-evidence-state-filter")
            state.click()
            page.locator(".q-menu .q-item").filter(has_text=report_state).click()
            expect(page.get_by_test_id("engineering-coverage-item")).to_have_count(13)
        elif route == "/system-architecture":
            expect(_header(question)).to_have_attribute("aria-expanded", "true")
        _fit(page)
        page.screenshot(path=str(case / (route[1:] + "-expanded.png")))

    for route, anchor, panel_id in (
        ("/platform", "co-creation-title", "platform-attribution-details"),
        ("/engineering", "engineering-evidence-title", "engineering-coverage-details"),
        ("/system-architecture", "developer-reference-title", "architecture-developer-details"),
    ):
        page.goto(base + route + "#" + anchor, wait_until="domcontentloaded")
        _ready(page)
        panel = page.get_by_test_id(panel_id)
        expect(_header(panel)).to_have_attribute("aria-expanded", "true")
        expect(page.locator("#" + anchor)).to_be_focused()
        panel.evaluate("node => { window.__d3bAnchorNodes = [...node.querySelectorAll('*')]; }")
        panel_id_target = {
            "/platform": "platform-attribution-section",
            "/engineering": "engineering-evidence-index-section",
            "/system-architecture": "architecture-developer-section",
        }[route]
        page.evaluate("anchor => { location.hash = anchor; }", panel_id_target)
        expect(_header(panel)).to_be_focused()
        page.go_back()
        expect(page.locator("#" + anchor)).to_be_focused()
        assert page.evaluate("window.__d3bAnchorNodes.every(node => node.isConnected)")
        page.go_forward()
        expect(_header(panel)).to_be_focused()
        results.append({"scenario": "original-heading-direct-link-history-focus-retained",
                        "route": route, "mode": mode, "status": "pass"})
        persist()

    transmitted = []
    marker = "fictional-private-d3b-fragment"
    page.on("websocket", lambda socket: socket.on("framesent", lambda payload:
            transmitted.append(True) if marker in str(payload) else None))
    page.goto(base + "/engineering#" + marker, wait_until="domcontentloaded")
    _ready(page)
    page.evaluate("location.hash='engineering-evidence-title'")
    expect(page.locator("#engineering-evidence-title")).to_be_focused()
    assert not transmitted
    results.append({"scenario": "unknown-fragment-not-transmitted", "mode": mode, "status": "pass"})
    persist()


def main():
    scratch = Path(tempfile.mkdtemp(prefix="sy-mobile-trust-"))
    source = _source_state(refresh_fingerprint=True)
    assert not source["sourceDirty"], "Clean checkpoint required"
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
                    metadata["contexts"].append({"mode": mode, "runId": environment["SING_YIN_E2E_RUN_ID"]})
                    from nicegui_app.services.guest_workspace import demo_fixture
                    from nicegui_app.services.roster_workflow import RosterWorkflow
                    seed = case / "fictional.json"
                    seed.write_text(json.dumps({"prefects": [dict(row, name=row["nameZh"], **{"class": row["className"]})
                        for row in demo_fixture()["prefects"]]}), encoding="utf-8")
                    RosterWorkflow(database_path=Path(environment["SING_YIN_DATABASE_PATH"]),
                                   backup_dir=Path(environment["SING_YIN_BACKUP_DIR"]), seed_path=seed).bootstrap()
                    process, output = _start_server(environment, case / "server.log")
                    try:
                        base = environment["SING_YIN_TEST_URL"].rstrip("/")
                        _wait_until_ready(process, base, case / "server.log")
                        page, context = mobile._new_mobile_page(browser, width=390, height=844,
                            label=mode, console_errors=errors, page_errors=errors)
                        if mode == "guest":
                            _install_gateway_stubs(context)
                        try:
                            _check(page, base, case, mode, results, persist)
                        except Exception:
                            page.screenshot(path=str(case / "failure.png"))
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
