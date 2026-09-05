# 更新、驗證與上傳：一個命令完成正確層級

<!-- SING_YIN_CURRENT_STATUS:START -->
> **已核實線上來源（2026-08-14）：** Windows origin 正運行 clean annotated `v1.2.0-rc.58`／`e90bb8fdb95ca874f668b5a7134853756471635f` 的不可變 bundle；319-file 指紋 `c57778ce438c1c23c824c444827db7eeb9166d20be3ba3e78f1bb1221fee5283` 通過 15／15 gate。SQLite 位於 Alembic `0014`；正式備份 `20260813-161554-736678-manual_verified_backup.sqlite3`／SHA-256 `0e0ee9cc9a592eeea66055e107c461e859f3ccec2791cb06f051e7078c3febc2`、隔離還原、health、`writeReady=true`、`maintenance=false`、`recoveryRequired=false` 及 `pendingBackups=0` 已核對。Worker 來源沒有改動，canonical Worker `7951ca55-ffda-4f16-b570-d37486311914` 維持 100% 流量且健康。`v1.2.0-rc.57` 只屬歷史來源，migration `0014` 後不可作 code-only rollback；須使用受控的相容資料庫還原。真人驗收仍為 `pending`，實體離線 BitLocker 復原演練仍為 `pending`。精確狀態及更新規則見[目前系統狀態](status/CURRENT_STATUS.md)。
<!-- SING_YIN_CURRENT_STATUS:END -->
> **rc37／rc38 歷史界線：**受保護的 `v1.2.0-rc.37` 指向較早 rc36 source，屬 void／未部署標籤；`v1.2.0-rc.38` 通過來源閘門但沒有通過 Windows 排程帳戶憑證切換，因此沒有取代 rc35。新部署或回退不可把兩者誤當成目前線上版本。

我是李創杰。這份流程是我與 Codex 對正式發布工作的反思結果：更新慢的主因不是 Git 上傳，而是過去把每次文字或測試修改都當成完整 runtime 發布。

> **歷史 rc30 乾淨發布界線：** annotated tag `v1.2.0-rc.30`／commit `74b84f43786b00feb15b51a6270ff71c9430773f` 與 Worker `11763f08-d40d-46d5-93dc-5ca2599d4154` 曾是正式乾淨基線，並完成 exact-source `--release`、正式備份、隔離還原、受控 Windows origin 切換、0% Worker smoke、100% promotion 及 canonical rendered checks。它現在只屬歷史證據；目前線上 origin、Worker 及 migration-aware recovery contract 以本頁頂部生成狀態為準。任何後續 focused tests、`--staged` 或文件更新都不會自動成為新的已部署 runtime；仍須以實際 origin／Worker 報告和線上核對為準。
>
> **歷史 rc31 候選界線：** `codex/rc31-unified-theme-controls` 曾修改排程核心、生成檔案交付、手機抽屜、通用寫入 admission、備份／交接／還原及 migration guard；其 297 個可部署來源檔案以指紋 `7f405269322e67ddc1fdfd5dde004af5079b315725487303fbecd8e1c0954042` 通過當時的 15／15 gate。它已被後續正式版本取代，不代表目前候選或線上狀態。

rc20 的完整候選報告約需 **404 秒**；當中主要時間用於完整 Python 套件、桌面／手機瀏覽器、寫入／PDF／還原、效能及備份失敗演練。這些證據對政策、資料庫、工作流、部署或正式 runtime 改動很重要，但不應因 README 改一句話而重跑。最近三次沒有 runtime 改動的提交亦在 GitHub Quality 與 CodeQL 合計使用約 18 分鐘。

## 文件與架構先行檢查

所有改動先執行同一個低成本治理檢查：

```powershell
python -X utf8 scripts\project_governance.py --check
```

它會核對文件生命週期、topic owner、本機連結、current-release 生成區塊及 Python 模組依賴方向。若觀察到正式 release、migration、backup、Worker 或真人驗收狀態改變，只修改 `docs/status/current-release.json` 的證據值，再執行：

```powershell
python -X utf8 scripts\project_governance.py --write
```

這會 deterministic 地更新 `docs/status/CURRENT_STATUS.md` 及所有重要指南頁首。不可逐份手動複製 tag、commit、fingerprint 或備份名稱；普通文件只保留 owner 連結與不會隨版本改變的程序。

## 日常唯一入口：先診斷，再核對 staged commit

