# 單一網站存取、訪客體驗與唯讀分享手冊

> **v1.2 rc5 候選狀態：** commit `bafaef6` 的統一訪客來源已以 fingerprint `c10de03174e519f86ac505f3cf883063830717166f2e482e0b0ed8c32f1563fd`（238 inputs）通過 13／13 正式 gate，計劃標籤為 `v1.2.0-rc.5`。`C:\SingYinRoster` 已 forward-recover 至健康、ready 的 schema-compatible rc4／`30f282f`；Cloudflare Worker 仍保留 pre-v1.2 baseline。Access 精確 `/auth/login` 已確認，Windows／Worker 受控切換仍待完成，尚未宣告 rc5 已部署。

我是李創杰。我希望所有使用者只需記住同一個網站，但同一個網址不代表相同權限。v1.2 把入口、完整 Guest 體驗及管理員工作台統一到同一套 NiceGUI 路由和元件；只有已發布週表的 `/view#…` 保留為獨立、只讀、可分享的能力連結。

完整 Guest 隔離細節見 [統一訪客模式安全模型](UNIFIED_GUEST_SECURITY_MODEL.md)。

## 一個網站，四種身份狀態

| 狀態 | 看見甚麼 | 可否寫入正式資料 |
|---|---|---|
| `PUBLIC` | 品牌入口、經文、角色選擇、登入／訪客開始 | 不可 |
| `GUEST` | 與管理員相同的 NiceGUI 頁面骨架及虛構資料工作流 | 不可；只改目前臨時工作區 |
| `ADMIN` | 完整正式工作台 | 可以，但仍受排班政策、版本、審計、備份及 maintenance lock 限制 |
| `LOCAL_MAINTENANCE` | Windows 主機本機維護入口 | 可以，只供受控維護 |

另有 `/view#…`：它只顯示首席導學風紀明確發出的已發布週表快照，不提供 Guest 試用或管理員能力。

## 入口及路由

- `/`：未有身份時顯示統一品牌入口；已有 Admin／Guest session 時顯示相同 Dashboard。
- `/auth/admin/start`：開始 Cloudflare Access 管理員登入。
- `POST /auth/guest/start`：建立最長 30 分鐘的 Guest session。
- `GET /auth/status`：讓頁面及分頁重新核實身份、到期、撤權及 origin 健康。
- `POST /auth/logout`：清除身份、Guest 工作區、待下載檔案、sessionStorage 及同 session 分頁狀態。
- `/guest`、`/try`：兼容舊書籤，重新導向統一入口並開始 Guest session；不再維護第二套靜態產品。
- `/view#…`：獨立、只讀、加密、到期及可撤銷的已發布週表。

## 訪客怎樣使用

1. 開啟同一正式網址：<https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/>。
2. 按 **訪客體驗 / Try as guest**。
3. 系統建立有時限的 Guest session，再開啟與管理員相同的 Dashboard。
4. 依「生成 → 核對／匯出 → 已發布請假調整」完成虛構示範。
5. 頁面以 `DEMO` 標示臨時資料；限制項使用 `PRECOMPUTED` 或 `RESTRICTED` 說明原因。
6. 完成後按 **登出**。共用電腦不可只關閉一個分頁。

訪客可以修改虛構名單、示範請假、草稿、手動調整、示範發布、公平顯示及 `DEMO` PDF／JSON。AI、檔案匯入、上載、剪貼簿、外部音樂網址、正式備份／還原、Viewer 分享、真實資料匯出及永久設定均不可用。

每個分頁有獨立 workspace；一個分頁的示範修改不應覆寫另一個分頁。每次有意義修改後，origin 只把最新、已簽署的 token 推送到該分頁 `sessionStorage`。重新整理時還原必須通過目前 Guest session、workspace、NiceGUI tab、revision、boot ID 及連線 nonce 核對；複製、篡改、過期、舊 revision 或 origin 重啟後的 token 會被拒絕並回到安全虛構 fixture。這不是長期儲存。

## 管理員怎樣登入

1. 在同一入口按 **管理員登入 / Admin sign-in**。
2. Cloudflare Access 只接管登入路徑；輸入 policy 精確列明的電郵及 Cloudflare One-time PIN。
3. Worker 驗證 Access JWT 的簽章、issuer、audience、到期及 allowlist。
4. Worker 建立有限期的第一方管理員 session，再為 origin 簽發 HMAC principal。
5. NiceGUI 驗證 `mode`、`subject`、`sid`、`exp`、`auth_epoch`、`kid` 及簽章後，才提供正式工作流。
6. 完成後按 **登出**；系統同時清除應用 session，再繼續 Cloudflare Access logout。

