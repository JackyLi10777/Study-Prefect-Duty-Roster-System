# Cloudflare 遠端存取完整設定手冊（Windows 專用主機）

**用途：** 讓獲准使用者在校外瀏覽器安全進入值班表網站。
**架構：** 瀏覽器 → Cloudflare Access 登入 → Cloudflare Tunnel → 主機 `127.0.0.1:8080`。
**不會做的事：** 不開放路由器埠、不把 NiceGUI 改綁 `0.0.0.0`、不公開 SQLite／備份／日誌，也不開放 Windows RDP 3389。

本文件配合三個自動工具：

- `scripts\prepare_cloudflare_remote_access.ps1`：安裝及檢查 `cloudflared`，但不公開網站。
- `scripts\activate_cloudflare_remote_access.ps1`：取得必要資料後才安裝 Tunnel 服務、切換 server 模式及驗證 Access。
- `scripts\verify_cloudflare_access.ps1`：日後隨時重做「未登入者必須先被 Access 攔截」測試。

---

## 0. 先分清兩種「遠端」

本階段建立的是**遠端使用網站**：你可在另一部電腦或手機以 HTTPS 網址登入值班表。這已足夠完成生成、發布、PDF、請假調整及公平核對。

它不是「遙控整部 Windows 桌面」。主機維護仍在主機前完成；不要在家中路由器開放 3389、8080 或任何埠。日後若確實需要無人在場的 Windows 桌面維護，應另作獨立方案及驗收，不與值班表公開網址混在一起。

---

## 1. 只有你必須親自完成的資料

Codex 及專案腳本可以準備本機檔案，但不能替你選擇或登入私人 Cloudflare 帳戶。你只需準備：

1. 一個已加入 Cloudflare 的網域，例如 `example.org`。
2. 一個專用子網域，例如 `roster.example.org`。
3. 允許登入的完整電郵地址名單；不要使用「Everyone」或整個公開電郵網域。
4. Cloudflare Zero Trust 團隊網域，例如 `your-team.cloudflareaccess.com`。
5. Access Application Audience（AUD）標籤。
6. Tunnel 安裝 token。它是秘密，只在啟用腳本的隱藏輸入框貼上一次，不寫入文件、Git 或畫面截圖。

非秘密三項可先抄到 `deployment\cloudflare\REMOTE_ACCESS_VALUES.example` 的私人副本；不要在該檔案加入 token。

---

## 2. 先完成本機主機

在考慮遠端前，必須完成 [Windows 專用主機完整設定手冊](WINDOWS_DEDICATED_HOST_SETUP.md)，並確認：

- `Sing Yin Roster Host` 工作排程存在；
- `http://127.0.0.1:8080` 可正常開啟；
- `/healthz` 顯示 `status : ok`、`database : ok`；
- 已建立至少一個已驗證快照；
- 主機不會睡眠。

以管理員身分開啟 PowerShell：

```powershell
Set-Location C:\SingYinRoster
powershell -ExecutionPolicy Bypass -File scripts\prepare_cloudflare_remote_access.ps1 -InstallCloudflared
```

看到 `Remote-access software is prepared` 只代表軟件已就緒；網站仍是本機模式，這是正常的。

---

## 3. 在 Cloudflare 建立 Access 保護（必須先做）

介面名稱可能隨 Cloudflare 更新而略有不同，但次序不可倒轉：**先 Access，後 Tunnel 啟用。**

1. 登入 Cloudflare Dashboard。
2. 進入 **Zero Trust**。
3. 完成 Zero Trust team name；記下完整 team domain。
4. 在 **Settings → Authentication** 設定登入方法。小型受控名單可使用 Cloudflare One-time PIN；若已有合適身分提供者，也可使用該登入方法。
5. 進入 **Access controls → Applications**。
6. 新增 **Self-hosted application**。
7. Application name 填 `Sing Yin Roster`。
8. Public hostname 填你選定的完整子網域，例如 `roster.example.org`。
9. 建立一條 **Allow** policy：
   - Include 使用 **Emails**；
   - 逐一填入獲准的完整電郵地址；
   - 不要選 Everyone；
   - 不要建立長期 Bypass policy。
10. Session duration 建議 8 小時或更短。
11. 儲存後，在應用程式詳情複製 **Application Audience (AUD) Tag**。

這一步完成後才進入 Tunnel。Cloudflare 官方說明指出 Access policy 決定誰可到達應用程式，而 Bypass 會停用 Access 執行，因此本系統的啟用器要求你明確確認沒有 Everyone／永久 Bypass。

---

## 4. 建立 remotely-managed Tunnel

1. 在 Cloudflare Zero Trust 進入 **Networks／Networking → Tunnels**。
2. 建立 Cloudflare Tunnel，名稱填 `sing-yin-roster-windows`。
3. Connector 選 **Windows**。
4. 在 Tunnel 的 **Public Hostname** 加入與 Access 完全相同的子網域。
5. Service type 選 `HTTP`。
6. URL 填：

```text
http://127.0.0.1:8080
```

7. 儲存。不要填 SQLite、備份或檔案資料夾路徑。
8. 在 Windows connector 安裝命令中，只複製 `service install` 後面的 Tunnel token；不要把整條命令貼入聊天、文件或 Git。

