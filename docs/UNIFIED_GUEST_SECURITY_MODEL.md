# 統一訪客模式安全模型 / Unified guest security model

> **文件狀態（v1.2 候選）：** 本文件描述 `codex/unified-guest-redesign` 分支的現行程式契約。統一訪客模式仍由 `SING_YIN_UNIFIED_GUEST=0` 預設關閉；只有正式發布 gate、隔離瀏覽器證據及 Cloudflare 設定全部通過後，才可在 Windows origin 啟用。這不是已部署聲明。

## 1. 目的

訪客和管理員應看見同一套 NiceGUI 頁面、導航、元件及每週工作流程，但兩者使用的身份、能力和資料空間完全不同：

- 管理員處理正式 SQLite、備份、公平帳本、審計及發布。
- 訪客只處理固定、虛構、繁中姓名的示範資料。
- `/view#…` 仍是另一條只讀、可分享的已發布週表能力連結；它不是訪客工作區，也不能提升權限。

`/guest` 與 `/try` 只保留為兼容入口，會轉到同一品牌入口並啟動訪客 session；不再維護另一套靜態試用產品。

## 2. 已實作的身份及能力邊界

正式程式使用翻譯文字以外的穩定代碼：

```text
AccessMode = PUBLIC | ADMIN | GUEST | LOCAL_MAINTENANCE

PageContext
├── principal
├── capabilities
├── workspace
├── preference_store
└── request_reference
```

`CapabilityPolicy` 採拒絕優先。訪客只獲：

- `demo_data.read`
- `demo_state.modify`
- `demo_result.download`
- `session_preferences.modify`

AI、名冊匯入、檔案上載、剪貼簿攝取、外部連接、同步、永久寫入、背景工作、外部交付、昂貴運算及真實資料匯出均被拒絕。頁面隱藏或停用按鈕只屬提示；`PageContext`、Guest adapter、下載及分享服務會再次核對能力。

Cloudflare Worker 會：

1. 移除瀏覽器自行加入的身份及 `Cf-Access-*` 標頭；
2. 驗證管理員 Access JWT 或訪客 session；
3. 以 HMAC 簽署包含 `mode`、`subject`、`sid`、`exp`、`auth_epoch` 及 `kid` 的 origin principal；
4. 由 NiceGUI origin 重新驗證簽章、到期、撤權 epoch 及 key ID；
5. 在 `/auth/status` 及每次回調重新確認 session 仍有效。

## 3. 訪客工作區

已實作的 `GuestWorkspaceRegistry` 是程序記憶體內、有限額、每分頁隔離的工作區：

| 邊界 | 預設值 |
|---|---:|
| Session 有效期 | 30 分鐘 |
| 同時訪客 session | 24 |
| 每 session 分頁 | 4 |
| 虛構風紀 | 40 |
| 示範週次 | 4 |
| 已簽署 snapshot | 256 KiB |
| 單次下載 | 5 MiB |
| 每分鐘命令 | 60 |

每個 NiceGUI client 取得獨立 `workspace_id`。狀態不寫入正式 SQLite、`app.storage.user`、備份、檔案、KV、Redis、`localStorage`、IndexedDB、Cache Storage、分析或內容日誌。Guest PDF／JSON 只在記憶體建立，標明 `DEMO`，以一次性 session-bound 下載票據回傳，並使用 `Cache-Control: no-store`。

登出、session 到期、撤權、分頁斷線及 origin 重啟會作冪等清理；前端以 `BroadcastChannel` 通知同 session 分頁清除狀態、媒體及下載票據。

### 尚未完成的瀏覽器 snapshot 橋接

程式已具備 HMAC snapshot codec，並驗證篡改、錯誤 SID、錯誤 workspace／tab、過期、大小、revision、重播及程序 boot ID。**現時 NiceGUI 頁面尚未把每次 Guest workspace revision 寫入及還原自 `sessionStorage`。** 因此 v1.2 正式啟用前仍要完成並驗證：

- 每次有意義修改後保存已簽署 snapshot；
- 重新整理同一分頁時只還原同 SID／workspace／tab 的最新 revision；
- 複製分頁時重新分配 workspace，而非兩頁共用；
- 到期、登出、撤權及程序重啟後拒絕舊 snapshot。

在這項 gate 完成前，不得把「重新整理後仍保留 30 分鐘 Guest 狀態」寫成已完成。

## 4. 資料與整合限制

訪客可操作同一套畫面，但以下項目只顯示一致的限制狀態：

- 名冊／AI：只用內置 fixture 或預先計算示例；不能上載、貼上或呼叫外部 AI。
- 備份／還原／新學年：只可重設 fixture 或觀看模擬說明；不能碰正式備份目錄或 maintenance lock。
- 音樂：只可改目前 session 的內置音樂選擇；不能輸入網址、YouTube、檔案或永久歌單。
- 分享：不能建立、撤銷或重新發出正式 Viewer 連結。
- 報告／PDF／JSON：只含虛構資料及 `DEMO` 標記；不能匯出正式資料。

UI 應以 `LIVE / DEMO / PRECOMPUTED / RESTRICTED` 語意狀態解釋差別，不以重複彈窗阻礙流程。

## 5. 正式資料並行及恢復關係

Guest adapter 不引用正式 SQLAlchemy、AI、HTTP、備份、上載、分享或背景工作。管理員仍由正式 `RosterWorkflow` 負責：

- `expected_version` 比對及衝突提示；
- 命令收據與冪等重播；
- 發布單一勝者及公平帳本；
- 提交後的 `backup_obligations`；
- 啟動時修復未完成備份，失敗則 `/readyz` 回報 degraded 並阻止新寫入；
- maintenance lock 下的受控還原。

`/healthz` 只表示程序及資料庫可讀；`/readyz` 才表示 migration、maintenance、恢復標記、備份義務及寫入能力均正常。正式部署及監察不可只看 `/healthz`。

## 6. 發布 gate

啟用 `SING_YIN_UNIFIED_GUEST=1` 前必須有以下證據：

- 服務層能力矩陣及 Guest 依賴邊界；
- snapshot 篡改、到期、重播及分頁隔離；
- 管理員／訪客並行及交叉下載隔離；
- 正式寫入衝突、冪等、備份崩潰及隔離還原；
- 所有正式路由的 Admin／Guest DOM 骨架對應；
- 繁中／英文、淺／深色、375／768／1280／1440 px、鍵盤、焦點、對比、reduced motion、console；
- 重複路由切換的 DOM、監聽器及 heap 趨勢；
- `python -X utf8 -m pytest -q`；
- `python -X utf8 scripts/verify_release_candidate.py`；
- 已驗證正式備份及隔離還原。

任何 gate 失敗，功能旗標保持 `0`，Windows origin 及 Worker 不切換。

## English operational summary

The v1.2 candidate uses the same NiceGUI routes and components for administrators and guests, but resolves a server-verified `PageContext` to either the official workflow or a bounded in-memory guest adapter. Guest capability is deny-by-default and excludes AI, upload/import, persistent storage, external delivery, official backup/restore, and real-data export. Guest exports are one-shot, memory-only, `DEMO`-marked, and `no-store`.

The source contains signed principal verification, a bounded guest registry, per-client workspace IDs, session expiry/revocation monitoring, cross-tab logout cleanup, and an HMAC snapshot codec. The browser bridge that saves and restores the latest signed snapshot through `sessionStorage` is still a release gate. `SING_YIN_UNIFIED_GUEST` therefore remains disabled by default, and this document does not claim that v1.2 has been deployed.
