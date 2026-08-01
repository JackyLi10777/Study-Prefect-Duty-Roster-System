# 可迭代改善登記 / Iteration register

本文件只保存仍會影響下一個決定的改善項目。已完成的發布內容進 `CHANGELOG.md`；一次性驗證進 `docs/audits/`；精確正式狀態進 [`status/CURRENT_STATUS.md`](status/CURRENT_STATUS.md)。不要把一般願望、重複 TODO 或沒有驗收方式的想法放進本表。

## 目前佇列 / Current queue

| ID | Outcome | Owning module/document | State | Evidence needed to close |
|---|---|---|---|---|
| ITR-001 | 完成首席導學風紀與教師顧問的受監督真人驗收 | `ACCEPTANCE_EVIDENCE.md` | Open | 真實身份登入、主要週流程、PDF／Viewer、手機／平板及顧問核對簽署 |
| ITR-002 | 下一次正式發布以單一 current-release source 更新所有狀態摘要 | `status/current-release.json` | Ready | `project_governance.py --write`、`--check` 及 staged verifier 通過，沒有手動複製目前版本值 |
| ITR-003 | 大型 living／standard 文件在實際觸及時按 owner 拆分，減少跨主題修改 | `DOCUMENTATION_SYSTEM.md` | Conditional | 一次真實改動仍需修改三個以上不相鄰段落，且拆分能降低而非增加跳轉成本 |

## 進入條件

新增項目必須同時有：

- 一個可觀察的使用者、操作者或維護者結果；
- 一個主要 owning module 或 document；
- 可判斷完成的 evidence；
- 明確狀態：`Proposed`、`Ready`、`Active`、`Conditional`、`Blocked` 或 `Done`；`Conditional` 只在記錄的觸發條件成立後才進入執行；
- 若風險高，附 rollback 或停止條件。

## 收斂規則

- `Done` 項目在對應 release／evidence 合併後移出本表，不長期堆積。
- `Blocked` 必須寫明外部依賴；沒有新證據時不反覆重開。
- `Conditional` 只有在觸發條件發生時才開始，避免為重構而重構。
- 一項改動如果只改善措辭而不改善查找、正確性、操作或修改成本，不建立工程迭代。

## English summary

Keep only decision-relevant improvement work here. Every item needs an observable outcome, one owner, closure evidence, and a real state. Completed work moves to release history or evidence; vague wishes and duplicate TODOs do not accumulate.
