from __future__ import annotations

from copy import deepcopy
from datetime import date
from io import BytesIO
from threading import BoundedSemaphore
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageStat
import pytest

from nicegui_app.services import roster_document, roster_export, roster_image_export
from nicegui_app.services.roster_document import capture_roster_document
from nicegui_app.services.roster_export import build_roster_pdf
from nicegui_app.services.roster_image_export import (
    MAX_PNG_BYTES,
    PNG_MEDIA_TYPE,
    SERVICE_TIME_TEXT,
    RosterPngCapacityError,
    build_roster_png_bundle,
)
from nicegui_app.services.roster_presentation import (
    DAY_ORDER,
    ROSTER_ROWS,
    RosterCellState,
    build_roster_presentation,
)


@pytest.mark.parametrize(
    ("week_start", "language", "expected"),
    [
        (date(2026, 12, 28), "zh", "2026年12月28日—2027年1月1日"),
        (date(2026, 12, 28), "en", "28 DEC 2026 — 01 JAN 2027"),
        (date(2026, 9, 7), "zh", "2026年9月7日—9月11日"),
    ],
)
def test_png_week_range_identifies_both_years_when_week_crosses_new_year(
    week_start, language, expected,
) -> None:
    assert roster_image_export._week_range(week_start, language) == expected