新工作從最新 `origin/main` 建立隔離的 `codex/<task>` 工作樹，PR 直接至 `main`。
`codex/mainline` 是歷史流程，不再作新分支起點或 PR 目標。
學校正式啟用前的重構範圍及新空庫決定见
[正式啟用計劃](plans/20260905-system-integration.md)；需求進度見
[交付追蹤](plans/PRELAUNCH_DELIVERY.md)。既有技術部署記錄不代表已正式啟用。

完成一批改動後，在本次隔離工作樹先執行：

```powershell
python -X utf8 scripts\verify_update.py --plan
```

它會先讀取 Git 變更，再顯示：

- 目前意圖是 `working-tree` 診斷，不是提交或正式發布；
- 選中的驗證 profile；
- 為何需要這個層級；
- 會執行哪些檢查；
- 正式部署前是否仍需要完整的正式發布證據。

然後閱讀 `git status --short`，逐一加入本次確實要上傳的檔案。不要使用 `git add -A`。完成 staging 後，執行真正的 pre-push gate：

```powershell
python -X utf8 scripts\verify_update.py --staged
```

它會顯示 `Verification intent: pre-push`，執行每項檢查、列出耗時，並把結果寫入 `logs/change-verification-report.json`；它不會覆蓋正式的 `logs/release-candidate-report.json`。

如這批改動沒有新增檔案，也可直接對整個工作樹執行：

```powershell
python -X utf8 scripts\verify_update.py
```

但未 staged 的新 release source 會令 repository hygiene 失敗，避免新程式檔在 push 時被漏掉。這是工作樹尚未整理完成的訊號，不是功能測試失敗。

pre-push 命令只證明「已 staged 的變更適合提交／push 並交給 CI」，不聲稱已可部署。即使分類為 `worker` 或 `full`，它也只執行完整 Python 測試、安全閘門、Worker 契約及 repository hygiene；桌面／手機瀏覽器、寫入／PDF、備份、還原及失敗演練會留待正式發布。

公共入口音樂屬於 Worker 行為，除 Deno 契約外必須執行 `python -X utf8 scripts\verify_public_entry_music.py --base-url <staged-worker-url>`。驗證器會在瀏覽器內模擬成功、拒絕、同步例外及未完成播放，但會攔截 `/auth/login`／`/guest` 目標請求：它不輸入 Access 憑證，也不建立真正 Guest session。正式上線仍須使用版本化 0% Worker、指定版本 smoke、100% promotion 及 canonical smoke；localhost 通過不能代替 Cloudflare 路徑證據。

## 只有正式發布才使用 `--release`

必需檢查清單由來源中的 `scripts/release-gates.json` 定義，報告不能自行縮減。
Schema 4 報告綁定清單版本與 canonical SHA-256；Python 狀態頁、正式驗證器、
Windows 和 Worker 部署器共用同一讀取契約。部署器直接使用單次嚴格驗證所得的
報告快照，不能先驗證一份再重新讀取另一份。歷史報告保留原樣，不能冒充新候選證據。
此清單現有 17 項閘門：既有 15 項加上 `generated_design_tokens` 及
`generated_service_weave_delivery`。兩個資產檢查只執行生成器的 `--check`，
不自動修復或重寫檔案；生成器本身亦納入來源指紋。任何輸出缺失或過期都不能通過。
完整手機原始樣本、獨立瀏覽器矩陣與 Public／Viewer 門檻的接入仍待完成，
不能用這次資產門檻接入宣稱全項驗收完成。

準備建立 release tag、更新 Windows 正式 bundle 或部署 Worker 時，明確執行：

```powershell
python -X utf8 scripts\verify_update.py --release
```

這會啟動 `scripts/verify_release_candidate.py`，產生正式 `logs/release-candidate-report.json`。即使工作樹沒有新改動，`--release` 仍可重新產生與目前 source fingerprint 對應的正式證據。瀏覽器元件截圖只寫入 ignored `logs/uiverse-components`；更新已追蹤 visual reference 必須另立明確、可審查的 baseline 變更，不可由一般 gate 暗中覆蓋。

