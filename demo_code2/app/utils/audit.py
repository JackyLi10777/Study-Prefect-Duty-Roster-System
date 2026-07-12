"""
Simple Audit Logger for the Sing Yin Study Prefect Duty Roster System.

Tracks important system changes: roster generation, leave adjustments,
manual swaps, and backup/restore events.
"""

from datetime import datetime
from typing import Dict, List, Optional

# In-memory audit log (appends per session)
_audit_log: List[Dict] = []


def log_action(
    action: str,
    details: str = "",
    affected: list = None,
    impact: dict = None,
) -> None:
    """Record an audit entry.

    Args:
        action: Action type (e.g. "leave_adjustment", "manual_swap", "roster_generate")
        details: Human-readable description
        affected: List of prefect names affected
        impact: Dict with fairness impact (e.g. {"old_load": 3.5, "new_load": 2.0})
    """
    _audit_log.append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "details": details,
        "affected": affected or [],
        "impact": impact or {},
    })
    # Keep log bounded
    if len(_audit_log) > 1000:
        _audit_log[:] = _audit_log[-500:]


def get_log() -> List[Dict]:
    """Return the current audit log (newest first)."""
    return sorted(_audit_log, key=lambda e: e["timestamp"], reverse=True)


def get_recent(n: int = 10) -> List[Dict]:
    """Return the most recent n entries."""
    return get_log()[:n]


def clear_log() -> None:
    """Clear the audit log."""
    _audit_log.clear()


# =============================================================================
# Persistence layer -- saves audit log to disk so institutional memory survives
# application restarts. REGENERATIVE: the system learns across sessions.
# =============================================================================
import json as _json
from pathlib import Path as _Path

_AUDIT_FILE = _Path(__file__).resolve().parent.parent.parent / 'data' / 'audit_log.json'


def save_audit_log() -> bool:
    """Persist the current audit log to disk. Returns True on success."""
    try:
        _AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_AUDIT_FILE, 'w', encoding='utf-8') as f:
            _json.dump(_audit_log[-500:], f, ensure_ascii=False, indent=2, default=str)
        return True
    except Exception:
        return False


def load_audit_log() -> int:
    """Restore audit log from disk. Returns number of entries loaded."""
    global _audit_log
    try:
        if _AUDIT_FILE.exists():
            with open(_AUDIT_FILE, 'r', encoding='utf-8') as f:
                data = _json.load(f)
            _audit_log = data[-500:] if len(data) > 500 else data
            return len(_audit_log)
    except Exception:
        pass
    return 0


# Auto-load on module import
_load_count = load_audit_log()
if _load_count > 0:
    pass  # Silent -- the system regenerates its memory without ceremony
