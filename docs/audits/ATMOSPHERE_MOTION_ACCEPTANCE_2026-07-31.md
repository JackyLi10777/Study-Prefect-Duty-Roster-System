# 全路由氣氛、每日聖言與語意動效驗收

**日期：** 2026-07-31

**發布來源：** `codex/rc42-atmosphere-motion` → protected `main`／`c8201f33e454d9120c73386642cbf9d737391466` → `v1.2.0-rc.43`

**開發基線：** clean `origin/main`／`22ebe1050721799d76c3adc5c52ab04e956da368`

**狀態：** rc43 已通過完整自動閘門、Codex 視覺審核、immutable Origin 切換、Worker staged rollout 及 canonical smoke；首席導學風紀／教師顧問的受監督真人驗收仍待完成

## 變更邊界

- 新增 `weekly-operations`、`people-fairness`、`administration-recovery`、`support-lifeline` 四組 Light／Dark route-family assets。
- 以同構圖 `devotional-sacred-*-v2.webp` 取代 Daily Verse v1，並重建淺色閱讀面。
- `PageDefinition` 為每個主要頁面指定一個 atmosphere slot 及 `embedded | shell` 呈現方式；子路由沿用其 canonical family shell。
- 旋轉限制於 Settings、Theme、Backup Settings navigation、History、Undo；正式 Restore 及既有 story controls 不疊加旋轉。
- Admin／Guest 共用相同資產、元件及互動品質；身份、權限、Session、SQLite、路由與資料格式不變。

## 資產證據

- [x] 十張新增／替換 WebP 全為 `1600×900`。
- [x] 每檔不超過 180KB，低於 250KB 硬上限。
- [x] 淺／深 companion 尺寸一致，Daily Verse v1 不再由 runtime registry 使用。
- [x] 人工檢視沒有人物、學生、姓名、可讀文字、校徽、商標、水印、假 UI、螢幕內容或可識別校園。
- [x] 提示詞、工具、日期、尺寸、大小、SHA-256、遮罩及禁用位置已寫入 `docs/design/ATMOSPHERE_ASSET_MANIFEST.md`。
- [x] 生成時只提供抽象創作提示及前一張生成 master；沒有上傳資料庫、名單、截圖、日誌或秘密。

## 自動驗收矩陣

| 項目 | 證據 | 狀態 |
|---|---|---|
| Registry／pair／hash／尺寸／大小 | focused pytest＋manifest | 通過 |
| 每個 `PageDefinition` 的 slot／presentation | page catalog contracts | 通過 |
| Shell band 位於 page context 後、內容前且沒有控制 | source＋rendered browser | 通過 |
| 四個 route family 的 Light／Dark computed asset | isolated desktop browser＋Resource Timing | 通過 |
| Daily Verse v2、文字 4.5:1、mobile 16–20% | desktop＋mobile browser | 通過 |
| 旋轉 allowlist、互斥、重複操作、cleanup | pytest＋semantic-motion browser | 通過 |
| tactile switch mouse／keyboard／touch／forced-colours | component＋mobile browser | 通過 |
| 320／390／tablet／desktop、繁中／英文、Light／Dark | release browser matrix | 通過 |
| Python、Deno、security、repository hygiene | staged＋formal release reports | 通過 |
| Origin backup／isolated restore／health／readiness | `windows-release-deployment-v1.2.0-rc.43.json`＋獨立 task／marker 核對 | 通過 |
| Worker 0%／version smoke／100%／canonical smoke | `cloudflare-worker-deployment-v1.2.0-rc.43.json`＋獨立 deployment-status 核對 | 通過 |

## 候選閘門證據

- `logs/release-candidate-report.json`：`status=pass`，綁定 `v1.2.0-rc.43`／commit `c8201f33e454d9120c73386642cbf9d737391466`／tree `11f759908218aee64c9d49024759beadf8ff9f5b`；SHA-256 `6e79ded5ae289bd9c5ecb775aa635109cdbbd12a2b0ebf7f145d72378ab848e9`。
- 15 個 required checks 全部通過，包括 repository hygiene、security gates、53／53 Worker tests、完整 Python suite、主題 16-case browser matrix、桌面／手機 browser、真實 write pipeline、Guest parity／隔離及 partial-backup recovery。
- Resource Timing 證明每個 shell atmosphere route 只下載當前主題資產；候選期間曾偵測到 inactive companion 被下載，修正 head-level theme prepaint 後才放行。
- Runtime performance：初始傳輸 1.26 MiB、route-cycle heap 增長 0.46 MiB、DOM nodes `+0`、listeners `+0`。
- 手機／平板矩陣：390px、320px reduced-motion、256px reflow、844×390 landscape、768×1024、820×1180 及 1024×768 全部通過。
- 八階段隔離寫入演練完成資料匯入、名單修改、請假、草稿、修正、發布、公平帳、雙語 PDF、交接、獨立還原及新學年切換。

## 人工視覺判斷

- [x] 五組淺／深資產在原始解析度逐張檢視，構圖一致、左側安全區可用、不同家族可辨識。
- [x] 在實際頁面核對圖片沒有壓過標題、表格、姓名、公平數據、警告、對話框或控制。
- [x] 在 Daily Verse 淺色頁核對晨光背景不再為了文字而過暗，經文、出處、翻譯及控制清楚。
- [x] 在 320px／390px 核對裁切、圖片強度、無橫向 overflow 及無 CLS。
- [ ] 由首席導學風紀／教師顧問判斷整體氣氛與動效是否精緻但不妨礙工作；此項不由自動 gate 代簽。

## 發布真相

- Origin 排程工作由 `SingYinRosterSvc` 執行 `C:\SingYinRoster\releases\v1.2.0-rc.43-c8201f33e454-5c891432a1d8\.venv\Scripts\python.exe`；marker 的 release／commit／tree 與正式報告一致。
- 切換前快照 `20260731-013103-079514-manual_verified_backup.sqlite3`／SHA-256 `f07306c89e79a610b40105627620c1603b707c39a7ab4cc537217df61c358e1c` 通過隔離還原、公平、行數及 restore-audit 核對。
- Origin `/healthz` 為 `ok`；`/readyz` 為 `ready`、`writeReady=true`、`maintenance=false`、`recoveryRequired=false`、`pendingBackupObligations=0`。
- Worker `394e2205-ae8f-4eef-a13a-e701931e6f0d` 經 0% candidate smoke 後承接 100% 流量；舊 Worker `610092f6-59d4-4fd4-ab3a-3fbf1dd2c64e` 是第一 edge rollback。
- `v1.2.0-rc.42` 與 rc43 同 commit／tree，但沒有 source-bound formal report，亦未部署；rc43 才是本輪唯一正式發布身份。
- 已封存的 rc43 Windows report 之 legacy `previousCommit` 取自 inactive host checkout；實際 pre-switch task marker 為 rc41／`74072b0175ff64807312a8cc5b9cd016b6628210`，回滾以保存的 task action 為準。Post-rc43 deployer 已改為驗證排程工作所指 bundle 的完整 marker／fingerprint，並為未來報告記錄 `previousReleaseRef`／`previousReleaseSource`。
