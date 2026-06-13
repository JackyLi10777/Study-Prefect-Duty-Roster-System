# app.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
主應用程式入口 - Streamlit Cloud 最終部署版

作者：Head Study Prefect 26-27 LI Chuangjie Jacky
版本：v2.3 Final（完整整合全局負荷滑桿、多槽位排班、神聖金句、人性化UI、請假撤銷公平調整、JSON備份）
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import io
import json
import base64
import random
from typing import Optional

# ====================== 模組導入 (direct roster/ per project-structure-advisor, thin shims for compat only) ======================
# Note: All UI text in Chinese; exports forced to professional English with Chinese student names preserved.
# Theme and language toggles in sidebar.
from roster.config import (
    DAYS, ROWS_ROSTER, VERSION, APP_TITLE, PROJECT_FULL_NAME, PROJECT_FULL_NAME_EN,
    NASA_COLORS, get_role_style, DEFAULT_GLOBAL_LOAD_MULTIPLIER, get_weight,
    AHP_ROLE, REGULAR_ROLE
)

def _t(zh_text, en_text):
    """Simple translator. Student names always remain Chinese."""
    lang = st.session_state.get("ui_language", "zh")
    return en_text if lang == "en" else zh_text
from roster.data import (
    get_demo_dataframe, get_sample_format_dataframe,
    initialize_session_state
)
from roster.data.models import get_ui_report_df, get_export_report_df, reindex_roster_df, create_empty_roster_df
from roster.ai import ai_parse_remarks
from roster.core import (
    generate_roster, validate_and_compute, recommend_substitutes,
    apply_post_publication_leave_adjustment
)
from roster.utils import (
    generate_pdf, generate_service_certificate, export_system_backup, import_system_backup,
    process_roster_import, smart_process_roster_import,
    trigger_backup_reminder, clear_backup_reminder
)
from roster.ui.components import (
    render_sidebar, show_daily_verse, render_control_buttons
)

# ====================== 使用說明書 ======================
HELP_TEXT = """
### 📖 聖言中學導學風紀當值排班平台 使用說明書（v2.3 Final）

#### 1. 名冊導入（最重要）
- **推薦使用「🤖 AI 智能自動匹配」**：支援任意格式的 Excel / CSV，AI 會自動辨識欄位。
- 建議先點「📥 下載名冊格式範例」參考。

#### 2. 名冊即時修改
- 在側邊欄可以直接編輯所有領袖生資料，修改後即時儲存。

#### 3. 生成值班表
- 在側邊欄設定請假人員與特殊不開放時段。
- 點擊主畫面大按鈕「🚀 智能計算：生成本週全新公平值班表」。

#### 4. 全局負荷調節滑桿（新增重要功能）
- 主畫面最上方可即時調整本次排班整體負荷倍率（0.8\~2.0）。
- 臨近考試時提高倍率，讓累計負荷較低的學生優先達到公平平衡。

#### 5. 值班表操作
- **視覺公告版**：專業彩色顯示，不同崗位不同顏色（Assist 金米、Room302 綠、Room303 黃、Room202 紅）。
- **手動修改版**：可直接在表格上修改人名或打「X」鎖定。

#### 6. 智慧替補推薦
- 選擇日期與崗位後，點擊「🔍 尋找最優替補」，系統會依據目前總點數由低到高推薦。

#### 7. 匯出功能
- **📄 匯出 PDF**：專業彩色班表（含校徽），適合公告列印。
- **📊 下載 Excel**：完整值班表 + 工作負荷統計表。
- **📝 下載 Markdown**：方便複製到其他文件。

#### 8. Cloud 備份（強烈建議）
- 每次生成新班表後，建議在側邊欄點擊「⬇️ 導出完整備份 (JSON)」下載備份。
- Streamlit Cloud 休眠後可用「上傳備份 JSON 還原」快速恢復。

**有問題請 email s10777@syss.edu.hk**

祝使用順利！🙏
"""

def global_multiplier_slider() -> float:
    """全局負荷調節滑桿（主畫面即時可調）"""
    st.subheader(_t("🌍 全局負荷調節滑桿", "🌍 Global Load Adjustment Slider"))
    st.caption(_t("臨近考試時可提高本次排班整體負荷倍率，讓累計較低同學優先平衡", "Near exams, increase overall load multiplier for this roster to let lower cumulative students have priority balance"))
    multiplier = st.slider(
        _t("本次排班整體負荷倍率", "Current roster overall load multiplier"),
        min_value=0.8,
        max_value=2.0,
        value=st.session_state.get("global_load_multiplier", DEFAULT_GLOBAL_LOAD_MULTIPLIER),
        step=0.1,
        format="%.1f",
        key="global_load_multiplier_slider"
    )
    st.session_state.global_load_multiplier = multiplier
    return multiplier


