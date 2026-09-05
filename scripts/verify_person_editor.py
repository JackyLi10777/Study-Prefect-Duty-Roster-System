"""Run the reusable person editor against fresh fictional, temporary data.

Usage: python -X utf8 scripts/verify_person_editor.py
This functional/DOM-lifecycle smoke never uses a configured production database
and is not a throttled performance baseline or a complete release gate.
"""
import os
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.extend([str(ROOT / "packages/roster_policy"), str(ROOT / "packages/roster_core")])
from scripts.verify_release_candidate import isolated_environment, _free_loopback_port, _start_server, _wait_until_ready, _stop_server


def main() -> None:
    scratch = Path(tempfile.mkdtemp(prefix="sy-person-editor-"))
    environment = isolated_environment(scratch, _free_loopback_port())
    environment["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(ROOT / "packages/roster_policy"), str(ROOT / "packages/roster_core")])
    os.environ.update(environment)
    from nicegui_app.services.roster_workflow import RosterWorkflow, PrefectInput, PrefectPatch
    from playwright.sync_api import sync_playwright, expect

    workflow = RosterWorkflow(database_path=Path(environment["SING_YIN_DATABASE_PATH"]), backup_dir=Path(environment["SING_YIN_BACKUP_DIR"]), seed_path=None)
    workflow.bootstrap()
    for index in range(22):
        workflow.create_prefect(PrefectInput(name_zh=f"虛構編輯{chr(0x4e00 + index)}", name_en=None, form="F.4", class_name="4A", role_code="assistant_head" if index == 1 else "study_prefect", available_days=("MONDAY", "WEDNESDAY"), fixed_general_duty="NONE", needs_mentoring=False, remarks=""), command_id=f"{environment['SING_YIN_E2E_RUN_ID']}:person:{index}")
    people = workflow.prefects()
    ids = {str(row["nameZh"]): str(row["id"]) for row in people}
    process, output = _start_server(environment, scratch / "server.log")
    print("ISOLATED", scratch, flush=True)
    try:
        _wait_until_ready(process, environment["SING_YIN_TEST_URL"], scratch / "server.log")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            try:
                page = browser.new_page(viewport={"width": 390, "height": 844})
                errors = []
                page.on("pageerror", lambda error: (errors.append(str(error)), print("PAGEERROR", str(error), flush=True)))
                page.on("console", lambda message: (errors.append(message.text), print("CONSOLE", message.text, flush=True)) if message.type == "error" else None)
                page.goto(environment["SING_YIN_TEST_URL"] + "/prefects", wait_until="networkidle")
                page.wait_for_function("window.did_handshake === true")
                expect(page.locator("article[data-prefect-id]")).to_have_count(20)
                expect(page.get_by_test_id("prefect-filter-sheet")).to_have_count(0)
                filter_keys = ("form", "role", "support", "sort")
                for key in filter_keys:
                    expect(page.get_by_test_id(f"prefect-filter-{key}")).to_have_count(0)
                reflow = {}
                for width in (256, 320, 390):
                    page.set_viewport_size({"width": width, "height": 844})
                    measurements = page.evaluate("""() => ({
                        documentOverflow: Math.max(0, document.documentElement.scrollWidth - innerWidth),
                        cardOverflow: Math.max(...[...document.querySelectorAll('article[data-prefect-id]')].map(card =>
                            Math.max(0, card.scrollWidth - card.clientWidth, card.getBoundingClientRect().right - innerWidth)))
                    })""")
                    reflow[str(width)] = measurements
                    page.screenshot(path=str(scratch / f"directory-{width}.png"), full_page=True)
                    assert measurements == {"documentOverflow": 0, "cardOverflow": 0}, measurements
                page.get_by_test_id("open-prefect-filters").click()
                filter_sheet = page.get_by_test_id("prefect-filter-sheet")
                expect(filter_sheet).to_be_visible()
                filter_ids = {key: page.get_by_test_id(f"prefect-filter-{key}").get_attribute("id") for key in filter_keys}
                for key in filter_keys:
                    page.get_by_test_id(f"prefect-filter-{key}").click()
                    page.get_by_role("option").nth(1).click()
                    expect(page.get_by_test_id("prefect-filter-summary")).to_have_text("已啟用 1 項")
                    page.get_by_test_id(f"prefect-filter-{key}").click()
                    page.get_by_role("option").nth(0).click()
                    expect(page.get_by_test_id("prefect-filter-summary")).to_have_text("已啟用 0 項")
                page.screenshot(path=str(scratch / "filters.png"), full_page=True)
                page.get_by_test_id("close-prefect-filters").click()
                expect(filter_sheet).not_to_be_visible()
                for _ in range(20):
                    page.get_by_test_id("open-prefect-filters").click()
                    expect(filter_sheet).to_be_visible()
                    assert {key: page.get_by_test_id(f"prefect-filter-{key}").get_attribute("id") for key in filter_keys} == filter_ids
                    page.get_by_test_id("close-prefect-filters").click()
                    expect(filter_sheet).not_to_be_visible()
                expect(page.locator("article[data-prefect-id]")).to_have_count(20)
                first_id = ids["虛構編輯一"]
                second_id = ids["虛構編輯丁"]
                sheet = page.get_by_test_id("prefect-editor-sheet")
                page.get_by_test_id(f"edit-prefect-{first_id}").click()
                expect(sheet).to_be_visible()
                page.evaluate("window.__firstEditorInput = document.querySelector('[data-editor-field=remarks] input')")
                sheet.locator('[data-editor-field="remarks"] input').fill("最後一字測試")
                sheet.get_by_test_id("close-prefect-editor").click()
                expect(sheet).not_to_be_visible()
                search = page.get_by_test_id("prefect-directory-search")
                search.fill("虛構編輯一")
                expect(page.locator("article[data-prefect-id]")).to_have_count(1)
                page.get_by_test_id("open-prefect-filters").click()
                page.get_by_test_id("prefect-filter-sort").click()
                page.get_by_role("option", name="姓名 Z–A", exact=True).click()
                page.get_by_test_id("close-prefect-filters").click()
                expect(filter_sheet).not_to_be_visible()
                page.get_by_test_id("clear-prefect-filters").click()
                expect(search).to_have_value("虛構編輯一")
                expect(page.get_by_test_id("prefect-filter-summary")).to_have_text("已啟用 0 項")
                expect(page.get_by_test_id("save-prefect-inline-changes")).to_be_enabled()
                search.fill("")
                expect(page.locator("article[data-prefect-id]")).to_have_count(20)
                page.wait_for_timeout(300)
                page.get_by_test_id(f"edit-prefect-{second_id}").click()
                expect(sheet.locator('[data-editor-field="remarks"] input')).to_have_value("")
                assert page.evaluate("window.__firstEditorInput.isSameNode(document.querySelector('[data-editor-field=remarks] input'))")
                expect(sheet.locator('[data-editor-field="fixedGeneralDuty"]')).to_be_visible()
                sheet.locator('[data-editor-field="fixedGeneralDuty"] select').select_option("MONDAY")
                expect(sheet.locator('[data-editor-field="fixedGeneralDuty"] select')).to_have_value("MONDAY")
                sheet.get_by_test_id("close-prefect-editor").click()
                expect(sheet).not_to_be_visible()
                page.get_by_test_id(f"edit-prefect-{first_id}").click()
                expect(sheet.locator('[data-editor-field="remarks"] input')).to_have_value("最後一字測試")
                expect(sheet.locator('[data-editor-field="fixedGeneralDuty"]')).not_to_be_visible()
                page.screenshot(path=str(scratch / "editor.png"), full_page=True)
                sheet.get_by_test_id("close-prefect-editor").click()
                expect(sheet).not_to_be_visible()
                cdp = page.context.new_cdp_session(page)
                cdp.send("HeapProfiler.collectGarbage")
                before = cdp.send("Memory.getDOMCounters")
                for index in range(20):
                    person_id = second_id if index % 2 == 0 else first_id
                    page.get_by_test_id(f"edit-prefect-{person_id}").click()
                    expect(sheet).to_be_visible()
                    assert page.evaluate("window.__firstEditorInput.isSameNode(document.querySelector('[data-editor-field=remarks] input'))")
                    sheet.get_by_test_id("close-prefect-editor").click()
                    expect(sheet).not_to_be_visible()
                cdp.send("HeapProfiler.collectGarbage")
                after = cdp.send("Memory.getDOMCounters")
                evidence = {"before": before, "after": after, "cycles": 20, "sameInputNode": True}
                print("CYCLES", json.dumps(evidence), flush=True)
                assert after["nodes"] - before["nodes"] <= 100, evidence
                assert after["jsEventListeners"] - before["jsEventListeners"] <= 40, evidence
                page.get_by_test_id("save-prefect-inline-changes").click()
                expect(page.get_by_test_id("save-prefect-inline-changes")).to_be_disabled()
                expect(page.get_by_text("所有行內欄位均已保存", exact=True)).to_be_visible()
                assert workflow.prefect(first_id)["remarks"] == "最後一字測試"
                page.get_by_test_id(f"edit-prefect-{first_id}").click()
                remarks = sheet.locator('[data-editor-field="remarks"] input')
                remarks.dispatch_event("compositionstart", {"data": "中"})
                remarks.fill("中文輸入完成")
                sheet.get_by_test_id("close-prefect-editor").click()
                expect(sheet).to_be_visible()
                remarks.dispatch_event("compositionend", {"data": "中文輸入完成"})
                expect(sheet).not_to_be_visible()
                page.get_by_test_id(f"edit-prefect-{first_id}").click()
                expect(sheet.locator('[data-editor-field="remarks"] input')).to_have_value("中文輸入完成")
                page.keyboard.press("Escape")
                expect(sheet).not_to_be_visible()
                page.get_by_test_id(f"edit-prefect-{first_id}").click()
                expect(sheet).to_be_visible()
                page.mouse.click(4, 4)
                expect(sheet).not_to_be_visible()
                page.get_by_test_id(f"edit-prefect-{first_id}").click()
                sheet.get_by_role("button", name="完整編輯", exact=True).click()
                full_name = page.get_by_label("中文姓名", exact=True)
                expect(full_name).to_be_visible()
                expect(full_name).to_have_value("虛構編輯一")
                assert workflow.prefect(first_id)["remarks"] == "中文輸入完成"
                page.get_by_role("button", name="取消", exact=True).click()
                page.get_by_test_id(f"edit-prefect-{first_id}").click()
                sheet.locator('[data-editor-field="remarks"] input').fill("待保存的本頁修改")
                sheet.get_by_test_id("close-prefect-editor").click()
                expect(sheet).not_to_be_visible()
                workflow.patch_prefects_batch((PrefectPatch(first_id, {"remarks": "另一個視窗更新"}, int(workflow.prefect(first_id)["version"])),), command_id=f"{environment['SING_YIN_E2E_RUN_ID']}:conflict")
                page.get_by_test_id(f"edit-prefect-{first_id}").click()
                sheet.get_by_role("button", name="完整編輯", exact=True).click()
                expect(sheet).not_to_be_visible()
                expect(page.get_by_test_id("prefect-directory-search")).to_be_focused()
                assert workflow.prefect(first_id)["remarks"] == "另一個視窗更新"
                page.get_by_role("tab", name="資料匯入", exact=True).click()
                page.get_by_role("tab", name="名單管理", exact=True).click()
                expect(sheet).not_to_be_visible()
                page.get_by_test_id("prefect-load-more").click()
                expect(page.locator("article[data-prefect-id]")).to_have_count(2)
                # A separate tab write must not become the reviewed archive version.
                page.reload(wait_until="networkidle")
                page.wait_for_function("window.did_handshake === true")
                selected = page.get_by_label("選擇風紀", exact=True)
                selected.click()
                page.get_by_role("option", name="虛構編輯一 (F.4 4A)", exact=True).click()
                workflow.patch_prefects_batch((PrefectPatch(first_id, {"remarks": "封存前的外部分頁更新"}, int(workflow.prefect(first_id)["version"])),), command_id=f"{environment['SING_YIN_E2E_RUN_ID']}:archive-conflict")
                page.get_by_test_id("open-archive-prefect").click()
                page.get_by_test_id("confirm-archive-prefect").click()
                expect(page.get_by_text("這份風紀資料已在另一個分頁更新。請重新整理，核對最新內容後再儲存。", exact=True)).to_be_visible()
                assert first_id in {row["id"] for row in workflow.prefects()}
                # The same page's own final snapshot and atomic flush may advance CAS.
                page.reload(wait_until="networkidle")
                page.wait_for_function("window.did_handshake === true")
                page.get_by_label("選擇風紀", exact=True).click()
                page.get_by_role("option", name="虛構編輯一 (F.4 4A)", exact=True).click()
                page.get_by_test_id(f"edit-prefect-{first_id}").click()
                sheet.locator('[data-editor-field="remarks"] input').fill("本頁儲存後封存")
                sheet.get_by_test_id("close-prefect-editor").click()
                expect(sheet).not_to_be_visible()
                page.get_by_test_id("open-archive-prefect").click()
                expect(page.get_by_test_id("confirm-archive-prefect")).to_be_visible()
                assert workflow.prefect(first_id)["remarks"] == "本頁儲存後封存"
                page.get_by_test_id("confirm-archive-prefect").click()
                expect(page.get_by_test_id(f"edit-prefect-{first_id}")).to_have_count(0)
                assert first_id not in {row["id"] for row in workflow.prefects()}
                assert not errors, errors
                report = {"runId": environment["SING_YIN_E2E_RUN_ID"], "status": "pass", "cycles": evidence, "filterControlsReused": True, "filterCycles": 20, "reflow": reflow, "archiveCas": "external-conflict-and-own-flush-pass", "consoleErrors": errors}
                (scratch / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
                print("PASS: 20-row batch, A/B/A ownership, final text, role fields, atomic save, IME, Escape/backdrop, full edit identity/conflict focus, tab remount, next batch, console", flush=True)
            except Exception as error:
                page.screenshot(path=str(scratch / "failure.png"), full_page=True)
                (scratch / "failure.json").write_text(json.dumps({"error": str(error), "consoleErrors": errors}, indent=2), encoding="utf-8")
                raise
            finally:
                browser.close()
    finally:
        _stop_server(process, output)



if __name__ == "__main__":
    main()
