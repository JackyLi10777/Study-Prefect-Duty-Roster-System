"""D2 source-bound diagnostics; not a release gate or controlled p75 evidence."""
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
from scripts.verify_mobile_preferences import _ready, _record_growth
from scripts.verify_rc31_theme_controls import _safe_environment
from scripts.verify_release_candidate import _source_state, _start_server, _stop_server, _wait_until_ready
from scripts.verify_unified_guest_ui import _install_gateway_stubs


def _open(panel):
    header = panel.locator(":scope > .q-expansion-item__container > .q-item")
    header.click()
    expect(header).to_have_attribute("aria-expanded", "true")


def _close(panel, field):
    field.focus()
    panel.evaluate("element => runMethod(Number(element.id.slice(1)), 'hide', [])")
    header = panel.locator(":scope > .q-expansion-item__container > .q-item")
    expect(header).to_have_attribute("aria-expanded", "false")
    expect(header).to_be_focused()


def _fit(page):
    for width, height in ((256, 760), (320, 760), (390, 844), (844, 390)):
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(100)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), f"Overflow at {width}"
    page.set_viewport_size({"width": 390, "height": 844})


def _admin(page, base, case, support_dir, results, persist):
    page.goto(base + "/support?source=/rosters/12/adjustments", wait_until="domcontentloaded")
    _ready(page)
    panel = page.locator(".sy-support-admin")
    expect(panel.locator("textarea")).to_have_count(3)
    expect(panel.locator("input[type=file]")).to_have_count(0)
    expect(page.get_by_test_id("support-lookup-id")).to_have_count(0)
    for index, value in enumerate(("Fictional expected D2", "Fictional actual D2", "Fictional step D2")):
        panel.locator("textarea").nth(index).fill(value)
    page.get_by_test_id("preview-support-incident").click()
    dialog = page.locator(".q-dialog")
    expect(dialog).to_be_visible()
    dialog.locator(".q-checkbox").click()
    page.get_by_test_id("save-support-incident").click()
    receipt = page.get_by_test_id("support-incident-id")
    expect(receipt).to_be_visible(timeout=20_000)
    incident_id = receipt.inner_text().strip()
    manifest = json.loads((support_dir / "inbox" / incident_id / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["route_category"] == "roster_workflow"
    assert manifest["workflow_action"] == "page_view" and manifest["attachment_manifest"] == []
    results.append({"scenario": "unopened-advanced-persistent-submit", "status": "pass"})
    persist()

    # Explicitly separate legitimate first materialization from retained-cycle growth.
    session = page.context.new_cdp_session(page)
    cold = _capture_runtime_footprint(page, session, label="support-cold")
    results.append({"scenario": "cold-support-before-first-mount", "footprint": cold})
    persist()
    details = page.get_by_test_id("support-progressive-details")
    history = page.get_by_test_id("support-history-lookup")
    _open(details)
    impact = details.locator("textarea")
    expect(impact).to_be_visible()
    impact.fill("Retained fictional impact D2")
    details.locator("input[type=file]").set_input_files({"name": "fictional.txt", "mimeType": "text/plain", "buffer": b"fictional attachment D2"})
    expect(details.get_by_text("fictional.txt", exact=False).last).to_be_visible()
    _open(history)
    lookup = page.get_by_test_id("support-lookup-id")
    lookup.fill(incident_id)
    page.get_by_test_id("lookup-support-incident").click()
    expect(page.get_by_test_id("support-lookup-result")).to_be_visible(timeout=20_000)
    _close(history, lookup)
    _close(details, impact)
    first = _capture_runtime_footprint(page, session, label="support-first-mount")
    results.append({"scenario": "first-materialization", "cold": cold, "firstMounted": first,
                    "coldBudgetClaimed": False})
    persist()
    page.evaluate("window.__d2Fields = [...document.querySelectorAll('.sy-support-admin input,.sy-support-admin textarea,[data-testid=support-lookup-id] input')]")
    for cycle in range(20):
        _open(details)
        expect(impact).to_have_value("Retained fictional impact D2")
        _close(details, impact)
        _open(history)
        expect(lookup).to_have_value(incident_id)
        expect(page.get_by_test_id("support-lookup-result")).to_be_visible()
        _close(history, lookup)
        assert page.evaluate("window.__d2Fields.every(node => node.isConnected)")
        if cycle in {0, 9, 19}:
            results.append({"scenario": "retained-cycle", "cycle": cycle + 1,
                            "footprint": _capture_runtime_footprint(page, session, label="support")})
            persist()
    after = _capture_runtime_footprint(page, session, label="support-after")
    _record_growth(first, after, mode="support-retained-not-cold", results=results, persist=persist)
    session.detach()
    _open(details)
    _open(history)
    _fit(page)
    page.screenshot(path=str(case / "support.png"), full_page=False)

    page.goto(base + "/access-control", wait_until="domcontentloaded")
    _ready(page)
    expect(page.get_by_test_id("access-status-summary")).to_be_visible()
    expect(page.get_by_test_id("operator-access-card")).to_have_count(0)
    technical = page.get_by_test_id("access-technical-controls")
    _open(technical)
    card = page.get_by_test_id("operator-access-card")
    expect(card).to_be_visible()
    page.evaluate("window.__d2Access = document.querySelector('[data-testid=operator-access-card]')")
    for _ in range(20):
        _close(technical, card.locator("button"))
        _open(technical)
        assert page.evaluate("window.__d2Access === document.querySelector('[data-testid=operator-access-card]')")
    _fit(page)
    page.screenshot(path=str(case / "access.png"), full_page=False)
    results.append({"scenario": "access-first-use-focus-reuse-and-reflow", "cycles": 20, "status": "pass"})
    persist()


def _guest(page, base, case, support_dir, results, persist):
    transmitted = []
    page.on("websocket", lambda socket: socket.on("framesent", lambda payload:
            transmitted.append(True) if "Fictional D2 private" in str(payload) else None))
    existing = set((support_dir / "inbox").glob("INC-*"))
    page.goto(base + "/support?source=/prefects", wait_until="domcontentloaded")
    _ready(page)
    root = page.get_by_test_id("guest-browser-only-support")
    expect(root).to_have_attribute("data-installed", "true")
    expect(root.locator("textarea")).to_have_count(3)
    expect(root.locator("#sy-support-route")).to_have_count(0)
    assert root.locator("template").evaluate("node => node.content.querySelectorAll('select,textarea').length") == 5
    expect(root.locator("input[type=file]")).to_have_count(0)
    page.evaluate("""window.__d2Fetch = 0; const original = window.fetch.bind(window);
        window.fetch = (...args) => { window.__d2Fetch++; return original(...args); };""")
    for name in ("expected", "actual", "steps"):
        root.locator(f"#sy-support-{name}").fill("Fictional D2 private " + name)

    def download():
        root.locator("button[type=submit]").click()
        with page.expect_download() as info:
            root.locator("#sy-support-browser-download").click()
        return json.loads(Path(info.value.path()).read_text(encoding="utf-8"))

    payload = download()
    assert payload["route_category"] == "prefects" and payload["workflow_action"] == "page_view"
    details = root.locator("#sy-support-details")
    details.locator("summary").click()
    impact = root.locator("#sy-support-impact")
    impact.fill("Fictional D2 private last impact")
    page.evaluate("window.__d2GuestField = document.querySelector('#sy-support-impact')")
    for _ in range(20):
        impact.focus()
        details.evaluate("node => { node.open = false; }")
        expect(details.locator("summary")).to_be_focused()
        details.locator("summary").click()
        expect(impact).to_have_value("Fictional D2 private last impact")
        assert page.evaluate("window.__d2GuestField === document.querySelector('#sy-support-impact')")
    payload = download()
    assert payload["impact"] == "Fictional D2 private last impact"
    assert page.evaluate("window.__d2Fetch") == 0 and not transmitted
    assert set((support_dir / "inbox").glob("INC-*")) == existing
    root.locator("button[type=reset]").click()
    expect(impact).to_have_value("")
    expect(root.locator("#sy-support-route")).to_have_value("prefects")
    _fit(page)
    page.screenshot(path=str(case / "guest-support.png"), full_page=False)
    page.reload(wait_until="domcontentloaded")
    expect(root).to_have_attribute("data-installed", "true")
    expect(root.locator("#sy-support-impact")).to_have_count(0)
    expect(root.locator("#sy-support-expected")).to_have_value("")
    page.goto(base + "/access-control", wait_until="domcontentloaded")
    _ready(page)
    expect(page.get_by_test_id("access-status-summary")).to_be_visible()
    expect(page.get_by_test_id("access-technical-controls")).to_have_count(0)
    results.append({"scenario": "guest-template-download-reuse-reset-no-report-transmission", "status": "pass", "cycles": 20})
    persist()


def main():
    scratch = Path(tempfile.mkdtemp(prefix="sy-mobile-access-support-"))
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
                            check = _guest if mode == "guest" else _admin
                            check(page, base, case, Path(environment["SING_YIN_SUPPORT_DIR"]), results, persist)
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
