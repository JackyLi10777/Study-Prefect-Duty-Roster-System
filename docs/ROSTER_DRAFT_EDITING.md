# 草稿試算表與全天停開操作 / Draft grid and whole-day closure

> **發布狀態：**`0013_roster_day_closures` 已隨正式 `v1.2.0-rc.52` 上線；本頁同時描述 `codex/rc53-spreadsheet-prefect-motion` 的來源候選，包括 additive `0014_roster_slot_exceptions`、拖放、redo 及單格不開放。正式網站的精確版本、migration 及 Worker 仍只以[目前系統狀態](status/CURRENT_STATUS.md)及即時部署證據為準；`0014` 在完成正式驗證、備份、隔離還原、合併及受控發布前，不應視為已上線。
>
> **Release status:** `0013_roster_day_closures` is live in production `v1.2.0-rc.52`. This page also covers source-only work on `codex/rc53-spreadsheet-prefect-motion`, including additive migration `0014_roster_slot_exceptions`, drag-and-drop, redo, and per-cell unavailability. The exact live release, migration, and Worker remain governed by [current system status](status/CURRENT_STATUS.md) and fresh deployment evidence. Do not treat `0014` as deployed before formal verification, backup, isolated restore, merge, and controlled release.

這個功能讓草稿像試算表一樣直接核對及修改，但所有格子會先留在目前頁面，按「核對並保存」後才以一個交易寫入。逐格點擊不會逐格更新資料庫，也不會改動公平帳本；`history_weight` 仍只在正式發布時按最終有效安排入帳。

This feature makes the draft directly reviewable and editable like a spreadsheet. Cell changes remain on the current page until **Review and save** applies one atomic transaction. Clicking a cell does not perform a database write, and draft edits do not affect the fairness ledger; `history_weight` is posted only when the final valid roster is published.

## 五種穩定狀態 / Five stable states

| 穩定狀態 | 繁體中文顯示 | English display | 意思及操作 |
|---|---|---|---|
| `assigned` | 已安排 | Assigned | 格內有一位合資格導學風紀；姓名在所有語言中保持中文。 |
| `vacant` | 空缺（待安排） | Vacant | 該崗位應當值但尚未有人選，可開啟格子選擇合資格人選。 |
| `room_closed` | 不開放 | Closed | 長期房間政策令該崗位當日不開放，例如 Room 202 星期二及星期五。 |
| `unavailable` | 本週不開放 | Unavailable | 操作員只對所選週次的指定格子停開；它不是空缺，也不會被生成器填入。 |
| `day_closed` | 全天不開放 | Closed all day | 本週指定日期整天停開，該星期欄不可安排任何人。 |

**空白輸入不是第五種狀態。** 清空搜尋框只代表尚未完成搜尋，不會自動刪除原安排、設為空缺或停開。要建立空缺，必須明確選擇「設為空缺」。

**Blank input is not a fifth state.** An empty search field means that the search is unfinished. It never deletes an assignment, creates a vacancy, or closes a day. Choose **Set as vacant** explicitly.

## 生成前設定全天停開 / Close a day before generation

1. 在「值班表」選擇正確的星期一週開始日期。
2. 登記已知請假，並選擇 Assist. in charge 的固定星期或每週靈活模式。
3. 在「本週全天不開放日」選擇公眾假期、學校活動或特別停開的日期；可選一日、多日，或整個星期。
4. 核對停開日及預計移除的安排，再生成草稿。
5. 整星期停開仍可保存及發布零當值週表；服務時數及公平點數均為零。

Whole-day closure is a week-specific override, not a permanent school calendar and not a change to the long-term room policy in `roster_policy`.

## 直接修改草稿 / Edit the draft directly

### 桌面 / Desktop

- 按一下儲存格，或以鍵盤移到格子後按 `Enter`／`F2`，開啟全頁唯一的共用編輯器。
- 輸入任一中文字，系統會按中文姓名、班別、職務及當週規則篩選合法候選；從下拉選單選擇完整姓名。
- 輸入 `X`、`×`、`空缺` 或 `待安排`，會出現明確的「設為空缺」選項。
- 若選中的合資格風紀已在同一天另一格當值，系統可把兩格作原子交換；保存時仍會重新核對所有規則。
- 可把已安排格拖到空缺格作暫存移動，或拖到另一個已安排格作暫存交換；只有超過移動閾值才視為拖放，pointer move 不會寫入資料庫。
- 觸控裝置使用「選擇來源 → 選擇目的地」兩步移動，避免長按與頁面捲動衝突。
- 方向鍵移動焦點；`Space` 進入／完成移動模式；`Escape` 取消；`Ctrl+Z`／`Cmd+Z` 撤銷；`Ctrl+Y` 或 `Ctrl/Cmd+Shift+Z` 重做。
- 「設為單格不開放」會清除該格的暫存安排；重新開放後顯示空缺，不會恢復舊安排。
- 「取消全部」放棄本頁尚未保存的變更；「核對並保存」先檢查整個矩陣，再一次保存。

### 平板及手機 / Tablet and phone

寬度足夠的平板顯示同一矩陣；較窄的平板及手機改為按星期排列的卡片。兩種版面使用同一 `RosterSchedulePresentation`、同一候選過濾及同一批次保存，不會產生另一套排班規則。

