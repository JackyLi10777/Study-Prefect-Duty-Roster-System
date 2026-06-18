"""
roster/ui/messages.py

Centralized management of all user-facing display texts for the Sing Yin Study Prefect Duty Roster Platform.

This module provides:
- A MESSAGES registry (key -> (zh, en) tuples) for static and template strings.
- get_text(key, **kwargs) for safe lookup + formatting (assemble result first, never complex inline f + .format).
- Backward-compatible _t(zh_text, en_text) during migration (still supported but discouraged for new code).

Goal: Eliminate scattered inline strings and complex f-strings in app.py / components.py.
All language handling remains strictly in the display layer (roster/ui/*).

Constraints respected:
- Student names and role data strings remain Chinese (never passed through here).
- Safe patterns: use get_text for new code; for legacy dynamic, prefer "prefix = get_text(...); result = f'{prefix} {var}'"
- No impact on backup, core logic, or exports.

Usage examples:
    from roster.ui.messages import get_text, _t

    # New preferred (key-based, centralized)
    st.subheader(get_text("global_load_slider"))
    st.success(get_text("success_roster_complete", multiplier=1.5, version=3))

    # Legacy compatibility (will be migrated away)
    st.button(_t("🔄 刷新金句", "🔄 Refresh Verse"))
"""

import streamlit as st

# ====================== CENTRALIZED MESSAGES REGISTRY ======================
# Format: "key": ("中文原文或模板", "English original or template")
# Use {var} placeholders for dynamic content. Formatting is done safely in get_text().

