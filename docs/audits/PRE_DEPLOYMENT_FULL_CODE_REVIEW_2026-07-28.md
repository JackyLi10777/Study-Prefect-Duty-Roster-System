# rc31 預部署全碼審查報告（草稿）

> **狀態：BLOCKED（候選尚未凍結）**
> 本文件記錄 2026-07-28 的最終候選審查進度。它不是部署完成聲明，也不以通過測試、HTTP 200 或健康檢查取代部署證據。只有在候選來源凍結、完整清單分類、所有必要閘門通過、發布標籤與受審樹一致後，方可改為 `PASS`。

## 1. 審查身份與發布事實

| 項目 | 草稿時證據 | 最終值 |
| --- | --- | --- |
| 審查日期 | 2026-07-28（Asia/Shanghai） | 2026-07-28 |
| 候選分支 | `codex/rc31-unified-theme-controls` | 待凍結確認 |
| 草稿建立時 base HEAD | `a3c45bae48ef99b3972790c7c0f5df8453a0dd19` | 不可當作最終候選 SHA |
| 草稿建立時 base tree | `3838f9b70d6aec2481325e07683c850c8829e8be` | 不可當作最終候選 tree |
| 最終候選 commit SHA | 未建立 | `TBD_FINAL_COMMIT_SHA` |
| 最終候選 Git tree SHA | 未建立 | `TBD_FINAL_TREE_SHA` |
| 發布標籤 | 未建立 | `TBD_RELEASE_TAG` |
| source fingerprint | 未從凍結來源產生 | `TBD_SOURCE_FINGERPRINT` |
| `requirements.lock` SHA-256 | `8b1961717c9941c3a35813c1141bbf8364fe7fbc95017200e6e933da6997b2de` | 凍結後重核 |
| `requirements-dev.lock` SHA-256 | `f21c14b128abfddc8206b59dbccb97252d820f617261f1199b844e7eb7a583f1` | 凍結後重核 |
| 追蹤檔案 | 568 | 凍結後重核 |
| 草稿時已修改追蹤檔案 | 62 | 最終 commit 應為乾淨工作樹 |
| 待納入聚焦測試 | `tests/test_roster_generator_integrity.py` | 必須明確 stage／review |
| 明確排除的本機證據 | `test-results/unified-access-gateway/public-support-browser-only.png`（非本候選來源） | 保持 untracked，不可誤納發布 |

### 目前線上狀態與最近乾淨基線

- **實際 Windows origin（2026-07-28）：**Git 仍指向 rc30 commit `74b84f43786b00feb15b51a6270ff71c9430773f`，但工作樹已有 73 個追蹤修改及 3 個未追蹤項目；當中 40 個追蹤檔與目前 rc31 候選相同、33 個不同。正在執行的程序於漂移後啟動，因此這個 origin 只可稱為「運作中但來源未對帳」，不可稱為 exact rc30、不可變 bundle 或 fingerprint-matched runtime。
- **實際 canonical Worker（2026-07-28）：**未標記、來源未歸屬的 version `a2e3ad14-d191-4ffc-85e4-eda40e42e5ed` 承接流量；不能由 HTTP 200 或頁面外觀推定其受審來源。
- **最近完整驗證的乾淨組合：**rc30／`74b84f43786b00feb15b51a6270ff71c9430773f` 配 Worker `11763f08-d40d-46d5-93dc-5ca2599d4154`。它是歷史乾淨基線，不是目前線上來源一致性證明；`11763f08-d40d-46d5-93dc-5ca2599d4154` 亦是目前最近一個已知、已驗證的 edge 回退版本。
- **更早回退歷史：**rc27 是已驗證 origin 回退來源；Worker `d7b51f21-7692-418d-866c-034c2c57292d` 是更早的 edge 歷史，而不是目前立即回退版本。
- **rc31：**只屬本機候選，尚未建立正式 commit／tag、尚未部署、尚未完成人工驗收。
- **人工驗收：**首席導學風紀及教師顧問的 supervised acceptance 仍未完成；任何自動化結果均不可代替此步驟。

