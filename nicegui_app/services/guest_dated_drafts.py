"""Ordinary draft Adapter over the existing bounded Guest workspace."""
from copy import deepcopy
from datetime import date, timedelta
import hashlib

from roster_core.dated_draft import accepted_assist_ownership, decode_draft, edit_draft, encode_draft, generate_draft
from roster_core.command_identity import operation_fingerprint
from roster_core.policy_settings import PolicySettings, PolicyVersionConflict
from roster_policy import AssistAssignmentMode, SchoolDay
from roster_policy.configurable import BusinessId, ScheduleExceptions, SeatKey
from roster_policy.policy_codec import encode_weekly_policy
from nicegui_app.services.dated_draft_types import DatedDraftCommandResult, DatedDraftSnapshot, draft_identity, draft_version, edit_payload, exception_payload
from nicegui_app.services.guest_policy import GuestPolicyRepository, guest_policy_command_id, validate_policy_state
from nicegui_app.services.workflow_types import WorkflowConflictError, WorkflowError


def validate_draft_state(state):
    payload = state.get("datedDrafts", {})
    if type(payload) is not dict:
        raise WorkflowError("Guest dated drafts require a history mapping.")
    policies = validate_policy_state(state)["years"]
    weeks = set()
    for identity, documents in payload.items():
        draft_identity(identity)
        if type(documents) is not list or not documents:
            raise WorkflowError("Guest dated draft history is empty or invalid.")
        first = None
        for document in documents:
            draft = decode_draft(document)
            reference = draft.policy_ref
            record = policies.get(str(reference.year_start))
            if (encode_draft(draft) != document or record is None or reference.revision > len(record["revisions"])
                    or record["revisions"][reference.revision - 1] != encode_weekly_policy(reference.policy)):
                raise WorkflowError("Guest dated draft has an invalid immutable policy reference.")
            metadata = (reference.year_start, draft.schedule.dates[0])
            if first is not None and metadata != first:
                raise WorkflowError("A dated draft cannot change its year or week.")
            first = metadata
        if first[1] in weeks:
            raise WorkflowError("A week already has a dated draft.")
        weeks.add(first[1])
    return payload


def validate_draft_transition(before, after):
    old = validate_draft_state(before)
    new = validate_draft_state(after)
    for identity, documents in old.items():
        if new.get(identity, [])[:len(documents)] != documents:
            raise WorkflowError("Immutable Guest draft history cannot be removed or overwritten.")


def draft_reference_snapshot(state, reference):
    if type(reference) is not tuple or len(reference) != 2:
        raise WorkflowError("Guest dated draft receipt is invalid.")
    identity, version = reference
    draft_identity(identity)
    draft_version(version)
    documents = validate_draft_state(state).get(identity)
    if documents is None or version > len(documents):
        raise WorkflowError("Guest dated draft revision was not found.")
    return DatedDraftSnapshot(identity, version, decode_draft(documents[version - 1]))


