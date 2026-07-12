"""Read non-sensitive release evidence and reject stale or malformed reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Iterable, Literal

from nicegui_app.config import POLICY_VERSION, PROJECT_ROOT


REPORT_PATH = PROJECT_ROOT / "logs" / "release-candidate-report.json"
PROJECT_ID = "sing-yin-study-prefect-duty-roster"
RELEASE_SOURCE_ROOTS = (
    PROJECT_ROOT / "nicegui_app",
    PROJECT_ROOT / "packages",
    PROJECT_ROOT / "migrations",
    PROJECT_ROOT / "scripts",
    PROJECT_ROOT / "tests",
)
RELEASE_SOURCE_FILES = (
    PROJECT_ROOT / "requirements.txt",
    PROJECT_ROOT / "requirements-dev.txt",
    PROJECT_ROOT / "pyproject.toml",
    PROJECT_ROOT / "alembic.ini",
    PROJECT_ROOT / "START_SING_YIN_ROSTER.cmd",
    PROJECT_ROOT / "START_PRACTICE_MODE.cmd",
    PROJECT_ROOT / "RESET_PRACTICE_MODE.cmd",
)
RELEASE_SUFFIXES = {".py", ".ini", ".toml", ".txt", ".ps1", ".cmd"}
EvidenceState = Literal["pass", "running", "stale", "fail", "missing", "unreadable"]


@dataclass(frozen=True)
class ReleaseEvidence:
    state: EvidenceState
    passed_checks: int = 0
    total_checks: int = 0
    finished_at: datetime | None = None
    human_acceptance_required: bool = True


def release_source_fingerprint(paths: Iterable[Path] | None = None) -> tuple[str, int]:
    """Hash release-sensitive source and verification inputs in stable order."""
    if paths is None:
        candidates = [
            path
            for root in RELEASE_SOURCE_ROOTS
            if root.is_dir()
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in RELEASE_SUFFIXES and "__pycache__" not in path.parts
        ]
        candidates.extend(path for path in RELEASE_SOURCE_FILES if path.is_file())
    else:
        candidates = [Path(path) for path in paths if Path(path).is_file()]
    unique_paths = sorted({path.resolve() for path in candidates}, key=lambda path: path.as_posix().lower())
    digest = hashlib.sha256()
    for path in unique_paths:
        try:
            relative = path.relative_to(PROJECT_ROOT.resolve()).as_posix()
        except ValueError:
            relative = path.name
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest(), len(unique_paths)


def load_release_evidence(
    report_path: Path = REPORT_PATH,
    *,
    current_fingerprint: str | None = None,
) -> ReleaseEvidence:
    """Return a display-safe state without exposing report parsing diagnostics."""
    if not report_path.is_file():
        return ReleaseEvidence("missing")
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ReleaseEvidence("unreadable")
    if not isinstance(payload, dict):
        return ReleaseEvidence("unreadable")
    if payload.get("schemaVersion") != 1 or payload.get("project") != PROJECT_ID:
        return ReleaseEvidence("unreadable")
    if payload.get("policyVersion") != POLICY_VERSION or payload.get("humanAcceptanceRequired") is not True:
        return ReleaseEvidence("unreadable")
    fingerprint = current_fingerprint or release_source_fingerprint()[0]
    if payload.get("sourceFingerprint") != fingerprint:
        return ReleaseEvidence("stale")

    checks = payload.get("checks")
    if not isinstance(checks, list) or any(not isinstance(item, dict) for item in checks):
        return ReleaseEvidence("unreadable")
    passed = sum(1 for item in checks if item.get("status") == "pass")
    total = len(checks)
    finished_at = None
    raw_finished_at = payload.get("finishedAt")
    if isinstance(raw_finished_at, str):
        try:
            finished_at = datetime.fromisoformat(raw_finished_at)
        except ValueError:
            return ReleaseEvidence("unreadable")

    status = payload.get("status")
    if status == "running":
        return ReleaseEvidence("running", passed, total)
    if status == "pass" and total > 0 and passed == total and finished_at is not None:
        return ReleaseEvidence("pass", passed, total, finished_at)
    if status == "fail" or any(item.get("status") == "fail" for item in checks):
        return ReleaseEvidence("fail", passed, total, finished_at)
    return ReleaseEvidence("unreadable", passed, total, finished_at)