class _SnapshotWorkflow:
    def __init__(
        self,
        week: dict[str, object],
        assignments: list[dict[str, object]],
    ) -> None:
        self.week = week
        self.assignments = assignments
        self.snapshot_calls = 0

    def roster_schedule_snapshot(
        self,
        roster_week_id: int,
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        assert roster_week_id == self.week["id"]
        self.snapshot_calls += 1
        return deepcopy(self.week), deepcopy(self.assignments)


def _snapshot(
    *,
    status: str = "published",
    version: int = 4,
    closed_days: tuple[str, ...] = (),
    unavailable_slots: tuple[str, ...] = (),
    vacancy: str | None = None,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    week: dict[str, object] = {
        "id": 42,
        "weekStart": date(2026, 9, 7),
        "status": status,
        "version": version,
        "closedDays": list(closed_days),
        "slotExceptions": [
            {"kind": "unavailable", "cellKey": cell_key}
            for cell_key in unavailable_slots
        ],
    }
    names = (
        "陳文",
        "李嘉明",
        "歐陽志明",
        "司徒歐陽諸葛孔明",
        "陳小明·",
        "黃國豪",
    )
    assignments: list[dict[str, object]] = []
    assignment_id = 1
    for day_index, day in enumerate(DAY_ORDER):
        for row_index, row in enumerate(ROSTER_ROWS):
            cell_key = f"{day.name}:{row.post.name}:{row.slot_index}"
            is_vacant = cell_key == vacancy
            assignments.append(
                {
                    "id": assignment_id,
                    "day": day.name,
                    "postCode": row.post.name,
                    "slotIndex": row.slot_index,
                    "prefectId": None if is_vacant else f"prefect-{assignment_id}",
                    "prefectName": None if is_vacant else names[(day_index + row_index) % len(names)],
                    "weight": 1.0,
                    "status": "vacant" if is_vacant else "active",
                }
            )
            assignment_id += 1
    return week, assignments


def _png_chunk_types(content: bytes) -> list[bytes]:
    assert content.startswith(b"\x89PNG\r\n\x1a\n")
    chunks: list[bytes] = []
    offset = 8
    while offset < len(content):
        length = int.from_bytes(content[offset : offset + 4], "big")
        chunk_type = content[offset + 4 : offset + 8]
        chunks.append(chunk_type)
        offset += 12 + length
        if chunk_type == b"IEND":
            break
    assert offset == len(content)
    return chunks


def _loaded_rgb_image(content: bytes) -> Image.Image:
    with Image.open(BytesIO(content)) as source:
        source.load()
        return source.convert("RGB")


def _presentation_cell_semantics(
    presentation: Any,
    language: str,
) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (
            cell.cell_key,
            cell.state.value,
            roster_image_export._cell_text(cell, language),
        )
        for row in presentation.rows
        for cell in row.cells
    )


def _pdf_table_cell_texts(
    table: Any,
    presentation: Any,
) -> tuple[str, ...]:
    """Expand ReportLab's whole-day column span back to its six cell semantics."""

    texts: list[str] = []
    for row_index, row in enumerate(presentation.rows, start=1):
        for column_index, cell in enumerate(row.cells, start=1):
            source_row = row_index
            if cell.state is RosterCellState.DAY_CLOSED:
                assert (
                    "SPAN",
                    (column_index, 1),
                    (column_index, -1),
                ) in table._spanCmds
                source_row = 1
            paragraph = table._cellvalues[source_row][column_index]
            texts.append(paragraph.getPlainText().strip())
    return tuple(texts)


def test_png_bundle_uses_one_atomic_snapshot_and_one_canonical_presentation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    week, assignments = _snapshot()
    workflow = _SnapshotWorkflow(week, assignments)
    real_builder = roster_document.build_roster_presentation
    presentation_calls = 0

    def counting_builder(*args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        nonlocal presentation_calls
        presentation_calls += 1
        return real_builder(*args, **kwargs)

    monkeypatch.setattr(roster_document, "build_roster_presentation", counting_builder)

    bundle = build_roster_png_bundle(workflow, 42, language="zh")

    assert workflow.snapshot_calls == 1
    assert presentation_calls == 1
    assert bundle.roster_status == "published"
    assert bundle.roster_version == 4
    assert bundle.avatar.filename == "SYSS_Roster_20260907_v4_Avatar_ZH.png"
    assert bundle.whatsapp.filename == "SYSS_Roster_20260907_v4_WhatsApp_ZH.png"
    assert bundle.avatar.kind == "avatar"
    assert bundle.whatsapp.kind == "whatsapp"

    for exported, expected_size in (
        (bundle.avatar, (1024, 1024)),
        (bundle.whatsapp, (1600, 2000)),
    ):
        assert exported.media_type == PNG_MEDIA_TYPE
        assert (exported.width, exported.height) == expected_size
        assert len(exported.content) <= MAX_PNG_BYTES
        assert set(_png_chunk_types(exported.content)) == {b"IHDR", b"IDAT", b"IEND"}
        with Image.open(BytesIO(exported.content)) as image:
            assert image.format == "PNG"
            assert image.mode == "RGB"
            assert image.size == expected_size
            assert image.info == {}


def test_pdf_avatar_and_detail_share_the_same_thirty_cell_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    week, assignments = _snapshot(
        closed_days=("WEDNESDAY",),
        unavailable_slots=("MONDAY:ROOM_302:1",),
        vacancy="MONDAY:ROOM_303:1",
    )
    presentation = build_roster_presentation(week, assignments)
    workflow = _SnapshotWorkflow(week, assignments)
    expected = _presentation_cell_semantics(presentation, "zh")
    presentation_inputs: list[tuple[dict[str, object], list[dict[str, object]]]] = []
    captured_tables: list[Any] = []
    rendered_png_cells: list[tuple[str, str, str]] = []
    real_schedule_grid = roster_export._schedule_grid
    real_cell_text = roster_image_export._cell_text

    def fixed_presentation(
        snapshot_week: dict[str, object],
        snapshot_assignments: list[dict[str, object]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        del args, kwargs
        assert snapshot_week["id"] == week["id"]
        assert snapshot_week["version"] == week["version"]
        assert list(snapshot_assignments) == assignments
        presentation_inputs.append((snapshot_week, snapshot_assignments))
        return presentation

    def capturing_schedule_grid(*args: Any, **kwargs: Any) -> Any:
        table = real_schedule_grid(*args, **kwargs)
        captured_tables.append(table)
        return table

    def recording_cell_text(cell: Any, language: str) -> str:
        value = real_cell_text(cell, language)
        rendered_png_cells.append((cell.cell_key, cell.state.value, value))
        return value

    monkeypatch.setattr(roster_document, "build_roster_presentation", fixed_presentation)
    monkeypatch.setattr(roster_export, "_schedule_grid", capturing_schedule_grid)
    monkeypatch.setattr(roster_image_export, "_cell_text", recording_cell_text)

    document = capture_roster_document(workflow, 42)
    pdf = roster_export.render_roster_pdf(document, language="zh")
    pngs = roster_image_export.render_roster_png_bundle(document, language="zh")

    assert pdf.content.startswith(b"%PDF")
    assert pngs.avatar.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert pngs.whatsapp.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert workflow.snapshot_calls == 1
    assert len(presentation_inputs) == 1
    assert len(captured_tables) == 1
    assert len(expected) == len(DAY_ORDER) * len(ROSTER_ROWS) == 30
    pdf_cells = _pdf_table_cell_texts(captured_tables[0], presentation)
    avatar_cells = tuple(rendered_png_cells[:30])
    detail_cells = tuple(rendered_png_cells[30:])
    assert tuple(item[2] for item in expected) == pdf_cells
    assert avatar_cells == expected
    assert detail_cells == expected


def test_png_bundle_is_deterministic_and_practice_names_are_stable() -> None:
    week, assignments = _snapshot(status="draft", version=7)
    clean = build_roster_png_bundle(
        _SnapshotWorkflow(week, assignments),
        42,
        language="en",
        practice=False,
    )
    first = build_roster_png_bundle(
        _SnapshotWorkflow(week, assignments),
        42,
        language="en",
        practice=True,
    )
    second = build_roster_png_bundle(
        _SnapshotWorkflow(week, assignments),
        42,
        language="en",
        practice=True,
    )

    assert first.avatar.filename == "PRACTICE_SYSS_Roster_20260907_v7_Avatar_EN.png"
    assert first.whatsapp.filename == "PRACTICE_SYSS_Roster_20260907_v7_WhatsApp_EN.png"
    assert first.avatar.content == second.avatar.content
    assert first.whatsapp.content == second.whatsapp.content
    for clean_file, practice_file, layout in (
        (clean.avatar, first.avatar, roster_image_export._AVATAR_LAYOUT),
        (clean.whatsapp, first.whatsapp, roster_image_export._WHATSAPP_LAYOUT),
    ):
        clean_image = _loaded_rgb_image(clean_file.content)
        practice_image = _loaded_rgb_image(practice_file.content)
        difference = ImageChops.difference(clean_image, practice_image)
        assert difference.getbbox() is not None
        assert difference.crop(layout.grid_box).getbbox() is not None


def test_both_pngs_attempt_every_day_row_name_time_and_semantic_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    week, assignments = _snapshot(
        closed_days=("WEDNESDAY",),
        unavailable_slots=("MONDAY:ROOM_302:1",),
        vacancy="MONDAY:ROOM_303:1",
    )
    workflow = _SnapshotWorkflow(week, assignments)
    presentation = build_roster_presentation(week, assignments)
    real_draw = roster_image_export._draw_fitted_text
    real_cell_text = roster_image_export._cell_text
    rendered_text: list[str] = []
    rendered_cells: list[tuple[RosterCellState, str]] = []

    def recording_draw(draw: Any, text: str, *args: Any, **kwargs: Any) -> None:
        rendered_text.append(text)
        real_draw(draw, text, *args, **kwargs)

    def recording_cell_text(cell: Any, language: str) -> str:
        value = real_cell_text(cell, language)
        rendered_cells.append((cell.state, value))
        return value

    monkeypatch.setattr(roster_image_export, "_draw_fitted_text", recording_draw)
    monkeypatch.setattr(roster_image_export, "_cell_text", recording_cell_text)

    build_roster_png_bundle(workflow, 42, language="zh")

    assert rendered_text.count(SERVICE_TIME_TEXT) == len(ROSTER_ROWS) * 2
    assert len(rendered_cells) == len(DAY_ORDER) * len(ROSTER_ROWS) * 2
    expected_cells = [
        (cell.state, real_cell_text(cell, "zh"))
        for row in presentation.rows
        for cell in row.cells
    ]
    assert rendered_cells == expected_cells * 2
    for row in ROSTER_ROWS:
        assert rendered_text.count(row.display_label) == 2
    for day in presentation.days:
        assert rendered_text.count(
            f"{day.label_zh}\n{day.duty_date.month}月{day.duty_date.day}日"
        ) == 2
    assigned_names = {
        cell.prefect_name
        for row in presentation.rows
        for cell in row.cells
        if cell.state is RosterCellState.ASSIGNED
    }
    assert assigned_names <= set(rendered_text)
    assert {"空缺", "本週不開放", "不開放", "全天不開放"} <= set(rendered_text)


def test_english_withdrawn_pngs_render_weekdays_dates_status_and_all_cell_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    week, assignments = _snapshot(
        status="withdrawn",
        version=9,
        closed_days=("WEDNESDAY",),
        unavailable_slots=("MONDAY:ROOM_302:1",),
        vacancy="MONDAY:ROOM_303:1",
    )
    presentation = build_roster_presentation(week, assignments)
    rendered_text: list[str] = []
    real_draw = roster_image_export._draw_fitted_text

    def recording_draw(draw: Any, text: str, *args: Any, **kwargs: Any) -> None:
        rendered_text.append(text)
        real_draw(draw, text, *args, **kwargs)

    monkeypatch.setattr(roster_image_export, "_draw_fitted_text", recording_draw)

    bundle = build_roster_png_bundle(
        _SnapshotWorkflow(week, assignments),
        42,
        language="en",
    )

    assert bundle.roster_status == "withdrawn"
    assert bundle.roster_version == 9
    assert rendered_text.count("WITHDRAWN · DO NOT DISTRIBUTE · v9") == 2
    for day in presentation.days:
        expected_heading = (
            f"{day.label_en.upper()}\n"
            f"{day.duty_date.day:02d} {roster_image_export._MONTHS[day.duty_date.month - 1]}"
        )
        assert rendered_text.count(expected_heading) == 2
    assert {"Vacant", "Unavailable", "Closed", "Closed all day"} <= set(rendered_text)


def test_avatar_round_crop_and_48_96_320_pixel_evidence_preserve_matrix_structure() -> None:
    week, assignments = _snapshot(
        closed_days=("WEDNESDAY",),
        unavailable_slots=("MONDAY:ROOM_302:1",),
        vacancy="MONDAY:ROOM_303:1",
    )
    avatar = build_roster_png_bundle(
        _SnapshotWorkflow(week, assignments),
        42,
        language="zh",
    ).avatar
    image = _loaded_rgb_image(avatar.content)
    background = Image.new("RGB", image.size, image.getpixel((0, 0)))
    circle_mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(circle_mask).ellipse(
        (0, 0, image.width - 1, image.height - 1),
        fill=255,
    )
    meaningful_pixels = ImageChops.difference(image, background)
    outside_circle = Image.composite(
        meaningful_pixels,
        Image.new("RGB", image.size, "black"),
        ImageOps.invert(circle_mask),
    )
    assert outside_circle.getbbox() is None

    circular_crop = Image.composite(image, background, circle_mask)
    for edge in (48, 96, 320):
        thumbnail = circular_crop.resize((edge, edge), Image.Resampling.LANCZOS)
        scale = edge / image.width
        grid_box = tuple(
            round(coordinate * scale)
            for coordinate in roster_image_export._AVATAR_LAYOUT.grid_box
        )
        matrix = ImageOps.grayscale(thumbnail.crop(grid_box))
        histogram = matrix.histogram()
        pixel_count = matrix.width * matrix.height
        assert ImageStat.Stat(matrix).stddev[0] > 40
        assert sum(histogram[:130]) / pixel_count > 0.20
        assert sum(histogram[181:]) / pixel_count > 0.40

        evidence = BytesIO()
        thumbnail.save(evidence, format="PNG")
        with Image.open(BytesIO(evidence.getvalue())) as verified:
            verified.load()
            assert verified.size == (edge, edge)
            assert verified.mode == "RGB"


def test_adjusted_vn_plus_one_changes_filenames_and_the_affected_cell_pixels() -> None:
    week, assignments = _snapshot(status="published", version=4)
    original = build_roster_png_bundle(
        _SnapshotWorkflow(week, assignments),
        42,
        language="zh",
    )
    adjusted_week = deepcopy(week)
    adjusted_assignments = deepcopy(assignments)
    adjusted_week["version"] = 5
    adjusted_assignments[0]["prefectName"] = "趙志明"
    adjusted = build_roster_png_bundle(
        _SnapshotWorkflow(adjusted_week, adjusted_assignments),
        42,
        language="zh",
    )

    assert original.avatar.filename == "SYSS_Roster_20260907_v4_Avatar_ZH.png"
    assert adjusted.avatar.filename == "SYSS_Roster_20260907_v5_Avatar_ZH.png"
    assert original.whatsapp.filename == "SYSS_Roster_20260907_v4_WhatsApp_ZH.png"
    assert adjusted.whatsapp.filename == "SYSS_Roster_20260907_v5_WhatsApp_ZH.png"
    assert original.avatar.content != adjusted.avatar.content
    assert original.whatsapp.content != adjusted.whatsapp.content

    layout = roster_image_export._AVATAR_LAYOUT
    left, top, right, bottom = layout.grid_box
    first_data_left = left + layout.first_column_width
    day_width = (right - first_data_left) / len(DAY_ORDER)
    row_height = (bottom - top - layout.header_height) / len(ROSTER_ROWS)
    changed_cell_box = (
        first_data_left + 2,
        top + layout.header_height + 2,
        round(first_data_left + day_width) - 2,
        round(top + layout.header_height + row_height) - 2,
    )
    cell_difference = ImageChops.difference(
        _loaded_rgb_image(original.avatar.content).crop(changed_cell_box),
        _loaded_rgb_image(adjusted.avatar.content).crop(changed_cell_box),
    )
    assert cell_difference.getbbox() is not None


def test_image_export_rejects_invalid_language_and_unfittable_name() -> None:
    week, assignments = _snapshot()
    with pytest.raises(ValueError, match="language"):
        build_roster_png_bundle(  # type: ignore[arg-type]
            _SnapshotWorkflow(week, assignments),
            42,
            language="fr",
        )

    assignments[0]["prefectName"] = "超" * 200
    with pytest.raises(ValueError, match="does not fit"):
        build_roster_png_bundle(
            _SnapshotWorkflow(week, assignments),
            42,
            language="zh",
        )

    assignments[0]["prefectName"] = ""
    with pytest.raises(ValueError, match="prefect name"):
        build_roster_png_bundle(
            _SnapshotWorkflow(week, assignments),
            42,
            language="zh",
        )


def test_png_renderer_fails_fast_above_global_and_practice_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(roster_image_export, "_PNG_RENDER_SLOTS", BoundedSemaphore(2))
    monkeypatch.setattr(
        roster_image_export,
        "_PRACTICE_RENDER_SLOTS",
        BoundedSemaphore(1),
    )

    with roster_image_export._claim_png_render_slot(practice=False):
        with roster_image_export._claim_png_render_slot(practice=False):
            with pytest.raises(RosterPngCapacityError, match="at capacity"):
                with roster_image_export._claim_png_render_slot(practice=False):
                    pass

    with roster_image_export._claim_png_render_slot(practice=True):
        with pytest.raises(RosterPngCapacityError, match="Practice"):
            with roster_image_export._claim_png_render_slot(practice=True):
                pass
