"""Deterministic exports for the read-only Study Prefect period report."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
import hashlib
from io import BytesIO
import json
from typing import Any, Literal
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from nicegui_app.config import DISPLAY_PRINT_CREST_PATH
from nicegui_app.services.roster_export import INK, TEAL, TEAL_DEEP, _register_cjk_fonts
from nicegui_app.services.workflow_types import PeriodSummaryReport, PrefectPeriodContribution


ReportLanguage = Literal["zh", "en"]


@dataclass(frozen=True)
class SummaryReportDownload:
    filename: str
    content: bytes
    media_type: str


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        text = value.isoformat()
        return f"{text}Z" if isinstance(value, datetime) and value.tzinfo is None else text
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def summary_report_payload(report: PeriodSummaryReport) -> dict[str, Any]:
    """Return the language-neutral payload shared by every presentation."""
    raw = _json_value(asdict(report))
    return {
        "schemaVersion": raw.pop("schema_version"),
        "generatedAt": raw.pop("generated_at"),
        "period": {
            "start": raw.pop("period_start"),
            "end": raw.pop("period_end"),
        },
        **raw,
    }


def build_summary_report_json(report: PeriodSummaryReport) -> SummaryReportDownload:
    payload = summary_report_payload(report)
    canonical_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    envelope = {
        "evidenceType": "sing-yin-study-prefect-period-summary",
        "payloadSha256": hashlib.sha256(canonical_payload).hexdigest(),
        "payload": payload,
    }
    content = json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    return SummaryReportDownload(
        filename=f"SYSS_Service_Summary_{_period_slug(report)}.json",
        content=content,
        media_type="application/json",
    )


def build_summary_report_pdf(
    report: PeriodSummaryReport,
    *,
    language: ReportLanguage = "en",
) -> SummaryReportDownload:
    """Render a professional internal report while keeping every name Chinese."""
    fonts = _register_cjk_fonts()
    styles = _styles(fonts)
    output = BytesIO()
    title = _text(language, "title")
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=13 * mm,
        bottomMargin=16 * mm,
        title=f"{title} {_period_slug(report)}",
        author="Sing Yin Study Prefect Duty Roster System",
    )
    story: list[object] = [
        Paragraph(title, styles["title"]),
        Paragraph(_period_line(report, language), styles["subtitle"]),
        Spacer(1, 5 * mm),
        Paragraph(_text(language, "internal_marker"), styles["marker"]),
        Spacer(1, 5 * mm),
        Paragraph(_text(language, "executive_summary"), styles["section"]),
        _metric_table(report, language, styles),
        Spacer(1, 5 * mm),
        Paragraph(_interpretation(report, language), styles["body"]),
        Spacer(1, 5 * mm),
        Paragraph(_text(language, "contribution_title"), styles["section"]),
        Paragraph(_text(language, "contribution_note"), styles["small"]),
        Spacer(1, 2 * mm),
        _contribution_table(report, language, styles),
    ]
    if report.trend:
        story.extend(
            [
                PageBreak(),
                Paragraph(_text(language, "trend_title"), styles["section"]),
                Paragraph(_text(language, "trend_note"), styles["small"]),
                Spacer(1, 3 * mm),
                _trend_table(report, language, styles),
            ]
        )
    story.extend(
        [
            Spacer(1, 6 * mm),
            Paragraph(_text(language, "source_title"), styles["section"]),
            Paragraph(_source_line(report, language), styles["small"]),
            Spacer(1, 4 * mm),
            Paragraph(_text(language, "closing_note"), styles["body"]),
        ]
    )
    document.build(
        story,
        onFirstPage=lambda canvas, doc: _draw_page_footer(canvas, doc, fonts["medium"], language),
        onLaterPages=lambda canvas, doc: _draw_page_footer(canvas, doc, fonts["medium"], language),
    )
    suffix = "ZH" if language == "zh" else "EN"
    return SummaryReportDownload(
        filename=f"SYSS_Service_Summary_{_period_slug(report)}_{suffix}.pdf",
        content=output.getvalue(),
        media_type="application/pdf",
    )


def build_duty_allocation_statement_pdf(
    report: PeriodSummaryReport,
    prefect_id: str,
    *,
    language: ReportLanguage = "zh",
) -> SummaryReportDownload:
    """Render one Chinese-name duty-hours statement from final published allocations.

    The document becomes evidence of completed service only after an operator
    verifies attendance and the sign-off section is completed. Generation by
    itself is deliberately an allocation calculation, not an attendance claim.
    """

    contribution = next((row for row in report.contributions if row.prefect_id == prefect_id), None)
    if contribution is None:
        raise ValueError("The selected prefect is not part of this period report.")
    fonts = _register_cjk_fonts()
    styles = _styles(fonts)
    output = BytesIO()
    title = (
        "聖言中學導學風紀值班編配時數證明"
        if language == "zh"
        else "Sing Yin Study Prefect Duty Allocation Hours Statement"
    )
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=10 * mm,
        bottomMargin=16 * mm,
        title=f"{title} {_period_slug(report)}",
        author="Sing Yin Study Prefect Duty Roster System",
    )
    crest = Image(str(DISPLAY_PRINT_CREST_PATH), width=18 * mm, height=18 * mm)
    crest.hAlign = "CENTER"
    period = _period_line(report, language)
    identity = (
        f"中文姓名：{xml_escape(contribution.name_zh)}　｜　已編排值班：{contribution.duty_count} 次"
        if language == "zh"
        else f"Chinese name: {xml_escape(contribution.name_zh)} | Scheduled duties: {contribution.duty_count}"
    )
    total = _scheduled_duration_text(contribution.scheduled_minutes, language)
    total_line = (
        f"按最終已發布值班表計算的編配時數：{total}"
        if language == "zh"
        else f"Scheduled allocation calculated from final published rosters: {total}"
    )
    caution = (
        "此文件按已發布週表及其後請假調整計算。系統沒有自動簽到資料；只有在核對實際出席並完成下方簽署後，方可作已完成服務證明。"
        if language == "zh"
        else "This statement is calculated from published rosters and later leave adjustments. The system has no automatic attendance record; it becomes evidence of completed service only after attendance is checked and the sign-off below is completed."
    )
    story: list[object] = [
        crest,
        Spacer(1, 2 * mm),
        Paragraph(title, styles["title"]),
        Paragraph(period, styles["subtitle"]),
        Spacer(1, 5 * mm),
        Paragraph(identity, styles["section"]),
        Paragraph(total_line, styles["body"]),
        Spacer(1, 3 * mm),
        Paragraph(caution, styles["marker"]),
        Spacer(1, 5 * mm),
        _allocation_table(contribution, language, styles),
        Spacer(1, 8 * mm),
        _allocation_signoff_table(language, styles),
    ]
    document.build(
        story,
        onFirstPage=lambda canvas, doc: _draw_allocation_footer(canvas, doc, fonts["medium"], language),
        onLaterPages=lambda canvas, doc: _draw_allocation_footer(canvas, doc, fonts["medium"], language),
    )
    suffix = "ZH" if language == "zh" else "EN"
    return SummaryReportDownload(
        filename=f"SYSS_Duty_Allocation_{contribution.name_zh}_{_period_slug(report)}_{suffix}.pdf",
        content=output.getvalue(),
        media_type="application/pdf",
    )


def _allocation_table(
    contribution: PrefectPeriodContribution,
    language: ReportLanguage,
    styles: dict[str, ParagraphStyle],
) -> Table:
    headers = (
        ("日期", "星期", "值班位置", "當值時間", "編配時長", "來源")
        if language == "zh"
        else ("Date", "Day", "Duty position", "Duty time", "Scheduled duration", "Source")
    )
    data: list[list[Paragraph]] = [[Paragraph(item, styles["table_heading"]) for item in headers]]
    day_names = {
        "MONDAY": ("星期一", "Monday"),
        "TUESDAY": ("星期二", "Tuesday"),
        "WEDNESDAY": ("星期三", "Wednesday"),
        "THURSDAY": ("星期四", "Thursday"),
        "FRIDAY": ("星期五", "Friday"),
    }
    post_names = {
        "ASSIST_IN_CHARGE": ("Assist. in charge", "Assist. in charge"),
        "ROOM_302": ("302 室（自修室）", "Room 302 (Study Room)"),
        "ROOM_303": ("303 室（功課完成）", "Room 303 (HW Completion)"),
        "ROOM_202": ("202 室（中一溫習小組）", "Room 202 (F.1 Study Group)"),
    }
    index = 0 if language == "zh" else 1
    for row in contribution.allocations:
        data.append(
            [
                Paragraph(f"{row.duty_date:%Y-%m-%d}", styles["table_cell"]),
                Paragraph(day_names[row.day][index], styles["table_cell"]),
                Paragraph(post_names[row.post_code][index], styles["table_cell"]),
                Paragraph(f"{row.start_time}–{row.end_time}", styles["table_number"]),
                Paragraph(_scheduled_duration_text(row.scheduled_minutes, language), styles["table_number"]),
                Paragraph(f"#{row.roster_week_id} v{row.roster_version}", styles["table_cell"]),
            ]
        )
    if len(data) == 1:
        message = "期間內沒有已編排值班。" if language == "zh" else "No scheduled duty falls within this period."
        data.append([Paragraph(message, styles["table_cell"]), "", "", "", "", ""])
    table = Table(data, repeatRows=1, colWidths=[28 * mm, 23 * mm, 43 * mm, 35 * mm, 29 * mm, 24 * mm])
    table.setStyle(_standard_table_style())
    if len(data) == 2 and not contribution.allocations:
        table.setStyle(TableStyle([("SPAN", (0, 1), (-1, 1))]))
    return table


def _allocation_signoff_table(language: ReportLanguage, styles: dict[str, ParagraphStyle]) -> Table:
    if language == "zh":
        headings = ("首席導學風紀核對", "顧問老師核實")
        date_label = "簽署／日期："
    else:
        headings = ("Head Study Prefect check", "Teacher-advisor verification")
        date_label = "Signature / date:"
    data = [
        [Paragraph(headings[0], styles["small"]), Paragraph(headings[1], styles["small"])],
        [Paragraph(f"{date_label} ____________________", styles["body"]), Paragraph(f"{date_label} ____________________", styles["body"])],
    ]
    table = Table(data, colWidths=[91 * mm, 91 * mm], rowHeights=[8 * mm, 14 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B6C8C5")),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CFDAD8")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _scheduled_duration_text(minutes: int, language: ReportLanguage) -> str:
    hours, remaining = divmod(minutes, 60)
    decimal_hours = minutes / 60
    if language == "zh":
        return f"{hours} 小時 {remaining} 分（{decimal_hours:.2f} 小時）"
    return f"{hours} h {remaining} min ({decimal_hours:.2f} hours)"


def _draw_allocation_footer(canvas, document, font_name: str, language: ReportLanguage) -> None:  # type: ignore[no-untyped-def]
    canvas.saveState()
    canvas.setFont(font_name, 7.5)
    canvas.setFillColor(colors.HexColor("#52666B"))
    text = (
        f"值班編配時數證明 ｜ 第 {document.page} 頁"
        if language == "zh"
        else f"Duty allocation hours statement | Page {document.page}"
    )
    canvas.drawCentredString(A4[0] / 2, 7 * mm, text)
    canvas.restoreState()


def _period_slug(report: PeriodSummaryReport) -> str:
    if report.period_start is None or report.period_end is None:
        return "NO_PUBLISHED_ROSTERS"
    return f"{report.period_start:%Y%m%d}_{report.period_end:%Y%m%d}"


def _period_line(report: PeriodSummaryReport, language: ReportLanguage) -> str:
    if report.period_start is None or report.period_end is None:
        return _text(language, "no_period")
    if language == "zh":
        return f"報告期間：{report.period_start:%Y-%m-%d} 至 {report.period_end:%Y-%m-%d}　｜　生成時間：{report.generated_at:%Y-%m-%d %H:%M}"
    return f"Reporting period: {report.period_start:%Y-%m-%d} to {report.period_end:%Y-%m-%d} | Generated: {report.generated_at:%Y-%m-%d %H:%M}"


def _metric_table(report: PeriodSummaryReport, language: ReportLanguage, styles: dict[str, ParagraphStyle]) -> Table:
    scheduled_hours = report.scheduled_minutes / 60
    items = [
        (_text(language, "published_weeks"), str(report.published_week_count)),
        (
            _text(language, "coverage"),
            f"{report.coverage_rate:.1f}%" if report.coverage_rate is not None else _text(language, "not_applicable"),
        ),
        (_text(language, "recorded_duties"), str(report.active_assignment_count)),
        (_text(language, "scheduled_hours"), f"{scheduled_hours:.1f}"),
        (_text(language, "adjustments"), str(report.leave_adjustment_count)),
        (_text(language, "vacancies"), str(report.vacant_slot_count)),
        (_text(language, "fairness_spread"), f"{report.fairness_spread:.1f}"),
        (
            _text(language, "ledger"),
            _text(language, "balanced") if report.fairness_ledger_balanced else _text(language, "review"),
        ),
    ]
    data: list[list[Paragraph]] = []
    for index in range(0, len(items), 2):
        row: list[Paragraph] = []
        for label, value in items[index : index + 2]:
            row.extend(
                [
                    Paragraph(xml_escape(label), styles["metric_label"]),
                    Paragraph(xml_escape(value), styles["metric_value"]),
                ]
            )
        data.append(row)
    table = Table(data, colWidths=[46 * mm, 35 * mm, 46 * mm, 35 * mm], rowHeights=[12 * mm] * len(data))
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F7F6")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B6C8C5")),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CFDAD8")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _contribution_table(
    report: PeriodSummaryReport,
    language: ReportLanguage,
    styles: dict[str, ParagraphStyle],
) -> Table:
    headers = (
        ("中文姓名", "職務", "值班次數", "負荷點數", "已編排時數", "領導崗位")
        if language == "zh"
        else ("Chinese name", "Role", "Duties", "Workload", "Scheduled hours", "Assist duties")
    )
    data: list[list[Paragraph]] = [[Paragraph(item, styles["table_heading"]) for item in headers]]
    for row in report.contributions:
        role = (
            ("助理首席導學風紀" if language == "zh" else "Assistant Head")
            if row.role_code == "assistant_head"
            else ("導學風紀" if language == "zh" else "Study Prefect")
        )
        data.append(
            [
                Paragraph(xml_escape(row.name_zh), styles["table_cell"]),
                Paragraph(role, styles["table_cell"]),
                Paragraph(str(row.duty_count), styles["table_number"]),
                Paragraph(f"{row.workload_points:.1f}", styles["table_number"]),
                Paragraph(f"{row.scheduled_minutes / 60:.2f}", styles["table_number"]),
                Paragraph(str(row.assist_in_charge_count), styles["table_number"]),
            ]
        )
    table = Table(data, repeatRows=1, colWidths=[35 * mm, 40 * mm, 24 * mm, 24 * mm, 28 * mm, 25 * mm])
    table.setStyle(_standard_table_style())
    return table


def _trend_table(report: PeriodSummaryReport, language: ReportLanguage, styles: dict[str, ParagraphStyle]) -> Table:
    headers = (
        ("週次", "最低", "中位數", "最高", "差距", "母體標準差", "來源版本")
        if language == "zh"
        else ("Week", "Minimum", "Median", "Maximum", "Spread", "Population SD", "Source version")
    )
    data: list[list[Paragraph]] = [[Paragraph(item, styles["table_heading"]) for item in headers]]
    for point in report.trend:
        data.append(
            [
                Paragraph(f"{point.week_start:%Y-%m-%d}", styles["table_cell"]),
                Paragraph(f"{point.minimum:.1f}", styles["table_number"]),
                Paragraph(f"{point.median:.1f}", styles["table_number"]),
                Paragraph(f"{point.maximum:.1f}", styles["table_number"]),
                Paragraph(f"{point.spread:.1f}", styles["table_number"]),
                Paragraph(f"{point.population_stddev:.2f}", styles["table_number"]),
                Paragraph(f"#{point.roster_week_id} v{point.version}", styles["table_cell"]),
            ]
        )
    table = Table(data, repeatRows=1, colWidths=[32 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm, 28 * mm, 30 * mm])
    table.setStyle(_standard_table_style())
    return table


def _standard_table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), TEAL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C0CECC")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F9F8")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )


def _interpretation(report: PeriodSummaryReport, language: ReportLanguage) -> str:
    assist_line = (
        f"助理首席導學風紀領導崗位覆蓋 {report.assist_filled_count}/{report.assist_required_count} 次。"
        if language == "zh"
        else f"Assistant Head leadership-post coverage: {report.assist_filled_count}/{report.assist_required_count}."
    )
    fairness_line = (
        f"目前公平帳本差距為 {report.fairness_spread:.1f} 點，母體標準差為 {report.fairness_population_stddev:.2f}。"
        if language == "zh"
        else f"The current ledger spread is {report.fairness_spread:.1f} points; population standard deviation is {report.fairness_population_stddev:.2f}."
    )
    return f"{assist_line} {fairness_line} {_text(language, 'service_not_performance')}"


def _source_line(report: PeriodSummaryReport, language: ReportLanguage) -> str:
    if not report.sources:
        return _text(language, "no_sources")
    source_text = ", ".join(
        f"#{source.roster_week_id} v{source.version} "
        f"({source.week_start:%Y-%m-%d}; policy {source.policy_version}; "
        f"history priority {source.history_priority_multiplier:.1f}x)"
        for source in report.sources
    )
    prefix = "已發布週表：" if language == "zh" else "Published rosters: "
    return xml_escape(f"{prefix}{source_text}")


def _draw_page_footer(canvas, document, font_name: str, language: ReportLanguage) -> None:  # type: ignore[no-untyped-def]
    canvas.saveState()
    canvas.setFont(font_name, 7.5)
    canvas.setFillColor(colors.HexColor("#52666B"))
    text = f"內部服務與公平記錄 ｜ 第 {document.page} 頁" if language == "zh" else f"Internal service and fairness record | Page {document.page}"
    canvas.drawCentredString(A4[0] / 2, 7 * mm, text)
    canvas.restoreState()


def _styles(fonts: dict[str, str]) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("summary-title", parent=base["Title"], fontName=fonts["semibold"], fontSize=19, leading=25, alignment=TA_CENTER, textColor=TEAL_DEEP),
        "subtitle": ParagraphStyle("summary-subtitle", parent=base["Normal"], fontName=fonts["medium"], fontSize=9, leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#4C6267")),
        "marker": ParagraphStyle("summary-marker", parent=base["Normal"], fontName=fonts["medium"], fontSize=9, leading=14, textColor=colors.HexColor("#574315"), backColor=colors.HexColor("#FFF7DE"), borderColor=colors.HexColor("#D8B85E"), borderWidth=0.5, borderPadding=7),
        "section": ParagraphStyle("summary-section", parent=base["Heading2"], fontName=fonts["semibold"], fontSize=12, leading=17, textColor=TEAL_DEEP, spaceAfter=4),
        "body": ParagraphStyle("summary-body", parent=base["Normal"], fontName=fonts["regular"], fontSize=9.2, leading=15, textColor=INK),
        "small": ParagraphStyle("summary-small", parent=base["Normal"], fontName=fonts["regular"], fontSize=8.2, leading=12.5, textColor=colors.HexColor("#4B6065")),
        "metric_label": ParagraphStyle("metric-label", parent=base["Normal"], fontName=fonts["regular"], fontSize=8.2, leading=10.5, textColor=colors.HexColor("#4B6065")),
        "metric_value": ParagraphStyle("metric-value", parent=base["Normal"], fontName=fonts["semibold"], fontSize=11, leading=13, alignment=TA_CENTER, textColor=TEAL_DEEP),
        "table_heading": ParagraphStyle("summary-table-heading", parent=base["Normal"], fontName=fonts["semibold"], fontSize=7.8, leading=10, alignment=TA_CENTER, textColor=colors.white),
        "table_cell": ParagraphStyle("summary-table-cell", parent=base["Normal"], fontName=fonts["regular"], fontSize=8.1, leading=10.5, alignment=TA_LEFT, textColor=INK),
        "table_number": ParagraphStyle("summary-table-number", parent=base["Normal"], fontName=fonts["medium"], fontSize=8.1, leading=10.5, alignment=TA_CENTER, textColor=INK),
    }


_TEXT = {
    "zh": {
        "title": "聖言中學導學風紀服務與公平總結報告",
        "internal_marker": "用途：供年度／學期審查、團隊匯報及校內存檔。公開值班表與本內部報告應分開分享。",
        "executive_summary": "執行摘要",
        "published_weeks": "已發布週數",
        "coverage": "崗位覆蓋率",
        "recorded_duties": "已記錄值班次數",
        "scheduled_hours": "已編排時數",
        "adjustments": "發布後請假調整",
        "vacancies": "最終空缺",
        "fairness_spread": "公平帳本差距",
        "ledger": "公平帳本對帳",
        "balanced": "一致",
        "review": "需要核對",
        "contribution_title": "已記錄服務參與概覽",
        "contribution_note": "時數按已發布週表的值班時段推算，只代表已編排服務，不等同出席證明或表現評級。",
        "trend_title": "歷史公平分布趨勢",
        "trend_note": "數據由公平帳本及匯入基準重建；不設手動保存按鈕，避免同一週重複計算。",
        "source_title": "資料來源與可追溯性",
        "closing_note": "公平不是把每一個人安排成完全相同，而是讓每次決定都有一致規則、可被解釋，並在有人需要關顧時作出負責任的調整。",
        "service_not_performance": "工作量只反映已記錄服務參與，不代表個人表現高低。",
        "no_period": "尚未有已發布週表；本報告只顯示目前公平帳本狀態。",
        "no_sources": "沒有已發布週表可列作本報告來源。",
        "not_applicable": "不適用",
    },
    "en": {
        "title": "Sing Yin Study Prefect Service & Fairness Summary",
        "internal_marker": "Purpose: annual or term review, team briefing, and internal archive. Keep the public weekly roster separate from this named internal report.",
        "executive_summary": "Executive summary",
        "published_weeks": "Published weeks",
        "coverage": "Post coverage",
        "recorded_duties": "Recorded duties",
        "scheduled_hours": "Scheduled hours",
        "adjustments": "Published-duty adjustments",
        "vacancies": "Final vacancies",
        "fairness_spread": "Ledger spread",
        "ledger": "Ledger reconciliation",
        "balanced": "Balanced",
        "review": "Review required",
        "contribution_title": "Recorded service participation",
        "contribution_note": "Hours are derived from published duty time windows. They show scheduled service only, not attendance evidence or a performance rating.",
        "trend_title": "Historical fairness distribution",
        "trend_note": "The series is reconstructed from the fairness ledger and import anchors; no manual snapshot button can double-count a week.",
        "source_title": "Sources and traceability",
        "closing_note": "Fairness does not mean making every assignment identical. It means applying consistent rules, explaining each decision, and adjusting responsibly when someone needs care.",
        "service_not_performance": "Workload records participation, not personal performance.",
        "no_period": "No published roster exists yet; this report only shows the current fairness-ledger state.",
        "no_sources": "There are no published roster sources for this report.",
        "not_applicable": "N/A",
    },
}


def _text(language: ReportLanguage, key: str) -> str:
    return _TEXT[language][key]


__all__ = [
    "SummaryReportDownload",
    "build_summary_report_json",
    "build_summary_report_pdf",
    "summary_report_payload",
]
