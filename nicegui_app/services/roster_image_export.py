"""Deterministic in-memory PNG exports for roster distribution.

The renderer consumes the same atomic workflow snapshot and canonical
presentation model as the local PDF export.  It never writes a temporary file
or embeds roster data as PNG metadata.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from threading import BoundedSemaphore
from typing import TYPE_CHECKING, Literal

from PIL import Image, ImageDraw, ImageFont, ImageOps

from nicegui_app.config import DISPLAY_PRINT_CREST_PATH, PROJECT_ROOT
from nicegui_app.services.roster_document import RosterDocument, capture_roster_document
from nicegui_app.services.roster_presentation import (
    RosterCellState,
    RosterScheduleCell,
    RosterSchedulePresentation,
)
from roster_policy import DutyPost

if TYPE_CHECKING:
    from nicegui_app.services.roster_workflow import RosterWorkflow


ExportLanguage = Literal["zh", "en"]
RosterPngKind = Literal["avatar", "whatsapp"]

PNG_MEDIA_TYPE = "image/png"
MAX_PNG_BYTES = 5 * 1024 * 1024
SERVICE_TIME_TEXT = "15:40–17:00"

_PNG_RENDER_SLOTS = BoundedSemaphore(2)
_PRACTICE_RENDER_SLOTS = BoundedSemaphore(1)

_TEAL = "#147E76"
_TEAL_DEEP = "#0C625C"
_GOLD = "#D3A930"
_GRID = "#B7C9CF"
_INK = "#17333A"
_MUTED = "#5E7377"
_CLOSED = "#EEF3F4"
_DAY_CLOSED = "#E4E8EC"
_DAY_CLOSED_HEADER = "#596674"
_CANVAS = "#FBFDFC"
_VACANT = "#8F1D14"

_ROW_BACKGROUNDS = {
    DutyPost.ASSIST_IN_CHARGE: "#FFF9E7",
    DutyPost.ROOM_302: "#EEF9F2",
    DutyPost.ROOM_303: "#FFF3F3",
    DutyPost.ROOM_202: "#FFF8ED",
}

_MONTHS = (
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
)


@dataclass(frozen=True, slots=True)
class RosterPngFile:
    """One bounded PNG payload ready for the existing download bridge."""

    filename: str
    media_type: str
    content: bytes
    width: int
    height: int
    kind: RosterPngKind


@dataclass(frozen=True, slots=True)
class RosterPngBundle:
    """Avatar and message-friendly exports from one roster snapshot."""

    avatar: RosterPngFile
    whatsapp: RosterPngFile
    roster_status: str
    roster_version: int


class RosterPngCapacityError(RuntimeError):
    """Raised immediately when the bounded in-memory renderer is occupied."""


@dataclass(frozen=True, slots=True)
class _Layout:
    width: int
    height: int
    kind: RosterPngKind
    crest_box: tuple[int, int, int, int]
    title_box: tuple[int, int, int, int]
    week_box: tuple[int, int, int, int]
    status_box: tuple[int, int, int, int]
    grid_box: tuple[int, int, int, int]
    first_column_width: int
    header_height: int
    footer_box: tuple[int, int, int, int] | None
    title_size: int
    day_size: int
    post_size: int
    time_size: int
    name_size: int
    state_size: int
    line_width: int


_AVATAR_LAYOUT = _Layout(
    width=1024,
    height=1024,
    kind="avatar",
    crest_box=(474, 58, 550, 134),
    title_box=(162, 142, 862, 194),
    week_box=(185, 199, 839, 232),
    status_box=(185, 237, 839, 271),
    # Every grid corner remains inside the circular crop used by WhatsApp.
    grid_box=(160, 290, 864, 842),
    first_column_width=200,
    header_height=64,
    footer_box=(220, 875, 804, 905),
    title_size=28,
    day_size=16,
    post_size=13,
    time_size=12,
    name_size=17,
    state_size=14,
    line_width=2,
)

_WHATSAPP_LAYOUT = _Layout(
    width=1600,
    height=2000,
    kind="whatsapp",
    crest_box=(720, 65, 880, 225),
    title_box=(100, 235, 1500, 315),
    week_box=(160, 325, 1440, 375),
    status_box=(160, 382, 1440, 435),
    grid_box=(70, 470, 1530, 1680),
    first_column_width=380,
    header_height=150,
    footer_box=(100, 1780, 1500, 1855),
    title_size=50,
    day_size=28,
    post_size=24,
    time_size=22,
    name_size=34,
    state_size=28,
    line_width=3,
)


def build_roster_png_bundle(
    workflow: "RosterWorkflow",
    roster_week_id: int,
    *,
    language: ExportLanguage = "zh",
    practice: bool = False,
) -> RosterPngBundle:
    """Convenience entrypoint: capture once, then render the immutable document."""

    return render_roster_png_bundle(
        capture_roster_document(workflow, roster_week_id), language=language, practice=practice
    )


def render_roster_png_bundle(
    document: RosterDocument,
    *,
    language: ExportLanguage = "zh",
    practice: bool = False,
) -> RosterPngBundle:
    """Build both PNGs from one document, without any workflow reads."""

    if language not in {"zh", "en"}:
        raise ValueError("Roster image language must be 'zh' or 'en'.")

    with _claim_png_render_slot(practice=practice):
        presentation = document.presentation
        avatar_content = _render_schedule_png(
            presentation,
            language=language,
            practice=practice,
            layout=_AVATAR_LAYOUT,
        )
        whatsapp_content = _render_schedule_png(
            presentation,
            language=language,
            practice=practice,
            layout=_WHATSAPP_LAYOUT,
        )
    prefix = "PRACTICE_" if practice else ""
    language_code = "ZH" if language == "zh" else "EN"
    stem = (
        f"{prefix}SYSS_Roster_{presentation.week_start:%Y%m%d}"
        f"_v{presentation.version}"
    )
    avatar = RosterPngFile(
        filename=f"{stem}_Avatar_{language_code}.png",
        media_type=PNG_MEDIA_TYPE,
        content=avatar_content,
        width=_AVATAR_LAYOUT.width,
        height=_AVATAR_LAYOUT.height,
        kind="avatar",
    )
    whatsapp = RosterPngFile(
        filename=f"{stem}_WhatsApp_{language_code}.png",
        media_type=PNG_MEDIA_TYPE,
        content=whatsapp_content,
        width=_WHATSAPP_LAYOUT.width,
        height=_WHATSAPP_LAYOUT.height,
        kind="whatsapp",
    )
    return RosterPngBundle(
        avatar=avatar,
        whatsapp=whatsapp,
        roster_status=presentation.status,
        roster_version=presentation.version,
    )


@contextmanager
def _claim_png_render_slot(*, practice: bool) -> Iterator[None]:
    """Bound peak image memory and reject excess work without queueing the UI."""

    if not _PNG_RENDER_SLOTS.acquire(blocking=False):
        raise RosterPngCapacityError("Roster image renderer is currently at capacity.")
    practice_claimed = False
    try:
        if practice:
            practice_claimed = _PRACTICE_RENDER_SLOTS.acquire(blocking=False)
            if not practice_claimed:
                raise RosterPngCapacityError(
                    "Practice roster image renderer is currently at capacity."
                )
        yield
    finally:
        if practice_claimed:
            _PRACTICE_RENDER_SLOTS.release()
        _PNG_RENDER_SLOTS.release()


def _render_schedule_png(
    presentation: RosterSchedulePresentation,
    *,
    language: ExportLanguage,
    practice: bool,
    layout: _Layout,
) -> bytes:
    image = Image.new("RGB", (layout.width, layout.height), _CANVAS)
    draw = ImageDraw.Draw(image)
    fonts = _font_paths()

    _draw_crest(image, layout.crest_box)
    _draw_fitted_text(
        draw,
        _title(language),
        layout.title_box,
        fonts["semibold"],
        max_size=layout.title_size,
        min_size=max(16, layout.title_size - 12),
        fill=_TEAL_DEEP,
        max_lines=2,
    )
    _draw_fitted_text(
        draw,
        _week_range(presentation.week_start, language),
        layout.week_box,
        fonts["medium"],
        max_size=max(15, int(layout.title_size * 0.48)),
        min_size=11,
        fill=_MUTED,
        max_lines=1,
    )
    _draw_fitted_text(
        draw,
        _status_line(presentation.status, presentation.version, language),
        layout.status_box,
        fonts["semibold"],
        max_size=max(15, int(layout.title_size * 0.48)),
        min_size=11,
        fill=_status_colour(presentation.status),
        max_lines=1,
    )
    _draw_grid(
        draw,
        presentation,
        language=language,
        layout=layout,
        fonts=fonts,
    )

    if layout.footer_box is not None:
        _draw_fitted_text(
            draw,
            _footer(language),
            layout.footer_box,
            fonts["medium"],
            max_size=18 if layout.kind == "whatsapp" else 11,
            min_size=9,
            fill=_MUTED,
            max_lines=2,
        )
    if practice:
        image = _apply_practice_mark(image, fonts["semibold"], layout)
    return _encode_png(image)


def _draw_grid(
    draw: ImageDraw.ImageDraw,
    presentation: RosterSchedulePresentation,
    *,
    language: ExportLanguage,
    layout: _Layout,
    fonts: dict[str, Path],
) -> None:
    left, top, right, bottom = layout.grid_box
    first_right = left + layout.first_column_width
    day_width = (right - first_right) / len(presentation.days)
    row_height = (bottom - top - layout.header_height) / len(presentation.rows)
    x_edges = [left, first_right] + [
        round(first_right + index * day_width)
        for index in range(1, len(presentation.days) + 1)
    ]
    y_edges = [top, top + layout.header_height] + [
        round(top + layout.header_height + index * row_height)
        for index in range(1, len(presentation.rows) + 1)
    ]

    _fill_cell(draw, (x_edges[0], y_edges[0], x_edges[1], y_edges[1]), _TEAL)
    _draw_fitted_text(
        draw,
        "值班位置" if language == "zh" else "Duty Position",
        _inset((x_edges[0], y_edges[0], x_edges[1], y_edges[1]), 6),
        fonts["semibold"],
        max_size=layout.day_size,
        min_size=10,
        fill="white",
        max_lines=2,
    )
    for column, day in enumerate(presentation.days, start=1):
        header_colour = _DAY_CLOSED_HEADER if day.state == "day_closed" else _TEAL
        box = (x_edges[column], y_edges[0], x_edges[column + 1], y_edges[1])
        _fill_cell(draw, box, header_colour)
        _draw_fitted_text(
            draw,
            _day_heading(day.duty_date, day.label_zh, day.label_en, language),
            _inset(box, 5),
            fonts["semibold"],
            max_size=layout.day_size,
            min_size=9,
            fill="white",
            max_lines=2,
        )

    for row_index, schedule_row in enumerate(presentation.rows, start=1):
        row_box = (x_edges[0], y_edges[row_index], x_edges[1], y_edges[row_index + 1])
        _fill_cell(draw, row_box, _TEAL_DEEP)
        label_bottom = row_box[1] + round((row_box[3] - row_box[1]) * 0.70)
        _draw_fitted_text(
            draw,
            schedule_row.spec.display_label,
            _inset((row_box[0], row_box[1] + 3, row_box[2], label_bottom), 5),
            fonts["medium"],
            max_size=layout.post_size,
            min_size=8,
            fill="white",
            max_lines=3,
        )
        _draw_fitted_text(
            draw,
            _service_time_text(schedule_row.spec.service_time),
            _inset((row_box[0], label_bottom - 2, row_box[2], row_box[3] - 2), 4),
            fonts["medium"],
            max_size=layout.time_size,
            min_size=8,
            fill="white",
            max_lines=1,
        )

        for column, cell in enumerate(schedule_row.cells, start=1):
            box = (
                x_edges[column],
                y_edges[row_index],
                x_edges[column + 1],
                y_edges[row_index + 1],
            )
            background, foreground = _cell_colours(cell, schedule_row.spec.post)
            _fill_cell(draw, box, background)
            _draw_fitted_text(
                draw,
                _cell_text(cell, language),
                _inset(box, 6 if layout.kind == "avatar" else 10),
                fonts["semibold"] if cell.state is RosterCellState.VACANT else fonts["medium"],
                max_size=(layout.name_size if cell.state is RosterCellState.ASSIGNED else layout.state_size),
                min_size=8 if layout.kind == "avatar" else 13,
                fill=foreground,
                max_lines=2,
            )

    for x in x_edges:
        draw.line((x, top, x, bottom), fill=_GRID, width=layout.line_width)
    for y in y_edges:
        draw.line((left, y, right, y), fill=_GRID, width=layout.line_width)
    draw.line(
        (left, y_edges[1], right, y_edges[1]),
        fill=_GOLD,
        width=layout.line_width + 1,
    )
    draw.line(
        (x_edges[1], top, x_edges[1], bottom),
        fill=_GOLD,
        width=layout.line_width + 1,
    )


def _draw_crest(image: Image.Image, box: tuple[int, int, int, int]) -> None:
    if not DISPLAY_PRINT_CREST_PATH.is_file():
        raise ValueError("Bundled display-print school crest is missing.")
    width = box[2] - box[0]
    height = box[3] - box[1]
    with Image.open(DISPLAY_PRINT_CREST_PATH) as source:
        crest = ImageOps.contain(source.convert("RGBA"), (width, height), Image.Resampling.LANCZOS)
    x = box[0] + (width - crest.width) // 2
    y = box[1] + (height - crest.height) // 2
    image.paste(crest, (x, y), crest)


def _draw_fitted_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    font_path: Path,
    *,
    max_size: int,
    min_size: int,
    fill: str,
    max_lines: int,
) -> None:
    value = str(text).strip()
    if not value:
        return
    available_width = max(1, box[2] - box[0])
    available_height = max(1, box[3] - box[1])
    for size in range(max_size, min_size - 1, -1):
        font = _font(font_path, size)
        lines = _wrap_text(draw, value, font, available_width, max_lines)
        if lines is None:
            continue
        rendered = "\n".join(lines)
        spacing = max(1, round(size * 0.18))
        bounds = draw.multiline_textbbox(
            (0, 0),
            rendered,
            font=font,
            spacing=spacing,
            align="center",
        )
        text_width = bounds[2] - bounds[0]
        text_height = bounds[3] - bounds[1]
        if text_width > available_width or text_height > available_height:
            continue
        x = box[0] + (available_width - text_width) / 2 - bounds[0]
        y = box[1] + (available_height - text_height) / 2 - bounds[1]
        draw.multiline_text(
            (round(x), round(y)),
            rendered,
            font=font,
            fill=fill,
            spacing=spacing,
            align="center",
        )
        return
    raise ValueError("Roster image text does not fit inside its assigned cell.")


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    max_lines: int,
) -> list[str] | None:
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        if _text_width(draw, paragraph, font) <= max_width:
            lines.append(paragraph)
            continue
        words = paragraph.split()
        if len(words) > 1:
            paragraph_lines = _wrap_words(draw, words, font, max_width)
        else:
            paragraph_lines = _wrap_characters(draw, paragraph, font, max_width)
        if paragraph_lines is None:
            return None
        lines.extend(paragraph_lines)
        if len(lines) > max_lines:
            return None
    return lines if len(lines) <= max_lines else None


def _wrap_words(
    draw: ImageDraw.ImageDraw,
    words: list[str],
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str] | None:
    lines: list[str] = []
    current = ""
    for word in words:
        if _text_width(draw, word, font) > max_width:
            chunks = _wrap_characters(draw, word, font, max_width)
            if chunks is None:
                return None
            if current:
                lines.append(current)
                current = ""
            lines.extend(chunks[:-1])
            current = chunks[-1]
            continue
        candidate = f"{current} {word}".strip()
        if not current or _text_width(draw, candidate, font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _wrap_characters(
    draw: ImageDraw.ImageDraw,
    value: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str] | None:
    lines: list[str] = []
    current = ""
    for character in value:
        candidate = f"{current}{character}"
        if _text_width(draw, candidate, font) <= max_width:
            current = candidate
            continue
        if not current:
            return None
        lines.append(current)
        current = character
    if current:
        lines.append(current)
    return lines


def _text_width(
    draw: ImageDraw.ImageDraw,
    value: str,
    font: ImageFont.FreeTypeFont,
) -> int:
    bounds = draw.textbbox((0, 0), value, font=font)
    return bounds[2] - bounds[0]


def _cell_text(cell: RosterScheduleCell, language: ExportLanguage) -> str:
    if cell.state is RosterCellState.ASSIGNED:
        prefect_name = str(cell.prefect_name or "").strip()
        if not prefect_name:
            raise ValueError("Assigned roster image cells require an authoritative name.")
        return prefect_name
    if cell.state is RosterCellState.VACANT:
        return "空缺" if language == "zh" else "Vacant"
    if cell.state is RosterCellState.ROOM_CLOSED:
        return "不開放" if language == "zh" else "Closed"
    if cell.state is RosterCellState.DAY_CLOSED:
        return "全天不開放" if language == "zh" else "Closed all day"
    return "本週不開放" if language == "zh" else "Unavailable"


def _cell_colours(cell: RosterScheduleCell, post: DutyPost) -> tuple[str, str]:
    if cell.state is RosterCellState.DAY_CLOSED:
        return _DAY_CLOSED, _MUTED
    if cell.state in {RosterCellState.ROOM_CLOSED, RosterCellState.UNAVAILABLE}:
        return _CLOSED, _MUTED
    if cell.state is RosterCellState.VACANT:
        return _ROW_BACKGROUNDS[post], _VACANT
    return _ROW_BACKGROUNDS[post], _INK


def _fill_cell(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    colour: str,
) -> None:
    draw.rectangle(box, fill=colour)


def _inset(
    box: tuple[int, int, int, int],
    amount: int,
) -> tuple[int, int, int, int]:
    return (
        box[0] + amount,
        box[1] + amount,
        box[2] - amount,
        box[3] - amount,
    )


def _title(language: ExportLanguage) -> str:
    return (
        "聖言中學導學風紀值周值班表"
        if language == "zh"
        else "Sing Yin Secondary School Study Prefect Duty Roster"
    )


def _week_range(week_start: date, language: ExportLanguage) -> str:
    week_end = week_start.fromordinal(week_start.toordinal() + 4)
    if language == "zh":
        end_year = f"{week_end.year}年" if week_end.year != week_start.year else ""
        return (
            f"{week_start.year}年{week_start.month}月{week_start.day}日"
            f"—{end_year}{week_end.month}月{week_end.day}日"
        )
    return (
        f"{week_start.day:02d} {_MONTHS[week_start.month - 1]} {week_start.year}"
        f" — {week_end.day:02d} {_MONTHS[week_end.month - 1]} {week_end.year}"
    )


def _status_line(status: str, version: int, language: ExportLanguage) -> str:
    if language == "zh":
        label = (
            "已發布"
            if status == "published"
            else "已撤回 · 不可派發"
            if status == "withdrawn"
            else "草稿 · 不可派發"
        )
        return f"{label} · v{version}"
    label = (
        "PUBLISHED"
        if status == "published"
        else "WITHDRAWN · DO NOT DISTRIBUTE"
        if status == "withdrawn"
        else "DRAFT · DO NOT DISTRIBUTE"
    )
    return f"{label} · v{version}"


def _status_colour(status: str) -> str:
    if status == "published":
        return _TEAL_DEEP
    if status == "withdrawn":
        return _VACANT
    return "#765B20"


def _day_heading(
    duty_date: date | None,
    label_zh: str,
    label_en: str,
    language: ExportLanguage,
) -> str:
    if duty_date is None:
        raise ValueError("Roster image days require calendar dates.")
    if language == "zh":
        return f"{label_zh}\n{duty_date.month}月{duty_date.day}日"
    return f"{label_en.upper()}\n{duty_date.day:02d} {_MONTHS[duty_date.month - 1]}"


def _footer(language: ExportLanguage) -> str:
    return (
        "僅供獲批准的校內群組"
        if language == "zh"
        else "FOR APPROVED INTERNAL SCHOOL GROUPS ONLY"
    )


def _service_time_text(service_time: tuple[str, str]) -> str:
    value = f"{service_time[0]}–{service_time[1]}"
    if value != SERVICE_TIME_TEXT:
        raise ValueError("Roster image rows must use the unified 15:40–17:00 service time.")
    return value


def _apply_practice_mark(
    image: Image.Image,
    font_path: Path,
    layout: _Layout,
) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font_size = 76 if layout.kind == "avatar" else 132
    font = _font(font_path, font_size)
    text = "PRACTICE"
    bounds = draw.textbbox((0, 0), text, font=font, stroke_width=2)
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    x = (layout.width - width) // 2 - bounds[0]
    y = (layout.grid_box[1] + layout.grid_box[3] - height) // 2 - bounds[1]
    draw.text(
        (x, y),
        text,
        font=font,
        fill=(139, 76, 0, 72),
        stroke_width=2,
        stroke_fill=(255, 255, 255, 90),
    )
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def _encode_png(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG", optimize=False, compress_level=9)
    content = output.getvalue()
    if len(content) > MAX_PNG_BYTES:
        raise ValueError("Roster image exceeds the 5 MiB delivery limit.")
    return content


def _font_paths() -> dict[str, Path]:
    font_dir = PROJECT_ROOT / "nicegui_app" / "assets" / "fonts"
    paths = {
        "regular": font_dir / "NotoSansHK-Regular.ttf",
        "medium": font_dir / "NotoSansHK-Medium.ttf",
        "semibold": font_dir / "NotoSansHK-SemiBold.ttf",
    }
    missing = [path.name for path in paths.values() if not path.is_file()]
    if missing:
        raise ValueError(f"Bundled Traditional Chinese image font is missing: {', '.join(missing)}.")
    return paths


@lru_cache(maxsize=128)
def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(path), size=size)
    except OSError as error:
        raise ValueError("Bundled Traditional Chinese image font could not be loaded.") from error


__all__ = [
    "RosterPngBundle",
    "RosterPngCapacityError",
    "RosterPngFile",
    "build_roster_png_bundle",
    "render_roster_png_bundle",
]
