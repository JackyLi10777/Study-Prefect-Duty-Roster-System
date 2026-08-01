# 正式驗收證據矩陣 / Acceptance evidence matrix

## rc45 正式機器與線上證據（真人驗收仍待完成）

- 合成 SQLite 規模驗證涵蓋 24／52、240／520、2,400／5,200 人／週層級；查詢計劃、statement count、p50／p95、記憶體、DB／WAL 大小及備份時間保存在 `docs/audits/rc44-sqlite-scale.json`。
<!-- SING_YIN_CURRENT_STATUS:START -->
> **已核實線上來源（2026-08-01）：** Windows origin 正運行 clean annotated `v1.2.0-rc.45`／`90777345ea9ed5652c73873edb3c8c846a9ceac5` 的不可變 bundle；308-file 指紋 `032bf3d5d41a74e6ad50090ab7ffb13af6e5cca43a23c24adb3f8506d6d29a83` 通過 15／15 gate。SQLite 位於 Alembic `0012`；正式備份 `20260801-064628-279309-manual_verified_backup.sqlite3`／SHA-256 `bdf8366aa7b2d3b91d6754dc58d9ec0b6725bf29f7fe3e7d5bf3592b223f69e8`、隔離還原、health、`writeReady=true`、`maintenance=false`、`recoveryRequired=false` 及 `pendingBackups=0` 已核對。Worker 來源沒有改動，canonical Worker `394e2205-ae8f-4eef-a13a-e701931e6f0d` 維持 100% 流量且健康。`v1.2.0-rc.43` 只屬歷史來源，migration `0012` 後不可作 code-only rollback；須使用受控的相容資料庫還原。真人驗收仍為 `pending`。精確狀態及更新規則見[目前系統狀態](status/CURRENT_STATUS.md)。
<!-- SING_YIN_CURRENT_STATUS:END -->

本文件把機器驗證與真人驗收分開。`logs/release-candidate-report.json` 顯示 `pass`，只代表下列自動化證據在隔離虛構資料中通過；它不代表實際名單、學校做法、專用電腦、加密離機位置或外部存取決定已獲真人批准。

