# 單一網站、訪客查看與管理員登入手冊 / Canonical site access guide

我是李創杰，2026–2027 年度首席導學風紀。我希望下一任只需記住及分享一個網站，不必向不同使用者解釋 localhost、WARP 或多個入口：

**`https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/`**

> **發布狀態提示（2026-07-15）：** `/try` 與正式資料零起點屬下一候選版本。下列內容定義完成後必須成立的安全／體驗契約；未通過 Worker、Python、PDF、桌面／手機瀏覽器及受控部署驗證前，不可把它描述為已上線。

這個網址提供五種清楚分開、權限不互相提升的狀態：

- **`/` 入口／Entrance：** 未有有效 Access session 時，Worker 原生首頁說明系統用途、訪客導覽、分享連結與管理員登入；它本身不是值班表或 NiceGUI。管理員驗證成功後會返回同一個 `/`，由 Worker 代理 NiceGUI。
- **`/guest` 訪客導覽／Guest tour：** Worker 原生靜態產品導覽，只接受 `GET`／`HEAD`。它不連接 VPC、NiceGUI、SQLite 或 KV，也不包含任何正式值班表資料。
- **`/try` 互動試用／Interactive trial：** 以固定虛構中文姓名完成請假、生成、核對及雙語 PDF；狀態只留在目前分頁 30 分鐘，不寫入伺服器或正式系統。
- **`/view#…` 已發布週表／Published roster：** 只有取得完整分享連結的人才可在瀏覽器取得 KV 中的加密快照，並用只留在 `#fragment` 的鑰匙於裝置內解密；它永遠唯讀。
- **管理員工作台／Administrator workbench：** 在同一入口按「管理員登入」，通過 Cloudflare Access 及 Worker JWT 驗證後，請求才會沿 VPC 到達 Windows 主機的 NiceGUI 與 SQLite。

我不會另外派發「管理員網站」。`/auth/*`、VPC Service、私人 WARP 地址及 localhost 都是系統內部或維護路徑，不是給一般使用者記住的第二個網站。

## 一個網域，五種安全狀態

| 狀態／State | 所屬層／Owner | 資料與方法／Data and methods | 權限結果／Permission result |
|---|---|---|---|
| 公開 `/` 入口／Public entrance | Cloudflare Worker | 沒有有效 Access session 時的靜態入口；不讀取值班資料／Static entrance without a valid Access session; no roster read | 只提供安全下一步，不提供編輯／Guidance only; no editing |
| `/guest` 訪客導覽／Guest tour | Cloudflare Worker | 只限 `GET`／`HEAD`；無 VPC、NiceGUI、SQLite、KV／`GET`／`HEAD` only; no VPC, NiceGUI, SQLite or KV | 只看系統流程及保障說明；沒有值班表／Read-only system tour; no roster data |
| `/try` 互動試用／Interactive trial | Worker static assets + browser | 固定虛構資料；30 分鐘 `sessionStorage`；無應用 API、KV、VPC、NiceGUI、SQLite、備份或伺服器日誌／Fixed fictional data; 30-minute `sessionStorage`; no application API or server persistence | 可試請假、生成、預覽及裝置內雙語 PDF；不能發布、分享或入帳／Try leave, generation, preview, and on-device PDF; no publication, share, or ledger posting |
| `/view#…` 已發布週表／Published roster | Worker + KV + browser Web Crypto | KV 只保存密文及最少 metadata；鑰匙留在 fragment／KV holds ciphertext and minimum metadata; key stays in the fragment | 只看獲分享的週表；不能編輯或升級權限／View the shared roster only; cannot edit or elevate |
| 已驗證管理員／Verified administrator | Access + Worker + VPC + NiceGUI | JWT 逐請求驗證後，才在同一 `/` 代理至 NiceGUI／JWT is verified before NiceGUI is proxied at the same `/` | 完整 OP 工作流，仍受政策、交易、確認及審計限制／Full OP workflow under policy, transaction, confirmation and audit controls |

