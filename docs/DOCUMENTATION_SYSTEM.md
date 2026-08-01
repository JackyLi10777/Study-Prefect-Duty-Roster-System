# 文件系統治理 / Documentation system governance

文件的目標不是累積最多文字，而是讓下一位讀者能快速找到、信任、修改及淘汰正確資訊。本專案以 [`documentation-manifest.json`](documentation-manifest.json) 管理生命週期與擁有者，以 [`status/current-release.json`](status/current-release.json) 管理會隨發布改變的精確狀態，並由 `scripts/project_governance.py` 自動檢查。

## 四個品質目標

1. **Findable**：每種讀者及工作都有一個入口，不必搜索整個版本庫。
2. **Authoritative**：一項會改變的事實只有一個 owner；其他文件連結或使用生成摘要。
3. **Changeable**：修改程式時可由 manifest 判斷需要同步哪份文件，不依賴記憶。
4. **Retirable**：決策、計劃與證據有清楚生命週期；舊資料不會冒充目前狀態。

## 文件類別與生命週期

| Class | 用途 | 更新方式 | 結束方式 |
|---|---|---|---|
| `entrypoint` | 讀者選路與產品摘要 | 保持短、連往 owner | 只在資訊架構改變時重構 |
| `living` | 目前狀態、迭代佇列 | 每次狀態改變同步更新 | 被新 owner 取代後標示 superseded |
| `standard` | 穩定契約、設計、安全、架構 | interface 或規則改變時更新 | 以 ADR 說明替換 |
| `runbook` | 可按步執行的操作、復原、部署 | 指令、畫面或責任改變時更新 | 舊程序移入歷史證據，不留雙入口 |
| `decision` | 背景、取捨、結果 | 決策後原則上不可改寫結論 | 後續 ADR supersede，不竄改歷史 |
| `governance` | Git、文件、agent、協作規則 | 流程或保護機制改變時更新 | 由新治理契約取代 |
| `evidence` | 某次可重現驗證或審計 | 補充勘誤，不改造成 living truth | 完成後保持不可變並標明日期 |
| `plan` | 尚未完成的意圖與順序 | 執行時更新狀態與偏差 | 完成、拒絕或被取代後封存 |
| `history` | 按時間記錄已發布變更 | 每次正式發布追加 | 不重寫成目前狀態 |

所有第一層文件及集合分類在 manifest；同一文件不可同時屬於兩個 class。

## 單一狀態來源

精確 release tag、commit、fingerprint、migration、backup、Worker、readiness 及真人驗收狀態只手動維護於：

```text
docs/status/current-release.json
```

人類可讀頁面及各重要指南的頁首摘要由它生成：

```powershell
python -X utf8 scripts/project_governance.py --write
python -X utf8 scripts/project_governance.py --check
```

普通指南不得在生成區塊外重複目前 tag、commit、fingerprint 或備份識別。`CHANGELOG.md`、日期化 evidence 及歷史段落可以保留過往值，但必須明確使用 historical／superseded／not deployed 等語意。

狀態語意固定分開：

- **live**：已在正式目標觀察到的版本；
- **candidate**：來源及測試可發布，但未證明正式環境已切換；
- **historical**：過往證據，不是目前 runtime；
- **rollback**：與目前 schema、Worker 及資料庫相容且已記錄的復原程序；
- **human acceptance**：首席導學風紀及教師顧問的受監督驗收，不由 CI 或 HTTP 200 代替。

## Topic owner 與更新觸發

`topic_owners` 指定每個主題的唯一權威文件。修改前先找到 owner，再按下表更新：

| 變更 | 必須檢查的 owner |
|---|---|
| runtime／模組 seam | `ARCHITECTURE_OVERVIEW.md`、`NICEGUI_ARCHITECTURE.md`、module-boundaries contract |
| UI token／motion／a11y | `Professional_Design_System.md` 與相應 acceptance evidence |
| Admin／Guest capability 或保存 | `UNIFIED_GUEST_SECURITY_MODEL.md`、operator/public guide |
| schema／migration／restore | architecture、release handover、host runbook、current release state |
| 公開 Worker／Access／Viewer | Cloudflare runbook、安全模型、public viewer guide |
| 操作者步驟或文案 | operator guide、quickstart、i18n／browser contract |
| release／deployment／rollback | current-release JSON、CHANGELOG、release evidence；再執行 `--write` |

README 只做導覽與產品摘要，不承擔完整 release history、架構細節或操作程序。

## 可迭代文件循環

1. **辨認改動結果**：描述使用者或維護者得到的實際改善。
2. **找到 owner**：由 manifest 選擇一份主要文件，不同專題才增加 supporting docs。
3. **改 interface，再改文字**：先確定真正行為與責任，再更新說明，避免用註解掩蓋混亂設計。
4. **更新狀態與決策**：會變的現況進 status；需要長期理由的取捨進 ADR；一次性結果進 evidence。
5. **自動驗證**：檢查分類、owner、連結、生成狀態與依賴方向。
6. **讀者驗證**：操作者能否按 runbook 完成工作；新維護者能否由 overview 找到 owning module。
7. **收斂**：刪除重複、過時及沒有決策價值的段落；不要為了顯得完整而複製內容。

## ADR 規則

跨模組 seam、資料持久化、安全身份、部署拓撲及治理方式的長期取捨使用 [`adr/`](adr/)：

- 編號、日期、狀態、背景、決策、後果、拒絕方案；
- Accepted ADR 不重寫原決策；新 ADR 以 `Supersedes` 取代；
- 小型、可逆、只影響單一 implementation 的變更不需要 ADR。

## 驗證及失敗處理

`python -X utf8 scripts/project_governance.py --check` 會拒絕：

- 未分類或重複分類的 Markdown；
- topic owner 或本機 Markdown link 不存在；
- current status JSON 格式、hash、gate 或 rollback 語意不完整；
- generated status 頁或 consumer 區塊過時；
- consumer 在生成區塊外重複可變的目前版本值；
- module-boundaries contract 禁止的反向 import。

正式推送前仍須使用 `verify_update.py --staged`。文件契約證明一致性，不證明 runtime、UI 或部署本身正確。

## English summary

The documentation system optimizes for findability, authority, changeability, and retirement. A manifest classifies every maintained document and assigns topic owners. Mutable production identifiers live in one JSON source and generate the human status plus consumer notices. Architecture dependencies are also executable. Plans, decisions, evidence, history, and live status remain distinct so an old paragraph cannot silently become current truth.
