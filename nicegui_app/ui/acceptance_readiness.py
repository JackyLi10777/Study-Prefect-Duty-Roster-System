"""Human-acceptance sessions shown by the handover workbench.

The detailed acceptance requirements and automated evidence remain owned by
``docs/ACCEPTANCE_EVIDENCE.md``.  This catalog groups those stable IDs into
operator-sized sessions without pretending that the application can sign them
off.  Tests bind the catalog back to the document so either side cannot drift
silently.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol


_CHECK_ID_PATTERN = re.compile(r"^(?:H|A)-\d{2}$")


class Translator(Protocol):
    def __call__(self, key: str, **values: object) -> str: ...


@dataclass(frozen=True, slots=True)
class AcceptanceSession:
    """One supervised, human-sized acceptance session."""

    key: str
    title_key: str
    body_key: str
    icon: str
    route: str
    destination_key: str
    operator_checks: tuple[str, ...] = ()
    advisor_checks: tuple[str, ...] = ()

    @property
    def check_ids(self) -> tuple[str, ...]:
        return self.operator_checks + self.advisor_checks

    @property
    def role_key(self) -> str:
        if self.operator_checks and self.advisor_checks:
            return "acceptance_role_shared"
        if self.advisor_checks:
            return "acceptance_role_advisor"
        return "acceptance_role_operator"


ACCEPTANCE_SESSIONS = (
    AcceptanceSession(
        key="access-devices",
        title_key="acceptance_session_access_title",
        body_key="acceptance_session_access_body",
        icon="verified_user",
        route="/getting-started",
        destination_key="getting_started",
        operator_checks=("H-14", "H-15", "H-19"),
        advisor_checks=("A-04",),
    ),
    AcceptanceSession(
        key="directory-policy",
        title_key="acceptance_session_directory_title",
        body_key="acceptance_session_directory_body",
        icon="groups",
        route="/prefects",
        destination_key="prefects",
        operator_checks=("H-01", "H-02", "H-03", "H-04", "H-05", "H-06", "H-20"),
    ),
    AcceptanceSession(
        key="publish-recover",
        title_key="acceptance_session_publish_title",
        body_key="acceptance_session_publish_body",
        icon="published_with_changes",
        route="/rosters",
        destination_key="rosters",
        operator_checks=("H-07", "H-08", "H-16"),
    ),
    AcceptanceSession(
        key="outputs-privacy",
        title_key="acceptance_session_outputs_title",
        body_key="acceptance_session_outputs_body",
        icon="picture_as_pdf",
        route="/rosters",
        destination_key="rosters",
        operator_checks=("H-09", "H-10"),
    ),
    AcceptanceSession(
        key="guest-support",
        title_key="acceptance_session_guest_title",
        body_key="acceptance_session_guest_body",
        icon="support_agent",
        route="/support",
        destination_key="report_problem",
        operator_checks=("H-18", "H-21"),
    ),
    AcceptanceSession(
        key="custody-recovery",
        title_key="acceptance_session_recovery_title",
        body_key="acceptance_session_recovery_body",
        icon="settings_backup_restore",
        route="/settings",
        destination_key="settings",
        operator_checks=("H-11", "H-12", "H-13", "H-17"),
        advisor_checks=("A-02", "A-03"),
    ),
    AcceptanceSession(
        key="fairness-approval",
        title_key="acceptance_session_fairness_title",
        body_key="acceptance_session_fairness_body",
        icon="balance",
        route="/audit",
        destination_key="audit",
        advisor_checks=("A-01",),
    ),
)


def acceptance_check_ids(prefix: str | None = None) -> tuple[str, ...]:
    """Return unique catalog IDs, optionally filtered to ``H`` or ``A``."""

    identifiers = tuple(check_id for session in ACCEPTANCE_SESSIONS for check_id in session.check_ids)
    if prefix is None:
        return identifiers
    normalized = prefix.strip().upper()
    if normalized not in {"H", "A"}:
        raise ValueError("acceptance prefix must be H or A")
    return tuple(check_id for check_id in identifiers if check_id.startswith(f"{normalized}-"))


def acceptance_check_counts() -> tuple[int, int]:
    """Return operator and teacher-advisor check counts."""

    return len(acceptance_check_ids("H")), len(acceptance_check_ids("A"))


def build_supervised_acceptance_worksheet(translate: Translator) -> bytes:
    """Build a local worksheet that the application does not persist."""

    operator_count, advisor_count = acceptance_check_counts()
    lines = [
        f"# {translate('acceptance_worksheet_title')}",
        "",
        translate(
            "acceptance_worksheet_intro",
            operator_count=operator_count,
            advisor_count=advisor_count,
        ),
        "",
        f"- {translate('acceptance_worksheet_release')}: ____________________",
        f"- {translate('acceptance_worksheet_date')}: ____________________",
        "",
    ]
    for index, session in enumerate(ACCEPTANCE_SESSIONS, start=1):
        lines.extend(
            (
                f"## {index}. {translate(session.title_key)}",
                "",
                translate(session.body_key),
                "",
                f"**{translate(session.role_key)}**",
                "",
            )
        )
        lines.extend(f"- [ ] {check_id}" for check_id in session.check_ids)
        lines.extend(
            (
                "",
                f"- {translate('acceptance_worksheet_observer')}: ____________________",
                f"- {translate('acceptance_worksheet_result')}: ____________________",
                "",
            )
        )
    lines.extend(("---", "", translate("acceptance_worksheet_final_note"), ""))
    return "\n".join(lines).encode("utf-8")


def _validate_catalog() -> None:
    identifiers = acceptance_check_ids()
    if not identifiers or len(identifiers) != len(set(identifiers)):
        raise ValueError("acceptance check IDs must be present and unique")
    invalid = tuple(check_id for check_id in identifiers if not _CHECK_ID_PATTERN.fullmatch(check_id))
    if invalid:
        raise ValueError(f"invalid acceptance check IDs: {invalid!r}")
    misclassified = tuple(
        check_id
        for session in ACCEPTANCE_SESSIONS
        for check_id in session.operator_checks
        if not check_id.startswith("H-")
    ) + tuple(
        check_id
        for session in ACCEPTANCE_SESSIONS
        for check_id in session.advisor_checks
        if not check_id.startswith("A-")
    )
    if misclassified:
        raise ValueError(f"acceptance check IDs use the wrong responsibility: {misclassified!r}")
    if any(not session.check_ids for session in ACCEPTANCE_SESSIONS):
        raise ValueError("every acceptance session must own at least one check")
    session_keys = tuple(session.key for session in ACCEPTANCE_SESSIONS)
    if len(session_keys) != len(set(session_keys)):
        raise ValueError("acceptance session keys must be unique")


_validate_catalog()


__all__ = [
    "ACCEPTANCE_SESSIONS",
    "AcceptanceSession",
    "acceptance_check_counts",
    "acceptance_check_ids",
    "build_supervised_acceptance_worksheet",
]
