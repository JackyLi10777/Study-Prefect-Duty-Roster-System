from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import select

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.persistence.database import database_url
from nicegui_app.persistence.models import AuditEventRecord, FairnessLedgerRecord
from nicegui_app.services.roster_workflow import RosterWorkflow, WorkflowError
from roster_core.generator import RosterGenerationError, generate_weekly_roster
from roster_core.loaders import load_prefect_seed
from roster_policy import SchoolDay, duty_weight, required_posts_for_day


WEEK_START = date(2026, 9, 7)


def _workflow(tmp_path) -> RosterWorkflow:
    service = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    service.bootstrap()
    return service


def _alembic_config(database_path: Path) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url(database_path))
    return config


def test_default_multiplier_is_the_existing_generation_behavior() -> None:
    prefects = load_prefect_seed()

    default_assignments = generate_weekly_roster(prefects)
    explicit_assignments = generate_weekly_roster(prefects, history_priority_multiplier=1.0)

    assert default_assignments == explicit_assignments


@pytest.mark.parametrize("multiplier", [0.8, 2.0])
def test_supported_multiplier_endpoints_preserve_every_hard_rule(multiplier: float) -> None:
    prefects = load_prefect_seed()
    assignments = generate_weekly_roster(prefects, history_priority_multiplier=multiplier)
    by_day = defaultdict(list)
    by_prefect = defaultdict(set)

    for assignment in assignments:
        by_day[assignment.day].append(assignment)
        by_prefect[assignment.prefect_id].add(assignment.day)
        assert assignment.weight == duty_weight(assignment.post)

    for day in SchoolDay:
        assert Counter(item.post for item in by_day[day]) == Counter(required_posts_for_day(day))
        assigned_ids = [item.prefect_id for item in by_day[day]]
        assert len(assigned_ids) == len(set(assigned_ids))
    for days in by_prefect.values():
        ordered_days = sorted(days)
        assert all(int(current) - int(previous) > 1 for previous, current in zip(ordered_days, ordered_days[1:]))
    assert sum(item.weight for item in assignments) == pytest.approx(34.0)


def test_multiplier_changes_priority_without_changing_slots_or_weights() -> None:
    prefects = load_prefect_seed()
    lower_priority = generate_weekly_roster(prefects, history_priority_multiplier=0.8)
    higher_priority = generate_weekly_roster(prefects, history_priority_multiplier=2.0)

    assert [item.prefect_id for item in lower_priority] != [item.prefect_id for item in higher_priority]
    assert [(item.day, item.post, item.weight) for item in lower_priority] == [
        (item.day, item.post, item.weight) for item in higher_priority
    ]


@pytest.mark.parametrize("multiplier", [0.79, 2.01, float("nan"), float("inf")])
def test_multiplier_outside_the_bounded_range_is_rejected(multiplier: float) -> None:
    with pytest.raises(RosterGenerationError, match="0.8 to 2.0"):
        generate_weekly_roster(load_prefect_seed(), history_priority_multiplier=multiplier)


def test_workflow_persists_and_audits_multiplier_without_changing_ledger_deltas(tmp_path) -> None:
    workflow = _workflow(tmp_path)
    before_loads = workflow.prefect_loads()

    draft = workflow.generate_and_save_draft(WEEK_START, history_priority_multiplier=2.0)
    draft_read_model = workflow.roster_week(draft.id)
    published = workflow.publish(draft.id, expected_week_version=draft.version)
    published_read_model = workflow.roster_week(draft.id)
    assignments = workflow.assignments(draft.id)

    assert draft.history_priority_multiplier == pytest.approx(2.0)
    assert draft_read_model["historyPriorityMultiplier"] == pytest.approx(2.0)
    assert published.history_priority_multiplier == pytest.approx(2.0)
    assert published_read_model["historyPriorityMultiplier"] == pytest.approx(2.0)
    assert workflow.roster_weeks()[0]["historyPriorityMultiplier"] == pytest.approx(2.0)

    expected_delta_by_assignment = {int(row["id"]): float(row["weight"]) for row in assignments}
    assert workflow.sessions is not None
    with workflow.sessions() as session:
        ledger_rows = session.scalars(
            select(FairnessLedgerRecord).where(FairnessLedgerRecord.roster_week_id == draft.id)
        ).all()
        audit_rows = session.scalars(
            select(AuditEventRecord).where(AuditEventRecord.roster_week_id == draft.id)
        ).all()

    assert len(ledger_rows) == len(assignments)
    assert all(
        row.assignment_id is not None
        and row.delta == pytest.approx(expected_delta_by_assignment[row.assignment_id])
        for row in ledger_rows
    )
    assert sum(workflow.prefect_loads().values()) - sum(before_loads.values()) == pytest.approx(34.0)
    multiplier_audits = {
        row.event_type: json.loads(row.metadata_json)["historyPriorityMultiplier"]
        for row in audit_rows
        if row.event_type in {"draft_generated", "roster_published"}
    }
    assert multiplier_audits == {"draft_generated": 2.0, "roster_published": 2.0}
    assert workflow.reconcile_fairness().balanced


def test_workflow_rejects_invalid_multiplier_without_creating_a_week(tmp_path) -> None:
    workflow = _workflow(tmp_path)

    with pytest.raises(WorkflowError, match="0.8 to 2.0"):
        workflow.generate_and_save_draft(WEEK_START, history_priority_multiplier=2.1)

    assert workflow.roster_weeks() == []


def test_migration_preserves_existing_weeks_with_neutral_default(tmp_path) -> None:
    database_path = tmp_path / "pre-multiplier.sqlite3"
    config = _alembic_config(database_path)
    command.upgrade(config, "0004")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO roster_weeks (
                week_start, status, version, policy_version, generated_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("2026-09-07", "draft", 1, "test-policy", "2026-09-01", "2026-09-01", "2026-09-01"),
        )
        connection.commit()

    command.upgrade(config, "head")

    with sqlite3.connect(database_path) as connection:
        multiplier = connection.execute(
            "SELECT history_priority_multiplier FROM roster_weeks WHERE week_start = ?",
            ("2026-09-07",),
        ).fetchone()
        assert multiplier == (1.0,)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE roster_weeks SET history_priority_multiplier = 2.1 WHERE week_start = ?",
                ("2026-09-07",),
            )
