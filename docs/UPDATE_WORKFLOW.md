# 更新、驗證與上傳：一個命令完成正確層級

我是李創杰。這份流程是我與 Codex 對正式發布工作的反思結果：更新慢的主因不是 Git 上傳，而是過去把每次文字或測試修改都當成完整 runtime 發布。

> **目前發布界線：** live rc18／`fd504a8` 與 Worker `f780feb2-671a-4feb-b6f6-b7f9d5b31e89` 仍是正式基線。rc19 mobile/accessibility working tree 只是候選；`--plan`、focused tests、`--staged` 或文件更新都不等於 rc19 已通過 `--release`，更不等於 Windows／Worker 已部署。

最近一份完整候選報告約需 **225 秒**；當中約 95% 用於完整 Python 套件、桌面／手機瀏覽器、寫入／PDF／還原、效能及備份失敗演練。這些證據對政策、資料庫、工作流、部署或正式 runtime 改動很重要，但不應因 README 改一句話而重跑。最近三次沒有 runtime 改動的提交亦在 GitHub Quality 與 CodeQL 合計使用約 18 分鐘。

## 日常唯一入口：先診斷，再核對 staged commit

完成一批改動後，在 `D:\code_v3` 先執行：

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

## 只有正式發布才使用 `--release`

準備建立 release tag、更新 Windows 正式 bundle 或部署 Worker 時，明確執行：

```powershell
python -X utf8 scripts\verify_update.py --release
```

這會啟動 `scripts/verify_release_candidate.py`，產生正式 `logs/release-candidate-report.json`。即使工作樹沒有新改動，`--release` 仍可重新產生與目前 source fingerprint 對應的正式證據。

可先檢視正式發布計劃：

```powershell
python -X utf8 scripts\verify_update.py --release --plan
```

對 rc19，正式 report 必須由最後 commit 重新產生，並將 256px／200% reflow、320px reduced motion、390px phone、768px adaptive touch tablet、1024×768 desktop-shell touch tablet、phone landscape、單一可見 navigation shell、`visualViewport` keyboard clearance、44px standalone targets、route focus、More current-page semantics、touch icon story 無漂移／旋轉、forced colours、paired light／dark parity，以及 public first-viewport Admin／Guest CTA 綁定至同一 source fingerprint。測試檔、局部通過訊息或 screenshot 存在都不是部署證據。其後仍須完成 fresh backup／isolated restore、Windows switch、Worker 0% stage→100% promotion、canonical smoke 及真人裝置核對；任何失敗依 handover／host guide 回復 rc18 exact pair。

## 風險矩陣

| 最高風險改動 | 自動選擇 | 執行內容 |
|---|---|---|
| 文件、README、狀態及交接文字 | `docs` | whitespace、文件契約、repository hygiene、包含文件的秘密掃描 |
| 只有測試及文件 | `tests` | 被修改的測試；共用 test helper 改動則升級為完整 Python suite；另加 hygiene 及秘密掃描 |
| GitHub workflow 或快速分類器 | `assurance` | assurance 聚焦測試、完整安全閘門及 hygiene |
| Cloudflare Worker／登入／Viewer | `worker` | pre-push 跑 Worker 聚焦契約、hygiene 及秘密掃描；正式部署使用 `--release` |
| NiceGUI、政策、公平、交易、SQLite、遷移、依賴、運行資產、Windows 主機腳本或正式驗證器 | `full` | pre-push 跑完整 Python、安全、Worker 及 hygiene；正式部署使用 `--release` 執行當前完整 gate（live rc18 基線為 14 項，後續以 source-matched report 為準） |
| 未能識別的新路徑或 Git base | `full` | 失敗時向高風險升級，不會靜默略過 |

pre-push profile 內互不寫入的檢查會並行執行。正式候選驗證仍保持受控次序，因為瀏覽器寫入、備份及還原證據不可互相競爭同一個隔離環境。

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
