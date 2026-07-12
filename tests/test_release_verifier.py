from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys

from scripts import verify_release_candidate
from scripts.verify_release_candidate import (
    CANONICAL_BACKUPS,
    CANONICAL_DATABASE,
    ReleaseVerificationError,
    _assert_server_console_clean,
    isolated_environment,
)


def test_release_verifier_builds_only_explicit_disposable_write_paths(tmp_path: Path) -> None:
    environment = isolated_environment(tmp_path / "normal", 18765)

    assert environment["SING_YIN_E2E_ISOLATED"] == "1"
    assert Path(environment["SING_YIN_DATABASE_PATH"]).resolve() != CANONICAL_DATABASE
    assert Path(environment["SING_YIN_BACKUP_DIR"]).resolve() != CANONICAL_BACKUPS
    assert Path(environment["SING_YIN_LOG_DIR"]).is_dir()
    assert environment["SING_YIN_HOST"] == "127.0.0.1"
    assert environment["SING_YIN_TEST_URL"] == "http://127.0.0.1:18765"


def test_release_verifier_can_create_the_deliberately_blocked_backup_fixture(tmp_path: Path) -> None:
    environment = isolated_environment(tmp_path / "partial", 18766, blocked_backup=True)
    blocked_path = Path(environment["SING_YIN_BACKUP_DIR"])

    assert blocked_path.is_file()
    assert Path(environment["SING_YIN_DATABASE_PATH"]).parent == blocked_path.parent


def test_release_verifier_records_an_unexpected_orchestration_failure(monkeypatch, tmp_path: Path) -> None:
    report_path = tmp_path / "release-report.json"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(verify_release_candidate, "REPORT_PATH", report_path)
    monkeypatch.setattr(verify_release_candidate.tempfile, "mkdtemp", lambda **_kwargs: str(workspace))
    monkeypatch.setattr(
        verify_release_candidate,
        "_run_check",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("unexpected verifier defect")),
    )

    exit_code = verify_release_candidate.main()
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert report["status"] == "fail"
    assert report["humanAcceptanceRequired"] is True
    assert report["humanAcceptanceGuide"] == "docs/ACCEPTANCE_EVIDENCE.md"
    assert len(report["sourceFingerprint"]) == 64
    assert report["sourceFileCount"] > 0
    assert "unexpected verifier defect" in report["failure"]
    assert workspace.is_dir()


def test_release_verifier_imports_directly_outside_the_project_working_directory(tmp_path: Path) -> None:
    script_path = Path(verify_release_candidate.__file__).resolve()
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", f"import runpy; runpy.run_path({str(script_path)!r})"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_release_verifier_accepts_normal_and_classified_disconnect_console_lines(tmp_path: Path) -> None:
    log_path = tmp_path / "server-console.log"
    log_path.write_text(
        "INFO sing_yin_roster event=application_starting\n"
        "INFO sing_yin_roster event=client_connection_closed error_type=ConnectionResetError\n",
        encoding="utf-8",
    )

    _assert_server_console_clean(log_path)


def test_release_verifier_rejects_server_error_without_exposing_console_payload(tmp_path: Path) -> None:
    log_path = tmp_path / "server-console.log"
    private_payload = "private-student-payload"
    log_path.write_text(
        f"ERROR [asyncio] unexpected failure {private_payload}\n"
        "Traceback (most recent call last):\n",
        encoding="utf-8",
    )

    try:
        _assert_server_console_clean(log_path)
    except ReleaseVerificationError as error:
        assert "unexpected failure marker" in str(error)
        assert private_payload not in str(error)
    else:
        raise AssertionError("server failure marker should fail the release verifier")
