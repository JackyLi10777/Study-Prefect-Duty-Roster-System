"""Read non-sensitive release evidence and reject stale or malformed reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Iterable, Literal

from nicegui_app.config import POLICY_VERSION, PROJECT_ROOT


REPORT_PATH = PROJECT_ROOT / "logs" / "release-candidate-report.json"
PROJECT_ID = "sing-yin-study-prefect-duty-roster"
RELEASE_REPORT_SCHEMA_VERSION = 3
RELEASE_SOURCE_ROOTS = (
    PROJECT_ROOT / "nicegui_app",
    PROJECT_ROOT / "packages",
    PROJECT_ROOT / "migrations",
    PROJECT_ROOT / "cloudflare",
    PROJECT_ROOT / "design_system",
    PROJECT_ROOT / "music",
)
RELEASE_SOURCE_FILES = (
    PROJECT_ROOT / ".env.example",
    PROJECT_ROOT / ".gitattributes",
    PROJECT_ROOT / ".gitignore",
    PROJECT_ROOT / "daily_verses.py",
    PROJECT_ROOT / "requirements.txt",
    PROJECT_ROOT / "requirements-dev.txt",
    PROJECT_ROOT / "requirements.lock",
    PROJECT_ROOT / "requirements-dev.lock",
    PROJECT_ROOT / "pyproject.toml",
    PROJECT_ROOT / "alembic.ini",
    PROJECT_ROOT / "START_SING_YIN_ROSTER.cmd",
    PROJECT_ROOT / "START_PRACTICE_MODE.cmd",
    PROJECT_ROOT / "RESET_PRACTICE_MODE.cmd",
    PROJECT_ROOT / "data" / "demo" / "prefects.zh-HK.seed.json",
    PROJECT_ROOT / "data" / "devotional" / "daily-verses.seed.json",
    # Runtime and host-operation scripts are explicit. Documentation, tests,
    # CI definitions, and the fast change classifier have their own focused
    # verification and no longer stale a proven runtime candidate.
    PROJECT_ROOT / "scripts" / "activate_cloudflare_private_warp.ps1",
    PROJECT_ROOT / "scripts" / "activate_cloudflare_remote_access.ps1",
    PROJECT_ROOT / "scripts" / "build_pdf_fonts.py",
    PROJECT_ROOT / "scripts" / "check_deployment_readiness.py",
    PROJECT_ROOT / "scripts" / "doctor_windows_remote_access.ps1",
    PROJECT_ROOT / "scripts" / "deploy_windows_release.ps1",
    PROJECT_ROOT / "scripts" / "inspect_support_log.py",
    PROJECT_ROOT / "scripts" / "prepare_cloudflare_remote_access.ps1",
    PROJECT_ROOT / "scripts" / "prepare_windows_host.ps1",
    PROJECT_ROOT / "scripts" / "register_windows_startup_task.ps1",
    PROJECT_ROOT / "scripts" / "reset_official_data.py",
    PROJECT_ROOT / "scripts" / "reset_practice_mode.py",
    PROJECT_ROOT / "scripts" / "start_sing_yin_roster.ps1",
    PROJECT_ROOT / "scripts" / "verify_cloudflare_access.ps1",
    PROJECT_ROOT / "scripts" / "verify_cloudflare_private_warp.ps1",
    PROJECT_ROOT / "scripts" / "verify_formal_backup_restore.py",
    PROJECT_ROOT / "scripts" / "verify_practice_mode.py",
    PROJECT_ROOT / "scripts" / "verify_public_roster_viewer.py",
    PROJECT_ROOT / "scripts" / "windows_host_common.ps1",
    # A change to a formal evidence gate invalidates old evidence. Ordinary
    # tests and documentation do not alter the deployed artifact.
    PROJECT_ROOT / "scripts" / "check_repository_hygiene.py",
    PROJECT_ROOT / "scripts" / "run_security_checks.py",
    PROJECT_ROOT / "scripts" / "verify_guest_trial.py",
    PROJECT_ROOT / "scripts" / "verify_nicegui_mobile.py",
    PROJECT_ROOT / "scripts" / "verify_nicegui_partial_backup.py",
    PROJECT_ROOT / "scripts" / "verify_nicegui_ui.py",
    PROJECT_ROOT / "scripts" / "verify_nicegui_write_pipeline.py",
    PROJECT_ROOT / "scripts" / "verify_rc31_theme_controls.py",
    PROJECT_ROOT / "scripts" / "verify_release_candidate.py",
    PROJECT_ROOT / "scripts" / "verify_runtime_performance.py",
    PROJECT_ROOT / "scripts" / "verify_unified_guest_ui.py",
)
RELEASE_EXCLUDED_DIRECTORY_NAMES = {"__pycache__", "node_modules", ".wrangler"}
RELEASE_EXCLUDED_RELATIVE_PREFIXES = (
    "music/custom/",
    "music/youtube-imports/",
    "music/.youtube-import-staging/",
    "music/custom-library.json",
    "music/youtube-playlists.json",
    "music/.custom-library.json",
    "music/.youtube-playlists.json",
)
RELEASE_EXCLUDED_RELATIVE_GLOBS = (
    # Keep the immutable release fingerprint aligned with .gitignore. These
    # downloader-created duplicate copies are browser-local library noise and
    # are never part of a clean release tag or host bundle.
    "music/*(1).m4a",
)
RELEASE_SUFFIXES = {
    ".py",
    ".ini",
    ".toml",
    ".txt",
    ".ps1",
    ".cmd",
    ".css",
    ".js",
    ".json",
    ".jsonc",
    ".md",
    ".m4a",
    ".ico",
    ".png",
    ".svg",
    ".webp",
    ".woff2",
    ".ttf",
    ".yml",
    ".yaml",
}
RELEASE_BYTE_EXACT_SUFFIXES = {".ico", ".m4a", ".png", ".webp", ".woff2", ".ttf"}
EvidenceState = Literal["pass", "running", "stale", "fail", "missing", "unreadable"]


@dataclass(frozen=True)
class ReleaseEvidence:
    state: EvidenceState
    passed_checks: int = 0
    total_checks: int = 0
    finished_at: datetime | None = None
    human_acceptance_required: bool = True


def _is_excluded_release_path(path: Path) -> bool:
    try:
        relative = path.relative_to(PROJECT_ROOT).as_posix().lower()
    except ValueError:
        return False
    return (
        any(relative.startswith(prefix) for prefix in RELEASE_EXCLUDED_RELATIVE_PREFIXES)
        or any(PurePosixPath(relative).match(pattern) for pattern in RELEASE_EXCLUDED_RELATIVE_GLOBS)
    )


def _release_fingerprint_payload(path: Path) -> bytes:
    """Return stable checkout bytes while preserving binary integrity exactly."""
    payload = path.read_bytes()
    if path.suffix.lower() in RELEASE_BYTE_EXACT_SUFFIXES:
        return payload
    # Git may materialize the same text blob as LF or CRLF on Windows. Only
    # canonicalize that checkout representation; BOMs, lone CRs, encodings,
    # whitespace, and all binary inputs remain significant.
    return payload.replace(b"\r\n", b"\n")


def _iter_release_source_paths(root: Path) -> Iterable[Path]:
    """Yield release files without entering ignored dependency mount points."""

    def raise_walk_error(error: OSError) -> None:
        raise error

    for directory_name, child_directories, filenames in os.walk(
        root,
        topdown=True,
        onerror=raise_walk_error,
        followlinks=False,
    ):
        directory = Path(directory_name)
        child_directories[:] = [
            name
            for name in child_directories
            if name.lower() not in RELEASE_EXCLUDED_DIRECTORY_NAMES
            and not _is_excluded_release_path(directory / name)
        ]
        for filename in filenames:
            path = directory / filename
            if (
                path.suffix.lower() in RELEASE_SUFFIXES
                and not _is_excluded_release_path(path)
            ):
                yield path


def _calculate_release_source_fingerprint(paths: Iterable[Path] | None = None) -> tuple[str, int]:
    candidates = [
        path
        for root in RELEASE_SOURCE_ROOTS
        if root.is_dir()
        for path in _iter_release_source_paths(root)
    ] if paths is None else [Path(path) for path in paths if Path(path).is_file()]
    if paths is None:
        candidates.extend(path for path in RELEASE_SOURCE_FILES if path.is_file())
    unique_paths = sorted({path.resolve() for path in candidates}, key=lambda path: path.as_posix().lower())
    digest = hashlib.sha256()
    for path in unique_paths:
        try:
            relative = path.relative_to(PROJECT_ROOT.resolve()).as_posix()
        except ValueError:
            relative = path.name
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_release_fingerprint_payload(path))
        digest.update(b"\0")
    return digest.hexdigest(), len(unique_paths)


@lru_cache(maxsize=1)
def _cached_release_source_fingerprint() -> tuple[str, int]:
    """Hash once per process; production runs with reload disabled and immutable source."""
    return _calculate_release_source_fingerprint()


def release_source_fingerprint(
    paths: Iterable[Path] | None = None,
    *,
    refresh: bool = False,
) -> tuple[str, int]:
    """Hash release-sensitive inputs; refresh only for an explicit integrity boundary."""
    if paths is not None or refresh:
        return _calculate_release_source_fingerprint(paths)
    return _cached_release_source_fingerprint()


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
    if payload.get("schemaVersion") != RELEASE_REPORT_SCHEMA_VERSION or payload.get("project") != PROJECT_ID:
        return ReleaseEvidence("unreadable")
    if payload.get("policyVersion") != POLICY_VERSION or payload.get("humanAcceptanceRequired") is not True:
        return ReleaseEvidence("unreadable")
    source_commit = payload.get("sourceCommit")
    source_tree = payload.get("sourceTree")
    planned_tag = payload.get("plannedReleaseTag")
    required_identities = payload.get("requiredCheckIdentities")
    tool_versions = payload.get("toolVersions")
    if (
        not isinstance(source_commit, str)
        or len(source_commit) != 40
        or not isinstance(source_tree, str)
        or len(source_tree) != 40
        or payload.get("sourceDirty") is not False
        or not isinstance(planned_tag, str)
        or payload.get("immutableReleaseReference") != f"refs/tags/{planned_tag}"
        or not isinstance(required_identities, list)
        or not required_identities
        or len(required_identities) != len(set(required_identities))
        or not isinstance(tool_versions, dict)
        or not all(isinstance(value, str) and value for value in tool_versions.values())
    ):
        return ReleaseEvidence("unreadable")
    fingerprint = current_fingerprint or release_source_fingerprint()[0]
    if payload.get("sourceFingerprint") != fingerprint:
        return ReleaseEvidence("stale")

    checks = payload.get("checks")
    if not isinstance(checks, list) or any(not isinstance(item, dict) for item in checks):
        return ReleaseEvidence("unreadable")
    passed = sum(1 for item in checks if item.get("status") == "pass")
    total = len(checks)
    if total != len(required_identities) or [item.get("name") for item in checks] != required_identities:
        return ReleaseEvidence("unreadable")
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
    post_verification_source = payload.get("postVerificationSource")
    expected_post_verification_source = {
        "sourceFingerprint": payload.get("sourceFingerprint"),
        "sourceFileCount": payload.get("sourceFileCount"),
        "sourceCommit": source_commit,
        "sourceTree": source_tree,
        "sourceDirty": False,
    }
    if post_verification_source != expected_post_verification_source:
        return ReleaseEvidence("unreadable", passed, total, finished_at)
    if status == "pass" and total > 0 and passed == total and finished_at is not None:
        return ReleaseEvidence("pass", passed, total, finished_at)
    if status == "fail" or any(item.get("status") == "fail" for item in checks):
        return ReleaseEvidence("fail", passed, total, finished_at)
    return ReleaseEvidence("unreadable", passed, total, finished_at)
