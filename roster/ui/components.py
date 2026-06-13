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
import textwrap

# ====================== 模組導入 ======================
from roster.config import (
    DAYS, get_roster_rows, VERSION, PROJECT_FULL_NAME,
    NASA_COLORS, get_role_style
)
from roster.data import get_demo_dataframe, get_sample_format_dataframe, DAILY_VERSES
from roster.core import generate_roster
from roster.utils import (
    process_roster_import, smart_process_roster_import,
    export_system_backup, import_system_backup,
    trigger_backup_reminder, clear_backup_reminder, get_backup_history
)
from roster.ai import ai_parse_remarks  # use package path (root ai_parser shim still works for legacy)

# ====================== 合併所有金句供隨機刷新使用 ======================
# 使用新 daily_verses.py 的結構 (verse_001 等 key)
ALL_VERSES = list(DAILY_VERSES.keys())

# Note: UI layer calls into business logic (generate_roster) per AGENTS.md guidelines.
# Direct calls are kept for now to preserve exact original behavior during migration.

def _t(zh_text, en_text):
    """Simple translator based on ui_language. UI follows language, student names always Chinese."""
    lang = st.session_state.get("ui_language", "zh")
    return en_text if lang == "en" else zh_text


def show_daily_verse():
    """
    神聖莊重每日聖經金句區塊。
    - 使用原生 Streamlit 元件 + CSS class 包裝，避免 raw HTML 標籤顯示。
    - 文字內容乾淨渲染。
    - 經文章節 + 經文內容清楚換行顯示。
    - 簡短靈修反思放在清晰的背景框內（.reflection-box）。
    - 深色模式有良好對比度（CSS 已強化）。
    - 完全支援語言切換（中文界面優先中文經文+反思，英文界面優先英文經文+反思）。
    """
    if ("current_verse" not in st.session_state or 
        st.session_state.current_verse is None or
        not isinstance(st.session_state.current_verse, str) or
        st.session_state.current_verse not in DAILY_VERSES):
        st.session_state.current_verse = random.choice(ALL_VERSES)

    verse_key = st.session_state.current_verse
    verse = DAILY_VERSES.get(verse_key, {})
    show_reflection = st.session_state.get("verse_bilingual", False)
    lang = st.session_state.get("ui_language", "zh")

    if lang == "en":
        ref = verse.get('reference_en', '')
        text = verse.get('en', '')
        refl_title = "English Reflection"
        refl = verse.get('reflection_en', '')
        footer = "— Sing Yin Study Prefect Team Spiritual Reminder | Servant Leadership, Service First"
    else:
        ref = verse.get('reference_zh', '')
        text = verse.get('zh', '')
        refl_title = "靈修反思"
        refl = verse.get('reflection_zh', '')
        footer = "—— 聖言中學導學風紀團隊靈修提醒 | 僕人領袖，以服事為本"

    # 使用 verse-card 包裝整個金句區塊
    st.markdown('<div class="verse-card">', unsafe_allow_html=True)

    # 標題
    st.markdown(f"**📖 {_t('今日聖經金句', 'Daily Bible Verse')}**")

    # 經文章節
    if ref:
        st.markdown(f"**{ref}**")

    # 經文內容（支援長文自然換行）
    if text:
        st.markdown(text)

    # 靈修反思放在清晰框內
    if show_reflection and refl:
        st.markdown(f'<div class="reflection-box"><strong>{refl_title}</strong><br>{refl}</div>', unsafe_allow_html=True)

    st.caption(footer)

    st.markdown('</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])
    with col1:
        if st.button(_t("🔄 刷新金句", "🔄 Refresh Verse"), use_container_width=True, type="secondary", help=_t("獲得新的靈修鼓勵", "Get new spiritual encouragement")):
            st.session_state.current_verse = random.choice(ALL_VERSES)
            st.rerun()
    with col2:
        st.session_state.verse_bilingual = st.checkbox(
            _t("顯示靈修反思", "Show Devotional Reflection"), 
            value=st.session_state.get("verse_bilingual", False), 
            key="verse_bilingual_toggle",
            help=_t("顯示簡短靈修反思", "Show short devotional reflection")
        )


def render_sidebar():
    """側邊欄 - 極簡專業、清晰流程、即時統計與信任感設計"""
    with st.sidebar:
        st.header(_t("🏫 Sing Yin Secondary School", "🏫 Sing Yin Secondary School"))
        st.caption(_t("導學風紀當值排班平台", "Study Prefect Duty Roster Platform"))

        # Light / Dark Mode and Language (per requirements)
        col_theme, col_lang = st.columns(2)
        with col_theme:
            is_dark = st.toggle("🌙 深色模式", value=st.session_state.get("theme", "light") == "dark", key="theme_toggle")
            st.session_state.theme = "dark" if is_dark else "light"
        with col_lang:
            # 更完整的語言模式：中文介面 / 英文介面
            # UI 主要保持中文（學校情境），匯出與部分標題可同步英文
            lang_options = [_t("中文介面", "中文介面 / Chinese Interface"), _t("英文介面", "英文介面 / English Interface")]
            current = st.session_state.get("ui_language", "zh")
            default_idx = 0 if current == "zh" else 1
            selected_lang = st.selectbox(
                "中文 / English", 
                lang_options, 
                index=default_idx, 
                key="lang_select"
            )
            st.session_state.ui_language = "zh" if selected_lang == "中文介面" else "en"
            if st.session_state.ui_language == "en":
                st.caption(_t("英文介面 + 專業英文匯出", "English Interface + Professional English Exports"))
            else:
                st.caption(_t("中文介面（匯出支援英文）", "Chinese Interface (Exports support English)"))

        # Apply theme CSS (graphic-design + streamlit-best-practices) - improved for full coverage and smoothness
        # Enhanced to make sidebar + main area fully consistent for Light/Dark
        if st.session_state.theme == "dark":
            st.markdown("""
            <style>
            .stApp { background-color: #0e1117; color: #fafafa; }
            .stSidebar { background-color: #161b22 !important; }
            .stButton > button { background-color: #262730; color: #fafafa; border: 1px solid #4b5563; }
            .stButton > button:hover { background-color: #374151; }
            .kpi-card { background-color: #1f2937 !important; border-left-color: #D4AF37 !important; color: #fafafa; }
            .verse-card { 
                background: linear-gradient(180deg, #1a1f2e 0%, #0e1117 100%) !important; 
                border: 1px solid #4b5563; padding: 12px; border-radius: 8px; 
                color: #ffeb3b !important;  /* 高對比亮黃 */
            }
            .verse-card * { color: #ffeb3b !important; }  /* 強制所有子元素高對比 */
            .verse-card p, .verse-card .stMarkdown { color: #ffffff !important; font-weight: 500; } /* 內文用亮白 */
            .reflection-box {
                background-color: #1f2937;
                border-left: 4px solid #D4AF37;
                padding: 8px 12px;
                margin-top: 8px;
                border-radius: 4px;
                font-size: 12px;
                color: #ffeb3b !important;
            }
            .stDataFrame, [data-testid="stDataEditor"] { background-color: #1f2937; color: #fafafa; }
            .stAlert { background-color: #1f2937; color: #fafafa; }
            .stTextInput > div > div > input, .stSelectbox > div > div { background-color: #262730; color: #fafafa; }
            </style>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <style>
            .stApp { background-color: #ffffff; color: #1a1a2e; }
            .stSidebar { background-color: #f8f9fa !important; }
            .stButton > button { background-color: #f0f0f0; color: #1a1a2e; }
            .kpi-card { background-color: #f8f9fa !important; border-left-color: #0B1E3D !important; }
            .verse-card { 
                background: linear-gradient(180deg, #1A1A2E 0%, #0B1E3D 100%) !important; 
                border: 1px solid #D4AF37; padding: 12px; border-radius: 8px; 
            }
            .verse-card * { color: #F5E8C7 !important; }
            .reflection-box {
                background-color: #f0f4f8;
                border-left: 4px solid #0B1E3D;
                padding: 8px 12px;
                margin-top: 8px;
                border-radius: 4px;
                font-size: 12px;
                color: #1a1a2e !important;
            }
            .stTextInput > div > div > input, .stSelectbox > div > div { background-color: #ffffff; color: #1a1a2e; }
            </style>
            """, unsafe_allow_html=True)

        # ==================== 校徽（心理信任錨點） ====================
        show_logo = st.checkbox(_t("🖼️ 顯示校徽（畫面與 PDF）", "🖼️ Show School Badge (UI & PDF)"), value=True, key="show_logo_toggle")

        uploaded_logo = st.file_uploader(_t("上傳自訂校徽 (PNG)", "Upload Custom Badge (PNG)"), type=["png"], key="logo_uploader")
        if uploaded_logo:
            st.session_state.logo_data = uploaded_logo.getvalue()
            st.success(_t("✅ 校徽已更新", "✅ Badge updated"))
        elif show_logo and "logo_data" not in st.session_state:
            try:
                with open("logo.png", "rb") as f:
                    st.session_state.logo_data = f.read()
            except FileNotFoundError:
                pass

        st.divider()

        # ==================== 即時統計（公平感與成就感） ====================
        st.subheader(_t("📊 即時累計統計", "📊 Live Statistics"))
        if not st.session_state.students_df.empty:
            total = len(st.session_state.students_df)
            total_points = st.session_state.students_df["history_weight"].sum()
            avg = round(total_points / total, 1) if total > 0 else 0.0
            st.metric(_t("總領袖生", "Total Prefects"), f"{total} {_t('人', 'people')}", delta=None)
            st.metric(_t("累計總點數", "Total Points"), f"{total_points:.1f}")
            st.metric(_t("平均負荷", "Average Load"), f"{avg:.1f} {_t('點', 'pts')}")
        else:
            st.info(_t("📌 請先載入名冊開始管理", "📌 Please load roster first to start management"))

        st.divider()

        # ==================== 名冊管理（清晰 CTA） ====================
        st.subheader(_t("🗄️ 名冊管理", "🗄️ Roster Management"))
        col_demo, col_sample = st.columns(2)
        with col_demo:
            if st.button(_t("💡 一鍵載入官方示範名冊", "💡 One-Click Load Official Demo Roster")):
                st.session_state.students_df = get_demo_dataframe()
                st.success(_t("✅ 示範名冊載入完成", "✅ Demo roster loaded successfully"))
                st.rerun()
        with col_sample:
            if st.button(_t("📥 下載格式範例", "📥 Download Format Example")):
                sample_df = get_sample_format_dataframe()
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    sample_df.to_excel(writer, index=False)
                st.download_button(_t("✅ 下載", "✅ Download"), output.getvalue(), "Prefect_Roster_Format_Example.xlsx", use_container_width=True)

        uploaded_roster = st.file_uploader(_t("上傳名冊 (Excel/CSV)", "Upload Roster (Excel/CSV)"), type=["csv", "xlsx", "xls"], key="roster_importer")
        col_trad, col_ai = st.columns(2)
        with col_trad:
            if uploaded_roster and st.button(_t("📋 傳統導入", "📋 Traditional Import")):
                process_roster_import(uploaded_roster)
        with col_ai:
            if uploaded_roster and st.button(_t("🤖 AI 智能匹配", "🤖 AI Smart Match"), type="primary"):
                smart_process_roster_import(uploaded_roster)

        st.caption(_t("💡 AI 支援任意欄位順序，節省您的時間", "💡 AI supports any column order, saving your time"))

        st.divider()

        # ==================== 名冊即時修改 ====================
        st.subheader(_t("👥 名冊即時修改", "👥 Live Roster Edit"))
        st.caption(_t("修改後自動儲存", "Auto-saved after modification"))

        # Quick Search & Filter (by name, form, role)
        search_term = st.text_input(_t("🔍 快速搜尋學生 (Quick Search by name, form, role)", "🔍 Quick Search Student (by name, form, role)"), value=st.session_state.get("student_search", ""), key="student_search_input")
        st.session_state.student_search = search_term

        # Always edit the full df for persistence; show filtered view below if searching
        st.session_state.students_df = st.data_editor(
            st.session_state.students_df,
            column_config={
                "name": st.column_config.TextColumn(_t("姓名 *", "Name *"), required=True),
                "form": st.column_config.SelectboxColumn(_t("年級", "Form"), options=["F.3", "F.4", "F.5", "F.6"]),
                "role": st.column_config.SelectboxColumn(_t("職級", "Role"), options=["首席導學風紀", "助理首席導學風紀", "導學風紀"]),
                "fixed_general_duty": st.column_config.SelectboxColumn(_t("固定值班", "Fixed Duty"), options=["NONE", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]),
                "available": st.column_config.TextColumn(_t("可用日子", "Available Days")),
                "history_duties": st.column_config.NumberColumn(_t("歷史次數", "History Count"), min_value=0),
                "history_weight": st.column_config.NumberColumn(_t("歷史點數", "History Points"), min_value=0.0),
                "remarks": st.column_config.TextColumn(_t("備註", "Remarks"))
            },
            num_rows="dynamic",
            hide_index=True,
            key="student_editor_widget"
        )

        if search_term:
            mask = (st.session_state.students_df["name"].astype(str).str.contains(search_term, case=False, na=False) |
                    st.session_state.students_df["form"].astype(str).str.contains(search_term, case=False, na=False) |
                    st.session_state.students_df["role"].astype(str).str.contains(search_term, case=False, na=False))
            filtered = st.session_state.students_df[mask]
            st.caption(f"{_t('顯示', 'Showing')} {len(filtered)} / {len(st.session_state.students_df)} {_t('位學生 (搜尋結果)', 'students (search results)')}")
            st.dataframe(filtered, hide_index=True)

        st.divider()

        # ==================== AI 解析 ====================
        st.subheader(_t("🤖 AI 智能解析", "🤖 AI Smart Parse"))
        if st.button(_t("🚀 執行 AI 解析 Remarks", "🚀 Run AI Parse Remarks"), type="secondary"):
            with st.spinner(_t("AI 正在智能分析...", "AI is intelligently analyzing...")):
                updated_df = ai_parse_remarks(st.session_state.students_df)
                st.session_state.students_df = updated_df
                st.success(_t("✅ AI 已自動更新固定值班、可值班日與職級", "✅ AI has auto-updated fixed duties, available days, and roles"))
                trigger_backup_reminder()  # 重要操作提醒
                st.rerun()

        st.divider()

        # ==================== 請假登記 ====================
        st.subheader(_t("🛑 請假登記", "🛑 Leave Registration"))
        valid_names = [str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip()]
        st.session_state.leave_tracker_input = st.multiselect(
            _t("今日請假人員（可多選）", "Today's Leave Personnel (multi-select)"),
            options=valid_names,
            default=st.session_state.get("leave_tracker_input", [])
        )

        st.divider()

        # ==================== 智慧自動完成輸入 (Smart Autocomplete for Adding Students) ====================
        st.subheader(_t("➕ 智慧新增學生 (Smart Autocomplete)", "➕ Smart Add Student (Autocomplete)"))
        st.caption(_t("輸入姓名，選擇職級 (僅三種選項)，快速新增", "Enter name, select role (only 3 options), quick add"))
        new_name = st.text_input(_t("姓名 (Name)", "Name (Name)"), key="new_name_input")
        new_role = st.selectbox(_t("職級 (Role)", "Role (Role)"), ["首席導學風紀", "助理首席導學風紀", "導學風紀"], key="new_role_select")
        if st.button(_t("新增學生 (Add Student)", "Add Student (Add Student)"), key="add_student_btn") and new_name.strip():
            new_row = pd.DataFrame([{
                "name": new_name.strip(),
                "form": "F.3",
                "class": "",
                "role": new_role,
                "fixed_general_duty": "NONE",
                "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
                "history_duties": 0,
                "history_weight": 0.0,
                "remarks": ""
            }])
            st.session_state.students_df = pd.concat([st.session_state.students_df, new_row], ignore_index=True)
            st.success(_t(f"已新增 {new_name.strip()} ({new_role})", f"Added {new_name.strip()} ({new_role})"))
            st.rerun()

        st.divider()

        # ==================== 批量管理 (Batch Leave & Fixed Duty - High Priority) ====================
        st.subheader(_t("📋 批量管理", "📋 Batch Management"))
        st.caption(_t("一次選擇多名學生，批量設定請假或固定值班（方便 Head / AHP 操作）", "Select multiple students for batch leave or fixed duty (convenient for Head / AHP)"))
        valid_names = [str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip()]
        bulk_selected = st.multiselect(
            "選擇學生（可多選）",
            options=valid_names,
            default=st.session_state.get("selected_students_for_bulk", []),
            key="bulk_students"
        )
        st.session_state.selected_students_for_bulk = bulk_selected

        if bulk_selected:
            bulk_type = st.radio(_t("批量類型", "Batch Type"), [_t("設定請假", "Set Leave"), _t("設定固定值班", "Set Fixed Duty")], horizontal=True, key="bulk_type")
            if bulk_type == _t("設定請假", "Set Leave"):
                if st.button(_t("✅ 批量請假", "✅ Batch Leave"), use_container_width=True, type="primary"):
                    current_leave = set(st.session_state.get("leave_tracker_input", []))
                    current_leave.update(bulk_selected)
                    st.session_state.leave_tracker_input = list(current_leave)
                    st.success(_t(f"✅ 已為 {len(bulk_selected)} 位學生批量設定請假。請記得在生成排班時套用，並下載 JSON 備份（建議 commit 到 GitHub backups/ 資料夾）。", f"✅ Batch leave set for {len(bulk_selected)} students. Remember to apply when generating roster and download JSON backup (recommend commit to GitHub backups/ folder)."))
                    st.session_state.selected_students_for_bulk = []
                    trigger_backup_reminder()
                    st.rerun()
            else:
                bulk_day = st.selectbox(_t("選擇固定日子", "Select Fixed Day"), ["NONE"] + DAYS, key="bulk_fixed_day")
                if st.button(_t("✅ 批量設定固定值班", "✅ Batch Set Fixed Duty"), use_container_width=True, type="primary"):
                    updated = 0
                    for name in bulk_selected:
                        mask = st.session_state.students_df["name"].str.strip() == name
                        if mask.any():
                            st.session_state.students_df.loc[mask, "fixed_general_duty"] = bulk_day
                            updated += 1
                    st.success(_t(f"✅ 已為 {updated} 位學生設定固定 {bulk_day}。請下載 JSON 備份以保存變更，並建議上傳到 GitHub backups/ 資料夾。", f"✅ Fixed {bulk_day} set for {updated} students. Please download JSON backup to save changes and recommend upload to GitHub backups/ folder."))
                    st.session_state.selected_students_for_bulk = []
                    trigger_backup_reminder()
                    st.rerun()
            if st.button(_t("❌ 清除選擇", "❌ Clear Selection"), use_container_width=True):
                st.session_state.selected_students_for_bulk = []
                st.rerun()

        st.divider()

        # ==================== Cloud 備份與還原 ====================
        st.subheader(_t("💾 Cloud 備份與還原", "💾 Cloud Backup & Restore"))
        st.caption(_t("⚠️ Streamlit Cloud 為無狀態環境，資料可能因休眠或重啟而遺失，請務必做好備份！", "⚠️ Streamlit Cloud is stateless. Data may be lost on sleep or restart. Always backup!"))

        # 備份說明（清楚解釋靜態/動態、JSON 與 PDF 的角色） - 內容固定英文 key 概念，但顯示跟語言
        backup_explain_zh = """
**備份說明（請詳讀）：**
- **靜態資料**（姓名、年級、班別、職級、可用日子、固定值班）：主要從 GitHub 倉庫載入（例如 data/students.csv），作為長期來源。
- **動態資料**（累計點數、當週排班、手動調整負荷、請假記錄、歷史趨勢等）：請使用下方 JSON 備份保存。
- **JSON 備份**：主要備份方式，只包含動態數據，檔案輕巧。重要操作後請立即下載。
- **PDF 備份頁**：匯出的 PDF 報告最後一頁會附加動態數據（標註「內部使用，請分享前刪除」）。此頁方便緊急還原，但請務必移除再分享。
- **長期保存建議**：重要的 JSON 備份，請手動上傳至 GitHub 倉庫的 `backups/` 資料夾，進行版本控制與災難恢復。
"""
        backup_explain_en = """
**Backup Instructions (Please read carefully):**
- **Static Data** (name, form, class, role, available days, fixed duty): Mainly loaded from GitHub repo (e.g. data/students.csv) as long-term source.
- **Dynamic Data** (cumulative points, weekly roster, manual adjustments, leave records, history trends, etc.): Use JSON backup below to save.
- **JSON Backup**: Primary backup method, contains only dynamic data, lightweight. Download immediately after important operations.
- **PDF Backup Page**: The last page of exported PDF report will include dynamic data (marked "INTERNAL USE ONLY - PLEASE REMOVE THIS PAGE BEFORE DISTRIBUTION"). Convenient for emergency restore, but must remove before sharing.
- **Long-term Storage Recommendation**: Important JSON backups, manually upload to GitHub repo's `backups/` folder for version control and disaster recovery.
"""
        st.markdown(_t(backup_explain_zh, backup_explain_en))

        # 自動備份提醒
        if st.session_state.get("backup_reminder", False):
            st.warning(_t("🔔 重要操作完成！強烈建議立即下載 JSON 備份（動態數據），並將重要版本上傳到 GitHub 的 backups/ 資料夾長期保存，以避免資料遺失。", "🔔 Important operation completed! Strongly recommend downloading JSON backup (dynamic data) immediately and uploading important versions to GitHub backups/ folder for long-term storage to avoid data loss."))
            if st.button(_t("立即備份", "Backup Now"), key="reminder_backup", type="primary"):
                backup_json = export_system_backup(st.session_state.get("master_report_df", pd.DataFrame()))
                st.download_button(_t("📥 下載備份 JSON", "📥 Download Backup JSON"), backup_json, f"SYSS_Backup_{datetime.date.today().strftime('%Y%m%d_%H%M')}.json")
                clear_backup_reminder()
                st.rerun()

        # 導出目前狀態
        if st.button(_t("⬇️ 導出目前完整備份", "⬇️ Export Current Full Backup")):
            backup_json = export_system_backup(st.session_state.get("master_report_df", pd.DataFrame()))
            st.download_button(
                _t("📥 下載 JSON 備份", "📥 Download JSON Backup"),
                backup_json,
                f"SYSS_Backup_{datetime.date.today().strftime('%Y%m%d_%H%M')}.json",
                use_container_width=True
            )
            clear_backup_reminder()

        # 多版本備份管理（從 session history）
        history = get_backup_history()
        if history:
            st.caption(_t(f"📚 本次工作階段備份歷史（共 {len(history)} 個，最新在前）", f"📚 Backup history this session ({len(history)} total, newest first)"))
            for i, entry in enumerate(reversed(history[-5:])):  # 顯示最近 5 個
                label = f"v{entry.get('version', i+1)} - {entry['timestamp'][:16]}"
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.caption(label)
                with col2:
                    if st.button(_t("下載", "Download"), key=f"dl_hist_{i}", help=f"下載 {label}"):
                        st.download_button(
                            f"📥 {label}.json",
                            entry["json"],
                            f"SYSS_Backup_v{entry.get('version')}.json",
                            key=f"dlbtn_hist_{i}"
                        )
                    if st.button(_t("還原此版本", "Restore this version"), key=f"restore_hist_{i}", help=_t("選擇還原模式", "Choose restore mode")):
                        # 暫存選中的 json 給下方 uploader 邏輯使用
                        st.session_state["pending_restore_json"] = entry["json"]
                        st.rerun()

        # 還原區塊（含驗證 + 模式選擇）
        st.caption(_t("上傳備份 JSON 進行還原", "Upload backup JSON to restore"))
        uploaded_backup = st.file_uploader(
            _t("選擇備份檔案 (.json)", "Select backup file (.json)"),
            type=["json"],
            key="backup_importer",
            help=_t("建議使用本系統導出的備份檔", "Recommend using backups exported by this system")
        )

        # 如果有 pending 歷史版本，顯示提示
        pending_json = st.session_state.get("pending_restore_json")
        if pending_json:
            st.info(_t("已選擇歷史版本。請選擇還原模式後點擊還原。", "History version selected. Please choose restore mode then click restore."))
            restore_mode = st.radio(
                _t("還原模式", "Restore Mode"),
                [_t("Full Replace（完全取代）", "Full Replace（Complete Replace）"), _t("Smart Merge（智慧合併）", "Smart Merge（Smart Merge）")],
                index=0,
                key="restore_mode_hist",
                horizontal=True
            )
            if st.button(_t("🔄 執行還原此版本", "🔄 Execute Restore this version"), type="primary", use_container_width=True, key="restore_hist_btn"):
                # 模擬檔案上傳
                import io
                fake_file = io.BytesIO(pending_json.encode('utf-8'))
                mode = "full" if "Full" in restore_mode else "smart_merge"
                import_system_backup(fake_file, replace_mode=mode)
                st.session_state.pop("pending_restore_json", None)
                st.rerun()
            if st.button(_t("取消選擇", "Cancel Selection"), key="cancel_hist"):
                st.session_state.pop("pending_restore_json", None)
                st.rerun()

        if uploaded_backup:
            restore_mode = st.radio(
                _t("還原模式", "Restore Mode"),
                [_t("Full Replace（完全取代）", "Full Replace（Complete Replace）"), _t("Smart Merge（智慧合併）", "Smart Merge（Smart Merge）")],
                index=0,
                key="restore_mode_upload",
                horizontal=True,
                help="Full Replace: 完全覆蓋目前所有資料。Smart Merge: 智慧合併學生資料，當週排班傾向使用備份。"
            )
            if st.button("🔄 執行還原", type="primary", use_container_width=True):
                mode = "full" if "Full" in restore_mode else "smart_merge"
                import_system_backup(uploaded_backup, replace_mode=mode)

        # 顯示上次備份時間（如果有）
        last_backup = st.session_state.get("last_backup_time")
        if last_backup:
            st.caption(f"上次成功備份時間: {last_backup[:16]}")

        # 長期保存引導（溫和建議）
        st.caption("💡 長期保存建議：重要的 JSON 備份，請手動上傳至 GitHub 倉庫的 `backups/` 資料夾（例如命名為 backup_2026-06-13_週三.json），以進行版本控制與災難恢復。即使本地遺失，也能從 GitHub 還原。")


def render_control_buttons():
    """主畫面控制按鈕 - 清晰、突出主要行動"""
    closure_options = [f"{d} - {room}" for d in DAYS for room in ["Room302", "Room303", "Room202"]
                       if not (room == "Room202" and d in ["TUESDAY", "FRIDAY"])]
    selected_closures = st.multiselect(_t("🛠️ 本週特殊不開放時段", "🛠️ This week's special closed periods"), options=closure_options, key="special_closures")

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button(_t("🚀 智能計算：生成本週全新公平值班表", "🚀 Smart Compute: Generate this week's new fair roster"), type="primary", use_container_width=True):
            with st.spinner(_t("正在進行公平排班計算...", "Performing fair roster calculation...")):
                seed = random.randint(10000, 99999)
                global_multiplier = st.session_state.get("global_load_multiplier", 1.0)
                st.session_state.roster_df = generate_roster(
                    st.session_state.students_df,
                    st.session_state.leave_tracker_input,
                    selected_closures,
                    seed,
                    global_load_multiplier=global_multiplier
                )
                # Save roster version for history (roster version history feature)
                versions = st.session_state.get("roster_versions", [])
                version_num = len(versions) + 1
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                versions.append({
                    "version": version_num,
                    "timestamp": timestamp,
                    "roster_df": st.session_state.roster_df.to_dict(),
                    "report_df": st.session_state.get("master_report_df", pd.DataFrame()).to_dict() if not st.session_state.get("master_report_df", pd.DataFrame()).empty else {}
                })
                st.session_state.roster_versions = versions
                st.success(_t(f"✅ 排班完成！（全局負荷倍率：{global_multiplier:.1f}） 已儲存版本 #{version_num}。請記得下載 JSON 備份，並建議將重要版本上傳到 GitHub backups/ 資料夾長期保存。", f"✅ Roster complete! (Global load multiplier: {global_multiplier:.1f}) Version #{version_num} saved. Remember to download JSON backup and recommend uploading important versions to GitHub backups/ folder for long-term storage."))

                # Auto update semester hours (1 hour per duty slot)
                for name in st.session_state.students_df["name"].dropna().astype(str).str.strip():
                    count = (st.session_state.roster_df == name).sum().sum()
                    hours = count * 1.0
                    current_hours = st.session_state.get("semester_hours", {}).get(name, 0)
                    st.session_state.semester_hours[name] = current_hours + hours

                # 自動備份提醒
                trigger_backup_reminder()

    with col2:
        if st.button(_t("🗑️ 清空", "🗑️ Clear"), type="secondary", use_container_width=True):
            st.session_state.show_clear_confirm = True

    if st.session_state.get("show_clear_confirm", False):
        st.error(_t("⚠️ 確定要清除全部排班？此操作無法復原！", "⚠️ Confirm to clear all roster? This cannot be undone!"))
        c1, c2 = st.columns(2)
        if c1.button(_t("💥 確定清空", "💥 Confirm Clear")):
            st.session_state.roster_df = pd.DataFrame(index=get_roster_rows(), columns=DAYS).fillna("")
            st.session_state.show_clear_confirm = False
            st.rerun()
        if c2.button(_t("❌ 取消", "❌ Cancel")):
            st.session_state.show_clear_confirm = False
            st.rerun()

    return selected_closures


print("✅ ui_components.py 已載入完成 - 人性化重新設計前端（心理學優化版）")