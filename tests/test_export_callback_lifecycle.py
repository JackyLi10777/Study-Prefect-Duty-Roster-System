"""Execute real UI callbacks while controlling browser event delivery order."""

from types import SimpleNamespace
import asyncio
import json
import re

import pytest

from nicegui_app.services.roster_export_session import ExportOptions, RosterExportSession
from nicegui_app.ui import page_shared


class Element:
    def __init__(self, ui, text="", **kwargs):
        self.ui = ui
        self.id = len(ui.elements)
        self.text = text
        self.props_text = ""
        self.events = {}
        self.methods = []
        self.is_deleted = False
        self.default_slot = SimpleNamespace(children=[])
        if ui.stack:
            ui.stack[-1].default_slot.children.append(self)
        ui.elements.append(self)
        if kwargs.get("on_click"):
            self.events["click"] = kwargs["on_click"]

    def __enter__(self):
        self.ui.stack.append(self)
        return self

    def __exit__(self, *_args):
        self.ui.stack.pop()

    def classes(self, *_args):
        return self

    def props(self, text="", **_kwargs):
        self.props_text += " " + text
        return self

    def on(self, name, callback, **kwargs):
        self.events[name] = callback
        self.events[name + "_js"] = kwargs.get("js_handler")
        return self

    def run_method(self, *args):
        self.methods.append(args)

    def set_text(self, text):
        self.text = text

    def set_visibility(self, value):
        self.visible = value

    def clear(self):
        for child in self.default_slot.children:
            child.clear()
            child.is_deleted = True
        self.default_slot.children.clear()


class UI:
    def __init__(self):
        self.elements = []
        self.stack = []
        self.notifications = []
        self.javascript = []
        self.timers = []

    def __getattr__(self, _name):
        return lambda *args, **kwargs: Element(self, args[0] if args else "", **kwargs)

    def notify(self, text, **kwargs):
        if self.stack and self.stack[-1].is_deleted:
            raise RuntimeError("The current event slot belongs to a deleted element")
        self.notifications.append((text, kwargs))

    def run_javascript(self, script):
        self.javascript.append(script)

    def timer(self, interval, callback, **kwargs):
        timer = SimpleNamespace(callback=callback, interval=interval, active=True)
        timer.cancel = lambda: setattr(timer, "active", False)
        self.timers.append(timer)
        return timer

    def by_test_id(self, test_id):
        return next(element for element in reversed(self.elements) if f'data-testid="{test_id}"' in element.props_text
                    or f'data-testid={test_id}' in element.props_text)


def share_event(**args):
    return SimpleNamespace(args=args)


def share_metadata(button):
    return json.loads(re.search(r"const metadata = (.*);", button.events["click_js"])[1])


@pytest.mark.parametrize("format", ["pdf", "png"])
@pytest.mark.parametrize("current", [True, False])
def test_share_requires_server_revision_check_before_native_confirmation(harness, format, current):
    ui, _client = harness
    checks = []
    session = RosterExportSession()
    session.open()
    session.complete(session.begin(), object())
    token = str(session.generation)
    common = dict(share_result_token=token, share_result_guard=session.accepts_share_result,
                  delivery_guard=lambda: checks.append("revision") or current)
    if format == "pdf":
        page_shared._render_pdf_delivery_ready(Element(ui), SimpleNamespace(content=b"%PDF-fixture", filename="fixture.pdf", roster_status="published"), **common)
        test_id = "share-schedule-pdf"
    else:
        image = SimpleNamespace(content=b"\x89PNG\r\n\x1a\nfixture", filename="fixture.png", media_type="image/png")
        page_shared._render_png_delivery_ready(Element(ui), SimpleNamespace(avatar=image, whatsapp=image, roster_status="published"), allow_download=True, allow_native_share=True, practice=False, **common)
        test_id = "share-roster-detail"
    first = ui.by_test_id(test_id)
    assert "navigator.share" not in (first.events["click_js"] or "")
    first.events["click"](share_event(preparedAt=1000))
    assert checks == ["revision"]
    if current:
        confirm = ui.by_test_id("confirm-" + test_id)
        metadata = share_metadata(confirm)
        assert metadata["leaseExpiresAt"] == 16000
        assert metadata["leaseToken"]
        assert "navigator.share" in confirm.events["click_js"]
        assert len(ui.timers) == 1 and ui.timers[0].interval == 15
        ui.by_test_id("cancel-" + test_id).events["click"]()
        assert not ui.timers[0].active
        confirm.events["click"](share_event(status="shared", token=token, lease=metadata["leaseToken"]))
        assert not ui.notifications
    else:
        assert not any("confirm-" + test_id in element.props_text for element in ui.elements)
        assert not ui.timers


