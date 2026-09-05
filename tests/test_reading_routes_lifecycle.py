"""Reading controls are first-use; existing workflow and verse state remain authoritative."""
import asyncio
import json
import subprocess
from contextlib import nullcontext
from datetime import date
from types import SimpleNamespace

import pytest
from nicegui import core, ui
from nicegui.client import Client

from nicegui_app.ui.page_routes import home
from nicegui_app.ui.reading_navigation import READING_RUNTIME, ReadingNavigation


def _run(monkeypatch, check):
    async def run():
        monkeypatch.setattr(core, "loop", asyncio.get_running_loop())
        monkeypatch.setattr(home, "page_shell", lambda _: nullcontext())
        monkeypatch.setattr(home, "_render_feedback_channel", lambda **_: None)
        with Client(ui.page("/reading-regression")) as client:
            try:
                await check(client)
            finally:
                await asyncio.sleep(0)
                client.delete()
    asyncio.run(run())


def _find(client, test_id):
    return next(e for e in client.elements.values() if e._props.get("data-testid") == test_id)


@pytest.mark.parametrize("has_people,state,expected", [
    (False, None, "open_prefects"), (True, None, "create_draft"),
    (True, "draft", "flow_open_draft"), (True, "published", "flow_open_published"),
    (True, "withdrawn", "create_draft"), (True, "other-week", "create_draft"),
])
def test_getting_started_uses_safe_exact_week_next_action(monkeypatch, has_people, state, expected):
    monkeypatch.setattr(home, "t", lambda key, **_: key)
    week_start = date(2026, 9, 7)
    monkeypatch.setattr(home, "_next_monday", lambda: week_start)
    row = {"id": 7, "weekStart": week_start.isoformat(), "status": state} if state else None
    if state == "other-week":
        row.update(weekStart="2026-08-31", status="published")
    calls = []
    workflow = SimpleNamespace(prefects=lambda: [object()] if has_people else [],
        roster_week_for_start=lambda value: (calls.append(value), None if state == "withdrawn" else row)[1],
        roster_week_history=lambda **_: [row] if row else [])
    monkeypatch.setattr(home, "get_workflow", lambda: workflow)
    async def check(client):
        home.getting_started_page()
        assert _find(client, "start-next-action").text == expected
        assert calls == [week_start]
        panel = _find(client, "start-reference-details")
        assert "id" not in panel._props, "Keep NiceGUI's internal id for close/focus lifecycle"
        assert not any(e._props.get("data-testid") == "reference-index" for e in client.elements.values())
        panel.set_value(True)
        initial = set(client.elements)
        for _ in range(20):
            panel.set_value(False)
            panel.set_value(True)
        assert set(client.elements) == initial
    _run(monkeypatch, check)


@pytest.mark.parametrize("locale", ["zh-HK", "en"])
def test_guide_search_matches_unmounted_answers_and_retains_controls(monkeypatch, locale):
    from nicegui_app.ui.i18n import MESSAGES
    monkeypatch.setattr(home, "t", lambda key, **kw: MESSAGES.get(key, {}).get(locale, key).format(**kw))
    body = MESSAGES["guide_issue_pdf_meaning"][locale]
    async def check(client):
        home.operator_guide_page()
        assert not any(getattr(e, "text", "") == body for e in client.elements.values())
        search = _find(client, "guide-search")
        search.set_value(body)
        panel = _find(client, "guide-answer-guide-issue-pdf")
        assert "id" not in panel._props
        assert panel.visible
        assert not _find(client, "guide-answer-guide-week-start").visible
        assert not _find(client, "guide-no-results").visible
        panel.set_value(True)
        assert any(getattr(e, "text", "") == body for e in client.elements.values())
        initial = set(client.elements)
        for _ in range(20):
            panel.set_value(False)
            panel.set_value(True)
        assert set(client.elements) == initial and search.value == body
        search.set_value("unmatched-fictional-query-xyz")
        assert _find(client, "guide-no-results").visible
        assert not panel.visible
        navigation = _find(client, "reading-navigation")
        listener = next(iter(navigation._event_listeners.values()))
        listener.handler(SimpleNamespace(args={"detail": {"anchor": "guide-issue-pdf", "sequence": 1}}))
        assert panel.visible and panel.value
        assert search.value == "unmatched-fictional-query-xyz"
        assert not _find(client, "guide-no-results").visible
        search.set_value("another-unmatched-fictional-query")
        assert not panel.visible and _find(client, "guide-no-results").visible
    _run(monkeypatch, check)


def test_reading_navigation_rejects_unknown_and_out_of_order_requests(monkeypatch):
    async def check(client):
        navigation = ReadingNavigation()
        calls = []
        navigation.register("safe-anchor", lambda: calls.append("mounted"))
        for detail in (None, {"anchor": "private-fragment", "sequence": 1},
                       {"anchor": ["safe-anchor"], "sequence": 1},
                       {"anchor": "safe-anchor", "sequence": True},
                       {"anchor": "safe-anchor", "sequence": 2**53}):
            navigation._receive(SimpleNamespace(args={"detail": detail}))
        assert calls == []
        navigation._receive(SimpleNamespace(args={"detail": {"anchor": "safe-anchor", "sequence": 2}}))
        assert calls == ["mounted"] and navigation.host._props["data-reading-ready"] == "2"
        for sequence in (1, 2):
            navigation._receive(SimpleNamespace(args={"detail": {"anchor": "safe-anchor", "sequence": sequence}}))
        assert calls == ["mounted"]
        with pytest.raises(ValueError):
            navigation.register("safe-anchor", lambda: None)
    _run(monkeypatch, check)