## 2. 完整檔案清單與分類

以下分類由 `git ls-files` 的 568 個追蹤路徑建立，分類總和等於追蹤檔案總數。最終凍結後須再次產生相同清單；新增、刪除或改名會令本表失效。

| 分類 | 檔案數 | 審查／驗證方法 | 草稿狀態 |
| --- | ---: | --- | --- |
| NiceGUI、domain packages 及 root Python application | 177 | 變更差異人工審查；Python unit／integration；正式 release verifier | 差異審查完成；凍結來源重核待辦 |
| Alembic／資料庫 migrations | 12 | 人工審查 upgrade／downgrade、logger、schema 相容；migration tests | 差異審查完成；凍結來源重核待辦 |
| Cloudflare Worker／gateway | 13 | 人工審查身份、cookie、header、代理和下載；Deno Worker contracts | 差異審查完成；正式瀏覽器接力待辦 |
| Tests 及 fixtures | 100 | 測試意圖、隔離資料、斷言與假陽性審查；pytest | 已執行工作樹套件；未追蹤 generator test 待納入 |
| Verification、build、deployment 及 root launch scripts | 51 | 人工審查命令、失敗邊界、配置 parity；PowerShell／release tests | 差異審查完成；正式 release gate 待辦 |
| 操作、架構、安全、設計與交接文件 | 42 | 命令／路由／環境變數／發布敘述與實作對照；documentation tests | 已更新目前事實；最終 SHA／部署證據待填 |
| CI、環境 schema、manifest 及配置 | 13 | schema／required keys／protected-branch／hygiene checks | 凍結來源閘門待辦 |
| 圖片、字體、音樂、資料、archive、test evidence | 157 | provenance、路徑、大小、digest、授權及 repository-hygiene controls；不作無意義逐行審查 | 最終 integrity／hygiene 待辦 |
| Dependency locks | 2 | SHA-256、可重現安裝、dependency／vulnerability scan | 草稿 hash 已記錄；正式 scan 待辦 |
| `LICENSE` | 1 | 法律文本存在性及發行一致性 | 不涉及行為變更 |
| **總計** | **568** |  | **最終逐檔分類 ledger 尚待凍結後確認** |

### 明確排除與理由

- `.git`、virtualenv、Python／browser caches、臨時 SQLite、臨時備份、臨時日誌及本機下載不屬 `git ls-files`，不構成候選來源。
- 二進位媒體、字體及 release evidence 不作虛假的「逐行人工審查」；它們以 provenance、digest、大小、格式、dependency／licence 及 repository-hygiene controls 驗證。
- 上述 untracked screenshot 是另一個瀏覽器流程的本機證據，不是 rc31 產品來源，故明確排除。
- `demo_code`／`demo_code2` 只可作歷史參考，不是正式 NiceGUI runtime 的功能來源。

## 3. 變更審查結論

### 3.1 已確認並修復的 P1

