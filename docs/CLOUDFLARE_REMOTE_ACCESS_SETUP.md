# Cloudflare 單一網址遠端存取手冊（Windows 專用主機）

<!-- SING_YIN_CURRENT_STATUS:START -->
> **已核實線上來源（2026-08-10）：** Windows origin 正運行 clean annotated `v1.2.0-rc.57`／`f83bbbb095e5fb2c029ac37add1308f33dd2eb9e` 的不可變 bundle；317-file 指紋 `33e77fb6cddc791b60e2b695db417f29d508b77bba71f143186c4f5591ba916a` 通過 15／15 gate。SQLite 位於 Alembic `0014`；正式備份 `20260810-111743-227200-manual_verified_backup.sqlite3`／SHA-256 `d9603c329c995132d9955bcfbe74aafa46c5b5c6e0393e7f009b76bc2b746a29`、隔離還原、health、`writeReady=true`、`maintenance=false`、`recoveryRequired=false` 及 `pendingBackups=0` 已核對。Worker 來源已更新，canonical Worker `7951ca55-ffda-4f16-b570-d37486311914` 維持 100% 流量且健康。`v1.2.0-rc.56` 只屬歷史來源，migration `0014` 後不可作 code-only rollback；須使用受控的相容資料庫還原。真人驗收仍為 `pending`，實體離線 BitLocker 復原演練仍為 `pending`。精確狀態及更新規則見[目前系統狀態](status/CURRENT_STATUS.md)。
<!-- SING_YIN_CURRENT_STATUS:END -->
>
> **歷史 rc30 乾淨發布證據：** Windows origin 曾以受控方式運行並驗證健康、ready 的 `v1.2.0-rc.30`／`74b84f43786b00feb15b51a6270ff71c9430773f`；其 296-file runtime fingerprint `15d155d8d745b14b574b08d793150c93aa77946e7d17a63030844c44adededbc` 已通過 14／14 gate，並完成正式備份、隔離還原及受控切換。canonical Worker `11763f08-d40d-46d5-93dc-5ca2599d4154` 通過 0% version smoke 後承接 100% 流量。canonical root、capability health 與 rendered desktop／320px／Guest Engineering checks 通過，private readiness 保持預期 redirect。當時的下一層 origin／edge 回退分別是 rc27／`c4c728aa…` 與 `d7b51f21…`；目前復原先使用較近的乾淨 rc30／`11763f08…`。真人 Admin／Viewer／長連線及操作驗收仍須依清單完成。
>
> **SSH 維護邊界（2026-07-17）：** Windows 主機另有只限 loopback、Ed25519 金鑰登入的 SSH 維護服務。目前只供主機本身的 Codex／受控終端使用；日後如新增校外 SSH，必須建立獨立的 Cloudflare 私有 SSH 路由指向 `localhost:22`，不可啟用 Windows OpenSSH 公開防火牆規則或路由器轉發。詳見 [Windows SSH 維護通道](WINDOWS_SSH_MAINTENANCE.md)。

## 1. 日常使用者只需知道

所有人使用同一個 canonical `workers.dev` 網址：

<https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/>

- 訪客按 **訪客體驗**，進入同一套 NiceGUI 頁面，但只操作虛構資料。
- 首席導學風紀按 **管理員登入**，經 Cloudflare Access 驗證後進入正式工作台。
- 收到完整 `/view#…` 連結的人只可查看該已發布週表。
- localhost 及 WARP 是維護後備，不是派發給一般使用者的第二個網站。

## 2. 技術路線

```text
瀏覽器
  │
  ▼
Cloudflare Worker
  ├─ PUBLIC：品牌入口
  ├─ GUEST：簽發 Guest session
  ├─ ADMIN：Cloudflare Access → 管理 session
  └─ /view#…：加密唯讀 Viewer
  │
  ▼
Workers VPC + 具名 Tunnel
  │
  ▼
127.0.0.1:8080 NiceGUI origin
```

Worker 是唯一外部前門。Windows 不開放 NiceGUI 公網連接埠，不設定路由器 port forwarding。

**不要在家中路由器開放 3389、8080**，也不要把 RDP 或 NiceGUI
直接暴露到互聯網。驗收必須明確覆蓋三種結果：**未登入／獲准／未獲准**；
只有獲准身份可取得相應的 Guest 或 Admin 能力。

