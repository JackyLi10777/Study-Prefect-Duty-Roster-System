"""Lossless, source-bound assembly of independent mobile evidence producers.

This module does not run browsers or grant release approval. Runners supply
observations; the v2 contract recomputes completeness and budgets from raw data.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping

from scripts import mobile_verification_contract as contract

FRAGMENT_VERSION = 2
PRODUCERS = ("nicegui-chromium", "workbench-webkit", "public-viewer")
IDENTITY_KEYS = ("runId", "fixtureId", "evidenceKind", "sourceCommit", "sourceTree",
                 "sourceFingerprint", "sourceDirty")
METADATA_KEYS = ("browserEngine", "browserVersion", "os", "toolVersions")
REASONS = {"assertion-failed", "runner-error", "integrity-stop",
           "fixture-or-engine-unavailable", "not-observed"}


def _identity(context: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(context, Mapping) or any(key not in context for key in IDENTITY_KEYS):
        raise ValueError("Missing evidence identity")
    if type(context["sourceDirty"]) is not bool:
        raise ValueError("sourceDirty must be explicit")
    if context["evidenceKind"] not in {"release", "diagnostic"}:
        raise ValueError("Unknown evidence kind")
    for key in IDENTITY_KEYS[:-1]:
        if not isinstance(context[key], str) or not context[key].strip():
            raise ValueError("Missing evidence identity")
    for key, size in (("sourceCommit", 40), ("sourceTree", 40), ("sourceFingerprint", 64)):
        if not re.fullmatch(rf"[0-9a-f]{{{size}}}", context[key]):
            raise ValueError("Invalid source identity")
    return deepcopy({key: context[key] for key in IDENTITY_KEYS})


def _owned_cases(producer: str) -> dict[tuple[str, str], contract.Scenario]:
    if producer not in PRODUCERS:
        raise ValueError("Unknown evidence producer")
    return {(scenario.id, profile): scenario for scenario in contract.scenarios()
            for profile in contract.required_profiles(scenario)
            if (scenario.surface in {"public", "viewer"} if producer == "public-viewer"
                else scenario.surface == "workbench" and profile.startswith(
                    "chromium:" if producer == "nicegui-chromium" else "webkit:"))}


def _raw(record: Mapping[str, Any], identity: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ValueError("Malformed raw observation")
    for key in IDENTITY_KEYS:
        if key in record and (record[key] != identity[key] or type(record[key]) is not type(identity[key])):
            raise ValueError("Raw observation contradicts evidence identity")
    row = deepcopy(dict(record))
    if "status" in row and row["status"] != "pass":
        # Preserve the measured values and failed status, including a runner's
        # contradictory green flag, but never let it satisfy the consumer.
        row.setdefault("observedSemanticResult", row.get("semanticResult"))
        row["semanticResult"] = False
    return row


class MobileEvidenceCollector:
    def __init__(self, context: Mapping[str, Any], producer: str) -> None:
        self.context = _identity(context)
        self.producer = producer
        self.definitions = _owned_cases(producer)
        self.coverage: dict[tuple[str, str], dict[str, Any]] = {}
        self.performance: dict[str, dict[str, Any]] = {}
        self.core: dict[tuple[str, int], dict[str, Any]] = {}
        self.lifecycle: dict[tuple[str, str], dict[str, Any]] = {}
        self.tool_versions: dict[str, str] = {}
        self.fixture_ids: list[str] = []
        self.integrity_stopped = False

    def record_case(self, record: Mapping[str, Any]) -> None:
        row = _raw(record, self.context)
        key = (row.get("scenarioId"), row.get("profileId"))
        if any(not isinstance(value, str) for value in key) or key not in self.definitions or key in self.coverage:
            raise ValueError("Unknown, unowned or duplicate case")
        definition = self.definitions[key]
        status, reason = row.get("status"), row.get("reason")
        if status not in {"pass", "fail", "error", "not_run"} or reason not in REASONS | {None}:
            raise ValueError("Use safe case status/reason codes")
        for field, expected in (("readyAssertion", definition.ready_assertion),
                                ("resultAssertion", definition.result_assertion)):
            if field in row and row[field] != expected:
                raise ValueError("Use source-owned assertion identities")
        if status == "pass" and (self.integrity_stopped or reason is not None
                or row.get("readyAssertion") != definition.ready_assertion
                or row.get("resultAssertion") != definition.result_assertion):
            raise ValueError("Passing case requires both observed assertions")
        self.coverage[key] = {field: row[field] for field in
                             ("scenarioId", "profileId", "status", "reason", "readyAssertion", "resultAssertion")
                             if field in row}
        self.integrity_stopped |= reason == "integrity-stop"

    def run_cases(self, runner: Callable[[contract.Scenario, str], bool], *,
                  check_integrity: Callable[[], None]) -> None:
        for (scenario_id, profile), scenario in self.definitions.items():
            if (scenario_id, profile) in self.coverage:
                raise ValueError("Cannot rerun observed cases")
            row = ({"scenarioId": scenario_id, "profileId": profile, "status": "not_run",
                    "reason": "integrity-stop"} if self.integrity_stopped else
                   contract.observe_case(runner, scenario, profile, check_integrity=check_integrity))
            self.record_case(row)

    def record_performance(self, scenario_id: str, samples: list[Mapping[str, Any]]) -> None:
        surface = contract.performance_scenarios().get(scenario_id)
        if (not isinstance(samples, list) or scenario_id in self.performance or not (
                self.producer == "nicegui-chromium" and surface == "nicegui"
                or self.producer == "public-viewer" and surface in {"public", "viewer"})):
            raise ValueError("Unknown, unowned or duplicate performance target")
        rows = [_raw(row, self.context) for row in samples]
        if any(row.get("scenarioId") != scenario_id for row in rows):
            raise ValueError("Sample belongs to a different target")
        self.performance[scenario_id] = {"scenarioId": scenario_id, "samples": rows}

    def record_core(self, record: Mapping[str, Any]) -> None:
        row = _raw(record, self.context)
        action, iteration = row.get("action"), row.get("iteration")
        if (self.producer != "nicegui-chromium" or not isinstance(action, str)
                or type(iteration) is not int
                or not 1 <= iteration <= contract.CORE_REPETITIONS.get(action, 0)
                or (action, iteration) in self.core):
            raise ValueError("Unknown, unowned or duplicate core interaction")
        self.core[action, iteration] = row

    def record_lifecycle(self, record: Mapping[str, Any]) -> None:
        row = _raw(record, self.context)
        key = (row.get("target"), row.get("mode"))
        if (self.producer != "nicegui-chromium" or any(not isinstance(value, str) for value in key)
                or key[0] not in contract.LIFECYCLE_TARGETS or key[1] not in contract.LIFECYCLE_MODES
                or key in self.lifecycle):
            raise ValueError("Unknown, unowned or duplicate lifecycle observation")
        # Keep failed/partial/warm observations intact: validation, not assembly,
        # must explain why they cannot certify a cold first-opening budget.
        self.lifecycle[key] = row

    def fragment(self) -> dict[str, Any]:
        return deepcopy({"fragmentVersion": FRAGMENT_VERSION, "schemaVersion": contract.CONTRACT_VERSION,
                         "contractFingerprint": contract.contract_fingerprint(), "producer": self.producer,
                         "context": self.context, "toolVersions": self.tool_versions,
                         "fixtureIds": self.fixture_ids, "integrityStopped": self.integrity_stopped,
                         "coverage": list(self.coverage.values()), "performance": list(self.performance.values()),
                         "coreInteractions": list(self.core.values()), "lifecycle": list(self.lifecycle.values())})

    def write_fragment(self, path: Path) -> None:
        payload = json.dumps(self.fragment(), ensure_ascii=False, indent=2, allow_nan=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as output:
            output.write(payload)


def assemble_report(context: Mapping[str, Any], fragments: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Missing observations remain missing; caller summaries cannot fill gaps."""
    identity = _identity(context)
    fixed = {"schemaVersion": contract.CONTRACT_VERSION, "contractFingerprint": contract.contract_fingerprint(),
             "profile": deepcopy(contract.PERFORMANCE_PROFILE)}
    for key, value in fixed.items():
        if key in context and (type(context[key]) is not type(value) or context[key] != value):
            raise ValueError("Caller contradicts source-owned contract")
    if "profile" in context and context["profile"].get("cacheDisabled") is not True:
        raise ValueError("Caller contradicts the source-owned cold cache contract")
    report = {**identity, **fixed, **deepcopy({key: context[key] for key in METADATA_KEYS if key in context})}
    coverage, performance, core, lifecycle = {}, [], [], []
    producers, fixtures, versions = set(), {}, {}
    stopped = False
    for fragment in fragments:
        if not isinstance(fragment, Mapping):
            raise ValueError("Malformed evidence fragment")
        producer = fragment.get("producer")
        if not isinstance(producer, str) or producer not in PRODUCERS or producer in producers:
            raise ValueError("Unknown or duplicate evidence producer")
        if (type(fragment.get("fragmentVersion")) is not int or fragment["fragmentVersion"] != FRAGMENT_VERSION
                or type(fragment.get("schemaVersion")) is not int
                or fragment["schemaVersion"] != contract.CONTRACT_VERSION
                or fragment.get("contractFingerprint") != contract.contract_fingerprint()
                or _identity(fragment.get("context", {})) != identity
                or type(fragment.get("integrityStopped")) is not bool):
            raise ValueError("Evidence context/version drift")
        producers.add(producer)
        collector = MobileEvidenceCollector(identity, producer)
        for key, record in (("coverage", collector.record_case), ("coreInteractions", collector.record_core),
                            ("lifecycle", collector.record_lifecycle)):
            if not isinstance(fragment.get(key), list):
                raise ValueError("Missing fragment evidence category")
            for row in fragment[key]:
                record(row)
        if not isinstance(fragment.get("performance"), list):
            raise ValueError("Missing performance category")
        for group in fragment["performance"]:
            if not isinstance(group, Mapping):
                raise ValueError("Malformed performance group")
            collector.record_performance(group.get("scenarioId"), group.get("samples"))
        tools, ids = fragment.get("toolVersions"), fragment.get("fixtureIds")
        metadata_valid = (isinstance(tools, dict) and bool(tools)
                          and all(isinstance(k, str) and k.strip() and isinstance(v, str) and v.strip()
                                  for k, v in tools.items())
                          and isinstance(ids, list) and bool(ids)
                          and all(isinstance(i, str) and i.strip() for i in ids) and len(set(ids)) == len(ids))
        if not metadata_valid:
            for row in collector.coverage.values():
                if row["status"] == "pass":
                    row.update(status="error", reason="fixture-or-engine-unavailable")
        else:
            fixtures[producer], versions[producer] = deepcopy(ids), deepcopy(tools)
        coverage.update(collector.coverage)
        performance.extend(collector.performance.values())
        core.extend(collector.core.values())
        lifecycle.extend(collector.lifecycle.values())
        stopped |= fragment["integrityStopped"] or collector.integrity_stopped
    for key in sorted(contract.expected_cases()):
        coverage.setdefault(key, {"scenarioId": key[0], "profileId": key[1],
                                  "status": "not_run", "reason": "not-observed"})
    if stopped:
        for row in coverage.values():
            if row["status"] == "pass":
                row.update(status="error", reason="integrity-stop")
    report.update(coverage=[coverage[key] for key in sorted(coverage)], performance=performance,
                  coreInteractions=core, lifecycle=lifecycle, producers=sorted(producers),
                  producerFixtures=fixtures, producerToolVersions=versions, integrityStopped=stopped)
    errors = contract.validate_mobile_release_report(report, fingerprint=identity["sourceFingerprint"])
    if stopped:
        errors.append("integrity-stop invalidates the complete run")
    report.update(status="fail" if errors else "pass", validationErrors=errors)
    return report
