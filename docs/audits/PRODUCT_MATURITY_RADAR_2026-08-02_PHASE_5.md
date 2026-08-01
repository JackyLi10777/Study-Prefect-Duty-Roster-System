# 產品成熟度雷達：第五階段 / Product maturity radar: Phase 5

日期：2026-08-02

範圍：`ITR-002` 的正式候選發布完整性、驗證器輸出隔離及驗證前後來源一致性

性質：本機 exact-source 候選證據；不是 tag、Windows／Worker 部署或真人驗收

## 現況、操作情境、優先級與方法

1. **現況：** `origin/main` 的 `6f7a19dd977ab3b4e25ad3e0333e759a42281714` 已通過主分支 CI，canonical 入口與本機 `/healthz`／`/readyz` 健康；正式運行仍是 rc45。
2. **操作情境：** 已合併的 Viewer 撤銷、離機復原 seam 及混合 Gateway 證據尚未進入正式主機，而不可靠的 release report 會令維護者誤以為候選可安全切換。
3. **優先級：** L1／`ITR-002`；先證明候選來源在完整 gate 前後完全一致，再考慮 tag 或部署。
4. **方法：** release-evidence owner 負責 schema／source binding，browser verifier 負責把一次性證據寫入 ignored logs；以聚焦測試、完整 15-gate run、最後 `git status` 及文件契約驗收，正式 rc45 是整個階段的 rollback boundary。

## 被否決的第一次綠燈

第一次 `python -X utf8 scripts\verify_update.py --release` 對乾淨 `6f7a19d` 執行，15 個功能 gate 全部回報 `pass`。然而完成後 `git status --short` 顯示以下三個已追蹤檔案被瀏覽器 verifier 改寫：

- `test-results/uiverse-components/desktop-light-components.png`
- `test-results/uiverse-components/desktop-dark-components.png`
- `test-results/uiverse-components/mobile-320-light-components.png`

因此該報告雖然顯示 `sourceDirty=false`，只證明開始時乾淨，沒有證明結束時仍是同一候選。本階段拒絕把這份表面綠燈當作 release evidence，並把缺口列為 L1 發布完整性問題。

## 實作決定

- `verify_nicegui_ui.py` 的 routine component captures 改寫到 Git ignored `logs/uiverse-components`；已追蹤 visual reference 只可由另一項明確 baseline review 修改。
- release report 升級為 schema 3，並新增 `postVerificationSource`。
- 完整 gate 後以不使用 runtime cache 的方式重新計算 source fingerprint，同時重新讀取 file count、HEAD commit、HEAD tree 及完整 working-tree 狀態。
- `postVerificationSource` 必須與開始時的五項資料完全相同且 `sourceDirty=false`；任何 verifier-induced mutation、提交／tree 漂移、漏入來源或 fingerprint 改變都令整體 `fail`。
- evidence reader 同樣 fail closed：缺少、污損或不匹配的 post-check binding 不可在交接頁顯示為通過。
- Windows origin 與 Worker deployment preflight 都要求 schema 3 nested binding 與頂層來源完全一致；Worker 路徑另以目前 tag checkout 的 Python runtime 重新計算 fingerprint／file count，不可信任可改寫的 ignored JSON。

## 修正後證據

- 309 個 release-sensitive source files；fingerprint `86e11e061a5b6d0ee08fc7e1dd2b8227c63c0575acd143440f4f41df8da637d3`。
- 15／15 gate 通過：repository hygiene、安全、6 個 motion、53 個 Worker contracts、完整 Python、compile／dependency、16 組主題交接、desktop、runtime、完整寫入／PDF／還原、mobile／tablet、strict readiness、Guest isolation 及 partial-backup recovery。
- schema 3 `postVerificationSource` 與初始 fingerprint、file count、commit、tree 完全相同，最後 Git working tree 乾淨。
- 正式主機、Worker、schema 及 current-release JSON 沒有改動；線上仍是 rc45。

## A–J 雷達

| Domain | Phase 4 → 5 | 本階段裁決 | 仍需證據／owner |
|---|---:|---|---|
| A. 操作者成果及工作流程 | 3 → 3 | 沒有改變每週流程；候選狀態更可信 | `ITR-001` 真人驗收 |
| B. 政策及資料正確性 | 4 → 4 | policy／transaction 沒有改動，完整 gate 重驗通過 | Managed |
| C. 資料庫及資料存取 | 4 → 4 | 隔離寫入、還原及 partial-backup 重驗通過 | Managed |
| D. 可靠性及復原 | 2 → 2 | source-level off-site seam 已驗證，但沒有真實外置媒體 | `ITR-004` |
| E. 並行、容量及效能 | 3 → 3 | Phase 4 混合負載證據保持有效，本輪沒有新 soak／edge 數據 | Managed |
| F. 安全及私隱 | 3 → 3 | 安全 gate、Guest 隔離與虛構資料重驗通過 | `ITR-001`／`ITR-004` |
| G. 架構及可維護性 | 3 → 3 | 一次性證據與 tracked baseline 分離；release schema 有單一 owner | `ITR-003` 仍為 conditional |
| H. 產品設計及無障礙 | 3 → 3 | desktop／mobile／tablet／theme 自動矩陣重驗；無 UI 改動 | `ITR-001` 實體裝置 |
| I. 資訊架構及元件一致性 | 3 → 3 | 元件 grammar 重驗，但不以截圖改寫代替審查 | Managed |
| J. 營運、可觀察性、文件及交接 | 3 → 3 | report 現可證明 gate 沒有改變候選；尚未部署故不升至 4 | `ITR-002` Active |

## 停止、回退及下一步

本階段在 corrected 15-gate report、post-verification source match、clean tree、文件契約及無可歸因 P0／P1 後停止。若 schema 3 或 browser evidence routing 需回退，只回退本階段來源提交；正式 rc45 不受影響。

下一個最高價值步驟仍是 `ITR-002` 的受控正式發布，但必須在本次任務有明確部署授權時，從 protected-main final commit 建立 annotated rc46 tag，重新產生 exact report，完成正式備份／隔離還原、origin switch、必要 Worker 判斷、canonical smoke 及 current-release generation。`ITR-001` 與 `ITR-004` 仍分別需要真人及真實外置媒體，不能由自動化冒充完成。

## English summary

Phase 5 rejects a superficially green release report because the browser verifier rewrote three tracked component screenshots after the initial clean-source check. Routine captures now go to ignored logs, and schema 3 requires a refreshed post-verification fingerprint, file count, commit, tree, and clean Git state to match the initial candidate exactly. The corrected 309-file candidate passed all 15 gates and finished clean. Production remains rc45; tagging, deployment, physical-device acceptance, and real external-media recovery are still separate evidence.