> **歷史 rc30 乾淨發布證據（2026-07-27）：** `v1.2.0-rc.30`／`74b84f43786b00feb15b51a6270ff71c9430773f` 與 Worker `11763f08-d40d-46d5-93dc-5ca2599d4154` 是當時完整驗證的乾淨組合。rc30 的 296-file runtime 指紋 `15d155d8d745b14b574b08d793150c93aa77946e7d17a63030844c44adededbc` 通過 14／14 正式 gate，包括 894 項 Python、3 個 motion 及 46 個 Worker contract，並完成受控 Windows 切換、正式備份、隔離還原、0% Worker smoke、100% promotion、origin health／readiness 與 canonical rendered checks。目前線上版本是本頁頂部的 rc45／Alembic `0012`；任何舊程式復原均須配合受控的相容資料庫還原。rc43／rc41／rc40／rc39／rc35 只屬歷史來源。機器與線上證據不能代替真人驗收，後者保持未完成。
>
> **歷史 rc31 綜合來源候選（已凍結、未上線）：** `codex/rc31-unified-theme-controls` 的 297 個可部署來源檔案曾以指紋 `7f405269322e67ddc1fdfd5dde004af5079b315725487303fbecd8e1c0954042` 通過當時 15／15 正式 `--release` 閘門。它只保留為來源演進證據，沒有部署，亦不是目前候選或回退目標；目前線上版本及 migration 後的受控資料庫復原限制以本頁頂部生成狀態為準。
>
> **rc28 來源候選（未上線）：** 46 個 Worker contract 已證明四個身份 CTA 共用同一控制器，並覆蓋成功、拒絕、同步例外、逾時、安靜意圖、已播放、重複啟動、`pageshow` 及媒體失敗分類。`scripts/verify_public_entry_music.py` 以真實 Chromium 覆蓋 desktop Admin、desktop Guest、390px mobile Admin／Guest、滑鼠／鍵盤、安靜、已播放、快速雙擊及 silent `/view`，每個身份測試只觀察一次目標請求並在建立真正 session／輸入私人憑證前截停。NiceGUI 的聚焦 Chromium 階段另已覆蓋 desktop menu、320px 全寬 System／Light／Dark 選擇器、目的語言本名、偏好隔離、256–1024px adaptive matrix、reduced motion 及零 console／page errors。Engineering 的 ≈10B 是按 2026-07-27 提供截圖把 9.38B 四捨五入的跨工具創作者指標，不是即時產品遙測。這些聚焦證據仍不是正式發布：須再由 exact-source release report、0% Worker version smoke、100% promotion 及 canonical live browser smoke 補完；首席導學風紀及教師顧問真人驗收仍保持未完成。
>
> **rc29 發布工具與 Worker（已上線）：** Windows PowerShell 5.1 的 Wrangler Secret 清單巢狀陣列問題已由明確 normalization 修正，測試只核對 Secret 名稱，不讀取或改動值。rc29 已完成 protected-main、annotated tag、14／14 exact-source gate、分段 Worker smoke、100% promotion 及 canonical live browser verification。Windows origin 因 runtime source 未變而保持 rc27；真人身份及業務驗收仍須另外完成。
>
> **rc30 介面與部署證據（已上線）：** 在 rc29 基線上加入目的語言本名、NiceGUI／Worker 明確 System／Light／Dark 選擇、320px 全寬 radio、44px Worker select、Admin／Guest／browser-local preference isolation，以及有日期與非遙測聲明的 ≈10B 創作者級 AI token 約數。rc30 自身的 296-file fingerprint `15d155d8d745b14b574b08d793150c93aa77946e7d17a63030844c44adededbc` 已通過 14／14 gates，包括 894 個 Python tests、3 個 motion contracts、46 個 Worker contracts、desktop／phone／tablet／256px reflow、preference／duplicated-tab isolation、write／PDF／backup／restore、runtime leak checks 及 partial-backup recovery。受控 origin 備份／隔離還原、0% Worker version smoke、100% promotion、canonical desktop／320px theme control 與 Guest Engineering ≈10B disclosure 均已通過；實體 iPhone／Android 及真人校務驗收仍未完成。
>
> **單一裝置矩陣：** rc20 的 source-matched 隔離瀏覽器證據把手機、兩種直向 adaptive tablet、橫向 desktop-shell touch tablet 及 full desktop 視為同一產品矩陣。768×1024、820×1180、1024×768、1440×1024 已一併進入正式報告；這只完成機器量測，不能代替實體裝置或部署後驗收。

## rc20 已驗證候選裝置矩陣 / Verified candidate device matrix

| 產品形態 | 必須量測的 viewport | 主要自動化證據 | 共存契約 |
|---|---|---|---|
| 窄屏／手機 | 256×700、320×760、390×844、844×390 | `scripts/verify_nicegui_mobile.py` | 真正 reflow、單一 adaptive shell、鍵盤／safe-area、44px 目標、零 document overflow |
| 直向 adaptive touch tablet | 768×1024、820×1180 | `scripts/verify_nicegui_mobile.py` | 操作表單維持一欄；卡片、證據及下載可使用兩個可讀欄 |
| 橫向 desktop-shell touch tablet | 1024×768 | `scripts/verify_nicegui_mobile.py` | 保留 compact desktop shell；操作／文件區不被壓成狹窄多欄 |
| Full desktop | 1440×1024 | `scripts/verify_nicegui_ui.py` | 保留完整 desktop shell、閱讀寬度、語言／theme／焦點與錯誤狀態證據 |

