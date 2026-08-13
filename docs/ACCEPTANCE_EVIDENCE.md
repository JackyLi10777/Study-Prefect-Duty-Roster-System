# 正式驗收證據矩陣 / Acceptance evidence matrix

## 目前正式機器與線上證據（真人驗收仍待完成）

- 合成 SQLite 規模驗證涵蓋 24／52、240／520、2,400／5,200 人／週層級；查詢計劃、statement count、p50／p95、記憶體、DB／WAL 大小及備份時間保存在 `docs/audits/rc44-sqlite-scale.json`。
<!-- SING_YIN_CURRENT_STATUS:START -->
> **已核實線上來源（2026-08-14）：** Windows origin 正運行 clean annotated `v1.2.0-rc.58`／`e90bb8fdb95ca874f668b5a7134853756471635f` 的不可變 bundle；319-file 指紋 `c57778ce438c1c23c824c444827db7eeb9166d20be3ba3e78f1bb1221fee5283` 通過 15／15 gate。SQLite 位於 Alembic `0014`；正式備份 `20260813-161554-736678-manual_verified_backup.sqlite3`／SHA-256 `0e0ee9cc9a592eeea66055e107c461e859f3ccec2791cb06f051e7078c3febc2`、隔離還原、health、`writeReady=true`、`maintenance=false`、`recoveryRequired=false` 及 `pendingBackups=0` 已核對。Worker 來源沒有改動，canonical Worker `7951ca55-ffda-4f16-b570-d37486311914` 維持 100% 流量且健康。`v1.2.0-rc.57` 只屬歷史來源，migration `0014` 後不可作 code-only rollback；須使用受控的相容資料庫還原。真人驗收仍為 `pending`，實體離線 BitLocker 復原演練仍為 `pending`。精確狀態及更新規則見[目前系統狀態](status/CURRENT_STATUS.md)。
<!-- SING_YIN_CURRENT_STATUS:END -->

本文件把機器驗證與真人驗收分開。`logs/release-candidate-report.json` 顯示 `pass`，只代表下列自動化證據在隔離虛構資料中通過；它不代表實際名單、學校做法、專用電腦、加密離機位置或外部存取決定已獲真人批准。

> **手機優先操作（rc57 已部署）：** 專用手機快速設定方格、drawer／鍵盤與底部導航的單一 ownership、精確有界週次查詢、分頁歷史、單日草稿視圖、共用 bottom sheet 及單一 dirty-save dock 已進入上方正式版本。正式網址的 real-Chrome 矩陣涵蓋手機、橫屏、平板、200%文字、forced colours及reduced motion；所有記錄路由 CLS 為 `0`，且沒有非預期 browser error。這是機器證據，不取代實體 Android Chrome 及受監督操作驗收。

### Quiet Command Center frontend reset evidence（2026-08-02; live）

- `python -X utf8 -m pytest`：`1135 passed`，涵蓋設計／元件契約、排班政策、交易、Guest、安全、PDF、備份與復原；本輪沒有為前端改動刪減後端驗證。
- `deno check worker.js` 及 `deno test worker_gateway_test.js`：53／53 Worker contracts 通過，包含 Admin／Guest 入口、音樂成功／拒絕／逾時 fallback、Session、Access、Viewer、支援及路由邊界。
- `verify_nicegui_mobile.py`：390px 手機、768×1024 與 820×1180 adaptive touch tablet、1024×768 desktop-shell touch tablet、320px 英文／reduced-motion、256px reflow 及 844×390 landscape 全部通過；沒有 document overflow、重複 shell、遮擋最終操作或焦點語意回歸。
- `verify_nicegui_ui.py`：在全新正式空白隔離 SQLite 上通過完整桌面／手機、深淺模式、名單／值班工作流、進度、設定、Daily Verse、音樂停用及錯誤恢復檢查，且沒有 console／page error。
- `verify_semantic_icon_motion.py`：Admin／Guest、forced-colours／reduced-motion 四種 context 及 20 次 route cycle 通過；glyph morph／rotation 沒有改變 host 幾何、競爭狀態或殘留 transform。
- `project_governance.py --check`、`git diff --check`、15／15 正式 release gate、Windows origin 切換、Worker 0% candidate smoke、100% promotion 及 canonical live smoke 已通過；真人裝置／校務驗收仍待完成，沒有被機器證據取代。

