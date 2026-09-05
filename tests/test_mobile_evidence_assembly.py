"""Fictional collector tests, never browser/release acceptance evidence."""

from copy import deepcopy
import json

import pytest

from scripts import mobile_verification_contract as contract
from scripts.mobile_evidence_collector import MobileEvidenceCollector, PRODUCERS, assemble_report
from tests.test_mobile_verification_contract import complete_report


@pytest.mark.parametrize("failure", [AssertionError, RuntimeError, contract.ScenarioUnavailable])
def test_failed_gesture_still_checks_source_before_any_later_gesture(failure):
    visited = []
    boundaries = []

    def integrity():
        boundaries.append(len(visited))
        if visited:
            raise contract.VerificationIntegrityError("private fixture changed")

    def run(scenario, profile):
        visited.append((scenario.id, profile))
        raise failure("private browser diagnostic")

    rows = contract.collect_case_results(run, check_integrity=integrity)
    assert boundaries == [0, 1]
    assert len(visited) == 1
    assert rows[0]["status"] == "error" and rows[0]["reason"] == "integrity-stop"
    assert all(row["status"] == "not_run" for row in rows[1:])
    assert "private" not in json.dumps(rows)


def fixture():
    report = complete_report()
    report["sourceFingerprint"] = "c" * 64
    for row in report["lifecycle"]:
        row["sourceFingerprint"] = report["sourceFingerprint"]
    return report


def complete_fragments():
    report = fixture()
    collectors = {name: MobileEvidenceCollector(report, name) for name in PRODUCERS}
    for collector in collectors.values():
        collector.tool_versions = {"browser": "fictional-test-version"}
        collector.fixture_ids = [f"fictional:{collector.producer}"]
        collector.run_cases(lambda *_: True, check_integrity=lambda: None)
    for group in report["performance"]:
        surface = contract.performance_scenarios()[group["scenarioId"]]
        producer = "nicegui-chromium" if surface == "nicegui" else "public-viewer"
        collectors[producer].record_performance(group["scenarioId"], group["samples"])
    for row in report["coreInteractions"]:
        collectors["nicegui-chromium"].record_core(row)
    for row in report["lifecycle"]:
        collectors["nicegui-chromium"].record_lifecycle(row)
    return [collector.fragment() for collector in collectors.values()]


def test_producers_partition_complete_source_owned_matrix():
    keys = [key for name in PRODUCERS for key in MobileEvidenceCollector(fixture(), name).definitions]
    assert len(keys) == len(set(keys))
    assert set(keys) == contract.expected_cases()


def test_complete_v2_observations_satisfy_consumer_without_changing_budgets():
    report = assemble_report(fixture(), complete_fragments())
    assert report["status"] == "pass", report["validationErrors"]
    assert not contract.validate_mobile_release_report(report, fingerprint="c" * 64)
    assert len(report["lifecycle"]) == 8


def test_caller_cannot_inject_missing_observations_through_context():
    report = assemble_report(fixture(), [])  # Contains otherwise complete raw arrays!
    assert report["status"] == "fail"
    assert len(report["coverage"]) == len(contract.expected_cases())
    assert all(row["status"] == "not_run" for row in report["coverage"])
    assert report["lifecycle"] == report["coreInteractions"] == report["performance"] == []


def test_numeric_true_cannot_be_relabelled_as_measured_cold_profile():
    context = fixture()
    context["profile"]["cacheDisabled"] = 1
    with pytest.raises(ValueError, match="contract"):
        assemble_report(context, [])


def test_failed_case_cannot_copy_arbitrary_assertion_text_into_aggregate():
    collector = MobileEvidenceCollector(fixture(), "nicegui-chromium")
    (scenario_id, profile), _ = next(iter(collector.definitions.items()))
    with pytest.raises(ValueError, match="assertion"):
        collector.record_case({"scenarioId": scenario_id, "profileId": profile,
                               "status": "fail", "reason": "assertion-failed",
                               "readyAssertion": "private fixture payload"})


@pytest.mark.parametrize("field", ["runId", "fixtureId", "sourceCommit", "sourceTree", "sourceFingerprint", "sourceDirty"])
def test_mixed_source_or_run_rejected(field):
    fragments = complete_fragments()
    fragments[0]["context"][field] = True if field == "sourceDirty" else "d" * (64 if field == "sourceFingerprint" else 40)
    with pytest.raises(ValueError, match="drift"):
        assemble_report(fixture(), fragments)


@pytest.mark.parametrize("field,value", [("fragmentVersion", 1), ("fragmentVersion", True),
    ("schemaVersion", 1), ("schemaVersion", True), ("contractFingerprint", "old"), ("integrityStopped", 0)])
def test_old_or_malformed_fragment_is_not_relabelled(field, value):
    fragments = complete_fragments()
    fragments[0][field] = value
    with pytest.raises(ValueError, match="drift"):
        assemble_report(fixture(), fragments)


