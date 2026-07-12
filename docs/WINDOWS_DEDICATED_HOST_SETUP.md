# Windows 專用主機完整設定手冊

**適用系統：** Sing Yin Study Prefect Duty Roster System（NiceGUI + SQLite）
**讀者：** 完全不懂程式、第一次設定電腦的人
**正式方案：** 一部長期放置的 Windows 11 專用電腦；先完成本機模式，再按需要啟用受 Cloudflare Access 保護的遠端網站
**預設網址：** `http://127.0.0.1:8080`

---

## 0. 先理解這個方案

完成本手冊後，運作方式如下：

1. 一部 Windows 電腦長期保存程式、SQLite 資料庫、備份、日誌、PDF 及音樂。
2. 網站只在這部電腦上開放；使用者坐在該電腦前，以瀏覽器進入 `http://127.0.0.1:8080`。
3. 電腦開機後，可由 Windows 工作排程器在背景自動啟動系統。
4. 初次安裝不設定 Cloudflare Tunnel、公開網址、路由器轉發或對外連接埠。
5. 即使電腦沒有互聯網，名單、排班、PDF、備份及還原仍可使用；YouTube 音樂除外。

### 很重要：專用主機不等於已經可以遙距進入

`127.0.0.1` 只代表「這部電腦自己」。手機、家中另一部電腦或校外裝置不能用這個網址進入。這是初次安裝刻意採用的安全邊界。需要遙距存取時，完成本手冊後再依 [Cloudflare 遠端存取完整設定手冊](CLOUDFLARE_REMOTE_ACCESS_SETUP.md) 啟用；不要自行把主機改成 `0.0.0.0`，也不要在路由器開啟 8080 埠。

### 最省手動操作的安裝方法

把程式下載到 `C:\SingYinRoster` 後，以管理員 PowerShell 執行：

```powershell
Set-Location C:\SingYinRoster
powershell -ExecutionPolicy Bypass -File scripts\prepare_windows_host.ps1 -InstallPrerequisites
powershell -ExecutionPolicy Bypass -File scripts\register_windows_startup_task.ps1 -AtStartup
```

第一條會自動檢查或安裝 Git、Python 3.12，建立 `.venv`、安裝套件、建立本機環境與執行預檢；第二條只在 Windows 必須保存開機工作時要求你輸入一次主機帳戶密碼。以下各節仍保留完整手動步驟，方便查錯及交接。

如果這部主機也要執行完整發布／瀏覽器驗證，在第一條命令末尾加上 `-IncludeDevelopmentTools`；它會一併安裝測試套件及隔離的 Playwright Chromium。日常只運行網站的主機不需要此額外下載。

---

## 1. 需要準備甚麼

### 1.1 電腦最低建議

| 項目 | 建議 |
|---|---|
| 作業系統 | Windows 11 64-bit，保持 Windows Update |
| 處理器 | Intel Core i3／AMD Ryzen 3 或以上 |
| 記憶體 | 最少 8 GB；建議 16 GB |
| 儲存 | 最少 128 GB SSD；建議保留 30 GB 可用空間 |
| 網絡 | 建議使用有線 Ethernet；Wi-Fi 亦可 |
| 電源 | 長期接駁可靠電源；可選用 UPS 不斷電系統 |
| 顯示器 | 初次設定及故障處理時需要 |

不要把主機放在會被拔走電源、經常關機、長期高溫或公眾可隨意操作的位置。

### 1.2 需要知道的帳戶

準備兩個 Windows 帳戶最清楚：

- **管理員帳戶：** 只用於安裝程式、Windows Update 和修理主機。
- **日常帳戶：** 建議命名為 `SingYinRoster`，只用來運行值班表系統。

日常帳戶應設定一個不容易猜到的密碼。不要把管理員帳戶長期登入在桌面。

### 1.3 建議的安裝位置

本手冊統一使用：

```text
C:\SingYinRoster
```

不要放入桌面、下載、OneDrive、Google Drive 或其他自動同步資料夾。路徑不要包含括號、特殊符號或很長的中文名稱。

---

## 2. 第一次整理 Windows 11

以下工作只做一次。

### 步驟 2.1：完成 Windows Update

