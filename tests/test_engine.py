"""Tests for roster.core.engine - scheduling and fairness logic."""

import pytest
import pandas as pd
from roster.config import DAYS, get_roster_rows, AHP_ROLE, REGULAR_ROLE
from roster.core import generate_roster, validate_and_compute


@pytest.fixture
def minimal_students():
    """Create a minimal student roster for testing (Chinese role names)."""
    ALL_DAYS = "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"
    data = []
    # 12 regular SPs
    for i in range(12):
        data.append({
            "name": f"Student_{i+1}",
            "form": "F.4",
            "class": "A",
            "role": REGULAR_ROLE,  # "導學風紀"
            "fixed_general_duty": "",
            "available": ALL_DAYS,
            "history_duties": i % 3,
            "history_weight": float(i * 0.5),
            "remarks": "",
        })
    # 3 AHPs
    for i in range(3):
        data.append({
            "name": f"AHP_{i+1}",
            "form": "F.5",
            "class": "B",
            "role": AHP_ROLE,  # "助理首席導學風紀"
            "fixed_general_duty": "",
            "available": ALL_DAYS,
            "history_duties": 0,
            "history_weight": float(i * 0.2),
            "remarks": "",
        })
    return pd.DataFrame(data)


class TestGenerateRoster:
    """Tests for the main roster generation function."""

    def test_generate_returns_dataframe(self, minimal_students):
        result = generate_roster(minimal_students, [], [], seed=42)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 6

    def test_roster_has_correct_structure(self, minimal_students):
        roster = generate_roster(minimal_students, [], [], seed=42)
        expected_rows = get_roster_rows()
        assert list(roster.index) == expected_rows
        assert list(roster.columns) == DAYS

    def test_no_empty_cells(self, minimal_students):
        roster = generate_roster(minimal_students, [], [], seed=42)
        empty_cells = []
        for role in roster.index:
            for day in DAYS:
                if str(roster.at[role, day]).strip() == "":
                    empty_cells.append(f"{role} {day}")
        assert not empty_cells, f"Empty cells: {empty_cells}"

    def test_assist_slot_has_ahp(self, minimal_students):
        """Assist. in charge must be filled by an AHP."""
        roster = generate_roster(minimal_students, [], [], seed=42)
        for day in DAYS:
            val = str(roster.at["Assist. in charge", day]).strip()
            assert val.startswith("AHP_"), f"Non-AHP in assist slot on {day}: {val}"

    def test_room202_closed_tue_fri(self, minimal_students):
        """Room 202 should show ⬜ on Tue and Fri."""
        roster = generate_roster(minimal_students, [], [], seed=42)
        for slot in ["Room 202 (F1 Study Group) - 1", "Room 202 (F1 Study Group) - 2"]:
            assert roster.at[slot, "TUESDAY"] == "⬜", f"{slot} not closed Tue: got {repr(roster.at[slot, 'TUESDAY'])}"
            assert roster.at[slot, "FRIDAY"] == "⬜", f"{slot} not closed Fri: got {repr(roster.at[slot, 'FRIDAY'])}"
            assert roster.at[slot, "MONDAY"] != "⬜", f"{slot} should be open Mon"

    def test_room303_two_slots_different_people(self, minimal_students):
        """Room 303's two daily slots must have different students."""
        roster = generate_roster(minimal_students, [], [], seed=42)
        for day in DAYS:
            p1 = str(roster.at["Room 303 (HW Completion) - 1", day]).strip()
            p2 = str(roster.at["Room 303 (HW Completion) - 2", day]).strip()
            if p1 and p2:
                assert p1 != p2, f"Same person in both Room 303 slots on {day}: {p1}"


class TestValidateAndCompute:
    """Tests for audit/report computation."""

    def test_validate_returns_dict_with_report(self, minimal_students):
        roster = generate_roster(minimal_students, [], [], seed=42)
        result = validate_and_compute(roster, minimal_students, [], pd.DataFrame(0.0, index=get_roster_rows(), columns=DAYS))
        assert isinstance(result, dict)
        assert "report_df" in result
        report = result["report_df"]
        assert isinstance(report, pd.DataFrame)
        assert len(report) > 0

    def test_report_has_required_columns(self, minimal_students):
        roster = generate_roster(minimal_students, [], [], seed=42)
        result = validate_and_compute(roster, minimal_students, [], pd.DataFrame(0.0, index=get_roster_rows(), columns=DAYS))
        report = result["report_df"]
        required = {"Student Name", "Form", "Class", "Role",
                     "This Week Added (points)", "Cumulative Weighted Load (points)"}
        missing = required - set(report.columns)
        assert not missing, f"Missing columns: {missing}"

    def test_report_includes_all_students(self, minimal_students):
        roster = generate_roster(minimal_students, [], [], seed=42)
        result = validate_and_compute(roster, minimal_students, [], pd.DataFrame(0.0, index=get_roster_rows(), columns=DAYS))
        report = result["report_df"]
        names_in_report = set(report["Student Name"].tolist())
        names_in_input = set(minimal_students["name"].tolist())
        assert names_in_report == names_in_input, f"Missing: {names_in_input - names_in_report}"

