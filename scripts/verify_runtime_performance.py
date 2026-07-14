"""Measure browser resource cost and bounded runtime growth on disposable data.

The verifier is intentionally read-only.  It expects an already-running local
NiceGUI instance and records only aggregate browser counters; no roster or
student payload is written to the report.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, sync_playwright


BASE_URL = os.getenv("SING_YIN_TEST_URL", "http://127.0.0.1:8080").rstrip("/")
LOG_DIR = Path(os.getenv("SING_YIN_LOG_DIR", Path(__file__).resolve().parents[1] / "logs"))
REPORT_PATH = LOG_DIR / "runtime-performance-report.json"

RESOURCE_BUDGET_BYTES = 6 * 1024 * 1024
LARGEST_RESOURCE_BUDGET_BYTES = 3 * 1024 * 1024
RESOURCE_COUNT_BUDGET = 140
HEAP_GROWTH_BUDGET_BYTES = 10 * 1024 * 1024
NODE_GROWTH_BUDGET = 160
LISTENER_GROWTH_BUDGET = 100
MOBILE_OVERFLOW_BUDGET_PX = 0

REPRESENTATIVE_ROUTES = (
    "/",
    "/rosters",
    "/prefects",
    "/handover",
    "/engineering",
    "/system-architecture",
)


def evaluate_budget(metrics: dict[str, int]) -> list[str]:
    """Return stable, payload-free budget failure codes."""
    limits = {
        "initial_transfer_bytes": RESOURCE_BUDGET_BYTES,
        "largest_resource_bytes": LARGEST_RESOURCE_BUDGET_BYTES,
        "initial_resource_count": RESOURCE_COUNT_BUDGET,
        "heap_growth_bytes": HEAP_GROWTH_BUDGET_BYTES,
        "node_growth": NODE_GROWTH_BUDGET,
        "listener_growth": LISTENER_GROWTH_BUDGET,
        "navigation_heap_growth_bytes": HEAP_GROWTH_BUDGET_BYTES,
        "navigation_node_growth": NODE_GROWTH_BUDGET,
        "navigation_listener_growth": LISTENER_GROWTH_BUDGET,
        "mobile_overflow_pixels": MOBILE_OVERFLOW_BUDGET_PX,
    }
    return [f"{name}_over_budget" for name, limit in limits.items() if metrics[name] > limit]


def _resource_summary(page: Page) -> dict[str, Any]:
    entries = page.evaluate(
        """
        () => [...performance.getEntriesByType('navigation'), ...performance.getEntriesByType('resource')].map((entry) => ({
          name: new URL(entry.name, location.href).pathname,
          type: entry.entryType === 'navigation' ? 'document' : (entry.initiatorType || 'other'),
          bytes: Math.max(entry.transferSize || 0, entry.encodedBodySize || 0),
          durationMs: Math.round(entry.duration * 10) / 10,
        }))
        """
    )
    initial = [entry for entry in entries if entry["type"] not in {"websocket"}]
    largest = sorted(initial, key=lambda entry: int(entry["bytes"]), reverse=True)[:8]
    return {
        "count": len(initial),
        "transferBytes": sum(int(entry["bytes"]) for entry in initial),
        "largest": largest,
    }


def _runtime_counters(cdp: Any) -> dict[str, int]:
    cdp.send("HeapProfiler.collectGarbage")
    counters = cdp.send("Memory.getDOMCounters")
    performance = cdp.send("Performance.getMetrics")
    values = {metric["name"]: metric["value"] for metric in performance["metrics"]}
    return {
        "documents": int(counters["documents"]),
        "nodes": int(counters["nodes"]),
        "listeners": int(counters["jsEventListeners"]),
        "heapBytes": int(values.get("JSHeapUsedSize", 0)),
    }


def _dom_shape(page: Page) -> dict[str, int]:
    selectors = (
        ".sy-music-dialog",
        "[role='dialog']",
        ".q-dialog",
        ".q-dialog__backdrop",
        ".q-tooltip",
        ".q-menu",
        "audio.sy-page-music-audio",
        ".sy-pointer-light",
    )
    return {selector: page.locator(selector).count() for selector in selectors}


def _wait_for_app(page: Page) -> None:
    page.wait_for_selector("main#main-content", timeout=15_000)
    page.wait_for_function(
        "document.documentElement.dataset.syMotion === 'ready' || "
        "document.documentElement.dataset.syMotion === 'reduced'",
        timeout=8_000,
    )
    page.evaluate("document.fonts?.ready || Promise.resolve()")
    page.wait_for_timeout(250)


def _exercise_repeated_interactions(page: Page, cycles: int = 10) -> None:
    music_button = page.get_by_test_id("page-music-button")
    for _ in range(cycles):
        music_button.click()
        dialog = page.get_by_test_id("page-music-dialog")
        dialog.wait_for(state="visible", timeout=5_000)
        dialog.locator(".sy-music-dialog-header button").first.click()
        dialog.wait_for(state="hidden", timeout=5_000)
        # Quasar removes the teleported dialog tree after its exit transition;
        # measuring sooner would count short-lived transition nodes as a leak.
        page.wait_for_timeout(320)


def main() -> int:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    report: dict[str, Any] = {
        "schemaVersion": 1,
        "status": "running",
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "baseUrl": "loopback-test-origin",
        "routes": list(REPRESENTATIVE_ROUTES),
    }
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1024})
            page = context.new_page()
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            cdp = context.new_cdp_session(page)
            cdp.send("Performance.enable")
            cdp.send("HeapProfiler.enable")

            page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
            _wait_for_app(page)
            resources = _resource_summary(page)

            # One cycle warms lazily-created dialog and pointer surfaces before
            # the baseline. Growth is measured only after this stable state.
            _exercise_repeated_interactions(page, cycles=1)
            baseline = _runtime_counters(cdp)
            baseline_shape = _dom_shape(page)
            _exercise_repeated_interactions(page)
            page.wait_for_timeout(750)
            after_interactions = _runtime_counters(cdp)
            after_shape = _dom_shape(page)

            route_samples: list[dict[str, int | str]] = []
            for route in REPRESENTATIVE_ROUTES:
                page.goto(f"{BASE_URL}{route}", wait_until="domcontentloaded")
                _wait_for_app(page)
                sample = _runtime_counters(cdp)
                route_samples.append({"route": route, **sample})

            page.set_viewport_size({"width": 390, "height": 844})
            mobile_overflow: list[dict[str, Any]] = []
            for route in ("/engineering", "/guide", "/settings", "/system-architecture"):
                page.goto(f"{BASE_URL}{route}", wait_until="domcontentloaded")
                _wait_for_app(page)
                overflow = page.evaluate(
                    """
                    () => {
                      const client = document.documentElement.clientWidth;
                      const offenders = [...document.querySelectorAll('body *')]
                        .map((element) => {
                          const bounds = element.getBoundingClientRect();
                          return {
                            tag: element.tagName.toLowerCase(),
                            className: String(element.className || '').slice(0, 120),
                            left: Math.round(bounds.left),
                            right: Math.round(bounds.right),
                          };
                        })
                        .filter((item) => item.right > client + 1)
                        .slice(0, 12);
                      return {
                        overflowPixels: Math.max(0, document.documentElement.scrollWidth - client),
                        offenders,
                      };
                    }
                    """
                )
                mobile_overflow.append({"route": route, **overflow})

            page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
            _wait_for_app(page)
            final_home = _runtime_counters(cdp)
            context.close()
            browser.close()

        metrics = {
            "initial_transfer_bytes": int(resources["transferBytes"]),
            "largest_resource_bytes": max((int(item["bytes"]) for item in resources["largest"]), default=0),
            "initial_resource_count": int(resources["count"]),
            "heap_growth_bytes": max(0, after_interactions["heapBytes"] - baseline["heapBytes"]),
            "node_growth": max(0, after_interactions["nodes"] - baseline["nodes"]),
            "listener_growth": max(0, after_interactions["listeners"] - baseline["listeners"]),
            "navigation_heap_growth_bytes": max(0, final_home["heapBytes"] - baseline["heapBytes"]),
            "navigation_node_growth": max(0, final_home["nodes"] - baseline["nodes"]),
            "navigation_listener_growth": max(0, final_home["listeners"] - baseline["listeners"]),
            "mobile_overflow_pixels": max(
                (int(sample["overflowPixels"]) for sample in mobile_overflow),
                default=0,
            ),
        }
        failures = evaluate_budget(metrics)
        report.update(
            {
                "status": "fail" if failures or console_errors or page_errors else "pass",
                "finishedAt": datetime.now(timezone.utc).isoformat(),
                "metrics": metrics,
                "baseline": baseline,
                "baselineDomShape": baseline_shape,
                "afterInteractions": after_interactions,
                "afterInteractionDomShape": after_shape,
                "finalHome": final_home,
                "routeSamples": route_samples,
                "mobileOverflow": mobile_overflow,
                "largestResources": resources["largest"],
                "consoleErrorCount": len(console_errors),
                "pageErrorCount": len(page_errors),
                "failures": failures
                + (["browser_console_errors"] if console_errors else [])
                + (["browser_page_errors"] if page_errors else []),
            }
        )
    except Exception as error:  # noqa: BLE001 - verifier boundary writes a failed aggregate report
        report.update(
            {
                "status": "fail",
                "finishedAt": datetime.now(timezone.utc).isoformat(),
                "failures": ["runtime_verifier_error"],
                "errorType": type(error).__name__,
            }
        )
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if report["status"] != "pass":
        print(f"Runtime performance verification failed: {report.get('failures', [])}")
        print(f"Aggregate report: {REPORT_PATH}")
        return 1
    metrics = report["metrics"]
    print(
        "Runtime performance passed: "
        f"initial={metrics['initial_transfer_bytes'] / 1024 / 1024:.2f} MiB, "
        f"heap growth={metrics['heap_growth_bytes'] / 1024 / 1024:.2f} MiB, "
        f"nodes +{metrics['node_growth']}, listeners +{metrics['listener_growth']}."
    )
    print(f"Aggregate report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
