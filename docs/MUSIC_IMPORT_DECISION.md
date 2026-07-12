# YouTube 本機音訊匯入技術決定

**狀態：** 已採納  
**日期：** 2026-07-12  
**擁有者：** 李創杰與 Codex

## Capability

- **工作成果：** 首席導學風紀可在「設定」貼上 YouTube／YouTube Music 分享連結，把獲准使用的音訊保存到本機歌庫，毋須離開網站整理輸出位置。
- **必要介面與限制：** Windows 專用主機、NiceGUI/Python、HTTPS YouTube 影片或公開歌單、M4A、本機固定路徑、非阻塞 UI、雙語狀態、不登入帳戶、不讀取 cookies、不接觸排班資料。
- **必須具備：** 影片及歌單連結、固定輸出、重複偵測、每檔 25 MB、每次最多 25 首及 150 MB、失敗安全清理、可移除及重新匯入。
- **非目標：** 私人影片、會員內容、帳戶登入、繞過地區或權限限制、影片保存、背景自動下載、把音樂納入排班備份。
- **淘汰條件：** 只能由另一個 GUI 手動完成、不能可靠指定輸出、要求把 cookies/密碼交給網站、或失敗會阻塞 NiceGUI。
- **決策期限：** v1.1；日後由下一任首席導學風紀按測試及維護狀態覆核。

## Search Scope

- **截至：** 2026-07-12。
- **類別：** Windows 圖形下載器、跨平台圖形下載器、可嵌入 Python/CLI 下載核心、現有可見 YouTube 播放器及本機上傳功能。
- **主要來源：** 三個專案的官方 GitHub repository、README、release、license 及程式進入點。
- **內部能力：** `online_music.py` 已保存及播放公開歌單；`music_library.py` 已驗證本機音訊及管理頁面分類。

## Candidate Matrix

| Candidate | 類別 | 功能切合 | 維護狀態（核對時） | 整合 | 授權／資料 | 決定 |
|---|---|---|---|---|---|---|
| `shaked6540/YoutubePlaylistDownloader` | Windows WPF GUI | 能下載影片、頻道及歌單並轉檔 | 1.9.33，2026-02-13；Apache-2.0 | 沒有穩定 CLI/嵌入介面；輸出及進度仍由另一視窗負責 | 不應把其 GUI 假裝成網站內工作流 | 保留為人工備援，不作正式適配層 |
| `Tyrrrz/YoutubeDownloader` | Avalonia 跨平台 GUI | 支援 URL、歌單、搜尋、格式及標籤 | 1.16.4，2026-04-22；MIT；2026-07 仍有更新 | `Program.Main` 啟動完整 GUI，沒有正式批次命令介面 | Core 可重用但會引入 .NET sidecar 及第二套生命週期 | 保留為人工備援，不嵌入 NiceGUI |
| `yt-dlp` Python wheel + Deno wheel | CLI／可嵌入核心 | URL、歌單、輸出模板、格式及限制均可由程式控制 | yt-dlp 2026.7.4；Deno 2.9.2；上游持續更新 | 與現有 Python runtime 直接整合；可鎖版本及 mock 測試 | 本實作禁用 cookies/登入，只接受 YouTube HTTPS URL；Deno 提供格式解析 runtime | **採用** |
| 現有可見播放器 | 官方 iframe | 最適合線上播放，無本機副本 | 已實作 | 無下載，保持完整控制窗 | 不接觸本機檔案 | 保留並與本機匯入並列 |

## Decision

- **方式：** Hybrid。保留官方可見播放器作日常線上播放；採用鎖定的 `yt-dlp` Python wheel作受控本機匯入；兩個建議 GUI 工具只作網站故障時的人工備援。
- **原因：** 只有此方案能在既有 Python/NiceGUI 生命週期內固定 `music/youtube-imports/`、限制數量及大小、提供真實等待狀態、完成後立即進入頁面歌單，且可在沒有網絡的單元測試中完整驗證。
- **離場路徑：** `YouTubeAudioImporter` 是獨立 adapter。若上游不可維護，可替換其 downloader factory，`MusicLibrary`、UI、檔案位置及排班邊界毋須改動。
- **會改變決定的條件：** 其中一個 GUI 專案提供有版本承諾、可設定輸出及可觀察進度的正式 CLI/API；或 YouTube 格式改變令無 FFmpeg 的 M4A 路徑不再可靠。

## Proof of Concept

- URL 驗證涵蓋 `youtube.com`、`music.youtube.com`、`youtu.be`、Shorts 及公開歌單。
- 假下載器測試證明 25 首／25 MB／150 MB 邊界、無 cookie/密碼選項、固定 staging、M4A 簽名驗證、重複 source ID 及清理。
- NiceGUI 瀏覽器驗證只檢查操作入口、雙語、鍵盤、深淺模式及手機排列；不在 CI 下載外部音樂。
- 真機驗收以操作者獲准使用的短測試連結進行一次，確認可下載、播放、移除及重新匯入。

## Sources

| Source | Owner | 更新／版本 | 2026-07-12 用途 |
|---|---|---|---|
| https://github.com/shaked6540/YoutubePlaylistDownloader | shaked6540 | 1.9.33 / 2026-02-13 | Windows GUI、格式轉換、Apache-2.0、release 狀態 |
| https://github.com/Tyrrrz/YoutubeDownloader | Tyrrrz | 1.16.4 / 2026-04-22 | Avalonia GUI、YoutubeExplode、跨平台、MIT、程式進入點 |
| https://github.com/yt-dlp/yt-dlp | yt-dlp maintainers | 2026.7.4 | Python/CLI 嵌入、輸出與限制選項、Deno runtime 建議、依賴及授權 |
