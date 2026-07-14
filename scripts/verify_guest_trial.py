"""Browser-verify the static guest tour and zero-server-write trial.

Run this against a local ``wrangler dev`` URL before deployment and against the
canonical Worker after deployment.  It uses only the fixed fictional directory
already shipped in the static trial and never contacts the NiceGUI origin.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import Page, sync_playwright
from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_DIR = PROJECT_ROOT / "test-results" / "guest-trial"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8791")
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    return parser.parse_args()


def _assert_no_page_errors(page: Page, console_errors: list[str], page_errors: list[str]) -> None:
    if console_errors or page_errors:
        raise RuntimeError({"consoleErrors": console_errors, "pageErrors": page_errors})
    overflow = page.evaluate(
        "() => ({viewport: innerWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth})"
    )
    if overflow["document"] > overflow["viewport"] + 1 or overflow["body"] > overflow["viewport"] + 1:
        raise RuntimeError(f"Horizontal viewport overflow: {overflow}")


def _assert_policy_rows(page: Page, absent_name: str) -> list[list[str]]:
    rows: list[list[str]] = page.locator("#rosterTable tbody tr").evaluate_all(
        "rows => rows.map(row => [...row.querySelectorAll('td')].map(cell => cell.textContent.trim()))"
    )
    if len(rows) != 6 or any(len(row) != 5 for row in rows):
        raise RuntimeError(f"Unexpected trial roster shape: {rows}")
    assistant_names = set(page.locator(".person-card.role-assistant strong").all_text_contents())
    ordinary_names = set(page.locator(".person-card.role-prefect strong").all_text_contents())
    assigned_by_day: list[set[str]] = []
    for day_index in range(5):
        assigned = {
            row[day_index]
            for row in rows
            if row[day_index] not in {"休室", "Closed", "待補", "Vacancy"}
        }
        if len(assigned) != sum(
            1 for row in rows if row[day_index] not in {"休室", "Closed", "待補", "Vacancy"}
        ):
            raise RuntimeError(f"Same-day duplicate on index {day_index}: {rows}")
        if day_index and assigned.intersection(assigned_by_day[-1]):
            raise RuntimeError(f"Consecutive generated duty on index {day_index}: {rows}")
        assigned_by_day.append(assigned)
    if any(name not in assistant_names for name in rows[0]):
        raise RuntimeError("Assist. in charge contains a non-assistant fictional member.")
    for row in rows[1:]:
        for name in row:
            if name not in {"休室", "Closed", "待補", "Vacancy"} and name not in ordinary_names:
                raise RuntimeError("A room contains a non-ordinary fictional member.")
    if rows[4][1] not in {"休室", "Closed"} or rows[4][4] not in {"休室", "Closed"}:
        raise RuntimeError("Room 202 is not closed on Tuesday and Friday.")
    if rows[5][1] not in {"休室", "Closed"} or rows[5][4] not in {"休室", "Closed"}:
        raise RuntimeError("Room 202 is not closed on Tuesday and Friday.")
    if rows[0][0] == absent_name:
        raise RuntimeError("The declared fictional leave was ignored.")
    names = [name for row in rows for name in row if name not in {"休室", "Closed", "待補", "Vacancy"}]
    if not names or any(not any("\u3400" <= character <= "\u9fff" for character in name) for name in names):
        raise RuntimeError("A trial assignment lost its Chinese display name.")
    return rows


def main() -> int:
    args = _parse_args()
    base_url = args.base_url.rstrip("/") + "/"
    evidence_dir = args.evidence_dir.expanduser().resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {"baseUrl": base_url, "status": "fail"}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        desktop = browser.new_context(viewport={"width": 1440, "height": 1000}, color_scheme="light", accept_downloads=True)
        page = desktop.new_page()
        page.clock.install()
        console_errors: list[str] = []
        page_errors: list[str] = []
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        guest_response = page.goto(urljoin(base_url, "guest"), wait_until="networkidle")
        if guest_response is None or guest_response.status != 200:
            raise RuntimeError("Guest tour did not return HTTP 200.")
        guest_csp = guest_response.headers.get("content-security-policy", "")
        if "connect-src 'none'" not in guest_csp:
            raise RuntimeError(f"Guest tour CSP is not isolated: {guest_csp}")
        page.locator('a[href="/try"]').first.wait_for(state="visible")
        page.screenshot(path=str(evidence_dir / "guest-desktop-light.png"), full_page=True)
        _assert_no_page_errors(page, console_errors, page_errors)

        page.locator("#guestLanguageToggle").click()
        if page.locator("html").get_attribute("lang") != "en":
            raise RuntimeError("Guest language control did not reach English.")
        page.locator("#guestThemeToggle").click()
        page.locator("#guestThemeToggle").click()
        if page.locator("html").get_attribute("data-theme") != "dark":
            raise RuntimeError("Guest theme control did not reach dark mode.")
        page.screenshot(path=str(evidence_dir / "guest-desktop-dark.png"), full_page=True)

        trial_response = page.goto(urljoin(base_url, "try"), wait_until="networkidle")
        if trial_response is None or trial_response.status != 200:
            raise RuntimeError("Interactive trial did not return HTTP 200.")
        trial_csp = trial_response.headers.get("content-security-policy", "")
        if "connect-src 'none'" not in trial_csp:
            raise RuntimeError(f"Trial CSP is not isolated: {trial_csp}")
        if page.locator("html").get_attribute("lang") != "en" or page.locator("html").get_attribute("data-theme") != "dark":
            raise RuntimeError("Guest display preferences did not carry into the trial.")
        page.locator("#languageToggle").click()
        page.locator("#themeToggleTrial").click()
        if page.locator("html").get_attribute("lang") != "zh-Hant-HK" or page.locator("html").get_attribute("data-theme") != "auto":
            raise RuntimeError("Trial display controls could not return to Traditional Chinese and automatic appearance.")
        interaction_requests: list[str] = []
        page.on("request", lambda request: interaction_requests.append(request.url))
        absent_name = page.locator("#absencePerson option:checked").inner_text().split(" · ", 1)[0]
        page.locator("#addAbsence").click()
        page.locator("#generateRoster").click()
        page.locator("#rosterPreview").wait_for(state="visible")
        if page.locator("#rosterEmpty").is_visible():
            raise RuntimeError("Generated preview did not replace the empty state.")
        rows = _assert_policy_rows(page, absent_name)
        page.screenshot(path=str(evidence_dir / "trial-desktop-light.png"), full_page=True)

        page.locator("#themeToggleTrial").click()
        page.locator("#themeToggleTrial").click()
        if page.locator("html").get_attribute("data-theme") != "dark":
            raise RuntimeError("Trial theme control did not reach dark mode.")
        page.screenshot(path=str(evidence_dir / "trial-desktop-dark.png"), full_page=True)
        page.locator("#languageToggle").click()
        if page.locator("html").get_attribute("lang") != "en":
            raise RuntimeError("Trial language control did not reach English.")
        english_rows = _assert_policy_rows(page, absent_name)
        if rows[0][0] != english_rows[0][0]:
            raise RuntimeError("Language switching changed a Chinese prefect name.")

        with page.expect_download() as download_info:
            page.locator("#downloadPdf").click()
        download = download_info.value
        pdf_path = evidence_dir / download.suggested_filename
        download.save_as(str(pdf_path))
        reader = PdfReader(str(pdf_path))
        if len(reader.pages) != 1:
            raise RuntimeError("Trial PDF is not exactly one page.")
        box = reader.pages[0].mediabox
        if float(box.width) <= float(box.height) or abs(float(box.width) - 841.89) > 0.1:
            raise RuntimeError(f"Trial PDF is not A4 landscape: {box}")
        if pdf_path.read_bytes()[:8] != b"%PDF-1.4":
            raise RuntimeError("Trial PDF header is invalid.")

        page.clock.fast_forward(31 * 60 * 1000)
        page.locator("#trialStatus").filter(has_text="expired").wait_for(state="visible")
        if page.locator("#rosterPreview").is_visible() or not page.locator("#downloadPdf").is_disabled():
            raise RuntimeError("An open tab remained usable after the 30-minute expiry.")
        if "expired" not in page.locator("#trialStatus").inner_text().lower():
            raise RuntimeError("Expiry did not explain the automatic reset in English.")
        stored = page.evaluate("() => JSON.parse(sessionStorage.getItem('sing-yin-guest-trial-v1'))")
        if stored.get("roster") is not None or stored.get("absences"):
            raise RuntimeError("Expired trial data remained in sessionStorage.")
        if interaction_requests:
            raise RuntimeError(f"Trial interactions made network requests: {interaction_requests}")
        _assert_no_page_errors(page, console_errors, page_errors)

        mobile = browser.new_context(viewport={"width": 390, "height": 844}, color_scheme="light")
        mobile_page = mobile.new_page()
        mobile_console: list[str] = []
        mobile_errors: list[str] = []
        mobile_page.on("console", lambda message: mobile_console.append(message.text) if message.type == "error" else None)
        mobile_page.on("pageerror", lambda error: mobile_errors.append(str(error)))
        mobile_page.goto(urljoin(base_url, "guest"), wait_until="networkidle")
        mobile_page.locator("#guestLanguageToggle").click()
        mobile_page.locator("#guestThemeToggle").click()
        mobile_page.locator("#guestThemeToggle").click()
        mobile_page.screenshot(path=str(evidence_dir / "guest-mobile-dark.png"), full_page=True)
        _assert_no_page_errors(mobile_page, mobile_console, mobile_errors)
        mobile_page.goto(urljoin(base_url, "try"), wait_until="networkidle")
        if mobile_page.locator("html").get_attribute("lang") != "en" or mobile_page.locator("html").get_attribute("data-theme") != "dark":
            raise RuntimeError("Mobile trial did not inherit the guest language and theme.")
        mobile_page.locator("#generateRoster").click()
        mobile_page.locator("#rosterPreview").wait_for(state="visible")
        mobile_page.screenshot(path=str(evidence_dir / "trial-mobile-dark.png"), full_page=True)
        mobile_page.locator("#languageToggle").click()
        mobile_page.locator("#themeToggleTrial").click()
        if mobile_page.locator("html").get_attribute("lang") != "zh-Hant-HK" or mobile_page.locator("html").get_attribute("data-theme") != "auto":
            raise RuntimeError("Mobile trial could not return to Traditional Chinese and automatic light appearance.")
        mobile_page.screenshot(path=str(evidence_dir / "trial-mobile-light.png"), full_page=True)
        _assert_no_page_errors(mobile_page, mobile_console, mobile_errors)

        missing = mobile_page.request.get(urljoin(base_url, "try/missing"))
        if missing.status != 404 or "connect-src 'none'" not in missing.headers.get("content-security-policy", ""):
            raise RuntimeError("Unknown /try/* route did not fail closed at the edge.")
        missing_guest = mobile_page.request.get(urljoin(base_url, "guest/missing"))
        if missing_guest.status != 404 or "connect-src 'none'" not in missing_guest.headers.get("content-security-policy", ""):
            raise RuntimeError("Unknown /guest/* route did not fail closed at the edge.")
        mobile_page.evaluate(
            "() => sessionStorage.setItem('sing-yin-guest-trial-v1', JSON.stringify({schema:'sing-yin-guest-trial-state-v1', createdAt:Date.now(), expiresAt:Date.now()+1800000, language:'zh', theme:'auto', absences:[null], roster:{rows:[]}}))"
        )
        mobile_page.reload(wait_until="networkidle")
        if mobile_page.locator(".person-card").count() != 18 or mobile_page.locator("#rosterPreview").is_visible():
            raise RuntimeError("A malformed tab-only trial state did not recover to a clean fictional session.")
        _assert_no_page_errors(mobile_page, mobile_console, mobile_errors)
        browser.close()

    report.update(
        {
            "status": "pass",
            "guestCsp": guest_csp,
            "trialCsp": trial_csp,
            "interactionRequestCount": 0,
            "pdf": str(pdf_path),
            "pdfPages": 1,
            "pdfMediaBox": [float(box.width), float(box.height)],
            "ttlResetVerified": True,
            "desktopLight": str(evidence_dir / "trial-desktop-light.png"),
            "desktopDark": str(evidence_dir / "trial-desktop-dark.png"),
            "mobileLight": str(evidence_dir / "trial-mobile-light.png"),
            "mobileDark": str(evidence_dir / "trial-mobile-dark.png"),
            "guestDesktopLight": str(evidence_dir / "guest-desktop-light.png"),
            "guestDesktopDark": str(evidence_dir / "guest-desktop-dark.png"),
            "guestMobileDark": str(evidence_dir / "guest-mobile-dark.png"),
        }
    )
    report_path = evidence_dir / "verification.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
