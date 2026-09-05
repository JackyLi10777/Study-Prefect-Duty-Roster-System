"""Compare isolated, fictional PNG renders against a same-host pre-refactor baseline.

Each sample runs in a fresh process. OS peak working set includes Pillow's native
allocations, unlike tracemalloc. Baselines are explicitly recorded, never silently
created/replaced by a release gate. Reports contain metrics, not roster payloads.
"""

from __future__ import annotations

import argparse
import ctypes
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for directory in (PROJECT_ROOT, PROJECT_ROOT / "packages/roster_policy", PROJECT_ROOT / "packages/roster_core"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

SAMPLE_COUNT = 5
REGRESSION_FACTOR = 1.10
FIXTURE_VERSION = "fictional-six-posts-20260907-v1"


def summarize(samples: list[dict]) -> dict:
    if len(samples) < SAMPLE_COUNT:
        raise ValueError("At least five fresh-process samples are required.")
    for sample in samples:
        for key in ("elapsed_ms", "peak_rss_bytes"):
            value = sample[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"Invalid measured {key}.")
    durations = sorted(sample["elapsed_ms"] for sample in samples)
    return {
        "sample_count": len(samples),
        "p75_elapsed_ms": durations[math.ceil(len(durations) * 0.75) - 1],
        "peak_rss_bytes": max(sample["peak_rss_bytes"] for sample in samples),
        "samples": samples,
    }


def compare_reports(baseline: dict, candidate: dict) -> list[str]:
    failures = []
    if baseline.get("schema_version") != 1 or candidate.get("schema_version") != 1:
        failures.append("Unsupported measurement schema.")
    if not baseline.get("environment") or baseline.get("environment") != candidate.get("environment"):
        failures.append("Baseline environment/assets differ; use the same measured host and fixture.")
    for language in ("zh", "en"):
        try:
            before = summarize(baseline["languages"][language]["samples"])
            after = summarize(candidate["languages"][language]["samples"])
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(f"{language}: incomplete/invalid measurements ({type(exc).__name__}).")
            continue
        if before["sample_count"] != after["sample_count"]:
            failures.append(f"{language}: sample counts differ.")
        if after["p75_elapsed_ms"] > before["p75_elapsed_ms"] * REGRESSION_FACTOR:
            failures.append(f"{language}: p75 elapsed time exceeds the baseline by more than 10%.")
        if after["peak_rss_bytes"] > before["peak_rss_bytes"] * REGRESSION_FACTOR:
            failures.append(f"{language}: native peak memory exceeds the baseline by more than 10%.")
    return failures


def _peak_rss_bytes() -> int:
    if sys.platform == "win32":
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                    "PagefileUsage", "PeakPagefileUsage",
                )
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(counters.PeakWorkingSetSize)
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def _fixture():
    from nicegui_app.services.roster_presentation import DAY_ORDER, ROSTER_ROWS
    from roster_policy import is_room_open

    week = {
        "id": 42, "weekStart": date(2026, 9, 7), "version": 4,
        "status": "published", "policyVersion": "2026.09.04-unified-duty-hours",
        "closedDays": ["WEDNESDAY"],
        "slotExceptions": [{"kind": "unavailable", "cellKey": "MONDAY:ROOM_302:1"}],
    }
    # Deliberately synthetic names covering 2/4/8 glyphs and punctuation.
    names = ("測甲", "測試乙丙", "測試甲乙丙丁戊己", "測試丁·", "測戊", "測試己庚")
    assignments = []
    for day in DAY_ORDER:
        for index, row in enumerate(ROSTER_ROWS):
            cell_key = f"{day.name}:{row.post.name}:{row.slot_index}"
            closed = day.name == "WEDNESDAY" or not is_room_open(row.post, day) or cell_key == "MONDAY:ROOM_302:1"
            vacant = cell_key == "THURSDAY:ROOM_303:1"
            assigned = not closed and not vacant
            assignments.append({
                "id": len(assignments) + 1, "day": day.name, "postCode": row.post.name,
                "slotIndex": row.slot_index, "status": "closed" if closed else "vacant" if vacant else "active",
                "prefectId": f"fictional-{len(assignments)}" if assigned else None,
                "prefectName": names[index] if assigned else None, "weight": 1.0,
            })
    return week, assignments


def _sample(language: str) -> dict:
    from nicegui_app.services.roster_image_export import build_roster_png_bundle

    class FictionalWorkflow:
        def roster_schedule_snapshot(self, roster_week_id):
            assert roster_week_id == 42
            return _fixture()

    start = time.perf_counter()
    bundle = build_roster_png_bundle(FictionalWorkflow(), 42, language=language)
    elapsed = (time.perf_counter() - start) * 1000
    return {
        "elapsed_ms": elapsed,
        "peak_rss_bytes": _peak_rss_bytes(),
        "avatar_bytes": len(bundle.avatar.content),
        "detail_bytes": len(bundle.whatsapp.content),
        "avatar_sha256": hashlib.sha256(bundle.avatar.content).hexdigest(),
        "detail_sha256": hashlib.sha256(bundle.whatsapp.content).hexdigest(),
    }


def _environment() -> dict:
    import PIL
    from nicegui_app.config import DISPLAY_PRINT_CREST_PATH

    font_dir = PROJECT_ROOT / "nicegui_app/assets/fonts"
    assets = [font_dir / f"NotoSansHK-{weight}.ttf" for weight in ("Regular", "Medium", "SemiBold")]
    assets.append(Path(DISPLAY_PRINT_CREST_PATH))
    digest = hashlib.sha256()
    for asset in assets:
        digest.update(asset.name.encode())
        digest.update(asset.read_bytes())
    return {
        "host_sha256": hashlib.sha256(platform.node().encode()).hexdigest(),
        "platform": platform.platform(), "machine": platform.machine(),
        "python": platform.python_version(), "pillow": PIL.__version__,
        "assets_sha256": digest.hexdigest(), "fixture": FIXTURE_VERSION,
    }


def measure() -> dict:
    languages = {}
    for language in ("zh", "en"):
        samples = []
        for _ in range(SAMPLE_COUNT):
            process = subprocess.run(
                [sys.executable, "-X", "utf8", str(Path(__file__).resolve()), "--sample", language],
                cwd=PROJECT_ROOT, check=True, capture_output=True, text=True, encoding="utf-8", timeout=120,
            )
            samples.append(json.loads(process.stdout))
        languages[language] = summarize(samples)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, check=True, capture_output=True, text=True).stdout.strip()
    return {"schema_version": 1, "source_commit": commit, "environment": _environment(), "languages": languages}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--record-baseline", action="store_true")
    modes.add_argument("--baseline", type=Path)
    modes.add_argument("--sample", choices=("zh", "en"), help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.sample:
        print(json.dumps(_sample(args.sample)))
        return 0
    if args.output is None:
        parser.error("--output is required")
    output = args.output.resolve()
    if args.record_baseline and output.exists():
        parser.error("Refusing to replace an existing baseline.")
    if args.baseline and args.baseline.resolve() == output:
        parser.error("Candidate output must not overwrite its baseline.")
    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline else None
    result = measure()
    failures = compare_reports(baseline, result) if baseline is not None else []
    result["state"] = "baseline" if baseline is None else "failed" if failures else "passed"
    result["failures"] = failures
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x" if args.record_baseline else "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    for language, summary in result["languages"].items():
        print(f"{language}: p75 {summary['p75_elapsed_ms']:.1f}ms; peak RSS {summary['peak_rss_bytes']} bytes")
    for failure in failures:
        print(failure, file=sys.stderr)
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
