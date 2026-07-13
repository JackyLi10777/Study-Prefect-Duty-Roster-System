# 單一網站、訪客查看與管理員登入手冊 / Canonical site access guide

我是李創杰，2026–2027 年度首席導學風紀。我希望下一任只需記住及分享一個網站，不必向不同使用者解釋 localhost、WARP 或多個入口：

**`https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/`**

這個網址同時服務兩種使用情境：

- **訪客／Guest：** 不登入，只能查看我明確發布的唯讀值班表。
- **管理員／Administrator：** 在同一網站按「管理員登入」，經 Cloudflare Access 驗證後，原網站會解鎖完整 NiceGUI 編輯工作台。

我不會另外派發「管理員網站」。`/auth/*`、`/op/*`、VPC Service、私人 WARP 地址及 localhost 都是系統內部或維護路徑，不是給一般使用者記住的第二個網站。

## 一個網址，兩種權限

| 狀態 | 畫面 | 可以做甚麼 | 不可以做甚麼 |
|---|---|---|---|
| 未登入訪客 | 同一 workers.dev 網站的唯讀頁面 | 查看指定的已發布週表、日期、崗位、當值時間及中文姓名 | 生成、修改、發布、請假調整、公平、審計、備份、還原或設定 |
| 已驗證管理員 | 同一 workers.dev 網站內的完整 NiceGUI 工作台 | 完整 OP 工作流，包括生成、發布、PDF、請假調整、公平、備份及還原 | 不能繞過排班政策、交易、確認或審計 |

一般人只會接觸主網址或同一 host 下的完整週表連結，例如 `/view#…`。管理員按頁面的登入按鈕即可；不需要抄寫內部路徑。

## 訪客怎樣查看

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
4. 以 Access policy 內精確列明的管理員電郵 `s10777@syss.edu.hk` 完成 Cloudflare 帳戶登入及 MFA。
5. 驗證成功後回到同一網站；Worker 核對 Access JWT，然後透過 Workers VPC 連到 Windows 主機的 NiceGUI。
6. 完成工作後按 **登出 / Log out**。網站會前往 Cloudflare Access logout，清除 Access session，再返回訪客唯讀狀態。

Cloudflare Access session 設為 **8 小時**。這是最長的登入時段，不代表瀏覽器可以無限期保持編輯權。離開共用裝置前必須主動登出；管理員電郵或 Cloudflare 帳戶被撤銷後，不能再登入。

## 密碼由誰管理

這套系統**沒有自製密碼資料表、密碼 hash、忘記密碼頁或共用 OP 密碼**。

- 管理員身份、密碼、MFA、登入復原及 Access session 由 Cloudflare Identity Provider／Cloudflare Access 管理。
- NiceGUI、SQLite、KV、備份及 Git 都不保存管理員密碼。
- 下一任交接時，更新 Access exact-email policy；不要把前任密碼交給下一任，也不要在 `.env` 建立人手密碼。

## Worker 為何仍要驗證 JWT

Access 已是第一道身份閘門，但 Worker 仍作第二層防護。每次準備代理管理員工作台時，它會核對：

- `Cf-Access-Jwt-Assertion` 是否存在；
- JWT 是否由 `https://restless-hall-73b2.cloudflareaccess.com` 的有效簽署金鑰簽發；
- `aud` 是否等於本系統 Access application 的 audience；
- `iss`、`exp` 及管理員電郵是否符合設定；
- 身份是否仍是 Access exact-email policy 允許的管理員。

Worker 不相信瀏覽器自行送來的 `role=admin`、email 或自訂 header。驗證完成後，它才建立受控的內部身份資訊；送往 NiceGUI 前會移除 Access JWT 及 `CF_Authorization` cookie。Access application ID 可記錄為非秘密部署識別值 `25072aab-0e60-4787-8ec7-48029e448e8e`，但 audience、session cookie、JWT、token 及 secret 不可寫入公開文件或截圖。

## `/auth/*` 和 `/op/*` 是甚麼

