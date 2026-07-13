from __future__ import annotations

from datetime import date
import hashlib
from io import BytesIO
import json

from pypdf import PdfReader
import pytest

from nicegui_app.services.roster_workflow import PrefectInput, RosterWorkflow, WorkflowError
from nicegui_app.services.summary_report_export import (
    build_duty_allocation_statement_pdf,
    build_summary_report_json,
    build_summary_report_pdf,
)


FIRST_WEEK = date(2026, 9, 7)
SECOND_WEEK = date(2026, 9, 14)


@pytest.fixture
def workflow(tmp_path) -> RosterWorkflow:
    service = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    service.bootstrap()
    return service


def _publish(service: RosterWorkflow, week_start: date):
    draft = service.generate_and_save_draft(week_start)
    service.publish(draft.id, expected_week_version=draft.version)
    return draft


def test_empty_summary_is_truthful_and_read_only(workflow: RosterWorkflow) -> None:
    backups_before = tuple(workflow.backup_dir.glob("*.sqlite3"))

    report = workflow.build_period_report()

    assert report.sources == ()
    assert report.published_week_count == 0
    assert report.recorded_slot_count == 0
    assert report.coverage_rate is None
    assert "no_published_rosters" in report.note_codes
    assert tuple(workflow.backup_dir.glob("*.sqlite3")) == backups_before
    assert workflow.reconcile_fairness().balanced


def test_period_summary_uses_only_published_final_assignment_state(workflow: RosterWorkflow) -> None:
    first = _publish(workflow, FIRST_WEEK)
    second = _publish(workflow, SECOND_WEEK)
    third_draft = workflow.generate_and_save_draft(date(2026, 9, 21))
    assert third_draft.status == "draft"

    first_assignment = next(item for item in workflow.assignments(first.id) if item["postCode"] == "ROOM_302")
    workflow.apply_leave_adjustment(
        roster_week_id=first.id,
        assignment_id=int(first_assignment["id"]),
        replacement_prefect_id=None,
        reason="Approved absence",
        command_id="summary-vacancy",
        expected_week_version=int(workflow.roster_week(first.id)["version"]),
    )
    second_assignment = next(item for item in workflow.assignments(second.id) if item["postCode"] == "ROOM_302")
    replacement = workflow.recommend_substitutes(second.id, int(second_assignment["id"]))[0]
    workflow.apply_leave_adjustment(
        roster_week_id=second.id,
        assignment_id=int(second_assignment["id"]),
        replacement_prefect_id=str(replacement["id"]),
        reason="Approved activity",
        command_id="summary-replacement",
        expected_week_version=int(workflow.roster_week(second.id)["version"]),
    )

    backups_before = tuple(workflow.backup_dir.glob("*.sqlite3"))
    report = workflow.build_period_report(period_start=FIRST_WEEK, period_end=SECOND_WEEK)

    assert report.published_week_count == 2
    assert [source.roster_week_id for source in report.sources] == [first.id, second.id]
    assert all(source.policy_version for source in report.sources)
    assert all(0.8 <= source.history_priority_multiplier <= 2.0 for source in report.sources)
    assert report.recorded_slot_count == 52
    assert report.active_assignment_count == 51
    assert report.vacant_slot_count == 1
    assert report.coverage_rate == pytest.approx(51 / 52 * 100, abs=0.01)
    assert report.leave_adjustment_count == 2
    assert report.replacement_count == 1
    assert report.assist_required_count == 10
    assert report.assist_filled_count == 10
    assert report.scheduled_minutes > 0
    assert report.scheduled_minutes == report.active_assignment_count * 80
    assert report.fairness_ledger_balanced
    assert len(report.trend) == 2
    assert all(row.name_zh and row.name_zh.isascii() is False for row in report.contributions)
    assert sum(row.duty_count for row in report.contributions) == 51
    assert sum(row.assist_in_charge_count for row in report.contributions) == 10
    assert all(sum(item.scheduled_minutes for item in row.allocations) == row.scheduled_minutes for row in report.contributions)
    assert tuple(workflow.backup_dir.glob("*.sqlite3")) == backups_before


