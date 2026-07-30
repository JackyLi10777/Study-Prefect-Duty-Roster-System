# 語意圖標與動作回饋覆蓋審計

**日期：** 2026-07-30

**候選分支：** `codex/semantic-icon-action-motion`

**候選基線：** `origin/main`／`ebe8d0c3219d9af40f8c44bdae9bf23c51366635`
**狀態：** 已完成本機來源及隔離瀏覽器驗證；未 commit、未 push、未部署、未完成受監督真人驗收

本審計把三種證據分開：來源呼叫點是可重現的程式盤點；瀏覽器數字是指定頁面當刻的渲染實例；正式線上狀態仍以 `PROJECT_STATUS.md` 所列 rc39 origin／Worker 為準。任一種證據都不可冒充另外兩種。

## 決策摘要

- 使用同一套 Material glyph、共享 NiceGUI runtime 及固定圖標槽，不加入第二個動畫框架。
- 互動語法分為 `persistent`、`preview`、`lifecycle`、`role`、`static`；真實持久狀態和真實操作結果永遠優先。
- 設定齒輪是唯一有界旋轉例外：hover／focus 只旋轉 glyph 70°，啟動時單次 270°；按鈕 host、文字與佈局不旋轉，active route 穩定，reduced motion 靜止。
- 動作按鈕以固定 footprint 顯示 working／success／attention／error；只有 `sy:feedback` 真實事件可改變結果 glyph，超時後回復來源。
- 未設定「重要操作提示音」時有效預設為開啟；明確開啟或關閉永遠保留，讀取預設不會回寫偏好。頁面載入、hover、錯誤及裝飾不發聲。

## 可重現來源盤點

執行 `python -X utf8 scripts/audit_icon_semantics.py`：

| 分母 | 數量 |
|---|---:|
| Python literal glyph 名稱 | 77 |
| Literal 互動圖標呼叫點 | 132 |
| Literal 資訊／裝飾圖標呼叫點 | 43 |
| 動態圖標表達式 | 38 |
| Preview story source／destination | 23／23 |
| Persistent pair direction | 8 |
| Mandatory control contract | 19 |
| Mandatory full-story contract | 16 |
| Mandatory role-only contract | 3 |

`nicegui_app.ui.icon_motion_contract` 是下列 19 個必需控制的可執行追蹤清單。它記錄 route、可見標籤鍵、呼叫點、Admin／Guest／Public 適用面、手機行為、來源／結果 glyph、role、category、狀態及 reduced-motion／static 理由。

| 工作域 | 控制 |
|---|---|
| 全域 | 系統設定、提示音、主題、使用說明 |
| 每週工作 | 生成草稿、核對／發布、已發布後請假、歷史／撤回 |
| 名單與公平 | 匯入、公平核對、新增／編輯／封存導學風紀 |
| 交接與復原 | 新學年名單、備份／還原、驗收指引、已驗證快照 |
| 經文與支援 | 換一篇經文、臨時問題報告 |

## 隔離瀏覽器證據

`python -X utf8 scripts/verify_semantic_icon_motion.py` 使用臨時 SQLite／備份／日誌及虛構資料，結果 `pass`：

| 情境 | Preview | Persistent | Lifecycle | Role | Static |
|---|---:|---:|---:|---:|---:|
| Admin 1440px light | 17 | 7 | 2 | 10 | 0 |
| Admin 20 次路由循環後 | 19 | 7 | 1 | 10 | 0 |
| Guest 390px dark | 19 | 7 | 2 | 10 | 0 |
| Admin 768px dark + forced colours | 17 | 7 | 2 | 10 | 0 |
| Guest 320px light + reduced motion | 19 | 7 | 2 | 10 | 0 |

同一驗證亦證明：

- 設定齒輪 hover／快速連續啟動後回到穩定 glyph，host 尺寸不變；
- lifecycle 控制由 `support_agent` 進入 `hourglass_top`，收到真實成功事件後顯示 `task_alt`，再回復來源；
- 未設定提示音顯示 `volume_up`，操作後顯示 `volume_off`；
- 20 次路由替換沒有殘留失控的語意屬性或圖標 host；
- reduced motion 直接顯示靜態最終狀態，forced colours 保留系統輪廓與焦點。

Public／Viewer 不載入 NiceGUI GSAP runtime。Worker 使用較小的固定槽 SVG 狀態實作；Deno 合約核對主題真實狀態、經文刷新、reduced-motion 及禁止經文 glyph 旋轉。公開 Viewer 繼續是安靜的唯讀文件表面。

## 剩餘風險與真人驗收

- 自動測試證明元件和狀態契約，不代表每一個真實業務結果已由真人逐一觀看。
- 真實滑鼠、鍵盤、觸控與輔助技術仍需由首席導學風紀／顧問老師完成受監督驗收。
- 本分支沒有建立 release tag、正式備份、origin bundle 或 Worker 版本；正式 rc39 不受本分支影響。
