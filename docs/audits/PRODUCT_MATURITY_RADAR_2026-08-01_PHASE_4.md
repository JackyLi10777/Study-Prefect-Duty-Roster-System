# 產品成熟度雷達：第四階段 / Product maturity radar: Phase 4

日期：2026-08-01

範圍：`ITR-005` 本機實際 Worker／WebSocket 混合負載驗收、容量證據與文件收斂

性質：乾淨來源與虛構資料證據；不是部署、Cloudflare edge soak 或真人驗收證明

## 基線與目前真相

- 本階段使用乾淨 `origin/main` worktree，程式驗證 commit 為 `a299412fa367db805ab66e058b1bdfbfad700be4`，最終報告記錄 `sourceDirty=false`。
- 正式運行真相仍只由 [`../status/CURRENT_STATUS.md`](../status/CURRENT_STATUS.md) 擁有：Windows origin 維持 rc45，Worker 維持既有 100% version；本階段沒有部署或修改 `status/current-release.json`。
- [`MIXED_GATEWAY_LOAD_ACCEPTANCE_2026-08-01.md`](MIXED_GATEWAY_LOAD_ACCEPTANCE_2026-08-01.md) 補上實際 Worker source、local workerd、WebSocket、Guest／Admin、下載、備份、outbox 及 Viewer 在同一拓撲中的可重現證據，因而關閉 `ITR-005`。
- 本階段審核了現有 GSAP Core、timeline、`quickTo`、`matchMedia`、interruptibility 及 cleanup。現況已由單一 runtime 和測試治理；NiceGUI／vanilla 頁面沒有 React 整合需求，操作介面也沒有 ScrollTrigger 或付費 plugin 的產品需要。因此沒有新增 GSAP runtime、ScrollTrigger、framework adapter 或動畫程式碼。這是避免無收益複雜度的明確決策，不是遺漏。

## 評分方法

| 分數 | 意義 |
|---|---|
| 0 | 沒有可依賴能力或證據 |
| 1 | 局部存在，但主要路徑仍靠人工或假設 |
| 2 | 核心路徑可用，仍有影響低維護營運的明確缺口 |
| 3 | 大部分受控且有證據，只餘受監督、災難或真實規模驗收 |
| 4 | 在本產品邊界內可觀察、可復原、可交接，沒有未追蹤的重要缺口 |

分數只在新增證據或風險改變時更新；依賴數量、動畫數量、文件篇幅或單次成功不會自動提高分數。

## A–J 雷達

| Domain | Phase 3 → 4 | Current evidence | Decision-relevant gap | Priority／tracking |
|---|---:|---|---|---|
| A. 操作者成果及工作流程 | 3 → 3 | 每週流程、回復、衝突、操作手冊及混合 gateway path 有自動證據 | 首席導學風紀與顧問老師尚未完成受監督簽署 | L1／`ITR-001` |
| B. 政策及資料正確性 | 4 → 4 | policy、core、workflow、optimistic version、idempotency、fairness、audit 及 backup obligation 有分層契約；混合負載下 fairness 仍 balanced | 本階段沒有政策語意改動 | Managed |
| C. 資料庫及資料存取 | 3 → 4 | SQLite／WAL／Alembic、bounded reads、verified snapshots 既有證據，現再證明 Guest 不寫正式 DB、Admin 後才改變、backup／outbox 與公平資料在混合路徑一致 | 本產品的單主機資料邊界內沒有新未追蹤缺口；災難復原另由 `ITR-004` 擁有 | Managed |
| D. 可靠性及復原 | 2 → 2 | 混合路徑無 lock／5xx，備份與 outbox 完成；off-site seam 仍保留 | 真實外置 BitLocker 副本及 replacement-location drill 尚未完成 | L1／`ITR-004` active |
| E. 並行、容量及效能 | 2 → 3 | 10 Guest × 2 waves、2 Admin、22 WebSockets、PDF、backup、outbox、Viewer 和清理記憶體已有本機 workerd 證據 | 尚無長時間 soak、真實 Cloudflare edge／VPC 數據或 24-session 飽和量度，因此不可升至 4 | Managed；邊界記入 dated evidence |
| F. 安全及私隱 | 3 → 3 | 測試資料虛構、環境 credential scrub、loopback-only、Guest DB write／external delivery fail closed | 真實媒體保管及 supervised identity/device acceptance 未完成 | L1／`ITR-004`＋`ITR-001` |
| G. 架構及可維護性 | 3 → 3 | verifier 以 Python orchestration、Node workerd adapter 及明確 process boundary 分層；Miniflare 為精確鎖定 dev-only 依賴；文件 owner／trigger 可執行 | 大型 living 文件只在實際修改成本符合條件時拆分 | L3／`ITR-003` conditional |
| H. 產品設計及無障礙 | 3 → 3 | 雙語、responsive、forced colours、reduced motion 及單一 GSAP motion grammar 保留不變 | iPhone Safari、Android Chrome 及顧問真人核對仍未簽署 | L1／`ITR-001` |
| I. 資訊架構及元件一致性 | 3 → 3 | 現有頁面及動效擁有者清楚；審核未發現再引入 ScrollTrigger／React adapter 能改善操作流程的證據 | 本階段沒有證據支持為改而改的 UI 或動畫重構 | Managed |
| J. 營運、可觀察性、文件及交接 | 3 → 3 | 結構化本機 report、停止條件、重現命令、限制、owner、驗收矩陣及迭代關閉均已記錄 | 正式部署、實體裝置、人員簽署和離機媒體仍由各自 owner 管理 | L1／`ITR-001`、`ITR-002`、`ITR-004` |

## 本階段最小有效改動

真正缺口不是更多動畫，而是 Worker 與 WebSocket 邊界缺少同一拓撲的混合證據。因此實作只增加 dev-only workerd harness、虛構資料 verifier、回歸測試及權威文件。它不改產品 UI、資料 schema、正式依賴、Cloudflare 設定或操作政策。

直接鎖定 Miniflare 是合理例外：腳本直接呼叫其 API，間接依賴不足以表達責任；版本鎖定及 offline frozen install 使環境可重建。React、ScrollTrigger、MorphSVG 等 GSAP 能力則沒有對應產品需求，引入它們只會增加 bundle、license／升級面及第二種元件生命週期，故明確拒絕。

## 完成、回退與剩餘工作

`ITR-005` 的原始關閉條件已滿足：沒有跨 session 洩漏、公平差異、未處理 lock／5xx、Guest 正式 DB write 或超出清理記憶體 budget，並記錄 p95、容量及停止條件。它從 active register 移除，證據保留於 dated audit、驗收矩陣與 Changelog。

本階段沒有部署或 schema 變更；如 verifier 架構有問題，可回退本階段來源 commits，正式 rc45 不受影響。仍待決策的工作只有 `ITR-001` 真人驗收、`ITR-004` 真實離機災難復原、`ITR-002` 下一次受控正式發布，以及條件式 `ITR-003` 文件拆分。

## English summary

Phase 4 closes the bounded source-evidence scope of `ITR-005` with a clean, reproducible local workerd/WebSocket mixed-load run. Database/data-access maturity rises from 3 to 4 within the single-host product boundary, while concurrency/capacity rises from 2 to 3—not 4—because this is neither a long soak nor real Cloudflare-edge saturation evidence. The GSAP audit intentionally produced no animation change: the current single-Core runtime already owns the required lifecycle, performance and cleanup contracts, and no practical React, ScrollTrigger or plugin need was found.
