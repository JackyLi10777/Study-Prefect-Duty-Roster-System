"""Verify truthful UI recovery when data commits but its snapshot fails."""

from __future__ import annotations

import os
from pathlib import Path
import re
import sqlite3
import sys

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.verify_nicegui_write_pipeline import isolated_paths


BASE_URL = os.getenv("SING_YIN_TEST_URL", "http://127.0.0.1:8080")
SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-committed-without-backup.png"


def main() -> None:
    database_path, blocked_backup_path, log_dir = isolated_paths()
    if not blocked_backup_path.is_file():
        raise RuntimeError("SING_YIN_BACKUP_DIR must initially point to an isolated blocking file for this test.")
    SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.goto(f"{BASE_URL}/rosters", wait_until="networkidle")
        page.get_by_role("button", name="生成並儲存草稿").click()

        partial_dialog = page.get_by_test_id("committed-without-backup-dialog")
        partial_dialog.wait_for(timeout=15_000)
        page.get_by_text("資料已儲存，但備份未完成", exact=True).wait_for(timeout=10_000)
        page.get_by_text("請勿重複執行剛才的操作", exact=False).wait_for(timeout=10_000)
        reference_copy = partial_dialog.get_by_text(re.compile(r"OP-[A-Z0-9]{8}"))
        assert reference_copy.count() == 1
        assert page.get_by_test_id("partial-review-action").count() == 1
        assert page.get_by_test_id("partial-backup-settings-action").count() == 1
        page.screenshot(path=str(SCREENSHOT), full_page=False)

        with sqlite3.connect(database_path) as connection:
            week_status, assignment_count = connection.execute(
                "SELECT status, (SELECT COUNT(*) FROM roster_assignments) FROM roster_weeks ORDER BY id DESC LIMIT 1"
            ).fetchone()
            backup_event, backup_success = connection.execute(
                "SELECT event_type, success FROM backup_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
        assert week_status == "draft"
        assert assignment_count == 26
        assert backup_event == "draft_generated" and backup_success == 0

        page.get_by_test_id("partial-backup-settings-action").click()
        page.wait_for_url("**/settings", timeout=10_000)
        page.get_by_test_id("create-verified-backup-action").wait_for(timeout=10_000)

        blocked_backup_path.unlink()
        blocked_backup_path.mkdir(parents=True)
        page.get_by_test_id("create-verified-backup-action").click()
        page.locator(".sy-progress-dialog").wait_for(timeout=10_000)
        page.get_by_text("已驗證", exact=True).first.wait_for(timeout=15_000)

        snapshots = list(blocked_backup_path.glob("*.sqlite3"))
        assert len(snapshots) == 1
        assert snapshots[0].with_suffix(".manifest.json").is_file()
        with sqlite3.connect(database_path) as connection:
            backup_event, backup_success = connection.execute(
                "SELECT event_type, success FROM backup_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
        assert backup_event == "manual_verified_backup" and backup_success == 1

        log_content = (log_dir / "app.log").read_text(encoding="utf-8")
        assert "event=operator_action_partial" in log_content
        assert "durable_state=committed backup=failed" in log_content
        assert console_errors == [], console_errors
        browser.close()

    print(f"Committed-without-backup browser recovery passed; screenshot: {SCREENSHOT}")


if __name__ == "__main__":
    main()