所有列共用 canonical URL、身份／session、NiceGUI route、資料 adapter、SQLite／記憶體邊界、排班 policy、審計、PDF 及內容順序。rc20 首次建立這個矩陣；rc26 的 source-matched 14-gate 報告重新覆蓋整個矩陣，受控 origin 切換及 canonical smoke 亦已完成；真人裝置驗收仍須另外完成。

## 使用方法

1. 維護者先執行 `python -X utf8 scripts\verify_release_candidate.py`，確認 JSON 報告目前 15 項檢查均為 `pass`；其中 `repository_hygiene` 必須證明有真正 commit 歷史、無已追蹤敏感檔、無尚未加入 Git 的發布敏感來源，且 ignore 契約完整；`security_gates` 必須通過依賴、靜態程式及 Python／Cloudflare 秘密掃描；`cloudflare_gateway_tests` 必須通過 Deno Worker 契約；`motion_state_machine_tests` 必須驗證快速滑入、滑出、鍵盤焦點及失效狀態最終一致；`verify_runtime_performance` 必須證明字體完成後的冷載、重複元件及跨頁返回後，強制 GC 的 heap／DOM／listener 增長與手機 overflow 均在門檻內；`verify_unified_guest_ui` 必須證明同路由訪客隔離、虛構資料、限制狀態、分頁與下載邊界。桌面、寫入、效能及手機瀏覽器閘門亦會把 console error 或未捕捉 `pageerror` 視為失敗；歷史版本的 14 項結果只作溯源，不是目前發布門檻。
   網站「交接指引」亦會核對報告的程式指紋；若顯示過期、失敗或格式不可信，先停止驗收並由 IT 支援重跑。
2. 首席導學風紀依下表只執行「仍需真人確認」欄，不需要重做已由自動化精確覆蓋的故障注入。
3. 教師顧問完成 A-01 至 A-04，並在 `docs/RELEASE_HANDOVER.md` 的正式驗收清單簽核。
4. 任一真人項目未完成，版本仍是「機器驗證完成、正式驗收未完成」。

## 首席導學風紀

### 等待、登入與重複操作

- [ ] 在桌面及手機分別按 Admin／Guest，確認只有所選角色顯示相應 busy 文案，另一入口暫時鎖定，返回上一頁後可再次操作。
- [ ] 模擬 200ms、1s 及 8s 導向：150ms 前沒有閃爍進度；延遲時顯示細軌；8s 後解鎖重試並保留登入協助，且不顯示完整電郵、Token 或內部錯誤。
- [ ] 在長操作確認只顯示真實階段；沒有實際 `completed／total` 時不得顯示百分比，也不得提供不能履行的取消鍵。
- [ ] 確認慢速或逾時的正式寫入不會自動重送；完成、失敗、返回及 reconnect 後沒有殘留 busy、transform、timer 或重疊進度。
- [ ] 在 reduced-motion、forced-colours、鍵盤及讀屏模式重做一次；階段只在變更時宣告，停止後不再播放動畫。

