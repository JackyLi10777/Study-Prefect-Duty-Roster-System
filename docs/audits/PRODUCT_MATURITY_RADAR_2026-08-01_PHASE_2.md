# 產品成熟度雷達：第二階段 / Product maturity radar: Phase 2

日期：2026-08-01

範圍：可迭代風險治理、身份生命週期證據及下一階段排序

性質：來源候選證據；不是部署或真人驗收證明

## 基線真相

- 審查來源由乾淨 `origin/main` commit `c8ec75c99933f7abb5d3517759e22c5ac9950870` 建立，沒有疊加使用者的未提交工作。
- 正式運行真相仍由 [`../status/CURRENT_STATUS.md`](../status/CURRENT_STATUS.md) 生成並擁有；本階段沒有修改 `current-release.json`，也沒有部署 origin 或 Worker。
- 正式版本與目前主線的 `shell.py`、`runtime.py`、`operation_context.py` 及既有撤銷測試沒有差異。已核實的到期登出與每次工作流呼叫身分重驗證，因此已存在於正式來源，不是本階段新增但未部署的功能。
- 本階段不改 UI、資料庫、migration、路由、Cloudflare 設定或產品政策，所以不需要用瀏覽器畫面冒充文件／契約驗證。

## 評分方法

| 分數 | 意義 |
|---|---|
| 0 | 沒有可依賴能力或證據 |
| 1 | 局部存在，但主要路徑仍靠人工或假設 |
| 2 | 核心路徑可用，仍有影響低維護營運的明確缺口 |
| 3 | 大部分受控且有證據，只餘受監督、災難或真實規模驗收 |
| 4 | 在本產品邊界內可觀察、可復原、可交接，沒有未追蹤的重要缺口 |

分數是本日期的決策工具，不是永久產品聲稱。只有新增證據或風險改變時才更新。

## A–J 雷達

| Domain | Score | Current evidence | Decision-relevant gap | Priority／tracking |
|---|---:|---|---|---|
| A. 操作者成果及工作流程 | 3 | 每週流程、回復路徑、衝突及操作手冊已有自動與瀏覽器證據 | 首席導學風紀與顧問老師尚未完成受監督簽署 | L1／`ITR-001` |
| B. 政策及資料正確性 | 4 | policy、core、workflow、optimistic version、idempotency、fairness、audit 及 backup obligation 有分層契約與測試 | 沒有本階段新發現；正式資料導入後仍須延續 release gate | Managed |
| C. 資料庫及資料存取 | 3 | SQLite／WAL／Alembic、索引、bounded reads、查詢量度及 1×／10×／100× 合成資料證據存在 | 尚未與實際 Worker／WebSocket 混合流量共同量度 | L2／`ITR-005` |
| D. 可靠性及復原 | 2 | 本機 verified backup、隔離還原、maintenance fence、migration-aware rollback 及 write readiness 已證明 | 完整主機損失後沒有加密離機副本及 replacement-location restore drill | L1／`ITR-004` |
| E. 並行、容量及效能 | 2 | Guest 配額、Admin 保留容量、序列化寫入、lock／idempotency 及合成規模測試存在 | 多 Guest＋Admin＋下載＋備份＋outbox 的真實 edge／WebSocket 混合負載未量度 | L2／`ITR-005` |
| F. 安全及私隱 | 3 | Worker 簽署 principal、精確 allowlist、Guest deny-by-default、撤銷、到期、secret、upload／download 及 log redaction 防線存在 | 受監督身份流程仍待真人驗收；exact CSP WebSocket host narrowing是獨立 hardening，不是本輪阻塞 | L1／`ITR-001` |
| G. 架構及可維護性 | 3 | policy／core／persistence／services／UI 邊界與文件 owner 已可執行檢查；UI 現在也不得直接建立正式 workflow | 大型 living／standard 文件只在真實修改成本出現時才拆分 | L3／`ITR-003` conditional |
| H. 產品設計及無障礙 | 3 | 雙語、responsive、forced colours、reduced motion、鍵盤及共用設計契約已有機器／瀏覽器證據 | iPhone Safari、Android Chrome 及顧問真人核對仍未簽署 | L1／`ITR-001` |
| I. 資訊架構及元件一致性 | 3 | 工作導向導航、共用 shell、共享按鈕／動效／等待契約及文件入口已建立 | 本階段沒有證據支持另一次全站重構；只按實際操作回饋開新項目 | Managed |
| J. 營運、可觀察性、文件及交接 | 3 | 單一 current-release JSON、生成狀態、文件分類、topic owner、連結、依賴方向及 release truth 可檢查 | 原風險表可保留沒有 owner 的開放事項；本階段以風險→iteration 契約修正 | 本階段切片 |

## 本階段選擇與驗收

最高價值切片不是新增另一套 WebSocket session manager。源碼與正式版本都已具備兩條獨立防線：瀏覽器在 principal 到期前開始安全登出並離頁；伺服器在 cached page context 及已捕捉 workflow method 的每次呼叫重新核對 expiry、`auth_epoch`、`kid` 及 process revocation。保留 transport 不會延長授權，因此新增第二個 socket-lifecycle owner 只會引入競態和維護成本。

本階段的完成條件：

1. `PROJECT_STATUS.md` 每個 `Tracked` 風險均指向現存 `ITR-NNN`。
2. Iteration 有唯一 ID、L1／L2／L3、owner、合法 state 及可判斷 closure evidence。
3. 沒有 iteration 的 `Tracked` 風險、未知 ID、重複 ID或模糊 state 會令 governance check 失敗。
4. 已捕捉的 workflow method 在到期、明確撤銷、auth epoch 改變及 key rotation 後均不會執行 delegate。
5. 文件清楚區分瀏覽器清理／UX、伺服器授權邊界、已編輯來源與正式部署真相。

## 下一個最高價值切片

`ITR-004` 是下一個未由軟件防線取代的 L1 缺口：建立加密離機備份、界定密鑰與保留責任、量度 RPO／RTO，並在不依賴正式主機的隔離位置從該副本完成還原。這需要操作者選定合法的離機儲存位置及密鑰保管方式；在取得該外部條件前，不應以雲端同步、額外資料庫或未演練的複製機制假裝完成。

## Rollback 與停止條件

本階段只改來源中的測試、治理腳本及文件。若契約誤判合法 Markdown，可回退本階段 commit；正式 runtime、SQLite、origin、Worker、session、route 及資料完全未變。聚焦與整合檢查通過、風險有 owner、部署真相未被改寫後即停止，不再因仍可增加文件而繼續擴張。