| ID | 問題、根因及受影響表面 | 修復及重審證據 | 狀態 |
| --- | --- | --- | --- |
| RC31-P1-001 | Public 入口和 Admin／Guest 工作台的主題狀態曾各自擁有不同循環；使用者未設定時無法可靠表達「跟隨系統」，跨身份進入亦沒有受信任的限時接力。受影響：Public、Admin、Guest、桌面及手機。 | `cloudflare/roster_viewer/worker.js:1831-2018,2923-3640` 將未設定狀態解析為 system、第一次點擊選擇相反的 explicit theme，並以 120 秒 Secure／SameSite=Lax staging cookie 接力；`nicegui_app/gateway_identity.py:141-181` 驗證簽署 principal；`nicegui_app/ui/theme.py:34-108` 只在目的工作區沒有既有偏好時採納；`nicegui_app/ui/shell.py:521-684,1008-1193` 統一控制器和清理。Unit／Worker contract 及 16 組真實 Public→Admin／Guest rendered continuity 情境已通過。 | **已修復並取得本機瀏覽器證據；正式凍結來源及部署後證據待辦** |
| RC31-P1-002 | 下載 registry 容量不足時，UI helper 曾可能吞掉失敗，令呼叫端發出成功提示；使用者實際沒有取得 PDF／JSON。根因是交付函式沒有可檢查的結果。 | `nicegui_app/ui/downloads.py:38-119` 現回傳 success boolean 並保留支援編號；所有受影響呼叫端只在 `True` 時報告成功；`tests/test_guest_downloads.py` 覆蓋拒絕、容量、單次票證、模式及清理。 | **已修復** |
| RC31-P1-003 | diagnostic-only 啟動在 recovery marker 被外部移除後可能把 `/readyz` 誤報為可寫，即使 workflow sessions 從未初始化。 | `nicegui_app/runtime.py:678-681` 增加 `workflowInitialized` 作寫入必要條件；`tests/test_runtime_readiness.py:8-22` 驗證 marker 消失亦不能令未初始化程序變為 ready。 | **已修復** |
| RC31-P1-004 | 兩個 origin 程序在 startup probe 與 migration 之間存在 TOCTOU 窗口；第二程序可能在第一程序尚未完成初始化時進入共享 SQLite。 | `nicegui_app/services/roster_workflow.py:138-154` 在 probe 至 migration／bootstrap 期間持有資料庫路徑級 lifecycle lease；workflow write fencing 與初始化前拒絕維持第二層保護。 | **已修復** |
| RC31-P1-005 | 恢復流程若重新讀取已變動的來源檔、接受 SQLite WAL／SHM sidecar，或把 database 與 manifest 拆開驗證，可能恢復非同一證據對。 | `nicegui_app/services/workflow_parts/recovery.py:136-147,369-473,668-698` 以 exact staged bytes／成對 manifest 處理、拒絕 sidecars、驗證 rollback；`tests/test_backup_restore.py:229-333` 覆蓋來源突變及 sidecar。 | **已修復** |
| RC31-P1-006 | 正式主機 checkout 與 canonical Worker 均已偏離最近受審 pair；主機有 73 個追蹤修改及 3 個未追蹤項目，Worker `a2e3ad14-d191-4ffc-85e4-eda40e42e5ed` 沒有可核實標籤／來源。受影響：部署歸屬、回退、事故判斷、文件及任何「目前已上線版本」聲明。 | 已完成唯讀差異盤點並修正文檔，不重設、不覆寫正式主機。必須先凍結 rc31 exact source、通過完整閘門，再由受控 clean-bundle 部署重建 origin／Worker 一致性；部署後以 tag、tree、fingerprint、Worker version 和 rendered checks 對帳。 | **OPEN — deployment blocker** |

### 3.2 已確認並修復的 release-relevant P2

