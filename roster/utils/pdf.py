# roster/utils/pdf.py
"""
PDF generation utilities.

Extracted from original utils.py during modularization.
All content and behavior kept identical.

Depends on roster.config for styles and constants.
"""

import streamlit as st
import pandas as pd
import io
import json
import datetime
import base64
import random

# ====================== PDF 支援強固檢查 ======================
try:
    from weasyprint import HTML
    PDF_AVAILABLE = True
except (ImportError, OSError, Exception) as e:
    PDF_AVAILABLE = False
    st.warning("⚠️ WeasyPrint 未就緒（PDF 功能暫時無法使用）。請確認 GitHub 已加入 packages.txt 並重新部署。")

# ====================== 模組導入 ======================
from roster.config import (
    DAYS, NASA_COLORS, get_role_style,
    PROJECT_FULL_NAME_EN, VERSION
)
from roster.utils.backup import get_dynamic_backup_json

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

    if "Room202" in role and day in ["TUESDAY", "FRIDAY"]:
        return f"background-color:{NASA_COLORS['closed_bg']}; color:#546E7A; font-style:italic; text-align:center; border:1px solid #90A4AE;"

    if val == "":
        return f"background-color:{NASA_COLORS['empty_bg']}; text-align:center;"

    style = get_role_style(role, day)

    return (
        f"font-weight:bold; text-align:center; padding:6px 5px; "
        f"background-color:{style['bg']}; "
        f"color:{style['text']}; "
        f"border:{style['border']};"
    )