> **歷史 rc30 乾淨發布證據（2026-07-27）：** `v1.2.0-rc.30`／`74b84f43786b00feb15b51a6270ff71c9430773f` 與 Worker `11763f08-d40d-46d5-93dc-5ca2599d4154` 是當時完整驗證的乾淨組合。rc30 的 296-file runtime 指紋 `15d155d8d745b14b574b08d793150c93aa77946e7d17a63030844c44adededbc` 通過 14／14 正式 gate，包括 894 項 Python、3 個 motion 及 46 個 Worker contract，並完成受控 Windows 切換、正式備份、隔離還原、0% Worker smoke、100% promotion、origin health／readiness 與 canonical rendered checks。目前線上版本及 Alembic 狀態只以本頁頂部生成區塊為準；任何舊程式復原均須配合受控的相容資料庫還原。rc45／rc43／rc41／rc40／rc39／rc35 只屬歷史來源。機器與線上證據不能代替真人驗收，後者保持未完成。
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

1. 維護者先執行 `python -X utf8 scripts\verify_release_candidate.py`，確認 JSON 報告目前 15 項檢查均為 `pass`，而且 schema 3 `postVerificationSource` 與開始時的 fingerprint、file count、commit、tree 及 clean Git state 完全一致；其中 `repository_hygiene` 必須證明有真正 commit 歷史、無已追蹤敏感檔、無尚未加入 Git 的發布敏感來源，且 ignore 契約完整；`security_gates` 必須通過依賴、靜態程式及 Python／Cloudflare 秘密掃描；`cloudflare_gateway_tests` 必須通過 Deno Worker 契約；`motion_state_machine_tests` 必須驗證快速滑入、滑出、鍵盤焦點及失效狀態最終一致；`verify_runtime_performance` 必須證明字體完成後的冷載、重複元件及跨頁返回後，強制 GC 的 heap／DOM／listener 增長與手機 overflow 均在門檻內；`verify_unified_guest_ui` 必須證明同路由訪客隔離、虛構資料、限制狀態、分頁與下載邊界。桌面、寫入、效能及手機瀏覽器閘門亦會把 console error 或未捕捉 `pageerror` 視為失敗；歷史版本的 14 項結果只作溯源，不是目前發布門檻。
   網站「交接指引」亦會核對報告的程式指紋；若顯示過期、失敗或格式不可信，先停止驗收並由 IT 支援重跑。頁面把本矩陣分成七段受監督演練，顯示每段對應的 H／A 編號，並可下載預設未勾選的本機驗收記錄；它不會自行判定或保存簽核結果。
2. 首席導學風紀依下表只執行「仍需真人確認」欄，不需要重做已由自動化精確覆蓋的故障注入。
3. 教師顧問完成 A-01 至 A-04，並在 `docs/RELEASE_HANDOVER.md` 的正式驗收清單簽核。
4. 任一真人項目未完成，版本仍是「機器驗證完成、正式驗收未完成」。

## 首席導學風紀

### 等待、登入與重複操作

