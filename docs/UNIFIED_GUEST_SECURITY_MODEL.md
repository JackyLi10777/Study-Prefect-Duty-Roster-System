# 統一訪客模式安全模型 / Unified guest security model

<!-- SING_YIN_CURRENT_STATUS:START -->
> **已核實線上來源（2026-08-01）：** Windows origin 正運行 clean annotated `v1.2.0-rc.45`／`90777345ea9ed5652c73873edb3c8c846a9ceac5` 的不可變 bundle；308-file 指紋 `032bf3d5d41a74e6ad50090ab7ffb13af6e5cca43a23c24adb3f8506d6d29a83` 通過 15／15 gate。SQLite 位於 Alembic `0012`；正式備份 `20260801-064628-279309-manual_verified_backup.sqlite3`／SHA-256 `bdf8366aa7b2d3b91d6754dc58d9ec0b6725bf29f7fe3e7d5bf3592b223f69e8`、隔離還原、health、`writeReady=true`、`maintenance=false`、`recoveryRequired=false` 及 `pendingBackups=0` 已核對。Worker 來源沒有改動，canonical Worker `394e2205-ae8f-4eef-a13a-e701931e6f0d` 維持 100% 流量且健康。`v1.2.0-rc.43` 只屬歷史來源，migration `0012` 後不可作 code-only rollback；須使用受控的相容資料庫還原。真人驗收仍為 `pending`。精確狀態及更新規則見[目前系統狀態](status/CURRENT_STATUS.md)。
<!-- SING_YIN_CURRENT_STATUS:END -->
>
> **歷史 rc30 乾淨發布證據：**受控 Windows origin 曾以受控方式運行 annotated tag `v1.2.0-rc.30`／commit `74b84f43786b00feb15b51a6270ff71c9430773f`；296 個 runtime 來源檔案以指紋 `15d155d8d745b14b574b08d793150c93aa77946e7d17a63030844c44adededbc` 通過 14／14 正式 gate 並完成受控切換。canonical Worker `11763f08-d40d-46d5-93dc-5ca2599d4154` 通過 0% smoke 後承接 100% 流量。這組 clean pair 是當時第一個已知、已驗證的復原目標；現行線上版本及其受控資料庫復原限制以本頁頂部生成狀態為準，較早版本均屬歷史來源。Admin、Guest 與公開 Viewer 使用同一身份邊界；該次 deployment report 證實當時 origin ready 且無 maintenance、recovery 或 pending backup obligation，真人身份與工作流驗收仍保持獨立未完成。

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
| Guest 單次下載 | 5 MiB |
| 每分鐘命令 | 60 |

每個 NiceGUI client 取得獨立 `workspace_id`。狀態不寫入正式 SQLite、`app.storage.user`、備份、檔案、KV、Redis、`localStorage`、IndexedDB、Cache Storage、分析或內容日誌。Guest PDF／JSON 只在記憶體建立，標明 `DEMO`，以一次性、同 verified Guest access mode 及 session 綁定的下載票據回傳，並使用 `Cache-Control: no-store`。

冪等命令收據只保存 operation、request digest、applied revision、result digest 及有限 metadata，不保存每次命令的完整 workspace。相同 `command_id`／payload 只執行一次；重播會以 `replayed=true` 回傳目前 copy-safe workspace 並附原 applied revision，避免把過時 snapshot 偽裝成當前狀態。相同 ID 配不同 payload 會被拒絕。每個 workspace 最多 120 項 receipt，另有全域 count／metadata admission 上限；清理、到期及分頁隔離保持冪等。

Guest 的語言、外觀、音樂及音效由獨立的有限期 origin-memory preference registry 保存；它只接受已核實 Guest session、限制鍵值及數值範圍，並與工作區一同在登出、到期、撤權或程序重啟時清除。這修正重新整理後語言回復的問題，但不把 Guest 偏好提升為永久資料。公開入口不會讀取或持續同步工作區偏好；只有刻意進入 Admin／Guest 時，才可暫存已明確選擇的 `light`／`dark` 提示，最長 120 秒。Worker 核對後把它放入已簽署 session 及 request-bound principal，建立 session 時清除暫存 cookie；目的地已有偏好時不覆寫。下載端點以同一有界限 `GeneratedFile` registry 服務 Admin／Guest，仍須重新核對 principal、能力、access mode、session、一次性票證、大小及 `no-store`；Guest 單檔上限為 5 MiB、Admin 為 64 MiB，registry 總內容上限為 128 MiB，並保留 64 MiB／16 票證予 Admin；總票證上限為 128、每 session 為 8、票證 TTL 為 90 秒。跨模式重播會被拒絕而不消耗合法票據，Guest 飽和亦不能阻塞正式檔案交付。前端帶同 cookie 取得 blob，先核對 HTTP status 及精確 MIME，才建立短期 object URL，不能靠隱藏按鈕或可猜網址繞過限制。

Assist. 排班模式也維持同頁面、同穩定代碼及同政策驗證：`legacy_fixed_weekday` 保留 AHP 的固定星期，`flexible_weekly` 只在名冊已選「可值班日」內按週輪換並在可行情況避免上週同日。兩者都拒絕非 AHP、請假日、同日重複及不連續規則衝突。Admin 透過 migration `0011_assist_assignment_mode` 把模式保存於週表；Guest 只把相同欄位保存在目前記憶體 workspace，重設或到期後消失。

登出、session 到期、撤權、分頁斷線及 origin 重啟會作冪等清理；前端以 `BroadcastChannel` 通知同 session 分頁清除狀態、媒體及下載票據。

