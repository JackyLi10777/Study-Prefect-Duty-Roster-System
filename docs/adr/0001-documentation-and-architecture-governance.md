# ADR-0001: Documentation and architecture governance

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

精確 production tag、commit、fingerprint、migration、backup 及 rollback 語意曾被手動複製到十多份長文件。一次發布需要修改大量不相鄰段落，測試亦綁定特定版本字串。程式已有 policy、core、persistence、workflow 及 UI 的實際分層，但依賴方向主要靠讀者理解，新增改動可能把 UI 或 persistence 知識推入錯誤模組。

## Decision

1. 以 `docs/status/current-release.json` 作目前正式狀態的唯一人工維護來源。
2. 由 `scripts/project_governance.py --write` 生成 `CURRENT_STATUS.md` 及重要文件的頁首狀態區塊。
3. 以 `docs/documentation-manifest.json` 分類文件生命週期、topic owner、集合及 status consumer。
4. 以 `docs/architecture/module-boundaries.json` 記錄並執行最重要的 Python 依賴方向。
5. 將兩項契約接入普通 staged verification；它們不取代 runtime、browser、security、backup 或 deployment evidence。

## Consequences

- 發布狀態只需更新一份 JSON，再以 deterministic generator 同步所有摘要。
- 普通指南不能在 generated block 外複製 mutable current identifiers。
- 新文件必須有生命週期；新主題必須有一個 owner。
- 反向 import 在 review 前即可被拒絕。
- 工具與 manifest 增加少量治理成本，但換取較低 change amplification、較少 stale truth 及更容易的維護者 onboarding。

## Rejected alternatives

- **只繼續增加文件測試字串：** 能發現部分遺漏，但每次發布仍需手動更新所有副本。
- **把所有歷史與目前狀態放在 README／PROJECT_STATUS：** 查找容易，但文件持續膨脹並混淆 live、candidate、history 與 rollback。
- **引入完整文件網站或新框架：** 現階段增加依賴、建置及部署面，沒有證據顯示能改善校內操作。
- **一次拆散所有大型文件：** 風險高且容易只增加跳轉；改為在真實改動顯示 change amplification 時按 owner 漸進拆分。
