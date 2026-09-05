from copy import deepcopy
from pathlib import Path

import pytest

from scripts import mobile_verification_contract as contract


def complete_coverage():
    definitions = {item.id: item for item in contract.scenarios()}
    return [{"scenarioId": sid, "profileId": pid, "status": "pass",
             "readyAssertion": definitions[sid].ready_assertion,
             "resultAssertion": definitions[sid].result_assertion}
            for sid, pid in sorted(contract.expected_cases())]


def test_catalog_covers_actual_routes_without_importing_pages():
    contract.assert_registered_routes(Path(__file__).parents[1] / "nicegui_app/ui/page_routes")
    assert "/audit" in contract.base_routes()
    assert "/rosters/history" in contract.base_routes()
    assert not contract.validate_coverage(complete_coverage())


def test_verification_contract_is_bound_to_release_source():
    from nicegui_app.release_evidence import RELEASE_SOURCE_FILES
    assert Path(contract.__file__).resolve() in RELEASE_SOURCE_FILES


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unexpected", "not_run", "unready"])
def test_coverage_cannot_be_forged_by_a_shortened_green_report(mutation):
    rows = complete_coverage()
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(dict(rows[0]))
    elif mutation == "unexpected":
        rows[0]["profileId"] = "made-up"
    elif mutation == "not_run":
        rows[0]["status"] = "not_run"
    else:
        rows[0].pop("readyAssertion")
    assert contract.validate_coverage(rows)


def test_new_route_requires_a_coverage_decision(tmp_path):
    (tmp_path / "page.py").write_text('@ui.page("/new-page")\ndef render(): pass\n')
    with pytest.raises(ValueError, match="uncovered"):
        contract.assert_registered_routes(tmp_path)


def valid_context():
    return {"schemaVersion": 1, "evidenceKind": "release", "sourceDirty": False,
            "contractFingerprint": contract.contract_fingerprint(), "sourceFingerprint": "source",
            "profile": deepcopy(contract.PERFORMANCE_PROFILE), "runId": "run", "fixtureId": "fictional",
            "sourceCommit": "a" * 40, "sourceTree": "b" * 40, "browserVersion": "test-version",
            "browserEngine": "chromium", "os": "test-os", "toolVersions": {"python": "3.12"}}


@pytest.mark.parametrize("key,value", [("evidenceKind", "diagnostic"), ("sourceDirty", True),
    ("sourceDirty", 0), ("sourceFingerprint", "old"), ("browserEngine", "webkit"),
    ("contractFingerprint", "old"), ("fixtureId", ""), ("toolVersions", {})])
def test_release_context_rejects_wrong_source_kind_or_profile(key, value):
    report = valid_context()
    assert not contract.validate_release_context(report, fingerprint="source")
    report[key] = value
    assert contract.validate_release_context(report, fingerprint="source")


def test_unthrottled_core_diagnostics_cannot_certify_release():
    report = valid_context()
    report["profile"]["cpuSlowdown"] = 1
    assert contract.validate_release_context(report, fingerprint="source")


def samples():
    return [{"sampleId": str(i), **contract.PERFORMANCE_BUDGETS["nicegui"],
             "observerSupport": sorted(contract.REQUIRED_OBSERVERS),
             "observerState": {name: "collected" for name in contract.REQUIRED_OBSERVERS},
             "semanticResult": True, "observedInteractionCount": 1, "lcpEntryCount": 1,
             "appliedProfile": deepcopy(contract.PERFORMANCE_PROFILE), "navigationStatus": 200,
             "contextId": str(i), "navigationId": str(i)} for i in range(5)]


@pytest.mark.parametrize("mutation", ["short", "nan", "bool", "negative", "missing", "duplicate", "over"])
def test_raw_performance_samples_are_required_and_recomputed(mutation):
    rows = samples()
    assert not contract.validate_performance(rows, surface="nicegui")
    if mutation == "short":
        rows.pop()
    elif mutation == "missing":
        rows[0].pop("fcp")
    elif mutation == "duplicate":
        rows[0]["sampleId"] = rows[1]["sampleId"]
    elif mutation == "over":
        for row in rows:
            row["lcp"] += 1
    else:
        rows[0]["fcp"] = {"nan": float("nan"), "bool": False, "negative": -1}[mutation]
    assert contract.validate_performance(rows, surface="nicegui")


