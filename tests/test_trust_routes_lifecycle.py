"""Truthful overall evidence and retained first-use Trust content."""
import asyncio
from contextlib import nullcontext
from datetime import datetime
from types import SimpleNamespace

import pytest
from nicegui import core, ui
from nicegui.client import Client

from nicegui_app.release_evidence import ReleaseEvidence
from nicegui_app.ui.page_routes import showcase
from nicegui_app.ui.platform_summary import PlatformSummary


def _run(monkeypatch, check):
    async def run():
        monkeypatch.setattr(core, "loop", asyncio.get_running_loop())
        monkeypatch.setattr(showcase, "page_shell", lambda _: nullcontext())
        monkeypatch.setattr(showcase, "t", lambda key, **kwargs: key)
        monkeypatch.setattr(showcase, "render_service_weave_mark", lambda **_: None)
        monkeypatch.setattr(showcase, "_render_feedback_channel", lambda **_: None)
        with Client(ui.page("/trust-regression")) as client:
            try:
                await check(client)
            finally:
                await asyncio.sleep(0)
                client.delete()
    asyncio.run(run())


def _find(client, test_id):
    return next(e for e in client.elements.values() if e._props.get("data-testid") == test_id)


def _texts(client):
    return [getattr(e, "text", "") for e in client.elements.values()]


def _repeat(panel, client):
    assert "id" not in panel._props, "Do not replace NiceGUI's internal expansion id"
    initial = set(client.elements)
    for _ in range(20):
        panel.set_value(False)
        panel.set_value(True)
    assert set(client.elements) == initial


@pytest.mark.parametrize("state", ["pass", "running", "stale", "fail", "missing", "unreadable"])
def test_platform_defers_anonymous_summary_and_never_hides_release_state(monkeypatch, state):
    calls = {"workflow": 0, "summary": 0, "seed": 0, "attribution": 0}
    def counted(name, value):
        calls[name] += 1
        return value
    monkeypatch.setattr(showcase, "get_workflow", lambda: counted("workflow", object()))
    monkeypatch.setattr(showcase, "load_platform_summary", lambda _: counted("summary",
        PlatformSummary(24, 9, True, state, 13, 13)))
    monkeypatch.setattr(showcase, "load_devotional_seed", lambda: counted("seed", [SimpleNamespace(
        id="dv-0122", scripture_en="fictional text (NKJV)", scripture_zh="fictional text",
        reference_en="fictional reference", reference_zh="fictional reference")]))
    monkeypatch.setattr(showcase, "_render_co_creation", lambda: counted("attribution", None))
    async def check(client):
        showcase.platform_page()
        assert calls == {"workflow": 0, "summary": 0, "seed": 0, "attribution": 0}
        assert _find(client, "platform-open-workspace").visible
        summary = _find(client, "platform-summary-details")
        summary.set_value(True)
        assert calls["workflow"] == calls["summary"] == 1
        assert _find(client, "platform-release-state").text == "platform_release_" + state
        _repeat(summary, client)
        assert calls["summary"] == 1
        convictions = _find(client, "platform-convictions-details")
        convictions.set_value(True)
        _repeat(convictions, client)
        attribution = _find(client, "platform-attribution-details")
        attribution.set_value(True)
        _repeat(attribution, client)
        assert calls == {"workflow": 1, "summary": 1, "seed": 1, "attribution": 1}
    _run(monkeypatch, check)


def test_platform_summary_failure_is_explicit_and_does_not_expose_exception(monkeypatch):
    calls = []
    monkeypatch.setattr(showcase, "get_workflow", lambda: object())
    def broken(_):
        raise RuntimeError("private-name-and-backup-path")
    monkeypatch.setattr(showcase, "load_platform_summary", broken)
    monkeypatch.setattr(showcase, "record_operator_failure", lambda *args, **kwargs: calls.append(kwargs["action"]))
    monkeypatch.setattr(showcase, "new_operation_reference", lambda: "SAFE-FICTIONAL-REF")
    async def check(client):
        showcase.platform_page()
        panel = _find(client, "platform-summary-details")
        panel.set_value(True)
        assert calls == ["load_platform_summary"]
        assert _find(client, "platform-summary-unavailable")
        assert "private-name-and-backup-path" not in " ".join(_texts(client))
        assert "platform_release_pass" not in _texts(client)
    _run(monkeypatch, check)


def test_engineering_uses_one_snapshot_and_does_not_claim_individual_category_passes(monkeypatch):
    calls = []
    def evidence():
        calls.append(1)
        return ReleaseEvidence("stale" if len(calls) == 1 else "pass", 13, 13, datetime(2026, 9, 5, 12))
    monkeypatch.setattr(showcase, "load_release_evidence", evidence)
    async def check(client):
        showcase.engineering_page()
        assert calls == [1]
        assert _find(client, "engineering-release-state").text == "platform_release_stale"
        assert not any(isinstance(e, (ui.select, ui.input, ui.toggle)) for e in client.elements.values())
        assert not any(e._props.get("data-testid") == "engineering-evidence-type-filter" for e in client.elements.values())
        panel = _find(client, "engineering-coverage-details")
        panel.set_value(True)
        assert calls == [1]
        assert _texts(client).count("platform_release_stale") == 1
        assert "platform_release_pass" not in _texts(client)
        assert len([e for e in client.elements.values() if e._props.get("data-testid") == "engineering-coverage-item"]) == 13
        category = _find(client, "engineering-evidence-type-filter")
        category.set_value("quality")
        _repeat(panel, client)
        assert category.value == "quality" and calls == [1]
    _run(monkeypatch, check)


