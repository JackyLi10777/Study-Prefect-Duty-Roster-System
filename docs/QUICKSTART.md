# 快速啟動 / Quick start

> **目前狀態：** `C:\SingYinRoster` 仍是現有 v1.1 official origin。v1.2 統一訪客候選位於 `codex/unified-guest-redesign`，`SING_YIN_UNIFIED_GUEST` 預設為 `0`，尚未正式部署。以下「每日使用」適用於 v1.2 通過 gate 並啟用後；現行線上行為仍以實際 v1.1 畫面為準。

## 每日使用

1. 確認 Windows 專用主機已開機；背景工作會自動啟動，毋須每日雙擊程式。
2. 在任何獲准裝置開啟唯一正式網站：<https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/>。
3. 未登入時可選：
   - **訪客體驗：** 進入同一套 NiceGUI 頁面，只操作虛構資料，不寫正式 SQLite、備份或公平帳本。
   - **管理員登入：** 輸入 Access policy 精確列明的電郵及 Cloudflare 寄出的單次驗證碼，同一網址才會解鎖正式工作台。
4. 完成後按「登出」，特別是共用裝置；只關閉分頁不等於清除管理員／Guest session 及同 session 的其他分頁狀態。
5. 如只需查看首席導學風紀發出的週表，直接開啟完整 `/view#…` 連結；不要以 Guest 或 Admin 入口取代分享連結。

## 本機維護或 Cloudflare 故障復原

只有在專用主機背景工作失效、Cloudflare 故障或 IT 診斷時，才在主機的系統資料夾雙擊 `START_SING_YIN_ROSTER.cmd`。等待黑色視窗顯示「The system is ready」；瀏覽器只會在服務真正可以回應 HTTP 後才自動開啟。如瀏覽器沒有自動開啟，使用黑色視窗最後顯示的完整本機網址。

啟動器會先快速掃描 8080–8099：

- 已有 Sing Yin 服務：直接開啟現有服務，不建立第二個程序。
- 兩個啟動視窗同時開啟：第二個會等待第一個服務就緒，再重用它。
- 8080 空閒：使用 `http://127.0.0.1:8080`。
- 8080 被其他程式佔用：自動選擇下一個可用埠，並顯示實際網址。
- 8080–8099 全部不可用：停止並清楚報錯，不會留下半啟動的背景程序。

因此，雙擊第二次不會再造成 `WinError 10048`；若另一個程式佔用 8080，也不會讓 NiceGUI 直接撞埠失敗。

## 練習模式（建議新任首席先完成一次）

1. 雙擊 `START_PRACTICE_MODE.cmd`。
2. 確認每頁頂部顯示「練習模式」，再開始操作；此模式只載入虛構中文姓名。
3. 依序練習請假、生成草稿、手動修改、發布、繁中／英文 PDF、發布後請假調整、公平審核及備份還原。
4. 練習 PDF 會以 `PRACTICE_` 開頭，正文與頁尾亦標示不可正式發布。
5. 要清空重來：先關閉正在執行的練習模式，再雙擊 `RESET_PRACTICE_MODE.cmd`。重設器只會清除 `data/practice/`，隨即重新啟動一個全新虛構環境。

練習模式使用 8090–8109 及獨立資料庫、備份、日誌、NiceGUI 偏好。正式啟動器和練習啟動器會核對 `/healthz` 的模式身份，因此不會把另一種模式誤認為自己的既有服務。

## 關閉本機維護啟動器

如果是為診斷而手動開啟啟動器，完成後可回到黑色視窗按 `Ctrl+C`，或關閉該視窗。日常使用只需在正式網站登出；不要每天停止專用主機的背景工作。

## 遇到錯誤

- 顯示 `Python is not installed`：請由教師顧問或 IT 支援按 README 的首次設定安裝 Python 3.12 及需求。
- 顯示 `No free local port`：關閉不需要的本機服務後再試；不要直接修改資料庫或刪除資料夾。
- 若畫面顯示 `OP-...`：這是應用程式操作支援編號，請保留編號並查看本機 `logs/app.log`。
- `/healthz` 只表示程序及資料庫可讀；不能寫入時要同時查看 `/readyz`。如 `/readyz` 顯示 maintenance、recovery 或 pending backup obligation，停止重試並交由維護者處理。
- 若啟動器報錯：保留黑色視窗中的完整訊息，交給教師顧問或 IT 支援；不要只報告「網站打不開」。

## English

After the v1.2 gate and deployment, the single canonical site offers either the time-limited **Guest experience** with fictional in-memory data or **Admin login** through Cloudflare Access. Select **Log out** when finished because closing one tab does not clear every session state. `/view#…` remains the separate read-only published-roster link. `START_SING_YIN_ROSTER.cmd` is a local maintenance and recovery launcher only. It reuses an existing official service, chooses a free port from 8080–8099 when necessary, waits for HTTP readiness, and only then opens the browser. For a durable fictional rehearsal with backup/restore, use `START_PRACTICE_MODE.cmd`; the remote Guest workspace is intentionally temporary. Check `/readyz`, not only `/healthz`, before accepting official writes.
