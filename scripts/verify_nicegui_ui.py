"""Browser smoke checks for the persistent NiceGUI shell and key routes."""

from __future__ import annotations

import os
import sqlite3
from http.client import HTTPConnection
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("SING_YIN_TEST_URL", "http://127.0.0.1:8080")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FAVICON_CREST_PATH = PROJECT_ROOT / "nicegui_app" / "assets" / "brand" / "sing-yin-crest-favicon.png"
LIGHT_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-dashboard-light.png"
DARK_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-dashboard-dark.png"
ROSTER_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-roster-workspace.png"
PREFECT_IMPORT_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-prefect-import.png"
MOBILE_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-dashboard-mobile.png"
ONBOARDING_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-getting-started.png"
PROGRESS_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-progress-dialog.png"
HANDOVER_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-handover-light.png"
HANDOVER_MOBILE_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-handover-mobile.png"
ARCHITECTURE_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-system-architecture.png"
ARCHITECTURE_DARK_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-system-architecture-dark.png"
ARCHITECTURE_MOBILE_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-system-architecture-mobile.png"
HOVER_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-pointer-hover.png"
MUSIC_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-page-music.png"
ROSTER_RECOVERY_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-roster-unavailable.png"


def assert_unexpected_host_rejected() -> None:
    """Verify the running NiceGUI app, not only the middleware helper, rejects an unapproved Host."""
    endpoint = urlsplit(BASE_URL)
    if endpoint.scheme != "http" or endpoint.hostname is None:
        raise RuntimeError("UI verification requires an explicit local HTTP endpoint.")
    connection = HTTPConnection(endpoint.hostname, endpoint.port or 80, timeout=3)
    try:
        connection.request("GET", "/", headers={"Host": "unexpected.invalid"})
        response = connection.getresponse()
        response.read()
    finally:
        connection.close()
    assert response.status == 400, "running NiceGUI accepted an unexpected Host header"


def prepare_invalid_backup_fixture() -> int:
    """Create one manifest-less snapshot only for an explicitly isolated UI run."""
    expected_count = int(os.getenv("SING_YIN_EXPECT_INVALID_BACKUP_COUNT", "0"))
    if expected_count == 0:
        return 0
    if expected_count != 1 or os.getenv("SING_YIN_E2E_ISOLATED") != "1":
        raise RuntimeError("Invalid-backup UI evidence requires one explicitly isolated fixture.")
    database_path = Path(os.environ["SING_YIN_DATABASE_PATH"]).resolve()
    backup_dir = Path(os.environ["SING_YIN_BACKUP_DIR"]).resolve()
    canonical_database = (PROJECT_ROOT / "data" / "runtime" / "sing-yin-roster.sqlite3").resolve()
    canonical_backups = (PROJECT_ROOT / "data" / "backups").resolve()
    if database_path == canonical_database or backup_dir == canonical_backups:
        raise RuntimeError("Invalid-backup UI evidence refuses canonical school storage.")
    backup_dir.mkdir(parents=True, exist_ok=True)
    invalid_snapshot = backup_dir / "ui-evidence-manifest-missing.sqlite3"
    invalid_snapshot.unlink(missing_ok=True)
    invalid_snapshot.with_suffix(".manifest.json").unlink(missing_ok=True)
    with sqlite3.connect(database_path) as source, sqlite3.connect(invalid_snapshot) as destination:
        source.backup(destination)
    return expected_count


def close_music_dialog(dialog) -> None:  # type: ignore[no-untyped-def]
    close_button = dialog.locator(".sy-music-dialog-header button").first
    close_button.click()
    dialog.wait_for(state="hidden", timeout=10_000)


