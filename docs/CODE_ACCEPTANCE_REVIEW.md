# 程式驗收與風險導向審查／Code Acceptance and Risk-led Review

本文件說明我與 Codex 如何判斷一項改動是「能執行」還是「可以安全交付」。逐行閱讀仍有價值，但不能取代可重複的失敗測試、資料庫交易證據、瀏覽器驗證、備份還原及正式來源指紋。

This document explains how LI Chuangjie Jacky and Codex distinguish code that merely runs from a change that is safe to deliver. Line-by-line reading remains useful, but it does not replace repeatable failure tests, database-transaction evidence, browser verification, backup/restore, or a production source fingerprint.

## 1. 先畫出變更與信任邊界／Map the change and trust boundaries first

每次審查先回答以下問題：

- 改動屬於 NiceGUI 呈現、`roster_policy`／`roster_core` 規則與生成、`roster_workflow` 交易，還是 Cloudflare／主機部署？
- 輸入來自已核實管理員、有限期 Guest、公開 Viewer、上載檔案、外部 API，還是本機維護工具？
- 哪些資料可進入正式 SQLite、備份、審計、日誌、下載或外部網絡？
- 哪些不變量不可因 UI 或重試而改變，例如一次性發布、公平帳本、角色限制、同日不重複及不連續當值？

Every review first identifies the owning layer, input principal, persistence boundary, external side effects, and invariants that must remain true. A disabled button is never accepted as the only security or concurrency boundary.

## 2. 主流程與失敗流程同時驗證／Verify the main and failure paths together

一項功能至少要證明成功、拒絕、重試及恢復四種狀態。相關邊界包括：

- 上載超過 **2 MiB**、超過 **2,000 列／50 欄**、單格超過 **4,096 字元**、JSON 嵌套超過 **8 層**；
- 副檔名、MIME、內容或工作表格式不符，CSV 編碼無法辨認，XLSX 含公式／巨集、異常壓縮或過大解壓內容；
- 網絡中斷、逾時、HTTP 401／403／429／5xx、回應 MIME 錯誤、JSON 損壞或回應超過上限；
- 使用者重複點擊、多分頁／多 Guest 同時操作、舊版本表單提交、程序重啟，以及提交成功但備份尚未完成；
- 下載、備份或還原只完成一部分時，畫面不得顯示成功，並須提供可核對的支援編號或安全下一步。

The happy path is not sufficient. Tests also cover rejection, interruption, retry, stale input, duplicate commands, concurrent sessions, process restart, and recovery from a committed write whose backup obligation is not yet complete.

## 3. 區分可配置值與安全常數／Separate configuration from safety constants

環境會改變的值須由受控設定提供，例如資料庫、備份、日誌、主機、連接埠、公開入口、外部 API key、逾時及功能開關。頁面處理器不得各自寫死同一網址或路徑。

有些固定值是刻意的安全或政策不變量，不應為了「消除硬編碼」而任意外置，例如：

- origin 只監聽 `127.0.0.1`；
- 值班房間、開放日、席位、職務資格及公平點數規則；
- Guest 的時間、工作區、分頁、下載與命令上限；
- 上載／回應大小及解析深度上限。

Review therefore classifies every literal as configuration, policy, safety budget, test fixture, or accidental duplication. Only the last category is mechanically removed.

## 4. 以 10 倍／100 倍情境審查效能／Review performance at 10× and 100×

目前產品是單一 Windows origin、SQLite、約數十位導學風紀及按週累積記錄。審查不只看一次操作速度，而會量度：

- 查詢數是否隨導學風紀人數形成 N+1；
- 產生報告、對帳及備份是否需要無界限全表掃描；
- 上載是否先把無界限內容完整留在記憶體；
- Guest session、分頁、快照、事件監聽器、DOM 及背景工作能否在離開後釋放；
- SQLite 寫入競爭、busy timeout、索引及交易鎖在併發操作下是否仍有確定結果。

At 10×, existing indexed and bounded operations should remain responsive. At 100×, the team measures query plans, report windows, browser rendering, backup duration, and write contention before adding pagination, summaries, stricter period limits, or moving to PostgreSQL. Redis, microservices, or another front end are not added without measured need.

當修改 Guest admission、Worker service binding／WebSocket、下載 registry、backup 或 outbox 的並行行為時，使用以下有界檢查補充單元與隔離流程：

```powershell
python -X utf8 scripts\verify_mixed_gateway_load.py
```

