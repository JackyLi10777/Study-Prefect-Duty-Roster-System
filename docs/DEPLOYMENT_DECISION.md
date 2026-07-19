# 部署與遠端存取決策指南 / Deployment decision

> **目前基線（live rc11）：** 受控 Windows origin 正運行 `v1.2.0-rc.11`／`7aff468`；canonical Worker 正運行已驗證 version `1cba4784-e265-4d87-a04d-5759b79a7530`。正式備份、隔離還原、13 項 release gate 及 staged Worker rollout 均已完成；Head Study Prefect／teacher-advisor 真人驗收仍待簽署。rc9 主機／Worker 組合只作已記錄回退基線。

## 結論

正式架構維持：

```text
一個 canonical workers.dev 網址
        │
        ▼
Cloudflare Worker：入口、身份交接、簽署 principal、Viewer
        │
        ▼
Workers VPC + 具名 Tunnel
        │
        ▼
Windows 11 專用主機：單一 NiceGUI origin
        │
        ▼
本機 SQLite／備份／日誌／PDF／音樂
```

目前不把正式資料搬到 Vercel、Supabase、GitHub Pages 或其他靜態主機。NiceGUI 需要長時間 Python 程序、WebSocket、可寫 SQLite、受控備份及還原；Windows 主機仍是唯一 system of record。真正遷移到受管 VM／容器及 PostgreSQL 是另一個 L3 決定。

NiceGUI 正式 origin 固定為 `127.0.0.1:8080`。Windows SSH 維護服務另行固定於 `127.0.0.1:22` 及 `[::1]:22`，只接受 Ed25519 金鑰，不開放 LAN、公網、防火牆入站規則或路由器轉發；日後校外 SSH 只能經獨立的 Cloudflare 私有路由進入。

## Live rc11 基線與回退組合

| 層 | 現況 |
|---|---|
| `C:\SingYinRoster` | live `v1.2.0-rc.11`／`7aff468`；健康、ready、loopback-only |
| Cloudflare Worker／Access／Tunnel | Worker `1cba4784-e265-4d87-a04d-5759b79a7530` live；Access 精確保護 `/auth/login`；Tunnel／VPC 連到單一 origin |
| `codex/service-weave-v1-2-editorial` | rc11 來源分支；13 項 gate、標籤、Windows bundle 及 Worker staged rollout 已完成 |
| `SING_YIN_UNIFIED_GUEST` | live rc11 的受保護主機設定為 `1`；後續候選不得以切換旗標取代完整驗證 |

rc4–rc9 或 v1.1 的既有 Worker version ID、主機 tag 及成功紀錄只屬歷史／回退證據；它們不可代替 rc11 或後續候選自己的來源指紋與發布證據。

既有 **私有 Cloudflare Tunnel + WARP** 路徑仍保留作維護後備。
交接時要保留並重新核對 **WARP device-enrollment policy**。其歷史狀態
「**主機連接器健康；待真人遠端裝置驗收**」只代表後備傳輸，不代表
v1.2 正式驗收完成。**Access app destination 只可是 `/auth/login`**；
`/auth/admin/start`、Guest start、status 及 logout 必須由 Worker 公開接收，
v1.2 的**應用內權限**由簽署 `PageContext` 決定，
**沒有管理員前綴或第二網站**。

## 一個網址，四種應用身份

- `PUBLIC`：品牌入口，不具應用能力。
- `GUEST`：同一 NiceGUI 產品及虛構資料工作區，不寫正式資料。
- `ADMIN`：Cloudflare Access 驗證後的正式工作台。
- `LOCAL_MAINTENANCE`：只供 Windows 主機受控維護。

`/view#…` 是獨立唯讀 Viewer 能力連結。它不等於 Guest session，也不能成為管理員身份。

v1.2 不再把 `/guest`、`/try` 維護成另一套靜態產品；兩者只作兼容重定向。詳細安全契約見 [統一訪客模式安全模型](UNIFIED_GUEST_SECURITY_MODEL.md)。

## 身份交接

管理員：

1. `/auth/admin/start` 進入 Cloudflare Access。
2. Access policy 以 exact-email 及 One-time PIN 核實身份。
3. Worker 驗證 Access JWT 並建立有限期管理 session。
4. Worker 移除瀏覽器身份標頭，向 origin 注入 HMAC 簽署 principal。
5. NiceGUI 核對簽章、`mode`、`sid`、到期、`auth_epoch` 及 `kid`。

訪客：

1. `POST /auth/guest/start` 建立最長 30 分鐘 Guest session。
2. Worker 向 origin 注入簽署 Guest principal。
3. NiceGUI 只在 `SING_YIN_UNIFIED_GUEST=1` 時建立記憶體工作區。
4. `/auth/status`、每次寫入回調及 WebSocket 生命週期重新核對到期與能力。

