"""Focused RosterWorkflow behavior extracted without changing its public API."""

from __future__ import annotations

from nicegui_app.services.workflow_dependencies import (
    Assignment,
    AuditEventRecord,
    BackupObligationRecord,
    DutyPost,
    FairnessDiscrepancy,
    FairnessLedgerRecord,
    FairnessReconciliationReport,
    Iterable,
    LeaveDeclarationRecord,
    MaintenanceModeError,
    OperationCommandRecord,
    Path,
    Prefect,
    PrefectAvailabilityRecord,
    PrefectInput,
    PrefectRecord,
    PrefectRole,
    ROLE_CODES,
    RosterAssignmentRecord,
    RosterDayClosureRecord,
    RosterWeekRecord,
    SchoolDay,
    Session,
    WorkflowConflictError,
    WorkflowError,
    WorkflowMaintenanceError,
    can_assign_role,
    contextmanager,
    current_operation_actor,
    date,
    datetime,
    defaultdict,
    delete,
    duty_weight,
    func,
    hashlib,
    is_chinese_display_name,
    json,
    parse_prefect_role,
    select,
    timezone,
    uuid4,
    validate_assignments,
)


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

    def _operation_command_id(self, operation_type: str, command_id: str | None) -> str:
        actor = current_operation_actor()
        candidate = command_id or (actor.command_id if actor else None) or f"{operation_type}:{uuid4().hex}"
        normalized = candidate.strip()
        if not normalized or len(normalized) > 64:
            raise WorkflowError("Operation command ID is invalid.")
        return normalized

    @staticmethod
    def _operation_fingerprint(operation_type: str, payload: dict[str, object]) -> str:
        encoded = json.dumps(
            {"operationType": operation_type, "payload": payload},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _claim_operation_command(
        self,
        session: Session,
        *,
        operation_type: str,
        command_id: str,
        payload: dict[str, object],
    ) -> tuple[OperationCommandRecord, dict[str, object] | None]:
        fingerprint = self._operation_fingerprint(operation_type, payload)
        existing = session.get(OperationCommandRecord, command_id)
        if existing is not None:
            if (
                existing.operation_type != operation_type
                or existing.request_fingerprint != fingerprint
            ):
                raise WorkflowConflictError(
                    "This command ID was already used for different work. Start the action again."
                )
            if existing.status != "committed":
                raise WorkflowConflictError(
                    "This command is still being recovered. Refresh after the system is ready."
                )
            try:
                result = json.loads(existing.result_json)
            except json.JSONDecodeError as error:
                raise WorkflowError("The saved operation receipt is invalid.") from error
            if not isinstance(result, dict):
                raise WorkflowError("The saved operation receipt is invalid.")
            return existing, result

        now = self._now()
        record = OperationCommandRecord(
            command_id=command_id,
            operation_type=operation_type,
            request_fingerprint=fingerprint,
            status="pending",
            result_json="{}",
            created_at=now,
            completed_at=None,
        )
        session.add(record)
        session.flush()
        return record, None

    def _commit_operation_command(
        self,
        session: Session,
        *,
        record: OperationCommandRecord,
        result: dict[str, object],
        roster_week_id: int | None,
    ) -> None:
        now = self._now()
        record.status = "committed"
        record.result_json = json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        record.completed_at = now
        session.add(
            BackupObligationRecord(
                command_id=record.command_id,
                operation_type=record.operation_type,
                roster_week_id=roster_week_id,
                status="pending",
                backup_path=None,
                error=None,
                created_at=now,
                completed_at=None,
            )
        )

    def _fulfill_backup_obligation(self, command_id: str) -> Path:
        """Create or replay the verified snapshot owed by one committed command."""

        with self.maintenance.serialized_operation():
            with self._session() as session:
                obligation = session.scalar(
                    select(BackupObligationRecord).where(
                        BackupObligationRecord.command_id == command_id
                    )
                )
                if obligation is None:
                    raise WorkflowError("The operation backup obligation was not found.")
                if obligation.status == "completed" and obligation.backup_path:
                    path = Path(obligation.backup_path)
                    if path.is_file() and self.verify_backup(path).get("valid"):
                        return path
                operation_type = obligation.operation_type
                roster_week_id = obligation.roster_week_id

            backup = self._create_and_record_backup(operation_type, roster_week_id)
            if backup.success and backup.path is not None:
                self._complete_backup_obligations_with_snapshot(
                    backup.path,
                    command_ids=(command_id,),
                )
                return backup.path
            with self._session() as session:
                self._begin_serialized_write(session)
                obligation = session.scalar(
                    select(BackupObligationRecord).where(
                        BackupObligationRecord.command_id == command_id
                    )
                )
                if obligation is None:
                    raise WorkflowError("The operation backup obligation was not found.")
                obligation.status = "failed"
                obligation.backup_path = str(backup.path) if backup.path else None
                obligation.error = backup.error_message
                obligation.completed_at = None
                session.commit()
            return self._require_backup(backup, committed_event=operation_type)

    def _complete_backup_obligations_with_snapshot(
        self,
        backup_path: Path,
        *,
        command_ids: tuple[str, ...] | None = None,
    ) -> int:
        """Settle live obligations covered by one already-verified recovery point."""

        with self._session() as session:
            self._begin_serialized_write(session)
            statement = select(BackupObligationRecord).where(
                BackupObligationRecord.status != "completed"
            )
            if command_ids is not None:
                statement = statement.where(BackupObligationRecord.command_id.in_(command_ids))
            obligations = list(session.scalars(statement.order_by(BackupObligationRecord.id)).all())
            completed_at = self._now()
            for obligation in obligations:
                obligation.status = "completed"
                obligation.backup_path = str(backup_path)
                obligation.error = None
                obligation.completed_at = completed_at
            session.commit()
        return len(obligations)

    def pending_backup_obligation_count(self) -> int:
        with self._session() as session:
            return int(
                session.scalar(
                    select(func.count())
                    .select_from(BackupObligationRecord)
                    .where(BackupObligationRecord.status != "completed")
                )
                or 0
            )

    def repair_pending_backup_obligations(self) -> int:
        """Attempt every pending repair, then fail closed if any repair failed."""

        with self._session() as session:
            command_ids = list(
                session.scalars(
                    select(BackupObligationRecord.command_id)
                    .where(BackupObligationRecord.status != "completed")
                    .order_by(BackupObligationRecord.id)
                ).all()
            )
        repaired = 0
        first_error: Exception | None = None
        for command_id in command_ids:
            try:
                self._fulfill_backup_obligation(str(command_id))
            except Exception as error:
                if first_error is None:
                    first_error = error
            else:
                repaired += 1
        if first_error is not None:
            raise first_error
        return repaired

    def _assert_name_available(self, session: Session, name_zh: str, *, exclude_prefect_id: str | None = None) -> None:
        statement = select(PrefectRecord).where(
            PrefectRecord.name_zh == name_zh.strip(),
            PrefectRecord.active.is_(True),
        )
        existing = session.scalar(statement)
        if existing is not None and existing.id != exclude_prefect_id:
            raise WorkflowError("A prefect with this Chinese name already exists.")

    def _prefect_output(self, session: Session, record: PrefectRecord) -> dict[str, object]:
        days = session.scalars(
            select(PrefectAvailabilityRecord.day).where(PrefectAvailabilityRecord.prefect_id == record.id)
        ).all()
        return self._prefect_output_from_days(record, days)

    @staticmethod
    def _prefect_output_from_days(
        record: PrefectRecord,
        days: Iterable[str],
    ) -> dict[str, object]:
        """Render an already-loaded prefect without issuing another query."""
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
        if (
            prefect_input.role_code == PrefectRole.ASSISTANT_HEAD.value
            and prefect_input.fixed_general_duty != "NONE"
            and prefect_input.fixed_general_duty not in prefect_input.available_days
        ):
            raise WorkflowError("Fixed duty must also be an available weekday.")
        if prefect_input.history_weight < 0 or prefect_input.history_duties < 0:
            raise WorkflowError("History values cannot be negative.")

    @staticmethod
    def _assert_assist_fixed_day_available(
        session: Session,
        prefect_input: PrefectInput,
        *,
        exclude_prefect_id: str | None = None,
    ) -> None:
        """Reject two active Assistant Heads owning the same legacy weekday.

        Callers hold the workflow's serialized SQLite write transaction before
        reaching this query, so the validation and the following insert/update
        form one atomic decision rather than a check-then-write race.
        """

        if (
            prefect_input.role_code != PrefectRole.ASSISTANT_HEAD.value
            or prefect_input.fixed_general_duty == "NONE"
        ):
            return
        statement = select(PrefectRecord.id).where(
            PrefectRecord.active.is_(True),
            PrefectRecord.role_code == PrefectRole.ASSISTANT_HEAD.value,
            PrefectRecord.fixed_general_duty == prefect_input.fixed_general_duty,
        )
        if exclude_prefect_id is not None:
            statement = statement.where(PrefectRecord.id != exclude_prefect_id)
        if session.scalar(statement.limit(1)) is not None:
            raise WorkflowConflictError(
                "Another active Assistant Head Study Prefect already owns this fixed weekday."
            )

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
        rows = session.execute(
            select(PrefectAvailabilityRecord.prefect_id, PrefectAvailabilityRecord.day)
            .join(PrefectRecord, PrefectRecord.id == PrefectAvailabilityRecord.prefect_id)
            .where(PrefectRecord.active.is_(True))
        ).all()
        for prefect_id, day in rows:
            availability[prefect_id].add(SchoolDay[day])
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

    def _required_legacy_assist_owners(
        self,
        session: Session,
        *,
        week_start: date,
    ) -> dict[str, str]:
        """Return fixed Assist owners who are genuinely eligible this week.

        Legacy ownership is a long-term preference, not an instruction to
        schedule someone through an availability conflict or registered leave.
        The generator uses the same distinction: it locks an available fixed
        owner and uses a temporary substitute only for an unavailable owner.
        """

        availability = self._availability_by_prefect(session)
        leave_days = self._leave_days_for_week(session, week_start)
        owners: dict[str, str] = {}
        for record in self._active_prefect_records(session):
            day_code = str(record.fixed_general_duty or "NONE")
            if (
                record.role_code != PrefectRole.ASSISTANT_HEAD.value
                or day_code not in SchoolDay.__members__
            ):
                continue
            day = SchoolDay[day_code]
            if day not in availability.get(record.id, set()):
                continue
            if day in leave_days.get(record.id, set()):
                continue
            owners[day_code] = record.id
        return owners

    @staticmethod
    def _leave_declaration_output(declaration: LeaveDeclarationRecord, prefect: PrefectRecord) -> dict[str, object]:
        return {
            "id": declaration.id,
            "weekStart": declaration.week_start,
            "prefectId": declaration.prefect_id,
            "prefectName": prefect.name_zh,
            "day": declaration.day,
            "reason": declaration.reason,
            "version": declaration.version,
            "createdAt": declaration.created_at,
            "updatedAt": declaration.updated_at,
        }

    def _validate_persisted_assignments(
        self,
        session: Session,
        rows: list[RosterAssignmentRecord],
        *,
        week_start: date,
        closed_days: Iterable[SchoolDay] = (),
        require_complete: bool = True,
    ) -> None:
        prefects = self._active_prefects(session)
        domain_rows: list[Assignment] = []
        for row in rows:
            if (row.prefect_id is None or row.status != "active") and require_complete:
                raise WorkflowError("A draft with missing assignments cannot be published.")
            if row.prefect_id is None or row.status != "active":
                continue
            domain_rows.append(
                Assignment(
                    day=SchoolDay[row.day],
                    post=DutyPost[row.post_code],
                    prefect_id=row.prefect_id,
                    prefect_name=row.prefect_name_snapshot,
                    weight=row.weight,
                )
            )
        validate_assignments(
            domain_rows,
            prefects,
            leave_days=self._leave_days_for_week(session, week_start),
            closed_days=closed_days,
            require_complete=require_complete,
        )

    @staticmethod
    def _closed_days(
        session: Session,
        roster_week_id: int,
    ) -> tuple[SchoolDay, ...]:
        codes = session.scalars(
            select(RosterDayClosureRecord.day)
            .where(RosterDayClosureRecord.roster_week_id == roster_week_id)
            .order_by(RosterDayClosureRecord.day)
        ).all()
        return tuple(sorted((SchoolDay[code] for code in codes), key=int))

    @staticmethod
    def _closed_days_by_week(
        session: Session,
        roster_week_ids: Iterable[int],
    ) -> dict[int, tuple[SchoolDay, ...]]:
        week_ids = tuple(dict.fromkeys(int(value) for value in roster_week_ids))
        if not week_ids:
            return {}
        rows = session.execute(
            select(
                RosterDayClosureRecord.roster_week_id,
                RosterDayClosureRecord.day,
            ).where(RosterDayClosureRecord.roster_week_id.in_(week_ids))
        ).all()
        grouped: dict[int, list[SchoolDay]] = defaultdict(list)
        for roster_week_id, day_code in rows:
            grouped[int(roster_week_id)].append(SchoolDay[str(day_code)])
        return {
            week_id: tuple(sorted(grouped.get(week_id, []), key=int))
            for week_id in week_ids
        }

    @staticmethod
    def _closure_outputs(
        session: Session,
        roster_week_id: int,
    ) -> list[dict[str, object]]:
        rows = session.scalars(
            select(RosterDayClosureRecord)
            .where(RosterDayClosureRecord.roster_week_id == roster_week_id)
            .order_by(RosterDayClosureRecord.day)
        ).all()
        return [
            {
                "day": row.day,
                "reasonCode": row.reason_code,
                "note": row.note,
            }
            for row in sorted(rows, key=lambda item: int(SchoolDay[item.day]))
        ]

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
        *,
        include_same_day_assigned: bool = False,
    ) -> list[dict[str, object]]:
        if assignment.status != "active" or assignment.prefect_id is None:
            raise WorkflowError("Only an active assignment can be changed manually.")
        day = SchoolDay[assignment.day]
        post = DutyPost[assignment.post_code]
        assigned_rows = self._assignment_rows(session, week.id)
        assigned_today = {
            str(row.prefect_id): row
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
            if prefect.id in assigned_today and not include_same_day_assigned:
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
        outputs: list[dict[str, object]] = []
        for candidate in candidates:
            output: dict[str, object] = {
                "id": candidate.id,
                "nameZh": candidate.name_zh,
                "form": candidate.form,
                "className": candidate.class_name,
                "historyWeight": candidate.history_weight,
            }
            occupied = assigned_today.get(candidate.id)
            if include_same_day_assigned:
                output["requiresSwap"] = occupied is not None
                output["occupiedCellKey"] = (
                    f"{occupied.day}:{occupied.post_code}:{occupied.slot_index}"
                    if occupied is not None
                    else None
                )
            outputs.append(output)
        return outputs

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
        actor = current_operation_actor()
        session.add(
            AuditEventRecord(
                event_type=event_type,
                roster_week_id=roster_week_id,
                metadata_json=json.dumps(metadata, ensure_ascii=False, sort_keys=True),
                actor_subject=actor.subject if actor else None,
                actor_mode=actor.mode if actor else None,
                command_id=actor.command_id if actor else None,
                request_reference=actor.request_reference if actor and actor.request_reference else None,
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
        rows = session.execute(
            select(
                PrefectRecord,
                func.coalesce(func.sum(FairnessLedgerRecord.delta), 0.0),
                func.coalesce(func.sum(FairnessLedgerRecord.duty_delta), 0),
            )
            .outerjoin(
                FairnessLedgerRecord,
                FairnessLedgerRecord.prefect_id == PrefectRecord.id,
            )
            .group_by(PrefectRecord.id)
            .order_by(PrefectRecord.id)
        ).all()
        discrepancies: list[FairnessDiscrepancy] = []
        for record, ledger_weight, ledger_duties in rows:
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
        return FairnessReconciliationReport(len(rows), tuple(discrepancies))

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