MESSAGES = {
    # Core UI chrome (migrated examples)
    "global_load_slider": (
        "🌍 全局負荷調節滑桿",
        "🌍 Global Load Adjustment Slider"
    ),
    "global_load_caption": (
        "臨近考試時可提高本次排班整體負荷倍率，讓累計較低同學優先平衡",
        "Near exams, increase overall load multiplier for this roster to let lower cumulative students have priority balance"
    ),
    "current_load_multiplier": (
        "本次排班整體負荷倍率",
        "Current roster overall load multiplier"
    ),

    # Success / action messages (examples of dynamic templates)
    "success_roster_complete": (
        "✅ 排班完成！（全局負荷倍率：{multiplier:.1f}） 已儲存版本 #{version}。請記得下載 JSON 備份，並建議將重要版本上傳到 GitHub backups/ 資料夾長期保存。",
        "✅ Roster complete! (Global load multiplier: {multiplier:.1f}) Version #{version} saved. Remember to download JSON backup and recommend uploading important versions to GitHub backups/ folder for long-term storage."
    ),
    "success_adjust_complete": (
        "✅ 調整完成！{action_msg} 累計點數與公平性圖表已即時更新。",
        "✅ Adjustment complete! {action_msg} Cumulative points and fairness chart updated in real time."
    ),

    # Warnings / info
    "warning_data_mismatch": (
        "⚠️ 數據不符警告：",
        "⚠️ Data Mismatch Warning:"
    ),
    "warning_duplicate_duty": (
        "⚠️ 重複排班警告：",
        "⚠️ Duplicate Duty Warning:"
    ),
    "warning_leave_conflict": (
        "🛑 請假衝突：",
        "🛑 Leave Conflict:"
    ),
    "info_vacancy": (
        "💡 空缺提示：",
        "💡 Vacancy Notice:"
    ),

    # Placeholders & search (examples)
    "placeholder_search_student": (
        "輸入姓名、年級或職級關鍵字",
        "Enter name, form or role keyword"
    ),
    "placeholder_search_roster": (
        "輸入職位或房間關鍵字",
        "Enter position or room keyword"
    ),
    "placeholder_new_student": (
        "輸入學生姓名",
        "Enter student name"
    ),

    # Special periods
    "special_unavailable_label": (
        "🛠️ 本週特殊不開放時段",
        "🛠️ This week's special closed periods"
    ),
    "special_unavailable_help": (
        "選擇本週因特殊原因不開放的時段（系統會自動避開）",
        "Select periods closed this week due to special reasons (system will auto-avoid)"
    ),

    # Help / manual (large static content moved here for centralization)
    "help_text_full": (
        """### 📖 聖言中學導學風紀當值排班平台 使用說明書（v2.3 Final）

#### 1. 名冊導入（最重要）
- **推薦使用「🤖 AI 智能自動匹配」**：支援任意格式的 Excel / CSV，AI 會自動辨識欄位。
- 建議先點「📥 下載名冊格式範例」參考。

#### 2. 名冊即時修改
- 在側邊欄可以直接編輯所有領袖生資料，修改後即時儲存。

#### 3. 生成值班表
- 在側邊欄設定請假人員與特殊不開放時段。
- 點擊主畫面大按鈕「🚀 智能計算：生成本週全新公平值班表」。

#### 4. 全局負荷調節滑桿（新增重要功能）
- 主畫面最上方可即時調整本次排班整體負荷倍率（0.8~2.0）。
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

祝使用順利！🙏""",
        """### 📖 Sing Yin Study Prefect Duty Roster Platform User Manual (v2.3 Final)

#### 1. Roster Import (Most Important)
- **Recommended: "🤖 AI Smart Match"**: Supports any Excel/CSV format. AI automatically identifies columns.
- First click "📥 Download Format Example" for reference.

#### 2. Live Roster Editing
- Edit all prefect data directly in the sidebar. Changes save instantly.

#### 3. Generate Roster
- Set leave personnel and special closed periods in the sidebar.
- Click the large main button "🚀 Smart Compute: Generate this week's new fair roster".

#### 4. Global Load Adjustment Slider (New Important Feature)
- Adjust the overall load multiplier for this roster in real time at the top of the main screen (0.8~2.0).
- Increase the multiplier near exams so students with lower cumulative load get priority for fairness balance.

#### 5. Roster Operations
- **Visual Announcement Board**: Professional color-coded display. Different positions have different colors (Assist gold, Room302 green, Room303 yellow, Room202 red).
- **Manual Edit Mode**: Directly modify names or type "X" to lock on the table.

#### 6. Smart Substitute Recommendation
- After selecting date and position, click "🔍 Find Optimal Substitute". The system recommends based on current total points from lowest to highest.

#### 7. Export Functions
- **📄 Export PDF**: Professional color-coded roster (with school badge), suitable for posting/printing.
- **📊 Download Excel**: Complete roster + workload statistics table.
- **📝 Download Markdown**: Convenient for copying into other documents.

#### 8. Cloud Backup (Strongly Recommended)
- After generating a new roster each time, click "⬇️ Export Current Full Backup (JSON)" in the sidebar.
- After Streamlit Cloud hibernation, use "Upload backup JSON to restore" for quick recovery.

**Questions?** email s10777@syss.edu.hk

Good luck! 🙏"""
    ),

    # English guidance for HELP when in en mode (short version)
    "help_text_en_note": (
        "See the bilingual UI elements and labels throughout the app for English guidance. Full Chinese manual is available by switching to 中文介面. Key features: roster management, fair auto-scheduling respecting AHP/rooms, leave adjustments for equity, JSON/PDF backups (always backup after edits), dark mode, language toggle. Student names preserved in Chinese in all exports.",
        "See the bilingual UI elements and labels throughout the app for English guidance. Full Chinese manual is available by switching to 中文介面. Key features: roster management, fair auto-scheduling respecting AHP/rooms, leave adjustments for equity, JSON/PDF backups (always backup after edits), dark mode, language toggle. Student names preserved in Chinese in all exports."
    ),

    # Common captions and labels (add more as migrated)
    "ai_support_caption": (
        "💡 AI 支援任意欄位順序，節省您的時間",
        "💡 AI supports any column order, saving your time"
    ),
    "auto_saved_caption": (
        "修改後自動儲存",
        "Auto-saved after modification"
    ),
    "batch_manage_caption": (
        "一次選擇多名學生，批量設定請假或固定值班",
        "Select multiple students for batch leave or fixed duty"
    ),

    # Strong role-branded headings / labels (to be fully neutralized - remove exclusive AHP/Head branding)
    # - management_dashboard_title, insight_title, certificate_signer, batch_manage_caption
    # Descriptive / data-related texts (keep necessary "AHP" role context for clarity on which position the stats refer to;
    # only avoid "專屬" etc. for neutral tone)
    # - report_contribution_label, average_load_label, ahp_load_detail_template, ahp_avg_load_phrase, report_generation_caption
    # All changes display-layer only; zero impact on logic/backup/permissions. Per approved plan.
    "management_dashboard_title": (
        "📈 管理視角儀表板",
        "📈 Management Dashboard"
    ),
    "insight_title": (
        "👑 特別洞察",
        "👑 Special Insight"
    ),
    "report_contribution_label": (
        "AHP 貢獻",
        "AHP Contribution"
    ),
    "average_load_label": (
        "AHP 平均負荷",
        "AHP Average Load"
    ),
    "ahp_load_detail_template": (
        "AHP 平均負荷：{avg:.1f} 點 (共 {count} 位)",
        "AHP Average Load: {avg:.1f} points ({count} AHPs)"
    ),
    "ahp_avg_load_phrase": (
        "位 AHP 平均負荷",
        "AHPs avg load"
    ),
    "certificate_signer": (
        "團隊負責人",
        "Team Leader"
    ),
    "report_generation_caption": (
        "一鍵生成報告，包含公平性、表現者、AHP貢獻、僕人領袖註記。支援中文預覽與專業英文匯出。",
        "One-click report generation, including fairness, top performers, AHP contributions, servant leadership notes. Supports Chinese preview and professional English export."
    ),

    # Add more keys for frequent strings over time (placeholders, buttons, etc.)
    # Example template for dynamic
    "showing_filtered": (
        "顯示 {shown} / {total} 位學生 (搜尋結果)",
        "Showing {shown} / {total} students (search results)"
    ),

    # High-frequency dynamic / error-prone f-string messages (migrated for centralization and safety)
    "saved_trend_week": (
        "已儲存第 {week_num} 週數據。用於趨勢分析。",
        "Saved week {week_num} data for trend analysis."
    ),
    "most_neglected": (
        "⚠️ 最需關注學生 (Most Neglected - 最低負荷): {names}。建議優先給予機會以促進公平。",
        "⚠️ Most Neglected Students (Lowest Load): {names}. Suggest prioritizing opportunities to promote fairness."
    ),
    "version_loaded_success": (
        "✅ 版本 {version} 已載入當前",
        "✅ Version {version} loaded to current"
    ),
    "no_data_for_version": (
        "選定版本無資料",
        "No data for selected version"
    ),
    "versions_auto_save": (
        "生成值班表後版本會自動儲存。",
        "Versions will be automatically saved after generating the roster."
    ),
    "revoke_points": (
        "已從 **{current_person}** 撤銷 {weight:.1f} 點",
        "Revoked {weight:.1f} pts from **{current_person}**"
    ),
    "handover_to": (
        "，並轉由 **{replacement}** 接手。",
        ", and handed over to **{replacement}**."
    ),
    "no_one_for_slot": (
        "，該崗位暫無人值班。",
        ", no one scheduled for that slot."
    ),
    "adjustment_complete": (
        "✅ 調整完成！{action_msg} 累計點數與公平性圖表已即時更新。",
        "✅ Adjustment complete! {action_msg} Cumulative points and fairness chart updated in real time."
    ),

    # High-frequency action success / feedback (migrated in this phase for safety - assemble vars first, pass to get_text)
    # These were previously error-prone _t(f"...") or inline f-strings with counts/vars.
    "batch_leave_success": (
        "✅ 已為 {count} 位學生批量設定請假。請記得在生成排班時套用，並下載 JSON 備份（建議 commit 到 GitHub backups/ 資料夾）。",
        "✅ Batch leave set for {count} students. Remember to apply when generating roster and download JSON backup (recommend commit to GitHub backups/ folder)."
    ),
    "batch_fixed_success": (
        "✅ 已為 {count} 位學生設定固定 {day}。請下載 JSON 備份以保存變更，並建議上傳到 GitHub backups/ 資料夾。",
        "✅ Fixed {day} set for {count} students. Please download JSON backup to save changes and recommend upload to GitHub backups/ folder."
    ),
    "manual_adjust_saved": (
        "✅ 手動調整已儲存。建議立即下載 JSON 備份，並將重要版本 commit 到 GitHub backups/ 資料夾。",
        "✅ Manual adjustment saved. Recommend downloading JSON backup immediately and committing important versions to GitHub backups/ folder."
    ),
    "roster_complete_success": (
        "✅ 排班完成！（全局負荷倍率：{multiplier:.1f}） 已儲存版本 #{version}。請記得下載 JSON 備份，並建議將重要版本上傳到 GitHub backups/ 資料夾長期保存。",
        "✅ Roster complete! (Global load multiplier: {multiplier:.1f}) Version #{version} saved. Remember to download JSON backup and recommend uploading important versions to GitHub backups/ folder for long-term storage."
    ),

    # Phase 3 continuation keys: remaining prompts/feedback + report/summary/certificate dynamic texts (and related high-freq with vars)
    # Safe templates; leverage prior keys where possible (e.g. report_generation_caption, service_hours_updated, certificate_signer already exist and used).
    # Focus on titles, buttons, headers, labels, warnings, dynamic f-captions (e.g. history counts).

    # Report / Summary generation
    "summary_report_subheader": (
        "📋 總結報告生成 (Advanced Summary Report)",
        "📋 Summary Report Generation (Advanced Summary Report)"
    ),
    "generate_summary_button": (
        "📊 生成總結報告 (Generate Summary Report)",
        "📊 Generate Summary Report"
    ),
    "chinese_preview_header": (
        "📝 中文預覽 (Chinese UI Preview)",
        "📝 Chinese Preview (Chinese UI Preview)"
    ),
    "english_export_header": (
        "📤 專業英文匯出版 (Professional English Export)",
        "📤 Professional English Export Version"
    ),
    "download_summary_txt_button": (
        "⬇️ 下載英文總結報告 (Download Professional English Summary .txt)",
        "⬇️ Download Professional English Summary .txt"
    ),
    "extra_pdf_summary_button": (
        "📄 額外下載英文PDF摘要 (Extra English PDF Summary)",
        "📄 Extra Download English PDF Summary"
    ),
    "report_backup_reminder_caption": (
        "💡 重要：下載英文報告後，請務必同時下載對應的 JSON 備份，並手動上傳到 GitHub 的 `backups/` 資料夾進行長期保存。",
        "💡 Important: After downloading the English report, please also download the corresponding JSON backup and manually upload it to the GitHub `backups/` folder for long-term storage."
    ),
    "export_pdf_best_format": (
        "使用匯出功能下載完整英文PDF以獲得最佳格式。",
        "Use the export function to download the full English PDF for best format."
    ),

    # Certificate / Service hours
    "semester_service_subheader": (
        "⏱️ 學期服務時數統計與證書生成 (Semester Service Hours & Certificate)",
        "⏱️ Semester Service Hours Statistics & Certificate Generation"
    ),
    "semester_service_caption": (
        "自動計算服務時數 (每值班1小時)，一鍵生成專業英文證書 (姓名保留中文)",
        "Automatically calculate service hours (1 hour per duty), one-click generate professional English certificate (names remain in Chinese)"
    ),
    "update_service_hours_button": (
        "🔄 更新/重新計算服務時數 (Update from Current Roster)",
        "🔄 Update/Recalculate Service Hours (Update from Current Roster)"
    ),
    "generate_service_cert_button": (
        "📜 生成服務證書 (Generate Professional English Certificate)",
        "📜 Generate Service Certificate (Generate Professional English Certificate)"
    ),
    "cert_preview_label": (
        "證書預覽 (Certificate Preview - English with Chinese Names)",
        "Certificate Preview (English with Chinese Names)"
    ),
    "download_cert_pdf_button": (
        "⬇️ 下載專業英文PDF證書 (Download Professional English PDF Certificate)",
        "⬇️ Download Professional English PDF Certificate"
    ),
    "download_cert_text_button": (
        "⬇️ 下載英文證書文字版 (Download English Certificate Text)",
        "⬇️ Download English Certificate Text"
    ),
    "pdf_cert_unavailable_warning": (
        "無法生成PDF證書，請確認WeasyPrint可用。",
        "Unable to generate PDF certificate, please confirm WeasyPrint is available."
    ),

    # Fairness monitoring & post-duty adjustment (high-freq in fairness flows)
    "overall_fairness_monitor_subheader": (
        "🦅 全體累積工作點數公平性監控",
        "🦅 Overall Cumulative Work Points Fairness Monitoring"
    ),
    "overall_workload_balance_title": (
        "全體領袖生加權工作量天平（點數低者將優先派班）",
        "Overall Prefect Weighted Workload Balance (Lower pts = Higher future priority)"
    ),
    "post_duty_leave_subheader": (
        "⚖️ 值班後請假調整（確保公平性）",
        "⚖️ Post-Duty Leave Adjustment (Ensure Fairness)"
    ),
    "post_duty_leave_caption": (
        "值班表發布後若有人臨時請假，可在此撤銷其已計算的負荷點數，並選擇替補人員（或留空）。調整後立即更新累計與報表，保證公平。",
        "If someone requests leave after the roster is published, you can revoke their calculated load points here and select a substitute (or leave blank). The cumulative and report will be updated immediately after adjustment to ensure fairness."
    ),

    # Export section
    "export_section_subheader": (
        "📤 匯出（跟隨語言設定）",
        "📤 Export (Follow Current Language)"
    ),
    "export_section_caption": (
        "匯出使用目前語言的標題與欄位，學生姓名永遠保留中文。",
        "Exports use titles/columns per current language. Student names always remain in Chinese."
    ),

    # Remaining prompts / feedback / info / warnings (high-freq daily)
    "audit_table_info": (
        "請先生成排班表以顯示審計表",
        "Please generate the roster first to display the audit table"
    ),
    "history_trend_prompt": (
        "💡 點擊「儲存本週」按鈕開始記錄歷史趨勢。",
        "💡 Click the 'Save This Week' button to start recording historical trends."
    ),
    "load_roster_prompt": (
        "📌 請先載入名冊開始管理",
        "📌 Please load roster first to start management"
    ),
    "clear_roster_confirm_error": (
        "⚠️ 確定要清除全部排班？此操作無法復原！",
        "⚠️ Confirm to clear all roster? This cannot be undone!"
    ),

    # Backup / history / restore dynamic (f with vars, warnings, labels)
    "backup_history_caption": (
        "📚 本次工作階段備份歷史（共 {count} 個，最新在前）",
        "📚 Backup history this session ({count} total, newest first)"
    ),
    "upload_backup_label": (
        "上傳備份 JSON 進行還原",
        "Upload backup JSON to restore"
    ),
    "history_version_selected_info": (
        "已選擇歷史版本。請選擇還原模式後點擊還原。",
        "History version selected. Please choose restore mode then click restore."
    ),
    "restore_mode_full": (
        "Full Replace（完全取代）",
        "Full Replace（Complete Replace）"
    ),
    "restore_mode_smart": (
        "Smart Merge（智慧合併）",
        "Smart Merge（Smart Merge）"
    ),
    "execute_restore_button": (
        "🔄 執行還原此版本",
        "🔄 Execute Restore this version"
    ),
    "cancel_selection_button": (
        "取消選擇",
        "Cancel Selection"
    ),
    "long_term_storage_tip": (
        "💡 長期保存建議：重要的 JSON 備份，請手動上傳至 GitHub 倉庫的 `backups/` 資料夾（例如命名為 backup_2026-06-13_週三.json），以進行版本控制與災難恢復。即使本地遺失，也能從 GitHub 還原。",
        "💡 Long-term storage tip: Please manually upload important JSON backups to the GitHub repo's `backups/` folder (e.g. named backup_2026-06-13_Wed.json) for version control and disaster recovery. Even if local data is lost, it can be restored from GitHub."
    ),
    "backup_warning_important": (
        "🔔 重要操作完成！強烈建議立即下載 JSON 備份（動態數據），並將重要版本上傳到 GitHub 的 backups/ 資料夾長期保存，以避免資料遺失。",
        "🔔 Important operation completed! Strongly recommend downloading JSON backup (dynamic data) immediately and uploading important versions to GitHub backups/ folder for long-term storage to avoid data loss."
    ),
    "cloud_backup_subheader": (
        "💾 Cloud 備份與還原",
        "💾 Cloud Backup & Restore"
    ),
    "cloud_stateless_caption": (
        "⚠️ Streamlit Cloud 為無狀態環境，資料可能因休眠或重啟而遺失，請務必做好備份！",
        "⚠️ Streamlit Cloud is stateless. Data may be lost on sleep or restart. Always backup!"
    ),
    "important_backup_reminder": (
        "💡 請記得下載 JSON 備份，並建議將此重要調整的備份上傳到 GitHub 的 backups/ 資料夾以長期保存。",
        "💡 Remember to download the JSON backup and recommend uploading this important adjustment's backup to the GitHub backups/ folder for long-term storage."
    ),
    "roster_version_history_expander": (
        "📜 值班表版本歷史 (Roster Version History) - 自動儲存每次生成",
        "📜 Roster Version History (Roster Version History) - Auto-saved after each generation"
    ),
    "sample_data_comparison": (
        "樣本資料比較 (Sample - first 5 rows)",
        "Sample Data Comparison (Sample - first 5 rows)"
    ),
    "current_label": ("當前:", "Current:"),
    "selected_version_label": ("選定版本:", "Selected Version:"),
    "service_hours_updated": (
        "服務時數已更新",
        "Service hours updated"
    ),
    "ai_parse_success": (
        "✅ AI 已自動更新固定值班、可值班日與職級",
        "✅ AI has auto-updated fixed duties, available days, and roles"
    ),
    "demo_roster_loaded": (
        "✅ 示範名冊載入完成",
        "✅ Demo roster loaded successfully"
    ),
    "badge_updated": (
        "✅ 校徽已更新",
        "✅ Badge updated"
    ),
    "student_added": (
        "已新增 {name} ({role})",
        "Added {name} ({role})"
    ),
    "leave_cleared_success": (
        "✅ 已清除請假同學",
        "✅ Leave students cleared"
    ),
    "substitute_matching_success": (
        "📋 媒合成功！已依據「最終總計加權負荷」由低到高為您排序推薦合格替補人員：",
        "📋 Matching successful! Sorted recommended qualified substitutes from lowest to highest based on 'Final Total Weighted Load':"
    ),

    # Fairness/KPI related (high-freq feedback, part of insights group)
    "fairness_gap_warning": (
        "⚠️ 公平差距較大，建議檢視固定值班與請假調整機制。",
        "⚠️ Fairness gap is large, suggest reviewing fixed duty and leave adjustment mechanisms."
    ),
    "overall_fairness_success": (
        "✅ 整體公平性良好，符合學校僕人領袖與公平原則。",
        "✅ Overall fairness is good, in line with school servant leadership and fairness principles."
    ),

    "footer_caption": (
        "聖言中學導學風紀當值排班平台 | {version} | 介面中文 | 匯出專業",
        "Sing Yin Secondary School Study Prefect Platform | {version} | UI: English | Exports: Professional"
    ),

    # For search result captions (minimal addition for this migration)
    "showing_prefix": ("顯示", "Showing"),
    "rows_label": ("列", "rows"),

    # ============================================================
    # Final low-priority static section titles / subheaders / captions cleanup
    # These are purely static (no variables), low-risk, for consistency.
    # Migrated as the very last phase after all high-freq dynamic + prompt/feedback.
    # ============================================================

    # app.py static titles
    "global_load_slider_subheader": (
        "🌍 全局負荷調節滑桿",
        "🌍 Global Load Adjustment Slider"
    ),
    "global_load_slider_caption": (
        "臨近考試時可提高本次排班整體負荷倍率，讓累計較低同學優先平衡",
        "Near exams, increase overall load multiplier for this roster to let lower cumulative students have priority balance"
    ),
    "this_week_roster_subheader": (
        "📅 本週值班表",
        "📅 This Week's Roster"
    ),
    "manual_load_adjust_subheader": (
        "🔧 手動調整本次值班負荷指數",
        "🔧 Manual Adjust This Week's Duty Load Index"
    ),
    "manual_load_adjust_caption": (
        "針對每個崗位本次值班，手動修改累計負荷點數（已受全局滑桿影響）",
        "Manually adjust cumulative load points for each position's duty this week (affected by global slider)"
    ),
    "cumulative_audit_subheader": (
        "📊 累計動態工作負荷審計表",
        "📊 Cumulative Dynamic Workload Audit Table"
    ),
    "history_fairness_subheader": (
        "📊 歷史趨勢與公平性分析",
        "📊 Historical Trends & Fairness Analysis"
    ),
    "smart_substitute_subheader": (
        "🔍 智慧替補推薦",
        "🔍 Smart Substitute Recommendation"
    ),

    # components.py static titles / subheaders / captions
    "platform_caption": (
        "導學風紀當值排班平台",
        "Study Prefect Duty Roster Platform"
    ),
    "english_exports_caption": (
        "英文介面 + 專業英文匯出",
        "English Interface + Professional English Exports"
    ),
    "chinese_exports_caption": (
        "中文介面（匯出支援英文）",
        "Chinese Interface (Exports support English)"
    ),
    "live_statistics_subheader": (
        "📊 即時累計統計",
        "📊 Live Statistics"
    ),
    "roster_management_subheader": (
        "🗄️ 名冊管理",
        "🗄️ Roster Management"
    ),
    "ai_support_caption": (
        "💡 AI 支援任意欄位順序，節省您的時間",
        "💡 AI supports any column order, saving your time"
    ),
    "live_roster_edit_subheader": (
        "👥 名冊即時修改",
        "👥 Live Roster Edit"
    ),
    "auto_saved_caption": (
        "修改後自動儲存",
        "Auto-saved after modification"
    ),
    "ai_smart_parse_subheader": (
        "🤖 AI 智能解析",
        "🤖 AI Smart Parse"
    ),
    "leave_registration_subheader": (
        "🛑 請假登記",
        "🛑 Leave Registration"
    ),
    "smart_add_student_subheader": (
        "➕ 智慧新增學生 (Smart Autocomplete)",
        "➕ Smart Add Student (Smart Autocomplete)"
    ),
    "smart_add_student_caption": (
        "輸入姓名，選擇職級 (僅三種選項)，快速新增",
        "Enter name, select role (only 3 options), quick add"
    ),
    "batch_management_subheader": (
        "📋 批量管理",
        "📋 Batch Management"
    ),

    # PDF Restore
    "pdf_restore_subheader": (
        "📄 從 PDF 備份還原數據",
        "📄 Restore Data from PDF Backup"
    ),
    "pdf_restore_caption": (
        "上傳之前生成的 PDF 值班表，系統將自動解析並還原所有風紀資料與排班記錄。",
        "Upload a previously generated PDF roster to restore all prefect data and scheduling records."
    ),
}

