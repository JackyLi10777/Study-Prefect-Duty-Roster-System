# 正式驗收證據矩陣 / Acceptance evidence matrix

本文件把機器驗證與真人驗收分開。`logs/release-candidate-report.json` 顯示 `pass`，只代表下列自動化證據在隔離虛構資料中通過；它不代表實際名單、學校做法、專用電腦、加密離機位置或外部存取決定已獲真人批准。

> **發布界線（2026-07-26）：** live `v1.2.0-rc.26`／`248955cb3300bfbe092b05036632991524d824cd` 與 Worker `76a23134-8355-4e25-bbba-abf17c6918c5` 是現行已部署基線；第一級回退是 `v1.2.0-rc.24`／`8d709f9b0b4e69fe38f7237ef2f473c27ff848fc`，rc21／`f7df4d0170e6bacd65340cc893992a17b5ed4aed` 是次級已驗證基線。rc26 的 296-file runtime 指紋 `5da902307e2d717a75c93e100ba9860eb7e6dd9c35dc42d4a1477bd3304de5e7` 通過 14／14 正式 gate，包括完整 Python suite、3 個 motion 及 41 個 Worker contract，並完成受控 Windows 切換、正式備份、隔離還原與 canonical 入口／Guest Platform smoke。rc24 至 rc26 的 Worker source／設定沒有差異，因此沿用已驗證 Worker，而不是作無意義的重新部署。Public `/support` 保持瀏覽器暫存，已驗證 Guest `/support` 進入 NiceGUI 工作台；機器與線上證據不能代替真人驗收，後者保持未完成。

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

1. 維護者先執行 `python -X utf8 scripts\verify_release_candidate.py`，確認 JSON 報告目前 14 項檢查均為 `pass`；其中 `repository_hygiene` 必須證明有真正 commit 歷史、無已追蹤敏感檔、無尚未加入 Git 的發布敏感來源，且 ignore 契約完整；`security_gates` 必須通過依賴、靜態程式及 Python／Cloudflare 秘密掃描；`cloudflare_gateway_tests` 必須通過 Deno Worker 契約；`motion_state_machine_tests` 必須驗證快速滑入、滑出、鍵盤焦點及失效狀態最終一致；`verify_runtime_performance` 必須證明字體完成後的冷載、重複元件及跨頁返回後，強制 GC 的 heap／DOM／listener 增長與手機 overflow 均在門檻內；`verify_unified_guest_ui` 必須證明同路由訪客隔離、虛構資料、限制狀態、分頁與下載邊界。桌面、寫入、效能及手機瀏覽器閘門亦會把 console error 或未捕捉 `pageerror` 視為失敗。
   網站「交接指引」亦會核對報告的程式指紋；若顯示過期、失敗或格式不可信，先停止驗收並由 IT 支援重跑。
2. 首席導學風紀依下表只執行「仍需真人確認」欄，不需要重做已由自動化精確覆蓋的故障注入。
3. 教師顧問完成 A-01 至 A-04，並在 `docs/RELEASE_HANDOVER.md` 的正式驗收清單簽核。
4. 任一真人項目未完成，版本仍是「機器驗證完成、正式驗收未完成」。

## 首席導學風紀

