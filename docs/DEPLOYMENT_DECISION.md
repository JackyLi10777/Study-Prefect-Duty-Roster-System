# 部署與遠端存取決策指南 / Deployment decision

> **線上來源真相（2026-07-31）：** clean annotated `v1.2.0-rc.43`／`c8201f33e454d9120c73386642cbf9d737391466` 正在 Windows origin 運行；canonical Worker `394e2205-ae8f-4eef-a13a-e701931e6f0d` 承接 100% 流量。rc43 已完成 15／15 gate、正式備份與隔離還原、受控 origin 部署、Worker 0% 指定版本 smoke、100% promotion 及 canonical health／entrance／Viewer 核對。第一層配對回退為 rc41／`74072b0175ff64807312a8cc5b9cd016b6628210` 與 Worker `610092f6-59d4-4fd4-ab3a-3fbf1dd2c64e`；rc40 與其 Worker 是第二層回退。rc42 與 rc43 同源但未綁定正式報告、未部署。真人驗收未完成。
>
> **歷史 rc30 乾淨發布證據：**受控 Windows origin 曾運行 `v1.2.0-rc.30`／`74b84f43786b00feb15b51a6270ff71c9430773f`；canonical Worker 是已驗證 version `11763f08-d40d-46d5-93dc-5ca2599d4154`。296 個 runtime 來源檔以 fingerprint `15d155d8d745b14b574b08d793150c93aa77946e7d17a63030844c44adededbc` 通過 14／14 release gate；切換前備份 `20260727-023041-069097-manual_verified_backup.sqlite3`／SHA-256 `6e2f44d2e577389d19de2feb5dd0a36260794ef2188551d6f604e46b7ac74e1b` 完成 checksum、公平對帳、行數核對、還原審計及隔離還原。Worker 通過 0% version smoke 後升至 100%；origin readiness 與 canonical rendered smoke 通過。當時的下一層 origin／edge 回退分別是 rc27／`c4c728aa…` 與 `d7b51f21…`；目前 rc43 production 及 rc41 第一層配對回退以本頁頂部記錄為準。Head Study Prefect／teacher-advisor 真人驗收仍待簽署。

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

## 目前已對帳的 runtime 與已驗證復原層級

| 層 | 現況 |
|---|---|
| Windows owned scheduled task | clean annotated `v1.2.0-rc.43`／`c8201f33e454d9120c73386642cbf9d737391466` immutable bundle；306-file runtime fingerprint `699dc436c69e02f3b9062a04500715929ba35f78f48e14a3d80a0ac33c18640b` 已對帳。Inactive `C:\SingYinRoster` Git HEAD 不代表 runtime。 |
| Cloudflare Worker／Access／Tunnel | canonical traffic 由受審 Worker `394e2205-ae8f-4eef-a13a-e701931e6f0d` 承接 100%；Access、Tunnel 與 OTP fail-closed 驗證已通過 |
| rc43 來源與部署證據 | 15／15 gate；受控 origin 切換、正式備份／隔離還原、0% Worker smoke、100% promotion 及 canonical health／entrance／Viewer checks 通過 |
| 第一個已驗證配對復原目標 | origin 使用 rc41 commit `74072b0175ff64807312a8cc5b9cd016b6628210`，edge 使用 Worker `610092f6-59d4-4fd4-ab3a-3fbf1dd2c64e`；不得任意單側回退 |
| 有條件單側回退 | 只有來源指紋、身份參數、路由契約及相容性 gate 證明未改動一側與目標相容時，事故負責人才可批准；不可把 gateway 回退誤寫成 origin 回退 |
| 更深歷史復原來源 | rc40／`2ec900a5` 與 Worker `2cb38b05…`，再到 rc39／rc35／rc30／rc27／rc26；只有較近乾淨來源無法安全恢復且事故負責人批准時使用 |
| `codex/frontend-guest-performance-rc16` | rc17 來源分支；14 項 gate、標籤、Windows bundle 及 Worker staged rollout 已完成 |
| `SING_YIN_UNIFIED_GUEST` | 正式環境的受保護設定必須為 `1`；後續候選不得以切換旗標取代完整驗證 |

rc4–rc29 或 v1.1 的既有 Worker version ID、主機 tag 及成功紀錄只屬歷史／更深層復原證據；它們不能代替目前 active pair 的來源歸屬，也不能代替任何新候選自己的來源指紋與部署證據。

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

1. 凍結候選、核對完整 report 與 fingerprint；候選必須先合併至 `main` 並建立新的獲批准 annotated tag；目前 rc43 origin／Worker 已對帳，任何新候選仍須產生自己的來源指紋及部署證據；
2. 建立並驗證正式備份，在另一隔離資料庫完成還原；
3. 進入短暫 maintenance；
4. 從該不可變 tag 更新 Windows bundle，執行 additive migration `0011_assist_assignment_mode`；
5. 保持現行受保護設定不變，核對 `/healthz` 及 `/readyz`；
6. 比較 Worker source／受保護設定；沒有改動時記錄沿用已驗證版本，有改動時才執行 staged Worker rollout；目前 edge 的立即回退是 `2cb38b05-6091-43be-86d3-d9f3ccae1ceb`，`d7069f99…`、rc34 的 `7816b183…` 與 rc30 的 `11763f08…` 只屬更早歷史；
7. 以虛構資料核對 Public、Admin、Guest、Viewer、PDF、登出、到期及多分頁隔離；
8. 完成真人驗收後才結束 maintenance 並宣布候選上線。

任何新候選 origin／線上 gate 失敗，先保存失敗證據，再回復 tagged `v1.2.0-rc.40`／commit `2ec900a5ef1c021183717dfa648ef76b55452ffb` 及 Worker `2cb38b05-6091-43be-86d3-d9f3ccae1ceb`；只有這個配對回退無法安全恢復且事故負責人批准時，才使用 rc39、rc35、rc34、rc30、rc27 或更早的已驗證基線。Additive migration 必須讓回退版本仍可讀原有資料。

逐步 Cloudflare 設定、staged rollout、驗收及回退命令見
[`CLOUDFLARE_REMOTE_ACCESS_SETUP.md`](CLOUDFLARE_REMOTE_ACCESS_SETUP.md)。

正式驗證命令：

```powershell
python -X utf8 -m pytest -q
python -X utf8 scripts\verify_release_candidate.py
```

## English summary

The selected topology remains one canonical Cloudflare Worker in front of one
loopback-only NiceGUI origin on a dedicated Windows host. The Windows machine
remains the sole system of record for SQLite, backups, logs, PDFs, and local
music. Current production identity is recorded in the document header and must
be re-observed after every rollout.

Historically, before the rc39 rollout, the active origin and Worker had periods
of provenance drift. Exact rc30 source passed its `15d155d8…` fingerprint gates
and completed the controlled origin switch, staged Worker smoke, 100% promotion,
and canonical Public／Guest／Admin handoff／Viewer checks. That evidence remains
historical. The immediate verified paired rollback is now rc41 commit
`74072b0175ff64807312a8cc5b9cd016b6628210` plus Worker
`610092f6-59d4-4fd4-ab3a-3fbf1dd2c64e`; rc40, rc39, rc35, rc34, rc30, rc27
and their older Workers are deeper history. Supervised human acceptance remains outstanding.
