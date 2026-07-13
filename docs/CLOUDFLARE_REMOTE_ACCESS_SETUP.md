# Cloudflare 免費無網域遠端存取手冊（Windows 專用主機）

**用途：** 讓首席導學風紀在校外透過已登記裝置進入值班表系統。

**正式方案：** Cloudflare Zero Trust Free + 私有 Cloudflare Tunnel + Cloudflare One Client（WARP）。

**費用：** 不需要購買網域；Cloudflare Free 計劃目前足以供小型團隊使用。

**私有網址：** `http://roster.singyin.internal:8080`。
**本機來源：** NiceGUI 仍只監聽 `127.0.0.1:8080`。

這不是公開網站。只有已獲准登記、正在連接 Sing Yin Zero Trust 組織的 WARP 裝置，才會把這個私有網址送入 Tunnel。不要在家中路由器開放 3389、8080、80 或 443；Tunnel 只建立由主機向外的連線。

正式驗收必須分別記錄「未登入／獲准／未獲准」三種裝置結果，避免只測試成功登入而漏掉拒絕路徑。

---

## 1. 一分鐘理解整個流程

```text
遠端瀏覽器
    ↓
已登記的 Cloudflare One Client（WARP）
    ↓
Cloudflare Zero Trust 私有路由
    ↓
具名 Tunnel：sing-yin-roster-windows-private
    ↓
Windows 主機 cloudflared 服務
    ↓
127.0.0.1:8080 NiceGUI
```

這個方案有三道邊界：

1. 未獲准的電郵帳戶不能登記裝置。
2. 沒有連接指定 Zero Trust 組織的裝置不能解析私有網址。
3. NiceGUI 仍拒絕外部網卡直接連線，只接受 loopback 及已聲明的私有 Host header。

---

## 2. 目前已完成的 Cloudflare 設定

截至 2026-07-13，下列項目已建立：

| 項目 | 目前值 | 狀態 |
|---|---|---|
| Zero Trust team domain | `restless-hall-73b2.cloudflareaccess.com` | 已建立 |
| Tunnel | `sing-yin-roster-windows-private` | 已建立 |
| Tunnel ID | `ba6b6426-d012-4ecb-bafa-cbdbf2659731` | 非秘密識別值 |
| 私有主機路由 | `roster.singyin.internal` | 已指向上述 Tunnel |
| WARP 裝置登記政策 | 只允許指定的導學風紀操作帳戶 | 已建立 |
| Gateway proxy | Traffic and DNS / WARP | 已啟用 |
| Split Tunnel | Cloudflare 私有 hostname 合成位址經 WARP | 已設定 |
| Local Domain Fallback | `.internal` 交由 Cloudflare Gateway | 已設定 |
| 公開 DNS／Public Hostname | 無 | 維持關閉 |

Tunnel token 是秘密，只可存放於主機受保護的 `data\runtime`；不得貼進 README、Git、截圖、電郵或支援紀錄。

---

## 3. Windows 主機：啟用私有連接器

這個步驟只需在主機完成一次，而且需要管理員權限。

### 3.1 啟用前檢查

1. 確認 `C:\SingYinRoster` 已完成 [Windows 專用主機設定](WINDOWS_DEDICATED_HOST_SETUP.md)。
2. 在主機開啟 Edge，進入 `http://127.0.0.1:8080`。
3. 確認 Dashboard 正常開啟。
4. 開啟 PowerShell，執行：

```powershell
Invoke-RestMethod http://127.0.0.1:8080/healthz | Format-List
```

應看到 `status : ok`、`database : ok` 及 `applicationMode : official`。

### 3.2 執行受控啟用器

以滑鼠右鍵按「Windows PowerShell」，選擇「以系統管理員身分執行」，然後貼上：

```powershell
Set-Location C:\SingYinRoster
powershell -ExecutionPolicy Bypass -File scripts\activate_cloudflare_private_warp.ps1 `
  -TunnelId "ba6b6426-d012-4ecb-bafa-cbdbf2659731" `
  -PrivateHostname "roster.singyin.internal" `
  -TeamDomain "restless-hall-73b2.cloudflareaccess.com"
```

啟用器會依次：

1. 核對 Tunnel ID、team domain、cloudflared 版本及本機健康狀態。
2. 核對 Windows 工作排程確實屬於這個專案及 `SingYinRosterSvc`。
3. 把私有 hostname 在 origin 解析到 `127.0.0.1`。
4. 以 token file 而非命令列明文建立自動啟動的 `cloudflared` 服務。
5. 讓 `.env` 進入 first-class `private_warp` server mode。
6. 產生獨立的 NiceGUI session secret。
7. 重新啟動 NiceGUI，驗證它接受私有 hostname，但仍只監聽 loopback。
8. 任何一步失敗時停止連接器並還原 `.env` 及 Windows hosts file。

成功訊息為：

```text
Private WARP connector is active without a public hostname.
Remote address after WARP enrollment: http://roster.singyin.internal:8080
```

### 3.3 本機驗證

```powershell
Set-Location C:\SingYinRoster
powershell -ExecutionPolicy Bypass -File scripts\verify_cloudflare_private_warp.ps1
```

報告必須為 `status: pass`，並且以下四項全部通過：

- `connector_service`
- `private_dns_origin`
- `private_host_header`
- `ownership_marker`

再執行完整而不顯示秘密的主機診斷：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\doctor_windows_remote_access.ps1
```

---

## 4. 遠端 Windows 電腦：只需完成一次

### 4.1 安裝 Cloudflare One Client