def test_p75_uses_raw_values_not_best_run():
    assert contract.p75([10, 30, 20, 50, 40]) == 40


@pytest.mark.parametrize("values", [[], [float("inf")], [False], [-1]])
def test_p75_rejects_invalid_values(values):
    with pytest.raises(ValueError):
        contract.p75(values)


def core_rows():
    return [{"action": action, "iteration": i, "longestTaskMs": 0,
             "semanticResult": True, "carryIn": False, "elapsedMs": 100,
             "tasks": [], "longTaskObserverSupported": True, "windowComplete": True}
            for action, count in contract.CORE_REPETITIONS.items() for i in range(1, count + 1)]


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "carry", "long", "unready"])
def test_core_requires_every_open_close_selection_and_clean_complete_window(mutation):
    rows = core_rows()
    assert not contract.validate_core_interactions(rows)
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(dict(rows[0]))
    elif mutation == "carry":
        rows[0]["carryIn"] = True
    elif mutation == "long":
        rows[0]["longestTaskMs"] = 51
    else:
        rows[0]["semanticResult"] = False
    assert contract.validate_core_interactions(rows)


def test_independent_failure_does_not_skip_webkit_or_viewer():
    visited = []

    def run(scenario, profile):
        visited.append((scenario.id, profile))
        if scenario.id == "page:/" and profile.startswith("chromium:"):
            raise AssertionError("sensitive diagnostic must not be in aggregate")
        return True

    rows = contract.collect_case_results(run, check_integrity=lambda: None)
    assert len(visited) == len(contract.expected_cases())
    assert any(row["scenarioId"] == "viewer:valid" and row["status"] == "pass" for row in rows)
    assert any(row["profileId"].startswith("webkit:") and row["status"] == "pass" for row in rows)
    assert "sensitive" not in str(rows)
    assert contract.validate_coverage(rows)


def test_integrity_failure_stops_gestures_but_reports_all_remaining_cases():
    visited = []

    def run(scenario, profile):
        visited.append(scenario.id)
        raise contract.VerificationIntegrityError()

    rows = contract.collect_case_results(run, check_integrity=lambda: None)
    assert len(visited) == 1
    assert len(rows) == len(contract.expected_cases())
    assert rows[0]["status"] == "error"
    assert all(row["status"] == "not_run" for row in rows[1:])


def test_unavailable_engine_is_not_a_pass():
    def run(scenario, profile):
        if profile.startswith("webkit:"):
            raise contract.ScenarioUnavailable()
        return True
    rows = contract.collect_case_results(run, check_integrity=lambda: None)
    assert contract.validate_coverage(rows)
    assert all(row["status"] == "not_run" for row in rows if row["profileId"].startswith("webkit:"))


@pytest.mark.parametrize("bad", [None, {}, {"scenarioId": [], "profileId": "x"}])
def test_malformed_coverage_is_rejected(bad):
    assert contract.validate_coverage([bad])


@pytest.mark.parametrize("key,value", [("observerSupport", []), ("semanticResult", False),
                                       ("observedInteractionCount", 0), ("fcp", 0)])
def test_unobserved_zeroes_are_not_successful_performance_samples(key, value):
    rows = samples()
    rows[0][key] = value
    assert contract.validate_performance(rows, surface="nicegui")


def complete_report():
    groups = []
    for sid, surface in contract.performance_scenarios().items():
        rows = samples()
        for i, row in enumerate(rows):
            row.update(contract.PERFORMANCE_BUDGETS["public" if surface == "viewer" else surface])
            row.update(scenarioId=sid, contextId=f"{sid}:context:{i}", navigationId=f"{sid}:navigation:{i}")
        groups.append({"scenarioId": sid, "samples": rows})
    return {**valid_context(), "coverage": complete_coverage(),
            "coreInteractions": core_rows(), "performance": groups}


