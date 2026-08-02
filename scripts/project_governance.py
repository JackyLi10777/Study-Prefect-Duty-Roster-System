"""Validate the documentation, release-status, and module-boundary contracts.

The repository used to repeat mutable production identifiers across many large
guides.  This module keeps one machine-readable release state, renders the
human status and consumer notices from it, and rejects dependency directions
that would push persistence or presentation knowledge into the wrong layer.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from typing import Iterable, Mapping, Sequence
from urllib.parse import unquote


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = Path("docs/documentation-manifest.json")
ARCHITECTURE_PATH = Path("docs/architecture/module-boundaries.json")
STATUS_START = "<!-- SING_YIN_CURRENT_STATUS:START -->"
STATUS_END = "<!-- SING_YIN_CURRENT_STATUS:END -->"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_COMMIT = re.compile(r"[0-9a-f]{40}")
_RELEASE = re.compile(r"v\d+\.\d+\.\d+-rc\.\d+")
_MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
_MUTABLE_CURRENT_RELEASE_CLAIM = re.compile(
    r"\bcurrent(?:\s+(?:production|origin|runtime))?\s+rc\d+\b"
    r"|(?:目前|現行)(?:正式)?\s*rc\d+\b",
    re.IGNORECASE,
)
_ITERATION_ID = re.compile(r"ITR-\d{3}")
_ITERATION_STATES = frozenset(
    {"Proposed", "Ready", "Active", "Conditional", "Blocked", "Done"}
)
_ACTIONABLE_ITERATION_STATES = frozenset({"Proposed", "Ready", "Active", "Blocked"})
_ITERATION_PRIORITIES = frozenset({"L1", "L2", "L3"})
_RISK_STATES = frozenset({"Tracked", "Managed", "Resolved", "Historical"})
_RISK_TRACKING = re.compile(r"(?:`ITR-\d{3}`)(?:,\s*`ITR-\d{3}`)*|—")
_RISK_TABLE_HEADING = "## Known Issues and Risks"
_ITERATION_TABLE_HEADING = "## 目前佇列 / Current queue"


@dataclass(frozen=True, order=True)
class ContractViolation:
    code: str
    path: str
    message: str


def mutable_current_release_claims(text: str) -> tuple[str, ...]:
    """Return version-bound current-state wording that belongs in status blocks.

    Historical phrases such as ``live rc27`` are deliberately excluded: they
    may be valid contemporaneous evidence.  A guide saying ``current rc45`` is
    different because it silently becomes false after the next deployment.
    """

    return tuple(match.group(0) for match in _MUTABLE_CURRENT_RELEASE_CLAIM.finditer(text))


def _markdown_table_after_heading(
    text: str, heading: str
) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    """Return one simple Markdown table immediately following an exact heading."""

    lines = text.splitlines()
    try:
        cursor = lines.index(heading) + 1
    except ValueError as error:
        raise ValueError(f"missing heading {heading!r}") from error
    while cursor < len(lines) and not lines[cursor].strip():
        cursor += 1
    if cursor + 1 >= len(lines):
        raise ValueError(f"missing table after {heading!r}")

    def cells(line: str) -> tuple[str, ...]:
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            raise ValueError(f"expected a pipe-delimited table after {heading!r}")
        return tuple(cell.strip() for cell in stripped[1:-1].split("|"))

    header = cells(lines[cursor])
    separator = cells(lines[cursor + 1])
    if len(separator) != len(header) or any(
        re.fullmatch(r":?-{3,}:?", cell) is None for cell in separator
    ):
        raise ValueError(f"invalid table separator after {heading!r}")

    rows: list[tuple[str, ...]] = []
    cursor += 2
    while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
        row = cells(lines[cursor])
        if len(row) != len(header):
            raise ValueError(f"table row has the wrong width after {heading!r}")
        rows.append(row)
        cursor += 1
    if not rows:
        raise ValueError(f"table after {heading!r} must contain at least one row")
    return header, tuple(rows)


def iteration_risk_violations(root: Path) -> tuple[ContractViolation, ...]:
    """Require every actionable project risk to resolve to owned iteration work."""

    project_status_path = root / "PROJECT_STATUS.md"
    iteration_path = root / "docs/ITERATION_REGISTER.md"
    violations: list[ContractViolation] = []
    for path, label in (
        (project_status_path, "project risk register"),
        (iteration_path, "iteration register"),
    ):
        if not path.is_file():
            violations.append(
                ContractViolation(
                    "iteration.missing-document",
                    str(path),
                    f"{label} does not exist",
                )
            )
    if violations:
        return tuple(sorted(violations))

    try:
        iteration_header, iteration_rows = _markdown_table_after_heading(
            iteration_path.read_text(encoding="utf-8"), _ITERATION_TABLE_HEADING
        )
        risk_header, risk_rows = _markdown_table_after_heading(
            project_status_path.read_text(encoding="utf-8"), _RISK_TABLE_HEADING
        )
    except ValueError as error:
        return (
            ContractViolation(
                "iteration.table-schema",
                "PROJECT_STATUS.md / docs/ITERATION_REGISTER.md",
                str(error),
            ),
        )

    expected_iteration_header = (
        "ID",
        "Priority",
        "Outcome",
        "Owning module/document",
        "State",
        "Evidence needed to close",
    )
    expected_risk_header = ("Risk", "State", "Tracking", "Mitigation")
    if iteration_header != expected_iteration_header:
        violations.append(
            ContractViolation(
                "iteration.table-schema",
                "docs/ITERATION_REGISTER.md",
                f"expected columns {expected_iteration_header!r}",
            )
        )
    if risk_header != expected_risk_header:
        violations.append(
            ContractViolation(
                "risk.table-schema",
                "PROJECT_STATUS.md",
                f"expected columns {expected_risk_header!r}",
            )
        )
    if violations:
        return tuple(sorted(violations))

    iteration_states: dict[str, str] = {}
    previous_priority = 0
    for raw_id, priority, _outcome, _owner, state, _evidence in iteration_rows:
        normalized_id = raw_id.strip("` ")
        iteration_id = (
            normalized_id if _ITERATION_ID.fullmatch(normalized_id) else ""
        )
        if not iteration_id or raw_id not in {iteration_id, f"`{iteration_id}`"}:
            violations.append(
                ContractViolation(
                    "iteration.invalid-id",
                    "docs/ITERATION_REGISTER.md",
                    f"iteration ID must be one exact ITR-NNN value: {raw_id!r}",
                )
            )
        elif iteration_id in iteration_states:
            violations.append(
                ContractViolation(
                    "iteration.duplicate-id",
                    "docs/ITERATION_REGISTER.md",
                    f"iteration ID is duplicated: {iteration_id}",
                )
            )
        else:
            iteration_states[iteration_id] = state
        if state not in _ITERATION_STATES:
            violations.append(
                ContractViolation(
                    "iteration.invalid-state",
                    "docs/ITERATION_REGISTER.md",
                    f"{iteration_id or raw_id} uses unsupported state {state!r}",
                )
            )
        if priority not in _ITERATION_PRIORITIES:
            violations.append(
                ContractViolation(
                    "iteration.invalid-priority",
                    "docs/ITERATION_REGISTER.md",
                    f"{iteration_id or raw_id} uses unsupported priority {priority!r}",
                )
            )
        else:
            priority_rank = int(priority[1])
            if priority_rank < previous_priority:
                violations.append(
                    ContractViolation(
                        "iteration.priority-order",
                        "docs/ITERATION_REGISTER.md",
                        "iterations must remain ordered L1, then L2, then L3",
                    )
                )
            previous_priority = priority_rank

    tracked_iteration_ids: set[str] = set()
    for risk, state, tracking, _mitigation in risk_rows:
        tracked_ids = tuple(_ITERATION_ID.findall(tracking))
        if _RISK_TRACKING.fullmatch(tracking) is None:
            violations.append(
                ContractViolation(
                    "risk.invalid-tracking",
                    "PROJECT_STATUS.md",
                    f"risk tracking must be backticked ITR references or an em dash: {risk}",
                )
            )
        if state not in _RISK_STATES:
            violations.append(
                ContractViolation(
                    "risk.invalid-state",
                    "PROJECT_STATUS.md",
                    f"risk {risk!r} uses unsupported state {state!r}",
                )
            )
        if state == "Tracked" and not tracked_ids:
            violations.append(
                ContractViolation(
                    "risk.untracked",
                    "PROJECT_STATUS.md",
                    f"tracked risk has no ITR reference: {risk}",
                )
            )
        elif state == "Tracked":
            tracked_iteration_ids.update(tracked_ids)
        elif state != "Tracked" and tracked_ids:
            violations.append(
                ContractViolation(
                    "risk.unexpected-tracking",
                    "PROJECT_STATUS.md",
                    f"only Tracked risks may reference active iterations: {risk}",
                )
            )
        for iteration_id in tracked_ids:
            if iteration_id not in iteration_states:
                violations.append(
                    ContractViolation(
                        "risk.unknown-iteration",
                        "PROJECT_STATUS.md",
                        f"risk {risk!r} references missing {iteration_id}",
                    )
                )
            elif iteration_states[iteration_id] == "Done":
                violations.append(
                    ContractViolation(
                        "risk.closed-iteration",
                        "PROJECT_STATUS.md",
                        f"tracked risk {risk!r} references completed {iteration_id}",
                    )
                )
    for iteration_id, state in iteration_states.items():
        if (
            state in _ACTIONABLE_ITERATION_STATES
            and iteration_id not in tracked_iteration_ids
        ):
            violations.append(
                ContractViolation(
                    "iteration.unlinked-risk",
                    "docs/ITERATION_REGISTER.md",
                    f"actionable {iteration_id} is not referenced by a Tracked project risk",
                )
            )
    return tuple(sorted(set(violations)))


def _read_json(path: Path) -> dict[str, object]:
    """Load a JSON object and reject non-object roots."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("the JSON root must be an object")
    return payload


