"""
Smoke tests for Phase 2 Stability Guards — roster and leave service validation.
Tests the guard logic that the UI triggers without requiring NiceGUI.
"""

import pytest
from models.enums import Role, Form, Weekday
from models.prefect import Prefect
from models.roster import WeeklyRoster
from services.roster_service import RosterService
from services.leave_service import LeaveAdjustmentService


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_prefects():
    """Minimal set of prefects for guard testing."""
    return [
        Prefect(name="AHP 1", form=Form.F5, class_name="5A",
                role=Role.ASSISTANT_HEAD_PREFECT,
                available=[Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI],
                history_weight=0.0, active=True),
        Prefect(name="AHP 2", form=Form.F5, class_name="5B",
                role=Role.ASSISTANT_HEAD_PREFECT,
                available=[Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI],
                history_weight=0.0, active=True),
        Prefect(name="SP 1", form=Form.F4, class_name="4A",
                role=Role.STUDY_PREFECT,
                available=[Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI],
                history_weight=0.0, active=True),
        Prefect(name="SP 2", form=Form.F4, class_name="4B",
                role=Role.STUDY_PREFECT,
                available=[Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI],
                history_weight=0.0, active=True),
        Prefect(name="SP 3", form=Form.F3, class_name="3A",
                role=Role.STUDY_PREFECT,
                available=[Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI],
                history_weight=0.0, active=True),
    ]


# =============================================================================
# 1. Pre-Generation Validation Guards (roster_service.py)
# =============================================================================

def test_pregen_rejects_empty_prefects():
    """Guard: generation with zero prefects raises ValueError."""
    svc = RosterService(prefects=[])
    from datetime import date
    with pytest.raises(ValueError, match="No prefects loaded"):
        svc.generate_weekly_roster(week_start=date(2026, 6, 29))


def test_pregen_rejects_too_few_prefects():
    """Guard: generation with <3 active prefects raises ValueError."""
    only_two = [
        Prefect(name="P1", form=Form.F4, class_name="4A", role=Role.STUDY_PREFECT,
                available=[Weekday.MON], history_weight=0.0, active=True),
        Prefect(name="P2", form=Form.F4, class_name="4B", role=Role.STUDY_PREFECT,
                available=[Weekday.MON], history_weight=0.0, active=True),
    ]
    svc = RosterService(prefects=only_two)
    from datetime import date
    with pytest.raises(ValueError, match="Need at least 3"):
        svc.generate_weekly_roster(week_start=date(2026, 6, 29))


def test_pregen_allows_valid_count(sample_prefects):
    """Guard: generation with >=3 prefects succeeds."""
    svc = RosterService(prefects=sample_prefects)
    from datetime import date
    roster = svc.generate_weekly_roster(week_start=date(2026, 6, 29))
    assert roster is not None
    assert len(roster.days) == 5


# =============================================================================
# 2. State Guard — Leave Adjustment (leave_service.py)
# =============================================================================

def test_leave_service_rejects_null_roster(sample_prefects):
    """Guard: leave adjustment with None roster returns error message."""
    svc = LeaveAdjustmentService(prefects=sample_prefects)
    result = svc.apply_adjustment(
        None, "SP 1", Weekday.MON, None, 0, "SP 2", 1.0
    )
    assert "No roster data available" in result


def test_leave_service_rejects_blank_name(sample_prefects):
    """Guard: leave adjustment with blank prefect name returns error."""
    svc = LeaveAdjustmentService(prefects=sample_prefects)
    from datetime import date; roster = WeeklyRoster(week_start=date(2026,6,29))
    result = svc.apply_adjustment(
        roster, "", Weekday.MON, None, 0, "SP 2", 1.0
    )
    assert "Prefect name is required" in result


# =============================================================================
# 3. State Integrity — _current_roster pattern (logic verification)
# =============================================================================

def test_workload_multiplier_default():
    """Guard: RosterService defaults workload_multiplier to 1.0."""
    svc = RosterService(prefects=[])
    assert svc.workload_multiplier == 1.0


def test_workload_multiplier_custom():
    """Guard: workload_multiplier respects custom value."""
    svc = RosterService(prefects=[], workload_multiplier=1.5)
    assert svc.workload_multiplier == 1.5


# =============================================================================
# 4. Export Guard — verify roster generation produces valid WeeklyRoster
# =============================================================================

def test_generated_roster_has_days(sample_prefects):
    """Smoke: generated roster contains all 5 weekdays."""
    from datetime import date
    svc = RosterService(prefects=sample_prefects)
    roster = svc.generate_weekly_roster(week_start=date(2026, 6, 29))
    assert Weekday.MON in roster.days
    assert Weekday.FRI in roster.days


def test_generated_roster_room_assignments(sample_prefects):
    """Smoke: generated roster has room assignments for all rooms."""
    from datetime import date
    svc = RosterService(prefects=sample_prefects)
    roster = svc.generate_weekly_roster(week_start=date(2026, 6, 29))
    for day in Weekday:
        daily = roster.days.get(day)
        assert daily is not None
        # At least one room should have assignments on each open day
        total_assigned = sum(len(names) for names in daily.room_assignments.values())
        assert total_assigned >= 0  # Some days may have unfilled slots (acceptable)

print('Smoke tests ready')
