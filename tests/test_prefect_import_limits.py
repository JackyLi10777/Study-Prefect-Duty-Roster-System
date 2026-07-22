from __future__ import annotations

import asyncio
import json

from nicegui_app.ui.i18n_catalog.importing import MESSAGES
from nicegui_app.ui.page_routes import people
from nicegui_app.utils.prefect_import import parse_prefect_import_rows, parse_prefect_import_text
from nicegui_app.utils.prefect_import_limits import (
    MAX_IMPORT_BYTES,
    MAX_IMPORT_CELL_CHARACTERS,
    MAX_IMPORT_COLUMNS,
    MAX_IMPORT_ROWS,
)


VALID_ROW = {
    "姓名": "測試甲",
    "級別": "F.3",
    "班別": "3A",
    "職務": "導學風紀",
    "可值班日": "星期一、星期三",
}


def test_pasted_import_rejects_oversized_content_before_parsing() -> None:
    preview = parse_prefect_import_text("x" * (MAX_IMPORT_BYTES + 1))

    assert preview.rows == ()
    assert "larger than 2 MB" in preview.issues[0]


def test_pasted_csv_rejects_excess_rows_columns_and_cell_length() -> None:
    too_many_rows = "姓名\n" + "\n".join(f"測試{i}" for i in range(MAX_IMPORT_ROWS + 1))
    row_preview = parse_prefect_import_text(too_many_rows)

    headers = ",".join(f"欄{i}" for i in range(MAX_IMPORT_COLUMNS + 1))
    values = ",".join("值" for _ in range(MAX_IMPORT_COLUMNS + 1))
    column_preview = parse_prefect_import_text(f"{headers}\n{values}")

    long_cell = "姓名,級別,班別,職務,可值班日,備註\n測試甲,F.3,3A,導學風紀,星期一," + (
        "字" * (MAX_IMPORT_CELL_CHARACTERS + 1)
    )
    cell_preview = parse_prefect_import_text(long_cell)

    assert "more than 2,000" in row_preview.issues[0]
    assert "more than 50 columns" in column_preview.issues[0]
    assert "longer than 4,096" in cell_preview.issues[0]


def test_pasted_csv_rejects_blank_and_duplicate_chinese_name_headings() -> None:
    blank = parse_prefect_import_text(
        "姓名,,班別,職務,可值班日\n測試甲,F.3,3A,導學風紀,星期一"
    )
    duplicate = parse_prefect_import_text(
        "姓名,姓名,班別,職務,可值班日\n測試甲,F.3,3A,導學風紀,星期一"
    )

    assert blank.rows == ()
    assert "Every imported column must have a heading" in blank.issues[0]
    assert duplicate.rows == ()
    assert "Column headings must be unique" in duplicate.issues[0]


def test_pasted_json_rejects_excessive_depth_but_accepts_flat_prefect_rows() -> None:
    deeply_nested = "[" * 9 + "]" * 9
    rejected = parse_prefect_import_text(deeply_nested)
    accepted = parse_prefect_import_text(json.dumps([VALID_ROW], ensure_ascii=False))

    assert "nested too deeply" in rejected.issues[0]
    assert accepted.issues == ()
    assert accepted.rows[0].name_zh == "測試甲"


def test_direct_row_normalisation_uses_the_same_resource_boundaries() -> None:
    preview = parse_prefect_import_rows([VALID_ROW] * (MAX_IMPORT_ROWS + 1))

    assert preview.rows == ()
    assert "more than 2,000" in preview.issues[0]


def test_pasted_parser_is_dispatched_off_the_ui_event_loop(monkeypatch) -> None:
    calls: list[tuple[object, tuple[object, ...]]] = []

    async def fake_io_bound(function, *args):
        calls.append((function, args))
        return function(*args)

    monkeypatch.setattr(people.run, "io_bound", fake_io_bound)

    preview = asyncio.run(
        people._parse_pasted_prefects_off_loop(json.dumps([VALID_ROW], ensure_ascii=False))
    )

    assert preview.issues == ()
    assert calls == [(parse_prefect_import_text, (json.dumps([VALID_ROW], ensure_ascii=False),))]


def test_upload_rejects_reported_oversize_before_reading_payload() -> None:
    class OversizedUpload:
        read_calls = 0

        def size(self) -> int:
            return MAX_IMPORT_BYTES + 1

        async def read(self) -> bytes:
            self.read_calls += 1
            return b"should-not-be-read"

    upload = OversizedUpload()

    try:
        asyncio.run(people._read_prefect_upload_with_limit(upload))
    except people.PrefectFileImportError as error:
        assert error.code == "too_large"
    else:
        raise AssertionError("oversized upload should be rejected")

    assert upload.read_calls == 0


def test_upload_size_guard_supports_async_size_and_normalizes_binary_payload() -> None:
    class AsyncSizedUpload:
        async def size(self) -> int:
            return 4

        async def read(self) -> bytearray:
            return bytearray(b"test")

    content = asyncio.run(people._read_prefect_upload_with_limit(AsyncSizedUpload()))

    assert content == b"test"
    assert isinstance(content, bytes)


def test_upload_rechecks_actual_payload_length_after_reported_size() -> None:
    class InconsistentUpload:
        def size(self) -> int:
            return 1

        async def read(self) -> bytes:
            return b"x" * (MAX_IMPORT_BYTES + 1)

    try:
        asyncio.run(people._read_prefect_upload_with_limit(InconsistentUpload()))
    except people.PrefectFileImportError as error:
        assert error.code == "too_large"
    else:
        raise AssertionError("the actual payload must retain the same hard limit")


def test_clipboard_capability_is_rechecked_for_every_protected_operation(monkeypatch) -> None:
    decisions = iter((True, False))
    checks: list[object] = []
    denied: list[bool] = []
    notifications: list[tuple[str, str | None]] = []

    def fake_allows(capability) -> bool:
        checks.append(capability)
        return next(decisions)

    monkeypatch.setattr(people, "_allows", fake_allows)
    monkeypatch.setattr(people, "t", lambda key, **_values: key)
    monkeypatch.setattr(
        people.ui,
        "notify",
        lambda message, *, type=None, **_values: notifications.append((message, type)),
    )

    assert people._require_clipboard_ingest(lambda: denied.append(True)) is True
    assert people._require_clipboard_ingest(lambda: denied.append(True)) is False
    assert checks == [people.Capability.CLIPBOARD_INGEST, people.Capability.CLIPBOARD_INGEST]
    assert denied == [True]
    assert notifications == [("access_restricted_title", "warning")]


def test_upload_read_failure_records_a_safe_reference_and_gives_a_retry(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_record(error, *, action):
        captured.update(error=error, action=action)
        return "OP-1234ABCD"

    monkeypatch.setattr(people, "record_operator_failure", fake_record)
    monkeypatch.setattr(people, "t", lambda key, **values: f"{key}:{values['reference']}")
    error = OSError("simulated disconnected upload")

    message = people._prefect_upload_read_failure_text(error)

    assert message == "prefect_file_read_failed:OP-1234ABCD"
    assert captured == {"error": error, "action": "prefect_file_upload_read"}
    for locale in ("zh-HK", "en"):
        assert "{reference}" in MESSAGES["prefect_file_read_failed"][locale]