def test_navigation_runtime_allowlist_request_order_and_cleanup():
    script = r"""
const assert = require('node:assert/strict');
const install = RUNTIME;
global.window = new EventTarget();
global.document = new EventTarget();
global.location = {hash:'#private-viewer-key'};
let pushes=0;
global.history = {pushState: (_a,_b,hash) => {pushes++; location.hash=hash;}};
let nextFrame=0;
const frames = new Map();
global.requestAnimationFrame = fn => {frames.set(++nextFrame,fn); return nextFrame;};
global.cancelAnimationFrame = id => frames.delete(id);
const tick = () => {const pending=[...frames.values()]; frames.clear(); pending.forEach(fn=>fn());};
const payloads=[];
const host = new EventTarget();
host.isConnected=true;
host.ready=null;
host.getAttribute = () => host.ready;
host.addEventListener('reading-anchor', e=>payloads.push(e.detail));
let focusCount=0;
const target={getClientRects:()=>[1], querySelector:()=>null, hasAttribute:()=>true,
focus:()=>focusCount++, scrollIntoView:()=>{}};
document.getElementById = id => id==='host' ? host : id==='safe-anchor' ? target : null;
install('host',['safe-anchor']);
assert.equal(payloads.length,0);
location.hash='#safe-anchor'; window.dispatchEvent(new Event('hashchange'));
assert.deepEqual(payloads,[{anchor:'safe-anchor',sequence:2}]);
tick(); assert.equal(focusCount,0);
location.hash='#another-private-key'; window.dispatchEvent(new Event('hashchange'));
host.ready='2'; tick(); assert.equal(focusCount,0);
assert.equal(payloads.length,1);
location.hash='#safe-anchor'; window.dispatchEvent(new Event('hashchange'));
host.ready='4'; tick(); assert.equal(focusCount,1);
const sameLink = {getAttribute:name => name==='data-sy-toc-target' ? 'safe-anchor' : '#safe-anchor'};
const click = new Event('click', {cancelable:true});
Object.defineProperties(click, {target:{value:{closest:()=>sameLink}},button:{value:0}});
document.dispatchEvent(click);
assert.equal(pushes,0);
host.ready=String(payloads.at(-1).sequence); tick(); assert.equal(focusCount,2);
install('host',['safe-anchor']);
const before=payloads.length;
window.dispatchEvent(new Event('hashchange'));
assert.equal(payloads.length,before+1);
window.dispatchEvent(new Event('pagehide'));
const closed=payloads.length;
window.dispatchEvent(new Event('hashchange')); tick();
assert.equal(payloads.length,closed);
assert.equal(frames.size,0);
console.log(JSON.stringify({allowlist:true,staleFocusRejected:true,cleanup:true}));
""".replace("RUNTIME", READING_RUNTIME)
    result = subprocess.run(["node", "-e", script], text=True, capture_output=True, check=True)
    assert json.loads(result.stdout) == {"allowlist": True, "staleFocusRejected": True, "cleanup": True}


def test_devotional_late_tone_reads_latest_preference_without_writing(monkeypatch):
    calls, writes = [], []
    preference = {"value": "auto"}
    verse = SimpleNamespace(reference_zh="fictional ref", reference_en="fictional ref",
        scripture_zh="fictional verse", scripture_en="fictional verse",
        reflection_zh={"title": "fictional reflection", "body": "same snapshot", "prayer": "fictional prayer"},
        reflection_en={"title": "fictional reflection", "body": "same snapshot", "prayer": "fictional prayer"})
    monkeypatch.setattr(home, "_dashboard_verse", lambda: (calls.append(1), verse)[1])
    monkeypatch.setattr(home, "current_locale", lambda: "zh-HK")
    monkeypatch.setattr(home, "preference_get", lambda *_: preference["value"])
    monkeypatch.setattr(home, "_set_devotional_tone", writes.append)
    async def check(client):
        home.devotional_page()
        assert calls == [1] and writes == []
        assert not any(e._props.get("data-testid") == "devotional-tone" for e in client.elements.values())
        assert not any(getattr(e, "text", "") == "same snapshot" for e in client.elements.values())
        assert _find(client, "devotional-return-work").visible
        preference["value"] = "comfort"
        panel = _find(client, "devotional-details")
        assert "id" not in panel._props
        panel.set_value(True)
        tone = _find(client, "devotional-tone")
        assert tone.value == "comfort" and writes == []
        assert any(getattr(e, "text", "") == "same snapshot" for e in client.elements.values())
        initial = set(client.elements)
        for _ in range(20):
            panel.set_value(False)
            panel.set_value(True)
        assert set(client.elements) == initial and calls == [1] and writes == []
        tone.set_value("guidance")
        assert writes == ["guidance"]
    _run(monkeypatch, check)
