"""Source-owned mobile coverage and evidence; reports cannot choose their gates.

Only aggregate, fictional-fixture evidence belongs here. Browser runners own
gestures and semantic assertions; this module owns the expected coverage.
"""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Mapping

from nicegui_app.ui.page_catalog import PAGE_DEFINITIONS

CONTRACT_VERSION = 1
VIEWPORTS = ((256, 700), (320, 760), (360, 800), (390, 844),
             (430, 932), (844, 390), (768, 1024), (820, 1180))
ENGINES = ("chromium", "webkit")
PERFORMANCE_PROFILE = {
    "id": "mobile-fast4g-cpu4-v1", "width": 390, "height": 844, "dpr": 2,
    "latencyMs": 150, "downloadBytesPerSecond": 200_000,
    "uploadBytesPerSecond": 93_750, "cpuSlowdown": 4, "cacheDisabled": True,
}
PERFORMANCE_BUDGETS = {
    "nicegui": {"ttfb": 800, "fcp": 1800, "lcp": 2500, "cls": 0.05,
                "tbt": 300, "longestTask": 200, "visualFeedback": 100,
                "labInteractionLatency": 200, "resourceBytes": 2 * 1024 * 1024,
                "requests": 80},
    "public": {"ttfb": 500, "fcp": 1500, "lcp": 2000, "cls": 0.05,
               "tbt": 200, "longestTask": 150, "visualFeedback": 100,
               "labInteractionLatency": 200, "resourceBytes": 350 * 1024,
               "requests": 10},
}
REQUIRED_OBSERVERS = frozenset(("navigation", "paint", "largest-contentful-paint",
                                "layout-shift", "longtask", "event"))
CORE_REPETITIONS = {
    "date-switch": 10, "person-switch": 10, "candidate-select": 10,
    "prefect-sheet-open": 20, "prefect-sheet-close": 20,
    "draft-sheet-open": 20, "draft-sheet-close": 20,
    "drawer-open": 20, "drawer-close": 20,
}
SUPPLEMENTAL_ROUTES = ("/audit", "/rosters/history")
REDIRECTS = {"/dashboard": "/", "/rosters/new": "/rosters",
             "/adjustments": "/rosters"}
DYNAMIC_ROUTES = ("/rosters/{roster_week_id}",
                  "/rosters/{roster_week_id}/adjustments")


@dataclass(frozen=True)
class Scenario:
    id: str
    surface: str
    route: str
    state: str
    ready_assertion: str
    result_assertion: str
    extended: bool = False


def base_routes() -> tuple[str, ...]:
    """Include non-navigation pages; aliases and dynamic states stay explicit."""
    return tuple(dict.fromkeys((*[page.route for page in PAGE_DEFINITIONS],
                               *SUPPLEMENTAL_ROUTES)))


def scenarios() -> tuple[Scenario, ...]:
    base = tuple(Scenario(f"page:{route}", "workbench", route, "ready",
                          "main-visible-and-connected", "layout-touch-focus")
                 for route in base_routes())
    aliases = tuple(Scenario(f"redirect:{route}", "workbench", route, "redirect",
                             "main-visible-and-connected", f"location:{target}")
                    for route, target in REDIRECTS.items())
    states = (
        ("/", "empty", False), ("/", "populated", False),
        (DYNAMIC_ROUTES[0], "draft-saved", True),
        (DYNAMIC_ROUTES[0], "draft-dirty", True),
        (DYNAMIC_ROUTES[0], "draft-conflict", True),
        (DYNAMIC_ROUTES[0], "published", False),
        (DYNAMIC_ROUTES[0], "withdrawn", False),
        (DYNAMIC_ROUTES[1], "replacement", True),
        (DYNAMIC_ROUTES[1], "vacancy", True),
        (DYNAMIC_ROUTES[1], "receipt", True),
        ("/prefects", "filter", True), ("/prefects", "editor", True),
        ("/prefects", "import-preview", True),
        ("/settings", "restore-confirmation", True),
        ("/support", "success", True), ("/support", "failure", True),
    )
    flows = tuple(Scenario(f"state:{route}:{state}", "workbench", route, state,
                           f"fixture:{state}", f"semantic:{state}", extended)
                  for route, state, extended in states)
    public = (Scenario("public:entrance", "public", "/", "ready",
                       "identity-options-visible", "identity-navigation"),)
    viewer = tuple(Scenario(f"viewer:{state}", "viewer", "/view", state,
                            f"fixture:{state}", f"decryption:{state}")
                   for state in ("valid", "revoked", "wrong-key", "expired"))
    return (*base, *aliases, *flows, *public, *viewer)