`/support` 亦遵守同一身份邊界：Worker 必須先解析並驗證 principal；沒有
principal 的 Public／Viewer `GET` 只取得 `Cache-Control: no-store` 的靜態瀏覽器
表單；只有同源、限量的 `POST /api/support/incidents` 會得到 60 秒、support-only 的簽署 principal 到達 origin。有效 Admin／Guest 請求才可連同完整簽署 principal 代理到
NiceGUI 支援工作台。部署後必須分別核對這兩條路徑，不能只測未登入頁面。

## 3. v1.2 必需設定

### Windows origin

受保護 `.env` 至少要由部署程序提供：

```dotenv
SING_YIN_DEPLOYMENT_MODE=server
SING_YIN_HOST=127.0.0.1
SING_YIN_PORT=8080
SING_YIN_SQLITE_BUSY_TIMEOUT_MS=10000
SING_YIN_UNIFIED_GUEST=1
SING_YIN_REQUIRE_GATEWAY_PRINCIPAL=1
ORIGIN_PRINCIPAL_SECRET=<managed-secret>
ORIGIN_PRINCIPAL_KID=<active-key-id>
AUTH_EPOCH=<positive-integer>
SING_YIN_GUEST_SNAPSHOT_SECRET=<managed-secret>
```

`<managed-secret>` is documentation syntax only. Candidate startup and Worker validation reject documented placeholders and repeated single-character values; generate independent random values through the existing secret setup procedure. `SING_YIN_HOST` must remain `127.0.0.1`; `::1` and `[::1]` are rejected because the installed trusted-host path cannot accept the bracketed IPv6 Host contract.

如程式實際使用的環境變數名稱有變，應以 `.env.example`、Worker 設定及 release verifier 為準，不可照抄舊主機的 secret 值。值只可由受控 secret store／主機設定寫入，不可貼到命令列歷史、文件或 Git。Worker `wrangler.jsonc` 的 `ORIGIN_PORT` 必須與受保護主機 `.env` 的 `SING_YIN_PORT` 完全相同；Windows 受控部署會在停機前核對兩者並拒絕不一致的候選。

### Cloudflare Worker

Worker 必須有：

- 管理員 Access JWT 驗證所需 audience／team domain／exact allowlist；
- 管理 session HMAC secret；
- Guest session HMAC secret；
- origin principal HMAC secret、`kid` 及 `auth_epoch`；
- `ROSTER_ORIGIN` VPC binding；
- Viewer KV binding；
- 既有受保護分享管理 bearer secret。

瀏覽器傳入的 `Cf-Access-*`、身份、管理員／Guest cookie 及偽造 principal 標頭，必須在 VPC proxy 前移除；origin 只相信 Worker 重新簽發的 principal。

### Cloudflare Access

- Access application 只保護精確的 `/auth/login`，不可保護 `/auth/*` 或整個 root。
- `/auth/admin/start`、Guest start、status 及 logout 由 Worker 公開接收；只有管理員 callback 進入 Access。
- 管理員使用 exact-email allow policy 及 One-time PIN。
- Allowlist 必須在 Access policy 與 Worker 驗證設定一致。
- 不把管理員加入 Cloudflare Dashboard 成員作為登入前提。
- 不建立應用內共用密碼。

**控制台與歷史乾淨證據：** `Sing Yin Roster Administrator` 的唯一 destination 已核對為 canonical hostname 的精確 `/auth/login`，並使用既定 allow policy／One-time PIN。乾淨 rc30 origin＋Worker `11763f08…` 組合曾通過 canonical root、gateway health、真實 Guest session／logout、Admin Access handoff、Viewer、desktop／320px theme control 及 Guest Engineering 核對；目前線上 origin、gateway 及 migration 後的受控復原限制以本頁頂部生成狀態為準。

## 4. 來源驗證

在 `D:\code_v3`：

```powershell
python -X utf8 -m pytest -q
python -X utf8 scripts\verify_release_candidate.py
```

正式 report 必須與準備部署的 commit／來源 fingerprint 一致，並包含：

- Worker Deno contracts 及 type check；
- Admin／Guest 路由 parity；
- Guest 能力、依賴、snapshot、分頁及下載隔離；
- 管理員並行、版本衝突、命令冪等及公平帳本；
- 備份義務崩潰注入及重啟修復；
- 已驗證備份及隔離還原；
- 繁中／英文、淺／深色、手機、鍵盤、焦點、對比、reduced motion；
- PDF、console、DOM／監聽器／heap 證據。

只有 `pytest` 綠燈不足以批准部署。

