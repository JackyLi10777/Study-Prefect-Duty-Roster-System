"""Focused RosterWorkflow behavior extracted without changing its public API."""

from __future__ import annotations

from nicegui_app.services.workflow_dependencies import (
    ASSIST_ASSIGNMENT_MODE_CODES,
    DraftAssignmentUpdateResult,
    DraftCellEdit,
    DraftDayEdit,
    DraftPatchResult,
    DutyPost,
    ExternalShareOutboxRecord,
    FairnessLedgerRecord,
    LEGACY_FIXED_WEEKDAY,
    LeaveAdjustmentRecord,
    LeaveAdjustmentResult,
    Iterable,
    POLICY_VERSION,
    Prefect,
    PrefectRecord,
    PrefectRole,
    RosterAssignmentRecord,
    RosterDayClosureRecord,
    RosterGenerationError,
    RosterWeekRecord,
    RosterWeekResult,
    RosterWithdrawalResult,
    SchoolDay,
    Session,
    WorkflowConflictError,
    WorkflowError,
    can_assign_role,
    date,
    datetime,
    defaultdict,
    delete,
    duty_weight,
    func,
    generate_weekly_roster,
    hashlib,
    json,
    legacy_assist_weekday_mapping,
    required_posts_for_day,
    select,
    update,
    WeekScheduleOverrides,
)
from nicegui_app.services.workflow_fencing import fenced_workflow_write
from roster_policy import AssistAssignmentMode


def _assist_assignment_mode_code(value: object) -> str:
    """Normalize an enum or stable code before it crosses the workflow boundary."""

    raw_value = getattr(value, "value", value)
    normalized = str(raw_value).strip()
    if normalized not in ASSIST_ASSIGNMENT_MODE_CODES:
        allowed = ", ".join(sorted(ASSIST_ASSIGNMENT_MODE_CODES))
        raise WorkflowError(
            f"Unsupported Assist assignment mode; expected one of: {allowed}."
        )
    return normalized


_DAY_CLOSURE_REASON_CODES = frozenset(
    {"school_event", "weather", "examination", "special_arrangement", "other"}
)


def _stable_school_day(value: SchoolDay | str) -> SchoolDay:
    if isinstance(value, SchoolDay):
        return value
    try:
        return SchoolDay[str(value).strip().upper()]
    except KeyError as error:
        raise WorkflowError("A roster day must use a stable weekday code.") from error


def _normalized_closed_days(values: object) -> tuple[SchoolDay, ...]:
    if values is None:
        return ()
    try:
        days = tuple(_stable_school_day(value) for value in values)  # type: ignore[arg-type]
    except TypeError as error:
        raise WorkflowError("Closed days must be a weekday collection.") from error
    if len(days) != len(set(days)):
        raise WorkflowError("Closed days contain a duplicate weekday.")
    return tuple(sorted(days, key=int))


def _parse_cell_key(cell_key: str) -> tuple[SchoolDay, DutyPost, int]:
    parts = str(cell_key).strip().upper().split(":")
    if len(parts) != 3:
        raise WorkflowError("Draft cell key must be DAY:POST:SLOT.")
    try:
        day = SchoolDay[parts[0]]
        post = DutyPost[parts[1]]
        slot_index = int(parts[2])
    except (KeyError, ValueError) as error:
        raise WorkflowError("Draft cell key contains an invalid stable code.") from error
    allowed_count = required_posts_for_day(day).count(post)
    if slot_index < 1 or slot_index > allowed_count:
        raise WorkflowError("Draft cell key does not identify a required roster slot.")
    return day, post, slot_index


def _initialize_legacy_assist_weekdays(
    session: Session,
    prefects: list[Prefect],
    *,
    now: datetime,
) -> dict[str, str]:
    """Persist the first accepted automatic legacy mapping.

    The old policy is person-owned rather than roster-owned: adding a new AHP
    later must not move everybody else's weekday. Existing explicit mappings
    are never overwritten, and a person serving more than once in a shortage
    week cannot be represented by the single legacy weekday field.
    """

    assist_days = legacy_assist_weekday_mapping(prefects)
    role_by_id = {prefect.id: prefect.role for prefect in prefects}
    initialized: dict[str, str] = {}
    for prefect_id, days in assist_days.items():
        if role_by_id.get(prefect_id) is not PrefectRole.ASSISTANT_HEAD or len(days) != 1:
            continue
        record = session.get(PrefectRecord, prefect_id)
        if record is None or record.fixed_general_duty != "NONE":
            continue
        record.fixed_general_duty = days[0].name
        record.version += 1
        record.updated_at = now
        initialized[prefect_id] = days[0].name
    return initialized


def _previous_assist_weekday_assignments(
    session: Session,
    week_start: date,
) -> dict[SchoolDay, str]:
    """Return Assist owners from the latest active roster before this week."""

    previous_week = session.scalar(
        select(RosterWeekRecord)
        .where(
            RosterWeekRecord.week_start < week_start,
            RosterWeekRecord.status.in_(("draft", "published")),
        )
        .order_by(RosterWeekRecord.week_start.desc(), RosterWeekRecord.id.desc())
        .limit(1)
    )
    if previous_week is None:
        return {}
    rows = session.scalars(
        select(RosterAssignmentRecord).where(
            RosterAssignmentRecord.roster_week_id == previous_week.id,
            RosterAssignmentRecord.post_code == DutyPost.ASSIST_IN_CHARGE.name,
            RosterAssignmentRecord.status == "active",
        )
    ).all()
    return {
        SchoolDay[row.day]: row.prefect_id
        for row in rows
        if row.prefect_id is not None and row.day in SchoolDay.__members__
    }


