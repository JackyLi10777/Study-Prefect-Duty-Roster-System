"""Tests for roster.config - SSOT for all scheduling rules."""

import pytest
from roster.config import (
    DAYS, ROWS_ROSTER, ROOMS_CONFIG, VERSION,
    PROJECT_FULL_NAME, PROJECT_FULL_NAME_EN,
    get_weight, is_assistant_head_only_role,
    is_room_open_on_weekday, get_roster_rows,
    get_base_role, get_daily_slots,
    NASA_COLORS, get_role_style,
    GLOBAL_LOAD_RANGE, DEFAULT_GLOBAL_LOAD_MULTIPLIER,
)

class TestConfigConstants:
    """Verify all configuration constants are well-formed."""

    def test_project_names(self):
        assert PROJECT_FULL_NAME == "聖言中學導學風紀當值排班平台"
        assert PROJECT_FULL_NAME_EN == "Sing Yin Secondary School Study Prefect Duty Roster Platform"
        assert bool(VERSION)

    def test_days(self):
        assert DAYS == ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
        assert len(DAYS) == 5

    def test_roster_rows(self):
        assert len(ROWS_ROSTER) == 6
        assert ROWS_ROSTER[0] == "Assist. in charge"
        assert ROWS_ROSTER[1] == "Room 302 (Study Room)"
        assert ROWS_ROSTER[2] == "Room 303 (HW Completion) - 1"
        assert ROWS_ROSTER[3] == "Room 303 (HW Completion) - 2"
        assert ROWS_ROSTER[4] == "Room 202 (F1 Study Group) - 1"
        assert ROWS_ROSTER[5] == "Room 202 (F1 Study Group) - 2"

    def test_global_load_range(self):
        assert GLOBAL_LOAD_RANGE == (0.8, 2.0)
        assert DEFAULT_GLOBAL_LOAD_MULTIPLIER == 1.0

class TestGetWeight:
    """Verify get_weight() returns correct values per school rules."""

    def test_assist_weight(self):
        assert get_weight("Assist. in charge") == 1.0

    def test_room302_weight(self):
        assert get_weight("Room 302 (Study Room)") == 1.0

    def test_room303_weight(self):
        assert get_weight("Room 303 (HW Completion) - 1") == 1.5
        assert get_weight("Room 303 (HW Completion) - 2") == 1.5

    def test_room202_weight(self):
        assert get_weight("Room 202 (F1 Study Group) - 1") == 1.5
        assert get_weight("Room 202 (F1 Study Group) - 2") == 1.5

    def test_unknown_role_returns_default(self):
        assert get_weight("Unknown Room") == 1.5

class TestAssistantHeadOnlyRole:
    """Verify AHP gate (only Assist. in charge allows AHP)."""

    def test_assist_is_ahp_only(self):
        assert is_assistant_head_only_role("Assist. in charge") is True

    def test_room302_not_ahp(self):
        assert is_assistant_head_only_role("Room 302 (Study Room)") is False

    def test_room303_not_ahp(self):
        assert is_assistant_head_only_role("Room 303 (HW Completion) - 1") is False

    def test_room202_not_ahp(self):
        assert is_assistant_head_only_role("Room 202 (F1 Study Group) - 1") is False

class TestRoomOpenOnWeekday:
    """Verify room open/close rules per school policy."""

    def test_assist_full_week(self):
        for day in DAYS:
            assert is_room_open_on_weekday("Assist. in charge", day) is True

    def test_room302_full_week(self):
        for day in DAYS:
            assert is_room_open_on_weekday("Room 302 (Study Room)", day) is True

    def test_room303_full_week(self):
        for day in DAYS:
            assert is_room_open_on_weekday("Room 303 (HW Completion) - 1", day) is True
            assert is_room_open_on_weekday("Room 303 (HW Completion) - 2", day) is True

    def test_room202_closed_tue_fri(self):
        assert is_room_open_on_weekday("Room 202 (F1 Study Group) - 1", "MONDAY") is True
        assert is_room_open_on_weekday("Room 202 (F1 Study Group) - 1", "TUESDAY") is False
        assert is_room_open_on_weekday("Room 202 (F1 Study Group) - 1", "WEDNESDAY") is True
        assert is_room_open_on_weekday("Room 202 (F1 Study Group) - 1", "THURSDAY") is True
        assert is_room_open_on_weekday("Room 202 (F1 Study Group) - 1", "FRIDAY") is False

    def test_unknown_room_open(self):
        assert is_room_open_on_weekday("Unknown Room", "TUESDAY") is True

class TestGetRoleStyle:
    """Verify color styling function returns consistent dict."""

    def test_assist_style_keys(self):
        style = get_role_style("Assist. in charge")
        for key in ["bg", "text", "border"]:
            assert key in style

    def test_assist_gold_border(self):
        style = get_role_style("Assist. in charge")
        assert "D4AF37" in style["border"]

    def test_room202_closed_style(self):
        style = get_role_style("Room 202 (F1 Study Group) - 1", "TUESDAY")
        assert style["bg"] == NASA_COLORS["closed_bg"]

    def test_nasa_colors_integrity(self):
        required = ["header_bg", "accent_gold", "assist_bg", "room302_bg", "room303_bg", "room202_bg"]
        for key in required:
            assert key in NASA_COLORS, f"Missing NASA_COLORS key: {key}"

class TestRoomsConfig:
    """Verify ROOMS_CONFIG contains all expected entries with correct values."""

    def test_all_rooms_present(self):
        expected = ["Assist. in charge", "Room 302 (Study Room)", "Room 303 (HW Completion)", "Room 202 (F1 Study Group)"]
        for room in expected:
            assert room in ROOMS_CONFIG, f"Missing room config: {room}"

    def test_assist_config(self):
        cfg = ROOMS_CONFIG["Assist. in charge"]
        assert cfg["daily_slots"] == 1
        assert cfg["weight"] == 1.0
        assert cfg["allow_assistant_head_only"] is True
        assert cfg["available_weekdays"] == DAYS

    def test_room302_config(self):
        cfg = ROOMS_CONFIG["Room 302 (Study Room)"]
        assert cfg["daily_slots"] == 1
        assert cfg["weight"] == 1.0
        assert cfg["allow_assistant_head_only"] is False

    def test_room303_config(self):
        cfg = ROOMS_CONFIG["Room 303 (HW Completion)"]
        assert cfg["daily_slots"] == 2
        assert cfg["weight"] == 1.5
        assert cfg["allow_assistant_head_only"] is False

    def test_room202_config(self):
        cfg = ROOMS_CONFIG["Room 202 (F1 Study Group)"]
        assert cfg["daily_slots"] == 2
        assert cfg["weight"] == 1.5
        assert cfg["allow_assistant_head_only"] is False
        assert "TUESDAY" not in cfg["available_weekdays"]
        assert "FRIDAY" not in cfg["available_weekdays"]