# ====================== SAFE TEXT RETRIEVAL ======================
def get_text(key: str, **kwargs) -> str:
    """
    Retrieve user-facing text by stable key.
    Supports safe .format() on the looked-up template.

    Always assembles the final string *after* lookup.
    Never embed .format() or complex expressions inside f-string literals at call sites.

    Example:
        msg = get_text("success_roster_complete", multiplier=1.2, version=5)
    """
    if key not in MESSAGES:
        # Fallback for unknown key during transition (should be rare)
        return key

    zh, en = MESSAGES[key]
    lang = st.session_state.get("ui_language", "zh")
    text = en if lang == "en" else zh

    if kwargs:
        # Safe formatting - assemble here, not in caller f-string
        text = text.format(**kwargs)

    return text


# ====================== LEGACY COMPATIBILITY _t (during migration) ======================
def _t(zh_text: str, en_text: str) -> str:
    """
    Backward-compatible translator.

    DEPRECATED for new code. Prefer get_text("key") or get_text("key", var=val).

    Still works for gradual migration of existing call sites.
    Student names must never be passed as zh_text/en_text.
    """
    lang = st.session_state.get("ui_language", "zh")
    return en_text if lang == "en" else zh_text


# Convenience re-export for very common simple cases if desired
# (callers can still do from roster.ui.messages import _t, get_text)