| ID | 問題、影響及證據 | 修復 | 狀態 |
| --- | --- | --- | --- |
| RC31-P2-001 | Admin／handover 曾錯誤繼承 Guest 的 5 MiB 下載上限，會令合法交接包在正式工作區失敗。 | `nicegui_app/services/guest_downloads.py:16-128` 改為 Guest 5 MiB、Admin 64 MiB、registry 128 MiB，並保留 Admin 64 MiB／16 tickets 的容量；相應文件和測試同步。 | **已修復** |
| RC31-P2-002 | 架構、快速開始、訪客安全和交接文件仍有靜態 Guest、舊下載限制或錯誤環境變數敘述，可能令下一任操作者作出錯誤設定。 | README、`docs/NICEGUI_ARCHITECTURE.md`、`docs/QUICKSTART.md`、`docs/RELEASE_HANDOVER.md`、`docs/SECURITY_AND_PRIVACY.md`、`docs/UNIFIED_GUEST_SECURITY_MODEL.md`、`docs/PUBLIC_ROSTER_VIEWER.md` 已對照現行實作更新；documentation contract 38 項通過。 | **已修復** |
| RC31-P2-003 | 早期 Chromium harness 只驗證 Admin／Guest 直接 origin，未穿過 Public 入口、真實身份按鈕、Worker principal 和目的工作台。 | `scripts/verify_rc31_theme_controls.py` 現由實際 Public 控制及 Admin／Guest 入口開始，核對 bounded explicit hint、signed session／request-bound principal、session mint、staging-cookie 清除、既有目的偏好優先、WebSocket callback、重新整理及跨路由持續性；OS Light／Dark、桌面／手機、reduced motion／forced colours 共 16 個情境通過。 | **已修復並取得 rendered evidence** |
| RC31-P2-004 | Windows 部署器原先在檢查已安裝主機 Git 是否乾淨之前，便套用並刪除一次性環境 overlay；雖然會安全中止服務切換，但操作者要重建敏感設定檔。 | `scripts/deploy_windows_release.ps1` 把 host cleanliness／previous commit 檢查移到讀取或消耗 overlay 之前；`tests/test_windows_release_deployment_script.py` 鎖定 host-clean → preflight → protect／merge／consume → stop 的順序。 | **已修復** |

### 3.3 P0、其他 P1、P3

- 目前差異審查未發現 P0。
- `RC31-P1-006` 是已確認而未解除的部署歸屬／回退風險；在 clean pair 受控重建前仍然阻擋發布。其他已檢視差異暫未發現未修 P1，但這不代替 final inventory 與 exact-source gate。
- 未記錄純風格、檔案行數或「可以再抽象」為缺陷；只有會影響正確性、安全、恢復、操作或交接的事項才進入發布判斷。

## 4. 正向更新、被調整方案及拒絕理由

### 保留的正向更新

- **主題契約：**未設定跟隨 OS；第一次互動選擇與目前解析結果相反的 explicit theme；其後只在 Light／Dark 間切換。Public 入口只暫存經 Worker 驗證、限時 120 秒且不承載身份的 `light`／`dark` 提示；Worker 只在刻意進入 Admin／Guest 時把它放進簽署 session 及 request-bound principal，建立 session 後清除暫存 cookie。目的工作區只在偏好未設定時採納；既有偏好永遠優先。
- **排班完整性：**regular-prefect solver 使用 deterministic matching、complete backtracking 及剩餘日可匹配剪枝，最後仍由嚴格 assignment coverage／weight validation 把關；不以貪心「能產出部分結果」冒充完整週表。
- **有界下載：**Guest、Admin 及 registry 有不同且合理的容量；ticket、session、access mode、expiry、filename 及 no-store 均在服務層驗證。
- **資料恢復：**備份、restore 和 handover 使用同一 staged database／manifest pair，拒絕含 sidecar 的非自足 SQLite snapshot，失敗時核對 rollback。
- **啟動與寫入：**資料庫路徑級 process lease、maintenance／recovery admission 及 transaction fencing 分層，避免只靠 UI 按鈕作安全邊界。
- **部署 parity：**`scripts/deploy_windows_release.ps1:227-479` 以嚴格 JSONC 解析取得 Worker 設定，並在停止服務前及套用後比較 `SING_YIN_PORT`、`AUTH_EPOCH`、`ORIGIN_PRINCIPAL_KID`。
- **日誌相容：**`migrations/env.py:15` 不再由 Alembic 停用既有應用 logger，保留支援編號和事故追查鏈。

### 經批判性審查後調整／拒絕

- 拒絕把「System／Light／Dark」藏成三段循環；它令按鈕下一步不可預測。System 現只作首次未設定狀態，直接互動後進入清楚的二元選擇。
- 拒絕讓 Admin 共用 Guest 5 MiB 上限；限制需要按風險模式而不是按共用程式碼方便程度決定。
- 拒絕因 recovery marker 消失便宣稱 write-ready；只有成功建立 sessions 的 workflow 才能報告可寫。
- 拒絕在下載 registry 寫入失敗後顯示「成功」；UI 必須依服務結果決定提示。
- 拒絕把 unit tests、HTTP 200、`/healthz` 或 release-gate PASS 描述成已部署或已完成人工驗收。
- 拒絕把另一工作樹的 screenshot、cache 或臨時資料納入 rc31 來源。

