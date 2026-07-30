# 單一網站存取、訪客體驗與唯讀分享手冊

> **線上來源真相（2026-07-30）：** Windows origin 正運行 clean annotated `v1.2.0-rc.40`／`2ec900a5ef1c021183717dfa648ef76b55452ffb`；canonical Worker `2cb38b05-6091-43be-86d3-d9f3ccae1ceb` 承接 100% 流量。Public 入口音樂、Viewer 靜默契約、canonical health 及真實 Guest Dashboard 已核對；Worker runtime 未變。第一個 origin 回退為 tagged `v1.2.0-rc.39`／commit `80b9de7ea8abce57b67c6041e580f915a819315e`；rc35／`570e29f745eef7c1995635d1b187021a8fec6ea4` 及 Worker `d7069f99-81b4-4388-aa28-383b58bfc68f` 是更深復原證據；真人驗收未完成。
> **歷史 rc30 乾淨發布證據：** `C:\SingYinRoster` 曾以受控方式運行 `v1.2.0-rc.30`／`74b84f43786b00feb15b51a6270ff71c9430773f`；canonical Worker version `11763f08-d40d-46d5-93dc-5ca2599d4154` 當時承接 100% 流量。Public、Guest、Admin 及獨立 `/view#…` Viewer 均由同一 canonical 網站提供；canonical public root、capability health、desktop／320px theme control 及 Guest Engineering ≈10B disclosure 已以 live Chromium 核對，private readiness 保持預期 redirect。
> **復原層級：**目前第一層 origin 是 tagged `v1.2.0-rc.39`／commit `80b9de7ea8abce57b67c6041e580f915a819315e`，保留相容 Worker `2cb38b05-6091-43be-86d3-d9f3ccae1ceb`。rc35／`570e29f…`、rc30／`74b84f…`、rc27／`c4c728aa…`、rc26／`248955cb…` 及較舊 Worker 只屬更深一層的歷史復原來源。
> **歷史 rc31 來源候選（已凍結、未上線）：** `codex/rc31-unified-theme-controls` 曾統一 Public／Viewer 與 NiceGUI 外觀控制，其 297 個可部署來源檔案以指紋 `7f405269322e67ddc1fdfd5dde004af5079b315725487303fbecd8e1c0954042` 通過當時 15／15 候選閘門。它沒有部署，亦不是目前候選或回退目標；目前 rc39 production pair 及 rc35 第一層回退以本頁頂部為準。
> **歷史 rc21 受控上線證據：** 291 個來源檔案以指紋 `e7b2a52a004968b899a76de583ca86cb1d575d2a9bbba4cedd5e0e7ab67361b1` 通過 14／14 正式 gate；切換前備份 `20260726-003841-844011-manual_verified_backup.sqlite3`／`fed7b02a82265477a19c9be675d7fd14e8d4b259055af5331e2f76f40b8ee777` 已完成 checksum、公平對帳、行數核對、還原審計及隔離還原。這段只保留歷史來源；目前 live 與第一層配對回退以上方 rc39／rc35 說明為準。

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
- 入口頁首的 Service Weave 標誌以同一幾何的透明淺／深資產配對呈現，並跟隨目前解析出的淺色／深色外觀；只有偏好尚未設定時才跟隨裝置系統。它不會再把固定深色 favicon 方塊放到淺色頁面上。
- `/auth/admin/start`：開始 Cloudflare Access 管理員登入。
- `POST /auth/guest/start`：建立最長 30 分鐘的 Guest session。
- `GET /auth/status`：讓頁面及分頁重新核實身份、到期、撤權及 origin 健康。
- `POST /auth/logout`：清除身份、Guest 工作區、待下載檔案、sessionStorage 及同 session 分頁狀態。
- `/guest`、`/try`：兼容舊書籤，重新導向統一入口並開始 Guest session；不再維護第二套靜態產品。
- `/view#…`：獨立、只讀、加密、到期及可撤銷的已發布週表。

rc20 已把 `<=560px` 的 Admin／Guest 操作放到 story 欄早段，讓兩者在首屏可觸及；原 access panel 的同角色連結只在該 mobile layout 隱藏，DOM 仍保留 desktop 結構。每一 viewport 只有一個 visible Admin 入口和一個 visible Guest 入口，兩者仍分別前往 `/auth/login` 及 `/guest`，不建立新的身份模式、資料 adapter 或 `/mobile` route。這項行為已通過 rc20 source-matched 自動化及 canonical smoke；真人手機驗收仍須按清單完成。

