"""
Integration tests for the Sing Yin Study Prefect Duty Roster System.

Covers cross-module workflows: state management, backup parsing,
school policy integration, and exception handling.
"""

import pytest
import pandas as pd
from io import BytesIO


class TestStateHelpers:
    """Tests for the Phase 2 session state helper functions."""

    def test_get_state_returns_default(self):
        """get_state returns default for missing keys."""
        from roster.data.state import get_state
        result = get_state("nonexistent_key_for_test", "fallback")
        assert result == "fallback"

    def test_reset_roster_related_state_clears_caches(self):
        """reset_roster_related_state clears PDF caches and related keys."""
        import streamlit as st
        from roster.data.state import reset_roster_related_state, initialize_session_state

        # Ensure state is initialized
        initialize_session_state()

        # Set some test values
        st.session_state.pdf_cache_zh = b"fake pdf zh"
        st.session_state.pdf_cache_en = b"fake pdf en"
        st.session_state.roster_search = "test search"
        st.session_state.roster_versions = [{"v": 1}]

        # Reset
        reset_roster_related_state()

        # Verify cleared
        assert "pdf_cache_zh" not in st.session_state
        assert "pdf_cache_en" not in st.session_state
        assert "roster_search" not in st.session_state
        assert "roster_versions" not in st.session_state

        # Verify persistent keys are NOT cleared
        assert "students_df" in st.session_state  # persistent


class TestStateIntegrityValidation:
    """Tests for validate_state_integrity from Phase 2."""

    def test_validate_healthy_state_passes(self):
        """validate_state_integrity returns empty list for initialized state."""
        import streamlit as st
        from roster.data.state import initialize_session_state, validate_state_integrity

        initialize_session_state()
        # Should not raise StateIntegrityError for healthy state
        issues = validate_state_integrity()
        assert issues == [], f"Expected no issues, got: {issues}"

    def test_validate_missing_key_raises_state_integrity_error(self):
        """validate_state_integrity raises StateIntegrityError when keys missing."""
        import streamlit as st
        from roster.data.state import initialize_session_state, validate_state_integrity
        from roster.exceptions import StateIntegrityError

        initialize_session_state()
        # Remove a required key
        st.session_state.pop("roster_df", None)
        st.session_state.pop("master_report_df", None)

        with pytest.raises(StateIntegrityError) as exc_info:
            validate_state_integrity()
        assert len(exc_info.value.issues) >= 2
        assert any("roster_df" in issue for issue in exc_info.value.issues)


class TestBackupParsingErrors:
    """Tests for parse_backup_from_pdf error handling (Phase 3)."""

    def test_bad_pdf_input_returns_error(self):
        """parse_backup_from_pdf returns success=False for non-PDF bytes."""
        from roster.utils.backup import parse_backup_from_pdf

        result = parse_backup_from_pdf(b"this is not a pdf file")
        assert isinstance(result, dict)
        assert result["success"] is False
        assert "error" in result
        assert result["error"] is not None

    def test_empty_bytes_returns_error(self):
        """parse_backup_from_pdf returns success=False for empty bytes."""
        from roster.utils.backup import parse_backup_from_pdf

        result = parse_backup_from_pdf(b"")
        assert isinstance(result, dict)
        assert result["success"] is False

    def test_no_markers_in_pdf_returns_error(self):
        """A valid PDF without backup markers returns success=False."""
        from roster.utils.backup import parse_backup_from_pdf

        # Create a minimal valid PDF that contains no backup markers
        minimal_pdf = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
            b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
        )

        result = parse_backup_from_pdf(minimal_pdf)
        assert isinstance(result, dict)
        assert result["success"] is False
        assert "markers" in result.get("error", "").lower()


class TestSchoolPolicyIntegration:
    """Tests verifying school_policy.py is the active SSOT."""

    def test_mentoring_thresholds_from_school_policy(self):
        """Engine uses MENTEE_THRESHOLD/MENTOR_THRESHOLD from school_policy."""
        from roster.config.school_policy import MENTEE_THRESHOLD, MENTOR_THRESHOLD
        from roster.core.engine import generate_roster

        # Verify the thresholds are reasonable
        assert MENTEE_THRESHOLD == 2.0
        assert MENTOR_THRESHOLD == 5.0
        assert MENTEE_THRESHOLD < MENTOR_THRESHOLD

    def test_room_202_closed_tue_fri_from_policy(self):
        """Room 202 closure rule comes from school_policy."""
        from roster.config.school_policy import is_room_open_on_weekday

        assert is_room_open_on_weekday("Room 202 (F1 Study Group) - 1", "MONDAY") is True
        assert is_room_open_on_weekday("Room 202 (F1 Study Group) - 1", "TUESDAY") is False
        assert is_room_open_on_weekday("Room 202 (F1 Study Group) - 1", "FRIDAY") is False

    def test_ahp_bonus_from_school_policy(self):
        """AHP_LOAD_BONUS is accessible from school_policy."""
        from roster.config.school_policy import AHP_LOAD_BONUS

        assert AHP_LOAD_BONUS == -8.0
        assert AHP_LOAD_BONUS < 0  # Bonus should be negative (reduces score = higher priority)


class TestExceptionHierarchy:
    """Tests for the Phase 3 exception hierarchy."""

    def test_backup_parse_error_is_roster_system_error(self):
        """BackupParseError is a subclass of RosterSystemError."""
        from roster.exceptions import BackupParseError, RosterSystemError

        err = BackupParseError("test")
        assert isinstance(err, RosterSystemError)
        assert isinstance(err, Exception)
        assert err.message == "test"

    def test_state_integrity_error_carries_issues(self):
        """StateIntegrityError preserves the issues list."""
        from roster.exceptions import StateIntegrityError, RosterSystemError

        err = StateIntegrityError(["key1 missing", "key2 wrong type"])
        assert isinstance(err, RosterSystemError)
        assert len(err.issues) == 2
        assert "key1 missing" in str(err)