class GuestDatedDraftMixin:
    def dated_draft_command_result(self, *, command_id):
        self._require_read()
        command_id = guest_policy_command_id(command_id)
        if not self._bound:
            raise WorkflowError("The demo workspace is still connecting.")
        view = self._view()
        receipt = self._registry.command_result(session_id=view.session_id, workspace_id=view.workspace_id,
                                                tab_id=view.tab_id, command_id=command_id)
        if receipt is None or receipt.draft_result_reference is None:
            return None
        return DatedDraftCommandResult(command_id, draft_reference_snapshot(receipt.state, receipt.draft_result_reference),
                                       "not_applicable", True)

    def dated_draft_snapshot(self, schedule_id: str, *, version: int | None = None):
        self._require_read()
        draft_identity(schedule_id)
        state = self._state()
        documents = validate_draft_state(state).get(schedule_id)
        if documents is None:
            raise WorkflowError("Guest dated draft was not found.")
        return draft_reference_snapshot(state, (schedule_id, len(documents) if version is None else version))

    def _guest_dated_inputs(self, state, monday):
        people = tuple(sorted(self._active_prefects(state), key=lambda person: person.id))
        ids = {person.id for person in people}
        leaves = tuple(sorted((identity, monday + timedelta(days=int(day)))
                              for identity, days in self._leave_days(state, monday).items() for day in days if identity in ids))
        occupied = tuple(sorted({(row["prefectId"], monday + timedelta(days=int(SchoolDay[row["day"]])))
                                 for week in state.get("weeks", [])
                                 if week["weekStart"] == monday.isoformat() and week["status"] == "published"
                                 for row in week.get("assignments", [])
                                 if row["status"] == "active" and row.get("prefectId") in ids}))
        return people, leaves, occupied

    def _guest_generate_dated(self, state, reference, monday, *, exceptions, assist_mode, history_multiplier):
        people, leaves, occupied = self._guest_dated_inputs(state, monday)
        previous = self._previous_assist_weekday_assignments(state, monday)
        legacy_date = max((str(week["weekStart"]) for week in state.get("weeks", [])
                           if week.get("status") in {"draft", "published"} and str(week["weekStart"]) < monday.isoformat()), default=None)
        prior = sorted((decode_draft(documents[-1]) for documents in validate_draft_state(state).values()),
                       key=lambda draft: draft.schedule.dates[0])
        prior = [draft for draft in prior if draft.schedule.dates[0] < monday]
        if prior and (legacy_date is None or prior[-1].schedule.dates[0].isoformat() >= legacy_date):
            previous = {SchoolDay(cell.key.duty_date.weekday()): cell.prefect_id for cell in prior[-1].cells
                        if cell.key.business is BusinessId.ASSIST_IN_CHARGE and cell.state == "assigned"}
        draft = generate_draft(reference, monday, people, leaves=leaves, occupied=occupied, exceptions=exceptions,
                               assist_mode=assist_mode, history_multiplier=history_multiplier, previous_assist=previous)
        draft, ownership = accepted_assist_ownership(draft)
        for person in state.get("prefects", []):
            if person["id"] in ownership:
                person["fixedGeneralDuty"] = ownership[person["id"]]
                person["version"] = int(person.get("version", 1)) + 1
        return draft

    def create_dated_weekly_draft(self, year_start, policy_revision, week_start, *, command_id,
                                  exceptions=ScheduleExceptions(), assist_mode=AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
                                  history_multiplier=1.0):
        self._require_modify()
        if type(week_start) is not date or week_start.weekday() != 0 or not isinstance(assist_mode, AssistAssignmentMode):
            raise WorkflowError("Select an actual Monday and supported Assist mode.")
        payload = {"year": year_start, "policyRevision": policy_revision, "monday": week_start.isoformat(),
                   "exceptions": exception_payload(exceptions), "assistMode": assist_mode.value, "multiplier": history_multiplier}

        def create(view, state):
            reference = PolicySettings(GuestPolicyRepository(self._registry, view, self._commit)).current(year_start)
            if type(policy_revision) is not int or reference.revision != policy_revision:
                raise PolicyVersionConflict("Review the current policy before generating.")
            if any(decode_draft(documents[0]).schedule.dates[0] == week_start for documents in validate_draft_state(state).values()):
                raise WorkflowConflictError("This week already has a dated draft; reopen it.")
            identity = "DRAFT-" + hashlib.sha256(guest_policy_command_id(command_id).encode("utf-8")).hexdigest()[:32]
            draft = self._guest_generate_dated(state, reference, week_start, exceptions=exceptions,
                                               assist_mode=assist_mode, history_multiplier=history_multiplier)
            state.setdefault("datedDrafts", {})[identity] = [encode_draft(draft)]
            return identity, 1

        return self._run_guest_dated("dated_draft_created", command_id, payload, create, expected_version=0)

    def regenerate_dated_draft(self, schedule_id, *, expected_version, command_id):
        return self._change_guest_dated(schedule_id, expected_version, command_id, "dated_draft_regenerated")

    def adopt_dated_draft_policy(self, schedule_id, policy_revision, *, expected_version, command_id):
        draft_version(policy_revision)
        return self._change_guest_dated(schedule_id, expected_version, command_id, "dated_draft_policy_adopted", policy_revision=policy_revision)

    def edit_dated_draft(self, schedule_id, changes, *, expected_version, command_id):
        edit_payload(changes)
        return self._change_guest_dated(schedule_id, expected_version, command_id, "dated_draft_edited", changes=changes)

    def _change_guest_dated(self, identity, expected, command_id, operation, *, policy_revision=None, changes=None):
        self._require_modify()
        draft_identity(identity)
        draft_version(expected)
        changes = dict(changes) if changes is not None else None
        payload = {"scheduleId": identity, "expectedVersion": expected, "policyRevision": policy_revision,
                   "changes": edit_payload(changes) if changes is not None else None}

        def change(view, state):
            documents = validate_draft_state(state).get(identity)
            if documents is None or len(documents) != expected:
                raise WorkflowConflictError("This dated draft changed; reload before editing.")
            old = decode_draft(documents[-1])
            reference = old.policy_ref
            if policy_revision is not None:
                reference = PolicySettings(GuestPolicyRepository(self._registry, view, self._commit)).current(reference.year_start)
                if reference.revision != policy_revision:
                    raise PolicyVersionConflict("Review the current policy before explicit adoption.")
            if changes is not None:
                people, leaves, occupied = self._guest_dated_inputs(state, old.schedule.dates[0])
                draft = edit_draft(old, changes, people=people, leaves=leaves, occupied=occupied)
            else:
                draft = self._guest_generate_dated(state, reference, old.schedule.dates[0], exceptions=old.exceptions,
                                                   assist_mode=old.assist_mode, history_multiplier=old.history_multiplier)
            documents.append(encode_draft(draft))
            return identity, expected + 1

        return self._run_guest_dated(operation, command_id, payload, change, expected_version=expected)

    def _run_guest_dated(self, operation, command_id, payload, action, *, expected_version):
        self._require_modify()
        command_id = guest_policy_command_id(command_id)
        if not self._bound:
            raise WorkflowError("The demo workspace is still connecting.")
        view = self._view()
        digest = operation_fingerprint(operation, payload)
        replay = self._registry.replay_command(session_id=view.session_id, workspace_id=view.workspace_id,
                                               tab_id=view.tab_id, command_id=command_id, request_digest=digest)
        if replay is None:
            state = deepcopy(view.state)
            reference = action(view, state)
            replay = self._commit(view, state, operation, command_id=command_id, request_digest=digest,
                                  draft_result_reference=reference)
        snapshot = draft_reference_snapshot(replay.state, replay.draft_result_reference)
        expected_id = payload.get("scheduleId", "DRAFT-" + hashlib.sha256(command_id.encode("utf-8")).hexdigest()[:32])
        if snapshot.schedule_id != expected_id or snapshot.version != expected_version + 1:
            raise WorkflowError("Guest dated receipt does not identify its original revision.")
        return DatedDraftCommandResult(command_id, snapshot, "not_applicable", replay.replayed)