## 5. 安全、效能、依賴及可維護性審查

### 安全與私隱

- Theme handoff 值域只允許 `light | dark`，不承載姓名、值班、請假或其他內容；Worker 在 identity 建立後清除 staging cookie，origin 只接受簽署 principal。
- Guest download 仍以 access mode＋session 綁定、單次票證、expiry、大小上限及 `Cache-Control: no-store` 處理；Admin 提高上限沒有取消相同的模式及 session 檢查。
- Recovery 接受的 snapshot 必須自足並與 manifest 相符；WAL／SHM／journal 會使驗證關閉而不是被默默忽略。
- Deployment parser 不執行 `wrangler.jsonc`，只解析和驗證允許的配置；host／Worker identity epoch、key id 及 port 不一致時在 service stop 前中止。
- 目前可變來源已通過 dependency audit、靜態分析、secret scan 及 48 項 Worker route contract；這些結果只證明當前工作樹。**待完成：**凍結來源後重跑 security／secret／dependency／repository-hygiene／configuration-mismatch gate，以及把來源漂移的 origin／Worker 對帳為同一受審 pair。

### 效能與抗壓力

- 新 solver 的 complete backtracking 在理論最壞情況仍可能呈指數增長；目前以候選排序、每日 bipartite matching 剪枝及此系統受限的五日／固定房間規模控制。`tests/test_roster_generator_integrity.py` 必須納入候選並提供完整性及界限證據，不能只量測成功案例。
- Download registry 有總記憶體、各模式檔案大小、tickets 及 Admin reserve 的硬上限，不形成無界記憶體隊列。
- Theme runtime 的 media／BroadcastChannel／DOM listeners 有 route cleanup；16 組 Public→Admin／Guest rendered 情境已核對入口接力、重新整理、跨路由、reduced motion 及 forced colours。完整 frozen-source release gate 仍須重跑長循環 listener／DOM／heap 證據。
- Restore／backup 是刻意的 maintenance-path I/O，不在互動 request 中偽裝成非阻塞操作；正式 release 須再驗證 partial-failure recovery。

### 依賴及 API 契約

- 本差異沒有新增第三方 runtime dependency；兩個 lockfile 在草稿時保持上述 digest。
- 新 browser evidence 沿用既有 Playwright／Deno／NiceGUI 工具鏈，不引入第二套 frontend 或動畫 runtime。
- NiceGUI、SQLAlchemy、Alembic、Deno Worker 及 PowerShell API 必須在凍結後由 lock／installed-version checks 和正式 release verifier 再核對；本報告不以 import success 作 API 相容證據。

### 架構及知識轉移

- UI 只處理控制狀態和呈現；身份由 Worker principal／`PageContext` 驗證，下載由 generated-file delivery service 管理，排班規則保留在 `roster_core`，恢復及公平交易保留在 workflow 層。
- 非直觀 invariant 已在程式和操作文件記錄：目的偏好優先於 entrance handoff、diagnostic-only 不可轉為 writable、備份 database／manifest 不可拆對、shared registry 必須預留 Admin 容量。
- rc31 文件現把未凍結候選、來源漂移的現行 runtime、最近乾淨 rc30 pair、rollback 及 supervised acceptance 分開；最終 commit／tag／部署後仍須再次同步。

## 6. 已取得的驗證證據（非最終凍結來源）

