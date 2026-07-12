"""roster.config.school_policy — Sing Yin Secondary School Policy Rules (SSOT)

This module is the authoritative Single Source of Truth for ALL school-specific
scheduling rules at Sing Yin Secondary School. Every scheduling constraint,
weight value, room closure, AHP restriction, and mentoring threshold is defined here
with documented rationale.
"""

from typing import List, Dict, Any

DAYS: List[str] = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]

ROOM_202_CLOSED_DAYS: List[str] = ["TUESDAY", "FRIDAY"]
ROOM_202_OPEN_DAYS: List[str] = ["MONDAY", "WEDNESDAY", "THURSDAY"]

ROOMS_CONFIG: Dict[str, Dict[str, Any]] = {
    "Assist. in charge": {"daily_slots": 1, "weight": 1.0, "available_weekdays": DAYS, "color": "assist", "allow_assistant_head_only": True, "display_name": "Assist. in charge"},
    "Room 302 (Study Room)": {"daily_slots": 1, "weight": 1.0, "available_weekdays": DAYS, "color": "room302", "allow_assistant_head_only": False, "display_name": "Room 302 (Study Room)"},
    "Room 303 (HW Completion)": {"daily_slots": 2, "weight": 1.5, "available_weekdays": DAYS, "color": "room303", "allow_assistant_head_only": False, "display_name": "Room 303 (HW Completion)"},
    "Room 202 (F1 Study Group)": {"daily_slots": 2, "weight": 1.5, "available_weekdays": ROOM_202_OPEN_DAYS, "color": "room202", "allow_assistant_head_only": False, "display_name": "Room 202 (F1 Study Group)"},
}

ROOM_ORDER: List[str] = ["Assist. in charge", "Room 302 (Study Room)", "Room 303 (HW Completion)", "Room 202 (F1 Study Group)"]

VALID_FORMS: List[str] = ["F.3", "F.4", "F.5", "F.6"]

AHP_LOAD_BONUS: float = -8.0

MENTEE_THRESHOLD: float = 2.0
MENTOR_THRESHOLD: float = 5.0
MENTORING_PAIR_BONUS: float = -2.0

GLOBAL_LOAD_RANGE: tuple = (0.8, 2.0)
DEFAULT_GLOBAL_LOAD_MULTIPLIER: float = 1.0

NO_CONSECUTIVE_DAYS: bool = True

MENTORING_ROOMS: List[str] = ["Room 303 (HW Completion)", "Room 202 (F1 Study Group)"]


def get_weight(role: str) -> float:
    """Return the weight (points) for a given duty role."""
    for key, cfg in ROOMS_CONFIG.items():
        if key in role:
            return cfg["weight"]
    return 1.5


def is_assistant_head_only_role(role: str) -> bool:
    """Return True if this role is restricted to Assistant Head Study Prefects only."""
    for key, cfg in ROOMS_CONFIG.items():
        if key in role:
            return cfg.get("allow_assistant_head_only", False)
    return False


def is_room_open_on_weekday(room: str, day: str) -> bool:
    """Return True if the given room is open on the specified day.

    Room 302/303: open Mon-Fri.
    Room 202: open Mon/Wed/Thu only (closed Tue/Fri for F.1 activities).
    """
    for key, cfg in ROOMS_CONFIG.items():
        if key in room:
            return day in cfg["available_weekdays"]
    return True


def get_daily_slots(role: str) -> int:
    """Return the number of duty slots per day for this role."""
    from roster.config.constants import get_base_role
    base = get_base_role(role)
    cfg = ROOMS_CONFIG.get(base, {})
    return cfg.get("daily_slots", 1)

