# 全站誠實等待體驗與登入入口執行契約

**制定：** 2026-07-30
**實作基線：** `origin/main`／`fa452e7`
**候選分支：** `codex/whole-site-waiting-experience`

## 1. 目前狀態與真正缺口

- 公開入口已有 Admin busy spinner、`aria-busy`、450ms 音樂上限、防雙擊和 `pageshow` reset；Guest 由同一導向控制器啟動，但沒有同等可見 busy 狀態。
- Workbench 已集中使用 `_run_with_progress`，並把正式工作移出 UI event loop；現有固定 `0.14 → 0.56 → 1.0` bar 是視覺階段值，不是服務量度，須改為誠實 indeterminate／phased 呈現。
- 官方 `nicegui_app/ui` 共有 136 個 `ui.button` 呼叫：132 個有 literal icon。4 個例外是兩個低風險 Cancel、隱藏 theme resolver，以及內含自有 `ui.icon` 的 workflow navigation control。目標是100%分類，不是為四個合理例外強塞圖標。
- 既有 semantic motion runtime、按壓材質、圖標 lifecycle、Admin／Guest adapters、Cloudflare Access 和 SQLite transaction boundary 均保留。

## 2. 唯一等待分類

| 類型 | 元件所有者 | 使用情境 | 禁止事項 |
|---|---|---|---|
| `entry` | Worker welcome-entry controller | Admin／Guest identity navigation | 假百分比、音樂錯誤冒充登入錯誤 |
| `inline` | shared `progress_state` | measured-slow read／check | 未知布局 skeleton、阻塞整頁 |
| `operation` | NiceGUI progress coordinator | durable write／backup／restore／export build | page-local dialog、可重複提交 |
| `determinate` | coordinator plus real service measurement | rows／pages／bytes with true total | 固定時間推進、虛構 ETA |
| `media` | existing music controller | starting／playing／blocked／loading／error | 全站 progress、阻塞身份導向 |
| `viewer` | Worker encrypted-view state | KV read／decrypt／render | 裝飾性永久 pulse、把 bearer viewer 當帳戶 |

Every lifecycle terminates in success, attention, error or reset and disposes its timers／listeners. Reduced motion is a static state, not a second behavior model.

## 3. Implementation ownership

- `cloudflare/roster_viewer/worker.js`: role-aware entry state, delayed track, slow watchdog, login-assistance disclosure and Viewer state cleanup.
- `nicegui_app/ui/page_shared.py`: one compatible operation-progress interface; indeterminate by default, true determinate only with real measurements, focus restoration and operation references.
- Shared token／component CSS: progress track, busy, slow, success and error roles in light, dark, forced-colour and reduced-motion states.
- i18n catalog: complete Traditional Chinese／English entry, slow, phase and recovery copy.
- Tests and browser scripts: normal, rejected media, timeout, duplicate, back-navigation, conflict, committed-without-backup, reduced motion, forced colours and lifecycle cleanup.

## 4. Acceptance boundary

- Admin and Guest expose equivalent waiting quality without changing `/auth/login`, `/guest`, One-time PIN, allowlist, signed principal or storage policy.
- No operation shows a numeric percentage without a real bounded value. No fast action is delayed to display motion.
- Busy controls cannot be activated twice; writes whose outcome is unknown are never auto-retried.
- Desktop light／dark, 320px, 390px, tablet, keyboard, reduced motion and forced colours retain readable bilingual status with no layout shift or console error.
- Machine evidence, exact-source release evidence, deployment evidence and supervised human acceptance remain separate claims.
