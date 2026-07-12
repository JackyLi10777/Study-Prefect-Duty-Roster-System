# 聖言中學導學風紀當值排班平台 — 使用手冊

**User Manual / 使用手冊**
**Version:** 1.0
**Date:** 2026-06-29
**Language:** 繁體中文

---

## 目錄

1. [系統簡介](#1-系統簡介)
2. [儀表板 Dashboard](#2-儀表板-dashboard)
3. [風紀管理 Prefects](#3-風紀管理-prefects)
4. [排班生成 Roster](#4-排班生成-roster)
5. [請假調整 Leave Adjustment](#5-請假調整-leave-adjustment)
6. [手動編輯 Manual Edit](#6-手動編輯-manual-edit)
7. [匯出排班表 Export](#7-匯出排班表-export)
8. [備份與還原 Backup](#8-備份與還原-backup)
9. [AI 智慧功能](#9-ai-智慧功能)
10. [常見問題](#10-常見問題)

---

## 1. 系統簡介

### 這是什麼系統？

聖言中學導學風紀當值排班平台是一個**專業的排班管理工具**，專門為導學風紀團隊設計。它能：

- **自動生成公平的每週值班表**：根據每位風紀的歷史工作量，自動分配值班崗位
- **處理臨時請假**：值班表發布後，如果有人請假，可以快速調整並重新計算公平性
- **匯出專業排班表**：生成 PDF/HTML 格式的值班表，方便在群組分享
- **永久保存資料**：所有資料儲存在 Google Sheets，不會因為電腦重啟而丟失

### 誰應該使用這個系統？

- **首席導學風紀（Head Study Prefect）**：負責每週生成和調整值班表
- **助理首席導學風紀（AHP）**：協助檢查值班表和處理請假

### 如何啟動系統？

```bash
cd D:\code_v2
python app/main.py
# 打開瀏覽器，前往 http://localhost:8080
```

---

## 2. 儀表板 Dashboard

Dashboard 是你打開系統後看到的第一個頁面。它分為三個區域：

### 每日金句（上方大區塊）

每天顯示一節聖經經文（中英對照），提醒我們以僕人領袖的心態服事。經文每天自動更換。

### 系統狀態（金句下方的小圓點）

- 🟢 **Sheets Connected**：Google Sheets 已連接，資料安全
- 🔴 **Sheets Offline**：使用本地 CSV 模式（資料仍會保存）
- 🟢 **DeepSeek Ready**：AI 功能可用
- 🟡 **DeepSeek Not Set**：AI 功能未設定（不影響排班）

### 操作概覽（下方卡片）

- **KPI 卡片**：顯示活躍風紀人數、AHP 人數、平均工作量
- **公平性圖表**：長條圖顯示每位風紀的累計工作量，越短的代表越需要被分配值班
- **師徒配對**：顯示本週的師徒配對情況
- **快速操作**：一鍵前往排班、風紀管理、審計記錄
- **備份與還原**：手動備份或恢復系統資料

---

## 3. 風紀管理 Prefects

Prefects 頁面用於管理所有風紀的資料。

### 如何新增風紀？

1. 點擊 **Add Prefect** 按鈕
2. 填寫姓名（英文）、中文姓名、年級、班級、職級
3. 勾選可值班的日子
4. 點擊 **Save**

### 如何大量匯入風紀？

1. 準備一個 CSV 檔案（可以用 Excel 編輯）
2. 點擊 **Import CSV** 按鈕
3. 上傳檔案後，系統會顯示**欄位對應預覽表**，彩色徽章顯示 AI 信心度（綠色=AI，黃色=別名，灰色=未對應）
4. 你可以透過下拉選單手動調整任何欄位對應
5. 確認無誤後，點擊**確認匯入**

### AI 解析備註

1. 在風紀的 Remarks 欄位填寫需求，例如：「固定星期一 Room 302，只可星期三和五值班」
2. 點擊 **AI Parse Remarks** 按鈕
3. 系統會自動解析並建議更新「固定值班日」和「可用日」
4. 你可以選擇性套用這些建議

### 欄位說明

| 欄位 | 說明 | 範例 |
|------|------|------|
| Name | 英文姓名 | CHAN Tai Man |
| Name (中文) | 中文姓名 | 陳大文 |
| Form | 年級 | F5 |
| Class | 班級 | 5A |
| Role | 職級 | Study Prefect / Assistant Head Study Prefect |
| Available Days | 可值班的日子 | MON,TUE,WED,THU,FRI |
| History Weight | 累計工作量分數（系統自動更新） | 3.5 |
| Remarks | 備註（可供 AI 解析） | 固定星期一 Room 302 |

---

## 4. 排班生成 Roster

Roster 頁面分為兩個分頁（Tab）：

### Generate and View（生成與檢視）

**Workload Multiplier（工作量倍率）：**
- 預設值為 **1.0x**（正常模式）
- 考試期間可以調高（例如 **1.5x**），讓每次值班的分數權重更高，優先分配給累計分數較低的風紀
- 輕鬆週可以調低（例如 **0.8x**）
- 調整後點擊 Generate Roster 即可生效

**Generate Roster（生成排班）：**
- 點擊後系統會自動根據公平性原則分配崗位
- AHP 只會被分配到 Assist. in charge 崗位
- 普通風紀只會被分配到 Room 302/303/202
- Room 202 星期二和星期五自動關閉

**搜尋風紀：**
- 在搜尋框中輸入姓名，可以快速找到特定風紀的值班安排

**空位提示：**
- 如果有崗位未能填滿，會顯示黃色提示
- 可能原因：該日可用的風紀人數不足

### Adjust and Edit（調整與編輯）

詳見第 5 節（請假調整）和第 6 節（手動編輯）。

---

## 5. 請假調整 Leave Adjustment

當值班表發布後，如果有風紀臨時請假，你可以使用此功能調整。

### 操作步驟

1. 前往 Roster → **Adjust and Edit** 分頁
2. 展開 **Leave Adjustment** 區塊
3. **選擇請假的風紀**：從下拉選單選擇
4. **選擇日期、房間、時段**：指定要調整的崗位
5. **選擇替補人選（可選）**：如果不選，該崗位會標記為「請假」
6. 點擊 **Confirm & Apply Adjustment**

### 公平性影響

- 原風紀的分數會被撤銷
- 替補風紀會獲得相應分數
- Dashboard 上的公平性圖表會即時更新

---

## 6. 手動編輯 Manual Edit

如果你需要手動交換任何崗位的風紀，可以使用此功能。

### 操作步驟

1. 前往 Roster → **Adjust and Edit** 分頁
2. 展開 **Manual Edit / Substitute** 區塊
3. 選擇日期、房間、時段
4. 點擊 **Check Current Assignment** 查看當前值班人
5. 系統會顯示**智能建議**的替補人選（按公平性排序，工作量最低的優先）
6. 選擇替換人選，確認交換

---

## 7. 匯出排班表 Export

### 如何匯出？

在 **Generate and View** 分頁，點擊 **Export PDF/HTML** 按鈕。系統會生成一份專業格式的 HTML 檔案。

### HTML 檔案如何使用？

- 用瀏覽器（Chrome / Edge）開啟
- 可以直接列印為 PDF（檔案 → 列印 → 另存為 PDF）
- 可以分享到 WhatsApp / Signal 群組

### 校徽設定

- 將校徽圖片命名為 `logo.png`，放入專案資料夾
- Dashboard 上的 **Show Logo on PDF** 開關控制是否在匯出時顯示校徽

---

## 8. 備份與還原 Backup

### 系統如何保護你的資料？

系統有三重保護：

1. **Google Sheets**（主要儲存）— 即時同步到雲端
2. **CSV 檔案**（本地備份）— 每次儲存都會同時寫入
3. **自動備份**（`data/auto_backups/`）— 每次生成排班都會自動儲存

### 手動備份

Dashboard → **Backup System** → 下載 JSON 備份檔案

### 從備份還原

Dashboard → **Restore from Backup** → 上傳 JSON 備份檔案

---

## 9. AI 智慧功能

### AI 解析備註（AI Parse Remarks）

在 Prefects 頁面使用。當你在 Remarks 欄位填寫自然語言描述（例如「固定星期一 Room 302」），AI 會自動解析並建議更新「固定值班日」和「可用日」。

### AI 欄位對應（AI Column Mapping）

在匯入 CSV 時自動啟用。AI 會嘗試識別 CSV 檔案中的欄位名稱，自動對應到系統的標準欄位。

### AI 功能需要什麼？

需要設定 `SY_DEEPSEEK_KEY` 環境變數（DeepSeek API 金鑰）。如果沒有設定，AI 功能不會運作，但不影響排班生成。

---

## 10. 常見問題

更詳細的常見問題請參閱 **FAQ.md**。

### 快速問答

**Q: 為什麼生成了排班但有些崗位是空的？**
A: 可能是該日可用的風紀人數不足。檢查 Dashboard 的 KPI 卡片，確認活躍風紀人數。你可以前往 Prefects 頁面新增更多風紀，或修改風紀的可用日。

**Q: 工作量倍率應該設多少？**
A: 正常週設 1.0x。考試週設 1.3x–1.5x，讓工作量較低的風紀優先被分配。輕鬆週設 0.8x。

**Q: Google Sheets 無法連接怎麼辦？**
A: 系統會自動切換到 CSV 模式。Dashboard 上的狀態指示器會顯示紅色。你的資料仍會保存在本地 CSV 檔案中。請檢查 `SY_SHEETS_KEY` 和 `SY_SHEETS_ID` 是否正確設定。

**Q: 如何永久刪除一個風紀？**
A: 前往 Prefects 頁面，將該風紀的 Active 設定為關閉，或直接在 Google Sheets 中刪除該行。

---

*此使用手冊會隨著系統更新持續完善。如有疑問，請聯繫首席導學風紀。*
*Last updated: 2026-06-29*
