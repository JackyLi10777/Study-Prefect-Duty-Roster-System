# R5 獨立審計報告 — Codex 代碼質量深度審查

**Round:** 5（脫離 Codex 審計框架，獨立判斷）
**Date:** 2026-07-27
**Commit:** `a3c45ba` (codex/rc31-unified-theme-controls)
**Working tree:** 44 modified files, 2 untracked
**Scope:** 568 tracked files（245 Python, 9 JS/TS, 10 CSS, 16 PowerShell, 49 Markdown, 100 tests）

---

## 執行裁決

**BLOCKED** — 測試套件有 2 個失敗，由本次工作樹中 `worker.js` 的主題切換改動引起合約測試不匹配。

### 五個最重要結論

1. **Codex 在 OS 主題切換時靜默重載頁面，無形中丟失未保存的表單數據** — 當用戶的 `theme_preference="system"`（預設值）時，OS 主題變化會觸發 `ui.navigate.reload()` 而無 dirty-form 警告。語言切換有此保護，主題重載卻沒有。
2. **"系統"主題狀態在 UI 上不可達** — a3c45ba 提交標題為"Unify light and dark theme controls"，但實際上將 3 態切換退回到 2 態（light↔dark）。用戶一旦點擊一次切換，就被永久鎖定在顯式模式，無法回到"跟隨系統"。
3. **"統一"的聲稱被誇大** — Worker 登入頁和 NiceGUI 儀表板使用完全不同的持久化層（localStorage vs preference adapter），不共享 BroadcastChannel。兩者可以在視覺上漂移。
4. **PNG 附件的 EXIF 元數據未清理** — 支援表單允許 PNG 上傳並通過 magic-byte 驗證，但 EXIF 中的 GPS/創建者/設備信息可以洩漏個人隱私。威脅模型文檔未覆蓋此風險。
5. **遷移 0011 的 downgrade 函數被部署後修改** — rc.20 部署了舊的 guard 邏輯，後續提交修改了 downgrade 函數。雖然 upgrade 路徑不受影響，但遷移不可變性原則被違反。

---

## 發現清單

### P1 — 高優先級

**R5-001: OS 主題切換導致靜默頁面重載，丟失未保存表單數據**
- Commit: `a3c45ba`
- File: `nicegui_app/ui/shell.py:547-555`
- Codex 做：添加了 `_remember_system_theme_resolution` → `ui.navigate.reload()`，當 OS 主題變化時觸發。
- 問題：語言切換有 dirty-form guard（`shell.py:472-481`），主題重載沒有。用戶在系統主題模式下編輯草稿時 OS 自動切換（如 macOS 日落），所有未保存輸入丟失。
- 修正：在 `_remember_system_theme_resolution` 中加入同樣的 dirty-form guard。
- 嚴重度：P1（數據丟失，雖然需要特定條件觸發）

**R5-002: 測試合約不匹配 — worker.js 改動未同步測試**
- File: `cloudflare/roster_viewer/worker.js:1904` + `tests/test_cloudflare_roster_viewer.py:329`
- Codex 做：改了 `EXPLICIT_THEME_STATES` 從 `['light','dark']` 到 `['system','light','dark']`。
- 問題：測試仍期望舊值 `['light','dark']`。測試套件有 2 個失敗。這是部署前必須修復的阻塞項。
- 修正：更新 `test_cloudflare_roster_viewer.py:329` 為新的值。
- 嚴重度：P1（測試套件紅燈，阻塞發布）

### P2 — 中優先級

**R5-003: "系統"主題狀態從 UI 不可達**
- Commit: `a3c45ba`
- File: `nicegui_app/ui/theme.py:79-89`
- Codex 做：`next_explicit_theme` 只返回 `light` 或 `dark`，永不返回 `system`。
- 問題：用戶一旦點擊切換按鈕就永久鎖定在顯式模式，無法回到"跟隨系統"。先前 `74b84f4` 有 3 態 `<select>`，a3c45ba 退回 2 態。
- 修正：提供二級選單或設置頁面讓用戶回到 system 模式。
- 嚴重度：P2（UX 回退，非數據問題）

**R5-004: "統一"聲稱被誇大 — 兩個平行主題系統仍會漂移**
- Commit: `a3c45ba`
- Files: `shell.py:615` (BroadcastChannel) vs `worker.js` (localStorage)
- Codex 做：提交標題為"Unify"，但 Worker 和 NiceGUI 使用不同持久化層。
- 問題：同時打開登入頁和儀表板時，在一個頁面切換主題不會更新另一個。
- 修正：在文檔中明確聲明跨表面同步不是目標，或共享 cookie。
- 嚴重度：P2（文檔/期望管理問題）