def required_profiles(scenario: Scenario) -> tuple[str, ...]:
    full = scenario.id.startswith(("page:", "public:")) or scenario.id == "viewer:valid"
    sizes = VIEWPORTS if full else ((390, 844),)
    profiles = [f"{engine}:{width}x{height}:default"
                for engine in ENGINES for width, height in sizes]
    # Each base page is checked under every preference, not just Dashboard.
    variants = ("dark", "english", "text200", "reduced", "forced") if full else ()
    profiles.extend(f"{engine}:390x844:{variant}"
                    for engine in ENGINES for variant in variants)
    if scenario.extended:
        profiles.extend(f"{engine}:{size}:{variant}" for engine in ENGINES
                        for size, variant in (("320x760", "default"),
                                              ("844x390", "default"),
                                              ("390x844", "text200"),
                                              ("390x844", "keyboard-proxy")))
    return tuple(profiles)


def expected_cases() -> frozenset[tuple[str, str]]:
    return frozenset((scenario.id, profile) for scenario in scenarios()
                     for profile in required_profiles(scenario))


def contract_fingerprint() -> str:
    payload = {"version": CONTRACT_VERSION, "scenarios": [asdict(s) for s in scenarios()],
               "cases": sorted(expected_cases()), "performance": PERFORMANCE_PROFILE,
               "budgets": PERFORMANCE_BUDGETS, "repetitions": CORE_REPETITIONS}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def assert_registered_routes(route_directory: Path) -> None:
    """Inspect decorators without importing pages or starting an application."""
    actual = []
    for path in route_directory.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name) and node.func.value.id == "ui"
                    and node.func.attr == "page"):
                route = node.args[0] if node.args else next(
                    (keyword.value for keyword in node.keywords if keyword.arg == "path"), None)
                if not isinstance(route, ast.Constant) or not isinstance(route.value, str):
                    raise ValueError("Unsupported route registration requires explicit coverage")
                actual.append(route.value)
    expected = set((*base_routes(), *REDIRECTS, *DYNAMIC_ROUTES))
    if set(actual) != expected or len(actual) != len(set(actual)):
        raise ValueError(f"Route coverage drift: missing={sorted(expected - set(actual))}; "
                         f"uncovered={sorted(set(actual) - expected)}")


def validate_coverage(records: Iterable[Mapping[str, Any]]) -> list[str]:
    rows = list(records)
    if any(not isinstance(row, Mapping)
           or not isinstance(row.get("scenarioId"), str)
           or not isinstance(row.get("profileId"), str) for row in rows):
        return ["malformed coverage record"]
    keys = [(row.get("scenarioId"), row.get("profileId")) for row in rows]
    counts = Counter(keys)
    expected = expected_cases()
    errors = []
    if set(keys) != expected:
        errors.append(f"coverage mismatch: missing={len(expected - set(keys))}, "
                      f"unexpected={len(set(keys) - expected)}")
    if any(count != 1 for count in counts.values()):
        errors.append("duplicate scenario/profile evidence")
    definitions = {scenario.id: scenario for scenario in scenarios()}
    for row in rows:
        definition = definitions.get(row.get("scenarioId"))
        if (row.get("status") != "pass" or not definition
                or row.get("readyAssertion") != definition.ready_assertion
                or row.get("resultAssertion") != definition.result_assertion):
            errors.append(f"unverified scenario: {row.get('scenarioId')}")
    return errors


def validate_release_context(report: Mapping[str, Any], *, fingerprint: str) -> list[str]:
    errors = []
    expected = {"schemaVersion": CONTRACT_VERSION, "evidenceKind": "release",
                "contractFingerprint": contract_fingerprint(), "sourceFingerprint": fingerprint,
                "sourceDirty": False, "profile": PERFORMANCE_PROFILE}
    for key, value in expected.items():
        if (report.get(key) != value or (key == "sourceDirty" and report.get(key) is not False)
                or (key == "schemaVersion" and type(report.get(key)) is not int)):
            errors.append(f"invalid {key}")
    profile = report.get("profile")
    if not isinstance(profile, Mapping) or profile.get("cacheDisabled") is not True:
        errors.append("cold cache must be explicitly disabled")
    for key in ("runId", "fixtureId", "browserVersion", "os"):
        if not isinstance(report.get(key), str) or not report[key].strip():
            errors.append(f"missing {key}")
    for key in ("sourceCommit", "sourceTree"):
        if not isinstance(report.get(key), str) or not re.fullmatch(r"[0-9a-f]{40}", report[key]):
            errors.append(f"invalid {key}")
    versions = report.get("toolVersions")
    if (not isinstance(versions, dict) or not versions
            or any(not isinstance(k, str) or not k or not isinstance(v, str) or not v
                   for k, v in versions.items())):
        errors.append("invalid toolVersions")
    if report.get("browserEngine") != "chromium":
        errors.append("CDP performance requires chromium evidence")
    return errors


