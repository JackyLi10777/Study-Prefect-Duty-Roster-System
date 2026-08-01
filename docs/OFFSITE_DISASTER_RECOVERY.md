# 離機災難復原手冊 / Off-site disaster recovery runbook

本手冊是「整部正式主機或其內置儲存同時損毀」的唯一操作來源。一般每週操作見[操作手冊](OPERATOR_GUIDE.md)，程式發布與相容回退見[發布與交接手冊](RELEASE_HANDOVER.md)，精確線上版本見[目前系統狀態](status/CURRENT_STATUS.md)。

> **目前證據（2026-08-01）：** 主線來源已具備外置 BitLocker 媒體檢查、精確副本收據及 replacement-location 隔離還原工具；聚焦合成資料測試已證明刪除原主機資料後仍可由副本還原。檢查時主機只有 C、D 兩個內置磁碟，沒有已連接且可核實的加密外置媒體，因此尚未產生真實離機副本，也未從第二部主機完成演練。本能力仍是**來源候選，不是已部署或已完成的災難復原證據**。

## 1. 保護目標與非目標

本流程保護正式 SQLite 值班資料、同名 checksum manifest，以及解讀該資料所需的 immutable release identity。它應在主機遺失、內置磁碟損毀或 Windows 無法啟動時，讓受託維護者由另一個乾淨 checkout／release bundle 完成受控還原。

它不備份 `.env`、Cloudflare token、session secret、SSH 私鑰、完整日誌、支援附件、音樂或開發工作樹。這些秘密與設定必須由各自的秘密保管／重建程序處理；把它們放入離機資料包只會擴大洩漏面。

## 2. 唯一接受的儲存邊界

自動匯出目前只接受同時符合以下條件的媒體：

- 實體 BusType 為 `USB` 或 `SD`，且不是 Windows boot／system disk；
- 獨立於主機內置 C、D 磁碟，可在匯出後安全拔除；
- NTFS、BitLocker `ProtectionStatus=On`、`VolumeStatus=FullyEncrypted`，匯出時已解鎖；
- 至少 512 MiB 可用空間；
- 由學校批准，並有一名不只依賴原開發者的保管人。

腳本會對 volume identity、disk number、bus type 及 encryption method 產生不可逆 SHA-256 摘要，只把摘要寫入收據，不保存磁碟序號或 recovery key。收據是可追溯操作證據，不是對抗惡意管理員的數位簽章。

以下全部**不算離機副本**：同一主機的 D 槽、OneDrive／同步資料夾、未經批准的網路分享、普通未加密 USB、電郵附件、GitHub artifact、DPAPI／EFS 綁定本機的加密檔案，或只有 SQLite 而沒有 matching manifest 的複製品。不要用自製 ZIP 密碼或自創加密格式取代 BitLocker。

## 3. RPO、RTO 與責任

| 指標 | 目標 | 量測方式 |
|---|---|---|
| 日常 RPO | 最多 7 日 | 每星期至少完成一次成功匯出；收據記錄新建快照至匯出的保守秒數 |
| 重大操作 RPO | 最多 24 小時 | 發布週表、發布後請假、更換正式名單、新學年準備或程式部署後 24 小時內再匯出 |
| 技術還原 RTO | 15 分鐘內 | `drill.rtoSeconds` 量度 checksum、解包、migration-aware restore、公平及行數核對 |
| 完整服務 RTO | 4 小時內 | 從乾淨 Windows／checkout、可用密鑰及離機媒體開始，到 origin、Worker、Admin／Guest／Viewer 驗收完成 |

RPO 是可接受的最大資料損失窗口，不是「備份檔有多舊」的簡化宣傳。匯出工具先透過正式跨 process mutex 建立一份新 verified snapshot，再原子複製；若此後沒有正式寫入，較舊副本仍可能包含完整現況。任何真人報告都要同時記錄最後正式寫入時間、匯出時間及收據值。

責任分工：

- 首席導學風紀：在規定時點執行匯出、核對 `pass`、安全退出媒體並登記日期；
- 教師顧問或學校指定 IT 保管人：保管 BitLocker recovery key／password，與媒體分開存放，並核准保留與銷毀；
- 維護者：每月在替代位置執行獨立 drill，保存不含學生資料的結果摘要；
- 不得由同一個遺失裝置同時保存媒體、唯一密鑰及唯一操作說明。

## 4. 建立真正離機副本

只有 [`status/CURRENT_STATUS.md`](status/CURRENT_STATUS.md) 明確顯示正式 immutable bundle 已包含本工具後，才在正式主機執行本節。目前頁首所述來源候選尚未部署，不能從 rc45 checkout 或主機根目錄的舊腳本替代執行。

### 4.1 準備

1. 在 Windows「管理 BitLocker」確認外置磁碟已**完整**加密；把 recovery key 交給批准保管人，不要放在主機、USB、Git、文件或交接 ZIP。
2. 連接並解鎖媒體，記下 drive letter（以下以 `E:` 為例）。
3. 確認沒有正在生成、發布、修改名單、處理請假、備份、還原或部署。
4. 以 Administrator PowerShell 取得目前排程實際使用的 immutable bundle；不要猜測 `C:\SingYinRoster` checkout 的 Git HEAD。

### 4.2 執行

```powershell
$Task = Get-ScheduledTask -TaskName "Sing Yin Roster Host"
$RuntimeRoot = [string]@($Task.Actions)[0].WorkingDirectory
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File (Join-Path $RuntimeRoot "scripts\export_offsite_recovery.ps1") `
  -DestinationDrive E:\
