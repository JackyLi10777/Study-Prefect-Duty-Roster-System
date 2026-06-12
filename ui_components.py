# ui_components.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
UI 元件模組 - 側邊欄、神聖每日聖經金句、控制按鈕（人性化重新設計版）

作者：Head Study Prefect 26-27 LI Chuangjie Jacky
版本：v2.3 Final（人性化優化版 - 降低認知負荷、強化公平感與信任、專業視覺層級）
"""

import streamlit as st
import pandas as pd
import datetime
import io
import random

# ====================== 模組導入 ======================
from config import (
    DAYS, ROWS_ROSTER, DAILY_VERSES, VERSION, PROJECT_FULL_NAME,
    NASA_COLORS, get_role_style
)
from core import generate_roster
from utils import (
    process_roster_import, smart_process_roster_import,
    export_system_backup, import_system_backup
)
from data import get_demo_dataframe, get_sample_format_dataframe
from ai_parser import ai_parse_remarks

# ====================== 合併所有金句供隨機刷新使用 ======================
ALL_VERSES = []
for day_list in DAILY_VERSES.values():
    ALL_VERSES.extend(day_list)


def show_daily_verse():
    """神聖莊重每日聖經金句區塊（深色漸層 + 金色文字 + 更大間距 + 心理慰藉感）"""
    if "current_verse" not in st.session_state or st.session_state.current_verse is None:
        st.session_state.current_verse = random.choice(ALL_VERSES)

    st.markdown(f"""
    <div style="background: linear-gradient(180deg, #1A1A2E 0%, #0B1E3D 100%); 
                padding: 32px 28px; 
                border-radius: 20px; 
                margin: 24px 0 36px 0; 
                text-align: center; 
                border: 2px solid #D4AF37; 
                box-shadow: 0 10px 40px rgba(212, 175, 55, 0.25);">
        <h3 style="margin: 0 0 16px 0; color: #D4AF37; font-size: 24px; letter-spacing: 2px; font-weight: 700;">
            📖 今日聖經金句
        </h3>
        <p style="font-size: 18px; margin: 0; color: #F5E8C7; line-height: 1.75; font-weight: 500;">
            {st.session_state.current_verse}
        </p>
        <div style="margin-top: 18px; font-size: 13px; color: #A8A8A8;">
            —— 聖言中學導學風紀團隊靈修提醒
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🔄 刷新金句", use_container_width=True, type="secondary", help="獲得新的靈修鼓勵"):
        st.session_state.current_verse = random.choice(ALL_VERSES)
        st.rerun()