## 訪客怎樣使用

1. 開啟同一正式網址：<https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/>。
2. 按 **訪客體驗 / Try as guest**。
3. 系統建立有時限的 Guest session，再開啟與管理員相同的 Dashboard。
4. 依「生成 → 核對／匯出 → 已發布請假調整」完成虛構示範。
5. 頁面以 `DEMO` 標示臨時資料；限制項使用 `PRECOMPUTED` 或 `RESTRICTED` 說明原因。
6. 完成後按 **登出**。共用電腦不可只關閉一個分頁。

訪客可以修改虛構名單、示範請假、草稿、手動調整、示範發布、公平顯示及 `DEMO` PDF／JSON。AI、檔案匯入、上載、剪貼簿、外部音樂網址、正式備份／還原、Viewer 分享、真實資料匯出及永久設定均不可用。

Admin 與 Guest 使用同一個 Assist. 排班模式選擇器及穩定代碼：`legacy_fixed_weekday` 保留 AHP 的固定星期，`flexible_weekly` 只在已選「可值班日」中按週輪換並在可行情況避免重複上週同日。兩種模式均只容許 Assistant Head Study Prefect 任 Assist. in charge，並重新核對請假、同日不重複及不連續當值。Admin 把模式連同週表持久化；Guest 只把相同操作結果留在目前記憶體工作區。

每個分頁有獨立 workspace；一個分頁的示範修改不應覆寫另一個分頁。每次有意義修改後，origin 只把最新、已簽署的 token 推送到該分頁 `sessionStorage`。重新整理時還原必須通過目前 Guest session、workspace、NiceGUI tab、revision、boot ID 及連線 nonce 核對；複製、篡改、過期、舊 revision 或 origin 重啟後的 token 會被拒絕並回到安全虛構 fixture。這不是長期儲存。

## 登入首頁的歡迎音樂

- 首頁只播放已核准的本機純音樂；不會在已發布週表的 `/view#…` 頁播放。
- 每次進入首頁都會立即嘗試播放；尚未儲存音量的瀏覽器以 **50%** 開始，任何已明確儲存的音量都會完整保留，包括 25%。可隨時暫停、播放下一首或調校音量；手動暫停只維持目前這次停留，音量則保存在目前瀏覽器。這些狀態不寫入名單、值班表、審計或備份。
- 淺色模式使用較明亮的歌單，深色模式使用較安靜的歌單。切換外觀會使用對應歌單，但不會改變登入身份或資料。
- 公開入口只顯示單一淺色／深色控制，圖標表示目前解析模式，文字替代說明下一個動作。瀏覽器尚未保存偏好時跟隨裝置系統；第一次操作保存目前解析結果的相反模式，其後只在明確淺色與深色間切換。Public／Viewer 偏好只保存在該瀏覽器，不會讀取或持續同步 Admin 的正式使用者偏好或 Guest 的 session 記憶體偏好。只有使用者刻意進入 Admin／Guest 時，才可暫存明確 `light`／`dark` 提示，最長 120 秒；Worker 核對後把它放入已簽署 session 及 request-bound principal，建立 session 時清除暫存 cookie。目的地已有偏好時永遠不覆寫。
- 瀏覽器可能阻止未經互動的有聲播放；此時頁面會顯示「預設：開啟音樂」與「安靜繼續」，但兩者只是可選偏好／復原控制。未作選擇時，管理員或訪客按鈕本身會在該次可信按鍵／點擊內同步重試音樂，再只前往所選身份一次。播放成功、再次被拒、格式不支援、載入過久或傳輸中斷均不會阻擋登入；其他頁面操作也不會暗中開始播放。
- 人聲版本保留在登入後的每日經文／相關工作頁歌庫，避免在身份選擇時蓋過雙語操作指示。

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
- `/readyz`：storage health 正常、`workflowInitialized=true`、沒有 maintenance／恢復標記、沒有待完成備份義務且 startup repair 沒有失敗，才回報可寫；diagnostic-only 固定為 HTTP 503／`writeReady=false`，不能靠手動移除 marker 變成可寫。
- `/auth/status`：瀏覽器身份、到期、撤權及 origin 可達狀態。

若 Guest session 到期，畫面應清除臨時工作區並返回入口。若 Admin session 到期或撤權，下一次狀態核對、HTTP 請求或回調會被拒絕；未提交輸入不應被靜默寫入。

