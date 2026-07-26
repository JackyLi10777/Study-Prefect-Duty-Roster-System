from __future__ import annotations

from pathlib import Path

from nicegui_app.access_context import AccessMode, Capability, CapabilityPolicy
from nicegui_app.ui.i18n_catalog.support import MESSAGES
from nicegui_app.ui.page_catalog import page_definition
from nicegui_app.ui.page_routes.support import _guest_report_markup, _support_defaults


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_support_route_is_one_shared_admin_and_guest_page() -> None:
    page = page_definition("/support")
    assert page is not None
    assert page.is_accessible_to(AccessMode.ADMIN)
    assert page.is_accessible_to(AccessMode.GUEST)
    assert CapabilityPolicy.allows(AccessMode.ADMIN, Capability.PERSISTENT_WRITE)
    assert not CapabilityPolicy.allows(AccessMode.GUEST, Capability.PERSISTENT_WRITE)


def test_guest_report_markup_is_browser_only_and_attachment_free() -> None:
    markup = _guest_report_markup("/rosters")
    assert 'data-testid="guest-browser-only-support"' in markup
    assert 'type="file"' not in markup
    assert "action=" not in markup
    assert "method=" not in markup
    assert "support inbox" not in markup.lower()
    assert '<details class="sy-support-details">' in markup
    assert 'id="sy-support-browser-result-actions"' in markup
    assert 'id="sy-support-browser-download" disabled' not in markup
    assert '<option value="rosters" selected>' in markup


def test_support_context_is_inferred_without_translation_keys() -> None:
    assert _support_defaults("/rosters") == ("rosters", "page_view")
    assert _support_defaults("/prefects") == ("prefects", "page_view")
    assert _support_defaults("/rosters/12/adjustments") == ("roster_workflow", "page_view")
    assert _support_defaults("https://example.invalid/") == ("other", "page_view")


def test_guest_feedback_javascript_has_no_network_or_persistent_storage() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "assets" / "motion" / "support-feedback-v1.js").read_text(
        encoding="utf-8"
    )
    for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "localStorage", "indexedDB", "sessionStorage"):
        assert forbidden not in source
    assert "new Blob" in source
    assert "mailto:" in source
    assert "resultActions.hidden = !enabled" in source
    assert "navigator.clipboard?.writeText" in source
    assert "root.dataset.copyFailedMessage" in source
    assert "catch {" in source
    assert "new MutationObserver" in source
    assert "if (install()) observer.disconnect()" in source


def test_admin_support_clears_consumed_attachments_after_save() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "support.py").read_text(encoding="utf-8")
    success = source[source.index("preview_dialog.close()", source.index("async def save_incident")):]
    assert success.index("attachments.clear()") < success.index('ui.notify(t("support_saved")')
    assert success.index("attachment_summary.clear()") < success.index('ui.notify(t("support_saved")')


def test_support_messages_are_complete_bilingual_copy() -> None:
    assert MESSAGES
    for value in MESSAGES.values():
        assert set(value) == {"zh-HK", "en"}
        assert value["zh-HK"].strip()
        assert value["en"].strip()