- [ ] 在桌面及手機分別按 Admin／Guest，確認只有所選角色顯示相應 busy 文案，另一入口暫時鎖定，返回上一頁後可再次操作。
- [ ] 模擬 200ms、1s 及 8s 導向：150ms 前沒有閃爍進度；延遲時顯示細軌；8s 後解鎖重試並保留登入協助，且不顯示完整電郵、Token 或內部錯誤。
- [ ] 在長操作確認只顯示真實階段；沒有實際 `completed／total` 時不得顯示百分比，也不得提供不能履行的取消鍵。
- [ ] 在工作台分別觸發一個 140ms 內完成及一個超過 140ms 的操作：前者不閃現載入視窗，後者只顯示誠實的 indeterminate 階段；兩者均不得為動畫加入最低等待時間。身份導向及跨頁細軌仍按各自的 150ms 門檻驗收。
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
| H-08 | 發布後請假只供合資格替補並保留帳本／審計；所有舊 Viewer 版本進入 durable revocation，回應遺失亦不留下可重送的密鑰，精確重試不撤銷新版本 | `test_pre_generation_leaves.py`; `test_roster_persistence.py`; `test_external_share_outbox.py`; `test_access_control_ui.py`; write pipeline | 由首席導學風紀解釋一次替補選擇理由，並以虛構週表核對舊 Viewer 撤銷／待撤銷收據及新版本重發次序；若要求零重疊，須按交接指引以 5 秒間隔／90 秒上限驗證舊連結終止，逾時不得發送新連結 |
| H-09 | 中英文 PDF 單頁橫向、中文姓名、完整星期／崗位、202 關閉格 | `test_roster_export.py::test_bilingual_published_schedule_pdfs_expose_every_operator_check`; write pipeline 下載後直接解析兩份 PDF | 在實際列印／手機群組預覽中核對字體大小、分頁及裁切 |
| H-10 | 群組週表與具名內部公平審計分開 | `test_roster_export.py::test_internal_audit_pdf_is_separate_from_group_schedule`; export dialog browser coverage | 決定審計檔接收者；不得預設發到風紀群組 |
| H-11 | 繼任者可依交接指引獨立完成 | handover route、雙語內容及狀態由 UI smoke／i18n 測試覆蓋 | 必須由一位未參與開發的人實際演練，不能由開發者代簽 |
| H-12 | 交接包含 SQLite、manifest、說明；離機副本只接受批准的 BitLocker 外置媒體、必須綁定 immutable release identity，並由 copied bundle 還原 | handover／backup tests；`test_offsite_recovery.py`、CLI 及 Windows wrapper contract 覆蓋 exact pair、receipt、missing／null release marker、tamper、target 及刪除原主機資料後的隔離還原 | 在真實 BitLocker USB／SD 完成匯出、安全退出、離線保存及 replacement-location drill；記錄 RPO／RTO 與分離保管責任 |
| H-13 | 無快照、無效快照及有效快照並存時行為安全 | UI smoke、backup inventory tests、write pipeline、partial-backup drill | 確認畫面用語不會令人嘗試手動修改備份 |
| H-14 | 同一網站在手機、200% zoom、tablet 及 desktop 保持同一產品並真正 reflow，讀取／焦點順序完整；手機抽屜使用四個非圓形狀態方格，單一 requested-open state 同步 More、固定右上 Close、backdrop、ARIA、inert 及 focus，離頁不殘留 listener／RAF | 候選的 `test_mobile_quick_settings.py`、`test_mobile_layout.py`、`test_mobile_verifier.py` 及 `verify_nicegui_mobile.py` 鎖定非 50% 圓角、無逐字直排、專用 close、20 次開關 cleanup、200% 文字、forced colours、visual keyboard、GSAP 靜態 fallback 及裝置矩陣。一次直接隔離的 real-Chrome matrix 已在 320／360／390／412／430px、844×390 landscape、768／820／1024px touch tablet 通過；量度後以內置 UnoCSS `wind3` 取代 Tailwind browser compilation，記錄路由的 observed max long task 由約 1.49–1.60s 降至約 273ms且 CLS 0。完整 exact-source release gate 仍待執行 | 在實體 iPhone Safari 及 Android Chrome 核對快速設定沒有橢圓光圈、逐字直排、重複底部 X 或內容遮擋；再核對 200% zoom、軟鍵盤後焦點、兩個 themes、reduced motion、旋轉、瀏海／home indicator，並以實際 tablet／desktop 抽查共存 |
| H-15 | 外觀／聲音不清空表單；語言離開前保護未儲存輸入；Public／Viewer 未設定時跟隨系統，刻意進入 Admin／Guest 時只暫存 120 秒的明確 Light／Dark 提示，並由 Worker 放入簽署身份後帶入；入口與 `/support` 必須使用同一二態 sun／moon state contract | `test_theme_preference.py`; `test_gateway_identity.py`; Worker contracts；Public→Admin／Guest Chromium matrix；`test_interface_sound.py`; `test_accessibility.py`；rc54 候選另鎖定 theme observer RAF cleanup 及 `/support` 控制 anatomy | 在一個未儲存表單親自切換偏好並確認不丟資料；另由 OS Light 及 OS Dark 的全新瀏覽器分別進入 Admin／Guest 及 `/support`，核對首次相反切換、刷新、返回、既有偏好不被覆寫、視覺一致、reduced motion 及 forced colours |
| H-16 | 兩個分頁不能以舊資料覆蓋較新風紀或草稿；一次名單多列保存不可只成功部分列 | prefect／roster concurrency tests；SQLite `BEGIN IMMEDIATE`、每列 version CAS、typed edit-session tests；rc54 候選另以兩個同時 batch 證明一方完整提交、另一方零列衝突，Guest 亦維持同一零部分寫入契約 | 以虛構資料完成一次 stale-tab 演練，確認本頁所有輸入仍可核對／重新套用，且資料庫沒有混合新舊列 |
| H-17 | 正式模式從空白名單開始且不自動 seed；Practice Mode 保留隔離虛構 seed | **rc.16 自動化閘門已通過：** `test_official_data_reset.py`、runtime mode tests、reset report 零筆表格／空白基線契約；只有正式主機 sanitized reset report 及重啟 health 才是已完成清除的部署證據 | 正式清除只可在已驗證備份、隔離還原及 Viewer 撤銷後執行；重啟兩個模式並核對正式為零、練習有虛構資料 |
| H-18 | v1.2 Guest 與 Admin 使用相同 NiceGUI 路由，但 Guest 只操作每分頁隔離的虛構記憶體 workspace；下載票證亦須綁定 access mode 及 session，跨模式／跨 session 重播失敗，Guest 不可耗盡 Admin 保留容量 | rc31 exact-current-source 正式報告已覆蓋共同路由、Guest workspace／snapshot、共用有界 registry、HTTP status／精確 MIME、mode／session binding、cross-mode replay rejection、Admin reserve、完整 Guest 寫入／雙語 PDF／JSON 流程及 Worker contracts。另有[本機 workerd 混合負載驗收](audits/MIXED_GATEWAY_LOAD_ACCEPTANCE_2026-08-01.md)：乾淨來源以 10 個同時 Guest × 2 waves 及 2 個 Admin 執行，報告觀察到 22 個已連線 browser sessions／WebSockets、backup `0 → 2`、隔離 Guest 流程、Admin 寫入、兩份 PDF、outbox 及 Viewer 解密，沒有跨 session 洩漏、Guest 正式 DB write、未處理 lock／5xx 或公平差異。Verifier 固定要求每個 session 開啟 Worker-proxied WebSocket 且 Admin write 增加 recovery evidence；`22` 及 `0 → 2` 是該次觀察值，不是未來 run 的硬編碼數量。預設限額為 Guest 5 MiB／檔、Admin 64 MiB／檔、registry 128 MiB，並保留 64 MiB／16 票證予 Admin；該驗收是本機基線，不是 edge soak 或正式 SLO。 | 在實體手機完成訪客請假→生成→修改→示範發布→雙語 PDF／JSON→請假調整；核對中文姓名、`DEMO`、30 分鐘、兩分頁隔離、重新整理、登出、失敗下載的雙語下一步與支援編號，以及 Guest 壓力下 Admin 仍可下載超過 5 MiB 的受控交接檔案 |
| H-19 | 公開入口在手機首屏提供清楚且唯一可見的 Admin／fictional Guest 入口，桌面排列及身份邊界不漂移 | rc26 source-matched release report 以 `test_cloudflare_roster_viewer.py` 鎖定結構與權限契約；部署後 canonical smoke 另以 `verify_public_roster_viewer.py` 證明入口及 Guest Platform 正確。Admin／Guest 各一個 visible CTA、first viewport、至少 48px（設計值 52px）、desktop access panel、mobile 不重複顯示、light／dark、reduced motion、forced colours、console／pageerror 仍屬同一契約 | 以 320px／390px 實體手機先確認兩個入口毋須捲動，再各進入一次並使用返回鍵；核對沒有重複 CTA、錯誤身份、被音樂／鍵盤遮擋或只在單一 theme 可見 |
| H-20 | 新週預設 `legacy_fixed_weekday`；固定模式維持 AHP 原有星期，`flexible_weekly` 只在可值班日輪換並在可行情況避免重複上週同日；每份週表保存所選模式 | `test_assist_assignment_modes.py`、`test_assist_mode_persistence.py`、`test_assist_mode_guardrails.py`、`test_assist_assignment_mode_ui_contract.py` 鎖定 AHP-only、可值班日、請假、固定擁有者、靈活輪換、模式持久化、重複固定日拒絕、Admin／Guest UI parity 及 migration `0011_assist_assignment_mode` 的舊資料回填契約 | 以虛構 AHP 連續生成兩週固定模式及兩週靈活模式；核對固定星期不漂移、請假只替補該次、靈活模式有輪換、不可當值日從不被使用，並確認中英文模式說明容易理解 |
| H-21 | Admin／Guest／Public／Viewer 有一致、可恢復且不污染排班交易的問題回報路徑；公開支援頁不得退化為另一套簡陋主題控制 | `test_support_incidents.py`、`test_public_support.py`、`test_support_feedback_ui.py`、`test_host_security_summary.py` 及 Worker contract 驗證 Admin 明確同意、本機原子收件匣、PNG 重編碼、redaction／quota／integrity／cleanup、Guest browser-only，以及 Public／Viewer exact same-origin text POST、短效 capability、edge limit、`INC-…` 成功與 `FB-…` 瀏覽器後備；rc54 候選鎖定入口同款 sun／moon 控制 | 分別以 Admin、Guest、Public 及一個 Viewer 頁進入 `/support`：核對外觀與 theme control 延續及核心欄位；Public／Viewer 成功得到可由 Admin 查閱的 `INC-…`；分別注入網絡中斷及收件匣／origin 不可用，確認表單不清空、錯誤原因準確並得到 `FB-…`；Admin 可保存有限附件、按追溯碼核對及下載；Guest 只能下載／複製／電郵；所有錯誤均提供下一步且不改週表、公平帳本或備份 |
| H-22 | 草稿以同一呈現模型清楚區分 `assigned`、`vacant`、`room_closed`、`unavailable` 及 `day_closed`；格子修改／交換及星期停開以一個版本化交易整批保存，衝突不靜默覆寫；Guest 只修改虛構記憶體工作區；網頁、雙語 PDF 及公開分享保持相同星期、日期、英文崗位、中文姓名及狀態 | 候選來源的 `test_roster_day_closures.py`、`test_draft_patch_integrity.py`、`test_draft_grid_ui_contract.py` 及 `test_roster_export.py` 提供聚焦證據；typed session 另拒絕在全天／單格停開面進行移動或重新指派；正式 exact-source gate、migration／備份／隔離還原、部署及真人驗收仍須另行完成，不能由這列推定已上線 | 以虛構週表用滑鼠、鍵盤及觸控各完成一次姓名聯想、設為空缺、原子交換、單格停開、單日／多日／全星期停開、重新開放及版本衝突恢復；再核對桌面矩陣、手機卡片、繁中／英文 PDF 與公開分享，確認空缺、個別房間停開和全天停開不被混淆 |