正式報告現使用 schema 4，並記錄 clean source commit／tree、fingerprint／file count、planned annotated tag、required check identities、timestamps、tool versions 及 `humanAcceptanceRequired=true`。每道 gate 完成時及整輪結束時都會重新計算 fingerprint，並把 `postVerificationSource` 與開始時的 commit、tree、file count 及 Git cleanliness 比對；任何 verifier 產生的 tracked／untracked source、提交漂移或 runtime fingerprint 改變都會在第一個 gate 邊界令整體 fail closed。正式 report 必須在最終 protected-main commit 上執行一次；部署器會把 report 與 clean HEAD、remote annotated tag 及 `origin/main` 再對照，並拒絕缺失、數字或字串形式的 `sourceDirty`。Staged、缺少 post-check binding 或舊 schema report 不能啟動正式切換，正式 gate 亦不能代替 deployment 或真人驗收。

`SING_YIN_HOST` 正式只接受已測試的 IPv4 loopback `127.0.0.1`。不要使用 `::1`／`[::1]`：目前 TrustedHostMiddleware 會拒絕相應 bracketed Host，設定驗證會在啟動前直接報錯，避免形成全站 HTTP 400。

可先檢視正式發布計劃：

```powershell
python -X utf8 scripts\verify_update.py --release --plan
```

rc20 的正式 report 已由最後 commit 重新產生，並把同一裝置矩陣的 256×700／200% reflow、320×760 reduced motion、390×844 phone、768×1024 與 820×1180 adaptive touch tablet、1024×768 desktop-shell touch tablet、1440×1024 full desktop、844×390 phone landscape、單一可見 navigation shell、`visualViewport` keyboard clearance、44px standalone targets、route focus、More current-page semantics、touch icon story 無漂移／旋轉、forced colours、paired light／dark parity，以及 public first-viewport Admin／Guest CTA 綁定至同一 source fingerprint。`verify_nicegui_mobile.py` 與 `verify_nicegui_ui.py` 提供互補成員；測試檔、局部通過訊息或 screenshot 本身仍不是部署證據。

rc20 的精確發布證據是：annotated tag `v1.2.0-rc.20`、commit `e3d84858abfe23714929a87c4bcf76e55999ce7c`、290 個來源檔案、fingerprint `93c6c93866c617862c790a4ed939d9acbe789dcdfaf512c9519aff9e0b4e6d3a`、14／14 gates、839 個 Python／3 個 motion／40 個 Worker 測試。fresh backup／isolated restore、提升權限的 Windows origin switch 及 canonical smoke 已完成；仍待完成的是真人裝置驗收。由於 Worker source／configuration 沒有改動，發布時保留已驗證 version `f780feb2-671a-4feb-b6f6-b7f9d5b31e89`，沒有執行無差異 Worker 部署。任何 origin 關鍵項失敗，依 handover／host guide 回復歷史 rc18 exact pair。

## 風險矩陣

| 最高風險改動 | 自動選擇 | 執行內容 |
|---|---|---|
| 文件、README、狀態及交接文字 | `docs` | whitespace、文件契約、repository hygiene、包含文件的秘密掃描 |
| 只有測試及文件 | `tests` | 被修改的測試；共用 test helper 改動則升級為完整 Python suite；另加 hygiene 及秘密掃描 |
| GitHub workflow 或快速分類器 | `assurance` | assurance 聚焦測試、完整安全閘門及 hygiene |
| Cloudflare Worker／登入／Viewer | `worker` | pre-push 跑 Worker 聚焦契約、hygiene 及秘密掃描；正式部署使用 `--release` |
| NiceGUI、政策、公平、交易、SQLite、遷移、依賴、運行資產、Windows 主機腳本或正式驗證器 | `full` | pre-push 跑完整 Python、安全、Worker 及 hygiene；正式部署使用 `--release` 執行當前完整 gate。歷史版本的 gate 數量只屬該版本；後續一律以凍結來源的 source-matched report 為準。 |
| 未能識別的新路徑或 Git base | `full` | 失敗時向高風險升級，不會靜默略過 |

`/support` 頁面、Worker route、`SupportInbox`、redaction／quota、收件匣設定、
主機安全摘要或支援文件均屬安全敏感的跨層變更，最低使用 `full`。版本控制只
包含程式、測試及文件；實際 support inbox、staging、quarantine、附件、主機
摘要輸出、日誌、資料庫及備份必須由 repository hygiene gate 排除。正式部署
只接受同一不可變來源的 Admin／Guest／Public／Viewer 支援流程證據。
其中路由回歸必須同時證明：無 principal 的 Public／Viewer `/support` 不到達
origin；有效 Admin／Guest principal 的同一路徑會到達 NiceGUI，而且下層能力仍
拒絕 Guest 持久寫入。只測其中一條路徑不構成發布證據。

