"""
Roster data models -- DutyAssignment, WeeklyRoster, and validation logic.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import date

from models.enums import (
    Weekday, Room, Role, DutyType, AHPAssignmentMode, SchoolRules,
)
from models.prefect import Prefect


@dataclass
class DutyAssignment:
    """A single duty slot assignment for one prefect on one day.

    Can represent either an AHP exclusive post or a room duty assignment.
    """
    weekday: Weekday
    duty_type: DutyType
    prefect_name: str = ""
    room: Optional[Room] = None

    def __post_init__(self):
        """Validate assignment consistency."""
        if self.duty_type == DutyType.ROOM_DUTY and self.room is None:
            raise ValueError("Room duty assignment must specify a room.")
        if self.duty_type == DutyType.AHP_EXCLUSIVE and self.room is not None:
            raise ValueError("AHP exclusive posts should not have a room.")

    @property
    def is_ahp_post(self) -> bool:
        return self.duty_type == DutyType.AHP_EXCLUSIVE

    @property
    def is_room_duty(self) -> bool:
        return self.duty_type == DutyType.ROOM_DUTY


@dataclass
class DailyRoster:
    """A single day's complete roster (AHP post + all room assignments)."""
    weekday: Weekday
    date: Optional[date] = None
    ahp_assignment: Optional[DutyAssignment] = None
    room_assignments: Dict[Room, List[str]] = field(default_factory=dict)

    @property
    def total_assignments(self) -> int:
        count = 1 if self.ahp_assignment else 0
        count += sum(len(names) for names in self.room_assignments.values())
        return count

    def is_valid(self) -> List[str]:
        """Validate this day's roster against school rules. Returns list of violations."""
        errors: List[str] = []

        # AHP post check
        if self.ahp_assignment and self.ahp_assignment.duty_type != DutyType.AHP_EXCLUSIVE:
            errors.append("AHP assignment must have AHP_EXCLUSIVE duty type.")

        # Room capacity checks
        for room, names in self.room_assignments.items():
            # Check room is open
            if self.weekday in room.closed_days:
                errors.append(f"{room.value} is closed on {self.weekday.value}.")
            # Check capacity
            if len(names) > room.capacity:
                errors.append(
                    f"{room.value} over capacity: {len(names)} assigned, "
                    f"max {room.capacity}."
                )

        return errors


@dataclass
class WeeklyRoster:
    """A complete week's duty roster (Monday through Friday)."""
    week_start: date
    days: Dict[Weekday, DailyRoster] = field(default_factory=dict)
    ahp_mode: AHPAssignmentMode = AHPAssignmentMode.RANDOM

    def __post_init__(self):
        """Ensure all 5 weekdays have a DailyRoster."""
        for day in Weekday:
            if day not in self.days:
                self.days[day] = DailyRoster(weekday=day)

    @property
    def total_assignments(self) -> int:
        return sum(d.total_assignments for d in self.days.values())

    def get_ahp_assignments(self) -> Dict[Weekday, Optional[str]]:
        """Return {weekday: prefect_name} for AHP posts."""
        result: Dict[Weekday, Optional[str]] = {}
        for day, roster in self.days.items():
            result[day] = roster.ahp_assignment.prefect_name if roster.ahp_assignment else None
        return result

    def get_prefect_loads(self) -> Dict[str, float]:
        """Calculate load points for each prefect in this roster (for fairness)."""
        loads: Dict[str, float] = {}
        for day, roster in self.days.items():
            if roster.ahp_assignment and roster.ahp_assignment.prefect_name:
                name = roster.ahp_assignment.prefect_name
                loads[name] = loads.get(name, 0) + 1.0  # AHP post = 1 point
            for room, names in roster.room_assignments.items():
                for name in names:
                    loads[name] = loads.get(name, 0) + 1.0  # Room duty = 1 point
        return loads

    def validate(self) -> List[str]:
        """Validate entire roster against all school rules."""
        errors: List[str] = []
        for day in Weekday:
            roster = self.days.get(day)
            if roster:
                errors.extend(roster.is_valid())

        # AHP weekly uniqueness: each AHP max 1 per week
        ahp_names = [
            a.prefect_name
            for a in [d.ahp_assignment for d in self.days.values() if d.ahp_assignment]
            if a.prefect_name
        ]
        if len(ahp_names) != len(set(ahp_names)):
            errors.append("Each AHP can only be assigned once per week (duplicate AHP found).")

        return errors