1. 按畫面下方的「開始」。
2. 開啟「設定」。
3. 選擇「Windows Update」。
4. 按「檢查更新」。
5. 安裝所有重要更新。
6. 如畫面要求重新啟動，先重新啟動。
7. 重新登入後，再按一次「檢查更新」，直至沒有等待中的重要更新。

### 步驟 2.2：替電腦設定容易辨認的名稱

1. 開啟「設定」→「系統」→「系統資訊」。
2. 按「重新命名這部電腦」。
3. 建議輸入：`SYSS-ROSTER-HOST`。
4. 重新啟動。

### 步驟 2.3：禁止主機自動睡眠

1. 開啟「設定」→「系統」→「電源與電池」。
2. 展開「螢幕、睡眠及休眠逾時」。
3. 「接上電源後，讓裝置進入睡眠」選擇「永不」。
4. 螢幕可以在 10 至 30 分鐘後關閉；關閉螢幕不會停止網站。
5. 如使用手提電腦作主機，再到控制台的電源選項，確認接上電源時關上機蓋不會令電腦睡眠。

不要關閉 Windows Update。應安排在不使用值班表的時間更新及重新啟動。

### 步驟 2.4：確認日期與時區

1. 開啟「設定」→「時間與語言」→「日期與時間」。
2. 開啟「自動設定時間」。
3. 時區選擇香港使用的 `UTC+08:00`。
4. 按「立即同步」。

正確時間會影響日誌、備份、審計及週次日期。

---

## 3. 安裝 Git 與 Python

### 步驟 3.1：安裝 Git for Windows

