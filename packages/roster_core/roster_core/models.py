from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from roster_policy import DutyPost, PrefectRole, SchoolDay


_LEGACY_ROLE_CODES = {
    "assistant_head": PrefectRole.ASSISTANT_HEAD,
    "Assistant Head Study Prefect (助理首席導學風紀)": PrefectRole.ASSISTANT_HEAD,
    "Assistant Head Study Prefect": PrefectRole.ASSISTANT_HEAD,
    "study_prefect": PrefectRole.STUDY_PREFECT,
    "Study Prefect (導學風紀)": PrefectRole.STUDY_PREFECT,
    "Study Prefect": PrefectRole.STUDY_PREFECT,
}


def parse_prefect_role(value: object) -> PrefectRole:
    """Translate supported import labels once at the adapter boundary."""

    try:
        return _LEGACY_ROLE_CODES[str(value).strip()]
    except KeyError as error:
        raise ValueError(f"Unsupported prefect role code: {value!s}") from error


@dataclass(frozen=True)
class Prefect:
    id: str
    name: str
    form: str
    class_name: str
    role: PrefectRole
    available_days: frozenset[SchoolDay]
    history_weight: float
    history_duties: int = 0
    needs_mentoring: bool = False
    fixed_general_duty: str = "NONE"
    remarks: str = ""

    @classmethod
    def from_seed(cls, raw: dict[str, Any]) -> "Prefect":
        return cls(
            id=str(raw["id"]),
            name=str(raw["name"]),
            form=str(raw["form"]),
            class_name=str(raw["class"]),
            role=parse_prefect_role(raw.get("roleCode", raw.get("role"))),
            available_days=frozenset(SchoolDay[str(day)] for day in raw.get("availableDays", [])),
            history_weight=float(raw.get("historyWeight", 0)),
            history_duties=int(raw.get("historyDuties", 0)),
            needs_mentoring=bool(raw.get("needsMentoring", False)),
            fixed_general_duty=str(raw.get("fixedGeneralDuty", "NONE")),
            remarks=str(raw.get("remarks", "")),
        )


@dataclass(frozen=True)
class Assignment:
    day: SchoolDay
    post: DutyPost
    prefect_id: str
    prefect_name: str
    weight: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "day": self.day.name,
            "post": self.post.value,
            "prefectId": self.prefect_id,
            "prefectName": self.prefect_name,
            "weight": self.weight,
        }