@pytest.fixture
def harness(monkeypatch):
    ui = UI()
    client = SimpleNamespace()
    monkeypatch.setattr(page_shared, "ui", ui)
    monkeypatch.setattr(page_shared, "context", SimpleNamespace(client=client))
    monkeypatch.setattr(page_shared, "t", lambda key: key)
    monkeypatch.setattr(page_shared, "is_demo_export", lambda: False)
    monkeypatch.setattr(page_shared, "current_locale", lambda: "zh-HK")
    monkeypatch.setattr(page_shared, "get_workflow", lambda: SimpleNamespace(roster_week=lambda _id: {"status": "published"}))
    monkeypatch.setattr(page_shared, "_safe_read_action", lambda action, **_kwargs: action())
    monkeypatch.setattr(page_shared, "semantic_native_dialog", lambda **_kwargs: Element(ui))
    return ui, client


def test_close_ack_cannot_clear_reopened_export_session(harness, monkeypatch):
    ui, client = harness
    session = RosterExportSession()
    monkeypatch.setattr(page_shared, "RosterExportSession", lambda _options: session)
    page_shared._open_page_owned_roster_export_dialog(42)
    dialog = client._sy_roster_export_dialogs[42]["dialog"]
    ui.by_test_id("close-roster-export").events["click"]()
    assert not session.opened
    # The browser has not acknowledged close yet. Reopen must not race it.
    page_shared._open_page_owned_roster_export_dialog(42)
    page_shared._open_page_owned_roster_export_dialog(42)
    assert not session.opened
    assert [call[0] for call in dialog.methods].count("showModal") == 1
    dialog.events["close"](SimpleNamespace(args={}))
    assert session.opened
    assert session.phase == "idle"
    assert [call[0] for call in dialog.methods].count("showModal") == 2


def test_native_escape_closes_once_and_next_open_still_works(harness, monkeypatch):
    ui, client = harness
    session = RosterExportSession()
    monkeypatch.setattr(page_shared, "RosterExportSession", lambda _options: session)
    page_shared._open_page_owned_roster_export_dialog(42)
    dialog = client._sy_roster_export_dialogs[42]["dialog"]
    dialog.events["close"](SimpleNamespace(args={}))
    generation = session.generation
    assert not session.opened
    dialog.events["close"](SimpleNamespace(args={}))
    assert session.generation == generation
    page_shared._open_page_owned_roster_export_dialog(42)
    assert session.opened


def test_twenty_close_reopen_ack_cycles_keep_one_live_session(harness, monkeypatch):
    ui, client = harness
    session = RosterExportSession()
    monkeypatch.setattr(page_shared, "RosterExportSession", lambda _options: session)
    page_shared._open_page_owned_roster_export_dialog(42)
    dialog = client._sy_roster_export_dialogs[42]["dialog"]
    initial_elements = len(ui.elements)
    close = ui.by_test_id("close-roster-export").events["click"]
    for _ in range(20):
        close()
        page_shared._open_page_owned_roster_export_dialog(42)
        assert not session.opened
        dialog.events["close"](SimpleNamespace(args={}))
        assert session.opened
        assert session.phase == "idle"
    assert len(ui.elements) == initial_elements
    assert [call[0] for call in dialog.methods].count("showModal") == 21


def test_cached_png_views_bind_share_bytes_filename_and_token_to_own_elements(harness):
    ui, _client = harness
    image = SimpleNamespace(content=b"\x89PNG\r\n\x1a\nfixture", filename="fixture.png", media_type="image/png")
    bundle = SimpleNamespace(avatar=image, whatsapp=image, roster_status="published")
    views = [page_shared._render_png_delivery_ready(
        Element(ui), bundle, allow_download=True, allow_native_share=True, practice=False,
        delivery_guard=lambda: True, share_result_token="2", share_result_guard=lambda _token: True,
    ) for _ in range(2)]
    for view, other in [(views[0], views[1]), (views[1], views[0])]:
        view["share_button"].events["click"](share_event(preparedAt=1000))
        script = ui.by_test_id("confirm-share-roster-detail").events["click_js"]
        assert f'"previewSelector":"#c{view["detail_image"].id}"' in script
        assert f'"filenameSelector":"#c{view["detail_filename"].id}"' in script
        assert f'"resultTokenSelector":"#c{view["detail_image"].id}"' in script
        assert f'"previewSelector":"#c{other["detail_image"].id}"' not in script