Cloudflare 暫時不可用時，只有維護者才使用 localhost 或已核准 WARP 後備；不要把維護地址當作第二個日常網站。

## 發布前核對

- [ ] 候選以隔離環境證明 `SING_YIN_UNIFIED_GUEST=0` 時 Guest fail closed；不得改動目前 live 設定作測試。
- [ ] `SING_YIN_UNIFIED_GUEST=1` 的隔離測試使用臨時 SQLite、備份及日誌路徑，並重新證明 Guest／Admin 邊界。
- [ ] Guest 與 Admin 每一正式路由有相同頁面骨架及清楚能力狀態。
- [ ] Guest adapter 不引用正式 SQLAlchemy、AI、HTTP、備份、上載、分享或背景工作。
- [ ] 兩個 Guest、同一 Guest 多分頁、登出、到期、撤權、程序重啟及交叉下載均通過。
- [ ] 同一分頁重新整理只還原最新合法 snapshot；複製分頁獲得新 workspace，篡改／過期／舊 boot token 安全回到 fixture。
- [ ] Guest PDF／JSON 標明 `DEMO`，使用 `no-store`，不含真實資料。
- [ ] `/view#…` 只接受已發布快照，草稿不能分享。
- [ ] 管理員登入／登出、長時間重連、上載、PDF 及完整寫入流程完成真人驗收。
- [ ] `/healthz` 及 `/readyz` 都通過後才開放寫入。
- [ ] rc20 的 mobile public root 在 320px／390px 首屏各只有一個 visible Admin 及 Guest CTA，至少 48px 高（設計 52px），位於 workflow／devotional 前；desktop access panel、路由及身份邊界不變。
- [ ] 兩個入口在 light／dark、reduced motion、forced colours、browser back 及 first-viewport checks 均通過，且沒有 console error／`pageerror`；只有最終 source-matched report 及已部署 Worker smoke 才可把它們標為 live。

## 問題回報／Support

公開入口及 Viewer 可開啟 `/support`，但報告只在目前瀏覽器建立。頁面不會
呼叫 origin、建立 WebSocket、寫入 Cookie／localStorage／IndexedDB，亦不會
把 Viewer fragment、週表內容或身份資料加入報告。使用者可下載 JSON、複製
已刪減摘要，或以預先填好的電郵草稿聯絡支援；離開頁面後網站不會保留內容。
完整分享連結仍是 bearer capability，不應貼入報告或公開 Issue。

The Public and Viewer support route builds a report entirely in the browser. It
does not upload, persist, or include a Viewer fragment or roster payload. The
user may download JSON, copy the redacted summary, or open a prefilled email.

## English quick guide

Historical rc30 origin (`v1.2.0-rc.30`, commit `74b84f43786b00feb15b51a6270ff71c9430773f`) passed all 14 formal gates with source fingerprint `15d155d8d745b14b574b08d793150c93aa77946e7d17a63030844c44adededbc`, including 894 Python tests, 3 motion contracts, and 46 Worker contracts, before the controlled Windows switch. Worker `11763f08-d40d-46d5-93dc-5ca2599d4154` passed zero-percent version smoke before promotion to 100%. Current rc39 production and rc35 origin／Worker rollback identifiers are recorded at the top of this document.

The current product contract uses one canonical site and one NiceGUI product. Public users choose either **Admin sign-in** or a time-limited **Guest experience**. Administrators use the official workflow and SQLite database; guests use a server-verified, memory-only adapter populated with fictional Chinese names. Each Guest tab stores only the latest signed, bound snapshot token in `sessionStorage`; restore also requires the current connection nonce, and copied, tampered, expired, stale, or old-boot tokens fail safely. UI hiding is not the security boundary: capabilities are checked again in callbacks, services, downloads, exports, storage, and sharing.

`/guest` and `/try` are compatibility redirects to the unified entry. `/view#…` remains a separate, encrypted, read-only published-roster link. The Service Weave editorial integration, rc27 audit remediations, and rc30 explicit language／appearance controls remain historical provenance; current production and rollback identifiers are recorded at the top of this document.

Admin and Guest share the same stable Assist. mode codes: `legacy_fixed_weekday` keeps the canonical AHP weekday, while `flexible_weekly` rotates only across selected available weekdays and avoids the previous week's day where feasible. Both enforce AHP-only eligibility, leave, same-day uniqueness, and no-consecutive-duty rules. Official rosters persist the selected mode; Guest rosters keep it only in the bounded in-memory workspace.
