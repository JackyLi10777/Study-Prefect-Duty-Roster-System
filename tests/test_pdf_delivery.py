from __future__ import annotations

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.pdf_delivery import (
    MAX_NATIVE_SHARE_BYTES,
    build_native_pdf_share_js,
    can_offer_native_pdf_share,
)


def test_native_pdf_share_bridge_uses_file_share_from_a_direct_click() -> None:
    script = build_native_pdf_share_js(
        content=b"%PDF-test",
        filename='SYSS_Roster_20260907_\"EN\".pdf',
        title="聖言中學導學風紀值班表",
        text="請查看最新版本。",
    )

    assert "navigator.canShare({files: [file]})" in script
    assert "await navigator.share({files: [file]" in script
    assert "new File([bytes]" in script
    assert "application/pdf" in script
    assert "AbortError" in script
    assert "emit({status: 'unsupported'})" in script
    assert "wa.me" not in script
    assert '\\"EN\\"' in script


def test_native_pdf_share_bridge_keeps_large_payloads_on_download_fallback() -> None:
    assert can_offer_native_pdf_share(b"%PDF")
    assert not can_offer_native_pdf_share(b"")
    assert not can_offer_native_pdf_share(b"x" * (MAX_NATIVE_SHARE_BYTES + 1))


def test_export_option_changes_invalidate_prepared_pdf_bytes() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_shared.py").read_text(encoding="utf-8")
    export_flow = source.split("def _open_roster_export_dialog", 1)[1].split("def _tone_badge", 1)[0]

    assert "prepared_signature" in export_flow
    assert "delivery_area.clear()" in export_flow
    assert "show_crest.on_value_change" in export_flow
    assert "show_footer_note.on_value_change" in export_flow
    assert 't("pdf_options_changed")' in export_flow