## 在草稿內切換全天停開 / Toggle a closed day in a draft

- 每個星期欄首提供「設為全天不開放」快捷操作，滑鼠、`Enter` 及 `Space` 均可使用。
- 尚未保存前再次按下，可立即把暫存狀態還原。
- 關閉已有安排的日期時，確認視窗會列出將移除的草稿安排數量。
- 保存後，該日所有草稿安排會被清除，整欄顯示「全天不開放 / Closed all day」。
- 日後重新開放時，格子會顯示「空缺（待安排）」，不會靜默恢復可能已不再合資格的舊安排。
- 原因代碼及備註均為選填；停開狀態本身必須明確。

## 保存、衝突及復原 / Save, conflict, and recovery

「核對並保存」會以週表版本及穩定命令 ID 執行一個原子交易，重新驗證職務、可值班日、請假、同日重複、連續當值、固定星期 Assist. 規則、全天停開及單格不開放，並建立命令收據、審計及備份義務。網絡重試會沿用同一命令 ID；只有新操作才建立新 ID。任一格失敗時，整批不會部分保存。

如另一分頁或另一位管理員已更新同一草稿，系統不會以最後寫入者覆蓋。畫面會保留本頁輸入並提供：

- **重新載入：**放棄本頁變更並採用最新版本；
- **比較變更：**查看目前輸入與最新版本的差異；
- **重新套用：**在最新版本上重新核對並套用仍有效的修改。

### 誠實等待回饋 / Honest waiting feedback

- 核對及保存若在 140ms 內完成，只顯示按壓／圖標回饋，不閃現載入視窗。
- 超過 140ms 且仍未完成時才顯示 indeterminate 等待狀態；只有後端提供真實事件時才顯示階段名稱，沒有實際 `completed／total` 就不顯示百分比。
- 結果一旦可用便立即呈現，不為動畫加入假進度或最低等待時間。
- 版本衝突、驗證失敗或備份義務未完成時，保留輸入及安全下一步，不以動畫掩蓋結果。

## 發布後限制 / Published-roster restriction

已發布週表不可直接修改格子或全天停開。若整週發布錯誤，先使用「撤回已發布值班表」，讓系統補償公平帳本、保留審計並撤銷分享，再建立正確草稿。若只是發布後有人請假，使用「請假調整」，不要撤回整週。

Published rosters cannot be patched or closed directly. Withdraw an incorrectly published week before generating a corrected draft. Use the published-duty absence workflow for a late absence instead.

## Admin、Guest、PDF 與公開分享 / Parity and boundaries

- Admin 使用正式 SQLite、版本、命令收據、審計及備份義務。
- Guest 使用相同介面、狀態、驗證及批次 API，但只修改有限期記憶體內的虛構工作區；不接觸正式 SQLite、公平帳本、備份或外部分享。
- 網頁、繁中／英文 PDF 及公開分享均由同一呈現模型產生，保持星期、實際日期、英文崗位名稱、服務時間、中文姓名及五種穩定狀態一致。
- PDF 不顯示內部停開原因；全天停開以完整星期欄清楚標示，固定房間停開仍只標示相應房間格。

## 維護者交接 / Maintainer handover

- 已部署 Alembic revision: `0013_roster_day_closures`（additive）。來源候選 revision: `0014_roster_slot_exceptions`（additive）。
- `roster_day_closures` 使用穩定星期代碼，限制每個週表／星期唯一；翻譯文字不是資料庫鍵值。
- `roster_slot_exceptions` 使用穩定資料庫欄位 `day / post_code / slot_index`，限制每週每格唯一；API 的 `cell_key` 內星期代碼會映射至 `day`，原因及備註均為選填。
- 公開型別：`WeekScheduleOverrides`、`DraftCellEdit`、`DraftDayEdit`、`DraftSlotStateEdit`。
- 交易入口：`apply_draft_patch(roster_week_id, expected_week_version, cell_edits, day_edits, slot_edits, reason?, command_id)`。
- 頁面狀態 owner：`nicegui_app/ui/edit_sessions.py::DraftEditSession`。它保存 reviewed baseline、pending cells／days／slots、selection、move source、undo／redo、dirty count、穩定 command ID 及 conflict reapply；`weekly.py` 只負責呈現及把不可變 patch 交給 workflow。
- 共用輸出：`RosterSchedulePresentation`，狀態只限 `assigned / vacant / room_closed / unavailable / day_closed`。
- migration `0014` 上線前必須完成上一 schema 備份、隔離還原及 current-head 恢復基線；舊程式不能對較新 schema 作 code-only rollback。

## 人工驗收清單 / Acceptance checklist

- [ ] 能清楚分辨空白、空缺、固定房間不開放、單格不開放及全天不開放。
- [ ] 中文單字可找到完整中文姓名；下拉只顯示合資格人選。
- [ ] `X`／`×`／`空缺`／`待安排` 只在明確確認後建立空缺。
- [ ] 拖放／觸控兩步移動、原子交換、撤銷、重做、取消全部及整批保存按預期運作。
- [ ] 單日、多日、整週停開，以及重新開放後顯示空缺均正確。
- [ ] 版本衝突保留輸入，並可重新載入、比較或重新套用。
- [ ] 桌面矩陣、手機卡片、PDF 及公開分享內容一致。
- [ ] Guest 完整示範不留下正式或長期資料。
