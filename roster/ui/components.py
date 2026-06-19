# ui_components.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
UI 元件模組 - 側邊欄、神聖每日聖經金句、控制按鈕（人性化重新設計版）

作者：首席導學風紀 26-27 LI Chuangjie Jacky
版本：v2.4 Final（師徒配對系統完成 + 深色模式 + PDF 師徒摘要 + 學徒進度追蹤 + 專業視覺層級）
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
    NASA_COLORS, get_role_style,
    HEAD_ROLE, AHP_ROLE, REGULAR_ROLE
)
from roster.data import get_demo_dataframe, get_sample_format_dataframe, DAILY_VERSES
from roster.data.state import get_state, set_state, reset_roster_related_state
from roster.core import generate_roster, annotate_mentoring_pairs, compute_possible_mentoring_pairs
from roster.utils import (
    process_roster_import, smart_process_roster_import,
    export_system_backup, import_system_backup,
    trigger_backup_reminder, clear_backup_reminder, get_backup_history, generate_pdf
)
from roster.data.models import get_ui_report_df
from roster.ai import ai_parse_remarks  # use package path (root ai_parser shim still works for legacy)

# Centralized display-layer language, messages & theme (new architecture)
from roster.ui.i18n import _t, get_text
from roster.ui import messages, theme
from roster.ui.theme import apply_theme  # future central injection point

# ====================== 合併所有金句供隨機刷新使用 ======================
# 使用新 daily_verses.py 的結構 (verse_001 等 key)
ALL_VERSES = list(DAILY_VERSES.keys())

# Note: UI layer calls into business logic (generate_roster) per AGENTS.md guidelines.
# Direct calls are kept for now to preserve exact original behavior during migration.