class RosterLifecycleMixin:
    def validate_week_start(self, week_start: date) -> None:
        """Expose the Monday-based workflow boundary without duplicating it in the UI."""
        self._require_monday(week_start)

    @fenced_workflow_write
    def generate_and_save_draft(
        self,
        week_start: date,
        *,
        history_priority_multiplier: float = 1.0,
        assist_assignment_mode: AssistAssignmentMode | str = LEGACY_FIXED_WEEKDAY,
        closed_days: Iterable[SchoolDay | str] = (),
        expected_week_version: int | None = None,
        command_id: str | None = None,
    ) -> RosterWeekResult:
        self._require_monday(week_start)
        normalized_assist_mode = _assist_assignment_mode_code(assist_assignment_mode)
        normalized_closed_days = _normalized_closed_days(closed_days)
        operation_type = "draft_generated"
        operation_id = self._operation_command_id(operation_type, command_id)
        operation_payload = {
            "weekStart": week_start.isoformat(),
            "historyPriorityMultiplier": float(history_priority_multiplier),
            "assistAssignmentMode": normalized_assist_mode,
            "closedDays": [day.name for day in normalized_closed_days],
            "expectedWeekVersion": expected_week_version,
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
                existing_week = session.scalar(
                    select(RosterWeekRecord).where(
                        RosterWeekRecord.week_start == week_start,
                        RosterWeekRecord.status.in_(("draft", "published")),
                    )
                )
                current_version = existing_week.version if existing_week is not None else 0
                if expected_week_version is not None and current_version != expected_week_version:
                    raise WorkflowConflictError(
                        "This roster week changed in another browser. "
                        "Reload the current version before generating again."
                    )
                prefects = self._active_prefects(session)
                leave_days = self._leave_days_for_week(session, week_start)
                previous_assist_assignments = _previous_assist_weekday_assignments(
                    session,
                    week_start,
                )
                try:
                    assignments = generate_weekly_roster(
                        prefects,
                        leave_days=leave_days,
                        history_priority_multiplier=history_priority_multiplier,
                        assist_assignment_mode=normalized_assist_mode,
                        assist_rotation_key=week_start.isoformat(),
                        previous_assist_assignments=previous_assist_assignments,
                        closed_days=normalized_closed_days,
                    )
                except RosterGenerationError as error:
                    raise WorkflowError(f"Draft generation needs attention: {error}") from error
                normalized_multiplier = float(history_priority_multiplier)
                week = existing_week
                now = self._now()
                initialized_fixed_weekdays = (
                    _initialize_legacy_assist_weekdays(
                        session,
                        prefects,
                        now=now,
                    )
                    if normalized_assist_mode == LEGACY_FIXED_WEEKDAY
                    and len(normalized_closed_days) < len(SchoolDay)
                    else {}
                )
                if week is None:
                    week = RosterWeekRecord(
                        week_start=week_start,
                        status="draft",
                        version=1,
                        policy_version=POLICY_VERSION,
                        history_priority_multiplier=normalized_multiplier,
                        assist_assignment_mode=normalized_assist_mode,
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
                    week.assist_assignment_mode = normalized_assist_mode
                    week.generated_at = now
                    week.updated_at = now
                    session.execute(delete(RosterAssignmentRecord).where(RosterAssignmentRecord.roster_week_id == week.id))
                    session.execute(
                        delete(RosterDayClosureRecord).where(
                            RosterDayClosureRecord.roster_week_id == week.id
                        )
                    )
                    session.flush()

                for closed_day in normalized_closed_days:
                    session.add(
                        RosterDayClosureRecord(
                            roster_week_id=week.id,
                            day=closed_day.name,
                            reason_code=None,
                            note=None,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                self._store_assignments(session, week.id, assignments, prefects)
                receipt = {
                    "id": week.id,
                    "weekStart": week.week_start.isoformat(),
                    "status": week.status,
                    "version": week.version,
                    "assignmentCount": len(assignments),
                    "historyPriorityMultiplier": week.history_priority_multiplier,
                    "assistAssignmentMode": week.assist_assignment_mode,
                    "closedDays": [day.name for day in normalized_closed_days],
                }
                self._audit(
                    session,
                    operation_type,
                    week.id,
                    {
                        "assignmentCount": len(assignments),
                        "leaveDeclarationCount": sum(len(days) for days in leave_days.values()),
                        "historyPriorityMultiplier": normalized_multiplier,
                        "assistAssignmentMode": normalized_assist_mode,
                        "previousAssistWeekdayCount": len(previous_assist_assignments),
                        "fixedWeekdayAssignmentsInitialized": initialized_fixed_weekdays,
                        "closedDays": [day.name for day in normalized_closed_days],
                        "version": week.version,
                    },
                )
                self._commit_operation_command(
                    session,
                    record=command,
                    result=receipt,
                    roster_week_id=week.id,
                )
                session.commit()
        assert receipt is not None
        backup_path = self._fulfill_backup_obligation(operation_id)
        result = RosterWeekResult(
            id=int(receipt["id"]),
            week_start=date.fromisoformat(str(receipt["weekStart"])),
            status=str(receipt["status"]),
            version=int(receipt["version"]),
            assignment_count=int(receipt["assignmentCount"]),
            backup_path=backup_path,
            history_priority_multiplier=float(receipt["historyPriorityMultiplier"]),
            assist_assignment_mode=str(
                receipt.get("assistAssignmentMode", LEGACY_FIXED_WEEKDAY)
            ),
        )
        return result

    @fenced_workflow_write
    def publish(
        self,
        roster_week_id: int,
        *,
        expected_week_version: int,
        command_id: str | None = None,
    ) -> RosterWeekResult:
        """Publish exactly the draft version the operator reviewed.

        ``expected_week_version`` is a compare-and-set token carried from the
        read model shown in the confirmation UI.  The database update remains
        the single-winner publication claim, while the version predicate also
        prevents an older browser tab from publishing assignments which were
        regenerated or edited after that tab completed its review.
        """
        if expected_week_version < 1:
            raise WorkflowError("The reviewed roster version is invalid. Refresh and review the draft again.")
        operation_type = "roster_published"
        command_key = self._operation_command_id(operation_type, command_id)
        receipt: dict[str, object] | None = None
        with self._session() as session:
            self._begin_serialized_write(session)
            command, receipt = self._claim_operation_command(
                session,
                operation_type=operation_type,
                command_id=command_key,
                payload={
                    "rosterWeekId": roster_week_id,
                    "expectedWeekVersion": expected_week_version,
                },
            )
            if receipt is not None:
                session.rollback()
            else:
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
                closed_days = self._closed_days(session, week.id)
                ledger_operation_id = f"roster-publish:{week.id}"
                self._validate_persisted_assignments(
                    session,
                    assignment_rows,
                    week_start=week.week_start,
                    closed_days=closed_days,
                )
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
                            event_type=operation_type,
                            source_type="roster_publish",
                            source_id=str(week.id),
                            operation_id=ledger_operation_id,
                            reason="Weekly roster published",
                            created_at=now,
                        )
                    )
                receipt = {
                    "id": week.id,
                    "weekStart": week.week_start.isoformat(),
                    "status": week.status,
                    "version": week.version,
                    "assignmentCount": len(assignment_rows),
                    "historyPriorityMultiplier": week.history_priority_multiplier,
                    "assistAssignmentMode": week.assist_assignment_mode,
                    "closedDays": [day.name for day in closed_days],
                }
                self._audit(
                    session,
                    operation_type,
                    week.id,
                    {
                        "assignmentCount": len(assignment_rows),
                        "historyPriorityMultiplier": week.history_priority_multiplier,
                        "assistAssignmentMode": week.assist_assignment_mode,
                        "closedDays": [day.name for day in closed_days],
                        "version": week.version,
                    },
                )
                self._assert_fairness_reconciled(session)
                self._commit_operation_command(
                    session,
                    record=command,
                    result=receipt,
                    roster_week_id=week.id,
                )
                session.commit()
        assert receipt is not None
        return RosterWeekResult(
            id=int(receipt["id"]),
            week_start=date.fromisoformat(str(receipt["weekStart"])),
            status=str(receipt["status"]),
            version=int(receipt["version"]),
            assignment_count=int(receipt["assignmentCount"]),
            backup_path=self._fulfill_backup_obligation(command_key),
            history_priority_multiplier=float(receipt["historyPriorityMultiplier"]),
            assist_assignment_mode=str(
                receipt.get("assistAssignmentMode", LEGACY_FIXED_WEEKDAY)
            ),
        )

    @fenced_workflow_write
    def withdraw_published_roster(
        self,
        roster_week_id: int,
        *,
        expected_version: int,
        reason: str | None = None,
        command_id: str | None = None,
    ) -> RosterWithdrawalResult:
        """Withdraw one published roster while preserving evidence and fairness truth.

        This is deliberately not a delete.  The roster, assignments, leave
        adjustments, publication evidence, and audit trail remain available;
        only the active publication state and its net fairness effect are
        reversed.  Grouping the existing ledger is essential because a
        published roster may already contain one or more substitute transfers.
        """

        normalized_reason = (reason or "").strip()
        if expected_version < 1:
            raise WorkflowError("The reviewed roster version is invalid. Refresh before withdrawing it.")

        operation_type = "roster_withdrawn"
        command_key = self._operation_command_id(operation_type, command_id)
        receipt: dict[str, object] | None = None
        idempotent = False
        with self._session() as session:
            self._begin_serialized_write(session)
            command, receipt = self._claim_operation_command(
                session,
                operation_type=operation_type,
                command_id=command_key,
                payload={
                    "rosterWeekId": roster_week_id,
                    "expectedVersion": expected_version,
                    "reason": normalized_reason,
                },
            )
            if receipt is not None:
                idempotent = True
                session.rollback()
            else:
                now = self._now()
                claim = session.execute(
                    update(RosterWeekRecord)
                    .where(
                        RosterWeekRecord.id == roster_week_id,
                        RosterWeekRecord.status == "published",
                        RosterWeekRecord.version == expected_version,
                    )
                    .values(
                        status="withdrawn",
                        version=expected_version + 1,
                        withdrawn_at=now,
                        withdrawal_reason=normalized_reason,
                        updated_at=now,
                    )
                )
                if claim.rowcount != 1:
                    current = session.get(RosterWeekRecord, roster_week_id)
                    if current is None:
                        raise WorkflowError("Roster week was not found.")
                    if current.status == "withdrawn":
                        raise WorkflowError("This published roster has already been withdrawn.")
                    if current.status != "published":
                        raise WorkflowError("Only a published roster can be withdrawn.")
                    raise WorkflowConflictError(
                        "This roster changed in another browser. Reload and review the latest version before withdrawing it."
                    )

                week = self._week_or_error(session, roster_week_id)
                ledger_totals = session.execute(
                    select(
                        FairnessLedgerRecord.prefect_id,
                        FairnessLedgerRecord.assignment_id,
                        func.coalesce(func.sum(FairnessLedgerRecord.delta), 0.0),
                        func.coalesce(func.sum(FairnessLedgerRecord.duty_delta), 0),
                    )
                    .where(FairnessLedgerRecord.roster_week_id == roster_week_id)
                    .group_by(
                        FairnessLedgerRecord.prefect_id,
                        FairnessLedgerRecord.assignment_id,
                    )
                ).all()
                prefect_ids = {prefect_id for prefect_id, *_rest in ledger_totals}
                prefects_by_id = {
                    prefect.id: prefect
                    for prefect in session.scalars(
                        select(PrefectRecord).where(PrefectRecord.id.in_(prefect_ids))
                    ).all()
                }
                compensation_count = 0
                ledger_operation_id = f"roster-withdraw:{week.id}"
                for prefect_id, assignment_id, net_weight, net_duties in ledger_totals:
                    weight_delta = round(float(net_weight), 4)
                    duty_delta = int(net_duties)
                    if abs(weight_delta) <= 0.0001 and duty_delta == 0:
                        continue
                    prefect = prefects_by_id.get(prefect_id)
                    if prefect is None:
                        raise WorkflowError("A fairness-ledger prefect no longer exists; withdrawal was rolled back.")
                    prefect.history_weight = round(prefect.history_weight - weight_delta, 4)
                    prefect.history_duties -= duty_delta
                    prefect.updated_at = now
                    session.add(
                        FairnessLedgerRecord(
                            prefect_id=prefect.id,
                            roster_week_id=week.id,
                            assignment_id=assignment_id,
                            delta=-weight_delta,
                            duty_delta=-duty_delta,
                            event_type=operation_type,
                            source_type="roster_withdrawal",
                            source_id=str(week.id),
                            operation_id=ledger_operation_id,
                            reason=normalized_reason,
                            created_at=now,
                        )
                    )
                    compensation_count += 1

                share_ids_to_revoke = self._queue_obsolete_external_share_revocations(
                    session,
                    roster_week_id=roster_week_id,
                    current_version=None,
                    invalidated_by="roster_withdrawn",
                    now=now,
                )

                receipt = {
                    "rosterWeekId": week.id,
                    "weekStart": week.week_start.isoformat(),
                    "status": week.status,
                    "version": week.version,
                    "reason": normalized_reason,
                    "shareIdsToRevoke": share_ids_to_revoke,
                }
                self._audit(
                    session,
                    operation_type,
                    week.id,
                    {
                        "reason": normalized_reason,
                        "version": week.version,
                        "compensationEntryCount": compensation_count,
                        "shareRevocationCount": len(share_ids_to_revoke),
                    },
                )
                self._assert_fairness_reconciled(session)
                self._commit_operation_command(
                    session,
                    record=command,
                    result=receipt,
                    roster_week_id=week.id,
                )
                session.commit()

        assert receipt is not None
        return RosterWithdrawalResult(
            roster_week_id=int(receipt["rosterWeekId"]),
            week_start=date.fromisoformat(str(receipt["weekStart"])),
            status=str(receipt["status"]),
            version=int(receipt["version"]),
            reason=str(receipt["reason"]),
            backup_path=self._fulfill_backup_obligation(command_key),
            idempotent=idempotent,
            share_ids_to_revoke=tuple(str(value) for value in receipt.get("shareIdsToRevoke", [])),
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

    def draft_cell_candidates(
        self,
        roster_week_id: int,
        cell_key: str,
    ) -> list[dict[str, object]]:
        """Return candidates for an assigned or currently vacant stable cell."""

        day, post, slot_index = _parse_cell_key(cell_key)
        with self._session() as session:
            week = self._week_or_error(session, roster_week_id)
            if week.status != "draft":
                raise WorkflowError("Manual changes are available only for a draft roster.")
            existing = session.scalar(
                select(RosterAssignmentRecord).where(
                    RosterAssignmentRecord.roster_week_id == roster_week_id,
                    RosterAssignmentRecord.day == day.name,
                    RosterAssignmentRecord.post_code == post.name,
                    RosterAssignmentRecord.slot_index == slot_index,
                )
            )
            probe = existing or RosterAssignmentRecord(
                id=-1,
                roster_week_id=roster_week_id,
                day=day.name,
                post_code=post.name,
                slot_index=slot_index,
                prefect_id="__vacant__",
                prefect_name_snapshot="",
                prefect_role_snapshot=None,
                weight=duty_weight(post),
                status="active",
            )
            candidates = self._eligible_assignment_candidates(
                session,
                week,
                probe,
                include_same_day_assigned=True,
            )
            if week.assist_assignment_mode != LEGACY_FIXED_WEEKDAY or post is not DutyPost.ASSIST_IN_CHARGE:
                return candidates
            fixed_owner = self._required_legacy_assist_owners(
                session,
                week_start=week.week_start,
            ).get(day.name)
            if fixed_owner is None:
                return candidates
            return [candidate for candidate in candidates if candidate["id"] == fixed_owner]

    @fenced_workflow_write
    def apply_draft_patch(
        self,
        *,
        roster_week_id: int,
        expected_week_version: int,
        cell_edits: Iterable[DraftCellEdit] = (),
        day_edits: Iterable[DraftDayEdit] = (),
        reason: str | None = None,
        command_id: str | None = None,
    ) -> DraftPatchResult:
        """Apply one final-state draft patch under a single version claim.

        The whole matrix is changed before policy validation, so a swap is
        validated as one operator decision rather than two temporarily invalid
        writes. ``None`` is the only explicit vacancy value; an empty prefect
        identifier is rejected at this service boundary.
        """

        normalized_reason = (reason or "").strip()
        if len(normalized_reason) > 1000:
            raise WorkflowError("Draft patch reason is too long.")
        if expected_week_version < 1:
            raise WorkflowError("The reviewed draft version is invalid.")

        materialized_cells = tuple(cell_edits)
        materialized_days = tuple(day_edits)
        if not materialized_cells and not materialized_days:
            raise WorkflowError("Choose at least one draft cell or weekday to change.")

        parsed_cells: list[tuple[DraftCellEdit, SchoolDay, DutyPost, int]] = []
        seen_cells: set[str] = set()
        for edit in materialized_cells:
            day, post, slot_index = _parse_cell_key(edit.cell_key)
            stable_key = f"{day.name}:{post.name}:{slot_index}"
            if stable_key in seen_cells:
                raise WorkflowError("A draft patch cannot change the same cell twice.")
            if edit.replacement_prefect_id is not None and not edit.replacement_prefect_id.strip():
                raise WorkflowError(
                    "An empty prefect identifier is not a vacancy decision; choose a prefect or explicitly clear the cell."
                )
            seen_cells.add(stable_key)
            parsed_cells.append((edit, day, post, slot_index))

        normalized_days: list[tuple[DraftDayEdit, SchoolDay, str | None, str | None]] = []
        seen_days: set[SchoolDay] = set()
        for edit in materialized_days:
            day = _stable_school_day(edit.day)
            if day in seen_days:
                raise WorkflowError("A draft patch cannot change the same weekday twice.")
            reason_code = (edit.reason_code or "").strip() or None
            note = (edit.note or "").strip() or None
            if reason_code is not None and reason_code not in _DAY_CLOSURE_REASON_CODES:
                raise WorkflowError("A day closure must use a stable reason code.")
            if note is not None and len(note) > 1000:
                raise WorkflowError("A day closure note is too long.")
            seen_days.add(day)
            normalized_days.append((edit, day, reason_code, note))

        closing_days = {
            day for edit, day, _, _ in normalized_days if edit.closed
        }
        if any(day in closing_days for _, day, _, _ in parsed_cells):
            raise WorkflowError(
                "A cell cannot be assigned in the same patch which closes its weekday."
            )

        operation_type = "draft_patch_applied"
        operation_key = self._operation_command_id(operation_type, command_id)
        operation_payload = {
            "rosterWeekId": roster_week_id,
            "expectedWeekVersion": expected_week_version,
            "cellEdits": [
                {
                    "cellKey": f"{day.name}:{post.name}:{slot_index}",
                    "replacementPrefectId": edit.replacement_prefect_id,
                }
                for edit, day, post, slot_index in parsed_cells
            ],
            "dayEdits": [
                {
                    "day": day.name,
                    "closed": edit.closed,
                    "reasonCode": reason_code,
                    "note": note,
                }
                for edit, day, reason_code, note in normalized_days
            ],
            "reason": normalized_reason,
        }

        receipt: dict[str, object] | None = None
        replayed = False
        with self._session() as session:
            self._begin_serialized_write(session)
            command, receipt = self._claim_operation_command(
                session,
                operation_type=operation_type,
                command_id=operation_key,
                payload=operation_payload,
            )
            if receipt is not None:
                replayed = True
                session.rollback()
            else:
                week = self._week_or_error(session, roster_week_id)
                if week.status != "draft":
                    raise WorkflowError("Only a draft roster can be changed.")
                if week.version != expected_week_version:
                    raise WorkflowConflictError(
                        "This draft changed in another browser. Refresh and review the latest version before saving."
                    )
                now = self._now()
                claim = session.execute(
                    update(RosterWeekRecord)
                    .where(
                        RosterWeekRecord.id == roster_week_id,
                        RosterWeekRecord.status == "draft",
                        RosterWeekRecord.version == expected_week_version,
                    )
                    .values(version=expected_week_version + 1, updated_at=now)
                )
                if claim.rowcount != 1:
                    raise WorkflowConflictError(
                        "This draft changed in another browser. Refresh and review the latest version before saving."
                    )
                session.refresh(week)

                closure_rows = session.scalars(
                    select(RosterDayClosureRecord).where(
                        RosterDayClosureRecord.roster_week_id == roster_week_id
                    )
                ).all()
                closures = {SchoolDay[row.day]: row for row in closure_rows}
                for edit, day, reason_code, note in normalized_days:
                    existing = closures.get(day)
                    if edit.closed:
                        if existing is None:
                            existing = RosterDayClosureRecord(
                                roster_week_id=roster_week_id,
                                day=day.name,
                                reason_code=reason_code,
                                note=note,
                                created_at=now,
                                updated_at=now,
                            )
                            session.add(existing)
                            closures[day] = existing
                        else:
                            existing.reason_code = reason_code
                            existing.note = note
                            existing.updated_at = now
                        session.execute(
                            delete(RosterAssignmentRecord).where(
                                RosterAssignmentRecord.roster_week_id == roster_week_id,
                                RosterAssignmentRecord.day == day.name,
                            )
                        )
                    elif existing is not None:
                        session.delete(existing)
                        closures.pop(day, None)

                requested_prefect_ids = {
                    edit.replacement_prefect_id
                    for edit, _, _, _ in parsed_cells
                    if edit.replacement_prefect_id is not None
                }
                prefect_records = {
                    record.id: record
                    for record in session.scalars(
                        select(PrefectRecord).where(
                            PrefectRecord.id.in_(requested_prefect_ids),
                            PrefectRecord.active.is_(True),
                        )
                    ).all()
                } if requested_prefect_ids else {}
                if set(prefect_records) != requested_prefect_ids:
                    raise WorkflowError("A selected prefect no longer exists or is inactive.")

                assignment_rows = self._assignment_rows(session, roster_week_id)
                rows_by_cell = {
                    (SchoolDay[row.day], DutyPost[row.post_code], row.slot_index): row
                    for row in assignment_rows
                }
                for edit, day, post, slot_index in parsed_cells:
                    if day in closures:
                        raise WorkflowError("A closed weekday cannot contain an assignment.")
                    key = (day, post, slot_index)
                    existing = rows_by_cell.get(key)
                    replacement_id = edit.replacement_prefect_id
                    if replacement_id is None:
                        if existing is not None:
                            session.delete(existing)
                            rows_by_cell.pop(key, None)
                        continue
                    replacement = prefect_records[replacement_id]
                    if existing is None:
                        existing = RosterAssignmentRecord(
                            roster_week_id=roster_week_id,
                            day=day.name,
                            post_code=post.name,
                            slot_index=slot_index,
                            prefect_id=replacement.id,
                            prefect_name_snapshot=replacement.name_zh,
                            prefect_role_snapshot=replacement.role_code,
                            weight=duty_weight(post),
                            status="active",
                        )
                        session.add(existing)
                        rows_by_cell[key] = existing
                    else:
                        existing.prefect_id = replacement.id
                        existing.prefect_name_snapshot = replacement.name_zh
                        existing.prefect_role_snapshot = replacement.role_code
                        existing.weight = duty_weight(post)
                        existing.status = "active"

                final_closed_days = tuple(sorted(closures, key=int))
                session.flush()
                final_rows = self._assignment_rows(session, roster_week_id)
                self._validate_persisted_assignments(
                    session,
                    final_rows,
                    week_start=week.week_start,
                    closed_days=final_closed_days,
                    require_complete=False,
                )

                if week.assist_assignment_mode == LEGACY_FIXED_WEEKDAY:
                    fixed_owners = self._required_legacy_assist_owners(
                        session,
                        week_start=week.week_start,
                    )
                    for row in final_rows:
                        if row.status != "active" or row.post_code != DutyPost.ASSIST_IN_CHARGE.name:
                            continue
                        fixed_owner = fixed_owners.get(row.day)
                        if fixed_owner is not None and row.prefect_id != fixed_owner:
                            raise WorkflowError(
                                "Legacy fixed-weekday mode requires the weekday's assigned Assistant Head Study Prefect."
                            )

                receipt = {
                    "rosterWeekId": roster_week_id,
                    "version": week.version,
                    "changedCellCount": len(parsed_cells),
                    "closedDays": [day.name for day in final_closed_days],
                }
                self._audit(
                    session,
                    operation_type,
                    roster_week_id,
                    {
                        "cellKeys": [
                            f"{day.name}:{post.name}:{slot_index}"
                            for _, day, post, slot_index in parsed_cells
                        ],
                        "dayEdits": [
                            {"day": day.name, "closed": edit.closed, "reasonCode": reason_code}
                            for edit, day, reason_code, _ in normalized_days
                        ],
                        "reason": normalized_reason,
                        "version": week.version,
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
        return DraftPatchResult(
            roster_week_id=int(receipt["rosterWeekId"]),
            version=int(receipt["version"]),
            changed_cell_count=int(receipt["changedCellCount"]),
            closed_days=tuple(str(day) for day in receipt.get("closedDays", [])),
            backup_path=self._fulfill_backup_obligation(operation_key),
            idempotent=replayed,
        )

    @fenced_workflow_write
    def update_draft_assignment(
        self,
        *,
        roster_week_id: int,
        assignment_id: int,
        replacement_prefect_id: str,
        reason: str | None = None,
        expected_week_version: int | None = None,
        command_id: str | None = None,
    ) -> DraftAssignmentUpdateResult:
        """Apply an auditable, policy-validated manual draft change without posting fairness weight."""
        normalized_reason = (reason or "").strip()
        operation_type = "draft_assignment_changed"
        command_key = self._operation_command_id(operation_type, command_id)
        receipt: dict[str, object] | None = None
        with self._session() as session:
            self._begin_serialized_write(session)
            command, receipt = self._claim_operation_command(
                session,
                operation_type=operation_type,
                command_id=command_key,
                payload={
                    "rosterWeekId": roster_week_id,
                    "assignmentId": assignment_id,
                    "replacementPrefectId": replacement_prefect_id,
                    "reason": normalized_reason,
                    "expectedWeekVersion": expected_week_version,
                },
            )
            if receipt is not None:
                session.rollback()
            else:
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
                self._validate_persisted_assignments(
                    session,
                    self._assignment_rows(session, week.id),
                    week_start=week.week_start,
                    closed_days=self._closed_days(session, week.id),
                )
                receipt = {
                    "rosterWeekId": week.id,
                    "assignmentId": assignment.id,
                    "version": week.version,
                }
                self._audit(
                    session,
                    operation_type,
                    week.id,
                    {
                        "assignmentId": assignment.id,
                        "fromPrefectId": original_prefect_id,
                        "fromPrefectName": original_name,
                        "toPrefectId": replacement.id,
                        "toPrefectName": replacement.name_zh,
                        "reason": normalized_reason,
                        "version": week.version,
                    },
                )
                self._commit_operation_command(
                    session,
                    record=command,
                    result=receipt,
                    roster_week_id=week.id,
                )
                session.commit()
        assert receipt is not None
        return DraftAssignmentUpdateResult(
            roster_week_id=int(receipt["rosterWeekId"]),
            assignment_id=int(receipt["assignmentId"]),
            version=int(receipt["version"]),
            backup_path=self._fulfill_backup_obligation(command_key),
        )

    @fenced_workflow_write
    def apply_leave_adjustment(
        self,
        *,
        roster_week_id: int,
        assignment_id: int,
        replacement_prefect_id: str | None,
        reason: str | None = None,
        command_id: str | None = None,
        expected_week_version: int | None = None,
    ) -> LeaveAdjustmentResult:
        normalized_reason = (reason or "").strip()
        operation_type = "leave_adjusted"
        operation_id = self._operation_command_id(operation_type, command_id)
        request_fingerprint = self._leave_adjustment_request_fingerprint(
            roster_week_id=roster_week_id,
            assignment_id=assignment_id,
            replacement_prefect_id=replacement_prefect_id,
            reason=normalized_reason,
        )
        operation_payload = {
            "rosterWeekId": roster_week_id,
            "assignmentId": assignment_id,
            "replacementPrefectId": replacement_prefect_id,
            "reason": normalized_reason,
        }
        receipt: dict[str, object] | None = None
        replayed = False
        with self._session() as session:
            self._begin_serialized_write(session)
            try:
                command, receipt = self._claim_operation_command(
                    session,
                    operation_type=operation_type,
                    command_id=operation_id,
                    payload=operation_payload,
                )
            except WorkflowConflictError as error:
                if "different work" in str(error):
                    raise WorkflowConflictError(
                        "This leave-adjustment command ID was already used for a different request."
                    ) from error
                raise
            if receipt is not None:
                replayed = True
                session.rollback()
            else:
                week = self._week_or_error(session, roster_week_id)
                assignment = self._assignment_or_error(session, roster_week_id, assignment_id)
                assignment_weight = float(assignment.weight)
                duplicate = session.scalar(
                    select(LeaveAdjustmentRecord).where(LeaveAdjustmentRecord.command_id == operation_id)
                )
                if duplicate is not None:
                    legacy_result = self._leave_adjustment_replay_result(
                        duplicate,
                        roster_week_id=roster_week_id,
                        assignment_id=assignment_id,
                        replacement_prefect_id=replacement_prefect_id,
                        reason=normalized_reason,
                        request_fingerprint=request_fingerprint,
                        assignment_weight=assignment_weight,
                    )
                    share_ids_to_revoke = self._queue_obsolete_external_share_revocations(
                        session,
                        roster_week_id=roster_week_id,
                        current_version=legacy_result.version,
                        invalidated_by="roster_adjusted",
                        now=self._now(),
                    )
                    receipt = {
                        "rosterWeekId": legacy_result.roster_week_id,
                        "assignmentId": legacy_result.assignment_id,
                        "status": legacy_result.status,
                        "version": legacy_result.version,
                        "originalPrefectName": legacy_result.original_prefect_name,
                        "replacementPrefectName": legacy_result.replacement_prefect_name,
                        "weight": legacy_result.weight,
                        "shareIdsToRevoke": share_ids_to_revoke,
                    }
                    replayed = True
                    self._commit_operation_command(
                        session,
                        record=command,
                        result=receipt,
                        roster_week_id=roster_week_id,
                    )
                    session.commit()
                else:
                    requested_version = week.version if expected_week_version is None else expected_week_version
                    if week.status != "published":
                        raise WorkflowError("Post-publication adjustments require a published roster.")
                    if week.version != requested_version:
                        raise WorkflowConflictError(
                            "This roster was updated in another tab. Refresh it and review the adjustment again."
                        )
                    if assignment.status != "active" or assignment.prefect_id is None:
                        raise WorkflowError("This assignment is no longer active.")
                    original = session.get(PrefectRecord, assignment.prefect_id)
                    if original is None:
                        raise WorkflowError("The original prefect no longer exists.")
                    candidates = {
                        candidate["id"]
                        for candidate in self._eligible_assignment_candidates(session, week, assignment)
                    }
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
                        raise WorkflowConflictError(
                            "This roster was updated in another tab. Refresh it and review the adjustment again."
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
                    share_ids_to_revoke = self._queue_obsolete_external_share_revocations(
                        session,
                        roster_week_id=roster_week_id,
                        current_version=requested_version + 1,
                        invalidated_by="roster_adjusted",
                        now=now,
                    )
                    receipt = {
                        "rosterWeekId": roster_week_id,
                        "assignmentId": assignment_id,
                        "status": status,
                        "version": requested_version + 1,
                        "originalPrefectName": original_name,
                        "replacementPrefectName": replacement_name,
                        "weight": assignment_weight,
                        "shareIdsToRevoke": share_ids_to_revoke,
                    }
                    self._audit(
                        session,
                        operation_type,
                        week.id,
                        {
                            "assignmentId": assignment.id,
                            "status": status,
                            "commandId": operation_id,
                            "shareRevocationCount": len(share_ids_to_revoke),
                        },
                    )
                    self._assert_fairness_reconciled(session)
                    self._commit_operation_command(
                        session,
                        record=command,
                        result=receipt,
                        roster_week_id=week.id,
                    )
                    session.commit()
        assert receipt is not None
        backup_path = self._fulfill_backup_obligation(operation_id)
        return LeaveAdjustmentResult(
            roster_week_id=int(receipt["rosterWeekId"]),
            assignment_id=int(receipt["assignmentId"]),
            status=str(receipt["status"]),
            backup_path=None if replayed else backup_path,
            version=int(receipt["version"]),
            idempotent=replayed,
            original_prefect_name=str(receipt["originalPrefectName"]),
            replacement_prefect_name=(
                str(receipt["replacementPrefectName"])
                if receipt.get("replacementPrefectName") is not None
                else None
            ),
            weight=float(receipt["weight"]),
            share_ids_to_revoke=tuple(str(value) for value in receipt.get("shareIdsToRevoke", [])),
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
        assignment_weight: float,
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
            roster_week_id=duplicate.roster_week_id,
            assignment_id=duplicate.assignment_id,
            status=duplicate.status,
            backup_path=None,
            version=duplicate.committed_version,
            idempotent=True,
            original_prefect_name=duplicate.original_prefect_name,
            replacement_prefect_name=duplicate.replacement_prefect_name,
            weight=assignment_weight,
        )

    @staticmethod
    def _roster_week_output(
        row: RosterWeekRecord,
        closed_days: Iterable[SchoolDay] = (),
    ) -> dict[str, object]:
        return {
            "id": row.id,
            "weekStart": row.week_start,
            "status": row.status,
            "version": row.version,
            "historyPriorityMultiplier": row.history_priority_multiplier,
            "assistAssignmentMode": row.assist_assignment_mode,
            "generatedAt": row.generated_at,
            "publishedAt": row.published_at,
            "withdrawnAt": row.withdrawn_at,
            "withdrawalReason": row.withdrawal_reason,
            "closedDays": [day.name for day in closed_days],
        }

    def latest_roster_week(self) -> dict[str, object] | None:
        """Return only the newest week for dashboards and next-action routing."""
        with self._session() as session:
            row = session.scalar(
                select(RosterWeekRecord)
                .order_by(RosterWeekRecord.week_start.desc(), RosterWeekRecord.id.desc())
                .limit(1)
            )
            return (
                self._roster_week_output(row, self._closed_days(session, row.id))
                if row is not None
                else None
            )

    def roster_week_history(
        self,
        *,
        page: int = 1,
        page_size: int = 24,
    ) -> list[dict[str, object]]:
        """Return one bounded history page in stable newest-first order."""
        if page < 1:
            raise WorkflowError("Roster history page must be at least one.")
        if page_size < 1 or page_size > 100:
            raise WorkflowError("Roster history page size must be between 1 and 100.")
        with self._session() as session:
            rows = session.scalars(
                select(RosterWeekRecord)
                .order_by(RosterWeekRecord.week_start.desc(), RosterWeekRecord.id.desc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            ).all()
            closures = self._closed_days_by_week(session, (row.id for row in rows))
            return [self._roster_week_output(row, closures.get(row.id, ())) for row in rows]

    def roster_weeks(self) -> list[dict[str, object]]:
        """Compatibility read for bounded-data services; UI uses history/latest APIs."""
        with self._session() as session:
            rows = session.scalars(
                select(RosterWeekRecord).order_by(
                    RosterWeekRecord.week_start.desc(),
                    RosterWeekRecord.id.desc(),
                )
            ).all()
            closures = self._closed_days_by_week(session, (row.id for row in rows))
            return [self._roster_week_output(row, closures.get(row.id, ())) for row in rows]

    def roster_week(self, roster_week_id: int) -> dict[str, object]:
        with self._session() as session:
            row = self._week_or_error(session, roster_week_id)
            return self._roster_week_output(row, self._closed_days(session, row.id))

    def week_schedule_overrides(self, roster_week_id: int) -> WeekScheduleOverrides:
        with self._session() as session:
            self._week_or_error(session, roster_week_id)
            return WeekScheduleOverrides(
                closed_days=tuple(
                    day.name for day in self._closed_days(session, roster_week_id)
                )
            )

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

    def roster_schedule_snapshot(
        self, roster_week_id: int
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        """Read one versioned schedule from a single database transaction."""
        with self._session() as session:
            week = self._week_or_error(session, roster_week_id)
            assignments = self._assignment_rows(session, roster_week_id)
            closed_days = self._closed_days(session, roster_week_id)
            return (
                {
                    "id": week.id,
                    "weekStart": week.week_start,
                    "status": week.status,
                    "version": week.version,
                    "historyPriorityMultiplier": week.history_priority_multiplier,
                    "assistAssignmentMode": week.assist_assignment_mode,
                    "generatedAt": week.generated_at,
                    "publishedAt": week.published_at,
                    "closedDays": [day.name for day in closed_days],
                    "dayClosures": self._closure_outputs(session, roster_week_id),
                },
                [
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
                    for row in assignments
                ],
            )

    def generation_requirements(
        self,
        week_start: date,
        *,
        closed_days: Iterable[SchoolDay | str] = (),
    ) -> list[dict[str, object]]:
        """Expose every required weekly slot and its currently eligible pool before generation."""
        self._require_monday(week_start)
        normalized_closed_days = frozenset(_normalized_closed_days(closed_days))
        with self._session() as session:
            availability = self._availability_by_prefect(session)
            leave_days = self._leave_days_for_week(session, week_start)
            prefects = self._active_prefect_records(session)
            requirements: list[dict[str, object]] = []
            for day in SchoolDay:
                if day in normalized_closed_days:
                    continue
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
