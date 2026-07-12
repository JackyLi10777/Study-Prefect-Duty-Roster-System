"""Tests for the Roster data models."""
import pytest
from datetime import date
from models.enums import Weekday, Room, DutyType, AHPAssignmentMode
from models.roster import DutyAssignment, DailyRoster, WeeklyRoster
from models.prefect import Prefect
from models.enums import Role, Form


class TestDutyAssignment:
    def test_room_duty_requires_room(self):
        with pytest.raises(ValueError, match="must specify a room"):
            DutyAssignment(weekday=Weekday.MON, duty_type=DutyType.ROOM_DUTY)

    def test_ahp_post_should_not_have_room(self):
        with pytest.raises(ValueError, match="should not have a room"):
            DutyAssignment(
                weekday=Weekday.MON,
                duty_type=DutyType.AHP_EXCLUSIVE,
                room=Room.ROOM_302,
            )

    def test_valid_ahp_assignment(self):
        a = DutyAssignment(
            weekday=Weekday.MON,
            duty_type=DutyType.AHP_EXCLUSIVE,
            prefect_name="WONG Siu Ming",
        )
        assert a.is_ahp_post
        assert not a.is_room_duty


class TestDailyRoster:
    def test_room_202_closed_tuesday(self):
        dr = DailyRoster(weekday=Weekday.TUE)
        dr.room_assignments[Room.ROOM_202] = ["A", "B"]
        errors = dr.is_valid()
        assert any("closed" in e for e in errors)

    def test_room_over_capacity(self):
        dr = DailyRoster(weekday=Weekday.WED)
        dr.room_assignments[Room.ROOM_302] = ["A", "B", "C"]  # Capacity is 1
        errors = dr.is_valid()
        assert any("over capacity" in e for e in errors)

    def test_valid_daily_roster(self):
        dr = DailyRoster(weekday=Weekday.WED)
        dr.ahp_assignment = DutyAssignment(
            weekday=Weekday.WED,
            duty_type=DutyType.AHP_EXCLUSIVE,
            prefect_name="AHP1",
        )
        dr.room_assignments[Room.ROOM_302] = ["A"]
        dr.room_assignments[Room.ROOM_303] = ["B", "C"]
        assert dr.is_valid() == []


class TestWeeklyRoster:
    def test_creates_all_five_days(self):
        wr = WeeklyRoster(week_start=date(2026, 6, 29))
        assert len(wr.days) == 5
        for day in Weekday:
            assert day in wr.days

    def test_total_assignments(self):
        wr = WeeklyRoster(week_start=date(2026, 6, 29))
        wr.days[Weekday.MON].ahp_assignment = DutyAssignment(
            weekday=Weekday.MON,
            duty_type=DutyType.AHP_EXCLUSIVE,
            prefect_name="AHP1",
        )
        wr.days[Weekday.MON].room_assignments[Room.ROOM_302] = ["A"]
        assert wr.total_assignments == 2

    def test_duplicate_ahp_detected(self):
        wr = WeeklyRoster(week_start=date(2026, 6, 29))
        wr.days[Weekday.MON].ahp_assignment = DutyAssignment(
            weekday=Weekday.MON, duty_type=DutyType.AHP_EXCLUSIVE, prefect_name="AHP1"
        )
        wr.days[Weekday.TUE].ahp_assignment = DutyAssignment(
            weekday=Weekday.TUE, duty_type=DutyType.AHP_EXCLUSIVE, prefect_name="AHP1"
        )
        errors = wr.validate()
        assert any("once per week" in e for e in errors)
