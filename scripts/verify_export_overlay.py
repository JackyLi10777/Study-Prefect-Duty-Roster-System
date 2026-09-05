"""Fictional-data diagnostic: export progress must be inside the modal top layer."""
from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "packages/roster_policy"), str(ROOT / "packages/roster_core")]

from scripts.verify_release_candidate import (
    _free_loopback_port, _source_state, _stop_server,
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
    from nicegui_app.ui.i18n import MESSAGES, ZH_HK

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
    # Delay ONLY this disposable process's real renderer, after configuring
    # storage normally. This is not a production timeout or a performance run.
    runner = scratch / "overlay_origin.py"
    runner.write_text('''from nicegui_app.launcher import configure_nicegui_storage_path
configure_nicegui_storage_path()
import time
from nicegui_app.services import roster_image_export
original = roster_image_export.render_roster_png_bundle
def delayed(*args, **kwargs):
    time.sleep(1.5)
    return original(*args, **kwargs)
roster_image_export.render_roster_png_bundle = delayed
from nicegui_app.main import run
run()
''', encoding="utf-8")
    output = (scratch / "server.log").open("w", encoding="utf-8")
    process = subprocess.Popen([sys.executable, "-X", "utf8", str(runner)],
        cwd=ROOT, env=environment, stdout=output, stderr=subprocess.STDOUT, text=True)
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
                    with page.expect_download(timeout=45_000) as received:
                        dialog.get_by_test_id("prepare-roster-images").click()
                        progress = dialog.get_by_test_id("roster-export-feedback")
                        expect(progress).to_be_visible(timeout=5000)
                        expect(progress).to_contain_text(MESSAGES["progress_roster_image_title"][ZH_HK])
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
                    received.value.delete()
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
                    "postVerificationSource": _source_state(refresh_fingerprint=True),
                    "fixtureRenderDelaySeconds": 1.5,
                }, indent=2), encoding="utf-8")
                print(f"PASS {scratch / 'report.json'}", flush=True)
            finally:
                browser.close()
    finally:
        _stop_server(process, output)


if __name__ == "__main__":
    main()
