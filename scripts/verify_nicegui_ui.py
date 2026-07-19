"""Browser smoke checks for the persistent NiceGUI shell and key routes."""

from __future__ import annotations

import os
import sqlite3
import csv
import json
from http.client import HTTPConnection
from io import BytesIO, StringIO
from pathlib import Path
import sys
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openpyxl import Workbook
from playwright.sync_api import sync_playwright

from nicegui_app.ui.product_identity import PRODUCT_IDENTITY

BASE_URL = os.getenv("SING_YIN_TEST_URL", "http://127.0.0.1:8080")
YOUTUBE_ENABLED = os.getenv("SING_YIN_YOUTUBE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
FAVICON_PRODUCT_ASSET = PRODUCT_IDENTITY.product_asset(
    PRODUCT_IDENTITY.delivery["faviconVariant"]
)
FAVICON_PRODUCT_PATH = FAVICON_PRODUCT_ASSET.path
NAVIGATION_PRODUCT_ASSETS = {
    appearance: PRODUCT_IDENTITY.product_asset(
        PRODUCT_IDENTITY.delivery[f"navigation{appearance.title()}Variant"]
    )
    for appearance in ("light", "dark")
}
LIGHT_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-dashboard-light.png"
DARK_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-dashboard-dark.png"
ROSTER_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-roster-workspace.png"
PREFECT_IMPORT_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-prefect-import.png"
FAIRNESS_REPORT_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-fairness-report.png"
PREFECT_IMPORT_DARK_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-prefect-import-dark.png"
FAIRNESS_REPORT_DARK_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-fairness-report-dark.png"
PREFECT_REPORT_MOBILE_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-prefect-report-mobile.png"
MOBILE_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-dashboard-mobile.png"
ONBOARDING_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-getting-started.png"
PROGRESS_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-progress-dialog.png"
HANDOVER_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-handover-light.png"
HANDOVER_DARK_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-handover-dark.png"
HANDOVER_MOBILE_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-handover-mobile.png"
PLATFORM_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-platform-team-light.png"
PLATFORM_DARK_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-platform-team-dark.png"
PLATFORM_MOBILE_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-platform-team-mobile.png"
ENGINEERING_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-engineering-quality-light.png"
ENGINEERING_DARK_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-engineering-quality-dark.png"
ENGINEERING_MOBILE_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-engineering-quality-mobile.png"
GUIDE_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-guide-light.png"
GUIDE_DARK_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-guide-dark.png"
GUIDE_MOBILE_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-guide-mobile.png"
ARCHITECTURE_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-system-architecture.png"
ARCHITECTURE_DARK_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-system-architecture-dark.png"
ARCHITECTURE_MOBILE_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-system-architecture-mobile.png"
HOVER_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-pointer-hover.png"
MUSIC_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-page-music.png"
ROSTER_RECOVERY_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-roster-unavailable.png"
SETTINGS_LIGHT_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-settings-light.png"
SETTINGS_DARK_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-settings-dark.png"
SETTINGS_MOBILE_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-settings-mobile.png"
DEVOTIONAL_LIGHT_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-devotional-light.png"
DEVOTIONAL_DARK_SCREENSHOT = PROJECT_ROOT / "logs" / "nicegui-devotional-dark.png"
COMPONENT_EVIDENCE_DIR = PROJECT_ROOT / "test-results" / "uiverse-components"
COMPONENT_LIGHT_SCREENSHOT = COMPONENT_EVIDENCE_DIR / "desktop-light-components.png"
COMPONENT_DARK_SCREENSHOT = COMPONENT_EVIDENCE_DIR / "desktop-dark-components.png"
COMPONENT_MOBILE_LIGHT_SCREENSHOT = COMPONENT_EVIDENCE_DIR / "mobile-320-light-components.png"
COMPONENT_MOBILE_DARK_SCREENSHOT = COMPONENT_EVIDENCE_DIR / "mobile-390-dark-components.png"


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


def invalid_formula_workbook_bytes() -> bytes:
    """Build an in-memory workbook that the local import safety policy must reject."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Prefects"
    worksheet.append(["姓名", "級別", "班別", "職務", "可值班日"])
    worksheet.append(["=1+1", "F.3", "3H", "導學風紀", "星期一、星期三"])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def fictional_directory_csv_bytes() -> tuple[bytes, int]:
    """Build the checked-in fictional directory for an isolated browser import."""
    seed_path = PROJECT_ROOT / "data" / "demo" / "prefects.zh-HK.seed.json"
    prefects = json.loads(seed_path.read_text(encoding="utf-8"))["prefects"]
    day_labels = {
        "MONDAY": "星期一",
        "TUESDAY": "星期二",
        "WEDNESDAY": "星期三",
        "THURSDAY": "星期四",
        "FRIDAY": "星期五",
    }
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["姓名", "級別", "班別", "職務", "可值班日"])
    for prefect in prefects:
        role = "助理首席導學風紀" if "Assistant Head" in prefect["role"] else "導學風紀"
        writer.writerow(
            [
                prefect["name"],
                prefect["form"],
                prefect["class"],
                role,
                "、".join(day_labels[day] for day in prefect["availableDays"]),
            ]
        )
    return output.getvalue().encode("utf-8-sig"), len(prefects)


def element_contrast_ratio(locator) -> float:  # type: ignore[no-untyped-def]
    """Measure the rendered foreground against composited ancestor backgrounds."""
    return float(
        locator.evaluate(
            """
            element => {
              const parse = value => {
                const numbers = (value.match(/[0-9.]+/g) || []).map(Number);
                return {r: numbers[0] || 0, g: numbers[1] || 0, b: numbers[2] || 0,
                        a: numbers.length > 3 ? numbers[3] : 1};
              };
              const over = (top, bottom) => {
                const a = top.a + bottom.a * (1 - top.a);
                if (a === 0) return {r: 0, g: 0, b: 0, a: 0};
                return {
                  r: (top.r * top.a + bottom.r * bottom.a * (1 - top.a)) / a,
                  g: (top.g * top.a + bottom.g * bottom.a * (1 - top.a)) / a,
                  b: (top.b * top.a + bottom.b * bottom.a * (1 - top.a)) / a,
                  a,
                };
              };
              const layers = [];
              for (let node = element; node; node = node.parentElement) {
                layers.push(parse(getComputedStyle(node).backgroundColor));
              }
              let background = {r: 255, g: 255, b: 255, a: 1};
              for (let index = layers.length - 1; index >= 0; index -= 1) {
                background = over(layers[index], background);
              }
              const foreground = over(parse(getComputedStyle(element).color), background);
              const luminance = color => {
                const channels = [color.r, color.g, color.b].map(channel => {
                  const value = channel / 255;
                  return value <= 0.04045 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4);
                });
                return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
              };
              const light = Math.max(luminance(foreground), luminance(background));
              const dark = Math.min(luminance(foreground), luminance(background));
              return (light + 0.05) / (dark + 0.05);
            }
            """
        )
    )


def assert_status_tone_contrast(page) -> None:  # type: ignore[no-untyped-def]
    """Guard every semantic pill tone in the browser's real cascade."""
    page.evaluate(
        """
        () => {
          document.querySelector('[data-testid="tone-contrast-fixture"]')?.remove();
          const surface = document.createElement('div');
          surface.className = 'sy-surface';
          surface.dataset.testid = 'tone-contrast-fixture';
          for (const tone of ['action', 'stable', 'attention', 'danger', 'neutral']) {
            const badge = document.createElement('span');
            badge.className = `q-badge sy-status-badge sy-tone-${tone}`;
            badge.dataset.tone = tone;
            badge.textContent = tone;
            surface.appendChild(badge);
          }
          document.body.appendChild(surface);
        }
        """
    )
    fixture = page.get_by_test_id("tone-contrast-fixture")
    for tone in ("action", "stable", "attention", "danger", "neutral"):
        badge = fixture.locator(f'[data-tone="{tone}"]')
        ratio = element_contrast_ratio(badge)
        assert ratio >= 4.5, f"{tone} status contrast was only {ratio:.2f}:1"
    fixture.evaluate("element => element.remove()")


def ensure_rendered_theme(page, target: str) -> None:  # type: ignore[no-untyped-def]
    """Switch through the visible UI at desktop or phone width and wait for the real body state."""

    assert target in {"light", "dark"}
    wants_dark = target == "dark"
    if (page.locator("body.body--dark").count() == 1) == wants_dark:
        return

    icon = "dark_mode" if wants_dark else "light_mode"
    visible_controls = page.locator("button:visible").filter(
        has=page.locator("i.q-icon", has_text=icon)
    )
    if visible_controls.count() == 0:
        mobile_navigation = page.get_by_test_id("mobile-bottom-navigation")
        assert mobile_navigation.count() == 1
        mobile_navigation.locator("button").last.click()
        drawer_tools = page.get_by_test_id("mobile-drawer-tools")
        drawer_tools.wait_for(timeout=10_000)
        visible_controls = page.locator("button:visible").filter(
            has=page.locator("i.q-icon", has_text=icon)
        )

    assert visible_controls.count() >= 1
    visible_controls.first.click()
    if wants_dark:
        page.locator("body.body--dark").wait_for(timeout=10_000)
    else:
        page.locator("body:not(.body--dark)").wait_for(timeout=10_000)
    # The mobile drawer deliberately remains open after changing a preference.
    # The isolated component evidence layer is placed above and hides shell chrome
    # while capturing, so the verification does not depend on drawer-close timing.


