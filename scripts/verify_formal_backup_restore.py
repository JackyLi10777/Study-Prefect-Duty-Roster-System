"""Create one verified official snapshot and prove it restores in isolation."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui_app.config import DEFAULT_BACKUP_DIR, DEFAULT_DATABASE_PATH, PROJECT_ROOT
from nicegui_app.services.roster_workflow import RosterWorkflow


REPORT_PATH = PROJECT_ROOT / "logs" / "formal-backup-restore-report.json"
COUNTED_TABLES = (
    "prefects",
    "prefect_availability",
    "roster_weeks",
    "roster_assignments",
    "fairness_ledger",
    "leave_adjustments",
    "leave_declarations",
)


def _counts(path: Path) -> dict[str, int]:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        return {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in COUNTED_TABLES
        }
    finally:
        connection.close()


def main() -> int:
    official = RosterWorkflow(
        database_path=DEFAULT_DATABASE_PATH,
        backup_dir=DEFAULT_BACKUP_DIR,
        seed_path=None,
    )
    official.bootstrap()
    fairness = official.reconcile_fairness()
    if not fairness.balanced:
        raise RuntimeError("Formal backup refused because fairness reconciliation failed.")

    snapshot = official.create_verified_backup()
    verification = official.verify_backup(snapshot)
    if not verification.get("valid"):
        raise RuntimeError("The newly created formal snapshot did not pass verification.")

    workspace = Path(tempfile.mkdtemp(prefix="sing-yin-formal-restore-"))
    try:
        isolated_backups = workspace / "backups"
        isolated_backups.mkdir(parents=True)
        copied_snapshot = isolated_backups / snapshot.name
        copied_manifest = copied_snapshot.with_suffix(".manifest.json")
        shutil.copy2(snapshot, copied_snapshot)
        shutil.copy2(snapshot.with_suffix(".manifest.json"), copied_manifest)

        isolated_database = workspace / "restored.sqlite3"
        isolated = RosterWorkflow(
            database_path=isolated_database,
            backup_dir=isolated_backups,
            seed_path=None,
        )
        isolated.bootstrap()
        isolated.restore_backup(copied_snapshot)
        isolated_fairness = isolated.reconcile_fairness()
        if not isolated_fairness.balanced:
            raise RuntimeError("The isolated restored database failed fairness reconciliation.")
        source_counts = _counts(DEFAULT_DATABASE_PATH)
        restored_counts = _counts(isolated_database)
        if source_counts != restored_counts:
            raise RuntimeError("The isolated restored database has different operational row counts.")
        with sqlite3.connect(DEFAULT_DATABASE_PATH) as source_connection, sqlite3.connect(isolated_database) as restored_connection:
            source_audits = int(source_connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0])
            restored_audits = int(restored_connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0])
        if restored_audits != source_audits + 1:
            raise RuntimeError("The isolated restore did not append exactly one restore audit event.")

        report = {
            "status": "pass",
            "checkedAt": datetime.now(timezone.utc).isoformat(),
            "snapshotFile": snapshot.name,
            "sha256": verification.get("sha256"),
            "integrity": verification.get("integrity"),
            "tableCount": verification.get("tableCount"),
            "fairnessBalanced": True,
            "rowCountsMatched": True,
            "restoreAuditAppended": True,
            "isolatedRestore": True,
        }
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
