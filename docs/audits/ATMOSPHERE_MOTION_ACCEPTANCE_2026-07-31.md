# 全路由氣氛、每日聖言與語意動效驗收

**日期：** 2026-07-31

**候選：** `codex/rc42-atmosphere-motion`

**基線：** clean `origin/main`／`22ebe1050721799d76c3adc5c52ab04e956da368`

**狀態：** staged release candidate 已通過完整自動閘門及 Codex 視覺審核；等待 immutable commit／tag 與正式部署證據

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
| Origin backup／isolated restore／health／readiness | Windows deployment report | 待部署 |
| Worker 0%／version smoke／100%／canonical smoke | Worker deployment report | 待部署 |

## 候選閘門證據

- `logs/release-candidate-report.json`：`status=pass`，SHA-256 `416b9e0586173c45d38cd1cb520b98efd9921f4482dc5fcce11bdba2a11d6ca0`。
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

在正式 tag、backup、isolated restore、origin switch、Worker staged promotion 及 canonical checks 完成前，production 仍是 `PROJECT_STATUS.md` 頂部所列 rc41 pair。本文件不得用「已上線」代替實際 deployment evidence。
