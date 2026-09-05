"""Phone adjustment choices follow the published, canonical cell state."""
import pytest

from nicegui_app.services.roster_document import capture_roster_document
from nicegui_app.ui.page_routes import weekly
from tests.test_roster_document import Source


def test_open_vacancy_is_selectable_but_closed_day_is_not():
    source = Source()
    source.assignments[0].update(status="vacant", prefectId=None, prefectName=None)
    source.week["closedDays"] = ["TUESDAY"]
    document = capture_roster_document(source, 42)
    targets = weekly._published_adjustment_targets(document)
    assert str(source.assignments[0]["id"]) in targets
    assert targets[str(source.assignments[0]["id"])]["status"] == "vacant"
    assert all(item["day"] != "TUESDAY" for item in targets.values())
    source.week["status"] = "withdrawn"
    assert weekly._published_adjustment_targets(capture_roster_document(source, 42)) == {}


@pytest.mark.parametrize("status,choice,expected", (
    ("vacant", None, False), ("vacant", "", False),
    ("vacant", "__vacant__", False), ("vacant", "candidate", True),
    ("active", "__vacant__", True), ("active", "candidate", True),
    ("active", "unknown-person", False), ("unavailable", "candidate", False),
))
def test_adjustment_needs_explicit_eligible_person_or_meaningful_vacancy(status, choice, expected):
    target = {"status": status, "prefectId": None if status == "vacant" else "original"}
    assert weekly._adjustment_selection_complete(target, choice, {"candidate"}) is expected
    assert not weekly._adjustment_selection_complete(None, choice, {"candidate"})


@pytest.mark.parametrize("snapshot_name", (None, "VACANT"))
def test_vacancy_choice_uses_localized_state_not_persisted_sentinel(monkeypatch, snapshot_name):
    monkeypatch.setattr(weekly, "t", lambda key: "空缺" if key == "vacant" else key)
    monkeypatch.setattr(weekly, "day_label", lambda _day: "星期一")
    assert weekly._adjustment_target_label({
        "status": "vacant", "prefectName": snapshot_name, "day": "MONDAY",
        "postCode": "ROOM_302", "slotIndex": 1,
    }) == "星期一 | Room 302 Study Room | 空缺"
