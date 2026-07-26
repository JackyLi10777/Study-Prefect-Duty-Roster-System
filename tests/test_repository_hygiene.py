from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts.check_repository_hygiene import PROJECT_ROOT, audit_repository, is_release_source, sensitive_category


def _git(root: Path, *arguments: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _initialize_committed_repository(root: Path) -> None:
    root.mkdir()
    shutil.copy2(PROJECT_ROOT / ".gitignore", root / ".gitignore")
    (root / "README.md").write_text("release fixture\n", encoding="utf-8")
    _git(root, "init", "--quiet")
    _git(root, "add", ".gitignore", "README.md")
    _git(root, "-c", "user.name=Release Test", "-c", "user.email=release@example.invalid", "commit", "-m", "fixture")


@pytest.mark.parametrize(
    ("path", "expected"),
    (
        (".env", "environment"),
        (".env.school", "environment"),
        (".env.example", None),
        ("demo_code2/service_account.json", "credential_file"),
        ("demo_code2/JSON 金钥.json", "credential_file"),
        ("demo_code2/service_account.example.json", None),
        ("data/runtime/live.sqlite3", "runtime_database"),
        ("data/backups/snapshot.sqlite3", "backup"),
        ("logs/app.log", "support_log"),
        ("data/support/inbox/INC-20990101-1234ABCD/manifest.json", "support_incident"),
        ("support/inbox/INC-20990101-1234ABCD/report.md", "support_incident"),
        ("weekly-roster.pdf", "generated_document"),
        ("handover.zip", "generated_document"),
        ("actual-prefects.csv", "operator_import"),
        ("music/custom/song.m4a", "operator_preferences"),
        ("music/built-in-track.m4a", None),
        ("archive/fictional-data/sing-yin-roster-fictional.sqlite3", None),
        ("nicegui_app/main.py", None),
    ),
)
def test_sensitive_repository_paths_are_classified_without_reading_content(path: str, expected: str | None) -> None:
    assert sensitive_category(path) == expected


def test_current_repository_hygiene_requires_real_history() -> None:
    report = audit_repository(PROJECT_ROOT)

    assert report.status == ("fail" if report.untracked_release_source_count else "pass")
    assert report.git_repository is True
    assert report.tracked_sensitive_count == 0
    assert report.missing_ignore_count == 0
    assert report.env_example_trackable is True
    assert report.history == "present"


@pytest.mark.parametrize(
    ("path", "expected"),
    (
        ("nicegui_app/new_module.py", True),
        ("migrations/versions/9999_release.py", True),
        ("cloudflare/roster_viewer/new_worker.js", True),
        ("cloudflare/roster_viewer/package.json", True),
        ("cloudflare/roster_viewer/wrangler.jsonc", True),
        ("design_system/product-identity.v1.json", True),
        ("nicegui_app/assets/brand/service-weave/service-weave-windows-v1.ico", True),
        (".env.example", True),
        ("daily_verses.py", True),
        ("notes/diagnostic.tmp", False),
        ("nicegui_app/local-scratch.tmp", False),
    ),
)
def test_release_source_classifier_ignores_unrelated_temporary_files(path: str, expected: bool) -> None:
    assert is_release_source(path) is expected


def test_hygiene_audit_blocks_an_untracked_release_source_without_naming_it(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    _initialize_committed_repository(repository)
    release_source = repository / "cloudflare" / "roster_viewer" / "new_worker.js"
    release_source.parent.mkdir(parents=True)
    release_source.write_text("export default {};\n", encoding="utf-8")

    report = audit_repository(repository)

    assert report.status == "fail"
    assert report.untracked_release_source_count == 1


def test_hygiene_audit_allows_an_untracked_non_release_temporary_file(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    _initialize_committed_repository(repository)
    scratch = repository / "notes" / "diagnostic.tmp"
    scratch.parent.mkdir()
    scratch.write_text("temporary local note\n", encoding="utf-8")

    report = audit_repository(repository)

    assert report.status == "pass"
    assert report.untracked_release_source_count == 0


def test_hygiene_audit_fails_when_repository_has_no_commit_history(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    shutil.copy2(PROJECT_ROOT / ".gitignore", repository / ".gitignore")
    _git(repository, "init", "--quiet")

    report = audit_repository(repository)

    assert report.status == "fail"
    assert report.history == "missing"


def test_hygiene_audit_fails_closed_for_a_force_tracked_sensitive_file(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    shutil.copy2(PROJECT_ROOT / ".gitignore", repository / ".gitignore")
    _git(repository, "init", "--quiet")
    sensitive = repository / "data" / "runtime" / "private.sqlite3"
    sensitive.parent.mkdir(parents=True)
    sensitive.write_bytes(b"private-data")
    _git(repository, "add", "-f", "data/runtime/private.sqlite3")

    report = audit_repository(repository)

    assert report.status == "fail"
    assert report.tracked_sensitive_count == 1
    assert report.tracked_sensitive_categories == ("runtime_database",)


def test_cli_report_never_exposes_a_sensitive_filename(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    shutil.copy2(PROJECT_ROOT / ".gitignore", repository / ".gitignore")
    _git(repository, "init", "--quiet")
    private_filename = "private-student-list.csv"
    (repository / private_filename).write_text("name\nprivate", encoding="utf-8")
    _git(repository, "add", "-f", private_filename)

    result = subprocess.run(
        ["python", "-X", "utf8", str(PROJECT_ROOT / "scripts" / "check_repository_hygiene.py"), "--root", str(repository)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["status"] == "fail"
    assert payload["tracked_sensitive_count"] == 1
    assert private_filename not in result.stdout
