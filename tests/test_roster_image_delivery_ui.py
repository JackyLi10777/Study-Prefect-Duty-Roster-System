from __future__ import annotations

from types import SimpleNamespace

import pytest

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui import page_shared
from nicegui_app.ui.i18n import EN, MESSAGES, ZH_HK


def _export_flow_source() -> str:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_shared.py").read_text(encoding="utf-8")
    return source.split("def _open_roster_export_dialog", 1)[1].split("def _tone_badge", 1)[0]


def test_roster_image_preparation_uses_one_bundle_and_exact_png_delivery() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_shared.py").read_text(encoding="utf-8")
    preparation = source.split("async def _prepare_roster_png_bundle", 1)[1].split(
        "def _png_data_url", 1
    )[0]
    ready = source.split("def _render_png_delivery_ready", 1)[1].split(
        "def _open_roster_export_dialog", 1
    )[0]

    assert "build_roster_png_bundle(" in preparation
    assert "workflow," in preparation
    assert "roster_week_id," in preparation
    assert "language=language" in preparation
    assert "practice=practice" in preparation
    assert "bundle.avatar" in ready
    assert "bundle.whatsapp" in ready
    assert 'media_type="image/png"' in ready
    assert "build_native_file_share_from_data_url_js(" in ready
    assert 'preview_selector=f"#c{detail_image.id}"' in ready
    assert "can_offer_native_file_share(" in ready


def test_page_pdf_and_png_all_use_the_atomic_canonical_roster_presentation(monkeypatch) -> None:
    from nicegui_app.services.roster_document import capture_roster_document
    from nicegui_app.services.roster_export import render_roster_pdf
    from nicegui_app.services.roster_image_export import render_roster_png_bundle
    from tests.test_export_callback_lifecycle import Element, UI
    from tests.test_roster_document import Source

    source = Source()
    document = capture_roster_document(source, 42)
    source.week["version"] = 5
    source.assignments[0]["prefectName"] = "另一版本姓名"
    ui = UI()
    tables = []

    def table(**kwargs):
        tables.append(kwargs)
        return Element(ui)

    ui.table = table
    monkeypatch.setattr(page_shared, "ui", ui)
    monkeypatch.setattr(page_shared, "t", lambda key: key)
    monkeypatch.setattr(page_shared, "day_label", lambda day: day.name)
    page_shared._render_roster_table(document.presentation)
    pdf = render_roster_pdf(document, language="en")
    images = render_roster_png_bundle(document)

    assert source.calls == 1
    assert pdf.roster_version == images.roster_version == 4
    assert len(tables) == 1 and len(tables[0]["rows"]) == 6
    assert len(tables[0]["columns"]) == 6
    state_labels = {"room_closed": "closed", "day_closed": "draft_day_closed",
                    "unavailable": "draft_slot_unavailable", "vacant": "vacant"}
    for row, expected in zip(tables[0]["rows"], document.presentation.rows, strict=True):
        assert row["postDisplay"] == expected.spec.display_label + " · 15:40–17:00"
        assert row["time"] == "15:40–17:00"
        for cell in expected.cells:
            assert row[cell.day.name.lower()] == (
                cell.prefect_name if cell.state.value == "assigned" else state_labels[cell.state.value]
            )
    for column, day in zip(tables[0]["columns"][1:], document.presentation.days, strict=True):
        assert str(day.duty_date) in column["label"]
    assert sum('data-testid="mobile-roster-card"' in element.props_text for element in ui.elements) == 30
    assert "另一版本姓名" not in [element.text for element in ui.elements]


def test_roster_image_download_rejects_a_mismatched_media_type_before_delivery() -> None:
    image = SimpleNamespace(
        content=b"not-an-image",
        filename="roster.jpg",
        media_type="image/jpeg",
    )

    with pytest.raises(ValueError, match="image/png"):
        page_shared._download_roster_png(image)  # type: ignore[arg-type]

    forged = SimpleNamespace(
        content=b"not-a-png",
        filename="roster.png",
        media_type="image/png",
    )
    with pytest.raises(ValueError, match="valid bounded image/png"):
        page_shared._download_roster_png(forged)  # type: ignore[arg-type]


