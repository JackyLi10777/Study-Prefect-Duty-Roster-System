"""Leave Adjustment Service — Post-publication leave handling.

ARCHITECTURE: This module handles leave AFTER roster generation. See
services/roster_service.py for the roster engine. UI is in pages/leave.py.
Retry logic is in utils/sheets.py (separate from this module).
"""

from typing import List, Dict, Tuple, Optional, Set

from models.enums import Weekday, Room
from models.roster import WeeklyRoster


# Leave markers (mirroring D:/code engine.py _UNASSIGNED_MARKERS)
_UNASSIGNED_MARKERS = {"", "X", "⬜", "Leave Revoked"}
LEAVE_MARKER = "[ON LEAVE]"


class LeaveAdjustmentService:
    """Service for handling leave requests on a published roster."""

    def __init__(self, prefects: list = None):
        self.prefects = prefects or []

    def find_affected_assignments(
        self, roster: WeeklyRoster, prefect_name: str
    ) -> List[Dict]:
        """Find all assignments for a prefect in the roster.

        Returns list of dicts: {day, room, slot_idx, current_name}
        """
        affected = []
        for day in Weekday:
            daily = roster.days.get(day)
            if not daily:
                continue
            for room_enum, names in daily.room_assignments.items():
                # Skip Room 202 on closed days
                if room_enum == Room.ROOM_202 and day in (Weekday.TUE, Weekday.FRI):
                    continue
                for idx, name in enumerate(names):
                    if name.strip() == prefect_name.strip():
                        affected.append({
                            "day": day,
                            "room": room_enum,
                            "slot_idx": idx,
                            "current_name": name,
                        })
        return affected

    def get_replacement_candidates(
        self, day: Weekday, room: Room, exclude_names: set = None
    ) -> List[dict]:
        """Get candidates who can replace for this (day, room).

        Filters: available on day, not AHP for regular rooms, not already
        assigned that day. Sorted by history_weight ascending (fairness).
        """
        exclude = exclude_names or set()
        candidates = []
        for p in self.prefects:
            name = p.name if hasattr(p, "name") else p.get("name", "")
            if name in exclude:
                continue
            # Check availability
            available = p.available if hasattr(p, "available") else p.get("available", [])
            if day not in available:
                continue
            # AHP check: only AHPs can take AHP slots (currently handled separately)
            history_weight = (
                p.history_weight if hasattr(p, "history_weight")
                else p.get("history_weight", 0)
            )
            candidates.append({"name": name, "history_weight": history_weight})
        # Sort by fairness: lowest load first
        candidates.sort(key=lambda c: c["history_weight"])
        return candidates

    def apply_adjustment(
        self,
        roster: WeeklyRoster,
        prefect_name: str,
        day: Weekday,
        room: Room,
        slot_idx: int,
        replacement_name: Optional[str] = None,
        room_weight: float = 1.0,
    ) -> str:
        """Apply a single leave adjustment:
        - Remove original prefect from the slot
        - Optionally assign a replacement
        - Update history_weight for both

        Returns a status message.
        """
        if roster is None:
            return "No roster data available. Generate a roster first."
        if not prefect_name or not prefect_name.strip():
            return "Prefect name is required."
        daily = roster.days.get(day)
        if not daily:
            return f"No roster data for {day.name}."

        assigned = daily.room_assignments.get(room, [])
        if slot_idx >= len(assigned):
            return f"Slot {slot_idx} does not exist for {room.name} on {day.name}."

        # Revoke points from the original prefect
        self._adjust_weight(prefect_name, -room_weight)

        # Assign replacement
        if replacement_name:
            assigned[slot_idx] = replacement_name
            self._adjust_weight(replacement_name, room_weight)
            return (
                f"Replaced {prefect_name} with {replacement_name} "
                f"on {day.name} in {room.name}."
            )
        else:
            assigned[slot_idx] = "[ON LEAVE]"
            return f"Marked {prefect_name} on leave for {day.name} in {room.name}."

    def _adjust_weight(self, name: str, delta: float):
        """Adjust a prefect's history_weight by delta."""
        for p in self.prefects:
            pname = p.name if hasattr(p, "name") else p.get("name", "")
            if pname.strip() == name.strip():
                if hasattr(p, "history_weight"):
                    p.history_weight = max(0, p.history_weight + delta)
                else:
                    p["history_weight"] = max(0, p.get("history_weight", 0) + delta)
                break

    def get_available_prefects(self) -> List[str]:
        """Return all prefect names."""
        names = []
        for p in self.prefects:
            n = p.name if hasattr(p, "name") else p.get("name", "")
            if n:
                names.append(n)
        return sorted(names)

    def get_prefect_load(self, name: str) -> float:
        """Return a prefect's current history_weight."""
        for p in self.prefects:
            pname = p.name if hasattr(p, "name") else p.get("name", "")
            if pname.strip() == name.strip():
                if hasattr(p, "history_weight"):
                    return p.history_weight
                return p.get("history_weight", 0)
        return 0.0

    def swap_assignment(
        self,
        roster: WeeklyRoster,
        day: Weekday,
        room: Room,
        slot_idx: int,
        old_name: str,
        new_name: str,
        room_weight: float = 1.0,
    ) -> str:
        """Swap an assignment: remove old_name, assign new_name, update weights."""
        daily = roster.days.get(day)
        if not daily:
            return f"No data for {day.name}."
        assigned = daily.room_assignments.get(room, [])
        if slot_idx >= len(assigned):
            return f"Slot {slot_idx} out of range."
        if assigned[slot_idx].strip() != old_name.strip():
            return f"Expected {old_name} but found {assigned[slot_idx]}."

        self._adjust_weight(old_name, -room_weight)
        assigned[slot_idx] = new_name
        self._adjust_weight(new_name, room_weight)
        return f"Swapped {old_name} -> {new_name} ({room_weight} pts)"


    def get_all_assignments_for_day(
        self, roster: WeeklyRoster, day: Weekday, exclude_name: str = ""
    ) -> set:
        """Get all assigned prefect names on a given day, excluding one name.

        Mirrors D:/code per-day duplicate check: no prefect assigned
        twice on the same day after adjustment.
        """
        daily = roster.days.get(day)
        if not daily:
            return set()
        names = set()
        for room_enum, assigned in daily.room_assignments.items():
            for name in assigned:
                name = name.strip()
                if name and name != exclude_name and name not in _UNASSIGNED_MARKERS and name != LEAVE_MARKER:
                    names.add(name)
        return names

    def get_assigned_days(
        self, roster: WeeklyRoster, prefect_name: str
    ) -> list:
        """Get all days a prefect is assigned. Mirrors D:/code per-day check."""
        days = []
        for day in Weekday:
            daily = roster.days.get(day)
            if not daily:
                continue
            for room_enum, names in daily.room_assignments.items():
                if prefect_name.strip() in [n.strip() for n in names]:
                    days.append(day)
        return days

    def get_replacement_with_day_check(
        self, roster: WeeklyRoster, day: Weekday, room: Room,
        exclude_names: set = None
    ) -> list:
        """Enhanced replacement candidates with per-day assignment check.

        Prevents assigning a prefect who already has a duty on the same day.
        This mirrors D:/code safety behavior.
        """
        exclude = exclude_names or set()
        already_on_day = self.get_all_assignments_for_day(roster, day)
        exclude = exclude | already_on_day
        candidates = []
        for p in self.prefects:
            name = p.name if hasattr(p, "name") else p.get("name", "")
            if name in exclude:
                continue
            available = p.available if hasattr(p, "available") else p.get("available", [])
            if day not in available:
                continue
            history_weight = (
                p.history_weight if hasattr(p, "history_weight")
                else p.get("history_weight", 0)
            )
            candidates.append({"name": name, "history_weight": history_weight})
        candidates.sort(key=lambda c: c["history_weight"])
        return candidates

    def preview_adjustment(
        self,
        roster: WeeklyRoster,
        prefect_name: str,
        day: Weekday,
        room: Room,
        slot_idx: int,
        replacement_name: str = None,
        room_weight: float = 1.0,
    ) -> dict:
        """Preview the impact of a leave adjustment before applying.

        Returns fairness impact for both prefects and any safety warnings.
        This mirrors D:/code pre-apply confirmation flow.
        """
        daily = roster.days.get(day)
        current = (
            daily.room_assignments.get(room, [])[slot_idx]
            if daily and slot_idx < len(daily.room_assignments.get(room, []))
            else ""
        )
        old_load = self.get_prefect_load(prefect_name)
        new_load = (
            self.get_prefect_load(replacement_name)
            if replacement_name else 0
        )
        return {
            "day": day.name,
            "room": room.name,
            "slot_idx": slot_idx,
            "current_assignment": current,
            "original_prefect": prefect_name,
            "original_load_before": old_load,
            "original_load_after": max(0, old_load - room_weight),
            "replacement": replacement_name,
            "replacement_load_before": new_load if replacement_name else None,
            "replacement_load_after": (
                new_load + room_weight if replacement_name else None
            ),
            "room_weight": room_weight,
        }

    def validate_post_adjustment(
        self, roster: WeeklyRoster, prefect_name: str
    ) -> dict:
        """Validate roster consistency after a leave adjustment.

        Mirrors D:/code validate_post_adjustment_roster():
        - typo: names not matching any known prefect
        - leave_conflict: leave person still assigned elsewhere
        - vacuum: empty/unfilled slots (excluding Room 202 closed days)
        """
        errors = {"typo": [], "leave_conflict": [], "vacuum": []}
        known_names = set()
        for p in self.prefects:
            n = p.name if hasattr(p, "name") else p.get("name", "")
            if n:
                known_names.add(n.strip())

        for day in Weekday:
            daily = roster.days.get(day)
            if not daily:
                continue
            for room_enum, assigned in daily.room_assignments.items():
                if room_enum == Room.ROOM_202 and day in (Weekday.TUE, Weekday.FRI):
                    continue
                for slot_idx, name in enumerate(assigned):
                    name = name.strip()
                    if name and name not in _UNASSIGNED_MARKERS and name != LEAVE_MARKER:
                        if name not in known_names:
                            errors["typo"].append(
                                str(day.name) + " - " + str(room_enum.name)
                                + " slot " + str(slot_idx)
                                + ": " + name + " not in prefect list"
                            )
                    if name == prefect_name.strip():
                        errors["leave_conflict"].append(
                            str(day.name) + " - " + str(room_enum.name)
                            + " slot " + str(slot_idx)
                            + ": " + prefect_name
                            + " on leave but still assigned"
                        )
                    if not name or name in _UNASSIGNED_MARKERS:
                        errors["vacuum"].append(
                            str(day.name) + " - " + str(room_enum.name)
                            + " slot " + str(slot_idx)
                            + ": unfilled"
                        )

        return {
            "typo": (len(errors["typo"]) > 0, errors["typo"]),
            "leave_conflict": (
                len(errors["leave_conflict"]) > 0,
                errors["leave_conflict"],
            ),
            "vacuum": (len(errors["vacuum"]) > 0, errors["vacuum"]),
            "has_errors": (
                len(errors["typo"]) > 0
                or len(errors["leave_conflict"]) > 0
                or len(errors["vacuum"]) > 0
            ),
        }

    def swap_preview(
        self, old_name: str, new_name: str, room_weight: float = 1.0
    ) -> dict:
        """Preview the fairness impact before swapping."""
        old_load = self.get_prefect_load(old_name)
        new_load = self.get_prefect_load(new_name)
        return {
            "old_name": old_name,
            "old_current": old_load,
            "old_after": max(0, old_load - room_weight),
            "new_name": new_name,
            "new_current": new_load,
            "new_after": new_load + room_weight,
            "room_weight": room_weight,
        }
