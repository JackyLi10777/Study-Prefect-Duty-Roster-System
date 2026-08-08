"""Local-only, print-ready roster and internal-audit PDF exports.

The weekly schedule deliberately fits on one A4 page so it can be sent to the
prefect group without exposing the private cumulative fairness ledger.  A
separate audit export is available for the Head Study Prefect and teacher
advisor when they need to review the ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from io import BytesIO
import os
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Mapping
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from nicegui_app.config import DISPLAY_PRINT_CREST_PATH, PROJECT_ROOT
from nicegui_app.services.roster_presentation import (
    DAY_TEXT,
    RosterCellState,
    build_roster_presentation,
)
from roster_policy import DutyPost, SchoolDay

if TYPE_CHECKING:
    from nicegui_app.services.roster_workflow import RosterWorkflow


ExportLanguage = Literal["zh", "en"]

ENGLISH_MONTH_ABBREVIATIONS = (
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

ROW_BACKGROUNDS = {
    DutyPost.ASSIST_IN_CHARGE: colors.HexColor("#FFF9E7"),
    DutyPost.ROOM_302: colors.HexColor("#EEF9F2"),
    DutyPost.ROOM_303: colors.HexColor("#FFF3F3"),
    DutyPost.ROOM_202: colors.HexColor("#FFF8ED"),
}
TEAL = colors.HexColor("#147E76")
TEAL_DEEP = colors.HexColor("#0C625C")
GOLD = colors.HexColor("#D3A930")
GRID = colors.HexColor("#B7C9CF")
INK = colors.HexColor("#17333A")
MUTED = colors.HexColor("#5E7377")
CLOSED = colors.HexColor("#EEF3F4")
DAY_CLOSED = colors.HexColor("#E4E8EC")
DAY_CLOSED_HEADER = colors.HexColor("#596674")


@dataclass(frozen=True)
class RosterPdfExport:
    """A locally generated PDF payload ready for operator-initiated delivery."""

    filename: str
    content: bytes


def build_roster_pdf(
    workflow: "RosterWorkflow",
    roster_week_id: int,
    *,
    language: ExportLanguage = "zh",
    practice: bool = False,
    show_crest: bool = True,
    show_footer_note: bool = False,
) -> RosterPdfExport:
    """Render the group-share weekly grid on a single A4 page.

    Labels follow the selected output language.  Prefect names intentionally
    remain the stored Traditional-Chinese names in both modes.
    """
    week, assignments = workflow.roster_schedule_snapshot(roster_week_id)
    fonts = _register_cjk_fonts()
    styles = _styles(fonts)
    output = BytesIO()
    document = _document(output, week_start=week["weekStart"], title=_schedule_title(language), orientation="landscape")

    story = _schedule_header(week["weekStart"], str(week["status"]), language, styles, show_crest=show_crest)
    if practice:
        story.extend([Spacer(1, 2 * mm), Paragraph(_practice_marker(language), styles["practice_marker"])])
    story.extend([
        Spacer(1, 4 * mm),
        _schedule_grid(
            assignments,
            week=week,
            language=language,
            styles=styles,
            landscape_mode=True,
        ),
    ])
    if show_footer_note:
        story.extend([Spacer(1, 5 * mm), Paragraph(_schedule_footer(language), styles["footer"])])
    render_page_footer = show_footer_note or practice
    document.build(
        story,
        onFirstPage=lambda canvas, doc: _draw_footer(canvas, doc, fonts["medium"], language, practice, visible=render_page_footer),
        onLaterPages=lambda canvas, doc: _draw_footer(canvas, doc, fonts["medium"], language, practice, visible=render_page_footer),
    )
    return RosterPdfExport(
        filename=_schedule_filename(week["weekStart"], language, int(week["version"]), practice),
        content=output.getvalue(),
    )


def build_fairness_audit_pdf(
    workflow: "RosterWorkflow", roster_week_id: int, *, language: ExportLanguage = "zh", practice: bool = False
) -> RosterPdfExport:
    """Render a clearly marked internal-only, named fairness ledger summary."""
    week = workflow.roster_week(roster_week_id)
    fonts = _register_cjk_fonts()
    styles = _styles(fonts)
    output = BytesIO()
    document = _document(output, week_start=week["weekStart"], title=_audit_title(language), orientation="portrait")
    fairness_rows = workflow.fairness_rows()
    active_assignments = [row for row in workflow.assignments(roster_week_id) if row["status"] == "active"]
    summary = _audit_summary(week["weekStart"], str(week["status"]), len(active_assignments), language)
    story = [
        Paragraph(_audit_title(language), styles["title"]),
        Paragraph(summary, styles["subtitle"]),
        *([Spacer(1, 2 * mm), Paragraph(_practice_marker(language), styles["practice_marker"])] if practice else []),
        Spacer(1, 5 * mm),
        Paragraph(_internal_marker(language), styles["internal_marker"]),
        Spacer(1, 4 * mm),
        Paragraph(_audit_section_title(language), styles["section"]),
        _audit_table(fairness_rows, language, styles),
        Spacer(1, 5 * mm),
        Paragraph(_audit_explanation(language), styles["note"]),
        Spacer(1, 3 * mm),
        Paragraph(_audit_confidentiality(language), styles["footer"]),
    ]
    document.build(
        story,
        onFirstPage=lambda canvas, doc: _draw_footer(canvas, doc, fonts["medium"], language, practice),
        onLaterPages=lambda canvas, doc: _draw_footer(canvas, doc, fonts["medium"], language, practice),
    )
    return RosterPdfExport(filename=_audit_filename(week["weekStart"], language, practice), content=output.getvalue())


def _document(
    output: BytesIO, *, week_start: object, title: str, orientation: Literal["landscape", "portrait"]
) -> SimpleDocTemplate:
    page_size = landscape(A4) if orientation == "landscape" else A4
    horizontal_margin = 10 * mm if orientation == "landscape" else 7 * mm
    return SimpleDocTemplate(
        output,
        pagesize=page_size,
        leftMargin=horizontal_margin,
        rightMargin=horizontal_margin,
        topMargin=9 * mm,
        bottomMargin=15 * mm,
        title=f"{title} {week_start}",
        author="Sing Yin Study Prefect Duty Roster System",
    )


def _schedule_header(
    week_start: object,
    status: str,
    language: ExportLanguage,
    styles: dict[str, ParagraphStyle],
    *,
    show_crest: bool,
) -> list[object]:
    story: list[object] = []
    badge = _school_badge()
    if show_crest and badge is not None:
        story.extend([badge, Spacer(1, 2 * mm)])
    story.extend([
        Paragraph(_schedule_title(language), styles["title"]),
        Paragraph(_schedule_subtitle(language), styles["gold_subtitle"]),
        Paragraph(_week_line(week_start, status, language), styles["subtitle"]),
        Spacer(1, 4 * mm),
        Paragraph(_weekly_label(language), styles["section"]),
    ])
    return story


def _schedule_grid(
    assignments: list[dict[str, object]],
    week: Mapping[str, object],
    language: ExportLanguage,
    styles: dict[str, ParagraphStyle],
    *,
    landscape_mode: bool,
) -> Table:
    presentation = build_roster_presentation(week, assignments)
    heading = "值班位置" if language == "zh" else "Duty Position"
    rows: list[list[Paragraph]] = [[Paragraph(heading, styles["grid_heading"])] + [
        Paragraph(
            _dated_day_heading(
                presentation.week_start,
                day.day,
                language,
            ),
            styles["grid_heading"],
        )
        for day in presentation.days
    ]]
    cell_backgrounds: list[tuple[int, int, colors.Color]] = []
    closed_columns = [
        index
        for index, day in enumerate(presentation.days, start=1)
        if day.state == "day_closed"
    ]
    for row_index, schedule_row in enumerate(presentation.rows, start=1):
        spec = schedule_row.spec
        post = spec.post
        start_time, end_time = spec.service_time
        # Duty-post names are operational identifiers and remain English in
        # both PDF languages; headings, weekdays and guidance still localise.
        post_label = xml_escape(spec.display_label)
        row = [
            Paragraph(
                f'{post_label}<br/><font size="8.1">{start_time}–{end_time}</font>',
                styles["post_cell"],
            )
        ]
        for column_index, cell in enumerate(schedule_row.cells, start=1):
            if cell.state is RosterCellState.DAY_CLOSED:
                row.append(
                    Paragraph(
                        ("全天不開放" if language == "zh" else "Closed all day")
                        if row_index == 1
                        else "",
                        styles["closed_cell"],
                    )
                )
                continue
            if cell.state is RosterCellState.ROOM_CLOSED:
                row.append(Paragraph("不開放" if language == "zh" else "Closed", styles["closed_cell"]))
                cell_backgrounds.append((column_index, row_index, CLOSED))
                continue
            if cell.state is RosterCellState.UNAVAILABLE:
                row.append(
                    Paragraph(
                        "不開放" if language == "zh" else "Unavailable",
                        styles["closed_cell"],
                    )
                )
                cell_backgrounds.append((column_index, row_index, CLOSED))
                continue
            if cell.state is RosterCellState.VACANT:
                row.append(Paragraph("空缺" if language == "zh" else "Vacant", styles["vacant_cell"]))
                cell_backgrounds.append((column_index, row_index, ROW_BACKGROUNDS[post]))
                continue
            row.append(Paragraph(xml_escape(cell.prefect_name or ""), styles["name_cell"]))
            cell_backgrounds.append((column_index, row_index, ROW_BACKGROUNDS[post]))
        rows.append(row)
    if landscape_mode:
        column_widths = [84 * mm] + [38.6 * mm] * 5
        row_heights = [14 * mm] + [14 * mm] * 6
    else:  # pragma: no cover - retained for any future compact export
        column_widths = [66.7 * mm] + [25.86 * mm] * 5
        row_heights = [12 * mm] + [11.5 * mm] * 6
    table = Table(rows, colWidths=column_widths, rowHeights=row_heights)
    commands: list[tuple[object, ...]] = [
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("BACKGROUND", (0, 1), (0, -1), TEAL_DEEP),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("TEXTCOLOR", (0, 1), (0, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.38, GRID),
        ("LINEBELOW", (0, 0), (-1, 0), 0.9, GOLD),
        ("LINEAFTER", (0, 0), (0, -1), 0.9, GOLD),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    commands.extend(("BACKGROUND", (column, row), (column, row), background) for column, row, background in cell_backgrounds)
    for column in closed_columns:
        commands.extend(
            [
                ("BACKGROUND", (column, 0), (column, 0), DAY_CLOSED_HEADER),
                ("SPAN", (column, 1), (column, -1)),
                ("BACKGROUND", (column, 1), (column, -1), DAY_CLOSED),
                ("BOX", (column, 1), (column, -1), 0.38, GRID),
                ("LINEBEFORE", (column, 0), (column, -1), 1.0, DAY_CLOSED_HEADER),
                ("LINEAFTER", (column, 0), (column, -1), 1.0, DAY_CLOSED_HEADER),
            ]
        )
    table.setStyle(TableStyle(commands))
    return table


def _dated_day_heading(
    week_start: object,
    day: SchoolDay,
    language: ExportLanguage,
) -> str:
    """Return a locale-stable weekday and calendar date for a PDF column."""

    start = _coerce_week_start(week_start)
    duty_date = start + timedelta(days=int(day))
    weekday = DAY_TEXT[day][0 if language == "zh" else 1]
    if language == "zh":
        date_text = f"{duty_date.month}月{duty_date.day}日"
    else:
        date_text = f"{duty_date.day:02d} {ENGLISH_MONTH_ABBREVIATIONS[duty_date.month - 1]}"
    return f'{weekday}<br/><font size="7.8">{date_text}</font>'


def _coerce_week_start(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ValueError("Roster week start must be an ISO calendar date.") from error
    raise TypeError("Roster week start must be a date or ISO date string.")


def _audit_table(rows: list[dict[str, object]], language: ExportLanguage, styles: dict[str, ParagraphStyle]) -> Table:
    headers = (
        ("中文姓名", "Form", "Class", "累計點數", "累計次數")
        if language == "zh"
        else ("Chinese name", "Form", "Class", "History weight", "History duties")
    )
    data: list[list[Paragraph]] = [[Paragraph(header, styles["audit_heading"]) for header in headers]]
    for row in rows:
        data.append([
            Paragraph(xml_escape(str(row["nameZh"])), styles["audit_cell"]),
            Paragraph(xml_escape(str(row["form"])), styles["audit_cell"]),
            Paragraph(xml_escape(str(row["className"])), styles["audit_cell"]),
            Paragraph(f"{float(row['historyWeight']):.1f}", styles["audit_cell_right"]),
            Paragraph(str(row["historyDuties"]), styles["audit_cell_right"]),
        ])
    table = Table(data, colWidths=[51 * mm, 27 * mm, 30 * mm, 38 * mm, 38 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FBFB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _school_badge() -> Image | None:
    badge_path = DISPLAY_PRINT_CREST_PATH
    if not badge_path.is_file():
        return None
    return Image(str(badge_path), width=15 * mm, height=15 * mm, hAlign="CENTER")


def _schedule_title(language: ExportLanguage) -> str:
    return "聖言中學導學風紀值周值班表" if language == "zh" else "Sing Yin Secondary School Study Prefect Duty Roster"


def _schedule_subtitle(language: ExportLanguage) -> str:
    return "導學風紀值班表與工作審核" if language == "zh" else "Study Prefect Duty Roster &amp; Workload Audit"


def _week_line(week_start: object, status: str, language: ExportLanguage) -> str:
    if language == "zh":
        state = (
            "已發布"
            if status == "published"
            else "已撤回－只供審計，不可派發"
            if status == "withdrawn"
            else "草稿－只供核對，不可派發"
        )
        return f"報告日期：{week_start} ｜ {state}"
    state = (
        "Published"
        if status == "published"
        else "Withdrawn — audit only; do not distribute"
        if status == "withdrawn"
        else "Draft — check only; do not distribute"
    )
    return f"Week commencing: {week_start} | {state}"


def _weekly_label(language: ExportLanguage) -> str:
    return "值周值班表" if language == "zh" else "Weekly Duty Roster"


def _schedule_footer(language: ExportLanguage) -> str:
    if language == "zh":
        return "服務精神：非以役人，乃役於人｜發送前請核對中文姓名；此頁可供校內受控分享。"
    return "Service principle: Not to be served, but to serve | Chinese names are authoritative; share only through approved school channels."


def _audit_title(language: ExportLanguage) -> str:
    return "聖言中學導學風紀公平審計摘要" if language == "zh" else "Sing Yin Study Prefect Fairness Audit Summary"


def _audit_summary(week_start: object, status: str, active_count: int, language: ExportLanguage) -> str:
    if language == "zh":
        state = "已發布" if status == "published" else "已撤回" if status == "withdrawn" else "草稿"
    else:
        state = "Published" if status == "published" else "Withdrawn" if status == "withdrawn" else "Draft"
    if language == "zh":
        return f"週次：{week_start} ｜ 狀態：{state} ｜ 本週有效崗位：{active_count}"
    return f"Week commencing: {week_start} | Status: {state} | Active assignments: {active_count}"


def _internal_marker(language: ExportLanguage) -> str:
    return "內部文件：供首席導學風紀及老師顧問核對，不應預設發到風紀群組。" if language == "zh" else "Internal record: for the Head Study Prefect and teacher advisor; do not send to the prefect group by default."


def _practice_marker(language: ExportLanguage) -> str:
    return (
        "練習版本｜只含虛構資料｜不可作正式發布"
        if language == "zh"
        else "PRACTICE VERSION | FICTIONAL DATA | NOT FOR OFFICIAL DISTRIBUTION"
    )


def _audit_section_title(language: ExportLanguage) -> str:
    return "累計工作量帳本" if language == "zh" else "Persistent workload ledger"


def _audit_explanation(language: ExportLanguage) -> str:
    if language == "zh":
        return "公平原則：history_weight 跨週保留；系統在符合職務、可值班日、同日不重複及不連續值班規則下，優先安排較低點數的風紀。只有發布週表或已記錄的發布後請假調整會改變帳本。"
    return "Fairness principle: history_weight persists across weeks. Within role eligibility, availability, no same-day duplicate, and no consecutive-duty rules, the system prioritizes lower-weight prefects. Only publication or an audited post-publication leave adjustment changes the ledger."


def _audit_confidentiality(language: ExportLanguage) -> str:
    return "此摘要含個人累計資料；如需向群組說明公平性，請先由老師顧問同意，並優先分享規則及整體趨勢。" if language == "zh" else "This summary contains individual cumulative data. If fairness needs to be explained to the group, obtain teacher-advisor approval and share the rules and overall trend first."


def _schedule_filename(
    week_start: object, language: ExportLanguage, version: int, practice: bool = False
) -> str:
    suffix = "中文" if language == "zh" else "EN"
    prefix = "PRACTICE_" if practice else ""
    return f"{prefix}SYSS_Roster_{week_start:%Y%m%d}_v{version}_{suffix}.pdf"


def _audit_filename(week_start: object, language: ExportLanguage, practice: bool = False) -> str:
    suffix = "中文" if language == "zh" else "EN"
    prefix = "PRACTICE_" if practice else ""
    return f"{prefix}SYSS_Fairness_Audit_{week_start:%Y%m%d}_{suffix}.pdf"


def _register_cjk_fonts() -> dict[str, str]:
    """Register deterministic static HK fonts so ReportLab never selects Thin."""

    bundled = PROJECT_ROOT / "nicegui_app" / "assets" / "fonts"
    legacy_override = os.getenv("SING_YIN_PDF_FONT", "")
    paths = {
        "regular": Path(os.getenv("SING_YIN_PDF_FONT_REGULAR", legacy_override or bundled / "NotoSansHK-Regular.ttf")),
        "medium": Path(os.getenv("SING_YIN_PDF_FONT_MEDIUM", bundled / "NotoSansHK-Medium.ttf")),
        "semibold": Path(os.getenv("SING_YIN_PDF_FONT_SEMIBOLD", bundled / "NotoSansHK-SemiBold.ttf")),
    }
    names = {
        "regular": "SingYinNotoSansHK-Regular",
        "medium": "SingYinNotoSansHK-Medium",
        "semibold": "SingYinNotoSansHK-SemiBold",
    }
    for weight, path in paths.items():
        if not path.is_file():
            raise ValueError(f"Bundled Traditional Chinese PDF font is missing: {path.name}.")
        if names[weight] not in pdfmetrics.getRegisteredFontNames():
            try:
                pdfmetrics.registerFont(TTFont(names[weight], str(path)))
            except Exception as error:  # pragma: no cover - depends on local font implementation
                raise ValueError(f"Traditional Chinese PDF font could not be loaded: {path.name}.") from error
    return names


def _styles(fonts: dict[str, str]) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName=fonts["semibold"], fontSize=18, leading=24, alignment=TA_CENTER, textColor=TEAL_DEEP, spaceBefore=0, spaceAfter=0),
        "gold_subtitle": ParagraphStyle("gold_subtitle", parent=base["Normal"], fontName=fonts["medium"], fontSize=10, leading=14, alignment=TA_CENTER, textColor=colors.HexColor("#765B20"), spaceBefore=0, spaceAfter=0),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=fonts["medium"], fontSize=9, leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#465C61"), spaceBefore=0, spaceAfter=0),
        "section": ParagraphStyle("section", parent=base["Heading2"], fontName=fonts["semibold"], fontSize=10.5, leading=14, textColor=TEAL_DEEP, spaceBefore=0, spaceAfter=0),
        "grid_heading": ParagraphStyle("grid_heading", parent=base["Normal"], fontName=fonts["semibold"], fontSize=8.8, leading=10.5, alignment=TA_CENTER, textColor=colors.white, spaceBefore=0, spaceAfter=0),
        "post_cell": ParagraphStyle("post_cell", parent=base["Normal"], fontName=fonts["medium"], fontSize=8.8, leading=10.8, alignment=TA_CENTER, textColor=colors.white, spaceBefore=0, spaceAfter=0),
        "name_cell": ParagraphStyle("name_cell", parent=base["Normal"], fontName=fonts["medium"], fontSize=9.4, leading=11.4, alignment=TA_CENTER, textColor=colors.HexColor("#1E3035"), spaceBefore=0, spaceAfter=0),
        "vacant_cell": ParagraphStyle("vacant_cell", parent=base["Normal"], fontName=fonts["semibold"], fontSize=8.8, leading=10.5, alignment=TA_CENTER, textColor=colors.HexColor("#8F1D14"), spaceBefore=0, spaceAfter=0),
        "closed_cell": ParagraphStyle("closed_cell", parent=base["Normal"], fontName=fonts["regular"], fontSize=8.2, leading=10.2, alignment=TA_CENTER, textColor=colors.HexColor("#52666B"), spaceBefore=0, spaceAfter=0),
        "audit_heading": ParagraphStyle("audit_heading", parent=base["Normal"], fontName=fonts["semibold"], fontSize=8.5, leading=10.5, alignment=TA_CENTER, textColor=colors.white, spaceBefore=0, spaceAfter=0),
        "audit_cell": ParagraphStyle("audit_cell", parent=base["Normal"], fontName=fonts["regular"], fontSize=8.8, leading=11.2, alignment=TA_LEFT, textColor=INK, spaceBefore=0, spaceAfter=0),
        "audit_cell_right": ParagraphStyle("audit_cell_right", parent=base["Normal"], fontName=fonts["medium"], fontSize=8.8, leading=11.2, alignment=TA_CENTER, textColor=INK, spaceBefore=0, spaceAfter=0),
        "note": ParagraphStyle("note", parent=base["Normal"], fontName=fonts["regular"], fontSize=8.8, leading=14, textColor=INK, spaceBefore=0, spaceAfter=0),
        "internal_marker": ParagraphStyle("internal_marker", parent=base["Normal"], fontName=fonts["medium"], fontSize=8.8, leading=13, textColor=colors.HexColor("#6D4700"), backColor=colors.HexColor("#FFF6D8"), borderColor=colors.HexColor("#E6C36A"), borderWidth=0.45, borderPadding=7, spaceBefore=0, spaceAfter=0),
        "practice_marker": ParagraphStyle("practice_marker", parent=base["Normal"], fontName=fonts["semibold"], fontSize=8.8, leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#6D3C00"), backColor=colors.HexColor("#FFF0C2"), borderColor=colors.HexColor("#D6A447"), borderWidth=0.6, borderPadding=5, spaceBefore=0, spaceAfter=0),
        "footer": ParagraphStyle("footer", parent=base["Normal"], fontName=fonts["medium"], fontSize=7.6, leading=10.5, alignment=TA_CENTER, textColor=colors.HexColor("#4D6065"), spaceBefore=0, spaceAfter=0),
    }


def _draw_footer(
    canvas,
    document,
    font_name: str,
    language: ExportLanguage,
    practice: bool = False,
    *,
    visible: bool = True,
) -> None:  # type: ignore[no-untyped-def]
    if not visible:
        return
    canvas.saveState()
    canvas.setFont(font_name, 7.5)
    canvas.setFillColor(colors.HexColor("#4D6065"))
    if practice:
        text = (
            f"練習版本・不可正式發布 ｜ 第 {document.page} 頁"
            if language == "zh"
            else f"PRACTICE · NOT OFFICIAL | Page {document.page}"
        )
    else:
        text = f"校內文件 ｜ 第 {document.page} 頁" if language == "zh" else f"Internal school document | Page {document.page}"
    canvas.drawCentredString(canvas._pagesize[0] / 2, 7 * mm, text)
    canvas.restoreState()
