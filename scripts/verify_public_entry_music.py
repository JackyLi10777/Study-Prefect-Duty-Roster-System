"""Verify that welcome music never gates Admin or Guest entry.

The browser's media API is replaced before page load so autoplay outcomes are
deterministic. Destination requests receive a no-content response after
observation; the check therefore keeps the entrance document available without
creating a Guest session or entering Cloudflare Access.
"""

from __future__ import annotations

import argparse
import json
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Page, Route, sync_playwright


PLAYBACK_OVERRIDE = """
({ outcome }) => {
  window.__welcomePlayCalls = 0;
  Object.defineProperty(HTMLMediaElement.prototype, 'play', {
    configurable: true,
    value: function () {
      window.__welcomePlayCalls += 1;
      console.info('__sing_yin_welcome_play__');
      if (outcome === 'reject') {
        return Promise.reject(new DOMException('deterministic block', 'NotAllowedError'));
      }
      if (outcome === 'throw') {
        throw new DOMException('deterministic synchronous failure', 'NotAllowedError');
      }
      if (outcome === 'pending') return new Promise(() => {});
      return Promise.resolve();
    },
  });
  Object.defineProperty(HTMLMediaElement.prototype, 'paused', {
    configurable: true,
    get: function () { return outcome !== 'success'; },
  });
}
"""


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _observe_entry_route(route: Route, requests: list[str]) -> None:
    requests.append(route.request.url)
    # A cancelled top-level navigation sends current Chromium releases to
    # chrome-error://chromewebdata and destroys the entrance DOM before its
    # loading state can be inspected. HTTP 204 deliberately leaves the current
    # document in place while still preventing either destination workflow from
    # starting.
    route.fulfill(
        status=204,
        headers={"Cache-Control": "no-store"},
        body=b"",
    )


