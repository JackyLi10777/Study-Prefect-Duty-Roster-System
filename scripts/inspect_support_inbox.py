"""Validate and summarize local incident bundles without exposing report text."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui_app.services.support_incidents import (
    INCIDENT_ID_PATTERN,
    IncidentValidationError,
    SupportInbox,
    SupportIncidentError,
)


def _safe_summary(inbox: SupportInbox, incident_id: str) -> dict[str, object]:
    summary = inbox.validate_bundle(incident_id)
    return asdict(summary)


def _candidate_ids(inbox: SupportInbox) -> tuple[str, ...]:
    inbox.initialize()
    return tuple(
        sorted(
            {
                item.name
                for bucket in ("inbox", "triaged", "resolved")
                for item in (inbox.root / bucket).iterdir()
                if item.is_dir() and INCIDENT_ID_PATTERN.fullmatch(item.name)
            },
            reverse=True,
        )
    )


def inspect(
    inbox: SupportInbox,
    *,
    incident_id: str | None = None,
    quarantine_invalid: bool = False,
) -> dict[str, object]:
    identifiers = (incident_id,) if incident_id else _candidate_ids(inbox)
    valid: list[dict[str, object]] = []
    invalid_count = 0
    quarantined_count = 0
    for identifier in identifiers:
        try:
            valid.append(_safe_summary(inbox, identifier))
        except (SupportIncidentError, OSError):
            invalid_count += 1
            if quarantine_invalid and INCIDENT_ID_PATTERN.fullmatch(identifier):
                try:
                    inbox.quarantine(identifier, reason_code="inspector_validation_failed")
                except (SupportIncidentError, OSError):
                    pass
                else:
                    quarantined_count += 1
    return {
        "status": "pass" if invalid_count == 0 else "attention",
        "valid_incident_count": len(valid),
        "invalid_incident_count": invalid_count,
        "quarantined_incident_count": quarantined_count,
        "incidents": valid,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="Override the configured local support root.")
    parser.add_argument("--incident", help="Inspect one INC-... identifier.")
    parser.add_argument("--quarantine-invalid", action="store_true", help="Move malformed bundles into quarantine.")
    parser.add_argument("--status", help="Append an allowlisted lifecycle status to one valid incident.")
    parser.add_argument("--note-code", default="operator_update", help="Safe non-content lifecycle note code.")
    args = parser.parse_args()
    if args.incident and not INCIDENT_ID_PATTERN.fullmatch(args.incident):
        parser.error("--incident must look like INC-YYYYMMDD-1234ABCD")
    if args.status and not args.incident:
        parser.error("--status requires --incident")
    inbox = SupportInbox(args.root)
    try:
        if args.status:
            inbox.append_status(args.incident, status_value=args.status, note_code=args.note_code)
        payload = inspect(
            inbox,
            incident_id=args.incident,
            quarantine_invalid=args.quarantine_invalid,
        )
    except (IncidentValidationError, SupportIncidentError, OSError):
        payload = {
            "status": "fail",
            "valid_incident_count": 0,
            "invalid_incident_count": 1,
            "quarantined_incident_count": 0,
            "incidents": [],
        }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
