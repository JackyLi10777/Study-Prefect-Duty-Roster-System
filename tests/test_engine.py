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




class TestMentoringPairing:
    """Tests for mentoring pairing logic (_is_mentee, _is_mentor, bonus, annotate_mentoring_pairs)."""

    def test_is_mentee_by_flag(self):
        from roster.core.engine import _is_mentee
        assert _is_mentee({"needs_mentoring": True, "history_weight": 10.0}) is True

    def test_is_mentee_by_low_weight(self):
        from roster.core.engine import _is_mentee
        assert _is_mentee({"needs_mentoring": False, "history_weight": 0.0}) is True
        assert _is_mentee({"needs_mentoring": False, "history_weight": 2.0}) is True

    def test_is_mentee_false_for_normal(self):
        from roster.core.engine import _is_mentee
        assert _is_mentee({"needs_mentoring": False, "history_weight": 3.0}) is False

    def test_is_mentor_true(self):
        from roster.core.engine import _is_mentor
        assert _is_mentor({"needs_mentoring": False, "history_weight": 6.0}) is True

    def test_is_mentor_false_when_needs_mentoring(self):
        from roster.core.engine import _is_mentor
        assert _is_mentor({"needs_mentoring": True, "history_weight": 6.0}) is False

    def test_is_mentor_false_low_weight(self):
        from roster.core.engine import _is_mentor
        assert _is_mentor({"needs_mentoring": False, "history_weight": 5.0}) is False

    def test_mentoring_bonus_smoke(self, minimal_students):
        """Smoke test: mentoring bonus code path runs without error."""
        from roster.core.engine import generate_roster
        roster = generate_roster(minimal_students, [], [], seed=42)
        assert roster is not None

    def test_mentoring_pairing_with_clear_mentees_and_mentors(self):
        """With explicit mentees (hw=0) and many mentors (hw=10), pairs should form."""
        from roster.core.engine import generate_roster, annotate_mentoring_pairs
        import pandas as pd
        ALL_DAYS = "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"
        from roster.config import REGULAR_ROLE, AHP_ROLE
        data = []
        # 4 mentees (hw=0, needs_mentoring=True)
        for i in range(4):
            data.append({
                "name": f"Mentee_{i+1}", "form": "F.3", "class": "A",
                "role": REGULAR_ROLE, "fixed_general_duty": "",
                "available": ALL_DAYS, "history_duties": 0,
                "history_weight": 0.0, "remarks": "",
                "needs_mentoring": True,
            })
        # 10 mentors (hw=10, not needing mentoring) — enough to fill all slots
        for i in range(10):
            data.append({
                "name": f"Mentor_{i+1}", "form": "F.5", "class": "B",
                "role": REGULAR_ROLE, "fixed_general_duty": "",
                "available": ALL_DAYS, "history_duties": 0,
                "history_weight": 10.0, "remarks": "",
                "needs_mentoring": False,
            })
        # 3 AHPs
        for i in range(3):
            data.append({
                "name": f"AHP_{i+1}", "form": "F.5", "class": "C",
                "role": AHP_ROLE, "fixed_general_duty": "",
                "available": ALL_DAYS, "history_duties": 0,
                "history_weight": 5.0, "remarks": "",
                "needs_mentoring": False,
            })
        students = pd.DataFrame(data)
        roster = generate_roster(students, [], [], seed=42)
        pairs = annotate_mentoring_pairs(roster, students)
        # With 4 mentees and 10 mentors, 2-slot rooms should form mentor-mentee combos
        assert len(pairs) > 0, f"Expected mentoring pairs but got none. Roster:`n{roster}"

    def test_annotate_mentoring_pairs_returns_dict(self, minimal_students):
        from roster.core.engine import generate_roster, annotate_mentoring_pairs
        roster = generate_roster(minimal_students, [], [], seed=42)
        pairs = annotate_mentoring_pairs(roster, minimal_students)
        assert isinstance(pairs, dict)

    def test_room202_tue_fri_not_in_pairs(self, minimal_students):
        """annotate_mentoring_pairs must skip Room 202 on Tue/Fri."""
        from roster.core.engine import generate_roster, annotate_mentoring_pairs
        roster = generate_roster(minimal_students, [], [], seed=42)
        pairs = annotate_mentoring_pairs(roster, minimal_students)
        for key in pairs:
            assert "TUESDAY" not in key.split("_"), f"Room 202 Tue should not appear: {key}"
            assert "FRIDAY" not in key.split("_"), f"Room 202 Fri should not appear: {key}"


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

