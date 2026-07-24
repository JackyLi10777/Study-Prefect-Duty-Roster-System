# AI Agent Git／GitHub 操作規則

> **適用對象**：所有在此專案協作的 AI Agent（Codex、其他 Agent）。  
> **最高原則**：Codex 是 `main` 的最終合併者。其他 Agent 透過 `collab/agent-workspace` 提交。

---

## 一、專案 Git 架構總覽

```
origin/main  ←── codex/mainline  ←── collab/agent-workspace
 (GitHub)        (Codex 主線)        (其他 Agent 工作區)
  受保護分支       D:\code_v3           D:\code_v3-agent
```

| 分支 | 角色 | 誰操作 | 可否直接推送 |
|---|---|---|---|
| `main` | 正式發布線 | **僅 Codex**（透過 PR 合併） | 否（GitHub 保護） |
| `codex/mainline` | Codex 主開發線 | Codex | 是 |
| `collab/agent-workspace` | 其他 Agent 工作區 | **所有非 Codex 的 AI Agent** | 是 |
| `codex/*`（其他） | Codex 輔助分支 | Codex | 是 |
| `collab/*`（其他） | 擴展協作分支 | 視需要 | 是 |

## 二、工作樹（worktree）對照

| 本機路徑 | 分支 | 用途 |
|---|---|---|
| `D:\code_v3` | `codex/mainline` | **Codex 主工作區**：開發、審查、最終合併 |
| `D:\code_v3-agent` | `collab/agent-workspace` | **其他 Agent 工作區**：獨立開發、提交、發 PR |

**規則**：
- 每個 Agent **只能在分配給自己的工作樹內工作**。
- 不可跨越工作樹直接修改另一個 Agent 的檔案。
- 不可在同一工作樹內同時開啟多個 Agent session（會造成競爭寫入）。

## 三、Commit 訊息規範

### 前綴（type prefix）

| 前綴 | 用途 | 範例 |
|---|---|---|
| `feat:` | 新功能／新模組 | `feat: add centralized HTML escaping` |
| `fix:` | 錯誤修正 | `fix: escape aria-label content` |
| `security:` | 安全相關變更 | `security: add CSP headers` |
| `refactor:` | 重構（不改變行為） | `refactor: separate pointer-light surfaces` |
| `docs:` | 文件變更 | `docs: update README for branch structure` |
| `test:` | 測試變更 | `test: add html_safety contract tests` |
| `build:` | 建置／依賴 | `build: update requirements.lock` |
| `chore:` | 雜項（不影響程式） | `chore: clean tmp directories` |

### 格式要求

```
<type>: <簡短中文或英文摘要>

<可選的詳細說明區塊，每行不超過 72 字元>
```

- 第一行不超過 72 字元。
- 一個 commit 只做**一件事**（一個關注點）。
- **禁止** `git add -A` 或 `git add .` 把不相關檔案包進同一個 commit。
- 每個 commit 必須可獨立通過測試（不允許 broken intermediate commit）。

### 提交前分類規則

1. 先 `git status` 看清楚所有變更檔案。
2. 按**關注點**分組（安全 / UI / 文件 / 測試），每個關注點一個 commit。
3. 先提交**新模組**，再提交**使用該模組的變更**（相依順序）。
4. 最後提交**純文件變更**。

## 四、其他 Agent 工作流程（非 Codex）

### 4.1 開始工作前

```powershell
# 進入 Agent 工作樹
cd D:\code_v3-agent

# 確保與遠端同步
git fetch origin
git rebase origin/collab/agent-workspace

# 確認起點相同
git log -1 --oneline
```

### 4.2 開發與提交