def show_daily_verse():
    """
    神聖莊重每日聖經金句區塊。
    - 經文（標題 + 章節 + 內容）和靈修反思明確放在金邊背景框（.verse-card）內。
    - 反思使用嵌套 .reflection-box 確保在框內不跑出。
    - 使用單一 unsafe HTML 塊確保視覺容器正確包含所有內容。
    - 完全支援語言切換，內容跟隨 ui_language。
    - 深色/淺色模式都有良好視覺層次與對比度（CSS 強化）。
    """
    if ("current_verse" not in st.session_state or 
        st.session_state.current_verse is None or
        not isinstance(st.session_state.current_verse, str) or
        st.session_state.current_verse not in DAILY_VERSES):
        st.session_state.current_verse = random.choice(ALL_VERSES)

    verse_key = st.session_state.current_verse
    verse = DAILY_VERSES.get(verse_key, {})
    lang = st.session_state.get("ui_language", "zh")

    if lang == "en":
        ref = verse.get('reference_en', '')
        text = verse.get('en', '')
        refl_title = "English Reflection"
        refl = verse.get('reflection_en', '')
        verse_title = "Daily Bible Verse"
        footer = "— Sing Yin Study Prefect Team Spiritual Reminder | Servant Leadership, Service First"
    else:
        ref = verse.get('reference_zh', '')
        text = verse.get('zh', '')
        refl_title = "靈修反思"
        refl = verse.get('reflection_zh', '')
        verse_title = "今日聖經金句"
        footer = "—— 聖言中學導學風紀團隊靈修提醒 | 僕人領袖，以服事為本"

    # Strict enclosure via .verse-inner (nested inside .verse-card golden border):
    # Guarantees verse (title + reference + content) + Spiritual Reflection (title + text)
    # are strictly inside the single golden border box with consistent >=16px padding
    # and no overflow in both light and dark modes. Reflection is internal framed section
    # (not independent). Footer moved inside .verse-inner for unified content block.
        # Determine translation attribution based on language
    if lang == "en":
        attr_text = "© RCUV 2010 (Shen) · HK Bible Society | NKJV © 1982 Thomas Nelson"
    else:
        attr_text = "© 和合本修訂版 2010（神版）· 香港聖經公會 | NKJV © 1982 Thomas Nelson"

    card_html = f"""
    <div class="verse-card">
        <div class="verse-inner">
            <h3 class="verse-title">📖 {verse_title}</h3>
            <p class="verse-ref"><strong>{ref}</strong></p>
            <p class="verse-text">{text}</p>
            <div class="reflection-box">
                <strong>{refl_title}</strong><br>{refl}
            </div>
            <p class="verse-attribution">{attr_text}</p>
            <div class="verse-footer">{footer}</div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    # 刷新按鈕（置於框外，但功能完整）
    if st.button(_t("🔄 刷新金句", "🔄 Refresh Verse"), width="stretch", type="secondary", help=_t("獲得新的靈修鼓勵", "Get new spiritual encouragement")):
        st.session_state.current_verse = random.choice(ALL_VERSES)
        st.rerun()


def render_sidebar():
    """側邊欄 - 極簡專業、清晰流程、即時統計與信任感設計"""
    with st.sidebar:
        st.header(_t("🏫 Sing Yin Secondary School", "🏫 Sing Yin Secondary School"))
        st.caption(get_text("platform_caption"))

        # Light / Dark Mode and Language (per requirements)
                # High Contrast mode was merged into Dark Mode for simplicity.
        # Now there is only one themed toggle: Dark Mode (boosted for maximum readability).
        # Any old high_contrast session_state values are silently ignored by theme.py.
        col_theme, col_lang = st.columns(2)
        with col_theme:
            is_dark = st.toggle(_t("深色模式", "Dark Mode"), value=get_state("theme", "light") == "dark", key="theme_toggle")
            set_state("theme", "dark" if is_dark else "light")
        with col_lang:
            # Capsule-style segmented control matching the Dark Mode toggle aesthetic.
            # Uses st.segmented_control for two connected pills: 中文 | English.
            current_lang = st.session_state.get("ui_language", "zh")
            default_lang = "中文" if current_lang == "zh" else "English"
            selected_lang = st.segmented_control(
                _t("介面語言", "Interface Language"),
                options=["中文", "English"],
                default=default_lang,
                key="lang_segmented",
                label_visibility="collapsed"
            )
            if selected_lang:
                new_lang = "zh" if selected_lang == "中文" else "en"
                if new_lang != st.session_state.get("_prev_lang_"):
                    st.toast(_t("語言已切換 ✓", "Language switched ✓"))
                st.session_state.ui_language = new_lang
                st.session_state._prev_lang_ = new_lang
            if st.session_state.ui_language == "en":
                st.caption(get_text("english_exports_caption"))
            else:
                st.caption(get_text("chinese_exports_caption"))

        # Apply theme CSS via centralized module (sole source of truth after de-dupe).
        # Base + dark/light overrides (strengthened contrast for placeholders, captions, labels, verse/reflection)
        # live in roster/ui/theme.py (get_base_css / get_dark_css / get_light_css / apply_theme).
        # Early apply in app.py main() + re-apply here after toggle ensures coverage + reactivity.
        # Toggle logic and verse HTML enclosure remain unchanged.
        theme.apply_theme()

        # ==================== 校徽（心理信任錨點） ====================
        show_logo = st.checkbox(_t("🖼️ 顯示校徽（畫面與 PDF）", "🖼️ Show School Badge (UI & PDF)"), value=True, key="show_logo_toggle")

        uploaded_logo = st.file_uploader(_t("上傳自訂校徽 (PNG)", "Upload Custom Badge (PNG)"), type=["png"], key="logo_uploader")
        if uploaded_logo:
            st.session_state.logo_data = uploaded_logo.getvalue()
            st.success(get_text("badge_updated"))
        elif show_logo and "logo_data" not in st.session_state:
            try:
                with open("logo.png", "rb") as f:
                    st.session_state.logo_data = f.read()
            except FileNotFoundError:
                pass

        st.divider()

        # ==================== 即時統計（公平感與成就感） ====================
        st.subheader(get_text("live_statistics_subheader"))
        if not st.session_state.students_df.empty:
            total = len(st.session_state.students_df)
            total_points = st.session_state.students_df["history_weight"].sum()
            avg = round(total_points / total, 1) if total > 0 else 0.0
            st.metric(_t("總領袖生", "Total Prefects"), f"{total} {_t('人', 'people')}", delta=None)
            st.metric(_t("累計總點數", "Total Points"), f"{total_points:.1f}")
            st.metric(_t("平均負荷", "Average Load"), f"{avg:.1f} {_t('點', 'pts')}")
        else:
            st.info(get_text("load_roster_prompt"))

        st.divider()

        # ==================== 名冊管理（清晰 CTA） ====================
        st.subheader(get_text("roster_management_subheader"))
        col_demo, col_sample = st.columns(2)
        with col_demo:
            if st.button(_t("💡 一鍵載入官方示範名冊", "💡 One-Click Load Official Demo Roster")):
                with st.spinner(_t("正在載入官方示範名冊，載入後建議立即下載 JSON 備份...", "Loading official demo roster — remember to download a JSON backup afterward...")):
                    st.session_state.students_df = get_demo_dataframe()
                st.success(get_text("demo_roster_loaded"))
                st.rerun()
        with col_sample:
            if st.button(_t("📥 下載格式範例", "📥 Download Format Example")):
                sample_df = get_sample_format_dataframe()
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    sample_df.to_excel(writer, index=False)
                st.download_button(_t("✅ 下載", "✅ Download"), output.getvalue(), "Prefect_Roster_Format_Example.xlsx", width="stretch")

        uploaded_roster = st.file_uploader(_t("上傳名冊 (Excel/CSV)", "Upload Roster (Excel/CSV)"), type=["csv", "xlsx", "xls"], key="roster_importer")
        col_trad, col_ai = st.columns(2)
        with col_trad:
            if uploaded_roster and st.button(_t("📋 傳統導入", "📋 Traditional Import")):
                with st.spinner(_t("正在導入名冊…", "Importing roster…")):
                    process_roster_import(uploaded_roster)
        with col_ai:
            if uploaded_roster and st.button(_t("🤖 AI 智能匹配", "🤖 AI Smart Match"), type="primary"):
                with st.spinner(_t("正在使用 AI 智能解析名冊…", "AI is parsing your roster…")):
                    smart_process_roster_import(uploaded_roster)

        st.caption(get_text("ai_support_caption"))

        st.divider()

        # ==================== 名冊即時修改 ====================
        st.subheader(get_text("live_roster_edit_subheader"))
        st.caption(get_text("auto_saved_caption"))

        # Quick Search & Filter (by name, form, role)
        search_term = st.text_input(_t("🔍 快速搜尋學生 (Quick Search by name, form, role)", "🔍 Quick Search Student (Quick Search by name, form, role)"), value=st.session_state.get("student_search", ""), key="student_search_input", placeholder=_t("輸入姓名、年級或職級關鍵字", "Enter name, form or role keyword"))
        st.session_state.student_search = search_term

        # Always edit the full df for persistence; show filtered view below if searching
        st.session_state.students_df = st.data_editor(
            st.session_state.students_df,
            column_config={
                "name": st.column_config.TextColumn(_t("姓名 *", "Name *"), required=True),
                "form": st.column_config.SelectboxColumn(_t("年級", "Form"), options=["F.3", "F.4", "F.5", "F.6"]),
                "role": st.column_config.SelectboxColumn(_t("職級", "Role"), options=[HEAD_ROLE, AHP_ROLE, REGULAR_ROLE]),
                "fixed_general_duty": st.column_config.SelectboxColumn(_t("固定值班", "Fixed Duty"), options=["NONE", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]),
                "available": st.column_config.TextColumn(_t("可用日子", "Available Days")),
                "history_duties": st.column_config.NumberColumn(_t("歷史次數", "History Count"), min_value=0),
                "history_weight": st.column_config.NumberColumn(_t("歷史點數", "History Points"), min_value=0.0),
                "needs_mentoring": st.column_config.CheckboxColumn(_t("需要師徒指導", "Needs Mentoring"), help=_t("累計點數過低時建議勾選，方便安排師徒配對", "Check when points are low to arrange mentoring")),
                "remarks": st.column_config.TextColumn(_t("備註", "Remarks"))
            },
            num_rows="dynamic",
            hide_index=True,
            key="student_editor_widget"
        )

        # Auto-tag legend
        st.caption(_t("自動標註說明：", "Auto-tagging:"))
        st.markdown('<div style="display:flex; gap:10px; flex-wrap:wrap; font-size:12px;">', unsafe_allow_html=True)
        st.markdown('<span style="background:#0F766E; color:white; padding:2px 8px; border-radius:10px;">🆕 新加入</span>', unsafe_allow_html=True)
        st.markdown('<span style="background:#F59E0B; color:white; padding:2px 8px; border-radius:10px;">👤 需要師徒指導</span>', unsafe_allow_html=True)
        st.markdown('<span style="background:#7C3AED; color:white; padding:2px 8px; border-radius:10px;">✅ 已指定師徒</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if search_term:
            mask = (st.session_state.students_df["name"].astype(str).str.contains(search_term, case=False, na=False) |
                    st.session_state.students_df["form"].astype(str).str.contains(search_term, case=False, na=False) |
                    st.session_state.students_df["role"].astype(str).str.contains(search_term, case=False, na=False))
            filtered = st.session_state.students_df[mask]
            if len(filtered) == 0:
                st.info(_t(
                    "🔍 ????????????????????????????",
                    "🔍 No matching students found. Try a different keyword (name, form, or role)."
                ))
            else:
                st.caption(f"{_t('顯示', 'Showing')} {len(filtered)} / {len(st.session_state.students_df)} {_t('位學生 (搜尋結果)', 'students (search results)')}")
            # Add mentoring status column
            search_display = filtered.copy()
            def _mentor_tag(row):
                hw = float(row.get("history_weight", 0))
                manual = bool(row.get("needs_mentoring", False))
                if manual:
                    return "✅ 已指定師徒"
                if hw == 0:
                    return "🆕 新加入"
                if hw <= 2:
                    return "👤 需要師徒指導"
                return ""
            search_display["狀態"] = search_display.apply(_mentor_tag, axis=1)
            st.dataframe(search_display[[_t("姓名", "Name"), "狀態", "form", "role", "history_weight"]], hide_index=True, width="stretch")

        st.divider()

        # ==================== AI 解析 ====================
        st.subheader(get_text("ai_smart_parse_subheader"))
        if st.button(_t("🚀 執行 AI 解析 Remarks", "🚀 Run AI Parse Remarks"), type="secondary"):
            with st.spinner(_t("AI 正在智能分析...", "AI is intelligently analyzing...")):
                updated_df = ai_parse_remarks(st.session_state.students_df)
                st.session_state.students_df = updated_df
                st.success(get_text("ai_parse_success"))
                trigger_backup_reminder()  # 重要操作提醒
                st.rerun()

        st.divider()

        # ==================== 請假登記 ====================
        st.subheader(get_text("leave_registration_subheader"))
        valid_names = [str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip()]
        st.session_state.leave_tracker_input = st.multiselect(
            _t("今日請假人員（可多選）", "Today's Leave Personnel (multi-select)"),
            options=valid_names,
            default=st.session_state.get("leave_tracker_input", [])
        )

        st.divider()

        # ==================== 智慧自動完成輸入 (Smart Autocomplete for Adding Students) ====================
        st.subheader(get_text("smart_add_student_subheader"))
        st.caption(get_text("smart_add_student_caption"))
        new_name = st.text_input(_t("姓名 (Name)", "Name (Name)"), key="new_name_input", placeholder=_t("輸入學生姓名", "Enter student name"))
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
                "needs_mentoring": False,
                "remarks": new_remark if new_remark.strip() else ""
            }])
            st.session_state.students_df = pd.concat([st.session_state.students_df, new_row], ignore_index=True)
            st.success(get_text("student_added", name=new_name.strip(), role=new_role))
            st.rerun()

        st.divider()

        # ==================== 批量管理 (Batch Leave & Fixed Duty - High Priority) ====================
        st.subheader(get_text("batch_management_subheader"))
        st.caption(get_text("batch_manage_caption"))
        valid_names = [str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip()]
        bulk_selected = st.multiselect(
            _t("選擇學生（可多選）", "Select Students (multi-select)"),
            options=valid_names,
            default=st.session_state.get("selected_students_for_bulk", []),
            key="bulk_students"
        )
        st.session_state.selected_students_for_bulk = bulk_selected

        if bulk_selected:
            bulk_type = st.radio(_t("批量類型", "Batch Type"), [_t("設定請假", "Set Leave"), _t("設定固定值班", "Set Fixed Duty"), _t("批量刪除", "Batch Delete")], horizontal=True, key="bulk_type")
            if bulk_type == _t("設定請假", "Set Leave"):
                if st.button(_t("✅ 批量請假", "✅ Batch Leave"), width="stretch", type="primary"):
                    current_leave = set(st.session_state.get("leave_tracker_input", []))
                    current_leave.update(bulk_selected)
                    st.session_state.leave_tracker_input = list(current_leave)
                    # Safe pattern: assemble first, then get_text (no f-string inside _t)
                    count = len(bulk_selected)
                    st.success(get_text("batch_leave_success", count=count))
                    st.session_state.selected_students_for_bulk = []
                    trigger_backup_reminder()
                    st.rerun()
            elif bulk_type == _t("設定固定值班", "Set Fixed Duty"):
                bulk_day = st.selectbox(_t("選擇固定日子", "Select Fixed Day"), ["NONE"] + DAYS, key="bulk_fixed_day")
                if st.button(_t("✅ 批量設定固定值班", "✅ Batch Set Fixed Duty"), width="stretch", type="primary"):
                    updated = 0
                    for name in bulk_selected:
                        mask = st.session_state.students_df["name"].str.strip() == name
                        if mask.any():
                            st.session_state.students_df.loc[mask, "fixed_general_duty"] = bulk_day
                            updated += 1
                    # Safe pattern: assemble first, then get_text
                    st.success(get_text("batch_fixed_success", count=updated, day=bulk_day))
            elif bulk_type == _t("批量刪除", "Batch Delete"):
                if st.button("🗑 " + _t("批量刪除選取學生", "Batch Delete Selected"), width="stretch", type="secondary"):
                    st.session_state.show_batch_delete_confirm = True
                if st.session_state.get("show_batch_delete_confirm", False):
                    st.error(_t("警告：刪除後，該學生的歷史排班紀錄與累計點數將無法復原，確定要刪除嗎？", "WARNING: After deletion, the student's historical duty records and cumulative points CANNOT be recovered. Are you sure?"))
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button(_t("✔ 確定刪除", "Confirm Delete"), type="primary", width="stretch", key="batch_delete_confirm"):
                            df = st.session_state.students_df
                            before = len(df)
                            df = df[~df["name"].astype(str).str.strip().isin(st.session_state.selected_students_for_bulk)]
                            st.session_state.students_df = df.reset_index(drop=True)
                            st.session_state.show_batch_delete_confirm = False
                            st.session_state.selected_students_for_bulk = []
                            st.success(get_text("batch_delete_success", count=before - len(df)))
                            st.rerun()
                    with col_cancel:
                        if st.button(_t("✖ 取消", "Cancel"), width="stretch", key="batch_delete_cancel"):
                            st.session_state.show_batch_delete_confirm = False
                            st.rerun()
                    st.session_state.selected_students_for_bulk = []
                    trigger_backup_reminder()
                    st.rerun()
            if st.button(_t("❌ 清除選擇", "❌ Clear Selection"), width="stretch"):
                st.session_state.selected_students_for_bulk = []
                st.rerun()

        st.divider()

        # ==================== Cloud 備份與還原 ====================
        st.subheader(get_text("cloud_backup_subheader"))
        st.caption(get_text("cloud_stateless_caption"))

        # 備份說明（清楚解釋靜態/動態、JSON 與 PDF 的角色） - 內容固定英文 key 概念，但顯示跟語言
        backup_explain_zh = """