def assert_component_grammar(page, screenshot_path: Path) -> None:  # type: ignore[no-untyped-def]
    """Render the production cascade as a temporary, data-free component matrix."""

    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    page.evaluate(
        """
        () => {
          document.querySelector('#sy-component-evidence')?.remove();
          const fixture = document.createElement('section');
          fixture.id = 'sy-component-evidence';
          fixture.className = 'sy-surface';
          fixture.setAttribute('aria-label', 'Component verification fixture');
          fixture.style.cssText = [
            'position:relative', 'z-index:2147483000', 'isolation:isolate', 'display:grid', 'gap:18px',
            'width:100%', 'max-width:980px', 'margin:0 auto 24px', 'padding:22px',
            'border:1px solid var(--sy-line)', 'border-radius:22px',
            'background:var(--sy-surface)', 'color:var(--sy-ink)',
            'box-shadow:0 16px 42px rgba(28,28,30,.10)'
          ].join(';');
          fixture.innerHTML = `
            <div style="display:grid;gap:4px">
              <strong style="font-size:18px">統一元件語法 · Unified component grammar</strong>
              <span style="color:var(--sy-muted);font-size:12px">Data-free browser verification fixture</span>
            </div>
            <div data-group="actions" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,180px),1fr));gap:12px">
              <button id="componentPrimary" class="q-btn q-btn-item non-selectable no-outline q-btn--rectangle q-btn--standard bg-primary text-white"><span class="q-btn__content">主要操作 · Primary</span></button>
              <button id="componentSecondary" class="q-btn q-btn-item non-selectable no-outline q-btn--rectangle q-btn--outline text-primary"><span class="q-btn__content">檢視 · Secondary</span></button>
              <button id="componentTertiary" class="q-btn q-btn-item non-selectable no-outline q-btn--rectangle q-btn--flat text-primary"><span class="q-btn__content">稍後 · Tertiary</span></button>
              <button id="componentAttention" class="q-btn q-btn-item non-selectable no-outline q-btn--rectangle q-btn--outline text-primary sy-button-attention"><span class="q-btn__content">復原核對 · Attention</span></button>
              <button id="componentDanger" class="q-btn q-btn-item non-selectable no-outline q-btn--rectangle q-btn--standard bg-negative text-white"><span class="q-btn__content">移除 · Danger</span></button>
              <button id="componentDangerOutline" class="q-btn q-btn-item non-selectable no-outline q-btn--rectangle q-btn--outline text-negative"><span class="q-btn__content">審慎移除 · Danger outline</span></button>
              <button id="componentDisabled" class="q-btn q-btn-item non-selectable no-outline q-btn--rectangle q-btn--standard bg-primary text-white disabled" aria-disabled="true"><span class="q-btn__content">尚未可用 · Disabled</span></button>
              <button id="componentBusy" class="q-btn q-btn-item non-selectable no-outline q-btn--rectangle q-btn--standard bg-primary text-white" aria-busy="true"><span class="q-btn__content">處理中 · Busy</span></button>
            </div>
            <div data-group="forms" style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;padding:14px;border:1px solid var(--sy-line);border-radius:16px;background:var(--sy-surface-subtle)">
              <label id="componentCheckbox" class="q-checkbox cursor-pointer no-outline row inline no-wrap items-center" tabindex="0" role="checkbox" aria-checked="true"><div class="q-checkbox__inner relative-position non-selectable q-checkbox__inner--truthy text-primary" aria-hidden="true"><input class="hidden q-checkbox__native absolute q-ma-none q-pa-none" type="checkbox" checked><div class="q-checkbox__bg absolute"><svg class="q-checkbox__svg fit absolute-full" viewBox="0 0 24 24"><path class="q-checkbox__truthy" fill="none" d="M4.1 12.7 9 17.6 20.3 6.3"></path></svg></div></div><div class="q-checkbox__label q-anchor--skip">已核對</div></label>
              <label id="componentToggle" class="q-toggle cursor-pointer no-outline row inline no-wrap items-center" tabindex="0" role="switch" aria-checked="true"><div class="q-toggle__inner relative-position non-selectable q-toggle__inner--truthy text-primary" aria-hidden="true"><input class="hidden q-toggle__native absolute q-ma-none q-pa-none" type="checkbox" checked><div class="q-toggle__track"></div><div class="q-toggle__thumb absolute flex flex-center no-wrap"></div></div><div class="q-toggle__label q-anchor--skip">已啟用</div></label>
              <label id="componentRadio" class="q-radio cursor-pointer no-outline row inline no-wrap items-center" tabindex="0" role="radio" aria-checked="true"><div class="q-radio__inner relative-position non-selectable q-radio__inner--truthy text-primary" aria-hidden="true"><input class="hidden q-radio__native absolute q-ma-none q-pa-none" type="radio" checked><div class="q-radio__bg absolute"><svg class="q-radio__svg fit absolute-full" viewBox="0 0 24 24"><path class="q-radio__check" d="M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z"></path></svg></div></div><div class="q-radio__label q-anchor--skip">目前選項</div></label>
              <label id="componentToggleDisabled" class="q-toggle row no-wrap inline items-center disabled" role="switch" aria-checked="false" aria-disabled="true"><div class="q-toggle__inner relative-position non-selectable q-toggle__inner--falsy" aria-hidden="true"><input class="hidden q-toggle__native absolute q-ma-none q-pa-none" type="checkbox" disabled><div class="q-toggle__track"></div><div class="q-toggle__thumb absolute flex flex-center no-wrap"></div></div><div class="q-toggle__label q-anchor--skip">不可用</div></label>
            </div>
            <div data-group="data" style="display:grid;gap:14px">
              <div class="q-tabs"><div id="componentTab" class="q-tab q-tab--active" style="display:inline-flex;padding:10px 16px">本週值班</div></div>
              <div class="q-linear-progress" style="position:relative;height:8px;overflow:hidden;border-radius:999px"><div id="componentProgress" class="q-linear-progress__model" style="position:absolute;inset:0 35% 0 0"></div></div>
            </div>`;
          (document.querySelector('main#main-content') || document.body).prepend(fixture);
        }
        """
    )
    fixture = page.locator("#sy-component-evidence")
    fixture.wait_for(timeout=5_000)
    # Quasar outlines live on ::before and semantic button transitions settle
    # shortly after this fixture enters the production cascade.
    page.wait_for_timeout(500)
    styles = page.evaluate(
        """
        () => {
          const pick = id => {
            const element = document.getElementById(id);
            const style = getComputedStyle(element);
            const before = getComputedStyle(element, '::before');
            return {color: style.color, background: style.backgroundImage,
                    backgroundColor: style.backgroundColor, border: style.borderTopColor,
                    outlineBorder: before.borderTopColor,
                    outlineWidth: before.borderTopWidth,
                    shadow: style.boxShadow, opacity: Number(style.opacity), cursor: style.cursor};
          };
          return Object.fromEntries(['componentPrimary', 'componentSecondary', 'componentAttention',
            'componentDanger', 'componentDangerOutline', 'componentDisabled', 'componentBusy',
            'componentTab', 'componentProgress', 'componentToggleDisabled'].map(id => [id, pick(id)]));
        }
        """
    )
    assert styles["componentPrimary"]["backgroundColor"] != styles["componentDanger"]["backgroundColor"], styles
    assert styles["componentPrimary"]["border"] != styles["componentDanger"]["border"], styles
    assert styles["componentPrimary"]["shadow"] != "none", styles
    assert styles["componentDanger"]["shadow"] != "none", styles
    outline_signatures = {
        (styles[key]["color"], styles[key]["outlineBorder"])
        for key in ("componentSecondary", "componentAttention", "componentDangerOutline")
    }
    assert len(outline_signatures) == 3, styles
    assert all(
        styles[key]["outlineWidth"] == "1px"
        for key in ("componentSecondary", "componentAttention", "componentDangerOutline")
    ), styles
    assert styles["componentDisabled"]["opacity"] < 0.8
    assert styles["componentBusy"]["cursor"] in {"wait", "progress"}
    assert styles["componentProgress"]["background"] != "none"
    assert styles["componentToggleDisabled"]["opacity"] < 0.8

    for component_id in (
        "componentPrimary",
        "componentSecondary",
        "componentTertiary",
        "componentAttention",
        "componentDanger",
        "componentDangerOutline",
        "componentBusy",
    ):
        ratio = element_contrast_ratio(page.locator(f"#{component_id} .q-btn__content"))
        assert ratio >= 4.5, f"{component_id} label contrast was only {ratio:.2f}:1"

    layout = fixture.evaluate(
        """
        element => {
          const groups = ['[data-group="actions"] > button', '[data-group="forms"] > label'];
          const outside = [];
          const overlaps = [];
          const root = element.getBoundingClientRect();
          for (const selector of groups) {
            const items = [...element.querySelectorAll(selector)];
            const boxes = items.map(item => ({id: item.id, box: item.getBoundingClientRect()}));
            for (const {id, box} of boxes) {
              if (box.left < root.left - 1 || box.right > root.right + 1 ||
                  box.top < root.top - 1 || box.bottom > root.bottom + 1) outside.push(id);
              if (innerWidth <= 420 && (box.width < 44 || box.height < 44)) {
                outside.push(`${id}:touch-${box.width.toFixed(1)}x${box.height.toFixed(1)}`);
              }
            }
            for (let i = 0; i < boxes.length; i += 1) {
              for (let j = i + 1; j < boxes.length; j += 1) {
                const a = boxes[i]; const b = boxes[j];
                const intersects = Math.min(a.box.right, b.box.right) - Math.max(a.box.left, b.box.left) > 1 &&
                  Math.min(a.box.bottom, b.box.bottom) - Math.max(a.box.top, b.box.top) > 1;
                if (intersects) overlaps.push(`${a.id}/${b.id}`);
              }
            }
          }
          return {outside, overlaps};
        }
        """
    )
    assert not layout["outside"], layout
    assert not layout["overlaps"], layout

    page.evaluate(
        """
        () => {
          const host = document.createElement('div');
          host.id = 'componentNotificationProbes';
          host.style.cssText = 'position:absolute;left:-10000px;top:0;display:grid;gap:8px';
          host.innerHTML = [
            ['positive text-white', 'stable'], ['info text-white', 'info'],
            ['warning text-dark', 'attention'], ['negative text-white', 'danger']
          ].map(([tone, id]) =>
            `<div class="q-notification bg-${tone}"><div id="notification-${id}" class="q-notification__message">${id}</div></div>`
          ).join('');
          document.body.appendChild(host);
        }
        """
    )
    try:
        for tone in ("stable", "info", "attention", "danger"):
            ratio = element_contrast_ratio(page.locator(f"#notification-{tone}"))
            assert ratio >= 4.5, f"{tone} notification contrast was only {ratio:.2f}:1"
    finally:
        page.locator("#componentNotificationProbes").evaluate("element => element.remove()")

    page.locator("#componentCheckbox").focus()
    focus_style = page.locator("#componentCheckbox .q-checkbox__inner").evaluate(
        "element => ({style:getComputedStyle(element).outlineStyle, width:getComputedStyle(element).outlineWidth})"
    )
    assert focus_style["style"] != "none" and float(focus_style["width"].removesuffix("px")) >= 3
    page.locator("#componentCheckbox").evaluate("element => element.blur()")
    page.evaluate(
        """
        () => {
          const selectors = '.sy-app-header,.sy-mobile-tabbar,.q-drawer,.q-drawer__backdrop,.sy-skip-link,.sy-status-stack';
          document.querySelectorAll(selectors).forEach(element => {
            element.dataset.syEvidenceVisibility = element.style.visibility || '';
            element.style.visibility = 'hidden';
          });
        }
        """
    )
    try:
        fixture.screenshot(path=str(screenshot_path))
    finally:
        page.evaluate(
            """
            () => {
              document.querySelectorAll('[data-sy-evidence-visibility]').forEach(element => {
                element.style.visibility = element.dataset.syEvidenceVisibility;
                delete element.dataset.syEvidenceVisibility;
              });
            }
            """
        )
        fixture.evaluate("element => element.remove()")


