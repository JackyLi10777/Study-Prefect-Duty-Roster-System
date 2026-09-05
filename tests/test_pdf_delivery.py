from __future__ import annotations

import pytest

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.services.roster_export import RosterPdfExport
from nicegui_app.ui import page_shared
from nicegui_app.ui.pdf_delivery import (
    MAX_NATIVE_SHARE_BYTES,
    build_native_pdf_share_js,
    can_offer_native_pdf_share,
)
from nicegui_app.ui.native_file_share import build_native_file_share_js


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
    assert "report('unsupported')" in script
    assert "wa.me" not in script
    assert '\\"EN\\"' in script


def test_native_pdf_share_bridge_keeps_large_payloads_on_download_fallback() -> None:
    assert can_offer_native_pdf_share(b"%PDF-")
    assert not can_offer_native_pdf_share(b"")
    assert not can_offer_native_pdf_share(b"x" * (MAX_NATIVE_SHARE_BYTES + 1))


def test_pdf_share_wrapper_preserves_the_generic_bridge_contract() -> None:
    arguments = {
        "content": b"%PDF-test",
        "filename": "roster.pdf",
        "title": "Roster",
        "text": "Latest version",
    }

    assert build_native_pdf_share_js(**arguments) == build_native_file_share_js(
        **arguments,
        media_type="application/pdf",
    )


def test_pdf_export_requires_rendered_snapshot_provenance() -> None:
    with pytest.raises(TypeError):
        RosterPdfExport("legacy.pdf", b"%PDF-test")  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("status", "practice", "expected"),
    [
        ("published", False, (True, True)),
        ("published", True, (True, False)),
        ("draft", False, (True, False)),
        ("draft", True, (True, False)),
        ("withdrawn", False, (False, False)),
        ("withdrawn", True, (False, False)),
        ("unknown", False, (False, False)),
    ],
)
def test_pdf_delivery_permissions_come_from_rendered_snapshot_provenance(
    status: str,
    practice: bool,
    expected: tuple[bool, bool],
) -> None:
    export = RosterPdfExport(
        "roster.pdf",
        b"%PDF-test",
        roster_status=status,
        roster_version=7,
    )

    assert page_shared._pdf_delivery_permissions(export, practice=practice) == expected


def test_export_option_changes_invalidate_prepared_file_bytes() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_shared.py").read_text(encoding="utf-8")
    export_flow = source.split("def _open_roster_export_dialog", 1)[1].split("def _tone_badge", 1)[0]

    assert "prepared_signature" in export_flow
    assert "_clear_png_delivery_view(png_delivery_view[0])" in export_flow
    assert "pdf_delivery_area[0].clear()" in export_flow
    assert "handle_checkbox_change(event, show_crest_state)" in export_flow
    assert "handle_checkbox_change(event, show_footer_note_state)" in export_flow
    assert 't("roster_export_options_changed")' in export_flow


def test_export_dialog_uses_generated_pdf_provenance_not_open_time_status() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_shared.py").read_text(encoding="utf-8")
    export_flow = source.split("def _open_roster_export_dialog", 1)[1].split("def _tone_badge", 1)[0]
    pdf_flow = export_flow.split("async def deliver_pdf", 1)[1].split("async def deliver_images", 1)[0]

    assert "_pdf_delivery_permissions(" in pdf_flow
    assert "export.roster_status" in pdf_flow
    assert "opened_as_published" not in pdf_flow
    assert "allow_native_share=allow_native_share" in pdf_flow
    assert "_deliver_prepared_roster_pdf(export, feedback=request_feedback)" in pdf_flow
