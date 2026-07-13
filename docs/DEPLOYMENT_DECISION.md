# 部署與遠端存取決策指南 / Deployment and remote-access decision guide

## 結論 / Recommendation

**正式方案是一部 Windows 11 專用主機，加上一個不需購買網域的 canonical workers.dev 網站。所有人開啟同一 URL：訪客未登入時只能查看；管理員在同站按「管理員登入」，通過 Cloudflare Access 後才進入完整 NiceGUI 工作台。**

正式網址：<https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/>

NiceGUI、SQLite、PDF、備份及日誌仍在 Windows 主機，origin 只監聽 `127.0.0.1:8080`。Cloudflare Worker 是唯一前門；管理員請求經 Access、Worker JWT 驗證、Workers VPC、既有具名 Tunnel 才抵達 NiceGUI。這不是把資料庫搬進 Worker，也不是公開 Windows 連接埠。

完整 Windows 安裝、工作排程器、健康檢查、更新、備份及搬機步驟見 [Windows 專用主機完整設定手冊](WINDOWS_DEDICATED_HOST_SETUP.md)；Access、VPC、Tunnel、驗收及後備程序見 [Cloudflare 遠端存取完整設定手冊](CLOUDFLARE_REMOTE_ACCESS_SETUP.md)；使用者入口、登入及分享見 [單一網站存取手冊](PUBLIC_ROSTER_VIEWER.md)。目前不採用 Linux、Raspberry Pi、Docker 或真正雲端主機作正式資料來源。

## 一個網址，兩種權限 / One URL, two permission states

| 狀態 | 同一網站顯示 | 權限 |
|---|---|---|
| 未登入訪客 | 唯讀首頁及獲明確分享的 `/view#…` 已發布週表 | 不可生成、修改、發布、調整、公平審核、備份、還原或設定 |
| 已驗證管理員 | 經 VPC 代理的完整 NiceGUI 工作台 | 可依既有政策、交易、確認及審計完成 OP 工作流 |

不另派發「管理員網址」。`/auth/*` 只供同站登入流程；登入後由 Worker 在每個 NiceGUI 請求驗證 hostname-wide Access cookie。VPC Service、Tunnel、localhost 及私人 WARP 地址只給維護者。一般訪客不需 WARP、帳戶或密碼。

## 身份及 session 決定

- Access policy 只接受精確列明的管理員電郵；目前交接身份為 `s10777@syss.edu.hk`。
- 密碼、MFA、帳戶復原及身份生命週期由 Cloudflare Identity Provider／Cloudflare Access 管理。
- 系統不建立密碼資料表、Argon2／bcrypt hash、共用 OP 密碼或忘記密碼頁；SQLite、KV、備份及 Git 均不保存管理員密碼。
- Access session 為 **8 小時**。完成工作必須按「登出」；離任交接以更新 exact-email policy 完成，不交接前任密碼。
- Access 應用只保護管理路徑，不可為整個 Worker 啟用強制登入，否則訪客也會被迫登入。

目前 self-hosted Access app 的非敏感識別碼是 `25072aab-0e60-4787-8ec7-48029e448e8e`。Access audience、JWT、cookie、client secret 及管理 token 是秘密，不寫入公開文件、Git、截圖或日誌。

## Worker 的第二道身份驗證

Cloudflare Access 的路徑政策是第一道閘門；Worker 在轉送 NiceGUI 前仍必須：

1. 從 Cloudflare Access JWK 驗證 `Cf-Access-Jwt-Assertion` 簽章。
2. 核對 `aud`、`iss`、`exp` 及 exact-email 管理員身份。
3. 不相信瀏覽器提供的角色、電郵或自訂身份標頭。
4. 驗證後移除外來 Access JWT、`CF_Authorization` cookie 及身份標頭，只注入由已驗證 claim 產生的內部身份。
5. 缺少、過期、錯誤 audience／issuer 或不符管理員電郵的請求一律拒絕或回到訪客頁。

Cloudflare team JWK endpoint 是 `https://restless-hall-73b2.cloudflareaccess.com/cdn-cgi/access/certs`。這是公開驗簽資料位置，不是登入網址；不要在使用者文件派發 `/auth/*` 或 JWK URL。

## VPC 與 Tunnel 邊界

| 元件 | 已選設定 |
|---|---|
| Named Tunnel | `sing-yin-roster-windows-private` |
| Tunnel ID | `ba6b6426-d012-4ecb-bafa-cbdbf2659731` |
| VPC Service | `sing-yin-roster-nicegui` |
| VPC Service ID | `019f5b30-d07c-7a63-a273-6b2ccb7318f8` |
| VPC target | `localhost:8080` |
| Worker binding | `ROSTER_ORIGIN`（remote VPC Service） |
| NiceGUI listen address | `127.0.0.1:8080` |

Worker 代理必須直接回傳 VPC `fetch()` 的原始 `Response`，不可重建 status／headers／body 後另造一份 Response；否則 `response.webSocket` 會遺失，NiceGUI 的即時連線會失效。