def assert_reference_toc(page, *, required_targets: tuple[str, ...]) -> None:  # type: ignore[no-untyped-def]
    """Verify the rendered reference navigation without freezing its section count."""

    links = page.get_by_test_id("reference-toc").locator(".sy-reference-toc-link")
    targets = links.evaluate_all(
        "elements => elements.map(element => element.dataset.syTocTarget || '')"
    )
    assert targets, "reference table of contents is empty"
    assert all(targets), "reference table of contents has a link without a target"
    assert len(targets) == len(set(targets)), "reference table of contents repeats a target"
    assert set(required_targets) <= set(targets), "reference table of contents lost a required section"
    for index, target in enumerate(targets):
        assert links.nth(index).get_attribute("href") == f"#{target}"
        assert page.locator(f'[id="{target}"]').count() == 1


def main() -> None:
    LIGHT_SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
    expected_invalid_backups = prepare_invalid_backup_fixture()
    assert_unexpected_host_rejected()
    console_errors: list[str] = []
    page_errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1024})
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        favicon_response = page.request.get(f"{BASE_URL}/favicon.ico")
        assert favicon_response.status == 200
        assert favicon_response.headers.get("content-type", "").split(";", 1)[0] == "image/png"
        assert (
            favicon_response.body() == FAVICON_PRODUCT_PATH.read_bytes()
        ), "favicon did not match the manifest-selected Service Weave product mark"
        page.goto(BASE_URL, wait_until="domcontentloaded")
        skip_link = page.locator("a.sy-skip-link")
        assert skip_link.count() == 1
        page.keyboard.press("Tab")
        assert page.evaluate("document.activeElement?.classList.contains('sy-skip-link')") is True
        page.keyboard.press("Enter")
        page.wait_for_function("document.activeElement?.id === 'main-content'")
        # User storage can retain the previous smoke run's language preference.
        if page.get_by_role("button", name="中").count():
            page.get_by_role("button", name="中").click()
            page.wait_for_load_state("domcontentloaded")
        page.get_by_text("第一次使用", exact=False).or_(
            page.get_by_text("First time here", exact=False)
        ).first.wait_for(timeout=10_000)
        desktop_theme_controls = page.locator(".sy-desktop-header-controls")
        if desktop_theme_controls.locator("i.q-icon", has_text="light_mode").count():
            desktop_theme_controls.locator("i.q-icon", has_text="light_mode").click()
            page.wait_for_load_state("domcontentloaded")
        page.get_by_text("本週值班工作台", exact=True).wait_for(timeout=10_000)
        assert page.locator(".sy-flow-step--active .q-btn.bg-primary").evaluate(
            "element => getComputedStyle(element).backgroundColor"
        ) == "rgb(53, 100, 124)"
        assert_component_grammar(page, COMPONENT_LIGHT_SCREENSHOT)
        assert page.locator(".sy-sidebar .sy-nav-active").evaluate(
            "element => getComputedStyle(element).color"
        ) == "rgb(48, 50, 49)"
        assert page.get_by_test_id("page-music-button").evaluate(
            "element => getComputedStyle(element).color"
        ) == "rgb(48, 50, 49)"
        assert page.locator("main#main-content").count() == 1
        assert page.locator('[role="navigation"][aria-label="主要導覽"]').count() == 1
        assert page.locator('[role="heading"][aria-level="1"]').count() == 1
        assert page.locator('[aria-current="page"]:visible').count() == 1
        assert page.get_by_role("button", name="開啟主要導覽").count() == 1
        sound_toggle = page.get_by_role("button", name="開啟提示音")
        assert sound_toggle.count() == 1
        assert page.get_by_role("button", name="切換深色模式").count() == 1
        assert page.get_by_role("link", name="跳至主要內容").count() == 1
        page.wait_for_function("document.documentElement.dataset.syMotion === 'ready'")
        assert page.evaluate("window.gsap?.version") == "3.13.0"
        primary_flow_action = page.locator(".sy-flow-step--active .q-btn.bg-primary")
        primary_flow_icon = primary_flow_action.locator(".q-icon[data-sy-icon-motion]").first
        primary_flow_icon.wait_for(timeout=5_000)
        assert primary_flow_icon.get_attribute("data-sy-icon-motion") == "forward"
        resting_icon_transform = primary_flow_icon.evaluate(
            "element => getComputedStyle(element).transform"
        )
        primary_flow_action.hover()
        page.wait_for_timeout(220)
        assert primary_flow_icon.evaluate(
            "element => getComputedStyle(element).transform"
        ) != resting_icon_transform
        page.mouse.move(1, 1)
        primary_flow_action.focus()
        page.wait_for_timeout(220)
        assert primary_flow_icon.evaluate(
            "element => getComputedStyle(element).transform"
        ) != resting_icon_transform
        page.evaluate(
            """() => {
              window.__syVerifiedSoundKinds = [];
              window.addEventListener('sy:feedback', event => {
                window.__syVerifiedSoundKinds.push(event.detail?.kind || 'unknown');
              });
            }"""
        )
        sound_toggle.click()
        enabled_sound_toggle = page.get_by_role("button", name="關閉提示音")
        enabled_sound_toggle.wait_for(timeout=5_000)
        assert enabled_sound_toggle.evaluate(
            "element => element.querySelector('.q-btn__content > span.block') === null"
        )
        page.wait_for_function("window.__syVerifiedSoundKinds.includes('success')", timeout=5_000)
        page.wait_for_function("window.__singYinAudioContext !== undefined", timeout=5_000)
        page.reload(wait_until="domcontentloaded")
        page.get_by_role("button", name="關閉提示音").wait_for(timeout=5_000)
        page.get_by_role("button", name="關閉提示音").click()
        page.get_by_role("button", name="開啟提示音").wait_for(timeout=5_000)
        primary_flow_action.dispatch_event("pointerdown")
        page.evaluate(
            """() => {
              const sink = document.createElement('span');
              sink.id = 'sy-feedback-focus-sink';
              sink.tabIndex = -1;
              document.body.appendChild(sink);
              sink.focus();
            }"""
        )
        page.evaluate("window.dispatchEvent(new CustomEvent('sy:feedback', {detail: {kind: 'success'}}))")
        page.locator(
            '.sy-flow-step--active .q-btn.bg-primary[data-sy-feedback-state="success"]'
        ).wait_for(
            timeout=2_000,
            state="attached",
        )
        page.locator(".sy-feedback-pulse--success").wait_for(timeout=2_000, state="attached")
        page.locator(".sy-feedback-pulse--success").wait_for(timeout=2_000, state="detached")
        images_without_alt = page.locator("img:not([alt])").count()
        assert images_without_alt == 0
        navigation_mark = page.get_by_test_id("navigation-product-mark")
        assert navigation_mark.get_attribute("role") == "img"
        for appearance, asset in NAVIGATION_PRODUCT_ASSETS.items():
            navigation_image = navigation_mark.locator(
                f".sy-product-mark-image--{appearance}"
            )
            assert (navigation_image.get_attribute("src") or "").endswith(
                asset.public_url or "__missing_product_mark__"
            )
            page.wait_for_function(
                "element => element.complete && element.naturalWidth > 0",
                arg=navigation_image.element_handle(),
            )
            assert navigation_image.evaluate("element => element.naturalWidth") == 256
        assert (navigation_mark.bounding_box() or {"width": 0})["width"] >= 58
        assert navigation_mark.evaluate(
            "element => getComputedStyle(element).backgroundColor"
        ) == "rgba(0, 0, 0, 0)"
        assert navigation_mark.evaluate(
            "element => getComputedStyle(element).borderTopWidth"
        ) == "0px"
        assert page.locator(".sy-flow-symbol").count() == 3
        assert page.locator(".sy-flow-step--active .sy-tone-action").evaluate(
            "element => getComputedStyle(element).color"
        ) == "rgb(24, 63, 85)"
        assert page.locator(".sy-flow-step--pending .sy-tone-neutral").first.evaluate(
            "element => getComputedStyle(element).color"
        ) == "rgb(52, 54, 58)"
        assert page.locator(".sy-workbench .sy-tone-action").first.evaluate(
            "element => getComputedStyle(element).color"
        ) == "rgb(24, 63, 85)"
        assert "bg-primary" not in (page.locator(".sy-workbench .sy-tone-action").first.get_attribute("class") or "")
        assert_status_tone_contrast(page)
        assert "devotional-sacred-light-v1.webp" in page.locator(".sy-daily-start").evaluate("element => getComputedStyle(element, '::after').backgroundImage")
        assert "weekly-pulse-light-v1.webp" in page.locator(".sy-workbench").evaluate("element => getComputedStyle(element, '::after').backgroundImage")
        assert "paper-fibre-light-v1.svg" in page.locator(".sy-main").evaluate(
            "element => getComputedStyle(element).backgroundImage"
        )
        assert "paper-fibre-light-v1.svg" in page.locator(".sy-workbench").evaluate(
            "element => getComputedStyle(element).backgroundImage"
        )
        assert "linen-weave-light-v1.svg" in page.locator(".sy-sidebar").evaluate(
            "element => getComputedStyle(element, '::after').backgroundImage"
        )
        dashboard_history = page.get_by_test_id("dashboard-history")
        assert dashboard_history.count() == 1
        assert dashboard_history.locator(".sy-dashboard-history-empty").count() == 1
        assert dashboard_history.evaluate("element => getComputedStyle(element).backgroundImage") == "none"
        workbench_box = page.locator(".sy-workbench").bounding_box()
        history_box = dashboard_history.bounding_box()
        assert workbench_box is not None and history_box is not None
        assert history_box["x"] > workbench_box["x"] + workbench_box["width"] - 2
        assert abs(history_box["y"] - workbench_box["y"]) <= 2
        assert page.locator(".sy-devotional-tone-select").count() == 1
        music_button = page.get_by_test_id("page-music-button")
        assert music_button.count() == 1
        music_button.click()
        music_dialog = page.get_by_test_id("page-music-dialog")
        music_dialog.wait_for(timeout=10_000)
        music_dialog.get_by_text("明亮專注", exact=False).first.wait_for(timeout=10_000)
        assert music_dialog.get_by_test_id("music-autoplay-switch").is_checked()
        assert page.locator("body").get_attribute("data-sy-music-autoplay") in {"playing", "blocked"}
        music_state = music_button.get_attribute("data-music-state")
        assert music_state in {"playing", "blocked"}
        assert music_dialog.get_by_test_id("music-playback-status").get_attribute("data-music-state") == music_state
        if music_state == "playing":
            music_dialog.get_by_text("正在播放", exact=True).wait_for(timeout=10_000)
        else:
            music_dialog.get_by_text("等待你按播放", exact=True).wait_for(timeout=10_000)
        music_audio = music_dialog.locator("audio.sy-page-music-audio")
        assert music_audio.count() == 1
        assert music_audio.get_attribute("autoplay") is None
        assert music_audio.get_attribute("loop") is None
        assert "Ambre.m4a" in (music_audio.get_attribute("src") or "")
        assert music_audio.evaluate("element => element.canPlayType('audio/mp4')") != ""
        youtube_panel = music_dialog.get_by_test_id("youtube-player-panel")
        youtube_panel.wait_for(timeout=10_000)
        assert youtube_panel.locator("iframe.sy-youtube-player").count() == 0, "Empty YouTube setup must not contact the platform"
        if YOUTUBE_ENABLED:
            page.get_by_text("此頁暫未設定 YouTube 歌單", exact=False).wait_for(timeout=10_000)
        else:
            page.get_by_text("YouTube 播放器已由環境設定停用", exact=False).wait_for(timeout=10_000)
        page.wait_for_function(
                "element => element.volume >= 0.33 && element.volume <= 0.37",
            arg=music_audio.element_handle(),
            timeout=10_000,
        )
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
        page.goto(f"{BASE_URL}/devotional", wait_until="domcontentloaded")
        page.locator(".sy-devotional-page").wait_for(timeout=10_000)
        # Quasar's desktop drawer animates after navigation.  Capture and measure
        # only after that layout transition has settled, otherwise the first
        # frame can make the reading appear clipped even though the final layout
        # is correct.
        page.wait_for_timeout(450)
        assert page.locator(".sy-devotional-reading-grid .sy-devotional-companion").count() == 3
        assert page.get_by_role("button", name="換一篇經文").count() == 1
        assert page.locator(".sy-devotional-tone-select").count() == 1
        assert "devotional-sacred-light-v1.webp" in page.locator(".sy-chapel").evaluate(
            "element => getComputedStyle(element, '::after').backgroundImage"
        )
        chapel_box = page.locator(".sy-chapel").bounding_box()
        reading_box = page.locator(".sy-devotional-reading").bounding_box()
        assert chapel_box is not None and reading_box is not None
        assert reading_box["x"] >= chapel_box["x"] + 20
        assert reading_box["x"] + reading_box["width"] <= chapel_box["x"] + chapel_box["width"] - 20
        assert page.locator(".sy-chapel").evaluate("element => element.scrollWidth <= element.clientWidth") is True
        page.screenshot(path=str(DEVOTIONAL_LIGHT_SCREENSHOT), full_page=True)
        for path, expected_text in (
            ("/", "今日經文"),
            ("/getting-started", "開始使用"),
            ("/guide", "使用手冊"),
            ("/platform", "平台與團隊"),
            ("/engineering", "工程與品質證據"),
            ("/system-architecture", "系統架構與可信設計"),
            ("/rosters", "請先建立正式名單"),
            ("/prefects", "名單管理"),
            ("/adjustments", "請先建立正式名單"),
            ("/audit", "公平審核"),
            ("/handover", "交接指引"),
        ):
            response = page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded")
            assert response is not None and response.status == 200, path
            page.get_by_text(expected_text, exact=False).first.wait_for(timeout=10_000)
            if path == "/rosters":
                assert "empty-ready-light-v1.webp" in page.locator(".sy-empty-state--illustrated").evaluate(
                    "element => getComputedStyle(element).backgroundImage"
                )
        page.goto(f"{BASE_URL}/handover", wait_until="domcontentloaded")
        assert page.get_by_test_id("reference-toc").locator(".sy-reference-toc-link").count() == 4
        assert page.get_by_test_id("reference-pager").locator(".sy-reference-pager-link").count() == 1
        assert "handover-archive-light-v1.webp" in page.locator(".sy-handover-hero").evaluate("element => getComputedStyle(element, '::after').backgroundImage")
        readiness_cards = page.locator(".sy-handover-readiness-card")
        assert readiness_cards.count() == 3
        readiness_grid = page.get_by_test_id("handover-readiness-grid")
        assert " " in readiness_grid.evaluate("element => getComputedStyle(element).gridTemplateColumns")
        acceptance_status = page.get_by_test_id("acceptance-status")
        acceptance_status.wait_for(timeout=10_000)
        attention_badge = page.locator(".sy-tone-attention").first
        assert "bg-primary" not in (attention_badge.get_attribute("class") or "")
        assert element_contrast_ratio(attention_badge) >= 4.5
        hero_copy = page.locator(".sy-handover-hero-copy")
        assert element_contrast_ratio(hero_copy) >= 4.5
        assert page.get_by_test_id("open-new-directory-import").count() == 1
        page.get_by_text("仍需首席導學風紀及教師顧問確認", exact=True).wait_for(timeout=10_000)
        acceptance_steps = page.get_by_test_id("acceptance-human-steps")
        acceptance_steps.locator(".q-item").click()
        assert acceptance_steps.locator("ol > li").count() == 4
        for button in page.locator(".sy-acceptance-actions .q-btn").all():
            box = button.bounding_box()
            assert box is not None and box["height"] >= 44
        page.screenshot(path=str(HANDOVER_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/platform", wait_until="domcontentloaded")
        platform_toc = page.get_by_test_id("reference-toc").locator(".sy-reference-toc-link")
        assert platform_toc.count() == 7
        operating_map_link = platform_toc.nth(2)
        assert "platform-operating-map-section" in (operating_map_link.get_attribute("href") or "")
        operating_map_link.focus()
        assert operating_map_link.evaluate("element => element === document.activeElement") is True
        assert page.get_by_test_id("reference-pager").locator(".sy-reference-pager-link").count() == 1
        page.get_by_text("共創結語", exact=True).wait_for(timeout=10_000)
        page.get_by_role(
            "heading", name="Study Prefect Team：由服事責任建立的團隊架構", exact=True
        ).wait_for(timeout=10_000)
        feedback_links = page.get_by_test_id("feedback-channel").locator("a")
        assert feedback_links.count() == 2
        feedback_link = page.get_by_test_id("feedback-channel").locator('a[href^="mailto:s10777@syss.edu.hk"]')
        github_link = page.get_by_test_id("feedback-channel").locator('a[href^="https://github.com/JackyLi10777/"]')
        assert feedback_link.count() == 1 and github_link.count() == 1
        feedback_box = feedback_link.bounding_box()
        assert feedback_box is not None and feedback_box["height"] >= 44
        github_box = github_link.bounding_box()
        assert github_box is not None and github_box["height"] >= 44
        assert github_link.get_attribute("target") == "_blank"
        sidebar_feedback_links = page.get_by_test_id("sidebar-feedback").locator("a")
        assert sidebar_feedback_links.count() == 2
        assert (sidebar_feedback_links.nth(0).get_attribute("href") or "").startswith("mailto:s10777@syss.edu.hk")
        assert (sidebar_feedback_links.nth(1).get_attribute("href") or "").startswith("https://github.com/JackyLi10777/")
        assert page.get_by_test_id("platform-live-summary").locator(".sy-platform-metric").count() == 4
        assert page.get_by_test_id("team-operating-model").locator(".sy-team-role").count() == 4
        assert page.get_by_test_id("capability-map").locator(".sy-capability-card").count() == 4
        assert page.get_by_test_id("platform-operating-map").locator(".sy-platform-map-node").count() == 6
        assert page.get_by_test_id("solutions-portfolio").locator(".sy-solution-card").count() == 4
        assert page.get_by_test_id("platform-principles").locator(".sy-platform-value").count() == 5
        assert page.get_by_test_id("platform-resources").locator(".sy-platform-resource").count() == 3
        team_role = page.get_by_test_id("team-operating-model").locator(".sy-team-role").first
        team_role_icon = team_role.locator(".sy-team-role-icon")
        team_role.scroll_into_view_if_needed()
        page.wait_for_function(
            """() => {
              const model = document.querySelector(
                '[data-testid="team-operating-model"]'
              );
              const role = model?.querySelector('.sy-team-role');
              return model?.dataset.syMotionComplete === 'true'
                && role
                && getComputedStyle(role).transform === 'none';
            }""",
            timeout=2_000,
        )
        static_card_transform = team_role.evaluate(
            "element => getComputedStyle(element).transform"
        )
        static_icon_transform = team_role_icon.evaluate(
            "element => getComputedStyle(element).transform"
        )
        team_role.hover()
        page.wait_for_timeout(220)
        assert team_role.evaluate(
            "element => getComputedStyle(element).transform"
        ) == static_card_transform
        assert team_role_icon.evaluate(
            "element => getComputedStyle(element).transform"
        ) != static_icon_transform
        assert "platform-stewardship-light-v1.webp" in page.locator(".sy-platform-hero").evaluate(
            "element => getComputedStyle(element, '::before').backgroundImage"
        )
        display_crest = page.locator(".sy-co-creation-crest")
        display_crest_image = display_crest.locator("img")
        assert "sing-yin-crest-display-web.png" in (display_crest_image.get_attribute("src") or "")
        display_crest.scroll_into_view_if_needed()
        page.wait_for_function("element => element.complete && element.naturalWidth > 0", arg=display_crest_image.element_handle())
        assert display_crest_image.evaluate("element => element.naturalWidth") == 640
        assert display_crest.evaluate("element => getComputedStyle(element).backgroundColor") == "rgba(0, 0, 0, 0)"
        assert display_crest.evaluate("element => getComputedStyle(element).borderTopWidth") == "0px"
        creator_profile = page.get_by_test_id("co-creation-profile")
        creator_banner_image = creator_profile.locator(".sy-co-creation-banner img")
        creator_avatar_image = creator_profile.locator(".sy-co-creation-avatar img")
        creator_instagram = creator_profile.locator('a[href="https://www.instagram.com/5662jacky/"]')
        assert creator_profile.get_by_text("李創杰 · LI Chuangjie, Jacky", exact=True).count() == 1
        assert creator_banner_image.count() == 1 and creator_avatar_image.count() == 1
        page.wait_for_function(
            "element => element.complete && element.naturalWidth > 0",
            arg=creator_banner_image.element_handle(),
        )
        page.wait_for_function(
            "element => element.complete && element.naturalWidth > 0",
            arg=creator_avatar_image.element_handle(),
        )
        assert creator_banner_image.evaluate("element => element.naturalWidth") == 1536
        assert creator_avatar_image.evaluate("element => element.naturalWidth") == 1024
        assert creator_instagram.count() == 1
        assert creator_instagram.get_attribute("target") == "_blank"
        creator_instagram_rel = set((creator_instagram.get_attribute("rel") or "").split())
        assert {"noopener", "noreferrer"} <= creator_instagram_rel
        creator_instagram_box = creator_instagram.bounding_box()
        assert creator_instagram_box is not None and creator_instagram_box["height"] >= 44
        assert element_contrast_ratio(creator_profile.locator(".sy-co-creation-name")) >= 4.5
        assert element_contrast_ratio(creator_instagram) >= 4.5
        pointer_surface = page.locator(".sy-co-creation")
        pointer_surface.locator(".sy-pointer-light").wait_for(timeout=10_000, state="attached")
        page.wait_for_timeout(520)
        pointer_surface.hover(position={"x": 86, "y": 74})
        page.wait_for_timeout(240)
        assert float(pointer_surface.locator(".sy-pointer-light").evaluate("element => getComputedStyle(element).opacity")) > 0.8
        pointer_coordinates = pointer_surface.evaluate(
            "element => [element.style.getPropertyValue('--sy-pointer-x'), element.style.getPropertyValue('--sy-pointer-y')]"
        )
        assert all(value.endswith("px") for value in pointer_coordinates), pointer_coordinates
        page.screenshot(path=str(HOVER_SCREENSHOT), full_page=True)
        page.screenshot(path=str(PLATFORM_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/engineering", wait_until="domcontentloaded")
        page.get_by_text("工程與品質證據", exact=True).first.wait_for(timeout=10_000)
        assert "engineering-workbench-light-v1.webp" in page.locator(".sy-engineering-hero").evaluate(
            "element => getComputedStyle(element, '::after').backgroundImage"
        )
        assert page.get_by_test_id("engineering-facts").locator(".sy-engineering-fact").count() == 4
        assert page.get_by_test_id("engineering-blueprint").locator(".sy-engineering-blueprint-layer").count() == 5
        assert page.get_by_test_id("engineering-gates").locator(".sy-engineering-gate").count() == 13
        assert page.get_by_role("heading", level=2).count() >= 5
        assert page.get_by_test_id("engineering-pillars").locator(".sy-engineering-pillar").count() == 6
        assert page.get_by_test_id("engineering-evolution").locator(".sy-engineering-evolution-item").count() == 4
        assert_reference_toc(
            page,
            required_targets=(
                "engineering-evidence-index-section",
                "engineering-resources-section",
            ),
        )
        assert page.get_by_test_id("reference-pager").locator(".sy-reference-pager-link").count() == 1
        engineering_links = page.locator(".sy-engineering-resources a, .sy-engineering-resources .q-btn")
        assert engineering_links.count() == 3
        for link in engineering_links.all():
            link_box = link.bounding_box()
            assert link_box is not None and link_box["height"] >= 44
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth") is True
        page.screenshot(path=str(ENGINEERING_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/system-architecture", wait_until="domcontentloaded")
        assert page.locator(".sy-team-operating-model").count() == 0
        assert page.locator(".sy-capability-map").count() == 0
        assert page.locator(".sy-solutions-grid").count() == 0
        assert page.locator(".sy-architecture-layer").count() == 5
        assert page.get_by_test_id("service-lifeline").locator(".sy-service-stage").count() == 6
        assert page.get_by_test_id("trust-evidence").locator(".sy-trust-evidence-card").count() == 4
        assert page.get_by_test_id("architecture-faq").locator(".sy-architecture-faq-item").count() == 9
        assert_reference_toc(
            page,
            required_targets=(
                "architecture-developer-section",
                "architecture-faq-section",
            ),
        )
        assert page.get_by_test_id("reference-pager").locator(".sy-reference-pager-link").count() == 2
        assert "architecture-lifeline-light-v1.webp" in page.get_by_test_id("architecture-lifeline-visual").evaluate(
            "element => getComputedStyle(element).backgroundImage"
        )
        page.get_by_text("草稿會增加累計工作量嗎？", exact=True).click()
        page.get_by_text("生成或重新生成草稿只保存待核對安排", exact=False).wait_for(timeout=10_000)
        static_layer = page.locator(".sy-architecture-layer").first
        assert static_layer.locator(".sy-pointer-light").count() == 0
        static_layer.hover(position={"x": 86, "y": 74})
        assert "architecture-stewardship-light-v1.webp" in page.locator(".sy-architecture-hero").evaluate("element => getComputedStyle(element, '::before').backgroundImage")
        assert "sidebar-stewardship-light-v1.webp" in page.locator(".sy-sidebar").evaluate("element => getComputedStyle(element).backgroundImage")
        page.screenshot(path=str(ARCHITECTURE_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/guide", wait_until="domcontentloaded")
        assert "guide-handbook-light-v1.webp" in page.locator(".sy-guide-hero").evaluate(
            "element => getComputedStyle(element, '::after').backgroundImage"
        )
        assert page.get_by_test_id("reference-toc").locator(".sy-reference-toc-link").count() == 4
        assert page.get_by_test_id("guide-troubleshooting").locator(".sy-troubleshooting-row").count() == 8
        assert page.get_by_test_id("reference-pager").locator(".sy-reference-pager-link").count() == 2
        page.screenshot(path=str(GUIDE_SCREENSHOT), full_page=True)
        expansion_header = page.locator(".q-expansion-item .q-item").first
        assert expansion_header.evaluate("element => getComputedStyle(element).cursor") == "pointer"
        expansion_header.hover()
        page.wait_for_timeout(190)
        assert expansion_header.evaluate("element => getComputedStyle(element).transform") != "none"
        page.goto(f"{BASE_URL}/getting-started", wait_until="domcontentloaded")
        page.locator(".sy-onboarding-symbol").wait_for(timeout=10_000)
        assert page.get_by_test_id("reference-index").locator(".sy-reference-index-card").count() == 3
        assert "onboarding-desk-light-v1.webp" in page.locator(".sy-onboarding-intro").evaluate("element => getComputedStyle(element, '::after').backgroundImage")
        page.screenshot(path=str(ONBOARDING_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/rosters/999999", wait_until="domcontentloaded")
        unavailable = page.get_by_test_id("roster-unavailable-state")
        unavailable.wait_for(timeout=10_000)
        assert unavailable.get_by_role("button", name="查看現有值班表").count() == 1
        assert unavailable.get_by_role("button", name="核對備份與還原").count() == 1
        page.screenshot(path=str(ROSTER_RECOVERY_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/rosters/999999/adjustments", wait_until="domcontentloaded")
        page.get_by_test_id("adjustment-roster-unavailable-state").wait_for(timeout=10_000)
        page.goto(f"{BASE_URL}/settings", wait_until="domcontentloaded")
        assert page.get_by_test_id("page-music-button").count() == 1
        page.get_by_test_id("online-music-settings").wait_for(timeout=10_000)
        if YOUTUBE_ENABLED:
            page.get_by_test_id("online-music-settings").get_by_text(
                "公開歌單播放已就緒", exact=False
            ).wait_for(timeout=10_000)
        else:
            page.get_by_test_id("online-music-settings").get_by_text(
                "YouTube 播放器已由環境設定停用", exact=False
            ).wait_for(timeout=10_000)
        page.get_by_test_id("music-library-settings").wait_for(timeout=10_000)
        assert page.get_by_test_id("settings-music-autoplay").count() == 1
        settings_profile = page.locator('[name="settings-music-profile"]')
        assert settings_profile.count() == 1
        assert page.locator('[name="youtube-local-import-url"]').count() == 1
        assert page.get_by_role("button", name="下載並加入本機歌庫").count() == 1
        page.get_by_text("music/youtube-imports", exact=False).wait_for(timeout=10_000)
        settings_sections = page.locator(".sy-settings-section")
        assert settings_sections.count() == 3
        section_border_colours = settings_sections.evaluate_all(
            "elements => elements.map(element => getComputedStyle(element).borderTopColor)"
        )
        assert len(set(section_border_colours)) == 1
        section_icon_colours = page.locator(".sy-settings-section-icon").evaluate_all(
            "elements => elements.map(element => getComputedStyle(element).color)"
        )
        assert len(section_icon_colours) == 3 and len(set(section_icon_colours)) == 1
        assert page.locator(".sy-inline-empty").count() >= (2 if YOUTUBE_ENABLED else 1)
        page.get_by_text("備份還原", exact=True).wait_for(timeout=10_000)
        page.get_by_test_id("create-verified-backup-action").wait_for(timeout=10_000)
        assert page.get_by_text("尚未有可使用的已驗證快照", exact=True).count() == 2
        assert page.get_by_test_id("handover-package-disabled-no-backup").is_disabled()
        assert page.get_by_test_id("restore-disabled-no-backup").is_disabled()
        assert page.get_by_test_id("handover-package-ready-action").count() == 0
        assert page.get_by_test_id("restore-ready-action").count() == 0
        page.screenshot(path=str(SETTINGS_LIGHT_SCREENSHOT), full_page=True)
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
            page.goto(f"{BASE_URL}/rosters", wait_until="domcontentloaded")
            page.locator("button").filter(
                has=page.locator("i.q-icon", has_text="auto_awesome")
            ).click()
            page.locator(".sy-progress-dialog").wait_for(timeout=10_000)
            assert page.locator(".sy-progress-dialog-title").count() == 1
            assert page.locator(".sy-progress-dialog .q-linear-progress").count() == 1
            page.wait_for_timeout(90)
            page.screenshot(path=str(PROGRESS_SCREENSHOT), full_page=False)
            page.wait_for_url("**/rosters/*", timeout=10_000)
        page.goto(f"{BASE_URL}/prefects", wait_until="domcontentloaded")
        page.get_by_role("button", name="新增風紀", exact=True).click()
        page.get_by_text("備註（選填）", exact=True).last.wait_for(timeout=10_000)
        page.get_by_role("button", name="取消", exact=True).last.click()
        page.get_by_text("備註（選填）", exact=True).last.wait_for(state="hidden", timeout=10_000)
        static_table = page.locator(".sy-table").first
        assert static_table.evaluate("element => getComputedStyle(element).cursor") != "pointer"
        assert static_table.evaluate("element => getComputedStyle(element).transform") == "none"
        page.get_by_text("資料匯入", exact=True).click()
        page.get_by_role("button", name="下載名單 CSV 格式範例").wait_for(timeout=10_000)
        page.get_by_text("上載 CSV／XLSX 或貼上 JSON／CSV", exact=False).wait_for(timeout=10_000)
        assert page.get_by_test_id("prefect-file-upload").count() == 1
        page.get_by_test_id("prefect-file-upload").locator('input[type="file"]').set_input_files(
            {
                "name": "fictional-prefects.csv",
                "mimeType": "text/csv",
                "buffer": "姓名,級別,班別,職務,可值班日\n測試檔案風紀,F.3,3H,導學風紀,星期一、星期三".encode("utf-8"),
            }
        )
        page.get_by_text("已讀取 1 筆資料、5 個欄位。", exact=True).wait_for(timeout=10_000)
        assert page.get_by_test_id("deepseek-column-mapping").is_disabled()
        assert page.get_by_test_id("import-prefect-file").is_disabled()
        page.get_by_test_id("preview-prefect-file").click()
        page.get_by_text("資料已通過驗證，可安全匯入。", exact=True).first.wait_for(timeout=10_000)
        assert page.get_by_test_id("import-prefect-file").is_enabled()
        page.get_by_test_id("prefect-file-upload").locator('input[type="file"]').set_input_files(
            {
                "name": "invalid-formula-prefects.xlsx",
                "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "buffer": invalid_formula_workbook_bytes(),
            }
        )
        page.get_by_test_id("import-prefect-file").wait_for(state="detached", timeout=10_000)
        page.locator(".q-notification").last.wait_for(timeout=10_000)
        assert page.get_by_test_id("prefect-file-mapping").locator(".q-select").count() == 0
        assert page.get_by_test_id("prefect-file-preview").get_by_text(
            "資料已通過驗證，可安全匯入。",
            exact=True,
        ).count() == 0
        pasted_input = page.get_by_test_id("paste-prefect-import-input")
        pasted_import = page.get_by_test_id("import-pasted-prefects")
        assert pasted_import.is_disabled()
        reviewed_text = "姓名,級別,班別,職務,可值班日\n測試風紀,F.3,3H,導學風紀,星期一、星期三"
        pasted_input.fill(reviewed_text)
        page.get_by_test_id("preview-pasted-prefects").click()
        page.get_by_text("資料已通過驗證，可安全匯入。", exact=True).first.wait_for(timeout=10_000)
        page.wait_for_function(
            "document.querySelector('[data-testid=\"import-pasted-prefects\"]')?.matches(':disabled') === false"
        )
        pasted_input.fill(reviewed_text.replace("測試風紀", "已修改風紀"))
        page.wait_for_function(
            "document.querySelector('[data-testid=\"import-pasted-prefects\"]')?.matches(':disabled') === true"
        )
        page.get_by_text("資料已通過驗證，可安全匯入。", exact=True).wait_for(
            state="detached",
            timeout=10_000,
        )
        pasted_input.fill(reviewed_text)
        page.get_by_test_id("preview-pasted-prefects").click()
        page.get_by_text("資料已通過驗證，可安全匯入。", exact=True).first.wait_for(timeout=10_000)
        page.wait_for_function(
            "document.querySelector('[data-testid=\"import-pasted-prefects\"]')?.matches(':disabled') === false"
        )
        page.screenshot(path=str(PREFECT_IMPORT_SCREENSHOT), full_page=True)

        fictional_csv, fictional_count = fictional_directory_csv_bytes()
        page.get_by_test_id("prefect-file-upload").locator('input[type="file"]').set_input_files(
            {
                "name": "fictional-release-directory.csv",
                "mimeType": "text/csv",
                "buffer": fictional_csv,
            }
        )
        page.get_by_text(f"已讀取 {fictional_count} 筆資料、5 個欄位。", exact=True).wait_for(timeout=10_000)
        page.get_by_test_id("preview-prefect-file").click()
        page.get_by_text("資料已通過驗證，可安全匯入。", exact=True).first.wait_for(timeout=10_000)
        page.get_by_test_id("import-prefect-file").click()
        page.get_by_text("名單管理", exact=True).wait_for(timeout=15_000)
        page.get_by_text("助理首席導學風紀", exact=True).first.wait_for(timeout=10_000)
        page.get_by_text("導學風紀", exact=True).first.wait_for(timeout=10_000)
        # Archiving is consequential; verify the recovery copy and cancel before invoking it.
        page.get_by_test_id("open-archive-prefect").click()
        page.get_by_text("確認停用這位風紀？", exact=True).wait_for(timeout=10_000)
        page.get_by_text("歷史週表、公平帳本及審計紀錄會完整保留", exact=False).wait_for(timeout=10_000)
        page.get_by_text("此介面沒有即時復原按鈕", exact=False).wait_for(timeout=10_000)
        page.get_by_role("button", name="取消", exact=True).last.click()
        page.get_by_text("確認停用這位風紀？", exact=True).wait_for(state="hidden", timeout=10_000)

        page.goto(f"{BASE_URL}/rosters", wait_until="domcontentloaded")
        page.get_by_text("生成前請假", exact=True).wait_for(timeout=10_000)
        page.get_by_text("請假原因（選填）", exact=True).wait_for(timeout=10_000)
        assert page.locator(".sy-operation-hint").count() >= 1
        page.get_by_text("用途：生成尚未發布的本週草稿。", exact=False).wait_for(timeout=10_000)
        page.locator(".sy-storage-lifecycle").wait_for(timeout=10_000)
        page.get_by_text("公平帳本說明", exact=True).click()
        page.get_by_text("草稿：已儲存，未入帳", exact=True).wait_for(timeout=10_000)
        page.get_by_text("本週崗位與空缺預覽", exact=True).click()
        page.get_by_text("尚待生成", exact=True).first.wait_for(timeout=10_000)
        page.screenshot(path=str(ROSTER_SCREENSHOT), full_page=True)
        slider = page.get_by_test_id("history-priority-multiplier")
        slider.wait_for(timeout=10_000)
        track_box = slider.locator(".q-slider__track").bounding_box()
        assert track_box is not None
        for value in (0.8, 1.0, 2.0):
            tick = page.locator(f'.sy-history-scale-mark[data-value="{value:.1f}"] .sy-history-scale-tick')
            tick_box = tick.bounding_box()
            assert tick_box is not None
            expected_x = track_box["x"] + track_box["width"] * ((value - 0.8) / (2.0 - 0.8))
            actual_x = tick_box["x"] + tick_box["width"] / 2
            assert abs(actual_x - expected_x) <= 1.0, (value, actual_x, expected_x)
        assert "1.0 為標準" in page.locator(".sy-history-scale-help").inner_text()
        leave_reason_label = page.locator(
            '.q-field:has([name="pre-generation-leave-reason"]) .q-field__label'
        )
        assert "選填" in leave_reason_label.inner_text()
        page.get_by_text("調整與編輯", exact=True).click()
        page.get_by_text("請假調整", exact=True).wait_for(timeout=10_000)

        page.goto(f"{BASE_URL}/prefects", wait_until="domcontentloaded")
        page.get_by_text("公平審核", exact=True).click()
        page.get_by_text("服務與公平總結報告", exact=True).wait_for(timeout=10_000)
        page.get_by_text("唯讀・不會重複入帳", exact=True).wait_for(timeout=10_000)
        assert page.get_by_test_id("summary-report-metrics").count() == 1
        assert page.get_by_test_id("summary-contribution-table").count() == 1
        assert page.get_by_test_id("download-summary-zh").count() == 1
        assert page.get_by_test_id("download-summary-en").count() == 1
        assert page.get_by_test_id("download-summary-json").count() == 1
        page.screenshot(path=str(FAIRNESS_REPORT_SCREENSHOT), full_page=True)
        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.screenshot(path=str(LIGHT_SCREENSHOT), full_page=True)
        language_button = page.get_by_role("button", name="EN")
        language_button.click()
        page.wait_for_load_state("domcontentloaded")
        page.get_by_text("Dashboard", exact=True).first.wait_for(timeout=10_000)
        page.goto(f"{BASE_URL}/rosters/999999", wait_until="domcontentloaded")
        page.get_by_text("This roster is no longer available", exact=True).wait_for(timeout=10_000)
        assert page.get_by_role("button", name="Review current rosters").count() == 1
        assert page.get_by_role("button", name="Check backup and restore").count() == 1
        page.goto(f"{BASE_URL}/handover", wait_until="domcontentloaded")
        page.get_by_text("Handover guide", exact=True).first.wait_for(timeout=10_000)
        page.get_by_text("Head Study Prefect and teacher-advisor sign-off still required", exact=True).wait_for(timeout=10_000)
        page.goto(BASE_URL, wait_until="domcontentloaded")
        desktop_theme_controls = page.locator(".sy-desktop-header-controls")
        if desktop_theme_controls.locator("i.q-icon", has_text="light_mode").count():
            desktop_theme_controls.locator("i.q-icon", has_text="light_mode").click()
            page.wait_for_load_state("domcontentloaded")
        page.locator(".sy-desktop-header-controls").locator("i.q-icon", has_text="dark_mode").click()
        page.wait_for_function("document.body.classList.contains('body--dark')")
        # Theme variables update immediately while the restrained state/layer
        # transitions can still be settling. Measure the stable rendered state,
        # not an arbitrary frame inside the 260 ms design-system transition.
        page.wait_for_timeout(320)
        assert "body--dark" in (page.locator("body").get_attribute("class") or "")
        assert page.locator(".sy-flow-step--active .q-btn.bg-primary").evaluate(
            "element => getComputedStyle(element).backgroundColor"
        ) == "rgb(71, 117, 139)"
        dark_active_navigation = page.locator(".sy-sidebar .sy-nav-active")
        dark_active_navigation_contrast = element_contrast_ratio(dark_active_navigation)
        dark_active_navigation_colours = dark_active_navigation.evaluate(
            "element => ({foreground: getComputedStyle(element).color, "
            "background: getComputedStyle(element).backgroundColor})"
        )
        assert dark_active_navigation_contrast >= 4.5, (
            f"dark active navigation contrast was {dark_active_navigation_contrast:.2f}:1 "
            f"for {dark_active_navigation_colours}"
        )
        assert "devotional-sacred-dark-v1.webp" in page.locator(".sy-daily-start").evaluate("element => getComputedStyle(element, '::after').backgroundImage")
        assert "weekly-pulse-dark-v1.webp" in page.locator(".sy-workbench").evaluate("element => getComputedStyle(element, '::after').backgroundImage")
        assert "paper-fibre-dark-v1.svg" in page.locator(".sy-main").evaluate(
            "element => getComputedStyle(element).backgroundImage"
        )
        assert "paper-fibre-dark-v1.svg" in page.locator(".sy-workbench").evaluate(
            "element => getComputedStyle(element).backgroundImage"
        )
        assert "linen-weave-dark-v1.svg" in page.locator(".sy-sidebar").evaluate(
            "element => getComputedStyle(element, '::after').backgroundImage"
        )
        assert page.get_by_test_id("dashboard-history").evaluate(
            "element => getComputedStyle(element).backgroundImage"
        ) == "none"
        assert page.locator(".sy-flow-step--active .sy-tone-action").evaluate(
            "element => getComputedStyle(element).color"
        ) == "rgb(155, 194, 210)"
        assert page.locator(".sy-workbench .sy-tone-action").first.evaluate(
            "element => getComputedStyle(element).color"
        ) == "rgb(155, 194, 210)"
        assert_status_tone_contrast(page)
        assert float(page.locator(".sy-workbench").evaluate("element => getComputedStyle(element, '::after').opacity")) >= 0.7
        page.get_by_test_id("page-music-button").click()
        dark_music_dialog = page.get_by_test_id("page-music-dialog")
        dark_music_dialog.wait_for(timeout=10_000)
        assert dark_music_dialog.locator('[name="music-profile"]').count() == 1
        dark_music_dialog.get_by_text("Quiet reflection", exact=False).first.wait_for(timeout=10_000)
        assert dark_music_dialog.locator("audio.sy-page-music-audio").evaluate("element => getComputedStyle(element).colorScheme") == "dark"
        close_music_dialog(dark_music_dialog)
        assert_component_grammar(page, COMPONENT_DARK_SCREENSHOT)
        page.screenshot(path=str(DARK_SCREENSHOT), full_page=True)
        assert page.locator(".sy-daily-start-verse").evaluate("element => getComputedStyle(element).color") != "rgb(0, 0, 0)"
        page.goto(f"{BASE_URL}/devotional", wait_until="domcontentloaded")
        page.locator(".sy-devotional-page").wait_for(timeout=10_000)
        page.wait_for_timeout(450)
        assert "devotional-sacred-dark-v1.webp" in page.locator(".sy-chapel").evaluate(
            "element => getComputedStyle(element, '::after').backgroundImage"
        )
        assert page.locator(".sy-devotional-reading-grid .sy-devotional-companion").count() == 3
        page.screenshot(path=str(DEVOTIONAL_DARK_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/prefects", wait_until="domcontentloaded")
        page.get_by_text("Data import", exact=True).click()
        page.get_by_text("Upload CSV/XLSX or paste JSON/CSV", exact=False).wait_for(timeout=10_000)
        assert page.locator("body.body--dark").count() == 1
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth") is True
        page.screenshot(path=str(PREFECT_IMPORT_DARK_SCREENSHOT), full_page=True)
        page.get_by_text("Fairness audit", exact=True).click()
        page.get_by_text("Service & fairness summary report", exact=True).wait_for(timeout=10_000)
        assert page.get_by_test_id("summary-report-metrics").count() == 1
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth") is True
        page.screenshot(path=str(FAIRNESS_REPORT_DARK_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/settings", wait_until="domcontentloaded")
        page.get_by_test_id("online-music-settings").wait_for(timeout=10_000)
        page.screenshot(path=str(SETTINGS_DARK_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/handover", wait_until="domcontentloaded")
        assert "handover-archive-dark-v1.webp" in page.locator(".sy-handover-hero").evaluate("element => getComputedStyle(element, '::after').backgroundImage")
        page.screenshot(path=str(HANDOVER_DARK_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/getting-started", wait_until="domcontentloaded")
        assert "onboarding-desk-dark-v1.webp" in page.locator(".sy-onboarding-intro").evaluate("element => getComputedStyle(element, '::after').backgroundImage")
        page.goto(f"{BASE_URL}/platform", wait_until="domcontentloaded")
        assert "platform-stewardship-dark-v1.webp" in page.locator(".sy-platform-hero").evaluate(
            "element => getComputedStyle(element, '::before').backgroundImage"
        )
        dark_creator_profile = page.get_by_test_id("co-creation-profile")
        dark_creator_profile.scroll_into_view_if_needed()
        dark_creator_banner_image = dark_creator_profile.locator(".sy-co-creation-banner img")
        dark_creator_avatar_image = dark_creator_profile.locator(".sy-co-creation-avatar img")
        page.wait_for_function(
            "element => element.complete && element.naturalWidth > 0",
            arg=dark_creator_banner_image.element_handle(),
        )
        page.wait_for_function(
            "element => element.complete && element.naturalWidth > 0",
            arg=dark_creator_avatar_image.element_handle(),
        )
        assert dark_creator_banner_image.evaluate(
            "element => element.complete && element.naturalWidth"
        ) == 1536
        assert dark_creator_avatar_image.evaluate(
            "element => element.complete && element.naturalWidth"
        ) == 1024
        assert element_contrast_ratio(dark_creator_profile.locator(".sy-co-creation-name")) >= 4.5
        assert element_contrast_ratio(dark_creator_profile.locator(".sy-co-creation-social")) >= 4.5
        page.screenshot(path=str(PLATFORM_DARK_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/engineering", wait_until="domcontentloaded")
        assert page.locator("body.body--dark").count() == 1
        assert "engineering-workbench-dark-v1.webp" in page.locator(".sy-engineering-hero").evaluate(
            "element => getComputedStyle(element, '::after').backgroundImage"
        )
        assert page.get_by_test_id("engineering-gates").locator(".sy-engineering-gate").count() == 13
        page.screenshot(path=str(ENGINEERING_DARK_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/system-architecture", wait_until="domcontentloaded")
        assert "architecture-stewardship-dark-v1.webp" in page.locator(".sy-architecture-hero").evaluate("element => getComputedStyle(element, '::before').backgroundImage")
        assert "architecture-lifeline-dark-v1.webp" in page.get_by_test_id("architecture-lifeline-visual").evaluate(
            "element => getComputedStyle(element).backgroundImage"
        )
        assert "sidebar-stewardship-dark-v1.webp" in page.locator(".sy-sidebar").evaluate("element => getComputedStyle(element).backgroundImage")
        page.screenshot(path=str(ARCHITECTURE_DARK_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/guide", wait_until="domcontentloaded")
        assert "guide-handbook-dark-v1.webp" in page.locator(".sy-guide-hero").evaluate(
            "element => getComputedStyle(element, '::after').backgroundImage"
        )
        page.screenshot(path=str(GUIDE_DARK_SCREENSHOT), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(f"{BASE_URL}/platform", wait_until="domcontentloaded")
        page.get_by_text("A co-creation note", exact=True).wait_for(timeout=10_000)
        page.get_by_role(
            "heading", name="Study Prefect Team: an organisation built around service", exact=True
        ).wait_for(timeout=10_000)
        assert page.locator(".sy-platform-metric").count() == 4
        assert page.locator(".sy-team-role").count() == 4
        assert page.locator(".sy-capability-card").count() == 4
        assert page.locator(".sy-solution-card").count() == 4
        first_solution_box = page.locator(".sy-solution-card").first.bounding_box()
        second_solution_box = page.locator(".sy-solution-card").nth(1).bounding_box()
        assert first_solution_box is not None and second_solution_box is not None
        assert first_solution_box["y"] < second_solution_box["y"], "Solution cards should stack on a phone"
        mobile_creator_profile = page.get_by_test_id("co-creation-profile")
        mobile_creator_profile.scroll_into_view_if_needed()
        mobile_creator_box = mobile_creator_profile.bounding_box()
        mobile_creator_social_box = mobile_creator_profile.locator(".sy-co-creation-social").bounding_box()
        assert mobile_creator_box is not None and mobile_creator_box["width"] <= 390
        assert mobile_creator_social_box is not None and mobile_creator_social_box["height"] >= 44
        assert mobile_creator_profile.locator(".sy-co-creation-crest").is_hidden()
        assert mobile_creator_profile.locator(".sy-co-creation-banner img").evaluate(
            "element => element.complete && element.naturalWidth"
        ) == 1536
        assert mobile_creator_profile.locator(".sy-co-creation-avatar img").evaluate(
            "element => element.complete && element.naturalWidth"
        ) == 1024
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth") is True
        page.screenshot(path=str(PLATFORM_MOBILE_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/engineering", wait_until="domcontentloaded")
        page.get_by_text("Engineering & quality", exact=True).first.wait_for(timeout=10_000)
        first_engineering_fact = page.locator(".sy-engineering-fact").nth(0).bounding_box()
        second_engineering_fact = page.locator(".sy-engineering-fact").nth(1).bounding_box()
        assert first_engineering_fact is not None and second_engineering_fact is not None
        assert first_engineering_fact["y"] < second_engineering_fact["y"]
        first_blueprint_layer = page.locator(".sy-engineering-blueprint-layer").nth(0).bounding_box()
        second_blueprint_layer = page.locator(".sy-engineering-blueprint-layer").nth(1).bounding_box()
        assert first_blueprint_layer is not None and second_blueprint_layer is not None
        assert first_blueprint_layer["y"] < second_blueprint_layer["y"]
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth") is True
        page.screenshot(path=str(ENGINEERING_MOBILE_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/guide", wait_until="domcontentloaded")
        page.get_by_text("Operator guide", exact=True).first.wait_for(timeout=10_000)
        assert page.get_by_test_id("reference-toc").locator(".sy-reference-toc-link").count() == 4
        assert page.get_by_test_id("reference-pager").locator(".sy-reference-pager-link").count() == 2
        troubleshooting_head = page.get_by_test_id("guide-troubleshooting").locator(".sy-troubleshooting-head")
        head_style = troubleshooting_head.evaluate(
            "element => { const style = getComputedStyle(element); return {position: style.position, width: style.width, height: style.height, overflow: style.overflow, clipPath: style.clipPath}; }"
        )
        assert head_style["position"] == "absolute", head_style
        assert float(head_style["width"].removesuffix("px")) <= 1, head_style
        assert float(head_style["height"].removesuffix("px")) <= 1, head_style
        assert head_style["overflow"] in {"hidden", "clip"}, head_style
        assert head_style["clipPath"] not in {"none", "auto"}, head_style
        assert troubleshooting_head.locator('[role="columnheader"]').count() == 3
        first_issue = page.get_by_test_id("guide-troubleshooting").locator(".sy-troubleshooting-row").nth(1)
        assert first_issue.evaluate("element => getComputedStyle(element).gridTemplateColumns").count(" ") == 0
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth") is True
        page.screenshot(path=str(GUIDE_MOBILE_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/prefects", wait_until="domcontentloaded")
        page.get_by_text("Data import", exact=True).click()
        page.get_by_text("Upload CSV/XLSX or paste JSON/CSV", exact=False).wait_for(timeout=10_000)
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth") is True
        page.get_by_text("Fairness audit", exact=True).click()
        page.get_by_text("Service & fairness summary report", exact=True).wait_for(timeout=10_000)
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth") is True
        page.screenshot(path=str(PREFECT_REPORT_MOBILE_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/settings", wait_until="domcontentloaded")
        page.get_by_role("button", name="Download to local library").wait_for(timeout=10_000)
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth") is True
        page.screenshot(path=str(SETTINGS_MOBILE_SCREENSHOT), full_page=True)
        page.goto(f"{BASE_URL}/system-architecture", wait_until="domcontentloaded")
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
        page.goto(f"{BASE_URL}/handover", wait_until="domcontentloaded")
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
        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.get_by_text("This week's roster desk", exact=True).wait_for(timeout=10_000)
        mobile_primary_actions = page.locator(".sy-mobile-next-action .q-btn.bg-primary")
        assert mobile_primary_actions.count() == 1
        mobile_primary_box = mobile_primary_actions.bounding_box()
        assert mobile_primary_box is not None and mobile_primary_box["y"] + mobile_primary_box["height"] <= 844, mobile_primary_box
        assert page.locator(".sy-flow-step--active .sy-flow-action").is_hidden()
        mobile_workbench_box = page.locator(".sy-workbench").bounding_box()
        mobile_history_box = page.get_by_test_id("dashboard-history").bounding_box()
        assert mobile_workbench_box is not None and mobile_history_box is not None
        assert mobile_history_box["y"] >= mobile_workbench_box["y"] + mobile_workbench_box["height"]
        assert page.locator(".sy-empty-state--illustrated").count() == 0
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
        assert page.locator(".sy-workbench .sy-flow").is_hidden(), "The compact next action should replace duplicate mobile flow cards"
        page.screenshot(path=str(MOBILE_SCREENSHOT), full_page=True)
        for narrow_width in (360, 320):
            page.set_viewport_size({"width": narrow_width, "height": 780})
            page.goto(BASE_URL, wait_until="domcontentloaded")
            assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth") is True
            assert page.locator(".sy-mobile-next-action .q-btn.bg-primary").count() == 1
            header_tools_box = page.locator(".sy-header-tools").bounding_box()
            assert header_tools_box is not None
            assert header_tools_box["x"] + header_tools_box["width"] <= narrow_width, header_tools_box
            if narrow_width == 320:
                page.goto(f"{BASE_URL}/platform", wait_until="domcontentloaded")
                narrow_profile = page.get_by_test_id("co-creation-profile")
                narrow_profile.scroll_into_view_if_needed()
                narrow_social_box = narrow_profile.locator(".sy-co-creation-social").bounding_box()
                assert narrow_social_box is not None and narrow_social_box["height"] >= 44
                assert narrow_social_box["x"] + narrow_social_box["width"] <= narrow_width
                assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth") is True
        component_dark_context = browser.new_context(
            viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, color_scheme="dark"
        )
        component_dark_page = component_dark_context.new_page()
        component_dark_page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        component_dark_page.on("pageerror", lambda error: page_errors.append(str(error)))
        component_dark_page.goto(BASE_URL, wait_until="domcontentloaded")
        ensure_rendered_theme(component_dark_page, "dark")
        assert_component_grammar(component_dark_page, COMPONENT_MOBILE_DARK_SCREENSHOT)
        component_dark_context.close()

        component_light_context = browser.new_context(
            viewport={"width": 320, "height": 780}, has_touch=True, is_mobile=True, color_scheme="light"
        )
        component_light_page = component_light_context.new_page()
        component_light_page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        component_light_page.on("pageerror", lambda error: page_errors.append(str(error)))
        component_light_page.goto(BASE_URL, wait_until="domcontentloaded")
        ensure_rendered_theme(component_light_page, "light")
        assert_component_grammar(component_light_page, COMPONENT_MOBILE_LIGHT_SCREENSHOT)
        component_light_context.close()
        reduced_context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
        reduced_page = reduced_context.new_page()
        reduced_page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        reduced_page.on("pageerror", lambda error: page_errors.append(str(error)))
        reduced_page.goto(f"{BASE_URL}/system-architecture", wait_until="domcontentloaded")
        reduced_page.wait_for_function("document.documentElement.dataset.syMotion === 'reduced'")
        reduced_layer = reduced_page.locator(".sy-architecture-layer").first
        assert reduced_layer.locator(".sy-pointer-light").count() == 0
        reduced_layer.hover()
        assert reduced_layer.evaluate("element => getComputedStyle(element).transform") == "none"
        reduced_icon = reduced_page.locator(".q-btn .q-icon[data-sy-icon-motion]").first
        reduced_icon.wait_for(timeout=5_000)
        reduced_icon.locator("xpath=ancestor::*[contains(@class,'q-btn')][1]").hover()
        assert reduced_icon.evaluate("element => getComputedStyle(element).transform") == "none"
        assert reduced_page.evaluate("typeof window.__disposeSingYinMotion") == "function"
        reduced_page.evaluate("window.__disposeSingYinMotion()")
        assert reduced_page.evaluate("document.documentElement.dataset.syMotion || null") is None
        reduced_context.close()
        touch_context = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        touch_page = touch_context.new_page()
        touch_page.on("pageerror", lambda error: page_errors.append(str(error)))
        touch_page.goto(f"{BASE_URL}/system-architecture", wait_until="domcontentloaded")
        assert touch_page.evaluate("matchMedia('(hover: hover) and (pointer: fine)').matches") is False
        assert touch_page.locator(".sy-pointer-light").count() == 0
        assert touch_page.evaluate(
            """() => {
                const tooltip = document.createElement('div');
                tooltip.className = 'q-tooltip';
                document.body.appendChild(tooltip);
                const display = getComputedStyle(tooltip).display;
                tooltip.remove();
                return display;
            }"""
        ) == "none"
        touch_context.close()
        assert not console_errors, console_errors
        assert not page_errors, page_errors
        browser.close()
    print(f"UI smoke checks passed; screenshots: {LIGHT_SCREENSHOT}, {DARK_SCREENSHOT}")


if __name__ == "__main__":
    main()
