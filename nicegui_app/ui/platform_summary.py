"""Display-safe, anonymous evidence for the public-facing platform story."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from nicegui_app.release_evidence import ReleaseEvidence, load_release_evidence


class HandoverReadinessSource(Protocol):
    def handover_readiness(self) -> dict[str, object]: ...


@dataclass(frozen=True)
class PlatformSummary:
    """The only operational values allowed on the Platform & Team page."""

    active_prefect_count: int = 0
    roster_count: int = 0
    verified_backup: bool = False
    release_state: str = "missing"
    release_passed_checks: int = 0
    release_total_checks: int = 0
    available: bool = True

    @classmethod
    def unavailable(cls) -> "PlatformSummary":
        return cls(available=False)


def load_platform_summary(
    workflow: HandoverReadinessSource,
    *,
    evidence_loader: Callable[[], ReleaseEvidence] = load_release_evidence,
) -> PlatformSummary:
    """Combine existing read models without exposing paths, names, or records."""
    readiness = workflow.handover_readiness()
    evidence = evidence_loader()
    return PlatformSummary(
        active_prefect_count=max(0, int(readiness["activePrefectCount"])),
        roster_count=max(0, int(readiness["rosterCount"])),
        verified_backup=bool(readiness["verifiedBackup"]),
        release_state=evidence.state,
        release_passed_checks=max(0, evidence.passed_checks),
        release_total_checks=max(0, evidence.total_checks),
    )
