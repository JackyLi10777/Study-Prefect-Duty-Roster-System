"""Source-bound D3a reading diagnostics, not the complete mobile release gate."""
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


def _check(page, base, case, mode, results, persist):
    for route, panel_id, content_id in (
        ("/getting-started", "start-reference-details", "reference-index"),
        ("/guide", "guide-answer-guide-issue-pdf", None),
        ("/devotional", "devotional-details", "devotional-tone"),
    ):
        page.goto(base + route, wait_until="domcontentloaded")
        _ready(page)
        panel = page.get_by_test_id(panel_id)
        expect(_header(panel)).to_have_attribute("aria-expanded", "false")
        if content_id:
            expect(page.get_by_test_id(content_id)).to_have_count(0)
        else:
            expect(panel.get_by_test_id(panel_id + "-content").locator(".nicegui-label")).to_have_count(0)
        _fit(page)
        page.screenshot(path=str(case / (route[1:] + "-initial.png")))
        session = page.context.new_cdp_session(page)
        cold = _capture_runtime_footprint(page, session, label=route + "-cold")
        _open(panel)
        expect(panel.get_by_test_id(panel_id + "-content")).to_be_visible()
        if content_id:
            expect(page.get_by_test_id(content_id)).to_be_visible()
        first = _capture_runtime_footprint(page, session, label=route + "-first-mount")
        results.append({"scenario": "first-materialization", "mode": mode, "route": route,
                        "cold": cold, "firstMounted": first, "coldBudgetClaimed": False})
        persist()
        panel.evaluate("node => { window.__d3Nodes = [...node.querySelectorAll('*')]; }")
        panel.get_by_test_id(panel_id + "-content").evaluate("node => node.tabIndex = -1")
        for _ in range(20):
            _close(panel, panel.get_by_test_id(panel_id + "-content"))
            _open(panel)
            assert page.evaluate("window.__d3Nodes.every(node => node.isConnected)")
        after = _capture_runtime_footprint(page, session, label=route + "-retained")
        _record_growth(first, after, mode=mode + route + "-retained-not-cold", results=results, persist=persist)
        session.detach()
        _fit(page)
        page.screenshot(path=str(case / (route[1:] + "-expanded.png")))

    page.goto(base + "/guide#guide-issue-pdf", wait_until="domcontentloaded")
    _ready(page)
    pdf = page.get_by_test_id("guide-answer-guide-issue-pdf")
    expect(_header(pdf)).to_have_attribute("aria-expanded", "true")
    expect(_header(pdf)).to_be_focused()
    text = pdf.get_by_test_id("guide-answer-guide-issue-pdf-content").locator(".nicegui-label").first.inner_text()
    search = page.get_by_test_id("guide-search")
    search.fill(text)
    expect(page.get_by_test_id("guide-answer-guide-week-start")).to_be_hidden()
    search.fill("unmatched-fictional-d3-query")
    expect(page.get_by_test_id("guide-no-results")).to_be_visible()
    contents = page.get_by_test_id("reading-contents")
    _open(contents)
    page.locator('[data-sy-toc-target="guide-week-start"]').click()
    first_answer = page.get_by_test_id("guide-answer-guide-week-start")
    expect(_header(first_answer)).to_be_focused()
    expect(_header(first_answer)).to_have_attribute("aria-expanded", "true")
    expect(search).to_have_value("unmatched-fictional-d3-query")
    page.go_back()
    expect(_header(pdf)).to_be_focused()
    page.go_forward()
    expect(_header(first_answer)).to_be_focused()
    search.fill("another-unmatched-d3-query")
    expect(first_answer).to_be_hidden()
    expect(page.get_by_test_id("guide-no-results")).to_be_visible()
    results.append({"scenario": "guide-search-hidden-content-deep-link-toc-history-focus", "mode": mode, "status": "pass"})
    persist()

    transmitted = []
    page.on("websocket", lambda socket: socket.on("framesent", lambda payload:
            transmitted.append(True) if "fictional-private-d3-fragment" in str(payload) else None))
    page.goto(base + "/getting-started#fictional-private-d3-fragment", wait_until="domcontentloaded")
    _ready(page)
    page.evaluate("location.hash='start-reference-map'")
    expect(_header(page.get_by_test_id("start-reference-details"))).to_be_focused()
    assert not transmitted
    page.goto(base + "/devotional#devotional-reflection", wait_until="domcontentloaded")
    _ready(page)
    expect(page.get_by_test_id("devotional-tone")).to_be_visible()
    expect(_header(page.get_by_test_id("devotional-details"))).to_be_focused()
    results.append({"scenario": "reading-direct-links-and-unknown-fragment-not-transmitted", "mode": mode, "status": "pass"})
    persist()


def main():
    scratch = Path(tempfile.mkdtemp(prefix="sy-mobile-reading-"))
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
