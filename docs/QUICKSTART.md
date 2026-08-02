# 快速啟動 / Quick start

<!-- SING_YIN_CURRENT_STATUS:START -->
> **已核實線上來源（2026-08-02）：** Windows origin 正運行 clean annotated `v1.2.0-rc.47`／`15f53f97eda81b3f4b1518a44567e18171891711` 的不可變 bundle；310-file 指紋 `3472686105c5a7356da526995438aaef025c52b8c252dc17c21e3de01e27e679` 通過 15／15 gate。SQLite 位於 Alembic `0012`；正式備份 `20260801-232211-102949-manual_verified_backup.sqlite3`／SHA-256 `13ca64426a59fcaae098548830de79c3da896a483b2aa8680a0f84488323c432`、隔離還原、health、`writeReady=true`、`maintenance=false`、`recoveryRequired=false` 及 `pendingBackups=0` 已核對。Worker 來源已更新，canonical Worker `a7218f51-ec6c-4002-a9be-9dfbb691136c` 維持 100% 流量且健康。`v1.2.0-rc.45` 只屬歷史來源，migration `0012` 後不可作 code-only rollback；須使用受控的相容資料庫還原。真人驗收仍為 `pending`。精確狀態及更新規則見[目前系統狀態](status/CURRENT_STATUS.md)。
<!-- SING_YIN_CURRENT_STATUS:END -->
>
> **歷史 rc30 乾淨發布證據：** `C:\SingYinRoster` 曾以受控方式運行 annotated tag `v1.2.0-rc.30`／commit `74b84f43786b00feb15b51a6270ff71c9430773f`；296 個 runtime 發布輸入以指紋 `15d155d8d745b14b574b08d793150c93aa77946e7d17a63030844c44adededbc` 通過 14／14 gate，正式備份、checksum、公平對帳、行數核對、還原審計及隔離還原亦已通過。canonical Worker version `11763f08-d40d-46d5-93dc-5ca2599d4154` 通過 0% smoke 後承接 100% 流量。這組 clean pair 是當時第一個已知、已驗證的復原目標；目前線上版本及 migration 後的受控資料庫復原限制以本頁頂部生成狀態為準，較早版本只屬歷史來源。
>
> **rc30 歷史乾淨發布證據（真人驗收仍未簽署）：** rc30 保留完整 Admin／Guest／Public／Viewer 邊界及 `/support` 身份分流，並加入目的語言本名、明確 System／Light／Dark 選擇及有日期／非遙測聲明的 ≈10B creator token 約數。機器驗證及線上 smoke 不能代替首席導學風紀與教師顧問真人驗收。
>
> **歷史 rc31 候選證據：** `codex/rc31-unified-theme-controls` 把可見外觀控制簡化為單一淺色／深色按鈕；`system` 只作未設定的初始化狀態。其 297 個可部署來源檔案曾以指紋 `7f405269322e67ddc1fdfd5dde004af5079b315725487303fbecd8e1c0954042` 通過當時的 15／15 正式候選閘門；它已被後續正式版本取代，不代表目前候選、復原目標或線上狀態。

## 每日使用

1. 確認 Windows 專用主機已開機；背景工作會自動啟動，毋須每日雙擊程式。
2. 在任何獲准裝置開啟唯一正式網站：<https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/>。
3. 未登入時可選：
   - **訪客體驗：** 進入同一套 NiceGUI 頁面，只操作虛構資料，不寫正式 SQLite、備份或公平帳本。
   - **管理員登入：** 輸入 Access policy 精確列明的電郵及 Cloudflare 寄出的單次驗證碼，同一網址才會解鎖正式工作台。
4. 完成後按「登出」，特別是共用裝置；只關閉分頁不等於清除管理員／Guest session 及同 session 的其他分頁狀態。
5. 如只需查看首席導學風紀發出的週表，直接開啟完整 `/view#…` 連結；不要以 Guest 或 Admin 入口取代分享連結。

目前正式版本中，生成前先在名單核對職務及「可值班日」：只有助理首席導學風紀可當 `Assist. in charge`，未勾選的星期一律視為不方便／不可值班。新週次可選「固定星期模式」或「每週靈活模式」；固定模式保留同一 AHP 的星期擁有權，本週請假只作一次替補；靈活模式按可值班日及長期公平記錄作可重現的每週變化。既有週表會重開其已保存模式。

首次進入而尚未保存外觀偏好時，畫面會跟隨電腦／手機的深淺模式。伺服器首屏只提供中性的淺色提示，瀏覽器會在外觀控制可見前解析系統模式並在需要時同步；若瀏覽器完全不支援系統色彩查詢才保留淺色。右上角只有一個淺色／深色按鈕：圖標顯示目前解析模式，輔助文字說明按下後的相反模式。第一次按下會儲存目前解析結果的相反模式，其後只在明確淺色與深色間切換。Guest 在同一有效 session 內重新整理仍會保留語言及外觀；登出後按設計回到新 session 預設。從公開入口刻意進入 Admin／Guest 時，只會暫存已明確選擇的 `light`／`dark` 提示，最長 120 秒；Worker 核對並放入簽署身份後才交給目的工作區，建立 session 時會清除暫存 cookie。目的地已有偏好時不會被覆寫。

