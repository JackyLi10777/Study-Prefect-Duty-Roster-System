from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from roster_policy import DutyPost, SchoolDay


@dataclass(frozen=True)
class Prefect:
    id: str
    name: str
    form: str
    class_name: str
    role: str
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
            role=str(raw["role"]),
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

