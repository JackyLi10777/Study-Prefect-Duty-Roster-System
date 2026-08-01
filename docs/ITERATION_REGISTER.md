# 可迭代改善登記 / Iteration register

本文件只保存仍會影響下一個決定的改善項目，並按 L1（正式效果、安全、資料或復原）→ L2（核心工作流、可靠性或真實負載）→ L3（可維護性改善）的產品影響排序。已完成的發布內容進 `CHANGELOG.md`；一次性驗證進 `docs/audits/`；精確正式狀態進 [`status/CURRENT_STATUS.md`](status/CURRENT_STATUS.md)。不要把一般願望、重複 TODO 或沒有驗收方式的想法放進本表。

## 目前佇列 / Current queue

| ID | Priority | Outcome | Owning module/document | State | Evidence needed to close |
|---|---|---|---|---|---|
| ITR-001 | L1 | 完成首席導學風紀與教師顧問的受監督真人驗收 | `ACCEPTANCE_EVIDENCE.md` | Ready | 真實身份登入、主要週流程、PDF／Viewer、長時間重新連線、手機／平板及顧問核對簽署 |
| ITR-004 | L1 | 建立加密離機備份並在不依賴正式主機的隔離位置演練完整還原 | `OFFSITE_DISASTER_RECOVERY.md` | Active | 真實 BitLocker USB／SD 目標摘要、分離密鑰保管、實際 RPO／RTO、離線保存確認，以及由該副本在 replacement location 完成的 `pass` 報告；來源測試或同機 C／D 副本不能關閉此項 |
| ITR-002 | L1 | 將已審查但尚未部署的來源整合成下一個正式發布，並從單一 current-release source 更新所有狀態摘要 | `status/current-release.json` | Ready | 正式 release gate、備份與隔離還原、受控 origin／必要 Worker 部署、canonical smoke、`project_governance.py --write`／`--check` 及 staged verifier 全部通過 |
| ITR-003 | L3 | 大型 living／standard 文件在實際觸及時按 owner 拆分，減少跨主題修改 | `DOCUMENTATION_SYSTEM.md` | Conditional | 一次真實改動仍需修改三個以上不相鄰段落，且拆分能降低而非增加跳轉成本 |

## 進入條件

新增項目必須同時有：

- 一個可觀察的使用者、操作者或維護者結果；
- `L1`、`L2` 或 `L3` 優先級，並按產品影響而非修改容易程度排列；
- 一個主要 owning module 或 document；
- 可判斷完成的 evidence；
- 明確狀態：`Proposed`、`Ready`、`Active`、`Conditional`、`Blocked` 或 `Done`；`Conditional` 只在記錄的觸發條件成立後才進入執行；
- 若風險高，附 rollback 或停止條件。

## 收斂規則

- `Done` 項目在對應 release／evidence 合併後移出本表，不長期堆積。
- `Blocked` 必須寫明外部依賴；沒有新證據時不反覆重開。
- `Conditional` 只有在觸發條件發生時才開始，避免為重構而重構。
- `PROJECT_STATUS.md` 中所有 `Tracked` 風險必須指向本表現存的 `ITR-NNN`；`Managed`、`Resolved` 及 `Historical` 不得假裝仍有活躍工作。
- 一項改動如果只改善措辭而不改善查找、正確性、操作或修改成本，不建立工程迭代。

## English summary

Keep only decision-relevant improvement work here. Every item needs an L1/L2/L3 priority, observable outcome, one owner, closure evidence, and a real state. Every `Tracked` project risk resolves to an existing iteration ID. Completed work moves to release history or evidence; vague wishes and duplicate TODOs do not accumulate.
