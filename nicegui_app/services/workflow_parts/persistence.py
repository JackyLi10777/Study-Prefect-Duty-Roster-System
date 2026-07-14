"""Focused RosterWorkflow behavior extracted without changing its public API."""

from __future__ import annotations

from nicegui_app.services.workflow_dependencies import *

class PersistenceWorkflowMixin:
    def _seed_prefects(self, session: Session) -> None:
        raw_data = json.loads(self.seed_path.read_text(encoding="utf-8"))
        now = self._now()
        for raw in raw_data["prefects"]:
            role = parse_prefect_role(raw.get("roleCode", raw.get("role")))
            history_weight = float(raw.get("historyWeight", 0))
            history_duties = int(raw.get("historyDuties", 0))
            record = PrefectRecord(
                id=raw["id"],
                name_zh=raw["name"],
                form=raw["form"],
                class_name=raw["class"],
                role_code=role.value,
                history_weight=history_weight,
                history_duties=history_duties,
                history_weight_anchor=history_weight,
                history_duties_anchor=history_duties,
                needs_mentoring=bool(raw.get("needsMentoring", False)),
                fixed_general_duty=raw.get("fixedGeneralDuty", "NONE"),
                remarks=raw.get("remarks", ""),
                active=True,
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            session.flush()
            for day in raw.get("availableDays", []):
                session.add(PrefectAvailabilityRecord(prefect_id=record.id, day=day))

    def _new_prefect_record(self, prefect_input: PrefectInput) -> PrefectRecord:
        now = self._now()
        return PrefectRecord(
            id=f"prefect-{uuid4().hex[:12]}",
            name_zh=prefect_input.name_zh.strip(),
            name_en=prefect_input.name_en.strip() if prefect_input.name_en else None,
            form=prefect_input.form,
            class_name=prefect_input.class_name.strip(),
            role_code=prefect_input.role_code,
            history_weight=prefect_input.history_weight,
            history_duties=prefect_input.history_duties,
            history_weight_anchor=prefect_input.history_weight,
            history_duties_anchor=prefect_input.history_duties,
            needs_mentoring=prefect_input.needs_mentoring,
            fixed_general_duty=prefect_input.fixed_general_duty,
            remarks=prefect_input.remarks.strip(),
            version=1,
            active=True,
            created_at=now,
            updated_at=now,
        )

    def _replace_availability(self, session: Session, prefect_id: str, available_days: Iterable[str]) -> None:
        session.execute(delete(PrefectAvailabilityRecord).where(PrefectAvailabilityRecord.prefect_id == prefect_id))
        session.flush()
        for day in available_days:
            session.add(PrefectAvailabilityRecord(prefect_id=prefect_id, day=day))
        session.flush()

    @staticmethod
    def _begin_serialized_write(session: Session) -> None:
        """Reserve SQLite's writer slot before reading compare-and-set state."""
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")

    def _assert_name_available(self, session: Session, name_zh: str, *, exclude_prefect_id: str | None = None) -> None:
        statement = select(PrefectRecord).where(PrefectRecord.name_zh == name_zh.strip())
        existing = session.scalar(statement)
        if existing is not None and existing.id != exclude_prefect_id:
            raise WorkflowError("A prefect with this Chinese name already exists.")

    def _prefect_output(self, session: Session, record: PrefectRecord) -> dict[str, object]:
        days = session.scalars(
            select(PrefectAvailabilityRecord.day).where(PrefectAvailabilityRecord.prefect_id == record.id)
        ).all()
        return {
            "id": record.id,
            "nameZh": record.name_zh,
            "nameEn": record.name_en,
            "form": record.form,
            "className": record.class_name,
            "roleCode": record.role_code,
            "historyWeight": record.history_weight,
            "historyDuties": record.history_duties,
            "availableDays": sorted(days, key=lambda day: int(SchoolDay[day])),
            "needsMentoring": record.needs_mentoring,
            "fixedGeneralDuty": record.fixed_general_duty,
            "remarks": record.remarks,
            "version": record.version,
            "active": record.active,
        }

    @staticmethod
    def _validate_prefect_input(prefect_input: PrefectInput) -> None:
        if not prefect_input.name_zh.strip():
            raise WorkflowError("Chinese name is required.")
        if not is_chinese_display_name(prefect_input.name_zh):
            raise WorkflowError("The authoritative prefect display name must be Chinese.")
        if prefect_input.form not in {"F.3", "F.4", "F.5", "F.6"}:
            raise WorkflowError("Form must be F.3, F.4, F.5, or F.6.")
        if not prefect_input.class_name.strip():
            raise WorkflowError("Class is required.")
        if prefect_input.role_code not in ROLE_CODES:
            raise WorkflowError("Role is not recognized.")
        if not prefect_input.available_days:
            raise WorkflowError("At least one available day is required.")
        if any(day not in SchoolDay.__members__ for day in prefect_input.available_days):
            raise WorkflowError("Availability contains an invalid weekday.")
        if len(set(prefect_input.available_days)) != len(prefect_input.available_days):
            raise WorkflowError("Availability contains duplicate weekdays.")
        if prefect_input.fixed_general_duty != "NONE" and prefect_input.fixed_general_duty not in SchoolDay.__members__:
            raise WorkflowError("Fixed duty contains an invalid weekday.")
        if prefect_input.history_weight < 0 or prefect_input.history_duties < 0:
            raise WorkflowError("History values cannot be negative.")

    def _store_assignments(self, session: Session, roster_week_id: int, assignments: Iterable[Assignment], prefects: list[Prefect]) -> None:
        role_by_id = {prefect.id: prefect.role for prefect in prefects}
        slot_counts: dict[tuple[str, str], int] = defaultdict(int)
        for assignment in assignments:
            key = (assignment.day.name, assignment.post.name)
            slot_counts[key] += 1
            session.add(
                RosterAssignmentRecord(
                    roster_week_id=roster_week_id,
                    day=assignment.day.name,
                    post_code=assignment.post.name,
                    slot_index=slot_counts[key],
                    prefect_id=assignment.prefect_id,
                    prefect_name_snapshot=assignment.prefect_name,
                    prefect_role_snapshot=role_by_id[assignment.prefect_id].value,
                    weight=assignment.weight,
                    status="active",
                )
            )

    def _active_prefects(self, session: Session) -> list[Prefect]:
        availability = self._availability_by_prefect(session)
        return [
            Prefect(
                id=record.id,
                name=record.name_zh,
                form=record.form,
                class_name=record.class_name,
                role=PrefectRole(record.role_code),
                available_days=frozenset(availability.get(record.id, set())),
                history_weight=record.history_weight,
                history_duties=record.history_duties,
                needs_mentoring=record.needs_mentoring,
                fixed_general_duty=record.fixed_general_duty,
                remarks=record.remarks,
            )
            for record in self._active_prefect_records(session)
        ]

    def _active_prefect_records(self, session: Session) -> list[PrefectRecord]:
        return session.scalars(select(PrefectRecord).where(PrefectRecord.active.is_(True))).all()

    def _availability_by_prefect(self, session: Session) -> dict[str, set[SchoolDay]]:
        availability: dict[str, set[SchoolDay]] = defaultdict(set)
        for record in session.scalars(select(PrefectAvailabilityRecord)).all():
            availability[record.prefect_id].add(SchoolDay[record.day])
        return availability

    def _leave_days_for_week(self, session: Session, week_start: date) -> dict[str, set[SchoolDay]]:
        leave_days: dict[str, set[SchoolDay]] = defaultdict(set)
        rows = session.scalars(
            select(LeaveDeclarationRecord).where(
                LeaveDeclarationRecord.week_start == week_start,
                LeaveDeclarationRecord.active.is_(True),
            )
        ).all()
        for row in rows:
            leave_days[row.prefect_id].add(SchoolDay[row.day])
        return leave_days

    @staticmethod
    def _leave_declaration_output(declaration: LeaveDeclarationRecord, prefect: PrefectRecord) -> dict[str, object]:
        return {
            "id": declaration.id,
            "weekStart": declaration.week_start,
            "prefectId": declaration.prefect_id,
            "prefectName": prefect.name_zh,
            "day": declaration.day,
            "reason": declaration.reason,
            "createdAt": declaration.created_at,
            "updatedAt": declaration.updated_at,
        }

    def _validate_persisted_assignments(
        self,
        session: Session,
        rows: list[RosterAssignmentRecord],
        *,
        week_start: date,
    ) -> None:
        prefects = self._active_prefects(session)
        domain_rows: list[Assignment] = []
        for row in rows:
            if row.prefect_id is None or row.status != "active":
                raise WorkflowError("A draft with missing assignments cannot be published.")
            domain_rows.append(
                Assignment(
                    day=SchoolDay[row.day],
                    post=DutyPost[row.post_code],
                    prefect_id=row.prefect_id,
                    prefect_name=row.prefect_name_snapshot,
                    weight=row.weight,
                )
            )
        validate_assignments(domain_rows, prefects, leave_days=self._leave_days_for_week(session, week_start))

    def _assignment_rows(self, session: Session, roster_week_id: int) -> list[RosterAssignmentRecord]:
        rows = session.scalars(
            select(RosterAssignmentRecord)
            .where(RosterAssignmentRecord.roster_week_id == roster_week_id)
        ).all()
        post_rank = {
            "ASSIST_IN_CHARGE": 0,
            "ROOM_302": 1,
            "ROOM_303": 2,
            "ROOM_202": 3,
        }
        return sorted(
            rows,
            key=lambda row: (int(SchoolDay[row.day]), post_rank[row.post_code], row.slot_index),
        )

    def _eligible_assignment_candidates(
        self,
        session: Session,
        week: RosterWeekRecord,
        assignment: RosterAssignmentRecord,
    ) -> list[dict[str, object]]:
        if assignment.status != "active" or assignment.prefect_id is None:
            raise WorkflowError("Only an active assignment can be changed manually.")
        day = SchoolDay[assignment.day]
        post = DutyPost[assignment.post_code]
        assigned_rows = self._assignment_rows(session, week.id)
        assigned_today = {
            row.prefect_id
            for row in assigned_rows
            if row.id != assignment.id and row.status == "active" and row.day == assignment.day and row.prefect_id
        }
        other_days: dict[str, set[SchoolDay]] = defaultdict(set)
        for row in assigned_rows:
            if row.id != assignment.id and row.status == "active" and row.prefect_id:
                other_days[row.prefect_id].add(SchoolDay[row.day])
        availability = self._availability_by_prefect(session)
        leave_days = self._leave_days_for_week(session, week.week_start)
        candidates = []
        for prefect in self._active_prefect_records(session):
            if prefect.id == assignment.prefect_id:
                continue
            if prefect.id in assigned_today:
                continue
            if day not in availability.get(prefect.id, set()):
                continue
            if day in leave_days.get(prefect.id, set()):
                continue
            if not can_assign_role(PrefectRole(prefect.role_code), post):
                continue
            if any(abs(int(existing_day) - int(day)) == 1 for existing_day in other_days[prefect.id]):
                continue
            candidates.append(prefect)
        candidates.sort(key=lambda candidate: (candidate.history_weight, self._form_rank(candidate.form), candidate.history_duties, candidate.name_zh))
        return [
            {
                "id": candidate.id,
                "nameZh": candidate.name_zh,
                "form": candidate.form,
                "className": candidate.class_name,
                "historyWeight": candidate.history_weight,
            }
            for candidate in candidates
        ]

    def _week_or_error(self, session: Session, roster_week_id: int) -> RosterWeekRecord:
        week = session.get(RosterWeekRecord, roster_week_id)
        if week is None:
            raise WorkflowError("Roster week was not found.")
        return week

    def _assignment_or_error(self, session: Session, roster_week_id: int, assignment_id: int) -> RosterAssignmentRecord:
        assignment = session.get(RosterAssignmentRecord, assignment_id)
        if assignment is None or assignment.roster_week_id != roster_week_id:
            raise WorkflowError("Roster assignment was not found.")
        return assignment

    def _audit(self, session: Session, event_type: str, roster_week_id: int | None, metadata: dict[str, object]) -> None:
        session.add(
            AuditEventRecord(
                event_type=event_type,
                roster_week_id=roster_week_id,
                metadata_json=json.dumps(metadata, ensure_ascii=False, sort_keys=True),
                occurred_at=self._now(),
            )
        )

    @contextmanager
    def _session(self):
        if self.sessions is None:
            raise RuntimeError("Call bootstrap() before using the roster workflow.")
        try:
            with self.maintenance.operation():
                with self.sessions() as session:
                    yield session
        except MaintenanceModeError as error:
            raise WorkflowMaintenanceError(str(error)) from error

    def _dispose_database_connections(self) -> None:
        if self.sessions is None:
            return
        engine = self.sessions.kw.get("bind")
        if engine is not None:
            engine.dispose()

    def _fairness_reconciliation(self, session: Session) -> FairnessReconciliationReport:
        session.flush()
        records = session.scalars(select(PrefectRecord).order_by(PrefectRecord.id)).all()
        discrepancies: list[FairnessDiscrepancy] = []
        for record in records:
            ledger_weight, ledger_duties = session.execute(
                select(
                    func.coalesce(func.sum(FairnessLedgerRecord.delta), 0.0),
                    func.coalesce(func.sum(FairnessLedgerRecord.duty_delta), 0),
                ).where(FairnessLedgerRecord.prefect_id == record.id)
            ).one()
            expected_weight = round(record.history_weight_anchor + float(ledger_weight), 4)
            expected_duties = record.history_duties_anchor + int(ledger_duties)
            if abs(expected_weight - record.history_weight) > 0.0001 or expected_duties != record.history_duties:
                discrepancies.append(
                    FairnessDiscrepancy(
                        prefect_id=record.id,
                        expected_weight=expected_weight,
                        actual_weight=record.history_weight,
                        expected_duties=expected_duties,
                        actual_duties=record.history_duties,
                    )
                )
        return FairnessReconciliationReport(len(records), tuple(discrepancies))

    def _assert_fairness_reconciled(self, session: Session) -> None:
        if not self._fairness_reconciliation(session).balanced:
            raise WorkflowError("Fairness ledger reconciliation failed; the write was rolled back.")

    @staticmethod
    def _form_rank(form: str) -> int:
        return int(form.removeprefix("F."))

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _require_monday(week_start: date) -> None:
        if week_start.weekday() != 0:
            raise WorkflowError("A roster week must start on Monday.")
