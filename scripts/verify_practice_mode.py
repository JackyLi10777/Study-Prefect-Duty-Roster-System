"""Read-only browser verification for the isolated Practice Mode identity."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


BASE_URL = os.getenv("SING_YIN_TEST_URL", "http://127.0.0.1:8090")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "playwright" / "practice-mode"


def _health() -> dict[str, object]:
    with urlopen(f"{BASE_URL}/healthz", timeout=3) as response:  # noqa: S310 - configured loopback test URL
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    health = _health()
    assert health["application"] == "sing-yin-roster"
    assert health["applicationMode"] == "practice"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 980})
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.goto(BASE_URL, wait_until="domcontentloaded")

        banner = page.get_by_test_id("practice-mode-banner")
        banner.wait_for(timeout=10_000)
        assert banner.get_by_text("練習模式", exact=True).count() == 1
        assert "虛構名單" in banner.inner_text()
        light_colors = banner.evaluate(
            "element => ({background: getComputedStyle(element).backgroundColor, color: getComputedStyle(element).color})"
        )
        page.screenshot(path=str(OUTPUT_DIR / "desktop-light.png"), full_page=True)

        page.get_by_role("button", name="EN").click()
        page.wait_for_load_state("domcontentloaded")
        english_banner = page.get_by_test_id("practice-mode-banner")
        english_banner.get_by_text("Practice Mode", exact=True).wait_for(timeout=10_000)
        assert "fictional names" in english_banner.inner_text()

        page.get_by_test_id("theme-control").click()
        page.get_by_test_id("desktop-theme-menu").locator('[data-theme-option="dark"]').click()
        page.wait_for_function("document.body.classList.contains('body--dark')")
        dark_banner = page.get_by_test_id("practice-mode-banner")
        dark_colors = dark_banner.evaluate(
            "element => ({background: getComputedStyle(element).backgroundColor, color: getComputedStyle(element).color})"
        )
        assert light_colors != dark_colors
        page.screenshot(path=str(OUTPUT_DIR / "desktop-dark.png"), full_page=True)

        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(BASE_URL, wait_until="domcontentloaded")
        mobile_banner = page.get_by_test_id("practice-mode-banner")
        mobile_banner.wait_for(timeout=10_000)
        banner_box = mobile_banner.bounding_box()
        assert banner_box is not None and banner_box["width"] <= 390
        assert mobile_banner.evaluate("element => getComputedStyle(element).position") == "relative"
        page.screenshot(path=str(OUTPUT_DIR / "mobile-dark.png"), full_page=True)

        assert not console_errors, console_errors
        browser.close()

    print(f"Practice Mode browser verification passed: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
