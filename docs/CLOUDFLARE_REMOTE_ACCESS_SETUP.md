# Cloudflare 免費無網域遠端存取手冊（Windows 專用主機）

**用途：** 讓所有人只需記住一個網站；訪客不登入只可查看，首席導學風紀在同站登入後才可編輯。

**唯一正式網址：** <https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/>

**資料來源：** Windows 11 專用主機上的 NiceGUI + SQLite；NiceGUI 只監聽 `127.0.0.1:8080`。

> **目前狀態（2026-07-16）：** rc.16 Worker、`/guest`、`/try`、唯讀 Viewer、Access 轉向及 VPC 健康已在正式網址通過自動化核對。`C:\SingYinRoster` 已成為唯一 official origin，開機排程在專用非管理員帳戶下運行，Tunnel 服務為 Running／Automatic；Worker 管理權杖亦已同步輪換，新值通過、舊值被拒絕。尚未完成的是一次有人在場的 Windows 重新開機證明、正式資料受控清理，以及管理員登入／登出、長時間重連、上載與 PDF 的真人驗收。

本方案不需購買網域，也不會把 NiceGUI 或 SQLite 直接公開到互聯網。Cloudflare Worker 是唯一前門；Cloudflare Access 管理登入，Workers VPC 與既有具名 Tunnel 把已驗證管理員請求送回 Windows 主機。localhost 及私人 WARP 地址只作維護後備。

每次後續修改 `/guest`／`/try` 資產，都必須先依 `docs/PUBLIC_ROSTER_VIEWER.md` 的「發布前及部署後怎樣驗證試用邊界」在本機 Wrangler 通過；部署後再以 canonical 網址重跑同一瀏覽器驗證。只有本機證據、只見 HTTP 200，或只在桌面查看，都不能證明更新後的 `/try` 仍保持零伺服器寫入邊界。

---

## 1. 日常使用者只需理解這一段

### 訪客／只需查看

1. 開啟唯一正式網址，或首席導學風紀發出的同 host `/view#…` 完整週表連結。
2. 不需安裝 WARP、不需帳戶、不需輸入密碼。
3. `/guest` 可閱讀不含值班資料的產品導覽；`/try` 可用固定虛構中文姓名完成 30 分鐘裝置內試用及雙語 PDF。這些頁面不能生成或修改正式資料、發布、進入公平、備份、還原及設定。

### 管理員／首席導學風紀

1. 開啟同一正式網址。
2. 按 **「管理員登入 / Admin login」**。
3. Cloudflare Access 會接管驗證；輸入 policy 精確列明的管理員電郵，再輸入 Cloudflare 寄出的 One-time PIN。
4. 成功後回到原網站；Worker 驗證 Access JWT 並建立獨立、已簽署的第一方管理員 session，完整 NiceGUI 工作台才會解鎖。
5. 管理員 session 最長 **8 小時**，而且不會長過 Access JWT。完成工作後按 **「登出 / Log out」**；共用裝置不可只關閉分頁。

目前獲准使用管理工作台的精確電郵是：

- `s10777@syss.edu.hk`
- `lichuangjie0208@gmail.com`
- `lichuangjie0208@outlook.com`

每個地址必須以相同拼寫出現在 Access Allow policy 及 Worker 有限名單；只在其中一邊出現並不足以取得編輯權。三個身份只獲本系統的管理存取權，並不因此成為 Cloudflare Dashboard 成員。

系統沒有自製密碼資料表、密碼 hash、共用 OP 密碼或忘記密碼頁。One-time PIN 由 Cloudflare Access 寄到獲准電郵；`/auth/*` 是按鈕背後的內部登入路徑，不應派發或另作書籤。

---

## 2. 一分鐘理解技術路線

```text
同一 workers.dev 網站
    ├─ 未登入訪客
    │    ├─ /guest 產品導覽（無值班資料）
    │    ├─ /try 30 分鐘瀏覽器試用（虛構資料；裝置內 PDF）
    │    └─ 同 host 加密 /view#… 唯讀週表
    └─ 按「管理員登入」
         └─ Cloudflare Access：exact email + One-time PIN
              └─ Worker 驗證 Access JWT並簽發第一方管理員 session
                   └─ 每次請求重新驗簽 → Workers VPC Service
                        └─ 具名 Cloudflare Tunnel
                             └─ Windows localhost:8080 NiceGUI
```