def _finite_nonnegative(value: Any) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def p75(values: list[float]) -> float:
    if not values or not all(_finite_nonnegative(value) for value in values):
        raise ValueError("p75 requires finite nonnegative samples")
    ordered = sorted(values)
    rank = (len(ordered) - 1) * 0.75
    low, high = math.floor(rank), math.ceil(rank)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def validate_performance(samples: list[Mapping[str, Any]], *, surface: str) -> list[str]:
    """Recompute budgets from raw samples; never trust a caller's summary."""
    errors = []
    if surface not in {"nicegui", "public", "viewer"}:
        return ["unknown performance surface"]
    if any(not isinstance(sample, Mapping) for sample in samples):
        return ["malformed performance sample"]
    if len(samples) < 5:
        errors.append("five cold samples required")
    sample_ids = [sample.get("sampleId") for sample in samples]
    if any(not isinstance(value, str) or not value for value in sample_ids):
        errors.append("missing or invalid sampleId")
    elif len(set(sample_ids)) != len(samples):
        errors.append("missing or duplicate sampleId")
    for sample in samples:
        support = sample.get("observerSupport")
        observer_state = sample.get("observerState")
        if (not isinstance(support, list) or any(not isinstance(value, str) for value in support)
                or not REQUIRED_OBSERVERS.issubset(support)
                or sample.get("semanticResult") is not True
                or type(sample.get("observedInteractionCount")) is not int
                or sample["observedInteractionCount"] < 1
                or type(sample.get("lcpEntryCount")) is not int or sample["lcpEntryCount"] < 1):
            errors.append("missing real observer/interaction evidence")
        if (not isinstance(observer_state, Mapping)
                or any(observer_state.get(name) not in {"observing", "collected"}
                       for name in REQUIRED_OBSERVERS)):
            errors.append("observer did not start/collect")
        applied = sample.get("appliedProfile")
        if (applied != PERFORMANCE_PROFILE or not isinstance(applied, Mapping)
                or applied.get("cacheDisabled") is not True
                or type(sample.get("navigationStatus")) is not int
                or sample["navigationStatus"] != 200):
            errors.append("unverified cold navigation/profile")
    for key in ("contextId", "navigationId"):
        values = [sample.get(key) for sample in samples]
        if (any(not isinstance(value, str) or not value for value in values)
                or len(set(values)) != len(samples)):
            errors.append(f"cold samples require unique {key}")
    budgets = PERFORMANCE_BUDGETS["public" if surface == "viewer" else surface]
    for metric, budget in budgets.items():
        values = [sample.get(metric) for sample in samples]
        if not values or not all(_finite_nonnegative(value) for value in values):
            errors.append(f"missing/invalid metric: {metric}")
        elif metric in {"requests", "resourceBytes"} and any(type(value) is not int for value in values):
            errors.append(f"invalid count: {metric}")
        elif metric in {"fcp", "lcp", "requests", "resourceBytes", "visualFeedback",
                        "labInteractionLatency"} and any(value == 0 for value in values):
            errors.append(f"unobserved metric: {metric}")
        elif p75(values) > budget:
            errors.append(f"p75 exceeds budget: {metric}")
    return errors


def performance_scenarios() -> dict[str, str]:
    """Cold pages plus actual dynamic workflow targets, not Dashboard alone."""
    dynamic = {f"state:{DYNAMIC_ROUTES[0]}:draft-saved",
               f"state:{DYNAMIC_ROUTES[0]}:published",
               f"state:{DYNAMIC_ROUTES[1]}:replacement"}
    return {scenario.id: "nicegui" if scenario.surface == "workbench" else scenario.surface
            for scenario in scenarios()
            if scenario.id.startswith("page:") or scenario.id in dynamic
            or scenario.id in {"public:entrance", "viewer:valid"}}


