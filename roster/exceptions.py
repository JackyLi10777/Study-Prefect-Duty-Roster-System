"""
roster.exceptions — Custom exception hierarchy for the Sing Yin Duty Roster System.

Provides structured, catchable exception types for expected failure modes:
- BackupParseError: PDF/JSON backup data parsing failures
- RosterValidationError: Roster data validation failures
- SchoolPolicyViolation: School rule enforcement failures
- StateIntegrityError: Session state corruption after restore

All exceptions inherit from RosterSystemError for broad catch-all handling.
"""


class RosterSystemError(Exception):
    """Base exception for all roster-system errors.

    Catch this to handle any expected failure from the roster system.
    Unexpected bugs (AttributeError, KeyError, etc.) should NOT be caught
    by this — they indicate programmer errors that need fixing.
    """
    pass


class SchoolPolicyViolation(RosterSystemError):
    """A school scheduling policy rule has been violated.

    Raised when roster generation or validation detects that a Sing Yin
    school rule constraint cannot be satisfied. Examples:
    - AHP student assigned to a non-Assist slot
    - Room 202 staffed on Tuesday or Friday
    - Same student assigned to consecutive days
    """
    pass


class BackupParseError(RosterSystemError):
    """Failed to parse backup data from a PDF or JSON file.

    Raised when the backup parser cannot extract valid data from
    an uploaded file. The original error message is preserved in
    the exception args for user display.

    Attributes:
        message: Human-readable error description.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class RosterValidationError(RosterSystemError):
    """Roster data failed validation checks.

    Raised when the roster DataFrame contains invalid or inconsistent
    data that prevents safe operation. Examples:
    - Duplicate student names in the same day
    - Data type mismatch in critical columns
    - Leave conflict detected during roster generation
    """

    def __init__(self, message: str, details: list = None):
        self.message = message
        self.details = details or []
        super().__init__(message)


class StateIntegrityError(RosterSystemError):
    """Session state integrity check failed after a restore operation.

    Raised by validate_state_integrity() when critical session_state
    keys are missing or have incorrect types after a backup restore.
    The issues list contains human-readable descriptions of each problem.

    Attributes:
        issues: list[str] — Human-readable descriptions of each problem.
    """

    def __init__(self, issues: list):
        self.issues = issues
        msg = f"State integrity check failed with {len(issues)} issue(s): " + "; ".join(issues[:5])
        if len(issues) > 5:
            msg += f" ... and {len(issues) - 5} more"
        super().__init__(msg)

