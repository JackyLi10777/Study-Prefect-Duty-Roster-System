# 單一網站、訪客查看與管理員登入手冊 / Canonical site access guide

我是李創杰，2026–2027 年度首席導學風紀。我希望下一任只需記住及分享一個網站，不必向不同使用者解釋 localhost、WARP 或多個入口：

**`https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/`**

這個網址提供四種清楚分開、權限不互相提升的狀態：

- **`/` 入口／Entrance：** 未有有效 Access session 時，Worker 原生首頁說明系統用途、訪客導覽、分享連結與管理員登入；它本身不是值班表或 NiceGUI。管理員驗證成功後會返回同一個 `/`，由 Worker 代理 NiceGUI。
- **`/guest` 訪客導覽／Guest tour：** Worker 原生靜態唯讀導覽，只接受 `GET`／`HEAD`。它不連接 VPC、NiceGUI、SQLite 或 KV，也不包含任何值班表資料。
- **`/view#…` 已發布週表／Published roster：** 只有取得完整分享連結的人才可在瀏覽器取得 KV 中的加密快照，並用只留在 `#fragment` 的鑰匙於裝置內解密；它永遠唯讀。
- **管理員工作台／Administrator workbench：** 在同一入口按「管理員登入」，通過 Cloudflare Access 及 Worker JWT 驗證後，請求才會沿 VPC 到達 Windows 主機的 NiceGUI 與 SQLite。

我不會另外派發「管理員網站」。`/auth/*`、VPC Service、私人 WARP 地址及 localhost 都是系統內部或維護路徑，不是給一般使用者記住的第二個網站。

## 一個網域，四種安全狀態

| 狀態／State | 所屬層／Owner | 資料與方法／Data and methods | 權限結果／Permission result |
|---|---|---|---|
| 公開 `/` 入口／Public entrance | Cloudflare Worker | 沒有有效 Access session 時的靜態入口；不讀取值班資料／Static entrance without a valid Access session; no roster read | 只提供安全下一步，不提供編輯／Guidance only; no editing |
| `/guest` 訪客導覽／Guest tour | Cloudflare Worker | 只限 `GET`／`HEAD`；無 VPC、NiceGUI、SQLite、KV／`GET`／`HEAD` only; no VPC, NiceGUI, SQLite or KV | 只看系統流程及保障說明；沒有值班表／Read-only system tour; no roster data |
| `/view#…` 已發布週表／Published roster | Worker + KV + browser Web Crypto | KV 只保存密文及最少 metadata；鑰匙留在 fragment／KV holds ciphertext and minimum metadata; key stays in the fragment | 只看獲分享的週表；不能編輯或升級權限／View the shared roster only; cannot edit or elevate |
| 已驗證管理員／Verified administrator | Access + Worker + VPC + NiceGUI | JWT 逐請求驗證後，才在同一 `/` 代理至 NiceGUI／JWT is verified before NiceGUI is proxied at the same `/` | 完整 OP 工作流，仍受政策、交易、確認及審計限制／Full OP workflow under policy, transaction, confirmation and audit controls |

**English contract:** without a valid Access session, `/` is the public Worker entrance. `/guest` is a Worker-native, data-free tour that accepts only `GET` and `HEAD`. `/view#…` is an encrypted, expiring and revocable published-roster snapshot backed by KV and decrypted in the browser. Only a verified administrator reaches NiceGUI through Access, Worker JWT validation and VPC, after which the same `/` serves the proxied workbench. NiceGUI has no guest account, guest role or guest RBAC.

一般人只需接觸主網址、同站 `/guest` 導覽，或首席導學風紀發出的完整 `/view#…` 週表連結。管理員按頁面的登入按鈕即可；不需要抄寫內部路徑。這些是同一網域下的不同安全狀態，不是不同網站。

## 入口頁怎樣使用

入口頁把「這個系統為何存在」與「我現在可以做甚麼」分開：寬螢幕以約 58/42 的敘事／登入面板排列，窄螢幕則依同一閱讀次序直向排列。訪客可選擇 **以訪客身份瀏覽／Continue as guest** 前往 `/guest`，獲准管理員則使用唯一清楚的 **管理員登入／Admin login** 按鈕。入口不是值班表本身，也不會把訪客誤導到編輯畫面。

