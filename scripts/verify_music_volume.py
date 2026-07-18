"""Focused browser check for the page-music default without touching roster data."""

from __future__ import annotations

import os

from playwright.sync_api import sync_playwright


def main() -> None:
    base_url = os.getenv("SING_YIN_TEST_URL", "http://127.0.0.1:18766")
    console_errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.goto(base_url, wait_until="domcontentloaded")
        page.locator("a.sy-skip-link").wait_for(timeout=10_000)
        audio = page.locator("audio.sy-page-music-audio")
        audio.wait_for(state="attached", timeout=10_000)
        page.wait_for_function(
            """document.querySelector('audio.sy-page-music-audio').volume >= 0.33 &&
            document.querySelector('audio.sy-page-music-audio').volume <= 0.37"""
        )
        state = audio.evaluate(
            "element => ({volume: element.volume, base: element.dataset.syBaseVolume})"
        )
        assert 0.33 <= float(state["volume"]) <= 0.37, state
        assert console_errors == [], console_errors
        print(f"music-volume-browser-pass volume={state['volume']} base={state['base']}")
        browser.close()


if __name__ == "__main__":
    main()