def test_report_range_is_defined_by_whole_roster_week_starts(workflow: RosterWorkflow) -> None:
    _publish(workflow, FIRST_WEEK)
    _publish(workflow, SECOND_WEEK)

    report = workflow.build_period_report(period_start=SECOND_WEEK, period_end=SECOND_WEEK)

    assert report.published_week_count == 1
    assert report.period_start == SECOND_WEEK
    assert report.period_end == SECOND_WEEK
    with pytest.raises(WorkflowError, match="Monday"):
        workflow.build_period_report(period_start=date(2026, 9, 8), period_end=SECOND_WEEK)
    with pytest.raises(WorkflowError, match="after"):
        workflow.build_period_report(period_start=SECOND_WEEK, period_end=FIRST_WEEK)


def test_published_week_trend_is_invariant_to_later_directory_add_and_archive(
    workflow: RosterWorkflow,
) -> None:
    _publish(workflow, FIRST_WEEK)
    before = workflow.build_period_report(period_start=FIRST_WEEK, period_end=FIRST_WEEK).trend[0]

    workflow.create_prefect(
        PrefectInput(
            name_zh="測試新風紀",
            form="F.3",
            class_name="3H",
            role_code="study_prefect",
            available_days=("MONDAY", "WEDNESDAY"),
        )
    )
    original = workflow.prefects()[0]
    workflow.archive_prefect(str(original["id"]))

    after = workflow.build_period_report(period_start=FIRST_WEEK, period_end=FIRST_WEEK).trend[0]
    assert after == before


def test_json_evidence_hashes_the_shared_language_neutral_payload(workflow: RosterWorkflow) -> None:
    _publish(workflow, FIRST_WEEK)
    report = workflow.build_period_report()

    download = build_summary_report_json(report)
    envelope = json.loads(download.content.decode("utf-8"))
    canonical = json.dumps(
        envelope["payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")

    assert download.filename == "SYSS_Service_Summary_20260907_20260907.json"
    assert envelope["evidenceType"] == "sing-yin-study-prefect-period-summary"
    assert envelope["payloadSha256"] == hashlib.sha256(canonical).hexdigest()
    assert envelope["payload"]["sources"][0]["policy_version"]
    assert envelope["payload"]["sources"][0]["history_priority_multiplier"] == 1.0


def test_bilingual_summary_pdfs_keep_authoritative_chinese_names(workflow: RosterWorkflow) -> None:
    _publish(workflow, FIRST_WEEK)
    report = workflow.build_period_report()
    authoritative_names = {row.name_zh for row in report.contributions}

    chinese = build_summary_report_pdf(report, language="zh")
    english = build_summary_report_pdf(report, language="en")
    chinese_text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(chinese.content)).pages)
    english_text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(english.content)).pages)

    assert chinese.content.startswith(b"%PDF")
    assert english.content.startswith(b"%PDF")
    assert "服務與公平總結報告" in chinese_text
    assert "Service & Fairness Summary" in english_text
    assert "scheduled service only" in english_text
    for name in authoritative_names:
        assert name in chinese_text
        assert name in english_text


def test_bilingual_allocation_statement_lists_dates_room_times_and_calculated_hours(
    workflow: RosterWorkflow,
) -> None:
    _publish(workflow, FIRST_WEEK)
    report = workflow.build_period_report()
    contribution = next(row for row in report.contributions if row.allocations)

    assert sum(item.scheduled_minutes for item in contribution.allocations) == contribution.scheduled_minutes
    assert all(item.duty_date >= FIRST_WEEK for item in contribution.allocations)
    assert {item.start_time for item in contribution.allocations} == {"15:40"}
    assert {item.end_time for item in contribution.allocations} == {"17:00"}
    assert {item.scheduled_minutes for item in contribution.allocations} == {80}
    chinese = build_duty_allocation_statement_pdf(report, contribution.prefect_id, language="zh")
    english = build_duty_allocation_statement_pdf(report, contribution.prefect_id, language="en")
    chinese_text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(chinese.content)).pages)
    english_text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(english.content)).pages)

    assert chinese.content.startswith(b"%PDF")
    assert english.content.startswith(b"%PDF")
    assert contribution.name_zh in chinese_text
    assert contribution.name_zh in english_text
    assert contribution.allocations[0].duty_date.isoformat() in chinese_text
    assert contribution.allocations[0].start_time in english_text
    assert "當值時間" in chinese_text
    assert "Duty time" in english_text
    assert "18:30" not in chinese_text
    assert "18:30" not in english_text
    assert "核對實際出席" in chinese_text
    assert "attendance is checked" in english_text