@pytest.mark.parametrize("defect", ["missing", "warm", "failed", "short", "over", "source", "reused"])
def test_cold_lifecycle_failures_survive_assembly_and_cannot_pass(defect):
    fragments = complete_fragments()
    rows = fragments[0]["lifecycle"]
    if defect == "missing":
        rows.pop()
    elif defect == "warm":
        rows[0]["baselineKind"] = "after-first-mount"
    elif defect == "failed":
        rows[0]["status"] = "fail"
    elif defect == "short":
        rows[0]["iterations"].pop()
    elif defect == "over":
        rows[0]["after"]["domNodes"] += 101
        rows[0]["growth"] = {"domNodes": 0}
    elif defect == "source":
        rows[0]["sourceFingerprint"] = "d" * 64
        with pytest.raises(ValueError, match="identity"):
            assemble_report(fixture(), fragments)
        return
    else:
        rows[0]["contextId"] = fragments[0]["performance"][0]["samples"][0]["contextId"]
        for phase in ("before", "after"):
            rows[0][phase]["contextId"] = rows[0]["contextId"]
    report = assemble_report(fixture(), fragments)
    assert report["status"] == "fail"
    assert len(report["lifecycle"]) == len(rows)
    assert report["lifecycle"][0]["after"] == rows[0]["after"]


@pytest.mark.parametrize("category", ["coverage", "performance", "coreInteractions", "lifecycle"])
def test_duplicate_and_unowned_evidence_cannot_overwrite(category):
    fragments = complete_fragments()
    fragments[0][category].append(deepcopy(fragments[0][category][0]))
    with pytest.raises(ValueError, match="duplicate"):
        assemble_report(fixture(), fragments)
    fragments = complete_fragments()
    fragments[1][category].append(deepcopy(fragments[0][category][0]))
    with pytest.raises(ValueError, match="unowned"):
        assemble_report(fixture(), fragments)


def test_no_best_sample_selection_or_green_failure_flag():
    fragments = complete_fragments()
    rows = fragments[0]["performance"][0]["samples"]
    rows[-1].update(status="fail", semanticResult=True, fcp=9000)
    report = assemble_report(fixture(), fragments)
    assert report["status"] == "fail"
    retained = report["performance"][0]["samples"]
    assert len(retained) == 5 and retained[-1]["fcp"] == 9000
    assert retained[-1]["semanticResult"] is False
    assert retained[-1]["observedSemanticResult"] is True


@pytest.mark.parametrize("field,value", [("evidenceKind", "diagnostic"), ("sourceDirty", True)])
def test_diagnostic_or_dirty_observations_cannot_certify_release(field, value):
    context, fragments = fixture(), complete_fragments()
    context[field] = value
    for fragment in fragments:
        fragment["context"][field] = value
    assert assemble_report(context, fragments)["status"] == "fail"


@pytest.mark.parametrize("metadata", ["fixtureIds", "toolVersions"])
def test_missing_observed_producer_metadata_invalidates_green_cases(metadata):
    fragments = complete_fragments()
    fragments[1][metadata] = [] if metadata == "fixtureIds" else {}
    report = assemble_report(fixture(), fragments)
    assert report["status"] == "fail"
    assert any(row["reason"] == "fixture-or-engine-unavailable"
               for row in report["coverage"] if row["status"] == "error")


def test_failure_continues_owned_cases_and_independent_producers_but_integrity_stops():
    visited = []
    collector = MobileEvidenceCollector(fixture(), "nicegui-chromium")

    def run(scenario, profile):
        visited.append((scenario.id, profile))
        if len(visited) == 1:
            raise AssertionError("private student payload")
        return True

    collector.run_cases(run, check_integrity=lambda: None)
    assert len(visited) == len(collector.definitions)
    assert next(iter(collector.coverage.values()))["status"] == "fail"
    assert "private" not in json.dumps(collector.fragment())
    fragments = complete_fragments()
    fragments[0]["integrityStopped"] = True  # Even after a final green gesture.
    report = assemble_report(fixture(), fragments)
    assert report["status"] == "fail"
    assert all(row["status"] != "pass" for row in report["coverage"])
    assert contract.validate_mobile_release_report(report, fingerprint="c" * 64)


def test_fragment_is_detached_exclusively_created_and_source_bound(tmp_path):
    from nicegui_app.release_evidence import RELEASE_SOURCE_FILES
    from scripts import mobile_evidence_collector
    from pathlib import Path

    assert Path(mobile_evidence_collector.__file__).resolve() in RELEASE_SOURCE_FILES
    collector = MobileEvidenceCollector(fixture(), "nicegui-chromium")
    row = fixture()["lifecycle"][0]
    collector.record_lifecycle(row)
    row["after"]["domNodes"] = 999999
    fragment = collector.fragment()
    assert fragment["lifecycle"][0]["after"]["domNodes"] == 500
    fragment["lifecycle"].clear()
    path = tmp_path / "immutable.json"
    collector.write_fragment(path)
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        collector.write_fragment(path)
    assert path.read_bytes() == original
    assert len(json.loads(original)["lifecycle"]) == 1