- `/auth/*` 只供 Worker、Access 登入流程及回程使用；它不是公開 API、第二個網站或書籤。
- `/op/*` 是受 Access 保護的內部管理路徑前綴；未驗證訪客不能直接使用。
- 對外文件、群組訊息和書籤只公布主網址；介面按鈕自行處理登入與登出路徑。
- 路徑級 Access 只保護管理功能，不可把整個 Worker 設為必須登入，否則訪客唯讀頁也會被攔截。

## 管理員流量怎樣到達 NiceGUI

```text
同一 workers.dev 網站
    ├─ 未登入 → Worker 訪客唯讀頁
    └─ 已登入 → Worker 驗證 Access JWT
                       ↓
              ROSTER_ORIGIN VPC binding
                       ↓
        VPC Service：sing-yin-roster-nicegui
        Service ID：019f5b30-d07c-7a63-a273-6b2ccb7318f8
                       ↓
        Tunnel：ba6b6426-d012-4ecb-bafa-cbdbf2659731
                       ↓
        Windows 主機 localhost:8080 NiceGUI
```

Workers VPC 代理必須原樣返回 VPC `fetch()` 的 Response，保留 HTTP Upgrade／WebSocket 物件；不能只複製 status、headers 及 body 後重建 Response。這讓 NiceGUI 的即時 Socket.IO 連線可穿過同一網站，而不需要開放家中路由器連接埠或把 origin 綁到 `0.0.0.0`。

## 已完成的 VPC 與 WebSocket 實證

2026-07-13 使用臨時隔離 Worker `sing-yin-roster-vpc-probe` 綁定上述 VPC Service，完成以下 live probe：

- 經 VPC → Tunnel → `localhost:8080/healthz` 回傳 HTTP 200。
- Python WebSocket client 連到 `/_nicegui_ws/socket.io/?EIO=4&transport=websocket`，收到 Engine.IO open packet：`0{"sid":"…","upgrades":[],"pingTimeout":2000,"pingInterval":…}`。
- 這證明 VPC HTTP Upgrade 及 NiceGUI WebSocket 路徑可實際通過，而不只是設定存在。
- 臨時 probe script 與 workers.dev 子網域已在測試後刪除；它不是日常入口，也沒有保留可派發的 probe URL。

正式 Worker 的 Access 登入、登出、長時間重新連線、檔案上載及 PDF 下載仍要納入最終瀏覽器驗收；臨時 probe 證明傳輸能力，不取代完整真人工作流驗收。

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
| 管理員登入不斷返回訪客頁 | 核對 Access exact-email policy、Cloudflare 帳戶及 8h session；不要建立本機共用密碼 |
| 已登入但編輯工作台未載入 | 核對 Worker JWT、VPC binding、Tunnel、主機 `/healthz` 及 WebSocket；必要時用維護後備入口 |
| 登出後仍見管理控制 | 關閉頁面並核對 Access logout/session；在修正前停止遠端編輯 |
| 誤發 Viewer 連結 | 撤銷該 KV 記錄，約一分鐘後核對，再建立新連結 |
| 週表經請假調整 | 完成正式調整後建立新 Viewer 連結並撤銷舊連結 |

## 交接核對

- [ ] 下一任只需記住及分享 canonical workers.dev 主網址。
- [ ] 未登入訪客可查看指定已發布週表，但沒有任何編輯入口。
- [ ] 「管理員登入」由 Cloudflare Access 接管，只有 exact-email 管理員通過；系統沒有自製密碼。
- [ ] 登入後同一網站顯示完整 NiceGUI；8 小時到期或主動登出後回復訪客權限。
- [ ] Worker 拒絕缺少、過期、錯誤 audience／issuer 或非管理員 email 的 JWT。
- [ ] `/auth/*` 只供內部流程，不在群組、README 快速入口或書籤中派發。
- [ ] VPC HTTP 及 WebSocket probe 證據有記錄；正式瀏覽器仍完成登入、登出、重新連線、上載、PDF 及虛構寫入驗收。
- [ ] 本機／WARP 後備可用，但只寫入維護手冊，不再當作正常使用入口。
- [ ] Access audience、JWT、cookie、管理 token 及其他 secret 沒有進入 Git、文件、截圖或日誌。

這個模型讓所有人面向同一個品牌網站：訪客看到清楚的唯讀值班表，獲准管理員登入後才取得工作工具，而維護後備仍在背後可復原。