- `/guest` 只展示每週流程、可公開說明的公平與可靠性原則，以及哪些操作受保護。它不顯示姓名、崗位、請假、公平帳本、備份、日誌或設定。
- `/guest` 的 HTML、CSS 及 JavaScript 由 Worker 直接提供；路由只接受 `GET` 及 `HEAD`，其他方法回傳 `405 Method Not Allowed`。
- 顯示 `/guest` 不會建立 VPC 連線，不會啟動或查詢 NiceGUI，不會讀寫 SQLite，也不會讀、寫、列出或刪除 KV。

- 外觀可以選擇跟隨系統、淺色或深色；選擇只保存在該瀏覽器，不影響身份或資料。
- **分享網站入口 / Share this site** 只分享 canonical 首頁網址，方便別人認識系統或前往管理員登入；它不會包含任何值班表、查看密鑰或編輯權限。要讓別人看某一週值班表，仍須在發布後另行發出該週的完整 `/view#…` 連結。
- 頁面在 320 px 寬度、鍵盤操作及 Windows 高對比／forced-colours 模式仍保留完整閱讀與焦點次序。
- 入場及按鈕回應都是一次性的短動效；系統要求 reduced motion 時會直接呈現完成狀態，沒有循環、背景漂浮或自動輪播。

入口也設有一段簡短的「今日經文與靈修提醒」，讓我在開始每週工作前先停下來反思。繁體中文固定使用 **和合本修訂版 2010（神版）**，英文固定使用 **New King James Version（NKJV）**。初次顯示會按日期穩定選取本機精選內容；只有我或訪客按「換一節經文 / Show another verse」才會更換，不會自動播放，也不會向外部經文服務傳送請求。精選池逐項與正式 `data/devotional/daily-verses.seed.json` 核對，錯誤譯本標籤、缺漏經文或未完成精確核實會阻擋發布。

以上只是呈現與閱讀改良：訪客唯讀、管理員登入、JWT 驗證、VPC 代理及 `/view#…` 加密快照的安全邊界完全不變。

## 訪客怎樣查看指定週表

`/guest` 是不含資料的系統導覽；它不能代替某一週的分享連結。要查看指定週表，必須依以下流程使用完整 `/view#…` 連結：

1. 我在管理員工作台完成「生成草稿 → 核對 → 發布」。草稿不能公開查看。
2. 如需要指定週表連結，我在已發布週表建立 Viewer 連結，並把完整 `https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/view#…` 發給收件者。
3. 收件者以 Edge、Chrome、Safari 或 Firefox 開啟；不需安裝 WARP、登入、輸入密碼或建立帳戶。
4. 瀏覽器在裝置內解密並顯示週次、日期、崗位、當值時間及中文姓名。
5. 訪客頁面沒有編輯控制，也不能經網址參數把自己變成管理員。
6. `/view#…` 永遠保持唯讀；即使同一瀏覽器已有有效 Access session，開啟分享連結也不會把該週表切換成編輯工作台。

完整週表連結中的 `#…` 是該份快照的解密資料。不要刪除、拆開或改寫。任何取得完整連結的人在到期或撤銷前都可查看，因此我只發到需要查看的群組；誤發時立即在管理員工作台撤銷。

## 管理員怎樣登入

1. 開啟同一個主網址。
2. 按 **管理員登入 / Admin login**。
3. 網站會在內部進入 `/auth/login`，Cloudflare Access 隨即接管驗證；使用者毋須自行輸入或收藏這條路徑。
4. 輸入 Access policy 與 Worker 有限管理員名單內共同精確列明的其中一個電郵，再輸入 Cloudflare 寄出的 One-time PIN；只在其中一邊出現並不足以取得編輯權。
5. 驗證成功後回到同一網站；Worker 核對 Access JWT，建立獨立的已簽署第一方管理員 session，然後才透過 Workers VPC 連到 Windows 主機的 NiceGUI。
6. 完成工作後按 **登出 / Log out**。網站先清除第一方管理員 session，再前往 Cloudflare Access logout，最後返回訪客唯讀狀態。

目前獲准的精確電郵是：

- `s10777@syss.edu.hk`
- `lichuangjie0208@gmail.com`
- `lichuangjie0208@outlook.com`

Access 使用 Cloudflare One-time PIN；三個電郵都不需加入本專案的 Cloudflare Dashboard。是否可進入管理工作台，仍由 Access exact-email policy、Access JWT 驗證及 Worker 有限名單共同決定；這不會授予 Cloudflare 設定或帳單權限。

