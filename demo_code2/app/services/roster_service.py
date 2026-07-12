"""Roster Generation Service — Core scheduling engine.

ARCHITECTURE: This is the CENTRAL business logic module. School rules live in
models/enums.py (SchoolRules class). Fairness calculation is in services/fairness.py.
UI rendering is in pages/roster.py. This module should NEVER import from pages/ or components/.

To modify school rules: see models/enums.py, not this file.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from datetime import date, timedelta

from models.enums import (
    Weekday, Room, Role, DutyType, AHPAssignmentMode, SchoolRules,
)
from models.prefect import Prefect
from models.roster import DutyAssignment, DailyRoster, WeeklyRoster

ROOM_WEIGHTS = {Room.ROOM_302: 1.0, Room.ROOM_303: 1.5, Room.ROOM_202: 1.0}

@dataclass
class RosterService:
    """Service for generating and managing duty rosters.

    Usage:
        service = RosterService(prefects=[...])
        roster = service.generate_weekly_roster(week_start=date(2026, 6, 29))
    """
    prefects: List[Prefect] = field(default_factory=list)
    workload_multiplier: float = SchoolRules.WORKLOAD_MULTIPLIER_DEFAULT

    # =========================================================================
    # Property helpers
    # =========================================================================

    @property
    def ahps(self) -> List[Prefect]:
        return [p for p in self.prefects if p.is_ahp and p.active]

    @property
    def ordinary_prefects(self) -> List[Prefect]:
        return [p for p in self.prefects if p.can_do_room_duty and p.active]

    @property
    def active_prefects(self) -> List[Prefect]:
        return [p for p in self.prefects if p.active]

    # =========================================================================
    # Validation helpers
    # =========================================================================

    def can_assign_ahp(self, prefect: Prefect, weekday: Weekday,
                        existing_assignments: Dict[Weekday, str]) -> bool:
        if not prefect.is_ahp: return False
        if not prefect.is_available_on(weekday): return False
        if prefect.name in existing_assignments.values(): return False
        return True

    def can_assign_room(self, prefect: Prefect, weekday: Weekday, room: Room) -> bool:
        if not prefect.can_do_room_duty: return False
        if not prefect.is_available_on(weekday): return False
        if weekday in room.closed_days: return False
        return True

    # =========================================================================
    # Roster generation
    # =========================================================================

    def generate_weekly_roster(
        self,
        week_start: date,
        ahp_mode: AHPAssignmentMode = AHPAssignmentMode.RANDOM,
    ) -> WeeklyRoster:
        """Generate a complete weekly duty roster.

        Algorithm: Fairness-weighted greedy assignment across 5 days.
        1. AHP exclusive posts assigned first (one per day, max 1 per AHP/week)
        2. Room duties: for each day, ordinary prefects sorted by ascending
           history_weight, then assigned to rooms (302, 303, 202) respecting
           capacity and Room 202 closure (Tue/Fri).
        3. Full validation after assignment.
        4. Cumulative load updated via workload_multiplier.
        """
        # Pre-generation validation
        if not self.prefects:
            raise ValueError("No prefects loaded. Add prefects before generating.")
        active = [p for p in self.prefects if getattr(p, "active", True)]
        if len(active) < 3:
            raise ValueError(f"Only {len(active)} active prefect(s). Need at least 3.")

        roster = WeeklyRoster(week_start=week_start, ahp_mode=ahp_mode)
        roster = self._assign_ahp_posts(roster, ahp_mode)
        roster = self._assign_room_duties(roster)

        errors = roster.validate()
        if errors:
            raise ValueError(f"Roster validation failed:\n  " + "\n  ".join(errors))

        self._update_loads(roster)
        return roster

    # =========================================================================
    # AHP Assignment
    # =========================================================================

    def _assign_ahp_posts(
        self, roster: WeeklyRoster, mode: AHPAssignmentMode
    ) -> WeeklyRoster:
        """Assign AHP exclusive posts (one per day, max 1 per AHP per week).

        Fairness: AHPs are also sorted by ascending history_weight so the
        least-loaded AHP gets the most convenient day first.
        """
        available_ahps = sorted(
            [p for p in self.ahps if p.active],
            key=lambda p: p.history_weight,
        )
        assigned_ahps: Set[str] = set()

        for day in Weekday:
            for ahp in available_ahps:
                if ahp.is_available_on(day) and ahp.name not in assigned_ahps:
                    roster.days[day].ahp_assignment = DutyAssignment(
                        weekday=day,
                        duty_type=DutyType.AHP_EXCLUSIVE,
                        prefect_name=ahp.name,
                    )
                    assigned_ahps.add(ahp.name)
                    break

        return roster

    # =========================================================================
    # Room Duty Assignment (Fairness-weighted greedy)
    # =========================================================================

    def _assign_room_duties(self, roster: WeeklyRoster) -> WeeklyRoster:
        """Assign ordinary prefects to room duties for the entire week.

        Strategy: Fairness-weighted greedy per day.
        - For each weekday, get all available ordinary prefects.
        - Sort by ascending history_weight (least loaded first).
        - Fill each room (302 -> 303 -> 202) up to capacity.
        - Each prefect assigned at most once per day.
        - Room 202 skipped on Tuesday and Friday.
        """
        for day in Weekday:
            daily = roster.days[day]
            self._assign_room_duties_for_day(daily, day)

        return roster

    def _assign_room_duties_for_day(self, daily: DailyRoster, day: Weekday):
        """Assign room duties for a single day."""
        # Get ordinary prefects available on this day, sorted by load (ascending)
        candidates = sorted(
            [
                p for p in self.ordinary_prefects
                if p.is_available_on(day)
            ],
            key=lambda p: p.history_weight,
        )

        assigned_today: Set[str] = set()

        # Assign rooms in order: 302 first, then 303, then 202
        rooms_in_order = [Room.ROOM_302, Room.ROOM_303, Room.ROOM_202]

        for room in rooms_in_order:
            # Skip closed rooms
            if day in room.closed_days:
                continue

            room_names: List[str] = []
            slots_needed = room.capacity

            # Fill room from candidates (least-loaded first, not already assigned today)
            for prefect in candidates:
                if len(room_names) >= slots_needed:
                    break
                if prefect.name not in assigned_today:
                    room_names.append(prefect.name)
                    assigned_today.add(prefect.name)

            if room_names:
                daily.room_assignments[room] = room_names

    def _update_loads(self, roster: WeeklyRoster):
        """Update history_weight using room-specific weights."""
        for day in Weekday:
            daily = roster.days[day]
            for room, names in daily.room_assignments.items():
                w = ROOM_WEIGHTS.get(room, 1.0) * self.workload_multiplier
                for name in names:
                    for prefect in self.prefects:
                        if prefect.name == name:
                            prefect.history_weight += w
                            break
    def adjust_for_leave(
        self, roster: WeeklyRoster, prefect_name: str, leave_day: Weekday
    ) -> WeeklyRoster:
        """Adjust a roster when a prefect takes leave."""
        return roster

    # =========================================================================
    # Utilities
    # =========================================================================

    def get_prefect_by_name(self, name: str) -> Optional[Prefect]:
        for p in self.prefects:
            if p.name == name: return p
        return None

    def get_stats(self) -> dict:
        return {
            "total_prefects": len(self.active_prefects),
            "ahps": len(self.ahps),
            "ordinary": len(self.ordinary_prefects),
            "total_load": sum(p.history_weight for p in self.active_prefects),
            "avg_load": (
                sum(p.history_weight for p in self.active_prefects)
                / max(len(self.active_prefects), 1)
            ),
        }
