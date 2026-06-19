"""
roster/ui/messages.py

Centralized management of all user-facing display texts for the Sing Yin Study Prefect Duty Roster Platform.


> 📋 **Quick Nav:** [1.Import](#1-roster-import) | [2.Edit](#2-live-roster-editing) | [3.Generate](#3-generate-duty-roster) | [4.Load Scale](#4-global-load-scale-slider) | [5.Operations](#5-roster-board-operations) | [6.Mentoring](#6-mentoring-dashboard) | [7.Substitutes](#7-smart-substitute-recommendation) | [8.Export](#8-export-functions) | [9.Backup](#9-cloud-backup) | [10.Advanced](#10-advanced-features) | [11.Roles](#11-roles--permissions) | [12.Tech](#12-technical-overview)

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
        """### 📖 聖言中學導學風紀當值排班平台 使用說明書（v2.4 Final）


> 📋 **快速導航：** [1.名冊導入](#1-名冊導入) | [2.名冊修改](#2-名冊即時修改) | [3.生成值班表](#3-生成值班表) | [4.負荷調節](#4-全局負荷調節滑桿) | [5.值班表操作](#5-值班表操作) | [6.師徒儀表板](#6-師徒配對儀表板) | [7.智慧替補](#7-智慧替補推薦) | [8.匯出](#8-匯出功能) | [9.備份](#9-cloud-備份) | [10.進階](#10-進階功能使用說明) | [11.權限](#11-權限與角色說明) | [12.技術](#12-系統技術概要)

#### 1. 名冊導入（最重要）
- **推薦使用「🤖 AI 智能自動匹配」**：支援任意格式的 Excel / CSV，DeepSeek-V4-Flash AI 會自動辨識欄位。
- 建議先點「📥 下載名冊格式範例」參考。

#### 2. 名冊即時修改
- 在側邊欄可以直接編輯所有領袖生資料，修改後即時儲存。
- **「需要師徒指導」欄位**：手動勾選後，該風紀將在排班時優先與經驗風紀配對。

#### 3. 生成值班表
- 在側邊欄設定請假人員與特殊不開放時段。
- 點擊主畫面大按鈕「🚀 一鍵生成公平值班表」。

#### 4. 全局負荷調節滑桿
- 主畫面最上方可即時調整本次排班整體負荷倍率（0.8～2.0）。
- 臨近考試時提高倍率，讓累計負荷較低的學生優先達到公平平衡。

#### 5. 值班表操作
- **視覺公告版**：專業彩色顯示，不同崗位不同顏色（Assist 金米、Room302 綠、Room303 黃、Room202 紅）。
- **手動修改版**：可直接在表格上修改人名或打「X」鎖定。
- **師徒配對標記**：若兩個風紀被安排在同一間房形成師徒配對，該儲存格左側會顯示 🟦 藍綠色邊框標記。
- **自動標籤**：名冊中自動顯示「🆕 新加入」（history_weight=0）、「👤 需要師徒指導」（weight≤2）、「✅ 已指定師徒」（手動勾選）。

#### 6. 師徒配對儀表板
- **配對成效卡**：生成值班表後，公平性區域自動顯示本週師徒配對數、配對成功率及評級。
- **學徒進度追蹤**：可摺疊面板，儲存當前點數為基準，下次生成值班表後回來查看學徒點數變化趨勢（進步中／持平／需關註）。

#### 7. 智慧替補推薦
- 選擇日期與崗位後，點擊「🔍 尋找最優替補」，系統會依據目前總點數由低到高推薦。
- 替補推薦結果會顯示「配對合適度」欄位，🤝 Mentor 表示推薦人選適合指導現有值班者，👤 Mentee 則表示適合接受指導。

#### 8. 匯出功能
- **📄 匯出中文 PDF**：專業彩色班表（含校徽），內含師徒配對摘要與完整備份數據（末頁）。適合公告列印。
- **📄 Export English PDF**：供外部或英文使用者。
- **📊 下載 Excel**：完整值班表 + 工作負荷統計表。
- **📝 下載 Markdown**：方便複製到其他文件。

#### 9. Cloud 備份（強烈建議）
- 每次生成新班表後，建議在側邊欄點擊「⬇️ 導出完整備份 (JSON)」下載備份。
- **PDF 備份還原**：上傳之前導出的完整 PDF（無需拆頁），系統自動解析並還原數據。
- Streamlit Cloud 休眠後可用「上傳備份 JSON 還原」或「PDF 備份還原」快速恢復。

#### 10. 進階功能使用說明
- **批量請假**：在側邊欄勾選多名風紀後點「標記為請假」，一次性設為本週請假。
- **批量固定值班**：選擇目標星期後點「設為固定值班」，為多人安排固定崗位。
- **歷史趨勢儀表板**：公平性區域「📈 歷史負荷趨勢」圖表，追蹤每週每人累計點數變化。
- **學徒進度追蹤**：展開摺疊面板，儲存基準線後對比師徒配對成效。
- **PDF 完整備份還原**：直接上傳導出的完整 PDF，系統自動尋找內嵌備份數據進行完整還原。
- **清除數據與重設**：側邊欄底部「🗑️ 完全清除所有數據」按鈕一鍵重置（需二次確認，無法復原）。

#### 11. 權限與角色說明

| 角色 | 英文名稱 | 可擔任崗位 | 特別權限 |
|------|----------|-----------|---------|
| **首席導學風紀** | Head Study Prefect | 所有崗位 | 完整排班管理權限 |
| **助理首席導學風紀** | Asst. Head Study Prefect (AHP) | **僅限「Assist. in charge」** | 不可擔任 Room 302/303/202 |
| **導學風紀** | Study Prefect | Room 302/303/202 等 | 不可擔任「Assist. in charge」 |

**關鍵規則：**
- 「Assist. in charge」僅限 AHP 擔任（-8.0 優先加權）。
- 系統目前主要設計給首席導學風紀使用。
- 師徒配對機制與角色無關，所有崗位皆可受益。

#### 12. 系統技術概要（附錄）

> 🔗 本節為進階技術說明。日常操作無需閱讀。

本系統採用 **Python + Streamlit** 構建，實施嚴謹的**分層模組化架構**（7 層級、33 個 Python 模組、62 項自動化測試覆蓋）。

**排班引擎**
基於 `history_weight` 的量化公平演算法，完整實現 AHP 角色限制、Room 202 週二/五自動關閉、F.3 師徒優先級、不可連續值班、全域負荷動態調節。

**AI 服務層**
DeepSeek-V4-Flash 驅動的智能解析層，獨立於核心排班邏輯。支援任意格式的 Excel/CSV 欄位自動映射與學生備註結構化提取。

**PDF 報告引擎**
WeasyPrint CSS 排版引擎生成中英雙語專業報告。含校徽、彩色崗位標記、工作量審計表、師徒配對摘要，末頁自動嵌入完整 JSON 備份。

**備份與持久化**
三層備份策略：PDF 嵌入備份（主通道，每次匯出即備份）+ JSON 輕量下載（備援）+ GitHub `ai` 分支長期託管。還原時自動執行 `validate_state_integrity()` 數據完整性校驗。

**測試體系**
62 項自動化測試（單元測試 + 引擎邏輯測試 + 端到端集成測試），涵蓋排班規則驗證、備份解析、PDF 生成、狀態管理、導入導出全鏈路。


**開發投入說明**

這個系統的開發，是我個人規模最大的一次 AI 輔助軟件工程實踐。我透過 Codex 接入 DeepSeek V4 Pro 作為主力開發模型，輔以 Grok 與 Grok Build，總計消耗約 **20 億 tokens** 的 AI 計算資源。

這些投入直接反映在專案的每一個層面：
- 5 輪架構重構 → 7 層模組化架構
- 62 項自動化測試覆蓋
- 10 張 Mermaid 架構圖詳解
- 雙語完整文檔體系
- DeepSeek AI 智能解析功能

AI 是我的開發加速器，但我主導所有架構決策與規則驗證——我親自審查了每一行程式碼，確保它符合聖言中學的實際需求。

我是 26-27 年度首席導學風紀李創杰（LI Chuangjie Jacky）。這個系統由我發起、設計並全程主導開發。從架構決策到品質標準，從 AI 協作到持續迭代——我投入了大量時間與精力，因為我相信導學風紀團隊值得一個真正專業的排班工具。

有問題請 email s10777@syss.edu.hk**


### 結語

這個系統由我（李創杰，26-27 年度首席導學風紀）與 Codex（DeepSeek V4 Pro）、Grok、Grok Build 協作開發。

> **Codex：** 「Jacky，從第一行代碼到現在的完整系統，我很榮幸能參與其中。願它在你畢業後繼續服務團隊。✨」
> **Grok：** 「你用行動證明了一個中學生可以打造專業級系統。這很酷。🚀」

做這個系統的過程遠比想像中複雜，但我從不後悔。我希望它能為未來的首席導學風紀帶來真正的便利，也讓每一位風紀感受到公平被認真對待。

**—— 李創杰，2026 年 6 月**
祝使用順利！🙏""",
        """### 📖 Sing Yin Study Prefect Duty Roster Platform — User Manual (v2.4 Final)

#### 1. Roster Import (Most Important)
- **Recommended: "🤖 AI Smart Match"**: Supports any Excel/CSV format. DeepSeek-V4-Flash AI auto-identifies columns.
- Download "📥 Format Example" for reference first.

#### 2. Live Roster Editing
- Edit all prefect data directly in the sidebar. Changes save instantly.
- **"Needs Mentoring" column**: When checked, the prefect will be prioritised for mentoring pairing during scheduling.

#### 3. Generate Roster
- Set leave personnel and special closure periods in the sidebar.
- Click the large button "🚀 Generate Fair Roster Now".

#### 4. Global Load Adjustment Slider
- Adjust the overall load multiplier (0.8–2.0) in real time at the top of the main screen.
- Increase near exams so lower-load students reach fairness balance faster.

#### 5. Roster Operations
- **Visual Board**: Professional colour-coded display (Assist = gold, Room 302 = green, Room 303 = yellow, Room 202 = red).
- **Manual Edit Mode**: Modify names directly or type "X" to lock cells.
- **Mentoring Pair Markers**: Cells with 🟦 teal left border indicate a mentoring pair has been formed.
- **Auto Badges**: "🆕 New" (weight=0), "👤 Needs Mentoring" (weight≤2), "✅ Designated Mentee" (manual flag).

#### 6. Mentoring Dashboard
- **Pairing Stats Card**: Auto-displays weekly mentoring pair count, success rate, and rating after roster generation.
- **Mentee Progress Tracker**: Collapsible panel to save baseline scores and compare changes over time.

#### 7. Smart Substitute Recommendation
- Select a date and role, then click "🔍 Find Optimal Substitute". System recommends by lowest current total points.
- Results show "Pairing Fit" column: 🤝 Mentor = suitable to guide current assignee, 👤 Mentee = suitable to be guided.

#### 8. Export Functions
- **📄 Export Chinese PDF**: Professional colour roster with school badge, mentoring summary, and embedded backup data.
- **📄 Export English PDF**: For external or English-speaking users.
- **📊 Download Excel**: Full roster + workload audit table.
- **📝 Download Markdown**: Convenient for copying into other documents.

#### 9. Cloud Backup (Strongly Recommended)
- After generating a roster, click "⬇️ Export Full Backup (JSON)" in the sidebar.
- **PDF Backup Restore**: Upload a previously exported PDF (no need to split pages). The system auto-parses and restores all data.
- After Streamlit Cloud hibernation, restore via "Upload JSON Backup" or "PDF Backup Restore".

#### 10. Advanced Features
- **Batch Leave**: Select multiple prefects in the sidebar and mark them as on leave for the week in one click.
- **Batch Fixed Duty**: Assign the same fixed duty day to multiple prefects (e.g., school-wide event day).
- **Historical Trend Dashboard**: "📈 Historical Load Trend" chart tracks cumulative points per person per week.
- **Mentee Progress Tracking**: Collapsible panel for baseline snapshots and mentoring outcome comparison.
- **Full PDF Restore**: Upload the complete exported PDF – system auto-locates embedded backup data for full state recovery.
- **Reset System**: "🗑️ Clear All Data" button at sidebar bottom (double-confirmation required, irreversible).

#### 11. Roles & Permissions

| Role | Permitted Slots | Restrictions |
|------|----------------|--------------|
| **Head Study Prefect** | All slots | Full management access |
| **Asst. Head Study Prefect (AHP)** | "Assist. in charge" only | Cannot serve Room 302/303/202 |
| **Study Prefect** | Room 302/303/202 | Cannot serve "Assist. in charge" |

**Key Rules:**
- "Assist. in charge" is AHP-exclusive (-8.0 priority weighting).
- System is primarily designed for the Head Study Prefect.
- Mentoring pairing applies to all roles equally.

#### 12. Technical Overview (Appendix)

> 🔗 This section contains advanced technical detail. Not required for daily operations.

Built with **Python + Streamlit** using a rigorous **layered modular architecture** (7 layers, 33 Python modules, 62 automated tests).

**Scheduling Engine**
Quantitative fairness algorithm based on `history_weight`. Full implementation of AHP role restrictions, Room 202 Tue/Fri auto-closure, F.3 junior priority, no-consecutive-days rule, and global load dynamic scaling.

**AI Service Layer**
DeepSeek-V4-Flash powered intelligent parsing layer, decoupled from core scheduling logic. Supports automatic column mapping for arbitrary Excel/CSV formats and structured extraction of student remarks.

**PDF Report Engine**
WeasyPrint CSS layout engine producing bilingual professional reports. Includes school badge, colour-coded role markers, workload audit table, mentoring pair summary, with full JSON backup embedded on the final page.

**Backup & Persistence**
Three-tier backup strategy: PDF-embedded backup (primary, auto-backed up on every export) + JSON lightweight download (secondary) + GitHub `ai` branch long-term storage. Auto-executes `validate_state_integrity()` on restore for data integrity verification.

**Test Suite**
62 automated tests (unit + engine logic + end-to-end integration), covering scheduling rule validation, backup parsing, PDF generation, state management, and full import/export pipeline.


**Development Investment**

Building this system was the largest AI-assisted software engineering practice I have personally undertaken. I used Codex with DeepSeek V4 Pro as my primary development model, supplemented by Grok and Grok Build, consuming approximately **2 billion tokens** of AI compute resources in total.

This investment is directly reflected in every layer:
- 5 rounds of architectural refactoring → 7-layer modular architecture
- 62 automated test coverage
- 10 Mermaid architecture diagrams
- Full bilingual documentation system
- DeepSeek AI smart parsing features

AI served as my development accelerator, but I owned all architecture decisions and rule validation — I personally reviewed every line of code to ensure it meets Sing Yin's real needs.

I am LI Chuangjie Jacky, the 26-27 Head Study Prefect. I initiated, designed, and led this system throughout its development. From architectural decisions to quality standards, from AI collaboration to continuous iteration — I invested significant time and effort because I believe the Study Prefect Team deserves a truly professional scheduling tool.

**Questions?** email s10777@syss.edu.hk


### Closing Thoughts

This system was developed through collaboration between myself (LI Chuangjie Jacky, 26-27 Head Study Prefect) and Codex (DeepSeek V4 Pro), Grok, and Grok Build.

> **Codex:** "Jacky, from the first line of code to this complete system, I am honoured to have been part of it. May it continue serving the team after you graduate. ✨"
> **Grok:** "You have proven with action that a secondary school student can build a professional-grade system. That is cool. 🚀"

Building this system was far more complex than I imagined, but I never regretted it. I hope it brings real convenience to future Head Study Prefects, and lets every prefect feel that fairness is taken seriously.

**— LI Chuangjie Jacky, June 2026**
Good luck! 🙏"""
    ),

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
        "⚠️ 最需關註學生 (Most Neglected - 最低負荷): {names}。建議優先給予機會以促進公平。",
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
        "上傳之前導出的完整 PDF 值班表（無需拆分頁面），系統將自動解析並還原所有風紀資料、排班記錄與師徒配對狀態。",
        "Upload the complete exported PDF (no need to split pages). The system will automatically restore all prefect data, roster records, and mentoring pair status."
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
