# roster/utils/pdf.py

"""

PDF generation utilities.



Extracted from original utils.py during modularization.

All content and behavior kept identical.



Depends on roster.config for styles and constants.

"""



import streamlit as st

import pandas as pd

import json

import datetime

import base64



# ====================== PDF 支援強固檢查 ======================

try:

    from weasyprint import HTML

    PDF_AVAILABLE = True

except (ImportError, OSError, Exception) as e:

    PDF_AVAILABLE = False

    _pdf_init_error = str(e)



# ====================== 模組導入 ======================

from roster.config import (

    DAYS, NASA_COLORS, get_role_style,

    PROJECT_FULL_NAME, PROJECT_FULL_NAME_EN, VERSION

)

from roster.utils.backup import get_dynamic_backup_json
from roster.core import annotate_mentoring_pairs, compute_possible_mentoring_pairs



# ====================== PDF 專用顏色樣式函數 ======================

def get_cell_style(val: str, role: str, day: str) -> str:

    """

    Generate professional cell styles for PDF export tables.

    Mirrors web get_role_style for consistency (graphic-design + streamlit-best-practices).

    Supports multi-slot roles (Room 303 -1/-2, Room 202 -1/-2).

    All styling for English professional exports.

    """

    val = str(val).strip()



    if val == "X":

        return f"color:{NASA_COLORS['x_text']}; font-weight:bold; background-color:{NASA_COLORS['x_bg']}; text-align:center; border:2px solid {NASA_COLORS['x_border']};"



    if "Room 202" in role and day in ["TUESDAY", "FRIDAY"]:

        return f"background-color:{NASA_COLORS['closed_bg']}; color:#546E7A; font-style:italic; text-align:center; border:1px solid #90A4AE;"



    if val == "":

        return f"background-color:{NASA_COLORS['empty_bg']}; text-align:center;"



    # Room-specific cell colors for PDF
    if "Room 303" in role:
        bg = NASA_COLORS["pdf_303_bg"]
        txt = NASA_COLORS["pdf_303_text"]
    elif "Room 202" in role:
        bg = NASA_COLORS["pdf_202_bg"]
        txt = NASA_COLORS["pdf_202_text"]
    elif "Assist. in charge" in role:
        bg = NASA_COLORS["pdf_assist_bg"]
        txt = NASA_COLORS["pdf_assist_text"]
    elif "Room 302" in role:
        bg = NASA_COLORS["pdf_302_bg"]
        txt = NASA_COLORS["pdf_302_text"]
    else:
        bg = "#F8FAFC"
        txt = "#1E293B"

    # Use dedicated border color for Assist. in charge
    _bdr = NASA_COLORS["pdf_assist_border"] if "Assist. in charge" in role else "#CBD5E1"
    return (
        f"font-weight:bold; text-align:center; padding:6px 5px; "
        f"background-color:{bg}; "
        f"color:{txt}; "
        f"border:1px solid {_bdr};"
    )



# ====================== A4 橫式彩色 PDF 生成引擎 (Professional English Export) ======================

