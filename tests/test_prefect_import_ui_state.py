from __future__ import annotations

from nicegui_app.ui.page_routes.people import (
    _prefect_file_preview_fingerprint,
    _prefect_text_preview_fingerprint,
)


def test_preview_fingerprint_is_order_independent_for_mapping() -> None:
    left = _prefect_file_preview_fingerprint(
        filename="prefects.csv",
        content=b"fictional-prefects",
        sheet_name=None,
        mapping={"name_zh": "Name", "form": "Form"},
    )
    right = _prefect_file_preview_fingerprint(
        filename="PREFECTS.CSV",
        content=b"fictional-prefects",
        sheet_name=None,
        mapping={"form": "Form", "name_zh": "Name"},
    )

    assert left == right


def test_preview_fingerprint_changes_for_each_operator_controlled_input() -> None:
    baseline = _prefect_file_preview_fingerprint(
        filename="prefects.xlsx",
        content=b"workbook-one",
        sheet_name="Week 1",
        mapping={"name_zh": "Name", "form": "Form"},
    )

    assert baseline != _prefect_file_preview_fingerprint(
        filename="prefects.xlsx",
        content=b"workbook-two",
        sheet_name="Week 1",
        mapping={"name_zh": "Name", "form": "Form"},
    )
    assert baseline != _prefect_file_preview_fingerprint(
        filename="prefects.xlsx",
        content=b"workbook-one",
        sheet_name="Week 2",
        mapping={"name_zh": "Name", "form": "Form"},
    )
    assert baseline != _prefect_file_preview_fingerprint(
        filename="prefects.xlsx",
        content=b"workbook-one",
        sheet_name="Week 1",
        mapping={"name_zh": "Chinese Name", "form": "Form"},
    )


def test_pasted_preview_fingerprint_is_bound_to_exact_reviewed_text() -> None:
    reviewed = "姓名,級別,班別\n虛構甲,F.3,3A"

    assert _prefect_text_preview_fingerprint(reviewed) == _prefect_text_preview_fingerprint(reviewed)
    assert _prefect_text_preview_fingerprint(reviewed) != _prefect_text_preview_fingerprint(
        "姓名,級別,班別\n虛構乙,F.3,3A"
    )
    assert _prefect_text_preview_fingerprint(reviewed) != _prefect_text_preview_fingerprint(f"{reviewed}\n")