Cloudflare Access 與第一方管理員 session 的最長時段都是 **8 小時**，而第一方 session 不會長過原 Access JWT。離開共用裝置前必須主動登出；管理員電郵從 allowlist 移除後，既有第一方 session 也會在下一個請求被拒絕。

## 密碼由誰管理

這套系統**沒有自製密碼資料表、密碼 hash、忘記密碼頁或共用 OP 密碼**。

- Cloudflare Access 以獲准電郵及 One-time PIN 驗證身份；應用程式不接收管理員密碼。
- NiceGUI、SQLite、KV、備份及 Git 都不保存管理員密碼。
- 下一任交接時，同步更新 Access exact-email policy 與 Worker 的 bounded exact-email allowlist；不要把前任密碼交給下一任，也不要在 `.env` 建立人手密碼。

## Worker 為何仍要驗證 JWT

Access 已是第一道身份閘門，但 Worker 仍作第二層防護。在 `/auth/login` 它會核對：

- `Cf-Access-Jwt-Assertion` 是否存在；
- JWT 是否由 `https://restless-hall-73b2.cloudflareaccess.com` 的有效簽署金鑰簽發；
- `aud` 是否等於本系統 Access application 的 audience；
- `iss`、`exp` 及管理員電郵是否符合設定；
- 身份是否同時仍在 Access exact-email policy 及 Worker 的有限精確電郵 allowlist 內。

Worker 不相信瀏覽器自行送來的 `role=admin`、email 或自訂 header。Access JWT 驗證完成後，它會建立 HMAC-SHA256 `__Host-SingYinAdminSession`；每次 HTTP／WebSocket 請求再核對簽章、期限及目前 allowlist。送往 NiceGUI 前會移除 Access JWT、`CF_Authorization` 及第一方管理員 cookie。Access application ID 可記錄為非秘密部署識別值 `25072aab-0e60-4787-8ec7-48029e448e8e`，但 audience、session cookie、JWT、token 及 secret 不可寫入公開文件或截圖。

## `/auth/*` 和登入後的頁面是甚麼

- `/auth/*` 只供 Worker、Access 登入流程及回程使用；它不是公開 API、第二個網站或書籤。
- 系統沒有另一個 `/op` 網站或管理員前綴。登入後仍在同一個 root／NiceGUI 路由；Worker 會先驗證已簽署的第一方管理員 session，才代理任何工作台頁面。
- 對外文件、群組訊息和書籤只公布主網址；介面按鈕自行處理登入與登出路徑。
- Access app destinations 只有 `/auth` 及 `/auth/*`，不可把整個 Worker 設為必須登入，否則訪客唯讀頁也會被攔截；登入後由 Worker 使用第一方管理員 session 逐一驗證 NiceGUI 請求。

## 管理員流量怎樣到達 NiceGUI

```text
同一 workers.dev 網域
    ├─ /                  → Worker 原生入口（無值班資料）
    ├─ /guest             → Worker 靜態導覽（只限 GET／HEAD；無 KV／VPC）
    ├─ /view#…            → Worker + KV 密文 → 瀏覽器本機解密（永遠唯讀）
    └─ 管理員登入         → Cloudflare Access One-time PIN → Worker 驗證 JWT
                                                   ↓ 建立／驗證第一方管理員 session
                                          ROSTER_ORIGIN VPC binding
                                                   ↓
                                VPC Service：sing-yin-roster-nicegui
                                                   ↓
                                Tunnel → Windows localhost:8080 NiceGUI／SQLite
```

NiceGUI 只存在於最後一條管理員路徑。系統沒有 NiceGUI 訪客帳戶、訪客角色或訪客 RBAC；未登入訪客不能到達 NiceGUI origin。`/view#…` 使用 KV 並不會開啟 VPC，而 `/guest` 連 KV 也不會接觸。

Workers VPC 代理必須原樣返回 VPC `fetch()` 的 Response，保留 HTTP Upgrade／WebSocket 物件；不能只複製 status、headers 及 body 後重建 Response。這讓 NiceGUI 的即時 Socket.IO 連線可穿過同一網站，而不需要開放家中路由器連接埠或把 origin 綁到 `0.0.0.0`。

## 已完成的 VPC 與 WebSocket 實證

2026-07-13 使用臨時隔離 Worker `sing-yin-roster-vpc-probe` 綁定上述 VPC Service，完成以下 live probe：

