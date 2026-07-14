"""Exercise the complete roster write pipeline against explicitly isolated data."""

from __future__ import annotations

from datetime import date
from io import BytesIO
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
from zipfile import ZipFile

from playwright.sync_api import Page, sync_playwright
from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.services.roster_workflow import RosterWorkflow
from roster_core import Prefect, generate_weekly_roster
from roster_policy import PrefectRole, SchoolDay


BASE_URL = os.getenv("SING_YIN_TEST_URL", "http://127.0.0.1:8080")
WEEK_START = date(2026, 9, 7)
CANONICAL_LIVE_DATABASE = PROJECT_ROOT / "data" / "runtime" / "sing-yin-roster.sqlite3"
CANONICAL_BACKUP_DIRECTORY = PROJECT_ROOT / "data" / "backups"
LIGHT_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-write-pipeline-light.png"
DARK_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-write-pipeline-dark.png"
MOBILE_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-write-pipeline-mobile.png"
MOBILE_FORMS_DARK_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-write-pipeline-mobile-forms-dark.png"
MOBILE_FORMS_LIGHT_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-write-pipeline-mobile-forms-light.png"
MOBILE_DIRECTORY_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-write-pipeline-mobile-directory.png"
PREFECT_ARCHIVE_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-prefect-archive-confirmation.png"

NATIVE_PDF_SHARE_STUB = """
Object.defineProperty(navigator, 'canShare', {
    configurable: true,
    value: (payload) => Boolean(payload?.files?.length),
});
Object.defineProperty(navigator, 'share', {
    configurable: true,
    value: async (payload) => {
        const file = payload.files[0];
        const bytes = new Uint8Array(await file.arrayBuffer());
        window.__singYinSharedPdf = {
            filename: file.name,
            size: file.size,
            type: file.type,
            header: String.fromCharCode(...bytes.slice(0, 4)),
        };
    },
});
"""


def isolated_paths() -> tuple[Path, Path, Path]:
    """Refuse to run unless all persistent locations were explicitly isolated."""
    if os.getenv("SING_YIN_E2E_ISOLATED") != "1":
        raise RuntimeError("Set SING_YIN_E2E_ISOLATED=1 before running a write-pipeline browser test.")
    e2e_run_id = os.getenv("SING_YIN_E2E_RUN_ID", "").strip()
    if not re.fullmatch(r"E2E-[A-F0-9]{12}", e2e_run_id):
        raise RuntimeError("Set a unique SING_YIN_E2E_RUN_ID before running a write-pipeline browser test.")
    required = ("SING_YIN_DATABASE_PATH", "SING_YIN_BACKUP_DIR", "SING_YIN_LOG_DIR")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing isolated path configuration: {', '.join(missing)}")
    database_path = Path(os.environ["SING_YIN_DATABASE_PATH"]).resolve()
    backup_dir = Path(os.environ["SING_YIN_BACKUP_DIR"]).resolve()
    log_dir = Path(os.environ["SING_YIN_LOG_DIR"]).resolve()
    if database_path == CANONICAL_LIVE_DATABASE.resolve() or backup_dir == CANONICAL_BACKUP_DIRECTORY.resolve():
        raise RuntimeError("Write-pipeline verification must not use the default school database or backup directory.")
    return database_path, backup_dir, log_dir


