# app.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
主應用程式入口 - Streamlit Cloud 最終部署版

作者：首席導學風紀 26-27 LI Chuangjie Jacky
版本：v2.4 Final（全局負荷滑桿、師徒配對、智能替補、神聖金句、深色模式、PDF/JSON雙重備份）
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
import re as _re

# ====================== 模組導入 (direct roster/ per project-structure-advisor, thin shims for compat only) ======================
# Note: All UI text in Chinese; exports forced to professional English with Chinese student names preserved.
# Theme and language toggles in sidebar.
from roster.config import (
    DAYS, ROWS_ROSTER, VERSION, APP_TITLE, PROJECT_FULL_NAME, PROJECT_FULL_NAME_EN,
    NASA_COLORS, get_role_style, DEFAULT_GLOBAL_LOAD_MULTIPLIER, get_weight,
)

# Centralized display-layer language & messages (new architecture - single source of _t)
from roster.ui.i18n import _t, get_text
from roster.data import (
    get_demo_dataframe, get_sample_format_dataframe,
    initialize_session_state
)
from roster.data.models import get_ui_report_df, get_export_report_df, reindex_roster_df, create_empty_roster_df
from roster.data.state import get_state, set_state, reset_roster_related_state
from roster.ai import ai_parse_remarks
from roster.core import (
    generate_roster, validate_and_compute, recommend_substitutes,
    apply_post_publication_leave_adjustment,
    annotate_mentoring_pairs
)
from roster.utils import (
    generate_pdf, generate_service_certificate, export_system_backup, import_system_backup,
    process_roster_import, smart_process_roster_import,
    trigger_backup_reminder, clear_backup_reminder
)
from roster.ui.components import (
    render_sidebar, show_daily_verse, render_control_buttons,
    render_pairing_effectiveness_card, render_mentee_progress_tracker,
    render_system_architecture_diagram,
)
from roster.ui.theme import apply_theme  # centralized dark/light + base (sole source after de-dupe)

# (User manual centralized in roster/ui/messages.py for bilingual support)