def _mapping(value: object, name: str) -> Mapping[str, object]:
    """Require a nested status value to be an object."""

    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _string(value: object, name: str) -> str:
    """Require a non-empty status string while preserving its exact value."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _status_values(state: Mapping[str, object]) -> dict[str, object]:
    """Flatten the release-state schema for validation and deterministic rendering."""

    release = _mapping(state.get("release"), "release")
    gates = _mapping(release.get("formal_gates"), "release.formal_gates")
    database = _mapping(state.get("database"), "database")
    recovery = _mapping(state.get("recovery"), "recovery")
    origin = _mapping(state.get("origin"), "origin")
    worker = _mapping(state.get("worker"), "worker")
    predecessor = _mapping(
        state.get("historical_predecessor"), "historical_predecessor"
    )
    acceptance = _mapping(state.get("acceptance"), "acceptance")
    return {
        "observed_at": _string(state.get("observed_at"), "observed_at"),
        "state": _string(state.get("state"), "state"),
        "tag": _string(release.get("tag"), "release.tag"),
        "commit": _string(release.get("commit"), "release.commit"),
        "bundle": _string(release.get("bundle"), "release.bundle"),
        "file_count": release.get("source_file_count"),
        "fingerprint": _string(
            release.get("fingerprint_sha256"), "release.fingerprint_sha256"
        ),
        "gates_passed": gates.get("passed"),
        "gates_total": gates.get("total"),
        "alembic_head": _string(
            database.get("alembic_head"), "database.alembic_head"
        ),
        "restore_required": database.get("rollback_requires_compatible_restore"),
        "backup_file": _string(recovery.get("backup_file"), "recovery.backup_file"),
        "backup_sha": _string(
            recovery.get("backup_sha256"), "recovery.backup_sha256"
        ),
        "service": _string(origin.get("service"), "origin.service"),
        "origin_health": _string(origin.get("health"), "origin.health"),
        "readiness": _string(origin.get("readiness"), "origin.readiness"),
        "write_ready": origin.get("write_ready"),
        "maintenance": origin.get("maintenance"),
        "recovery_required": origin.get("recovery_required"),
        "pending_backups": origin.get("pending_backup_obligations"),
        "worker_version": _string(worker.get("version_id"), "worker.version_id"),
        "worker_source_changed": worker.get("source_changed_for_release"),
        "worker_traffic": worker.get("traffic_percent"),
        "worker_health": _string(worker.get("health"), "worker.health"),
        "predecessor": _string(
            predecessor.get("release"), "historical_predecessor.release"
        ),
        "rollback_mode": _string(
            predecessor.get("rollback_mode"),
            "historical_predecessor.rollback_mode",
        ),
        "automated_acceptance": _string(
            acceptance.get("automated"), "acceptance.automated"
        ),
        "human_acceptance": _string(
            acceptance.get("supervised_human"), "acceptance.supervised_human"
        ),
    }


def _status_schema_violations(
    state: Mapping[str, object], path: str
) -> list[ContractViolation]:
    """Return fail-closed release-state violations without mutating documents."""

    violations: list[ContractViolation] = []
    try:
        values = _status_values(state)
    except ValueError as error:
        return [ContractViolation("status.schema", path, str(error))]

    if state.get("schema_version") != 1:
        violations.append(
            ContractViolation("status.schema-version", path, "schema_version must be 1")
        )
    if values["state"] != "live":
        violations.append(
            ContractViolation("status.state", path, "state must be live for CURRENT_STATUS")
        )
    if not _RELEASE.fullmatch(str(values["tag"])):
        violations.append(
            ContractViolation("status.release-tag", path, "release.tag is malformed")
        )
    if not _COMMIT.fullmatch(str(values["commit"])):
        violations.append(
            ContractViolation(
                "status.commit",
                path,
                "release.commit must be 40 lowercase hex characters",
            )
        )
    for field in ("fingerprint", "backup_sha"):
        if not _SHA256.fullmatch(str(values[field])):
            violations.append(
                ContractViolation("status.sha256", path, f"{field} must be 64 lowercase hex characters")
            )
    if not isinstance(values["file_count"], int) or int(values["file_count"]) <= 0:
        violations.append(
            ContractViolation("status.file-count", path, "source_file_count must be positive")
        )
    if (
        not isinstance(values["gates_passed"], int)
        or not isinstance(values["gates_total"], int)
        or values["gates_passed"] != values["gates_total"]
    ):
        violations.append(
            ContractViolation("status.gates", path, "formal gates must be integer and fully passed")
        )
    if values["restore_required"] is not True:
        violations.append(
            ContractViolation(
                "status.rollback",
                path,
                "the migration-aware rollback requirement must remain explicit",
            )
        )
    if values["write_ready"] is not True or values["origin_health"] != "passed":
        violations.append(
            ContractViolation("status.origin", path, "live origin must record passed health and write readiness")
        )
    if (
        values["maintenance"] is not False
        or values["recovery_required"] is not False
        or values["pending_backups"] != 0
    ):
        violations.append(
            ContractViolation(
                "status.origin-obligations",
                path,
                "live origin must record no maintenance, recovery requirement, or pending backup obligation",
            )
        )
    if values["worker_traffic"] != 100 or values["worker_health"] != "passed":
        violations.append(
            ContractViolation("status.worker", path, "canonical Worker must record passed health and 100% traffic")
        )
    if not isinstance(values["worker_source_changed"], bool):
        violations.append(
            ContractViolation(
                "status.worker-source",
                path,
                "worker.source_changed_for_release must be a JSON Boolean",
            )
        )
    if values["human_acceptance"] not in {"pending", "passed"}:
        violations.append(
            ContractViolation("status.acceptance", path, "supervised_human must be pending or passed")
        )
    return violations


def render_status_block(
    state: Mapping[str, object], *, language: str, link: str
) -> str:
    """Render one generated bilingual consumer notice from release state."""

    values = _status_values(state)
    worker_source_changed = values["worker_source_changed"]
    if not isinstance(worker_source_changed, bool):
        raise ValueError(
            "worker.source_changed_for_release must be a JSON Boolean"
        )
    if language == "zh-Hant":
        worker_status = (
            "Worker 來源已更新，"
            if worker_source_changed
            else "Worker 來源沒有改動，"
        )
        notice = (
            f"> **已核實線上來源（{values['observed_at']}）：** Windows origin 正運行 clean annotated "
            f"`{values['tag']}`／`{values['commit']}` 的不可變 bundle；{values['file_count']}-file 指紋 "
            f"`{values['fingerprint']}` 通過 {values['gates_passed']}／{values['gates_total']} gate。"
            f"SQLite 位於 Alembic `{values['alembic_head']}`；正式備份 `{values['backup_file']}`／SHA-256 "
            f"`{values['backup_sha']}`、隔離還原、health、`writeReady=true`、`maintenance=false`、"
            f"`recoveryRequired=false` 及 `pendingBackups=0` 已核對。{worker_status}"
            f"canonical Worker `{values['worker_version']}` 維持 {values['worker_traffic']}% 流量且健康。"
            f"`{values['predecessor']}` 只屬歷史來源，migration `{values['alembic_head']}` 後不可作 code-only "
            f"rollback；須使用受控的相容資料庫還原。真人驗收仍為 `{values['human_acceptance']}`。"
            f"精確狀態及更新規則見[目前系統狀態]({link})。"
        )
    elif language == "en":
        worker_status = (
            "Worker source changed and was promoted; "
            if worker_source_changed
            else "Worker source did not change; "
        )
        notice = (
            f"> **Verified production truth ({values['observed_at']}):** the live Windows origin is clean annotated "
            f"`{values['tag']}` at `{values['commit']}` and runs an immutable bundle. Its {values['file_count']}-file "
            f"fingerprint `{values['fingerprint']}` passed {values['gates_passed']}/{values['gates_total']} gates. "
            f"SQLite is at Alembic `{values['alembic_head']}`; verified backup `{values['backup_file']}` with SHA-256 "
            f"`{values['backup_sha']}`, isolated restore, health, `writeReady=true`, `maintenance=false`, "
            f"`recoveryRequired=false`, and `pendingBackups=0` passed. {worker_status}"
            f"canonical Worker `{values['worker_version']}` remains healthy at {values['worker_traffic']}% "
            f"traffic. `{values['predecessor']}` is historical source evidence, not a code-only rollback after migration "
            f"`{values['alembic_head']}`; recovery requires the controlled compatible database restore. Supervised human "
            f"acceptance remains `{values['human_acceptance']}`. See [current system status]({link}) for the exact state "
            f"and update contract."
        )
    else:
        raise ValueError(f"unsupported status language: {language}")
    return f"{STATUS_START}\n{notice}\n{STATUS_END}"


def render_current_status(state: Mapping[str, object]) -> str:
    """Render the canonical human-readable status page deterministically."""

    values = _status_values(state)
    worker_source_changed = values["worker_source_changed"]
    if not isinstance(worker_source_changed, bool):
        raise ValueError(
            "worker.source_changed_for_release must be a JSON Boolean"
        )
    if values["human_acceptance"] == "passed":
        human = "已完成 / Passed"
    elif values["human_acceptance"] == "pending":
        human = "尚待完成 / Pending"
    else:
        human = "未通過（狀態無效） / Not passed (invalid state)"
    worker_source = (
        "source updated and promoted for this release"
        if worker_source_changed
        else "source unchanged for this release"
    )
    return (
        "<!-- Generated from current-release.json by scripts/project_governance.py. Do not edit by hand. -->\n"
        "# 目前系統狀態 / Current system status\n\n"
        f"> 最後核實 / Last verified: **{values['observed_at']}**. This page records observed release truth; "
        "a newer repository commit does not imply a newer production deployment.\n\n"
        "## 正式運行 / Live production\n\n"
        "| 項目 / Item | 已核實值 / Verified value |\n"
        "|---|---|\n"
        f"| 狀態 / State | `{values['state']}` |\n"
        f"| Release | `{values['tag']}` |\n"
        f"| Production source commit | `{values['commit']}` |\n"
        f"| Immutable bundle | `{values['bundle']}` |\n"
        f"| Source evidence | {values['file_count']} files; `{values['fingerprint']}`; "
        f"{values['gates_passed']}/{values['gates_total']} gates passed |\n"
        f"| Windows service | `{values['service']}`; health `{values['origin_health']}`; readiness "
        f"`{values['readiness']}`; `writeReady={str(values['write_ready']).lower()}`; "
        f"`maintenance={str(values['maintenance']).lower()}`; "
        f"`recoveryRequired={str(values['recovery_required']).lower()}`; "
        f"`pendingBackups={values['pending_backups']}` |\n"
        f"| Canonical Worker | `{values['worker_version']}`; {values['worker_traffic']}% traffic; "
        f"health `{values['worker_health']}`; {worker_source} |\n\n"
        "## 資料與復原 / Data and recovery\n\n"
        "| 項目 / Item | 已核實值 / Verified value |\n"
        "|---|---|\n"
        f"| Alembic head | `{values['alembic_head']}` |\n"
        f"| Verified backup | `{values['backup_file']}` |\n"
        f"| Backup SHA-256 | `{values['backup_sha']}` |\n"
        f"| Previous application source | `{values['predecessor']}` — historical only |\n"
        "| Rollback contract | Migration-aware controlled restore; never switch old code alone |\n\n"
        "## 驗收 / Acceptance\n\n"
        f"- Automated and release evidence: **{values['automated_acceptance']}**.\n"
        f"- Supervised Head Study Prefect and teacher-advisor acceptance: **{human}**.\n"
        "- HTTP 200, health, or CI alone never substitutes for rendered workflow and human acceptance evidence.\n\n"
        "## 更新契約 / Update contract\n\n"
        "1. Update `current-release.json` only from observed deployment, recovery, and acceptance evidence.\n"
        "2. Run `python -X utf8 scripts/project_governance.py --write` to regenerate this page and every status notice.\n"
        "3. Run `python -X utf8 scripts/project_governance.py --check` and the staged verifier before push.\n"
        "4. Keep historical releases in `CHANGELOG.md` and evidence records; do not copy mutable current identifiers into ordinary guides.\n"
    )


def _all_imports(path: Path, root: Path) -> Iterable[str]:
    """Yield absolute import targets, resolving package-relative imports."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    relative = path.relative_to(root)
    package_parts = relative.parent.parts
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if not node.module:
                    continue
                module = node.module
            else:
                retained_parts = len(package_parts) - (node.level - 1)
                if retained_parts < 0:
                    continue
                resolved_parts = list(package_parts[:retained_parts])
                if node.module:
                    resolved_parts.extend(node.module.split("."))
                module = ".".join(resolved_parts)
            if module:
                yield module
            yield from (
                f"{module}.{alias.name}" if module else alias.name
                for alias in node.names
                if alias.name != "*"
            )


