"""Isolated D4a restore diagnostics; not formal mobile or recovery acceptance."""
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
from scripts.verify_mobile_trust import _fit
from scripts.verify_rc31_theme_controls import _safe_environment
from scripts.verify_release_candidate import _source_state, _start_server, _stop_server, _wait_until_ready
from scripts.verify_unified_guest_ui import _install_gateway_stubs


def _check(page, base, case, mode, results, persist, backup=None):
    page.goto(base + "/settings", wait_until="domcontentloaded")
    _ready(page)
    if mode == "guest":
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.get_by_test_id("create-verified-backup-action").click()
        _ready(page)
    ready = page.get_by_test_id("restore-ready-action")
    expect(ready).to_be_disabled()
    page.get_by_test_id("restore-backup-choice").click()
    page.get_by_role("option").first.click()
    expect(ready).to_be_enabled()
    _fit(page)
    session = page.context.new_cdp_session(page)
    baseline = _capture_runtime_footprint(page, session, label=mode + "-before-first-review")
    dialog = page.get_by_test_id("restore-confirm-dialog")
    confirm = page.get_by_test_id("confirm-restore-action")
    phrase = page.locator("[data-testid='restore-confirmation-text'] input, input[data-testid='restore-confirmation-text']")
    results.append({"mode": mode, "scenario": "explicit-selection", "baseline": baseline})
    persist()
    for cycle in range(20):
        ready.click()
        expect(dialog).to_be_visible()
        expect(dialog).to_have_attribute("role", "alertdialog")
        expect(confirm).to_be_disabled()
        expect(phrase).to_have_value("")
        phrase.fill("wrong confirmation")
        expect(confirm).to_be_disabled()
        phrase.fill("確認還原備份")
        expect(confirm).to_be_enabled()
        if cycle == 0:
            _fit(page)
            page.screenshot(path=str(case / "review.png"))
        page.get_by_test_id("restore-cancel-action").click()
        expect(dialog).to_be_hidden()
        expect(ready).to_be_focused()
        expect(page.get_by_test_id("restore-success-receipt")).to_be_hidden()
        results.append({"mode": mode, "scenario": "cancel-clears-consent", "cycle": cycle + 1})
        persist()
    after = _capture_runtime_footprint(page, session, label=mode + "-after-20-cancelled-reviews")
    _record_growth(baseline, after, mode=mode, results=results, persist=persist)
    session.detach()
    # Additional unmeasured accessibility cases do not warm the cold endpoints.
    for dismissal in ("escape", "backdrop"):
        ready.click()
        expect(dialog).to_be_visible()
        expect(phrase).to_have_value("")
        phrase.fill("確認還原備份")
        expect(confirm).to_be_enabled()
        if dismissal == "escape":
            page.keyboard.press("Escape")
        else:
            page.locator(".q-dialog__backdrop").click(position={"x": 2, "y": 2})
        expect(dialog).to_be_hidden()
        expect(ready).to_be_focused()
        results.append({"mode": mode, "scenario": dismissal + "-clears-consent", "status": "pass"})
        persist()
    ready.click()
    expect(dialog).to_be_visible()
    expect(phrase).to_have_value("")
    expect(confirm).to_be_disabled()
    text_style = page.add_style_tag(content="html { font-size: 200% !important; }")
    _fit(page)
    page.screenshot(path=str(case / "review-text-200.png"))
    text_style.evaluate("node => node.remove()")
    page.get_by_test_id("restore-cancel-action").click()
    expect(dialog).to_be_hidden()
    results.append({"mode": mode, "scenario": "eight-viewports-200-percent-text", "status": "pass"})
    persist()
    ready.click()
    expect(dialog).to_be_visible()
    expect(confirm).to_be_disabled()
    phrase.fill("確認還原備份")
    confirm.click()
    expect(dialog).to_be_hidden()
    expect(page.get_by_test_id("restore-success-receipt")).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("restore-failure-receipt")).to_be_hidden()
    expect(ready).to_be_disabled()
    _fit(page)
    page.get_by_test_id("restore-success-receipt").scroll_into_view_if_needed()
    page.screenshot(path=str(case / "success.png"))
    results.append({"mode": mode, "scenario": "real-restore-persistent-receipt", "status": "pass"})
    persist()
    if backup is not None:
        # Corrupt only this disposable fixture's manifest after reviewing it.
        # This proves the real backend rejects a changed source, with no success.
        assert case.resolve() in backup.resolve().parents
        page.get_by_test_id("restore-backup-choice").click()
        page.get_by_role("option").first.click()
        ready.click()
        expect(dialog).to_be_visible()
        manifest = backup.with_suffix(".manifest.json")
        original = manifest.read_bytes()
        changed = json.loads(original)
        changed["sha256"] = "0" * 64
        try:
            manifest.write_text(json.dumps(changed), encoding="utf-8")
            phrase.fill("確認還原備份")
            confirm.click()
            expect(page.get_by_test_id("restore-failure-receipt")).to_be_visible(timeout=30_000)
            expect(page.get_by_test_id("restore-success-receipt")).to_be_hidden()
            page.get_by_test_id("restore-failure-receipt").scroll_into_view_if_needed()
            page.screenshot(path=str(case / "changed-backup-rejected.png"))
            results.append({"mode": mode, "scenario": "backend-changed-backup-rejected", "status": "pass"})
            persist()
        finally:
            manifest.write_bytes(original)


def main():
    scratch = Path(tempfile.mkdtemp(prefix="sy-settings-restore-"))
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
                    workflow = RosterWorkflow(database_path=Path(environment["SING_YIN_DATABASE_PATH"]),
                        backup_dir=Path(environment["SING_YIN_BACKUP_DIR"]), seed_path=seed)
                    workflow.bootstrap()
                    backup = workflow.create_verified_backup() if mode != "guest" else None
                    # Windows restore swaps the SQLite file. The fixture creator
                    # must not keep an unrelated pool holding its WAL/SHM open.
                    workflow._dispose_database_connections()
                    process, output = _start_server(environment, case / "server.log")
                    try:
                        base = environment["SING_YIN_TEST_URL"].rstrip("/")
                        _wait_until_ready(process, base, case / "server.log")
                        page, context = mobile._new_mobile_page(browser, width=390, height=844,
                            label=mode, console_errors=errors, page_errors=errors)
                        if mode == "guest":
                            _install_gateway_stubs(context)
                        try:
                            _check(page, base, case, mode, results, persist, backup)
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
