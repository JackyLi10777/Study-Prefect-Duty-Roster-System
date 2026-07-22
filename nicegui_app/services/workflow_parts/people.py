"""Focused RosterWorkflow behavior extracted without changing its public API."""

from __future__ import annotations

from nicegui_app.services.workflow_dependencies import *
from nicegui_app.services.workflow_fencing import fenced_workflow_write

class PeopleWorkflowMixin:
    def prefect_loads(self) -> dict[str, float]:
        with self._session() as session:
            rows = self._active_prefect_records(session)
            return {row.id: row.history_weight for row in rows}

    def prefects(self) -> list[dict[str, object]]:
        with self._session() as session:
            availability = self._availability_by_prefect(session)
            return [
                {
                    "id": row.id,
                    "nameZh": row.name_zh,
                    "nameEn": row.name_en,
                    "form": row.form,
                    "className": row.class_name,
                    "roleCode": row.role_code,
                    "historyWeight": row.history_weight,
                    "historyDuties": row.history_duties,
                    "version": row.version,
                    "availableDays": [day.name for day in sorted(availability.get(row.id, set()))],
                    "needsMentoring": row.needs_mentoring,
                    "fixedGeneralDuty": row.fixed_general_duty,
                }
                for row in self._active_prefect_records(session)
            ]

    def prefect(self, prefect_id: str) -> dict[str, object]:
        with self._session() as session:
            record = session.get(PrefectRecord, prefect_id)
            if record is None:
                raise WorkflowError("Prefect was not found.")
            return self._prefect_output(session, record)

    @fenced_workflow_write
    def create_prefect(
        self,
        prefect_input: PrefectInput,
        *,
        command_id: str | None = None,
    ) -> dict[str, object]:
        self._validate_prefect_input(prefect_input)
        operation_type = "prefect_created"
        operation_id = self._operation_command_id(operation_type, command_id)
        operation_payload = {
            "nameZh": prefect_input.name_zh.strip(),
            "nameEn": prefect_input.name_en.strip() if prefect_input.name_en else None,
            "form": prefect_input.form,
            "className": prefect_input.class_name.strip(),
            "roleCode": prefect_input.role_code,
            "availableDays": list(prefect_input.available_days),
            "needsMentoring": prefect_input.needs_mentoring,
            "fixedGeneralDuty": prefect_input.fixed_general_duty,
            "remarks": prefect_input.remarks.strip(),
            "historyWeight": prefect_input.history_weight,
            "historyDuties": prefect_input.history_duties,
        }
        receipt: dict[str, object] | None = None
        with self._session() as session:
            self._begin_serialized_write(session)
            command, receipt = self._claim_operation_command(
                session,
                operation_type=operation_type,
                command_id=operation_id,
                payload=operation_payload,
            )
            if receipt is not None:
                session.rollback()
            else:
                self._assert_name_available(session, prefect_input.name_zh)
                self._assert_assist_fixed_day_available(session, prefect_input)
                record = self._new_prefect_record(prefect_input)
                session.add(record)
                session.flush()
                self._replace_availability(session, record.id, prefect_input.available_days)
                self._audit(session, operation_type, None, {"prefectId": record.id})
                receipt = self._prefect_output(session, record)
                self._commit_operation_command(
                    session,
                    record=command,
                    result=receipt,
                    roster_week_id=None,
                )
                session.commit()
        assert receipt is not None
        self._fulfill_backup_obligation(operation_id)
        return receipt

    @fenced_workflow_write
    def update_prefect(
        self,
        prefect_id: str,
        prefect_input: PrefectInput,
        *,
        expected_version: int | None = None,
        command_id: str | None = None,
    ) -> dict[str, object]:
        self._validate_prefect_input(prefect_input)
        operation_type = "prefect_updated"
        operation_id = self._operation_command_id(operation_type, command_id)
        operation_payload = {
            "prefectId": prefect_id,
            "expectedVersion": expected_version,
            "nameZh": prefect_input.name_zh.strip(),
            "nameEn": prefect_input.name_en.strip() if prefect_input.name_en else None,
            "form": prefect_input.form,
            "className": prefect_input.class_name.strip(),
            "roleCode": prefect_input.role_code,
            "availableDays": list(prefect_input.available_days),
            "needsMentoring": prefect_input.needs_mentoring,
            "fixedGeneralDuty": prefect_input.fixed_general_duty,
            "remarks": prefect_input.remarks.strip(),
        }
        receipt: dict[str, object] | None = None
        with self._session() as session:
            self._begin_serialized_write(session)
            command, receipt = self._claim_operation_command(
                session,
                operation_type=operation_type,
                command_id=operation_id,
                payload=operation_payload,
            )
            if receipt is not None:
                session.rollback()
            else:
                record = session.get(PrefectRecord, prefect_id)
                if record is None:
                    raise WorkflowError("Prefect was not found.")
                if not record.active:
                    raise WorkflowConflictError(
                        "This prefect record was archived in another browser. Refresh before making further changes."
                    )
                reviewed_version = record.version if expected_version is None else expected_version
                if record.version != reviewed_version:
                    raise WorkflowConflictError(
                        "This prefect record changed in another browser. Refresh and review the latest details before saving."
                    )
                self._assert_name_available(session, prefect_input.name_zh, exclude_prefect_id=prefect_id)
                self._assert_assist_fixed_day_available(
                    session,
                    prefect_input,
                    exclude_prefect_id=prefect_id,
                )
                claim = session.execute(
                    update(PrefectRecord)
                    .where(
                        PrefectRecord.id == prefect_id,
                        PrefectRecord.active.is_(True),
                        PrefectRecord.version == reviewed_version,
                    )
                    .values(
                        name_zh=prefect_input.name_zh.strip(),
                        name_en=prefect_input.name_en.strip() if prefect_input.name_en else None,
                        form=prefect_input.form,
                        class_name=prefect_input.class_name.strip(),
                        role_code=prefect_input.role_code,
                        needs_mentoring=prefect_input.needs_mentoring,
                        fixed_general_duty=prefect_input.fixed_general_duty,
                        remarks=prefect_input.remarks.strip(),
                        version=reviewed_version + 1,
                        updated_at=self._now(),
                    )
                )
                if claim.rowcount != 1:
                    raise WorkflowConflictError(
                        "This prefect record changed in another browser. Refresh and review the latest details before saving."
                    )
                self._replace_availability(session, record.id, prefect_input.available_days)
                session.refresh(record)
                self._audit(session, operation_type, None, {"prefectId": record.id, "version": record.version})
                receipt = self._prefect_output(session, record)
                self._commit_operation_command(
                    session,
                    record=command,
                    result=receipt,
                    roster_week_id=None,
                )
                session.commit()
        assert receipt is not None
        self._fulfill_backup_obligation(operation_id)
        return receipt

    @fenced_workflow_write
    def archive_prefect(
        self,
        prefect_id: str,
        *,
        expected_version: int | None = None,
        command_id: str | None = None,
    ) -> None:
        operation_type = "prefect_archived"
        operation_id = self._operation_command_id(operation_type, command_id)
        receipt: dict[str, object] | None = None
        with self._session() as session:
            self._begin_serialized_write(session)
            command, receipt = self._claim_operation_command(
                session,
                operation_type=operation_type,
                command_id=operation_id,
                payload={
                    "prefectId": prefect_id,
                    "expectedVersion": expected_version,
                },
            )
            if receipt is not None:
                session.rollback()
            else:
                record = session.get(PrefectRecord, prefect_id)
                if record is None:
                    raise WorkflowError("Prefect was not found.")
                if not record.active:
                    raise WorkflowError("Prefect is already archived.")
                reviewed_version = record.version if expected_version is None else expected_version
                if record.version != reviewed_version:
                    raise WorkflowConflictError(
                        "This prefect record changed in another browser. Refresh and review the latest details before archiving."
                    )
                claim = session.execute(
                    update(PrefectRecord)
                    .where(
                        PrefectRecord.id == prefect_id,
                        PrefectRecord.active.is_(True),
                        PrefectRecord.version == reviewed_version,
                    )
                    .values(active=False, version=reviewed_version + 1, updated_at=self._now())
                )
                if claim.rowcount != 1:
                    raise WorkflowConflictError(
                        "This prefect record changed in another browser. Refresh and review the latest details before archiving."
                    )
                session.refresh(record)
                receipt = {"prefectId": record.id, "version": record.version}
                self._audit(
                    session,
                    operation_type,
                    None,
                    receipt,
                )
                self._commit_operation_command(
                    session,
                    record=command,
                    result=receipt,
                    roster_week_id=None,
                )
                session.commit()
        self._fulfill_backup_obligation(operation_id)

    def prepare_new_school_year(self) -> dict[str, object]:
        """Archive the active directory while retaining every historical record.

        The rollover runs under the host-wide maintenance lock so the verified
        pre-change snapshot, directory archive, audit event, and verified
        post-change snapshot describe one controlled operation.
        """
        with self.maintenance.maintenance("school_year_rollover"):
            with self._session() as session:
                active_count = int(
                    session.scalar(
                        select(func.count()).select_from(PrefectRecord).where(PrefectRecord.active.is_(True))
                    )
                    or 0
                )
                if active_count == 0:
                    raise WorkflowError("The active prefect directory is already empty.")
                self._assert_fairness_reconciled(session)

            before_result = self._create_and_record_backup("pre_school_year_rollover", None)
            if not before_result.success or before_result.path is None:
                raise WorkflowError(
                    "The school-year rollover did not start because the pre-operation backup failed."
                )
            before_backup = before_result.path

            with self._session() as session:
                self._begin_serialized_write(session)
                now = self._now()
                cancelled_leave_count = int(
                    session.scalar(
                        select(func.count())
                        .select_from(LeaveDeclarationRecord)
                        .where(LeaveDeclarationRecord.active.is_(True))
                    )
                    or 0
                )
                archived = session.execute(
                    update(PrefectRecord)
                    .where(PrefectRecord.active.is_(True))
                    .values(
                        active=False,
                        version=PrefectRecord.version + 1,
                        updated_at=now,
                    )
                )
                session.execute(
                    update(LeaveDeclarationRecord)
                    .where(LeaveDeclarationRecord.active.is_(True))
                    .values(active=False, updated_at=now)
                )
                archived_count = int(archived.rowcount or 0)
                if archived_count != active_count:
                    raise WorkflowConflictError(
                        "The prefect directory changed while the school-year rollover was starting."
                    )
                self._audit(
                    session,
                    "school_year_directory_archived",
                    None,
                    {
                        "archivedPrefectCount": archived_count,
                        "cancelledLeaveCount": cancelled_leave_count,
                    },
                )
                session.commit()

            try:
                after_backup = self._require_backup(
                    self._create_and_record_backup("post_school_year_rollover", None),
                    committed_event="school_year_directory_archived",
                )
            except CommittedWriteBackupError:
                # The directory archive is already durable.  Keep the
                # host-wide marker so no later write can make the verified
                # pre-operation recovery point stale before review.
                self.maintenance.require_recovery_review(
                    reason_code="school_year_rollover_post_backup_failed"
                )
                raise
            return {
                "archivedPrefectCount": archived_count,
                "cancelledLeaveCount": cancelled_leave_count,
                "beforeBackup": before_backup,
                "afterBackup": after_backup,
            }

    @fenced_workflow_write
    def import_prefects(
        self,
        prefect_inputs: Iterable[PrefectInput],
        *,
        command_id: str | None = None,
    ) -> list[dict[str, object]]:
        inputs = list(prefect_inputs)
        if not inputs:
            raise WorkflowError("Import contains no prefects.")
        for prefect_input in inputs:
            self._validate_prefect_input(prefect_input)
        normalized_names = [prefect_input.name_zh.strip() for prefect_input in inputs]
        if len(normalized_names) != len(set(normalized_names)):
            raise WorkflowError("Import contains duplicate Chinese names.")
        fixed_assist_days = [
            prefect_input.fixed_general_duty
            for prefect_input in inputs
            if (
                prefect_input.role_code == PrefectRole.ASSISTANT_HEAD.value
                and prefect_input.fixed_general_duty != "NONE"
            )
        ]
        if len(fixed_assist_days) != len(set(fixed_assist_days)):
            raise WorkflowError(
                "Import contains duplicate Assistant Head fixed weekdays."
            )
        operation_type = "prefects_imported"
        operation_id = self._operation_command_id(operation_type, command_id)
        operation_payload = {
            "prefects": [
                {
                    "nameZh": item.name_zh.strip(),
                    "nameEn": item.name_en.strip() if item.name_en else None,
                    "form": item.form,
                    "className": item.class_name.strip(),
                    "roleCode": item.role_code,
                    "availableDays": list(item.available_days),
                    "needsMentoring": item.needs_mentoring,
                    "fixedGeneralDuty": item.fixed_general_duty,
                    "remarks": item.remarks.strip(),
                    "historyWeight": item.history_weight,
                    "historyDuties": item.history_duties,
                }
                for item in inputs
            ]
        }
        receipt: dict[str, object] | None = None
        with self._session() as session:
            self._begin_serialized_write(session)
            command, receipt = self._claim_operation_command(
                session,
                operation_type=operation_type,
                command_id=operation_id,
                payload=operation_payload,
            )
            if receipt is not None:
                session.rollback()
            else:
                for name in normalized_names:
                    self._assert_name_available(session, name)
                for prefect_input in inputs:
                    self._assert_assist_fixed_day_available(session, prefect_input)
                records: list[PrefectRecord] = []
                for prefect_input in inputs:
                    record = self._new_prefect_record(prefect_input)
                    session.add(record)
                    session.flush()
                    self._replace_availability(session, record.id, prefect_input.available_days)
                    records.append(record)
                outputs = [self._prefect_output(session, record) for record in records]
                receipt = {"prefects": outputs}
                self._audit(session, operation_type, None, {"count": len(records)})
                self._commit_operation_command(
                    session,
                    record=command,
                    result=receipt,
                    roster_week_id=None,
                )
                session.commit()
        assert receipt is not None
        self._fulfill_backup_obligation(operation_id)
        replayed = receipt.get("prefects")
        if not isinstance(replayed, list):
            raise WorkflowError("The saved prefect import receipt is invalid.")
        return [dict(item) for item in replayed if isinstance(item, dict)]

    def leave_adjustment_count(self, roster_week_id: int) -> int:
        with self._session() as session:
            return int(
                session.scalar(
                    select(func.count()).select_from(LeaveAdjustmentRecord).where(LeaveAdjustmentRecord.roster_week_id == roster_week_id)
                )
                or 0
            )

    @fenced_workflow_write
    def declare_leave(
        self,
        *,
        week_start: date,
        prefect_id: str,
        day: str,
        reason: str | None = None,
        expected_version: int | None = None,
        command_id: str | None = None,
    ) -> dict[str, object]:
        """Record a pre-generation absence without changing published fairness history."""
        self._require_monday(week_start)
        normalized_reason = reason.strip() if reason else None
        try:
            school_day = SchoolDay[day]
        except KeyError as error:
            raise WorkflowError("Leave declaration contains an invalid weekday.") from error

        operation_type = "pre_generation_leave_declared"
        operation_id = self._operation_command_id(operation_type, command_id)
        operation_payload = {
            "weekStart": week_start.isoformat(),
            "prefectId": prefect_id,
            "day": school_day.name,
            "reason": normalized_reason,
            "expectedVersion": expected_version,
        }
        receipt: dict[str, object] | None = None
        roster_week_id: int | None = None
        with self._session() as session:
            self._begin_serialized_write(session)
            command, receipt = self._claim_operation_command(
                session,
                operation_type=operation_type,
                command_id=operation_id,
                payload=operation_payload,
            )
            if receipt is not None:
                session.rollback()
            else:
                prefect = session.get(PrefectRecord, prefect_id)
                if prefect is None or not prefect.active:
                    raise WorkflowError("The selected prefect is not active.")
                existing_week = session.scalar(
                    select(RosterWeekRecord).where(
                        RosterWeekRecord.week_start == week_start,
                        RosterWeekRecord.status.in_(("draft", "published")),
                    )
                )
                roster_week_id = existing_week.id if existing_week else None
                if existing_week is not None and existing_week.status == "published":
                    raise WorkflowError("A published roster must use a post-publication leave adjustment.")

                declaration = session.scalar(
                    select(LeaveDeclarationRecord).where(
                        LeaveDeclarationRecord.week_start == week_start,
                        LeaveDeclarationRecord.prefect_id == prefect_id,
                        LeaveDeclarationRecord.day == school_day.name,
                    )
                )
                current_version = declaration.version if declaration is not None else 0
                if expected_version is not None and current_version != expected_version:
                    raise WorkflowConflictError(
                        "This leave declaration changed in another browser. "
                        "Reload it before saving."
                    )
                now = self._now()
                if declaration is None:
                    declaration = LeaveDeclarationRecord(
                        week_start=week_start,
                        prefect_id=prefect_id,
                        day=school_day.name,
                        reason=normalized_reason,
                        active=True,
                        version=1,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(declaration)
                else:
                    claim = session.execute(
                        update(LeaveDeclarationRecord)
                        .where(
                            LeaveDeclarationRecord.id == declaration.id,
                            LeaveDeclarationRecord.version == current_version,
                        )
                        .values(
                            reason=normalized_reason,
                            active=True,
                            version=current_version + 1,
                            updated_at=now,
                        )
                    )
                    if claim.rowcount != 1:
                        raise WorkflowConflictError(
                            "This leave declaration changed in another browser. "
                            "Reload it before saving."
                        )
                    session.refresh(declaration)
                session.flush()
                output = self._leave_declaration_output(declaration, prefect)
                receipt = {
                    **output,
                    "weekStart": declaration.week_start.isoformat(),
                    "createdAt": declaration.created_at.isoformat(),
                    "updatedAt": declaration.updated_at.isoformat(),
                }
                self._audit(
                    session,
                    operation_type,
                    roster_week_id,
                    {
                        "prefectId": prefect_id,
                        "weekStart": week_start.isoformat(),
                        "day": school_day.name,
                        "version": declaration.version,
                    },
                )
                self._commit_operation_command(
                    session,
                    record=command,
                    result=receipt,
                    roster_week_id=roster_week_id,
                )
                session.commit()
        assert receipt is not None
        self._fulfill_backup_obligation(operation_id)
        return {
            **receipt,
            "weekStart": date.fromisoformat(str(receipt["weekStart"])),
            "createdAt": datetime.fromisoformat(str(receipt["createdAt"])),
            "updatedAt": datetime.fromisoformat(str(receipt["updatedAt"])),
        }

    @fenced_workflow_write
    def cancel_pre_generation_leave(
        self,
        leave_declaration_id: int,
        *,
        expected_version: int | None = None,
        command_id: str | None = None,
    ) -> None:
        operation_type = "pre_generation_leave_cancelled"
        operation_id = self._operation_command_id(operation_type, command_id)
        operation_payload = {
            "leaveDeclarationId": leave_declaration_id,
            "expectedVersion": expected_version,
        }
        receipt: dict[str, object] | None = None
        with self._session() as session:
            self._begin_serialized_write(session)
            command, receipt = self._claim_operation_command(
                session,
                operation_type=operation_type,
                command_id=operation_id,
                payload=operation_payload,
            )
            if receipt is not None:
                session.rollback()
            else:
                declaration = session.get(LeaveDeclarationRecord, leave_declaration_id)
                if declaration is None or not declaration.active:
                    raise WorkflowError("The leave declaration was not found.")
                reviewed_version = declaration.version if expected_version is None else expected_version
                if declaration.version != reviewed_version:
                    raise WorkflowConflictError(
                        "This leave declaration changed in another browser. "
                        "Reload it before cancelling."
                    )
                week = session.scalar(
                    select(RosterWeekRecord).where(
                        RosterWeekRecord.week_start == declaration.week_start,
                        RosterWeekRecord.status.in_(("draft", "published")),
                    )
                )
                if week is not None and week.status == "published":
                    raise WorkflowError("A published roster must use a post-publication leave adjustment.")
                claim = session.execute(
                    update(LeaveDeclarationRecord)
                    .where(
                        LeaveDeclarationRecord.id == declaration.id,
                        LeaveDeclarationRecord.active.is_(True),
                        LeaveDeclarationRecord.version == reviewed_version,
                    )
                    .values(
                        active=False,
                        version=reviewed_version + 1,
                        updated_at=self._now(),
                    )
                )
                if claim.rowcount != 1:
                    raise WorkflowConflictError(
                        "This leave declaration changed in another browser. "
                        "Reload it before cancelling."
                    )
                receipt = {
                    "leaveDeclarationId": declaration.id,
                    "version": reviewed_version + 1,
                }
                self._audit(
                    session,
                    operation_type,
                    week.id if week else None,
                    {
                        "leaveDeclarationId": declaration.id,
                        "version": reviewed_version + 1,
                    },
                )
                self._commit_operation_command(
                    session,
                    record=command,
                    result=receipt,
                    roster_week_id=week.id if week else None,
                )
                session.commit()
        self._fulfill_backup_obligation(operation_id)

    def pre_generation_leaves(self, week_start: date) -> list[dict[str, object]]:
        self._require_monday(week_start)
        with self._session() as session:
            records = session.execute(
                select(LeaveDeclarationRecord, PrefectRecord)
                .join(PrefectRecord, PrefectRecord.id == LeaveDeclarationRecord.prefect_id)
                .where(
                    LeaveDeclarationRecord.week_start == week_start,
                    LeaveDeclarationRecord.active.is_(True),
                )
                .order_by(LeaveDeclarationRecord.day, PrefectRecord.name_zh)
            ).all()
            return [self._leave_declaration_output(declaration, prefect) for declaration, prefect in records]

    def fairness_rows(self) -> list[dict[str, object]]:
        with self._session() as session:
            rows = sorted(self._active_prefect_records(session), key=lambda row: (row.history_weight, row.name_zh))
            return [
                {
                    "id": row.id,
                    "nameZh": row.name_zh,
                    "form": row.form,
                    "className": row.class_name,
                    "historyWeight": row.history_weight,
                    "historyDuties": row.history_duties,
                }
                for row in rows
            ]

    def reconcile_fairness(self) -> FairnessReconciliationReport:
        """Compare persistent totals with immutable anchors plus ledger deltas."""

        with self._session() as session:
            return self._fairness_reconciliation(session)