def architecture_violations(
    root: Path, contract: Mapping[str, object]
) -> tuple[ContractViolation, ...]:
    """Check declared Python dependency directions, including relative imports."""

    violations: list[ContractViolation] = []
    if contract.get("schema_version") != 1:
        violations.append(
            ContractViolation(
                "architecture.schema-version",
                ARCHITECTURE_PATH.as_posix(),
                "schema_version must be 1",
            )
        )
    rules = contract.get("rules")
    if not isinstance(rules, list):
        return tuple(
            violations
            + [
                ContractViolation(
                    "architecture.schema",
                    ARCHITECTURE_PATH.as_posix(),
                    "rules must be a list",
                )
            ]
        )
    for raw_rule in rules:
        if not isinstance(raw_rule, Mapping):
            violations.append(
                ContractViolation(
                    "architecture.schema",
                    ARCHITECTURE_PATH.as_posix(),
                    "every rule must be an object",
                )
            )
            continue
        rule_name = str(raw_rule.get("name") or "unnamed-rule")
        source_paths = raw_rule.get("source_paths")
        forbidden = raw_rule.get("forbidden_import_prefixes")
        if not isinstance(source_paths, list) or not isinstance(forbidden, list):
            violations.append(
                ContractViolation(
                    "architecture.schema",
                    ARCHITECTURE_PATH.as_posix(),
                    f"{rule_name} must define source_paths and forbidden_import_prefixes lists",
                )
            )
            continue
        for source_path in source_paths:
            candidate = root / str(source_path)
            if not candidate.exists():
                violations.append(
                    ContractViolation(
                        "architecture.missing-source",
                        str(source_path),
                        f"{rule_name} source path does not exist",
                    )
                )
                continue
            python_files = [candidate] if candidate.is_file() else sorted(candidate.rglob("*.py"))
            for python_file in python_files:
                relative = python_file.relative_to(root).as_posix()
                try:
                    imports = tuple(_all_imports(python_file, root))
                except (SyntaxError, UnicodeDecodeError) as error:
                    violations.append(
                        ContractViolation(
                            "architecture.unreadable-source",
                            relative,
                            f"{rule_name}: {error}",
                        )
                    )
                    continue
                for prefix in (str(item) for item in forbidden):
                    matched = next(
                        (
                            imported
                            for imported in imports
                            if imported == prefix or imported.startswith(prefix + ".")
                        ),
                        None,
                    )
                    if matched is not None:
                        violations.append(
                            ContractViolation(
                                "architecture.forbidden-import",
                                relative,
                                f"{rule_name} forbids import {matched!r} via {prefix!r}",
                            )
                        )
    return tuple(sorted(violations))