1. 在瀏覽器開啟 [Git for Windows 官方下載頁](https://git-scm.com/download/win)。
2. 下載 64-bit 安裝程式。
3. 雙擊安裝檔。
4. 如不確定選項，保留安裝程式預設值，一直按「Next」。
5. 完成後按「Finish」。

### 步驟 3.2：安裝 Python Install Manager

1. 在瀏覽器開啟 [Python 官方 Windows 說明](https://docs.python.org/3/using/windows.html)。
2. 從 python.org 或 Microsoft Store 安裝 Python Install Manager。
3. 完成後重新開啟「開始」選單。
4. 搜尋並開啟「PowerShell」。

### 步驟 3.3：安裝 Python 3.12

在 PowerShell 複製以下一行，按 Enter：

```powershell
py install 3.12
```

完成後輸入：

```powershell
py -V:3.12 --version
```

應看到類似：

```text
Python 3.12.x
```

再輸入：

```powershell
git --version
```

應看到類似 `git version 2.x.x`。如果 `py` 或 `git` 顯示「不是可辨識的命令」，先關閉 PowerShell，重新開啟後再試；仍失敗才重新安裝相應程式。

---

## 4. 從 GitHub 取得正式程式

### 步驟 4.1：以管理員身分建立資料夾

1. 按開始，輸入 `PowerShell`。
2. 在「Windows PowerShell」按右鍵。
3. 選擇「以系統管理員身分執行」。
4. 如出現確認視窗，按「是」。
5. 貼上：

```powershell
New-Item -ItemType Directory -Path C:\SingYinRoster -Force
```

### 步驟 4.2：讓日常帳戶可使用資料夾

如果目前登入的就是日常 `SingYinRoster` 帳戶，可以跳到步驟 4.3。否則由管理員在檔案總管：

1. 在 `C:\SingYinRoster` 按右鍵→「內容」。
2. 選「安全性」→「編輯」→「新增」。
3. 輸入日常帳戶名稱 `SingYinRoster`。
4. 按「檢查名稱」→「確定」。
5. 允許「修改」、「讀取及執行」、「列出資料夾內容」、「讀取」和「寫入」。
6. 不需要給予「完全控制」。

### 步驟 4.3：下載 `main` 正式分支

改用日常帳戶登入 Windows，開啟普通 PowerShell，貼上：

```powershell
git clone --branch main --single-branch https://github.com/JackyLi10777/Study-Prefect-Duty-Roster-System.git C:\SingYinRoster
```

如果畫面說資料夾不是空的：

1. 不要加入 `--force`。
2. 確認資料夾內沒有需要保留的檔案。
3. 把空資料夾改名為 `C:\SingYinRoster-old`。
4. 再執行以上 `git clone`。

完成後輸入：

```powershell
Set-Location C:\SingYinRoster
git branch --show-current
```

應顯示：

```text
main
```

---

## 5. 建立獨立 Python 環境

獨立環境可避免其他 Python 程式影響值班表系統。

### 步驟 5.1：建立 `.venv`

在普通 PowerShell 貼上：

```powershell
Set-Location C:\SingYinRoster
py -V:3.12 -m venv .venv
```

### 步驟 5.2：更新安裝工具

```powershell
C:\SingYinRoster\.venv\Scripts\python.exe -m pip install --upgrade pip
```

### 步驟 5.3：安裝正式運行需求

```powershell
C:\SingYinRoster\.venv\Scripts\python.exe -m pip install --require-hashes -r C:\SingYinRoster\requirements.lock
```

這一步可能需要數分鐘。完成時不應有紅色 `ERROR`。鎖定檔同時安裝網站內的 YouTube 本機音訊匯入元件；無需另行下載另一個圖形介面程式。

完成後核對下載元件版本：

```powershell
C:\SingYinRoster\.venv\Scripts\python.exe -m yt_dlp --version
C:\SingYinRoster\.venv\Scripts\deno.exe --version
```

第一條應顯示 `2026.7.4`，第二條應顯示 Deno `2.9.2`。Deno 是 YouTube 現時影片格式解析所需的本機 JavaScript runtime；鎖定需求會一併安裝，不需要另開網站下載。實際匯入時，網站只接受 HTTPS YouTube／YouTube Music 影片、Shorts 或公開歌單分享連結，並把結果放在 `C:\SingYinRoster\music\youtube-imports\`。此資料夾會在第一次成功匯入時自動建立，不需要手動建立。

### 步驟 5.4：確認 NiceGUI 可載入

```powershell
C:\SingYinRoster\.venv\Scripts\python.exe -c "import nicegui; print('NiceGUI ready')"
```

應顯示：

```text
NiceGUI ready
```

專案的雙擊啟動器會優先使用 `.venv\Scripts\python.exe`；如果 `.venv` 不存在，才會尋找全系統 Python。

---

## 6. 建立主機設定檔 `.env`

### 步驟 6.1：複製範例

在 PowerShell 貼上：

```powershell
Set-Location C:\SingYinRoster
Copy-Item .env.example .env
notepad .env
```

### 步驟 6.2：把本機設定改成以下內容

在記事本內，確認至少有以下設定：

```dotenv
SING_YIN_DEPLOYMENT_MODE=local
SING_YIN_HOST=127.0.0.1
SING_YIN_PORT=8080
SING_YIN_OPEN_BROWSER=false
SING_YIN_YOUTUBE_ENABLED=true
SING_YIN_LOG_DIR=C:\SingYinRoster\logs
SING_YIN_LOG_LEVEL=INFO
SING_YIN_LOG_CONSOLE=true
SING_YIN_LOG_MAX_BYTES=2000000
SING_YIN_LOG_BACKUP_COUNT=5
```

按 `Ctrl+S` 儲存，再關閉記事本。

請保持以下項目停用或留空：

- `SING_YIN_REMOTE_ACCESS_ENABLED`
- `SING_YIN_CLOUDFLARE_PROTECT_WITH_ACCESS`
- `SING_YIN_CLOUDFLARE_ACCESS_AUD`
- `SING_YIN_CLOUDFLARE_TEAM_DOMAIN`
- `SING_YIN_PUBLIC_HOSTNAME`

本機模式第一次啟動會自動建立 `data\runtime\.nicegui-storage-secret`，不需要手動輸入 secret，也不要打開、分享或修改該檔案。

---

## 7. 第一次啟動

### 步驟 7.1：先用雙擊啟動器

1. 用檔案總管開啟 `C:\SingYinRoster`。
2. 雙擊 `START_SING_YIN_ROSTER.cmd`。
3. Windows 如顯示保護提示，先核對檔案確實位於 `C:\SingYinRoster`；不要執行來歷不明的同名檔案。
4. 黑色視窗會檢查埠、啟動 NiceGUI，再等待 `/healthz` 真正就緒。
5. 看到 `The system is ready` 後，在 Edge 或 Chrome 開啟：

```text
http://127.0.0.1:8080
```

因 `.env` 已把自動開瀏覽器關閉，日後背景啟動時不會突然開視窗；雙擊啟動器仍會在服務就緒後替你開啟瀏覽器。

### 步驟 7.2：核對健康狀態

另開一個 PowerShell，貼上：

```powershell
Invoke-RestMethod http://127.0.0.1:8080/healthz | Format-List
```

應看到：

- `status : ok`
- `application : sing-yin-roster`
- `applicationMode : official`
- `database : ok`

若 `database` 不是 `ok`，不要開始正式排班。

### 步驟 7.3：確認資料夾已建立

在檔案總管核對：

```text
C:\SingYinRoster\data\runtime
C:\SingYinRoster\data\backups
C:\SingYinRoster\logs
```

不要直接開啟或修改 `sing-yin-roster.sqlite3`。

### 步驟 7.4：停止第一次測試

回到黑色視窗，按 `Ctrl+C`。等待程序停止後才關閉視窗。

---

## 8. 先完成一次練習模式

在加入正式名單前：

1. 雙擊 `START_PRACTICE_MODE.cmd`。
2. 確認每頁頂部都顯示「練習模式」。
3. 完成：請假→生成草稿→修改→發布→下載中英文 PDF→發布後請假調整→公平審核→建立備份→還原。
4. 關閉練習模式黑色視窗。
5. 雙擊 `RESET_PRACTICE_MODE.cmd`，確認練習資料能安全重設。

練習完成後才開始設定開機自動啟動。

---

## 9. 設定 Windows 開機自動啟動

本方案使用 Windows 內置「工作排程器」，不需要安裝 NSSM、Docker 或額外 Windows Service 軟件。

### 步驟 9.1：開啟工作排程器

1. 按開始。
2. 輸入「工作排程器」或 `Task Scheduler`。
3. 按右鍵→「以系統管理員身分執行」。
4. 右方選擇「建立工作」；不要選只有少量設定的「建立基本工作」。

### 步驟 9.2：「一般」分頁

填寫：

- 名稱：`Sing Yin Roster Host`
- 描述：`Starts the local Sing Yin NiceGUI roster system on this dedicated Windows host.`
- 選擇日常運行帳戶 `SingYinRoster`。
- 選擇「不論使用者登入與否均執行」。
- **不要**勾選「以最高權限執行」；網站不需要管理員權限。
- 設定適用於 Windows 11。

儲存時 Windows 可能要求輸入日常帳戶密碼。日後如更改該密碼，要回到工作排程器重新儲存密碼。

### 步驟 9.3：「觸發程序」分頁

1. 按「新增」。
2. 「開始工作」選擇「啟動時」。
3. 勾選延遲工作 `30 秒`。
4. 確認「已啟用」。
5. 按「確定」。

### 步驟 9.4：「動作」分頁

按「新增」，填寫：

**程式或指令碼：**

```text
C:\SingYinRoster\.venv\Scripts\python.exe
```

**新增引數：**

```text
-X utf8 -m nicegui_app.main
```

**開始位置：**

```text
C:\SingYinRoster
```

「開始位置」不可留空，亦不要加引號。

### 步驟 9.5：「條件」分頁

- 桌面電腦：取消「只有在電腦使用 AC 電源時才啟動」沒有影響，但可保留。
- 手提電腦：建議只在接上電源時運行。
- 不要要求電腦進入閒置才啟動。
- 不需要為此網站喚醒已睡眠電腦，因第 2 節已把接電睡眠設為「永不」。

### 步驟 9.6：「設定」分頁

勾選或設定：

- 允許視需要執行工作。
- 如果工作失敗，每 `1 分鐘`重新啟動一次。
- 嘗試重新啟動最多 `3 次`。
- 如果工作已在執行：選擇「不要啟動新執行個體」。
- 取消「如果工作執行超過 3 天便停止」之類的時間上限。
- 允許要求時停止工作。

按「確定」完成。

### 步驟 9.7：立即測試排程

1. 在工作排程器左方開啟「工作排程器程式庫」。
2. 找到 `Sing Yin Roster Host`。
3. 按右鍵→「執行」。
4. 等候 10 至 30 秒。
5. 在瀏覽器開啟 `http://127.0.0.1:8080`。
6. 執行第 7.2 節健康檢查。
7. 回到工作排程器，確認「上次執行結果」是 `0x0` 或工作仍顯示「執行中」。長時間服務顯示「執行中」是正常的。

### 步驟 9.8：重新啟動整部電腦測試

1. 關閉網站分頁。
2. 重新啟動 Windows。
3. 登入後等候一分鐘。
4. 開啟 `http://127.0.0.1:8080`。
5. 再做一次健康檢查。

只有這一步成功，才算完成自動啟動。

---

## 10. 日常使用方法

每天使用時：

1. 確認主機已開機。
2. 開啟 Edge 或 Chrome。
3. 輸入 `http://127.0.0.1:8080`。
4. 先閱讀每日經文。
5. 依「本週值班工作台」目前步驟操作。
6. 使用完畢只需關閉瀏覽器分頁；不要每天停止背景工作。

如網站打不開：

1. 等候 30 秒再重新整理。
2. 到工作排程器查看 `Sing Yin Roster Host` 是否「執行中」。
3. 如沒有執行，按右鍵→「執行」。
4. 做健康檢查。
5. 仍然失敗才查看第 14 節。

---

## 11. 備份安排

### 系統自動處理的備份

生成、發布、請假、名單修改及還原等重要寫入會建立 SQLite 快照和 SHA-256 manifest。它們在：

```text
C:\SingYinRoster\data\backups
```

### 你仍要做的離機備份

至少每星期一次，以及每次更新程式前：

1. 進入網站「系統設定」。
2. 確認最新快照顯示「已驗證」。
3. 按「建立交接備份包」。
4. 把下載的 ZIP 複製到學校批准的加密 USB 或其他受控離機位置。
5. 檔名加入日期，例如 `SYSS-Roster-Handover-2026-09-14.zip`。
6. 每月在練習／複製環境完成一次還原演練。

不要只把 `sing-yin-roster.sqlite3` 單獨拖走；manifest 和還原說明同樣重要。

---

## 12. 更新程式的完整步驟

只在沒有進行排班或發布時更新。

### 步驟 12.1：先建立已驗證離機備份

完成第 11 節全部步驟。

### 步驟 12.2：停止排程工作

1. 開啟工作排程器。
2. 找到 `Sing Yin Roster Host`。
3. 按右鍵→「結束」。
4. 確認瀏覽器重新整理後已不能進入網站。

### 步驟 12.3：下載最新 `main`

開啟普通 PowerShell：

```powershell
Set-Location C:\SingYinRoster
git status --short
```

正常情況不會列出程式檔修改。如果看到不明檔案或 `M`、`D`，先停止，不要執行 reset 或刪除，交給維護者檢查。

確認沒有不明修改後：

```powershell
git pull --ff-only origin main
```

這個命令只從 GitHub下載程式，不會上載本機資料。

### 步驟 12.4：更新 Python 套件

```powershell
C:\SingYinRoster\.venv\Scripts\python.exe -m pip install --require-hashes -r C:\SingYinRoster\requirements.lock
```

### 步驟 12.5：重新啟動及核對

1. 在工作排程器對 `Sing Yin Roster Host` 按右鍵→「執行」。
2. 開啟 `http://127.0.0.1:8080`。
3. 執行健康檢查。
4. 核對名單、最近一份週表和最新備份仍可讀。
5. 下載一份測試 PDF，確認中文正常顯示。

---

## 13. 建議的每月主機保養

每月安排一次 20 至 30 分鐘：

- [ ] 完成 Windows Update，並在無人使用時重新啟動。
- [ ] 確認磁碟仍有最少 30 GB 空間。
- [ ] 執行 `/healthz` 健康檢查。
- [ ] 確認工作排程器沒有重複的 Sing Yin 工作。
- [ ] 在設定頁確認最近快照已驗證。
- [ ] 建立一個新的離機交接備份包。
- [ ] 檢查 `logs\app.log` 是否持續輪替，而不是無限增長。
- [ ] 確認電腦仍不會接電自動睡眠。
- [ ] 核對主機日期和時區。

---

## 14. 常見問題與處理

| 畫面／情況 | 先做甚麼 | 不要做甚麼 |
|---|---|---|
| 網站打不開 | 檢查工作排程器，重新執行工作，再檢查 `/healthz` | 不要改成 `0.0.0.0` |
| 8080 被佔用 | 停止不需要的程式；背景排程應固定使用 8080 | 不要同時啟動兩份正式系統 |
| `database : degraded` 或不是 `ok` | 停止正式操作，保留日誌和最新備份，聯絡維護者 | 不要直接修改 SQLite |
| 畫面顯示 `OP-...` | 記下完整編號，先核對輸入；需要時查本機日誌 | 不要公開整份日誌 |
| 顯示「資料已儲存，但備份未完成」 | 重新載入核對結果，再到設定建立已驗證快照 | 絕對不要重複剛才操作 |
| 中文 PDF 變成方格 | 安裝 Noto Sans TC，或設定 `SING_YIN_PDF_FONT` | 不要改學生姓名為英文 |
| 排程在改密碼後失敗 | 重新開啟工作內容並儲存新密碼 | 不要改成管理員帳戶長期運行 |
| 更新時 `git pull` 失敗 | 保留完整訊息，停止更新並聯絡維護者 | 不要執行 `git reset --hard` |
| 電腦重新啟動後網站沒有出現 | 等候一分鐘，檢查工作排程器「歷程記錄」 | 不要重複建立多個工作 |

查找一個 `OP-...` 編號時，可由維護者執行：

```powershell
Set-Location C:\SingYinRoster
C:\SingYinRoster\.venv\Scripts\python.exe -X utf8 scripts\inspect_support_log.py --reference OP-XXXXXXXX
```

---

## 15. 如何安全停止整個系統

只有維修、更新或搬機時才需要停止：

1. 確認沒有正在進行生成、發布、請假調整、備份或還原。
2. 關閉所有網站分頁。
3. 開啟工作排程器。
4. 對 `Sing Yin Roster Host` 按右鍵→「結束」。
5. 做健康檢查；此時連線失敗是正常的。
6. 如要關機，使用 Windows「開始」→「電源」→「關機」。

不要在 SQLite 寫入途中直接拔電源。

---

## 16. 搬到另一部 Windows 主機

1. 在舊主機建立最新已驗證交接備份包。
2. 在新主機依第 2 至第 9 節全新安裝程式。
3. 先以新主機的練習模式確認運作正常。
4. 解壓交接包，把 SQLite 快照及同名 manifest 放入新主機 `data\backups`。
5. 在網站「系統設定」確認該快照顯示「已驗證」。
6. 使用介面內的受控還原，不要手動覆寫 runtime SQLite。
7. 核對名單、週表、公平帳本和中文 PDF。
8. 新主機完成後才停止舊主機，避免兩部主機同時作正式寫入來源。

---

## 17. 最後驗收清單

### 安裝者

- [ ] Windows 11 已更新。
- [ ] 主機接電時不會睡眠。
- [ ] 程式位於 `C:\SingYinRoster`，不在同步資料夾。
- [ ] `main` 分支已下載。
- [ ] Python 3.12 `.venv` 已建立。
- [ ] `requirements.txt` 安裝成功。
- [ ] `.env` 維持 `local` 及 `127.0.0.1`。
- [ ] 工作排程器只存在一個 `Sing Yin Roster Host`。
- [ ] 重新啟動後網站會自動恢復。
- [ ] `/healthz` 顯示 official 及 database ok。
- [ ] 已建立並移走一個已驗證交接備份包。

### 首席導學風紀

- [ ] 已完成一次完整練習模式。
- [ ] 知道每日只需開啟瀏覽器進入 `127.0.0.1:8080`。
- [ ] 知道只有發布才會更新公平帳本。
- [ ] 知道發布後請假必須使用「請假調整」。
- [ ] 知道看到 `OP-...` 時要保留編號。
- [ ] 知道不能直接修改 SQLite 或把 8080 對外開放。

---

## 18. 官方參考資料

- [Microsoft：Windows 11 電源設定](https://support.microsoft.com/en-us/windows/experience/power-battery/power-settings-in-windows-11)
- [Microsoft：工作排程器及 `schtasks`](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks-create)
- [Python：在 Windows 安裝及使用 Python](https://docs.python.org/3/using/windows.html)
- [Git：Git for Windows](https://git-scm.com/download/win)

本文件先配置本機 Windows 專用主機。需要遠端使用時，必須接續 [Cloudflare 遠端存取完整設定手冊](CLOUDFLARE_REMOTE_ACCESS_SETUP.md)；該流程仍不會開放路由器連接埠或把 NiceGUI 改綁 `0.0.0.0`。
