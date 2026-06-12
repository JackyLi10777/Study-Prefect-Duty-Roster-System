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
    PROJECT_FULL_NAME, VERSION
)

# ====================== PDF 專用顏色樣式函數 ======================
def get_cell_style(val: str, role: str, day: str) -> str:
    """
    為 PDF 表格生成 cell style（與 Web 版 get_role_style 邏輯完全一致）
    支援多槽位角色（Room 303 -1 / -2、Room 202 -1 / -2）
    """
    val = str(val).strip()

    if val == "X":
        return f"color:{NASA_COLORS['x_text']}; font-weight:bold; background-color:{NASA_COLORS['x_bg']}; text-align:center; border:2px solid {NASA_COLORS['x_border']};"

    # Room 202 常規不開放日顯示 ⬜
    if "Room202" in role and day in ["TUESDAY", "FRIDAY"]:
        return f"background-color:{NASA_COLORS['closed_bg']}; color:#546E7A; font-style:italic; text-align:center; border:1px solid #90A4AE;"

    if val == "":
        return f"background-color:{NASA_COLORS['empty_bg']}; text-align:center;"

    # 使用 config.py 的 get_role_style 確保 Web 與 PDF 顏色 100% 一致
    style = get_role_style(role, day)

    return (
        f"font-weight:bold; text-align:center; padding:9px 7px; "
        f"background-color:{style['bg']}; "
        f"color:{style['text']}; "
        f"border:{style['border']};"
    )

# ====================== A4 橫式彩色 PDF 生成引擎 ======================
def generate_pdf(roster_df: pd.DataFrame, master_report_df: pd.DataFrame, logo_b64: str = None) -> bytes:
    """生成專業彩色 PDF 公告版（含校徽、每日聖經金句、角色背景色）"""
    if not PDF_AVAILABLE:
        st.error("❌ PDF 引擎未就緒，請確認 packages.txt 已加入 weasyprint 並重新部署")
        return None

    # 確保有校徽
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
    html_table += f"<tr><th style='background-color:{NASA_COLORS['header_bg']}; color:white; padding:10px; text-align:center; border:1px solid #D4AF37;'>崗位</th>"
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

    # 工作負荷統計表
    report_table = master_report_df.to_html(index=False, classes='table') if not master_report_df.empty else "<p style='color:#666;'>尚無審計數據</p>"

    html = f"""
    <html><head><meta charset="UTF-8">
    <style>
        @page {{ size: A4 landscape; margin: 12mm; }}
        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.4; }}
        .header-container {{ text-align: center; margin-bottom: 15px; }}
        h1 {{ color:{NASA_COLORS['header_bg']}; font-size: 24px; margin: 5px 0; }}
        h2 {{ color:{NASA_COLORS['accent_gold']}; font-size: 15px; margin: 0 0 8px 0; font-weight: 600; }}
        .date-sub {{ font-size: 11px; color: #666; margin-bottom: 12px; }}
        h3 {{ color:{NASA_COLORS['header_bg']}; border-left: 5px solid {NASA_COLORS['accent_gold']}; padding-left: 10px; margin-top: 20px; font-size: 15px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 11px; }}
        th, td {{ border: 1px solid #BDC3C7; padding: 8px 10px; text-align: center; }}
        th {{ background-color: {NASA_COLORS['header_bg']}; color: white; font-weight: bold; }}
    </style></head><body>
    <div class="header-container">
    """
    if logo_b64:
        html += f'<img src="data:image/png;base64,{logo_b64}" style="height:60px; margin-bottom:8px;">'
    html += f"""
        <h1>{PROJECT_FULL_NAME}</h1>
        <h2>Study Prefect Duty Roster & Workload Audit</h2>
        <div class="date-sub">Report Generated: {today}</div>
    </div>
    <h3>📅 本週值班表 (Weekly Duty Roster)</h3>
    {html_table}
    <div style="page-break-before: always;"></div>
    <h3>📊 累積動態工作負荷審計表</h3>
    {report_table}
    </body></html>
    """

    return HTML(string=html).write_pdf()