def _classified_paths(manifest: Mapping[str, object]) -> tuple[set[str], list[ContractViolation]]:
    """Collect explicit lifecycle classifications and report duplicates."""

    violations: list[ContractViolation] = []
    classified: set[str] = set()
    classes = manifest.get("document_classes")
    if not isinstance(classes, Mapping):
        return classified, [
            ContractViolation(
                "documentation.schema",
                MANIFEST_PATH.as_posix(),
                "document_classes must be an object",
            )
        ]
    for class_name, raw_paths in classes.items():
        if not isinstance(raw_paths, list):
            violations.append(
                ContractViolation(
                    "documentation.schema",
                    MANIFEST_PATH.as_posix(),
                    f"document class {class_name!r} must be a list",
                )
            )
            continue
        for raw_path in raw_paths:
            path = str(raw_path).replace("\\", "/")
            if path in classified:
                violations.append(
                    ContractViolation(
                        "documentation.duplicate-classification",
                        path,
                        "a document must have exactly one lifecycle class",
                    )
                )
            classified.add(path)
    return classified, violations


def _is_collection_member(path: str, collections: Mapping[str, object]) -> bool:
    """Return whether a document is governed through a declared collection."""

    return any(path == prefix or path.startswith(prefix.rstrip("/") + "/") for prefix in collections)