1. **不要**建立額外的本機分支；直接在 `collab/agent-workspace` 上工作。
2. 按 [第三節](#三commit-訊息規範) 分組 commit。
3. 每個 commit 後執行 `git status` 確認乾淨。

### 4.3 推送與發 PR

```powershell
# 先拉取遠端最新（避免衝突）
git pull --rebase origin collab/agent-workspace

# 推送
git push origin collab/agent-workspace
```

推送後到 GitHub 建立 Pull Request：
- **Base**: `codex/mainline`
- **Head**: `collab/agent-workspace`
- PR 描述需列出所有 commit 摘要及變更模組。

### 4.4 等待審查

- Codex 會在 `D:\code_v3`（`codex/mainline`）審查 PR。
- 審查意見需逐條回覆或修改。
- **不可自行合併 PR**（合併權在 Codex）。

## 五、Codex 工作流程

### 5.1 審查 Agent PR

```powershell
cd D:\code_v3
git fetch origin

# 建立審查分支
git checkout -b review/agent-<日期> origin/collab/agent-workspace

# 審查 diff
git diff origin/codex/mainline..review/agent-<日期>

# 執行驗證
python -X utf8 scripts/verify_update.py
```

### 5.2 合併到 codex/mainline

審查通過後：

```powershell
git checkout codex/mainline
git merge review/agent-<日期> --no-ff
git push origin codex/mainline
git branch -d review/agent-<日期>
```

### 5.3 合併到 main（發布）

```powershell
# 建立 PR：codex/mainline → main
gh pr create --base main --head codex/mainline --title "..."
# 等待 CI 通過後合併
```

## 六、禁止事項

| 禁止動作 | 原因 |
|---|---|
| `git push --force` 到**任何**遠端分支 | 破壞歷史，GitHub 規則禁止 |
| 直接推送 `main` | GitHub 分支保護 |
| `git push --delete` 遠端分支（未經確認） | 遺失協作分支 |
| 提交 `.env`、`*.sqlite3`、`data/runtime/`、`logs/` 內容 | 機密與本機執行期資料 |
| `git add -A` 或 `git add .` | 可能夾帶機密或不相關檔案 |
| `git commit --amend` 已推送的 commit | 改寫已發布歷史 |
| `git rebase` 已推送的分支（codex/mainline 除外） | 改寫共享歷史 |
| 在工作樹外直接操作檔案 | 跳過 Git 追蹤 |
| 使用 `git filter-branch` 或 `git rebase -i` 清理歷史 | 需操作者明確授權 |
| 建立名稱不含 `codex/` 或 `collab/` 前綴的新分支 | 命名混亂 |
| 跨工作樹同時操作同一分支 | 競爭寫入 |

## 七、GitHub 規則（已在 GitHub 設定）

| 規則 | 說明 |
|---|---|
| `main` 分支保護 | 必須透過 PR，需通過 `test-and-audit` + `analyze` 檢查 |
| 不可 force-push `main` | 管理者也無法繞過 |
| `v*` 標籤不可變 | 發布標籤建立後不可刪除或移動 |
| Dependabot 自動 PR | 限 `pip` 與 `github-actions`，自動建立 |
| Actions 權限 | 僅讀取 repo 內容，無 secrets 寫入權 |

## 八、預推送檢查清單

每次推送前確認：

- [ ] `git status` 乾淨（沒有忘記 staged 的檔案）
- [ ] 每個 commit 只做一件事
- [ ] commit 訊息有正確的前綴
- [ ] 沒有 `.env`、`*.sqlite3`、`data/runtime/`、`logs/` 在 staged 中
- [ ] 新模組的 commit 先於使用該模組的 commit
- [ ] `python -X utf8 scripts/verify_update.py` 已執行且通過（如有修改 Python 檔案）
- [ ] 目標分支正確（Agent → `collab/agent-workspace`，Codex → `codex/mainline`）

## 九、快速參考卡片

```
┌─────────────────────────────────────────────────────────┐
│  你是                                         推送到          │
├─────────────────────────────────────────────────────────┤
│  其他 Agent    →  D:\code_v3-agent  →  collab/agent-workspace │
│  Codex         →  D:\code_v3       →  codex/mainline         │
│  發布          →  PR to main       →  main（僅 Codex）       │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Commit 前綴：feat│fix│security│refactor│docs│test│build│chore   │
│  一 commit 一事：不要混關注點                                │
│  禁止：force push、提交 secret、git add -A、直接推 main     │
└─────────────────────────────────────────────────────────┘
```
