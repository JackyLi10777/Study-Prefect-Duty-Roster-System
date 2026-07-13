"""Verify the live public viewer with an isolated fictional roster only."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import shutil
import sys
import tempfile

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui_app.config import PROJECT_ROOT  # noqa: E402
from nicegui_app.services.public_roster_share import PublicRosterShareService, PublicRosterShareSettings
from nicegui_app.services.roster_workflow import RosterWorkflow


EVIDENCE_DIR = PROJECT_ROOT / "test-results" / "public-roster-viewer"
GATEWAY_EVIDENCE_DIR = PROJECT_ROOT / "test-results" / "unified-access-gateway"


def main() -> int:
    settings = PublicRosterShareSettings.from_environment()
    settings.require_configured()
    receipt = None
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    GATEWAY_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix="sing-yin-public-viewer-e2e-"))
    try:
        workflow = RosterWorkflow(
            database_path=temporary_root / "fictional.sqlite3",
            backup_dir=temporary_root / "backups",
        )
        workflow.bootstrap()
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        draft = workflow.generate_and_save_draft(week_start)
        workflow.publish(draft.id, expected_week_version=draft.version)
        service = PublicRosterShareService(workflow, settings=settings)
        receipt = service.create_share(draft.id)
        expected_names = {
            str(item["prefectName"])
            for item in workflow.assignments(draft.id)
            if item["status"] in {"active", "replaced"}
        }

        console_errors: list[str] = []
        page_errors: list[str] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            desktop = browser.new_context(viewport={"width": 1440, "height": 1000}, color_scheme="light")
            page = desktop.new_page()
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto(settings.base_url, wait_until="networkidle")
            page.locator("#guestState").wait_for(state="visible")
            login_link = page.locator('a[href="/auth/login"]')
            if login_link.count() != 1:
                raise RuntimeError("The unified guest landing does not expose exactly one administrator login.")
            page.screenshot(path=str(GATEWAY_EVIDENCE_DIR / "desktop-light.png"), full_page=True)

            page.emulate_media(color_scheme="dark")
            page.reload(wait_until="networkidle")
            page.locator("#guestState").wait_for(state="visible")
            page.screenshot(path=str(GATEWAY_EVIDENCE_DIR / "desktop-dark.png"), full_page=True)

            page.emulate_media(color_scheme="light")
            page.goto(receipt.share_url, wait_until="networkidle")
            page.locator("#rosterState").wait_for(state="visible")
            rendered = page.locator("#rosterTable").inner_text()
            if not expected_names or not expected_names.issubset(set(rendered.split())):
                raise RuntimeError("The live viewer did not render every fictional Chinese name.")
            page.screenshot(path=str(EVIDENCE_DIR / "desktop-light.png"), full_page=True)

            page.emulate_media(color_scheme="dark")
            page.reload(wait_until="networkidle")
            page.locator("#rosterState").wait_for(state="visible")
            page.screenshot(path=str(EVIDENCE_DIR / "desktop-dark.png"), full_page=True)
            desktop.close()

            mobile = browser.new_context(viewport={"width": 390, "height": 844}, color_scheme="light")
            mobile_page = mobile.new_page()
            mobile_page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            mobile_page.on("pageerror", lambda error: page_errors.append(str(error)))
            mobile_page.goto(settings.base_url, wait_until="networkidle")
            mobile_page.locator("#guestState").wait_for(state="visible")
            mobile_page.screenshot(path=str(GATEWAY_EVIDENCE_DIR / "mobile-light.png"), full_page=True)

            mobile_page.goto(receipt.share_url, wait_until="networkidle")
            mobile_page.locator("#rosterState").wait_for(state="visible")
            mobile_page.screenshot(path=str(EVIDENCE_DIR / "mobile-light.png"), full_page=True)
            mobile.close()
            browser.close()

        if console_errors or page_errors:
            raise RuntimeError(f"Browser errors: console={len(console_errors)} page={len(page_errors)}")

        service.revoke_share(receipt.share_id)
        receipt = None
        print("PASS unified gateway: guest landing and fictional encrypted share rendered in desktop light/dark and phone layouts.")
        print(f"Gateway evidence: {GATEWAY_EVIDENCE_DIR}")
        print(f"Viewer evidence: {EVIDENCE_DIR}")
        return 0
    finally:
        if receipt is not None:
            try:
                PublicRosterShareService(workflow, settings=settings).revoke_share(receipt.share_id)
            except Exception:
                pass
        shutil.rmtree(temporary_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