| ID | 驗收要求 | 直接自動化證據 | 仍需真人確認 |
|---|---|---|---|
| H-01 | 實際名單的中文姓名、職務及可值班日正確 | `test_prefect_management.py`; write pipeline 以虛構中文姓名完成匯入／新增／修改／停用 | 逐人核對正式名單；自動化不可判斷真實資料是否正確 |
| H-02 | 漏填欄位不開始寫入；停用前解釋歷史保留 | `test_accessibility.py`; write pipeline 的缺漏修復及停用確認 | 閱讀繁中措辭是否適合本屆操作習慣 |
| H-03 | 非星期一、缺替補／草稿修改／發布後調整原因在本頁修復；生成前請假原因可留空 | `test_roster_persistence.py`; `test_pre_generation_leaves.py`; `test_accessibility.py`; write pipeline 證明無效輸入無進度／無寫入，空白生成前原因則以 `NULL` 保存 | 用鍵盤及滑鼠各操作一次，確認焦點位置及「未提供」顯示自然 |
| H-04 | 助理首席只任 Assist；一般導學風紀只任房間 | `test_roster_policy.py::test_policy_role_gates_are_strict`; `test_assist_assignment_modes.py`; generator invariant test | 抽查實際生成週表的職務標示及 Assist. 模式 |
| H-05 | 302／303／202 人數、開放日、名冊「可值班日」、同日不重複、不連續 | `test_roster_policy.py::test_generated_roster_preserves_non_negotiable_rules`; `test_assist_mode_guardrails.py`; Room 202 closure test | 抽查一個實際週，確認未選的不可當值日從未被使用，且校務安排沒有臨時政策變更 |
| H-06 | 生成前請假排除；舊草稿須重新生成 | `test_pre_generation_leaves.py`; write pipeline | 以獲批准的測試情境核對提示是否易明 |
| H-07 | 發布需確認；公平帳本只入帳一次 | `test_roster_persistence.py` 的單次及並行發布測試；write pipeline 34.0 入帳證據 | 閱讀確認內容後才發布實際測試週 |
| H-08 | 發布後請假只供合資格替補並保留帳本／審計 | `test_pre_generation_leaves.py`; `test_roster_persistence.py`; write pipeline | 由首席導學風紀解釋一次替補選擇理由 |
| H-09 | 中英文 PDF 單頁橫向、中文姓名、完整星期／崗位、202 關閉格 | `test_roster_export.py::test_bilingual_published_schedule_pdfs_expose_every_operator_check`; write pipeline 下載後直接解析兩份 PDF | 在實際列印／手機群組預覽中核對字體大小、分頁及裁切 |
| H-10 | 群組週表與具名內部公平審計分開 | `test_roster_export.py::test_internal_audit_pdf_is_separate_from_group_schedule`; export dialog browser coverage | 決定審計檔接收者；不得預設發到風紀群組 |
| H-11 | 繼任者可依交接指引獨立完成 | handover route、雙語內容及狀態由 UI smoke／i18n 測試覆蓋 | 必須由一位未參與開發的人實際演練，不能由開發者代簽 |
| H-12 | 交接包含 SQLite、manifest、說明 | `test_backup_integrity.py`; write pipeline 建立並檢查 ZIP | 把測試包移到學校批准的加密離機位置，確認可找回 |
| H-13 | 無快照、無效快照及有效快照並存時行為安全 | UI smoke、backup inventory tests、write pipeline、partial-backup drill | 確認畫面用語不會令人嘗試手動修改備份 |
| H-14 | 同一網站在手機、200% zoom、tablet 及 desktop 保持同一產品並真正 reflow，讀取／焦點順序完整 | rc20 source-matched report 已包含 `verify_nicegui_mobile.py`、`verify_nicegui_ui.py`、`test_mobile_layout.py`、`test_accessibility.py`、`test_motion_system.py`，並收錄上方單一裝置矩陣：256×700 reflow、320×760 reduced motion、390×844 phone、768×1024 與 820×1180 adaptive touch tablet、1024×768 desktop-shell touch tablet、1440×1024 full desktop、844×390 phone landscape、單一可見 navigation shell、44px standalone controls、route focus、More／drawer current-page semantics、`visualViewport` keyboard clearance、safe-area/footer、touch icon story、forced colours、paired themes、零 document overflow／console／pageerror | 在實體 iPhone Safari 及 Android Chrome 核對 200% zoom、軟鍵盤後焦點欄位、跨頁 main focus、More 語意、兩個 themes、reduced motion、forced colours、旋轉、瀏海／home indicator；另以實際 tablet 及 desktop 抽查 shell／欄位共存，不另建 `/mobile` |
| H-15 | 外觀／聲音不清空表單；語言離開前保護未儲存輸入 | `test_interface_sound.py`; `test_accessibility.py`; UI smoke 的 in-place theme／sound 及 dirty-language guard | 在一個未儲存表單親自切換三項偏好，確認提示、一次短聲及鍵盤流程自然 |
| H-16 | 兩個分頁不能以舊資料覆蓋較新風紀或草稿 | prefect／roster concurrency tests；SQLite `BEGIN IMMEDIATE` 與 version CAS | 以虛構資料完成一次 stale-tab 演練，確認提示要求重新載入及核對 |
| H-17 | 正式模式從空白名單開始且不自動 seed；Practice Mode 保留隔離虛構 seed | **rc.16 自動化閘門已通過：** `test_official_data_reset.py`、runtime mode tests、reset report 零筆表格／空白基線契約；只有正式主機 sanitized reset report 及重啟 health 才是已完成清除的部署證據 | 正式清除只可在已驗證備份、隔離還原及 Viewer 撤銷後執行；重啟兩個模式並核對正式為零、練習有虛構資料 |
| H-18 | v1.2 Guest 與 Admin 使用相同 NiceGUI 路由，但 Guest 只操作每分頁隔離的虛構記憶體 workspace；重新整理可還原最新合法 token，複製／篡改／過期／重啟後不可重播 | rc26 的 `verify_unified_guest_ui` 正式 gate 配合 `test_guest_workspace.py`、`test_guest_adapter.py`、`test_guest_downloads.py`、`test_guest_snapshot_bridge.py` 驗證相同路由、簽署、綁定、nonce、revision、重播拒絕、下載及 `sessionStorage` 邊界。報告已綁定 rc26 source fingerprint並完成部署後 smoke；真人實體裝置驗收仍未完成 | 在實體手機完成訪客請假→生成→修改→示範發布→雙語 PDF／JSON→請假調整；核對中文姓名、`DEMO`、30 分鐘、兩分頁隔離、重新整理、登出及 Network／正式資料邊界 |
| H-19 | 公開入口在手機首屏提供清楚且唯一可見的 Admin／fictional Guest 入口，桌面排列及身份邊界不漂移 | rc20 source-matched release report 以 `test_cloudflare_roster_viewer.py` 鎖定結構與權限契約；部署後仍要以 `verify_public_roster_viewer.py` 在 canonical 網址證明 Admin／Guest 各一個 visible CTA、位於 first viewport、至少 48px（設計值 52px）、在補充 workflow／devotional 前。Desktop access panel 仍存在，mobile 不重複顯示；light／dark、reduced motion、forced colours、console／pageerror 均須核對 | 以 320px／390px 實體手機先確認兩個入口毋須捲動，再各進入一次並使用返回鍵；核對沒有重複 CTA、錯誤身份、被音樂／鍵盤遮擋或只在單一 theme 可見 |
| H-20 | 新週預設 `legacy_fixed_weekday`；固定模式維持 AHP 原有星期，`flexible_weekly` 只在可值班日輪換並在可行情況避免重複上週同日；每份週表保存所選模式 | `test_assist_assignment_modes.py`、`test_assist_mode_persistence.py`、`test_assist_mode_guardrails.py`、`test_assist_assignment_mode_ui_contract.py` 鎖定 AHP-only、可值班日、請假、固定擁有者、靈活輪換、模式持久化、重複固定日拒絕、Admin／Guest UI parity 及 migration `0011_assist_assignment_mode` 的舊資料回填契約 | 以虛構 AHP 連續生成兩週固定模式及兩週靈活模式；核對固定星期不漂移、請假只替補該次、靈活模式有輪換、不可當值日從不被使用，並確認中英文模式說明容易理解 |
| H-21 | Admin／Guest／Public／Viewer 有一致、可恢復且不污染排班交易的問題回報路徑 | `test_support_incidents.py`、`test_support_feedback_ui.py`、`test_host_security_summary.py` 及 Worker contract 驗證 Admin 明確同意、本機原子收件匣、redaction／quota／integrity／cleanup、Guest browser-only 及 Public／Viewer 無 fetch／XHR／WebSocket／storage；`test_content_design_contract.py` 鎖定漸進披露及文件入口 | 分別以 Admin、Guest、Public 及一個 Viewer 頁進入 `/support`：核對核心欄位先顯示；Admin 可選擇有限附件並在確認後得到編號；其餘三種模式只能下載／複製／電郵，重新載入後沒有網站保存的內容；所有錯誤均提供下一步且不改週表、公平帳本或備份 |