@pytest.mark.parametrize("format", ["pdf", "png"])
@pytest.mark.parametrize("invalidation", ["aba", "close_reopen"])
def test_late_native_share_result_cannot_notify_new_workspace(harness, format, invalidation):
    ui, _client = harness
    session = RosterExportSession()
    session.open()
    request = session.begin()
    session.complete(request, object())
    old_token = str(request.generation)
    container = Element(ui)
    options = {"share_result_token": old_token, "share_result_guard": session.accepts_share_result, "delivery_guard": lambda: True}
    if format == "pdf":
        page_shared._render_pdf_delivery_ready(
            container, SimpleNamespace(content=b"%PDF-test", filename="fixture.pdf", roster_status="published"), **options,
        )
        button = ui.by_test_id("share-schedule-pdf")
    else:
        image = SimpleNamespace(content=b"\x89PNG\r\n\x1a\nfixture", filename="fixture.png", media_type="image/png")
        bundle = SimpleNamespace(avatar=image, whatsapp=image, roster_status="published")
        page_shared._render_png_delivery_ready(
            container, bundle, allow_download=True, allow_native_share=True, practice=False, **options,
        )
        button = ui.by_test_id("share-roster-detail")
    button.events["click"](share_event(preparedAt=1000))
    confirm = ui.by_test_id("confirm-share-schedule-pdf" if format == "pdf" else "confirm-share-roster-detail")
    lease = share_metadata(confirm)["leaseToken"]
    confirm.events["click"](share_event(status="started", token=old_token, lease=lease))
    if invalidation == "aba":
        session.change_options(ExportOptions(language="en"))
        session.change_options(ExportOptions(language="zh"))
    else:
        session.close()
        session.open()
    new_request = session.begin()
    session.complete(new_request, object())
    for status in ["shared", "cancelled", "failed", "unsupported"]:
        confirm.events["click"](share_event(status=status, token=old_token, lease=lease))
    assert ui.notifications == []


def test_confirmation_expiry_requires_new_preparation_and_late_result_is_ignored(harness, monkeypatch):
    ui, _client = harness
    clock = [0]
    monkeypatch.setattr(page_shared, "perf_counter", lambda: clock[0])
    area = Element(ui)
    reports = []
    cleanup = page_shared._mount_native_share_confirmation(
        area, share_event(preparedAt=0), test_id="fixture", generation="2", result_guard=lambda token: token == "2",
        build_handler=lambda lease, deadline: page_shared.build_native_file_share_js(
            content=b"%PDF-fixture", filename="fixture.pdf", media_type="application/pdf", title="Fixture", text="Fixture",
            result_token="2", lease_token=lease.token, lease_expires_at=deadline,
        ), report_result=reports.append,
    )
    assert cleanup is not None
    confirm = ui.by_test_id("confirm-fixture")
    lease = share_metadata(confirm)["leaseToken"]
    clock[0] = 15
    ui.timers[0].callback()
    assert not area.default_slot.children
    confirm.events["click"](share_event(status="started", token="2", lease=lease))
    confirm.events["click"](share_event(status="shared", token="2", lease=lease))
    assert not reports
    assert ui.notifications[0][0] == "native_share_prepare_expired"


def test_current_confirm_reports_cancel_and_cannot_be_replayed(harness):
    ui, _client = harness
    reports = []
    page_shared._mount_native_share_confirmation(
        Element(ui), share_event(preparedAt=0), test_id="fixture", generation="2", result_guard=lambda token: token == "2",
        build_handler=lambda lease, deadline: page_shared.build_native_file_share_js(
            content=b"%PDF-fixture", filename="fixture.pdf", media_type="application/pdf", title="Fixture", text="Fixture",
            result_token="2", lease_token=lease.token, lease_expires_at=deadline,
        ), report_result=reports.append,
    )
    confirm = ui.by_test_id("confirm-fixture")
    lease = share_metadata(confirm)["leaseToken"]
    confirm.events["click"](share_event(status="started", token="2", lease=lease))
    confirm.events["click"](share_event(status="cancelled", token="2", lease=lease))
    confirm.events["click"](share_event(status="shared", token="2", lease=lease))
    assert [event.args["status"] for event in reports] == ["cancelled"]
    assert not ui.timers[0].active


@pytest.mark.parametrize("status", ("shared", "cancelled", "failed", "unsupported", "expired"))
def test_native_result_notification_uses_surviving_container_after_button_cleanup(harness, status):
    ui, _client = harness
    area = Element(ui)
    page_shared._mount_native_share_confirmation(
        area, share_event(preparedAt=0), test_id="fixture", generation="2", result_guard=lambda token: token == "2",
        build_handler=lambda lease, deadline: page_shared.build_native_file_share_js(
            content=b"%PDF-fixture", filename="fixture.pdf", media_type="application/pdf", title="Fixture", text="Fixture",
            result_token="2", lease_token=lease.token, lease_expires_at=deadline,
        ), report_result=lambda _event: ui.notify("observed result"),
    )
    confirm = ui.by_test_id("confirm-fixture")
    lease = share_metadata(confirm)["leaseToken"]
    # NiceGUI executes an event under its sender's slot. Clearing the short-lived
    # confirmation removes that slot; the persistent owner must host feedback.
    with confirm:
        if status in {"shared", "cancelled"}:
            confirm.events["click"](share_event(status="started", token="2", lease=lease))
        confirm.events["click"](share_event(status=status, token="2", lease=lease))
    assert confirm.is_deleted
    assert len(ui.notifications) == 1


