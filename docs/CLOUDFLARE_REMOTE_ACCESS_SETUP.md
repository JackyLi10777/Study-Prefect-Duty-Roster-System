# Cloudflare 單一網址遠端存取手冊（Windows 專用主機）

> **v1.2 發布狀態：** 2026-07-17 可重現的凍結來源已以指紋 `c8a9b8c5c06480e32b127d8e565f007dc37a6d291fe3fb6ca0ad1dce36ce9aca`（238 個發布輸入）通過 13／13 正式 gate；匹配報告於 `2026-07-17T00:09:33.953144Z` 完成。Cloudflare Access 已以控制台截圖確認只保護精確的 `/auth/login`。發布參照將是 `v1.2.0-rc.4`；rc.1／rc.2／rc.3 均在任何主機變更前由可重現性、瀏覽器驗證或 Windows PowerShell 指紋 gate 停止，從未部署。現依次執行新備份、隔離還原、origin、Worker secrets 及線上抽查；`C:\SingYinRoster` 及 live Worker 在切換前保留 v1.1 回退基線。

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

## 3. v1.2 必需設定

### Windows origin

受保護 `.env` 至少要由部署程序提供：

```dotenv
SING_YIN_DEPLOYMENT_MODE=server
SING_YIN_HOST=127.0.0.1
SING_YIN_PORT=8080
SING_YIN_UNIFIED_GUEST=0
SING_YIN_REQUIRE_GATEWAY_PRINCIPAL=1
ORIGIN_PRINCIPAL_SECRET=<managed-secret>
ORIGIN_PRINCIPAL_KID=<active-key-id>
AUTH_EPOCH=<positive-integer>
SING_YIN_GUEST_SNAPSHOT_SECRET=<managed-secret>
```

如程式實際使用的環境變數名稱有變，應以 `.env.example`、Worker 設定及 release verifier 為準，不可照抄舊主機的 secret 值。值只可由受控 secret store／主機設定寫入，不可貼到命令列歷史、文件或 Git。

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

**目前控制台證據（2026-07-17）：** `Sing Yin Roster Administrator` 的唯一 destination 已核對為 canonical hostname 的精確 `/auth/login`，並使用既定 allow policy／One-time PIN。這只完成 Access 路徑設定；在 Windows origin 及 Worker 仍為 v1.1 時，不可把它寫成 v1.2 已部署。

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

由既有受控主機部署腳本完成：

1. 進入 maintenance，拒絕新寫入。
2. 停止 `Sing Yin Roster Host` 工作。
3. 核對沒有第二個 NiceGUI origin 佔用同一資料庫。
4. 安裝已驗證 bundle 及 hash-locked dependencies。
5. 執行 additive Alembic migration。
6. 保持 `SING_YIN_UNIFIED_GUEST=0` 啟動。
7. 核對：

```powershell
Invoke-RestMethod http://127.0.0.1:8080/healthz
Invoke-RestMethod http://127.0.0.1:8080/readyz
```

`/healthz` 只證明可讀；`/readyz` 必須顯示 `writeReady=true`、沒有 maintenance／recovery、沒有 pending backup obligation，才可繼續。

## 7. Worker staged rollout

1. 以固定、版本庫內的 Wrangler／lockfile 安裝依賴。
2. 執行 Worker tests、type check 及 dry run。
3. 核對所有必需 secret **名稱**存在；不要顯示值。
4. 建立新 Worker version，但先不要全量。
5. 在測試流量核對：
   - `/` 公開入口；
   - `/auth/admin/start` 正確進入 Access；
   - `POST /auth/guest/start` 建立 Guest session；
   - `/auth/status` 正確回報 public／guest／admin；
   - `/guest`、`/try` 兼容重定向；
   - `/view#…` Viewer；
   - VPC WebSocket 及 origin `/healthz`。
6. 保存新舊 version ID，才提高流量。

## 8. 啟用統一 Guest

只有 staged Worker 及 origin 全部通過後：

1. 短暫進入 maintenance。
2. 把 origin `SING_YIN_UNIFIED_GUEST` 改為 `1`。
3. 重新啟動 owned scheduled task。
4. 核對 `/healthz`、`/readyz`。
5. 用 InPrivate／虛構資料完成 Guest 流程。
6. 用獲准身份完成 Admin 登入／登出及隔離寫入流程。
7. 才結束 maintenance。

若 Guest principal 到達但 flag 仍為 `0`，origin 會拒絕它。這是預期的 fail-closed 行為，不應用臨時繞過修正。

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

## 10. 回退

任一線上 gate 失敗：

1. 恢復 maintenance；
2. 把 `SING_YIN_UNIFIED_GUEST` 恢復為 `0`；
3. 回退上一個 Worker version；
4. 回復上一個主機 bundle；
5. 核對 `/healthz`、`/readyz`、Admin、Viewer；
6. 如資料完整性受疑，使用受控 restore，而非手動覆寫 SQLite。

additive migration 必須讓舊 bundle 可讀原有資料。若不能證明，部署前 gate 應已拒絕該 migration。

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

The v1.2 rollout keeps one Cloudflare Worker in front of one loopback-only Windows NiceGUI origin. The Worker owns public entry, Cloudflare Access handoff, guest session creation, signed origin principals, VPC proxying, and the encrypted Viewer. The origin resolves the same NiceGUI routes to either the official workflow or a bounded guest adapter.

Do not enable `SING_YIN_UNIFIED_GUEST` until the complete release report matches the deployed source, a verified backup passes isolated restore, `/healthz` and `/readyz` are healthy, the staged Worker passes Admin/Guest/Viewer checks, and supervised browser acceptance succeeds. Roll back both the host bundle and Worker version if any gate fails.