def _repository_markdown(root: Path) -> Iterable[str]:
    """Yield maintained Markdown while excluding dependency and build trees."""

    excluded_parts = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "build",
        "dist",
        "node_modules",
        "test-results",
        "venv",
    }
    for path in root.rglob("*.md"):
        relative = path.relative_to(root)
        if any(part in excluded_parts for part in relative.parts):
            continue
        yield relative.as_posix()


def _local_link_violations(root: Path, relative_path: str) -> list[ContractViolation]:
    """Check local Markdown targets without following external URLs."""

    path = root / relative_path
    violations: list[ContractViolation] = []
    text = path.read_text(encoding="utf-8")
    for raw_target in _MARKDOWN_LINK.findall(text):
        target = raw_target.strip().strip("<>")
        if not target or target.startswith(("#", "http://", "https://", "mailto:", "data:")):
            continue
        target = target.split(" ", 1)[0].split("#", 1)[0].split("?", 1)[0]
        if not target or "://" in target or "<" in target or ">" in target:
            continue
        resolved = (path.parent / unquote(target)).resolve()
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            violations.append(
                ContractViolation(
                    "documentation.link-outside-root",
                    relative_path,
                    f"local link escapes the repository: {raw_target}",
                )
            )
            continue
        if not resolved.exists():
            violations.append(
                ContractViolation(
                    "documentation.broken-link",
                    relative_path,
                    f"local link does not exist: {raw_target}",
                )
            )
    return violations


