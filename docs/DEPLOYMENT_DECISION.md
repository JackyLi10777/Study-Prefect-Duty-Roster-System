# 部署與遠端存取決策指南 / Deployment decision

<!-- SING_YIN_CURRENT_STATUS:START -->
> **已核實線上來源（2026-08-14）：** Windows origin 正運行 clean annotated `v1.2.0-rc.58`／`e90bb8fdb95ca874f668b5a7134853756471635f` 的不可變 bundle；319-file 指紋 `c57778ce438c1c23c824c444827db7eeb9166d20be3ba3e78f1bb1221fee5283` 通過 15／15 gate。SQLite 位於 Alembic `0014`；正式備份 `20260813-161554-736678-manual_verified_backup.sqlite3`／SHA-256 `0e0ee9cc9a592eeea66055e107c461e859f3ccec2791cb06f051e7078c3febc2`、隔離還原、health、`writeReady=true`、`maintenance=false`、`recoveryRequired=false` 及 `pendingBackups=0` 已核對。Worker 來源沒有改動，canonical Worker `7951ca55-ffda-4f16-b570-d37486311914` 維持 100% 流量且健康。`v1.2.0-rc.57` 只屬歷史來源，migration `0014` 後不可作 code-only rollback；須使用受控的相容資料庫還原。真人驗收仍為 `pending`，實體離線 BitLocker 復原演練仍為 `pending`。精確狀態及更新規則見[目前系統狀態](status/CURRENT_STATUS.md)。
<!-- SING_YIN_CURRENT_STATUS:END -->
>
> **歷史 rc30 乾淨發布證據：**受控 Windows origin 曾運行 `v1.2.0-rc.30`／`74b84f43786b00feb15b51a6270ff71c9430773f`；canonical Worker 是已驗證 version `11763f08-d40d-46d5-93dc-5ca2599d4154`。296 個 runtime 來源檔以 fingerprint `15d155d8d745b14b574b08d793150c93aa77946e7d17a63030844c44adededbc` 通過 14／14 release gate；切換前備份 `20260727-023041-069097-manual_verified_backup.sqlite3`／SHA-256 `6e2f44d2e577389d19de2feb5dd0a36260794ef2188551d6f604e46b7ac74e1b` 完成 checksum、公平對帳、行數核對、還原審計及隔離還原。Worker 通過 0% version smoke 後升至 100%；origin readiness 與 canonical rendered smoke 通過。當時的下一層 origin／edge 回退分別是 rc27／`c4c728aa…` 與 `d7b51f21…`；目前線上版本及 migration 後的受控復原限制以本頁頂部生成狀態為準。Head Study Prefect／teacher-advisor 真人驗收仍待簽署。

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
| Windows owned scheduled task | 精確 tag／commit／bundle／fingerprint 由頁首生成狀態及 `status/CURRENT_STATUS.md` 擁有。Inactive `C:\SingYinRoster` Git HEAD 不代表 runtime。 |
| Cloudflare Worker／Access／Tunnel | Worker 來源已更新，經 0% version smoke 後推廣至新的 100% canonical version；`wrangler.jsonc`、Access scope、Tunnel route、binding 與 secret-name contract 未更改，OTP fail-closed 及 gateway health 已重新核對 |
| 目前來源與部署證據 | 精確 tag、gate、migration、正式備份／隔離還原及 canonical checks 只由頁首生成狀態與 [`status/CURRENT_STATUS.md`](status/CURRENT_STATUS.md) 擁有 |
| 第一個已驗證復原目標 | 保留目前程式並使用 [`status/CURRENT_STATUS.md`](status/CURRENT_STATUS.md) 記錄的已驗證正式備份進行受控還原；先在隔離資料庫核對 checksum、公平、行數及 restore audit |
| 舊程式相容復原 | migration `0013` 後，rc51 及所有較舊程式不得作 code-only rollback；必須先選取與目標程式相容的已驗證快照並完成受控隔離還原，再由事故負責人批准切換 |
| 更深歷史復原來源 | rc43／rc41／rc40／rc39／rc35／rc30／rc27／rc26 及其 Worker 只屬歷史來源；只有頁首所列的原地復原不能安全恢復且事故負責人批准時使用 |
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

1. 凍結候選、核對完整 report 與 fingerprint；候選必須先合併至 `main` 並建立新的獲批准 annotated tag；目前線上 origin、Alembic head 與 gateway 以本頁頂部生成狀態為準，任何新候選仍須產生自己的來源指紋及部署證據；
2. 建立並驗證正式備份，在另一隔離資料庫完成還原；
3. 進入短暫 maintenance；
4. 從該不可變 tag 更新 Windows bundle，執行候選所需的 additive migration；目前 schema head 以本頁頂部生成狀態為準；
5. 保持現行受保護設定不變，核對 `/healthz` 及 `/readyz`；
6. 比較 Worker source／受保護設定；沒有改動時記錄沿用已驗證版本並重新核對 gateway health，有改動時才執行 staged Worker rollout；Worker 與 origin 的復原必須各自有來源及相容性證據，不得把歷史 Worker 版本當作目前 migration 後的直接程式回退；
7. 以虛構資料核對 Public、Admin、Guest、Viewer、PDF、登出、到期及多分頁隔離；
8. 完成真人驗收後才結束 maintenance 並宣布候選上線。

任何新候選 origin／線上 gate 失敗，先保存失敗證據，再把資料庫還原至切換前已捕獲、已驗證且與舊 task target 相容的快照；只有資料庫 checksum、schema、integrity 與 ACL 證明通過後，才恢復並啟動舊 task target。若事故需要回復至 rc51 或更舊程式，必須先停止正式寫入，選取相容快照，完成 checksum、公平、行數、restore-audit 及隔離還原，再由事故負責人批准程式及必要的 Worker 切換。不得把任何舊程式當作 code-only rollback，也不得假設 additive migration 自動保證舊程式可讀新 schema。

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
historical. Current release, migration, gateway, and backup identity are generated
at the top of this guide. The first recovery path keeps the current application
and restores the verified backup named there under the controlled procedure.
Rc51 and every older application require a database snapshot compatible with
that exact application and are not code-only rollback targets. Supervised human acceptance
remains outstanding.
