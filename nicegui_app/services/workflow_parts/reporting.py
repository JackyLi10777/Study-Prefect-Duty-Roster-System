"""Read-only operational reporting derived from published roster facts.

The report deliberately owns no counters of its own.  Published assignments,
post-publication adjustments, and the immutable fairness ledger remain the
authoritative sources, so generating a report can never double-count service.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import median, pstdev

from sqlalchemy import select

from nicegui_app.services.workflow_dependencies import *
from roster_policy import DUTY_TIME_WINDOWS


def _distribution(values: list[float]) -> tuple[float, float, float, float, float]:
    if not values:
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    minimum = min(values)
    maximum = max(values)
    return (
        round(minimum, 4),
        round(float(median(values)), 4),
        round(maximum, 4),
        round(maximum - minimum, 4),
        round(float(pstdev(values)), 4) if len(values) > 1 else 0.0,
    )


def _duty_minutes(post_code: str) -> int:
    post = DutyPost[post_code]
    start_text, end_text = DUTY_TIME_WINDOWS[post]
    start = datetime.strptime(start_text, "%H:%M")
    end = datetime.strptime(end_text, "%H:%M")
    return int((end - start).total_seconds() // 60)


class ReportingWorkflowMixin:
    """Build explainable period reports without introducing a second ledger."""

    def build_period_report(
        self,
        *,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> PeriodSummaryReport:
        if period_start is not None and period_end is not None and period_start > period_end:
            raise WorkflowError("Report start date must not be after its end date.")
        if period_start is not None:
            self._require_monday(period_start)
        if period_end is not None:
            self._require_monday(period_end)

        with self._session() as session:
            statement = select(RosterWeekRecord).where(RosterWeekRecord.status == "published")
            if period_start is not None:
                statement = statement.where(RosterWeekRecord.week_start >= period_start)
            if period_end is not None:
                statement = statement.where(RosterWeekRecord.week_start <= period_end)
            weeks = list(session.scalars(statement.order_by(RosterWeekRecord.week_start, RosterWeekRecord.id)).all())
            source_ids = [week.id for week in weeks]
            week_by_id = {week.id: week for week in weeks}

            all_prefects = list(session.scalars(select(PrefectRecord).order_by(PrefectRecord.name_zh)).all())
            active_prefects = [prefect for prefect in all_prefects if prefect.active]
            prefect_by_id = {prefect.id: prefect for prefect in all_prefects}

            assignments = (
                list(
                    session.scalars(
                        select(RosterAssignmentRecord)
                        .where(RosterAssignmentRecord.roster_week_id.in_(source_ids))
                        .order_by(RosterAssignmentRecord.roster_week_id, RosterAssignmentRecord.id)
                    ).all()
                )
                if source_ids
                else []
            )
            adjustments = (
                list(
                    session.scalars(
                        select(LeaveAdjustmentRecord)
                        .where(LeaveAdjustmentRecord.roster_week_id.in_(source_ids))
                        .order_by(LeaveAdjustmentRecord.created_at, LeaveAdjustmentRecord.id)
                    ).all()
                )
                if source_ids
                else []
            )

            contribution_values: dict[str, dict[str, object]] = defaultdict(
                lambda: {
                    "duty_count": 0,
                    "workload_points": 0.0,
                    "scheduled_minutes": 0,
                    "assist_count": 0,
                    "name_zh": "",
                    "role_code": "",
                    "allocations": [],
                }
            )
            active_assignments = []
            for assignment in assignments:
                if assignment.status != "active" or assignment.prefect_id is None:
                    continue
                active_assignments.append(assignment)
                values = contribution_values[assignment.prefect_id]
                values["name_zh"] = assignment.prefect_name_snapshot
                values["role_code"] = assignment.prefect_role_snapshot or ""
                values["duty_count"] = int(values["duty_count"]) + 1
                values["workload_points"] = round(float(values["workload_points"]) + assignment.weight, 4)
                values["scheduled_minutes"] = int(values["scheduled_minutes"]) + _duty_minutes(assignment.post_code)
                if assignment.post_code == DutyPost.ASSIST_IN_CHARGE.name:
                    values["assist_count"] = int(values["assist_count"]) + 1
                source_week = week_by_id[assignment.roster_week_id]
                start_time, end_time = DUTY_TIME_WINDOWS[DutyPost[assignment.post_code]]
                allocation_rows = values["allocations"]
                assert isinstance(allocation_rows, list)
                allocation_rows.append(
                    DutyAllocationEntry(
                        roster_week_id=source_week.id,
                        roster_version=source_week.version,
                        policy_version=source_week.policy_version,
                        assignment_id=assignment.id,
                        duty_date=source_week.week_start + timedelta(days=int(SchoolDay[assignment.day])),
                        day=assignment.day,
                        post_code=assignment.post_code,
                        start_time=start_time,
                        end_time=end_time,
                        scheduled_minutes=_duty_minutes(assignment.post_code),
                    )
                )

            report_prefects = [
                prefect
                for prefect in all_prefects
                if prefect.active or prefect.id in contribution_values
            ]
            contributions: list[PrefectPeriodContribution] = []
            for prefect in report_prefects:
                values = contribution_values[prefect.id]
                status_codes: list[str] = []
                if prefect.history_weight == 0 and prefect.history_duties == 0:
                    status_codes.append("new_prefect")
                if prefect.needs_mentoring:
                    status_codes.append("needs_mentoring")
                if prefect.role_code == PrefectRole.ASSISTANT_HEAD.value:
                    status_codes.append("assistant_head")
                allocation_rows = values["allocations"]
                assert isinstance(allocation_rows, list)
                contributions.append(
                    PrefectPeriodContribution(
                        prefect_id=prefect.id,
                        name_zh=str(values["name_zh"] or prefect.name_zh),
                        role_code=str(values["role_code"] or prefect.role_code),
                        duty_count=int(values["duty_count"]),
                        workload_points=round(float(values["workload_points"]), 4),
                        scheduled_minutes=int(values["scheduled_minutes"]),
                        assist_in_charge_count=int(values["assist_count"]),
                        current_history_weight=round(prefect.history_weight, 4),
                        current_history_duties=prefect.history_duties,
                        status_codes=tuple(status_codes),
                        allocations=tuple(sorted(allocation_rows, key=lambda row: (row.duty_date, row.assignment_id))),
                    )
                )
            contributions.sort(key=lambda row: (-row.duty_count, -row.workload_points, row.name_zh))

            trend = self._fairness_trend(
                session,
                prefects=all_prefects,
                period_start=period_start,
                period_end=period_end,
            )
            if trend:
                fairness_minimum = trend[-1].minimum
                fairness_median = trend[-1].median
                fairness_maximum = trend[-1].maximum
                fairness_spread = trend[-1].spread
                fairness_stddev = trend[-1].population_stddev
            else:
                (
                    fairness_minimum,
                    fairness_median,
                    fairness_maximum,
                    fairness_spread,
                    fairness_stddev,
                ) = _distribution([prefect.history_weight for prefect in active_prefects])

            reconciliation = self._fairness_reconciliation(session)
            recorded_slots = len(assignments)
            active_count = len(active_assignments)
            assist_required = sum(
                1 for assignment in assignments if assignment.post_code == DutyPost.ASSIST_IN_CHARGE.name
            )
            assist_filled = sum(
                1
                for assignment in active_assignments
                if assignment.post_code == DutyPost.ASSIST_IN_CHARGE.name
            )
            note_codes = ["service_is_not_performance"]
            note_codes.append("ledger_reconciled" if reconciliation.balanced else "ledger_review_required")
            if not weeks:
                note_codes.append("no_published_rosters")
            elif recorded_slots != active_count:
                note_codes.append("vacancies_require_review")
            else:
                note_codes.append("all_required_posts_covered")
            note_codes.append("scheduled_times_use_current_policy")

            resolved_start = weeks[0].week_start if weeks else period_start
            resolved_end = weeks[-1].week_start if weeks else period_end
            return PeriodSummaryReport(
                schema_version="1.0",
                generated_at=self._now(),
                period_start=resolved_start,
                period_end=resolved_end,
                sources=tuple(
                    ReportRosterSource(
                        week.id,
                        week.week_start,
                        week.version,
                        week.policy_version,
                        week.history_priority_multiplier,
                    )
                    for week in weeks
                ),
                active_prefect_count=len(active_prefects),
                published_week_count=len(weeks),
                recorded_slot_count=recorded_slots,
                active_assignment_count=active_count,
                vacant_slot_count=recorded_slots - active_count,
                coverage_rate=round(active_count / recorded_slots * 100, 2) if recorded_slots else None,
                workload_points=round(sum(assignment.weight for assignment in active_assignments), 4),
                scheduled_minutes=sum(_duty_minutes(assignment.post_code) for assignment in active_assignments),
                leave_adjustment_count=len(adjustments),
                replacement_count=sum(1 for adjustment in adjustments if adjustment.status == "replaced"),
                assist_required_count=assist_required,
                assist_filled_count=assist_filled,
                fairness_minimum=fairness_minimum,
                fairness_median=fairness_median,
                fairness_maximum=fairness_maximum,
                fairness_spread=fairness_spread,
                fairness_population_stddev=fairness_stddev,
                fairness_ledger_balanced=reconciliation.balanced,
                contributions=tuple(contributions),
                trend=trend,
                note_codes=tuple(note_codes),
            )

    def _fairness_trend(
        self,
        session: Session,
        *,
        prefects: list[PrefectRecord],
        period_start: date | None,
        period_end: date | None,
    ) -> tuple[FairnessTrendPoint, ...]:
        if not prefects:
            return ()
        statement = select(RosterWeekRecord).where(RosterWeekRecord.status == "published")
        if period_end is not None:
            statement = statement.where(RosterWeekRecord.week_start <= period_end)
        all_weeks = list(session.scalars(statement.order_by(RosterWeekRecord.week_start, RosterWeekRecord.id)).all())
        if not all_weeks:
            return ()
        week_ids = [week.id for week in all_weeks]
        ledger_rows = list(
            session.scalars(
                select(FairnessLedgerRecord)
                .where(FairnessLedgerRecord.roster_week_id.in_(week_ids))
                .order_by(FairnessLedgerRecord.created_at, FairnessLedgerRecord.id)
            ).all()
        )
        deltas_by_week: dict[int, list[FairnessLedgerRecord]] = defaultdict(list)
        for row in ledger_rows:
            deltas_by_week[row.roster_week_id].append(row)
        prefect_by_id = {prefect.id: prefect for prefect in prefects}
        totals = {prefect.id: prefect.history_weight_anchor for prefect in prefects}
        points: list[FairnessTrendPoint] = []
        for week in all_weeks:
            for row in deltas_by_week.get(week.id, []):
                if row.prefect_id in totals:
                    totals[row.prefect_id] = round(totals[row.prefect_id] + row.delta, 4)
            if period_start is not None and week.week_start < period_start:
                continue
            published_at = week.published_at or week.updated_at
            cohort_values = [
                totals[prefect_id]
                for prefect_id, prefect in prefect_by_id.items()
                if prefect.created_at <= published_at
                and (prefect.active or prefect.updated_at > published_at)
            ]
            minimum, midpoint, maximum, spread, stddev = _distribution(cohort_values)
            points.append(
                FairnessTrendPoint(
                    roster_week_id=week.id,
                    week_start=week.week_start,
                    version=week.version,
                    minimum=minimum,
                    median=midpoint,
                    maximum=maximum,
                    spread=spread,
                    population_stddev=stddev,
                )
            )
        return tuple(points)


__all__ = ["ReportingWorkflowMixin"]