def validate_mobile_release_report(report: Any, *, fingerprint: str) -> list[str]:
    """Single consumer entry point; every expected evidence category is required."""
    if not isinstance(report, Mapping):
        return ["malformed mobile report"]
    errors = validate_release_context(report, fingerprint=fingerprint)
    coverage = report.get("coverage")
    core = report.get("coreInteractions")
    performance = report.get("performance")
    errors.extend(validate_coverage(coverage) if isinstance(coverage, list) else ["missing coverage"])
    errors.extend(validate_core_interactions(core) if isinstance(core, list) else ["missing core interactions"])
    if (not isinstance(performance, list) or any(not isinstance(row, Mapping)
            or not isinstance(row.get("scenarioId"), str) for row in performance)):
        return [*errors, "missing/malformed performance groups"]
    expected = performance_scenarios()
    ids = [row["scenarioId"] for row in performance]
    if set(ids) != set(expected) or len(ids) != len(expected):
        errors.append("missing, unexpected or duplicate performance target")
    for row in performance:
        samples = row.get("samples")
        if row["scenarioId"] not in expected or not isinstance(samples, list):
            errors.append("invalid performance target/samples")
        else:
            if any(not isinstance(sample, Mapping) or sample.get("scenarioId") != row["scenarioId"]
                   for sample in samples):
                errors.append("sample belongs to a different performance target")
            errors.extend(f"{row['scenarioId']}: {error}" for error in
                          validate_performance(samples, surface=expected[row["scenarioId"]]))
    for key in ("contextId", "navigationId"):
        values = [sample.get(key) for row in performance if isinstance(row.get("samples"), list)
                  for sample in row["samples"] if isinstance(sample, Mapping)]
        if any(not isinstance(value, str) or not value for value in values):
            errors.append(f"invalid global {key}")
        elif len(set(values)) != len(values):
            errors.append(f"cold {key} reused across performance targets")
    return errors


def validate_core_interactions(records: list[Mapping[str, Any]]) -> list[str]:
    if any(not isinstance(row, Mapping) or not isinstance(row.get("action"), str)
           or type(row.get("iteration")) is not int for row in records):
        return ["malformed core interaction"]
    expected = {(action, iteration) for action, count in CORE_REPETITIONS.items()
                for iteration in range(1, count + 1)}
    keys = [(row.get("action"), row.get("iteration")) for row in records]
    errors = []
    if set(keys) != expected or len(keys) != len(expected):
        errors.append("missing, unexpected or duplicate core interaction")
    for row in records:
        duration = row.get("longestTaskMs")
        elapsed = row.get("elapsedMs")
        tasks = row.get("tasks")
        if (not _finite_nonnegative(elapsed) or elapsed == 0 or not isinstance(tasks, list)
                or any(not isinstance(task, Mapping)
                       or type(task.get("startMs")) not in (float, int)
                       or not _finite_nonnegative(abs(task["startMs"]))
                       or not _finite_nonnegative(task.get("durationMs"))
                       or task["durationMs"] == 0 for task in tasks)):
            errors.append("missing/invalid raw core task window")
            continue
        overlapping = [task for task in tasks if task["startMs"] < elapsed
                       and task["startMs"] + task["durationMs"] > 0]
        measured = max((task["durationMs"] for task in overlapping), default=0)
        carry_in = any(task["startMs"] < 0 for task in overlapping)
        if (not _finite_nonnegative(duration) or duration > 50
                or duration != measured or carry_in
                or row.get("semanticResult") is not True or row.get("carryIn") is not False
                or row.get("longTaskObserverSupported") is not True
                or row.get("windowComplete") is not True):
            errors.append(f"invalid core window: {row.get('action')}/{row.get('iteration')}")
    return errors


class VerificationIntegrityError(RuntimeError):
    """Source drift or unsafe fixture ownership stops all remaining gestures."""


class ScenarioUnavailable(RuntimeError):
    """An unavailable fixture/engine must leave an explicit not_run record."""


def collect_case_results(
    run_case: Callable[[Scenario, str], bool],
    *,
    check_integrity: Callable[[], None],
) -> list[dict[str, Any]]:
    """Continue independent failures, stop unsafe runs, never lose expected rows.

    A runner returns True only after both named assertions complete. Exceptions
    are categorized without copying browser text, URLs, names or secrets into
    the aggregate report. Detailed diagnostics stay in the isolated local log.
    """
    results = []
    stopped = False

    def require_integrity() -> None:
        try:
            check_integrity()
        except Exception as error:
            raise VerificationIntegrityError("unverifiable source or fixture") from error

    for scenario in scenarios():
        for profile in required_profiles(scenario):
            row = {"scenarioId": scenario.id, "profileId": profile, "status": "not_run"}
            if stopped:
                row["reason"] = "integrity-stop"
            else:
                try:
                    require_integrity()
                    if run_case(scenario, profile) is not True:
                        raise AssertionError("semantic assertions not confirmed")
                    # Drift during the gesture invalidates its result too.
                    require_integrity()
                    row.update(status="pass", readyAssertion=scenario.ready_assertion,
                               resultAssertion=scenario.result_assertion)
                except VerificationIntegrityError:
                    row.update(status="error", reason="integrity-stop")
                    stopped = True
                except ScenarioUnavailable:
                    row["reason"] = "fixture-or-engine-unavailable"
                except AssertionError:
                    row.update(status="fail", reason="assertion-failed")
                except Exception:
                    row.update(status="error", reason="runner-error")
            results.append(row)
    return results
