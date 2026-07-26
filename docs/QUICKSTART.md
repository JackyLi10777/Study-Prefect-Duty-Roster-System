# 快速啟動 / Quick start

> **目前狀態（live rc24）：** `C:\SingYinRoster` 正運行 annotated tag `v1.2.0-rc.24`／commit `8d709f9b0b4e69fe38f7237ef2f473c27ff848fc`；296 個 runtime 發布輸入以指紋 `a6a1f4641f0eafa54fb740eb57f9173febc651ab0f11e3cfefcbe4c6ce38f477` 通過 14／14 gate，正式備份、checksum、公平對帳、行數核對、還原審計及隔離還原亦已通過。canonical Worker version `76a23134-8355-4e25-bbba-abf17c6918c5` 正承接 100% 流量；第一級回退是 `v1.2.0-rc.21`／`f7df4d0170e6bacd65340cc893992a17b5ed4aed`，rc20／`e3d84858abfe23714929a87c4bcf76e55999ce7c` 是次級已驗證基線。
>
> **rc24 已上線（真人驗收仍未簽署）：** rc24 整合內容精煉、本機優先支援回報及完整 Admin／Guest／Public／Viewer 邊界，並修正 `/support` 的身份分流：Public／Viewer 保持瀏覽器暫存，已驗證 Admin／Guest 進入 NiceGUI 工作台。機器驗證及線上 smoke 不能代替首席導學風紀與教師顧問真人驗收。

## 每日使用

1. 確認 Windows 專用主機已開機；背景工作會自動啟動，毋須每日雙擊程式。
2. 在任何獲准裝置開啟唯一正式網站：<https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/>。
3. 未登入時可選：
   - **訪客體驗：** 進入同一套 NiceGUI 頁面，只操作虛構資料，不寫正式 SQLite、備份或公平帳本。
   - **管理員登入：** 輸入 Access policy 精確列明的電郵及 Cloudflare 寄出的單次驗證碼，同一網址才會解鎖正式工作台。
4. 完成後按「登出」，特別是共用裝置；只關閉分頁不等於清除管理員／Guest session 及同 session 的其他分頁狀態。
5. 如只需查看首席導學風紀發出的週表，直接開啟完整 `/view#…` 連結；不要以 Guest 或 Admin 入口取代分享連結。

rc20 上線後，生成前先在名單核對職務及「可值班日」：只有助理首席導學風紀可當 `Assist. in charge`，未勾選的星期一律視為不方便／不可值班。新週次可選「固定星期模式」或「每週靈活模式」；固定模式保留同一 AHP 的星期擁有權，本週請假只作一次替補；靈活模式按可值班日及長期公平記錄作可重現的每週變化。既有週表會重開其已保存模式。

首次進入會跟隨電腦／手機的深淺模式；如瀏覽器尚未能判定，畫面先以深色安全呈現。按右上角外觀按鈕可依次選擇「跟隨系統 → 深色 → 淺色」。Guest 在同一有效 session 內重新整理仍會保留語言及外觀；登出後按設計回到新 session 預設。

Guest 同一分頁重新整理時，可還原最新、已簽署且綁定該 session／workspace／tab 的示範 revision；複製分頁會獲得另一個 workspace。這只是 30 分鐘臨時續接，不是長期儲存；登出、到期、撤權或 origin 重啟後舊 token 會失效。

## rc20 手機快速核對（live 功能的真人驗收）

只有交接紀錄已列出 rc20 的正式 tag／commit、來源 fingerprint、沿用的 Worker version 及成功 origin rollout 後，才執行以下使用者核對；維護者必須另按[完整已驗證候選裝置矩陣](ACCEPTANCE_EVIDENCE.md#rc20-已驗證候選裝置矩陣--verified-candidate-device-matrix)核對手機、兩種直向平板、橫向觸控平板及 full desktop，不以本節簡表代替矩陣：

1. 以 320px／390px 手機開啟 canonical 網址；毋須捲動已可看見唯一一組「管理員登入」及「進入訪客示範」，每個按鈕容易觸控且不與桌面 access panel 重複。
2. 把瀏覽器放大至 200%，確認頁面文字、頁首、頁尾及四個底部導航在窄屏內 reflow；只有明確資料區可局部橫向捲動，整頁不可左右漂移。
3. 在一個表單開啟軟鍵盤；固定底欄應退開，焦點欄位保持可見。關閉鍵盤及旋轉後，安全區與最後一個操作仍可到達。
4. 用鍵盤或讀屏由 Dashboard 轉到 Rosters／Prefects，焦點應到新頁 `main`。開啟次要頁時 **More** 可視覺 active，但 current page 應是抽屜內的實際路由，而不是 More menu trigger。
5. 在淺色、深色、reduced motion 及 forced-colours 各核對一次。Standalone action 至少 44px；touch icon story 只在原位做一次 opacity／scale 變化，不漂移、不旋轉，且 reduced motion 保持靜止。

任一項失敗都先停止正式寫入、記錄時間／route／裝置及非敏感畫面並登出，不要反覆提交表單。維護者依 [發布與交接手冊](RELEASE_HANDOVER.md) 先證明受控 rollback 至 rc18／`fd504a8` 與 Worker `f780feb2-671a-4feb-b6f6-b7f9d5b31e89`；只看到 `/healthz` 200 不足以恢復使用。

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

Live `v1.2.0-rc.20` at `e3d84858abfe23714929a87c4bcf76e55999ce7c` passed 14／14 source-matched gates under fingerprint `93c6c93866c617862c790a4ed939d9acbe789dcdfaf512c9519aff9e0b4e6d3a` (839 Python, 3 motion, and 40 Worker contracts) and completed the controlled Windows deployment. Continue to use rc20 behavior; supervised Head Study Prefect and teacher-advisor acceptance remains pending. rc18／`fd504a8` is the first historical rollback target.

The live `v1.2.0-rc.20` origin (`e3d84858abfe23714929a87c4bcf76e55999ce7c`) and verified Worker `f780feb2-671a-4feb-b6f6-b7f9d5b31e89` provide one canonical site with either a time-limited **Guest experience** using fictional in-memory data or **Admin login** through Cloudflare Access. A refresh in the same Guest tab may restore its latest signed revision, but a duplicated tab receives another workspace and logout, expiry, revocation, or origin restart invalidates the temporary token. Select **Log out** when finished because closing one tab does not clear every session state. `/view#…` remains the separate read-only published-roster link. `START_SING_YIN_ROSTER.cmd` is a local maintenance and recovery launcher only. It reuses an existing official service, chooses a free port from 8080–8099 when necessary, waits for HTTP readiness, and only then opens the browser. For a durable fictional rehearsal with backup/restore, use `START_PRACTICE_MODE.cmd`; the remote Guest workspace is intentionally temporary. Check `/readyz`, not only `/healthz`, before accepting official writes. In rc20, Fixed weekday preserves each AHP's weekday across weeks while a leave substitute remains week-local; Flexible weekly varies deterministically among declared available days with fairness history primary. Unchecked days are never eligible, and an existing week reopens with its saved mode.