rc26 的正式 report 已固定為 `v1.2.0-rc.26`／`248955cb3300bfbe092b05036632991524d824cd`／`5da902307e2d717a75c93e100ba9860eb7e6dd9c35dc42d4a1477bd3304de5e7`，14／14 gate 全部通過。相配的 deployment report 亦已記錄正式備份、隔離還原、migration 及 origin health／readiness；日後候選不可沿用這份 source-matched 證據。

來源候選的 `tests/test_guest_snapshot_bridge.py` 已聚焦通過：它驗證同分頁最新 revision 還原、連線 nonce、token 輪換、複製／篡改拒絕、登出清理及只使用 `sessionStorage`。這項結果只關閉 snapshot 橋接的實作缺口，不取代本節列出的完整 release report、正式備份／隔離還原或 Cloudflare 線上驗收。

## 5. 部署前備份

1. 確認目前正式 origin 的 `/readyz` 為 200。
2. 在應用內建立新的已驗證快照。
3. 核對 manifest、SHA-256、SQLite integrity、schema 及公平帳本。
4. 建立交接備份包。
5. 在另一個臨時 SQLite 路徑完成受控還原。
6. 保存目前主機 bundle／tag、Worker version ID 及回退程序；不要保存 secret 值。

任一步失敗即停止，不進入 maintenance。

## 6. Windows origin 更新

rc26 已由提升權限的 PowerShell 執行既有受控主機部署腳本；以下命令只記錄該次完成的 exact rollout，不可改名後直接重跑：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File C:\Users\lichu\.codex\worktrees\rc26-deploy\scripts\deploy_windows_release.ps1 `
  -SourceRoot C:\Users\lichu\.codex\worktrees\rc26-candidate `
  -HostRoot C:\SingYinRoster `
  -ReleaseRef v1.2.0-rc.26 `
  -TaskName "Sing Yin Roster Host" `
  -RuntimeUser SingYinRosterSvc
```

受控次序如下：

1. 進入 maintenance，拒絕新寫入。
2. 停止 `Sing Yin Roster Host` 工作。
3. 核對沒有第二個 NiceGUI origin 佔用同一資料庫。
4. 安裝已驗證 bundle 及 hash-locked dependencies。
5. 執行 additive Alembic migration `0011_assist_assignment_mode`。
6. 保持正式環境的受保護設定 `SING_YIN_UNIFIED_GUEST=1`，不得用切換旗標略過候選驗證。
7. 核對：

```powershell
Invoke-RestMethod http://127.0.0.1:8080/healthz
Invoke-RestMethod http://127.0.0.1:8080/readyz
```

`/healthz` 只證明可讀；`/readyz` 必須顯示 `writeReady=true`、沒有 maintenance／recovery、沒有 pending backup obligation，才可繼續。

**歷史事故記錄 — 2026-07-17 rc4：** rc4 rollout 的 additive migration `0007` → `0008`、已驗證正式備份及隔離還原均成功；失敗發生在其後的 ancestry gate。`git fetch origin main` 只刷新 `FETCH_HEAD`，但 gate 讀取 stale `origin/main`，因而把有效 commit 誤判為未包含於 `main`。rc4 從未被宣告 live；其部署腳本其後改用明確 refspec `+refs/heads/main:refs/remotes/origin/main` 刷新 remote-tracking branch。這是已解決的歷史教訓，不是目前主機狀態或未來標籤指令。

**歷史事故記錄 — 2026-07-17 rc5 staged readiness：** rc5 再次建立全新 checksum-verified backup 並通過 isolated restore；停止原因不是資料或 origin health 失敗，而是 generic strict-warning gate 在 matching Worker 尚未部署時，把 `cloudflare_access` 的預期 pending 狀態當成 fatal。rc6 修正 staged 次序，rc7 完成後續切換。這是歷史 provenance；未來候選仍須讓每個 failure、未獲明確批准的 warning 及最終線上檢查 fail closed。

## 7. Worker staged rollout

**rc20 例外決策：**候選的 Worker source／設定沒有改動，故本次跳過本節，不建立新 Worker version；canonical traffic 繼續由已驗證 `f780feb2-671a-4feb-b6f6-b7f9d5b31e89` 承接。以下步驟只適用於日後 Worker source 或受保護設定實際改變的候選。

