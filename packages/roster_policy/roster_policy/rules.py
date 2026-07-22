from __future__ import annotations

from enum import Enum, IntEnum
import re


class RosterPolicyError(ValueError):
    """Raised when a duty assignment violates school roster policy."""


class SchoolDay(IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4


DAYS: tuple[SchoolDay, ...] = (
    SchoolDay.MONDAY,
    SchoolDay.TUESDAY,
    SchoolDay.WEDNESDAY,
    SchoolDay.THURSDAY,
    SchoolDay.FRIDAY,
)


class DutyPost(str, Enum):
    ASSIST_IN_CHARGE = "Assist. in charge"
    ROOM_302 = "Room 302"
    ROOM_303 = "Room 303"
    ROOM_202 = "Room 202"


class PrefectRole(str, Enum):
    """Stable policy identity for roster-eligible prefect roles.

    Human-readable Chinese and English labels belong to presentation adapters;
    policy decisions must never depend on translated text.
    """

    ASSISTANT_HEAD = "assistant_head"
    STUDY_PREFECT = "study_prefect"


class AssistAssignmentMode(str, Enum):
    """Stable policy codes for assigning the weekly Assist. in charge duty.

    ``LEGACY_FIXED_WEEKDAY`` preserves a canonical weekday for each Assistant
    Head Study Prefect. ``FLEXIBLE_WEEKLY`` deliberately rotates otherwise
    equivalent candidates between weeks. Human-readable labels belong to the
    presentation layer and must not be used as policy input.
    """

    LEGACY_FIXED_WEEKDAY = "legacy_fixed_weekday"
    FLEXIBLE_WEEKLY = "flexible_weekly"


_CHINESE_NAME_PATTERN = re.compile(
    r"^[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\U00020000-\U0002FA1F·・．\- ]+$"
)
_CHINESE_IDEOGRAPH_PATTERN = re.compile(
    r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\U00020000-\U0002FA1F]"
)


def is_chinese_display_name(value: str) -> bool:
    """Return whether a prefect's authoritative display name is Chinese.

    Presentation language never changes this value. Restrained separators are
    accepted for legitimate Chinese names, while Latin-only aliases and labels
    are rejected before they can enter a roster or PDF.
    """

    candidate = value.strip()
    ideograph_count = len(_CHINESE_IDEOGRAPH_PATTERN.findall(candidate))
    return 2 <= ideograph_count <= 8 and _CHINESE_NAME_PATTERN.fullmatch(candidate) is not None


DUTY_WEIGHTS: dict[DutyPost, float] = {
    DutyPost.ASSIST_IN_CHARGE: 1.0,
    DutyPost.ROOM_302: 1.0,
    DutyPost.ROOM_303: 1.5,
    DutyPost.ROOM_202: 1.5,
}


# A room can remain open after the prefect's scheduled service has ended.  Keep
# these two concepts separate so certificates never turn a room-closing time
# into service credit.
ROOM_OPENING_TIME_WINDOWS: dict[DutyPost, tuple[str, str]] = {
    DutyPost.ASSIST_IN_CHARGE: ("15:40", "18:30"),
    DutyPost.ROOM_302: ("15:40", "18:30"),
    DutyPost.ROOM_303: ("15:40", "17:00"),
    DutyPost.ROOM_202: ("15:40", "17:00"),
}


DUTY_SERVICE_TIME_WINDOWS: dict[DutyPost, tuple[str, str]] = {
    post: ("15:40", "17:00") for post in DutyPost
}


# Backwards-compatible display alias.  New code must select the explicit room
# opening or duty-service mapping above instead of depending on this name.
DUTY_TIME_WINDOWS = ROOM_OPENING_TIME_WINDOWS


ROOM_CAPACITY: dict[DutyPost, int] = {
    DutyPost.ASSIST_IN_CHARGE: 1,
    DutyPost.ROOM_302: 1,
    DutyPost.ROOM_303: 2,
    DutyPost.ROOM_202: 2,
}


ROOM_OPEN_DAYS: dict[DutyPost, set[SchoolDay]] = {
    DutyPost.ASSIST_IN_CHARGE: set(DAYS),
    DutyPost.ROOM_302: set(DAYS),
    DutyPost.ROOM_303: set(DAYS),
    DutyPost.ROOM_202: {
        SchoolDay.MONDAY,
        SchoolDay.WEDNESDAY,
        SchoolDay.THURSDAY,
    },
}


def is_ahp_role(role: PrefectRole) -> bool:
    return role is PrefectRole.ASSISTANT_HEAD


def is_regular_prefect_role(role: PrefectRole) -> bool:
    return role is PrefectRole.STUDY_PREFECT


def can_assign_role(role: PrefectRole, post: DutyPost) -> bool:
    if post is DutyPost.ASSIST_IN_CHARGE:
        return is_ahp_role(role)
    return is_regular_prefect_role(role)


def is_room_open(post: DutyPost, day: SchoolDay) -> bool:
    return day in ROOM_OPEN_DAYS[post]


def duty_weight(post: DutyPost) -> float:
    return DUTY_WEIGHTS[post]


def required_posts_for_day(day: SchoolDay) -> list[DutyPost]:
    posts: list[DutyPost] = []
    for post in (
        DutyPost.ASSIST_IN_CHARGE,
        DutyPost.ROOM_302,
        DutyPost.ROOM_303,
        DutyPost.ROOM_202,
    ):
        if is_room_open(post, day):
            posts.extend([post] * ROOM_CAPACITY[post])
    return posts
