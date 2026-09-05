"""Prelaunch-only pure policy and dated-seat compiler; not wired into the app.

No people, eligibility, fairness, persistence or earned service totals live here.
``service_minutes`` is the duration of one future assignment, including on a
closed display row; only effective published assignments may later earn it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
import re

from .rules import RosterPolicyError


class ConfigurationError(RosterPolicyError):
    """An explicit policy or exception decision is invalid."""


class ScheduleDateError(ConfigurationError):
    """A date selection cannot describe the requested ordinary/CP schedule."""


class TimeWindowError(ConfigurationError):
    """A service/opening window is not an increasing minute-precision period."""


class BusinessId(str, Enum):
    ASSIST_IN_CHARGE = "assist_in_charge"
    STUDY_ROOM = "study_room"
    HOMEWORK_COMPLETION = "homework_completion"
    FORM_1_STUDY_GROUP = "form_1_study_group"
    CP_FORM_1 = "cp_form_1"
    CP_FORM_2 = "cp_form_2"
    CP_FORM_3 = "cp_form_3"


class ScheduleMode(str, Enum):
    WEEKLY = "weekly"
    CP = "cp"


class SeatState(str, Enum):
    REQUIRED = "required"
    DAY_CLOSED = "day_closed"
    BUSINESS_CLOSED = "business_closed"
    UNAVAILABLE = "unavailable"


_WEEKLY_BUSINESSES = (
    BusinessId.ASSIST_IN_CHARGE, BusinessId.STUDY_ROOM,
    BusinessId.HOMEWORK_COMPLETION, BusinessId.FORM_1_STUDY_GROUP,
)
_CP_BUSINESSES = (BusinessId.CP_FORM_1, BusinessId.CP_FORM_2, BusinessId.CP_FORM_3)
_BUSINESS_NAMES = {
    BusinessId.ASSIST_IN_CHARGE: "Assist. in charge",
    BusinessId.STUDY_ROOM: "Study Room",
    BusinessId.HOMEWORK_COMPLETION: "Homework Completion",
    BusinessId.FORM_1_STUDY_GROUP: "Form 1 Study Group",
    BusinessId.CP_FORM_1: "CP Test Revision - Form 1",
    BusinessId.CP_FORM_2: "CP Test Revision - Form 2",
    BusinessId.CP_FORM_3: "CP Test Revision - Form 3",
}


def _minute_of_day(value: str) -> int:
    if not isinstance(value, str) or re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value) is None:
        raise TimeWindowError("Time must use HH:MM with no seconds or timezone.")
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


@dataclass(frozen=True)
class TimeWindow:
    start: str
    end: str
    minutes: int = field(init=False)

    def __post_init__(self) -> None:
        minutes = _minute_of_day(self.end) - _minute_of_day(self.start)
        if minutes <= 0:
            raise TimeWindowError("Start time must be before end time on the same date.")
        object.__setattr__(self, "minutes", minutes)


@dataclass(frozen=True)
class DutyTimes:
    opening: TimeWindow
    service: TimeWindow
    linked: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.opening, TimeWindow) or not isinstance(self.service, TimeWindow):
            raise TimeWindowError("Opening and service require explicit TimeWindow values.")
        if type(self.linked) is not bool:
            raise TimeWindowError("Time linkage must be an explicit boolean decision.")
        if self.linked and self.opening != self.service:
            raise TimeWindowError("Linked opening and service times must match; explicitly unlink to differ.")


def _items(values: object, label: str) -> tuple:
    if isinstance(values, (str, bytes)):
        raise ConfigurationError(f"{label} requires a collection, not text.")
    try:
        return tuple(values)
    except TypeError as error:
        raise ConfigurationError(f"{label} requires a collection.") from error


def _positive_integer(value: int, label: str) -> None:
    if type(value) is not int or value < 1:
        raise ConfigurationError(f"{label} must be a positive integer, not a boolean or decimal.")


@dataclass(frozen=True)
class BusinessSettings:
    business: BusinessId
    room: str | None
    capacity: int
    times: DutyTimes
    enabled: bool = True
    open_weekdays: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.business, BusinessId):
            raise ConfigurationError("Business identity must be a BusinessId, never a room number.")
        _positive_integer(self.capacity, "Capacity")
        if not isinstance(self.times, DutyTimes):
            raise TimeWindowError("Business hours require explicit DutyTimes.")
        if type(self.enabled) is not bool:
            raise ConfigurationError("Enabled must be an explicit boolean decision.")
        if self.room is None:
            if self.business is not BusinessId.ASSIST_IN_CHARGE:
                raise ConfigurationError("A room is required for this business, including CP groups.")
        elif not isinstance(self.room, str) or not self.room.strip() or any(
            ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF or char in "\u0085\u2028\u2029"
            for char in self.room
        ):
            raise ConfigurationError("Room must be nonempty single-line Unicode text.")
        else:
            object.__setattr__(self, "room", self.room.strip())
        if self.business in _WEEKLY_BUSINESSES:
            days = _items(self.open_weekdays, "Ordinary open weekdays")
            if any(type(day) is not int or day not in range(5) for day in days):
                raise ConfigurationError("Ordinary open weekdays must be integers 0 through 4.")
            if len(set(days)) != len(days):
                raise ConfigurationError("Ordinary open weekdays must not repeat.")
            object.__setattr__(self, "open_weekdays", tuple(sorted(days)))
        elif self.open_weekdays is not None:
            raise ConfigurationError("CP uses selected actual dates, never ordinary weekday restrictions.")


def _policy_businesses(values: object, expected: tuple[BusinessId, ...]) -> tuple[BusinessSettings, ...]:
    posts = _items(values, "Business settings")
    if not all(isinstance(post, BusinessSettings) for post in posts):
        raise ConfigurationError("Every business requires BusinessSettings.")
    if len(posts) != len(expected) or {post.business for post in posts} != set(expected):
        raise ConfigurationError("Each business of this schedule mode must appear exactly once.")
    if sum(post.capacity for post in posts) > 20:
        raise ConfigurationError("At most 20 display rows are allowed, including disabled businesses.")
    by_business = {post.business: post for post in posts}
    return tuple(by_business[business] for business in expected)


@dataclass(frozen=True)
class WeeklyPolicy:
    businesses: tuple[BusinessSettings, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "businesses", _policy_businesses(self.businesses, _WEEKLY_BUSINESSES))


@dataclass(frozen=True)
class CpPolicy:
    businesses: tuple[BusinessSettings, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "businesses", _policy_businesses(self.businesses, _CP_BUSINESSES))


def default_weekly_policy() -> WeeklyPolicy:
    window = TimeWindow("15:40", "17:00")
    times = DutyTimes(window, window)
    return WeeklyPolicy((
        BusinessSettings(BusinessId.ASSIST_IN_CHARGE, None, 1, times, open_weekdays=(0, 1, 2, 3, 4)),
        BusinessSettings(BusinessId.STUDY_ROOM, "407", 1, times, open_weekdays=(0, 1, 2, 3, 4)),
        BusinessSettings(BusinessId.HOMEWORK_COMPLETION, "406", 2, times, open_weekdays=(0, 1, 2, 3, 4)),
        BusinessSettings(BusinessId.FORM_1_STUDY_GROUP, "202", 2, times, enabled=False, open_weekdays=(0, 2, 3)),
    ))


def default_cp_policy(
    *, f1_room: str | None = None, f2_room: str | None = None, f3_room: str | None = None,
) -> CpPolicy:
    """Supply this activity's rooms; no previous year's rooms are inferred."""
    window = TimeWindow("08:55", "12:00")
    times = DutyTimes(window, window)
    return CpPolicy(tuple(
        BusinessSettings(business, room, 2, times)
        for business, room in zip(_CP_BUSINESSES, (f1_room, f2_room, f3_room), strict=True)
    ))


def _actual_date(value: date) -> None:
    if type(value) is not date:
        raise ScheduleDateError("An actual date is required, not a datetime, weekday or text.")


def _dates(values: object) -> tuple[date, ...]:
    dates = _items(values, "Actual dates")
    for value in dates:
        _actual_date(value)
    if len(set(dates)) != len(dates):
        raise ScheduleDateError("Actual dates must not repeat.")
    return tuple(sorted(dates))


@dataclass(frozen=True)
class SeatKey:
    duty_date: date
    business: BusinessId
    seat_index: int

    def __post_init__(self) -> None:
        _actual_date(self.duty_date)
        if not isinstance(self.business, BusinessId):
            raise ConfigurationError("Seat key requires a stable business identity.")
        _positive_integer(self.seat_index, "Seat index")

    @property
    def value(self) -> str:
        return f"{self.duty_date.isoformat()}:{self.business.value}:{self.seat_index}"


@dataclass(frozen=True)
class ApprovedUnavailable:
    seat: SeatKey
    approval_reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.seat, SeatKey):
            raise ConfigurationError("An approved unavailable exception requires a SeatKey.")
        if not isinstance(self.approval_reference, str) or not self.approval_reference.strip():
            raise ConfigurationError("An unavailable seat requires an explicit approval reference.")


@dataclass(frozen=True)
class ScheduleExceptions:
    closed_dates: tuple[date, ...] = ()
    unavailable: tuple[ApprovedUnavailable, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "closed_dates", _dates(self.closed_dates))
        entries = _items(self.unavailable, "Approved unavailable seats")
        if not all(isinstance(entry, ApprovedUnavailable) for entry in entries):
            raise ConfigurationError("Unavailable seats require explicit approved exceptions.")
        if len({entry.seat for entry in entries}) != len(entries):
            raise ConfigurationError("Approved unavailable seats must not repeat.")
        object.__setattr__(self, "unavailable", entries)


@dataclass(frozen=True)
class CompiledSeat:
    key: SeatKey
    state: SeatState


@dataclass(frozen=True)
class CompiledRow:
    business: BusinessId
    business_name: str
    room: str | None
    seat_index: int
    opening: TimeWindow
    service: TimeWindow
    service_minutes: int
    seats: tuple[CompiledSeat, ...]


@dataclass(frozen=True)
class CompiledSchedule:
    mode: ScheduleMode
    policy: WeeklyPolicy | CpPolicy
    dates: tuple[date, ...]
    rows: tuple[CompiledRow, ...]


def compile_weekly(
    policy: WeeklyPolicy, monday: date, *, exceptions: ScheduleExceptions = ScheduleExceptions(),
) -> CompiledSchedule:
    if not isinstance(policy, WeeklyPolicy):
        raise ConfigurationError("Ordinary compilation requires WeeklyPolicy.")
    _actual_date(monday)
    if monday.weekday() != 0:
        raise ScheduleDateError("An ordinary schedule must start on Monday.")
    if monday > date.max - timedelta(days=4):
        raise ScheduleDateError("The five ordinary dates exceed the supported calendar.")
    return _compile(policy, tuple(monday + timedelta(days=offset) for offset in range(5)), exceptions)


def compile_cp(
    policy: CpPolicy, *, start: date, end: date, selected_dates: tuple[date, ...],
    rooms_confirmed: bool = False, exceptions: ScheduleExceptions = ScheduleExceptions(),
) -> CompiledSchedule:
    if not isinstance(policy, CpPolicy):
        raise ConfigurationError("CP compilation requires CpPolicy.")
    if rooms_confirmed is not True:
        raise ConfigurationError("Explicitly confirm this CP activity's actual rooms.")
    _actual_date(start)
    _actual_date(end)
    if start > end:
        raise ScheduleDateError("CP start date must not be after its end date.")
    dates = _dates(selected_dates)
    if not dates:
        raise ScheduleDateError("Explicitly select at least one CP actual date.")
    if any(day < start or day > end for day in dates):
        raise ScheduleDateError("Every selected CP date must be inside the activity range.")
    return _compile(policy, dates, exceptions)


def _compile(
    policy: WeeklyPolicy | CpPolicy, dates: tuple[date, ...], exceptions: ScheduleExceptions,
) -> CompiledSchedule:
    if not isinstance(exceptions, ScheduleExceptions):
        raise ConfigurationError("Schedule exceptions require explicit ScheduleExceptions.")
    selected_dates = frozenset(dates)
    if not set(exceptions.closed_dates).issubset(selected_dates):
        raise ScheduleDateError("A closed date must be one of the selected actual dates.")
    unavailable = {entry.seat for entry in exceptions.unavailable}
    capacities = {post.business: post.capacity for post in policy.businesses}
    # Validate the few exceptions directly instead of materializing a second
    # complete date/seat matrix solely to test membership.
    if any(
        key.duty_date not in selected_dates
        or key.seat_index > capacities.get(key.business, 0)
        for key in unavailable
    ):
        raise ConfigurationError("An unavailable exception must identify an existing date and seat.")
    closed_dates = frozenset(exceptions.closed_dates)
    rows = []
    for post in policy.businesses:
        for index in range(1, post.capacity + 1):
            seats = []
            for day in dates:
                key = SeatKey(day, post.business, index)
                # Whole-day closure takes presentation precedence; the policy
                # still retains the business's own enabled/weekday decisions.
                if day in closed_dates:
                    state = SeatState.DAY_CLOSED
                elif not post.enabled or (post.open_weekdays is not None and day.weekday() not in post.open_weekdays):
                    state = SeatState.BUSINESS_CLOSED
                else:
                    state = SeatState.REQUIRED
                if key in unavailable:
                    if state is not SeatState.REQUIRED:
                        raise ConfigurationError("An already closed seat cannot also be approved unavailable.")
                    state = SeatState.UNAVAILABLE
                seats.append(CompiledSeat(key, state))
            rows.append(CompiledRow(
                post.business, _BUSINESS_NAMES[post.business], post.room, index,
                post.times.opening, post.times.service, post.times.service.minutes, tuple(seats),
            ))
    return CompiledSchedule(
        ScheduleMode.WEEKLY if isinstance(policy, WeeklyPolicy) else ScheduleMode.CP,
        policy, dates, tuple(rows),
    )