| ID | 驗收要求 | 直接自動化證據 | 仍需真人確認 |
|---|---|---|---|
| H-01 | 實際名單的中文姓名、職務及可值班日正確 | `test_prefect_management.py`; write pipeline 以虛構中文姓名完成匯入／新增／修改／停用 | 逐人核對正式名單；自動化不可判斷真實資料是否正確 |
| H-02 | 漏填欄位不開始寫入；停用前解釋歷史保留 | `test_accessibility.py`; write pipeline 的缺漏修復及停用確認 | 閱讀繁中措辭是否適合本屆操作習慣 |
| H-03 | 非星期一、缺替補／草稿修改／發布後調整原因在本頁修復；生成前請假原因可留空 | `test_roster_persistence.py`; `test_pre_generation_leaves.py`; `test_accessibility.py`; write pipeline 證明無效輸入無進度／無寫入，空白生成前原因則以 `NULL` 保存 | 用鍵盤及滑鼠各操作一次，確認焦點位置及「未提供」顯示自然 |
| H-04 | 助理首席只任 Assist；一般導學風紀只任房間 | `test_roster_policy.py::test_policy_role_gates_are_strict`; `test_assist_assignment_modes.py`; generator invariant test | 抽查實際生成週表的職務標示及 Assist. 模式 |
| H-05 | 302／303／202 人數、開放日、名冊「可值班日」、同日不重複、不連續；普通房間求解只能返回完整週表或受控無解，不得留下部分安排或錯誤點數 | `test_roster_policy.py::test_generated_roster_preserves_non_negotiable_rules`; `test_assist_mode_guardrails.py`; Room 202 closure、greedy-dead-end、完整 slot multiplicity 及 duty-weight rejection 測試已納入 rc31 exact-current-source 15／15 正式報告 | 抽查一個實際週，確認未選的不可當值日從未被使用，所有必需格完整且點數正確，並確認校務安排沒有臨時政策變更 |
| H-06 | 生成前請假排除；舊草稿須重新生成 | `test_pre_generation_leaves.py`; write pipeline | 以獲批准的測試情境核對提示是否易明 |
| H-07 | 發布需確認；公平帳本只入帳一次 | `test_roster_persistence.py` 的單次及並行發布測試；write pipeline 34.0 入帳證據 | 閱讀確認內容後才發布實際測試週 |
| H-08 | 發布後請假只供合資格替補並保留帳本／審計 | `test_pre_generation_leaves.py`; `test_roster_persistence.py`; write pipeline | 由首席導學風紀解釋一次替補選擇理由 |
| H-09 | 中英文 PDF 單頁橫向、中文姓名、完整星期／崗位、202 關閉格 | `test_roster_export.py::test_bilingual_published_schedule_pdfs_expose_every_operator_check`; write pipeline 下載後直接解析兩份 PDF | 在實際列印／手機群組預覽中核對字體大小、分頁及裁切 |
| H-10 | 群組週表與具名內部公平審計分開 | `test_roster_export.py::test_internal_audit_pdf_is_separate_from_group_schedule`; export dialog browser coverage | 決定審計檔接收者；不得預設發到風紀群組 |
| H-11 | 繼任者可依交接指引獨立完成 | handover route、雙語內容及狀態由 UI smoke／i18n 測試覆蓋 | 必須由一位未參與開發的人實際演練，不能由開發者代簽 |
| H-12 | 交接包含 SQLite、manifest、說明 | `test_backup_integrity.py`; write pipeline 建立並檢查 ZIP | 把測試包移到學校批准的加密離機位置，確認可找回 |
| H-13 | 無快照、無效快照及有效快照並存時行為安全 | UI smoke、backup inventory tests、write pipeline、partial-backup drill | 確認畫面用語不會令人嘗試手動修改備份 |
| H-14 | 同一網站在手機、200% zoom、tablet 及 desktop 保持同一產品並真正 reflow，讀取／焦點順序完整；手機抽屜以實際渲染狀態同步 ARIA、inert 及 focus，離頁不殘留 listener／RAF | rc31 exact-current-source 正式報告已包含 `verify_nicegui_mobile.py`、`verify_nicegui_ui.py`、`test_mobile_layout.py`、`test_accessibility.py`、`test_motion_system.py`、rendered-state settle／快速切換／cleanup 及 20 次路由循環；效能證據為 DOM `+0`、listener `+0`、forced-GC heap `+0.45 MiB` | 在實體 iPhone Safari 及 Android Chrome 核對 200% zoom、軟鍵盤後焦點欄位、跨頁 main focus、快速開關 More 抽屜、兩個 themes、reduced motion、forced colours、旋轉、瀏海／home indicator；另以實際 tablet 及 desktop 抽查 shell／欄位共存，不另建 `/mobile` |
| H-15 | 外觀／聲音不清空表單；語言離開前保護未儲存輸入；Public／Viewer 未設定時跟隨系統，刻意進入 Admin／Guest 時只暫存 120 秒的明確 Light／Dark 提示，並由 Worker 放入簽署身份後帶入；既有目的地偏好優先 | `test_theme_preference.py`; `test_gateway_identity.py`; Worker contracts；rc31 專用 Public→Admin／Guest Chromium matrix；`test_interface_sound.py`; `test_accessibility.py` | 在一個未儲存表單親自切換偏好並確認不丟資料；另由 OS Light 及 OS Dark 的全新瀏覽器分別進入 Admin／Guest，核對首次相反切換、刷新、返回、既有偏好不被覆寫、reduced motion 及 forced colours |
| H-16 | 兩個分頁不能以舊資料覆蓋較新風紀或草稿 | prefect／roster concurrency tests；SQLite `BEGIN IMMEDIATE` 與 version CAS | 以虛構資料完成一次 stale-tab 演練，確認提示要求重新載入及核對 |
| H-17 | 正式模式從空白名單開始且不自動 seed；Practice Mode 保留隔離虛構 seed | **rc.16 自動化閘門已通過：** `test_official_data_reset.py`、runtime mode tests、reset report 零筆表格／空白基線契約；只有正式主機 sanitized reset report 及重啟 health 才是已完成清除的部署證據 | 正式清除只可在已驗證備份、隔離還原及 Viewer 撤銷後執行；重啟兩個模式並核對正式為零、練習有虛構資料 |
| H-18 | v1.2 Guest 與 Admin 使用相同 NiceGUI 路由，但 Guest 只操作每分頁隔離的虛構記憶體 workspace；下載票證亦須綁定 access mode 及 session，跨模式／跨 session 重播失敗，Guest 不可耗盡 Admin 保留容量 | rc31 exact-current-source 正式報告已覆蓋共同路由、Guest workspace／snapshot、共用有界 registry、HTTP status／精確 MIME、mode／session binding、cross-mode replay rejection、Admin reserve、完整 Guest 寫入／雙語 PDF／JSON 流程及 Worker contracts。預設限額為 Guest 5 MiB／檔、Admin 64 MiB／檔、registry 128 MiB，並保留 64 MiB／16 票證予 Admin。 | 在實體手機完成訪客請假→生成→修改→示範發布→雙語 PDF／JSON→請假調整；核對中文姓名、`DEMO`、30 分鐘、兩分頁隔離、重新整理、登出、失敗下載的雙語下一步與支援編號，以及 Guest 壓力下 Admin 仍可下載超過 5 MiB 的受控交接檔案 |
| H-19 | 公開入口在手機首屏提供清楚且唯一可見的 Admin／fictional Guest 入口，桌面排列及身份邊界不漂移 | rc26 source-matched release report 以 `test_cloudflare_roster_viewer.py` 鎖定結構與權限契約；部署後 canonical smoke 另以 `verify_public_roster_viewer.py` 證明入口及 Guest Platform 正確。Admin／Guest 各一個 visible CTA、first viewport、至少 48px（設計值 52px）、desktop access panel、mobile 不重複顯示、light／dark、reduced motion、forced colours、console／pageerror 仍屬同一契約 | 以 320px／390px 實體手機先確認兩個入口毋須捲動，再各進入一次並使用返回鍵；核對沒有重複 CTA、錯誤身份、被音樂／鍵盤遮擋或只在單一 theme 可見 |
| H-20 | 新週預設 `legacy_fixed_weekday`；固定模式維持 AHP 原有星期，`flexible_weekly` 只在可值班日輪換並在可行情況避免重複上週同日；每份週表保存所選模式 | `test_assist_assignment_modes.py`、`test_assist_mode_persistence.py`、`test_assist_mode_guardrails.py`、`test_assist_assignment_mode_ui_contract.py` 鎖定 AHP-only、可值班日、請假、固定擁有者、靈活輪換、模式持久化、重複固定日拒絕、Admin／Guest UI parity 及 migration `0011_assist_assignment_mode` 的舊資料回填契約 | 以虛構 AHP 連續生成兩週固定模式及兩週靈活模式；核對固定星期不漂移、請假只替補該次、靈活模式有輪換、不可當值日從不被使用，並確認中英文模式說明容易理解 |
| H-21 | Admin／Guest／Public／Viewer 有一致、可恢復且不污染排班交易的問題回報路徑 | `test_support_incidents.py`、`test_support_feedback_ui.py`、`test_host_security_summary.py` 及 Worker contract 驗證 Admin 明確同意、本機原子收件匣、redaction／quota／integrity／cleanup、Guest browser-only 及 Public／Viewer 無 fetch／XHR／WebSocket／storage；`test_content_design_contract.py` 鎖定漸進披露及文件入口 | 分別以 Admin、Guest、Public 及一個 Viewer 頁進入 `/support`：核對核心欄位先顯示；Admin 可選擇有限附件並在確認後得到編號；其餘三種模式只能下載／複製／電郵，重新載入後沒有網站保存的內容；所有錯誤均提供下一步且不改週表、公平帳本或備份 |

