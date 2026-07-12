"""
Mentoring Service for the Sing Yin Study Prefect Duty Roster System.

Detects mentor-mentee pairs in 2-slot rooms (Room 303 and Room 202).
A pair forms when an experienced prefect (mentor) is assigned alongside
a junior or new prefect (mentee) in the same room on the same day.

Mentee criteria: F.3 student, or low history_weight (< 1.0)
Mentor criteria: F.4-F.6 student, history_weight > 0, not a mentee themselves
"""

from typing import Dict, List, Optional, Tuple
from models.enums import Room, Weekday, Form
from models.roster import WeeklyRoster

# 2-slot rooms where mentoring pairs can form
PAIR_ROOMS = [Room.ROOM_303, Room.ROOM_202]


def _is_mentee(prefect) -> bool:
    """Check if a prefect qualifies as a mentee (needs mentoring)."""
    form = getattr(prefect, "form", None)
    weight = getattr(prefect, "history_weight", 0)
    needs = getattr(prefect, "needs_mentoring", False) if hasattr(prefect, "needs_mentoring") else False
    is_f3 = (form == Form.F3) if hasattr(form, "name") else str(form) == "F3"
    return is_f3 or needs or weight < 1.0


def _is_mentor(prefect) -> bool:
    """Check if a prefect qualifies as a mentor."""
    form = getattr(prefect, "form", None)
    weight = getattr(prefect, "history_weight", 0)
    is_f3 = (form == Form.F3) if hasattr(form, "name") else str(form) == "F3"
    needs = getattr(prefect, "needs_mentoring", False) if hasattr(prefect, "needs_mentoring") else False
    return (not is_f3) and (not needs) and weight > 0


def compute_possible_pairs(roster: WeeklyRoster) -> int:
    """Count how many 2-slot room-days are structurally open for pairing.

    Room 303: 5 days x 1 pair = 5
    Room 202: 3 open days (Mon/Wed/Thu) = 3
    Total: 8 possible pairs in standard Sing Yin config.
    """
    possible = 0
    for room in PAIR_ROOMS:
        for day in Weekday:
            daily = roster.days.get(day)
            if not daily:
                continue
            if day in getattr(room, "closed_days", []):
                continue
            assigned = daily.room_assignments.get(room, [])
            # Both slots must be structurally open (not marked as closed)
            if len(assigned) >= 2:
                possible += 1
            elif len(assigned) == 0:
                possible += 1  # Both slots open
            # If exactly 1 slot filled, it's not a pair-able day
    return possible


def detect_pairs(roster: WeeklyRoster, prefects: list) -> List[Dict]:
    """Detect actual mentor-mentee pairs in the current roster.

    Returns a list of dicts:
        {day: Weekday, room: Room, mentor: str, mentee: str}
    """
    # Build lookup: name -> prefect
    lookup = {}
    for p in prefects:
        name = p.name if hasattr(p, "name") else p.get("name", "")
        if name:
            lookup[name] = p

    pairs = []
    for room in PAIR_ROOMS:
        for day in Weekday:
            daily = roster.days.get(day)
            if not daily:
                continue
            if day in getattr(room, "closed_days", []):
                continue
            assigned = daily.room_assignments.get(room, [])
            if len(assigned) < 2:
                continue
            # Check each pair of assignees
            names = [n for n in assigned if n and n.strip() and n.strip() != "[ON LEAVE]"]
            if len(names) < 2:
                continue
            # Find mentor and mentee in this pair
            mentors = [n for n in names if n in lookup and _is_mentor(lookup[n])]
            mentees = [n for n in names if n in lookup and _is_mentee(lookup[n])]
            if mentors and mentees:
                pairs.append({
                    "day": day,
                    "room": room,
                    "mentor": mentors[0],
                    "mentee": mentees[0],
                })
    return pairs


def get_pairing_stats(roster: WeeklyRoster, prefects: list) -> Dict:
    """Return summary stats about mentoring pairs.

    Returns:
        {possible: int, actual: int, pairs: List[Dict], pct: float}
    """
    possible = compute_possible_pairs(roster)
    actual_pairs = detect_pairs(roster, prefects)
    pct = (len(actual_pairs) / possible * 100) if possible > 0 else 0
    return {
        "possible": possible,
        "actual": len(actual_pairs),
        "pairs": actual_pairs,
        "pct": round(pct, 1),
    }
