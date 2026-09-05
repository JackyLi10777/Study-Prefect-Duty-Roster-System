# 正式啟用需求追蹤與來源帳

本表追蹤 [已批准計劃](20260905-system-integration.md) 的交付，不是部署證明。
狀態：待實作、進行中、本地驗證、已合併、已部署、人工待驗收、已驗收。
不得由上一個狀態推斷下一個狀態；每次關閉需求須寫入來源提交和相應測試。

## 固定來源與採納規則

| 來源 | 固定提交／狀態 | 採納及禁止覆蓋項 |
|---|---|---|
| protected main | `2acf98fe9ec79eb0936857bf72f5235eb23c14e4` | PR #122／#123通過必要CI後合併；已有統一時間／auth／release guard／下載閒置回收；新分支仍須即時 fetch |
| 手機／PNG final | `29ac083fd4d1e9a54854c8fe4436573d0c51fd5b`，2026-09-05 核對 clean | 安全PNG交付、匯入保存保護、原生sheet、調整後匯出owner、關閉候選清理及抽屜取消；逐項比對，不整檔套用 |
| 效能／手機 overhaul | `ecdf7ae` 加未提交工作；尚無最終checkpoint | 等完成SHA；不能用移除PNG／分享橋／測試的版本覆蓋final；保留資產、首屏、名冊、gate改進的行為證據 |
| 本任務 auth修正 | `cb5cccc`，經PR #122合併為 `12d6732` | 背景不poll、返回驗證、到期與撤權、已清理runtime忽略晚到回應 |
| 本任務 release guard | `f8dbc0f`，經PR #122合併為 `12d6732` | 宣告／執行清單精確一致才pass；不代替整合新gate的部署器更新 |
| 下載閒置回收 | `2041310`，經PR #123合併為 `2acf98f` | 最終PR head `8939dbb` 的test-and-audit／analyze通過；保留單次票據、配額及mode/session綁定；未部署 |
| 一致讀取快照 | `7ab0dfc`／`2522680`，本地定向驗證 | SQLite session不等於讀交易；audit／週表／年報共用明確BEGIN，Guest使用單次隔離拷貝；不新增schema；最終全套與CI仍待通過 |
| 發布後空缺恢復 | 獨立 `codex/vacancy-recovery-20260905`，進行中 | 同一版本化命令補入合資格人員，只credit、不再次debit；服務端與手機接合分開驗收 |

`4dd134e` 與 `ecdf7ae` 的 tree 同為 `04b1af5b41df305a08a7ca2131bebdb2c83b810a`。
這是共同底稿，不當作兩份功能重播。完整並行整合尚未完成。

## 需求矩陣

「責任／落點」是實作所屬模組，不代表該功能已存在。