**R5-005: MutationObserver 無去抖 — 主題切換期間 sync() 可能閃爍**
- Commit: `a3c45ba`
- File: `nicegui_app/ui/shell.py:663-664`
- 問題：body class 變化監聽器在 Quasar 220ms 主題過渡期間多次調用 `sync()`，更新所有按鈕的 aria-pressed/label/icon。
- 修正：用 `requestAnimationFrame` 去抖，或只監聽 `data-theme-resolved`/`data-theme-preference`。
- 嚴重度：P2（性能閃爍）

**R5-006: PNG 附件 EXIF 元數據未清理 — 隱私殘留風險**
- Commit: `e1bee59`
- File: `nicegui_app/services/support_incidents.py:104`
- 問題：PNG 驗證只檢查 magic bytes。512KB PNG 可包含 GPS、創建者名、相機序列號等 EXIF/PII。
- 修正：可選地用 Pillow 清除 EXIF，或在文檔中記錄殘留風險。
- 嚴重度：P2（隱私殘留，未被威脅模型覆蓋）

**R5-007: 遷移 0011 downgrade 函數在部署後被修改**
- Commit: 工作樹修改 `migrations/versions/0011_assist_assignment_mode.py:34-45`
- Codex 做：反轉了 guard 邏輯。rc.20 部署了舊版本。
- 問題：遷移不可變性原則被違反。雖然 upgrade 路徑不受影響（只有 upgrade 在生產上跑過），但已部署的 migration source 不再與 HEAD source 匹配。
- 修正：在發布說明中記錄此更正，或作為新 RC 的一部分發布。
- 嚴重度：P2（不可變性衛生問題）

### P3 — 低優先級

**R5-008: DP 排班器失去具體不可行診斷**
- File: `packages/roster_core/roster_core/generator.py:771`
- Codex 做：將貪婪算法的具體錯誤消息（"Room 303 on Monday has no eligible prefect"）改為通用消息。
- 問題：操作員失去可操作的失敗原因。
- 嚴重度：P3

**R5-009: 公開主題切換 aria-label 失去動作動詞**
- File: `cloudflare/roster_viewer/worker.js:1951-1952`
- Codex 做：從 "切換至深色模式"（動作）改為 "深色模式"（狀態）。
- 問題：螢幕閱讀器用戶失去動作語意。
- 嚴重度：P3

**R5-010: 6 個孤立 i18n 鍵**
- File: `nicegui_app/ui/i18n_catalog/foundation.py:46-51`
- 確認無調用者的鍵：`appearance`, `choose_appearance`, `theme_system`, `theme_light`, `theme_dark`, `theme_current`。
- 嚴重度：P3

**R5-011: Admin 剪貼板複製無錯誤回退（Guest 有）**
- File: `nicegui_app/ui/page_routes/support.py:372-374`
- 問題：Admin 路徑無 try/catch，Guest 路徑有。不一致。
- 嚴重度：P3

**R5-012: PROJECT_STATUS.md:67 過時的現行版本聲稱**
- File: `PROJECT_STATUS.md:67`
- 問題：稱 "live Windows origin tracks rc26"，但同文件第 88 行稱 rc30 為現行。矛盾。
- 嚴重度：P3

**R5-013: 首次訪問的主題閃爍（FOUC）**
- File: `nicegui_app/ui/theme.py:42-65`
- 問題：首渲染預設 light，50-200ms 後 JS 解析到 dark 時重載。深色模式用戶看到短暫淺色閃爍。
- 嚴重度：P3

---

## API 與幻覺驗證矩陣

| 項目 | 驗證方法 | 結果 | 證據 |
|------|---------|------|------|
| `EXPLICIT_THEME_STATES = ['system','light','dark']` | worker.js 源碼讀取 | ✅ 正確 | matchMedia listener 存在，system 正確處理 |
| `runtimeThemePreference = null` 初始化 | 邏輯推導 | ✅ 安全 | `EXPLICIT_THEME_STATES.includes(null)` 為 false，正確 fallthrough 到 localStorage |
| `_assist_assignment_mode_code` 兩份副本 | 逐行對比 | ✅ 功能相同 | guest_adapter.py:73 和 lifecycle.py:45 邏輯一致，無 bug |
| DeepSeek `deepseek-v4-flash` 模型 | 官方 API 文檔對照 | ✅ 存在 | prefect_import_assistant.py 有真實 urllib POST |
| `BEGIN IMMEDIATE` 序列化寫入 | 源碼搜索 | ✅ 正確 | 21+ 調用點 |
| 遷移 0007→0011 可恢復性 | recovery.py 源碼 | ✅ 正確 | `_REQUIRED_TABLES_BY_REVISION` 精確映射 |
| 虛構辦公室名稱 | test_showcase_truth.py | ✅ 已被主動拒絕 | 測試斷言虛構名稱不在源碼中 |
| ≈10B AI tokens 數據 | showcase.py + i18n_catalog | ✅ 準確 | "9.38B" 在 platform.py:110 |
| Worker 合約測試（源碼字符串） | test_cloudflare_roster_viewer.py | ⚠️ 限制 | 29/30 個測試只驗證源碼字符串存在，非行為驗證 |