def render_sidebar():
    """側邊欄 - 極簡專業、清晰流程、即時統計與信任感設計"""
    with st.sidebar:
        st.header("🏫 Sing Yin Secondary School")
        st.caption("導學風紀當值排班平台")

        # ==================== 校徽（心理信任錨點） ====================
        show_logo = st.checkbox("🖼️ 顯示校徽（畫面與 PDF）", value=True, key="show_logo_toggle")

        uploaded_logo = st.file_uploader("上傳自訂校徽 (PNG)", type=["png"], key="logo_uploader")
        if uploaded_logo:
            st.session_state.logo_data = uploaded_logo.getvalue()
            st.success("✅ 校徽已更新")
        elif show_logo and "logo_data" not in st.session_state:
            try:
                with open("logo.png", "rb") as f:
                    st.session_state.logo_data = f.read()
            except FileNotFoundError:
                pass

        st.divider()

        # ==================== 即時統計（公平感與成就感） ====================
        st.subheader("📊 即時累計統計")
        if not st.session_state.students_df.empty:
            total = len(st.session_state.students_df)
            total_points = st.session_state.students_df["history_weight"].sum()
            avg = round(total_points / total, 1) if total > 0 else 0.0
            st.metric("總領袖生", f"{total} 人", delta=None)
            st.metric("累計總點數", f"{total_points:.1f}")
            st.metric("平均負荷", f"{avg:.1f} 點")
        else:
            st.info("📌 請先載入名冊開始管理")

        st.divider()

        # ==================== 名冊管理（清晰 CTA） ====================
        st.subheader("🗄️ 名冊管理")
        col_demo, col_sample = st.columns(2)
        with col_demo:
            if st.button("💡 一鍵載入官方示範名冊", use_container_width=True):
                st.session_state.students_df = get_demo_dataframe()
                st.success("✅ 示範名冊載入完成")
                st.rerun()
        with col_sample:
            if st.button("📥 下載格式範例", use_container_width=True):
                sample_df = get_sample_format_dataframe()
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    sample_df.to_excel(writer, index=False)
                st.download_button("✅ 下載", output.getvalue(), "Prefect_名冊格式範例.xlsx", use_container_width=True)

        uploaded_roster = st.file_uploader("上傳名冊 (Excel/CSV)", type=["csv", "xlsx", "xls"], key="roster_importer")
        col_trad, col_ai = st.columns(2)
        with col_trad:
            if uploaded_roster and st.button("📋 傳統導入", use_container_width=True):
                process_roster_import(uploaded_roster)
        with col_ai:
            if uploaded_roster and st.button("🤖 AI 智能匹配", type="primary", use_container_width=True):
                smart_process_roster_import(uploaded_roster)

        st.caption("💡 AI 支援任意欄位順序，節省您的時間")

        st.divider()

        # ==================== 名冊即時修改 ====================
        st.subheader("👥 名冊即時修改")
        st.caption("修改後自動儲存")
        st.session_state.students_df = st.data_editor(
            st.session_state.students_df,
            column_config={
                "name": st.column_config.TextColumn("姓名 *", required=True),
                "form": st.column_config.SelectboxColumn("年級", options=["F.3", "F.4", "F.5", "F.6"]),
                "role": st.column_config.SelectboxColumn("職級", options=["Study Prefect", "Assistant Head Study Prefect"]),
                "fixed_general_duty": st.column_config.SelectboxColumn("固定值班", options=["NONE", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]),
                "available": st.column_config.TextColumn("可用日子"),
                "history_duties": st.column_config.NumberColumn("歷史次數", min_value=0),
                "history_weight": st.column_config.NumberColumn("歷史點數", min_value=0.0),
                "remarks": st.column_config.TextColumn("備註")
            },
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="student_editor_widget"
        )

        st.divider()

        # ==================== AI 解析 ====================
        st.subheader("🤖 AI 智能解析")
        if st.button("🚀 執行 AI 解析 Remarks", use_container_width=True, type="secondary"):
            with st.spinner("AI 正在智能分析..."):
                updated_df = ai_parse_remarks(st.session_state.students_df)
                st.session_state.students_df = updated_df
                st.success("✅ AI 已自動更新固定值班、可值班日與職級")
                st.rerun()

        st.divider()

        # ==================== 請假登記 ====================
        st.subheader("🛑 請假登記")
        valid_names = [str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip()]
        st.session_state.leave_tracker_input = st.multiselect(
            "今日請假人員（可多選）",
            options=valid_names,
            default=st.session_state.get("leave_tracker_input", [])
        )

        st.divider()

        # ==================== Cloud 備份 ====================
        st.subheader("💾 Cloud 備份")
        st.caption("防止休眠資料遺失")
        if st.button("⬇️ 導出完整備份", use_container_width=True):
            backup_json = export_system_backup(st.session_state.get("master_report_df", pd.DataFrame()))
            st.download_button("✅ 下載 JSON", backup_json, f"SYSS_Backup_{datetime.date.today().strftime('%Y%m%d')}.json", use_container_width=True)

        uploaded_backup = st.file_uploader("還原備份 JSON", type=["json"], key="backup_importer")
        if uploaded_backup and st.button("🔄 還原備份", use_container_width=True):
            import_system_backup(uploaded_backup)


def render_control_buttons():
    """主畫面控制按鈕 - 清晰、突出主要行動"""
    closure_options = [f"{d} - {room}" for d in DAYS for room in ["Room302", "Room303", "Room202"]
                       if not (room == "Room202" and d in ["TUESDAY", "FRIDAY"])]
    selected_closures = st.multiselect("🛠️ 本週特殊不開放時段", options=closure_options, key="special_closures")

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🚀 智能計算：生成本週全新公平值班表", type="primary", use_container_width=True):
            with st.spinner("正在進行公平排班計算..."):
                seed = random.randint(10000, 99999)
                global_multiplier = st.session_state.get("global_load_multiplier", 1.0)
                st.session_state.roster_df = generate_roster(
                    st.session_state.students_df,
                    st.session_state.leave_tracker_input,
                    selected_closures,
                    seed,
                    global_load_multiplier=global_multiplier
                )
                st.success(f"✅ 排班完成！（全局負荷倍率：{global_multiplier:.1f}）")

    with col2:
        if st.button("🗑️ 清空", type="secondary", use_container_width=True):
            st.session_state.show_clear_confirm = True

    if st.session_state.get("show_clear_confirm", False):
        st.error("⚠️ 確定要清除全部排班？此操作無法復原！")
        c1, c2 = st.columns(2)
        if c1.button("💥 確定清空"):
            st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
            st.session_state.show_clear_confirm = False
            st.rerun()
        if c2.button("❌ 取消"):
            st.session_state.show_clear_confirm = False
            st.rerun()

    return selected_closures


print("✅ ui_components.py 已載入完成 - 人性化重新設計前端（心理學優化版）")