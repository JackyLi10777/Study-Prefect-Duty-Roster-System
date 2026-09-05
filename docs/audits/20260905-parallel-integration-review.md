# 並行更新整合審查（2026-09-05）

這份文件記錄一次開發版本審查，並非正式發布或實體手機驗收證明。
後續提交可能已修正下列問題；整合時必須對最終來源重新核對。

## 審查來源

- protected main：`c5ab76ed1ec5ee998749703f39906400d0c710c3`。
- PNG／手機操作線：`codex/unified-hours-mobile-final`，固定審查提交 `8fd3b28`。
- 效能／發布驗證線：`codex/unified-hours-mobile-overhaul`，`ecdf7ae` 加當時未提交差異；仍在進行。
- `4dd134e` 與 `ecdf7ae` 的 Git tree 相同：`04b1af5b41df305a08a7ca2131bebdb2c83b810a`。
  它們是同一批修改的不同歷史，不應重複套用。
- 原始 `D:\code_v3` 的既有未提交內容未動。

審查採用 code-review、codebase-design、check-work 的行為與介面檢查，
以及隔離的 JavaScript／瀏覽器復現。沒有將測試通過視為已完成部署。

## 必須收斂的問題

| 編號 | 優先級 | 證據及使用者影響 | 修正與驗收 |
|---|---|---|---|
| R1 | P1 | overhaul 的 `verify_release_candidate.py` 新執行 `generated_web_assets`、`public_viewer_mobile_release_gate`，但宣告及 Windows 部署清單仍為原來 15 項；產生 17 項的 pass 報告會被 reader／部署器拒絕。 | 同步執行、宣告、reader 與部署器契約；產生 pass 前驗證精確清單和順序。注入漏項、多項、重複、錯序、失敗時都必須失敗。 |
| R2 | P1 | overhaul 刪除 PNG renderer、native file share 和相應測試；final 的匯出介面仍依賴它們。 | 保留 renderer、POST ticket 交付、分享橋和測試為一組；禁止整檔覆蓋 main.py／page_shared.py 後漏回 PNG。正式及 Guest 均下載驗證。 |
| R3 | P1 | overhaul 的調整收據提供恢復，但選項排除了 vacant；Official／Guest 的既有調整命令亦拒絕非 active assignment。 | 增加具版本檢查、冪等及補償記帳的 vacant-slot 恢復命令，並接收據；驗證發布→空缺→恢復原人／合資格替補→報告與公平帳一致。Guest 記憶體復現已確認現況會拒絕恢復。 |
| R4 | P1 | final 的名冊匯入會先 flush 未保存編輯，兩種匯入提交前亦重新檢查；overhaul 整檔替換會丟掉此保護。 | 保留 final 的匯入保護並移入必要的懶掛載。模擬編輯保存失敗後進入文字／檔案匯入，禁止提交並保留編輯。 |
| R5 | P1 | 兩線的週表編輯器及 mobile verifier 已分歧；overhaul 的整檔替換會丟掉 final 的重新開日導航、原子讀取、局部編輯、每路由 5 次量測、草稿及 PNG lifecycle 驗證。 | final 已驗證的操作作為功能參考，按區塊整合生成頁、收據及資產改進；保留所有已接受的行為門檻。反覆關閉／開放日期、undo／redo、候選切換及匯出。 |
| R6 | P2 | final `page_shared.py` 的匯出使用原生 modal dialog，但進度仍是掛在 body 的 Quasar portal；portal 被原生 top layer 遮住，且無法取得焦點。 | 將進度、錯誤編號及重試置於匯出 sheet 內，或使用明確擁有者的原生 status dialog。以延遲及失敗 renderer 實測；提高 z-index 無效。隔離 Chrome 已重現覆蓋及焦點限制。 |
| R7 | P2 | final 首次預覽 draft 不建立 native-share 按鈕，快取 view 以後只更新既有按鈕。另一分頁發布後再生成仍缺少分享。 | 正式模式預先建立控制項，每次新 bundle 依權限與狀態更新。測試 draft 預覽→另一 client 發布→原頁重新生成；Guest 始終不得分享。 |
| R8 | P2 | overhaul Public／Viewer gate 把成功量測寫入一次性 workspace，父報告只留路徑，成功清理又刪掉證據。 | 把不含名冊／密鑰的原始樣本、預算、截圖保存在 run-specific evidence 目錄，父報告記錄摘要、雜湊及來源；workspace 清理後仍能核驗。 |
| R9 | P2 | 核心日期／人員／單元格操作沒有直接量測其間的 50ms 長任務；首屏及抽屜數值不能代替。 | 在指定操作開始前重置觀測、完成後收集 long tasks；注入 80ms 阻塞必須令門檻失敗。保留各路由原來的 p75 與記憶體循環檢查。 |
| R10 | P2 | 內部 fairness PDF 分開讀取週表、累計公平及 assignments；並行發布／撤回時可能混合不同版本。此為 main 已存在問題。 | 增加一次 read transaction 的 audit snapshot；在並行寫入測試中，報告所有數字與來源必須一致。 |

## 本審查分支已處理

- `shell.py`：可見分頁保留 45 秒核對；隱藏分頁取消一般 poll timer，返回立即核對。
  到期 timer、跨分頁登出與伺服器寫入權限檢查繼續生效。
- 已停止的 monitor 忽略晚到回應，避免重新建立 timer 或覆寫新頁狀態。
- `verify_release_candidate.py`：pass 前檢查實際 checks 與宣告精確一致且全部成功。
  這防止 R1 的假 pass；整合新增兩個 gate 時仍須同步 Windows 部署清單。
- 新增執行實際注入 JavaScript 的 Admin／Guest 行為測試，以及 release main 的報告完整性測試。

## 本分支驗證結果

- `tests/test_auth_status_runtime.py`：Admin／Guest × 13 個生命週期及失敗情境，共 26 項通過。
  包含隱藏／返回、到期、撤銷、跨分頁登出、晚到 fetch／JSON、重複安裝、網路失敗及登出重試。
- `tests/test_release_verifier.py` 新增 6 個完成報告情境：完整成功，以及多項、漏項、重複、錯序、失敗的拒絕。
- 基準 `c5ab76e` 的原始 auth script 在新增的 hidden 與 late-response 情境均失敗；修正後通過。
- 隔離 Chromium／WebKit，各以 Admin／Guest、390×844 執行實際注入 script。
  虛擬時鐘及受控 visibility 模擬下，初始隱藏 3 分鐘及每次隱藏 90 秒均無 poll；
  20 次返回各核對一次；清理後無 poll，無 page error。這不是實體背景分頁／耗電或全站瀏覽器驗收。
- `python -X utf8 scripts/verify_update.py --staged --max-workers 2`：full pre-push profile 的
  diff、governance、完整 Python suite、Worker contract、repository hygiene、security gates 全部通過。
  此報告明確記錄 `formalReleaseExecuted: false`；正式 release drill 尚未執行。

## 尚未完成的證據

兩個來源任務仍在修改，尚無包含全部成果的最終合併提交。
本次審查未執行正式部署、受批准 WhatsApp 群換圖、實體 Android／iPhone 驗收或正式加密備份恢復。
完整整合順序與業務需求見 [執行計劃](../plans/20260905-system-integration.md)。