def documentation_violations(
    root: Path, manifest: Mapping[str, object], state: Mapping[str, object]
) -> tuple[ContractViolation, ...]:
    """Validate lifecycle, ownership, links, and generated status consumers."""

    violations: list[ContractViolation] = []
    if manifest.get("schema_version") != 1:
        violations.append(
            ContractViolation(
                "documentation.schema-version",
                MANIFEST_PATH.as_posix(),
                "schema_version must be 1",
            )
        )
    classified, classification_violations = _classified_paths(manifest)
    violations.extend(classification_violations)
    collections = manifest.get("collections")
    if not isinstance(collections, Mapping):
        collections = {}
        violations.append(
            ContractViolation(
                "documentation.schema",
                MANIFEST_PATH.as_posix(),
                "collections must be an object",
            )
        )
    for relative_path in sorted(classified):
        if not (root / relative_path).is_file():
            violations.append(
                ContractViolation(
                    "documentation.missing-file",
                    relative_path,
                    "classified document does not exist",
                )
            )
    for relative_path in sorted(_repository_markdown(root)):
        if relative_path not in classified and not _is_collection_member(relative_path, collections):
            violations.append(
                ContractViolation(
                    "documentation.unclassified",
                    relative_path,
                    "Markdown must have one lifecycle class or a declared collection",
                )
            )

    topic_owners = manifest.get("topic_owners")
    if not isinstance(topic_owners, Mapping):
        violations.append(
            ContractViolation(
                "documentation.schema",
                MANIFEST_PATH.as_posix(),
                "topic_owners must be an object",
            )
        )
    else:
        for topic, raw_path in topic_owners.items():
            path = str(raw_path)
            if not (root / path).is_file():
                violations.append(
                    ContractViolation(
                        "documentation.missing-owner",
                        path,
                        f"topic {topic!r} has no existing owner",
                    )
                )

    status_document = str(manifest.get("status_document") or "")
    if not status_document:
        violations.append(
            ContractViolation(
                "documentation.schema",
                MANIFEST_PATH.as_posix(),
                "status_document is required",
            )
        )
    else:
        actual = (root / status_document).read_text(encoding="utf-8") if (root / status_document).is_file() else ""
        try:
            expected = render_current_status(state)
        except ValueError as error:
            violations.append(
                ContractViolation(
                    "documentation.unrenderable-status",
                    status_document,
                    str(error),
                )
            )
            expected = None
        if expected is not None and actual != expected:
            violations.append(
                ContractViolation(
                    "documentation.stale-generated-status",
                    status_document,
                    "regenerate from current-release.json with --write",
                )
            )

    consumers = manifest.get("status_consumers")
    if not isinstance(consumers, list):
        violations.append(
            ContractViolation(
                "documentation.schema",
                MANIFEST_PATH.as_posix(),
                "status_consumers must be a list",
            )
        )
    else:
        try:
            critical_values = _status_values(state)
        except ValueError:
            mutable_tokens: tuple[str, ...] = ()
        else:
            mutable_tokens = tuple(
                str(critical_values[key])
                for key in ("tag", "commit", "fingerprint", "backup_file", "backup_sha")
            )
        for consumer in consumers:
            if not isinstance(consumer, Mapping):
                violations.append(
                    ContractViolation(
                        "documentation.schema",
                        MANIFEST_PATH.as_posix(),
                        "every status consumer must be an object",
                    )
                )
                continue
            relative_path = str(consumer.get("path") or "")
            language = str(consumer.get("language") or "")
            link = str(consumer.get("link") or "")
            path = root / relative_path
            if not path.is_file():
                violations.append(
                    ContractViolation(
                        "documentation.missing-status-consumer",
                        relative_path,
                        "status consumer does not exist",
                    )
                )
                continue
            text = path.read_text(encoding="utf-8")
            pattern = re.compile(
                re.escape(STATUS_START) + r".*?" + re.escape(STATUS_END), re.DOTALL
            )
            matches = pattern.findall(text)
            try:
                expected = render_status_block(state, language=language, link=link)
            except ValueError as error:
                violations.append(
                    ContractViolation(
                        "documentation.unrenderable-status-consumer",
                        relative_path,
                        str(error),
                    )
                )
                continue
            if len(matches) != 1 or matches[0] != expected:
                violations.append(
                    ContractViolation(
                        "documentation.stale-status-consumer",
                        relative_path,
                        "consumer must contain exactly one generated current-status block",
                    )
                )
                continue
            ordinary_text = pattern.sub("", text)
            for token in mutable_tokens:
                if token in ordinary_text:
                    violations.append(
                        ContractViolation(
                            "documentation.duplicated-current-state",
                            relative_path,
                            f"mutable current value must remain inside the generated block: {token}",
                        )
                    )
            for claim in mutable_current_release_claims(ordinary_text):
                violations.append(
                    ContractViolation(
                        "documentation.version-bound-current-claim",
                        relative_path,
                        f"replace mutable wording {claim!r} with the generated status reference",
                    )
                )

    for relative_path in sorted(_repository_markdown(root)):
        violations.extend(_local_link_violations(root, relative_path))
    return tuple(sorted(violations))


