# 聖言中學導學風紀值班系統

> **非以役人，乃役於人。**
> 
> **Not to be served, but to serve.** — Mark 10:45

這是一個供聖言中學首席導學風紀使用的本機優先值班管理系統。當任首席導學風紀負責日常操作；顧問老師主要在工作完成後核對已發布週表、公平與交接證據。它幫助使用者安全完成：

**生成草稿 → 核對 → 發布 → 匯出 PDF → 已發布後請假調整 → 公平解釋 → 備份／還原 → 交接。**

系統以公平、清晰、責任、耐心與關顧為原則。學生姓名、請假原因、值班紀錄、PDF 及備份均保留在受控環境；現時不會自動上載到公開服務。

[English README](README-EN.md) · [GitHub repository](https://github.com/JackyLi10777/Study-Prefect-Duty-Roster-System) · [MIT License](LICENSE)

## 版本分支與運行平台

| 分支 | 運行平台 | 定位 |
|---|---|---|
| `main` | NiceGUI + SQLite；Windows／Linux 自託管 | 目前正式維護版本及交接來源 |
| `nicegui-self-hosted` | 專用 Windows 電腦或 Linux／Raspberry Pi 主機 | 與發布時 `main` 一致的平台命名版本 |
| `streamlit-cloud` | Streamlit Cloud | 由舊 `ai` 分支原提交改名保留的歷史參考版本 |

NiceGUI 版本是底層架構重構，不是把 Streamlit 頁面換皮。`roster_policy`、`roster_core`、`roster_workflow`、SQLite交易、備份還原及 NiceGUI 呈現均有清楚責任邊界。完整分支規則見 [Branch Strategy](docs/BRANCH_STRATEGY.md)。

GitHub同時保存程式、測試、文件、設計素材、內置音樂、虛構 SQLite 快照、無內容支援日誌及瀏覽器測試證據。可公開封存內容由 `scripts/build_public_archive.py` 產生；若 SQLite 存在任何週表、請假、發布、公平帳本或調整資料，腳本會拒絕建立封存。即時 `.env`、session secret、Tunnel／API token、`node_modules`、`.next`、快取及臨時效能資料不屬於可重建專案內容。

舊 `demo_code2` 的 service-account 私鑰檔不會上傳；版本庫只保留同欄位、全占位值的 `service_account.example.json`，讓參考整合仍可理解而不包含可用credential。

**共創者說明：這次 NiceGUI 重構、設計、測試、文件及正式發布版本，只由李創杰與 Codex 共同完成。`Study Prefect Systems & Stewardship Office` 是我們兩人的項目團隊名稱，沒有其他開發者、部門成員或外判團隊。**

## 首席導學風紀：每日怎樣進入

1. 開啟系統資料夾。
2. **雙擊 `START_SING_YIN_ROSTER.cmd`**。
3. 啟動器會先檢查是否已有系統在執行；若已有，會直接開啟原有服務，不會再啟動第二個 NiceGUI。
4. 預設網址是 [http://127.0.0.1:8080](http://127.0.0.1:8080)。若 8080 被其他程式佔用，啟動器會自動選擇 8081–8099 之間的可用埠，並在黑色視窗顯示實際網址。
5. 只有在 HTTP 確認系統真正就緒後，瀏覽器才會開啟；若沒有自動開啟，請使用黑色視窗顯示的網址，不要猜測埠號。
6. 先閱讀首頁每日經文，然後依「本週值班工作台」的目前步驟工作。

### 第一次接手：先用練習模式走一次完整流程

- 雙擊 `START_PRACTICE_MODE.cmd`。它使用 8090–8109、`data/practice/` 內的獨立 SQLite、備份、日誌及介面偏好，並自動載入虛構中文姓名；不會讀寫正式資料庫或正式備份。
- 每一頁頂部都會顯示繁中／英文「練習模式」狀態列；練習 PDF 的檔名、正文及頁尾均標示不可作正式發布。
- 可放心練習「請假 → 生成 → 手動修改 → 發布 → 雙語 PDF → 發布後請假調整 → 公平審核 → 備份／還原」。
- 要重新開始時，先關閉練習模式的黑色視窗，再雙擊 `RESET_PRACTICE_MODE.cmd`；它只會清除 `data/practice/`，然後重新建立虛構練習環境。
- 正式工作仍只使用 `START_SING_YIN_ROSTER.cmd`。兩個啟動器會透過 `/healthz` 的 `applicationMode` 身份辨識服務，不會互相誤開。

日常安全次序：

1. 在「風紀名單」核對中文姓名、職務及可值班日。
2. 在「值班表」先登記尚未發布週的請假，再生成草稿。
3. 核對草稿；如需要，使用「手動修改草稿」並填寫原因。
4. 發布前再次核對。**只有發布才會更新 `history_weight` 公平帳本。**
5. 下載繁中或英文的橫向 A4 週表；所有導學風紀姓名均維持中文。
6. 已發布後有人請假時，只使用「請假調整」，不要重新生成已發布週表或直接修改資料庫；依頁面步驟選擇原崗位、載入替補、填寫原因，才儲存。手機版會把名單及值班資料顯示為完整卡片，避免靠橫向滑動尋找中文姓名。
7. 新任首席導學風紀可在側邊欄依次查看「開始使用」→「使用手冊」→「系統架構與共創」；它們分別說明第一次操作、每週安全流程，以及系統如何保護公平與復原，不需要先懂程式。

名單新增／修改／停用及生成前請假會連同本機快照一起安全處理；進度視窗完成前不要重複點擊。停用只會停止日後選用，不會刪除既有週表、公平帳本或審計紀錄，且必須先經過清楚確認。

首次使用而尚未有已驗證快照時，「建立交接備份包」及「還原已選備份」會保持停用，畫面只提供「立即建立已驗證快照」這個安全下一步。完成快照及完整性驗證後，兩個入口才會出現為可操作狀態。

如最近檢查的快照有 manifest 遺失、SHA-256 不符、SQLite 完整性或資料表問題，設定頁只會顯示安全分類及數量，並自動把它們排除於交接和還原選單。不要改名、手動修補或公開上載這些檔案；先建立新的已驗證快照，調查時只向受控 IT 支援提供 OP／REQ 編號。

設定頁每次開啟仍會重新核對快照，不依賴過時快取；最近最多 12 個快照會以最多四路唯讀方式驗證，保持最新優先並縮短等候。檔案在檢查途中被移走時會安全略過或標記為不可使用，不會令設定頁中斷。

如畫面顯示 `OP-...` 支援編號，這次失敗不會自行發布值班表。先檢查資料、職務、可值班日和請假；若問題持續，向教師顧問或 IT 支援提供該編號。維護者可在受控電腦以 `python -X utf8 scripts\inspect_support_log.py --reference OP-XXXXXXXX` 查找本機日誌；不要把整份日誌傳送到公開或個人雲端。

## 教師顧問／IT：首次設定

在專用、受控的校內電腦完成一次：

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

本機模式不需手動建立 session secret：第一次啟動會原子建立並持續沿用已被 Git 忽略的 `data/runtime/.nicegui-storage-secret`。只有日後改為專用主機的 `server` 模式時，才必須以受控環境變數提供獨立 `SING_YIN_STORAGE_SECRET`。然後以：

```powershell
python -X utf8 -m nicegui_app.main
```

啟動系統。預設只綁定 `127.0.0.1`；啟動器會優先使用 8080，必要時在 8081–8099 選擇本機可用埠。這是刻意的私隱保護設定。

## 文件地圖

| 你要完成的事 | 請閱讀 |
|---|---|
| 每週生成、發布、PDF、請假調整 | [首席導學風紀操作手冊](docs/OPERATOR_GUIDE.md) |
| 雙擊啟動、埠號衝突、重複開啟 | [快速啟動](docs/QUICKSTART.md) |
| 第一次接手、隔離練習及重設 | `START_PRACTICE_MODE.cmd`、`RESET_PRACTICE_MODE.cmd` 及 [快速啟動](docs/QUICKSTART.md) |
| 備份、還原、交接、正式驗收 | [首次發布與交接手冊](docs/RELEASE_HANDOVER.md) |
| 每項驗收要求的自動化證據與真人責任 | [正式驗收證據矩陣](docs/ACCEPTANCE_EVIDENCE.md) |
| 本機、Cloudflare Access 與真正雲端部署之取捨 | [部署與遠端存取決策指南](docs/DEPLOYMENT_DECISION.md) |
| NiceGUI、政策、工作流與資料層責任 | [NiceGUI 架構](docs/NICEGUI_ARCHITECTURE.md) |
| 視覺、無障礙、深淺模式與動效標準 | [Professional Design System](Professional_Design_System.md) |
| 系統如何分工、保障資料和交接脈絡 | 系統內「系統架構與共創」頁面，以及 [NiceGUI 架構](docs/NICEGUI_ARCHITECTURE.md) |
| 當前完成內容、測試證據與已知風險 | [Project Status](PROJECT_STATUS.md) |
| GitHub分支、歷史版本及發布規則 | [Branch Strategy](docs/BRANCH_STRATEGY.md) |
| 虛構資料、日誌及測試證據封存 | [Public project archive](archive/README.md) |

## 系統架構與可信設計

這套系統的高級感不只來自畫面，而來自每一層都能說明「誰作決定、何時寫入、失敗後怎樣回復」。日常使用毋須理解程式碼；本節供顧問老師、繼任者及維護者核對系統為何值得信任。

```mermaid
flowchart TB
    OP["首席導學風紀<br/>Head Study Prefect"] --> UI["NiceGUI 操作層<br/>雙語 · 深淺模式 · 可存取提示"]
    UI --> WF["roster_workflow<br/>交易 · 公平帳本 · 審計"]
    WF --> CORE["roster_core<br/>純生成與完整驗證"]
    CORE --> POLICY["roster_policy<br/>校規唯一來源"]
    WF --> DB["SQLite + SQLAlchemy<br/>持久週表與 history_weight"]
    WF --> SNAP["自動 SQLite 快照<br/>SHA-256 manifest · 完整性核對"]
    DB --> PDF["本機 PDF 輸出<br/>橫向週表 · 直向內部審計"]
    SNAP --> RESTORE["受控還原<br/>還原前安全快照 · 審計"]
    LOG["無內容本機日誌<br/>OP / REQ 支援編號"] -. 診斷而不記錄姓名 .-> UI
```

### 一個值班週的資料生命線

```mermaid
stateDiagram-v2
    [*] --> 準備名單與請假
    準備名單與請假 --> 草稿: 生成並驗證
    草稿 --> 草稿: 填寫原因後手動修正
    草稿 --> 已發布: 確認並取得唯一發布權
    已發布 --> 週表PDF: 繁中或英文標籤／中文姓名
    已發布 --> 已調整: 發布後請假局部替換
    已調整 --> 更新PDF: 重新輸出
    已發布 --> 已驗證備份: 自動快照與校驗
    已調整 --> 已驗證備份: 自動快照與校驗
    已驗證備份 --> 交接包: manifest + SQLite + 復原說明
    交接包 --> [*]

    note right of 草稿
      不更新 history_weight
      不寫入公平帳本
    end note
    note right of 已發布
      交易內重新驗證
      公平工作量只入帳一次
    end note
```

### 五層責任與可核對證據

| 層 | 唯一責任 | 可核對證據 |
|---|---|---|
| NiceGUI 呈現 | 導覽、語言、提示、狀態與響應式畫面 | 繁中／英文、深淺模式、鍵盤、手機及 browser smoke |
| `roster_policy` | 崗位、開放日、人數、時段、職務與權重 | 純規則測試；不依賴翻譯文字或頁面 |
| `roster_core` | 生成候選、長期公平排序及完整週表驗證 | 同日不重複、不連續當值、請假與角色限制測試 |
| `roster_workflow` | 草稿、一次性發布、帳本、調整、審計、備份與還原交易 | 並發發布、負荷轉移、快照及隔離寫入 E2E |
| SQLite／輸出／支援 | 保存正式狀態、列印結果與無內容診斷證據 | Alembic、完整性檢查、雙語 PDF、OP／REQ 查詢 |

四項不可妥協的系統契約：

- **校規單一來源：** 頁面不自行決定誰可在哪裏當值。
- **公平持久而可解釋：** 草稿不入帳，發布只入帳一次，請假調整留下扣回與轉移紀錄。
- **重要寫入可復原：** 快照、manifest、SHA-256、SQLite 完整性及還原前安全快照共同工作。
- **資料邊界清楚：** 姓名、請假與週表不進入公開服務、音樂層或診斷內容；外部存取尚未批准。

## YouTube 音樂控制窗（自選）

- 前往「設定」→「YouTube 音樂控制窗」，貼上公開歌單連結，命名並選擇適用頁面；之後在該頁頂部按耳機圖示即可選擇及播放。
- 公開歌單播放器免費使用，無需登入、付費或 API key。它保持完整可見，不會自動播放；播放、暫停、音量和換歌均由首席導學風紀親自控制。
- 若希望在網站內搜尋公開影片／歌單，才由維護者在本機 `.env` 加入選用的 `SING_YIN_YOUTUBE_API_KEY`。此 key 不可輸入介面、提交版本庫或放入學生資料。
- YouTube 會接收一般播放器所需的網絡資料。歌單標題、音樂偏好與 API 搜尋不得含學生姓名、請假、值班或公平資料；顧問老師的核對資料也不包含音樂設定。

## 資料安全與遠端存取

現時系統是 **本機正式版本**。不要使用 Quick Tunnel、公開網址、個人雲端同步資料夾或公開 Sites 服務處理學生資料。

將系統透過 Cloudflare Tunnel + Cloudflare Access 提供受控遠端存取是可行的，但它不是「把網站上傳到雲端」：資料與 NiceGUI 程序仍可保留在一部受控的學校主機上，Cloudflare 只在前面提供身份驗證及加密通道。NiceGUI origin 仍必須只聽聽 `127.0.0.1`；Tunnel 必須啟用 **Protect with Access**，而程式只接受 localhost 與已核准的公開 hostname。這項設定必須先由教師顧問完成書面安全決定，並依[部署與遠端存取決策指南](docs/DEPLOYMENT_DECISION.md)完成所有閘門。

真正遷移到雲端主機是另一個 L3 架構項目：目前系統使用長時間運行的 Python NiceGUI 程序及可寫入 SQLite 資料目錄，不能直接搬到靜態網站平台。任何雲端遷移必須先有身份權限模型、受控持久化資料庫、加密備份、復原演練及資料保留決定。

## FAQ／常見問題

**草稿會增加累計工作量嗎？**  
不會。生成及重新生成只保存草稿；正式發布才寫入公平帳本及更新 `history_weight`。

**如果兩個分頁同時發布，會重複入帳嗎？**  
不會。資料庫交易以條件更新取得唯一發布權；另一個操作會在寫入公平點數前被拒絕。

**發布後有人請假，是否重新生成整張週表？**  
不要重新生成。使用「請假調整」只改受影響崗位，重新核對替補資格，並正確扣回或轉移負荷。

**英文模式或英文 PDF 會翻譯姓名嗎？**  
不會。所有導學風紀姓名在介面及兩種 PDF 中一律保持中文。

**資料保存在甚麼地方？**  
正式名單、週表、公平帳本及審計保存在受控電腦的本機 SQLite；音樂和個人介面偏好與排班資料分開。

**可否直接用舊 SQLite 覆蓋目前資料庫？**  
不可。必須在「系統設定」選擇已驗證快照，讓系統先建立安全快照，再執行原子還原及審計。

**畫面顯示 `OP-...` 時怎樣處理？**  
依提示核對並安全重試一次；問題持續時只提供 OP 編號，維護者用本機查詢工具定位，不要上載整份日誌。

**畫面顯示「資料已儲存，但備份未完成」時可否重試？**  
不可重複剛才的操作，因為資料庫變更已經生效。先重新載入核對結果，再前往「系統設定」按「立即建立已驗證快照」。這個狀態會使用獨立的 OP 支援編號，避免與已回復的普通失敗混淆。

**目前可否公開到互聯網？**  
不可。正式模式仍是 localhost；專用主機、Cloudflare Access、允許名單及書面安全決定完成前，不設定 Tunnel。

**YouTube 或背景音樂會取得學生資料嗎？**  
不會。媒體層只接收非敏感頁面分類及歌單設定，不會收到名單、請假、週表、公平、PDF、備份或審計內容。

## 開發與驗證

目前自動化套件超過 180 項，並有三條互補的瀏覽器證據：`scripts/verify_nicegui_ui.py` 核對繁中／英文、深淺模式、鍵盤焦點、手機排版、配圖主題切換、校徽、停用確認、無快照、無效快照、失效週表網址，以及交接頁發布證據／真人責任狀態；`scripts/verify_nicegui_write_pipeline.py` 只可在隔離 SQLite／備份／日誌路徑，以虛構中文姓名驗證星期與必填欄位修正、草稿不可進入發布後請假表單、並行驗證下的有效／無效快照並存、交接／還原入口啟用，並完成整條排班寫入及還原流程；`scripts/verify_nicegui_partial_backup.py` 故意令備份失敗，證明已提交資料不會被誤報為回復，並完成手動快照復原。

```powershell
python -X utf8 scripts\check_deployment_readiness.py
python -X utf8 -m pytest -q
```

第一個命令只讀取非敏感的本機部署狀態，檢查 localhost 綁定、SQLite 完整性、最近快照的 manifest／checksum／完整性／schema 驗證，以及尚未啟用的 Cloudflare 閘門；只有檔名而未通過驗證的 SQLite 不會被報成可用備份。它不會配置 Tunnel、建立 DNS 或上傳資料。

完整 UI 驗證必須使用隔離 SQLite 資料庫和備份目錄，絕不可碰觸真實學校資料；詳細命令及規則見[架構文件](docs/NICEGUI_ARCHITECTURE.md)。

正式發布前，教師顧問或 IT 支援先安裝獨立驗證依賴及 Chromium，然後使用單一安全入口：

```powershell
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python -X utf8 scripts\verify_release_candidate.py
```

驗證器自行建立暫存 SQLite、備份及日誌路徑，依次執行完整測試、編譯、依賴檢查、繁中／英文與深淺模式 UI smoke、整條虛構資料寫入／PDF／替補／交接／另一資料庫還原流程、嚴格部署檢查，以及獨立的「資料已提交但備份失敗」復原演練。每個瀏覽器階段停機後亦會檢查伺服器終端；`ERROR`、`CRITICAL`、traceback 或未取回的 task exception 均會令發布候選失敗，而不會把原始終端內容複製到報告。兩份 PDF 會直接解析並核對已發布狀態、五個星期、所有中文姓名及四個 202 室關閉格。它不會採用 `.env` 內的正式資料路徑；結果寫入 `logs/release-candidate-report.json`，並明確標示仍需真人驗收。任何一關失敗，整體狀態均為 `fail`，不可視為發布候選通過。

交接頁會把機器報告與目前發布相關程式、測試、遷移、依賴及驗證腳本的 SHA-256 指紋重新比對。報告缺失、失敗、格式不可信或程式改動後過期時，均不會顯示為通過；即使當前八關通過，畫面仍保留首席導學風紀 13 項及教師顧問 4 項真人驗收責任。

第八關 `repository_hygiene` 只輸出類別與數量，不顯示檔名或內容。它會阻擋即時 `.env`、運行中 SQLite／備份／日誌、PDF／ZIP、匯入名單及操作者自訂音樂，並核對 `.gitignore` 仍保留這些邊界。只有經零筆營運資料檢查產生的 `archive/fictional-data/` 快照及已審閱的根目錄內置音樂可進入版本庫；虛構封存不能成為繞過即時資料邊界的方法。

---

## English quick guide

This is a local-first duty roster system for Sing Yin Secondary School Study Prefects. The current Head Study Prefect handles routine operation; the teacher advisor mainly reviews published results, fairness, and handover evidence after completion. It supports draft generation, review, publication, bilingual PDF export, post-publication leave adjustment, fairness explanation, verified backup/restore, and handover.

The optional YouTube control window plays public playlists for free without sign-in or an API key. It remains visible and never autoplays. An optional `SING_YIN_YOUTUBE_API_KEY` enables in-app public search; keep it only in the local `.env` and never include student information in music searches or playlist names.

### Daily use

1. Double-click `START_SING_YIN_ROSTER.cmd`.
2. The launcher reuses an already-running Sing Yin service instead of starting a duplicate copy. If another program occupies port 8080, it automatically selects a free port between 8081 and 8099 and prints the exact URL.
3. The browser opens only after the local HTTP service is confirmed ready. If it does not open, use the exact URL printed in the black launcher window.
4. Read the Daily Verse, then follow the highlighted step in the weekly roster desk.
5. Check the prefect directory, declare pre-generation leave, generate a draft, review it, publish once, export the roster, and use the dedicated leave-adjustment workflow for a late absence. In that workflow, choose the original duty, load a substitute, record a reason, then save; phone views keep the relevant Chinese identity and duty information together in cards.

Traditional Chinese is the primary interface language. English labels are complete, but prefect names always remain Chinese in the UI and both PDF languages.

### Local support log

An operator failure displays an `OP-...` reference and does not publish anything automatically. On the controlled school computer, the advisor or IT supporter can find one local record with `python -X utf8 scripts\inspect_support_log.py --reference OP-XXXXXXXX`. HTTP responses also carry a `REQ-...` trace in `X-Request-ID`. Never upload `logs/app.log` to a public site or personal cloud service.

### Safety and remote access

The current approved mode is localhost-only. Do not expose student data through a public URL, Quick Tunnel, public site, or personal cloud-sync folder. A Cloudflare Tunnel protected by Cloudflare Access can later provide controlled remote access to a dedicated school host, but only after the teacher advisor approves the security decision and completes every gate in the [Deployment and remote-access decision guide](docs/DEPLOYMENT_DECISION.md).

For operating instructions, recovery, architecture, and current release evidence, use the document map above.

### Architecture and FAQ summary

- NiceGUI owns presentation; `roster_policy` and `roster_core` own rules and generation; `roster_workflow` owns transactions, ledger effects, audit, backups, and restore.
- Drafts never post workload. Publication posts once through a database-level claim. Post-publication leave uses a dedicated audited adjustment.
- Official state stays in local SQLite. Only checksum- and integrity-verified snapshots are eligible for managed restore.
- Prefect names remain Chinese in both locales and both schedule PDFs.
- An `OP-...` reference is safe to share with the advisor or IT; the full local log is not.
- The current approved network mode is localhost, not a public URL.

---

## 共創結語 / Co-creation closing note

這個系統由李創杰（2026–2027 年度首席導學風紀）與 Codex 協作建立。它從一個排班需要，逐步成為一套把公平、責任、復原與交接都認真處理的校務工作台。

本次正式版本的需求整理、架構重構、核心邏輯、UI／UX、測試、文件及發布工作，只有李創杰與 Codex 兩位共創者參與完成。

> 做這個系統的過程遠比想像中複雜，但我們從不後悔。願它為未來的首席導學風紀帶來真正的便利，也讓每一位導學風紀感受到：公平確實被認真對待。
>
> —— 李創杰與 Codex，Study Prefect Systems & Stewardship Office

**Codex 的結語：** 我所參與的不只是編寫程式，而是把李創杰對公平、責任與傳承的要求，逐項轉化為可以測試、復原和交接的系統行為。真正值得保留的不是某一版畫面，而是下一位首席導學風紀仍能理解每個決定、放心完成工作，並在出錯時找到回去的路。願這個平台一直忠於它最初的目的：減少不必要的負擔，讓服事更有秩序，也讓公平被認真看見。

This system was co-created by Li Chongjie and Codex. Its lasting value is not a particular screen, but a trustworthy process future Head Study Prefects can understand, operate, recover, and hand over. May it continue to reduce avoidable burden, bring order to service, and make fairness visible.

---

## 授權 / License

程式碼及專案文件依 [MIT License](LICENSE) 發布。LICENSE內的專案說明保留李創杰與 Codex 的共創脈絡，但不會限制MIT所授予的權利；外部來源的音樂、字型及校務識別素材仍按其各自條款處理。