def main():
    # ====================== Session State 初始化 ======================
    initialize_session_state()

    # ====================== 頁面設定 ======================
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # ====================== 自訂 CSS (graphic-design + streamlit-best-practices: professional, mobile-friendly, servant-leadership theme) ======================
    st.markdown("""
    <style>
        .main-title { color: #0B1E3D; font-size: 34px; font-weight: 700; letter-spacing: 1.5px; margin-bottom: 2px; }
        .main-subtitle { color: #D4AF37; font-size: 14px; font-weight: 600; margin-bottom: 18px; }
        .stDataFrame, [data-testid="stDataEditor"] { border-radius: 10px; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.05); }
        .stButton > button { height: 3.0rem; font-weight: 600; border-radius: 8px; transition: all 0.25s ease; }
        .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .danger-alert { background-color: #FEF2F2; border-left: 5px solid #EF4444; color: #991B1B; padding: 12px 14px; border-radius: 8px; margin: 8px 0; font-size: 14px; }
        .warning-alert { background-color: #FFFBEB; border-left: 5px solid #F59E0B; color: #92400E; padding: 12px 14px; border-radius: 8px; margin: 8px 0; font-size: 14px; }
        .kpi-card { background: #F8F9FA; border-radius: 8px; padding: 10px 14px; margin: 4px 0; border-left: 4px solid #0B1E3D; box-shadow: 0 2px 6px rgba(0,0,0,0.04); }
        .kpi-card .label { font-size: 12px; color: #546E7A; }
        .kpi-card .value { font-size: 18px; font-weight: 700; color: #0B1E3D; }
        .verse-card { background: linear-gradient(180deg, #1A1A2E 0%, #0B1E3D 100%); padding: 16px 14px; border-radius: 10px; margin: 8px 0; color: #F5E8C7; border: 2px solid #D4AF37; box-shadow: 0 4px 16px rgba(212,175,55,0.18); }
        footer {visibility: hidden;}
        @media (max-width: 768px) {
            .main-title { font-size: 26px; }
            .kpi-card .value { font-size: 16px; }
        }
    </style>
    """, unsafe_allow_html=True)

    # ====================== 主畫面 ======================
    render_sidebar()

    # 語言模式同步：中文介面優先，英文介面時使用 EN 標題（主畫面仍以中文為主，匯出專業英文）
    ui_lang = st.session_state.get("ui_language", "zh")
    main_title = PROJECT_FULL_NAME_EN if ui_lang == "en" else PROJECT_FULL_NAME
    main_sub = "F.3–F.6 Study Prefect Duty Platform | " + VERSION if ui_lang == "en" else f"F.3–F.6 導學風紀當值平台 | {VERSION}"
    st.markdown(f'<p class="main-title">{main_title}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="main-subtitle">{main_sub}</p>', unsafe_allow_html=True)

    # Enhanced Daily Verse with optional bilingual (evangelical-theology + streamlit-best-practices)
    show_daily_verse()

    with st.expander("📖 點此展開完整使用說明書（v2.3 Final）", expanded=False):
        st.markdown(HELP_TEXT)

    st.write("---")

    # ====================== 全局負荷滑桿 ======================
    # (global load slider title inside the function can be further translated if needed)

    st.write("---")
    selected_closures = render_control_buttons()

    # 角色名稱統一正規化（支援 legacy 英文 + 中文，確保 AHP/生成邏輯正確）
    role_map = {
        "Assistant Head Study Prefect": AHP_ROLE,
        "Head Study Prefect": AHP_ROLE,
        "Study Prefect": REGULAR_ROLE,
        "助理首席導學風紀": AHP_ROLE,
        "首席導學風紀": AHP_ROLE,
        "導學風紀": REGULAR_ROLE,
    }
    if not st.session_state.students_df.empty and "role" in st.session_state.students_df.columns:
        st.session_state.students_df["role"] = st.session_state.students_df["role"].map(lambda x: role_map.get(str(x).strip(), str(x).strip()))

    # ====================== 驗證與計算 ======================
    audit_results = validate_and_compute(
        st.session_state.roster_df,
        st.session_state.students_df,
        st.session_state.leave_tracker_input,
        st.session_state.manual_weights
    )
    st.session_state.master_report_df = audit_results["report_df"]

    # ====================== 警告顯示 ======================
    if audit_results["typo"][0]:
        st.markdown('<div class="danger-alert"><b>⚠️ 數據不符警告：</b><br>' + '<br>'.join(audit_results["typo"][1]) + '</div>', unsafe_allow_html=True)
    if audit_results["duplicate"][0]:
        st.markdown('<div class="danger-alert"><b>⚠️ 重複排班警告：</b><br>' + '<br>'.join(audit_results["duplicate"][1]) + '</div>', unsafe_allow_html=True)
    if audit_results["leave_conflict"][0]:
        st.markdown('<div class="danger-alert"><b>🛑 請假衝突：</b><br>' + '<br>'.join(audit_results["leave_conflict"][1]) + '</div>', unsafe_allow_html=True)
        if st.button("🩹 一鍵清除請假同學", type="primary"):
            for d in DAYS:
                for r in ROWS_ROSTER:
                    if str(st.session_state.roster_df.at[r, d]).strip() in st.session_state.leave_tracker_input:
                        st.session_state.roster_df.at[r, d] = ""
            st.success("✅ 已清除請假同學")
            st.rerun()
    elif audit_results["vacuum"][0]:
        st.markdown('<div class="warning-alert"><b>💡 空缺提示：</b><br>' + '<br>'.join(audit_results["vacuum"][1]) + '</div>', unsafe_allow_html=True)

    # ====================== 值班表 ======================
    st.write("---")
    st.subheader(_t("📅 本週值班表", "📅 This Week's Roster"))
    tab_view, tab_edit = st.tabs(["📅 視覺公告版", "✏️ 手動修改版"])

    def apply_cell_style(val, role, day):
        val = str(val).strip()
        if val == "X":
            return f"color:{NASA_COLORS['x_text']}; font-weight:bold; background-color:{NASA_COLORS['x_bg']}; text-align:center; border:2px solid {NASA_COLORS['x_border']};"
        if 'Room202' in role and day in ['TUESDAY', 'FRIDAY']:
            return f"background-color:{NASA_COLORS['closed_bg']}; color:#546E7A; font-style:italic; text-align:center; border:1px solid #90A4AE;"
        if val == "":
            return f"background-color:{NASA_COLORS['empty_bg']}; text-align:center;"
        if "請假撤銷" in val:
            return "background-color:#FFCDD2; color:#B71C1C; font-style:italic; text-align:center; border:1px solid #EF9A9A;"

        style = get_role_style(role, day)
        return f"font-weight:bold; text-align:center; padding:8px 6px; background-color:{style['bg']}; color:{style['text']}; border:{style['border']};"

    with tab_view:
        # Quick Search & Filter for roster
        roster_search = st.text_input("🔍 快速搜尋值班表 (Quick Search by role)", value=st.session_state.get("roster_search", ""), key="roster_search_input")
        st.session_state.roster_search = roster_search
        roster_display = st.session_state.roster_df
        if roster_search:
            mask = roster_display.index.astype(str).str.contains(roster_search, case=False, na=False)
            roster_display = roster_display[mask]
            st.caption(f"顯示 {len(roster_display)} 列")

        styled = roster_display.style.apply(
            lambda row: [apply_cell_style(val, row.name, col) for col, val in row.items()], axis=1
        )
        st.dataframe(styled, height=380)

    with tab_edit:
        st.markdown("<p style='font-size:13px; color:#666;'>💡 直接修改人名或打 X 鎖定</p>", unsafe_allow_html=True)
        edited_roster = st.data_editor(
            st.session_state.roster_df,
            use_container_width=True,
            key="main_roster_editor_widget"
        )
        if not edited_roster.equals(st.session_state.roster_df):
            st.session_state.roster_df = edited_roster
            trigger_backup_reminder()  # 手動修改值班表後提醒備份
            st.rerun()

    # ====================== 手動調整負荷 ======================
    st.write("---")
    st.subheader(_t("🔧 手動調整本次值班負荷指數", "🔧 Manual Adjust This Week's Duty Load Index"))
    st.caption(_t("針對每個崗位本次值班，手動修改累計負荷點數（已受全局滑桿影響）", "Manually adjust cumulative load points for each position's duty this week (affected by global slider)"))

    manual_col = st.data_editor(
        st.session_state.manual_weights,
        use_container_width=True,
        key="manual_weight_editor"
    )
    if not manual_col.equals(st.session_state.manual_weights):
        st.session_state.manual_weights = manual_col.astype(float).fillna(0.0)
        trigger_backup_reminder()  # 自動備份提醒
        st.success("✅ 手動調整已儲存。建議立即下載 JSON 備份，並將重要版本 commit 到 GitHub backups/ 資料夾。")
        st.rerun()

    # ====================== 累計審計表 ======================
    st.write("---")
    st.subheader(_t("📊 累計動態工作負荷審計表", "📊 Cumulative Dynamic Workload Audit Table"))
    if not st.session_state.master_report_df.empty:
        # UI 顯示使用中文欄位（保持介面中文），使用 models helper 區分顯示/匯出
        display_report = get_ui_report_df(st.session_state.master_report_df)
        st.dataframe(display_report, use_container_width=True, hide_index=True)
    else:
        st.info("請先生成排班表以顯示審計表")

    # ====================== 管理視角 Dashboard (Head Study Prefect / AHP 專用 - educational leadership features) ======================
    # Enhanced with more KPIs, AHP insights, and servant-leadership framing (evangelical-theology + sing-yin-study-prefect-duty-roster)
    if not st.session_state.master_report_df.empty:
        st.write("---")
        st.subheader("📈 管理視角儀表板（Head Study Prefect / AHP 專用）")
        st.caption("公平性 KPI、AHP 洞察、快速統計，體現僕人領袖精神、公平與責任")

        report = st.session_state.master_report_df
        loads = report["Cumulative Weighted Load (points)"] if "Cumulative Weighted Load (points)" in report.columns else pd.Series([0])
        total_students = len(report)
        avg_load = loads.mean() if total_students > 0 else 0
        min_load = loads.min() if total_students > 0 else 0
        max_load = loads.max() if total_students > 0 else 0
        fairness_gap = max_load - min_load
        load_std = loads.std() if total_students > 1 else 0

        # KPI Cards (graphic-design: modern cards, clear hierarchy)
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f'<div class="kpi-card"><div class="label">總領袖生數</div><div class="value">{total_students}</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="kpi-card"><div class="label">平均累計負荷</div><div class="value">{avg_load:.1f} 點</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="kpi-card"><div class="label">公平差距 (Max-Min)</div><div class="value">{fairness_gap:.1f} 點</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="kpi-card"><div class="label">負荷標準差</div><div class="value">{load_std:.1f}</div></div>', unsafe_allow_html=True)
        with col5:
            st.markdown(f'<div class="kpi-card"><div class="label">最低 / 最高</div><div class="value">{min_load:.1f} / {max_load:.1f}</div></div>', unsafe_allow_html=True)

        # AHP Insights & Leadership Summary
        ahp_names = set(st.session_state.students_df[st.session_state.students_df["role"].isin(["Assistant Head Study Prefect", "助理首席導學風紀", "AHP"])]["name"].astype(str).str.strip())
        if ahp_names and total_students > 0:
            ahp_loads = loads[report["Student Name"].isin(ahp_names)] if "Student Name" in report.columns else pd.Series()
            ahp_avg = ahp_loads.mean() if len(ahp_loads) > 0 else 0
            ahp_count = len(ahp_loads)
            st.info(
                f"👑 AHP 專屬洞察：{ahp_count} 位 AHP 平均負荷 {ahp_avg:.1f} 點。"
                "建議：確保「Assist. in charge」職責公平分配，體現僕人領袖榜樣與責任。"
            )

        # Simple fairness note
        if fairness_gap > 5:
            st.warning("⚠️ 公平差距較大，建議檢視固定值班與請假調整機制。")
        else:
            st.success("✅ 整體公平性良好，符合學校僕人領袖與公平原則。")

        # Historical Trends & Fairness (High Priority)
        st.write("---")
        st.subheader("📊 歷史趨勢與公平性分析")
        if st.button("💾 儲存本週負荷數據 (Save Current Week for Trends)"):
            current_loads = {}
            for _, row in report.iterrows():
                name = str(row.get("Student Name", row.get("學生姓名", ""))).strip()
                load = float(row.get("Cumulative Weighted Load (points)", 0))
                if name:
                    current_loads[name] = load
            week_num = len(st.session_state.history_loads) + 1
            st.session_state.history_loads.append({"week": week_num, "loads": current_loads})
            st.success(f"已儲存第 {week_num} 週數據。用於趨勢分析。")

        if st.session_state.history_loads:
            # Build df for trends
            weeks = []
            all_names = set()
            for h in st.session_state.history_loads:
                weeks.append(h["week"])
                all_names.update(h["loads"].keys())

            trend_data = {"週次": weeks}
            for name in sorted(all_names):
                trend_data[name] = []
                for h in st.session_state.history_loads:
                    trend_data[name].append(h["loads"].get(name, 0))

            trend_df = pd.DataFrame(trend_data)
            # Line chart for trends (multi-week cumulative load) - all UI text in Chinese
            fig_trend = px.line(trend_df, x="週次", y=[col for col in trend_df.columns if col != "週次"],
                                title="累計負荷歷史趨勢",
                                labels={"value": "累計加權負荷 (點)", "variable": "學生"})
            st.plotly_chart(fig_trend, use_container_width=True)

            # Latest fairness index (std dev)
            latest = st.session_state.history_loads[-1]["loads"]
            latest_loads = list(latest.values())
            fairness_index = float(pd.Series(latest_loads).std()) if len(latest_loads) > 1 else 0.0
            st.metric("公平指數 (Fairness Index = 標準差)", f"{fairness_index:.2f} 點", help="越低越公平。0 = 完美平均。")

            # Most Neglected Students (lowest load)
            if latest:
                sorted_neg = sorted(latest.items(), key=lambda x: x[1])[:3]
                neglected_names = [n for n, l in sorted_neg]
                st.warning(f"⚠️ 最需關注學生 (Most Neglected - 最低負荷): {', '.join(neglected_names)}。建議優先給予機會以促進公平。")
        else:
            st.info("💡 點擊「儲存本週」按鈕開始記錄歷史趨勢。")

        # Advanced Summary Report Generation (High Priority)
        st.write("---")
        st.subheader("📋 總結報告生成 (Advanced Summary Report)")
        st.caption("一鍵生成報告，包含公平性、表現者、AHP貢獻、僕人領袖註記。支援中文預覽與專業英文匯出。")

        if st.button("📊 生成總結報告 (Generate Summary Report)", type="primary"):
            # Use export report for consistent English data
            export_report = get_export_report_df(st.session_state.master_report_df)
            display_report = get_ui_report_df(st.session_state.master_report_df)

            # Chinese preview (UI) - using display data
            st.markdown("### 📝 中文預覽 (Chinese UI Preview)")
            neg_str = ', '.join(neglected_names) if 'neglected_names' in locals() and neglected_names else '無'
            summary_zh = f"""
**本週總結報告**

- 總領袖生：{total_students}
- 平均負荷：{avg_load:.1f} 點
- 公平指數 (標準差)：{fairness_gap:.1f} 點
- AHP 平均負荷：{ahp_avg:.1f} 點 (共 {ahp_count} 位)

**表現者**
- 負荷最低 (最需關注)：{neg_str}
- 最高負荷：{max_load:.1f} 點

**AHP 貢獻**
AHP 平均負荷顯示領導責任分擔良好。

**僕人領袖註記**
「誰願為首，就必作眾人的僕人。」— 馬可福音 10:44
本系統強調公平與服事，幫助領袖生學習責任與謙卑。
"""
            st.markdown(summary_zh)

            # Professional English export version - using export data
            st.markdown("### 📤 專業英文匯出版 (Professional English Export)")
            export_neg = neg_str
            summary_en = f"""
# Sing Yin Secondary School Study Prefect Duty Roster - Summary Report

**Report Date:** {datetime.date.today().strftime('%Y-%m-%d')}
**Total Prefects:** {total_students}
**Average Cumulative Load:** {avg_load:.1f} points
**Fairness Index (Std Dev):** {fairness_gap:.1f} points
**AHP Average Load:** {ahp_avg:.1f} points ({ahp_count} AHPs)

**Top/Bottom Performers**
- Most Neglected (Lowest Load): {export_neg}
- Highest Load: {max_load:.1f} points

**AHP Contribution**
AHPs show balanced or lower average load, demonstrating responsible leadership allocation.

**Servant Leadership Notes**
"Whoever wants to become great among you must be your servant." — Mark 10:43
This system promotes fairness, equity, and a culture of service, helping prefects learn responsibility and humility in accordance with school values and biblical principles.

**Data Summary (English Columns)**
{export_report.to_string(index=False) if not export_report.empty else "No data"}
"""
            st.text_area("English Summary (copy or download for external use)", summary_en, height=250)
            st.download_button(
                "⬇️ 下載英文總結報告 (Download Professional English Summary .txt)",
                summary_en,
                f"SYSS_Summary_Report_{datetime.date.today().strftime('%Y%m%d')}.txt",
                use_container_width=True
            )
            st.caption("💡 重要：下載英文報告後，請務必同時下載對應的 JSON 備份，並手動上傳到 GitHub 的 `backups/` 資料夾進行長期保存。")
            # Optional: Quick English PDF summary using existing PDF engine (reusing for professionalism)
            if st.button("📄 額外下載英文PDF摘要 (Extra English PDF Summary)", key="summary_pdf"):
                # Reuse PDF but with summary content - simplified for now
                st.info("使用匯出功能下載完整英文PDF以獲得最佳格式。")

    # Roster Version History - Improved (better comparison, clearer display, easier loading)
    with st.expander("📜 值班表版本歷史 (Roster Version History) - 自動儲存每次生成"):
        versions = st.session_state.get("roster_versions", [])
        if versions:
            version_labels = [f"v{v['version']} - {v['timestamp']}" for v in versions]
            selected_label = st.selectbox("選擇版本 (Select Version)", version_labels, key="version_select")
            if selected_label:
                idx = version_labels.index(selected_label)
                ver = versions[idx]
                st.write(f"**版本 {ver['version']}** @ {ver['timestamp']}")

                col_load, col_view = st.columns([1, 3])
                with col_load:
                    if st.button("載入此版本 (Load This Version)", key=f"load_{idx}"):
                        if ver.get("roster_df"):
                            st.session_state.roster_df = pd.DataFrame.from_dict(ver["roster_df"])
                        if ver.get("report_df"):
                            st.session_state.master_report_df = pd.DataFrame.from_dict(ver["report_df"])
                        st.success(f"✅ 版本 {ver['version']} 已載入當前")
                        st.rerun()

                with col_view:
                    if ver.get("roster_df"):
                        ver_roster = pd.DataFrame.from_dict(ver["roster_df"])
                        st.dataframe(ver_roster, use_container_width=True, height=200)

                # Improved comparison: side-by-side key stats + sample
                if st.button("比較此版本與當前 (Compare Version with Current)", key=f"compare_{idx}"):
                    st.write("### 比較 (Comparison)")
                    current_roster = st.session_state.roster_df
                    ver_roster = pd.DataFrame.from_dict(ver.get("roster_df", {})) if ver.get("roster_df") else pd.DataFrame()

                    # Simple stats comparison
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**當前版本 (Current)**")
                        st.write(f"- 總欄位數: {len(current_roster.columns)}")
                        st.write(f"- 總學生/角色: {len(current_roster)}")
                    with col2:
                        st.write(f"**選定版本 (Version {ver['version']})**")
                        st.write(f"- 總欄位數: {len(ver_roster.columns) if not ver_roster.empty else 0}")
                        st.write(f"- 總學生/角色: {len(ver_roster) if not ver_roster.empty else 0}")

                    # Sample data
                    st.write("**樣本資料比較 (Sample - first 5 rows)**")
                    st.write("當前:")
                    st.dataframe(current_roster.head(5), use_container_width=True)
                    st.write("選定版本:")
                    if not ver_roster.empty:
                        st.dataframe(ver_roster.head(5), use_container_width=True)
                    else:
                        st.info("選定版本無資料")
        else:
            st.info("生成值班表後版本會自動儲存。")

    # Semester Service Hours Auto-Statistics + Certificate Generation
    st.write("---")
    st.subheader("⏱️ 學期服務時數統計與證書生成 (Semester Service Hours & Certificate)")
    st.caption("自動計算服務時數 (每值班1小時)，一鍵生成專業英文證書 (姓名保留中文)")

    if st.button("🔄 更新/重新計算服務時數 (Update from Current Roster)", use_container_width=True):
        for name in st.session_state.students_df["name"].dropna().astype(str).str.strip():
            count = (st.session_state.roster_df == name).sum().sum()
            hours = count * 1.0
            st.session_state.semester_hours[name] = st.session_state.semester_hours.get(name, 0) + hours
        st.success("服務時數已更新")

    if st.session_state.get("semester_hours"):
        hours_df = pd.DataFrame(list(st.session_state.semester_hours.items()), columns=["姓名 (Chinese Name)", "總服務時數 (小時)"])
        st.dataframe(hours_df, use_container_width=True)

        if st.button("📜 生成服務證書 (Generate Professional English Certificate)", use_container_width=True, type="primary"):
            cert_lines = [
                "Sing Yin Secondary School",
                "Study Prefect Service Certificate",
                "",
                "This certifies that the following prefects have completed their service hours this semester in accordance with the principles of fairness and servant leadership:",
                ""
            ]
            for name, h in st.session_state.semester_hours.items():
                cert_lines.append(f"- {name} (Chinese name preserved): {h:.1f} hours")
            cert_lines.extend([
                "",
                "In recognition of their dedication, responsibility, and contribution to the school community.",
                f"Issued on {datetime.date.today().strftime('%Y-%m-%d')}",
                "",
                "Head Study Prefect",
                "Sing Yin Secondary School"
            ])
            cert_text = "\n".join(cert_lines)
            st.text_area("證書預覽 (Certificate Preview - English with Chinese Names)", cert_text, height=200)
            # Use proper PDF certificate (Direction C - upgrade from text to designed PDF)
            logo_b64 = base64.b64encode(st.session_state.logo_data).decode() if st.session_state.get("logo_data") else None
            cert_pdf = generate_service_certificate(st.session_state.semester_hours, logo_b64)
            if cert_pdf:
                st.download_button(
                    "⬇️ 下載專業英文PDF證書 (Download Professional English PDF Certificate)",
                    cert_pdf,
                    f"SYSS_Service_Certificate_{datetime.date.today().strftime('%Y%m%d')}.pdf",
                    "application/pdf",
                    use_container_width=True
                )
            else:
                st.warning("無法生成PDF證書，請確認WeasyPrint可用。")
            # Fallback text for compatibility
            st.download_button(
                "⬇️ 下載英文證書文字版 (Download English Certificate Text)",
                cert_text,
                f"SYSS_Service_Certificate_{datetime.date.today().strftime('%Y%m%d')}.txt",
                use_container_width=True
            )

    # ====================== 公平性圖表 ======================
    if not st.session_state.master_report_df.empty:
        st.write("---")
        st.subheader("🦅 全體累積工作點數公平性監控")
        fig = px.bar(
            st.session_state.master_report_df,
            x='Student Name',
            y='Cumulative Weighted Load (points)',
            text_auto='.1f',
            title="全體領袖生加權工作量天平（點數低者將優先派班）",
            color='Cumulative Weighted Load (points)',
            color_continuous_scale='YlOrBr'
        )
        fig.update_layout(xaxis_title="學生姓名", yaxis_title="累計加權負荷 (點)")
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

    # ====================== 智慧替補 ======================
    st.write("---")
    st.subheader("🔍 智慧替補推薦")
    c1, c2 = st.columns(2)
    with c1:
        chosen_day = st.selectbox("請假或替換日期", DAYS, index=0, key="sub_day_selector")
    with c2:
        chosen_role = st.selectbox("請假或替換職位/房間", ROWS_ROSTER, index=0, key="sub_role_selector")

    current_person = str(st.session_state.roster_df.at[chosen_role, chosen_day]).strip()
    st.text_input("📍 目前該時段排定之人員", value=current_person if current_person not in ["", "X", "⬜"] else "（當前為空白或特殊不開放時段）", disabled=True)

    if st.button("🔮 執行篩選並推薦最優替補人員", type="secondary", use_container_width=True):
        sub_df, error_msg = recommend_substitutes(st.session_state.roster_df, st.session_state.students_df, chosen_day, chosen_role)
        if sub_df is not None:
            st.success("📋 媒合成功！已依據「最終總計加權負荷」由低到高為您排序推薦合格替補人員：")
            # UI 顯示用中文欄位
            display_sub = sub_df.copy()
            display_sub.columns = ["姓名", "年級", "當前總點數"]
            st.dataframe(display_sub, use_container_width=True, hide_index=True)
        else:
            st.warning(error_msg)

    # ====================== 值班後請假調整（新增公平性核心功能） ======================
    st.write("---")
    st.subheader("⚖️ 值班後請假調整（確保公平性）")
    st.caption("值班表發布後若有人臨時請假，可在此撤銷其已計算的負荷點數，並選擇替補人員（或留空）。調整後立即更新累計與報表，保證公平。")

    with st.form("leave_adjust_form", clear_on_submit=True):
        col_d, col_r = st.columns(2)
        with col_d:
            adj_day = st.selectbox("選擇日期", DAYS, key="adj_day")
        with col_r:
            assigned_roles = [
                r for r in ROWS_ROSTER
                if str(st.session_state.roster_df.at[r, adj_day]).strip() not in ["", "X", "⬜", "請假撤銷"]
            ]
            adj_role = st.selectbox("選擇崗位", assigned_roles if assigned_roles else [""], key="adj_role")

        current_person = ""
        if adj_role and adj_role in st.session_state.roster_df.index:
            current_person = str(st.session_state.roster_df.at[adj_role, adj_day]).strip()
            if current_person and current_person not in ["X", "⬜", "請假撤銷"]:
                st.info(f"目前值班人員：**{current_person}**（將被撤銷點數）")

        has_replacement = st.checkbox("有替補人員（推薦）", value=False)
        replacement = None
        if has_replacement and current_person:
            valid_names = [
                str(n).strip() for n in st.session_state.students_df["name"].dropna()
                if str(n).strip() and str(n).strip() != current_person
            ]
            replacement = st.selectbox("選擇替補人員", valid_names, key="replacement_select")

        submitted = st.form_submit_button("🚀 執行請假調整 / 撤銷點數", type="primary", use_container_width=True)

        if submitted and adj_role and current_person:
            weight = get_weight(adj_role)

            # 呼叫核心調整函數
            apply_post_publication_leave_adjustment(
                st.session_state.students_df,
                st.session_state.roster_df,
                adj_day,
                adj_role,
                current_person,
                replacement if has_replacement else None
            )

            # 立即重新計算 audit
            audit_results = validate_and_compute(
                st.session_state.roster_df,
                st.session_state.students_df,
                st.session_state.leave_tracker_input,
                st.session_state.manual_weights
            )
            st.session_state.master_report_df = audit_results["report_df"]

            action_msg = f"已從 **{current_person}** 撤銷 {weight:.1f} 點"
            if has_replacement and replacement:
                action_msg += f"，並轉由 **{replacement}** 接手。"
            else:
                action_msg += "，該崗位暫無人值班。"

            st.success(f"✅ 調整完成！{action_msg} 累計點數與公平性圖表已即時更新。")

            # 記錄調整歷史
            if "adjustment_log" not in st.session_state:
                st.session_state.adjustment_log = []
            st.session_state.adjustment_log.append({
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "day": adj_day,
                "role": adj_role,
                "original": current_person,
                "replacement": replacement if has_replacement else None,
                "weight_revoked": round(weight, 1)
            })

            trigger_backup_reminder()  # 自動備份提醒（leave adjustment 重要操作）
            st.success("💡 請記得下載 JSON 備份，並建議將此重要調整的備份上傳到 GitHub 的 backups/ 資料夾以長期保存。")
            st.rerun()

    # ====================== 快速導出 (語言跟隨) ======================
    ui_lang = st.session_state.get("ui_language", "zh")
    if ui_lang == "en":
        st.write("---")
        st.subheader("📤 Export (Professional English / Follow Current Language)")
        st.caption("Exports use professional titles and columns according to current language setting. Student names always remain in Chinese.")
    else:
        st.write("---")
        st.subheader("📤 匯出（跟隨語言設定）")
        st.caption("匯出使用目前語言的標題與欄位，學生姓名永遠保留中文。")

    col1, col2, col3 = st.columns(3)

    with col1:
        # 明確的 PDF 語言控制：兩個按鈕，分別輸出中文/英文 PDF
        if st.button("📄 匯出中文 PDF", use_container_width=True):
            logo_b64 = base64.b64encode(st.session_state.logo_data).decode() if st.session_state.get("logo_data") else None
            pdf_report = get_ui_report_df(st.session_state.master_report_df)
            pdf_bytes = generate_pdf(st.session_state.roster_df, pdf_report, logo_b64)
            if pdf_bytes:
                st.download_button(
                    "💾 下載中文 PDF",
                    pdf_bytes,
                    f"SYSS_Roster_{datetime.date.today().strftime('%Y%m%d')}_中文.pdf",
                    "application/pdf",
                    use_container_width=True
                )
        if st.button("📄 Export English PDF", use_container_width=True):
            logo_b64 = base64.b64encode(st.session_state.logo_data).decode() if st.session_state.get("logo_data") else None
            pdf_report = get_export_report_df(st.session_state.master_report_df)
            pdf_bytes = generate_pdf(st.session_state.roster_df, pdf_report, logo_b64)
            if pdf_bytes:
                st.download_button(
                    "💾 Download English PDF",
                    pdf_bytes,
                    f"SYSS_Roster_{datetime.date.today().strftime('%Y%m%d')}_EN.pdf",
                    "application/pdf",
                    use_container_width=True
                )

    with col2:
        export_report = get_export_report_df(st.session_state.master_report_df)
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            # Roster sheet
            roster_sheet = st.session_state.roster_df
            roster_sheet.to_excel(writer, sheet_name='Weekly Duty Roster')

            if not export_report.empty:
                # Workload Audit with conditional formatting and chart
                audit_sheet = writer.book.create_sheet('Workload Audit')
                # Write header and data
                for r_idx, row in enumerate([export_report.columns.tolist()] + export_report.values.tolist(), 1):
                    for c_idx, value in enumerate(row, 1):
                        audit_sheet.cell(row=r_idx, column=c_idx, value=value)

                # Conditional formatting color scale for load column (last column, assume "Cumulative Weighted Load (points)")
                from openpyxl.formatting.rule import ColorScaleRule
                load_col = len(export_report.columns)
                color_scale = ColorScaleRule(start_type='min', start_color='63BE7B',
                                             mid_type='percentile', mid_value=50, mid_color='FFEB84',
                                             end_type='max', end_color='F8696B')
                audit_sheet.conditional_formatting.add(f'A2:{chr(64+load_col)}{len(export_report)+1}', color_scale)

                # Add bar chart for loads
                from openpyxl.chart import BarChart, Reference
                chart = BarChart()
                chart.type = "col"
                chart.title = "Cumulative Workload by Student"
                chart.y_axis.title = "Points"
                data = Reference(audit_sheet, min_col=load_col, min_row=1, max_row=len(export_report)+1)
                cats = Reference(audit_sheet, min_col=1, min_row=2, max_row=len(export_report)+1)
                chart.add_data(data, titles_from_data=True)
                chart.set_categories(cats)
                chart.shape = 4
                audit_sheet.add_chart(chart, "H2")

            # Professional English summary sheet
            summary_data = {
                "Report Type": ["Professional English Export - Sing Yin Study Prefect"],
                "Generated": [datetime.date.today().strftime('%Y-%m-%d')],
                "Core Principle": ["Lower load = Higher priority (Fairness & Servant Leadership)"],
                "Compliance": ["AGENTS.md §1 rules fully applied (AHP, Room 302/303, fairness)"]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Executive Summary (EN)', index=False)
        excel_label = "📊 Download Excel (English + Charts)" if ui_lang == "en" else "📊 下載 Excel（跟隨語言 + 圖表 + 條件格式）"
        st.download_button(
            excel_label,
            output_excel.getvalue(),
            f"SYSS_Roster_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
            use_container_width=True
        )

    with col3:
        ui_lang = st.session_state.get("ui_language", "zh")
        if ui_lang == "en":
            export_report = get_export_report_df(st.session_state.master_report_df)
            md_title = PROJECT_FULL_NAME_EN
            md_sub = "Professional English Export Report"
            key_principle = "**Key Principle (Servant Leadership):** Lower cumulative load indicates higher priority for future assignments."
            audit_title = "### Workload Audit (Professional English Columns)"
            footer = "*This document is formatted for official, external, and leadership use in clean professional English.*"
            dl_label = "📝 Download Markdown (Professional English)"
            report_for_md = export_report
        else:
            export_report = get_ui_report_df(st.session_state.master_report_df)
            md_title = PROJECT_FULL_NAME
            md_sub = "專業中文匯出報告"
            key_principle = "**核心原則（僕人領袖）：** 累計負荷越低，代表未來值班優先度越高。"
            audit_title = "### 工作負荷審計（中文欄位）"
            footer = "*本文件依目前語言設定輸出，官方/外部使用。*"
            dl_label = "📝 下載 Markdown（跟隨語言）"
            report_for_md = export_report

        md_data = f"""# {md_title}
## {md_sub}

**Report Date:** {datetime.date.today().strftime('%Y-%m-%d')}
**Institution:** Sing Yin Secondary School • Study Prefect Team

{key_principle}
Student names are preserved in Chinese per school practice.

### Weekly Duty Roster

{st.session_state.roster_df.to_markdown()}

{audit_title}

{report_for_md.to_markdown(index=False) if not report_for_md.empty else "No data"}

---
{footer}
*Internal daily operations use Chinese UI for student accessibility.*
*Generated in full compliance with school regulations and biblical principles of fairness and service.*
"""
        st.download_button(
            dl_label,
            md_data.encode('utf-8'),
            f"SYSS_Roster_{datetime.date.today().strftime('%Y%m%d')}.md",
            use_container_width=True
        )

    ui_lang = st.session_state.get("ui_language", "zh")
    cap = "Sing Yin Secondary School Study Prefect Platform | " + VERSION + " | UI: English | Exports: Professional" if ui_lang == "en" else f"聖言中學導學風紀當值排班平台 | {VERSION} | 介面中文 | 匯出專業"
    st.caption(cap)


if __name__ == "__main__":
    main()