"""Fictional-data diagnostic: export progress must be inside the modal top layer."""
from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
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
    scratch = Path(tempfile.mkdtemp(prefix="sy-export-overlay-"))
    environment = isolated_environment(scratch, _free_loopback_port())
    environment["PYTHONPATH"] = os.pathsep.join(sys.path[:3])
    os.environ.update(environment)
    from playwright.sync_api import expect, sync_playwright
    from nicegui_app.services.guest_workspace import demo_fixture
    from nicegui_app.services.roster_workflow import RosterWorkflow
    from scripts import verify_nicegui_mobile as mobile

    source = _source_state(refresh_fingerprint=True)
    if source["sourceDirty"]:
        raise AssertionError("Overlay evidence requires a clean source checkpoint")
    rows = [dict(row, name=row["nameZh"], **{"class": row["className"]})
            for row in demo_fixture()["prefects"]]
    seed = scratch / "fictional.json"
    seed.write_text(json.dumps({"prefects": rows}), encoding="utf-8")
    workflow = RosterWorkflow(database_path=Path(environment["SING_YIN_DATABASE_PATH"]),
                              backup_dir=Path(environment["SING_YIN_BACKUP_DIR"]), seed_path=seed)
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    workflow.publish(draft.id, expected_week_version=draft.version)
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
                    label="export-overlay", console_errors=errors, page_errors=errors)
                try:
                    page.goto(f"{mobile.BASE_URL}/rosters/{draft.id}", wait_until="domcontentloaded")
                    page.get_by_test_id("open-roster-export").click()
                    dialog = page.get_by_test_id("roster-export-dialog")
                    expect(dialog).to_be_visible()
                    # Lock ONLY the disposable fixture to observe real progress.
                    with sqlite3.connect(environment["SING_YIN_DATABASE_PATH"]) as lock:
                        lock.execute("BEGIN EXCLUSIVE")
                        try:
                            dialog.get_by_test_id("prepare-roster-images").click()
                            progress = dialog.get_by_test_id("roster-export-feedback")
                            expect(progress).to_be_visible(timeout=5000)
                            expect(progress).to_have_attribute("role", "status")
                            expect(progress).to_have_attribute("aria-busy", "true")
                            expect(progress).not_to_be_empty()
                            assert page.get_by_test_id("operation-progress-dialog").count() == 0
                            hit = progress.evaluate("""element => {
                                const card = element.querySelector('.sy-dialog-card') || element;
                                const box = card.getBoundingClientRect();
                                const top = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
                                return {inside: element.contains(top), topTag: top?.tagName,
                                    topTestId: top?.getAttribute('data-testid'),
                                    role: element.getAttribute('role'),
                                    title: element.querySelector('.sy-dialog-title')?.textContent || element.textContent};
                            }""")
                            observations.append({"scenario": "progress-top-layer", **hit})
                            page.screenshot(path=str(scratch / "progress.png"), full_page=True)
                            assert hit["inside"], "Export progress is behind the native modal top layer"
                        finally:
                            lock.rollback()
                    if errors:
                        raise AssertionError("Browser errors observed")
                except Exception:
                    (scratch / "failure.json").write_text(json.dumps({**source,
                        "status": "fail", "observations": observations,
                        "runId": environment["SING_YIN_E2E_RUN_ID"],
                        "browserVersion": browser.version, "evidenceKind": "functional-diagnostic",
                        "formalReleaseExecuted": False,
                        "postVerificationSource": _source_state(refresh_fingerprint=True),
                    }, indent=2), encoding="utf-8")
                    raise
                finally:
                    context.close()
                if _source_state(refresh_fingerprint=True) != source:
                    raise AssertionError("Source changed during overlay verification")
                (scratch / "report.json").write_text(json.dumps({**source,
                    "status": "pass", "observations": observations,
                    "runId": environment["SING_YIN_E2E_RUN_ID"],
                    "browserVersion": browser.version, "evidenceKind": "functional-diagnostic",
                    "formalReleaseExecuted": False,
                }, indent=2), encoding="utf-8")
                print(f"PASS {scratch / 'report.json'}", flush=True)
            finally:
                browser.close()
    finally:
        _stop_server(process, output)


if __name__ == "__main__":
    main()