### 已實作的瀏覽器 snapshot 橋接

程式已具備 HMAC snapshot codec 及 NiceGUI 瀏覽器橋接：

- 每次有意義修改後，Guest adapter 只向該連線分頁推送最新、已簽署的 snapshot token；
- 分頁只把 token、workspace／tab ID 及 revision 寫入 `sessionStorage`，不保存可獨立信任的明文工作區；
- 重新整理時，前端向 `POST /api/guest/snapshot/restore` 提交 token，伺服器須同時核對 Worker 已驗證的 Guest session、穩定 NiceGUI tab、workspace、程序 boot ID、revision 及當次連線 nonce；
- 複製分頁會因新的 NiceGUI tab ID 取得另一個 workspace；來源分頁的 token 不能綁定到新分頁；
- 篡改、錯誤 SID、錯誤 workspace／tab、過期、過大、舊 revision、重播或舊 boot token 均被拒絕；頁面繼續使用安全虛構 fixture，並收到新的合法 token；
- 登出、到期、撤權及跨分頁 session 終止會清除 `sessionStorage`、媒體及待下載票據；origin 重啟後舊 boot token 按設計失效。

`tests/test_guest_snapshot_bridge.py` 聚焦驗證同分頁還原、token 輪換、複製／篡改拒絕、連線 nonce、登出清理及只使用 `sessionStorage` 的前端契約；完整 pytest、隔離瀏覽器及 release verifier 已納入 rc20 的 14／14 source-matched 正式候選報告。這完成候選機器驗證，但歷史或候選報告都不可代替受控 origin 切換、canonical smoke 及真人驗收。

## 4. 資料與整合限制

### Guest 問題回報

Guest 的 `/support` 介面與 Admin 使用同一內容結構，但能力政策拒絕本機收件匣
寫入及附件上載。報告只在目前瀏覽器記憶體組合，使用者可下載 JSON、複製摘要
或開啟電郵草稿；流程不使用正式 SQLite、`app.storage.user`、session snapshot、
localStorage、IndexedDB、Cache Storage、備份或背景工作。登出、到期、撤權、
重新載入或程序重啟均不需要伺服器清理，因為 origin 從未收到報告內容。

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
- 正常安全啟動時修復未完成備份，失敗則 `/readyz` 回報 degraded，並由中央 admission guard 阻止所有業務寫入；
- 如 durable recovery marker 在啟動前已存在，系統在 migration／session／SQLite journal mutation 之前進入 diagnostic-only，只提供不改資料的健康與復原診斷；
- maintenance lock 下的受控還原。

`/healthz` 只表示程序及資料庫可讀；`/readyz` 只在 storage health 正常、`workflowInitialized=true`、沒有 maintenance／recovery marker、待完成備份義務為零且 startup repair 沒有失敗時，才以 HTTP 200 回報 `writeReady=true`。Diagnostic-only 啟動會固定回報 `workflowInitialized=false`、`writeReady=false` 及 HTTP 503；單獨移除 marker 不會令現有程序變成可寫，必須完成受控恢復並安全重啟以建立真正 workflow sessions。正式部署及監察不可只看 `/healthz`。

## 6. 發布 gate

每次把涉及統一 Guest 的新候選切換到正式環境前，都必須重新取得以下證據：

- 服務層能力矩陣及 Guest 依賴邊界；
- snapshot 篡改、到期、重播及分頁隔離；
- 管理員／訪客並行、票據同 access mode／session 綁定、重播／跨模式拒絕，以及 Guest 飽和時 Admin reserved capacity；
- 正式寫入衝突、冪等、備份崩潰及隔離還原；
- 所有正式路由的 Admin／Guest DOM 骨架對應；
- 繁中／英文、淺／深色、375／768／1280／1440 px、鍵盤、焦點、對比、reduced motion、console；
- 重複路由切換的 DOM、監聽器及 heap 趨勢；
- `python -X utf8 -m pytest -q`；
- `python -X utf8 scripts/verify_release_candidate.py`；
- 已驗證正式備份及隔離還原。

任何 gate 失敗，都不得切換候選 Windows origin、Worker 或現行 `SING_YIN_UNIFIED_GUEST` 設定；受控主機繼續使用最近一組已驗證的 origin／Worker 組合。

## English operational summary

The live v1.2 product uses the same NiceGUI routes and components for administrators and guests, but resolves a server-verified `PageContext` to either the official workflow or a bounded in-memory guest adapter. Guest capability is deny-by-default and excludes AI, upload/import, persistent storage, external delivery, official backup/restore, and real-data export. Guest exports are one-shot, memory-only, `DEMO`-marked, and `no-store`.

The source contains signed principal verification, a bounded guest registry, per-client workspace IDs, session expiry/revocation monitoring, cross-tab logout cleanup, an HMAC snapshot codec, and the `sessionStorage` browser bridge. Each revision is saved only as a signed, tab-bound token; restore also requires the current live-connection nonce. Duplicate tabs receive new workspaces, while tampered, copied, expired, stale, or old-boot tokens fall back safely to the fictional fixture. Admin and Guest share the stable Assist. mode codes and policy checks, while only Admin persists the roster mode through migration `0011_assist_assignment_mode`.

The exact current release, migration, Worker and acceptance identity is generated at the top of this document. The bounded-receipt, write-boundary-expiry, semantic-motion, honest-waiting and R7 reliability changes remain part of the verified source. Older applications require the compatible controlled database restore recorded in current status and are not code-only rollback targets.