def global_multiplier_slider() -> float:
    """全局負荷調節滑桿（主畫面即時可調）"""
    st.subheader(get_text("global_load_slider_subheader"))
    st.caption(get_text("global_load_slider_caption"))
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

    # ====================== Centralized Theme (base + dark/light overrides) ======================
    # Sole source is now roster/ui/theme.py (get_base_css + get_dark_css/get_light_css + apply_theme).
    # Early call ensures verse enclosure (.verse-card/.verse-inner), gold #D4AF37 accents,
    # alerts, kpi, and all mode contrast rules are present before any UI elements (verse, subheaders,
    # data_editor, kpi-cards, captions, placeholders). Sidebar re-applies after toggle for reactivity.
    # Verse structure (HTML enclosure + padding/borders/shadows) lives in show_daily_verse + theme CSS.
    apply_theme()

    # ====================== 主畫面 ======================
    render_sidebar()

    # 語言模式同步：中文介面優先，英文介面時使用 EN 標題（主畫面仍以中文為主，匯出專業英文）
    ui_lang = st.session_state.get("ui_language", "zh")
    main_title = PROJECT_FULL_NAME_EN if ui_lang == "en" else PROJECT_FULL_NAME
    main_sub = "Study Prefect (導學風紀) Duty Platform | " + VERSION if ui_lang == "en" else f"導學風紀當值平台 | {VERSION}"
    st.markdown(f'<p class="main-title">{main_title}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="main-subtitle">{main_sub}</p>', unsafe_allow_html=True)

    # Enhanced Daily Verse with optional bilingual (evangelical-theology + streamlit-best-practices)
    show_daily_verse()

    with st.expander(_t("📖 點此展開完整使用說明書（v2.4 Final）", "📖 Click to expand full user manual (v2.4 Final)"), expanded=False):
        st.markdown(get_text("help_text_full"))

    st.write("---")

    # ====================== 全局負荷滑桿 ======================
    # (global load slider title inside the function can be further translated if needed)

    st.markdown(f'<p style="font-size:13px; font-weight:600; color:#0F766E; margin:8px 0 0 0;">{_t("每日工作流程", "Daily Workflow")}</p>', unsafe_allow_html=True)
    st.write("---")
    selected_closures = render_control_buttons()

    # 角色名稱統一正規化（支援中英文，由 config 中的 ROLE_MAP 集中處理）
    from roster.config import normalize_students_role_column
    normalize_students_role_column(st.session_state.students_df)

    # ====================== 驗證與計算 ======================
    audit_results = validate_and_compute(
        st.session_state.roster_df,
        st.session_state.students_df,
        st.session_state.leave_tracker_input,
        st.session_state.manual_weights
    )
    st.session_state.master_report_df = audit_results["report_df"]

    # ====================== PDF 自動預生成 (only after Smart Compute) ======================
    if st.session_state.pop("_pdf_needs_generation", False):
        if st.session_state.roster_df is not None and not st.session_state.roster_df.empty:
            with st.spinner(_t("正在準備專業 PDF 報告，請稍候…", "Preparing professional PDF reports, please wait…")):
                try:
                    _logo_b64 = base64.b64encode(st.session_state.logo_data).decode() if st.session_state.get("logo_data") else None
                    st.session_state.pdf_cache_zh = generate_pdf(
                        st.session_state.roster_df,
                        get_ui_report_df(st.session_state.master_report_df),
                        _logo_b64, lang="zh", students_df=st.session_state.students_df
                    )
                    st.session_state.pdf_cache_en = generate_pdf(
                        st.session_state.roster_df,
                        get_export_report_df(st.session_state.master_report_df),
                        _logo_b64, lang="en", students_df=st.session_state.students_df
                    )
                except Exception as _e:
                    st.warning(f"PDF pre-generation failed: {_e}")

    # ====================== 警告顯示 ======================
    if audit_results["typo"][0]:
        st.markdown('<div class="danger-alert"><b>' + _t("⚠️ 數據不符警告：", "⚠️ Data Mismatch Warning:") + '</b><br>' + '<br>'.join(audit_results["typo"][1]) + '</div>', unsafe_allow_html=True)
    if audit_results["duplicate"][0]:
        st.markdown('<div class="danger-alert"><b>' + _t("⚠️ 重複排班警告：", "⚠️ Duplicate Duty Warning:") + '</b><br>' + '<br>'.join(audit_results["duplicate"][1]) + '</div>', unsafe_allow_html=True)
    if audit_results["leave_conflict"][0]:
        st.markdown('<div class="danger-alert"><b>' + _t("🛑 請假衝突：", "🛑 Leave Conflict:") + '</b><br>' + '<br>'.join(audit_results["leave_conflict"][1]) + '</div>', unsafe_allow_html=True)
        if st.button(_t("🩹 一鍵清除請假同學", "🩹 One-Click Clear Leave Students"), type="primary"):
            for d in DAYS:
                for r in ROWS_ROSTER:
                    if str(st.session_state.roster_df.at[r, d]).strip() in st.session_state.leave_tracker_input:
                        st.session_state.roster_df.at[r, d] = ""
            st.success(get_text("leave_cleared_success"))
            st.rerun()
    elif audit_results["vacuum"][0]:
        st.markdown('<div class="warning-alert"><b>' + _t("💡 空缺提示：", "💡 Vacancy Notice:") + '</b><br>' + '<br>'.join(audit_results["vacuum"][1]) + '</div>', unsafe_allow_html=True)

    # ====================== 值班表 ======================
    st.write("---")
        # Empty state: show helpful message when no roster has been generated yet
    if st.session_state.roster_df is None or st.session_state.roster_df.empty:
        st.info(_t(
            "📋 尚未生成值班表。請在側邊欄設定請假人員後，點擊「🚀 一鍵生成公平值班表」開始。",
            "📋 No roster generated yet. Set leave personnel in the sidebar, then click \"🚀 Generate Fair Roster\" to begin."
        ))
    else:
        st.subheader(get_text("this_week_roster_subheader"))
        if st.session_state.get("roster_versions") and len(st.session_state.roster_versions) > 0:
            _last_ts = st.session_state.roster_versions[-1].get("timestamp", "")
            if _last_ts:
                _zh_ts = f"🕒 上次生成：{_last_ts}"
                _en_ts = f"🕒 Last generated: {_last_ts}"
                st.caption(_zh_ts if st.session_state.get("ui_language", "zh") == "zh" else _en_ts)
    tab_view, tab_edit = st.tabs([_t("📅 視覺公告版", "📅 Visual Board"), _t("✏️ 手動修改版", "✏️ Manual Edit Mode")])

    # Compute mentoring pairs for visual indicators
    _mentoring_pairs = annotate_mentoring_pairs(st.session_state.roster_df, st.session_state.students_df)

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
            roster_search = st.text_input(_t("🔍 快速搜尋值班表 (Quick Search by role)", "🔍 Quick Search Roster (Quick Search by role)"), value=st.session_state.get("roster_search", ""), key="roster_search_input", placeholder=_t("輸入職位或房間關鍵字", "Enter position or room keyword"))
            st.session_state.roster_search = roster_search
            roster_display = st.session_state.roster_df.copy()
            if roster_search:
                mask = roster_display.index.astype(str).str.contains(roster_search, case=False, na=False)
                roster_display = roster_display[mask]
                # Safe: use get_text for dynamic count (assemble not needed here)
                st.caption(f"{get_text('showing_prefix')} {len(roster_display)} {get_text('rows_label')}")

            def _cell_style(val, role, day):
                base = apply_cell_style(val, role, day)
                _parent = role.rsplit(" - ", 1)[0] if " - " in role else role
                _pk = _parent + "_" + day
                if _pk in _mentoring_pairs and str(val).strip():
                    base += " border-left:4px solid #0F766E; background-color:rgba(15,118,110,0.08) !important;"

                return base
            styled = roster_display.style.apply(
                lambda row: [_cell_style(val, row.name, col) for col, val in row.items()], axis=1
            )
            st.dataframe(styled, height=380)
            # Dynamic mentoring pair badge with live count
            _pair_count = len(_mentoring_pairs)
            _legend_parts = ['<div style="display:flex; gap:8px; flex-wrap:wrap; font-size:12px; margin:4px 0;">']
            if _pair_count > 0:
                _legend_parts.append(
                    '<span style="background:#0F766E; color:white; padding:2px 10px; border-radius:10px;">'
                    + chr(0x1f91d) + ' ' + _t('師徒配對', 'Mentoring Pair')
                    + f'：{_pair_count}對'
                    + '</span>'
                )
            _legend_parts.append('<span style="background:#0F766E; color:white; padding:2px 10px; border-radius:10px;">🆕 新加入</span>')
            _legend_parts.append('<span style="background:#F59E0B; color:white; padding:2px 10px; border-radius:10px;">👤 需要師徒指導</span>')
            _legend_parts.append('<span style="background:#7C3AED; color:white; padding:2px 10px; border-radius:10px;">✅ 已指定師徒</span>')
            _legend_parts.append('<span style="background:#6B7280; color:white; padding:2px 10px; border-radius:10px;">一般</span>')
            _legend_parts.append('</div>')
            st.markdown(''.join(_legend_parts), unsafe_allow_html=True)
            if _pair_count > 0:
                _zh_cap = f'🟦 本週共有 {_pair_count} 對師徒配對（藍綠色左邊框標記）。'
                _en_cap = f'🟦 {_pair_count} mentoring pair' + ('s' if _pair_count != 1 else '') + ' detected (teal left border).'
                st.caption(_zh_cap if st.session_state.get('ui_language', 'zh') == 'zh' else _en_cap)

    with tab_edit:
        st.markdown('<p class="edit-hint">' + _t("💡 直接修改人名或打 X 鎖定", "💡 Directly edit name or type X to lock") + "</p>", unsafe_allow_html=True)
        # Show mentoring pair summary in edit tab when pairs exist
        if _mentoring_pairs:
            with st.expander(
                _t(
                    f"🤝 師徒配對詳情（{len(_mentoring_pairs)}對）",
                    f"🤝 Mentoring Pairs ({len(_mentoring_pairs)} pairs)"
                ),
                expanded=False
            ):
                _pair_rows = []
                for _pk, _info in sorted(_mentoring_pairs.items()):
                    _room = _pk.rsplit("_", 1)[0]
                    _day = _pk.rsplit("_", 1)[1]
                    _mentor = _info.get("mentor", "")
                    _mentee = _info.get("mentee", "")
                    _pair_rows.append({
                        _t("房間", "Room"): _room,
                        _t("日期", "Day"): _day,
                        _t("師傅 (Mentor)", "Mentor"): _mentor,
                        _t("學徒 (Mentee)", "Mentee"): _mentee,
                    })
                if _pair_rows:
                    st.dataframe(
                        pd.DataFrame(_pair_rows),
                        width="stretch",
                        hide_index=True
                    )
                    st.caption(
                        _t(
                            "💡 師徒配對加分（-2.0）遠小於 AHP 崗位加成（-8.0），不會影響領導職位優先。手動修改值班表後請留意是否影響配對。",
                            "💡 Mentoring bonus (-2.0) is much smaller than AHP slot bonus (-8.0), preserving leadership priority. Manual edits may affect pairing status."
                        )
                    )
        edited_roster = st.data_editor(
            st.session_state.roster_df,
            width="stretch",
            key="main_roster_editor_widget"
        )
        if not edited_roster.equals(st.session_state.roster_df):
            set_state("roster_df", edited_roster)
            trigger_backup_reminder()  # 手動修改值班表後提醒備份
            st.rerun()

    # ====================== 手動調整負荷 ======================
    st.write("---")
    st.write("---")
    st.subheader(get_text("post_duty_leave_subheader"))
    st.caption(get_text("post_duty_leave_caption"))
    st.info(get_text("post_duty_leave_info"))
    with st.form("leave_adjust_form", clear_on_submit=True):
        col_d, col_r = st.columns(2)
        with col_d:
            adj_day = st.selectbox(_t("選擇日期", "Select Date"), DAYS, key="adj_day")
        with col_r:
            assigned_roles = [
                r for r in ROWS_ROSTER
                if str(st.session_state.roster_df.at[r, adj_day]).strip() not in ["", "X", "⬜", "請假撤銷"]
            ]
            adj_role = st.selectbox(_t("選擇崗位", "Select Position"), assigned_roles if assigned_roles else [""], key="adj_role")

        current_person = ""
        if adj_role and adj_role in st.session_state.roster_df.index:
            current_person = str(st.session_state.roster_df.at[adj_role, adj_day]).strip()
            if current_person and current_person not in ["X", "⬜", "請假撤銷"]:
                st.info(f"{_t('目前值班人員：**{current_person}**（將被撤銷點數）', 'Currently scheduled person: **{current_person}** (points will be revoked)').format(current_person=current_person)}")

        has_replacement = st.checkbox(_t("有替補人員（推薦）", "Has substitute (recommended)"), value=False)
        replacement = None
        if has_replacement and current_person:
            valid_names = [
                str(n).strip() for n in st.session_state.students_df["name"].dropna()
                if str(n).strip() and str(n).strip() != current_person
            ]
            replacement = st.selectbox(_t("選擇替補人員", "Select Substitute"), valid_names, key="replacement_select")

        submitted = st.form_submit_button(_t("🚀 執行請假調整 / 撤銷點數", "🚀 Execute Leave Adjustment / Revoke Points"), type="primary", width="stretch")

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
            # Invalidate PDF cache so it regenerates on next download
            set_state("pdf_cache_zh", None)
            set_state("pdf_cache_en", None)

            # Safe assembly: build parts first using get_text, then combine
            revoke = get_text("revoke_points", current_person=current_person, weight=weight)
            if has_replacement and replacement:
                handover = get_text("handover_to", replacement=replacement)
                action_msg = revoke + handover
            else:
                no_one = get_text("no_one_for_slot")
                action_msg = revoke + no_one

            st.success(get_text("adjustment_complete", action_msg=action_msg))

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
            st.success(get_text("important_backup_reminder"))
            st.rerun()

    # ====================== 快速導出 (語言跟隨) ======================
    ui_lang = st.session_state.get("ui_language", "zh")
    st.write("---")
    st.subheader(get_text("export_section_subheader"))
    st.caption("點擊按鈕直接下載PDF報告：按鈕決定報告標題與欄位語言（中文或專業英文），學生姓名永遠保留中文。UI語言切換與此獨立。")
    st.caption(
        _t("提示：PDF 渲染約需數秒，請稍候。重複下載將使用快取，速度更快。",
           "Tip: PDF rendering takes a few seconds. Repeat downloads use cache for speed.")
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        # 明確的 PDF 語言控制：兩個按鈕，分別輸出中文/英文 PDF
        # Buttons directly trigger generation + download (using st.download_button for reliable one-click behavior).
        # lang param selects report titles/headers language; student names/roles always Chinese (unchanged rule).
        logo_b64 = base64.b64encode(st.session_state.logo_data).decode() if st.session_state.get("logo_data") else None
        _roster_ok = st.session_state.roster_df is not None and not st.session_state.roster_df.empty
        _pdf_zh_data = get_state("pdf_cache_zh")
        if _pdf_zh_data is None and _roster_ok:
            with st.spinner(_t("正在渲染專業中文 PDF 報告，請稍候…", "Rendering professional Chinese PDF report, please wait…")):
                _pdf_zh_data = generate_pdf(st.session_state.roster_df, get_ui_report_df(st.session_state.master_report_df), logo_b64, lang="zh", students_df=st.session_state.students_df)
                st.session_state.pdf_cache_zh = _pdf_zh_data
        if _pdf_zh_data is None:
            _pdf_zh_data = b""  # Empty bytes placeholder so download button exists but is harmless
        st.download_button(
            _t("📄 匯出中文 PDF", "📄 Export Chinese PDF (report titles/headers in Chinese)"),
            data=_pdf_zh_data,
            file_name=f"SYSS_Roster_{datetime.date.today().strftime('%Y%m%d')}_中文.pdf",
            mime="application/pdf",
            width="stretch",
            key="dl_pdf_cn_direct"
        )
        _pdf_en_data = get_state("pdf_cache_en")
        if _pdf_en_data is None and _roster_ok:
            with st.spinner(_t("正在渲染專業英文 PDF 報告，請稍候…", "Rendering professional English PDF report, please wait…")):
                _pdf_en_data = generate_pdf(st.session_state.roster_df, get_export_report_df(st.session_state.master_report_df), logo_b64, lang="en", students_df=st.session_state.students_df)
                st.session_state.pdf_cache_en = _pdf_en_data
        if _pdf_en_data is None:
            _pdf_en_data = b""  # Empty bytes placeholder
        st.download_button(
            _t("📄 Export English PDF", "📄 Export English PDF (report titles/headers in English)"),
            data=_pdf_en_data,
            file_name=f"SYSS_Roster_{datetime.date.today().strftime('%Y%m%d')}_EN.pdf",
            mime="application/pdf",
            width="stretch",
            key="dl_pdf_en_direct"
        )

    with col2:
        if not st.session_state.get("excel_md_ready"):
            if st.button(_t("生成 Excel / Markdown", "Generate Excel / Markdown"), width="stretch"):
                st.session_state.excel_md_ready = True
                st.rerun()
        else:
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
                    "Report Type": ["Professional English Export - Sing Yin Study Prefect (導學風紀)"],
                    "Generated": [datetime.date.today().strftime('%Y-%m-%d')],
                    "Core Principle": ["Lower load = Higher priority (Fairness & Servant Leadership)"],
                    "Compliance": ["AGENTS.md §1 rules fully applied (AHP, Room 302/303, fairness)"]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Executive Summary (EN)', index=False)
            excel_label = _t("📊 下載 Excel（跟隨語言 + 圖表 + 條件格式）", "📊 Download Excel (Follow Language + Charts + Formatting)")
            st.download_button(
                excel_label,
                output_excel.getvalue(),
                f"SYSS_Roster_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
                width="stretch"
            )

    with col3:
        if st.session_state.get("excel_md_ready"):
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
                dl_label = _t("📝 下載 Markdown（跟隨語言）", "📝 Download Markdown (Follow Language)")
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
                width="stretch"
            )

    ui_lang = st.session_state.get("ui_language", "zh")
    st.subheader(get_text("manual_load_adjust_subheader"))
    st.caption(get_text("manual_load_adjust_caption"))

    manual_col = st.data_editor(
        st.session_state.manual_weights,
            width="stretch",
        key="manual_weight_editor"
    )
    if not manual_col.equals(st.session_state.manual_weights):
        st.session_state.manual_weights = manual_col.astype(float).fillna(0.0)
        trigger_backup_reminder()  # 自動備份提醒
        # Safe pattern: use get_text (key already has the full text with backup advice)
        st.success(get_text("manual_adjust_saved"))
        st.rerun()

    # ====================== 累計審計表 ======================
    st.write("---")
    st.subheader(get_text("cumulative_audit_subheader"))
    if not st.session_state.master_report_df.empty:
        # UI 顯示使用中文欄位（保持介面中文），使用 models helper 區分顯示/匯出
        display_report = get_ui_report_df(st.session_state.master_report_df)
        st.dataframe(display_report, width="stretch", hide_index=True)
    else:
        st.info(get_text("audit_table_info"))

    # ====================== 管理視角 Dashboard (首席導學風紀 / AHP 專用 - educational leadership features) ======================
    # Enhanced with more KPIs, AHP insights, and servant-leadership framing (evangelical-theology + sing-yin-study-prefect-duty-roster)
    if not st.session_state.master_report_df.empty:
        st.write("---")
        st.subheader(get_text("management_dashboard_title"))
        st.caption(_t("公平性 KPI、AHP 洞察、快速統計，體現僕人領袖精神、公平與責任", "Fairness KPIs, AHP insights, quick stats, embodying servant leadership spirit, fairness and responsibility"))

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
            st.markdown(f'<div class="kpi-card"><div class="label">{_t("總領袖生數", "Total Prefects")}</div><div class="value">{total_students}</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="kpi-card"><div class="label">{_t("平均累計負荷", "Average Cumulative Load")}</div><div class="value">{avg_load:.1f} {_t("點", "pts")}</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="kpi-card"><div class="label">{_t("公平差距 (Max-Min)", "Fairness Gap (Max-Min)")}</div><div class="value">{fairness_gap:.1f} {_t("點", "pts")}</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="kpi-card"><div class="label">{_t("負荷標準差", "Load Std Dev")}</div><div class="value">{load_std:.1f}</div></div>', unsafe_allow_html=True)
        with col5:
            st.markdown(f'<div class="kpi-card"><div class="label">{_t("最低 / 最高", "Min / Max")}</div><div class="value">{min_load:.1f} / {max_load:.1f}</div></div>', unsafe_allow_html=True)

        # AHP Insights & Leadership Summary
        ahp_names = set(st.session_state.students_df[st.session_state.students_df["role"].isin(["Assistant 首席導學風紀", "助理首席導學風紀", "AHP"])]["name"].astype(str).str.strip())
        if ahp_names and total_students > 0:
            ahp_loads = loads[report["Student Name"].isin(ahp_names)] if "Student Name" in report.columns else pd.Series()
            ahp_avg = ahp_loads.mean() if len(ahp_loads) > 0 else 0
            ahp_count = len(ahp_loads)
            # Safe assembly per messages.py / AGENTS.md: lookup first, assemble after (no inline complex f+format)
            insight_title = get_text("insight_title")
            load_phrase = get_text("ahp_avg_load_phrase")
            msg = (
                f"👑 {insight_title}：{ahp_count} {load_phrase} {ahp_avg:.1f} {_t('點', 'pts')}。"
                + _t("建議：確保「Assist. in charge」職責公平分配，體現僕人領袖榜樣與責任。", "Suggestion: Ensure fair distribution of 'Assist. in charge' duties, embodying servant leadership example and responsibility.")
            )
            st.info(msg)

        # Simple fairness note
        if fairness_gap > 5:
            st.warning(get_text("fairness_gap_warning"))
        else:
            st.success(get_text("overall_fairness_success"))

        # ---- Mentoring Dashboard (Phase D) ----
        render_pairing_effectiveness_card()
        render_mentee_progress_tracker()

        # Historical Trends & Fairness (High Priority)
        st.write("---")
        st.subheader(get_text("history_fairness_subheader"))
        if st.button(_t("💾 儲存本週負荷數據 (Save Current Week for Trends)", "💾 Save This Week's Load Data (Save Current Week for Trends)")):
            current_loads = {}
            for _, row in report.iterrows():
                name = str(row.get("Student Name", row.get("學生姓名", ""))).strip()
                load = float(row.get("Cumulative Weighted Load (points)", 0))
                if name:
                    current_loads[name] = load
            week_num = len(st.session_state.history_loads) + 1
            st.session_state.history_loads.append({"week": week_num, "loads": current_loads})
            st.success(get_text("saved_trend_week", week_num=week_num))

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
                                title=_t("累計負荷歷史趨勢", "Cumulative Load History Trend"),
                                labels={"value": _t("累計加權負荷 (點)", "Cumulative Weighted Load (pts)"), "variable": _t("學生", "Student")})
            st.plotly_chart(fig_trend, width="stretch")

            # Latest fairness index (std dev)
            latest = st.session_state.history_loads[-1]["loads"]
            latest_loads = list(latest.values())
            fairness_index = float(pd.Series(latest_loads).std()) if len(latest_loads) > 1 else 0.0
            st.metric(_t("公平指數 (Fairness Index = 標準差)", "Fairness Index (Fairness Index = Std Dev)"), f"{fairness_index:.2f} {_t('點', 'pts')}", help=_t("越低越公平。0 = 完美平均。", "Lower is fairer. 0 = perfect average."))

            # Most Neglected Students (lowest load)
            if latest:
                sorted_neg = sorted(latest.items(), key=lambda x: x[1])[:3]
                neglected_names = [n for n, l in sorted_neg]
                neglected_str = ', '.join(neglected_names)
                st.warning(get_text("most_neglected", names=neglected_str))
        else:
            st.info(get_text("history_trend_prompt"))

        # Advanced Summary Report Generation (High Priority)
        st.write("---")
        st.subheader(get_text("summary_report_subheader"))
        st.caption(get_text("report_generation_caption"))

        if st.button(get_text("generate_summary_button"), type="primary"):
            # Use export report for consistent English data
            export_report = get_export_report_df(st.session_state.master_report_df)
            display_report = get_ui_report_df(st.session_state.master_report_df)

            # Chinese preview (UI) - using display data
            st.markdown("### " + get_text("chinese_preview_header"))
            neg_str = ', '.join(neglected_names) if 'neglected_names' in locals() and neglected_names else '無'
            # Safe display labels for descriptive AHP data (role context kept per plan distinction;
            # only the strong branded headings were neutralized elsewhere)
            contrib_header = get_text("report_contribution_label")
            if 'ahp_avg' in locals() and 'ahp_count' in locals():
                ahp_load_line = get_text("ahp_load_detail_template", avg=ahp_avg, count=ahp_count)
            else:
                ahp_load_line = get_text("average_load_label") + "：— (無 AHP 資料)"
            summary_zh = f"""
**本週總結報告**

- 總領袖生：{total_students}
- 平均負荷：{avg_load:.1f} 點
- 公平指數 (標準差)：{fairness_gap:.1f} 點
- {ahp_load_line}

**表現者**
- 負荷最低 (最需關註)：{neg_str}
- 最高負荷：{max_load:.1f} 點

**{contrib_header}**
AHP 平均負荷顯示領導責任分擔良好。

**僕人領袖註記**
「誰願為首，就必作眾人的僕人。」— 馬可福音 10:44
本系統強調公平與服事，幫助領袖生學習責任與謙卑。
"""
            st.markdown(summary_zh)

            # Professional English export version - using export data
            st.markdown("### " + get_text("english_export_header"))
            export_neg = neg_str
            # English descriptive AHP labels via context-keeping keys (AHP retained for data clarity, per distinction)
            contrib_header_en = get_text("report_contribution_label")
            if 'ahp_avg' in locals() and 'ahp_count' in locals():
                ahp_load_line_en = get_text("ahp_load_detail_template", avg=ahp_avg, count=ahp_count)
            else:
                ahp_load_line_en = get_text("average_load_label") + ": — (no AHP data)"
            summary_en = f"""
# Sing Yin Secondary School Study Prefect Duty Roster - Summary Report

**Report Date:** {datetime.date.today().strftime('%Y-%m-%d')}
**Total Prefects:** {total_students}
**Average Cumulative Load:** {avg_load:.1f} points
**Fairness Index (Std Dev):** {fairness_gap:.1f} points
{ahp_load_line_en}

**Top/Bottom Performers**
- Most Neglected (Lowest Load): {export_neg}
- Highest Load: {max_load:.1f} points

**{contrib_header_en}**
AHPs show balanced or lower average load, demonstrating responsible leadership allocation.

**Servant Leadership Notes**
"Whoever wants to become great among you must be your servant." — Mark 10:43
This system promotes fairness, equity, and a culture of service, helping prefects learn responsibility and humility in accordance with school values and biblical principles.

**Data Summary (English Columns)**
{export_report.to_string(index=False) if not export_report.empty else "No data"}
"""
            st.text_area("English Summary (copy or download for external use)", summary_en, height=250)
            st.download_button(
                get_text("download_summary_txt_button"),
                summary_en,
                f"SYSS_Summary_Report_{datetime.date.today().strftime('%Y%m%d')}.txt",
                width="stretch"
            )
            st.caption(get_text("report_backup_reminder_caption"))
            # Optional: Quick English PDF summary using existing PDF engine (reusing for professionalism)
            if st.button(get_text("extra_pdf_summary_button"), key="summary_pdf"):
                # Reuse PDF but with summary content - simplified for now
                st.info(get_text("export_pdf_best_format"))

    # Roster Version History - Improved (better comparison, clearer display, easier loading)
    with st.expander(get_text("roster_version_history_expander")):
        versions = st.session_state.get("roster_versions", [])
        if versions:
            version_labels = [f"v{v['version']} - {v['timestamp']}" for v in versions]
            selected_label = st.selectbox(_t("選擇版本 (Select Version)", "Select Version"), version_labels, key="version_select")
            if selected_label:
                idx = version_labels.index(selected_label)
                ver = versions[idx]
                st.write(f"**{_t('版本', 'Version')} {ver['version']}** @ {ver['timestamp']}")

                col_load, col_view = st.columns([1, 3])
                with col_load:
                    if st.button(_t("載入此版本 (Load This Version)", "Load This Version"), key=f"load_{idx}"):
                        if ver.get("roster_df"):
                            st.session_state.roster_df = pd.DataFrame.from_dict(ver["roster_df"])
                        if ver.get("report_df"):
                            st.session_state.master_report_df = pd.DataFrame.from_dict(ver["report_df"])
                        st.success(get_text("version_loaded_success", version=ver['version']))
                        st.rerun()

                with col_view:
                    if ver.get("roster_df"):
                        ver_roster = pd.DataFrame.from_dict(ver["roster_df"])
                        st.dataframe(ver_roster, width="stretch", height=200)

                # Improved comparison: side-by-side key stats + sample
                if st.button(_t("比較此版本與當前 (Compare Version with Current)", "Compare Version with Current"), key=f"compare_{idx}"):
                    st.write("### " + _t("比較 (Comparison)", "Comparison"))
                    current_roster = st.session_state.roster_df
                    ver_roster = pd.DataFrame.from_dict(ver.get("roster_df", {})) if ver.get("roster_df") else pd.DataFrame()

                    # Simple stats comparison
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**" + _t("當前版本 (Current)", "Current Version") + "**")
                        st.write(f"- {_t('總欄位數', 'Total Columns')}: {len(current_roster.columns)}")
                        st.write(f"- {_t('總學生/角色', 'Total Students/Roles')}: {len(current_roster)}")
                    with col2:
                        version_label = _t("選定版本 (Version {})", "Selected Version (Version {})").format(ver['version'])
                        st.write(f"**{version_label}**")
                        st.write(f"- {_t('總欄位數', 'Total Columns')}: {len(ver_roster.columns) if not ver_roster.empty else 0}")
                        st.write(f"- {_t('總學生/角色', 'Total Students/Roles')}: {len(ver_roster) if not ver_roster.empty else 0}")

                    # Sample data
                    st.write("**" + get_text("sample_data_comparison") + "**")
                    st.write(get_text("current_label"))
                    st.dataframe(current_roster.head(5), width="stretch")
                    st.write(get_text("selected_version_label"))
                    if not ver_roster.empty:
                        st.dataframe(ver_roster.head(5), width="stretch")
                    else:
                        st.info(get_text("no_data_for_version"))
        else:
            st.info(get_text("versions_auto_save"))

    # Semester Service Hours Auto-Statistics + Certificate Generation
    st.write("---")
    st.subheader(get_text("semester_service_subheader"))
    st.caption(get_text("semester_service_caption"))

    if st.button(get_text("update_service_hours_button"), width="stretch"):
        for name in st.session_state.students_df["name"].dropna().astype(str).str.strip():
            count = (st.session_state.roster_df == name).sum().sum()
            hours = count * 1.0
            st.session_state.semester_hours[name] = st.session_state.semester_hours.get(name, 0) + hours
        st.success(get_text("service_hours_updated"))

    if st.session_state.get("semester_hours"):
        hours_df = pd.DataFrame(list(st.session_state.semester_hours.items()), columns=[_t("姓名 (Chinese Name)", "Name (Chinese Name)"), _t("總服務時數 (小時)", "Total Service Hours (hrs)")])
        st.dataframe(hours_df, width="stretch")

        if st.button(get_text("generate_service_cert_button"), width="stretch", type="primary"):
            cert_lines = [
                "Sing Yin Secondary School",
                "Study Prefect (導學風紀) Service Certificate",
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
                get_text("certificate_signer"),
                "Sing Yin Secondary School"
            ])
            cert_text = "\n".join(cert_lines)
            st.text_area(get_text("cert_preview_label"), cert_text, height=200)
            # Use proper PDF certificate (Direction C - upgrade from text to designed PDF)
            logo_b64 = base64.b64encode(st.session_state.logo_data).decode() if st.session_state.get("logo_data") else None
            cert_pdf = generate_service_certificate(st.session_state.semester_hours, logo_b64)
            if cert_pdf:
                st.download_button(
                    get_text("download_cert_pdf_button"),
                    cert_pdf,
                    f"SYSS_Service_Certificate_{datetime.date.today().strftime('%Y%m%d')}.pdf",
                    "application/pdf",
                    width="stretch"
                )
            else:
                st.warning(get_text("pdf_cert_unavailable_warning"))
            # Fallback text for compatibility
            st.download_button(
                get_text("download_cert_text_button"),
                cert_text,
                f"SYSS_Service_Certificate_{datetime.date.today().strftime('%Y%m%d')}.txt",
                width="stretch"
            )

    # ====================== 公平性圖表 ======================
    if not st.session_state.master_report_df.empty:
        st.write("---")
        st.subheader(get_text("overall_fairness_monitor_subheader"))
        fig = px.bar(
            st.session_state.master_report_df,
            x='Student Name',
            y='Cumulative Weighted Load (points)',
            text_auto='.1f',
            title=get_text("overall_workload_balance_title"),
            color='Cumulative Weighted Load (points)',
            color_continuous_scale='YlOrBr'
        )
        fig.update_layout(xaxis_title=_t("學生姓名", "Student Name"), yaxis_title=_t("累計加權負荷 (點)", "Cumulative Weighted Load (pts)"))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, width="stretch")

    # ====================== 智慧替補 ======================
    st.markdown(f'<p style="font-size:13px; font-weight:600; color:#6B7280; margin:16px 0 0 0;">{_t("其他功能", "Other Features")}</p>', unsafe_allow_html=True)
    st.write("---")
    st.subheader(get_text("smart_substitute_subheader"))
    c1, c2 = st.columns(2)
    with c1:
        chosen_day = st.selectbox(_t("請假或替換日期", "Leave or Replacement Date"), DAYS, index=0, key="sub_day_selector")
    with c2:
        chosen_role = st.selectbox(_t("請假或替換職位/房間", "Leave or Replacement Position/Room"), ROWS_ROSTER, index=0, key="sub_role_selector")

    current_person = str(st.session_state.roster_df.at[chosen_role, chosen_day]).strip()
    st.text_input(_t("📍 目前該時段排定之人員", "📍 Currently Scheduled Person for This Slot"), value=current_person if current_person not in ["", "X", "⬜"] else _t("（當前為空白或特殊不開放時段）", "(Currently blank or special closed period)"), disabled=True)

    if st.button(_t("🔮 執行篩選並推薦最優替補人員", "🔮 Execute Filter and Recommend Optimal Substitutes"), type="secondary", width="stretch"):
        sub_df, error_msg = recommend_substitutes(st.session_state.roster_df, st.session_state.students_df, chosen_day, chosen_role)
        if sub_df is not None:
            st.success(get_text("substitute_matching_success"))
            # Add mentoring fit column
            display_sub = sub_df.copy()
            names_lookup = {}
            for _, r in st.session_state.students_df.iterrows():
                n = str(r["name"]).strip()
                if n:
                    names_lookup[n] = r
            def _fit_label(row):
                rep_name = str(row["Name"]).strip()
                rep_info = names_lookup.get(rep_name)
                cur_info = names_lookup.get(current_person)
                if rep_info is not None and cur_info is not None:
                    rep_hw = float(rep_info.get("history_weight", 0))
                    cur_hw = float(cur_info.get("history_weight", 0))
                    rep_mentee = bool(rep_info.get("needs_mentoring", False)) or rep_hw <= 2
                    cur_mentee = bool(cur_info.get("needs_mentoring", False)) or cur_hw <= 2
                    rep_mentor = rep_hw > 5 and not bool(rep_info.get("needs_mentoring", False))
                    cur_mentor = cur_hw > 5 and not bool(cur_info.get("needs_mentoring", False))
                    if rep_mentor and cur_mentee:
                        return "🤝 Mentor"
                    if rep_mentee and cur_mentor:
                        return "👤 Mentee"
                return "－"
            display_sub = sub_df.copy()
            display_sub["Mentoring Fit"] = display_sub.apply(_fit_label, axis=1)
            display_sub.columns = [_t("姓名", "Name"), _t("年級", "Form"), _t("當前總點數", "Load"), _t("配對合適度", "Mentoring Fit")]
            st.dataframe(display_sub, width="stretch", hide_index=True)
        else:
            st.warning(error_msg)

    # ====================== 值班後請假調整（新增公平性核心功能） ======================
        # System architecture diagram (collapsible)
    render_system_architecture_diagram(
        expander_label=_t("System Architecture", "System Architecture"),
        caption_text=_t("以下為本系統的分層模組化架構，箭頭表示模組間的調用關係。完整架構說明請參閱 GitHub README。", "The layered modular architecture of this system. Arrows indicate module call relationships. See GitHub README for full documentation.")
    )
    
    cap = get_text("footer_caption", version=VERSION)
    st.caption(cap)


if __name__ == "__main__":
    main()