## 教師顧問

| ID | 驗收要求 | 直接自動化證據 | 必須由教師顧問確認 |
|---|---|---|---|
| A-01 | 公平帳本符合學校做法 | 角色、點數、一次性發布及請假轉移均有單元／整合測試 | 審閱一份發布表和一次調整；確認 `history_weight` 解釋符合學校政策 |
| A-02 | 最近備份可驗證及還原 | strict readiness、`test_backup_restore.py`、write pipeline 第二隔離資料庫；完整 table／Alembic head preflight、跨程序 maintenance lease、失敗後自動回復測試 | 在非正式副本完成一次受監督演練並記錄日期；確認維護期間其他分頁不能寫入 |
| A-03 | 專用電腦、秘密、加密離機位置及責任人 | readiness 只會指出缺口，不會替學校作決定 | 指定電腦、保管人、輪替方式及事故聯絡人 |
| A-04 | 正式 canonical 網站完成 Cloudflare 遠端驗收，維護入口仍保持私有 | deployment fail-closed tests 證明 origin 只綁定 loopback；Worker 契約驗證 Public、Guest、Admin OTP callback、Viewer、簽署 principal、WebSocket 及隔離邊界。Access 只保護 `/auth/login`，UI middleware 拒絕未聲明 Host | 以 <https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/> 驗收 Public、Guest、Admin OTP、Viewer、WebSocket／重連及隔離；再核對 WARP 後備可用，而 WARP-off、未獲准裝置及直接 LAN origin 均不可繞過 |

## 證據失效規則

- 修改排班政策、交易、migration、備份、PDF、語言、route focus／mobile reflow、Cloudflare Worker／JSONC 或發布驗證器後，必須重新執行當前完整發布候選驗證。rc20 的候選基線是 14 項；後續以最終候選 report 列出的 source-matched gate 集合為準，不可沿用舊日期或舊計數。
- JSON 報告缺少 `humanAcceptanceRequired: true`、任何檢查不是 `pass`，或報告早於最後程式改動，均不可用作發布證據。
- 自動化只使用虛構中文姓名；正式姓名、請假原因、PDF、資料庫、備份及日誌不可上載到公開服務。
