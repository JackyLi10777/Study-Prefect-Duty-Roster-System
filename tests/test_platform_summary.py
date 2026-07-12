from __future__ import annotations

from datetime import datetime

import pytest

from nicegui_app.release_evidence import ReleaseEvidence
from nicegui_app.ui.platform_summary import PlatformSummary, load_platform_summary


class _WorkflowStub:
    def handover_readiness(self) -> dict[str, object]:
        return {
            "activePrefectCount": 24,
            "rosterCount": 9,
            "verifiedBackup": True,
            "backupPath": "must-not-enter-the-summary.sqlite3",
        }


def test_platform_summary_exposes_only_anonymous_readiness_evidence() -> None:
    evidence = ReleaseEvidence("pass", 8, 8, datetime(2026, 7, 12, 12, 0))

    summary = load_platform_summary(_WorkflowStub(), evidence_loader=lambda: evidence)

    assert summary == PlatformSummary(
        active_prefect_count=24,
        roster_count=9,
        verified_backup=True,
        release_state="pass",
        release_passed_checks=8,
        release_total_checks=8,
    )
    assert not hasattr(summary, "backup_path")
    assert not hasattr(summary, "prefect_names")
    assert not hasattr(summary, "roster_content")


def test_platform_summary_does_not_hide_read_failures_from_the_page_boundary() -> None:
    class BrokenWorkflow:
        def handover_readiness(self) -> dict[str, object]:
            raise RuntimeError("private diagnostic detail")

    with pytest.raises(RuntimeError, match="private diagnostic detail"):
        load_platform_summary(BrokenWorkflow())


def test_unavailable_platform_summary_contains_no_operational_payload() -> None:
    assert PlatformSummary.unavailable() == PlatformSummary(available=False)