## 教師顧問

| ID | 驗收要求 | 直接自動化證據 | 必須由教師顧問確認 |
|---|---|---|---|
| A-01 | 公平帳本符合學校做法 | 角色、點數、一次性發布及請假轉移均有單元／整合測試 | 審閱一份發布表和一次調整；確認 `history_weight` 解釋符合學校政策 |
| A-02 | 最近備份可驗證及還原；還原只接受精確 database／manifest 配對，拒絕 sidecar、非 object／損壞 manifest、待完成 backup obligation 及未知／未來 migration，並在成功後回到 write-ready | rc31 exact-current-source 正式報告已覆蓋 strict readiness、`test_backup_restore.py`、write pipeline 第二隔離資料庫、maintenance lease、來源／staged substitution、DB／manifest digest、`0007` 支援鏈隔離遷移、current schema／FK／fairness、失敗自動 rollback、exact-pair handover ZIP、diagnostic-only marker、partial-backup drill 及隔離還原 | 在非正式副本完成一次受監督演練並記錄日期；確認維護期間所有業務寫入不能進入，成功後 `/readyz` 恢復 write-ready；另確認 durable marker 啟動只進 diagnostic-only，而不是手動刪除 marker |
| A-03 | 專用電腦、秘密、加密離機位置及責任人 | Source wrapper 會拒絕內置／system disk、非 USB／SD、非 NTFS、未完整加密或 BitLocker protection off；它不保存 recovery key | 指定批准媒體、分離密鑰保管人、8 週／6 月保留輪替、事故聯絡人及實際 replacement-location 報告；來源測試不能代簽 |
| A-04 | 正式 canonical 網站完成 Cloudflare 遠端驗收，維護入口仍保持私有 | deployment fail-closed tests 證明 origin 只綁定 loopback；Worker 契約驗證 Public、Guest、Admin OTP callback、Viewer、簽署 principal、WebSocket 及隔離邊界。Access 只保護 `/auth/login`，UI middleware 拒絕未聲明 Host | 以 <https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/> 驗收 Public、Guest、Admin OTP、Viewer、WebSocket／重連及隔離；再核對 WARP 後備可用，而 WARP-off、未獲准裝置及直接 LAN origin 均不可繞過 |

## 證據失效規則

- 修改排班政策、交易、migration、備份、PDF、語言、route focus／mobile reflow、Cloudflare Worker／JSONC 或發布驗證器後，必須重新執行當前完整發布候選驗證。rc20 的候選基線是 14 項；後續以最終候選 report 列出的 source-matched gate 集合為準，不可沿用舊日期或舊計數。
- JSON 報告缺少 `humanAcceptanceRequired: true`、任何檢查不是 `pass`，或報告早於最後程式改動，均不可用作發布證據。
- 自動化只使用虛構中文姓名；正式姓名、請假原因、PDF、資料庫、備份及日誌不可上載到公開服務。