Guest 同一分頁重新整理時，可還原最新、已簽署且綁定該 session／workspace／tab 的示範 revision；複製分頁會獲得另一個 workspace。這只是 30 分鐘臨時續接，不是長期儲存；登出、到期、撤權或 origin 重啟後舊 token 會失效。

## rc30 手機快速核對（live 功能的真人驗收）

只有交接紀錄已列出受審候選的正式 tag／commit、來源 fingerprint、Worker version 及成功 origin／Worker rollout 後，才執行以下使用者核對；維護者必須另按[完整已驗證候選裝置矩陣](ACCEPTANCE_EVIDENCE.md#rc20-已驗證候選裝置矩陣--verified-candidate-device-matrix)核對手機、兩種直向平板、橫向觸控平板及 full desktop，不以本節簡表代替矩陣。矩陣最初由 rc20 建立；rc30 report 只保留為最近完整驗證的歷史證據，新候選必須產生自己的 exact-source report：

1. 以 320px／390px 手機開啟 canonical 網址；毋須捲動已可看見唯一一組「管理員登入」及「進入訪客示範」，每個按鈕容易觸控且不與桌面 access panel 重複。
2. 把瀏覽器放大至 200%，確認頁面文字、頁首、頁尾及四個底部導航在窄屏內 reflow；只有明確資料區可局部橫向捲動，整頁不可左右漂移。
3. 在一個表單開啟軟鍵盤；固定底欄應退開，焦點欄位保持可見。關閉鍵盤及旋轉後，安全區與最後一個操作仍可到達。
4. 用鍵盤或讀屏由 Dashboard 轉到 Rosters／Prefects，焦點應到新頁 `main`。開啟次要頁時 **More** 可視覺 active，但 current page 應是抽屜內的實際路由，而不是 More menu trigger。
5. 在淺色、深色、reduced motion 及 forced-colours 各核對一次。Standalone action 至少 44px；touch icon story 只在原位做一次 opacity／scale 變化，不漂移、不旋轉，且 reduced motion 保持靜止。

任一項失敗都先停止正式寫入、記錄時間／route／裝置及非敏感畫面並登出，不要反覆提交表單。維護者依 [發布與交接手冊](RELEASE_HANDOVER.md) 判斷事故屬 origin、gateway 還是資料狀態：第一個復原選擇是保留頁首所列的目前程式，並以同一生成狀態記錄的已驗證正式備份執行受控還原。資料庫已升至 Alembic `0012`；rc45 只屬歷史相容資料庫復原來源，回復 rc43／rc41 或更舊程式前，必須使用相容的 pre-0012 快照完成隔離還原，不能只切換程式或 Worker。只看到 `/healthz` 200 不足以恢復使用。

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

Historically, clean `v1.2.0-rc.30` at `74b84f43786b00feb15b51a6270ff71c9430773f` passed 14／14 source-matched gates under fingerprint `15d155d8d745b14b574b08d793150c93aa77946e7d17a63030844c44adededbc` (894 Python tests, 3 motion, and 46 Worker contracts) and completed controlled Windows and Worker deployments. It was the first known verified clean recovery source at that time. Current production is identified only by the generated status at the top of this page; the first recovery path keeps that application and restores its recorded verified backup. Rc45 is a historical compatible-database recovery source, while rc43, rc41 and older applications require a compatible pre-0012 database restore. Supervised Head Study Prefect and teacher-advisor acceptance remains pending.

The verified origin and gateway identified at the top of this document provide one canonical site with either a time-limited **Guest experience** using fictional in-memory data or **Admin login** through Cloudflare Access. A refresh in the same Guest tab may restore its latest signed revision, but a duplicated tab receives another workspace and logout, expiry, revocation, or origin restart invalidates the temporary token. Select **Log out** when finished because closing one tab does not clear every session state. `/view#…` remains the separate read-only published-roster link. `START_SING_YIN_ROSTER.cmd` is a local maintenance and recovery launcher only. It reuses an existing official service, chooses a free port from 8080–8099 when necessary, waits for HTTP readiness, and only then opens the browser. For a durable fictional rehearsal with backup/restore, use `START_PRACTICE_MODE.cmd`; the remote Guest workspace is intentionally temporary. Check `/readyz`, not only `/healthz`, before accepting official writes. Fixed weekday preserves each AHP's weekday across weeks while a leave substitute remains week-local; Flexible weekly varies deterministically among declared available days with fairness history primary. Unchecked days are never eligible, and an existing week reopens with its saved mode. These Assist. modes were introduced in historical rc20 and remain part of the verified production state.
