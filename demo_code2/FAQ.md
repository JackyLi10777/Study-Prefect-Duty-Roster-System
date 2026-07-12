# Sing Yin Study Prefect Duty Roster System — FAQ

**常問問題 Frequently Asked Questions**

---

## 1. 開始使用 Getting Started

### Q1: 如何第一次啟動系統？
打開 Terminal（終端機）或 Command Prompt，輸入以下指令：
```
cd D:\code_v2
pip install -r requirements.txt
python app/main.py
```
然後打開瀏覽器，前往 **http://localhost:8080**。你應該會看到 Dashboard 和每日金句。

### Q2: 系統需要什麼設定？
你需要設定三個環境變數（詳見 `SETUP.md`）：
- `SY_SHEETS_KEY` — Google 服務帳號的 JSON 金鑰檔案路徑
- `SY_SHEETS_ID` — Google Sheets 的試算表 ID
- `SY_DEEPSEEK_KEY` — DeepSeek API 金鑰（AI 功能需要）

如果沒有設定，系統會自動使用本地 CSV 檔案作為資料儲存。

### Q3: Dashboard 上的綠色/紅色圓點是什麼？
這是**系統狀態指示器**：
- 🟢 **Sheets Connected** — Google Sheets 已連接，資料會自動同步
- 🔴 **Sheets Offline** — 使用本地 CSV 模式（資料仍會保存，但不會同步到 Sheets）
- 🟢 **DeepSeek Ready** — AI 功能（智慧解析備註、欄位對應）可用
- 🟡 **DeepSeek Not Set** — AI 功能未設定（不影響排班生成）

### Q4: 如何新增第一批風紀資料？
有三種方式：
1. **從 CSV 匯入**：前往 Prefects 頁面 → 點擊「Import CSV」→ 上傳 CSV 檔案
2. **手動新增**：前往 Prefects 頁面 → 點擊「Add Prefect」→ 填寫表格
3. **使用示範資料**：前往 Prefects 頁面 → 點擊「Load Demo Data」

---

### Q4a: 如何用 CSV 檔案匯入真實風紀資料？
1. 在 Dashboard 先做一次備份（Backup System → 下載 JSON）
2. 準備一個 CSV 檔案，確保欄位名稱正確（參考 HANDOVER.md Section 4）
3. 前往 Prefects 頁面 → 點擊 Import CSV
4. 上傳檔案後，檢查欄位對應預覽表（綠色=AI確認，黃色=別名對應，灰色=未對應）
5. 如有需要，透過下拉選單手動調整對應
6. 確認匯入後，檢查通知訊息中的警告（特別是年級和重複名稱）
7. 前往 Prefects 頁面確認所有風紀資料正確
8. 前往 Roster 頁面生成一次測試排班確認運作正常

## 2. 排班生成 Roster Generation

### Q5: 如何生成本週排班表？
1. 前往 **Roster** 頁面
2. 確認你在「Generate and View」分頁
3. 點擊 **Generate Roster** 按鈕
4. 系統會自動根據公平性原則分配崗位

每次生成後，系統會自動儲存備份到 `data/auto_backups/` 資料夾。

### Q6: Workload Multiplier（工作量倍率）是什麼？
這是一個調整排班公平性的滑桿（0.5x – 2.0x）：
- **1.0x**（預設）：正常模式
- **>1.0x**（例如 1.5x）：考試期間使用，讓每次值班的分數權重更高，優先分配給累計分數較低的風紀
- **<1.0x**（例如 0.8x）：輕鬆週使用，減少分數差距

調整後直接點擊 Generate Roster 即可生效。

### Q7: 生成排班時出現「Only 2 active prefect(s)」怎麼辦？
這表示系統中活躍的風紀人數不足。請前往 **Prefects** 頁面新增更多風紀，確保至少有 3 名活躍風紀。

### Q8: 排班表中出現黃色「slot(s) unfilled」提示是什麼意思？
這表示某些日期/房間的崗位沒有被填滿。可能原因：
- 該日可用的風紀人數不足以填滿所有崗位
- 某些風紀的可用日設定不完整

你可以前往 **Adjust and Edit** 分頁手動調整，或在 Prefects 頁面修改風紀的可用日。

### Q9: 如何在排班表中搜尋特定風紀？
在排班表上方的搜尋框中輸入風紀的英文姓名，系統會即時篩選顯示。

---

## 3. 請假調整與手動編輯 Leave & Adjustment

### Q10: 生成排班後，有風紀請假怎麼辦？
1. 前往 **Roster** 頁面 → **Adjust and Edit** 分頁
2. 在「Leave Adjustment」區塊：
   - 選擇請假的風紀
   - 選擇日期（Day）、房間（Room）、時段（Slot）
   - 可選擇替補人選（Replacement），或留空標記為請假
3. 點擊 **Confirm & Apply Adjustment**

系統會自動撤銷原風紀的點數，並給予替補風紀相應點數。

### Q11: 如何手動交換兩個崗位的風紀？
1. 前往 **Roster** 頁面 → **Adjust and Edit** 分頁
2. 在「Manual Edit / Substitute」區塊：
   - 選擇日期、房間、時段
   - 點擊 **Check Current Assignment** 查看當前值班人
   - 選擇替換人選（系統會按公平性排序建議）
   - 點擊確認交換