這是一個網站、兩種權限，不是兩套正常入口。`/guest` 與 `/try` 都是公開層的靜態產品體驗，不是 NiceGUI 訪客帳戶或較低權限管理員。本機及 WARP 留在背後，只在 Cloudflare 故障、主機診斷、還原或搬機時使用。

---

## 3. 目前已建立的非秘密設定

截至 2026-07-16：

| 項目 | 目前值 | 狀態 |
|---|---|---|
| Canonical Worker | `sing-yin-roster-viewer.singyin-study-prefect.workers.dev` | 根路徑未登入回傳 200 |
| Worker production version | `754f36b4-c36d-4d48-82ee-08c98c82831f` | 100%；兩個必需 secret 名稱均存在，值不寫入文件 |
| Cloudflare team domain | `restless-hall-73b2.cloudflareaccess.com` | 已建立 |
| Self-hosted Access app ID | `25072aab-0e60-4787-8ec7-48029e448e8e` | 已建立；只保護管理流程 |
| Access identities | exact email：`s10777@syss.edu.hk`、`lichuangjie0208@gmail.com`、`lichuangjie0208@outlook.com` | Access policy、Worker 名單及 WARP 後備 policy 已同步 |
| Access login method | Cloudflare One-time PIN | 不需要 Cloudflare Dashboard 帳戶；授權邊界仍是 exact-email policy |
| Access session | 8 小時 | 已選定 |
| `/auth/*` 未登入測試 | HTTP 302 至 Access | 已確認 |
| Named Tunnel | `sing-yin-roster-windows-private` | 已建立 |
| Tunnel ID | `ba6b6426-d012-4ecb-bafa-cbdbf2659731` | 非秘密識別值 |
| VPC Service | `sing-yin-roster-nicegui` | target `localhost:8080` |
| VPC Service ID | `019f5b30-d07c-7a63-a273-6b2ccb7318f8` | 非秘密識別值 |
| Worker VPC binding | `ROSTER_ORIGIN` | remote VPC Service |
| Viewer KV | `ROSTER_SHARES` | 只存密文、nonce 及最少 metadata |
| Official origin | `C:\SingYinRoster`，`v1.1.0-rc.16` | 唯一正式 Python origin；`D:\code_v3` 只作開發及驗證 |
| Windows task | `Sing Yin Roster Host`／`SingYinRosterSvc` | Running；專用非管理員帳戶、stored-password logon |
| Tunnel service | `cloudflared` | Running／Automatic |
| NiceGUI origin | `127.0.0.1:8080` | `server` mode，但只限 loopback，不監聽 LAN／公網 |

Access audience、JWT、cookie、Tunnel token、Worker admin token、API token 及其他 secret 不列在本表，也不可寫入 Git、文件、截圖、電郵、PDF、備份或日誌。

正式及範本 Wrangler 設定宣告 `ADMIN_BEARER_TOKEN` 與 `ADMIN_SESSION_SECRET` 都是必需 secret，絕不保存其值；新環境若缺少其中一項，`wrangler deploy`／`wrangler versions upload` 會在部署前停止。

Worker 的部署工具亦是版本控制的一部分：`cloudflare/roster_viewer/package.json` 固定 Wrangler `4.110.0`，`pnpm-lock.yaml` 固定其完整依賴，`pnpm-workspace.yaml` 只允許 Wrangler 必需的 `esbuild`、`sharp`、`workerd` 執行原生安裝腳本；其他依賴一律不可在安裝時執行程式。Wrangler 4.110.0 的依賴要求 Node.js 22 或以上；維護者安裝 Node.js 22+ 及 pnpm 11.7.0 後，再執行：

```powershell
Set-Location D:\code_v3\cloudflare\roster_viewer
pnpm install --frozen-lockfile
pnpm run gateway:test
pnpm run gateway:check
pnpm run deploy:dry-run
pnpm exec wrangler whoami
```

