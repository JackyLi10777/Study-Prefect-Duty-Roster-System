
   # 聖言中學 Study Prefect 值日編排系統 — 使用指南

   **版本：** 1.0
   **日期：** 2026-06-27
   **對象：** Head Study Prefect（現任及接任者）
   **語言：** 繁體中文

   ---

   ## 目錄

   1. [系統簡介](#1-系統簡介)
   2. [系統啟動與首次使用](#2-系統啟動與首次使用)
   3. [使用 Demo Data 練習完整流程](#3-使用-demo-data-練習完整流程)（強烈建議新手先做）
   4. [導入真實 Prefect 資料](#4-導入真實-prefect-資料)
   5. [每週生成值日表——標準操作流程](#5-每週生成值日表標準操作流程)
   6. [請假調整與手動替補](#6-請假調整與手動替補)
   7. [匯出與分享 Roster](#7-匯出與分享-roster)
   8. [資料備份與還原](#8-資料備份與還原)
   9. [常見問題與排除](#9-常見問題與排除)
   10. [附錄：快速參考卡](#10-附錄快速參考卡)

   ---

   ## 1. 系統簡介

   這套系統是為聖言中學 Study Prefect 團隊設計的**每週值日編排工具**。它能根據公平性演算法自動分配值日崗位、處理突發請假、匯出專業排班表 PDF，讓 Head Study Prefect 從繁瑣的手動排班中解放出來。

   ### 你能用它做什麼

   | 功能 | 說明 |
   |------|------|
   | **自動生成值日表** | 一鍵生成每週五天（星期一至五）的完整值日安排 |
   | **請假調整** | 已發布的排班有人請假？系統自動推薦替補人選 |
   | **手動調換** | 直接拖放或選擇調換任何崗位的人選 |
   | **匯出 PDF** | 生成中英雙語、附校徽的專業排班表，可直接分享到群組 |
   | **公平性追蹤** | Dashboard 顯示每位 prefect 的累積工作量，確保沒人被過度編排 |
   | **AI 智慧匯入** | 上傳 CSV 後，AI 自動辨識欄位、解析備註中的固定值日資訊 |
   | **Google Sheets 同步** | 所有資料即時同步到 Google Sheets，手機也能查看和編輯 |
   | **備份與還原** | 一鍵下載完整備份，任何錯誤操作都能秒速還原 |

   ### 三個主要頁面

   - **Dashboard**（首頁）— 每日金句、系統狀態、備份、公平性圖表
   - **Roster**（值日表）— 生成排班、查看、請假調整、匯出
   - **Prefects**（風紀管理）— 新增/編輯/刪除 prefect、CSV 匯入、AI 解析

   ---

   ## 2. 系統啟動與首次使用

   ### 2.1 啟動系統

   1. 打開 **Terminal**（終端機）或 **Command Prompt**（命令提示字元）。
      > 💡 在 Windows 上：按 `Win + R`，輸入 `cmd`，按 Enter。

   2. 輸入以下指令，切換到專案資料夾：
      ```
      cd D:\code_v2
      ```

   3. 啟動應用程式：
      ```
      python app/main.py
      ```

   4. 看到類似以下的輸出後，打開瀏覽器：
      ```
      NiceGUI ready to go on http://localhost:8080
      ```

   5. 在瀏覽器網址列輸入 **`http://localhost:8080`**，按 Enter。

   > 🔒 **注意**：啟動後，Terminal 視窗**不要關閉**。關閉視窗 = 系統停止。每天使用完畢後再關閉即可。

   ### 2.2 首次看到的畫面

   系統啟動後，你會看到 **Dashboard** 頁面，分為兩個區域：

   - **上方金色框框**：每日金句（中英對照聖經經文，每天自動更換）
   - **下方操作區**：系統狀態指示燈、備份系統、公平性圖表等

   ### 2.3 認識系統狀態指示燈

   Dashboard 上有幾個彩色圓點，它們告訴你係統當前的健康狀態：

   | 指示燈 | 綠色代表 | 紅色/黃色代表 |
   |--------|---------|-------------|
   | **Sheets** | Google Sheets 已連線，資料自動同步 | 未設定或未連線（系統會改用本地 CSV 儲存，資料不會遺失） |
   | **DeepSeek** | AI 功能可用（智慧解析備註） | 未設定（不影響排班生成，僅 AI 功能暫停） |

   > 🟢 兩個都綠色 = 完美。🔴 Sheets 紅色 = 仍可使用，但建議參考 SETUP.md 設定。

   ### 2.4 導覽列

   頁面頂部有導覽列，點擊可在三個頁面之間切換：
   - **Dashboard** — 首頁
   - **Roster** — 值日表管理
   - **Prefects** — 風紀管理

   ---

   ## 3. 使用 Demo Data 練習完整流程

   > 🎯 **強烈建議新手先走完這一節。** 用示範資料跑完整個流程只需要 5–10 分鐘，能讓你對系統有全面認識，減少正式操作時的緊張感。

   ### 3.1 載入示範資料

   1. 點擊導覽列的 **Prefects**
   2. 點擊 **Load Demo Data** 按鈕
   3. 系統會彈出確認視窗，點擊確認
   4. 你會看到表格中出現 11 位示範 prefect（含 2 位 AHP、9 位 Study Prefect）

   ### 3.2 生成第一份值日表

   1. 點擊導覽列的 **Roster**
   2. 確認你在 **Generate and View** 分頁（預設已選中）
   3. 點擊綠色的 **Generate Roster** 按鈕
   4. 等待幾秒鐘，值日表會出現在下方

   **你會看到：**
   - 一個 5 欄（星期一至五）的表格
   - 每天有 5–6 個崗位被填滿（AHP 崗位 + Room 302/303/202）
   - 星期二和星期五的 Room 202 顯示為 `—`（因為 Room 202 這兩天不開放）
   - AHP 只出現在 "Assist. in charge" 崗位上

> ✅ **驗證清單：生成後請逐項檢查**
>
> | ✅ | 檢查項目 | 你應該看到 |
> |-----|---------|----------|
> | ☐ | AHP 崗位 | Mon–Fri 每天 1 位 AHP，且盡量是不同人 |
> | ☐ | Room 202 | Tue 和 Fri 為空（—），Mon/Wed/Thu 各 2 人 |
> | ☐ | Room 302 | 每天 1 人 |
> | ☐ | Room 303 | 每天 2 人（不同人） |
> | ☐ | 無連續排班 | 同一人不會出現在連續兩天 |
> | ☐ | 無紅色錯誤 | 所有通知都是綠色或藍色，沒有紅色錯誤訊息 |
>
> ⚠️ 如果以上任何一項不符合，代表 Demo Data 可能有問題或系統設定需要調整。
   ### 3.3 查看公平性

   回到 **Dashboard**，往下捲動，你會看到：
   - **Fairness Chart**：每位 prefect 的累積工作量長條圖
   - **Mentoring Pairs**：系統自動配對的「指導組合」（senior + junior）

   這就是每週生成排班後你應該檢查的東西。

   ### 3.4 匯出試試看

   1. 回到 **Roster** → **Generate and View** 分頁
   2. 點擊 **Export PDF** 或 **Export HTML**
   3. 瀏覽器會下載一個檔案
   4. 打開 PDF 看看——這就是最終分享給 prefect 團隊的排班表

   ### 3.5 練習備份與還原

   1. 回到 **Dashboard**
   2. 在 **Backup System** 區塊點擊 **Download Backup**，會下載一個 `.json` 檔案
   3. 這就是你的完整備份。把它存到安全的地方
   4. 如果想練習還原：點擊 **Restore from Backup** → 上傳剛才的 `.json` 檔案 → 系統會恢復到備份時的狀態

   > ✅ 恭喜！你已經完成了一次完整的操作流程。準備好後，可以進入下一步——導入真實資料。

> 🎉 **恭喜！你已經完成了 Demo Data 的完整練習。**
>
> 你現在已經知道：
> - ✅ 如何生成一份值日表
> - ✅ 如何檢查 AHP 崗位和房間分配是否正確
> - ✅ 如何匯出 PDF 給 prefect 團隊
> - ✅ 如何備份和還原資料
>
> 這些技能**完全一樣**適用於真實資料。唯一的區別是——真實資料裡的是你認識的同學的名字。
>
> **準備好導入真實資料了嗎？** 往下看 Section 4，我們會一步一步帶你完成。
   ---

   ## 4. 導入真實 Prefect 資料

> ⚠️ **安全第一！在開始之前，請務必先做備份！**
> Dashboard → Backup System → Download Backup。
> 這樣即使導入過程出錯，你也可以在 **10 秒內**一鍵還原到導入前的狀態。
>
> **為什麼這一步這麼重要？** 導入 CSV 會完全覆蓋當前資料。有了備份，你就擁有了一張「安全網」——任何操作都可以後悔、都可以回頭。
>
   > ⚠️ **在開始之前，請務必先做備份！** Dashboard → Backup System → Download Backup。這樣即使導入過程出錯，你也可以一鍵還原。

   ### 4.1 準備你的 CSV 檔案

>
> ✅ **匯入前最後確認清單（逐項打勾後再繼續）**
>
> - [ ] **已完成備份** — Dashboard → Backup System → Download Backup（非選項，是必須！）
> - [ ] **已用 Demo Data 練習過** — 載入 → 生成排班 → 調整 → 匯出 → 備份
> - [ ] **CSV 檔案欄位名稱正確** — name, form, class_name, role, available_days
> - [ ] **年級格式正確** — F3 / F4 / F5（不是 F.3 / Form 3）
> - [ ] **角色名稱正確** — Study Prefect / Assistant Head Study Prefect / Head Study Prefect
> - [ ] **沒有重複名稱** — CSV 中每位 prefect 的 name 欄位都是唯一的
> - [ ] **可用日格式正確** — MON,TUE,WED,THU,FRI（大寫，逗號分隔）
> - [ ] **我知道如何還原** — Dashboard → Restore from Backup → 上傳備份檔
>
> ⚠️ 如果以上任何一項無法打勾，請**先解決後再匯入**，不要冒險跳過。

   用 Excel 或 Google Sheets 建立一個 CSV 檔案，包含以下欄位（有 `*` 的是必填）：

   | 欄位名稱 | 必填 | 範例 | 注意事項 |
   |---------|------|------|---------|
   | `name` | ✅ | `CHAN Tai Man` | 英文全名，不可重複 |
   | `name_zh` | | `陳大文` | 中文名 |
   | `form` | ✅ | `F5` | 必須是 F3、F4、F5（不要寫 F.5） |
   | `class_name` | ✅ | `5A` | 班級 |
   | `role` | ✅ | `Study Prefect` | 三選一：`Study Prefect`、`Assistant Head Study Prefect`、`Head Study Prefect` |
   | `available_days` | | `MON,TUE,WED,THU,FRI` | 大寫英文，逗號分隔 |
   | `history_weight` | | `0` | 新 prefect 填 0 |
   | `remarks` | | `固定星期一 Room 302` | 可用中文，AI 會自動解析 |
   | `date_joined` | | `2026-09-01` | 日期格式 YYYY-MM-DD |
   | `active` | | `true` | `true` 或 `false` |

   ### 4.2 執行導入——逐步操作

   1. **做備份**（跳過這步的後果自負！）：
      - Dashboard → Backup System → Download Backup
      - 把下載的 `.json` 檔案存好，命名為 `backup_before_import.json`

   2. **前往 Prefects 頁面** → 點擊 **Import CSV**

   3. **上傳你的 CSV 檔案**

   4. **檢查欄位對應預覽表**：
      - 🟢 **綠色** = AI 高度確信對應正確
      - 🟡 **黃色** = 系統根據名稱相似度推測的對應
      - ⬜ **灰色** = 未對應——你需要手動從下拉選單選擇正確欄位

      > 🔍 仔細檢查每一欄的對應是否正確。特別是 `role` 和 `form`——這兩個錯會直接影響排班結果。

   5. **修正錯誤對應**：點擊灰色或黃色欄位的下拉選單，選擇正確的欄位名稱

   6. **點擊「確認匯入 (Confirm Import)」**

   7. **閱讀匯入結果通知**：
      - 導入了多少人？
      - 有沒有「年級格式不正確」的警告？（這些 prefect 被自動設為 F4，需要手動修正）
      - 有沒有「重複名稱」的警告？（重複的 prefect 被跳過了）

   8. **驗證資料**：
      - 回到 Prefects 頁面，檢查表格中的所有 prefect
      - 姓名、角色、年級是否都正確？
      - AHP 的角色是否顯示為 "Assistant Head Study Prefect"？
      - 年級是否都是 F3/F4/F5（不應該全部是 F4）？

   9. **測試生成排班**：
      - 前往 Roster → Generate and View → Generate Roster
      - 如果能成功生成沒有報錯，說明導入成功！

   10. **再做一次備份**：
       - Dashboard → Backup System → Download Backup
       - 命名為 `backup_after_import.json`

   ### 4.3 如果導入失敗了怎麼辦？

   **不要慌！** 因為你在第 1 步做了備份。

   1. Dashboard → **Restore from Backup**
   2. 上傳 `backup_before_import.json`
   3. 系統會在 10 秒內恢復到導入前的狀態
   4. 檢查 CSV 檔案中的問題，修正後再試一次

   > 🔑 **核心原則：每次導入前必做備份。只要遵守這條規則，資料永遠不會永久遺失。**

   ---

   ## 5. 每週生成值日表——標準操作流程

   這是每週最重要的例行工作，整個流程只需 **2–3 分鐘**。

   ### 5.1 啟動系統

   ```bash
   cd D:\code_v2
   python app/main.py
   ```
   打開瀏覽器 → `http://localhost:8080`

   ### 5.2 檢查系統狀態

   在 Dashboard 確認：
   - 🟢 Sheets Connected（綠色 = Google Sheets 同步中）
   - 🟢 DeepSeek Ready（綠色 = AI 功能可用；黃色也可以，不影響排班）

   ### 5.3 生成本週值日表

   1. 點擊導覽列的 **Roster**
   2. 確認在 **Generate and View** 分頁
   3. 點擊 **Generate Roster** 按鈕
   4. 等待 2–5 秒，值日表出現

   ### 5.4 檢查值日表

   生成後，請逐項檢查：

   | 檢查項目 | 正常情況 |
   |---------|---------|
   | **AHP 崗位** | 星期一至五每天 1 個 AHP，且 5 天盡量是不同人 |
   | **Room 202** | 星期二和星期五為空（`—`），星期一三四各 2 人 |
   | **Room 302** | 每天 1 人 |
   | **Room 303** | 每天 2 人（兩人不同） |
   | **同一人不連續兩天** | 不應出現同一 prefect 星期一和星期二都被排班 |
   | **空缺提示** | 如果某天某崗位顯示黃色警告，代表該時段人手不足 |

   ### 5.5 查看公平性

   回到 Dashboard，往下捲動查看 Fairness Chart：
   - 新加入的 prefect（`history_weight` 較低）應該會比資深 prefect 被分配到更多崗位
   - 如果某位 prefect 的長條明顯過高或過低，可能需要在 Remarks 欄位調整其可用日

   ### 5.6 匯出並分享

   1. Roster → Generate and View → 點擊 **Export PDF**
   2. 下載 PDF 後，分享到 Study Prefect 群組
   3. （可選）也可以匯出 HTML 版本，方便手機查看

   ---

   ## 6. 請假調整與手動替補

   值日表發布後，偶爾會有 prefect 臨時請假。系統提供兩種處理方式。

   ### 6.1 請假調整（Leave Adjustment）

   當有 prefect 告知某天無法值日時：

   1. 前往 **Roster** → **Adjust and Edit** 分頁
   2. 在 **Leave Adjustment** 區塊：
      - 從下拉選單選擇**請假的 prefect**
      - 選擇**請假日期**（星期幾）
   3. 點擊 **Apply Leave**
   4. 系統會自動：
      - 將該 prefect 從當天崗位移除
      - 從可用名單中推薦最合適的替補人選
      - 顯示替補人選的當前負荷量，幫助你判斷
   5. 確認替補人選，點擊 **Confirm Substitute**

   > 💡 系統推薦替補的邏輯：優先選擇當天有空、且累積負荷最低的 prefect。

   ### 6.2 手動調換（Manual Edit）

   如果需要手動調整（例如兩位 prefect 互換崗位）：

   1. 前往 **Roster** → **Adjust and Edit** 分頁
   2. 在 **Manual Edit / Substitute** 區塊：
      - 選擇要**替換的崗位**（星期幾 + Room）
      - 選擇**新的 prefect**
   3. 點擊 **Apply Change**
   4. 變更立即生效，值日表會自動更新

   ### 6.3 調整後的檢查

   每次調整後請確認：
   - 被替換的 prefect 確實從崗位移除
   - 新指派的 prefect 當天沒有其他崗位（同一天不應被排兩個崗位）
   - 如果調整後出現空缺（黃色警告），表示需要再安排其他人

   > ⚠️ 請假調整**不會**自動更新公平性權重（`history_weight`）。如果你希望請假不計入該 prefect 的累積負荷，需要在 Prefects 頁面手動修改其 `history_weight`。

   ---

   ## 7. 匯出與分享 Roster

   ### 7.1 匯出 PDF（推薦）

   1. Roster → Generate and View → 點擊 **Export PDF**
   2. 瀏覽器會下載一個 PDF 檔案（命名格式：`roster_YYYY-MM-DD.pdf`）
   3. PDF 包含：
      - 聖言中學校徽（如果 `logo.png` 存在於專案資料夾）
      - 中英雙語的執行摘要
      - 完整的五天值日表
      - 日期範圍和生成時間

   ### 7.2 匯出 HTML

   1. 點擊 **Export HTML**
   2. 適合在手機上查看，或貼到學校網頁

   ### 7.3 分享方式

   - **WhatsApp / Telegram 群組**：直接上傳 PDF 檔案
   - **Google Classroom**：上傳 PDF 到課堂資源區
   - **列印**：PDF 格式適合直接列印，建議使用 A4 紙張

   ### 7.4 自訂匯出選項

   在 Dashboard 上可以設定：
   - **Show Logo on PDF**：是否在 PDF 上顯示校徽（預設開啟）
   - **Include Backup Data**：是否在 PDF 附錄中包含 JSON 備份資料（預設關閉，僅供內部使用）

   ---

   ## 8. 資料備份與還原

   系統有三層資料保護機制，層層把關，確保你的資料不會遺失。

   ### 8.1 三層保護機制

   | 層級 | 儲存位置 | 更新頻率 | 用途 |
   |------|---------|---------|------|
   | **Google Sheets** | 雲端試算表 | 即時同步 | 主要資料儲存，手機也能查看 |
   | **CSV 檔案** | `data/prefects.csv` | 每次儲存 | 本地備份，即使沒有網路也能用 |
   | **JSON 備份** | 手動下載 / 自動備份 | 每次生成排班 | 完整快照，包含歷史記錄 |

   ### 8.2 手動備份（建議每週做）

   1. Dashboard → **Backup System**
   2. 點擊 **Download Backup**
   3. 瀏覽器會下載一個 `.json` 檔案
   4. 把它存到安全的地方（例如命名為 `backup_2026-06-27.json`）

   > 💡 建議每週生成排班後順手做一次備份。只需 5 秒鐘。

   ### 8.3 自動備份

   每次點擊 **Generate Roster** 時，系統會自動在 `data/auto_backups/` 資料夾儲存一份備份，命名格式為 `roster_YYYY-MM-DD.json`。建議保留最近 10–20 份，定期清理舊檔案。

   ### 8.4 還原資料

   如果需要恢復到之前的狀態：

   1. Dashboard → **Restore from Backup**
   2. 點擊 **Upload** 並選擇你的備份 `.json` 檔案
   3. 系統會先驗證備份檔案是否有效
   4. 確認無誤後，點擊 **Restore**
   5. 所有資料（prefect 名單、歷史權重、排班記錄）會在幾秒內恢復

   > ⚠️ 還原**會覆蓋當前資料**。如果你不確定當前資料是否需要保留，請先做一次備份再還原。

   ### 8.5 災難恢復

   如果發生最壞情況（例如電腦損壞、檔案誤刪）：

   1. 檢查 `data/auto_backups/` 中最近的自動備份
   2. 如果自動備份也不在了，檢查你的 Google Sheets——所有 prefect 資料都在雲端
   3. 從 Google Sheets 重新匯出 CSV，再用 Import CSV 功能匯入
   4. 最後手段：檢查你手動下載的備份檔案

   只要你有定期做備份，資料就不會永久遺失。

   ---

   ## 9. 常見問題與排除

   ### Q1：應用程式無法啟動

   **症狀：** 輸入 `python app/main.py` 後出現錯誤訊息。

   **解決方案：**
   1. 確認 Python 已安裝：打開 Terminal，輸入 `python --version`，應顯示 3.12 或以上
   2. 確認依賴套件已安裝：`pip install -r requirements.txt`
   3. 確認在正確的資料夾：`cd D:\code_v2`

   ### Q2：Generate Roster 按鈕沒有反應

   **可能原因：**
   - 活躍的 prefect 人數少於 3 人（系統最低要求）
   - 所有 prefect 的可用日都設為空

   **解決方案：**
   1. 前往 Prefects 頁面，確認至少有 3 位 `active: true` 的 prefect
   2. 確認每位 prefect 的 `available_days` 欄位不為空（例如 `MON,TUE,WED,THU,FRI`）

   ### Q3：某位 prefect 從來沒有被排班

   **可能原因：**
   - 該 prefect 的可用日太少（例如只設了 `MON`，但星期一剛好不需要那麼多人）
   - 該 prefect 是 AHP，但 AHP 崗位已被其他 AHP 佔用（每週 5 個 AHP 崗位，由所有 AHP 輪流）

   **解決方案：**
   1. 前往 Prefects 頁面，檢查該 prefect 的 `available_days`
   2. 如果需要，增加其可用日
   3. 如果他們確實只能在特定日子值日，可以在 `remarks` 中加入「固定星期X Room XXX」，然後使用 AI Parse Remarks

   ### Q4：星期二或星期五 Room 202 有人被排班

   **這是 bug。** Room 202 在星期二和星期五是不開放的。

   **解決方案：**
   1. 截圖存證
   2. 手動在 Adjust and Edit 分頁移除該指派
   3. 回報問題給系統維護者

   ### Q5：Google Sheets 狀態顯示紅燈

   **這不影響系統使用。** 系統會自動切換到本地 CSV 模式。

   **如果你希望修復 Sheets 連線：**
   1. 確認 `service_account.json` 存在於 `D:\code_v2\`
   2. 確認 Google Sheet 已分享給 service account 的 email（`study-prefect-duty-roster@...`）
   3. 確認 `.env` 中的 `SY_SHEETS_ID` 正確

   ### Q6：AI Parse Remarks 沒有反應

   **可能原因：** DeepSeek API 金鑰未設定或已過期。

   **解決方案：**
   1. 檢查 Dashboard 上的 DeepSeek 狀態燈是否為綠色
   2. 如果是黃色，表示 API 金鑰未設定——請參考 SETUP.md
   3. AI 功能不影響排班生成，只是備註解析和欄位對應需要手動處理

   ### Q7：匯入 CSV 後，所有 prefect 的年級都變成 F4

   這是系統的保護機制：如果 CSV 中的 `form` 欄位格式不正確（例如寫了 `F.5` 而不是 `F5`），系統會預設為 F4 並顯示警告。

   **解決方案：**
   1. 在 Prefects 頁面手動修正每位 prefect 的年級
   2. 或者修正 CSV 檔案後重新匯入

   ### Q8：兩位 prefect 有相同的名字怎麼辦？

   系統使用名字作為唯一識別碼。如果匯入時偵測到重複名稱，**第二筆及之後的重複資料會被自動跳過**，並在匯入通知中顯示警告。

   **解決方案：** 在 CSV 中為同名 prefect 加上區別（例如 `CHAN Tai Man (5A)` 和 `CHAN Tai Man (5B)`）。

   ### Q9：如何把系統轉交給下一任 Head Study Prefect？

   1. 確保所有文件都在 `D:\code_v2\` 中
   2. 做一份完整的 JSON 備份
   3. 把整個 `D:\code_v2\` 資料夾複製給接任者
   4. 接任者只需執行 `pip install -r requirements.txt` 和 `python app/main.py` 即可
   5. 建議接任者先閱讀本指南和 HANDOVER.md

   ### Q10：系統運行到一半突然當機

   1. 關閉 Terminal 視窗
   2. 重新打開 Terminal，輸入 `cd D:\code_v2` → `python app/main.py`
   3. 所有資料都會自動恢復（因為儲存在 CSV 和 Sheets 中）
   4. 如果排班資料遺失，從備份還原

   ---

   ## 10. 附錄：快速參考卡

   ### 每週操作清單（2–3 分鐘）

   - [ ] 啟動系統：`python app/main.py` → `http://localhost:8080`
   - [ ] 檢查 Dashboard 狀態燈（兩個都綠最好）
   - [ ] Roster → Generate and View → Generate Roster
   - [ ] 檢查值日表（AHP 崗位、Room 202 關閉日、空缺提示）
   - [ ] 如有請假 → Adjust and Edit → Leave Adjustment
   - [ ] Export PDF → 分享到群組
   - [ ] Dashboard → Backup System → Download Backup（5 秒）
   - [ ] 關閉 Terminal 視窗

   ### 角色對照表

   | 英文（系統內） | 中文 |
   |-------------|------|
   | Head Study Prefect | 首席學長風紀 |
   | Assistant Head Study Prefect (AHP) | 助理首席學長風紀 |
   | Study Prefect | 學長風紀 |
   | Assist. in charge | 值日生負責人（AHP 專屬崗位） |

   ### 房間對照表

   | Room | 每日人數 | 開放時間 | 關閉日 |
   |------|---------|---------|--------|
   | Room 302 | 1 人 | 放學後 15:45–18:00 | 無（每天開放） |
   | Room 303 | 2 人 | 放學後 15:45–17:00 | 無（每天開放） |
   | Room 202 (F1 Study Group) | 2 人 | 放學後 15:45–17:00 | 星期二、星期五 |

   ### 頁面功能速查

   | 想做什麼 | 去哪裡 |
   |---------|--------|
   | 生成排班 | Roster → Generate and View → Generate Roster |
   | 處理請假 | Roster → Adjust and Edit → Leave Adjustment |
   | 手動調換 | Roster → Adjust and Edit → Manual Edit |
   | 匯出 PDF | Roster → Generate and View → Export PDF |
   | 新增 prefect | Prefects → Add Prefect |
   | 匯入 CSV | Prefects → Import CSV |
   | AI 解析備註 | Prefects → AI Parse Remarks |
   | 載入示範資料 | Prefects → Load Demo Data |
   | 備份 | Dashboard → Backup System → Download Backup |
   | 還原 | Dashboard → Restore from Backup |
   | 查看公平性 | Dashboard → 往下捲動至 Fairness Chart |

   ---

   *本指南由 LI Chuangjie 於 2026-06-27 編寫。隨著系統演進，請持續更新本文件。如有疑問，請參閱 FAQ.md 或聯絡上一任 Head Study Prefect。*

