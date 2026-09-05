from contextlib import nullcontext
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from nicegui_app.ui.dashboard_flow import resolve_dashboard_next_action


WEEK = date(2026, 9, 7)


def week(status, *, start=WEEK, identifier=42):
    return {"id": identifier, "weekStart": start, "status": status, "version": 3}


@pytest.mark.parametrize("status,action,path,tone", [
    (None, "create_draft", "/rosters", "action"),
    ("withdrawn", "create_draft", "/rosters", "attention"),
    ("draft", "flow_open_draft", "/rosters/42", "action"),
    ("published", "flow_open_published", "/rosters/42", "stable"),
])
def test_next_action_follows_only_the_selected_week(status, action, path, tone):
    result = resolve_dashboard_next_action(
        has_prefects=True, week_start=WEEK,
        selected_week=week(status) if status else None,
    )
    assert (result.action_key, result.destination, result.tone) == (action, path, tone)
    assert "/adjustments" not in result.destination


@pytest.mark.parametrize("status", [None, "draft", "published", "withdrawn"])
def test_empty_directory_always_leads_to_people(status):
    result = resolve_dashboard_next_action(
        has_prefects=False, week_start=WEEK,
        selected_week=week(status) if status else None,
    )
    assert result.destination == "/prefects"
    assert result.status_key == "flow_directory_ready"


@pytest.mark.parametrize("start", [date(2026, 8, 31), date(2026, 9, 14)])
@pytest.mark.parametrize("status", ["draft", "published", "withdrawn"])
def test_previous_or_future_history_never_selects_the_primary_flow(start, status):
    result = resolve_dashboard_next_action(
        has_prefects=True, week_start=WEEK, selected_week=None,
        latest_week=week(status, start=start),
    )
    assert result.destination == "/rosters"
    assert result.status_key == "dashboard_no_active_week"
    assert result.action_key == "create_draft"


def test_missing_active_week_does_not_claim_no_history_when_later_week_is_latest():
    # The exact lookup omits withdrawn weeks. A later history item cannot prove
    # whether the selected week was never started or was subsequently withdrawn.
    result = resolve_dashboard_next_action(
        has_prefects=True, week_start=WEEK, selected_week=None,
        latest_week=week("published", start=date(2026, 9, 14)),
    )
    assert result.status_key == "dashboard_no_active_week"
    assert (result.action_key, result.destination) == ("create_draft", "/rosters")


def test_no_active_week_copy_is_neutral_in_both_languages():
    from nicegui_app.ui.i18n import MESSAGES

    assert MESSAGES["dashboard_no_active_week"] == {
        "zh-HK": "所選週目前沒有有效週表",
        "en": "No active roster for the selected week",
    }


def test_exact_active_lookup_takes_precedence_over_latest_history():
    result = resolve_dashboard_next_action(
        has_prefects=True, week_start=WEEK,
        selected_week=week("draft"), latest_week=week("withdrawn", identifier=99),
    )
    assert result.destination == "/rosters/42"
    assert result.status_key == "flow_draft_ready"


def test_exact_withdrawn_history_explains_missing_active_week():
    result = resolve_dashboard_next_action(
        has_prefects=True, week_start=WEEK, selected_week=None,
        latest_week=week("withdrawn"),
    )
    assert result.destination == "/rosters"
    assert result.status_key == "withdrawn"


def test_guest_iso_date_uses_the_same_exact_week_as_official_date_values():
    official = week("published")
    guest = {**official, "weekStart": WEEK.isoformat()}
    assert resolve_dashboard_next_action(
        has_prefects=True, week_start=WEEK, selected_week=official,
    ) == resolve_dashboard_next_action(
        has_prefects=True, week_start=WEEK, selected_week=guest,
    )


def test_mismatched_active_lookup_cannot_open_another_week():
    result = resolve_dashboard_next_action(
        has_prefects=True, week_start=WEEK,
        selected_week=week("published", start=date(2026, 8, 31)),
    )
    assert result.destination == "/rosters"
    assert result.status_key == "dashboard_no_active_week"