pre-push profile 內互不寫入的檢查會並行執行。正式候選驗證仍保持受控次序，因為瀏覽器寫入、備份及還原證據不可互相競爭同一個隔離環境。

## 有界混合 Gateway 容量檢查

以下命令不是每次修改都要執行；只有 Admin read／write path、Guest isolation／admission／workspace 容量、Worker service binding／WebSocket 代理、generated-file download、backup、outbox concurrency 或 Viewer publish／decrypt 的風險改變時才加入：

```powershell
python -X utf8 scripts\verify_mixed_gateway_load.py
```

它在本機執行實際 Worker source、Miniflare／workerd、瀏覽器 WebSocket、loopback NiceGUI origin 及虛構 disposable SQLite。它拒絕 production URL／資料路徑／account credential，並記錄 session 數、p95 的測試語境、隔離、公平、backup／outbox 與 cleanup memory stop condition。成功報告位於被忽略的 `logs/mixed-gateway-load/verification.json`；日期化、可審閱的結論進 [`audits/MIXED_GATEWAY_LOAD_ACCEPTANCE_2026-08-01.md`](audits/MIXED_GATEWAY_LOAD_ACCEPTANCE_2026-08-01.md)。

本機 workerd 證據不證明 Cloudflare edge／VPC Service、長時間 soak、正式 SLO、部署或真人裝置體驗，也不取代 `verify_update.py --release`。已有相同 runtime commit、lockfile、設定及風險邊界的乾淨證據可以沿用；任一相關輸入改變後不可沿用。

## 正式證據不再被文字改動誤傷

正式 `sourceFingerprint` 現只覆蓋可部署 runtime、內置音樂／資產、依賴、主機操作腳本及正式證據閘門。以下內容改動不再令已證實的 runtime 候選變成 stale：

- `docs/`、README、`PROJECT_STATUS.md`；
- `tests/`；
- `.github/`；
- `scripts/verify_update.py`。

這不是少驗證，而是把證據對準它真正證明的對象。文件仍有文件契約及秘密掃描，測試仍有測試 profile，CI workflow 仍有 assurance profile。

## GitHub 自動行為

`Quality gates` 先用同一分類器判斷變更：

- 文件更新不安裝 Deno，也不跑完整 Python／Worker 套件；
- Worker 或 runtime 更新才安裝 Deno；
- 同一分支有較新提交時，未完成的舊 CI 會自動取消；
- CodeQL 只因 Python、依賴或自身 workflow 改動而在 push／PR 啟動；每星期排程仍保留完整分析。

不要用 `git add -A` 或自動提交所有檔案。先人工閱讀 `git status --short`，只加入本次改動；本機 `.codex/`、`.env`、SQLite、備份、日誌及操作者資料不可因便利而誤上傳。

## 甚麼仍不可省略

以下情況不是一般「上傳更新」；部署前必須使用 `--release`，並保留所列人手確認：

- 正式政策、公平、交易、備份、還原或 migration 改動；
- 排程求解器、完整崗位／權重 validation、generated-file ticket isolation／capacity、mobile drawer focus/cleanup、universal write admission、recovery marker 或 exact-byte staged backup／handover 改動；
- Assist. 模式或名冊可值班日契約改動，包括 `legacy_fixed_weekday`／`flexible_weekly`、AHP-only、同日不重複、不連續當值及 migration `0011_assist_assignment_mode`；
- Worker 身份驗證、管理 session、Viewer 加密或 VPC 邊界改動；
- Windows 主機切換、依賴更新或正式 release tag；
- UAC／服務帳戶憑證、Cloudflare One-time PIN；
- 正式資料清除、新學年受控重置；
- 實體手機、WhatsApp 分享、PDF 肉眼核對及重啟後自動恢復。
- 窄屏／200% zoom、軟鍵盤、route focus、More 語意、forced colours、paired themes、touch targets，以及 public mobile first-viewport CTA 的真人核對和使用者可見 rollback 演練。

## 每次流程失敗怎樣反思

只記錄四個不含敏感內容的指標：

1. 自動等待時間；
2. 必須人手操作的時間；
3. 重試次數；
4. 哪個風險分類令檢查被執行或略過。

如低風險文件更新仍超過兩分鐘，先檢查是否誤分類、依賴快取失效或 CI 排隊；不要直接再加一套檢查。只有新的失敗證據顯示現有 profile 漏掉真實風險，才調整分類器與測試。
