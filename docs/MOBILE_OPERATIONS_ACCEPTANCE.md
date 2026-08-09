# 手機操作驗收 / Mobile operations acceptance

本文件描述 `codex/mobile-first-operations` 的候選契約。它不是部署記錄；目前正式版本、schema、Worker 與備份只以 [`status/CURRENT_STATUS.md`](status/CURRENT_STATUS.md) 為準。

## 主要真人流程

在 390×844 的實體 Android Chrome，以 Guest 虛構資料先完成一次，再由獲准 Admin 使用批准的非正式測試週重做：

1. 開啟「更多」，確認快速設定是 2×2 圓角方格，沒有橢圓光圈、逐字直排、永久 hover 或被遮住仍可點擊的底部導航。
2. 切換語言、提示音及系統／淺色／深色；關閉抽屜後焦點回到「更多」，表單及週次不被清空。
3. 在 `/rosters` 選週次、設定全天停開及請假、閱讀規則摘要、核對阻擋原因，再生成草稿。
4. 以星期列切換日期，點擊一個崗位，在 bottom sheet 以中文一字聯想人選；再演練空缺、單格不開放、復原及重新套用。
5. 核對只有一個固定操作面；軟鍵盤、bottom sheet、dirty-save dock 與底部導航互不遮擋。保存後發布、下載 PDF，並使用頁面內返回鍵回到週表詳情及工作台。
6. 開關 Drawer 20 次、旋轉一次、開關鍵盤一次；確認沒有殘留遮罩、`inert`、重複 close、無法點擊內容或失去焦點。

## 自動化裝置矩陣

| 類型 | Viewport | 必須證明 |
|---|---:|---|
| 極窄重排 | 256×700 | 快速設定單欄、200%文字仍可讀、沒有文字直排或控制項裁切 |
| 窄手機 | 320×760 | 快速設定單欄、16px 輸入、44px 目標、無水平頁面溢出 |
| 一般手機 | 360×800、390×844、412×915、430×932 | 2×2 設定、單日六崗位、星期摘要、bottom sheet、單一固定操作面 |
| 橫向手機 | 844×390 | safe area、星期列、鍵盤／導航不重疊 |
| 觸控平板 | 768×1024、820×1180 | 最多兩欄星期卡片、相同資料與操作順序 |
| 橫向觸控平板 | 1024×768 | 桌面 shell 密度、觸控目標及導航返回路徑共存 |
| 桌面基準 | 1440px | PDF 式矩陣及既有桌面 shell 不回歸 |

每個適用 viewport 都要覆蓋繁中／英文、淺／深／自動、200% 文字、reduced motion、forced colours、console／page error、TTFB、FCP、LCP、CLS、long task 與資源大小。量度只報告真實時間，不加入假百分比或最低動畫時長。

## 發布判定

- 聚焦元件、路由、Admin／Guest exact-week 及 i18n 測試全部通過。
- 隔離真實 Chrome 完成上述矩陣；390px 寫入流程保留輸入、衝突及焦點證據。
- 完整 pytest、依賴安全、staged／release verifier、備份及隔離還原通過。
- PR required checks、不可變 tag、Origin bundle／fingerprint、schema、health／ready 及 Worker 是否需部署的差異判定全部一致。
- 最後仍由首席導學風紀在實體 Android Chrome 完成上方真人流程；自動化不能代簽。