def test_export_dialog_separates_formal_draft_guest_and_withdrawn_delivery() -> None:
    export_flow = _export_flow_source()
    weekly_source = (
        PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "weekly.py"
    ).read_text(encoding="utf-8")

    assert 'roster_status == "withdrawn"' in export_flow
    assert "opened_as_published = roster_status == \"published\"" in export_flow
    assert 'bundle.roster_status == "published" and not practice' in export_flow
    assert 'practice and bundle.roster_status in {"draft", "published"}' in export_flow
    assert "allow_native_share=bundle_is_formal_published" in export_flow
    assert 't("generate_draft_image_preview")' in export_flow
    assert 't("generate_download_avatar")' in export_flow
    assert "_download_roster_png(bundle.avatar, feedback=request_feedback)" in export_flow
    for test_id in (
        "roster-export-dialog",
        "roster-export-language",
        "prepare-roster-images",
        "pdf-advanced-options",
        "prepare-roster-pdf",
        "close-roster-export",
    ):
        assert test_id in export_flow
    assert "data-testid=open-roster-export" in weekly_source


def test_export_option_change_drops_prepared_image_bytes_and_previews() -> None:
    export_flow = _export_flow_source()

    assert "prepared_bundle" in export_flow
    assert "prepared_bundle[0] = None" in export_flow
    assert "reset_delivery_views()" in export_flow
    assert "handle_language_change" in export_flow
    assert "handle_checkbox_change" in export_flow
    assert "def build_advanced_options()" in export_flow
    assert 't("roster_export_options_changed")' in export_flow


def test_export_close_uses_native_modal_and_releases_previews_and_bytes() -> None:
    export_flow = _export_flow_source()

    assert "with semantic_native_dialog(" in export_flow
    assert 'dialog.run_method("showModal")' in export_flow
    assert 'dialog.run_method("close")' in export_flow
    assert "def release_export_dialog_resources()" in export_flow
    assert "prepared_signature[0] = None" in export_flow
    assert "prepared_bundle[0] = None" in export_flow
    assert "_clear_png_delivery_view(png_delivery_view[0])" in export_flow
    assert 'run_method("removeAttribute", "src")' in (
        (PROJECT_ROOT / "nicegui_app" / "ui" / "page_shared.py").read_text(encoding="utf-8")
    )
    assert "finish_export_dialog_close()" in export_flow
    assert 'getattr(client, "_sy_roster_export_dialogs", None)' in export_flow
    assert "call_later(_DIALOG_DISMISSAL_SECONDS" not in export_flow


def test_roster_image_delivery_copy_is_bilingual_and_explicit_about_whatsapp_boundaries() -> None:
    required = {
        "roster_image_export_title",
        "roster_image_export_notice",
        "generate_download_avatar",
        "generate_draft_image_preview",
        "roster_images_ready_notice",
        "roster_images_draft_notice",
        "roster_images_practice_notice",
        "download_roster_avatar",
        "download_roster_detail",
        "share_roster_detail",
        "roster_export_options_changed",
    }

    assert required <= MESSAGES.keys()
    assert all(MESSAGES[key][locale].strip() for key in required for locale in (ZH_HK, EN))
    assert "不會代你" in MESSAGES["roster_image_export_notice"][ZH_HK]
    assert "never chooses" in MESSAGES["roster_image_export_notice"][EN]
    assert "PRACTICE" in MESSAGES["roster_images_practice_notice"][ZH_HK]


def test_adjustment_receipt_warns_that_both_pdf_and_png_are_stale() -> None:
    assert "PDF／PNG" in MESSAGES["adjustment_old_pdf_warning"][ZH_HK]
    assert "PDF/PNG" in MESSAGES["adjustment_old_pdf_warning"][EN]
    assert "群組頭像" in MESSAGES["adjustment_old_pdf_warning"][ZH_HK]
    assert "group icon" in MESSAGES["adjustment_old_pdf_warning"][EN]


def test_ready_preview_does_not_claim_device_download_has_completed() -> None:
    # A ticket admission cannot prove that the browser saved a file to disk.
    assert "已下載" not in MESSAGES["roster_images_ready_notice"][ZH_HK]
    assert "has downloaded" not in MESSAGES["roster_images_ready_notice"][EN]