只有以上檢查通過、工作樹乾淨、兩個 secret 名稱均能由 `pnpm exec wrangler secret list` 讀回，而且已記錄目前 Worker version ID，才可執行 `pnpm run deploy`。不要使用未固定版本的全域 Wrangler；回退必須指定已記錄的 version ID，且不會回復 KV 內容。

### 管理 API bearer 權杖輪換

`ADMIN_BEARER_TOKEN` 是 Worker 與受保護 NiceGUI origin 之間的內部 API 憑證，**不是**首席導學風紀登入密碼，也不取代 Cloudflare One-time PIN。平日不需查看或輸入它。

只有懷疑洩漏、交接或安全維護時，才由維護者以經審閱的受控程序在同一個互斥維護窗口更新 Worker secret 與主機 `SING_YIN_PUBLIC_ROSTER_VIEWER_ADMIN_TOKEN`。程序必須使用標準輸入及原子檔案替換，不在參數、輸出或 recovery 檔名留下值；重新啟動專用工作後，核對 owner、loopback health、Tunnel 及 Worker，再證明新值回傳 HTTP 200、舊值回傳 HTTP 401。任何一步失敗必須回復兩端，不能容許 token drift。交接紀錄只保存日期、Worker version、通過／失敗與不可逆短指紋，不保存 token。

2026-07-16 已完成一次正式輪換：Worker version `754f36b4-c36d-4d48-82ee-08c98c82831f` 為 100%，新值通過、舊值被拒絕，C-host 仍由 `SingYinRosterSvc` 運行，臨時 recovery copy 已移除。

Worker observability 只保存登入橋接及 invocation 的受控技術事件。登入失敗會回傳 `GW-...` 支援編號，並只記錄階段、穩定原因代碼、截短的 Cloudflare Ray ID，以及 assertion／authorization cookie 是否存在；不記錄電郵、JWT、cookie、session secret、值班表或請假資料。排查時以 `GW-...` 對應 Cloudflare Logs，不要把完整日誌貼到公開渠道。

---

## 4. Cloudflare Dashboard：核對 Access，而不是另建密碼

只有在搬機、交接或設定被改動時才核對；不要因為看見本手冊便重建一個同名應用。

1. 登入 Cloudflare Dashboard，進入 **Zero Trust → Access → Applications**。
2. 開啟現有 self-hosted 應用，核對 App ID 與上表相符。
3. 核對應用的 destinations 只有 `/auth` 及 `/auth/*`，**不可保護整個 Worker root**；否則訪客一開主網址也會被迫登入。
4. 核對 Allow policy 只列出本手冊第 3 節的三個精確管理員電郵，而不是 `Everyone`、任何 email domain 或公開一次性 PIN。
5. 在 **Zero Trust → Settings → Authentication → Login methods** 核對本應用只選用 **Sing Yin email verification / One-time PIN**；管理員入口不可再跳到 `dash.cloudflare.com/oauth2` 或顯示 `Unknown app`。
6. 三個地址只需收取各自電郵的單次驗證碼，不需加入本專案的 Cloudflare Dashboard 成員名單，也不會取得 DNS、Worker、Access 或帳單管理權。
7. 核對 session duration 是 **8 hours**。
8. 核對 cookie／導向設定：HTTP-only、停用 path-only cookie、auto redirect to identity；不要把應用放進公開 launcher。Worker 在 `/auth/login` 後改用自己的已簽署 HttpOnly session，並對所有寫入及 WebSocket 另作同源檢查。
9. 以未登入 InPrivate 視窗測試：主網址應回到訪客頁；按「管理員登入」才出現 One-time PIN 電郵表單；不可出現 Dashboard OAuth 或 `Unknown app`。
10. 交接時先在 Access、Worker 及 WARP 後備 policy 加入下一任 exact email，以虛構資料完成驗收，再移除前任 exact email；不要交換前任帳戶密碼。

`scripts/verify_cloudflare_access.ps1` 會自動核對本機健康、公開訪客 HTTP 200、登入路徑的正確 team-domain redirect、One-time PIN 電郵表單，以及 Dashboard OAuth／`Unknown app` 不存在；任何一項不符便 fail closed。它不會輸入電郵、讀取驗證碼或建立管理員 session，所以最後一次真人登入仍由獲准管理員完成。

