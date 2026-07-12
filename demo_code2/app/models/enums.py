"""Domain Enums and School Rules — Single Source of Truth.

ARCHITECTURE: ALL school-specific constraints live here. To change room
capacities, closed days, AHP count, or allowed forms, change this file.
roster_service.py and leave_service.py read from here — they do NOT define
their own constraints. See docs/ARCHITECTURE.md Section 4 for rationale.
"""
from enum import Enum, auto
from typing import List


class Role(str, Enum):
    """Prefect role hierarchy (Sing Yin Secondary School)."""
    HEAD_STUDY_PREFECT = "Head Study Prefect"
    ASSISTANT_HEAD_PREFECT = "Assistant Head Study Prefect"
    STUDY_PREFECT = "Study Prefect"

    @property
    def display(self) -> str:
        """Return display name (English)."""
        return self.value

    @property
    def display_zh(self) -> str:
        """Return Chinese display name."""
        mapping = {
            "Head Study Prefect": "首席學習風紀",
            "Assistant Head Study Prefect": "助理首席學習風紀",
            "Study Prefect": "學習風紀",
        }
        return mapping.get(self.value, self.value)

    @property
    def is_ahp(self) -> bool:
        """AHP can be assigned to the exclusive AHP duty post."""
        return self == Role.ASSISTANT_HEAD_PREFECT

    @property
    def is_leader(self) -> bool:
        """Leader roles (Head Prefect or AHP) have elevated permissions."""
        return self in (Role.HEAD_STUDY_PREFECT, Role.ASSISTANT_HEAD_PREFECT)

    @property
    def can_hold_ahp_post(self) -> bool:
        """Only AHPs can be assigned to AHP exclusive duty posts."""
        return self == Role.ASSISTANT_HEAD_PREFECT


class Form(str, Enum):
    """Year levels at Sing Yin Secondary School."""
    F3 = "F.3"
    F4 = "F.4"
    F5 = "F.5"


class Weekday(str, Enum):
    """Days of the school week (Monday to Friday)."""
    MON = "Monday"
    TUE = "Tuesday"
    WED = "Wednesday"
    THU = "Thursday"
    FRI = "Friday"

    @classmethod
    def all_days(cls) -> List["Weekday"]:
        return list(cls)

    @classmethod
    def count(cls) -> int:
        return 5


class Room(str, Enum):
    """Rooms available for ordinary prefect duty assignments.
    Room 202 is closed on Tuesday and Friday.
    """
    ROOM_302 = "Room 302"
    ROOM_303 = "Room 303"
    ROOM_202 = "Room 202"

    @property
    def capacity(self) -> int:
        """Daily capacity (prefects needed per day)."""
        _capacities = {
            Room.ROOM_302: 1,
            Room.ROOM_303: 2,
            Room.ROOM_202: 2,
        }
        return _capacities[self]

    @property
    def closed_days(self) -> List[Weekday]:
        """Days this room is unavailable."""
        _closed = {
            Room.ROOM_302: [],
            Room.ROOM_303: [],
            Room.ROOM_202: [Weekday.TUE, Weekday.FRI],
        }
        return _closed[self]

    @classmethod
    def all_rooms(cls) -> List["Room"]:
        return list(cls)

    @classmethod
    def total_daily_ordinary_slots(cls) -> int:
        """Total ordinary (non-AHP) prefect slots available per non-closed day."""
        return 5  # 302(1) + 303(2) + 202(2)


class AHPAssignmentMode(str, Enum):
    """Assignment mode for AHP exclusive duty posts."""
    RANDOM = "Random"
    FIXED = "Fixed"


class DutyType(str, Enum):
    """Type of duty assignment."""
    AHP_EXCLUSIVE = "AHP Exclusive Post"
    ROOM_DUTY = "Room Duty"
    LEAVE = "On Leave"


# =============================================================================
# SCHOOL RULES (immutable constants)
# =============================================================================

class SchoolRules:
    """Sing Yin Secondary School duty roster rules.
    These constants encode non-negotiable school policies.
    """
    # AHP Rules
    AHP_COUNT = 5                      # Number of AHPs in the system
    AHP_POSTS_PER_DAY = 1              # One exclusive AHP post per weekday
    AHP_POSTS_PER_WEEK = 5             # Total AHP posts per week
    AHP_MAX_ASSIGNMENTS_PER_WEEK = 1   # Each AHP max 1 per week

    # Room Rules
    ROOM_302_CAPACITY = 1
    ROOM_303_CAPACITY = 2
    ROOM_202_CAPACITY = 2
    ROOM_202_CLOSED_DAYS = (Weekday.TUE, Weekday.FRI)

    # Fairness
    WORKLOAD_MULTIPLIER_MIN = 0.8
    WORKLOAD_MULTIPLIER_MAX = 2.0
    WORKLOAD_MULTIPLIER_DEFAULT = 1.0

    # Forms (year levels) that participate
    ALLOWED_FORMS = (Form.F3, Form.F4, Form.F5)

    # Weekly slots
    DAYS_PER_WEEK = 5
    TOTAL_ORDINARY_SLOTS_PER_DAY = 5   # Sum of all room capacities
    TOTAL_AHP_SLOTS_PER_DAY = 1
    TOTAL_SLOTS_PER_DAY = 6
    TOTAL_SLOTS_PER_WEEK = 30
