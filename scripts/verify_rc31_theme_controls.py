"""Verify the rc31 binary appearance control without touching school data.

This focused browser gate deliberately starts a fresh disposable NiceGUI
process for every access-mode, viewport, and operating-system colour-scheme
combination.  A fresh process is important for Guest evidence because the
isolated E2E principal intentionally has one stable session identifier per
run; reusing that process would turn an earlier explicit preference into the
next case's initial state.

All mutable paths, including NiceGUI's ``app.storage.user`` files, live below
one temporary evidence root.  The script never targets an already-running
server and never writes screenshots into the repository.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Literal

from playwright.sync_api import Browser, BrowserContext, Locator, Page, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui_app.ui.design_token_contract import quasar_palette
from scripts.verify_nicegui_mobile import _open_mobile_drawer
from scripts.verify_release_candidate import (
    _assert_server_console_clean,
    _free_loopback_port,
    _start_server,
    _stop_server,
    _wait_until_ready,
    isolated_environment,
)
from scripts.verify_unified_guest_ui import _install_gateway_stubs, _open_route


AccessMode = Literal["admin", "guest"]
ViewportMode = Literal["desktop", "mobile"]
ColourScheme = Literal["light", "dark"]

EXPECTED_PRIMARY = {
    mode: str(quasar_palette(mode=mode)["primary"]).lower()
    for mode in ("light", "dark")
}


class ThemeControlVerificationError(RuntimeError):
    """Raised when one browser-visible appearance contract is broken."""


def _safe_environment(case_root: Path, *, access_mode: AccessMode) -> dict[str, str]:
    """Return a fail-closed environment whose every mutable path is disposable."""

    environment = isolated_environment(case_root, _free_loopback_port())
    storage_path = (case_root / "nicegui-storage").resolve()
    storage_path.mkdir(parents=True, exist_ok=True)
    environment.update(
        {
            "NICEGUI_STORAGE_PATH": str(storage_path),
            "PYTHONDONTWRITEBYTECODE": "1",
            "SING_YIN_UNIFIED_GUEST": "1",
        }
    )
    if access_mode == "guest":
        environment["SING_YIN_E2E_ACCESS_MODE"] = "guest"

    mutable_paths = (
        Path(environment["SING_YIN_DATABASE_PATH"]),
        Path(environment["SING_YIN_BACKUP_DIR"]),
        Path(environment["SING_YIN_LOG_DIR"]),
        Path(environment["SING_YIN_SUPPORT_DIR"]),
        storage_path,
    )
    canonical_paths = {
        (PROJECT_ROOT / "data" / "runtime" / "sing-yin-roster.sqlite3").resolve(),
        (PROJECT_ROOT / "data" / "backups").resolve(),
        (PROJECT_ROOT / ".nicegui").resolve(),
    }
    for path in mutable_paths:
        resolved = path.resolve()
        if resolved in canonical_paths or PROJECT_ROOT == resolved or PROJECT_ROOT in resolved.parents:
            raise ThemeControlVerificationError(f"Mutable verifier path escaped the temporary root: {resolved}")
        if case_root.resolve() != resolved and case_root.resolve() not in resolved.parents:
            raise ThemeControlVerificationError(f"Mutable verifier path is outside its case root: {resolved}")
    return environment


def _new_context(
    browser: Browser,
    *,
    access_mode: AccessMode,
    viewport_mode: ViewportMode,
    colour_scheme: ColourScheme,
) -> BrowserContext:
    options: dict[str, Any] = {
        "viewport": {"width": 1440, "height": 960}
        if viewport_mode == "desktop"
        else {"width": 390, "height": 844},
        "color_scheme": colour_scheme,
        "reduced_motion": "no-preference",
    }
    if viewport_mode == "mobile":
        options.update({"is_mobile": True, "has_touch": True})
    context = browser.new_context(**options)
    if access_mode == "guest":
        _install_gateway_stubs(context)
    return context


def _theme_control(page: Page, *, viewport_mode: ViewportMode) -> Locator:
    if viewport_mode == "desktop":
        control = page.get_by_test_id("theme-control")
        if control.count() != 1:
            raise ThemeControlVerificationError("Desktop appearance control is not unique.")
        control.wait_for(state="visible", timeout=10_000)
        if page.get_by_test_id("desktop-theme-menu").count() != 0:
            raise ThemeControlVerificationError("Obsolete desktop appearance menu is still rendered.")
        return control

    drawer = _open_mobile_drawer(page)
    control = drawer.get_by_test_id("mobile-theme-control")
    if control.count() != 1:
        raise ThemeControlVerificationError("Mobile appearance control is not unique.")
    control.wait_for(state="visible", timeout=10_000)
    return control


def _normalise_hex(value: str) -> str:
    return value.strip().lower().replace(" ", "")


def _assert_theme_state(
    page: Page,
    control: Locator,
    *,
    expected_theme: ColourScheme,
    expected_preference: Literal["system", "light", "dark"],
) -> dict[str, Any]:
    expected_dark = expected_theme == "dark"
    page.wait_for_function(
        """([testId, expectedTheme, expectedPreference]) => {
          const control = document.querySelector(`[data-testid="${testId}"]`);
          if (!control) return false;
          const rendered = document.body.classList.contains('body--dark') ? 'dark' : 'light';
          return rendered === expectedTheme &&
            control.dataset.themeResolved === expectedTheme &&
            control.dataset.themePreference === expectedPreference &&
            control.getAttribute('aria-pressed') === String(expectedTheme === 'dark');
        }""",
        arg=[
            "mobile-theme-control"
            if control.get_attribute("data-testid") == "mobile-theme-control"
            else "theme-control",
            expected_theme,
            expected_preference,
        ],
        timeout=10_000,
    )

    state = page.evaluate(
        """testId => {
          const control = document.querySelector(`[data-testid="${testId}"]`);
          const icon = control?.querySelector('.q-icon');
          return {
            bodyDark: document.body.classList.contains('body--dark'),
            quasarDark: Boolean(window.Quasar?.Dark?.isActive),
            qPrimary: getComputedStyle(document.body).getPropertyValue('--q-primary'),
            preference: control?.dataset.themePreference || '',
            resolved: control?.dataset.themeResolved || '',
            pressed: control?.getAttribute('aria-pressed') || '',
            label: control?.getAttribute('aria-label') || '',
            title: control?.getAttribute('title') || '',
            actionLight: control?.dataset.actionLight || '',
            actionDark: control?.dataset.actionDark || '',
            icon: (icon?.textContent || '').trim(),
          };
        }""",
        control.get_attribute("data-testid"),
    )
    expected_label = state["actionLight"] if expected_dark else state["actionDark"]
    expected_icon = "dark_mode" if expected_dark else "light_mode"
    failures: list[str] = []
    if state["bodyDark"] is not expected_dark:
        failures.append("body--dark")
    if state["quasarDark"] is not expected_dark:
        failures.append("Quasar.Dark.isActive")
    if _normalise_hex(str(state["qPrimary"])) != EXPECTED_PRIMARY[expected_theme]:
        failures.append(
            f"--q-primary={state['qPrimary']!r}, expected {EXPECTED_PRIMARY[expected_theme]!r}"
        )
    if state["preference"] != expected_preference:
        failures.append(f"preference={state['preference']!r}")
    if state["resolved"] != expected_theme:
        failures.append(f"resolved={state['resolved']!r}")
    if state["pressed"] != str(expected_dark).lower():
        failures.append(f"aria-pressed={state['pressed']!r}")
    if not expected_label or state["label"] != expected_label or state["title"] != expected_label:
        failures.append("aria-label/title action semantics")
    if state["icon"] != expected_icon:
        failures.append(f"icon={state['icon']!r}, expected {expected_icon!r}")
    if failures:
        raise ThemeControlVerificationError(
            f"Theme state mismatch for {expected_theme}/{expected_preference}: {', '.join(failures)}"
        )
    return state


def _screenshot(page: Page, evidence_dir: Path, name: str) -> str:
    path = (evidence_dir / f"{name}.png").resolve()
    page.screenshot(path=str(path), full_page=False)
    return str(path)


def _exercise_case(
    browser: Browser,
    evidence_root: Path,
    *,
    access_mode: AccessMode,
    viewport_mode: ViewportMode,
    colour_scheme: ColourScheme,
) -> dict[str, Any]:
    case_id = f"{access_mode}-{viewport_mode}-os-{colour_scheme}"
    case_root = (evidence_root / "runtime" / case_id).resolve()
    environment = _safe_environment(case_root, access_mode=access_mode)
    server_log = case_root / "server-console.log"
    process, output = _start_server(environment, server_log)
    context: BrowserContext | None = None
    console_errors: list[str] = []
    page_errors: list[str] = []
    case_error: BaseException | None = None
    try:
        _wait_until_ready(process, environment["SING_YIN_TEST_URL"], server_log)
        context = _new_context(
            browser,
            access_mode=access_mode,
            viewport_mode=viewport_mode,
            colour_scheme=colour_scheme,
        )
        page = context.new_page()
        page.on(
            "console",
            lambda message: console_errors.append(message.text) if message.type == "error" else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        _open_route(page, environment["SING_YIN_TEST_URL"], "/")
        page.wait_for_function("() => Boolean(window.__syThemeControls)", timeout=10_000)

        control = _theme_control(page, viewport_mode=viewport_mode)
        initial = _assert_theme_state(
            page,
            control,
            expected_theme=colour_scheme,
            expected_preference="system",
        )
        initial_shot = _screenshot(page, evidence_root / "screenshots", f"{case_id}-initial")

        first_target: ColourScheme = "dark" if colour_scheme == "light" else "light"
        control.click()
        control = page.get_by_test_id(
            "theme-control" if viewport_mode == "desktop" else "mobile-theme-control"
        )
        first_click = _assert_theme_state(
            page,
            control,
            expected_theme=first_target,
            expected_preference=first_target,
        )
        first_click_shot = _screenshot(
            page,
            evidence_root / "screenshots",
            f"{case_id}-first-click-{first_target}",
        )

        _open_route(page, environment["SING_YIN_TEST_URL"], "/platform")
        page.wait_for_function("() => Boolean(window.__syThemeControls)", timeout=10_000)
        control = _theme_control(page, viewport_mode=viewport_mode)
        persisted = _assert_theme_state(
            page,
            control,
            expected_theme=first_target,
            expected_preference=first_target,
        )

        control.click()
        control = page.get_by_test_id(
            "theme-control" if viewport_mode == "desktop" else "mobile-theme-control"
        )
        reversed_state = _assert_theme_state(
            page,
            control,
            expected_theme=colour_scheme,
            expected_preference=colour_scheme,
        )
        reverse_shot = _screenshot(
            page,
            evidence_root / "screenshots",
            f"{case_id}-reverse-{colour_scheme}",
        )

        page.reload(wait_until="domcontentloaded", timeout=20_000)
        page.wait_for_selector("main#main-content", timeout=15_000)
        page.wait_for_function("() => Boolean(window.__syThemeControls)", timeout=10_000)
        control = _theme_control(page, viewport_mode=viewport_mode)
        reverse_persisted = _assert_theme_state(
            page,
            control,
            expected_theme=colour_scheme,
            expected_preference=colour_scheme,
        )
        if console_errors or page_errors:
            raise ThemeControlVerificationError(
                f"{case_id} emitted browser errors: console={console_errors!r}; page={page_errors!r}"
            )
        return {
            "case": case_id,
            "accessMode": access_mode,
            "viewport": viewport_mode,
            "osColourScheme": colour_scheme,
            "initial": initial,
            "firstClick": first_click,
            "routePersistence": persisted,
            "reverseToggle": reversed_state,
            "reverseReloadPersistence": reverse_persisted,
            "screenshots": [initial_shot, first_click_shot, reverse_shot],
            "databasePath": environment["SING_YIN_DATABASE_PATH"],
            "niceguiStoragePath": environment["NICEGUI_STORAGE_PATH"],
            "serverLog": str(server_log),
        }
    except BaseException as error:
        case_error = error
        raise
    finally:
        if context is not None:
            context.close()
        _stop_server(process, output)
        try:
            _assert_server_console_clean(server_log)
        except Exception:
            # Preserve the browser-visible contract failure when it caused the
            # matching server exception; otherwise the report would replace
            # the actionable root cause with a generic console marker.
            if case_error is None:
                raise


def main() -> int:
    evidence_root = Path(tempfile.mkdtemp(prefix="sing-yin-rc31-theme-")).resolve()
    (evidence_root / "screenshots").mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schemaVersion": 1,
        "status": "running",
        "verifiedAt": datetime.now(timezone.utc).isoformat(),
        "evidenceRoot": str(evidence_root),
        "cases": [],
    }
    report_path = evidence_root / "verification.json"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for access_mode in ("admin", "guest"):
                    for viewport_mode in ("desktop", "mobile"):
                        for colour_scheme in ("light", "dark"):
                            report["cases"].append(
                                _exercise_case(
                                    browser,
                                    evidence_root,
                                    access_mode=access_mode,
                                    viewport_mode=viewport_mode,
                                    colour_scheme=colour_scheme,
                                )
                            )
                            report_path.write_text(
                                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8",
                            )
            finally:
                browser.close()
        report["status"] = "pass"
        report["completedAt"] = datetime.now(timezone.utc).isoformat()
    except Exception as error:
        report["status"] = "fail"
        report["completedAt"] = datetime.now(timezone.utc).isoformat()
        report["failureType"] = type(error).__name__
        report["failure"] = str(error)
        raise
    finally:
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"RC31 theme evidence: {report_path}", flush=True)
    print(f"RC31 binary appearance verification passed ({len(report['cases'])} cases).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
