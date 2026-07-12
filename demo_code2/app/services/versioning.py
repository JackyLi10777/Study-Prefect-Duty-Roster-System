"""
Roster Version History Service — save/restore/view past generated rosters.

Stores up to 10 past WeeklyRoster objects in memory.
Each version records: timestamp, week_start, prefect_assignments snapshot.
"""

from datetime import datetime
from typing import List, Dict, Optional

_versions: List[Dict] = []
MAX_VERSIONS = 10


def save_version(roster) -> int:
    """Save a snapshot of the current roster as a version.

    Args:
        roster: A WeeklyRoster object with .week_start and .days.

    Returns:
        Version number (1-based).
    """
    snapshot = {
        "version": len(_versions) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "week_start": str(roster.week_start),
        "roster": roster,  # Reference to the live object
    }
    _versions.append(snapshot)
    if len(_versions) > MAX_VERSIONS:
        _versions.pop(0)
    return snapshot["version"]


def get_versions() -> List[Dict]:
    """Return list of version summaries (newest first)."""
    result = []
    for v in reversed(_versions):
        result.append({
            "version": v["version"],
            "timestamp": v["timestamp"],
            "week_start": v["week_start"],
        })
    return result


def get_version(version_num: int) -> Optional[Dict]:
    """Return a specific version by number (1-based), or None."""
    for v in _versions:
        if v["version"] == version_num:
            return v
    return None


def restore_version(version_num: int):
    """Return the roster snapshot for the given version, or None."""
    v = get_version(version_num)
    return v["roster"] if v else None


def clear_versions():
    """Clear all stored versions."""
    _versions.clear()
