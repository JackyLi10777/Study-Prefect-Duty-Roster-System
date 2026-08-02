# 產品成熟度雷達：第六階段 / Product maturity radar: Phase 6

日期：2026-08-02（Asia／Shanghai）

範圍：rc47 上線後的發布真相、風險歸屬及可迭代改善佇列閉環

性質：文件與治理契約修正；不修改正式 runtime、Worker、資料庫、排班政策或使用者介面

## 現況、操作情境、優先級與方法

1. **現況：** `origin/main` 與 machine-owned current-release state 均記錄 rc47 已上線，但 living iteration register 仍把已完成的正式發布列為 `ITR-002 Active`，兩項其實只待真人驗收的風險亦錯誤指向它。
2. **操作情境：** 接手者需要從一張佇列表判斷下一步；把已部署功能標成「尚未部署」會誘發沒有缺陷依據的新版本，並分散真正的真人驗收及離機復原工作。
3. **優先級：** L1 發布與交接真相；先消除會改變正式操作決定的狀態漂移，再考慮任何新功能或視覺修改。
4. **方法：** `docs/status/current-release.json` 保持正式版本 owner，`PROJECT_STATUS.md` 擁有風險，`docs/ITERATION_REGISTER.md` 只保存未閉環工作；聚焦測試、治理檢查及 staged verifier 證明一致性，單一來源提交是完整 rollback boundary。

## 證據與判斷

- 遠端 annotated `v1.2.0-rc.47` 仍解析至 `15f53f97eda81b3f4b1518a44567e18171891711`；canonical `/` 與 `/healthz` 回應 HTTP 200，Gateway 自報 `status=ok`。
- `docs/status/current-release.json` 記錄 rc47、15／15 gates、Alembic `0012`、健康 origin、100% Worker 及 supervised acceptance `pending`；本階段沒有改寫這份已觀察的正式狀態。
- Host-local Support Inbox 在 rc24 前已進入來源，Quiet Command Center／rc47 亦保留其路由與元件；它的剩餘 H-21 工作是 canonical 真人操作，不是重新部署。
- Durable Viewer withdrawal 已包含在 rc47 release history 與 H-08 自動化證據；剩餘工作是受監督的 5 秒／90 秒零重疊驗收，不是另一個 source candidate。
- 因此移除 `ITR-002`，並把兩項風險歸回 `ITR-001`。歷史 Phase 5 audit 中的 `ITR-002` 保持不可變，因為它準確記錄當時 rc47 尚未部署的決策。
- 治理契約新增反向檢查：`Proposed`、`Ready`、`Active` 或 `Blocked` iteration 若沒有任何 `Tracked` 風險引用即失敗；未觸發的 `Conditional` 仍可存在而不製造假風險。

## A–J 雷達

| Domain | Phase 5 → 6 | 本階段裁決 | 仍需證據／owner |
|---|---:|---|---|
| A. 操作者成果及工作流程 | 3 → 3 | 正式流程無改動；Support／Viewer 待驗收工作現在回到正確 owner | `ITR-001` |
| B. 政策及資料正確性 | 4 → 4 | policy、fairness、transaction 及正式資料無改動 | Managed |
| C. 資料庫及資料存取 | 4 → 4 | SQLite／Alembic／backup 狀態無改動 | Managed |
| D. 可靠性及復原 | 2 → 2 | rc47 具備 external-media seam，但沒有真實 BitLocker replacement-location drill | `ITR-004` |
| E. 並行、容量及效能 | 3 → 3 | 既有 mixed-gateway／scale 證據仍有效；本輪不製造新 SLO 聲稱 | Managed |
| F. 安全及私隱 | 3 → 3 | 身分、Guest、Viewer 及支援資料邊界無改動；真人 canonical 驗收仍未代簽 | `ITR-001` |
| G. 架構及可維護性 | 3 → 4 | living risk 與 actionable iteration 現為雙向可執行契約，不只單向引用 | `ITR-003` 仍為 Conditional |
| H. 產品設計及無障礙 | 3 → 3 | rc47 自動矩陣保持有效；實體手機與受監督工作流仍待完成 | `ITR-001` |
| I. 資訊架構及元件一致性 | 3 → 3 | 本輪沒有為了改動而重構 UI；Quiet Command Center owner 不變 | Managed |
| J. 營運、可觀察性、文件及交接 | 3 → 3 | 發布真相與佇列已一致，但真人簽署及異機復原仍阻止整體升級 | `ITR-001`／`ITR-004` |

## 驗收、停止與回退

本階段的完成條件是：目前佇列不再含已發布的 `ITR-002`；Support／Viewer 的未完成證據只指向 `ITR-001`；可執行 iteration 的反向引用回歸測試通過；專案治理及 staged verifier 通過；Git diff 不含 runtime、Worker、schema 或資產。若契約造成不合理阻塞，只回退本階段單一提交，rc47 正式 bundle、Worker 及資料庫均不受影響。

下一個真實 L1 步驟只剩兩項：由首席導學風紀與教師顧問完成 `ITR-001`，以及使用學校批准的 BitLocker 外置媒體在 replacement location 完成 `ITR-004`。自動化、同機副本或 Codex 自我簽署都不能取代兩項證據；在它們可用前，不建立沒有缺陷或政策依據的新版本。

## English summary

Phase 6 removes the stale post-release `ITR-002` item and reassigns the live Support Inbox and Viewer-withdrawal residuals to supervised acceptance (`ITR-001`). The governance contract now checks both directions: tracked risks must resolve to real iterations, and every actionable non-conditional iteration must be justified by a tracked risk. Production rc47 is unchanged. The remaining L1 gates are supervised school acceptance and a real encrypted off-host replacement-location recovery drill.
