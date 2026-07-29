# 全站語意圖標形態轉變執行基線

**日期：** 2026-07-29
**活動分支：** `codex/rc32-ui-command-id-fix`
**起始提交：** `53e25f18fae1a8148398b20eb4906e7e85f23b93`
**狀態：** 候選實作與本機驗證已完成；只可在全站整合閘門通過後進入受控 commit、候選發布及部署

## 1. 可重現分母

`python -X utf8 scripts/audit_icon_semantics.py` 只量度來源，不能冒充渲染後 DOM 實例：

| 分母 | 數值 |
|---|---:|
| Python literal glyph 名稱 | 77 |
| Literal 互動圖標呼叫點 | 132 |
| Literal 資訊／裝飾圖標呼叫點 | 43 |
| 動態圖標表達式 | 38 |
| Preview story source／destination | 24／24 |
| Persistent pair direction | 8 |

渲染實例由隔離瀏覽器的 `assert_rendered_icon_semantics` 逐頁量度。所有 `.q-btn`、`.q-tab` 與可點擊 `.q-item` 內 Material 圖標，必須取得 `role` 和 `category`；來源呼叫點與 DOM 實例永遠分開報告。

## 2. 唯一語法

每個圖標屬於以下一類：

1. `persistent`：只由真實狀態驅動，例如提示音、主題、播放器與抽屜。
2. `preview`：hover／focus／短觸控預告準確的意圖或結果；離開後回復。
3. `operation lifecycle`：working／success／attention／error 只由真實操作事件驅動。
4. `static`：轉變會誤導時保持原 glyph；可保留標準焦點與色彩回饋。

優先次序為：真實 persistent state > disabled／busy／reduced-motion guard > 暫時 preview。頁面不得建立自己的 timeline 或覆寫共用 glyph 狀態。

## 3. 幾何與動效契約

- 圖標通常留在同一 24×24 slot；按鈕／導航列／卡片 host 不位移、不旋轉、不傾斜、不改尺寸。
- glyph 在中心以 opacity＋scale 收合再展開，總長 180 ms；禁止漂移、彈跳、旋轉和循環動畫。
- Fine pointer：hover 和 focus 採一個聚合狀態，兩者重疊時不會過早回復。
- Coarse touch：只在具有準確 preview 時短暫播放；真實 persistent 狀態改變時立即取消舊 preview。
- Disabled／busy：取消 timeline 並顯示真實 glyph。
- Reduced motion：立即顯示最終狀態，不播放 transition；執行期間切換亦須清理。
- DOM replacement、路由離開與重連：MutationObserver／AbortController／WeakMap 清理，不累積逐按鈕 listener。

## 4. 已採納的故事

### Persistent state

- `volume_off ↔ volume_up`
- `light_mode ↔ dark_mode`
- `play_arrow ↔ pause`
- `menu ↔ close`

Persistent glyph 由 `window.__syIconMotion.setPersistentGlyph` 更新。Hover 不得假裝聲音、主題、播放或抽屜狀態已改變。

### Intent-to-outcome preview

- 導覽：`space_dashboard → dashboard_customize`、`dashboard → view_quilt`、`groups → diversity_3`、`handshake → sync_alt`。
- 工作：`calendar_month → event_available`、`calendar_view_week → event_note`、`edit_calendar → calendar_month`、`edit_note → fact_check`、`save → task_alt`、`picture_as_pdf → file_download`。
- 指引：`help_outline → lightbulb`、`menu_book → auto_stories`、`play_circle → rocket_launch`。
- 系統：`admin_panel_settings → verified_user`、`settings → settings_suggest`、`domain → apartment`、`account_tree → hub`、`build_circle → construction`。
- 工具：`translate → language`、`logout → exit_to_app`、`headphones → graphic_eq`、`support_agent → contact_support`、`mail_outline → forward_to_inbox`、`format_list_bulleted → checklist`。

### 明確拒絕

- `balance → account_balance_wallet`：公平不是財務錢包。
- `pause → stop`：Pause 與 Stop 是不同命令。
- `check_circle_outline → gpp_maybe`：不可把已核實改成不確定。
- `gpp_maybe → cloud_off`、`add_to_drive → cloud_upload`：本機備份不等於雲端服務。
- 表格、姓名、經文、證據、警告與純資訊 glyph：保持靜態，不以 button-level story 假裝可互動。

## 5. 共用接口與所有權

- `nicegui_app/ui/components.py`：`action(..., motion_role, icon_story_to, icon_story_category)`。
- `nicegui_app/assets/motion/sing-yin-icon-story-state.js`：輸入聚合、persistent revision、guard、clear。
- `nicegui_app/assets/motion/sing-yin-motion.js`：唯一 NiceGUI hydration、preview、persistent morph、cleanup 和分類器。
- `nicegui_app/ui/shell.py`：頁首、手機工具與抽屜的真實狀態橋接。
- `nicegui_app/ui/music.py`：只有播放器確認 `playing` 才顯示 `graphic_eq`。
- `cloudflare/roster_viewer/worker.js`：公共入口採相同幾何語法，但不載入第二套 runtime。

## 6. 驗證閘門

- 狀態機：快速 reversal、pointer／focus 重疊、persistent 覆蓋、disabled／busy／reduced、DOM replacement。
- 原始碼：Python／JavaScript 語法、語意清單、禁用誤導配對、無頁面局部 GSAP。
- 瀏覽器：Admin／Guest、繁中／英文、淺／深、桌面／平板／手機、pointer／focus／touch、reduced motion、forced colours。
- 幾何：persistent glyph 轉變前後 host bounding box 不變；抽屜初次 hydration 不播放入場動畫。
- 清理：二十次路由／DOM replacement 後 listener、timer、timeline 和 detached host 不累積。
- 公共入口：主題狀態轉變不旋轉 host，公開檢視器維持安靜文件表面。

本文件是執行契約，不是視覺候選清單。任何新增配對都必須先證明語意準確、狀態來源真實、無障礙資訊完整及清理邊界成立。