1. 以固定、版本庫內的 Wrangler／lockfile 安裝依賴。
2. 執行 Worker tests、type check 及 dry run，並再次確認 `wrangler.jsonc` 的 `ORIGIN_PORT` 等於主機 `SING_YIN_PORT`；兩端必須來自同一不可變候選。
3. 核對 `wrangler.jsonc` 的 `secrets.required` 所有名稱存在；不要顯示值。管理員 exact-email 名單屬 `ADMIN_IDENTITY_ALLOWLIST` secret，內容是受限 JSON 物件，不再放在公開 `vars`。Access policy、Worker secret 與 WARP maintenance policy 必須由操作者私下核對為同一組身份。
4. 從已推送、屬於 `origin/main`、HEAD 與標籤完全一致的乾淨 annotated tag 執行：

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass `
     -File scripts\deploy_cloudflare_worker.ps1 `
     -SourceRoot "<乾淨發布工作樹>" `
     -ReleaseRef "<next-approved-annotated-tag>"
   ```

   由公開 `vars` 首次遷移 allowlist 時，先在 Windows `%TEMP%` 建立只用一次的 `sing-yin-worker-secrets-<random>.json`，只包含 `ADMIN_IDENTITY_ALLOWLIST` 及 secret 字串；再加上 `-SecretOverlayPath "<absolute-temp-path>"`。腳本會把它與新程式放進同一個未分流 version，先以 0% traffic 驗證，再覆寫及刪除臨時檔。不要先用普通 `wrangler secret put` 改動 live binding，否則尚在運行、仍預期物件格式的舊 Worker 會拒絕管理員登入。

   腳本只使用鎖定的 Wrangler 4.116.0：先保存目前 100% version ID，再上傳新 version，以「舊版 100%／新版 0%」建立 deployment；指定版本標頭的 smoke checks 通過後，才把新版提升至 100%。任何遠端切換開始後的失敗都會精確 rollback 到原 version ID，結果寫入 `logs/cloudflare-worker-deployment-<tag>.json`，不記錄 cookie、token 或 secret 值。
5. 在新版仍為 0% 時核對：
   - `/` 公開入口；
   - `/auth/admin/start` 正確進入 Access；
   - `POST /auth/guest/start` 建立 Guest session；
   - `/auth/status` 正確回報 public／guest／admin；
   - `/guest`、`/try` 兼容重定向；
   - `/support` Public／Viewer 有界文字提交及 `INC-…`／`FB-…` 回復，以及 Guest origin 頁的非持久化限制；
   - `/view#…` Viewer；
   - VPC WebSocket 及 origin `/healthz`。
6. 只有上述核對及 deployment traffic 查詢全部相符，才提高流量；完成後再用不帶版本標頭的正式網址核對一次。

## 8. 核對候選的統一 Guest

只有候選 origin 及需要變更的 staged Worker 全部通過後：

1. 短暫進入 maintenance。
2. 保持 origin 的受保護 `SING_YIN_UNIFIED_GUEST=1` 設定，不重新建立或顯示 secret。
3. 重新啟動 owned scheduled task。
4. 核對 `/healthz`、`/readyz`。
5. 用 InPrivate／虛構資料完成 Guest 流程。
6. 用獲准身份完成 Admin 登入／登出及隔離寫入流程。
7. 才結束 maintenance。

候選的隔離測試仍須證明 flag 為 `0` 時 Guest fail closed；乾淨 rc30 的歷史正式 gate 已在臨時環境完成該證據，不可因此弱化正式環境的受保護設定。

## 9. 線上驗收

### Public

- [ ] root 不強制登入。
- [ ] 品牌、經文、Admin／Guest 入口在桌面及手機可用。
- [ ] 修改 query、header、storage 或 JavaScript 不能升級身份。

### Guest

- [ ] 顯示與 Admin 相同的正式路由、導航及主要元件。
- [ ] 只見虛構中文姓名及 `DEMO` 狀態。
- [ ] 可完成請假、生成、手動修改、示範發布、PDF／JSON、請假調整及公平說明。
- [ ] AI、上載、匯入、外部音樂、正式分享、備份／還原及永久設定均被服務層拒絕。
- [ ] 兩分頁互不覆寫；登出、到期、撤權及重啟清除狀態。
- [ ] 同一分頁重新整理只還原最新合法 token；複製分頁取得新 workspace，篡改／錯誤綁定／舊 boot token 安全回到虛構 fixture。
- [ ] 下載為一次性、`no-store`、不超過限制。

### Admin

