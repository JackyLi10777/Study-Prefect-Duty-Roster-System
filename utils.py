# utils.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
工具模組 - PDF 生成、系統備份/還原、名冊導入引擎

作者：Head Study Prefect 26-27 LI Chuangjie Jacky
版本：v2.3 Final（完整支援全局負荷滑桿、多槽位排班、彩色 PDF、JSON 備份解決 Cloud 休眠問題）
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
from config import (
    DAYS, ROWS_ROSTER, NASA_COLORS, get_role_style,
    PROJECT_FULL_NAME, VERSION, GEMINI_MODEL
)
from data import get_demo_dataframe, get_sample_format_dataframe

# ====================== Gemini 配置（AI 導入後備使用） ======================
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    import google.generativeai as genai
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(GEMINI_MODEL)
else:
    model = None

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

# ====================== 名冊導入引擎（傳統格式） ======================
def process_roster_import(uploaded_file):
    """傳統格式 Excel/CSV 導入（後備方案）"""
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # 欄位智能映射
        mapping = {
            '姓名': 'name', 'name': 'name', 'Prefect Name': 'name', '學生姓名': 'name',
            '年級': 'form', 'form': 'form', 'Form': 'form',
            '班別': 'class', 'class': 'class', 'Class': 'class',
            '職級': 'role', 'role': 'role', 'Role': 'role',
            '學年固定總值班': 'fixed_general_duty', 'fixed_general_duty': 'fixed_general_duty',
            '可用日子': 'available', 'available': 'available',
            '歷史累計(次)': 'history_duties', 'history_duties': 'history_duties',
            '歷史動態(點)': 'history_weight', 'history_weight': 'history_weight',
            '備註': 'remarks', 'remarks': 'remarks'
        }

        df = df.rename(columns=lambda x: mapping.get(str(x).strip(), str(x).strip()))

        required_cols = ["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "remarks"]
        for col in required_cols:
            if col not in df.columns:
                if col == "fixed_general_duty":
                    df[col] = "NONE"
                elif col == "available":
                    df[col] = "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"
                elif col == "history_duties":
                    df[col] = 0
                elif col == "history_weight":
                    df[col] = 0.0
                else:
                    df[col] = ""

        df = df[required_cols].copy()
        df["name"] = df["name"].astype(str).str.strip()
        df = df[(df["name"] != "") & (df["name"] != "nan")]
        df["history_duties"] = pd.to_numeric(df["history_duties"], errors='coerce').fillna(0).astype(int)
        df["history_weight"] = pd.to_numeric(df["history_weight"], errors='coerce').fillna(0.0)

        st.session_state.students_df = df.reset_index(drop=True)
        st.sidebar.success(f"🎉 傳統格式導入成功！共 {len(df)} 位領袖生")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"❌ 傳統導入失敗: {str(e)}")


# ====================== AI 智能名冊導入 ======================
def smart_process_roster_import(uploaded_file):
    """AI 智能自動匹配欄位導入（Gemini 支援任意格式）"""
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        if df.empty or len(df.columns) < 2:
            st.error("❌ 檔案為空或格式不正確")
            return

        from ai_parser import get_column_mapping_from_ai
        mapping = get_column_mapping_from_ai(df)

        rename_dict = {v: k for k, v in mapping.items() if v in df.columns}
        df = df.rename(columns=rename_dict)

        required_cols = ["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "remarks"]
        for col in required_cols:
            if col not in df.columns:
                if col == "fixed_general_duty":
                    df[col] = "NONE"
                elif col == "available":
                    df[col] = "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"
                elif col == "history_duties":
                    df[col] = 0
                elif col == "history_weight":
                    df[col] = 0.0
                else:
                    df[col] = ""

        df["name"] = df["name"].astype(str).str.strip()
        df = df[df["name"].notna() & (df["name"] != "")]
        df["history_duties"] = pd.to_numeric(df["history_duties"], errors="coerce").fillna(0).astype(int)
        df["history_weight"] = pd.to_numeric(df["history_weight"], errors="coerce").fillna(0.0)

        st.session_state.students_df = df[required_cols].reset_index(drop=True)
        st.success(f"🎉 AI 智能導入成功！已處理 {len(df)} 位領袖生（自動匹配欄位）")
        st.rerun()

    except Exception as e:
        st.error(f"❌ AI 智能導入失敗: {str(e)}")
        st.info("💡 提示：若 AI 無法解析，請改用「傳統格式導入」")


# ====================== 系統完整備份 / 還原（解決 Cloud 休眠） ======================
def export_system_backup(master_report_df: pd.DataFrame) -> str:
    """導出完整系統狀態（包含全局負荷滑桿）"""
    backup_data = {
        "students_df": st.session_state.students_df.to_dict(orient="records"),
        "roster_df": st.session_state.roster_df.to_dict(orient="index"),
        "manual_weights": st.session_state.manual_weights.to_dict(orient="index"),
        "master_report": master_report_df.to_dict(orient="records") if not master_report_df.empty else [],
        "leave_tracker_input": st.session_state.get("leave_tracker_input", []),
        "global_load_multiplier": st.session_state.get("global_load_multiplier", 1.0),
        "logo_data": base64.b64encode(st.session_state.logo_data).decode() if st.session_state.get("logo_data") else None,
        "version": VERSION,
        "timestamp": datetime.datetime.now().isoformat()
    }
    return json.dumps(backup_data, ensure_ascii=False, indent=2)


def import_system_backup(uploaded_json_file):
    """還原完整系統狀態"""
    try:
        data = json.load(uploaded_json_file)

        # 還原學生名冊
        if "students_df" in data:
            st.session_state.students_df = pd.DataFrame(data["students_df"])

        # 還原排班表
        if "roster_df" in data:
            restored_roster = pd.DataFrame.from_dict(data["roster_df"], orient="index")
            st.session_state.roster_df = restored_roster.reindex(index=ROWS_ROSTER, columns=DAYS).fillna("")

        # 還原手動調整負荷
        if "manual_weights" in data:
            manual_df = pd.DataFrame.from_dict(data["manual_weights"], orient="index")
            st.session_state.manual_weights = manual_df.reindex(index=ROWS_ROSTER, columns=DAYS).fillna(0.0)

        # 還原全局負荷滑桿
        if "global_load_multiplier" in data:
            st.session_state.global_load_multiplier = float(data["global_load_multiplier"])

        # 還原請假人員
        st.session_state.leave_tracker_input = data.get("leave_tracker_input", [])

        # 還原校徽
        if data.get("logo_data"):
            st.session_state.logo_data = base64.b64decode(data["logo_data"])

        st.sidebar.success("🔮 備份已完美還原（包含全局負荷滑桿與所有數據）！")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"❌ 還原失敗: {str(e)}")


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


print("✅ utils.py 已載入完成 - PDF 引擎、備份還原、名冊導入模組就緒（已支援全局負荷滑桿）")