# ====================== A4 橫式彩色 PDF 生成引擎 (Professional English Export) ======================
def generate_pdf(roster_df: pd.DataFrame, master_report_df: pd.DataFrame, logo_b64: str = None) -> bytes:
    """
    Generate highly professional English PDF report for external/official use.
    - Titles, headers, summaries in clean professional English.
    - Student names preserved in original Chinese (per strict requirements).
    - Strong visual hierarchy, clean typography (graphic-design).
    - Includes servant leadership and fairness principles (evangelical-theology).
    UI remains fully Chinese; this is export-only.
    """
    if not PDF_AVAILABLE:
        # Error is in Chinese for UI context, but this function is for English exports
        st.error("PDF 引擎未就緒，請確認 packages.txt 已加入 weasyprint 並重新部署")
        return None

    if logo_b64 is None:
        if st.session_state.get("logo_data"):
            logo_b64 = base64.b64encode(st.session_state.logo_data).decode()
        else:
            try:
                with open("logo.png", "rb") as f:
                    logo_data = f.read()
                    logo_b64 = base64.b64encode(logo_data).decode()
                    st.session_state.logo_data = logo_data
            except FileNotFoundError:
                logo_b64 = None

    today = datetime.date.today().strftime("%Y-%m-%d")

    # ==================== 彩色值班表 HTML ====================
    html_table = "<table style='width:100%; border-collapse:collapse; font-size:11px; margin:15px 0;'>"

    # Header
    html_table += f"<tr><th style='background-color:{NASA_COLORS['header_bg']}; color:white; padding:10px; text-align:center; border:1px solid #D4AF37;'>Duty Position</th>"
    for day in DAYS:
        html_table += f"<th style='background-color:{NASA_COLORS['header_bg']}; color:white; padding:10px; text-align:center; border:1px solid #D4AF37;'>{day}</th>"
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
        h1 {{ color:#0B1E3D; font-size: 20px; margin: 2px 0; font-weight: 700; letter-spacing: 0.8px; }}
        h2 {{ color:#D4AF37; font-size: 13px; margin: 0 0 3px 0; font-weight: 600; }}
        .date-sub {{ font-size: 9px; color: #555; margin-bottom: 6px; }}
        h3 {{ color:#0B1E3D; border-left: 3px solid #D4AF37; padding-left: 6px; margin: 10px 0 4px; font-size: 11px; font-weight: 600; }}
        table {{ width: 100%; border-collapse: collapse; margin: 4px 0; font-size: 8.5px; }}
        th, td {{ border: 0.5px solid #BDC3C7; padding: 4px 5px; text-align: center; }}
        th {{ background-color: #0B1E3D; color: white; font-weight: 600; }}
        .summary {{ background: #f8f9fa; padding: 6px 8px; border-radius: 3px; margin: 4px 0; font-size: 8.5px; border: 0.5px solid #e0e0e0; }}
        .kpi {{ font-weight: 600; color: #0B1E3D; }}
        .footer-note {{ font-size: 7.5px; color: #666; text-align: center; margin-top: 6px; font-style: italic; }}
    </style></head><body>
    <div class="header-container">
    """
    if logo_b64:
        html += f'<img src="data:image/png;base64,{logo_b64}" style="height:42px; margin-bottom:2px;">'
    html += f"""
        <h1>{PROJECT_FULL_NAME_EN}</h1>
        <h2>Study Prefect Duty Roster &amp; Workload Audit</h2>
        <div class="date-sub">Report Date: {today} | Sing Yin Secondary School • Study Prefect Team</div>
    </div>

    <h3>Weekly Duty Roster</h3>
    {html_table}

    <div style="page-break-before: always;"></div>

    <h3>Cumulative Workload Audit Table</h3>
    {report_table}

    <div class="summary">
        <strong>Executive Summary (Professional English)</strong><br>
        This report was generated in full compliance with school regulations:
        <br>• AHP (Assistant Head Study Prefect) may only serve in "Assist. in charge". Regular Study Prefects are excluded from this leadership slot.
        <br>• Room 302: 1 slot/day, weight 1.0, open all days.
        <br>• Room 303: 2 slots/day (separate people required), weight 1.5 each, open all days.
        <br>• Room 202: 2 slots, weight 1.5, closed Tue/Fri (shown as ⬜).
        <br>• Fairness rule: Assignments prioritize lower cumulative load. F.3 students receive tie-break preference.
        <br>• "請假撤銷" (Leave Revocation) cells are excluded from all workload calculations.
        <br><br>
        <span class="kpi">Key Principle:</span> Lower load = higher priority for future duties. This embodies servant leadership and equitable service.
    </div>

    <div class="footer-note">
        Internal operations use Chinese UI for accessibility. This document is prepared for official, external, and leadership use in professional English.<br>
        Student names are preserved in Chinese per school practice. Generated with fairness, responsibility, and a spirit of service.
    </div>

    <!-- BACKUP DATA PAGE - INTERNAL USE ONLY - REMOVE THIS PAGE BEFORE DISTRIBUTION -->
    <div style="page-break-before: always; font-family: monospace; font-size: 8px; color: #000; background: #fff; padding: 10px; border: 2px solid #f00;">
        <h2 style="color: #f00; text-align: center; font-size: 14px;">BACKUP DATA - INTERNAL USE ONLY - PLEASE REMOVE THIS PAGE BEFORE DISTRIBUTION</h2>
        <p style="text-align: center;">This page contains dynamic data in JSON format for recovery purposes. It is not part of the official report.</p>
        <pre style="white-space: pre-wrap; word-wrap: break-word; background: #f5f5f5; padding: 5px; border: 1px solid #ccc;">
{backup_json_str}
        </pre>
    </div>
    </body></html>
    """.format(backup_json_str=get_dynamic_backup_json(master_report_df))

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
        st.error("PDF 引擎未就緒，請確認 packages.txt 已加入 weasyprint 並重新部署")
        return None

    if logo_b64 is None:
        if st.session_state.get("logo_data"):
            logo_b64 = base64.b64encode(st.session_state.logo_data).decode()
        else:
            try:
                with open("logo.png", "rb") as f:
                    logo_data = f.read()
                    logo_b64 = base64.b64encode(logo_data).decode()
                    st.session_state.logo_data = logo_data
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
        h1 {{ color:#0B1E3D; font-size: 22px; margin: 5px 0; font-weight: 700; }}
        h2 {{ color:#D4AF37; font-size: 14px; margin: 0 0 5px 0; font-weight: 600; }}
        .logo {{ height: 50px; margin-bottom: 5px; }}
        table {{ width: 80%; margin: 15px auto; border-collapse: collapse; font-size: 10px; }}
        th, td {{ border: 1px solid #BDC3C7; padding: 6px 8px; }}
        th {{ background-color: #0B1E3D; color: white; font-weight: 600; }}
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
        <p><strong>Head Study Prefect</strong><br>Sing Yin Secondary School</p>
    </div>

    <div class="footer">
        Internal management uses Chinese UI. This document is for official records in professional English. Student names preserved in Chinese.
    </div>
    </body></html>
    """

    return HTML(string=html).write_pdf()