def generate_pdf(roster_df: pd.DataFrame, master_report_df: pd.DataFrame, logo_b64: str = None, lang: str = "en", include_backup_page: bool = True, students_df: pd.DataFrame = None) -> bytes:

    """

    Generate highly professional English PDF report for external/official use.

    - Titles, headers, summaries in clean professional English.

    - Student names preserved in original Chinese (per strict requirements).

    - Strong visual hierarchy, clean typography (graphic-design).

    - Includes servant leadership and fairness principles (evangelical-theology).

    - If include_backup_page is True, appends a complete internal JSON backup page (default: True — always included for primary backup).

    UI remains fully Chinese; this is export-only.

    """

    # === Color System ===
    # Primary dark/header backgrounds: NASA_COLORS['header_bg']  (#0F766E teal)
    # Gold accents:           NASA_COLORS['accent_gold']
    # Room cell colors:       NASA_COLORS['pdf_*'] keys
    # To change colors, update roster/config/constants.py

    if not PDF_AVAILABLE:

        err_info = getattr(st.session_state, "_pdf_init_error", None) or "unknown error"

        st.error(f"PDF 引擎未就緒，請確認 packages.txt 已加入 weasyprint 並重新部署 ({err_info})")

        return None



    if logo_b64 is None:

        cached_logo = st.session_state.get("logo_data")

        if cached_logo:

            logo_b64 = base64.b64encode(cached_logo).decode()

        else:

            try:

                with open("logo.png", "rb") as f:

                    file_data = f.read()

                    logo_b64 = base64.b64encode(file_data).decode()

                    st.session_state["logo_data"] = file_data

            except FileNotFoundError:

                logo_b64 = None



    today = datetime.date.today().strftime("%Y-%m-%d")



    # Language-specific titles/headers for the PDF report (buttons choose report lang; names always Chinese)

    if lang == "zh":

        duty_pos_header = "值班位置"

        roster_h3 = "週值班表"

        audit_h3 = "累計工作量審計表"

        summary_strong = "執行摘要（專業中文）"

        compliance_intro = "此報告完全符合學校規定："

        ahp_text = "• AHP（Assistant 首席導學風紀）只能擔任「Assist. in charge」崗位，絕對不能排到任何 Room。"

        room302_text = "• Room 302：每天1人，放學後15:45至18:00，全週開放。"

        room303_text = "• Room 303：每天2人，放學後15:45至17:00。"

        room202_text = "• Room 202：每天2人，放學後15:45至17:00（註明星期二、五不開放）。"

        fairness_text = "• 公平規則：派班優先考慮累計負荷較低者。F.3學生在分數相同時優先。"

        leave_text = "• 「請假撤銷」單元格不計入所有工作量計算。"

        # Mentoring summary
        mentoring_pairs_dict = annotate_mentoring_pairs(roster_df, students_df) if students_df is not None else {}
        mentoring_pair_count = len(mentoring_pairs_dict)
        mentoring_possible = compute_possible_mentoring_pairs(roster_df)
        mentoring_rate = (mentoring_pair_count / mentoring_possible * 100) if mentoring_possible > 0 else 0
        if mentoring_rate >= 50:
            mentoring_rating = "優秀"
        elif mentoring_rate >= 25:
            mentoring_rating = "良好"
        else:
            mentoring_rating = "尚可"
        if mentoring_pair_count > 0:
            mentoring_summary_text = f"• 師徒配對摘要：本週形成 {mentoring_pair_count}/{mentoring_possible} 組師徒配對（配對率 {mentoring_rate:.0f}%，{mentoring_rating}）。師徒配對加分（-2.0）遠小於 AHP 崗位加成（-8.0），確保領導職位優先。"
        else:
            mentoring_summary_text = "• 本週未形成師徒配對。"
        mentoring_label = "師徒配對摘要："

        backup_note = "• 備份資料（JSON）現已預設附加於 PDF 最後一頁（內部備份用）。分享 PDF 時請移除最後一頁。"
        key_principle_label = "核心原則："

        principle_text = "負荷越低 = 未來值班優先度越高。這體現僕人領袖與公平服務精神。"

        footer_text = "內部作業使用中文介面以方便使用。本文件為官方、外部及領導層使用準備專業中文版本。<br>學生姓名依學校慣例保留中文。生成時秉持公平、負責與服務精神。"

        h1_text = PROJECT_FULL_NAME

        h2_text = "導學風紀值班表與工作量審計"

        date_sub_text = f"報告日期：{today} | 聖言中學 • 導學風紀團隊"

    else:

        duty_pos_header = "Duty Position"

        roster_h3 = "Weekly Duty Roster"

        audit_h3 = "Cumulative Workload Audit Table"

        summary_strong = "Executive Summary (Professional English)"

        compliance_intro = "This report was generated in full compliance with school regulations:"

        ahp_text = "• AHP (Assistant 首席導學風紀) may only serve in \"Assist. in charge\". Regular Study Prefects are excluded from this leadership slot."

        room302_text = "• Room 302: 1 slot/day, 15:45-18:00 after school, open all week."

        room303_text = "• Room 303: 2 slots/day, 15:45-17:00 after school."

        room202_text = "• Room 202: 2 slots/day, 15:45-17:00 after school (closed Tuesday & Friday)."

        fairness_text = "• Fairness rule: Assignments prioritize lower cumulative load. F.3 students receive tie-break preference."

        leave_text = "• \"請假撤銷\" (Leave Revocation) cells are excluded from all workload calculations."

        # Mentoring summary
        mentoring_pairs_dict = annotate_mentoring_pairs(roster_df, students_df) if students_df is not None else {}
        mentoring_pair_count = len(mentoring_pairs_dict)
        mentoring_possible = compute_possible_mentoring_pairs(roster_df)
        mentoring_rate = (mentoring_pair_count / mentoring_possible * 100) if mentoring_possible > 0 else 0
        if mentoring_rate >= 50:
            mentoring_rating = "Excellent"
        elif mentoring_rate >= 25:
            mentoring_rating = "Good"
        else:
            mentoring_rating = "Fair"
        if mentoring_pair_count > 0:
            mentoring_summary_text = f"• Mentoring Pairing Summary: {mentoring_pair_count}/{mentoring_possible} pairs formed this week (pairing rate {mentoring_rate:.0f}%, {mentoring_rating}). The mentoring bonus (-2.0) is much smaller than the AHP slot bonus (-8.0), ensuring leadership priority."
        else:
            mentoring_summary_text = "• No mentoring pairs were formed in this roster."
        mentoring_label = "Mentoring Pairing Summary:"

        backup_note = "• Backup data (JSON) is now automatically included on the final page of exported PDFs (for internal recovery). Remove the last page before sharing."

        key_principle_label = "Key Principle:"

        principle_text = "Lower load = higher priority for future duties. This embodies servant leadership and equitable service."

        footer_text = "Internal operations use Chinese UI for accessibility. This document is prepared for official, external, and leadership use in professional English.<br>Student names are preserved in Chinese per school practice. Generated with fairness, responsibility, and a spirit of service."

        h1_text = PROJECT_FULL_NAME_EN

        h2_text = "Study Prefect Duty Roster &amp; Workload Audit"

        date_sub_text = f"Report Date: {today} | Sing Yin Secondary School • Study Prefect Team"



    # ==================== 彩色值班表 HTML ====================

    html_table = "<table style='width:100%; border-collapse:collapse; font-size:11px; margin:15px 0;'>"



    # Header

    html_table += f"<tr><th style='background-color:{NASA_COLORS['header_bg']}; color:white; padding:10px; text-align:center; border:1px solid {NASA_COLORS['accent_gold']};'>{duty_pos_header}</th>"

    for day in DAYS:

        html_table += f"<th style='background-color:{NASA_COLORS['header_bg']}; color:white; padding:10px; text-align:center; border:1px solid {NASA_COLORS['accent_gold']};'>{day}</th>"

    html_table += "</tr>"



    # Data rows

    for role in roster_df.index:

        html_table += f"<tr><td style='background-color:{NASA_COLORS['header_bg']}; color:{NASA_COLORS['accent_gold']}; font-weight:bold; padding:10px; text-align:center; border:2px solid {NASA_COLORS['accent_gold']};'>{role}</td>"

        for day in DAYS:

            val = str(roster_df.at[role, day]).strip()

            style = get_cell_style(val, role, day)

            display_val = val if val else "&nbsp;"

            html_table += f"<td style='{style}'>{display_val}</td>"

        html_table += "</tr>"



    html_table += "</table>"



    # 工作負荷統計表 (English for export)

    report_table = master_report_df.to_html(index=False, classes='table') if not master_report_df.empty else "<p style='color:#666;'>No audit data available.</p>"



    # Professional English export layout (graphic-design principles: clean typography, visual hierarchy, servant leadership tone)

    # Student names remain in original Chinese as values (strict requirement). UI display stays in Chinese.

    html = f"""

    <html><head><meta charset="UTF-8">

    <style>

        @page {{ size: A4 landscape; margin: 8mm; }}

        body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e; line-height: 1.3; font-size: 9.5px; }}

        .header-container {{ text-align: center; margin-bottom: 8px; }}

        h1 {{ color:{NASA_COLORS['header_bg']}; font-size: 20px; margin: 2px 0; font-weight: 700; letter-spacing: 0.8px; }}

        h2 {{ color:{NASA_COLORS['accent_gold']}; font-size: 13px; margin: 0 0 3px 0; font-weight: 600; }}

        .date-sub {{ font-size: 9px; color: #555; margin-bottom: 6px; }}

        h3 {{ color:{NASA_COLORS['header_bg']}; border-left: 3px solid {NASA_COLORS['accent_gold']}; padding-left: 6px; margin: 10px 0 4px; font-size: 11px; font-weight: 600; }}

        table {{ width: 100%; border-collapse: collapse; margin: 4px 0; font-size: 8.5px; }}

        th, td {{ border: 0.5px solid #BDC3C7; padding: 4px 5px; text-align: center; }}

        th {{ background-color: {NASA_COLORS['header_bg']}; color: white; font-weight: 600; }}

        .summary {{ background: #f8f9fa; padding: 6px 8px; border-radius: 3px; margin: 4px 0; font-size: 8.5px; border: 0.5px solid #e0e0e0; }}

        .kpi {{ font-weight: 600; color: {NASA_COLORS['header_bg']}; }}

        .footer-note {{ font-size: 7.5px; color: #666; text-align: center; margin-top: 6px; font-style: italic; }}

    </style></head><body>

    <div class="header-container">

    """

    if logo_b64:

        html += f'<img src="data:image/png;base64,{logo_b64}" style="height:42px; margin-bottom:2px;">'

    html += f"""

        <h1>{h1_text}</h1>

        <h2>{h2_text}</h2>

        <div class="date-sub">{date_sub_text}</div>

    </div>



    <h3>{roster_h3}</h3>

    {html_table}



    <div style="page-break-before: always;"></div>



    <h3>{audit_h3}</h3>

    {report_table}



    <div class="summary">

        <strong>{summary_strong}</strong><br>

        {compliance_intro}

        <br>{ahp_text}

        <br>{room302_text}

        <br>{room303_text}

        <br>{room202_text}

        <br>{fairness_text}

        <br>{leave_text}

        <br><br>

        <span class="kpi">{mentoring_label}</span> {mentoring_summary_text}

        <br>{backup_note}

        <br><br>

        <span class="kpi">{key_principle_label}</span> {principle_text}

    </div>



    <div class="footer-note">

        {footer_text}

    </div>



    </body></html>

    """



    if include_backup_page:

        # Build complete backup dataset including students_df if available
        _bk_dict = {
            "version": "v2.4",
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "roster_df": roster_df.to_dict() if roster_df is not None and not roster_df.empty else {},
            "report_df": master_report_df.to_dict() if master_report_df is not None and not master_report_df.empty else {},
            "students_df": students_df.to_dict() if students_df is not None and not students_df.empty else {},
        }
        import json as _json
        bk_data = _json.dumps(_bk_dict, ensure_ascii=False, indent=2, default=str)

        bk_html = f"""

    <div style="page-break-before: always; font-family: monospace; font-size: 8px; color: #000; background: #fff; padding: 10px; border: 2px solid #f00;">

        <h2 style="color: #f00; text-align: center; font-size: 14px;">INTERNAL BACKUP DATA — DO NOT DISTRIBUTE</h2>

        <p style="text-align: center; font-size: 10px;">Copy the JSON block between the markers to restore the system.</p>

        <pre style="white-space: pre-wrap; word-wrap: break-word; background: #f5f5f5; padding: 5px; border: 1px solid #ccc;">

___SYSS_BACKUP_START___

{bk_data}

___SYSS_BACKUP_END___

        </pre>

    </div>

    """

        html += bk_html



    return HTML(string=html).write_pdf()





