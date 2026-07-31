# 語意圖標與動作回饋覆蓋審計

**首次審計：** 2026-07-30

**本次修訂：** 2026-07-31

**候選分支：** `codex/rc42-atmosphere-motion`

**基線：** clean `origin/main`／`22ebe1050721799d76c3adc5c52ab04e956da368`

**狀態：** 來源契約已更新；正式發布、部署及受監督真人驗收另以 `PROJECT_STATUS.md` 為準

本審計把來源呼叫點、渲染實例、正式發布及真人觀感分開。來源盤點不能證明瀏覽器動畫；隔離瀏覽器通過不能證明正式主機已部署；正式 deployment 亦不能取代首席導學風紀及教師顧問的觀感與操作驗收。

## 決策摘要

- 全站只使用 Material glyph、共享 NiceGUI motion runtime 及固定圖標槽，不增加第二個動畫框架。
- 每個 host 只可解析一個 `motion_mode`：`static`、`role-only`、`morph-only`、`lifecycle-morph`、`persistent-morph` 或五個受控 rotary mode 之一。
- 旋轉白名單只有五項語意控制：Settings、Light／Dark、Backup Settings navigation、History、Undo。只有真實 Light／Dark 狀態切換可同時 morph＋rotate。
- 實際 Restore 永遠是 lifecycle morph；草稿、發布、匯入、風紀管理、換經文、支援及其他已有明確 glyph story 的操作不得再疊加旋轉。
- 旋轉只作用於 glyph。host、文字、焦點框及佈局固定；busy、disabled、reconnect、DOM removal、dispose 及 reduced-motion 會取消 timeline 並清理 transform。
- 未設定「重要操作提示音」時有效預設為開啟；明確偏好永遠保留。聲音及音樂開關以短暫 inset／thumb 壓縮提供觸覺回饋，不使用常駐脈動。

## 可重現來源盤點

執行 `python -X utf8 scripts/audit_icon_semantics.py`：

| 分母 | 數量 |
|---|---:|
| Python literal glyph 名稱 | 77 |
| Literal 互動圖標呼叫點 | 132 |
| Literal 資訊／裝飾圖標呼叫點 | 44 |
| 動態圖標表達式 | 38 |
| Preview story source／destination | 23／23 |
| Persistent pair direction | 8 |
| Mandatory control contract | 21 |
| Mandatory full-story contract | 16 |
| Mandatory role-only contract | 5 |
| Rotary contract | 5 |

`nicegui_app.ui.icon_motion_contract` 記錄每個必要控制的 route、i18n、callsite、Admin／Guest／Public 範圍、手機行為、來源／結果 glyph、category、motion mode、方向、預覽／啟動角度及 reduced-motion 結果。

| 模式 | 控制 | 動作 |
|---|---|---|
| `rotary-only` | Settings | hover／focus 70°；啟動順時針 270°／260ms |
| `persistent-rotary` | Light ↔ Dark | 只在真實狀態改變時 morph＋順時針 90°／180ms；初次載入及 OS reconcile 靜止 |
| `rotary-navigation` | Backup Settings navigation | hover／focus 60°；啟動順時針 180° |
| `rotary-history` | History | hover／focus 逆時針 55°；啟動逆時針 180° |
| `rotary-action` | Undo／withdraw | 啟動逆時針 180°；busy 後由正式進度與結果接管 |
| `lifecycle-morph` | Restore、draft、publish、import、directory、snapshot、verse、support | 只依真實 working／success／attention／error 事件改變 glyph |

「立即建立已驗證快照」與真實 UI 一致使用 `add_to_drive → arrow_forward → hourglass_top／verified`；Backup Settings 的 `settings_backup_restore` 旋轉只代表前往復原設定，不冒充資料已還原。

## 驗證邊界

- 靜態測試核對 exact allowlist、模式互斥、角度、初始主題不播放、操作中止、DOM cleanup、reduced-motion 及 forced-colours。
- `scripts/verify_semantic_icon_motion.py` 以隔離 Admin／Guest、桌面／手機、Light／Dark、forced colours、reduced motion 及 20 次路由循環核對真實 DOM、host 尺寸及殘留 transform。
- Public／Viewer 不載入 NiceGUI GSAP runtime；Worker 只為真實主題狀態使用 180ms 有界 SVG morph／rotation。經文刷新及安全入口圖標不旋轉、不常駐循環。
- 正式線上版本、Worker identity、備份、回退及 canonical smoke 只可從 `PROJECT_STATUS.md` 及 deployment reports 判定。

## 剩餘真人驗收

- 以實體滑鼠、鍵盤、觸控及輔助技術核對旋轉是否有助辨識且不搶奪注意力。
- 在淺／深、繁中／英文及 320px／390px／tablet／desktop 下確認 pressed、busy、success、error 與 reduced-motion 的靜態結果。
- 對任何覺得「為動而動」的控制，優先退回 morph-only 或 static；不得因追求覆蓋率擴大 rotation allowlist。