## 教師顧問

| ID | 驗收要求 | 直接自動化證據 | 必須由教師顧問確認 |
|---|---|---|---|
| A-01 | 公平帳本符合學校做法 | 角色、點數、一次性發布及請假轉移均有單元／整合測試 | 審閱一份發布表和一次調整；確認 `history_weight` 解釋符合學校政策 |
| A-02 | 最近備份可驗證及還原；還原只接受精確 database／manifest 配對，拒絕 sidecar、非 object／損壞 manifest、待完成 backup obligation 及未知／未來 migration，並在成功後回到 write-ready | rc31 exact-current-source 正式報告已覆蓋 strict readiness、`test_backup_restore.py`、write pipeline 第二隔離資料庫、maintenance lease、來源／staged substitution、DB／manifest digest、`0007` 支援鏈隔離遷移、current schema／FK／fairness、失敗自動 rollback、exact-pair handover ZIP、diagnostic-only marker、partial-backup drill 及隔離還原 | 在非正式副本完成一次受監督演練並記錄日期；確認維護期間所有業務寫入不能進入，成功後 `/readyz` 恢復 write-ready；另確認 durable marker 啟動只進 diagnostic-only，而不是手動刪除 marker |
| A-03 | 專用電腦、秘密、加密離機位置及責任人 | readiness 只會指出缺口，不會替學校作決定 | 指定電腦、保管人、輪替方式及事故聯絡人 |
| A-04 | 正式 canonical 網站完成 Cloudflare 遠端驗收，維護入口仍保持私有 | deployment fail-closed tests 證明 origin 只綁定 loopback；Worker 契約驗證 Public、Guest、Admin OTP callback、Viewer、簽署 principal、WebSocket 及隔離邊界。Access 只保護 `/auth/login`，UI middleware 拒絕未聲明 Host | 以 <https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/> 驗收 Public、Guest、Admin OTP、Viewer、WebSocket／重連及隔離；再核對 WARP 後備可用，而 WARP-off、未獲准裝置及直接 LAN origin 均不可繞過 |

## 證據失效規則

- 修改排班政策、交易、migration、備份、PDF、語言、route focus／mobile reflow、Cloudflare Worker／JSONC 或發布驗證器後，必須重新執行當前完整發布候選驗證。rc20 的候選基線是 14 項；後續以最終候選 report 列出的 source-matched gate 集合為準，不可沿用舊日期或舊計數。
- JSON 報告缺少 `humanAcceptanceRequired: true`、任何檢查不是 `pass`，或報告早於最後程式改動，均不可用作發布證據。
- 自動化只使用虛構中文姓名；正式姓名、請假原因、PDF、資料庫、備份及日誌不可上載到公開服務。
