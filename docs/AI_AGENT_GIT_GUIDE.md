# AI Agent Git／GitHub 操作規則

## 唯一主線與工作樹

所有新任務從最新 `origin/main` 建立隔離 worktree 與 `codex/<task>` 分支，
直接提交 PR 至 `main`。`codex/mainline` 只保留作歷史參考，不再作起點或 PR 目標。
輔助代理只實作分配的任務，由整合負責者審查後才合併；不得改動其他任務的 worktree。

開始前讀取 git status、HEAD 及來源差異。保留原始未提交內容、runtime 資料與其他任務。
不要在髒工作區 switch、reset、stash 或覆蓋檔案來取得乾淨基線。

```powershell
git fetch origin main
git worktree add -b codex/<task> <new-absolute-worktree-path> origin/main
```

每個可寫工作樹只由一個實作負責者擁有。其他代理可唯讀 review。
多個任務共享 Git object store，但不能把另一個任務未完成的工作當成穩定來源。
整合來源須記錄 final SHA、測試範圍及未完成項；相同 tree 不重複整合。

## 提交與驗證

- 使用 Conventional Commits：`feat:`、`fix:`、`refactor:`、`test:`、`docs:`、
  `build:`、`chore:`；一個提交一個關注點，第一行不超過 72 字元。
- 只 stage 已核對的明確路徑；禁止未審查的 `git add -A`／`git add .`。
- 測試行為、权限、版本及失敗路徑，不降低門檻使新實作看似成功。
- 提交前執行 `python -X utf8 scripts/verify_update.py --staged`。
  未加 `--release` 的結果不是正式部署證據。
- 推送後建立 `codex/<task>` → `main` PR；CI 要求 `test-and-audit`、
  `analyze` 及所有適用檢查。整合負責者完成 review 後才合併。
- main 前進時用普通 merge 同步並重新驗證；不重寫已分享的提交。

```powershell
git add -- <reviewed-paths>
python -X utf8 scripts/verify_update.py --staged
git commit -m "fix: describe one verified behavior"
git push -u origin codex/<task>
gh pr create --base main --head codex/<task> --title "<reviewed change>"
```

## 發布與正式啟用

合併後在乾淨、確切 protected-main 提交執行
`python -X utf8 scripts/verify_update.py --release`。
報告必須證明每個宣告 gate 已執行且成功，並保留來源與瀏覽器證據。

依 [更新流程](UPDATE_WORKFLOW.md) 核對主機、schema、備份與 Worker，
使用不可變 bundle 和已驗證的恢復路徑；不跨 schema 只回退程式碼。
生產狀態文件只能根據觀察到的部署結果生成，不预寫完成。

[正式啟用計劃](plans/20260905-system-integration.md) 已確認：
學校尚未正式使用；正式庫從空庫開始，演練資料不遷入。
這允許內部重構，但不授權自動刪除舊資料、跳過安全檢查或宣稱人工驗收完成。

## 禁止事項

- 直接或 force-push 至受保護主線；繞過檢查合併。
- 移動／刪除發布標籤、刪除遠端分支或改寫共享 Git 歷史。
- 提交憑證、token、`.env`、runtime SQLite、`data/runtime/`、日誌及未批准資料。
- 修改其他工作樹，或把某個來源的整檔版本蓋過另一個來源的已驗證行為。
- 把本地通過、主線合併、測試部署和正式啟用混成同一個完成狀態。

現有遠端規則不因本文改寫而改變。保護、發布與版本責任見
[Branch Strategy](BRANCH_STRATEGY.md) 及 [安全契約](SECURITY_AND_PRIVACY.md)。
