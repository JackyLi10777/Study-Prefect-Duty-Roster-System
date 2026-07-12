"""Audit Git privacy boundaries without printing tracked filenames or file contents."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
_MEDIA_EXTENSIONS = {".m4a", ".mp3", ".ogg", ".wav"}
_IMPORT_EXTENSIONS = {".csv", ".xls", ".xlsx"}
_REQUIRED_IGNORE_PROBES = {
    "environment": (".env", ".env.local"),
    "credential_file": ("demo_code2/service_account.json", "demo_code2/JSON 金钥.json"),
    "runtime_database": ("data/runtime/privacy-probe.sqlite3",),
    "backup": ("data/backups/privacy-probe.sqlite3",),
    "support_log": ("logs/app.log",),
    "generated_document": ("privacy-probe.pdf", "privacy-probe.zip"),
    "operator_import": ("privacy-probe.csv", "privacy-probe.xlsx"),
    "operator_music": ("music/privacy-probe.mp3", "music/custom/privacy-probe.m4a"),
    "operator_preferences": ("music/custom-library.json", "music/youtube-playlists.json", ".nicegui/storage.json"),
    "remote_attachment": (".codex-remote-attachments/privacy-probe.bin",),
}


@dataclass(frozen=True)
class RepositoryHygieneReport:
    status: str
    git_repository: bool
    history: str
    tracked_sensitive_count: int
    tracked_sensitive_categories: tuple[str, ...]
    missing_ignore_count: int
    missing_ignore_categories: tuple[str, ...]
    env_example_trackable: bool


def sensitive_category(raw_path: str) -> str | None:
    """Return a non-identifying category for paths that must never be versioned."""
    normalized = raw_path.replace("\\", "/").lower()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.lstrip("/")
    path = PurePosixPath(normalized)
    if normalized.startswith("archive/fictional-data/") and path.suffix == ".sqlite3":
        # This path is produced only by build_public_archive.py after a
        # quick_check and zero-row guard across every operational roster table.
        return None
    if normalized == ".env" or (normalized.startswith(".env.") and normalized != ".env.example"):
        return "environment"
    if path.name in {"service_account.json", "json 金钥.json", "json 金鑰.json"}:
        return "credential_file"
    if normalized.startswith("data/runtime/"):
        return "runtime_database"
    if normalized.startswith("data/backups/"):
        return "backup"
    if normalized.startswith("logs/"):
        return "support_log"
    if normalized.startswith(".nicegui/"):
        return "operator_preferences"
    if normalized.startswith(".codex-remote-attachments/"):
        return "remote_attachment"
    if normalized.startswith("local-imports/") or path.suffix in _IMPORT_EXTENSIONS:
        return "operator_import"
    if normalized.startswith("music/custom/") or normalized in {
        "music/custom-library.json",
        "music/youtube-playlists.json",
    }:
        return "operator_preferences"
    if normalized.startswith("music/") and path.suffix in _MEDIA_EXTENSIONS:
        # Root-level audio is the reviewed built-in library. Operator imports
        # remain confined to music/custom and are rejected above.
        return None
    if path.suffix in {".pdf", ".zip"}:
        return "generated_document"
    if ".sqlite3" in path.name:
        return "runtime_database"
    return None


def _git(root: Path, arguments: Iterable[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as error:
        raise RuntimeError("Git is unavailable for the repository privacy audit.") from error


def _probe_is_ignored(root: Path, path: str) -> bool:
    return _git(root, ("check-ignore", "--quiet", "--no-index", path)).returncode == 0


def audit_repository(root: Path = PROJECT_ROOT) -> RepositoryHygieneReport:
    """Inspect index and ignore behavior; never emit filenames or Git command output."""
    root = root.resolve()
    repository_check = _git(root, ("rev-parse", "--is-inside-work-tree"))
    if repository_check.returncode != 0 or repository_check.stdout.strip().lower() != "true":
        return RepositoryHygieneReport("fail", False, "missing", 0, (), 0, (), False)

    tracked_result = _git(root, ("ls-files", "-z"))
    if tracked_result.returncode != 0:
        return RepositoryHygieneReport("fail", True, "unknown", 0, (), 0, (), False)
    tracked_categories = tuple(
        sorted(
            {
                category
                for raw_path in tracked_result.stdout.split("\0")
                if raw_path and (category := sensitive_category(raw_path)) is not None
            }
        )
    )
    tracked_sensitive_count = sum(
        1 for raw_path in tracked_result.stdout.split("\0") if raw_path and sensitive_category(raw_path) is not None
    )

    missing_ignore_categories = tuple(
        sorted(
            category
            for category, probes in _REQUIRED_IGNORE_PROBES.items()
            if any(not _probe_is_ignored(root, probe) for probe in probes)
        )
    )
    env_example_trackable = not _probe_is_ignored(root, ".env.example")
    history = "present" if _git(root, ("rev-parse", "--verify", "HEAD")).returncode == 0 else "missing"
    status = (
        "pass"
        if (
            history == "present"
            and tracked_sensitive_count == 0
            and not missing_ignore_categories
            and env_example_trackable
        )
        else "fail"
    )
    return RepositoryHygieneReport(
        status,
        True,
        history,
        tracked_sensitive_count,
        tracked_categories,
        len(missing_ignore_categories),
        missing_ignore_categories,
        env_example_trackable,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT, help="Repository root to inspect.")
    args = parser.parse_args()
    try:
        report = audit_repository(args.root)
    except RuntimeError:
        report = RepositoryHygieneReport("fail", False, "unknown", 0, (), 0, (), False)
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    return 0 if report.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