### Q12: 調整後，公平性分數會自動更新嗎？
會。每次請假調整或手動交換後，系統會自動：
- 從原風紀撤銷該崗位的分數
- 給予替補風紀相應分數
- 立即更新 Dashboard 上的公平性圖表

---

## 4. 匯出與報表 Export & Reports

### Q13: 如何匯出排班表 PDF？
在 **Generate and View** 分頁，點擊 **Export PDF/HTML** 按鈕。系統會生成一份專業格式的 HTML 檔案（可直接用瀏覽器開啟或列印為 PDF）。

### Q14: PDF 上沒有顯示校徽怎麼辦？
確認以下兩項：
1. `logo.png` 檔案存在於專案資料夾（`D:\code_v2\logo.png`）
2. Dashboard 上的「Show Logo on PDF」開關是開啟的

### Q15: 可以匯出過往週次的排班表嗎？
可以。在 Roster 頁面下方的「Roster Version History」區塊，可以查看過往生成的版本。選擇版本後可以匯出。

---

## 5. 資料管理與備份 Data & Backup

### Q16: 我的資料會丟失嗎？
不會。系統有三重保護：
1. **Google Sheets**（主要儲存）— 資料即時同步到雲端
2. **CSV 檔案**（本地備份）— 每次儲存都會同時寫入 CSV
3. **自動備份**（`data/auto_backups/`）— 每次生成排班都會自動儲存 JSON 備份

### Q17: 如何手動備份系統？
前往 Dashboard → 點擊 **Backup System** 按鈕。系統會下載一份完整的 JSON 備份檔案。

### Q18: 如何從備份還原？
前往 Dashboard → 點擊 **Restore from Backup** → 上傳之前下載的 JSON 備份檔案。系統會驗證備份內容後恢復資料。

### Q19: Google Sheets 無法連接時怎麼辦？
系統會自動切換到 CSV 模式。Dashboard 上的狀態指示器會顯示「Sheets Offline」。你的資料仍會保存在本地 CSV 檔案中，不會丟失。

---

## 6. 權限與角色 Permissions & Roles

### Q20: AHP（Assistant Head Study Prefect）和普通 Study Prefect 有什麼區別？
- **AHP**：可以擔任「Assist. in charge」領導崗位（每天 1 個，每週 5 個）。每位 AHP 每週最多擔任 1 次。
- **Study Prefect**：只能擔任 Room 302/303/202 的房間值班。

系統會自動確保 AHP 不會被分配到普通房間，普通風紀也不會被分配到 AHP 崗位。

### Q21: Room 202 為什麼星期二和星期五沒有排班？
Room 202（F1 Study Group）在星期二和星期五**固定關閉**。這是學校政策，系統會自動遵守。

---

## 7. 疑難排解 Troubleshooting

### Q22: 點擊 Generate Roster 沒有反應？
可能原因：
- 風紀人數不足（需要至少 3 名活躍風紀）
- 系統正在生成中（請等待上一次生成完成）

查看畫面上的通知訊息，系統會提示具體原因和解決方法。

### Q23: AI Parse Remarks 沒有反應？
確認以下兩項：
1. `SY_DEEPSEEK_KEY` 環境變數已設定
2. Dashboard 上的 DeepSeek 狀態指示器是綠色

如果 DeepSeek 未設定，你仍可以手動編輯風紀的「fixed_general_duty」和「available」欄位。

### Q24: 匯出的 HTML 檔案排版很奇怪？
HTML 匯出使用 Professional Teal 設計系統的樣式。如果在某些瀏覽器中顯示異常，請嘗試使用 Chrome 或 Edge 開啟。你也可以使用瀏覽器的「列印」功能將 HTML 儲存為 PDF。

### Q25: 我想更換校徽，要怎麼做？
將新的校徽圖片命名為 `logo.png`，放入專案資料夾（`D:\code_v2\logo.png`），覆蓋舊檔案即可。Dashboard 上的「Show Logo on PDF」開關控制是否在匯出時顯示校徽。

---

## 附錄：常用快捷操作 Cheat Sheet

| 操作 | 路徑 |
|------|------|
| 生成本週排班 | Roster → Generate and View → Generate Roster |
| 處理請假 | Roster → Adjust and Edit → Leave Adjustment |
| 手動交換崗位 | Roster → Adjust and Edit → Manual Edit |
| 匯出排班表 | Roster → Generate and View → Export PDF/HTML |
| 新增風紀 | Prefects → Add Prefect |
| AI 解析備註 | Prefects → AI Parse Remarks |
| 匯入 CSV | Prefects → Import CSV |
| 備份系統 | Dashboard → Backup System |
| 還原備份 | Dashboard → Restore from Backup |
| 查看公平性 | Dashboard → Fairness Chart |
| 查看師徒配對 | Dashboard → Mentoring Pairs |

---

*此 FAQ 會隨著系統更新和實際使用反饋持續完善。如有新問題，請聯繫 Head Study Prefect。*
*Last updated: 2026-06-29*