def _new_page(
    browser: Browser,
    base_url: str,
    outcome: str,
    viewport: dict[str, int],
    *,
    context_options: dict[str, object] | None = None,
    stored_volume: str | None = None,
) -> tuple[Page, list[str], list[str], list[str]]:
    context = browser.new_context(viewport=viewport, **(context_options or {}))
    page = context.new_page()
    requests: list[str] = []
    errors: list[str] = []
    play_events: list[str] = []
    origin = f"{urlsplit(base_url).scheme}://{urlsplit(base_url).netloc}"

    def observe_entry(route) -> None:
        _observe_entry_route(route, requests)

    page.route(f"{origin}/auth/login", observe_entry)
    page.route(f"{origin}/guest", observe_entry)
    page.route(
        f"{origin}/welcome-audio/**",
        lambda route: route.fulfill(
            status=200,
            content_type="audio/mpeg",
            headers={"Cache-Control": "no-store"},
            body=b"ID3",
        ),
    )
    page.on("pageerror", lambda error: errors.append(str(error)))

    def observe_console(message) -> None:
        if message.text == "__sing_yin_welcome_play__":
            play_events.append(message.text)
        elif message.type == "error":
            errors.append(f"console: {message.text}")

    page.on("console", observe_console)
    if stored_volume is not None:
        page.add_init_script(
            "localStorage.setItem('sing-yin:welcome-audio-volume:v1', "
            f"{json.dumps(stored_volume)});"
        )
    page.add_init_script(f"({PLAYBACK_OVERRIDE})({json.dumps({'outcome': outcome})});")
    page.goto(base_url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(900)
    _assert(page.locator("#welcomeAudioPlayer").count() == 1, "welcome player did not render")
    return page, requests, errors, play_events


def _entry_case(
    browser: Browser,
    base_url: str,
    *,
    role: str,
    outcome: str,
    viewport: dict[str, int],
    keyboard: bool = False,
    context_options: dict[str, object] | None = None,
) -> dict[str, object]:
    page, requests, errors, play_events = _new_page(
        browser,
        base_url,
        outcome,
        viewport,
        context_options=context_options,
    )
    button = page.locator(f'[data-entry-role="{role}"]:visible').first
    _assert(button.count() == 1, f"visible {role} entry button missing")
    if keyboard:
        button.focus()
        page.keyboard.press("Enter")
    else:
        button.click(no_wait_after=True)
    page.wait_for_function(
        "([role]) => document.querySelector(`[data-entry-role=\"${role}\"]:not([hidden])`)?.dataset.entryState === 'navigating'",
        arg=[role],
    )
    _assert(button.get_attribute("aria-busy") == "true", f"{role}/{outcome} did not expose aria-busy")
    other_role = "guest" if role == "admin" else "admin"
    other_button = page.locator(f'[data-entry-role="{other_role}"]:visible').first
    _assert(other_button.get_attribute("data-entry-locked") == "true", f"{role}/{outcome} did not lock role switching")
    expected_copy = "正在連接安全登入" if role == "admin" else "正在建立私人示範工作區"
    _assert(expected_copy in button.inner_text(), f"{role}/{outcome} did not render role-specific waiting copy")
    _assert("__ENTRY_REFERENCE__" not in page.content(), "entry support reference was not rendered")
    _assert(page.get_by_text("收不到驗證碼？", exact=False).count() >= 1, "sign-in help is missing")
    if context_options and context_options.get("reduced_motion") == "reduce":
        spinner_animation = button.locator(".entry-spinner").evaluate(
            "element => getComputedStyle(element).animationName"
        )
        _assert(spinner_animation == "none", "reduced-motion entry spinner still animates")
    page.wait_for_timeout(800)
    expected_path = "/auth/login" if role == "admin" else "/guest"
    matching = [url for url in requests if urlsplit(url).path == expected_path]
    _assert(len(matching) == 1, f"{role}/{outcome} navigated {len(matching)} times instead of once")
    _assert(not errors, f"{role}/{outcome} raised page errors: {errors}")
    calls = len(play_events)
    _assert(calls >= 2, f"{role}/{outcome} did not retry playback inside the entry activation")
    page.context.close()
    return {"role": role, "outcome": outcome, "keyboard": keyboard, "requests": len(matching), "play_calls": calls}


def _slow_state_case(browser: Browser, base_url: str) -> dict[str, object]:
    page, requests, errors, _ = _new_page(browser, base_url, "pending", {"width": 1440, "height": 1000})
    button = page.locator('[data-entry-role="guest"]:visible').first
    button.click(no_wait_after=True)
    page.wait_for_function(
        "() => document.querySelector('[data-entry-role=\"guest\"]:not([hidden])')?.dataset.entryState === 'slow'",
        timeout=10_000,
    )
    _assert(button.get_attribute("aria-busy") is None, "slow Guest entry remained aria-busy")
    _assert(button.get_attribute("aria-disabled") is None, "slow Guest entry did not unlock")
    _assert("需時較長" in button.inner_text(), "slow Guest entry did not explain the delay")
    button.click(no_wait_after=True)
    page.wait_for_timeout(700)
    matching = [url for url in requests if urlsplit(url).path == "/guest"]
    _assert(len(matching) == 2, "slow Guest retry did not start exactly one fresh navigation")
    _assert(not errors, f"slow Guest retry raised errors: {errors}")
    page.context.close()
    return {"role": "guest", "outcome": "slow-retry", "requests": len(matching)}


def _quiet_case(browser: Browser, base_url: str) -> dict[str, object]:
    page, requests, errors, play_events = _new_page(browser, base_url, "reject", {"width": 390, "height": 844})
    _assert(
        page.locator("#welcomeAudioRecovery").get_attribute("hidden") is None,
        "blocked recovery was not available",
    )
    calls_before = len(play_events)
    page.locator("#welcomeAudioQuiet").click()
    _assert(page.locator("#welcomeAudioPlayer").get_attribute("data-entry-intent") == "quiet", "quiet intent was not recorded")
    page.locator('[data-entry-role="guest"]:visible').first.click(no_wait_after=True)
    page.wait_for_timeout(250)
    matching = [url for url in requests if urlsplit(url).path == "/guest"]
    _assert(len(matching) == 1, "quiet entry did not navigate exactly once")
    _assert(len(play_events) == calls_before, "quiet entry attempted playback")
    _assert(not errors, f"quiet entry raised page errors: {errors}")
    page.context.close()
    return {"role": "guest", "outcome": "quiet", "requests": len(matching), "play_calls": calls_before}


def _already_playing_case(browser: Browser, base_url: str) -> dict[str, object]:
    page, requests, errors, play_events = _new_page(browser, base_url, "success", {"width": 1440, "height": 1000})
    calls_before = len(play_events)
    _assert(calls_before >= 1, "page-load playback did not settle")
    page.locator('[data-entry-role="admin"]:visible').first.click(no_wait_after=True)
    page.wait_for_timeout(250)
    matching = [url for url in requests if urlsplit(url).path == "/auth/login"]
    _assert(len(matching) == 1, "already-playing entry did not navigate exactly once")
    _assert(len(play_events) == calls_before, "already-playing entry restarted audio")
    _assert(not errors, f"already-playing entry raised page errors: {errors}")
    page.context.close()
    return {"role": "admin", "outcome": "already-playing", "requests": len(matching), "play_calls": calls_before}


def _rapid_activation_case(browser: Browser, base_url: str) -> dict[str, object]:
    page, requests, errors, play_events = _new_page(browser, base_url, "reject", {"width": 1440, "height": 1000})
    page.evaluate("""
      () => {
        const button = document.querySelector('#guestEnter');
        button.click();
        button.click();
      }
    """)
    page.wait_for_timeout(600)
    matching = [url for url in requests if urlsplit(url).path == "/guest"]
    _assert(len(matching) == 1, f"rapid activation navigated {len(matching)} times")
    _assert(len(play_events) == 2, f"rapid activation attempted playback {len(play_events)} times")
    _assert(not errors, f"rapid activation raised page errors: {errors}")
    page.context.close()
    return {"role": "guest", "outcome": "rapid-double", "requests": len(matching), "play_calls": len(play_events)}


def _explicit_music_case(browser: Browser, base_url: str) -> dict[str, object]:
    page, requests, errors, play_events = _new_page(browser, base_url, "reject", {"width": 768, "height": 1024})
    page.locator("#welcomeAudioEnter").click()
    _assert(page.locator("#welcomeAudioPlayer").get_attribute("data-entry-intent") == "music", "music intent was not recorded")
    page.locator('[data-entry-role="guest"]:visible').first.click(no_wait_after=True)
    page.wait_for_timeout(500)
    matching = [url for url in requests if urlsplit(url).path == "/guest"]
    _assert(len(matching) == 1, "explicit music entry did not reach Guest exactly once")
    _assert(len(play_events) >= 3, "explicit music entry did not use its trusted retry")
    _assert(not errors, f"explicit music entry raised errors: {errors}")
    page.context.close()
    return {"role": "guest", "outcome": "explicit-music", "requests": len(matching), "play_calls": len(play_events)}


def _manual_pause_case(browser: Browser, base_url: str) -> dict[str, object]:
    page, requests, errors, play_events = _new_page(browser, base_url, "success", {"width": 768, "height": 1024})
    calls_before = len(play_events)
    page.locator("#welcomeAudioToggle").click()
    _assert(page.locator("#welcomeAudioPlayer").get_attribute("data-entry-intent") == "quiet", "manual pause did not select quiet intent")
    page.locator('[data-entry-role="admin"]:visible').first.click(no_wait_after=True)
    page.wait_for_timeout(300)
    matching = [url for url in requests if urlsplit(url).path == "/auth/login"]
    _assert(len(matching) == 1, "manual pause entry did not reach Admin exactly once")
    _assert(len(play_events) == calls_before, "manual pause entry restarted audio")
    _assert(not errors, f"manual pause entry raised errors: {errors}")
    page.context.close()
    return {"role": "admin", "outcome": "manual-pause", "requests": len(matching), "play_calls": calls_before}


def _pageshow_reset_case(browser: Browser, base_url: str) -> dict[str, object]:
    page, requests, errors, play_events = _new_page(browser, base_url, "pending", {"width": 1440, "height": 1000})
    button = page.locator('[data-entry-role="admin"]:visible').first
    button.click(no_wait_after=True)
    page.wait_for_timeout(100)
    page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }))")
    button.click(no_wait_after=True)
    page.wait_for_timeout(700)
    matching = [url for url in requests if urlsplit(url).path == "/auth/login"]
    _assert(len(matching) == 1, "pageshow did not cancel stale work and permit exactly one fresh navigation")
    _assert(len(play_events) >= 3, "pageshow did not permit a fresh trusted playback attempt")
    _assert(not errors, f"pageshow reset raised errors: {errors}")
    page.context.close()
    return {"role": "admin", "outcome": "pageshow-reset", "requests": len(matching), "play_calls": len(play_events)}