系統不保存管理員密碼。Worker secret、Access token、cookie、Tunnel token、API token及 HMAC key 不可進入 Git、文件、截圖、日誌或備份。

## 資料及並行邊界

- 只支援一部 Windows 主機、一個 NiceGUI origin、多使用者／多分頁。
- SQLite 版本不宣稱支援多個 NiceGUI origin。
- 第二個 origin 程序在 migration 前由資料庫絕對路徑鎖阻止。
- 正式互動寫入使用 `expected_version`、命令收據及冪等重播。
- 提交交易同時建立 `backup_obligations`；未完成義務在啟動時修復，失敗則 `/readyz` degraded 並阻止新寫入。
- 外部分享使用 durable outbox，綁定值班表版本及 digest；不以「HTTP 回應遺失」當作可以盲目重建分享的理由。
- Guest adapter 不接觸正式 SQLite、備份、外部整合或背景工作。
- Guest 最新 revision 只以簽署 token 存入該分頁 `sessionStorage`；還原要重新核對 live nonce、session／workspace／tab／boot／revision，複製或無效 token 不能跨工作區重播。

## 為甚麼保留 Windows 主機

優點：

- 現有 NiceGUI、SQLite、ReportLab、音樂及備份可直接運行；
- 日常資料與復原點仍在可控制的本機；
- 不需立即重寫成無狀態雲端服務；
- 現有工作排程器、ACL、loopback origin 及 Tunnel 流程可沿用。

代價：

- 主機斷電、Windows 更新、網絡或硬碟故障會影響可用性；
- 必須完成開機自啟、健康監察、已驗證備份及隔離還原；
- 不能水平擴展多個 origin；
- 遠端可用性仍依賴 Cloudflare、家中網絡及主機運作。

## 不採用的方案

- **Quick Tunnel：** 只供短暫測試，沒有固定身份、版本、復原及交接契約。
- **直接開放路由器連接埠：** 不採用；NiceGUI origin 必須保持 loopback。
- **Vercel／GitHub Pages：** 靜態／短生命週期執行模型不能直接承載目前的 NiceGUI、SQLite、WebSocket 及備份。
- **把真實資料、備份或日誌當作 Git 儲存：** 不採用；Git 是程式和非敏感可重建資產的版本庫，不是運行資料庫或災難復原系統。
- **多個 NiceGUI origin 共用 SQLite：** 不支援。

## 正式切換程序

只有完整 release report 與來源 fingerprint 一致時，才可：

1. 凍結候選、核對完整 report 與 fingerprint，再把 exact commit 合併至 `main` 並建立 `<next-approved-annotated-tag>`；
2. 建立並驗證正式備份，在另一隔離資料庫完成還原；
3. 進入短暫 maintenance；
4. 從該不可變 tag 更新 Windows bundle，執行 additive migration；
5. 保持現行受保護設定不變，核對 `/healthz` 及 `/readyz`；
6. 只有 Worker source 或受保護設定確實改變時才部署對應 Worker，否則記錄沿用的 verified version ID；
7. 以虛構資料核對 Public、Admin、Guest、Viewer、PDF、登出、到期及多分頁隔離；
8. 完成真人驗收後才結束 maintenance 並宣布候選上線。

任何 gate 失敗，回復 rc9／`18a5c73` 主機 bundle 及 Worker `b13e5721-d1e8-4048-9885-ffb422fe2010`；additive migration 必須讓舊版本仍可讀原有資料。

逐步 Cloudflare 設定、staged rollout、驗收及回退命令見
[`CLOUDFLARE_REMOTE_ACCESS_SETUP.md`](CLOUDFLARE_REMOTE_ACCESS_SETUP.md)。

正式驗證命令：

```powershell
python -X utf8 -m pytest -q
python -X utf8 scripts\verify_release_candidate.py
```

## English summary

The selected topology remains one canonical Cloudflare Worker in front of one loopback-only NiceGUI origin on a dedicated Windows host. The Windows machine remains the sole system of record for SQLite, backups, logs, PDFs, and local music. Live `v1.2.0-rc.11`／`7aff468` unifies administrator and guest pages through a signed `PageContext`; guest data stays in a bounded in-memory adapter. The verified Worker is `1cba4784-e265-4d87-a04d-5759b79a7530`.

Service Weave rc11 is the deployed release candidate, while supervised human acceptance remains outstanding. Every later candidate requires its own verified source fingerprint, `<next-approved-annotated-tag>`, fresh backup, isolated restore, additive migration, `/healthz` and `/readyz`, complete automated evidence, controlled origin／Worker decision, and supervised browser acceptance.