@pytest.mark.parametrize("locale", ["zh-HK", "en"])
@pytest.mark.parametrize("route,section_ids", [
    (showcase.platform_page, ("platform-summary-details", "platform-team-details",
        "platform-operating-map-details", "platform-capabilities-details", "platform-solutions-details",
        "platform-convictions-details", "platform-principles-details", "platform-resources-details",
        "platform-attribution-details")),
    (showcase.engineering_page, ("engineering-facts-details", "engineering-coverage-details",
        "engineering-blueprint-details", "engineering-process-details", "engineering-pillars-details",
        "engineering-evolution-details", "engineering-resources-details")),
    (showcase.system_architecture_page, ("architecture-flow-details", "architecture-layers-details",
        "architecture-evidence-details", "architecture-developer-details", "architecture-faq-details")),
])
def test_every_trust_section_has_complete_translations_and_retained_content(monkeypatch, locale, route, section_ids):
    from nicegui_app.ui.i18n import MESSAGES
    monkeypatch.setattr(showcase, "get_workflow", lambda: object())
    monkeypatch.setattr(showcase, "load_platform_summary", lambda _: PlatformSummary())
    monkeypatch.setattr(showcase, "load_release_evidence", lambda: ReleaseEvidence("unreadable", 0, 0, None))
    async def check(client):
        monkeypatch.setattr(showcase, "t", lambda key, **values: MESSAGES[key][locale].format(**values))
        route()
        for test_id in section_ids:
            panel = _find(client, test_id)
            assert panel.value is False
            assert not _find(client, test_id + "-content").default_slot.children
            panel.set_value(True)
            assert _find(client, test_id + "-content").default_slot.children
            _repeat(panel, client)
    _run(monkeypatch, check)


def test_architecture_faq_and_commands_are_first_use(monkeypatch):
    async def check(client):
        showcase.system_architecture_page()
        assert not any(e._props.get("data-testid") == "developer-health-command" for e in client.elements.values())
        assert "faq_draft_a" not in _texts(client)
        faq = _find(client, "architecture-faq-details")
        faq.set_value(True)
        assert "faq_draft_q" in _texts(client) and "faq_draft_a" not in _texts(client)
        question = _find(client, "architecture-faq-draft")
        question.set_value(True)
        assert "faq_draft_a" in _texts(client)
        _repeat(question, client)
        _repeat(faq, client)
        developer = _find(client, "architecture-developer-details")
        developer.set_value(True)
        assert _find(client, "developer-health-command")
        _repeat(developer, client)
    _run(monkeypatch, check)


@pytest.mark.parametrize("state", ["pass", "running", "stale", "fail", "missing", "unreadable"])
@pytest.mark.parametrize("finished_at", [datetime(2026, 9, 5, 12), None])
def test_engineering_report_date_is_visible_before_expansion(monkeypatch, state, finished_at):
    calls = []
    def load():
        calls.append(1)
        return ReleaseEvidence(state, 13, 13, finished_at)
    monkeypatch.setattr(showcase, "load_release_evidence", load)
    async def check(client):
        showcase.engineering_page()
        assert _find(client, "engineering-release-state").text == "platform_release_" + state
        label = _find(client, "engineering-release-date")
        assert label.visible
        assert ("2026-09-05" if finished_at else "engineering_report_date_unavailable") in label.text
        panel = _find(client, "engineering-coverage-details")
        panel.set_value(True)
        _repeat(panel, client)
        assert calls == [1]
    _run(monkeypatch, check)


@pytest.mark.parametrize("route,anchor,panel_id", [
    (showcase.engineering_page, "engineering-evidence-title", "engineering-coverage-details"),
    (showcase.system_architecture_page, "developer-reference-title", "architecture-developer-details"),
])
def test_original_heading_links_reveal_once_without_accepting_unknown_fragments(monkeypatch, route, anchor, panel_id):
    monkeypatch.setattr(showcase, "load_release_evidence", lambda: ReleaseEvidence("missing", 0, 0, None))
    async def check(client):
        route()
        panel = _find(client, panel_id)
        navigation = _find(client, "reading-navigation")
        listener = next(iter(navigation._event_listeners.values()))
        def navigate(target, sequence):
            listener.handler(SimpleNamespace(args={"detail": {"anchor": target, "sequence": sequence}}))
        navigate("fictional-private-fragment", 1)
        assert not panel.value
        navigate(anchor, 2)
        assert panel.value
        assert any(e._props.get("id") == anchor for e in client.elements.values())
        initial = set(client.elements)
        panel.set_value(False)
        navigate(anchor, 3)
        assert panel.value and set(client.elements) == initial
        assert navigation._props["data-reading-ready"] == "3"
    _run(monkeypatch, check)
