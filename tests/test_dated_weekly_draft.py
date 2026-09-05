"""Fictional people only; exercise the dated draft Module's public Interface."""
from dataclasses import replace
from datetime import date, timedelta
import json

import pytest

from roster_core.dated_draft import (
    DraftError, decode_draft, edit_draft, encode_draft, generate_draft,
)
from roster_core.generator import generate_weekly_roster
from roster_core.models import Prefect
from roster_core.policy_settings import PolicyRevision
from roster_policy import AssistAssignmentMode, DutyPost, PrefectRole, SchoolDay
from roster_policy.configurable import (
    BusinessId, DutyTimes, ScheduleExceptions, SeatKey, TimeWindow, WeeklyPolicy,
    default_weekly_policy,
)

MONDAY = date(2026, 9, 7)


def people(count=16):
    names = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    return tuple(Prefect(
        id=f"fictional-{index:03}", name="測" + names[index // 10] + names[index % 10],
        form="F.4", class_name="A", role=(PrefectRole.ASSISTANT_HEAD if index < 5 else PrefectRole.STUDY_PREFECT),
        available_days=frozenset(SchoolDay), history_weight=0,
    ) for index in range(count))


def policy(**changes):
    return PolicyRevision(2026, 1, WeeklyPolicy(tuple(
        replace(post, **changes.get(post.business.value, {}))
        for post in default_weekly_policy().businesses
    )))


def test_default_keeps_thirty_cells_and_disabled_f1_with_eighty_minutes():
    draft = generate_draft(policy(), MONDAY, people())
    assert len(draft.cells) == 30
    assert all(row.service_minutes == 80 for row in draft.schedule.rows)
    assert [row.room for row in draft.schedule.rows] == [None, "407", "406", "406", "202", "202"]
    assert {cell.state for cell in draft.cells if cell.key.business is BusinessId.FORM_1_STUDY_GROUP} == {"business_closed"}
    assert all(cell.state == "assigned" for cell in draft.cells if cell.key.business is not BusinessId.FORM_1_STUDY_GROUP)
    assert decode_draft(encode_draft(draft)) == draft
    assert encode_draft(generate_draft(policy(), MONDAY, people())) == encode_draft(draft)


@pytest.mark.parametrize("mode", list(AssistAssignmentMode))
def test_single_assist_seat_retains_existing_mode_exactly(mode):
    prefects = people()
    legacy = generate_weekly_roster(list(prefects), assist_assignment_mode=mode, assist_rotation_key=MONDAY.isoformat())
    draft = generate_draft(policy(), MONDAY, prefects, assist_mode=mode)
    actual = {cell.key.duty_date.weekday(): cell.prefect_id for cell in draft.cells if cell.key.business is BusinessId.ASSIST_IN_CHARGE}
    assert actual == {int(item.day): item.prefect_id for item in legacy if item.post is DutyPost.ASSIST_IN_CHARGE}


def test_twenty_rows_and_custom_minutes_do_not_use_room_enums():
    times = DutyTimes(TimeWindow("15:00", "16:37"), TimeWindow("15:00", "16:37"))
    selected = policy(study_room={"room": "自修室甲", "capacity": 15, "times": times})
    draft = generate_draft(selected, MONDAY, people(60))
    assert len(draft.schedule.rows) == 20 and len(draft.cells) == 100
    assert all(row.service_minutes == 97 for row in draft.schedule.rows if row.business is BusinessId.STUDY_ROOM)
    assert all(cell.state in {"assigned", "business_closed"} for cell in draft.cells)


def test_missing_people_produce_explained_vacancies_not_forbidden_assignments():
    draft = generate_draft(policy(), MONDAY, ())
    assert {cell.state for cell in draft.cells} == {"vacant", "business_closed"}
    assert all(cell.reason for cell in draft.cells if cell.state == "vacant")


def test_edit_preserves_rules_and_rejects_duplicate_and_consecutive_assignments():
    draft = generate_draft(policy(), MONDAY, people())
    monday = [cell for cell in draft.cells if cell.key.duty_date == MONDAY and cell.state == "assigned"]
    with pytest.raises(DraftError):
        edit_draft(draft, {monday[2].key: monday[1].prefect_id})
    empty = edit_draft(draft, {monday[1].key: None})
    assert next(cell for cell in empty.cells if cell.key == monday[1].key).reason == "operator_vacancy"
    assert edit_draft(empty, {monday[1].key: monday[1].prefect_id}) == draft
    tuesday = SeatKey(MONDAY + timedelta(days=1), BusinessId.STUDY_ROOM, 1)
    with pytest.raises(DraftError):
        edit_draft(draft, {tuesday: monday[1].prefect_id})


def test_closed_day_and_external_occupancy_are_constraints():
    selected = ScheduleExceptions(closed_dates=(MONDAY,))
    draft = generate_draft(policy(), MONDAY, people(), exceptions=selected,
                           occupied=(("fictional-005", MONDAY + timedelta(days=1)),))
    assert all(cell.state == "day_closed" for cell in draft.cells if cell.key.duty_date == MONDAY)
    assert not any(cell.prefect_id == "fictional-005" and cell.key.duty_date == MONDAY + timedelta(days=1) for cell in draft.cells)


def test_multiple_assist_seats_fail_explicitly_until_mode_contract_is_supported():
    with pytest.raises(DraftError, match="Assist.*capacity"):
        generate_draft(policy(assist_in_charge={"capacity": 2}), MONDAY, people())


@pytest.mark.parametrize("raw", ['{"schemaVersion":1,"schemaVersion":1}', '{"x":NaN}', '[]'])
def test_ambiguous_or_invalid_documents_fail(raw):
    with pytest.raises(DraftError):
        decode_draft(raw)


def test_edit_refreshes_live_eligibility_and_can_clear_a_now_inactive_person():
    draft = generate_draft(policy(), MONDAY, people())
    person_id = next(cell.prefect_id for cell in draft.cells if cell.key.business is BusinessId.STUDY_ROOM)
    active = tuple(person for person in draft.people if person.id != person_id)
    with pytest.raises(DraftError):
        edit_draft(draft, {}, people=active)
    changes = {cell.key: None for cell in draft.cells if cell.prefect_id == person_id}
    result = edit_draft(draft, changes, people=active)
    assert all(cell.prefect_id != person_id for cell in result.cells)
    added = replace(people()[5], id="new-fictional", name="測新甲")
    target = next(iter(changes))
    result = edit_draft(result, {target: added.id}, people=(*active, added))
    assert next(cell for cell in result.cells if cell.key == target).prefect_name == added.name


@pytest.mark.parametrize("mutation", ["minutes", "date", "row", "cell", "name", "policy", "type", "unknown"])
def test_readback_rejects_semantically_corrupt_full_snapshot(mutation):
    raw = json.loads(encode_draft(generate_draft(policy(), MONDAY, people())))
    if mutation == "minutes":
        raw["rows"][1]["minutes"] = 81
    elif mutation == "date":
        raw["dates"][1] = "2026-09-10"
    elif mutation == "row":
        raw["rows"].pop()
    elif mutation == "cell":
        raw["cells"].pop()
    elif mutation == "name":
        raw["cells"][0]["name"] = "測錯甲"
    elif mutation == "policy":
        raw["policyRef"][0] = True
    elif mutation == "type":
        raw["cells"][0]["key"][2] = True
    else:
        raw["unsupported"] = "ignored?"
    with pytest.raises(DraftError):
        decode_draft(json.dumps(raw))


def test_search_budget_returns_reviewable_partial_result(monkeypatch):
    import roster_core.dated_draft as module
    monkeypatch.setattr(module, "SEARCH_NODE_LIMIT", 1)
    draft = generate_draft(policy(study_room={"capacity": 15}), MONDAY, people(8))
    assert any(cell.state == "vacant" for cell in draft.cells)
    module.validate_draft(draft)