**備份說明（請詳讀）：**
- **靜態資料**（姓名、年級、班別、職級、可用日子、固定值班）：主要從 GitHub 倉庫載入（例如 data/students.csv），作為長期來源。
- **動態資料**（累計點數、當週排班、手動調整負荷、請假記錄、歷史趨勢、師徒配對狀態等）：請使用下方 JSON 備份保存。
- **JSON 備份**：主要備份方式，只包含動態數據，檔案輕巧。重要操作後請立即下載。
- **PDF 備份頁**：匯出的 PDF 報告最後一頁會自動附加動態數據（標註「內部使用，分享前請刪除此頁」）。上傳 PDF 即可一鍵還原全部數據。
- **還原模式**：「完全取代」以備份覆蓋所有數據；「智能合併」保留當前學生名單結構，只合併動態欄位，適合不同名單版本的跨週還原。
- **師徒配對狀態**（「需要師徒指導」欄位）：自動包含在 JSON 備份與 PDF 備份頁中，還原時一併恢復。
- **長期保存建議**：重要的 JSON 備份，請手動上傳至 GitHub 倉庫的 `backups/` 資料夾，進行版本控制與災難恢復。
"""
        backup_explain_en = """
**Backup Instructions (Please read carefully):**
- **Static Data** (name, form, class, role, available days, fixed duty): Mainly loaded from GitHub repo (e.g. data/students.csv) as long-term source.
- **Dynamic Data** (cumulative points, weekly roster, manual adjustments, leave records, history trends, mentoring status, etc.): Use JSON backup below to save.
- **JSON Backup**: Primary backup method, contains only dynamic data, lightweight. Download immediately after important operations.
- **PDF Backup Page**: The last page of exported PDF report automatically includes dynamic data (marked "INTERNAL USE — REMOVE BEFORE DISTRIBUTION"). Upload the PDF anytime for one-click full restore.
- **Restore Modes**: "Full Replace" overwrites all data with backup; "Smart Merge" keeps current student roster structure and only merges dynamic fields — ideal for cross-week restores with different rosters.
- **Mentoring Status** ("Needs Mentoring" field): Automatically included in JSON backups and PDF backup pages, restored together with other data.
- **Long-term Storage Recommendation**: Important JSON backups, manually upload to GitHub repo's `backups/` folder for version control and disaster recovery.
"""
        st.markdown(_t(backup_explain_zh, backup_explain_en))

        # 自動備份提醒
        if st.session_state.get("backup_reminder", False):
            st.warning(get_text("backup_warning_important"))
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
                width="stretch"
            )
            clear_backup_reminder()

        # 多版本備份管理（從 session history）
        history = get_backup_history()
        if history:
            st.caption(get_text("backup_history_caption", count=len(history)))
            for i, entry in enumerate(reversed(history[-5:])):  # 顯示最近 5 個
                label = f"v{entry.get('version', i+1)} - {entry['timestamp'][:16]}"
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.caption(label)
                with col2:
                    if st.button(_t("下載", "Download"), key=f"dl_hist_{i}", help=_t(f"下載 {label}", f"Download {label}")):
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

        # ==================== 備份策略說明 ====================
        st.caption(
            _t(
                "📌 備份策略：PDF 導出時自動內嵌完整備份（動態資料）。靜態資料（姓名、年級、職級）存於 Git 版控，可透過「一鍵載入示範名冊」還原。",
                "📌 Backup strategy: PDF exports embed full dynamic backup automatically. Static data (names, forms, roles) lives in Git version control — restore via ‘Load Demo Roster’."
            )
        )
        st.divider()

        # ==================== 還原系統狀態（從 PDF 備份 — 主要方式 + 圖形化提示） ====================
        st.subheader(get_text("pdf_restore_subheader"))
        st.caption(get_text("pdf_restore_caption"))
        uploaded_pdf = st.file_uploader(
            _t("選擇包含備份數據的 PDF 檔案 (.pdf)", "Select PDF with backup data (.pdf)"),
            type=["pdf"],
            key="pdf_restore_uploader",
            help=_t("系統導出的 PDF 已自動內嵌完整備份（最後一頁）。直接上傳同一個 PDF 檔案即可還原，無需拆分頁面。", "The exported PDF embeds full backup (last page). Upload the same PDF directly to restore — no page-splitting needed.")
        )
        if uploaded_pdf:
            from roster.utils.backup import parse_backup_from_pdf
            with st.spinner(_t("正在從 PDF 解析備份數據...", "Parsing backup data from PDF...")):
                result = parse_backup_from_pdf(uploaded_pdf.getvalue())
            if result.get("success"):
                restored_count = 0
                if not result.get("students_df", pd.DataFrame()).empty:
                    st.session_state.students_df = result["students_df"]
                    restored_count += 1
                if not result.get("roster_df", pd.DataFrame()).empty:
                    st.session_state.roster_df = result["roster_df"]
                    restored_count += 1
                if not result.get("report_df", pd.DataFrame()).empty:
                    st.session_state.master_report_df = result["report_df"]
                    restored_count += 1
                # Restore additional dynamic state if available
                extra = result.get("data", {})
                if extra:
                    if extra.get("leave_tracker_input"):
                        st.session_state.leave_tracker_input = extra["leave_tracker_input"]
                    if extra.get("global_load_multiplier"):
                        st.session_state.global_load_multiplier = extra["global_load_multiplier"]
                    if extra.get("manual_weights") and extra["manual_weights"]:
                        st.session_state.manual_weights = pd.DataFrame.from_dict(extra["manual_weights"])
                st.success(
                    _t(
                        f"PDF 備份已成功還原！已恢復 {restored_count} 項資料集。",
                        f"PDF backup restored! {restored_count} dataset(s) recovered."
                    )
                )
                # Validate restored state integrity
                from roster.data.state import validate_state_integrity
                from roster.exceptions import StateIntegrityError
                try:
                    validate_state_integrity()
                except StateIntegrityError as sie:
                    st.warning(f"State validation found {len(sie.issues)} issue(s): " + "; ".join(sie.issues[:3]))
                st.rerun()
            else:
                error_msg = result.get("error", "Unknown error")
                st.warning(
                    _t(
                        f"PDF 中未找到有效的備份數據。{error_msg}",
                        f"No valid backup data found. {error_msg}"
                    )
                )

        
        # 還原區塊（含驗證 + 模式選擇）
        st.caption(get_text("upload_backup_label"))
        uploaded_backup = st.file_uploader(
            _t("選擇備份檔案 (.json)", "Select backup file (.json)"),
            type=["json"],
            key="backup_importer",
            help=_t("建議使用本系統導出的備份檔", "Recommend using backups exported by this system")
        )

        # 如果有 pending 歷史版本，顯示提示
        pending_json = st.session_state.get("pending_restore_json")
        if pending_json:
            st.info(get_text("history_version_selected_info"))
            restore_mode = st.radio(
                _t("還原模式", "Restore Mode"),
                [get_text("restore_mode_full"), get_text("restore_mode_smart")],
                index=0,
                key="restore_mode_hist",
                horizontal=True
            )
            if st.button(get_text("execute_restore_button"), type="primary", width="stretch", key="restore_hist_btn"):
                # 模擬檔案上傳
                fake_file = io.BytesIO(pending_json.encode('utf-8'))
                mode = "full" if "Full" in restore_mode else "smart_merge"
                import_system_backup(fake_file, replace_mode=mode)
                st.session_state.pop("pending_restore_json", None)
                st.rerun()
            if st.button(get_text("cancel_selection_button"), key="cancel_hist"):
                st.session_state.pop("pending_restore_json", None)
                st.rerun()

        if uploaded_backup:
            restore_mode = st.radio(
                _t("還原模式", "Restore Mode"),
                [_t("Full Replace（完全取代）", "Full Replace（Complete Replace）"), _t("Smart Merge（智慧合併）", "Smart Merge（Smart Merge）")],
                index=0,
                key="restore_mode_upload",
                horizontal=True,
                help=_t("Full Replace: 完全覆蓋目前所有資料。Smart Merge: 智慧合併學生資料，當週排班傾向使用備份。", "Full Replace: Completely overwrite all current data. Smart Merge: Smart merge student data, current week's roster tends to use the backup.")
            )
            if st.button(_t("🔄 執行還原", "🔄 Execute Restore"), type="primary", width="stretch"):
                mode = "full" if "Full" in restore_mode else "smart_merge"
                import_system_backup(uploaded_backup, replace_mode=mode)

        # 顯示上次備份時間（如果有）
        last_backup = st.session_state.get("last_backup_time")
        if last_backup:
            st.caption(f"{_t('上次成功備份時間', 'Last successful backup time')}: {last_backup[:16]}")

        # 長期保存引導（溫和建議）
        st.caption(get_text("long_term_storage_tip"))


def render_control_buttons():
    """主畫面控制按鈕 - 清晰、突出主要行動"""
    closure_options = [f"{d} - {room}" for d in DAYS for room in ["Room302", "Room303", "Room202"]
                       if not (room == "Room202" and d in ["TUESDAY", "FRIDAY"])]
    selected_closures = st.multiselect(
        get_text("special_unavailable_label"),
        options=closure_options,
        key="special_closures",
        help=get_text("special_unavailable_help")
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button(_t("🚀 一鍵生成公平值班表", "🚀 Generate Fair Roster"), type="primary", width="stretch"):
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
                # Safe pattern: assemble first then get_text (key handles the full text + advice)
                st.success(get_text("roster_complete_success", multiplier=global_multiplier, version=version_num))

                # Auto update semester hours (1 hour per duty slot)
                for name in st.session_state.students_df["name"].dropna().astype(str).str.strip():
                    count = (st.session_state.roster_df == name).sum().sum()
                    hours = count * 1.0
                    current_hours = st.session_state.get("semester_hours", {}).get(name, 0)
                    st.session_state.semester_hours[name] = current_hours + hours

                # 自動備份提醒
                trigger_backup_reminder()
                # Signal app.py to pre-generate PDFs
                st.session_state._pdf_needs_generation = True

    with col2:
        if st.button(_t("🗑️ 清空", "🗑️ Clear"), type="secondary", width="stretch"):
            st.session_state.show_clear_confirm = True

    if st.session_state.get("show_clear_confirm", False):
        st.error(get_text("clear_roster_confirm_error"))
        c1, c2 = st.columns(2)
        if c1.button(_t("💥 確定清空", "💥 Confirm Clear")):
            from roster.data.state import reset_roster_related_state
            reset_roster_related_state()
            st.session_state.roster_df = pd.DataFrame(index=get_roster_rows(), columns=DAYS).fillna("")
            st.session_state.show_clear_confirm = False
            st.rerun()
        if c2.button(_t("❌ 取消", "❌ Cancel")):
            st.session_state.show_clear_confirm = False
            st.rerun()

    return selected_closures




def render_pairing_effectiveness_card():
    """Display a 3-column metric card showing mentoring pairing effectiveness.

    Reuses annotate_mentoring_pairs() to count pairs formed this week against
    the theoretical maximum of 8 possible 2-slot room-pairs (Room 303: 5 days
    + Room 202: 3 open days).

    Intended for the fairness/dashboard sidebar in app.py.
    Requires st.session_state.roster_df and st.session_state.students_df.
    """
    st.caption(
        _t("??????", "Mentoring Pairing Effectiveness")
    )
    mentoring_pairs = annotate_mentoring_pairs(
        st.session_state.roster_df, st.session_state.students_df
    )
    pair_count = len(mentoring_pairs)
    possible_pairs = compute_possible_mentoring_pairs(st.session_state.roster_df)
    pair_rate = (pair_count / possible_pairs * 100) if possible_pairs > 0 else 0

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric(
            _t("🤝 師徒配對", "🤝 Mentoring Pairs"),
            f"{pair_count} / {possible_pairs}",
            delta=None,
            help=_t(
                "本週形成的師徒配對數目（Room 303 及 Room 202 開放日）",
                "Mentoring pairs formed this week in Room 303 and Room 202 (open days)",
            ),
        )
    with col_b:
        st.metric(
            _t("📊 配對成功率", "📊 Pairing Rate"),
            f"{pair_rate:.0f}%",
            delta=None,
            help=_t(
                "配對數目佔可行雙人房間的比例（共8個可行配對位）",
                "Pairing count as percentage of possible 2-slot rooms (8 possible)",
            ),
        )
    with col_c:
        if pair_rate >= 50:
            pair_label = _t("優秀", "Excellent")
        elif pair_rate >= 25:
            pair_label = _t("良好", "Good")
        else:
            pair_label = _t("尚可", "Fair")
        st.metric(
            _t("🏷️ 評估", "🏷️ Rating"),
            pair_label,
            delta=None,
            help=_t(
                "配對率 ≥50% 優秀，≥25% 良好，<25% 尚可",
                "≥50% Excellent, ≥25% Good, <25% Fair",
            ),
        )


def render_mentee_progress_tracker():
    """Display a collapsible mentee progress table with baseline snapshot support.

    Shows all students currently flagged as needing mentoring (history_weight ≤ 2
    or needs_mentoring=True) with current weight and trend indicators. Users can
    save a baseline snapshot, generate a new roster, then return to compare.

    Trend indicators:
        ⬇ Improving  — weight decreased since baseline
        ➡ Stable     — weight unchanged
        ⬆ Needs attention — weight increased
        － No baseline — no snapshot saved yet

    Requires st.session_state.students_df.
    Uses st.session_state.mentee_baseline and .mentee_baseline_date for snapshots.
    """
    with st.expander(
        _t("📈 學徒進度追蹤", "📈 Mentee Progress Tracker"), expanded=False
    ):
        st.caption(
            _t(
                "追蹤被標記為「需要師徒指導」的風紀之點數變化",
                "Track weight changes for prefects flagged as needing mentoring",
            )
        )

        students = st.session_state.students_df

        # --- Defensive: handle missing needs_mentoring column ---
        has_needs_col = "needs_mentoring" in students.columns
        if not has_needs_col:
            needs_series = pd.Series([False] * len(students), index=students.index)
        else:
            needs_series = students["needs_mentoring"].fillna(False).astype(bool)

        # --- Identify current mentees ---
        mentee_mask = (students["history_weight"] <= 2.0) | needs_series
        mentees = students[mentee_mask].copy()

        if mentees.empty:
            st.info(
                _t("目前沒有需要師徒指導的風紀。", "No prefects currently need mentoring.")
            )
            return

        # --- Baseline management ---
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button(
                _t("📸 儲存當前為基準", "📸 Save Current as Baseline"),
                key="save_mentee_baseline",
            ):
                st.session_state.mentee_baseline = dict(
                    zip(
                        mentees["name"].astype(str).str.strip(),
                        mentees["history_weight"].astype(float),
                    )
                )
                st.session_state.mentee_baseline_date = (
                    datetime.date.today().isoformat()
                )
                st.success(_t("基準已儲存！", "Baseline saved!"))
        with col_btn2:
            if st.button(
                _t("🗑️ 清除基準", "🗑️ Clear Baseline"),
                key="clear_mentee_baseline",
            ):
                st.session_state.pop("mentee_baseline", None)
                st.session_state.pop("mentee_baseline_date", None)
                st.info(_t("基準已清除。", "Baseline cleared."))

        # --- Build display table ---
        baseline = st.session_state.get("mentee_baseline", {})
        baseline_date = st.session_state.get("mentee_baseline_date", None)
        rows = []
        for _, row in mentees.iterrows():
            name = str(row["name"]).strip()
            hw = float(row["history_weight"])
            prev = baseline.get(name, None)
            if prev is not None and baseline_date:
                diff = hw - prev
                if diff < 0:
                    trend = "⬇ " + _t("進步中", "Improving")
                elif diff == 0:
                    trend = "➡ " + _t("持平", "Stable")
                else:
                    trend = "⬆ " + _t("需關註", "Needs attention")
            else:
                diff = None
                trend = "－ " + _t("無基準", "No baseline")
            rows.append(
                {
                    _t("姓名", "Name"): name,
                    _t("年級", "Form"): row.get("form", ""),
                    _t("當前點數", "Current Weight"): f"{hw:.1f}",
                    _t("變化", "Change"): (
                        f"{diff:+.1f}" if diff is not None else "－"
                    ),
                    _t("趨勢", "Trend"): trend,
                }
            )
        progress_df = pd.DataFrame(rows)
        st.dataframe(progress_df, width="stretch", hide_index=True)

        if baseline_date:
            st.caption(
                _t(f"基準日期：{baseline_date}", f"Baseline date: {baseline_date}")
            )
        st.caption(
            _t(
                "提示：先按「儲存當前為基準」，生成新值班表後再回來查看點數變化。",
                "Tip: Save a baseline first, then generate a new roster and return to see weight changes.",
            )
        )