系統沒有自製管理員密碼資料表、共用 OP 密碼或忘記密碼流程。Cloudflare 的 secret、JWT、cookie 及 HMAC 金鑰不可寫入 Git、文件、截圖、日誌或備份。

## 為甚麼同一畫面仍然安全

Guest 和 Admin 共用渲染器，不共用資料 adapter：

```text
同一 NiceGUI 頁面
        │
        ▼
伺服器核實 PageContext
        │
        ├── ADMIN ──> RosterWorkflow ──> 正式 SQLite／備份／審計
        │
        └── GUEST ──> GuestWorkspaceAdapter ──> 程序記憶體／虛構 fixture
```

按鈕是否顯示不是安全邊界。每個頁面回調、服務、匯出、下載、分享及儲存層仍會重新核對能力。瀏覽器自行修改 header、query、JavaScript 或儲存內容不能升級身份。

## 唯讀 `/view#…` 分享

只有管理員可從已發布週表建立 Viewer 連結：

1. NiceGUI 從已發布版本建立最少欄位快照。
2. 快照在 Windows 主機本機以 AES-GCM 加密。
3. Worker／KV 只保存 nonce、密文、時間及非秘密 metadata。
4. 解密 key 只存在完整 URL 的 `#fragment`，初始 HTTP request 不會把它送到 Worker。
5. 收件者瀏覽器取得密文並在本機解密。

連結在到期或撤銷前，任何持有完整 URL 的人都可查看；只應發給需要的人。已發布後請假調整不會自動修改舊快照，必須撤銷舊連結並建立新版本。分享連結不能升級為 Guest 或 Admin。

## 健康、到期及故障

- `/healthz`：程序及資料庫可讀的基本存活狀態。
- `/readyz`：migration、maintenance、恢復標記及待完成備份義務均正常，才回報可寫。
- `/auth/status`：瀏覽器身份、到期、撤權及 origin 可達狀態。

若 Guest session 到期，畫面應清除臨時工作區並返回入口。若 Admin session 到期或撤權，下一次狀態核對、HTTP 請求或回調會被拒絕；未提交輸入不應被靜默寫入。

Cloudflare 暫時不可用時，只有維護者才使用 localhost 或已核准 WARP 後備；不要把維護地址當作第二個日常網站。

## 發布前核對

- [ ] `SING_YIN_UNIFIED_GUEST=0` 時，未驗證 Guest principal 不可進入 origin。
- [ ] `SING_YIN_UNIFIED_GUEST=1` 的隔離測試使用臨時 SQLite、備份及日誌路徑。
- [ ] Guest 與 Admin 每一正式路由有相同頁面骨架及清楚能力狀態。
- [ ] Guest adapter 不引用正式 SQLAlchemy、AI、HTTP、備份、上載、分享或背景工作。
- [ ] 兩個 Guest、同一 Guest 多分頁、登出、到期、撤權、程序重啟及交叉下載均通過。
- [ ] 同一分頁重新整理只還原最新合法 snapshot；複製分頁獲得新 workspace，篡改／過期／舊 boot token 安全回到 fixture。
- [ ] Guest PDF／JSON 標明 `DEMO`，使用 `no-store`，不含真實資料。
- [ ] `/view#…` 只接受已發布快照，草稿不能分享。
- [ ] 管理員登入／登出、長時間重連、上載、PDF 及完整寫入流程完成真人驗收。
- [ ] `/healthz` 及 `/readyz` 都通過後才開放寫入。

## English quick guide

The verified v1.2 rc5 candidate uses one canonical site and one NiceGUI product. Public users choose either **Admin sign-in** or a time-limited **Guest experience**. Administrators use the official workflow and SQLite database; guests use a server-verified, memory-only adapter populated with fictional Chinese names. Each Guest tab stores only the latest signed, bound snapshot token in `sessionStorage`; restore also requires the current connection nonce, and copied, tampered, expired, stale, or old-boot tokens fail safely. UI hiding is not the security boundary: capabilities are checked again in callbacks, services, downloads, exports, storage, and sharing.

`/guest` and `/try` are compatibility redirects to the unified entry. `/view#…` remains a separate, encrypted, read-only published-roster link. The rc5 source has its matching thirteen-gate report; the feature becomes live only after the controlled rc5 Windows rollout, already-confirmed exact `/auth/login` Access path, matching Worker secrets, Worker deployment and live acceptance all pass.