它以實際 Worker source、local workerd、瀏覽器 WebSocket、loopback NiceGUI origin 及虛構 disposable SQLite 量度混合路徑。2026-08-01 的乾淨基線為 10 個同時 Guest × 2 waves、2 個 Admin、22 個 WebSockets，沒有跨 session 洩漏、Guest DB write、未處理 lock／5xx 或公平差異；詳見[日期化驗收](audits/MIXED_GATEWAY_LOAD_ACCEPTANCE_2026-08-01.md)。這個命令不是每次 pre-push 儀式，也不把本機 p95 變成 production SLO；只有風險邊界被觸及時才重跑。

## 5. 依賴必須有明確責任／Every dependency needs an owner and purpose

新增或保留依賴前須回答：

- 它解決的問題是否可用標準庫或現有已鎖定依賴完成？
- 它是否只在測試／建置使用，卻被帶入正式 runtime？
- 版本是否鎖定並可重建，授權、更新及漏洞掃描由誰負責？
- 它是否新增外部網絡、遙測、背景程序、瀏覽器儲存或原生執行風險？
- 移除它會影響哪一項可驗證能力？

The repository keeps one locked Python dependency set and locally governed front-end assets. A dependency is not justified by convenience alone; it must remove more risk or work than it introduces.

`cloudflare/roster_viewer` 直接鎖定 dev-only Miniflare，因為混合 gateway verifier 直接使用其 API 啟動 workerd、KV、rate limits 及 service binding；只依賴 Wrangler 的傳遞性版本會隱藏真正 owner。它不進入 production Worker bundle 或 NiceGUI runtime。相反，React adapter、ScrollTrigger 或額外 GSAP plugins 只有出現對應產品需求及可量度收益時才可加入；「skill 存在」或裝飾性動畫本身不是依賴理由。

## 6. 驗證深度按風險分級／Scale verification to risk

### 最小可靠檢查／Minimum reliable check

適用於文字、單一樣式、無行為改變的小修正：

1. 核對實際 diff 及擁有該行為的層；
2. 執行最接近改動的聚焦測試或靜態契約；
3. UI 有變更時檢查受影響路由、語言、主題及窄屏；
4. 確認沒有加入正式資料、秘密、日誌、資料庫或測試輸出。

This is the smallest acceptable evidence for a low-risk local change. It is not sufficient for a release.

### 正式候選檢查／Formal release-candidate check

跨頁、交易、資料庫、身份、下載、備份、部署或無界限影響必須完成：

1. 聚焦測試及完整 `pytest`；
2. `scripts/verify_update.py --staged`，確認只發布已審查的 staged source；
3. 隔離 SQLite／備份／日誌下的 Admin、Guest、繁中、英文、深淺模式及手機瀏覽器流程；
4. Cloudflare Worker 契約、真實代理路徑、下載標頭及身份邊界；
5. 正式備份的 checksum／SQLite integrity／公平對帳，以及另一隔離資料庫的受控還原；
6. `scripts/verify_release_candidate.py` 產生與候選來源綁定的完整報告；
7. origin 與 Worker 分階段更新、`/healthz`／`/readyz`、回復路徑及線上 smoke check；
8. 線上 source fingerprint、commit／tag、Worker version 與驗證報告完全吻合後才可宣稱已部署。

A previous test report, localhost HTTP 200, or “NiceGUI ready” message cannot prove a new production build. A release claim requires current-source evidence and the actual deployed fingerprint.

## 可以省略甚麼／What may be skipped

- 純文件修正毋須重跑完整瀏覽器寫入流水線，但要執行文件契約測試及連結檢查。
- 不涉及資料庫的局部 CSS 修正毋須做隔離還原，但須檢查受影響畫面和 reduced-motion／鍵盤狀態。
- 已有相同來源指紋、相同環境及未過期的聚焦證據可避免重複執行；任何來源、依賴、設定或部署版本改變後不得沿用舊證據。

Pure documentation changes do not require the full write pipeline, and local presentation-only changes do not require a restore drill. Evidence may be reused only when the source fingerprint, environment, dependency lock, and relevant configuration are unchanged.

## 不可省略甚麼／What may never be skipped for release

- 政策與交易不變量；
- Guest／Admin／公開 Viewer 的能力與資料隔離；
- 並發、冪等、舊版本提交及失敗恢復；
- 正式備份、校驗、公平對帳與隔離還原；
- staged source、commit／tag、origin fingerprint 及 Worker version 的一致性；
- 首席導學風紀及教師顧問對真實操作、列印、語氣、公平及交接責任的真人驗收。

Policy and transaction invariants, identity isolation, concurrency, recovery, verified backup/restore, deployed-source matching, and responsible human acceptance remain mandatory release evidence.
