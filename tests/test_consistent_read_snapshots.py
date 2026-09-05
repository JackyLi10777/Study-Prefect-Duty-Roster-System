"""Multi-query exports must keep one committed SQLite state during real writes."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import date
from threading import Event
from types import SimpleNamespace

import pytest

from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.services.roster_workflow import RosterWorkflow
from nicegui_app.services.workflow_dependencies import RosterWeekRecord


WEEK_START = date(2026, 9, 7)


@pytest.fixture
def workflows(tmp_path):
    reader = RosterWorkflow(
        database_path=tmp_path / "fictional-snapshots.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    reader.bootstrap()
    writer = RosterWorkflow(
        database_path=reader.database_path,
        backup_dir=reader.backup_dir,
    )
    writer.bootstrap()
    draft = reader.generate_and_save_draft(WEEK_START)
    try:
        yield reader, writer, draft
    finally:
        reader._dispose_database_connections()
        writer._dispose_database_connections()


def _read_across_commit(read, mutate, first_read, committed):
    def concurrent_write():
        assert first_read.wait(15), "Reader did not reach the first materialized SELECT"
        try:
            mutate()
        finally:
            committed.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        writer = pool.submit(concurrent_write)
        reader = pool.submit(read)
        # Surface a failed mutation before interpreting any snapshot mismatch.
        writer.result(timeout=20)
        return reader.result(timeout=20)


@pytest.mark.parametrize("change", ["vacancy", "replacement", "restore"])
def test_schedule_snapshot_does_not_mix_version_with_concurrent_adjustment(
    workflows, monkeypatch, change,
):
    reader, writer, draft = workflows
    writer.publish(draft.id, expected_week_version=draft.version)
    initial_week, initial_assignments = writer.roster_schedule_snapshot(draft.id)
    assignment = next(row for row in initial_assignments if row["postCode"] == "ROOM_302")
    if change == "restore":
        writer.apply_leave_adjustment(
            roster_week_id=draft.id, assignment_id=int(assignment["id"]),
            replacement_prefect_id=None, command_id="prepare-schedule-vacancy",
            expected_week_version=int(initial_week["version"]),
        )
    before = reader.roster_schedule_snapshot(draft.id)
    substitute_id = (
        str(writer.recommend_substitutes(draft.id, int(assignment["id"]))[0]["id"])
        if change != "vacancy" else None
    )
    first_read, committed = Event(), Event()
    original_week_read = reader._week_or_error

    def pause_after_week(*args, **kwargs):
        week = original_week_read(*args, **kwargs)
        first_read.set()
        assert committed.wait(15), "Writer must commit while the snapshot remains open"
        return week

    monkeypatch.setattr(reader, "_week_or_error", pause_after_week)

    def adjust():
        writer.apply_leave_adjustment(
            roster_week_id=draft.id,
            assignment_id=int(assignment["id"]),
            replacement_prefect_id=substitute_id,
            reason="Fictional concurrent adjustment",
            command_id="schedule-snapshot-adjustment",
            expected_week_version=int(before[0]["version"]),
        )

    snapshot = _read_across_commit(
        lambda: reader.roster_schedule_snapshot(draft.id), adjust, first_read, committed,
    )
    assert snapshot == before
    after = writer.roster_schedule_snapshot(draft.id)
    assert after[0]["version"] == before[0]["version"] + 1
    assert after[1] != before[1]


@pytest.mark.parametrize("change", ["publish", "withdraw", "adjust", "restore"])
def test_period_report_keeps_sources_allocations_and_ledger_at_one_commit(
    workflows, monkeypatch, change,
):
    reader, writer, draft = workflows
    if change != "publish":
        writer.publish(draft.id, expected_week_version=draft.version)
    assignment = next(row for row in writer.assignments(draft.id) if row["postCode"] == "ROOM_302")
    if change == "restore":
        writer.apply_leave_adjustment(
            roster_week_id=draft.id, assignment_id=int(assignment["id"]),
            replacement_prefect_id=None, command_id="prepare-report-vacancy",
            expected_week_version=int(writer.roster_week(draft.id)["version"]),
        )
    before = reader.build_period_report()
    before_week = writer.roster_week(draft.id)
    first_read, committed = Event(), Event()
    original_session = reader._session

    @contextmanager
    def pause_after_materialized_weeks():
        with original_session() as session:
            original_scalars = session.scalars

            def scalars(statement, *args, **kwargs):
                result = original_scalars(statement, *args, **kwargs)
                if (
                    not first_read.is_set()
                    and statement.column_descriptions[0].get("entity") is RosterWeekRecord
                ):
                    rows = result.all()
                    first_read.set()
                    assert committed.wait(15), "Writer must commit after the report's initial SELECT"
                    return SimpleNamespace(all=lambda: rows)
                return result

            with monkeypatch.context() as patch:
                patch.setattr(session, "scalars", scalars)
                yield session

    monkeypatch.setattr(reader, "_session", pause_after_materialized_weeks)

    def change_roster():
        if change == "publish":
            writer.publish(draft.id, expected_week_version=int(before_week["version"]))
        elif change == "withdraw":
            writer.withdraw_published_roster(
                draft.id, expected_version=int(before_week["version"]),
                reason="Fictional concurrent withdrawal", command_id="report-snapshot-withdrawal",
            )
        else:
            writer.apply_leave_adjustment(
                roster_week_id=draft.id,
                assignment_id=int(assignment["id"]),
                replacement_prefect_id=str(assignment["prefectId"]) if change == "restore" else None,
                reason="Fictional concurrent absence", command_id="report-snapshot-adjustment",
                expected_week_version=int(before_week["version"]),
            )

    # Without a real read transaction, publish raises KeyError because the
    # assignments SELECT sees a newly published week absent from week_by_id.
    report = _read_across_commit(reader.build_period_report, change_roster, first_read, committed)
    assert replace(report, generated_at=before.generated_at) == before
    assert report.scheduled_minutes == report.active_assignment_count * 80
    assert writer.build_period_report().active_assignment_count != before.active_assignment_count