- 經 VPC → Tunnel → `localhost:8080/healthz` 回傳 HTTP 200。
- Python WebSocket client 連到 `/_nicegui_ws/socket.io/?EIO=4&transport=websocket`，收到 Engine.IO open packet：`0{"sid":"…","upgrades":[],"pingTimeout":2000,"pingInterval":…}`。
- 這證明 VPC HTTP Upgrade 及 NiceGUI WebSocket 路徑可實際通過，而不只是設定存在。
- 臨時 probe script 與 workers.dev 子網域已在測試後刪除；它不是日常入口，也沒有保留可派發的 probe URL。

正式 Worker 的 One-time PIN 登入、第一方 session 建立／登出、長時間重新連線、檔案上載及 PDF 下載仍要納入最終瀏覽器驗收；臨時 probe 證明傳輸能力，不取代完整真人工作流驗收。

## 訪客快照的加密生命週期

已發布週表仍採最少資料快照：

```text
已發布週表（Windows 主機）
    ↓ 只挑選週次／日期／崗位／當值時間／中文姓名／狀態
本機產生 AES-256-GCM key 及 nonce
    ↓
Cloudflare KV 保存密文 + 最少 week/created/expiry metadata
    ↓ key 只在完整連結 #fragment
訪客瀏覽器取得密文並以 Web Crypto 在裝置內解密
```

KV 不保存解密 key、完整查看連結、請假、班別、角色、公平、審計、備份、日誌、設定或音樂。記錄會按 expiration 到期，也可由管理員撤銷；邊緣同步最多可能需要約一分鐘。

## 本機及 WARP 只作維護後備

- `http://127.0.0.1:8080`：主機健康檢查、故障診斷及 Cloudflare 無法使用時的現場維護後備。
- `http://roster.singyin.internal:8080`：已登記 WARP 裝置的緊急／維護後備。
- 兩者都不是日常派發地址，也不應印在給訪客的使用指引。
- 後備入口保留至正式 Access、登入／登出、WebSocket、上載、PDF 及完整虛構寫入流程驗收完成；不要為了「只留一個網址」而提早刪除復原路徑。

## 故障時的下一步

| 情況 | 安全處理 |
|---|---|
| 訪客連結不完整、到期或撤銷 | 向首席導學風紀索取同一主網站的新完整連結 |
| 管理員登入不斷返回訪客頁 | 核對 Access exact-email policy、Worker bounded allowlist、Cloudflare 帳戶及 8h session；不要建立本機共用密碼 |
| 已登入但編輯工作台未載入 | 核對 Worker JWT、VPC binding、Tunnel、主機 `/healthz` 及 WebSocket；必要時用維護後備入口 |
| 登出後仍見管理控制 | 關閉頁面並核對 Access logout/session；在修正前停止遠端編輯 |
| 誤發 Viewer 連結 | 撤銷該 KV 記錄，約一分鐘後核對，再建立新連結 |
| 週表經請假調整 | 完成正式調整後建立新 Viewer 連結並撤銷舊連結 |

## 交接核對

- [ ] 下一任只需記住及分享 canonical workers.dev 主網址。
- [ ] 未登入訪客可查看指定已發布週表，但沒有任何編輯入口。
- [ ] 入口的系統／淺色／深色、320 px、鍵盤、forced-colours 及 reduced-motion 狀態都可閱讀；經文只在使用者要求時刷新。
- [ ] 全站直接經文已核對為繁中 RCUV 2010（神版）與英文 NKJV；服務精神文字沒有冒充逐字經文。
- [ ] 「管理員登入」由 Cloudflare Access 接管，只有同時在 Access policy 與 Worker bounded exact-email allowlist 的管理員通過；系統沒有自製密碼。
- [ ] 登入後同一網站顯示完整 NiceGUI；8 小時到期或主動登出後回復訪客權限。
- [ ] Worker 拒絕缺少、過期、錯誤 audience／issuer 或非管理員 email 的 JWT。
- [ ] `/auth/*` 只供內部流程，不在群組、README 快速入口或書籤中派發。
- [ ] VPC HTTP 及 WebSocket probe 證據有記錄；正式瀏覽器仍完成登入、登出、重新連線、上載、PDF 及虛構寫入驗收。
- [ ] 本機／WARP 後備可用，但只寫入維護手冊，不再當作正常使用入口。
- [ ] Access audience、JWT、cookie、管理 token 及其他 secret 沒有進入 Git、文件、截圖或日誌。

這個模型讓所有人面向同一個品牌網站：訪客看到清楚的唯讀值班表，獲准管理員登入後才取得工作工具，而維護後備仍在背後可復原。