def _workflow(database_path: Path, backup_dir: Path) -> RosterWorkflow:
    workflow = RosterWorkflow(
        database_path=database_path,
        backup_dir=backup_dir,
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    return workflow


def _select_option(page: Page, label: str, option_text: str) -> None:
    field = page.locator(".q-field").filter(has_text=label).first
    field.click()
    page.get_by_text(option_text, exact=True).last.click()


def _wait_for_progress_cycle(page: Page) -> None:
    """Wait for one new operation dialog and its one-shot cleanup."""
    dialog = page.locator(".sy-progress-dialog")
    dialog.wait_for(state="visible", timeout=10_000)
    dialog.wait_for(state="hidden", timeout=20_000)
    dialog.wait_for(state="detached", timeout=10_000)


def _click_mobile_drawer_tool(page: Page, index: int, *, expects_navigation: bool = True) -> None:
    """Use the real phone preference path instead of hidden desktop controls."""
    navigation = page.get_by_test_id("mobile-bottom-navigation")
    navigation.locator(".sy-mobile-tab").last.click()
    drawer = page.locator("#main-navigation-drawer")
    drawer.wait_for(state="visible", timeout=10_000)
    tools = drawer.get_by_test_id("mobile-drawer-tools").locator(".sy-mobile-drawer-tool")
    if tools.count() <= index:
        raise AssertionError(f"Mobile drawer preference {index} is unavailable.")
    if expects_navigation:
        with page.expect_navigation(wait_until="domcontentloaded", timeout=15_000):
            tools.nth(index).click()
    else:
        tools.nth(index).click()
    page.wait_for_load_state("networkidle")


def _fixture_leave_prefect() -> tuple[str, str]:
    """Pick a seeded Monday assignment without writing a preliminary draft."""
    import json

    raw_prefects = json.loads(PREFECT_SEED_PATH.read_text(encoding="utf-8"))["prefects"]
    prefects = [
        Prefect(
            id=str(item["id"]),
            name=str(item["name"]),
            form=str(item["form"]),
            class_name=str(item["class"]),
            role=(
                PrefectRole.ASSISTANT_HEAD
                if "Assistant Head Study Prefect" in str(item["role"])
                else PrefectRole.STUDY_PREFECT
            ),
            available_days=frozenset(SchoolDay[str(day)] for day in item["availableDays"]),
            history_weight=float(item.get("historyWeight", 0)),
            history_duties=int(item.get("historyDuties", 0)),
            needs_mentoring=bool(item.get("needsMentoring", False)),
            fixed_general_duty=str(item.get("fixedGeneralDuty", "NONE")),
            remarks=str(item.get("remarks", "")),
        )
        for item in raw_prefects
    ]
    assignments = generate_weekly_roster(prefects)
    assignment = next(item for item in assignments if item.day is SchoolDay.MONDAY)
    return assignment.prefect_id, assignment.prefect_name


def _assignment_label(assignment: dict[str, object]) -> str:
    day_labels = {
        "MONDAY": "星期一",
        "TUESDAY": "星期二",
        "WEDNESDAY": "星期三",
        "THURSDAY": "星期四",
        "FRIDAY": "星期五",
    }
    post_labels = {
        "ASSIST_IN_CHARGE": "助理首席導學風紀當值",
        "ROOM_302": "302 室（自修室）",
        "ROOM_303": "303 室（功課完成室）",
        "ROOM_202": "202 室（F.1 自修小組）",
    }
    return f"{day_labels[str(assignment['day'])]} | {post_labels[str(assignment['postCode'])]} | {assignment['prefectName']}"


def _candidate_label(candidate: dict[str, object]) -> str:
    return f"{candidate['nameZh']} ({candidate['form']} {candidate['className']}; {float(candidate['historyWeight']):.1f})"


def _audit_event_types(database_path: Path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        return {str(row[0]) for row in connection.execute("SELECT event_type FROM audit_events")}


def _assert_schedule_pdf(content: bytes, *, english: bool, expected_name: str) -> None:
    reader = PdfReader(BytesIO(content))
    assert len(reader.pages) == 1
    page = reader.pages[0]
    assert float(page.mediabox.width) > float(page.mediabox.height)
    text = "\n".join(item.extract_text() for item in reader.pages)
    assert expected_name in text
    assert ("Sing Yin Secondary School" if english else "聖言中學") in text
    day_labels = (
        ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY")
        if english
        else ("星期一", "星期二", "星期三", "星期四", "星期五")
    )
    for label in day_labels:
        assert label in text
    assert ("Published" if english else "已發布") in text
    assert text.count("Closed" if english else "不開放") == 4


def main() -> None:
    database_path, backup_dir, log_dir = isolated_paths()
    e2e_run_id = os.environ["SING_YIN_E2E_RUN_ID"].strip()
    print("[1/7] Starting isolated browser write-pipeline verification", flush=True)
    artifacts_dir = database_path.parent / "write-pipeline-artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    LIGHT_SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    leave_prefect_id, leave_prefect_name = _fixture_leave_prefect()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1024}, accept_downloads=True)
        page.add_init_script(NATIVE_PDF_SHARE_STUB)
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        health_response = page.request.get(f"{BASE_URL}/healthz")
        assert health_response.status == 200
        assert health_response.json().get("e2eRunId") == e2e_run_id, (
            "Write verification connected to a different server; no browser write was attempted."
        )
        first_response = page.goto(f"{BASE_URL}/prefects", wait_until="networkidle")
        assert first_response is not None
        request_reference = first_response.headers.get("x-request-id", "")
        assert re.fullmatch(r"REQ-[A-F0-9]{8}", request_reference)
        page.get_by_text("資料匯入", exact=True).click()
        page.locator("textarea").fill(
            "姓名,級別,班別,職務,可值班日\n"
            "虛構驗證風紀,F.3,3T,導學風紀,星期五"
        )
        page.get_by_role("button", name="驗證與預覽").click()
        page.get_by_text("資料已通過驗證，可安全匯入。", exact=True).wait_for(timeout=10_000)
        page.get_by_role("button", name="匯入風紀").click()
        page.locator(".sy-progress-dialog").wait_for(state="visible", timeout=10_000)
        page.get_by_text("名單管理", exact=True).wait_for(timeout=10_000)
        page.locator(".sy-responsive-table-desktop:visible td", has_text="虛構驗證風紀").wait_for(
            timeout=10_000
        )
        page.locator(".sy-progress-dialog").wait_for(state="hidden", timeout=20_000)
        page.locator(".sy-progress-dialog").wait_for(state="detached", timeout=10_000)
        workflow = _workflow(database_path, backup_dir)
        assert any(item["nameZh"] == "虛構驗證風紀" for item in workflow.prefects())

        page.get_by_role("button", name="新增風紀").click()
        page.get_by_role("button", name="儲存", exact=True).click()
        page.get_by_text("請先填寫中文姓名。", exact=True).wait_for(timeout=10_000)
        assert page.locator(".sy-progress-dialog").count() == 0
        page.get_by_label("中文姓名").fill("虛構非阻塞風紀")
        page.get_by_label("班別").fill("3U")
        _select_option(page, "可值班日", "星期一")
        _select_option(page, "可值班日", "星期三")
        page.get_by_role("button", name="儲存", exact=True).click()
        _wait_for_progress_cycle(page)
        page.get_by_text("虛構非阻塞風紀", exact=True).first.wait_for(timeout=15_000)

        workflow = _workflow(database_path, backup_dir)
        created_prefect = next(item for item in workflow.prefects() if item["nameZh"] == "虛構非阻塞風紀")
        _select_option(page, "選擇風紀", "虛構非阻塞風紀 (F.3 3U)")
        page.get_by_role("button", name="編輯風紀").click()
        page.get_by_label("備註").fill("虛構非阻塞修改")
        page.get_by_role("button", name="儲存", exact=True).click()
        _wait_for_progress_cycle(page)
        page.get_by_text("名單管理", exact=True).wait_for(timeout=15_000)
        workflow = _workflow(database_path, backup_dir)
        assert workflow.prefect(str(created_prefect["id"]))["remarks"] == "虛構非阻塞修改"

        _select_option(page, "選擇風紀", "虛構非阻塞風紀 (F.3 3U)")
        page.get_by_test_id("open-archive-prefect").click()
        page.get_by_text("確認停用這位風紀？", exact=True).wait_for(timeout=10_000)
        page.get_by_text("歷史週表、公平帳本及審計紀錄會完整保留", exact=False).wait_for(timeout=10_000)
        page.screenshot(path=str(PREFECT_ARCHIVE_SCREENSHOT), full_page=False)
        page.get_by_test_id("confirm-archive-prefect").click()
        _wait_for_progress_cycle(page)
        page.get_by_text("名單管理", exact=True).wait_for(timeout=15_000)
        workflow = _workflow(database_path, backup_dir)
        assert created_prefect["id"] not in {item["id"] for item in workflow.prefects()}
        assert {"prefect_created", "prefect_updated", "prefect_archived"} <= _audit_event_types(database_path)
        print("[2/7] Imported, created, edited, and confirmation-archived fictional prefect data through the UI", flush=True)

        workflow = _workflow(database_path, backup_dir)
        leave_prefect = workflow.prefect(leave_prefect_id)
        leave_prefect_option = f"{leave_prefect_name} ({leave_prefect['form']} {leave_prefect['className']})"

        page.goto(f"{BASE_URL}/rosters", wait_until="commit", timeout=10_000)
        page.get_by_role("button", name="生成並儲存草稿").wait_for(timeout=10_000)
        page.locator('input[type="date"]').fill("2026-09-08")
        page.get_by_role("button", name="生成並儲存草稿").click()
        page.get_by_text("週開始日期必須是星期一。", exact=True).wait_for(timeout=10_000)
        assert page.locator(".sy-progress-dialog").count() == 0
        page.locator('input[type="date"]').fill(WEEK_START.isoformat())
        _select_option(page, "選擇風紀", leave_prefect_option)
        _select_option(page, "請假日", "星期一")
        assert page.get_by_label("請假原因（選填）").count() == 1
        page.get_by_role("button", name="登記請假").click()
        _wait_for_progress_cycle(page)
        page.get_by_text("已登記請假", exact=False).wait_for(timeout=10_000)
        page.get_by_role("button", name="生成並儲存草稿").click()
        page.locator(".sy-progress-dialog").wait_for(state="visible", timeout=10_000)
        deadline = time.monotonic() + 20
        generated_weeks: list[dict[str, object]] = []
        while time.monotonic() < deadline:
            generated_weeks = _workflow(database_path, backup_dir).roster_weeks()
            if generated_weeks:
                break
            time.sleep(0.1)
        assert generated_weeks, "The browser generation action did not persist a draft."
        roster_week_id = int(generated_weeks[0]["id"])
        backup_deadline = time.monotonic() + 20
        while time.monotonic() < backup_deadline and not any(backup_dir.glob("*-draft_generated.manifest.json")):
            time.sleep(0.1)
        assert any(backup_dir.glob("*-draft_generated.manifest.json")), "Draft generation did not finish its verified backup."
        page.evaluate("window.stop()")
        browser.close()
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1024}, accept_downloads=True)
        page.add_init_script(NATIVE_PDF_SHARE_STUB)
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        health_response = page.request.get(f"{BASE_URL}/healthz")
        assert health_response.status == 200 and health_response.json().get("e2eRunId") == e2e_run_id
        page.goto(f"{BASE_URL}/rosters/{roster_week_id}", wait_until="domcontentloaded")
        page.get_by_text("草稿預覽", exact=True).wait_for(timeout=10_000)
        print("[3/7] Recorded leave and generated a draft through the UI", flush=True)

        workflow = _workflow(database_path, backup_dir)
        week = workflow.roster_weeks()[0]
        assert int(week["id"]) == roster_week_id
        declared = workflow.pre_generation_leaves(WEEK_START)
        assert {item["prefectId"] for item in declared} == {leave_prefect_id}
        assert declared[0]["reason"] is None
        assert all(
            not (item["prefectId"] == leave_prefect_id and item["day"] == "MONDAY")
            for item in workflow.assignments(roster_week_id)
        )

        manual_assignment = workflow.assignments(roster_week_id)[0]
        manual_candidate = workflow.draft_assignment_candidates(roster_week_id, int(manual_assignment["id"]))[0]
        before_publish_loads = workflow.prefect_loads()
        page.get_by_role("button", name="載入合資格人選").click()
        page.locator(".q-notification").filter(has_text="合資格替補").last.wait_for(timeout=10_000)
        _select_option(page, "替補風紀", _candidate_label(manual_candidate))
        page.get_by_role("button", name="儲存草稿修改").click()
        page.get_by_text("請先填寫草稿修改原因。", exact=True).wait_for(timeout=10_000)
        assert page.locator(".sy-progress-dialog").count() == 0
        log_content = (log_dir / "app.log").read_text(encoding="utf-8")
        assert "progress_draft_change_working" not in log_content

        page.get_by_label("修改原因（必填）").fill("虛構草稿核對修正")
        with page.expect_navigation(wait_until="networkidle", timeout=20_000):
            page.get_by_role("button", name="儲存草稿修改").click()
        page.get_by_text("草稿預覽", exact=True).wait_for(timeout=10_000)
        workflow = _workflow(database_path, backup_dir)
        changed_assignment = next(item for item in workflow.assignments(roster_week_id) if item["id"] == manual_assignment["id"])
        assert changed_assignment["prefectId"] == manual_candidate["id"]
        assert workflow.prefect_loads() == before_publish_loads
        log_content = (log_dir / "app.log").read_text(encoding="utf-8")
        assert "progress_draft_change_working" in log_content
        assert "虛構草稿核對修正" not in log_content
        print("[4/7] Rejected a missing manual-change reason, then saved an auditable correction", flush=True)

        page.goto(f"{BASE_URL}/rosters/{roster_week_id}/adjustments", wait_until="networkidle")
        premature_adjustment = page.get_by_test_id("adjustment-unavailable-state")
        premature_adjustment.wait_for(timeout=10_000)
        assert page.locator(".sy-adjustment-form").count() == 0
        premature_adjustment.get_by_role("button", name="返回這份週表").click()
        page.wait_for_url(f"**/rosters/{roster_week_id}", timeout=10_000)
        page.get_by_text("草稿預覽", exact=True).wait_for(timeout=10_000)

        page.get_by_role("button", name="發布週表").click()
        page.get_by_text("確認發布週表", exact=True).wait_for(timeout=10_000)
        with page.expect_navigation(wait_until="networkidle", timeout=20_000):
            page.get_by_role("button", name="確認發布並入帳").click()
        page.get_by_role("button", name="處理請假調整").first.wait_for(timeout=10_000)
        page.screenshot(path=str(LIGHT_SCREENSHOT), full_page=True)
        workflow = _workflow(database_path, backup_dir)
        published = workflow.roster_week(roster_week_id)
        assert published["status"] == "published"
        after_publish_loads = workflow.prefect_loads()
        assert sum(after_publish_loads.values()) - sum(before_publish_loads.values()) == 34.0
        print("[5/7] Published once and verified fairness-ledger posting", flush=True)

        page.get_by_role("button", name="下載列印版 PDF").click()
        page.get_by_text("選擇 PDF 匯出", exact=True).wait_for(timeout=10_000)
        expected_name = str(workflow.assignments(roster_week_id)[0]["prefectName"])
        page.get_by_role("button", name="準備中文週表 PDF").click()
        page.get_by_test_id("pdf-delivery-ready").wait_for(timeout=20_000)
        # Some full-page NiceGUI transitions replace the browsing context in
        # Chromium. Reinstall the deterministic test-only native-share target
        # immediately before exercising the real client click handler.
        page.evaluate(f"() => {{ {NATIVE_PDF_SHARE_STUB} }}")
        page.get_by_test_id("share-schedule-pdf").click()
        page.wait_for_timeout(1_000)
        shared_pdf = page.evaluate("window.__singYinSharedPdf")
        assert shared_pdf is not None, {
            "navigatorCanShare": page.evaluate("typeof navigator.canShare"),
            "navigatorShare": page.evaluate("typeof navigator.share"),
            "consoleErrors": console_errors,
            "pageErrors": page_errors,
        }
        assert shared_pdf["type"] == "application/pdf"
        assert shared_pdf["header"] == "%PDF"
        assert shared_pdf["filename"].endswith(f"_v{published['version']}_中文.pdf")
        assert shared_pdf["size"] > 0
        with page.expect_download(timeout=20_000) as chinese_download_info:
            page.get_by_test_id("download-prepared-pdf").click()
        chinese_download = chinese_download_info.value
        chinese_path = artifacts_dir / chinese_download.suggested_filename
        chinese_download.save_as(chinese_path)
        assert shared_pdf["size"] == chinese_path.stat().st_size
        _assert_schedule_pdf(chinese_path.read_bytes(), english=False, expected_name=expected_name)
        page.get_by_role("button", name="取消").last.click()

        page.get_by_role("button", name="下載列印版 PDF").click()
        page.get_by_role("button", name="準備英文週表 PDF").click()
        page.get_by_test_id("pdf-delivery-ready").wait_for(timeout=20_000)
        with page.expect_download(timeout=20_000) as english_download_info:
            page.get_by_test_id("download-prepared-pdf").click()
        english_download = english_download_info.value
        english_path = artifacts_dir / english_download.suggested_filename
        english_download.save_as(english_path)
        _assert_schedule_pdf(english_path.read_bytes(), english=True, expected_name=expected_name)
        page.get_by_role("button", name="取消").last.click()
        print("[6/7] Downloaded and inspected Chinese and English schedule PDFs", flush=True)

        adjustment_assignment = workflow.assignments(roster_week_id)[0]
        replacement = workflow.recommend_substitutes(roster_week_id, int(adjustment_assignment["id"]))[0]
        page.get_by_role("button", name="處理請假調整").first.click()
        page.get_by_text("請假調整", exact=True).last.wait_for(timeout=10_000)
        page.get_by_role("button", name="載入合資格替補").click()
        page.locator(".q-notification").filter(has_text="合資格替補").last.wait_for(timeout=10_000)
        _select_option(page, "替補風紀", _candidate_label(replacement))
        page.get_by_role("button", name="儲存請假調整").click()
        page.get_by_text("請先填寫調整原因", exact=False).wait_for(timeout=10_000)
        page.get_by_label("調整原因").fill("虛構已發布後請假")
        page.get_by_role("button", name="儲存請假調整").click()
        page.get_by_text("請假調整已完成", exact=True).wait_for(timeout=20_000)
        page.get_by_text("先前下載或已發出的 PDF 不會自行更新", exact=False).wait_for(timeout=10_000)
        page.get_by_test_id("export-updated-roster").wait_for(timeout=10_000)
        workflow = _workflow(database_path, backup_dir)
        adjusted = next(item for item in workflow.assignments(roster_week_id) if item["id"] == adjustment_assignment["id"])
        adjusted_week = workflow.roster_week(roster_week_id)
        page.get_by_test_id("export-updated-roster").click()
        page.get_by_text("選擇 PDF 匯出", exact=True).wait_for(timeout=10_000)
        page.get_by_role("button", name="準備中文週表 PDF").click()
        page.get_by_test_id("pdf-delivery-ready").wait_for(timeout=20_000)
        page.get_by_test_id("share-schedule-pdf").click()
        page.wait_for_function(
            "expected => window.__singYinSharedPdf?.filename?.endsWith(expected)",
            arg=f"_v{adjusted_week['version']}_中文.pdf",
        )
        corrected_shared_pdf = page.evaluate("window.__singYinSharedPdf")
        with page.expect_download(timeout=20_000) as corrected_download_info:
            page.get_by_test_id("download-prepared-pdf").click()
        corrected_download = corrected_download_info.value
        corrected_path = artifacts_dir / corrected_download.suggested_filename
        corrected_download.save_as(corrected_path)
        assert corrected_shared_pdf["header"] == "%PDF"
        assert corrected_shared_pdf["size"] == corrected_path.stat().st_size
        _assert_schedule_pdf(
            corrected_path.read_bytes(),
            english=False,
            expected_name=str(replacement["nameZh"]),
        )
        page.get_by_role("button", name="取消").last.click()
        page.goto(f"{BASE_URL}/rosters/{roster_week_id}", wait_until="networkidle")
        page.get_by_text("已發布後有人請假？", exact=True).wait_for(timeout=10_000)

        after_adjustment_loads = workflow.prefect_loads()
        assert adjusted["prefectId"] == replacement["id"]
        assert after_adjustment_loads[str(adjustment_assignment["prefectId"])] == round(
            after_publish_loads[str(adjustment_assignment["prefectId"])] - float(adjustment_assignment["weight"]),
            4,
        )
        assert after_adjustment_loads[str(replacement["id"])] == round(
            after_publish_loads[str(replacement["id"])] + float(adjustment_assignment["weight"]),
            4,
        )
        assert workflow.leave_adjustment_count(roster_week_id) == 1
        assert {"draft_generated", "draft_assignment_changed", "roster_published", "leave_adjusted"} <= _audit_event_types(database_path)
        backup_inventory = workflow.backup_inventory()
        expected_invalid_backups = int(os.getenv("SING_YIN_EXPECT_INVALID_BACKUP_COUNT", "0"))
        assert int(backup_inventory["invalidCount"]) == expected_invalid_backups
        assert int(backup_inventory["verifiedCount"]) >= 1
        if expected_invalid_backups:
            assert backup_inventory["invalidReasonCounts"] == {"manifest_missing": expected_invalid_backups}
        log_content = (log_dir / "app.log").read_text(encoding="utf-8")
        assert f"trace={request_reference}" in log_content
        assert "event=http_request method=GET target=prefects status=200" in log_content
        assert "虛構已發布後請假" not in log_content

        page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        assert page.get_by_test_id("handover-package-ready-action").is_enabled()
        assert page.get_by_test_id("restore-ready-action").is_enabled()
        assert page.get_by_test_id("handover-package-disabled-no-backup").count() == 0
        assert page.get_by_test_id("restore-disabled-no-backup").count() == 0
        if int(os.getenv("SING_YIN_EXPECT_INVALID_BACKUP_COUNT", "0")):
            page.get_by_test_id("invalid-backup-summary").wait_for(timeout=10_000)
        page.get_by_role("button", name="建立交接備份包").click()
        page.get_by_text("建立交接備份包", exact=True).last.wait_for(timeout=10_000)
        with page.expect_download(timeout=20_000) as package_download_info:
            page.get_by_role("button", name="建立並下載交接備份包").click()
        package_download = package_download_info.value
        package_path = artifacts_dir / package_download.suggested_filename
        package_download.save_as(package_path)
        with ZipFile(package_path) as package:
            names = set(package.namelist())
            snapshot_name = next(name for name in names if name.endswith(".sqlite3"))
            manifest_name = next(name for name in names if name.endswith(".manifest.json"))
            assert "README.txt" in names

        recovery_root = database_path.parent / "write-pipeline-recovery"
        recovery_backups = recovery_root / "backups"
        recovery_backups.mkdir(parents=True, exist_ok=True)
        with ZipFile(package_path) as package:
            package.extract(snapshot_name, recovery_backups)
            package.extract(manifest_name, recovery_backups)
        recovery = RosterWorkflow(
            database_path=recovery_root / "recovered.sqlite3",
            backup_dir=recovery_backups,
        )
        recovery.bootstrap()
        restored = recovery.restore_backup(recovery_backups / snapshot_name)
        assert restored["restoredFrom"] == recovery_backups / snapshot_name
        assert recovery.roster_week(roster_week_id)["status"] == "published"
        assert recovery.leave_adjustment_count(roster_week_id) == 1
        print("[7/7] Applied leave adjustment, built handover package, and restored a separate database", flush=True)

        page.goto(f"{BASE_URL}/rosters/{roster_week_id}", wait_until="networkidle")
        desktop_theme_controls = page.locator(".sy-desktop-header-controls")
        if desktop_theme_controls.locator("i.q-icon", has_text="light_mode").count():
            desktop_theme_controls.locator("i.q-icon", has_text="light_mode").click()
            page.wait_for_load_state("networkidle")
        page.locator(".sy-desktop-header-controls").locator("i.q-icon", has_text="dark_mode").click()
        page.wait_for_function("document.body.classList.contains('body--dark')")
        page.screenshot(path=str(DARK_SCREENSHOT), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(f"{BASE_URL}/rosters/{roster_week_id}", wait_until="networkidle")
        page.get_by_text("已發布後有人請假？", exact=True).wait_for(timeout=10_000)
        mobile_cards = page.locator('[data-testid="mobile-roster-card"]')
        assert mobile_cards.count() == 26
        assert not page.locator(".sy-roster-desktop").is_visible()
        # A valid substitute may also be rostered on a non-consecutive day, so
        # require the persisted Chinese name to be visible without assuming it
        # appears in only one card.
        assert mobile_cards.filter(has_text=str(adjusted["prefectName"])).count() >= 1
        page.screenshot(path=str(MOBILE_SCREENSHOT), full_page=True)
        _click_mobile_drawer_tool(page, 0)
        page.wait_for_load_state("networkidle")
        page.get_by_text("Phone view:", exact=False).wait_for(timeout=10_000)
        english_mobile_cards = page.locator('[data-testid="mobile-roster-card"]')
        assert english_mobile_cards.count() == 26
        assert english_mobile_cards.filter(has_text=str(adjusted["prefectName"])).count() >= 1

        _click_mobile_drawer_tool(page, 0)
        page.wait_for_load_state("networkidle")
        page.goto(f"{BASE_URL}/prefects", wait_until="networkidle")
        page.get_by_text("名單管理", exact=True).wait_for(timeout=10_000)
        mobile_prefect_cards = page.locator('[data-testid="mobile-prefect-card"]')
        assert mobile_prefect_cards.count() == len(workflow.prefects())
        assert not page.locator(".sy-prefect-directory-desktop").is_visible()
        assert mobile_prefect_cards.filter(has_text="虛構驗證風紀").count() == 1
        page.screenshot(path=str(MOBILE_DIRECTORY_SCREENSHOT), full_page=True)

        page.goto(f"{BASE_URL}/rosters/{roster_week_id}/adjustments", wait_until="networkidle")
        page.get_by_text("請假調整", exact=True).last.wait_for(timeout=10_000)
        adjustment_steps = page.locator(".sy-adjustment-step")
        assert adjustment_steps.count() == 3
        assert page.locator(".sy-adjustment-form .q-field").count() == 3
        for button in page.locator(".sy-adjustment-actions .q-btn").all():
            box = button.bounding_box()
            assert box is not None and box["width"] >= 280 and box["height"] >= 44
        page.screenshot(path=str(MOBILE_FORMS_DARK_SCREENSHOT), full_page=True)
        _click_mobile_drawer_tool(page, 2, expects_navigation=False)
        page.wait_for_function("!document.body.classList.contains('body--dark')")
        page.screenshot(path=str(MOBILE_FORMS_LIGHT_SCREENSHOT), full_page=True)
        assert not console_errors, console_errors
        assert not page_errors, page_errors
        browser.close()

    print(f"Write-pipeline browser verification passed; artifacts: {artifacts_dir}")


if __name__ == "__main__":
    main()
