"""
Prefect data model for the Sing Yin Study Prefect Duty Roster System.
Each Prefect represents a student who participates in the duty roster.
The model encodes all required fields and validates school-specific constraints.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date
from models.enums import Role, Form, Weekday, Room, SchoolRules


@dataclass
class Prefect:
    """A Study Prefect at Sing Yin Secondary School.

    Attributes:
        name: Prefect name in English (as registered).
        name_zh: Prefect name in Chinese (optional, for bilingual display).
        form: Year level (F.3, F.4, or F.5).
        class_name: Class section identifier (e.g., "4A", "5B").
        role: Duty role (Head / AHP / Study Prefect).
        available: Days the prefect is generally available for duty.
        history_weight: Cumulative duty load points for fairness balancing.
        remarks: Free-text notes (AI-parseable, e.g., leave reasons).
        date_joined: When the prefect was added to the system.
        active: Whether the prefect is currently active in the roster.
    """
    # ---- Identity ----
    name: str
    name_zh: Optional[str] = None

    # ---- Academic ----
    form: Form = Form.F4
    class_name: str = ""

    # ---- Duty Role ----
    role: Role = Role.STUDY_PREFECT

    # ---- Availability ----
    available: List[Weekday] = field(default_factory=list)

    # ---- Fairness ----
    history_weight: float = 0.0

    # ---- Metadata ----
    remarks: str = ""
    date_joined: Optional[date] = None
    active: bool = True

    # =========================================================================
    # Validation
    # =========================================================================

    def __post_init__(self):
        """Validate school constraints after construction."""
        errors: List[str] = []

        if not self.name or not self.name.strip():
            errors.append("Name is required.")

        if self.form not in SchoolRules.ALLOWED_FORMS:
            errors.append(
                f"Form must be one of "
                f"{[f.value for f in SchoolRules.ALLOWED_FORMS]}, "
                f"got {self.form.value}"
            )

        if self.role == Role.ASSISTANT_HEAD_PREFECT:
            if self.form == Form.F3:
                errors.append("AHP must be F.4 or F.5 (F.3 students cannot serve as AHP).")

        if self.history_weight < 0:
            errors.append("history_weight must be non-negative.")

        for day in self.available:
            if day not in Weekday:
                errors.append(f"Invalid weekday in available: {day}")

        if errors:
            raise ValueError(
                f"Invalid Prefect '{self.name or '(unnamed)'}':\n  "
                + "\n  ".join(errors)
            )

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def is_ahp(self) -> bool:
        return self.role == Role.ASSISTANT_HEAD_PREFECT

    @property
    def is_study_prefect(self) -> bool:
        return self.role == Role.STUDY_PREFECT

    @property
    def is_head(self) -> bool:
        return self.role == Role.HEAD_STUDY_PREFECT

    @property
    def is_leader(self) -> bool:
        return self.role in (Role.HEAD_STUDY_PREFECT, Role.ASSISTANT_HEAD_PREFECT)

    @property
    def can_do_room_duty(self) -> bool:
        return self.role == Role.STUDY_PREFECT

    def is_available_on(self, day: Weekday) -> bool:
        return day in self.available

    # =========================================================================
    # Methods
    # =========================================================================

    def add_load(self, points: float):
        if points < 0:
            raise ValueError("Load points must be non-negative.")
        self.history_weight += points

    def apply_multiplier(self, multiplier: float):
        if not (SchoolRules.WORKLOAD_MULTIPLIER_MIN <= multiplier <= SchoolRules.WORKLOAD_MULTIPLIER_MAX):
            raise ValueError(
                f"Multiplier must be between {SchoolRules.WORKLOAD_MULTIPLIER_MIN} "
                f"and {SchoolRules.WORKLOAD_MULTIPLIER_MAX}, got {multiplier}."
            )
        self.history_weight *= multiplier

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "name_zh": self.name_zh or "",
            "form": self.form.value,
            "class": self.class_name,
            "role": self.role.value,
            "available": ",".join(d.value for d in self.available),
            "history_weight": self.history_weight,
            "remarks": self.remarks,
            "active": self.active,
        }

    @classmethod
    def from_row(cls, row: dict) -> "Prefect":
        available_raw = row.get("available", "")
        if isinstance(available_raw, str) and available_raw:
            available = [
                Weekday(d.strip())
                for d in available_raw.split(",")
                if d.strip()
            ]
        elif isinstance(available_raw, list):
            available = [Weekday(d) if isinstance(d, str) else d for d in available_raw]
        else:
            available = []

        return cls(
            name=str(row.get("name", "")),
            name_zh=str(row.get("name_zh", "")) if row.get("name_zh") else None,
            form=Form(str(row.get("form", "F.4"))),
            class_name=str(row.get("class", "")),
            role=Role(str(row.get("role", "Study Prefect"))),
            available=available,
            history_weight=float(row.get("history_weight", 0)),
            remarks=str(row.get("remarks", "")),
            active=bool(row.get("active", True)),
        )

    def __repr__(self) -> str:
        return (
            f"Prefect(name='{self.name}', role={self.role.value}, "
            f"form={self.form.value}, load={self.history_weight:.1f})"
        )
