from __future__ import annotations

from enum import Enum, IntEnum


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


DUTY_WEIGHTS: dict[DutyPost, float] = {
    DutyPost.ASSIST_IN_CHARGE: 1.0,
    DutyPost.ROOM_302: 1.0,
    DutyPost.ROOM_303: 1.5,
    DutyPost.ROOM_202: 1.5,
}


# Displayed by every interface from the same policy source; not a UI-only copy.
DUTY_TIME_WINDOWS: dict[DutyPost, tuple[str, str]] = {
    DutyPost.ASSIST_IN_CHARGE: ("15:45", "18:00"),
    DutyPost.ROOM_302: ("15:45", "18:00"),
    DutyPost.ROOM_303: ("15:45", "17:00"),
    DutyPost.ROOM_202: ("15:45", "17:00"),
}


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


def is_ahp_role(role: str) -> bool:
    normalized = role.casefold()
    return "assistant head study prefect" in normalized or "助理首席導學風紀" in role


def is_regular_prefect_role(role: str) -> bool:
    return not is_ahp_role(role)


def can_assign_role(role: str, post: DutyPost) -> bool:
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
