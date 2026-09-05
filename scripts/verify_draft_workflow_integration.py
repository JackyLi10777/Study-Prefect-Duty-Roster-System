"""Bounded fictional-data browser check for the mainline draft integration.

This is source-bound functional evidence, not a release or controlled p75 gate.
It never runs against an existing school database or changes a production host.
"""
from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "packages/roster_policy"), str(ROOT / "packages/roster_core")]

from scripts.verify_release_candidate import (
    _free_loopback_port, _source_state, _start_server, _stop_server,
    _wait_until_ready, isolated_environment,
)


def main() -> None:
    scratch = Path(tempfile.mkdtemp(prefix="sy-draft-mainline-"))
    environment = isolated_environment(scratch, _free_loopback_port())
    environment["PYTHONPATH"] = os.pathsep.join(sys.path[:3])
    os.environ.update(environment)
    from playwright.sync_api import expect, sync_playwright
    from nicegui_app.services.guest_workspace import demo_fixture
    from nicegui_app.services.roster_workflow import RosterWorkflow
    from nicegui_app.services.workflow_types import DraftSlotStateEdit
    from scripts import verify_nicegui_mobile as mobile

    source = _source_state(refresh_fingerprint=True)
    if source["sourceDirty"]:
        raise AssertionError("Draft browser evidence requires a clean checkpoint")
    rows = [dict(row, name=row["nameZh"], **{"class": row["className"]})
            for row in demo_fixture()["prefects"]]
    seed = scratch / "fictional.json"
    seed.write_text(json.dumps({"prefects": rows}), encoding="utf-8")
    workflow = RosterWorkflow(database_path=Path(environment["SING_YIN_DATABASE_PATH"]),
                              backup_dir=Path(environment["SING_YIN_BACKUP_DIR"]), seed_path=seed)
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    key = "MONDAY:ROOM_302:1"
    original = next(row for row in workflow.assignments(draft.id)
                    if row["day"] == "MONDAY" and row["postCode"] == "ROOM_302")
    closed = workflow.apply_draft_patch(roster_week_id=draft.id,
        expected_week_version=draft.version, slot_edits=(DraftSlotStateEdit(key, "unavailable"),),
        command_id="fictional-browser-close-slot")
    errors = []
    observations = []
    process, output = _start_server(environment, scratch / "server.log")
    print(f"ISOLATED {scratch}", flush=True)
    try:
        _wait_until_ready(process, environment["SING_YIN_TEST_URL"], scratch / "server.log")
        with sync_playwright() as playwright:
            browser = mobile._launch_real_chrome(playwright)
            try:
                page, context = mobile._new_mobile_page(browser, width=390, height=844,
                    label="draft-mainline", console_errors=errors, page_errors=errors)
                try:
                    page.goto(f"{mobile.BASE_URL}/rosters/{draft.id}", wait_until="domcontentloaded")
                    cell = page.locator(f'.sy-draft-mobile-cell[data-cell-key="{key}"]')
                    expect(cell).to_be_visible()
                    cell.click()
                    sheet = page.get_by_test_id("draft-mobile-editor-sheet")
                    expect(sheet).to_be_visible()
                    sheet.get_by_test_id("draft-slot-reopen-mobile").click()
                    choices = sheet.get_by_test_id("draft-candidate-options-mobile")
                    candidate = choices.get_by_role("radio", name=re.compile(re.escape(str(original["prefectName"]))))
                    expect(candidate).to_be_visible(timeout=10_000)
                    candidate.click()
                    sheet.get_by_test_id("draft-mobile-editor-close").click()
                    page.get_by_test_id("draft-save-all-mobile").click()
                    # Hold only this disposable DB's write lock so status-dialog
                    # semantics are observable without changing production delays.
                    with sqlite3.connect(environment["SING_YIN_DATABASE_PATH"]) as lock:
                        lock.execute("BEGIN IMMEDIATE")
                        try:
                            page.get_by_test_id("draft-save-all-mobile-confirm").click()
                            progress = page.get_by_test_id("operation-progress-dialog")
                            expect(progress).to_be_visible(timeout=5_000)
                            progress_title = progress.locator(".sy-dialog-title").inner_text()
                            expect(page.get_by_role("dialog", name=progress_title, exact=True)).to_be_visible()
                            expect(progress).to_have_accessible_description(
                                progress.locator(".sy-dialog-description").inner_text())
                        finally:
                            lock.rollback()
                    page.wait_for_function("window.__syDraftDirty === false")
                    after = workflow.roster_week(draft.id)
                    assert after["version"] == closed.version + 1
                    restored = next(row for row in workflow.assignments(draft.id)
                                    if row["day"] == "MONDAY" and row["postCode"] == "ROOM_302")
                    assert restored["prefectId"] == original["prefectId"]
                    assert not any(item.get("cellKey") == key for item in after.get("slotExceptions", []))
                    observations.append({"scenario": "reopen-and-assign", "version": after["version"]})
                    search = sheet.get_by_test_id("draft-candidate-search-mobile")
                    search_id = search.get_attribute("id")
                    for cycle in range(20):
                        cell.click()
                        expect(sheet).to_be_visible()
                        assert search.get_attribute("id") == search_id
                        assert page.get_by_test_id("draft-mobile-editor-sheet").count() == 1
                        sheet.get_by_test_id("draft-mobile-editor-close").click()
                        expect(sheet).to_be_hidden()
                        expect(cell).to_be_focused()
                    observations.append({"scenario": "editor-reuse-focus", "cycles": 20})
                    day_section = page.get_by_test_id("draft-mobile-day-monday")
                    day_section.locator("button").first.click()
                    confirmation = page.get_by_test_id("draft-day-confirm-monday")
                    expect(confirmation).to_be_visible()
                    title = confirmation.locator(".sy-dialog-title").inner_text()
                    expect(page.get_by_role("alertdialog", name=title, exact=True)).to_be_visible()
                    expect(confirmation).to_have_accessible_description(
                        confirmation.locator(".sy-dialog-description").inner_text())
                    confirmation.get_by_role("button").first.click()
                    expect(confirmation).to_be_hidden()
                    observations.append({"scenario": "named-status-and-alert-dialogs"})
                    for width in (256, 320, 390):
                        page.set_viewport_size({"width": width, "height": 844})
                        page.goto(f"{mobile.BASE_URL}/rosters", wait_until="domcontentloaded")
                        toggle = page.get_by_test_id("roster-mobile-rules-toggle")
                        expect(toggle).to_be_visible()
                        assert page.get_by_test_id("history-priority-chart").count() == 0
                        toggle.click()
                        expect(page.get_by_test_id("history-priority-chart")).to_be_visible()
                        overflow = page.evaluate("document.documentElement.scrollWidth - innerWidth")
                        assert overflow == 0, f"Expanded rules overflow at {width}px: {overflow}"
                        observations.append({"scenario": "lazy-rules-reflow", "width": width, "overflow": overflow})
                    if errors:
                        raise AssertionError(f"Browser errors: {errors}")
                except Exception:
                    page.screenshot(path=str(scratch / "failure.png"), full_page=True)
                    (scratch / "failure.json").write_text(json.dumps({**source, "observations": observations,
                        "browserErrors": errors, "status": "fail"}), encoding="utf-8")
                    raise
                finally:
                    context.close()
                if _source_state(refresh_fingerprint=True) != source:
                    raise AssertionError("Source changed during browser verification")
                report = {**source, "status": "pass", "evidenceKind": "functional-diagnostic",
                    "runId": environment["SING_YIN_E2E_RUN_ID"], "browserVersion": browser.version,
                    "observations": observations, "browserErrors": errors, "formalReleaseExecuted": False}
                (scratch / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
                print(f"PASS {scratch / 'report.json'}", flush=True)
            finally:
                browser.close()
    finally:
        _stop_server(process, output)


if __name__ == "__main__":
    main()
