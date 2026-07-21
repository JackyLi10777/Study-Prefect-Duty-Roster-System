from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import sqlite3

from sqlalchemy import event, select

from nicegui_app.persistence.models import (
    FairnessLedgerRecord,
    PrefectRecord,
    RosterWeekRecord,
)
from nicegui_app.services.roster_workflow import RosterWorkflow


_LEDGER_DELTAS = (
    (1.5, 1),
    (-0.5, -1),
    (0.25, 1),
    (-0.25, 0),
    (0.5, 1),
    (-0.5, -1),
)


def _workflow(tmp_path: Path) -> RosterWorkflow:
    workflow = RosterWorkflow(
        database_path=tmp_path / "fairness.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    workflow.bootstrap()
    return workflow


def _insert_reconciliation_rows(
    workflow: RosterWorkflow,
    *,
    count: int,
    ledger_entries_per_prefect: int,
    start_index: int = 0,
) -> None:
    assert workflow.sessions is not None
    now = datetime(2026, 9, 1)
    with workflow.sessions() as session:
        week = session.scalar(select(RosterWeekRecord).order_by(RosterWeekRecord.id))
        if week is None:
            week = RosterWeekRecord(
                week_start=date(2026, 9, 7),
                status="published",
                version=1,
                policy_version="test",
                history_priority_multiplier=1.0,
                generated_at=now,
                published_at=now,
                created_at=now,
                updated_at=now,
            )
            session.add(week)
            session.flush()

        prefects: list[PrefectRecord] = []
        for offset in range(count):
            prefect_index = start_index + offset
            anchor_weight = float(prefect_index % 5) / 4
            anchor_duties = prefect_index % 3
            deltas = _LEDGER_DELTAS[:ledger_entries_per_prefect]
            prefect = PrefectRecord(
                id=f"prefect-{prefect_index:04d}",
                name_zh=f"效能測試風紀{prefect_index:04d}",
                form="F.5",
                class_name="5A",
                role_code="study_prefect",
                history_weight=round(anchor_weight + sum(delta for delta, _ in deltas), 4),
                history_duties=anchor_duties + sum(duty for _, duty in deltas),
                history_weight_anchor=anchor_weight,
                history_duties_anchor=anchor_duties,
                needs_mentoring=False,
                fixed_general_duty="NONE",
                remarks="",
                version=1,
                active=True,
                created_at=now,
                updated_at=now,
            )
            session.add(prefect)
            prefects.append(prefect)
        session.flush()

        for prefect in prefects:
            prefect_index = int(prefect.id.removeprefix("prefect-"))
            for entry_index, (delta, duty_delta) in enumerate(
                _LEDGER_DELTAS[:ledger_entries_per_prefect]
            ):
                operation_id = f"reconcile-{prefect_index}-{entry_index}"
                session.add(
                    FairnessLedgerRecord(
                        prefect_id=prefect.id,
                        roster_week_id=week.id,
                        assignment_id=None,
                        delta=delta,
                        duty_delta=duty_delta,
                        event_type=f"test_delta_{entry_index}",
                        source_type="test",
                        source_id=operation_id,
                        operation_id=operation_id,
                        reason="",
                        created_at=now,
                    )
                )
        session.commit()


def test_grouped_reconciliation_preserves_anchor_plus_ledger_semantics(tmp_path: Path) -> None:
    workflow = _workflow(tmp_path)
    _insert_reconciliation_rows(
        workflow,
        count=1,
        ledger_entries_per_prefect=4,
    )
    _insert_reconciliation_rows(
        workflow,
        count=1,
        ledger_entries_per_prefect=0,
        start_index=1,
    )
    assert workflow.sessions is not None
    with workflow.sessions() as session:
        record = session.get(PrefectRecord, "prefect-0000")
        assert record is not None
        record.history_weight += 0.5
        session.commit()

    report = workflow.reconcile_fairness()

    assert report.checked_prefects == 2
    assert len(report.discrepancies) == 1
    discrepancy = report.discrepancies[0]
    assert discrepancy.prefect_id == "prefect-0000"
    assert discrepancy.expected_weight == 1.0
    assert discrepancy.actual_weight == 1.5
    assert discrepancy.expected_duties == discrepancy.actual_duties == 1


def test_reconciliation_executes_one_select_for_a_large_directory(tmp_path: Path) -> None:
    workflow = _workflow(tmp_path)
    _insert_reconciliation_rows(
        workflow,
        count=300,
        ledger_entries_per_prefect=4,
    )
    assert workflow.sessions is not None
    engine = workflow.sessions.kw["bind"]
    select_statements: list[str] = []

    def record_select(_connection, _cursor, statement, _parameters, _context, _many) -> None:
        normalized = " ".join(statement.split()).lower()
        if normalized.startswith("select"):
            select_statements.append(normalized)

    event.listen(engine, "before_cursor_execute", record_select)
    try:
        report = workflow.reconcile_fairness()
    finally:
        event.remove(engine, "before_cursor_execute", record_select)

    assert report.balanced
    assert report.checked_prefects == 300
    assert len(select_statements) == 1
    assert "left outer join fairness_ledger" in select_statements[0]
    assert "group by prefects.id" in select_statements[0]


def test_reconciliation_scale_path_uses_the_prefect_ledger_index(tmp_path: Path) -> None:
    workflow = _workflow(tmp_path)
    _insert_reconciliation_rows(
        workflow,
        count=600,
        ledger_entries_per_prefect=6,
    )

    report = workflow.reconcile_fairness()
    with sqlite3.connect(workflow.database_path) as connection:
        plan = connection.execute(
            """
            EXPLAIN QUERY PLAN
            SELECT p.id, COALESCE(SUM(f.delta), 0.0), COALESCE(SUM(f.duty_delta), 0)
            FROM prefects AS p
            LEFT JOIN fairness_ledger AS f ON f.prefect_id = p.id
            GROUP BY p.id
            ORDER BY p.id
            """
        ).fetchall()

    assert report.balanced
    assert report.checked_prefects == 600
    assert any("ix_fairness_ledger_prefect_id" in str(row[3]) for row in plan)