def generate_service_certificate(semester_hours: dict, logo_b64: str = None) -> bytes:

    """

    Generate a professional English PDF service certificate.

    - Professional English text and layout (graphic-design).

    - Student names kept in original Chinese.

    - Includes servant leadership and fairness notes (evangelical-theology).

    - Clean, leadership-ready format.

    """

    if not PDF_AVAILABLE:

        err_info = getattr(st.session_state, "_pdf_init_error", None) or "unknown error"

        st.error(f"PDF 引擎未就緒，請確認 packages.txt 已加入 weasyprint 並重新部署 ({err_info})")

        return None



    if logo_b64 is None:

        cached_logo = st.session_state.get("logo_data")

        if cached_logo:

            logo_b64 = base64.b64encode(cached_logo).decode()

        else:

            try:

                with open("logo.png", "rb") as f:

                    file_data = f.read()

                    logo_b64 = base64.b64encode(file_data).decode()

                    st.session_state["logo_data"] = file_data

            except FileNotFoundError:

                logo_b64 = None



    today = datetime.date.today().strftime("%Y-%m-%d")



    # Build table rows for students (name Chinese, hours)

    table_rows = ""

    for name, hours in sorted(semester_hours.items()):

        table_rows += f"""

        <tr>

            <td style="border: 1px solid #BDC3C7; padding: 6px 8px; text-align: left;">{name}</td>

            <td style="border: 1px solid #BDC3C7; padding: 6px 8px; text-align: center;">{hours:.1f}</td>

        </tr>

        """



    html = f"""

    <html><head><meta charset="UTF-8">

    <style>

        @page {{ size: A4; margin: 15mm; }}

        body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1f2937; line-height: 1.4; font-size: 11px; }}

        .header {{ text-align: center; margin-bottom: 15px; }}

        h1 {{ color:{NASA_COLORS['header_bg']}; font-size: 22px; margin: 5px 0; font-weight: 700; }}

        h2 {{ color:{NASA_COLORS['accent_gold']}; font-size: 14px; margin: 0 0 5px 0; font-weight: 600; }}

        .logo {{ height: 50px; margin-bottom: 5px; }}

        table {{ width: 80%; margin: 15px auto; border-collapse: collapse; font-size: 10px; }}

        th, td {{ border: 1px solid #BDC3C7; padding: 6px 8px; }}

        th {{ background-color: {NASA_COLORS['header_bg']}; color: white; font-weight: 600; }}

        .notes {{ margin: 15px auto; width: 80%; background: #f8fafc; padding: 10px; border-radius: 4px; border: 1px solid #e2e8f0; font-size: 9.5px; }}

        .footer {{ text-align: center; margin-top: 20px; font-size: 9px; color: #6b7280; }}

        .signature {{ margin-top: 30px; text-align: center; }}

    </style></head><body>

    <div class="header">

    """

    if logo_b64:

        html += f'<img src="data:image/png;base64,{logo_b64}" class="logo">'

    html += f"""

        <h1>{PROJECT_FULL_NAME_EN}</h1>

        <h2>Study Prefect Semester Service Certificate</h2>

        <p style="margin: 5px 0; font-size: 10px;">Report Date: {today}</p>

    </div>



    <p style="text-align: center; width: 80%; margin: 10px auto;">This certificate confirms that the following prefects have completed their assigned service hours this semester, contributing to the school's values of fairness, responsibility, and servant leadership.</p>



    <table>

        <tr><th>Student Name (Chinese)</th><th>Service Hours</th></tr>

        {table_rows}

    </table>



    <div class="notes">

        <strong>Notes (Professional English):</strong><br>

        • Service hours are calculated based on assigned duties (1 hour per slot).<br>

        • All assignments followed strict school rules (AHP gates, Room 302/303 restrictions, fairness mechanisms).<br>

        • "請假撤銷" (Leave Revocation) periods do not count toward service hours.<br>

        <br>

        <strong>Core Principle:</strong> Lower cumulative load indicates higher priority for future duties. This promotes equity and a culture of service.

    </div>



    <div class="signature">

        <p>Issued with appreciation for dedicated service.</p>

        <p><strong>Head Study Prefect (首席導學風紀)</strong><br>Sing Yin Secondary School</p>

    </div>



    <div class="footer">

        Internal management uses Chinese UI. This document is for official records in professional English. Student names preserved in Chinese.

    </div>

    </body></html>

    """



    return HTML(string=html).write_pdf()