def _explicit_zero_volume_case(browser: Browser, base_url: str) -> dict[str, object]:
    page, _, errors, play_events = _new_page(
        browser,
        base_url,
        "success",
        {"width": 390, "height": 844},
        stored_volume="0",
    )
    _assert(page.locator("#welcomeAudioVolume").input_value() == "0", "explicit zero volume was replaced")
    _assert(page.evaluate("document.querySelector('#welcomeAudio').volume") == 0, "audio element did not preserve zero volume")
    _assert(not errors, f"zero-volume entrance raised errors: {errors}")
    page.context.close()
    return {"outcome": "explicit-zero-volume", "play_calls": len(play_events)}


def _share_stays_silent(browser: Browser, base_url: str) -> dict[str, object]:
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    page.add_init_script(f"({PLAYBACK_OVERRIDE})({json.dumps({'outcome': 'success'})});")
    page.goto(f"{base_url.rstrip('/')}/view#deterministic-share-token", wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(500)
    calls = page.evaluate("window.__welcomePlayCalls")
    _assert(calls == 0, "public share attempted welcome playback")
    context.close()
    return {"route": "/view", "play_calls": calls}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8790/")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/") + "/"

    results: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        results.append(_entry_case(browser, base_url, role="admin", outcome="reject", viewport={"width": 1440, "height": 1000}, context_options={"color_scheme": "light"}))
        results.append(_entry_case(browser, base_url, role="guest", outcome="throw", viewport={"width": 1440, "height": 1000}, context_options={"color_scheme": "dark"}))
        results.append(_entry_case(browser, base_url, role="admin", outcome="pending", viewport={"width": 390, "height": 844}, context_options={"is_mobile": True, "has_touch": True, "color_scheme": "no-preference"}))
        results.append(_entry_case(browser, base_url, role="guest", outcome="reject", viewport={"width": 390, "height": 844}, keyboard=True, context_options={"reduced_motion": "reduce", "forced_colors": "active"}))
        results.append(_slow_state_case(browser, base_url))
        results.append(_quiet_case(browser, base_url))
        results.append(_already_playing_case(browser, base_url))
        results.append(_rapid_activation_case(browser, base_url))
        results.append(_explicit_music_case(browser, base_url))
        results.append(_manual_pause_case(browser, base_url))
        results.append(_pageshow_reset_case(browser, base_url))
        results.append(_explicit_zero_volume_case(browser, base_url))
        results.append(_share_stays_silent(browser, base_url))
        browser.close()

    print(json.dumps({"base_url": base_url, "checks": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
