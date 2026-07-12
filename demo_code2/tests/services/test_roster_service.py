"""Tests for the RosterService room duty generation algorithm."""
import pytest
from datetime import date

from models.enums import Role, Form, Weekday, Room, AHPAssignmentMode, SchoolRules
from models.prefect import Prefect
from models.roster import WeeklyRoster, DutyAssignment, DutyType
from services.roster_service import RosterService
from services.fairness import FairnessService


def _make_prefects_for_tests() -> list:
    """Create a realistic set of prefects for testing the algorithm."""
    return [
        Prefect(name="AHP1", form=Form.F4, role=Role.ASSISTANT_HEAD_PREFECT,
                available=[Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI]),
        Prefect(name="AHP2", form=Form.F5, role=Role.ASSISTANT_HEAD_PREFECT,
                available=[Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI]),
        Prefect(name="AHP3", form=Form.F4, role=Role.ASSISTANT_HEAD_PREFECT,
                available=[Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI]),
        Prefect(name="AHP4", form=Form.F5, role=Role.ASSISTANT_HEAD_PREFECT,
                available=[Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI]),
        Prefect(name="AHP5", form=Form.F4, role=Role.ASSISTANT_HEAD_PREFECT,
                available=[Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI]),
        Prefect(name="P1", form=Form.F4, role=Role.STUDY_PREFECT,
                available=[Weekday.MON, Weekday.WED, Weekday.FRI], history_weight=0),
        Prefect(name="P2", form=Form.F4, role=Role.STUDY_PREFECT,
                available=[Weekday.MON, Weekday.TUE, Weekday.THU], history_weight=5),
        Prefect(name="P3", form=Form.F5, role=Role.STUDY_PREFECT,
                available=[Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI], history_weight=3),
        Prefect(name="P4", form=Form.F3, role=Role.STUDY_PREFECT,
                available=[Weekday.TUE, Weekday.WED, Weekday.THU], history_weight=2),
        Prefect(name="P5", form=Form.F4, role=Role.STUDY_PREFECT,
                available=[Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI], history_weight=1),
        Prefect(name="P6", form=Form.F5, role=Role.STUDY_PREFECT,
                available=[Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI], history_weight=0),
        Prefect(name="P7", form=Form.F4, role=Role.STUDY_PREFECT,
                available=[Weekday.MON, Weekday.WED, Weekday.FRI], history_weight=0),
        Prefect(name="P8", form=Form.F3, role=Role.STUDY_PREFECT,
                available=[Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI], history_weight=0),
    ]


class TestRosterGeneration:
    """Tests for the complete roster generation pipeline."""

    def test_generate_valid_roster(self):
        service = RosterService(prefects=_make_prefects_for_tests())
        roster = service.generate_weekly_roster(week_start=date(2026, 6, 29))
        assert isinstance(roster, WeeklyRoster)
        violations = roster.validate()
        assert violations == [], f"Expected no violations, got: {violations}"

    def test_ahp_assignment_count(self):
        service = RosterService(prefects=_make_prefects_for_tests())
        roster = service.generate_weekly_roster(week_start=date(2026, 6, 29))
        ahp_assignments = roster.get_ahp_assignments()
        assigned = [v for v in ahp_assignments.values() if v is not None]
        assert len(assigned) == 5, f"Expected 5 AHP assignments (1/day), got {len(assigned)}"

    def test_no_duplicate_ahp(self):
        service = RosterService(prefects=_make_prefects_for_tests())
        roster = service.generate_weekly_roster(week_start=date(2026, 6, 29))
        ahp_names = roster.get_ahp_assignments().values()
        ahp_names = [n for n in ahp_names if n is not None]
        assert len(ahp_names) == len(set(ahp_names)), "Duplicate AHP assignment detected"

    def test_room_202_closed_tuesday(self):
        service = RosterService(prefects=_make_prefects_for_tests())
        roster = service.generate_weekly_roster(week_start=date(2026, 6, 30))  # Tuesday
        tue_roster = roster.days[Weekday.TUE]
        assert Room.ROOM_202 not in tue_roster.room_assignments, "Room 202 should be closed Tuesday"

    def test_room_202_closed_friday(self):
        service = RosterService(prefects=_make_prefects_for_tests())
        roster = service.generate_weekly_roster(week_start=date(2026, 6, 29))
        fri_roster = roster.days[Weekday.FRI]
        assert Room.ROOM_202 not in fri_roster.room_assignments, "Room 202 should be closed Friday"

    def test_room_202_open_wednesday(self):
        service = RosterService(prefects=_make_prefects_for_tests())
        roster = service.generate_weekly_roster(week_start=date(2026, 7, 1))  # Wednesday
        wed_roster = roster.days[Weekday.WED]
        assert Room.ROOM_202 in wed_roster.room_assignments, "Room 202 should be open Wednesday"

    def test_room_capacities_respected(self):
        service = RosterService(prefects=_make_prefects_for_tests())
        roster = service.generate_weekly_roster(week_start=date(2026, 6, 29))
        for day in Weekday:
            daily = roster.days[day]
            for room, names in daily.room_assignments.items():
                assert len(names) <= room.capacity, (
                    f"{room.value} on {day.value}: {len(names)} assigned, capacity {room.capacity}"
                )

    def test_no_prefect_assigned_twice_same_day(self):
        service = RosterService(prefects=_make_prefects_for_tests())
        roster = service.generate_weekly_roster(week_start=date(2026, 6, 29))
        for day in Weekday:
            daily = roster.days[day]
            all_names = []
            if daily.ahp_assignment and daily.ahp_assignment.prefect_name:
                all_names.append(daily.ahp_assignment.prefect_name)
            for names in daily.room_assignments.values():
                all_names.extend(names)
            assert len(all_names) == len(set(all_names)), (
                f"Duplicate prefect on {day.value}: {all_names}"
            )

    def test_loads_updated_after_generation(self):
        service = RosterService(prefects=_make_prefects_for_tests())
        old_loads = {p.name: p.history_weight for p in service.prefects}
        service.generate_weekly_roster(week_start=date(2026, 6, 29))
        total_old = sum(old_loads.values())
        total_new = sum(p.history_weight for p in service.prefects)
        assert total_new > total_old, "Loads should increase after generation"

    def test_fairness_improves_for_least_loaded(self):
        """The least-loaded prefects should receive more assignments than the most-loaded."""
        service = RosterService(prefects=_make_prefects_for_tests())
        old_loads = {p.name: p.history_weight for p in service.prefects}

        # Find the initially least-loaded and most-loaded ordinary prefects
        ordinary = [p for p in service.ordinary_prefects]
        least = min(ordinary, key=lambda p: p.history_weight)
        most = max(ordinary, key=lambda p: p.history_weight)

        service.generate_weekly_roster(week_start=date(2026, 6, 29))

        least_delta = least.history_weight - old_loads[least.name]
        most_delta = most.history_weight - old_loads[most.name]

        # The least-loaded should receive at least as much additional load as the most-loaded
        assert least_delta >= most_delta, (
            f"Least-loaded ({least.name}) got {least_delta}pts, "
            f"most-loaded ({most.name}) got {most_delta}pts. "
            f"Fairness-weighted algorithm should prefer least-loaded."
        )
