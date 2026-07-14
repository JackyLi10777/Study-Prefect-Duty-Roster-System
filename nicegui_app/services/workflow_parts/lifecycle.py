"""Focused RosterWorkflow behavior extracted without changing its public API."""

from __future__ import annotations

from nicegui_app.services.workflow_dependencies import *

class RosterLifecycleMixin:
    def validate_week_start(self, week_start: date) -> None:
        """Expose the Monday-based workflow boundary without duplicating it in the UI."""
        self._require_monday(week_start)

    def generate_and_save_draft(
        self,
        week_start: date,
        *,
        history_priority_multiplier: float = 1.0,
    ) -> RosterWeekResult:
        self._require_monday(week_start)
        with self._session() as session:
            self._begin_serialized_write(session)
            prefects = self._active_prefects(session)
            leave_days = self._leave_days_for_week(session, week_start)
            try:
                assignments = generate_weekly_roster(
                    prefects,
                    leave_days=leave_days,
                    history_priority_multiplier=history_priority_multiplier,
                )
            except RosterGenerationError as error:
                raise WorkflowError(f"Draft generation needs attention: {error}") from error
            normalized_multiplier = float(history_priority_multiplier)
            week = session.scalar(select(RosterWeekRecord).where(RosterWeekRecord.week_start == week_start))
            now = self._now()
            if week is None:
                week = RosterWeekRecord(
                    week_start=week_start,
                    status="draft",
                    version=1,
                    policy_version=POLICY_VERSION,
                    history_priority_multiplier=normalized_multiplier,
                    generated_at=now,
                    created_at=now,
                    updated_at=now,
                )
                session.add(week)
                session.flush()
            elif week.status == "published":
                raise WorkflowError("This roster is already published; use a post-publication adjustment instead.")
            else:
                week.version += 1
                week.history_priority_multiplier = normalized_multiplier
                week.generated_at = now
                week.updated_at = now
                session.execute(delete(RosterAssignmentRecord).where(RosterAssignmentRecord.roster_week_id == week.id))
                session.flush()

            self._store_assignments(session, week.id, assignments, prefects)
            self._audit(
                session,
                "draft_generated",
                week.id,
                {
                    "assignmentCount": len(assignments),
                    "leaveDeclarationCount": sum(len(days) for days in leave_days.values()),
                    "historyPriorityMultiplier": normalized_multiplier,
                    "version": week.version,
                },
            )
            session.commit()
            result = RosterWeekResult(
                id=week.id,
                week_start=week.week_start,
                status=week.status,
                version=week.version,
                assignment_count=len(assignments),
                backup_path=Path(),
                history_priority_multiplier=week.history_priority_multiplier,
            )
        backup = self._create_and_record_backup("draft_generated", result.id)
        return RosterWeekResult(
            **{**result.__dict__, "backup_path": self._require_backup(backup, committed_event="draft_generated")}
        )

    def publish(self, roster_week_id: int, *, expected_week_version: int) -> RosterWeekResult:
        """Publish exactly the draft version the operator reviewed.

        ``expected_week_version`` is a compare-and-set token carried from the
        read model shown in the confirmation UI.  The database update remains
        the single-winner publication claim, while the version predicate also
        prevents an older browser tab from publishing assignments which were
        regenerated or edited after that tab completed its review.
        """
        if expected_week_version < 1:
            raise WorkflowError("The reviewed roster version is invalid. Refresh and review the draft again.")
        with self._session() as session:
            now = self._now()
            claim = session.execute(
                update(RosterWeekRecord)
                .where(
                    RosterWeekRecord.id == roster_week_id,
                    RosterWeekRecord.status == "draft",
                    RosterWeekRecord.version == expected_week_version,
                )
                .values(status="published", published_at=now, updated_at=now)
            )
            if claim.rowcount != 1:
                current_week = session.get(RosterWeekRecord, roster_week_id)
                if current_week is None:
                    raise WorkflowError("Roster week was not found.")
                if current_week.status != "draft":
                    raise WorkflowError("This roster is already published.")
                raise WorkflowConflictError(
                    "This draft changed after it was reviewed. Refresh it and review the latest version before publishing."
                )

            # Claiming the draft before reading assignments makes publication a
            # database-level single-winner operation. Any later validation
            # error rolls this transaction back to the draft state.
            week = self._week_or_error(session, roster_week_id)
            assignment_rows = self._assignment_rows(session, week.id)
            operation_id = f"roster-publish:{week.id}"
            self._validate_persisted_assignments(session, assignment_rows, week_start=week.week_start)
            for row in assignment_rows:
                if row.prefect_id is None or row.status != "active":
                    raise WorkflowError("A roster with a vacancy cannot be published.")
                prefect = session.get(PrefectRecord, row.prefect_id)
                if prefect is None:
                    raise WorkflowError("An assigned prefect no longer exists.")
                prefect.history_weight = round(prefect.history_weight + row.weight, 4)
                prefect.history_duties += 1
                prefect.updated_at = now
                session.add(
                    FairnessLedgerRecord(
                        prefect_id=prefect.id,
                        roster_week_id=week.id,
                        assignment_id=row.id,
                        delta=row.weight,
                        duty_delta=1,
                        event_type="roster_published",
                        source_type="roster_publish",
                        source_id=str(week.id),
                        operation_id=operation_id,
                        reason="Weekly roster published",
                        created_at=now,
                    )
                )
            self._audit(
                session,
                "roster_published",
                week.id,
                {
                    "assignmentCount": len(assignment_rows),
                    "historyPriorityMultiplier": week.history_priority_multiplier,
                    "version": week.version,
                },
            )
            self._assert_fairness_reconciled(session)
            session.commit()
            result = RosterWeekResult(
                id=week.id,
                week_start=week.week_start,
                status=week.status,
                version=week.version,
                assignment_count=len(assignment_rows),
                backup_path=Path(),
                history_priority_multiplier=week.history_priority_multiplier,
            )
        backup = self._create_and_record_backup("roster_published", result.id)
        return RosterWeekResult(
            **{**result.__dict__, "backup_path": self._require_backup(backup, committed_event="roster_published")}
        )

    def recommend_substitutes(self, roster_week_id: int, assignment_id: int) -> list[dict[str, object]]:
        """Return only currently eligible substitutes for a published-duty absence.

        This deliberately shares the same leave, availability, duplicate-day,
        consecutive-duty, and role gates as a manual draft change.  A recorded
        pre-generation absence remains a real absence after publication; it
        cannot be bypassed by the later adjustment screen.
        """
        with self._session() as session:
            week = self._week_or_error(session, roster_week_id)
            if week.status != "published":
                raise WorkflowError("Substitute recommendations are available only for a published roster.")
            assignment = self._assignment_or_error(session, roster_week_id, assignment_id)
            return self._eligible_assignment_candidates(session, week, assignment)

    def draft_assignment_candidates(self, roster_week_id: int, assignment_id: int) -> list[dict[str, object]]:
        """Offer only rule-compliant replacements while a roster is still a draft."""
        with self._session() as session:
            week = self._week_or_error(session, roster_week_id)
            if week.status != "draft":
                raise WorkflowError("Manual assignment changes are available only for a draft roster.")
            assignment = self._assignment_or_error(session, roster_week_id, assignment_id)
            return self._eligible_assignment_candidates(session, week, assignment)

    def update_draft_assignment(
        self,
        *,
        roster_week_id: int,
        assignment_id: int,
        replacement_prefect_id: str,
        reason: str,
        expected_week_version: int | None = None,
    ) -> DraftAssignmentUpdateResult:
        """Apply an auditable, policy-validated manual draft change without posting fairness weight."""
        if not reason.strip():
            raise WorkflowError("A manual draft change requires a reason.")
        with self._session() as session:
            self._begin_serialized_write(session)
            week = self._week_or_error(session, roster_week_id)
            if week.status != "draft":
                raise WorkflowError("Only a draft roster can be changed manually.")
            reviewed_version = week.version if expected_week_version is None else expected_week_version
            if week.version != reviewed_version:
                raise WorkflowConflictError(
                    "This draft changed in another browser. Refresh and review the latest version before saving."
                )
            assignment = self._assignment_or_error(session, roster_week_id, assignment_id)
            candidates = {candidate["id"] for candidate in self._eligible_assignment_candidates(session, week, assignment)}
            if replacement_prefect_id not in candidates:
                raise WorkflowError("The selected prefect does not meet the current roster rules for this post.")
            if assignment.prefect_id == replacement_prefect_id:
                raise WorkflowError("Choose a different prefect or cancel this manual change.")
            replacement = session.get(PrefectRecord, replacement_prefect_id)
            if replacement is None:
                raise WorkflowError("The selected prefect no longer exists.")
            claim = session.execute(
                update(RosterWeekRecord)
                .where(
                    RosterWeekRecord.id == roster_week_id,
                    RosterWeekRecord.status == "draft",
                    RosterWeekRecord.version == reviewed_version,
                )
                .values(version=reviewed_version + 1, updated_at=self._now())
            )
            if claim.rowcount != 1:
                raise WorkflowConflictError(
                    "This draft changed in another browser. Refresh and review the latest version before saving."
                )
            session.refresh(week)
            original_prefect_id = assignment.prefect_id
            original_name = assignment.prefect_name_snapshot
            assignment.prefect_id = replacement.id
            assignment.prefect_name_snapshot = replacement.name_zh
            assignment.prefect_role_snapshot = replacement.role_code
            assignment.status = "active"
            self._validate_persisted_assignments(session, self._assignment_rows(session, week.id), week_start=week.week_start)
            self._audit(
                session,
                "draft_assignment_changed",
                week.id,
                {
                    "assignmentId": assignment.id,
                    "fromPrefectId": original_prefect_id,
                    "fromPrefectName": original_name,
                    "toPrefectId": replacement.id,
                    "toPrefectName": replacement.name_zh,
                    "reason": reason.strip(),
                    "version": week.version,
                },
            )
            session.commit()
            result = DraftAssignmentUpdateResult(week.id, assignment.id, week.version, Path())
        backup = self._create_and_record_backup("draft_assignment_changed", roster_week_id)
        return DraftAssignmentUpdateResult(
            **{
                **result.__dict__,
                "backup_path": self._require_backup(backup, committed_event="draft_assignment_changed"),
            }
        )

    def apply_leave_adjustment(
        self,
        *,
        roster_week_id: int,
        assignment_id: int,
        replacement_prefect_id: str | None,
        reason: str,
        command_id: str | None = None,
        expected_week_version: int | None = None,
    ) -> LeaveAdjustmentResult:
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise WorkflowError("A leave adjustment requires a reason.")
        operation_id = command_id or f"leave-adjustment:{uuid4().hex}"
        if len(operation_id) > 64 or not operation_id.strip():
            raise WorkflowError("Leave adjustment command ID is invalid.")
        request_fingerprint = self._leave_adjustment_request_fingerprint(
            roster_week_id=roster_week_id,
            assignment_id=assignment_id,
            replacement_prefect_id=replacement_prefect_id,
            reason=normalized_reason,
        )
        committed_version = 0
        with self._session() as session:
            duplicate = session.scalar(
                select(LeaveAdjustmentRecord).where(LeaveAdjustmentRecord.command_id == operation_id)
            )
            if duplicate is not None:
                return self._leave_adjustment_replay_result(
                    duplicate,
                    roster_week_id=roster_week_id,
                    assignment_id=assignment_id,
                    replacement_prefect_id=replacement_prefect_id,
                    reason=normalized_reason,
                    request_fingerprint=request_fingerprint,
                )

            week = self._week_or_error(session, roster_week_id)
            requested_version = week.version if expected_week_version is None else expected_week_version
            if week.status != "published":
                raise WorkflowError("Post-publication adjustments require a published roster.")
            assignment = self._assignment_or_error(session, roster_week_id, assignment_id)
            if assignment.status != "active" or assignment.prefect_id is None:
                raise WorkflowError("This assignment is no longer active.")
            original = session.get(PrefectRecord, assignment.prefect_id)
            if original is None:
                raise WorkflowError("The original prefect no longer exists.")
            candidates = {candidate["id"] for candidate in self._eligible_assignment_candidates(session, week, assignment)}
            replacement = None
            if replacement_prefect_id:
                if replacement_prefect_id not in candidates:
                    raise WorkflowError("The selected substitute no longer meets roster rules.")
                replacement = session.get(PrefectRecord, replacement_prefect_id)
                if replacement is None:
                    raise WorkflowError("The selected substitute no longer exists.")

            now = self._now()
            claim = session.execute(
                update(RosterWeekRecord)
                .where(
                    RosterWeekRecord.id == roster_week_id,
                    RosterWeekRecord.status == "published",
                    RosterWeekRecord.version == requested_version,
                )
                .values(version=RosterWeekRecord.version + 1, updated_at=now)
            )
            if claim.rowcount != 1:
                session.rollback()
                duplicate = session.scalar(
                    select(LeaveAdjustmentRecord).where(LeaveAdjustmentRecord.command_id == operation_id)
                )
                if duplicate is None:
                    raise WorkflowConflictError(
                        "This roster was updated in another tab. Refresh it and review the adjustment again."
                    )
                return self._leave_adjustment_replay_result(
                    duplicate,
                    roster_week_id=roster_week_id,
                    assignment_id=assignment_id,
                    replacement_prefect_id=replacement_prefect_id,
                    reason=normalized_reason,
                    request_fingerprint=request_fingerprint,
                )

            original_name = assignment.prefect_name_snapshot
            original_id = assignment.prefect_id
            original.history_weight = round(original.history_weight - assignment.weight, 4)
            original.history_duties = max(0, original.history_duties - 1)
            original.updated_at = now
            session.add(
                FairnessLedgerRecord(
                    prefect_id=original.id,
                    roster_week_id=week.id,
                    assignment_id=assignment.id,
                    delta=-assignment.weight,
                    duty_delta=-1,
                    event_type="leave_adjustment_debit",
                    source_type="leave_adjustment",
                    source_id=operation_id,
                    operation_id=operation_id,
                    reason=normalized_reason,
                    created_at=now,
                )
            )

            status = "vacant"
            replacement_name = None
            if replacement is not None:
                replacement.history_weight = round(replacement.history_weight + assignment.weight, 4)
                replacement.history_duties += 1
                replacement.updated_at = now
                assignment.prefect_id = replacement.id
                assignment.prefect_name_snapshot = replacement.name_zh
                assignment.prefect_role_snapshot = replacement.role_code
                replacement_name = replacement.name_zh
                status = "replaced"
                session.add(
                    FairnessLedgerRecord(
                        prefect_id=replacement.id,
                        roster_week_id=week.id,
                        assignment_id=assignment.id,
                        delta=assignment.weight,
                        duty_delta=1,
                        event_type="leave_adjustment_credit",
                        source_type="leave_adjustment",
                        source_id=operation_id,
                        operation_id=operation_id,
                        reason=normalized_reason,
                        created_at=now,
                    )
                )
            else:
                assignment.prefect_id = None
                assignment.prefect_name_snapshot = "VACANT"
                assignment.prefect_role_snapshot = None
                assignment.status = "vacant"

            adjustment = LeaveAdjustmentRecord(
                roster_week_id=week.id,
                assignment_id=assignment.id,
                original_prefect_id=original_id,
                original_prefect_name=original_name,
                replacement_prefect_id=replacement.id if replacement else None,
                replacement_prefect_name=replacement_name,
                reason=normalized_reason,
                status=status,
                command_id=operation_id,
                request_fingerprint=request_fingerprint,
                committed_version=requested_version + 1,
                created_at=now,
            )
            session.add(adjustment)
            self._audit(
                session,
                "leave_adjusted",
                week.id,
                {"assignmentId": assignment.id, "status": status, "commandId": operation_id},
            )
            self._assert_fairness_reconciled(session)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                duplicate = session.scalar(
                    select(LeaveAdjustmentRecord).where(LeaveAdjustmentRecord.command_id == operation_id)
                )
                if duplicate is None:
                    raise
                return self._leave_adjustment_replay_result(
                    duplicate,
                    roster_week_id=roster_week_id,
                    assignment_id=assignment_id,
                    replacement_prefect_id=replacement_prefect_id,
                    reason=normalized_reason,
                    request_fingerprint=request_fingerprint,
                )
            committed_version = requested_version + 1

        backup = self._create_and_record_backup("leave_adjusted", roster_week_id)
        return LeaveAdjustmentResult(
            roster_week_id,
            assignment_id,
            status,
            self._require_backup(backup, committed_event="leave_adjusted"),
            committed_version,
            False,
        )

    @staticmethod
    def _leave_adjustment_request_fingerprint(
        *,
        roster_week_id: int,
        assignment_id: int,
        replacement_prefect_id: str | None,
        reason: str,
    ) -> str:
        """Return the durable identity of one leave-adjustment intent.

        The optimistic version is not part of the identity: after an unknown
        response, an exact retry must recover the original receipt even if the
        aggregate version has since advanced.
        """
        payload = {
            "assignmentId": assignment_id,
            "reason": reason,
            "replacementPrefectId": replacement_prefect_id,
            "rosterWeekId": roster_week_id,
            "schemaVersion": 1,
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _leave_adjustment_replay_result(
        duplicate: LeaveAdjustmentRecord,
        *,
        roster_week_id: int,
        assignment_id: int,
        replacement_prefect_id: str | None,
        reason: str,
        request_fingerprint: str,
    ) -> LeaveAdjustmentResult:
        same_request = (
            duplicate.roster_week_id == roster_week_id
            and duplicate.assignment_id == assignment_id
            and duplicate.replacement_prefect_id == replacement_prefect_id
            and duplicate.reason == reason
            and duplicate.request_fingerprint == request_fingerprint
        )
        if not same_request:
            raise WorkflowConflictError(
                "This leave-adjustment command ID was already used for a different request."
            )
        return LeaveAdjustmentResult(
            duplicate.roster_week_id,
            duplicate.assignment_id,
            duplicate.status,
            None,
            duplicate.committed_version,
            True,
        )

    def roster_weeks(self) -> list[dict[str, object]]:
        with self._session() as session:
            rows = session.scalars(select(RosterWeekRecord).order_by(RosterWeekRecord.week_start.desc())).all()
            return [
                {
                    "id": row.id,
                    "weekStart": row.week_start,
                    "status": row.status,
                    "version": row.version,
                    "historyPriorityMultiplier": row.history_priority_multiplier,
                    "generatedAt": row.generated_at,
                    "publishedAt": row.published_at,
                }
                for row in rows
            ]

    def roster_week(self, roster_week_id: int) -> dict[str, object]:
        with self._session() as session:
            row = self._week_or_error(session, roster_week_id)
            return {
                "id": row.id,
                "weekStart": row.week_start,
                "status": row.status,
                "version": row.version,
                "historyPriorityMultiplier": row.history_priority_multiplier,
                "generatedAt": row.generated_at,
                "publishedAt": row.published_at,
            }

    def assignments(self, roster_week_id: int) -> list[dict[str, object]]:
        with self._session() as session:
            # Keep "not found" distinct from a real roster with no assignments.
            # Route recovery, exports, and operator diagnostics all depend on this
            # read boundary reporting a stale roster identifier consistently.
            self._week_or_error(session, roster_week_id)
            rows = self._assignment_rows(session, roster_week_id)
            return [
                {
                    "id": row.id,
                    "day": row.day,
                    "postCode": row.post_code,
                    "slotIndex": row.slot_index,
                    "prefectId": row.prefect_id,
                    "prefectName": row.prefect_name_snapshot,
                    "weight": row.weight,
                    "status": row.status,
                }
                for row in rows
            ]

    def generation_requirements(self, week_start: date) -> list[dict[str, object]]:
        """Expose every required weekly slot and its currently eligible pool before generation."""
        self._require_monday(week_start)
        with self._session() as session:
            availability = self._availability_by_prefect(session)
            leave_days = self._leave_days_for_week(session, week_start)
            prefects = self._active_prefect_records(session)
            requirements: list[dict[str, object]] = []
            for day in SchoolDay:
                slot_counts: dict[DutyPost, int] = defaultdict(int)
                for post in required_posts_for_day(day):
                    slot_counts[post] += 1
                    candidates = [
                        prefect
                        for prefect in prefects
                    if day in availability.get(prefect.id, set())
                    and day not in leave_days.get(prefect.id, set())
                    and can_assign_role(PrefectRole(prefect.role_code), post)
                    ]
                    requirements.append(
                        {
                            "day": day.name,
                            "postCode": post.name,
                            "slotIndex": slot_counts[post],
                            "eligibleCount": len(candidates),
                            "hasVacancyRisk": not candidates,
                        }
                    )
            return requirements
