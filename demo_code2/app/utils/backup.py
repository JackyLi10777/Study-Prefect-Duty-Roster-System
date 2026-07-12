"""
JSON Backup / Restore Module for Sing Yin Study Prefect Duty Roster System.

Exports the complete system state as a downloadable JSON file,
and supports safe restore with confirmation and data integrity checks.
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

BACKUP_VERSION = "1.0"


def export_backup(prefects: list, roster=None, audit_log: list = None,
                  extra: dict = None) -> str:
    """Export the complete system state as a JSON string.

    Args:
        prefects: List of Prefect objects or dicts.
        roster: Optional WeeklyRoster object.
        audit_log: Optional list of audit entries.
        extra: Optional dict of extra state (config, etc.).

    Returns:
        JSON string ready for download.
    """
    # Serialize prefects
    prefect_data = []
    for p in prefects:
        if hasattr(p, "name"):
            prefect_data.append({
                "name": p.name,
                "name_zh": getattr(p, "name_zh", ""),
                "form": p.form.name if hasattr(p.form, "name") else str(p.form),
                "class_name": getattr(p, "class_name", ""),
                "role": p.role.name if hasattr(p.role, "name") else str(p.role),
                "available": [d.name for d in p.available] if hasattr(p, "available") and p.available else [],
                "history_weight": p.history_weight,
                "remarks": getattr(p, "remarks", ""),
                "active": getattr(p, "active", True),
            })
        elif isinstance(p, dict):
            prefect_data.append({
                "name": p.get("name", ""),
                "name_zh": p.get("name_zh", ""),
                "form": p["form"].name if hasattr(p["form"], "name") else str(p.get("form", "")),
                "class_name": p.get("class_name", ""),
                "role": p["role"].name if hasattr(p["role"], "name") else str(p.get("role", "")),
                "available": [d.name if hasattr(d, "name") else str(d) for d in p.get("available", [])],
                "history_weight": p.get("history_weight", 0),
                "remarks": p.get("remarks", ""),
                "active": p.get("active", True),
            })

    # Serialize roster
    roster_data = None
    if roster:
        roster_data = {
            "week_start": str(roster.week_start),
            "days": {}
        }
        for day_raw in roster.days:
            daily = roster.days[day_raw]
            day_key = day_raw.name if hasattr(day_raw, "name") else str(day_raw)
            roster_data["days"][day_key] = {
                "room_assignments": {}
            }
            for room_raw, names in daily.room_assignments.items():
                room_key = room_raw.name if hasattr(room_raw, "name") else str(room_raw)
                roster_data["days"][day_key]["room_assignments"][room_key] = names

    backup = {
        "version": BACKUP_VERSION,
        "exported_at": datetime.now().isoformat(),
        "prefects": prefect_data,
        "roster": roster_data,
        "audit_log": audit_log or [],
        "extra": extra or {},
    }
    return json.dumps(backup, ensure_ascii=False, indent=2)


def import_backup(json_str: str) -> dict:
    """Parse a backup JSON string and return the data dict.

    Returns dict with keys: version, prefects, roster, audit_log, extra.
    Raises ValueError if the JSON is invalid or missing required fields.
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    if "version" not in data:
        raise ValueError("Missing backup version field.")
    if "prefects" not in data:
        raise ValueError("Missing prefects data in backup.")

    return data


def import_safe(data: dict, current_prefects: list) -> dict:
    """Safely merge backup data with current state.

    Returns a dict with validation results and warnings.
    """
    warnings = []
    backup_prefects = data.get("prefects", [])
    if len(backup_prefects) == 0:
        warnings.append("Backup contains no prefects.")
    if len(backup_prefects) < 5:
        warnings.append(f"Backup only has {len(backup_prefects)} prefects (expected >= 5).")

    return {
        "valid": True,
        "warnings": warnings,
        "prefect_count": len(backup_prefects),
        "has_roster": data.get("roster") is not None,
        "audit_entries": len(data.get("audit_log", [])),
    }


def restore_state(data: dict, prefects: list) -> dict:
    """Safely apply backup data to the current prefects list."""
    bp = {p["name"]: p for p in data.get("prefects", [])}
    updated = 0
    skipped = 0
    warnings = []
    for p in prefects:
        name = p.name if hasattr(p, "name") else p.get("name", "")
        if name in bp:
            b = bp[name]
            w = float(b.get("history_weight", 0))
            if hasattr(p, "history_weight"):
                if abs(p.history_weight - w) > 0.01:
                    updated += 1
                p.history_weight = w
            else:
                if abs(p.get("history_weight", 0) - w) > 0.01:
                    updated += 1
                p["history_weight"] = w
            if hasattr(p, "active"):
                p.active = b.get("active", True)
        else:
            skipped += 1
    if skipped:
        warnings.append(f"{skipped} prefects not in backup (unchanged).")
    return {"updated": updated, "skipped": skipped, "warnings": warnings, "backup_date": data.get("exported_at", "?"), "prefect_count": len(bp)}


def restore_audit_log(data: dict) -> int:
    """Restore audit log from backup data."""
    from utils.audit import _audit_log as log_ref
    backup_log = data.get("audit_log", [])
    if backup_log:
        log_ref.clear()
        log_ref.extend(backup_log)
    return len(backup_log)

def silent_backup(prefects: list, label: str = "auto") -> bool:
    """Perform a silent auto-backup before a destructive operation.

    Saves to data/auto_backups/ with timestamp. Does not disturb the user.
    Returns True on success, False on failure (never raises).

    REGENERATIVE: The system protects its own memory before risky changes.
    """
    import os as _os
    from datetime import datetime as _dt
    try:
        _os.makedirs("data/auto_backups", exist_ok=True)
        ts = _dt.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/auto_backups/auto_{label}_{ts}.json"
        json_str = export_backup(prefects=prefects)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(json_str)
        return True
    except Exception:
        return False