---

## 5. 一次完成本機啟用

以管理員身分開啟 PowerShell：

```powershell
Set-Location C:\SingYinRoster
powershell -ExecutionPolicy Bypass -File scripts\activate_cloudflare_remote_access.ps1 `
  -PublicHostname "roster.example.org" `
  -TeamDomain "your-team.cloudflareaccess.com" `
  -AccessAudience "你的 AUD 標籤"
```

腳本會按以下次序工作：

1. 確認本機 `/healthz` 與資料庫正常；
2. 確認工作排程已存在；
3. 要求你輸入 `ACCESS READY`；
4. 以隱藏方式讀取 Tunnel token；
5. 安裝 `cloudflared` Windows service；
6. 備份 `.env`，產生獨立的隨機 storage secret；
7. 保持 `SING_YIN_HOST=127.0.0.1`，只把應用程式切到受控 server mode；
8. 重啟 NiceGUI 工作排程；
9. 從未登入狀態測試公開網址；
10. 只有看到 Cloudflare Access 登入重新導向才報告成功。

若第 9 步沒有被 Access 攔截，腳本會停止 `cloudflared`、還原舊 `.env` 並把 NiceGUI 退回原狀。不要繞過這個失敗封鎖。

---

## 6. 真人驗收

### 6.1 未登入測試

1. 開啟 Edge InPrivate 或 Chrome 無痕視窗。
2. 輸入 `https://roster.example.org`。
3. 必須先出現 Cloudflare Access 登入頁，不可直接看到值班表。

### 6.2 獲准帳戶測試

1. 以 Allow policy 內的帳戶登入。
2. 確認繁中首頁、值班表、PDF 下載及請假調整頁可正常使用。
3. 確認網址全程是 `https://`。
4. 登出或關閉無痕視窗。

### 6.3 未獲准帳戶測試

以不在 Allow policy 的帳戶測試；必須被拒絕，不可進入 NiceGUI。

### 6.4 自動閘門重測

```powershell
Set-Location C:\SingYinRoster
powershell -ExecutionPolicy Bypass -File scripts\verify_cloudflare_access.ps1 `
  -PublicHostname "roster.example.org" `
  -TeamDomain "your-team.cloudflareaccess.com"
```

---

## 7. 日常運作

- Windows 工作排程負責 NiceGUI；`cloudflared` Windows service 負責 Tunnel。
- 主機仍只在 `127.0.0.1:8080` 接受來源連線，家用路由器不需要 port forwarding。
- 每月及 Cloudflare policy 修改後重做第 6 節。
- 新增或移除使用者只在 Access Allow policy 逐一調整完整電郵地址。
- `.env`、Tunnel token、credentials、Cookie、資料庫及備份不要貼到 issue、README 或公開截圖。

檢查兩項服務：

```powershell
Get-ScheduledTask -TaskName "Sing Yin Roster Host" | Format-List TaskName,State
Get-Service cloudflared | Format-List Name,Status,StartType
```

---

## 8. 立即停止遠端存取

本機值班表可以繼續使用；只停止 Tunnel：

```powershell
Stop-Service cloudflared
Set-Service cloudflared -StartupType Disabled
```

然後在 Cloudflare Dashboard 停用或刪除 Public Hostname／Tunnel route。若要把應用程式本身退回 local mode，把 `.env` 改回：

```dotenv
SING_YIN_DEPLOYMENT_MODE=local
SING_YIN_HOST=127.0.0.1
SING_YIN_REMOTE_ACCESS_ENABLED=false
SING_YIN_CLOUDFLARE_PROTECT_WITH_ACCESS=false
```

再重啟 `Sing Yin Roster Host` 工作排程。

---

## 9. 哪些工作仍需要你完成

| 工作 | 可否由專案自動完成 |
|---|---|
| 安裝 Python／Git／`.venv`／requirements | 可以，由 `prepare_windows_host.ps1` 完成 |
| 建立本機 `.env`、資料夾及預檢 | 可以 |
| 建立 Windows NiceGUI 工作排程 | 可以；開機模式只需輸入一次 Windows 密碼 |
| 安裝 `cloudflared` | 可以 |
| 選擇你的 Cloudflare 帳戶、網域及獲准登入者 | 必須由你決定 |
| 在 Dashboard 建立 Access app、Allow policy 及 Tunnel | 必須由你登入後完成 |
| 安裝 Tunnel service、切換 `.env`、重啟與自動失敗回復 | 可以；只需貼一次隱藏 token |
| 未登入／獲准／未獲准三種真人驗收 | 需要你以實際帳戶完成 |

---

## 10. 官方參考

- [Cloudflare：Windows 上把 cloudflared 作為服務運行](https://developers.cloudflare.com/tunnel/advanced/local-management/as-a-service/windows/)
- [Cloudflare：建立 Tunnel](https://developers.cloudflare.com/learning-paths/clientless-access/connect-private-applications/create-tunnel/)
- [Cloudflare：Access policies](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/)
- [Cloudflare：保護 private apps](https://developers.cloudflare.com/cloudflare-one/setup/secure-private-apps/)