若管理員收不到單次驗證碼，先核對輸入的 exact email、垃圾郵件匣及 Access policy；不要在 `.env`、SQLite 或網頁加入臨時共用密碼。

---

## 5. Worker：JWT 防禦性驗證

Access path policy 是第一道閘門，但正式 Worker 仍不可只相信「請求來自 Cloudflare」。在 `/auth/login` 必須：

1. 讀取 `Cf-Access-Jwt-Assertion`。
2. 從 `https://restless-hall-73b2.cloudflareaccess.com/cdn-cgi/access/certs` 取得 JWK 並驗證簽章。
3. 核對 `aud`、`iss`、`exp` 及 exact-email 管理員身份。
4. 拒絕缺少、過期、錯誤 audience／issuer 或電郵不符的 token。
5. 不相信瀏覽器自報的角色、電郵或自訂身份標頭。
6. 驗證後使用獨立 `ADMIN_SESSION_SECRET` 建立 HMAC-SHA256 `__Host-SingYinAdminSession`；它是 HttpOnly、Secure、SameSite=Lax、Path=/、沒有 Domain，最長 8 小時且不超過 Access JWT `exp`。
7. 其後每個 HTTP／WebSocket 請求重新核對 session 簽章、期限與目前 exact-email allowlist；不得依靠前端 local storage 或自報角色。
8. 送往 VPC 前移除外來 Access JWT、`CF_Authorization`、第一方管理員 cookie 及身份標頭，只注入由已驗證 session 產生的內部身份。

Access audience 值、JWT 本文、cookie 及驗證 secret 只放受控 Cloudflare 設定；不要把它們貼進測試輸出或本文件。JWT 驗證是 defense in depth，不能取代 Access policy，也不能由前端 JavaScript完成。

---

## 6. Worker：VPC binding 與 WebSocket

正式 Worker 的 VPC binding 應保持：

```json
{
  "vpc_services": [
    {
      "binding": "ROSTER_ORIGIN",
      "service_id": "019f5b30-d07c-7a63-a273-6b2ccb7318f8",
      "remote": true
    }
  ]
}
```

VPC Service `sing-yin-roster-nicegui` 的 target 是 `localhost:8080`，並由 Tunnel `sing-yin-roster-windows-private` 抵達 Windows 主機。NiceGUI 不改為 `0.0.0.0`；**不要在家中路由器開放 3389、8080、80 或 443**，Windows 防火牆亦不需公開這些 origin 連接埠。

NiceGUI 依賴 WebSocket。Worker 代理必須直接回傳：

```javascript
return env.ROSTER_ORIGIN.fetch(request);
```

不要讀出 status／headers／body 再建立另一個 `Response`，否則原始 `response.webSocket` 會遺失，畫面可能只載入外殼但無法互動或重新連線。

---

## 7. 已確認的 VPC 傳輸證據

臨時 `sing-yin-roster-vpc-probe` Worker 曾綁定上述 VPC Service，經具名 Tunnel 連到 Windows `localhost:8080`：

- `/healthz` 回傳 HTTP 200。
- Python WebSocket client 連到 `/_nicegui_ws/socket.io/?EIO=4&transport=websocket`，收到 Engine.IO open packet。
- 這證明 VPC HTTP Upgrade 及 NiceGUI WebSocket 路徑在 live environment 可通過。
- probe Worker script 及 workers.dev 子網域已刪除；它不是日常入口，也不可派發。

這只證明 transport。正式 Worker 仍須完成下一節的完整瀏覽器驗收。

---

## 8. 正式瀏覽器驗收（只用虛構資料）

驗收紀錄必須清楚分開 **未登入／獲准／未獲准** 三種身份結果，不能只記錄一次成功登入。

### A. 訪客狀態