1. 進入 [Cloudflare One Client 官方下載頁](https://developers.cloudflare.com/cloudflare-one/team-and-resources/devices/cloudflare-one-client/downloads/)。
2. 選擇 Windows Stable release。
3. 下載並安裝。
4. 在工作列右下角開啟 Cloudflare 圖示。

### 4.2 加入 Sing Yin Zero Trust 組織

1. 在 Cloudflare One Client 選擇登入 Zero Trust 組織。
2. Team name 輸入：

```text
restless-hall-73b2
```

3. 以獲批准的帳戶登入。
4. 完成後確認狀態為 Connected，模式為 WARP／Traffic and DNS。

### 4.3 開啟網站

在 Edge 或 Chrome 輸入：

```text
http://roster.singyin.internal:8080
```

這個 HTTP 是 Tunnel 內的私有 origin 位址；裝置至 Cloudflare、Cloudflare 至主機的傳輸由 WARP／Tunnel 保護。它不是公開 HTTP 網站。

---

## 5. 手機或平板設定

1. 從官方 App Store／Google Play 安裝 Cloudflare One Agent。
2. 選擇 Zero Trust 組織登入。
3. Team name 輸入 `restless-hall-73b2`。
4. 以獲批准帳戶完成登入。
5. 允許建立裝置 VPN 設定。
6. 顯示 Connected 後，以瀏覽器開啟 `http://roster.singyin.internal:8080`。

手機只需使用網站，不應開放 Windows RDP。

---

## 6. 正式驗收清單

### 主機

- [ ] `http://127.0.0.1:8080/healthz` 顯示 application、database 均正常。
- [ ] NiceGUI 仍只監聽 `127.0.0.1:8080`。
- [ ] `cloudflared` Windows service 為 Running／Automatic。
- [ ] Cloudflare Tunnel 狀態為 Healthy。
- [ ] 私有 hostname 的 origin 解析為 `127.0.0.1`。
- [ ] 主機重啟後 NiceGUI 及 Tunnel 自動恢復。

### 已獲准遠端裝置

- [ ] WARP 顯示已連接 `restless-hall-73b2`。
- [ ] 私有網址可開啟 Dashboard。
- [ ] 繁中／英文、深淺模式及手機排列正常。
- [ ] 可完成虛構資料的草稿、PDF 下載及已發布後請假調整。
- [ ] PDF 仍留在使用者主動下載的位置，不會傳入 Cloudflare 儲存。

### 未獲准路徑

- [ ] 關閉 WARP 後，私有網址不能進入。
- [ ] 未獲准帳戶不能登記新裝置。
- [ ] 家庭網絡內另一部未登記裝置不能直接以主機 LAN IP 進入 8080。
- [ ] Cloudflare 帳戶沒有 Public Hostname、Quick Tunnel 或公開 DNS route。

---

## 7. 日常使用

1. 主機保持開機及接駁網絡。
2. 遠端裝置先確認 WARP 為 Connected。
3. 開啟 `http://roster.singyin.internal:8080`。
4. 完成值班工作後正常關閉瀏覽器即可；毋須停止 WARP，但可按個人需要暫停。

如網站不能開啟，依次檢查：

1. 遠端裝置 WARP 是否 Connected。
2. 主機是否開機。
3. 主機本機 `127.0.0.1:8080` 是否正常。
4. 主機 `cloudflared` service 是否 Running。
5. Cloudflare Dashboard 的 Tunnel 是否 Healthy。

---

## 8. 立即停止遠端存取

以管理員 PowerShell 在主機執行：

```powershell
Stop-Service cloudflared
Set-Service cloudflared -StartupType Disabled
```

這只停止遠端 Tunnel，本機網站及 SQLite 不會被刪除。需要恢復時：

```powershell
Set-Service cloudflared -StartupType Automatic
Start-Service cloudflared
```

如需永久取消，再於 Cloudflare Zero Trust 刪除 hostname route、撤銷 WARP 裝置及刪除 Tunnel；不要只刪除本機 token file 而保留不明狀態。

---

## 9. 為下一任首席導學風紀新增帳戶

1. 先由現任負責人及教師顧問確認交接日期。
2. 在 Cloudflare Zero Trust 的 WARP device enrollment policy 加入下一任的完整電郵地址。
3. 讓下一任依第 4 節登記自己的裝置。
4. 在虛構資料下完成第 6 節驗收。
5. 確認新裝置正常後，移除前任電郵並 revoke 前任裝置。
6. 把這次變更及驗收日期寫入交接紀錄；不要記錄登入密碼或 token。

---

## 10. 為何不用 Quick Tunnel

Quick Tunnel 雖然免費並提供隨機 `trycloudflare.com` 網址，但網址會改變、不能完整管理存取政策，而且官方定位為測試用途。本系統的正式無網域方案使用具名私有 Tunnel + WARP；Quick Tunnel 不屬於故障備援方法。

---

## 11. 官方參考

- [Cloudflare：連接私有 hostname](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/private-net/cloudflared/connect-private-hostname/)
- [Cloudflare：建立 Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/)
- [Cloudflare：裝置登記權限](https://developers.cloudflare.com/cloudflare-one/team-and-resources/devices/cloudflare-one-client/deployment/device-enrollment/)
- [Cloudflare：設定 Cloudflare One Client](https://developers.cloudflare.com/cloudflare-one/team-and-resources/devices/cloudflare-one-client/set-up/)
- [Cloudflare：Split Tunnels](https://developers.cloudflare.com/cloudflare-one/team-and-resources/devices/cloudflare-one-client/configure/route-traffic/split-tunnels/)
- [Cloudflare：Local Domain Fallback](https://developers.cloudflare.com/cloudflare-one/team-and-resources/devices/cloudflare-one-client/configure/route-traffic/local-domains/)
