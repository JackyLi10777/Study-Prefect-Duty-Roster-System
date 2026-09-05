# F2b2：手機證據分片與新版彙整

## 來源與邊界

- 乾淨來源：protected main `bd8912e27494aec740014b810a285c17b5bc3e56`。
- 獨立分支：`codex/mobile-evidence-assembly-v2-20260905`。
- 已檢視舊 collector checkpoint `94665b2d3a5b5d9affd61f3100e80251bb6de1b7`；
  不移植其 v1 browser adapter、舊頁面或報告。新版只沿用 producer 分工概念。
- 本批不改 UI、資料庫、Worker、效能門檻、release manifest 或部署狀態。
  所有 unit fixtures 均為虛構資料，不可作為真實瀏覽器或發布證據。

## 實作契約

1. 三個 producer 分別擁有 NiceGUI Chromium、workbench WebKit、Public／Viewer
   的固定 scenario/profile；不能自選縮減最終矩陣，不能跨 producer 補寫。
2. 分片版本 2 綁定 contract v2、contract fingerprint、run、logical fixture、
   commit、tree、source fingerprint、clean/diagnostic 狀態。每個 producer
   自行提供實測工具版本和隔離 fixture IDs，缺少則不能通過。
3. coverage、原始 performance、core interactions、cold lifecycle 四項都必須
   明確存在。只有 NiceGUI Chromium 可提供核心互動與八組冷啟動生命週期證據。
4. 不覆寫重複事件、target 或分片；分片檔案採 exclusive create。
   複製入站資料和對外快照，防止呼叫者事後更改已收集樣本。
5. 呼叫者的 context 即使夾帶完整 raw arrays、green status 或 summary，
   也不能注入彙整結果；觀測只能來自通過 ownership/identity 檢查的分片。
6. 每次 gesture 前後都驗證來源與隔離資料；一般 failure/unavailable 也執行
   事後檢查。來源或隔離資料失效立即停止後續 owned gestures，剩餘項列 not_run。
   聚合時任何分片 integrity stop 都令整次結果不能通過。
7. 一般失敗保留原始值，不能挑最佳五次、刪失敗樣本或以 summary 改寫結果。
   lifecycle 的 after-first-mount 診斷不可冒充 before-first-open；v2 validator
   重新檢查八組 twenty-cycle 語義、來源、獨立 contexts、原始 counters 和差值。
8. collector 自身加入 release source fingerprint。聚合使用既有唯一 v2 consumer；
   dirty、diagnostic、不足樣本、缺測、過期契約、超門檻均不能得到 pass。

## 驗證與剩餘工作

- 三個 regression 最初在既有 collect_case_results 失敗：gesture 拋出一般錯誤／
  assertion／unavailable 時，當次事後來源漂移未被記錄；修正後綠燈。
- 新增分片 ownership、重複、混合來源、失敗保留、冷啟動門檻、context 注入、
  immutable file、診斷與正式證據分離測試；保留既有 contract 測試。
- 完整更新驗證、獨立 review 及必要 CI 的 exact-head 結果記錄於 PR，未先寫通過。
- 尚未完成：三個真實 producer 接線、共用全域 integrity-stop coordinator、
  獨立 engine/layout/performance 執行、隔離 Public／Viewer runtime、release gate
  消費 raw 報告、完整受控 p75 與實機矩陣。現有 release runner 仍有 fail-fast
  編排，本批不以彙整工具已存在就宣稱整個 F2 或手機驗收完成。
- 部署和測試站均不變；須整合全部功能、以最新乾淨 main 完成正式驗收後再更新。
