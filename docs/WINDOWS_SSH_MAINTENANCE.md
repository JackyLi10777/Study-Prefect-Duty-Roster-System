# Windows SSH 維護通道／Windows SSH Maintenance Channel

本文件說明首席導學風紀或下一位受託維護者如何安全地維護正式 Windows 主機。SSH 是技術維護入口，不是一般使用者網址，也不會取代正式 `workers.dev` 網站。

This guide explains the protected maintenance channel for the official Windows host. SSH is a technical maintenance path; it is not a user-facing URL and does not replace the canonical `workers.dev` site.

## 1. 目前正式設定／Current production configuration

截至 2026-07-17，主機 `LAPTOP-NQ22TI3V` 已完成：

- Windows OpenSSH Server 已安裝，`sshd` 為 `Running` 及 `Automatic`。
- 只監聽 `127.0.0.1:22` 及 `[::1]:22`。
- Windows 的 OpenSSH 入站防火牆規則保持停用。
- 只允許本機管理員 `lichu` 登入。
- 只接受 Ed25519 公開金鑰；密碼及互動式登入均停用。
- agent、TCP、gateway、tunnel 及 X11 forwarding 均停用。
- SSH 私鑰只保存於 `C:\Users\lichu\.ssh\sing_yin_codex_ed25519`，不在專案、Git、備份、日誌或交接包內。
- SSH 設定別名為 `sing-yin-roster-host`。

As of 2026-07-17, the host accepts key-only maintenance sessions on loopback. No router rule, public TCP 22 rule, LAN listener, password fallback, or repository-held private key exists.

## 2. 日常使用／Daily use

在正式主機上的 PowerShell 或 Codex 終端執行：

```powershell
ssh sing-yin-roster-host
```

執行單一命令而不進入互動終端：

```powershell
ssh sing-yin-roster-host "Get-Service sshd"
ssh sing-yin-roster-host "Invoke-RestMethod http://127.0.0.1:8080/healthz | ConvertTo-Json"
```

重新執行完整、無密碼的維護驗證：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File D:\code_v3\scripts\verify_windows_ssh.ps1 `
  -ReportPath D:\code_v3\logs\windows-ssh-verification.json
```

只有報告同時顯示以下內容才算通過：

- `status: pass`
- `isAdministrator: true`
- `sshdStatus: Running`
- `rosterTaskState: Ready` 或 `Running`
- `productionCommit` 為 40 位 Git commit
- `websiteStatus: ok`
- `applicationMode: official`
- `database: ok`

## 3. 安全邊界／Security boundary

目前的 SSH 只供同一台 Windows 主機上的 Codex 或受控終端使用。即使家中路由器、Wi-Fi 或公網知道這台電腦的位址，也不能直接連到 TCP 22。

The server binds only to loopback. A future off-device SSH connection must be carried by an authenticated Cloudflare private route to `localhost:22`; never change `ListenAddress` to `0.0.0.0`, never enable the OpenSSH public firewall rule, and never configure router port forwarding.

SSH 維護與網站權限是兩件事：

- 一般使用者及管理員日常工作仍使用同一個正式網站及 Cloudflare Access。
- SSH 只用於更新、備份、還原、服務重啟、日誌調查及主機修復。
- `SingYinRosterSvc` 是非互動網站執行帳戶，不能透過 SSH 登入。
- 不可把 SSH 私鑰交給下一任、上載 GitHub、放進 OneDrive 或附加到交接備份。

## 4. 重建或輪換金鑰／Rebuild or rotate the key

先在受控維護端建立新的 Ed25519 金鑰，私鑰路徑必須位於使用者 `.ssh`，不可位於 `D:\code_v3`：

```powershell
ssh-keygen -t ed25519 -a 64 `
  -f C:\Users\lichu\.ssh\sing_yin_codex_ed25519_next `
  -C "sing-yin-maintenance"
```

然後以系統管理員 PowerShell 重新執行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File D:\code_v3\scripts\configure_windows_ssh.ps1 `
  -AuthorizedPublicKeyPath C:\Users\lichu\.ssh\sing_yin_codex_ed25519_next.pub `
  -MaintenanceUser lichu `
  -ClientProfilePath C:\Users\lichu `
  -ReportPath D:\code_v3\logs\windows-ssh-setup.json
```

先用新金鑰通過 `verify_windows_ssh.ps1`，才可移除舊私鑰。任何失敗都保留舊金鑰及本機 Windows 登入，不可在未證明新登入成功前刪除復原路徑。

## 5. 緊急停用／Emergency disable

如懷疑維護金鑰遺失，在主機以系統管理員 PowerShell 執行：

```powershell
Stop-Service sshd
Set-Service sshd -StartupType Disabled
```

這只會停用 SSH，不會停止 NiceGUI、SQLite、工作排程器或 Cloudflare 網站。完成調查及金鑰輪換後，才可重新設為 `Automatic` 並啟動。

## 6. 遠端 SSH 尚餘一步／Remaining off-device step

本機 SSH 已完成並通過。若要讓另一台受控電腦上的 Codex 連入，仍需在現有 Cloudflare Zero Trust 架構中新增獨立的 SSH 私有路由或 Access SSH application，指向 `localhost:22`，並在遠端裝置保存另一把受控私鑰。

This off-device route is deliberately separate from the public roster site. It must reuse the existing exact-identity policy, must not expose port 22 publicly, and requires an end-to-end remote-device acceptance test before it is called operational.