def main() -> None:
    LIGHT_SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
    expected_invalid_backups = prepare_invalid_backup_fixture()
    assert_unexpected_host_rejected()
    console_errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1024})
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.goto(BASE_URL, wait_until="networkidle")
        skip_link = page.locator("a.sy-skip-link")
        assert skip_link.count() == 1
        page.keyboard.press("Tab")
        assert page.evaluate("document.activeElement?.classList.contains('sy-skip-link')") is True
        page.keyboard.press("Enter")
        page.wait_for_function("document.activeElement?.id === 'main-content'")
        favicon_response = page.request.get(f"{BASE_URL}/favicon.ico")
        assert favicon_response.status == 200
        assert favicon_response.body() == FAVICON_CREST_PATH.read_bytes(), "favicon did not use the dedicated square crest"
        # User storage can retain the previous smoke run's language preference.
        if page.get_by_role("button", name="中").count():
            page.get_by_role("button", name="中").click()
            page.wait_for_load_state("networkidle")
        page.get_by_text("第一次使用", exact=False).or_(
            page.get_by_text("First time here", exact=False)
        ).first.wait_for(timeout=10_000)
        if page.locator("i.q-icon", has_text="light_mode").count():
            page.locator("i.q-icon", has_text="light_mode").click()
            page.wait_for_load_state("networkidle")
        page.get_by_text("本週值班工作台", exact=True).wait_for(timeout=10_000)
        assert page.locator("main#main-content").count() == 1
        assert page.locator('[role="navigation"][aria-label="主要導覽"]').count() == 1
        assert page.locator('[role="heading"][aria-level="1"]').count() == 1
        assert page.locator('[aria-current="page"]').count() == 1
        assert page.get_by_role("button", name="開啟主要導覽").count() == 1
        assert page.get_by_role("button", name="開啟操作提示音").count() == 1
        assert page.get_by_role("button", name="切換深色模式").count() == 1
        assert page.get_by_role("link", name="跳至主要內容").count() == 1
        images_without_alt = page.locator("img:not([alt])").count()
        assert images_without_alt == 0
        navigation_crest = page.locator(".sy-brand-mark")
        navigation_crest_image = navigation_crest.locator("img")
        assert "sing-yin-crest-navigation.png" in (navigation_crest_image.get_attribute("src") or "")
        assert navigation_crest_image.evaluate("element => element.naturalWidth") == 545
        assert (navigation_crest.bounding_box() or {"width": 0})["width"] >= 58
        assert page.locator(".sy-flow-symbol").count() == 3
        assert "devotional-sacred-light-v1.webp" in page.locator(".sy-daily-start").evaluate("element => getComputedStyle(element, '::after').backgroundImage")
        assert "weekly-pulse-light-v1.webp" in page.locator(".sy-workbench").evaluate("element => getComputedStyle(element, '::after').backgroundImage")
        music_button = page.get_by_test_id("page-music-button")
        assert music_button.count() == 1
        music_button.click()
        music_dialog = page.get_by_test_id("page-music-dialog")
        music_dialog.wait_for(timeout=10_000)
        music_audio = music_dialog.locator("audio.sy-page-music-audio")
        assert music_audio.count() == 1
        assert music_audio.get_attribute("autoplay") is None
        assert music_audio.get_attribute("loop") is None
        assert "Ambre.m4a" in (music_audio.get_attribute("src") or "")
        assert music_audio.evaluate("element => element.canPlayType('audio/mp4')") != ""
        youtube_panel = music_dialog.get_by_test_id("youtube-player-panel")
        youtube_panel.wait_for(timeout=10_000)
        assert youtube_panel.locator("iframe.sy-youtube-player").count() == 0, "Empty YouTube setup must not contact the platform"
        page.get_by_text("此頁暫未設定 YouTube 歌單", exact=False).wait_for(timeout=10_000)
        assert 0.15 <= float(music_audio.evaluate("element => element.volume")) <= 0.2
        music_src = music_audio.get_attribute("src") or ""
        music_response = page.request.get(f"{BASE_URL}{music_src}" if music_src.startswith("/") else music_src)
        assert music_response.status == 200
        assert "audio" in music_response.headers.get("content-type", "")
        page.screenshot(path=str(MUSIC_SCREENSHOT), full_page=False)
        first_music_src = music_audio.get_attribute("src") or ""
        page.evaluate("HTMLMediaElement.prototype.play = () => Promise.resolve()")
        music_audio.dispatch_event("ended")
        page.wait_for_function(
            "([selector, original]) => document.querySelector(selector)?.getAttribute('src') !== original",
            arg=["audio.sy-page-music-audio", first_music_src],
        )
        assert "Near%20Light.m4a" in (music_audio.get_attribute("src") or "")
        close_music_dialog(music_dialog)
        for path, expected_text in (
            ("/", "今日經文"),
            ("/getting-started", "開始使用"),
            ("/guide", "使用手冊"),
            ("/system-architecture", "系統架構與共創"),
            ("/rosters", "生成與檢視"),
            ("/prefects", "名單管理"),
            ("/adjustments", "生成與檢視"),
            ("/audit", "公平審核"),
            ("/handover", "交接指引"),
        ):
            response = page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
            assert response is not None and response.status == 200, path
            page.get_by_text(expected_text, exact=False).first.wait_for(timeout=10_000)
        page.goto(f"{BASE_URL}/handover", wait_until="networkidle")
        assert "handover-archive-light-v1.webp" in page.locator(".sy-handover-hero").evaluate("element => getComputedStyle(element, '::after').backgroundImage")
        readiness_cards = page.locator(".sy-handover-readiness-card")
        assert readiness_cards.count() == 3
        readiness_grid = page.get_by_test_id("handover-readiness-grid")
        assert " " in readiness_grid.evaluate("element => getComputedStyle(element).gridTemplateColumns")
        acceptance_status = page.get_by_test_id("acceptance-status")
        acceptance_status.wait_for(timeout=10_000)
        page.get_by_text("仍需首席導學風紀及教師顧問確認", exact=True).wait_for(timeout=10_000)
        acceptance_steps = page.get_by_test_id("acceptance-human-steps")
        acceptance_steps.locator(".q-item").click()
        assert acceptance_steps.locator("ol > li").count() == 4
        for button in page.locator(".sy-acceptance-actions .q-btn").all():
            box = button.bounding_box()
            assert box is not None and box["height"] >= 44
        page.screenshot(path=str(HANDOVER_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/system-architecture", wait_until="networkidle")
        page.get_by_text("共創結語", exact=True).wait_for(timeout=10_000)
        assert page.locator(".sy-architecture-layer").count() == 5
        assert page.get_by_test_id("service-lifeline").locator(".sy-service-stage").count() == 6
        assert page.get_by_test_id("trust-evidence").locator(".sy-trust-evidence-card").count() == 4
        assert page.get_by_test_id("architecture-faq").locator(".sy-architecture-faq-item").count() == 9
        assert "architecture-lifeline-light-v1.webp" in page.get_by_test_id("architecture-lifeline-visual").evaluate(
            "element => getComputedStyle(element).backgroundImage"
        )
        page.get_by_text("草稿會增加累計工作量嗎？", exact=True).click()
        page.get_by_text("生成或重新生成草稿只保存待核對安排", exact=False).wait_for(timeout=10_000)
        page.get_by_text("Codex 的結語", exact=True).wait_for(timeout=10_000)
        display_crest = page.locator(".sy-co-creation-crest")
        display_crest_image = display_crest.locator("img")
        assert "sing-yin-crest-display-web.png" in (display_crest_image.get_attribute("src") or "")
        assert display_crest_image.evaluate("element => element.naturalWidth") == 640
        pointer_layer = page.locator(".sy-architecture-layer").first
        pointer_layer.locator(".sy-pointer-light").wait_for(timeout=10_000, state="attached")
        assert pointer_layer.evaluate("element => getComputedStyle(element).transform") == "none"
        pointer_layer.hover(position={"x": 86, "y": 74})
        page.wait_for_timeout(240)
        assert pointer_layer.evaluate("element => getComputedStyle(element).transform") != "none"
        assert float(pointer_layer.locator(".sy-pointer-light").evaluate("element => getComputedStyle(element).opacity")) > 0.8
        pointer_coordinates = pointer_layer.evaluate("element => [element.style.getPropertyValue('--sy-pointer-x'), element.style.getPropertyValue('--sy-pointer-y')]")
        assert all(value.endswith("px") for value in pointer_coordinates), pointer_coordinates
        page.screenshot(path=str(HOVER_SCREENSHOT), full_page=True)
        assert "architecture-stewardship-light-v1.webp" in page.locator(".sy-architecture-hero").evaluate("element => getComputedStyle(element, '::before').backgroundImage")
        assert "sidebar-stewardship-light-v1.webp" in page.locator(".sy-sidebar").evaluate("element => getComputedStyle(element, '::before').backgroundImage")
        page.screenshot(path=str(ARCHITECTURE_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/guide", wait_until="networkidle")
        expansion_header = page.locator(".q-expansion-item .q-item").first
        assert expansion_header.evaluate("element => getComputedStyle(element).cursor") == "pointer"
        expansion_header.hover()
        page.wait_for_timeout(190)
        assert expansion_header.evaluate("element => getComputedStyle(element).transform") != "none"
        page.goto(f"{BASE_URL}/getting-started", wait_until="networkidle")
        page.locator(".sy-onboarding-symbol").wait_for(timeout=10_000)
        assert "onboarding-desk-light-v1.webp" in page.locator(".sy-onboarding-intro").evaluate("element => getComputedStyle(element, '::after').backgroundImage")
        page.screenshot(path=str(ONBOARDING_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/rosters", wait_until="networkidle")
        page.get_by_text("生成前請假", exact=True).wait_for(timeout=10_000)
        assert page.locator(".sy-operation-hint").count() >= 1
        page.get_by_text("用途：生成尚未發布的本週草稿。", exact=False).wait_for(timeout=10_000)
        page.locator(".sy-storage-lifecycle").wait_for(timeout=10_000)
        page.get_by_text("公平帳本說明", exact=True).click()
        page.get_by_text("草稿：已儲存，未入帳", exact=True).wait_for(timeout=10_000)
        page.get_by_text("本週崗位與空缺預覽", exact=True).click()
        page.get_by_text("尚待生成", exact=True).first.wait_for(timeout=10_000)
        page.screenshot(path=str(ROSTER_SCREENSHOT), full_page=True)
        page.get_by_text("調整與編輯", exact=True).click()
        page.get_by_text("請假調整", exact=True).wait_for(timeout=10_000)
        page.goto(f"{BASE_URL}/rosters/999999", wait_until="networkidle")
        unavailable = page.get_by_test_id("roster-unavailable-state")
        unavailable.wait_for(timeout=10_000)
        assert unavailable.get_by_role("button", name="查看現有值班表").count() == 1
        assert unavailable.get_by_role("button", name="核對備份與還原").count() == 1
        page.screenshot(path=str(ROSTER_RECOVERY_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/rosters/999999/adjustments", wait_until="networkidle")
        page.get_by_test_id("adjustment-roster-unavailable-state").wait_for(timeout=10_000)
        page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        assert page.get_by_test_id("page-music-button").count() == 0
        page.get_by_test_id("online-music-settings").wait_for(timeout=10_000)
        page.get_by_text("公開歌單播放已就緒", exact=False).wait_for(timeout=10_000)
        page.get_by_test_id("music-library-settings").wait_for(timeout=10_000)
        page.get_by_text("備份還原", exact=True).wait_for(timeout=10_000)
        page.get_by_test_id("create-verified-backup-action").wait_for(timeout=10_000)
        assert page.get_by_text("尚未有可使用的已驗證快照", exact=True).count() == 2
        assert page.get_by_test_id("handover-package-disabled-no-backup").is_disabled()
        assert page.get_by_test_id("restore-disabled-no-backup").is_disabled()
        assert page.get_by_test_id("handover-package-ready-action").count() == 0
        assert page.get_by_test_id("restore-ready-action").count() == 0
        assert page.get_by_text("不要電郵、公開上載或傳送至未經批准的平台。", exact=False).count() == 0
        if expected_invalid_backups:
            page.get_by_test_id("invalid-backup-summary").wait_for(timeout=10_000)
            page.get_by_text(
                f"最近檢查的快照中，有 {expected_invalid_backups} 個未通過驗證",
                exact=True,
            ).wait_for(timeout=10_000)
            page.get_by_text("校驗清單遺失或不可讀 · 1", exact=True).wait_for(timeout=10_000)
            assert page.get_by_text("Backup is missing its checksum manifest.", exact=False).count() == 0
        else:
            assert page.get_by_test_id("invalid-backup-summary").count() == 0
        # This action is deliberately opt-in: a normal smoke run must never
        # create a real roster or backup package. CI/local UI verification can
        # enable it only with an isolated database and backup directory.
        if os.getenv("SING_YIN_EXERCISE_PROGRESS") == "1":
            page.goto(f"{BASE_URL}/rosters", wait_until="networkidle")
            page.locator("button").filter(
                has=page.locator("i.q-icon", has_text="auto_awesome")
            ).click()
            page.locator(".sy-progress-dialog").wait_for(timeout=10_000)
            assert page.locator(".sy-progress-dialog-title").count() == 1
            assert page.locator(".sy-progress-dialog .q-linear-progress").count() == 1
            page.wait_for_timeout(90)
            page.screenshot(path=str(PROGRESS_SCREENSHOT), full_page=False)
            page.wait_for_url("**/rosters/*", timeout=10_000)
        page.goto(f"{BASE_URL}/prefects", wait_until="networkidle")
        page.get_by_text("助理首席導學風紀", exact=True).first.wait_for(timeout=10_000)
        page.get_by_text("導學風紀", exact=True).first.wait_for(timeout=10_000)
        static_table = page.locator(".sy-table").first
        assert static_table.evaluate("element => getComputedStyle(element).cursor") != "pointer"
        assert static_table.evaluate("element => getComputedStyle(element).transform") == "none"
        # Archiving is consequential but this smoke run must remain read-only:
        # verify the recovery copy and cancel before the workflow is invoked.
        page.get_by_test_id("open-archive-prefect").click()
        page.get_by_text("確認停用這位風紀？", exact=True).wait_for(timeout=10_000)
        page.get_by_text("歷史週表、公平帳本及審計紀錄會完整保留", exact=False).wait_for(timeout=10_000)
        page.get_by_text("此介面沒有即時復原按鈕", exact=False).wait_for(timeout=10_000)
        page.get_by_role("button", name="取消", exact=True).last.click()
        page.get_by_text("確認停用這位風紀？", exact=True).wait_for(state="hidden", timeout=10_000)
        page.get_by_text("AI 匯入", exact=True).click()
        page.get_by_role("button", name="下載名單 CSV 格式範例").wait_for(timeout=10_000)
        page.get_by_text("貼上由 AI 整理或匯出的 JSON／CSV", exact=False).wait_for(timeout=10_000)
        page.locator("textarea").fill("姓名,級別,班別,職務,可值班日\n測試風紀,F.3,3H,導學風紀,星期一、星期三")
        page.get_by_role("button", name="驗證與預覽").click()
        page.get_by_text("資料已通過驗證，可安全匯入。", exact=True).wait_for(timeout=10_000)
        page.screenshot(path=str(PREFECT_IMPORT_SCREENSHOT), full_page=True)
        page.goto(BASE_URL, wait_until="networkidle")
        page.screenshot(path=str(LIGHT_SCREENSHOT), full_page=True)
        language_button = page.get_by_role("button", name="EN")
        language_button.click()
        page.wait_for_load_state("networkidle")
        page.get_by_text("Dashboard", exact=True).first.wait_for(timeout=10_000)
        page.goto(f"{BASE_URL}/rosters/999999", wait_until="networkidle")
        page.get_by_text("This roster is no longer available", exact=True).wait_for(timeout=10_000)
        assert page.get_by_role("button", name="Review current rosters").count() == 1
        assert page.get_by_role("button", name="Check backup and restore").count() == 1
        page.goto(f"{BASE_URL}/handover", wait_until="networkidle")
        page.get_by_text("Handover guide", exact=True).first.wait_for(timeout=10_000)
        page.get_by_text("Head Study Prefect and teacher-advisor sign-off still required", exact=True).wait_for(timeout=10_000)
        page.goto(BASE_URL, wait_until="networkidle")
        if page.locator("i.q-icon", has_text="light_mode").count():
            page.locator("i.q-icon", has_text="light_mode").click()
            page.wait_for_load_state("networkidle")
        page.locator("i.q-icon", has_text="dark_mode").click()
        page.wait_for_function("document.body.classList.contains('body--dark')")
        assert "body--dark" in (page.locator("body").get_attribute("class") or "")
        assert "devotional-sacred-dark-v1.webp" in page.locator(".sy-daily-start").evaluate("element => getComputedStyle(element, '::after').backgroundImage")
        assert "weekly-pulse-dark-v1.webp" in page.locator(".sy-workbench").evaluate("element => getComputedStyle(element, '::after').backgroundImage")
        assert float(page.locator(".sy-workbench").evaluate("element => getComputedStyle(element, '::after').opacity")) >= 0.7
        page.get_by_test_id("page-music-button").click()
        dark_music_dialog = page.get_by_test_id("page-music-dialog")
        dark_music_dialog.wait_for(timeout=10_000)
        assert dark_music_dialog.locator("audio.sy-page-music-audio").evaluate("element => getComputedStyle(element).colorScheme") == "dark"
        close_music_dialog(dark_music_dialog)
        page.screenshot(path=str(DARK_SCREENSHOT), full_page=True)
        assert page.locator(".sy-daily-start-verse").evaluate("element => getComputedStyle(element).color") != "rgb(0, 0, 0)"
        page.goto(f"{BASE_URL}/handover", wait_until="networkidle")
        assert "handover-archive-dark-v1.webp" in page.locator(".sy-handover-hero").evaluate("element => getComputedStyle(element, '::after').backgroundImage")
        page.goto(f"{BASE_URL}/getting-started", wait_until="networkidle")
        assert "onboarding-desk-dark-v1.webp" in page.locator(".sy-onboarding-intro").evaluate("element => getComputedStyle(element, '::after').backgroundImage")
        page.goto(f"{BASE_URL}/system-architecture", wait_until="networkidle")
        assert "architecture-stewardship-dark-v1.webp" in page.locator(".sy-architecture-hero").evaluate("element => getComputedStyle(element, '::before').backgroundImage")
        assert "architecture-lifeline-dark-v1.webp" in page.get_by_test_id("architecture-lifeline-visual").evaluate(
            "element => getComputedStyle(element).backgroundImage"
        )
        assert "sidebar-stewardship-dark-v1.webp" in page.locator(".sy-sidebar").evaluate("element => getComputedStyle(element, '::before').backgroundImage")
        page.screenshot(path=str(ARCHITECTURE_DARK_SCREENSHOT), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(f"{BASE_URL}/system-architecture", wait_until="networkidle")
        page.get_by_text("A co-creation note", exact=True).wait_for(timeout=10_000)
        assert page.locator(".sy-architecture-layer").count() == 5
        assert page.locator(".sy-service-stage").count() == 6
        assert page.locator(".sy-trust-evidence-card").count() == 4
        first_layer_box = page.locator(".sy-architecture-layer").first.bounding_box()
        second_layer_box = page.locator(".sy-architecture-layer").nth(1).bounding_box()
        assert first_layer_box is not None and second_layer_box is not None
        assert first_layer_box["y"] < second_layer_box["y"], "Architecture layers should stack on a phone"
        first_stage_box = page.locator(".sy-service-stage").first.bounding_box()
        second_stage_box = page.locator(".sy-service-stage").nth(1).bounding_box()
        assert first_stage_box is not None and second_stage_box is not None
        assert first_stage_box["y"] < second_stage_box["y"], "Service lifeline should become a vertical sequence on a phone"
        page.screenshot(path=str(ARCHITECTURE_MOBILE_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/handover", wait_until="networkidle")
        mobile_readiness_cards = page.locator(".sy-handover-readiness-card")
        assert mobile_readiness_cards.count() == 3
        first_readiness_box = mobile_readiness_cards.nth(0).bounding_box()
        second_readiness_box = mobile_readiness_cards.nth(1).bounding_box()
        assert first_readiness_box is not None and second_readiness_box is not None
        assert first_readiness_box["y"] < second_readiness_box["y"]
        acceptance_cards = page.locator(".sy-acceptance-card")
        first_acceptance_box = acceptance_cards.nth(0).bounding_box()
        second_acceptance_box = acceptance_cards.nth(1).bounding_box()
        assert first_acceptance_box is not None and second_acceptance_box is not None
        assert first_acceptance_box["y"] < second_acceptance_box["y"]
        page.screenshot(path=str(HANDOVER_MOBILE_SCREENSHOT), full_page=True)
        page.goto(BASE_URL, wait_until="networkidle")
        page.get_by_text("This week's roster desk", exact=True).wait_for(timeout=10_000)
        mobile_music_button = page.get_by_test_id("page-music-button")
        mobile_music_box = mobile_music_button.bounding_box()
        assert mobile_music_box is not None and mobile_music_box["width"] >= 44 and mobile_music_box["height"] >= 44
        mobile_music_button.click()
        mobile_music_dialog = page.get_by_test_id("page-music-dialog")
        mobile_dialog_box = mobile_music_dialog.bounding_box()
        assert mobile_dialog_box is not None and mobile_dialog_box["width"] <= 390
        close_music_dialog(mobile_music_dialog)
        verse_box = page.locator(".sy-daily-start").bounding_box()
        workbench_box = page.locator(".sy-workbench").bounding_box()
        assert verse_box is not None and workbench_box is not None
        assert verse_box["y"] < workbench_box["y"], "Daily Verse must remain before the weekly workflow on mobile"
        page.screenshot(path=str(MOBILE_SCREENSHOT), full_page=True)
        reduced_context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
        reduced_page = reduced_context.new_page()
        reduced_page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        reduced_page.goto(f"{BASE_URL}/system-architecture", wait_until="networkidle")
        reduced_layer = reduced_page.locator(".sy-architecture-layer").first
        reduced_layer.locator(".sy-pointer-light").wait_for(timeout=10_000, state="attached")
        reduced_layer.hover()
        assert reduced_layer.evaluate("element => getComputedStyle(element).transform") == "none"
        assert reduced_layer.locator(".sy-pointer-light").evaluate("element => getComputedStyle(element).display") == "none"
        reduced_context.close()
        touch_context = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        touch_page = touch_context.new_page()
        touch_page.goto(f"{BASE_URL}/system-architecture", wait_until="networkidle")
        assert touch_page.evaluate("matchMedia('(hover: hover) and (pointer: fine)').matches") is False
        touch_context.close()
        assert not console_errors, console_errors
        browser.close()
    print(f"UI smoke checks passed; screenshots: {LIGHT_SCREENSHOT}, {DARK_SCREENSHOT}")


if __name__ == "__main__":
    main()