def test_cancelled_lease_late_start_cannot_remove_new_confirmation(harness):
    ui, _client = harness
    area = Element(ui)
    def mount():
        return page_shared._mount_native_share_confirmation(
            area, share_event(preparedAt=0), test_id="fixture", generation="2", result_guard=lambda token: token == "2",
            build_handler=lambda lease, deadline: page_shared.build_native_file_share_js(
                content=b"%PDF-fixture", filename="fixture.pdf", media_type="application/pdf", title="Fixture", text="Fixture",
                result_token="2", lease_token=lease.token, lease_expires_at=deadline,
            ), report_result=lambda _event: None,
        )
    old_cleanup = mount()
    old_confirm = ui.by_test_id("confirm-fixture")
    old_lease = share_metadata(old_confirm)["leaseToken"]
    old_cleanup()
    mount()
    children = list(area.default_slot.children)
    old_confirm.events["click"](share_event(status="started", token="2", lease=old_lease))
    old_cleanup()
    assert area.default_slot.children == children


@pytest.mark.parametrize("practice", [True, False])
def test_guest_never_receives_native_share_prepare_or_confirm_controls(harness, practice):
    ui, _client = harness
    image = SimpleNamespace(content=b"\x89PNG\r\n\x1a\nfixture", filename="fixture.png", media_type="image/png")
    if practice:
        page_shared._render_png_delivery_ready(Element(ui), SimpleNamespace(avatar=image, whatsapp=image, roster_status="published"),
            allow_download=True, allow_native_share=False, practice=True)
    else:
        page_shared._render_pdf_delivery_ready(Element(ui), SimpleNamespace(content=b"%PDF-fixture", filename="fixture.pdf", roster_status="published"),
            allow_native_share=False)
    assert not any("share-roster-detail" in element.props_text or "share-schedule-pdf" in element.props_text for element in ui.elements)
    assert not ui.timers


@pytest.mark.parametrize("format", ["pdf", "png"])
@pytest.mark.parametrize("new_status", ["published", "withdrawn"])
def test_other_session_revision_change_prevents_native_confirmation(harness, monkeypatch, format, new_status):
    ui, _client = harness
    week = {"id": 42, "status": "published", "version": 1}
    session = RosterExportSession()
    document = SimpleNamespace(matches_revision=lambda current: current["version"] == 1 and current["status"] == "published")
    image = SimpleNamespace(content=b"\x89PNG\r\n\x1a\nfixture", filename="fixture.png", media_type="image/png")
    async def prepare_document(*_args, **_kwargs):
        return document
    async def prepare_png(*_args, **_kwargs):
        return SimpleNamespace(avatar=image, whatsapp=image, roster_status="published")
    async def prepare_pdf(*_args, **_kwargs):
        return SimpleNamespace(content=b"%PDF-fixture", filename="fixture.pdf", roster_status="published")
    downloads = []
    monkeypatch.setattr(page_shared, "get_workflow", lambda: SimpleNamespace(roster_week=lambda _id: dict(week)))
    monkeypatch.setattr(page_shared, "RosterExportSession", lambda _options: session)
    monkeypatch.setattr(page_shared, "_prepare_export_document", prepare_document)
    monkeypatch.setattr(page_shared, "_prepare_roster_png_bundle", prepare_png)
    monkeypatch.setattr(page_shared, "_prepare_roster_pdf", prepare_pdf)
    monkeypatch.setattr(page_shared, "_download_roster_png", lambda image: downloads.append(image) or True)
    page_shared._open_page_owned_roster_export_dialog(42)
    if format == "pdf":
        ui.by_test_id("pdf-advanced-options").events["click"]()
        asyncio.run(ui.by_test_id("prepare-roster-pdf").events["click"]())
        test_id = "share-schedule-pdf"
    else:
        asyncio.run(ui.by_test_id("prepare-roster-images").events["click"]())
        test_id = "share-roster-detail"
        assert downloads == [image], "one-click avatar download must remain unchanged"
    assert session.phase == "ready"
    week.update(version=2, status=new_status)
    ui.by_test_id(test_id).events["click"](share_event(preparedAt=1000))
    assert session.phase == "stale"
    assert session.document is None
    assert not any("confirm-" + test_id in element.props_text for element in ui.elements)
    assert not ui.timers