---

## 多用戶、併發、存儲、備份、恢復評估

| 維度 | 評估 | 證據 |
|------|------|------|
| 併發寫入 | ✅ 安全 | `_begin_serialized_write` + `BEGIN IMMEDIATE` |
| Admin+Guest 同時操作 | ✅ 隔離 | 記憶體 adapter，不同工作區 |
| 多標籤重複提交 | ✅ 冪等 | 指令收據表 |
| OS 主題切換期間操作 | ⚠️ 數據丟失風險 | R5-001 |
| 備份義務失敗 | ✅ fail-closed | recovery.py 正確處理 |
| 遷移 downgrade 安全性 | ⚠️ 被事後修改 | R5-007 |
| PNG EXIF 洩漏 | ⚠️ 未覆蓋 | R5-006 |

---

## 前端、雙語、無障礙、響應式、主題評估

| 維度 | 評估 |
|------|------|
| 雙語對等 | ✅ 強 |
| 無障礙 | ✅ 強（aria-label、keyboard、focus trap、44px touch targets） |
| 響應式 | ✅ 強（900px 斷點、320px 最小寬度、200% 縮放） |
| 主題切換 | ⚠️ 有問題（R5-001 數據丟失、R5-003 system 不可達、R5-005 閃爍、R5-013 FOUC） |
| Admin/Guest 視覺對等 | ✅ 強 |

---

## 測試、觀測性、文檔、部署缺口

| 缺口 | 嚴重度 |
|------|--------|
| 2 個測試失敗（worker.js 合約不匹配） | P1 — 阻塞 |
| Worker 合約測試只驗證源碼字符串，非行為 | P3 — 限制 |
| 6 個孤立 i18n 鍵未清理 | P3 |
| PROJECT_STATUS.md 版本聲稱過時 | P3 |

---

## 優先修復積壓

### 立即阻塞（部署前必須修復）
1. **R5-002** — 更新 `test_cloudflare_roster_viewer.py` 匹配新的 `EXPLICIT_THEME_STATES`

### 下一個 RC 的改進
2. **R5-001** — 在 `_remember_system_theme_resolution` 中加入 dirty-form guard
3. **R5-003** — 提供 UI 路徑回到 system 主題模式
4. **R5-005** — MutationObserver 去抖
5. **R5-006** — PNG EXIF 清理或文檔記錄殘留風險
6. **R5-007** — 在發布說明中記錄遷移 0011 的 downgrade 更正

### 可選清理
7. **R5-004** — 文檔明確跨表面主題同步不是目標
8. **R5-008** — 恢復 DP 排班器的具體錯誤消息
9. **R5-009** — 恢復公開按鈕的 "切換至" 動詞
10. **R5-010** — 移除孤立 i18n 鍵
11. **R5-011** — Admin 剪貼板添加 try/catch
12. **R5-012** — 修正 PROJECT_STATUS.md 過時聲稱
13. **R5-013** — 添加 blocking script 防止首渲染主題閃爍

---

## 殘留不確定性

| 未檢查項 | 原因 | 需要的下一步證據 |
|---------|------|-----------------|
| 跨表面主題同步的實際用戶影響 | 需要真實多用戶瀏覽器測試 | 在兩個瀏覽器同時測試登入頁和儀表板 |
| PNG EXIF 在實際使用中的洩漏概率 | 需要分析實際附件 | 檢查生產環境中已提交的支援報告 |
| MutationObserver 閃爍的可感知性 | 需要真實瀏覽器性能分析 | Chrome DevTools Performance 記錄主題切換 |
| 首渲染 FOUC 的實際持續時間 | 需要真實網絡條件測量 | Lighthouse + 3G throttle |

---

## R1-R5 累計發現統計

| 輪次 | P0 | P1 | P2 | P3 | 總計 |
|------|-----|-----|-----|-----|------|
| R1 | 3 | 5 | 5 | 3 | 16 |
| R2 | 0 | 0 | 3 | 2 | 5 |
| R3 | 3 | 4 | 6 | 4 | 17 |
| R4 | 0 | 2 | 7 | 8 | 17 |
| **R5** | **0** | **2** | **5** | **6** | **13** |
| 合計唯一 | 6 | 13 | 26 | 23 | **68** |

*R5 的 2 個 P1 是由本次工作樹的 worker.js 改動引起的測試合約不匹配和 OS 主題重載數據丟失。*

---

報告完成。未修改任何代碼。未執行部署。