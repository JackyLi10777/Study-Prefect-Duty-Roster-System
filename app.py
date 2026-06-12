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

# ====================== 模組導入 ======================
from config import (
    DAYS, ROWS_ROSTER, VERSION, APP_TITLE, PROJECT_FULL_NAME,
    NASA_COLORS, get_role_style, DEFAULT_GLOBAL_LOAD_MULTIPLIER, get_weight
)
from data import (
    get_demo_dataframe, get_sample_format_dataframe,
    initialize_session_state
)
from ai_parser import ai_parse_remarks
from core import (
    generate_roster, validate_and_compute, recommend_substitutes,
    apply_post_publication_leave_adjustment
)
from utils import (
    generate_pdf, export_system_backup, import_system_backup,
    process_roster_import, smart_process_roster_import
)
from ui_components import (
    render_sidebar, show_daily_verse, render_control_buttons
)

# ====================== 使用說明書 ======================
HELP_TEXT = """
### 📖 Sing Yin Study Prefect Duty Roster System 使用說明書（v2.3 Final）

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
    st.subheader("🌍 全局負荷調節滑桿")
    st.caption("臨近考試時可提高本次排班整體負荷倍率，讓累計較低同學優先平衡")
    multiplier = st.slider(
        "本次排班整體負荷倍率",
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

    # ====================== 自訂 CSS ======================
    st.markdown("""
    <style>
        .main-title { color: #0B1E3D; font-size: 38px; font-weight: 700; letter-spacing: 2px; margin-bottom: 4px; }
        .main-subtitle { color: #D4AF37; font-size: 17px; font-weight: 600; margin-bottom: 25px; }
        .stDataFrame, [data-testid="stDataEditor"] { border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.06); }
        .stButton > button { height: 3.4rem; font-weight: 600; border-radius: 10px; transition: all 0.3s; }
        .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,0.12); }
        .danger-alert { background-color: #FEF2F2; border-left: 5px solid #EF4444; color: #991B1B; padding: 16px; border-radius: 10px; margin: 12px 0; }
        .warning-alert { background-color: #FFFBEB; border-left: 5px solid #F59E0B; color: #92400E; padding: 16px; border-radius: 10px; margin: 12px 0; }
        footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

    # ====================== 主畫面 ======================
    render_sidebar()

    st.markdown(f'<p class="main-title">{PROJECT_FULL_NAME}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="main-subtitle">F.3–F.6 Study Prefect Duty Platform | {VERSION}</p>', unsafe_allow_html=True)

    show_daily_verse()

    with st.expander("📖 點此展開完整使用說明書（v2.3 Final）", expanded=False):
        st.markdown(HELP_TEXT)

    st.write("---")

    # ====================== 全局負荷滑桿 ======================
    global_multiplier_slider()

    st.write("---")
    selected_closures = render_control_buttons()

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
        if st.button("🩹 一鍵清除請假同學", type="primary", use_container_width=True):
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
    st.subheader("📅 本週值班表")
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
        styled = st.session_state.roster_df.style.apply(
            lambda row: [apply_cell_style(val, row.name, col) for col, val in row.items()], axis=1
        )
        st.dataframe(styled, use_container_width=True, height=380)

    with tab_edit:
        st.markdown("<p style='font-size:13px; color:#666;'>💡 直接修改人名或打 X 鎖定</p>", unsafe_allow_html=True)
        edited_roster = st.data_editor(
            st.session_state.roster_df,
            use_container_width=True,
            key="main_roster_editor_widget"
        )
        if not edited_roster.equals(st.session_state.roster_df):
            st.session_state.roster_df = edited_roster
            st.rerun()

    # ====================== 手動調整負荷 ======================
    st.write("---")
    st.subheader("🔧 手動調整本次值班負荷指數")
    st.caption("針對每個崗位本次值班，手動修改累計負荷點數（已受全局滑桿影響）")

    manual_col = st.data_editor(
        st.session_state.manual_weights,
        use_container_width=True,
        key="manual_weight_editor"
    )
    if not manual_col.equals(st.session_state.manual_weights):
        st.session_state.manual_weights = manual_col.astype(float).fillna(0.0)
        st.rerun()

    # ====================== 累計審計表 ======================
    st.write("---")
    st.subheader("📊 累計動態工作負荷審計表")
    if not st.session_state.master_report_df.empty:
        st.dataframe(st.session_state.master_report_df, use_container_width=True, hide_index=True)
    else:
        st.info("請先生成排班表以顯示審計表")

    # ====================== 公平性圖表 ======================
    if not st.session_state.master_report_df.empty:
        st.write("---")
        st.subheader("🦅 全體累積工作點數公平性監控")
        fig = px.bar(
            st.session_state.master_report_df,
            x='學生姓名 (Prefect Name)',
            y='最終總計加權負荷 (點)',
            text_auto='.1f',
            title="全體領袖生加權工作量天平（點數低者將優先派班）",
            color='最終總計加權負荷 (點)',
            color_continuous_scale='YlOrBr'
        )
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
            st.dataframe(sub_df, use_container_width=True, hide_index=True)
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

            st.rerun()

    # ====================== 快速導出 ======================
    st.write("---")
    st.subheader("📤 快速導出")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📄 匯出 PDF", use_container_width=True):
            logo_b64 = base64.b64encode(st.session_state.logo_data).decode() if st.session_state.get("logo_data") else None
            pdf_bytes = generate_pdf(st.session_state.roster_df, st.session_state.master_report_df, logo_b64)
            if pdf_bytes:
                st.download_button(
                    "💾 下載 PDF",
                    pdf_bytes,
                    f"SYSS_Roster_{datetime.date.today().strftime('%Y%m%d')}.pdf",
                    "application/pdf",
                    use_container_width=True
                )

    with col2:
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            st.session_state.roster_df.to_excel(writer, sheet_name='本週值班表')
            if not st.session_state.master_report_df.empty:
                st.session_state.master_report_df.to_excel(writer, sheet_name='工作負荷統計', index=False)
        st.download_button(
            "📊 下載 Excel",
            output_excel.getvalue(),
            f"SYSS_Roster_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
            use_container_width=True
        )

    with col3:
        md_data = "### 本週值班表\n\n" + st.session_state.roster_df.to_markdown() + "\n\n### 工作負荷統計\n\n" + (st.session_state.master_report_df.to_markdown(index=False) if not st.session_state.master_report_df.empty else "")
        st.download_button(
            "📝 下載 Markdown",
            md_data.encode('utf-8'),
            f"SYSS_Roster_{datetime.date.today().strftime('%Y%m%d')}.md",
            use_container_width=True
        )

    st.caption(f"Sing Yin Secondary School Study Prefect Platform | {VERSION}")


if __name__ == "__main__":
    main()