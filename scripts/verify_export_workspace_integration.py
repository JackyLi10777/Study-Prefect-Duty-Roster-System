"""Bounded export-only browser evidence; not a release, route-matrix or p75 gate.

Checks are extracted from frozen 856d06c's mobile verifier. See the adoption note.
All writes use a newly-created fictional fixture; no school or production path.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import secrets
import sys
import tempfile
import time
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "packages/roster_policy"), str(ROOT / "packages/roster_core")]

from playwright.sync_api import Error, Locator, Page, expect, sync_playwright
from scripts.verify_release_candidate import (
    CANONICAL_DATABASE, CANONICAL_BACKUPS, _free_loopback_port, _source_state,
    _start_server, _stop_server, _wait_until_ready, isolated_environment,
)

BASE_URL = ""
LIFECYCLE_CYCLE_COUNT = 20
RUNTIME_HEAP_GROWTH_BUDGET_BYTES = 10 * 1024 * 1024
RUNTIME_DOM_GROWTH_BUDGET = 100
RUNTIME_LISTENER_GROWTH_BUDGET = 40
PERFORMANCE_EVIDENCE: list[dict[str, Any]] = []
EVIDENCE_METADATA: dict[str, Any] = {}
PERFORMANCE_EVIDENCE_PATH: Path


@dataclass(frozen=True)
class DynamicRosterRouteFixture:
    draft_id: int
    published_id: int
    historical_id: int


def _write_performance_evidence() -> None:
    PERFORMANCE_EVIDENCE_PATH.write_text(json.dumps({
        **EVIDENCE_METADATA, "samples": PERFORMANCE_EVIDENCE,
    }, indent=2), encoding="utf-8")


def isolated_paths() -> tuple[Path, Path, Path]:
    """Fail closed unless every durable location belongs to an E2E run."""
    if os.getenv("SING_YIN_E2E_ISOLATED") != "1":
        raise RuntimeError("Set SING_YIN_E2E_ISOLATED=1 before mobile browser verification.")
    run_id = os.getenv("SING_YIN_E2E_RUN_ID", "").strip()
    if not re.fullmatch(r"E2E-[A-F0-9]{12}", run_id):
        raise RuntimeError("Set a unique, valid SING_YIN_E2E_RUN_ID before mobile browser verification.")
    required = ("SING_YIN_DATABASE_PATH", "SING_YIN_BACKUP_DIR", "SING_YIN_LOG_DIR")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing isolated path configuration: {', '.join(missing)}")

    database_path = Path(os.environ["SING_YIN_DATABASE_PATH"]).resolve()
    backup_dir = Path(os.environ["SING_YIN_BACKUP_DIR"]).resolve()
    log_dir = Path(os.environ["SING_YIN_LOG_DIR"]).resolve()
    if database_path == CANONICAL_DATABASE or backup_dir == CANONICAL_BACKUPS:
        raise RuntimeError("Mobile verification must not use the canonical school database or backup directory.")

    endpoint = urlsplit(BASE_URL)
    if endpoint.scheme != "http" or endpoint.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("Mobile verification requires an isolated loopback HTTP endpoint.")
    return database_path, backup_dir, log_dir


def _next_unused_monday(weeks: Sequence[Mapping[str, Any]]) -> date:
    """Choose a deterministic fixture week without colliding with retained history."""

    occupied: set[date] = set()
    for week in weeks:
        raw_start = week.get("weekStart")
        try:
            occupied.add(
                raw_start if isinstance(raw_start, date) else date.fromisoformat(str(raw_start))
            )
        except (TypeError, ValueError) as error:
            raise AssertionError(f"Mobile route fixture found an invalid weekStart: {raw_start!r}.") from error
    candidate = max(occupied, default=date(2026, 9, 7)) + timedelta(days=7)
    while candidate in occupied:
        candidate += timedelta(days=7)
    if candidate.weekday() != 0:
        raise AssertionError(f"Mobile route fixture did not resolve a Monday: {candidate!s}.")
    return candidate


def _ensure_dynamic_roster_route_fixtures(
    database_path: Path,
    backup_dir: Path,
) -> DynamicRosterRouteFixture:
    """Create only missing draft/published states inside the disposable E2E database.

    The release runner executes this verifier after the write-pipeline browser
    scenario, so retained withdrawn history is reused.  Draft and published
    states are added through the real workflow only when absent; production
    paths remain protected by :func:`isolated_paths` before this function runs.
    """

    isolated_database, isolated_backups, _ = isolated_paths()
    if database_path.resolve() != isolated_database or backup_dir.resolve() != isolated_backups:
        raise RuntimeError("Mobile route fixtures require the exact verified isolated storage paths.")

    from nicegui_app.config import PREFECT_SEED_PATH
    from nicegui_app.services.roster_workflow import PrefectInput, RosterWorkflow
    from roster_core import parse_prefect_role

    workflow = RosterWorkflow(
        database_path=database_path,
        backup_dir=backup_dir,
        seed_path=None,
    )
    workflow.bootstrap()
    weeks = list(workflow.roster_weeks())
    by_status = {
        status: next((week for week in weeks if week.get("status") == status), None)
        for status in ("draft", "published", "withdrawn")
    }

    if by_status["draft"] is None or by_status["published"] is None:
        raw_seed = json.loads(PREFECT_SEED_PATH.read_text(encoding="utf-8"))
        raw_prefects = raw_seed.get("prefects")
        if not isinstance(raw_prefects, list) or not raw_prefects:
            raise AssertionError("Mobile route fixture seed does not contain fictional prefects.")
        active_names = {str(item["nameZh"]) for item in workflow.prefects()}
        missing_inputs: list[PrefectInput] = []
        for raw in raw_prefects:
            if not isinstance(raw, Mapping):
                raise AssertionError("Mobile route fixture seed contains a malformed prefect row.")
            name_zh = str(raw.get("name", "")).strip()
            if not name_zh or name_zh in active_names:
                continue
            missing_inputs.append(
                PrefectInput(
                    name_zh=name_zh,
                    name_en=str(raw["nameEn"]).strip() if raw.get("nameEn") else None,
                    form=str(raw.get("form", "")),
                    class_name=str(raw.get("class", "")),
                    role_code=parse_prefect_role(raw.get("roleCode", raw.get("role"))).value,
                    available_days=tuple(str(day) for day in raw.get("availableDays", ())),
                    needs_mentoring=bool(raw.get("needsMentoring", False)),
                    fixed_general_duty=str(raw.get("fixedGeneralDuty", "NONE")),
                    remarks=str(raw.get("remarks", "")),
                    history_weight=float(raw.get("historyWeight", 0)),
                    history_duties=int(raw.get("historyDuties", 0)),
                )
            )
        if missing_inputs:
            workflow.import_prefects(
                missing_inputs,
                command_id=f"mobile-route-fixture-prefects:{os.environ['SING_YIN_E2E_RUN_ID']}",
            )

    weeks = list(workflow.roster_weeks())
    draft = next((week for week in weeks if week.get("status") == "draft"), None)
    if draft is None:
        draft_result = workflow.generate_and_save_draft(
            _next_unused_monday(weeks),
            command_id=f"mobile-route-fixture-draft:{os.environ['SING_YIN_E2E_RUN_ID']}",
        )
        draft = workflow.roster_week(draft_result.id)
        weeks = list(workflow.roster_weeks())

    published = next((week for week in weeks if week.get("status") == "published"), None)
    if published is None:
        publish_draft = workflow.generate_and_save_draft(
            _next_unused_monday(weeks),
            command_id=f"mobile-route-fixture-publish-draft:{os.environ['SING_YIN_E2E_RUN_ID']}",
        )
        workflow.publish(
            publish_draft.id,
            expected_week_version=publish_draft.version,
            command_id=f"mobile-route-fixture-publish:{os.environ['SING_YIN_E2E_RUN_ID']}",
        )
        published = workflow.roster_week(publish_draft.id)
        weeks = list(workflow.roster_weeks())

    historical = next((week for week in weeks if week.get("status") == "withdrawn"), published)
    if draft is None or published is None or historical is None:
        raise AssertionError("Mobile route fixture could not establish draft, published, and history states.")
    if draft.get("status") != "draft" or published.get("status") != "published":
        raise AssertionError(
            f"Mobile route fixture states drifted: draft={draft.get('status')!r}, "
            f"published={published.get('status')!r}."
        )
    return DynamicRosterRouteFixture(
        draft_id=int(draft["id"]),
        published_id=int(published["id"]),
        historical_id=int(historical["id"]),
    )


def _capture_runtime_footprint(page: Page, session: Any, *, label: str) -> dict[str, float]:
    """Read GC-stabilized heap, DOM-node, and JS-listener counts through CDP."""

    page.wait_for_timeout(250)
    try:
        session.send("HeapProfiler.collectGarbage")
        page.wait_for_timeout(100)
        heap = session.send("Runtime.getHeapUsage")
        dom = session.send("Memory.getDOMCounters")
    except Error as error:
        raise AssertionError(f"{label} could not collect the required runtime footprint.") from error

    raw_values = {
        "heapBytes": heap.get("usedSize") if isinstance(heap, Mapping) else None,
        "domNodes": dom.get("nodes") if isinstance(dom, Mapping) else None,
        "listeners": dom.get("jsEventListeners") if isinstance(dom, Mapping) else None,
    }
    footprint: dict[str, float] = {}
    for metric, value in raw_values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise AssertionError(f"{label} did not produce a valid {metric}: {value!r}.")
        footprint[metric] = float(value)
    return footprint


def _assert_runtime_growth_budget(
    baseline: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    label: str,
    cycles: int,
    persist_evidence: bool = False,
) -> dict[str, Any]:
    """Fail closed when a repeated UI lifecycle exceeds any release budget."""

    if cycles != LIFECYCLE_CYCLE_COUNT:
        raise AssertionError(
            f"{label} must execute exactly {LIFECYCLE_CYCLE_COUNT} lifecycle cycles; received {cycles}."
        )
    budgets = {
        "heapBytes": RUNTIME_HEAP_GROWTH_BUDGET_BYTES,
        "domNodes": RUNTIME_DOM_GROWTH_BUDGET,
        "listeners": RUNTIME_LISTENER_GROWTH_BUDGET,
    }
    growth: dict[str, float] = {}
    failures: list[str] = []
    for metric, limit in budgets.items():
        before_value = baseline.get(metric)
        after_value = after.get(metric)
        for phase, value in (("baseline", before_value), ("after", after_value)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                raise AssertionError(
                    f"{label} {phase} did not produce a valid {metric}: {value!r}."
                )
        growth[metric] = float(after_value) - float(before_value)
        if growth[metric] > limit:
            failures.append(
                f"{metric} growth budget exceeded (growth={growth[metric]}, limit={limit})"
            )
    summary = {
        "label": label,
        "kind": "runtime-growth",
        "cycles": cycles,
        "baseline": dict(baseline),
        "after": dict(after),
        "growth": growth,
        "budgets": budgets,
    }
    PERFORMANCE_EVIDENCE.append(summary)
    if persist_evidence:
        _write_performance_evidence()
    if failures:
        raise AssertionError(
            f"{label} exceeds runtime growth budgets after {cycles} cycles: "
            + "; ".join(failures)
        )
    return summary


def _install_png_share_counter(page: Page) -> None:
    """Install a local native-share sink which exposes duplicate click handlers."""

    page.evaluate(
        """() => {
          window.__syPngShareCalls = 0;
          Object.defineProperty(navigator, 'canShare', {
            configurable: true,
            value: payload => Boolean(payload?.files?.length === 1),
          });
          Object.defineProperty(navigator, 'share', {
            configurable: true,
            value: async payload => {
              const files = payload?.files || [];
              if (files.length !== 1 || files[0].type !== 'image/png') {
                throw new Error('Expected exactly one image/png file.');
              }
              const signature = Array.from(new Uint8Array(await files[0].arrayBuffer()).slice(0, 8));
              if (signature.join(',') !== '137,80,78,71,13,10,26,10') {
                throw new Error('Native-share preview did not receive a PNG.');
              }
              window.__syPngShareCalls += 1;
            },
          });
        }"""
    )


def _assert_export_dialog_png_cleanup_cycles(
    page: Page,
    *,
    published_roster_id: int,
    label: str,
    cycles: int = LIFECYCLE_CYCLE_COUNT,
) -> None:
    """Generate/share repeatedly from a cold page and retain one byte-free native core."""

    response = page.goto(
        f"{BASE_URL}/rosters/{published_roster_id}",
        wait_until="domcontentloaded",
    )
    if response is None or response.status != 200:
        raise AssertionError(f"{label} could not open the published roster detail: {response}")
    page.locator(".sy-roster-mobile-day").first.wait_for(state="visible", timeout=15_000)
    export_trigger = page.get_by_test_id("open-roster-export")
    if export_trigger.count() != 1 or not export_trigger.is_visible():
        raise AssertionError(f"{label} requires one visible export trigger.")
    _install_png_share_counter(page)
    if page.get_by_test_id("roster-export-dialog").count() != 0:
        raise AssertionError(f"{label} mounted its export form before the first operator click.")

    session = page.context.new_cdp_session(page)
    try:
        session.send("HeapProfiler.enable")
        baseline = _capture_runtime_footprint(page, session, label=f"{label} baseline")
        PERFORMANCE_EVIDENCE.append({"kind": "runtime-growth-baseline", "footprint": baseline})
        _write_performance_evidence()
        for cycle in range(cycles):
            export_trigger.click()
            dialog = page.get_by_test_id("roster-export-dialog")
            dialog.wait_for(state="visible", timeout=10_000)
            if dialog.count() != 1:
                raise AssertionError(
                    f"{label} mounted {dialog.count()} export dialogs in cycle {cycle + 1}."
                )
            native_state = dialog.evaluate(
                "element => ({tag: element.tagName, open: element.open, modal: element.matches(':modal')})"
            )
            if native_state != {"tag": "DIALOG", "open": True, "modal": True}:
                raise AssertionError(
                    f"{label} did not open one browser-native modal in cycle {cycle + 1}: {native_state}"
                )
            if cycle == 0:
                page.evaluate(
                    "window.__syPersistentExportDialog = "
                    "document.querySelector('[data-testid=\"roster-export-dialog\"]')"
                )
            elif not dialog.evaluate("element => element === window.__syPersistentExportDialog"):
                raise AssertionError(f"{label} replaced its reusable native core in cycle {cycle + 1}.")
            with page.expect_download(timeout=45_000) as avatar_download:
                dialog.get_by_test_id("prepare-roster-images").click()
            download = avatar_download.value
            if not download.suggested_filename.endswith("_Avatar_ZH.png"):
                raise AssertionError(
                    f"{label} produced an unexpected Avatar filename in cycle {cycle + 1}: "
                    f"{download.suggested_filename!r}."
                )
            download.delete()

            ready = dialog.get_by_test_id("roster-images-ready")
            ready.wait_for(state="visible", timeout=45_000)
            counts = {
                "ready": dialog.get_by_test_id("roster-images-ready").count(),
                "avatar": dialog.get_by_test_id("roster-avatar-preview").count(),
                "detail": dialog.get_by_test_id("roster-whatsapp-preview").count(),
                "share": dialog.get_by_test_id("share-roster-detail").count(),
            }
            if counts != {"ready": 1, "avatar": 1, "detail": 1, "share": 1}:
                raise AssertionError(
                    f"{label} duplicated a dialog, preview, or share handler in cycle {cycle + 1}: {counts}"
                )
            preview_sources = ready.locator('img[src^="data:image/png;base64,"]')
            if preview_sources.count() != 2:
                raise AssertionError(
                    f"{label} did not expose exactly two in-memory PNG previews in cycle {cycle + 1}."
                )

            _prepare_and_confirm_png_share(page, ready)
            page.wait_for_function(
                "expected => window.__syPngShareCalls === expected",
                arg=cycle + 1,
                timeout=10_000,
            )
            dialog.get_by_test_id("close-roster-export").click()
            dialog.wait_for(state="hidden", timeout=10_000)
            retained = page.evaluate(
                """() => ({
                  dialogs: document.querySelectorAll('[data-testid="roster-export-dialog"]').length,
                  sameDialog: document.querySelector('[data-testid="roster-export-dialog"]') ===
                    window.__syPersistentExportDialog,
                  open: document.querySelector('[data-testid="roster-export-dialog"]')?.open,
                  visibleReady: [...document.querySelectorAll('[data-testid="roster-images-ready"]')]
                    .filter(element => element.getClientRects().length > 0).length,
                  pngPreviewSources: document.querySelectorAll(
                    '[data-testid="roster-export-dialog"] img[src^="data:image/png;base64,"]'
                  ).length,
                })"""
            )
            expected_retained = {
                "dialogs": 1,
                "sameDialog": True,
                "open": False,
                "visibleReady": 0,
                "pngPreviewSources": 0,
            }
            if retained != expected_retained:
                raise AssertionError(
                    f"{label} did not return its native dialog to one clean hidden instance after "
                    f"cycle {cycle + 1}: {retained}"
                )
            if cycle in {0, 9, cycles - 1}:
                page.wait_for_function("document.querySelectorAll('.q-notification').length === 0",
                                       timeout=20_000)
                footprint = _capture_runtime_footprint(page, session, label=f"{label} cycle {cycle + 1}")
                PERFORMANCE_EVIDENCE.append({"kind": "runtime-growth-checkpoint", "label": label,
                    "cycle": cycle + 1, "footprint": footprint,
                    "mounted": page.evaluate("""() => ({
                        all: document.querySelectorAll('*').length,
                        dialog: document.querySelector('[data-testid="roster-export-dialog"]')?.querySelectorAll('*').length,
                        dialogNodes: [...document.querySelector('[data-testid="roster-export-dialog"]').querySelectorAll('*')]
                            .map(node => ({tag: node.tagName, id: node.id, class: node.className,
                                testId: node.getAttribute('data-testid')})),
                    })""")})
                _write_performance_evidence()

        page.wait_for_function(
            "document.querySelectorAll('.q-notification').length === 0",
            timeout=20_000,
        )
        if page.evaluate("window.__syPngShareCalls") != cycles:
            raise AssertionError(f"{label} did not invoke exactly one native-share handler per cycle.")
        after = _capture_runtime_footprint(page, session, label=f"{label} after")
        _assert_runtime_growth_budget(
            baseline,
            after,
            label=label,
            cycles=cycles,
            persist_evidence=True,
        )
    finally:
        try:
            session.send("HeapProfiler.disable")
        finally:
            session.detach()


def _prepare_and_confirm_png_share(page: Page, container: Locator) -> None:
    """Verify preparation does not share, then exercise the direct user gesture."""
    before = int(page.evaluate("window.__syPngShareCalls || 0"))
    container.get_by_test_id("share-roster-detail").click()
    confirmation = container.get_by_test_id("confirm-share-roster-detail")
    # Locator.wait_for in Playwright 1.60 retains an undisposed ElementHandle.
    # Assertions observe visibility without rooting each short-lived button.
    expect(confirmation).to_be_visible(timeout=10_000)
    if int(page.evaluate("window.__syPngShareCalls || 0")) != before:
        raise AssertionError("Native sharing ran before confirmation")
    confirmation.click()


def _assert_png_native_share_outcomes_and_download_fallback(
    page: Page,
    *,
    label: str,
) -> None:
    """Exercise cancellation, failure, unsupported sharing, and explicit download fallback."""

    from nicegui_app.ui.i18n import MESSAGES, ZH_HK

    dialog = page.get_by_test_id("roster-export-dialog")
    page.get_by_test_id("open-roster-export").click()
    dialog.wait_for(state="visible", timeout=10_000)
    with page.expect_download(timeout=45_000) as avatar_download:
        dialog.get_by_test_id("prepare-roster-images").click()
    avatar_download.value.delete()
    dialog.get_by_test_id("roster-images-ready").wait_for(state="visible", timeout=45_000)
    previous_successes = int(page.evaluate("window.__syPngShareCalls || 0"))
    _prepare_and_confirm_png_share(page, dialog)
    page.wait_for_function(
        "expected => window.__syPngShareCalls === expected",
        arg=previous_successes + 1,
        timeout=10_000,
    )
    page.get_by_text(MESSAGES["roster_image_share_completed"][ZH_HK], exact=True).last.wait_for(
        state="visible",
        timeout=10_000,
    )

    scenarios = (
        (
            "cancelled",
            "async () => { throw new DOMException('cancelled by user', 'AbortError'); }",
            "roster_image_share_cancelled",
        ),
        (
            "failed",
            "async () => { throw new Error('synthetic share failure'); }",
            "roster_image_share_failed",
        ),
    )
    for outcome, implementation, message_key in scenarios:
        page.evaluate(
            "implementation => Object.defineProperty(navigator, 'share', "
            "{configurable: true, value: (0, eval)(implementation)})",
            implementation,
        )
        _prepare_and_confirm_png_share(page, dialog)
        page.get_by_text(MESSAGES[message_key][ZH_HK], exact=True).last.wait_for(
            state="visible",
            timeout=10_000,
        )

    page.evaluate(
        """() => {
          Object.defineProperty(navigator, 'canShare', {configurable: true, value: () => false});
          Object.defineProperty(navigator, 'share', {
            configurable: true,
            value: async () => { throw new Error('share must not run when unsupported'); },
          });
        }"""
    )
    _prepare_and_confirm_png_share(page, dialog)
    page.get_by_text(MESSAGES["roster_image_share_unsupported"][ZH_HK], exact=True).last.wait_for(
        state="visible",
        timeout=10_000,
    )

    with page.expect_download(timeout=20_000) as detail_download:
        dialog.get_by_test_id("download-roster-detail").click()
    downloaded = detail_download.value
    if not downloaded.suggested_filename.endswith("_WhatsApp_ZH.png"):
        raise AssertionError(
            f"{label} lost the detailed PNG fallback after native-share failure: "
            f"{downloaded.suggested_filename!r}."
        )
    download_path = downloaded.path()
    if download_path is None or Path(download_path).read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"{label} detailed download fallback was not a PNG.")
    downloaded.delete()
    dialog.get_by_test_id("close-roster-export").click()
    dialog.wait_for(state="hidden", timeout=10_000)


def _assert_export_advanced_options_are_lazy(page: Page, *, label: str) -> None:
    """Prove advanced language/PDF/audit controls mount only on explicit expansion."""

    dialog = page.get_by_test_id("roster-export-dialog")
    page.get_by_test_id("open-roster-export").click()
    dialog.wait_for(state="visible", timeout=10_000)
    advanced = dialog.get_by_test_id("roster-export-advanced")
    toggle = dialog.get_by_test_id("pdf-advanced-options")
    if advanced.count() != 1 or not advanced.is_hidden():
        raise AssertionError(f"{label} advanced shell did not start collapsed.")
    lazy_counts = {
        "language": dialog.get_by_test_id("roster-export-language").count(),
        "pdf": dialog.get_by_test_id("prepare-roster-pdf").count(),
        "auditZh": dialog.get_by_test_id("export-audit-zh").count(),
        "auditEn": dialog.get_by_test_id("export-audit-en").count(),
    }
    if lazy_counts != {"language": 0, "pdf": 0, "auditZh": 0, "auditEn": 0}:
        raise AssertionError(f"{label} mounted advanced controls early: {lazy_counts}")

    toggle.click()
    advanced.wait_for(state="visible", timeout=10_000)
    controls = {
        "language": dialog.get_by_test_id("roster-export-language").count(),
        "pdf": dialog.get_by_test_id("prepare-roster-pdf").count(),
        "auditZh": dialog.get_by_test_id("export-audit-zh").count(),
        "auditEn": dialog.get_by_test_id("export-audit-en").count(),
    }
    if controls != {"language": 1, "pdf": 1, "auditZh": 1, "auditEn": 1}:
        raise AssertionError(f"{label} did not mount one complete advanced control set: {controls}")
    page.evaluate(
        "window.__syAdvancedExportPanel = "
        "document.querySelector('[data-testid=\"roster-export-advanced\"]')"
    )
    dialog.get_by_test_id("roster-export-language").select_option("en")
    page.wait_for_function(
        "document.querySelector('[data-testid=\"roster-export-language\"]')?.value === 'en'"
    )

    toggle.click()
    advanced.wait_for(state="hidden", timeout=10_000)
    if toggle.get_attribute("aria-expanded") != "false":
        raise AssertionError(f"{label} did not expose the collapsed advanced state.")
    toggle.click()
    advanced.wait_for(state="visible", timeout=10_000)
    if not advanced.evaluate("element => element === window.__syAdvancedExportPanel"):
        raise AssertionError(f"{label} remounted its advanced controls on reopen.")
    dialog.get_by_test_id("close-roster-export").click()
    dialog.wait_for(state="hidden", timeout=10_000)
    if not advanced.is_hidden() or toggle.get_attribute("aria-expanded") != "false":
        raise AssertionError(f"{label} did not collapse advanced options on dialog close.")


def _bind_isolated_admin_session(page: Page) -> None:
    """Exercise the real signed Admin download path, never local fallback.

    The release harness supplies an ephemeral signing key. Interception is
    restricted to its verified loopback origin; no test principal is sent to
    third-party resources or installed into production authentication code.
    """
    from nicegui_app.gateway_identity import (
        ORIGIN_PRINCIPAL_AUDIENCE, ORIGIN_PRINCIPAL_HEADER, ORIGIN_PRINCIPAL_VERSION,
        origin_request_binding, seal_origin_principal_for_test,
    )
    isolated_paths()
    origin = urlsplit(BASE_URL)
    if origin.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("Signed browser verification requires a loopback origin.")
    if not os.environ.get("ORIGIN_PRINCIPAL_SECRET"):
        raise RuntimeError("The isolated release harness must supply a signing key.")

    def authenticate(route):  # type: ignore[no-untyped-def]
        request = route.request
        target = urlsplit(request.url)
        if (target.scheme, target.netloc) != (origin.scheme, origin.netloc):
            route.continue_()
            return
        current = int(time.time())
        if target.path == "/auth/status":
            # This endpoint belongs to the gateway, not the isolated origin.
            route.fulfill(status=200, content_type="application/json", body=json.dumps({
                "authenticated": True, "mode": "admin", "expiresAt": current + 600,
            }))
            return
        token = seal_origin_principal_for_test(
            {
                "v": ORIGIN_PRINCIPAL_VERSION,
                "aud": ORIGIN_PRINCIPAL_AUDIENCE,
                "mode": "admin",
                "subject": "fictional-write-verification-admin",
                "sid": "W" * 22,
                "iat": current,
                "exp": current + 600,
                "auth_epoch": 1,
                "kid": "origin-v1",
                "request_binding": origin_request_binding(
                    method=request.method,
                    public_host=target.netloc,
                    path_and_query=target.path + (f"?{target.query}" if target.query else ""),
                ),
            },
            environment=os.environ,
        )
        route.continue_(headers={**request.all_headers(), ORIGIN_PRINCIPAL_HEADER: token})

    page.route("**/*", authenticate)


def _is_generated_get(request) -> bool:
    # Match only in memory; never persist or print the ticket-bearing URL.
    path = urlsplit(request.url).path
    return request.method == "GET" and re.fullmatch(
        r"/api/generated-download/[A-Za-z0-9_-]{32,96}", path,
    ) is not None


def _assert_inline_feedback(page: Page, *, role: str, message: str, label: str) -> None:
    feedback = page.get_by_test_id("roster-export-feedback")
    expect(feedback).to_contain_text(message, timeout=20_000)
    expect(feedback).to_have_attribute("role", role)
    expect(feedback).to_have_attribute("aria-busy", "false")
    visible = feedback.evaluate("""element => {
        const box = element.getBoundingClientRect();
        const top = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
        return element.closest('dialog')?.open === true && element.contains(top);
    }""")
    if not visible:
        raise AssertionError(f"{label} is behind or outside the native top layer")
    PERFORMANCE_EVIDENCE.append({"kind": "inline-feedback", "label": label, "role": role, "hit": True})
    _write_performance_evidence()


def _assert_signed_admin_get_and_feedback(page: Page, published_id: int) -> None:
    from nicegui_app.ui.i18n import MESSAGES, ZH_HK

    _bind_isolated_admin_session(page)
    page.goto(f"{BASE_URL}/rosters/{published_id}", wait_until="domcontentloaded")
    page.get_by_test_id("open-roster-export").click()
    dialog = page.get_by_test_id("roster-export-dialog")
    expect(dialog).to_be_visible()
    with page.expect_response(lambda response: _is_generated_get(response.request), timeout=45_000) as captured:
        with page.expect_download(timeout=45_000) as received:
            dialog.get_by_test_id("prepare-roster-images").click()
    response = captured.value
    assert response.status == 200
    assert response.headers.get("content-type", "").split(";", 1)[0] == "image/png"
    assert "no-store" in response.headers.get("cache-control", "")
    assert response.headers.get("x-content-type-options") == "nosniff"
    received.value.delete()
    # The same real signed session may not consume its completed ticket twice.
    replay = page.evaluate("url => fetch(url, {credentials:'same-origin',cache:'no-store'}).then(r=>r.status)",
                           response.url)
    assert replay == 410
    PERFORMANCE_EVIDENCE.append({"kind": "signed-admin-get", "mime": "image/png",
        "status": 200, "replay": replay, "ticketInEvidence": False})
    _write_performance_evidence()

    page.evaluate("""() => {
        Object.defineProperty(navigator, 'canShare', {configurable:true, value:()=>true});
        Object.defineProperty(navigator, 'share', {configurable:true,
            value:async()=>{throw new Error('fictional native failure');}});
    }""")
    _prepare_and_confirm_png_share(page, dialog)
    _assert_inline_feedback(page, role="alert", message=MESSAGES["roster_image_share_failed"][ZH_HK],
                            label="native-failure-top-layer")

    dialog.get_by_test_id("share-roster-detail").click()
    expect(dialog.get_by_test_id("confirm-share-roster-detail")).to_be_visible()
    _assert_inline_feedback(page, role="status", message=MESSAGES["native_share_prepare_expired"][ZH_HK],
                            label="lease-expiry-top-layer")

    # Fill only this fictional session's real eight-ticket allowance by aborting
    # browser fetches before consumption. No server quota or expiry is changed.
    pattern = "**/api/generated-download/*"
    aborted = []
    def block_download(route):
        assert _is_generated_get(route.request)
        aborted.append(True)
        route.abort("failed")
    page.route(pattern, block_download)
    try:
        for index in range(8):
            page.evaluate("document.body.dataset.syDownload='pending'")
            with page.expect_request(_is_generated_get, timeout=10_000):
                dialog.get_by_test_id("download-roster-detail").click()
            page.wait_for_function("document.body.dataset.syDownload === 'failed'")
            _assert_inline_feedback(page, role="alert", message=MESSAGES["download_delivery_failed"][ZH_HK],
                                    label="fetch-failure-top-layer")
            if index == 0:
                page.evaluate("""() => Object.defineProperty(navigator, 'share', {
                    configurable:true, value:async()=>{throw new DOMException('cancelled', 'AbortError');}
                })""")
                _prepare_and_confirm_png_share(page, dialog)
                _assert_inline_feedback(page, role="status", message=MESSAGES["roster_image_share_cancelled"][ZH_HK],
                                        label="server-status-after-browser-alert")
        assert len(aborted) == 8
        dialog.get_by_test_id("download-roster-detail").click()
        _assert_inline_feedback(page, role="alert", message="REQ-",
                                label="quota-rejection-top-layer")
        assert len(aborted) == 8, "Quota rejection must not start another fetch"
    finally:
        page.unroute(pattern, block_download)
    dialog.get_by_test_id("close-roster-export").click()
    expect(dialog).to_be_hidden()
    page.get_by_test_id("open-roster-export").click()
    _assert_inline_feedback(page, role="status", message=MESSAGES["roster_image_export_notice"][ZH_HK],
                            label="reopened-feedback-reset")
    dialog.get_by_test_id("close-roster-export").click()
    expect(dialog).to_be_hidden()


def main() -> None:
    global BASE_URL, PERFORMANCE_EVIDENCE_PATH, EVIDENCE_METADATA
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signed-only", action="store_true", help="Run signed delivery diagnostics only; no lifecycle evidence")
    args = parser.parse_args()
    scratch = Path(tempfile.mkdtemp(prefix="sy-export-mainline-"))
    environment = isolated_environment(scratch, _free_loopback_port())
    environment["PYTHONPATH"] = os.pathsep.join(sys.path[:3])
    environment.update(ORIGIN_PRINCIPAL_SECRET=secrets.token_hex(32), AUTH_EPOCH="1",
                       ORIGIN_PRINCIPAL_KID="origin-v1")
    os.environ.update(environment)
    BASE_URL = environment["SING_YIN_TEST_URL"]
    from scripts import verify_nicegui_mobile as mobile

    source = _source_state(refresh_fingerprint=True)
    if source["sourceDirty"]:
        raise AssertionError("Export browser evidence requires a clean checkpoint")
    EVIDENCE_METADATA = {**source, "runId": environment["SING_YIN_E2E_RUN_ID"],
        "evidenceKind": "functional-diagnostic", "formalReleaseExecuted": False,
        "controlledPerformance": False, "extractionSource": "856d06c",
        "toolVersions": {"python": platform.python_version(),
            **{name: importlib.metadata.version(name) for name in ("playwright", "nicegui", "Pillow")}}}
    PERFORMANCE_EVIDENCE_PATH = scratch / "raw-samples.json"
    _write_performance_evidence()
    database, backups, _ = isolated_paths()
    fixtures = _ensure_dynamic_roster_route_fixtures(database, backups)
    process, output = _start_server(environment, scratch / "server.log")
    print(f"ISOLATED {scratch}", flush=True)
    errors = []
    expected_console_errors = []
    try:
        _wait_until_ready(process, BASE_URL, scratch / "server.log")
        with sync_playwright() as playwright:
            browser = mobile._launch_real_chrome(playwright)
            EVIDENCE_METADATA["browserVersion"] = browser.version
            try:
                # Keep the original cold maintenance-page lifecycle context.
                if not args.signed_only:
                    page, context = mobile._new_mobile_page(browser, width=390, height=844,
                        label="export-cold", console_errors=errors, page_errors=errors)
                    try:
                        _assert_export_dialog_png_cleanup_cycles(page,
                            published_roster_id=fixtures.published_id, label="export", cycles=20)
                        _assert_png_native_share_outcomes_and_download_fallback(page, label="native-share")
                        _assert_export_advanced_options_are_lazy(page, label="advanced")
                    except Exception:
                        page.screenshot(path=str(scratch / "failure.png"), full_page=True)
                        raise
                    finally:
                        context.close()
                # Separate signed Admin context so auth/request interception
                # cannot warm or change the measured twenty-cycle baseline.
                page, context = mobile._new_mobile_page(browser, width=390, height=844,
                    label="export-signed", console_errors=errors, page_errors=errors,
                    collect_console_errors=False)
                def signed_console(message):
                    if message.type != "error":
                        return
                    path = urlsplit(message.location.get("url", "")).path
                    if re.fullmatch(r"/api/generated-download/[A-Za-z0-9_-]{32,96}", path) and (
                        "410" in message.text or "ERR_FAILED" in message.text
                    ):
                        expected_console_errors.append("intentional-generated-download-failure")
                    else:
                        errors.append("unexpected signed-browser console error")
                page.on("console", signed_console)
                try:
                    _assert_signed_admin_get_and_feedback(page, fixtures.published_id)
                except Exception:
                    page.screenshot(path=str(scratch / "signed-failure.png"), full_page=True)
                    raise
                finally:
                    context.close()
                if errors:
                    raise AssertionError("Unexpected browser errors observed")
            finally:
                browser.close()
        final_source = _source_state(refresh_fingerprint=True)
        if final_source != source:
            raise AssertionError("Source changed during export verification")
        report = {**EVIDENCE_METADATA, "postVerificationSource": final_source,
            "status": "pass", "exportCycles": 0 if args.signed_only else 20, "rawSamples": "raw-samples.json",
            "outcomes": [] if args.signed_only else ["shared", "cancelled", "failed", "unsupported", "download-fallback"],
            "signedOnly": args.signed_only,
            "browserErrorCount": len(errors), "expectedConsoleErrorCount": len(expected_console_errors),
            "routeMatrixExecuted": False}
        (scratch / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"PASS {scratch / 'report.json'}", flush=True)
    except Exception as error:
        (scratch / "failure.json").write_text(json.dumps({**EVIDENCE_METADATA,
            "postVerificationSource": _source_state(refresh_fingerprint=True),
            "status": "fail", "errorType": type(error).__name__,
            "browserErrorCount": len(errors), "rawSamples": "raw-samples.json",
        }, indent=2), encoding="utf-8")
        raise
    finally:
        _write_performance_evidence()
        _stop_server(process, output)


if __name__ == "__main__":
    main()
