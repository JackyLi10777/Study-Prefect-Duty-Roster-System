from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import date
from io import BytesIO

import pytest
from pypdf import PdfReader

from nicegui_app.services.roster_document import capture_roster_document
from nicegui_app.services.roster_export import render_roster_pdf
from nicegui_app.services.roster_image_export import render_roster_png_bundle
from nicegui_app.services.roster_presentation import DAY_ORDER, ROSTER_ROWS, RosterPresentationError
from roster_policy import is_room_open


class Source:
    def __init__(self):
        self.calls = 0
        self.week = dict(id=42, weekStart=date(2026, 9, 7), status="published", version=4)
        self.assignments = [
            dict(id=index * 6 + n + 1, day=day.name, postCode=row.post.name,
                 slotIndex=row.slot_index, prefectId=f"fiction-{index}-{n}",
                 prefectName="陳文", status="active")
            for index, day in enumerate(DAY_ORDER)
            for n, row in enumerate(ROSTER_ROWS) if is_room_open(row.post, day)
        ]

    def roster_schedule_snapshot(self, roster_week_id):
        self.calls += 1
        assert roster_week_id == 42
        return self.week, self.assignments


def test_document_freezes_one_read_and_all_renderers_use_it():
    source = Source()
    document = capture_roster_document(source, 42)
    source.week["version"] = 5
    source.assignments[0]["prefectName"] = "李文"
    pdf = render_roster_pdf(document, language="en")
    images = render_roster_png_bundle(document)
    assert source.calls == 1
    assert pdf.roster_version == images.roster_version == document.snapshot.version == 4
    assert "v4" in PdfReader(BytesIO(pdf.content)).pages[0].extract_text()
    assert document.presentation.rows[0].cells[0].prefect_name == "陳文"
    with pytest.raises(FrozenInstanceError):
        document.snapshot.version = 6
    with pytest.raises(TypeError):
        document.snapshot.assignments[0]["prefectName"] = "李文"


@pytest.mark.parametrize("malformation", ["missing", "duplicate", "invalid_status", "missing_name"])
def test_all_output_formats_share_strict_document_validation(malformation):
    source = Source()
    if malformation == "missing":
        source.assignments.pop(0)
    elif malformation == "duplicate":
        source.assignments.append(deepcopy(source.assignments[0]))
    elif malformation == "invalid_status":
        source.assignments[0]["status"] = "typo"
    else:
        source.assignments[0]["prefectName"] = ""
    with pytest.raises(RosterPresentationError):
        capture_roster_document(source, 42)


def test_closed_day_retains_underlying_assignments_without_becoming_invalid():
    source = Source()
    source.week["closedDays"] = ["MONDAY"]
    document = capture_roster_document(source, 42)
    assert all(row.cells[0].state.value == "day_closed" for row in document.presentation.rows)


@pytest.mark.parametrize("change", [{"version": 5}, {"status": "withdrawn"}, {"id": 99}])
def test_document_rejects_changed_revision_before_delivery(change):
    source = Source()
    document = capture_roster_document(source, 42)
    assert document.matches_revision(source.week)
    assert not document.matches_revision({**source.week, **change})


def test_document_normalizes_week_dates_and_freezes_policy_times(monkeypatch):
    from roster_policy import DUTY_SERVICE_TIME_WINDOWS, DutyPost

    source = Source()
    source.week["weekStart"] = "2026-09-07"
    document = capture_roster_document(source, 42)
    monkeypatch.setitem(DUTY_SERVICE_TIME_WINDOWS, DutyPost.ROOM_302, ("01:00", "02:00"))
    assert document.snapshot.week_start == date(2026, 9, 7)
    assert document.snapshot.week["weekStart"] == date(2026, 9, 7)
    assert document.presentation.rows[1].spec.service_time == ("15:40", "17:00")


def test_boolean_revision_is_not_silently_rendered_as_version_one():
    source = Source()
    source.week["version"] = True
    with pytest.raises(RosterPresentationError):
        capture_roster_document(source, 42)


@pytest.mark.parametrize("field,value", [("id", 42.5), ("version", 4.9), ("version", "4")])
def test_document_rejects_non_integer_identity_or_revision(field, value):
    source = Source()
    source.week[field] = value
    with pytest.raises(RosterPresentationError):
        capture_roster_document(source, 42)


@pytest.mark.parametrize("field,value", [("day", "SATURDAY"), ("postCode", "UNKNOWN"), ("slotIndex", 1.5)])
def test_document_rejects_extra_invalid_cells_instead_of_silently_ignoring_them(field, value):
    source = Source()
    invalid = {**source.assignments[0], field: value}
    source.assignments.append(invalid)
    with pytest.raises(RosterPresentationError):
        capture_roster_document(source, 42)