- [ ] InPrivate／無 Access cookie 開啟 canonical root，HTTP 200 並顯示訪客唯讀頁，不自動要求登入。
- [ ] 訪客看不到生成、發布、請假調整、公平、備份、還原或設定。
- [ ] 訪客直接輸入 `/prefects`、`/rosters` 或其他 NiceGUI 路徑只會返回訪客首頁，不能取得編輯權。
- [ ] 訪客修改 query、header、local storage 或畫面 JavaScript 不能升級身份。
- [ ] `/guest` 只載入產品導覽；`/try` 只載入固定虛構中文姓名，能完成示範請假、生成、預覽及雙語 A4 橫向 PDF。
- [ ] 瀏覽器 Network／Worker 觀察證明試用互動沒有應用 API、KV、VPC 或 NiceGUI 請求；30 分鐘、關閉分頁及重置均清除 `sessionStorage` 狀態。
- [ ] 試用 PDF 只在使用者下載後留於裝置，清楚標示非正式；不能發布、建立 `/view#…` 或影響 `history_weight`。

### B. 管理員登入及登出

- [ ] 按「管理員登入」才進入 Access；三個已列明 exact-email 身份分別收到並輸入 One-time PIN，返回原 host 後建立已簽署管理員 session。
- [ ] 非 policy 電郵不能登入。
- [ ] 登入後完整 NiceGUI 可載入，繁中／英文及深淺模式正常。
- [ ] 主動「登出」後回到訪客權限；舊管理分頁重新整理亦不能繼續編輯。
- [ ] 8 小時 session 到期後重新驗證，不會無限保持 OP 權限。
- [ ] 缺少、過期、錯誤 audience／issuer 或非管理員 email 的 JWT 被拒絕；被篡改、過期或已移出 allowlist 的第一方 session 同樣被拒絕。

### C. NiceGUI transport 與完整工作流

- [ ] Dashboard 長時間保持連線；網絡短暫中斷後 WebSocket 可重新連接。
- [ ] 以隔離 SQLite 匯入虛構中文姓名、登記請假、生成草稿、手動修改、發布一次。
- [ ] 繁中及英文 PDF 可下載，姓名均保持中文。
- [ ] 上載 CSV／XLSX、下載格式範例及 PDF 均通過 VPC 代理。
- [ ] 已發布後請假調整、公平帳本、審計及備份結果正確。
- [ ] 兩個瀏覽器同時發布仍只入帳一次；資料庫交易是最終保護。

### D. 同 host 唯讀分享

- [ ] 以虛構已發布週表建立完整 `/view#…` 連結。
- [ ] 一般瀏覽器不登入即可查看指定週表，但沒有編輯入口。
- [ ] KV 只保存密文、nonce、週次／建立／到期 metadata；沒有解密 key 或 OP 狀態。
- [ ] 撤銷後約一分鐘舊連結失效；到期連結同樣失效。
- [ ] 請假調整後建立新連結並撤銷舊連結。

任何一項未通過，停止以 canonical site 進行真實寫入，改用本機／WARP 維護後備，先修正再重新驗收。

---

## 9. 日常故障排查

| 現象 | 依次檢查 |
|---|---|
| 主網址完全不能開啟 | Worker deployment、Cloudflare status、主機網絡 |
| 訪客一開 root 就被要求登入 | Access 是否誤設為保護整個 Worker；應只保護管理流程 |
| 輸入 One-time PIN 後顯示「未能確認管理員身分」 | 先在 Access Logs 核對該事件是否 `Allow`；如已允許，以 Worker Logs 的 `admin_login_bridge_failure` 及 `GW-...` 對照 `access_token`、`access_jwt` 或 `admin_session` 階段。若是 `access_jwt / jwks_fetch`，檢查 Worker 的 JWKS 子請求及目前部署版本；不要反覆清除瀏覽器資料或重設電郵政策 |
| 按登入後不斷返回訪客頁 | exact-email policy、Access session、Worker JWT `aud`／`iss`／`exp`／email及第一方管理員 session cookie |
| 登入後只有外殼、按鈕不動 | VPC binding、Tunnel、主機 `/healthz`、原始 WebSocket Response 是否保留 |
| 上載或 PDF 失敗 | VPC request／response streaming、檔案大小、NiceGUI 日誌中的 OP／REQ 編號 |
| 登出後仍可編輯 | Access logout、cookie、session 及舊分頁重載；修正前停止遠端使用 |
| Viewer 連結失效 | 完整 fragment、到期、撤銷；由管理員重建而不要猜 key |

技術支援只提供 OP／REQ 編號，不附姓名、值班表、PDF、資料庫、備份、JWT、cookie 或完整日誌。

---