def validate_project_contracts(root: Path = PROJECT_ROOT) -> tuple[ContractViolation, ...]:
    """Run all release, architecture, and documentation governance contracts."""

    violations: list[ContractViolation] = []
    try:
        manifest = _read_json(root / MANIFEST_PATH)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return (
            ContractViolation(
                "documentation.manifest",
                MANIFEST_PATH.as_posix(),
                str(error),
            ),
        )
    status_source = Path(str(manifest.get("status_source") or ""))
    try:
        state = _read_json(root / status_source)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return (
            ContractViolation("status.source", status_source.as_posix(), str(error)),
        )
    violations.extend(_status_schema_violations(state, status_source.as_posix()))
    try:
        architecture = _read_json(root / ARCHITECTURE_PATH)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        violations.append(
            ContractViolation(
                "architecture.contract",
                ARCHITECTURE_PATH.as_posix(),
                str(error),
            )
        )
    else:
        violations.extend(architecture_violations(root, architecture))
    violations.extend(documentation_violations(root, manifest, state))
    violations.extend(iteration_risk_violations(root))
    return tuple(sorted(set(violations)))


def synchronize_status(root: Path = PROJECT_ROOT) -> tuple[str, ...]:
    """Preflight and regenerate every status consumer as one logical operation."""

    manifest = _read_json(root / MANIFEST_PATH)
    status_source = Path(str(manifest["status_source"]))
    state = _read_json(root / status_source)
    schema_violations = _status_schema_violations(state, status_source.as_posix())
    if schema_violations:
        details = "; ".join(
            f"[{item.code}] {item.message}" for item in schema_violations
        )
        raise ValueError(f"refusing to write from an invalid release state: {details}")
    status_path = root / str(manifest["status_document"])
    rendered_status = render_current_status(state)
    pattern = re.compile(
        re.escape(STATUS_START) + r".*?" + re.escape(STATUS_END), re.DOTALL
    )
    prepared_consumers: list[tuple[Path, str, str]] = []
    for consumer in manifest["status_consumers"]:
        relative_path = str(consumer["path"])
        path = root / relative_path
        text = path.read_text(encoding="utf-8")
        if len(pattern.findall(text)) != 1:
            raise ValueError(
                f"{relative_path} must contain exactly one generated status marker pair"
            )
        replacement = render_status_block(
            state,
            language=str(consumer["language"]),
            link=str(consumer["link"]),
        )
        updated = pattern.sub(replacement, text)
        prepared_consumers.append((path, text, updated))

    changed: list[str] = []
    if not status_path.exists() or status_path.read_text(encoding="utf-8") != rendered_status:
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(rendered_status, encoding="utf-8", newline="\n")
        changed.append(status_path.relative_to(root).as_posix())
    for path, original, updated in prepared_consumers:
        if updated != original:
            path.write_text(updated, encoding="utf-8", newline="\n")
            changed.append(path.relative_to(root).as_posix())
    return tuple(changed)


def _build_parser() -> argparse.ArgumentParser:
    """Build the small check/write command-line interface."""

    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="validate without changing files")
    mode.add_argument("--write", action="store_true", help="regenerate status documents, then validate")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute synchronization when requested, then report contract results."""

    args = _build_parser().parse_args(argv)
    if args.write:
        try:
            changed = synchronize_status(PROJECT_ROOT)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
            print(f"Status synchronization failed: {error}", file=sys.stderr)
            return 1
        if changed:
            print("Updated status documents:")
            for path in changed:
                print(f"- {path}")
        else:
            print("Status documents were already current.")
    violations = validate_project_contracts(PROJECT_ROOT)
    if violations:
        print(f"Project governance contract failed with {len(violations)} issue(s):", file=sys.stderr)
        for violation in violations:
            print(
                f"- [{violation.code}] {violation.path}: {violation.message}",
                file=sys.stderr,
            )
        return 1
    print("Project governance contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