**English contract:** without a valid Access session, `/` is the public Worker entrance. `/guest` is a Worker-native, data-free platform tour. `/try` is a static browser-only trial with fixed fictional Chinese names, a 30-minute tab session, and on-device bilingual PDF generation; trial interaction calls no application API and writes to no server system. `/view#…` is an encrypted, expiring and revocable published-roster snapshot backed by KV and decrypted in the browser. Only a verified administrator reaches NiceGUI through Access, Worker JWT validation and VPC, after which the same `/` serves the proxied workbench. NiceGUI has no guest account, guest role or guest RBAC.

一般人只需接觸主網址、同站 `/guest` 導覽、導覽內的 `/try` 試用，或首席導學風紀發出的完整 `/view#…` 週表連結。管理員按頁面的登入按鈕即可；不需要抄寫內部路徑。這些是同一網域下的不同安全狀態，不是不同網站。

## 入口頁怎樣使用

入口頁把「這個系統為何存在」與「我現在可以做甚麼」分開：寬螢幕以約 58/42 的敘事／登入面板排列，窄螢幕則依同一閱讀次序直向排列。訪客可選擇 **以訪客身份瀏覽／Continue as guest** 前往 `/guest`，獲准管理員則使用唯一清楚的 **管理員登入／Admin login** 按鈕。入口不是值班表本身，也不會把訪客誤導到編輯畫面。

- `/guest` 依「平台用途 → 每週能力 → 開始試用 → 可信邊界 → 資源」整理產品敘事；它不顯示正式姓名、崗位、請假、公平帳本、備份、日誌或設定。
- `/guest` 的 HTML、CSS 及 JavaScript 由 Worker 直接提供；路由只接受 `GET` 及 `HEAD`，其他方法回傳 `405 Method Not Allowed`。
- 顯示 `/guest` 不會建立 VPC 連線，不會啟動或查詢 NiceGUI，不會讀寫 SQLite，也不會讀、寫、列出或刪除 KV。

## 訪客怎樣安全試用 `/try`

1. 在 `/guest` 閱讀平台用途後按「開始試用」，進入同站 `/try`。
2. 核對頁頂「虛構資料／目前分頁／30 分鐘／不寫入伺服器」邊界；不要在試用頁輸入真實姓名或校務資料。
3. 使用預載虛構中文姓名及職位，加入一項示範請假，再生成及核對週表。
4. 需要時切換繁中／英文提示及淺／深色外觀；兩種語言的姓名仍保持中文。
5. 按下載後，瀏覽器直接建立中英並列的 A4 橫向 PDF。PDF 只因訪客主動保存而留在裝置；網站不保存下載副本。
6. 按「重置」可立即清除；建立 30 分鐘後或關閉分頁時，`sessionStorage` 狀態失效。

Worker 只傳送同源、版本控制的 HTML／CSS／JavaScript 靜態資產。載入完成後，試用的名單選擇、請假、生成結果及 PDF 不會送往應用 API，也不接觸 KV、VPC、NiceGUI、SQLite、公平帳本、備份或伺服器日誌。試用不能發布、不能建立 `/view#…`、不能轉入正式名單，也不能用作正式公平或服務時數證據。完整發布／備份／還原演練仍使用本機 Practice Mode。

### 發布前及部署後怎樣驗證試用邊界

以下是可重複的候選版本證據，不是以「頁面看起來正常」代替安全核對。先在專案根目錄執行靜態與路由契約：

```powershell
python -X utf8 -m pytest -q tests\test_cloudflare_guest_trial.py tests\test_cloudflare_roster_viewer.py
Set-Location cloudflare\roster_viewer
deno check worker.js
deno test worker_gateway_test.js
```

再在第一個 PowerShell 視窗保持本機 Worker 運行：

```powershell
pnpm exec wrangler dev --config .\wrangler.jsonc --port 8791 --local
```

在第二個視窗回到專案根目錄，執行真正瀏覽器驗證：

```powershell
python -X utf8 scripts\verify_guest_trial.py --base-url http://127.0.0.1:8791
```