def test_complete_report_is_required_by_single_consumer_entrypoint():
    report = complete_report()
    assert not contract.validate_mobile_release_report(report, fingerprint="source")
    report["performance"] = report["performance"][:1]
    assert contract.validate_mobile_release_report(report, fingerprint="source")


@pytest.mark.parametrize("key", ["coverage", "coreInteractions", "performance"])
def test_green_summary_cannot_replace_raw_evidence(key):
    report = complete_report()
    report[key] = {"status": "pass", "p75": 0}
    assert contract.validate_mobile_release_report(report, fingerprint="source")


def test_core_recomputes_long_task_instead_of_trusting_summary():
    rows = core_rows()
    rows[0]["tasks"] = [{"startMs": 10, "durationMs": 76}]
    assert contract.validate_core_interactions(rows)


def test_task_crossing_window_start_is_contaminated_even_with_zero_summary():
    rows = core_rows()
    rows[0]["tasks"] = [{"startMs": -70, "durationMs": 76}]
    assert contract.validate_core_interactions(rows)


@pytest.mark.parametrize("declaration", ['@ui.page(path="/new")', '@ui.page(UNKNOWN_ROUTE)'])
def test_route_registration_cannot_silently_escape_the_manifest(tmp_path, declaration):
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "page.py").write_text(f"{declaration}\ndef page(): pass\n")
    with pytest.raises(ValueError):
        contract.assert_registered_routes(tmp_path)


@pytest.mark.parametrize("error", [OSError, ValueError, AssertionError])
def test_unreadable_integrity_stops_before_any_gesture(error):
    gestures = []
    def integrity():
        raise error("private diagnostics")
    rows = contract.collect_case_results(lambda *args: gestures.append(args), check_integrity=integrity)
    assert not gestures
    assert rows[0]["status"] == "error"
    assert all(row["status"] == "not_run" for row in rows[1:])


@pytest.mark.parametrize("mutation", ["warm", "context", "navigation", "status", "lcp", "fractional"])
def test_cold_samples_need_independent_successful_measured_navigations(mutation):
    rows = samples()
    if mutation == "warm":
        rows[0]["appliedProfile"]["cacheDisabled"] = False
    elif mutation in {"context", "navigation"}:
        rows[0][mutation + "Id"] = rows[1][mutation + "Id"]
    elif mutation == "status":
        rows[0]["navigationStatus"] = 503
    elif mutation == "lcp":
        rows[0]["lcpEntryCount"] = 0
    else:
        rows[0]["requests"] = 0.5
    assert contract.validate_performance(rows, surface="nicegui")


def test_boolean_schema_and_huge_numeric_input_fail_closed():
    report = complete_report()
    report["schemaVersion"] = True
    assert contract.validate_mobile_release_report(report, fingerprint="source")
    rows = samples()
    rows[0]["lcp"] = 10 ** 10000
    assert contract.validate_performance(rows, surface="nicegui")


@pytest.mark.parametrize("mutation", ["copied", "mislabeled"])
def test_other_target_cannot_reuse_dashboard_measurement(mutation):
    report = complete_report()
    if mutation == "copied":
        copied = deepcopy(report["performance"][0]["samples"])
        for sample in copied:
            sample["scenarioId"] = report["performance"][1]["scenarioId"]
        report["performance"][1]["samples"] = copied
    else:
        report["performance"][0]["samples"][0]["scenarioId"] = "public:entrance"
    assert contract.validate_mobile_release_report(report, fingerprint="source")


@pytest.mark.parametrize("state", [None, {}, {"longtask": "failed"}, {"longtask": "not-started"}])
def test_supported_but_unstarted_observer_is_not_evidence(state):
    rows = samples()
    rows[0]["observerState"] = state
    assert contract.validate_performance(rows, surface="nicegui")


def test_numeric_cache_flag_does_not_masquerade_as_boolean():
    report = complete_report()
    report["profile"]["cacheDisabled"] = 1
    assert contract.validate_mobile_release_report(report, fingerprint="source")
    rows = samples()
    rows[0]["appliedProfile"]["cacheDisabled"] = 1
    assert contract.validate_performance(rows, surface="nicegui")
