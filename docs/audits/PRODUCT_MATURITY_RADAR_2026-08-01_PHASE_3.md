# 產品成熟度雷達：第三階段 / Product maturity radar: Phase 3

日期：2026-08-01

範圍：`ITR-004` 完整主機損失、加密離機副本及 replacement-location 復原

性質：來源候選與合成資料證據；不是部署、真實媒體或真人驗收證明

## 基線與目前真相

- 本階段從乾淨 `origin/main` commit `ae1bde544f4c414c8f3d6b3d3bc1b670c33c1b6c` 建立獨立 worktree；沒有疊加原工作樹的使用者截圖或舊 rc32 分支內容。
- 正式運行真相仍只由 [`../status/CURRENT_STATUS.md`](../status/CURRENT_STATUS.md) 擁有。本階段沒有修改 `status/current-release.json`，亦沒有部署 Windows origin 或 Cloudflare Worker。
- 主機檢查只找到 C、D 內置磁碟，沒有可核實的外置 BitLocker 目標。因此軟件 seam、合成 copied-bundle restore 及 runbook 已建立，但 `ITR-004` 仍是 `Active`。
- 本階段不改 UI、路由、Guest 能力、SQLite schema、Cloudflare 設定或產品政策；GSAP／瀏覽器動畫驗證不屬此復原切片。

## 評分方法

| 分數 | 意義 |
|---|---|
| 0 | 沒有可依賴能力或證據 |
| 1 | 局部存在，但主要路徑仍靠人工或假設 |
| 2 | 核心路徑可用，仍有影響低維護營運的明確缺口 |
| 3 | 大部分受控且有證據，只餘受監督、災難或真實規模驗收 |
| 4 | 在本產品邊界內可觀察、可復原、可交接，沒有未追蹤的重要缺口 |

分數只在新增證據或風險改變時更新；程式碼數量、文件篇幅或單次測試成功不會自動提高分數。

## A–J 雷達

| Domain | Score | Current evidence | Decision-relevant gap | Priority／tracking |
|---|---:|---|---|---|
| A. 操作者成果及工作流程 | 3 | 每週流程、回復路徑、衝突及操作手冊已有自動與瀏覽器證據 | 首席導學風紀與顧問老師尚未完成受監督簽署 | L1／`ITR-001` |
| B. 政策及資料正確性 | 4 | policy、core、workflow、optimistic version、idempotency、fairness、audit 及 backup obligation 有分層契約與測試 | 本階段沒有政策或資料語意改動 | Managed |
| C. 資料庫及資料存取 | 3 | SQLite／WAL／Alembic、bounded reads、verified snapshot／manifest 及 migration-aware restore 已有證據 | 尚未與實際 Worker／WebSocket 混合流量共同量度 | L2／`ITR-005` |
| D. 可靠性及復原 | 2 | 新 seam 可原子匯出 exact handover package、重算 RPO、拒絕篡改，並在刪除原主機合成資料後只由 copied bundle 完成 restore／fairness／audit 核對 | 沒有真實外置 BitLocker 副本、分離密鑰保管或 replacement-host drill；因此仍不可升至 3 | L1／`ITR-004` active |
| E. 並行、容量及效能 | 2 | Guest 配額、Admin 保留容量、序列化寫入及合成規模測試存在；離機匯出先使用正式快照 fence | 多 Guest＋Admin＋下載＋備份＋outbox 的真實 edge／WebSocket 混合負載未量度 | L2／`ITR-005` |
| F. 安全及私隱 | 3 | Wrapper fail closed 只接受非 system USB／SD、NTFS、BitLocker fully encrypted／protection on；receipt 無路徑／資料列，沒有 internal／cloud／DPAPI fallback | 需要學校批准媒體及保管制度；已控制主機的管理員仍可讀 export-time plaintext 或改寫 unsigned receipt | L1／`ITR-004`＋`ITR-001` |
| G. 架構及可維護性 | 3 | Python artifact-correctness seam 與 Windows storage adapter 分離；只有兩個 public operations；依賴、topic owner 及文件觸發可執行檢查 | 其他大型文件只在實際三段以上修改成本出現時才再拆分 | L3／`ITR-003` conditional |
| H. 產品設計及無障礙 | 3 | 雙語、responsive、forced colours、reduced motion、鍵盤及共用設計契約保留不變 | iPhone Safari、Android Chrome 及顧問真人核對仍未簽署 | L1／`ITR-001` |
| I. 資訊架構及元件一致性 | 3 | 日常、發布／相容回退與完整 host-loss 各有唯一入口；其他指南只連到離機 owner | 本階段沒有證據支持另一次全站 UI 重構 | Managed |
| J. 營運、可觀察性、文件及交接 | 3 | 路徑無關 JSON report、RPO／RTO、保留、custody、失敗處理、manifest owner、status／risk 連結及 deployment truth 已明確 | 仍欠真實媒體、第二位置、保管人及執行日期形成的外部證據 | L1／`ITR-004` |

## 本階段選擇

選擇外置 BitLocker USB／SD 是目前最小而可交接的可信邊界。C→D 仍會與主機一同損失；DPAPI／EFS 把解密能力綁回原 Windows 身份；未批准雲端同步或 network share 會新增資料駐留、憑證及可用性系統；自製 ZIP 密碼或自創加密會增加無法審查的密鑰與密碼學責任。因此程式沒有 fallback，也不因主機暫時缺少媒體而偽造完成。

artifact correctness 與 storage trust 分開：Python 收到已驗證的非敏感 target evidence 後，負責 package、receipt、digest、ZIP 邊界及臨時 restore；PowerShell 從 active immutable bundle 執行，負責 Windows task、disk topology、BitLocker、NTFS 及 volume identity。這個 split 讓核心測試可在虛構資料上運行，同時不讓跨平台程式假裝能證明硬件加密。

## 完成與外部證據

目前來源證據為：15 項新 recovery／CLI／Windows wrapper 聚焦測試通過；連同既有 backup integrity、restore、obligation、Windows deployment 與 governance 的 109 項整合回歸通過；修復一次 Next Steps 發布契約回歸後，完整 Python suite 為 **1,100 passed**。兩個 Python entry point 完成 `compileall`，PowerShell 5.1 scriptblock parse、project governance、diff whitespace 及 working-tree plan verifier 通過。第一次 staged gate 的 Bandit 指出動態組裝固定表名；改為封閉 SQL allowlist 而非 suppress 後，精確 23-file staged set 的 diff、governance、完整 tests、Worker contracts、repository hygiene、dependency audit、Bandit 與 secret scan 全部通過。正式 release gate 和部署不屬本階段。

`ITR-004` 的產品完成條件仍是：

1. 指定學校批准的 BitLocker USB／SD 與獨立 recovery-key 保管人。
2. 從包含本工具的正式 immutable bundle 執行 `export_offsite_recovery.ps1`。
3. 安全退出並把媒體離線存放在不同位置。
4. 在另一部受控 Windows 電腦或真正 replacement location，只由該 copied bundle 執行 `drill`。
5. 保存不含路徑及學生資料的 `pass`、RPO、RTO、日期、保管與保留證據。

## Rollback 與停止條件

本階段沒有部署或 schema 變更。若 seam 或文件契約有誤，可回退本階段來源 commit；正式 rc45、SQLite、Worker、Session、路由及資料完全不變。沒有批准的外置媒體時必須停止在「來源就緒、外部證據待辦」，不可改用內置磁碟、同步資料夾或未加密媒體繞過。
