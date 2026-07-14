# 正式驗收證據矩陣 / Acceptance evidence matrix

本文件把機器驗證與真人驗收分開。`logs/release-candidate-report.json` 顯示 `pass`，只代表下列自動化證據在隔離虛構資料中通過；它不代表實際名單、學校做法、專用電腦、加密離機位置或外部存取決定已獲真人批准。

## 使用方法

1. 維護者先執行 `python -X utf8 scripts\verify_release_candidate.py`，確認 JSON 報告目前 12 項檢查均為 `pass`；其中 `repository_hygiene` 必須證明有真正 commit 歷史、無已追蹤敏感檔、無尚未加入 Git 的發布敏感來源，且 ignore 契約完整；`security_gates` 必須通過依賴、靜態程式及 Python／Cloudflare 秘密掃描；`cloudflare_gateway_tests` 必須通過 Deno Worker 契約；`verify_runtime_performance` 必須證明字體完成後的冷載、重複元件及跨頁返回後，強制 GC 的 heap／DOM／listener 增長與手機 overflow 均在門檻內。桌面、寫入、效能及手機瀏覽器閘門亦會把 console error 或未捕捉 `pageerror` 視為失敗。
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
| H-04 | 助理首席只任 Assist；一般導學風紀只任房間 | `test_roster_policy.py::test_policy_role_gates_are_strict`; generator invariant test | 抽查實際生成週表的職務標示 |
| H-05 | 302／303／202 人數、開放日、同日不重複、不連續 | `test_roster_policy.py::test_generated_roster_preserves_non_negotiable_rules`; Room 202 closure test | 抽查一個實際週，確認校務安排沒有臨時政策變更 |
| H-06 | 生成前請假排除；舊草稿須重新生成 | `test_pre_generation_leaves.py`; write pipeline | 以獲批准的測試情境核對提示是否易明 |
| H-07 | 發布需確認；公平帳本只入帳一次 | `test_roster_persistence.py` 的單次及並行發布測試；write pipeline 34.0 入帳證據 | 閱讀確認內容後才發布實際測試週 |
| H-08 | 發布後請假只供合資格替補並保留帳本／審計 | `test_pre_generation_leaves.py`; `test_roster_persistence.py`; write pipeline | 由首席導學風紀解釋一次替補選擇理由 |
| H-09 | 中英文 PDF 單頁橫向、中文姓名、完整星期／崗位、202 關閉格 | `test_roster_export.py::test_bilingual_published_schedule_pdfs_expose_every_operator_check`; write pipeline 下載後直接解析兩份 PDF | 在實際列印／手機群組預覽中核對字體大小、分頁及裁切 |
| H-10 | 群組週表與具名內部公平審計分開 | `test_roster_export.py::test_internal_audit_pdf_is_separate_from_group_schedule`; export dialog browser coverage | 決定審計檔接收者；不得預設發到風紀群組 |
| H-11 | 繼任者可依交接指引獨立完成 | handover route、雙語內容及狀態由 UI smoke／i18n 測試覆蓋 | 必須由一位未參與開發的人實際演練，不能由開發者代簽 |
| H-12 | 交接包含 SQLite、manifest、說明 | `test_backup_integrity.py`; write pipeline 建立並檢查 ZIP | 把測試包移到學校批准的加密離機位置，確認可找回 |
| H-13 | 無快照、無效快照及有效快照並存時行為安全 | UI smoke、backup inventory tests、write pipeline、partial-backup drill | 確認畫面用語不會令人嘗試手動修改備份 |
| H-14 | 手機適應排列與讀取順序完整 | `verify_nicegui_mobile.py`; `test_mobile_layout.py`; 320／390px portrait、phone landscape、safe-area、44px、零 overflow／console／pageerror | 在實體 iPhone Safari 及 Android Chrome 核對鍵盤、旋轉、瀏海／home indicator；不另建 `/mobile` |
| H-15 | 外觀／聲音不清空表單；語言離開前保護未儲存輸入 | `test_interface_sound.py`; `test_accessibility.py`; UI smoke 的 in-place theme／sound 及 dirty-language guard | 在一個未儲存表單親自切換三項偏好，確認提示、一次短聲及鍵盤流程自然 |
| H-16 | 兩個分頁不能以舊資料覆蓋較新風紀或草稿 | prefect／roster concurrency tests；SQLite `BEGIN IMMEDIATE` 與 version CAS | 以虛構資料完成一次 stale-tab 演練，確認提示要求重新載入及核對 |

## 教師顧問

| ID | 驗收要求 | 直接自動化證據 | 必須由教師顧問確認 |
|---|---|---|---|
| A-01 | 公平帳本符合學校做法 | 角色、點數、一次性發布及請假轉移均有單元／整合測試 | 審閱一份發布表和一次調整；確認 `history_weight` 解釋符合學校政策 |
| A-02 | 最近備份可驗證及還原 | strict readiness、`test_backup_restore.py`、write pipeline 第二隔離資料庫；完整 table／Alembic head preflight、跨程序 maintenance lease、失敗後自動回復測試 | 在非正式副本完成一次受監督演練並記錄日期；確認維護期間其他分頁不能寫入 |
| A-03 | 專用電腦、秘密、加密離機位置及責任人 | readiness 只會指出缺口，不會替學校作決定 | 指定電腦、保管人、輪替方式及事故聯絡人 |
| A-04 | 外部存取保持私有或完成 Cloudflare 遠端驗收 | deployment fail-closed tests 證明兩種 server 路線均只綁定 loopback；private WARP 必須有有效 team domain、私有 hostname 且不可混入 public Access 設定，public Access 仍需 Protect with Access、AUD 及公開 Host。UI middleware 拒絕未聲明 Host | 啟用連接器後，以已登記 WARP 裝置、WARP-off、未獲准登記及直接 LAN origin 四條路徑驗收一次 |

## 證據失效規則

- 修改排班政策、交易、備份、PDF、語言、路由復原、Cloudflare Worker／JSONC 或發布驗證器後，必須重新執行完整 12 項發布候選驗證。
- JSON 報告缺少 `humanAcceptanceRequired: true`、任何檢查不是 `pass`，或報告早於最後程式改動，均不可用作發布證據。
- 自動化只使用虛構中文姓名；正式姓名、請假原因、PDF、資料庫、備份及日誌不可上載到公開服務。
