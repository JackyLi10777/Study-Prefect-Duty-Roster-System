from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import shutil
import subprocess
import sys

from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.services.roster_workflow import RosterWorkflow


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "offsite_recovery.py"


def test_cli_exports_drills_and_writes_a_bounded_report(tmp_path: Path) -> None:
    host = tmp_path / "host"
    database = host / "runtime" / "sing-yin-roster.sqlite3"
    backups = host / "backups"
    workflow = RosterWorkflow(
        database_path=database,
        backup_dir=backups,
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    workflow.generate_and_save_draft(date(2026, 9, 7))
    workflow.create_verified_backup()
    assert workflow.sessions is not None
    workflow.sessions.kw["bind"].dispose()
    workflow.sessions = None

    destination = tmp_path / "external"
    destination.mkdir()
    marker = tmp_path / ".sing-yin-release.json"
    marker.write_text(
        json.dumps(
            {
                "schemaVersion": 2,
                "releaseRef": "v1.2.0-test",
                "commit": "b" * 40,
                "sourceTree": "c" * 40,
            }
        ),
        encoding="utf-8",
    )
    report_path = tmp_path / "reports" / "offsite.json"

    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPT),
            "export-and-drill",
            "--database-path",
            str(database),
            "--backup-dir",
            str(backups),
            "--destination-root",
            str(destination),
            "--release-marker",
            str(marker),
            "--target-kind",
            "bitlocker_external",
            "--target-evidence-sha256",
            "a" * 64,
            "--target-encryption-method",
            "XtsAes256",
            "--report",
            str(report_path),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    serialized = json.dumps(report)
    assert report["status"] == "pass"
    assert report["drill"]["status"] == "pass"
    assert report["drill"]["rowCountsMatched"] is True
    assert report["drill"]["fairnessBalanced"] is True
    assert report["drill"]["restoreAuditAppended"] is True
    assert str(database) not in serialized
    assert str(destination) not in serialized

    bundle_dir = next((destination / "SingYinRosterRecovery").glob("SYSS_Offsite_*"))
    shutil.rmtree(host)
    replacement_report_path = tmp_path / "replacement" / "drill.json"
    replacement = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPT),
            "drill",
            "--bundle-dir",
            str(bundle_dir),
            "--report",
            str(replacement_report_path),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )

    assert replacement.returncode == 0, replacement.stderr
    replacement_report = json.loads(replacement_report_path.read_text(encoding="utf-8"))
    assert replacement_report["status"] == "pass"
    assert replacement_report["drill"]["bundleName"] == bundle_dir.name


def test_cli_fails_closed_when_the_release_marker_is_missing(tmp_path: Path) -> None:
    destination = tmp_path / "external"
    destination.mkdir()
    report_path = tmp_path / "reports" / "offsite.json"

    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPT),
            "export-and-drill",
            "--database-path",
            str(tmp_path / "runtime" / "sing-yin-roster.sqlite3"),
            "--backup-dir",
            str(tmp_path / "backups"),
            "--destination-root",
            str(destination),
            "--release-marker",
            str(tmp_path / "missing-release-marker.json"),
            "--target-kind",
            "bitlocker_external",
            "--target-evidence-sha256",
            "a" * 64,
            "--target-encryption-method",
            "XtsAes256",
            "--report",
            str(report_path),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )

    assert result.returncode == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report == {
        "checkedAt": report["checkedAt"],
        "failure": "The immutable release marker is unreadable.",
        "schemaVersion": 1,
        "status": "fail",
    }
    assert not (destination / "SingYinRosterRecovery").exists()