@pytest.mark.parametrize("identifier", [None, 0, -1, True, "42", "42/adjustments"])
def test_invalid_detail_identity_is_rejected(identifier):
    with pytest.raises(ValueError, match="identifier"):
        resolve_dashboard_next_action(
            has_prefects=True, week_start=WEEK,
            selected_week=week("published", identifier=identifier),
        )


def test_non_monday_and_unknown_status_are_not_silently_reinterpreted():
    with pytest.raises(ValueError, match="Monday"):
        resolve_dashboard_next_action(
            has_prefects=True, week_start=date(2026, 9, 8), selected_week=None,
        )
    with pytest.raises(ValueError, match="status"):
        resolve_dashboard_next_action(
            has_prefects=True, week_start=WEEK, selected_week=week("unexpected"),
        )


@pytest.mark.parametrize("today,expected", [
    (date(2026, 9, 7), date(2026, 9, 7)),
    (date(2026, 9, 8), date(2026, 9, 14)),
    (date(2026, 9, 11), date(2026, 9, 14)),
    (date(2026, 9, 12), date(2026, 9, 14)),
    (date(2026, 9, 13), date(2026, 9, 14)),
    (date(2026, 12, 31), date(2027, 1, 4)),
])
def test_dashboard_uses_the_same_default_monday_as_generation(monkeypatch, today, expected):
    from nicegui_app.ui import page_shared
    from nicegui_app.ui.page_routes import home, weekly

    class FrozenDate(date):
        @classmethod
        def today(cls):
            return today

    monkeypatch.setattr(page_shared, "date", FrozenDate)
    assert home._next_monday is weekly._next_monday
    assert home._next_monday() == expected


@pytest.mark.parametrize("status,has_prefects,expected", [
    (None, False, "/prefects"), (None, True, "/rosters"),
    ("draft", True, "/rosters/42"), ("published", True, "/rosters/42"),
    ("withdrawn", True, "/rosters"),
])
@pytest.mark.parametrize("has_history", [False, True])
def test_dashboard_render_has_one_primary_and_bounded_reads_without_devotional(
    monkeypatch, status, has_prefects, expected, has_history,
):
    from nicegui_app.ui.page_routes import home

    current = week(status) if status else None
    latest = current or week("published", start=date(2026, 8, 31), identifier=19)
    workflow = SimpleNamespace(
        prefects=MagicMock(return_value=[{"id": "fictional"}] if has_prefects else []),
        roster_week_for_start=MagicMock(return_value=None if status == "withdrawn" else current),
        roster_week_history=MagicMock(return_value=[latest] if has_history else []),
    )
    ui = MagicMock()
    actions = MagicMock()
    navigate = MagicMock()
    verse = MagicMock(side_effect=AssertionError("Dashboard must not load devotional data"))
    monkeypatch.setattr(home, "get_workflow", lambda: workflow)
    monkeypatch.setattr(home, "_next_monday", lambda: WEEK)
    monkeypatch.setattr(home, "page_shell", lambda route: nullcontext())
    monkeypatch.setattr(home, "ui", ui)
    monkeypatch.setattr(home, "t", lambda key: key)
    monkeypatch.setattr(home, "_tone_badge", MagicMock())
    monkeypatch.setattr(home, "action", actions)
    monkeypatch.setattr(home, "_navigate_with_feedback", navigate)
    monkeypatch.setattr(home, "_dashboard_verse", verse)

    home.dashboard_page()

    workflow.roster_week_for_start.assert_called_once_with(WEEK)
    workflow.roster_week_history.assert_called_once_with(page=1, page_size=1)
    verse.assert_not_called()
    primary = [call for call in actions.call_args_list if call.kwargs.get("variant", "primary") == "primary"]
    assert len(primary) == 1
    assert primary[0].kwargs["test_id"] == "dashboard-next-action"
    primary[0].kwargs["on_click"]()
    navigate.assert_called_once_with(expected)
    assert len(actions.call_args_list) == (2 if has_history else 1)
    if has_history:
        assert actions.call_args_list[1].kwargs["variant"] == "quiet"
    else:
        ui.label.assert_any_call("no_rosters")
    ui.label.assert_any_call("week_start: 2026-09-07")
    assert not ui.select.called and not ui.expansion.called