- [ ] exact-email One-time PIN 登入。
- [ ] 登出同時清除應用及 Access session。
- [ ] 長時間 WebSocket 重連及 session 到期。
- [ ] 匯入、生成、手動修改、發布、雙語 PDF、請假調整、公平、備份。
- [ ] 兩管理員／多分頁衝突不會靜默覆寫。

### Viewer

- [ ] 只有 published 版本可建立。
- [ ] 草稿、Guest 結果及真實資料庫不能分享。
- [ ] 到期、撤銷及修正版重發。

### Support

- [ ] Public／Viewer `/support` 只向 exact same-origin support API 發出一個有界 POST；成功為 `INC-…`，失敗保留內容並產生 `FB-…`，且不使用持久 browser storage。
- [ ] Guest `/support` 不能呼叫 Admin 收件匣服務或保存附件。
- [ ] Admin 必須明確同意才建立主機本機 incident；結果不進入排班交易或備份。
- [ ] Worker、origin、README、操作手冊及威脅模型使用同一資料邊界。

## 10. 回退

任一 live origin、gateway 或線上 gate 失敗：

1. 恢復 maintenance；
2. 以受控部署報告確認自動 rollback 的 `attempted`／`succeeded`、previous commit 及 previous Worker version；
3. 在現行 origin／Worker 來源已漂移或未歸屬時，先保存及歸屬差異；第一個復原選擇是保留頁首所列 rc52 程式與 Worker，使用其已驗證 schema-`0013` 備份執行受控還原；不得直接回退至 rc30，也不得單側回退而形成未驗證組合；
4. 只有來源指紋、身份參數、路由契約及相容性 gate 已證明另一側仍與目標版本相容時，事故負責人才可批准單側 origin 或 Worker 回退；報告必須記錄所用證據及配對版本；
5. 核對 host commit、`/healthz`、`/readyz`／`writeReady=true`、Admin、Guest、Viewer、WebSocket、登出及資料狀態；
6. 只有頁首生成狀態所列的現行版本無法安全原地恢復，且事故負責人明確批准更深復原時，才考慮歷史 bundle；每個舊程式都必須先配對相容資料庫快照並通過隔離驗證，歷史 rc30／rc27／rc26／rc24 不可作 code-only rollback；
7. 如資料完整性受疑，使用受控 restore，而非手動覆寫 SQLite。

additive migration 不代表舊 bundle 必然可讀新 schema。部署前 gate 必須證明候選升級及回復契約；事故回復必須先還原與目標 bundle 相容的資料庫，再啟動該 bundle。

## 11. 故障排查

| 症狀 | 下一步 |
|---|---|
| root 強制要求登入 | 檢查 Access 是否錯誤保護整個 hostname |
| Guest 進入後 503 | 檢查 feature flag、origin principal secret／kid／epoch 及 `/readyz` |
| Admin 登入後返回 public | 檢查 Access JWT、allowlist、管理 session cookie 及 auth epoch |
| WebSocket 反覆斷線 | 核對 Worker 是否直接回傳 VPC response、Tunnel 及 session 到期 |
| `/healthz` 200、不能寫 | 立即看 `/readyz` 的 maintenance、recovery、backup obligation |
| Guest 看見正式資料 | 立即關閉 `SING_YIN_UNIFIED_GUEST`、進入 maintenance、保存支援編號並調查 adapter 邊界 |
| Viewer 舊版本仍存在 | 撤銷舊連結，等待 KV 傳播，再發修正版 |

不要把姓名、請假原因、週表、PDF、資料庫、備份、cookie、token 或完整日誌貼到公開渠道。

## 12. 交接下一任

- 交接 canonical URL，不交接 localhost 作日常入口。
- 在 Access／Worker allowlist 加入下一任後，先用虛構資料驗收，再移除前任。
- 輪換管理及 principal secrets；只保存日期、version ID、結果及非秘密指紋。
- 建立最新已驗證備份並完成隔離還原。
- 讓下一任親自完成 Admin 登入、Guest 體驗、Viewer、PDF、登出及故障後備。

## English operational summary

The exact active origin, Worker, migration and acceptance identity is generated at the top of this guide from the canonical current-status source. Older source pairs remain historical evidence only; restoring an older application requires the controlled compatible database-restore procedure recorded there.

The generated status block at the top records the exact source-matched gate set, controlled origin switch, verified backup and isolated restore, canonical health／entrance／Guest／support checks, Worker disposition and Cloudflare Access fail-closed verification. Historical release evidence does not describe current production. Supervised human acceptance remains open.