| 檢查 | 工作樹結果 | 限制 |
| --- | --- | --- |
| 聚焦 theme／gateway／runtime／download suite | 61 passed | 不是 final frozen source |
| 擴展 changed-unit set | 154 passed | 不是完整 release gate |
| 完整 `python -X utf8 -m pytest -q` | exit 0 | 在可變工作樹執行；候選凍結後必須重跑 |
| `deno test cloudflare/roster_viewer/worker_gateway_test.js` | 48 passed | 不代替真實瀏覽器／部署 |
| `scripts/verify_rc31_theme_controls.py` | 16 cases passed | 包含 Public→Admin／Guest 真實入口、簽署接力、目的工作區採納／優先、路由及伺服器 callback；仍不是部署後 canonical evidence |
| `python -X utf8 scripts/run_security_checks.py` | PASS（dependency audit、static analysis、secret scan） | 在可變工作樹執行；凍結後重跑 |
| `python -X utf8 -m pytest -q tests/test_documentation.py` | 38 passed | 鎖定目前來源漂移、乾淨回退 pair 及候選／部署分界 |
| `python -X utf8 -m compileall -q nicegui_app packages tests scripts` | exit 0 | 語法／bytecode 檢查，不代替行為驗證 |
| `git diff --check` | 沒有 whitespace error；只有既有 Windows LF→CRLF 提示 | 凍結後重跑 |

已保存的完整 theme browser 證據：`C:\Users\lichu\AppData\Local\Temp\sing-yin-rc31-theme-6qq8xuk3\verification.json`。此臨時路徑只記錄本機驗證，不應進入 product repository 或被描述為正式部署證據。

## 7. PASS 前仍需完成

1. 明確 stage `tests/test_roster_generator_integrity.py`，明確排除 untracked screenshot；凍結候選 commit。
2. 由 final `git ls-files` 重新產生逐檔分類 ledger，確認沒有 unreadable、unclassified 或 silently skipped 路徑。
3. 從凍結來源執行 focused checks、完整 pytest、Worker contracts、security／secret／dependency／hygiene、Admin／Guest isolation、backup／checksum／isolated restore、deployment-script 及 browser matrix。
4. 執行 `python -X utf8 scripts/verify_update.py --release`，保存正式 report、source fingerprint、file inventory 及 dependency hashes。
5. 把以下欄位填為實際值，並確認 release tag tree 與受審 tree 完全相同：
   - `TBD_FINAL_COMMIT_SHA`
   - `TBD_FINAL_TREE_SHA`
   - `TBD_SOURCE_FINGERPRINT`
   - `TBD_RELEASE_TAG`
   - `TBD_FORMAL_GATE_REPORT`
6. 只有上述項目全部通過、零 unresolved P0／P1／release-critical P2，方可把本報告 verdict 改為 `PASS`。
7. PASS 後才可建立／推送正式 tag，並在保留目前主機差異證據後以 clean reviewed bundle 對帳 Windows origin、部署／推廣 Worker。部署後再填：
   - origin commit／tag／source fingerprint；
   - Worker version 及 traffic；
   - canonical URL、`/healthz`、`/readyz`、Admin／Guest／Viewer rendered checks；
   - verified backup、isolated restore、origin／Worker rollback target；
   - SSH／UAC 實際結果；
   - supervised human acceptance 狀態。

## 8. 目前判決

**BLOCKED**

原因：最終候選仍是 dirty working tree，完整逐檔分類尚未對 final commit 凍結；正式 `--release`、tag/tree/fingerprint parity、備份／隔離還原及 canonical deployment evidence 亦未完成。更重要的是 `RC31-P1-006`：目前 Windows origin 與 Worker 均有來源漂移，必須由通過審查的 clean pair 受控重建一致性後才能解除。

因此目前：

- **不允許**建立或推廣 production release tag；
- **不允許**更新 `C:\SingYinRoster`；
- **不允許**上傳或推廣 Cloudflare Worker；
- **不允許**把 rc31 寫成已上線；
- 現有服務保持運作，但只可稱為「來源未對帳的線上 runtime」；不得把它寫成 exact rc30、rc31 或任何已審 fingerprint。最近完整驗證的乾淨 pair 只作回退及比較基線。
