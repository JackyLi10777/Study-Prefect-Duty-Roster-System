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
    DAYS, get_roster_rows, DAILY_VERSES, VERSION, PROJECT_FULL_NAME,
    NASA_COLORS, get_role_style
)
from roster.core import generate_roster
from roster.utils import (
    process_roster_import, smart_process_roster_import,
    export_system_backup, import_system_backup,
    trigger_backup_reminder, clear_backup_reminder, get_backup_history
)
from roster.data import get_demo_dataframe, get_sample_format_dataframe
from roster.ai import ai_parse_remarks  # use package path (root ai_parser shim still works for legacy)

# ====================== 合併所有金句供隨機刷新使用 ======================
ALL_VERSES = []
for day_list in DAILY_VERSES.values():
    ALL_VERSES.extend(day_list)

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
    """
    if "current_verse" not in st.session_state or st.session_state.current_verse is None:
        st.session_state.current_verse = random.choice(ALL_VERSES)

    verse_text = st.session_state.current_verse
    show_bilingual = st.session_state.get("verse_bilingual", False)

    # 使用最小 unsafe 包裝 class，內容用原生 markdown 乾淨顯示
    st.markdown('<div class="verse-card">', unsafe_allow_html=True)

    st.markdown("**📖 今日聖經金句**")
    st.markdown(verse_text)

    if show_bilingual:
        st.markdown(
            "English Reflection: “Whoever wants to become great among you must be your servant.” — Mark 10:43  \n"
            "默想：以謙卑服事他人，促進公平與責任。"
        )

    st.caption("—— 聖言中學導學風紀團隊靈修提醒 | 僕人領袖，以服事為本")

    st.markdown('</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])
    with col1:
        if st.button("🔄 刷新金句", use_container_width=True, type="secondary", help="獲得新的靈修鼓勵"):
            st.session_state.current_verse = random.choice(ALL_VERSES)
            st.rerun()
    with col2:
        st.session_state.verse_bilingual = st.checkbox(
            "顯示英文反思", 
            value=st.session_state.get("verse_bilingual", False), 
            key="verse_bilingual_toggle",
            help="Bilingual option for deeper reflection"
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
            lang_options = ["中文介面", "英文介面"]
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
                st.caption("英文介面 + 專業英文匯出")
            else:
                st.caption("中文介面（匯出支援英文）")

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
            .verse-card { background: linear-gradient(180deg, #1a1f2e 0%, #0e1117 100%) !important; border: 1px solid #4b5563; padding: 12px; border-radius: 8px; }
            .verse-card h3, .verse-card p, .verse-card { color: #ffeb3b !important; } /* 高對比亮黃 */
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
            .verse-card { background: linear-gradient(180deg, #1A1A2E 0%, #0B1E3D 100%) !important; border: 1px solid #D4AF37; padding: 12px; border-radius: 8px; }
            .verse-card h3, .verse-card p, .verse-card { color: #F5E8C7 !important; }
            .stTextInput > div > div > input, .stSelectbox > div > div { background-color: #ffffff; color: #1a1a2e; }
            </style>
            """, unsafe_allow_html=True)

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
        st.subheader(_t("📊 即時累計統計", "📊 Live Statistics"))
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
        st.subheader(_t("🗄️ 名冊管理", "🗄️ Roster Management"))
        col_demo, col_sample = st.columns(2)
        with col_demo:
            if st.button("💡 一鍵載入官方示範名冊"):
                st.session_state.students_df = get_demo_dataframe()
                st.success("✅ 示範名冊載入完成")
                st.rerun()
        with col_sample:
            if st.button("📥 下載格式範例"):
                sample_df = get_sample_format_dataframe()
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    sample_df.to_excel(writer, index=False)
                st.download_button("✅ 下載", output.getvalue(), "Prefect_名冊格式範例.xlsx", use_container_width=True)

        uploaded_roster = st.file_uploader("上傳名冊 (Excel/CSV)", type=["csv", "xlsx", "xls"], key="roster_importer")
        col_trad, col_ai = st.columns(2)
        with col_trad:
            if uploaded_roster and st.button("📋 傳統導入"):
                process_roster_import(uploaded_roster)
        with col_ai:
            if uploaded_roster and st.button("🤖 AI 智能匹配", type="primary"):
                smart_process_roster_import(uploaded_roster)

        st.caption("💡 AI 支援任意欄位順序，節省您的時間")

        st.divider()

        # ==================== 名冊即時修改 ====================
        st.subheader(_t("👥 名冊即時修改", "👥 Live Roster Edit"))
        st.caption("修改後自動儲存")

        # Quick Search & Filter (by name, form, role)
        search_term = st.text_input("🔍 快速搜尋學生 (Quick Search by name, form, role)", value=st.session_state.get("student_search", ""), key="student_search_input")
        st.session_state.student_search = search_term

        # Always edit the full df for persistence; show filtered view below if searching
        st.session_state.students_df = st.data_editor(
            st.session_state.students_df,
            column_config={
                "name": st.column_config.TextColumn("姓名 *", required=True),
                "form": st.column_config.SelectboxColumn("年級", options=["F.3", "F.4", "F.5", "F.6"]),
                "role": st.column_config.SelectboxColumn("職級", options=["首席導學風紀", "助理首席導學風紀", "導學風紀"]),
                "fixed_general_duty": st.column_config.SelectboxColumn("固定值班", options=["NONE", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]),
                "available": st.column_config.TextColumn("可用日子"),
                "history_duties": st.column_config.NumberColumn("歷史次數", min_value=0),
                "history_weight": st.column_config.NumberColumn("歷史點數", min_value=0.0),
                "remarks": st.column_config.TextColumn("備註")
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
            st.caption(f"顯示 {len(filtered)} / {len(st.session_state.students_df)} 位學生 (搜尋結果)")
            st.dataframe(filtered, hide_index=True)

        st.divider()

        # ==================== AI 解析 ====================
        st.subheader(_t("🤖 AI 智能解析", "🤖 AI Smart Parse"))
        if st.button("🚀 執行 AI 解析 Remarks", type="secondary"):
            with st.spinner("AI 正在智能分析..."):
                updated_df = ai_parse_remarks(st.session_state.students_df)
                st.session_state.students_df = updated_df
                st.success("✅ AI 已自動更新固定值班、可值班日與職級")
                trigger_backup_reminder()  # 重要操作提醒
                st.rerun()

        st.divider()

        # ==================== 請假登記 ====================
        st.subheader(_t("🛑 請假登記", "🛑 Leave Registration"))
        valid_names = [str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip()]
        st.session_state.leave_tracker_input = st.multiselect(
            "今日請假人員（可多選）",
            options=valid_names,
            default=st.session_state.get("leave_tracker_input", [])
        )

        st.divider()

        # ==================== 智慧自動完成輸入 (Smart Autocomplete for Adding Students) ====================
        st.subheader("➕ 智慧新增學生 (Smart Autocomplete)")
        st.caption("輸入姓名，選擇職級 (僅三種選項)，快速新增")
        new_name = st.text_input("姓名 (Name)", key="new_name_input")
        new_role = st.selectbox("職級 (Role)", ["首席導學風紀", "助理首席導學風紀", "導學風紀"], key="new_role_select")
        if st.button("新增學生 (Add Student)", key="add_student_btn") and new_name.strip():
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
            st.success(f"已新增 {new_name.strip()} ({new_role})")
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
            bulk_type = st.radio("批量類型", ["設定請假", "設定固定值班"], horizontal=True, key="bulk_type")
            if bulk_type == "設定請假":
                if st.button("✅ 批量請假", use_container_width=True, type="primary"):
                    current_leave = set(st.session_state.get("leave_tracker_input", []))
                    current_leave.update(bulk_selected)
                    st.session_state.leave_tracker_input = list(current_leave)
                    st.success(f"✅ 已為 {len(bulk_selected)} 位學生批量設定請假。請記得在生成排班時套用，並下載 JSON 備份（建議 commit 到 GitHub backups/ 資料夾）。")
                    st.session_state.selected_students_for_bulk = []
                    trigger_backup_reminder()
                    st.rerun()
            else:
                bulk_day = st.selectbox("選擇固定日子", ["NONE"] + DAYS, key="bulk_fixed_day")
                if st.button("✅ 批量設定固定值班", use_container_width=True, type="primary"):
                    updated = 0
                    for name in bulk_selected:
                        mask = st.session_state.students_df["name"].str.strip() == name
                        if mask.any():
                            st.session_state.students_df.loc[mask, "fixed_general_duty"] = bulk_day
                            updated += 1
                    st.success(f"✅ 已為 {updated} 位學生設定固定 {bulk_day}。請下載 JSON 備份以保存變更，並建議上傳到 GitHub backups/ 資料夾。")
                    st.session_state.selected_students_for_bulk = []
                    trigger_backup_reminder()
                    st.rerun()
            if st.button("❌ 清除選擇", use_container_width=True):
                st.session_state.selected_students_for_bulk = []
                st.rerun()

        st.divider()

        # ==================== Cloud 備份與還原 ====================
        st.subheader("💾 Cloud 備份與還原")
        st.caption("⚠️ Streamlit Cloud 為無狀態環境，資料可能因休眠或重啟而遺失，請務必做好備份！")

        # 備份說明（清楚解釋靜態/動態、JSON 與 PDF 的角色）
        st.markdown("""
**備份說明（請詳讀）：**
- **靜態資料**（姓名、年級、班別、職級、可用日子、固定值班）：主要從 GitHub 倉庫載入（例如 data/students.csv），作為長期來源。
- **動態資料**（累計點數、當週排班、手動調整負荷、請假記錄、歷史趨勢等）：請使用下方 JSON 備份保存。
- **JSON 備份**：主要備份方式，只包含動態數據，檔案輕巧。重要操作後請立即下載。
- **PDF 備份頁**：匯出的 PDF 報告最後一頁會附加動態數據（標註「內部使用，請分享前刪除」）。此頁方便緊急還原，但請務必移除再分享。
- **長期保存建議**：重要的 JSON 備份，請手動上傳至 GitHub 倉庫的 `backups/` 資料夾，進行版本控制與災難恢復。
""")

        # 自動備份提醒
        if st.session_state.get("backup_reminder", False):
            st.warning("🔔 重要操作完成！強烈建議立即下載 JSON 備份（動態數據），並將重要版本上傳到 GitHub 的 backups/ 資料夾長期保存，以避免資料遺失。")
            if st.button("立即備份", key="reminder_backup", type="primary"):
                backup_json = export_system_backup(st.session_state.get("master_report_df", pd.DataFrame()))
                st.download_button("📥 下載備份 JSON", backup_json, f"SYSS_Backup_{datetime.date.today().strftime('%Y%m%d_%H%M')}.json")
                clear_backup_reminder()
                st.rerun()

        # 導出目前狀態
        if st.button("⬇️ 導出目前完整備份"):
            backup_json = export_system_backup(st.session_state.get("master_report_df", pd.DataFrame()))
            st.download_button(
                "📥 下載 JSON 備份",
                backup_json,
                f"SYSS_Backup_{datetime.date.today().strftime('%Y%m%d_%H%M')}.json",
                use_container_width=True
            )
            clear_backup_reminder()

        # 多版本備份管理（從 session history）
        history = get_backup_history()
        if history:
            st.caption(f"📚 本次工作階段備份歷史（共 {len(history)} 個，最新在前）")
            for i, entry in enumerate(reversed(history[-5:])):  # 顯示最近 5 個
                label = f"v{entry.get('version', i+1)} - {entry['timestamp'][:16]}"
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.caption(label)
                with col2:
                    if st.button("下載", key=f"dl_hist_{i}", help=f"下載 {label}"):
                        st.download_button(
                            f"📥 {label}.json",
                            entry["json"],
                            f"SYSS_Backup_v{entry.get('version')}.json",
                            key=f"dlbtn_hist_{i}"
                        )
                    if st.button("還原此版本", key=f"restore_hist_{i}", help="選擇還原模式"):
                        # 暫存選中的 json 給下方 uploader 邏輯使用
                        st.session_state["pending_restore_json"] = entry["json"]
                        st.rerun()

        # 還原區塊（含驗證 + 模式選擇）
        st.caption("上傳備份 JSON 進行還原")
        uploaded_backup = st.file_uploader(
            "選擇備份檔案 (.json)",
            type=["json"],
            key="backup_importer",
            help="建議使用本系統導出的備份檔"
        )

        # 如果有 pending 歷史版本，顯示提示
        pending_json = st.session_state.get("pending_restore_json")
        if pending_json:
            st.info("已選擇歷史版本。請選擇還原模式後點擊還原。")
            restore_mode = st.radio(
                "還原模式",
                ["Full Replace（完全取代）", "Smart Merge（智慧合併）"],
                index=0,
                key="restore_mode_hist",
                horizontal=True
            )
            if st.button("🔄 執行還原此版本", type="primary", use_container_width=True, key="restore_hist_btn"):
                # 模擬檔案上傳
                import io
                fake_file = io.BytesIO(pending_json.encode('utf-8'))
                mode = "full" if "Full" in restore_mode else "smart_merge"
                import_system_backup(fake_file, replace_mode=mode)
                st.session_state.pop("pending_restore_json", None)
                st.rerun()
            if st.button("取消選擇", key="cancel_hist"):
                st.session_state.pop("pending_restore_json", None)
                st.rerun()

        if uploaded_backup:
            restore_mode = st.radio(
                "還原模式",
                ["Full Replace（完全取代）", "Smart Merge（智慧合併）"],
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
                st.success(f"✅ 排班完成！（全局負荷倍率：{global_multiplier:.1f}） 已儲存版本 #{version_num}。請記得下載 JSON 備份，並建議將重要版本上傳到 GitHub backups/ 資料夾長期保存。")

                # Auto update semester hours (1 hour per duty slot)
                for name in st.session_state.students_df["name"].dropna().astype(str).str.strip():
                    count = (st.session_state.roster_df == name).sum().sum()
                    hours = count * 1.0
                    current_hours = st.session_state.get("semester_hours", {}).get(name, 0)
                    st.session_state.semester_hours[name] = current_hours + hours

                # 自動備份提醒
                trigger_backup_reminder()

    with col2:
        if st.button("🗑️ 清空", type="secondary", use_container_width=True):
            st.session_state.show_clear_confirm = True

    if st.session_state.get("show_clear_confirm", False):
        st.error("⚠️ 確定要清除全部排班？此操作無法復原！")
        c1, c2 = st.columns(2)
        if c1.button("💥 確定清空"):
            st.session_state.roster_df = pd.DataFrame(index=get_roster_rows(), columns=DAYS).fillna("")
            st.session_state.show_clear_confirm = False
            st.rerun()
        if c2.button("❌ 取消"):
            st.session_state.show_clear_confirm = False
            st.rerun()

    return selected_closures


print("✅ ui_components.py 已載入完成 - 人性化重新設計前端（心理學優化版）")