| ID | 階段 | 結果及責任／落點 | 狀態 | 關閉所需證據 |
|---|---|---|---|---|
| SRC-01 | A | 固定來源與按行為去重；本表 | 進行中 | 兩來源SHA及cleanliness、差異、測試和剩餘項；overhaul尚未固定 |
| GOV-01 | A | direct-main工作流；Branch Strategy／AI Guide | 已合併 | PR #122／12d6732；41項文件測試、治理及CI通過；pre-push與release不混用 |
| TIME-01 | A | 全部普通時段15:40–17:00；roster_policy | 已合併 | main c5ab76e；tests/test_roster_policy.py；不等於正式學校啟用 |
| AUTH-01 | B | 背景登入輪詢／晚到回應；shell | 已合併 | PR #122／12d6732；26個Admin/Guest執行實際JS測試；未部署 |
| REL-01 | B | 完成報告拒絕漏項／多項／錯序／失敗 | 已合併 | PR #122／12d6732；6個release完成情境；未部署 |
| REL-02 | B | 資產／Public gate與reader／部署器一致 | 待實作 | 所有gate精確清單、完整執行、失敗注入與清理後可核驗證據 |
| EDIT-01 | B | 局部編輯、候選清理、匯入dirty保護 | 進行中 | final來源功能；合併版重載、切日、匯入失敗、undo/redo瀏覽器測試 |
| ADJUST-01 | B | 空缺恢復、版本／command_id、舊表單鎖定 | 進行中 | 獨立服務端修正；仍需發布→換人／空缺→恢復→撤回的手機閉環，服務分鐘及公平不重複 |
| EXPORT-01 | B | 原生modal內進度／錯誤、發布後分享控制 | 進行中 | 29ac083含owner修正；合併版延遲、失敗、跨分頁發布後分享測試 |
| MODEL-01 | C | 新空庫、日期席位、發布版本；persistence/core | 待實作 | 空庫初始化、約束、重啟及備份還原；無舊業務資料遷入 |
| POLICY-01 | C | 學年政策快照、持久房間／人數／星期／時間 | 待實作 | Room407／406、預設人數、最多20列、設定保存重載及發布快照隔離 |
| POLICY-02 | C | F1持續開關、恢復預設、升學年草稿 | 待實作 | 預設關閉、明確啟用、不自动按考試日期開啟；重設不改已發布結果 |
| WEEK-01 | C | 普通生成／候選／保存／發布採新模型 | 待實作 | 四業務資格規則；20列100格、關閉、空缺及跨模式衝突 |
| GUEST-01 | C | 共享規則與隔離adapter、fixture／policy分版 | 待實作 | 虛構資料、不得正式寫入／上傳／AI／備份／原生分享 |
| REPORT-01 | B/C/D | 日期範圍報告、快照分鐘、單次audit讀取 | 進行中 | B先修並行讀取一致性；普通80／CP185／自訂時間、任意日期範圍、排除無效安排及人工簽核仍待新核心 |
| PNG-01 | C | 原子snapshot的完整雙圖及PDF；與人數設定一併交付 | 待實作 | 1024RGB／1600×2000、6/20列、長姓名、所有狀態、中英、無metadata、確定性≤5MiB |
| PNG-02 | B/C | 頭像快捷下載、詳表分享及狀態隔離 | 待實作 | 90秒POST票據、session/mode/重放/過期、併發、5MiB、取消／失敗回退、舊圖提示 |
| CP-01 | D | CP日期活動、三角色同權、日期不可值班 | 待實作 | 非連續日期、房間可改、人數可改、185分鐘、跨普通同日重複檢查 |
| CP-02 | D | 全期生成→發布→恢復→PDF/PNG→年報 | 待實作 | 三組／最多20席、10日期分頁、CP公平分帳及服務合計；不使用Public v1 |
| MOBILE-01 | E | Shell／Dashboard／Public首屏 | 進行中 | 兩来源待整合；唯一下一步、More先導航、焦點／鍵盤／觸控 |
| MOBILE-02 | E | 名冊／匯入／Audit | 進行中 | 搜尋全域完整、每批20、單人sheet、dirty不丟失、匯入原子提交 |
| MOBILE-03 | E | Handover／Settings／Access／Support | 進行中 | 次級資訊延後，恢復確認不縮短，Admin持久／Guest暫存語義保留 |
| MOBILE-04 | E | 內容頁／Viewer | 進行中 | 單列、延遲掛載、手機按日／打印全表、fragment安全 |
| IDLE-01 | E | 無流量時過期下載釋放；guest_downloads | 已合併 | PR #123／2acf98f；16個新增情境、75項Guest回歸、完整驗證及CI；真timer到期後0records/0timer/thread增量0；未部署 |
| PERF-01 | E | 局部瀏覽器運算、GSAP、observer、靜態資產 | 進行中 | 不下載全名冊、本地預覽不作權威、音頻0B、無boot輪詢、hash cache |
| PERF-02 | E | 全路由／核心操作／idle驗收 | 待實作 | 原預算、5次p75、>50ms操作窗口、20次生命週期、服務器/手機雙端量測 |
| RELEASE-01 | F | exact-main完整release及不可變部署 | 待實作 | clean來源、所有gate、schema/backup/Worker對帳；有Worker變更才candidate |
| HUMAN-01 | F | 正式新庫與實體手機／WhatsApp驗收 | 人工待驗收 | 操作者確認名冊、Android/iPhone、換圖／發圖／版本更新 |
| RECOVERY-01 | F | 受監督加密備份恢復及交接 | 人工待驗收 | 真實恢復設定/名冊/排班/版本/報告；手冊及確認記錄 |

## 已有證據與下一步

本任務 2026-09-05 full pre-push 六項通過，明確 `formalReleaseExecuted=false`。
auth用Chromium／WebKit的受控visibility／時鐘作生命週期檢查，不是實體耗電證據。
`7ab0dfc` 的audit修正通過完整六項驗證；程序內移除BEGIN時兩個官方並行發布／撤回測試會失敗，恢復後通過。`2522680` 補上週表及年報，同分支較廣回歸124 passed／3個來源不適用skip；原始五個並行反例會混用分派／帳本或在新週發布時觸發KeyError。最終提交仍須再跑完整驗證及CI，不能沿用較早結果宣稱全部完成。
final任務回報完整寫入流程通過，但全站手機／效能未完成；這不代替整合提交的測試。
下一步取得overhaul checkpoint，依B的功能群組形成可測試差異，再啟動C的新核心。
不可因目前網站可打開而關閉HUMAN-01或RECOVERY-01。
