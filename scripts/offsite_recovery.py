"""Export one verified backup to approved off-site media and drill its restore."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui_app.services.offsite_recovery import (
    OffsiteRecoveryError,
    OffsiteReleaseIdentity,
    OffsiteTargetEvidence,
    drill_offsite_recovery,
    export_offsite_recovery,
)
from nicegui_app.services.roster_workflow import RosterWorkflow


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create and drill a verified off-site Sing Yin recovery bundle.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    export = subparsers.add_parser(
        "export-and-drill",
        help="Export the latest verified snapshot and restore only from that copy.",
    )
    export.add_argument("--database-path", type=Path, required=True)
    export.add_argument("--backup-dir", type=Path, required=True)
    export.add_argument("--destination-root", type=Path, required=True)
    export.add_argument("--release-marker", type=Path, required=True)
    export.add_argument("--target-kind", choices=("bitlocker_external",), required=True)
    export.add_argument("--target-evidence-sha256", required=True)
    export.add_argument("--target-encryption-method", required=True)
    export.add_argument("--report", type=Path, required=True)
    drill = subparsers.add_parser(
        "drill",
        help="Restore from one existing off-site bundle without the original host data.",
    )
    drill.add_argument("--bundle-dir", type=Path, required=True)
    drill.add_argument("--report", type=Path, required=True)
    return parser


def _read_release_identity(path: Path) -> OffsiteReleaseIdentity:
    try:
        marker = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OffsiteRecoveryError("The immutable release marker is unreadable.") from error
    if not isinstance(marker, dict) or marker.get("schemaVersion") != 2:
        raise OffsiteRecoveryError("The immutable release marker is invalid.")
    return OffsiteReleaseIdentity(
        release_ref=str(marker.get("releaseRef", "")),
        commit=str(marker.get("commit", "")),
        source_tree=str(marker.get("sourceTree", "")),
    )


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as destination:
            json.dump(payload, destination, ensure_ascii=False, indent=2, sort_keys=True)
            destination.write("\n")
            destination.flush()
            os.fsync(destination.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _run_export_and_drill(args: argparse.Namespace) -> dict[str, Any]:
    workflow = RosterWorkflow(
        database_path=args.database_path,
        backup_dir=args.backup_dir,
        seed_path=None,
    )
    target = OffsiteTargetEvidence(
        kind=args.target_kind,
        evidence_sha256=args.target_evidence_sha256,
        encryption_method=args.target_encryption_method,
    )
    release = _read_release_identity(args.release_marker)
    try:
        workflow.bootstrap()
        if workflow.diagnostic_only:
            raise OffsiteRecoveryError("The official database is in recovery maintenance mode.")
        workflow.create_verified_backup()
        exported = export_offsite_recovery(
            workflow,
            args.destination_root,
            target=target,
            release=release,
        )
    finally:
        if workflow.sessions is not None:
            workflow.sessions.kw["bind"].dispose()
            workflow.sessions = None
    drilled = drill_offsite_recovery(exported.bundle_dir)
    return {
        "schemaVersion": 1,
        "status": "pass",
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "export": exported.to_report(),
        "drill": drilled.to_report(),
        "operatorActionRequired": (
            "Disconnect the encrypted external volume and place it with the approved school custodian."
        ),
    }


def _run_standalone_drill(args: argparse.Namespace) -> dict[str, Any]:
    drilled = drill_offsite_recovery(args.bundle_dir)
    return {
        "schemaVersion": 1,
        "status": "pass",
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "drill": drilled.to_report(),
        "operatorActionRequired": (
            "Record this replacement-location evidence and keep the encrypted volume offline."
        ),
    }


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "export-and-drill":
            report = _run_export_and_drill(args)
        elif args.command == "drill":
            report = _run_standalone_drill(args)
        else:  # pragma: no cover - argparse owns the command set
            raise OffsiteRecoveryError("The requested off-site recovery operation is unsupported.")
    except OffsiteRecoveryError as error:
        report = {
            "schemaVersion": 1,
            "status": "fail",
            "checkedAt": datetime.now(timezone.utc).isoformat(),
            "failure": str(error),
        }
        _write_report(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
    except Exception as error:  # keep local paths and payloads out of the report
        report = {
            "schemaVersion": 1,
            "status": "fail",
            "checkedAt": datetime.now(timezone.utc).isoformat(),
            "failure": f"Unexpected {type(error).__name__}; inspect the protected host locally.",
        }
        _write_report(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1

    _write_report(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