## 10. 本機及 WARP 維護後備

### localhost

在 Windows 主機：

```powershell
Invoke-RestMethod http://127.0.0.1:8080/healthz | Format-List
```

若正式服務未啟動，維護者才雙擊 `START_SING_YIN_ROSTER.cmd`。啟動器會重用既有程序，8080 被佔用時選用 8081–8099，並顯示實際 URL。

### 私人 WARP

`http://roster.singyin.internal:8080` 只供已登記維護裝置在 canonical Worker／Access／VPC 故障時使用。它不寫進給訪客的教學，不在群組派發，也不是管理員平日書籤。

需要重建主機連接器時，才以管理員 PowerShell 執行既有受控腳本：

```powershell
Set-Location C:\SingYinRoster
powershell -ExecutionPolicy Bypass -File scripts\activate_cloudflare_private_warp.ps1 `
  -TunnelId "ba6b6426-d012-4ecb-bafa-cbdbf2659731" `
  -PrivateHostname "roster.singyin.internal" `
  -TeamDomain "restless-hall-73b2.cloudflareaccess.com"

powershell -ExecutionPolicy Bypass -File scripts\verify_cloudflare_private_warp.ps1
powershell -ExecutionPolicy Bypass -File scripts\doctor_windows_remote_access.ps1
```

腳本取得 Tunnel token 時，token 只可保存在主機受控 runtime 位置。WARP device enrollment 的 reusable policy 目前只列出第 3 節相同的三個 exact emails；WARP-off、未獲准帳戶及家庭網絡其他裝置應不能直連 origin。WARP 登記只是維護後備，不會取代 canonical 網站的 Access 登入。

---

## 11. 交接下一任

1. 現任首席導學風紀與教師顧問確認交接日期及下一任正式電郵。
2. 在 Access Allow policy、Worker 有限管理員名單及 WARP 維護後備 policy 同步加入下一任 **exact email**，不要建立共用密碼。
3. 下一任不需獲授 Cloudflare Dashboard membership；讓下一任在普通瀏覽器由 canonical site 按「管理員登入」，以正式 exact email 收取並輸入 One-time PIN。
4. 只用虛構資料完成第 8 節全部驗收。
5. 核對下一任可主動登出，並明白 8 小時 session、Viewer 撤銷及本機/WARP 後備。
6. 驗收通過後移除前任 exact email，撤銷不再需要的 Access session 及 WARP 維護裝置。
7. 更新交接紀錄；不要記錄或傳送任何人的密碼、JWT、cookie、audience、Tunnel token 或管理 token。

---

## 12. 立即停止遠端管理

如身份、Worker 或 VPC 邊界有疑問：

1. 在 Access policy 暫停管理員 Allow 或撤銷相關身份／session。
2. 停止正式 Worker 的管理路徑轉送，但保留必要的訪客公告／唯讀狀態。
3. 如需切斷主機 Tunnel，以管理員 PowerShell 執行：

```powershell
Stop-Service cloudflared
Set-Service cloudflared -StartupType Disabled
```

這不會刪除本機網站或 SQLite。修正後才恢復：

```powershell
Set-Service cloudflared -StartupType Automatic
Start-Service cloudflared
```

在正式重新驗收前，只於主機 localhost 完成必要維護。不要改用 Quick Tunnel、公開 LAN port 或臨時共用密碼。

---

## 13. 官方參考

- [Cloudflare Access applications](https://developers.cloudflare.com/cloudflare-one/applications/)
- [Cloudflare Access JWT validation](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/)
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/)
- [Cloudflare One Client](https://developers.cloudflare.com/cloudflare-one/team-and-resources/devices/cloudflare-one-client/)
- [Cloudflare Workers routes](https://developers.cloudflare.com/workers/configuration/routing/)
- [Cloudflare KV expiration](https://developers.cloudflare.com/kv/api/write-key-value-pairs/)
- [Cloudflare Workers Web Crypto](https://developers.cloudflare.com/workers/runtime-apis/web-crypto/)

本手冊記錄的是正式架構及交接程序；Cloudflare Dashboard 的按鈕名稱若日後改動，以同一安全意圖核對，不可為了方便而移除 exact-email、JWT、VPC 或登出邊界。