```

腳本會依序：核對 Administrator、owned production task、immutable bundle、外置 bus、非 system disk、NTFS 及 BitLocker；建立最新 verified snapshot；在外置媒體的 `SingYinRosterRecoveryMedia\SingYinRosterRecovery` 下以 private partial directory 寫入；重新核對 package／snapshot／manifest digest、schema 及安全 ZIP members；原子發布資料包；只從該外置副本完成隔離 restore drill；最後把不含路徑、姓名或資料列的報告寫到：

```text
C:\SingYinRoster\logs\offsite-recovery-latest.json
```

只有終端顯示 export、row counts、fairness、restore audit 全部通過，才可記為成功。失敗或留下 `.partial` 不可計入 RPO；不要手動改名成正式資料包。

### 4.3 離線保存

1. 記錄 bundle name、日期、報告 `pass`、RPO 秒數及 drill RTO；不要抄錄學生資料或完整本機路徑。
2. 使用 Windows「安全地移除硬體」退出，再拔除媒體。
3. 媒體與正式主機分開保存；密鑰再與媒體分開，由批准保管人持有。
4. 不要為方便而長期插在主機、開啟自動雲端同步或關閉 BitLocker。

## 5. 保留與銷毀

- 保留最近 8 份成功週備份，以及最近 6 個月各一份通過 replacement-location drill 的月度副本。
- 新副本尚未通過完整 drill 前，不得刪除上一個已驗證副本。
- 每學年交接時由教師顧問／指定 IT 核對學校資料保留政策；超期資料以 BitLocker 媒體的受控清除／重置程序銷毀，不只刪除 ZIP。
- 工具刻意不自動刪除舊資料包，避免插錯磁碟或一次失敗匯出造成不可逆資料損失。

## 6. 在替代位置演練

每月至少一次，使用另一部受控 Windows 電腦或完全獨立的乾淨工作目錄。先安裝與 receipt `release.releaseRef`／`commit` 相符或已明確支援其 `schemaRevision` 的程式與鎖定依賴；不要使用正式資料庫或正式主機的 backup directory。

```powershell
python -X utf8 scripts\offsite_recovery.py drill `
  --bundle-dir "E:\SingYinRosterRecoveryMedia\SingYinRosterRecovery\<SYSS_Offsite_bundle>" `
  --report ".\logs\replacement-location-drill.json"
```

通過條件：package／snapshot／manifest digest 一致；沒有額外、重複、加密或 traversal ZIP member；SQLite integrity、supported migration、schema、零 pending obligation、公平對帳及 operational row counts 通過；還原只追加一個 restore audit；報告為 `pass` 並量得 RTO。演練使用臨時資料庫並在完成後清理，不把它設成第二個正式寫入主機。

完整 ITR-004 關閉證據還必須包含：真實外置 BitLocker 媒體摘要、實際 RPO／RTO、分離密鑰保管責任、離線保存確認，以及不依賴正式主機資料的 replacement-location `pass` 報告。

## 7. 真實事故還原

1. 宣布正式寫入停止；不要讓舊主機與替代主機同時成為 authoritative writer。
2. 由保管人提供媒體及 BitLocker 解鎖資料；維護者不得把密鑰貼入聊天、command line、日誌或文件。
3. 從 receipt 核對 release identity、schema revision、snapshot／manifest digest 及最近成功 drill。
4. 在替代主機先執行上節 `drill`。任何失敗都停止，不手動覆寫 SQLite。
5. 依[Windows 專用主機手冊](WINDOWS_DEDICATED_HOST_SETUP.md)建立乾淨 origin，把資料包中的 SQLite 與 matching manifest 放入受保護 backup directory，再使用既有受控 restore；不要直接把快照改名成 live database。
6. 核對 `/healthz`、`/readyz`、`writeReady=true`、migration、零 pending backup obligation、名單、最近週表、公平、中文 PDF 及 canonical Admin／Guest／Viewer。
7. 只有 source、資料、Worker、文件與真人驗收一致後才恢復正式寫入，並立即建立新的離機副本。

## 8. 失敗處理與剩餘限制

| 情況 | 安全處理 |
|---|---|
| 不是 USB／SD、是 system disk 或無 BitLocker | 停止；更換批准媒體，不使用 `-Force` 或 fallback |
| 匯出或 drill 失敗 | 保留上一份成功離機副本；本次不計入 RPO，按受保護報告調查 |
| 收據／ZIP／manifest digest 不符 | 視為不可用或可能被篡改，隔離媒體；不要重新計算收據來「修好」它 |
| 密鑰遺失 | 該媒體不可作可恢復證據；建立新批准媒體與新保管安排 |
| 只有內置 C／D 磁碟 | 保持 ITR-004 未完成；同機副本仍只屬 local recovery |

BitLocker 保護離線媒體遺失時的靜態資料，但不抵抗已登入的惡意管理員、匯出期間的完整主機入侵或錯誤的學校保管流程。收據的 hash 證明 bytes 一致，不證明操作者身份；因此分離保管、replacement-location drill 與受監督驗收仍不可省略。

## English operator summary

Use only a school-approved, fully encrypted BitLocker USB／SD NTFS volume. Run the administrator wrapper from the immutable bundle; it creates a fresh verified snapshot, atomically copies a bounded handover package, writes a path-free receipt, and restores only from that copied package. Eject and store the volume away from the host, keep its recovery key with a separate approved custodian, and run the standalone `drill` command monthly from a replacement location. Internal disks, sync folders, unencrypted media, DPAPI／EFS, email, GitHub, or a database without its manifest never satisfy this runbook.