## 已完成的傳輸證據

臨時 `sing-yin-roster-vpc-probe` Worker 曾綁定上述 VPC Service，經 Tunnel 連到 Windows 的 `localhost:8080`：

- `/healthz` 回傳 HTTP 200。
- WebSocket client 連到 `/_nicegui_ws/socket.io/?EIO=4&transport=websocket`，收到 Engine.IO open packet。
- 這證明 VPC HTTP Upgrade 及 NiceGUI WebSocket 路徑在實際環境可通過。
- probe script 及 workers.dev 子網域已刪除；它不是第二個入口，也不應留下書籤。

這項證據只確認 transport。正式發布前仍須以虛構資料完成 Access 登入／登出、8 小時 session／撤銷、長時間重新連線、檔案上載、PDF 下載及完整寫入流程的瀏覽器驗收。

## 同站唯讀分享邊界

1. 只有 `published` 週表可建立 `/view#…` 連結；草稿及完整資料庫不送到 Worker。
2. 分享白名單只有週次／日期、崗位、當值時間、中文姓名及休室／待補顯示狀態。
3. Windows 主機為每條連結產生獨立 AES-256-GCM key 及 nonce；KV 沒有 key，不能獨立解讀密文。
4. key 留在完整 URL fragment，不會隨初始 HTTP request 傳給 Worker；同源 JavaScript 在收件者瀏覽器解密。
5. KV 記錄會到期，也可由管理員撤銷；邊緣同步最多可能約一分鐘。
6. 持有完整連結的人在到期或撤銷前都可查看。誤發時立即撤銷；週表經請假調整後建立新連結並撤銷舊連結。

同一 host 同時提供訪客與管理員模式，但兩者資料權限完全不同；分享連結本身永遠不能把訪客升級為管理員。

## 本機及 WARP 的定位

`http://127.0.0.1:8080` 與 `http://roster.singyin.internal:8080` 保留作：

- Cloudflare／Access／Worker 故障時的健康檢查與緊急維護；
- 主機、Tunnel、VPC 或 WebSocket 診斷；
- 正式入口未通過完整真人驗收前的安全後備；
- 還原或搬機時的受控現場操作。

它們不是正常分享地址，不放入群組、首頁快速入口或一般使用者書籤。WARP device enrollment 仍只列出維護所需的獲准帳戶；WARP-off 及未獲准裝置應不能使用後備地址。

### 維護後備的既有驗收契約

原有「**私有 Cloudflare Tunnel + WARP**」路徑不再是日常入口，但仍是可復原的維護資產。其 **WARP device-enrollment policy**、WARP-on／WARP-off／未獲准裝置拒絕測試及「**主機連接器健康；待真人遠端裝置驗收**」狀態仍須保留至後備驗收完成。這個 **應用內權限** 契約只容許維護帳戶，不得升級訪客或取代 canonical Admin login。Access app destinations 只有 `/auth` 及 `/auth/*`；停用 path-only cookie 後，Worker 會在同一 hostname 的每個 NiceGUI 代理請求驗證身份，沒有管理員前綴或第二網站。

## 為甚麼不用 Quick Tunnel、Pages 或直接公開 origin？

完整系統需要長時間運行的 Python NiceGUI、WebSocket、可寫入 SQLite、備份及日誌。靜態網站平台不能取代這些狀態；Quick Tunnel 是短暫開發工具，也不提供這套固定身份、VPC、驗收及復原邊界。Windows 防火牆不應為 NiceGUI、SQLite、備份或檔案分享開放公網入站連接埠。

## 真正雲端主機是另一個 L3 決定

如日後確有多主機高可用或集中 IT 維護需要，才另行設計：

- 長時間運行的受管 VM／容器，而不是靜態網站主機；
- 加密持久化儲存，以及經測試的 PostgreSQL 遷移或單主機資料策略；
- 保留 `history_weight`、一次性發布、審計、備份及還原語義；
- 身份與角色生命週期、資料保留、事故處理、成本上限及災難復原演練。

目前 Worker + Access + VPC + Tunnel 只是安全地把同一 Windows origin 帶到一個正式網址，Windows 主機仍是唯一 system of record。

## English summary

The selected design uses one canonical `workers.dev` URL. Guests see read-only content; an approved administrator selects **Admin login**, completes Cloudflare Access sign-in and MFA, and returns to the same host with the full NiceGUI editor. The Worker independently verifies the Access JWT before proxying through Workers VPC and the existing named Tunnel to a Windows loopback origin.

Passwords, MFA, and account recovery remain with the Cloudflare identity provider. The application has no custom password database. Same-host `/view#…` links remain encrypted, expiring, and revocable. Localhost and private WARP are maintenance fallbacks only, not additional URLs to distribute. The Windows host remains the system of record; a true cloud-host migration is a separate L3 project.