驗證器會檢查桌面／手機、繁中／英文、淺／深色、排班政策、試用請假、單頁 A4 橫向 PDF、中文姓名、30 分鐘真實失效、畸形 `sessionStorage` 復原、未知子路徑 fail-closed、零試用互動請求、console／page error 及水平 overflow，並把不含正式資料的截圖與 `verification.json` 放在 `test-results/guest-trial/`。本機通過只證明候選資產；Worker 部署後必須把 `--base-url` 改為 canonical 網址再完整執行一次，才可聲稱 `/try` 已上線。最後仍要執行 `python -X utf8 -m pytest -q` 及完整發布閘門。

- 外觀可以選擇跟隨系統、淺色或深色；選擇只保存在該瀏覽器，不影響身份或資料。
- **分享網站入口 / Share this site** 只分享 canonical 首頁網址，方便別人認識系統或前往管理員登入；它不會包含任何值班表、查看密鑰或編輯權限。要讓別人看某一週值班表，仍須在發布後另行發出該週的完整 `/view#…` 連結。
- 頁面在 320 px 寬度、鍵盤操作及 Windows 高對比／forced-colours 模式仍保留完整閱讀與焦點次序。
- 入場及按鈕回應都是一次性的短動效；系統要求 reduced motion 時會直接呈現完成狀態，沒有循環、背景漂浮或自動輪播。

入口也設有一段簡短的「今日經文與靈修提醒」，讓我在開始每週工作前先停下來反思。繁體中文固定使用 **和合本修訂版 2010（神版）**，英文固定使用 **New King James Version（NKJV）**。初次顯示會按日期穩定選取本機精選內容；只有我或訪客按「換一節經文 / Show another verse」才會更換，不會自動播放，也不會向外部經文服務傳送請求。精選池逐項與正式 `data/devotional/daily-verses.seed.json` 核對，錯誤譯本標籤、缺漏經文或未完成精確核實會阻擋發布。

以上只是呈現與閱讀改良：訪客唯讀、管理員登入、JWT 驗證、VPC 代理及 `/view#…` 加密快照的安全邊界完全不變。

## 訪客怎樣查看指定週表

`/guest` 是不含資料的系統導覽；它不能代替某一週的分享連結。要查看指定週表，必須依以下流程使用完整 `/view#…` 連結：

1. 我在管理員工作台完成「生成草稿 → 核對 → 發布」。草稿不能公開查看。
2. 如需要指定週表連結，我在已發布週表建立 Viewer 連結，並等待安全處理完成。Cloudflare KV 需要時間把新密文同步到可讀節點；系統會先以不帶管理員權杖的公開請求核對同一份密文，成功後才顯示完整 `https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/view#…`。如逾時，系統不會交付連結或解密鑰匙，並會對該次密文的精確儲存鍵提出撤銷要求；操作員仍應在「存取控制台」核對。
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
    ├─ /try               → 靜態瀏覽器試用（30 分鐘 sessionStorage；裝置內 PDF）
    ├─ /view#…            → Worker + KV 密文 → 瀏覽器本機解密（永遠唯讀）
    └─ 管理員登入         → Cloudflare Access One-time PIN → Worker 驗證 JWT
                                                   ↓ 建立／驗證第一方管理員 session
                                          ROSTER_ORIGIN VPC binding
                                                   ↓
                                VPC Service：sing-yin-roster-nicegui
                                                   ↓
                                Tunnel → Windows localhost:8080 NiceGUI／SQLite
```

NiceGUI 只存在於最後一條管理員路徑。系統沒有 NiceGUI 訪客帳戶、訪客角色或訪客 RBAC；未登入訪客不能到達 NiceGUI origin。`/view#…` 使用 KV 並不會開啟 VPC；`/guest` 與 `/try` 都不接觸 KV 或 VPC，試用狀態只存在瀏覽器分頁。

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
- [ ] `/guest` 不含正式資料；`/try` 只載入固定虛構中文姓名，30 分鐘／關閉分頁／重置後清除，且網絡記錄沒有試用 API、KV 或 VPC 請求。
- [ ] `/try` 可在桌面及手機完成請假、生成、預覽與雙語 A4 橫向 PDF；PDF 姓名保持中文並清楚標示非正式試用。
- [ ] 本機 Wrangler 與 canonical Worker 都有各自的 `scripts/verify_guest_trial.py` pass report；報告日期及 base URL 與本次發布相符。
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
