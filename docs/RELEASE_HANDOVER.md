# 首次發布與交接手冊 / First-release and handover guide

我是李創杰，2026–2027 年度首席導學風紀。我把這份手冊與系統一起留給下一任首席導學風紀，希望你不必依賴原開發者，也能安全完成每週排班、處理請假、理解公平紀錄，並把完整資料再交給下一任。以下操作程序以直接指令寫成，方便你在真正工作時逐項核對。

> **目前線上基線是 rc21：**受控 Windows origin 正運行 annotated tag `v1.2.0-rc.21`／commit `f7df4d0170e6bacd65340cc893992a17b5ed4aed`。291 個發布輸入以指紋 `e7b2a52a004968b899a76de583ca86cb1d575d2a9bbba4cedd5e0e7ab67361b1` 通過 14／14 正式 gate（完整 Python suite、3 motion、40 Worker contract）。切換前正式備份 `20260726-003841-844011-manual_verified_backup.sqlite3`、SHA-256 `fed7b02a82265477a19c9be675d7fd14e8d4b259055af5331e2f76f40b8ee777`、公平對帳、行數核對、還原審計及隔離還原全部通過。canonical Worker version `f780feb2-671a-4feb-b6f6-b7f9d5b31e89` 因 source／設定未變而刻意沿用；origin `/healthz` 健康、`/readyz` ready、`writeReady=true`、`policyVersion=2026.07.22-assist-modes`，沒有待處理備份義務。Windows `cloudflared` 已恢復為 Running／Automatic，canonical public／Guest／Trust routes 的桌面及手機 rendered smoke 通過且無 console／page error。第一級回退是 rc20／`e3d84858abfe23714929a87c4bcf76e55999ce7c` 與同一 Worker exact pair。首席導學風紀及教師顧問真人驗收仍未完成。

> **rc23 已完成 exact-source 機器驗證，但尚未上線：**commit `e66c697463d4982f1d7cb6c0f064f3c355aa0bee`／runtime fingerprint `b65b7a41714614793e3445be1ddff9fbc248b7b770f5160b6fc57a889427a7df` 已通過 14／14 正式 gate，包括完整 Python suite、3 motion、40 Worker contract、桌面／手機／平板、效能、Admin／Guest、雙語 PDF、完整寫入／公平／交接／隔離還原及備份失敗復原。Admin 支援事件只在明確同意後寫入隔離本機 inbox；Guest 支援摘要沒有發出網絡請求並在重新整理後消失。此證據不等於部署；建立 immutable tag、合併 protected main、正式備份／還原、Windows／Worker 配對切換及 canonical smoke 前，仍須以 rc21 作日常及回退基線。

> **部署時發現的主機漂移：**切換前 `C:\SingYinRoster` 的 rc20 checkout 有 26 個未提交／未追蹤項目。發布流程沒有把它們混入候選，而是完整保存為 stash commit `56e2f5148f4be1444c45d31c25b81f5a7df1ba03`，再從不可變 rc21 tag 部署；除非先作獨立差異審查，切勿把這份 stash 套回正式主機。
>
> **歷史 rc18 受控發布（已由 rc20 取代）：**annotated tag `v1.2.0-rc.18`／commit `fd504a8` 曾是 live origin。288 個發布輸入以指紋 `de0612fb8d9ee0530ba108efb1f658ab06e3e2212477fdb8832eb9ab3c0e1664` 通過 14／14 gate；正式備份 `20260722-024349-422389-manual_verified_backup.sqlite3`、SHA-256 `51ad0e42284c0d42363d2f8fd2bc3dc70ae0ce1f79d258016ec2d66bf6741c7f` 及隔離還原通過。其 host／Worker pair 現為 rc20 第一級回退目標。

> **手機／平板／桌面共存規則：**平板不是放大的手機，桌面也不可繼承平板壓縮。768×1024 及 820×1180 直向平板使用 adaptive shell，操作表單維持一欄，支援卡片可使用兩欄；1024×768 橫向觸控平板保留 compact desktop shell，但操作及文件區不得壓成多個狹窄欄，證據與下載最多兩欄；1440×1024 保留 full desktop shell 與閱讀寬度。四個 viewport 屬於同一候選裝置矩陣，並與手機共用同一網址、身份、路由、資料、排班規則、審計、PDF 及返回邏輯。

> **歷史 rc4 rollout 記錄（不可作現行步驟）：** rc4 已成功把正式 Alembic schema 由 `0007` 升至 `0008`，建立已驗證備份並完成隔離還原；其後 `git fetch origin main` 只更新 `FETCH_HEAD`，而 ancestry gate 讀取 stale `origin/main`，造成假失敗。rc4 因而從未被宣告為 live。自動 rollback 未能證明 origin health 後，主機以相容的 rc4／`30f282f` 完成 forward recovery；rc5／`bafaef6` 已改用明確 remote-tracking refspec，並重新通過完整 13-gate 報告。

> **歷史 rc7 分階段規則（現已完成）：** origin 階段阻擋每一個 failure 及所有其他 warning；只有明確依賴尚未部署 Worker 的 `cloudflare_access` 可暫時延後。匹配 Worker 上線後，這項檢查以及 Admin／Guest／Viewer／WebSocket 線上驗收全部通過，才結束 maintenance。後續發布須依本文件的通用受控次序重新產生候選專屬證據，不可重用 rc7 標籤或報告。

## 運作原則

我把本系統設計成本機優先、單一網站進入的工具。v1.2 中，訪客與管理員使用同一套 NiceGUI 頁面；訪客只操作有時限、虛構、記憶體內的工作區，管理員經 Cloudflare Access 後才使用正式 SQLite 工作流。收到我明確發出的 `/view#…` 連結的人只可查看該已發布週表。完整名單、請假、公平帳本、審計、備份及正式 PDF 仍留在受控 Windows 主機；只有首席導學風紀明確建立分享連結時，系統才把最少欄位、AES-GCM 加密的已發布週表密文保存到 Cloudflare KV。我希望每一項操作都服務於清楚、公平、責任與關顧，而不是把管理負擔交給下一位風紀。

我在任內由首席導學風紀負責日常操作；交接後亦應由下一任首席導學風紀承接。顧問老師主要在週表完成後檢視已發布結果、公平審計、備份和交接證據；本發布不要求老師日常生成、編輯或處理請假。

## 每週操作

1. 在「導學風紀名單」核對中文姓名、職務及可值班日。
2. 先登記未發布週的請假，核對「固定星期模式」或「每週靈活模式」，然後生成草稿。
3. 核對草稿的每日崗位、姓名與請假；草稿 PDF 只可核對，不可張貼。
4. 在明確確認視窗中發布；這時才會更新持續累計的 `history_weight` 公平帳本。
5. 用「下載列印版 PDF」選擇中文或英文單頁週表。已發布週表會先在記憶體中準備，然後提供「分享 PDF（可選 WhatsApp）」及「下載 PDF」；所有風紀姓名一律為中文，PDF 不會寫入公開網址。
6. 如需瀏覽器直達查看，從已發布週表或「存取控制台」明確建立唯讀連結；等待「安全處理」完成，系統確認公開端已讀到同一份加密快照後才會顯示完整連結。只把完整連結發給需要查看的人。
7. 如發布後有人請假，使用「請假調整」；不要改動歷史資料或直接覆寫 SQLite 檔案。完成收據會顯示扣回／轉移點數、週表新版本、帳本對帳及備份結果。立即用收據上的入口重新匯出及分享修正版；如使用 Viewer，建立新連結並撤銷舊連結。

新週次在介面預設使用「固定星期模式」。啟用 AHP 名單及可值班日不變時，同一人會在固定星期重複當值；已登記的本週請假只會為該次當值使用合資格替補，沒有替補則停止生成並清楚指出空缺。「每週靈活模式」按週次作可重現輪換，並在公平與可值班條件容許時優先避開個人上週相同星期。重開既有草稿時必須沿用該週已保存的模式，除非操作員在重新生成前明確更改。兩種模式均不得安排未選的可值班日；完整說明見 [Assist. in charge 編排模式](ROSTER_POLICY_MODES.md)。

名單新增／修改／停用，以及生成前請假登記／取消，均可能同時建立本機快照。按下操作後，請等候雙語「安全處理」視窗完成，不要重複點擊或關閉分頁。漏填中文姓名、班別、可值班日或替補選擇時，系統會先把焦點帶回相關欄位，不會開始寫入；週開始日期不是星期一亦會先提示修正。生成前請假、草稿修改、發布後請假調整及撤回原因均屬選填；留空不會削弱版本核對、公平對帳、審計或備份。停用風紀前必須閱讀確認：停用不是刪除，既有週表、公平帳本及審計紀錄仍會保留，而且介面沒有即時復原功能。

如另一個分頁已修改同一位風紀或同一份草稿，系統會拒絕較舊版本，不會用舊畫面覆蓋新資料。不要再次按儲存；依提示重新載入、核對最新內容，再重做仍然需要的改動。淺／深色模式和提示音會在原頁即時切換，不會令表單重載；語言切換需要重載，因此有未儲存輸入時會先詢問是否離開。

完整的新手與日常操作說明見 [操作手冊](OPERATOR_GUIDE.md)；系統內亦可從「使用手冊」直接閱讀同一流程。

## 名冊資料匯入 / Prefect data import

名冊檔案不應一上傳便直接寫入。按以下次序完成：

1. 前往「導學風紀名單」→「資料匯入」，先下載格式範例；準備不超過 2 MB 的 `.csv` 或 `.xlsx`。如檔案是舊式 `.xls` 或含巨集，先另存為普通 `.xlsx`；公式儲存格不會獲接受。
2. 選擇檔案。系統先在本機讀取；如有多個工作表，選擇真正的名冊工作表。
3. 逐欄核對「中文姓名、級別、班別、職務、可值班日」；備註可留空。同一來源欄不可配對兩次。
4. 按「驗證配對並預覽」。先核對每個中文姓名、正式職務及可值班日；有任何錯誤都不要按匯入。
5. 預覽完全正確後，才按最終匯入按鈕。這一步才會經正式工作流寫入 SQLite、留下審計脈絡及建立本機快照。

頁面下方保留貼上 JSON／CSV 的短名單方式，但同樣必須先預覽再確認。手動欄位配對永遠可用，不需要外部服務。

可選 DeepSeek 建議預設關閉。只有當本機 `.env` 同時設定 `SING_YIN_DEEPSEEK_ENABLED=true`、獲准模型，以及一個**新建立**的 `SING_YIN_DEEPSEEK_API_KEY`，按鈕才可使用。每次仍須由操作者主動按下；系統只傳送欄名、資料型態及約略非空筆數，不傳送中文姓名、完整資料列、工作簿或匯入結果。回來的配對只會填入選單，必須依第 3 至 5 步核對。金鑰只放在已被 Git 忽略的本機 `.env`，不可貼進文件、程式、日誌、備份或 Git。沒有需要時保持 `SING_YIN_DEEPSEEK_ENABLED=false`。

## PDF 列印

- 「中文週表 PDF」和「英文週表 PDF」均為橫向單頁 A4，保留清楚的「左欄崗位、上欄星期、格內中文姓名」版面，可於核對後透過校內受控渠道分享。
- 週表檔名包含資料庫週表版本，例如 `SYSS_Roster_20260907_v2_中文.pdf`。首次發布一般為 `v1`；每次已發布後請假調整會遞增版本。已發出的舊 PDF 不會自行更新，必須重新生成並清楚通知群組以新版本為準。
- 手機按「分享 PDF（可選 WhatsApp）」會開啟作業系統分享面板；再由操作者選擇 WhatsApp 及群組。瀏覽器不能預先指定群組或代替操作者發送。若裝置不支援 PDF 檔案分享，按「下載 PDF」後在 WhatsApp 手動加入附件。
- 「內部公平審計 PDF」另行以直向 A4 輸出，含個人累計點數及次數；預設只給首席導學風紀與老師顧問。若需向群組說明公平性，先分享規則和整體趨勢，並取得老師顧問同意後才考慮分享具名帳本。
- 系統隨程式附帶 `nicegui_app/assets/fonts/NotoSansHK-Regular.ttf`、`NotoSansHK-Medium.ttf` 及 `NotoSansHK-SemiBold.ttf`，正常部署毋須另外安裝中文字體。如三個檔案遺失或校驗失敗，先從正式版本重新部署；只有經測試的替代字體才分別用 `.env` 的 `SING_YIN_PDF_FONT_REGULAR`、`SING_YIN_PDF_FONT_MEDIUM`、`SING_YIN_PDF_FONT_SEMIBOLD` 指定。舊有 `SING_YIN_PDF_FONT` 只會覆蓋 Regular，不足以代表完整三字重設定。
- 先開啟 PDF 並核對所有中文姓名與草稿/發布狀態，再校內列印或透過學校核准的受控渠道分享。

## 服務與公平總結報告 / Service and fairness summary

這份報告用於學期／年度回顧、內部匯報及交接核對，不是另一套公平帳本：

1. 前往「導學風紀名單」→「公平審核」。在頁面下方選擇首個及最後一個週表的星期一；系統以完整週表為範圍。
2. 按「產生／更新預覽」，先核對已發布週數、最終崗位覆蓋、請假調整、Assist. in charge 覆蓋、公平帳本對帳及個人參與記錄。
3. 草稿不會計入；發布後的替補或保留空缺會按最終狀態呈現。產生或重複整理預覽都是唯讀，不會更新 `history_weight`，也不會重複入帳。
4. 核對後可下載繁中 PDF、英文 PDF 或 JSON 證據包。兩份 PDF 的姓名均保持中文；JSON 記錄來源週表版本、政策版本及內容 SHA-256，方便日後核對。

「已編排時數」只按目前 `DUTY_SERVICE_TIME_WINDOWS` 對最終值班安排作排程換算；所有崗位的實際當值時段均為 15:40–17:00。302 室及 Assist. in charge 的房間開放顯示可延至 18:30，但不會因此增加服務時數。系統沒有簽到／完成服務紀錄，因此這個數字**不是出席證明、完成服務時數、個人表現評核或服務證書**。如日後需要正式證書，必須另行建立已核實的出席及批准流程，不能改稱現有排程資料。

JSON 是唯讀報告證據，不是 SQLite 還原備份。需要交接或復原整個系統時，必須依下一節建立已驗證交接備份包。報告、JSON、PDF 及具名資料都不會自動上載到 GitHub；下載後由操作者按受控保存程序處理。

## 備份與復原

- 每次生成、發布、請假、名單修改與還原均會建立可驗證 SQLite 快照。
- 在「系統設定」只選擇標示為「已驗證」的快照。還原前系統會先建立 `pre_restore` 安全快照。
- 「已驗證」不只代表檔案可打開：系統會核對 manifest、SHA-256、SQLite 完整性及完整資料表契約。受控還原會先把候選快照複製到隔離位置，在副本上升級至目前 Alembic head，再核對 schema 與公平帳本；任何缺表、migration 或對帳失敗都會停止。正式 live 資料庫完成啟動或還原後必須位於目前 head，否則 `/healthz` 會顯示 degraded，而不是健康。
- 新安裝或尚未完成第一次快照時，交接包與還原按鈕會停用；依空狀態提示按「立即建立已驗證快照」。只有校驗成功並重新載入後，才可選擇還原或建立交接包。不要嘗試以手動放置、改名或未附 manifest 的 SQLite 檔繞過此狀態。
- 若畫面顯示「最近檢查的快照中，有 N 個未通過驗證」，這些檔案已被隔離於交接／還原選單。分類只用來指出 manifest、checksum、SQLite 或 schema 層級；不要自行修補或刪除證據。先建立新的已驗證快照，若仍失敗，向受控 IT 支援提供 OP／REQ 編號，由支援人員在本機調查。
- 離機備份時，在「系統設定」按「建立交接備份包」。確認敏感資料提示後，系統只會下載最近一份已驗證快照、對應 SHA-256 manifest 及還原說明；封包在記憶體本機生成，不會自動加密、上載或留下第二份本機副本。
- 立即把下載的 ZIP 儲存在學校批准的加密離機位置。日後需要還原時，解壓 ZIP，把 SQLite 檔案及同名 manifest 一併放回 `data/backups/`，再在「系統設定」選擇顯示為「已驗證」的快照。切勿在程式執行時手動覆寫 `data/runtime/sing-yin-roster.sqlite3`。
- 每次交接均由繼任者在「交接指引」確認：名單存在、週表歷史可讀、最近備份已驗證。
- 如畫面顯示「資料已儲存，但備份未完成」，不可重複剛才的生成、發布、調整或名單操作。先按「重新載入並核對」，確認資料庫結果，再到「系統設定」按「立即建立已驗證快照」。只有新快照顯示「已驗證」後才繼續下一項工作。
- 還原後，瀏覽器歷史或舊書籤可能指向已不存在的週表。看到「找不到這份值班表」時，不代表目前資料再次損壞；先按「查看現有值班表」核對現有週次，如剛完成還原則再按「核對備份與還原」確認快照。不要修改網址中的週表編號猜測資料。
- 只有已發布週表可進入「值班後請假調整」。如直接開啟草稿的調整網址，系統會要求返回該週表完成核對及發布，不會顯示可提交表單，也不會改動公平帳本。
- 每次會改動資料的操作，會把「提交 → 建立快照 → 校驗 → 備份證據入帳」鎖成同一個跨程序序列；另一個分頁或程序必須等待，故操作回傳的版本與恢復點不會錯配。這不是畫面上的重複點擊鎖，而是主機資料層的保護。
- 還原會先進入全主機 maintenance 狀態。系統以跨程序 operation lease 等候其他分頁／程序的正常工作及其快照完整結束，然後才取得獨佔 marker；期間新操作會被拒絕，頁面會顯示維護狀態。候選快照會先在隔離副本完成 migration、外鍵及公平帳本對帳，再接觸正式資料庫。若交換後的重連或審計失敗，系統會自動裝回 `pre_restore`；只有無法證明回復安全時才保留 recovery-review marker，等待 IT 支援處理。

## 本機設定

### 問題回報與支援收件匣

操作者先由網站 `/support` 建立支援編號及已刪減摘要。Admin 只有在畫面
再次確認後，才可把有限 TXT／JSON／PNG 證據保存到主機本機收件匣；Guest、
Public 及 Viewer 一律只在瀏覽器建立報告。支援記錄不屬於排班交易、正式
SQLite、公平帳本、週表 PDF、備份或 Git 發布輸入。

維護者只使用以下唯讀入口查看摘要，不直接翻找或改名收件匣檔案：

```powershell
python -X utf8 scripts\inspect_support_inbox.py
```

如需要主機控制狀態，另執行
`scripts\collect_host_security_summary.ps1`；輸出只記錄設定是否存在及服務
狀態，不記錄 secret 值。將摘要交到 GitHub 時，只貼支援編號、版本、可公開
重現步驟及已刪減技術內容；姓名、請假、週表、完整資料庫／備份、cookie、
token 及完整日誌留在私人受控渠道。完整程序及威脅模型見
[本機問題回報與事故處理](SUPPORT_AND_INCIDENT_WORKFLOW.md)及
[支援收件匣威脅模型](THREAT_MODEL_SUPPORT_INBOX.md)。

正式長期主機採用 Windows 11，並維持 NiceGUI 只監聽 `127.0.0.1`。第一次由空白電腦安裝、設定開機自動啟動、更新、保養或搬機時，先依 [Windows 專用主機完整設定手冊](WINDOWS_DEDICATED_HOST_SETUP.md) 完成，不要從本節零散拼湊指令。

受控技術維護可使用 [Windows SSH 維護通道](WINDOWS_SSH_MAINTENANCE.md)。正式設定只接受 Ed25519 金鑰、只監聽 loopback，並拒絕密碼、轉發及公開 TCP 22。`SingYinRosterSvc` 仍是非互動網站執行帳戶，不可用作 SSH 登入；SSH 私鑰亦不可放入 Git、交接備份、日誌或雲端同步資料夾。

需要從其他裝置工作時，只使用同一正式網站：<https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/>。目前 live rc20 中，訪客不需輸入電郵或密碼，只按「訪客體驗」建立有限期 Guest session；管理員按同站「管理員登入」，輸入 exact-email policy 列明的電郵及 Cloudflare 寄出的單次驗證碼。Worker 驗證相應 session 後，以獨立 HMAC principal 把 Guest／Admin 送到同一 NiceGUI origin；origin 再分流至虛構記憶體 adapter 或正式 workflow。私人 WARP 及本機 `127.0.0.1` 保留作故障維護後備。完整設定見[Cloudflare 遠端存取完整設定手冊](CLOUDFLARE_REMOTE_ACCESS_SETUP.md)，分享週表見[單一網站存取手冊](PUBLIC_ROSTER_VIEWER.md)。

### 交接前練習模式

- 新任首席導學風紀先雙擊 `START_PRACTICE_MODE.cmd`，完成一次生成至還原的完整流程，再進入正式模式。
- 只在頁頂持續顯示「練習模式」時使用虛構資料；練習 PDF 有 `PRACTICE_` 檔名前綴及雙語非正式標記。
- 練習資料、備份、日誌及介面偏好全部位於 `data/practice/`，正式 SQLite、公平歷史及備份不會被開啟。
- 重設前先關閉練習服務，然後雙擊 `RESET_PRACTICE_MODE.cmd`。若練習服務仍在執行，重設器會拒絕刪除。
- `/healthz` 的 `applicationMode` 及啟動器模式核對，防止正式與練習視窗互相誤用。

### 正式零起點與公開試用的分界

- 正式模式第一次啟動只建立已遷移的空白資料庫，不會自動載入示範名單。空白「導學風紀名單」是正確的首次狀態；只可由首席導學風紀核對後匯入真正名單。
- Practice Mode 保留虛構 seed、獨立 SQLite、審計、備份及還原，供繼任者完整演練。
- v1.2 Guest 不是 Practice Mode，也不是另一套 `/try` 靜態產品。`/guest`、`/try` 只作兼容重定向；Guest 使用同一 NiceGUI 路由，但只連到固定虛構中文姓名的程序記憶體 workspace，30 分鐘後失效。
- Guest 可示範請假、生成、手動修改、發布、雙語 PDF／JSON、發布後請假調整及公平說明；AI、匯入、上載、正式備份／還原、Viewer 分享及永久設定仍由服務層拒絕。每個分頁的最新狀態只以已簽署、綁定 session／workspace／tab 的 token 放在 `sessionStorage`，還原時須核對當次連線 nonce；它不能寫正式 SQLite、公平帳本、備份或外部整合。
- Guest 下載是一次性、`DEMO` 標示及 `no-store`；下載檔只因訪客主動保存而存在，不能轉入正式資料或成為公平／服務證據。
- Guest 的語言、深淺模式、音樂及音效只在已核實 session 的 origin 記憶體中保留；重新整理可延續，登出、到期、撤權或程序重啟即清除。預設外觀跟隨裝置系統，無法判定時使用深色；按外觀控制可依次選系統、深色及淺色。
- Admin／Guest 的繁中 PDF、英文 PDF 及 JSON 均由同一帶憑證交付流程下載；如失敗，先記下畫面顯示的支援編號再重試，不要把瀏覽器「無法擷取檔案」當成 PDF 內容錯誤。

### 發布錯誤時：撤回，不直接刪除

如整個週次發布錯誤，在週表調整頁選「撤回已發布值班表」。操作員必須核對週次；原因可選填。系統保留原週表、請假調整及審計，以補償項抵銷該版本的淨公平點數，建立已驗證備份義務，並把既有公開分享送入撤銷程序。畫面顯示撤回完成後才重新生成；不要直接刪 SQLite、改公平帳本或重複按確認。

### 一次性退休舊示範資料（只供受控 IT 維護）

舊主機如曾以正式路徑載入示範資料，不可在網頁逐項刪除，也不可直接移除 SQLite。歷史不可變發布版本 `v1.1.0-rc.16` 已提供 `scripts/reset_official_data.py` 作一次性、明確確認的受控遷移：主機必須先停止；工具先核對資料庫與公平帳本，建立新已驗證快照並在另一隔離資料庫完成還原演練，撤銷並重新核對所有公開 Viewer 連結，再把舊資料及舊備份移入受限 quarantine，最後原子安裝已遷移的空白 SQLite 及唯一一份已驗證空白基線。任何一關失敗均停止；安裝後核對失敗會自動回復原資料，無法證明回復時保留 recovery-review marker。

這不是日常「清空」功能，也不會出現在網站。只可使用已通過完整發布閘門的不可變版本，在核對目標路徑、停止並停用正式工作排程後由維護者執行；正式主機是否已完成清除，必須以 sanitized reset report、零筆業務資料表、有效空白基線及重新啟動後 `/healthz` 證據判斷，不可只看空白頁面或口頭聲稱。

正式指令、`--host-port-range 8080-8099`、固定確認詞及 report 路徑見 `docs/WINDOWS_DEDICATED_HOST_SETUP.md` 第 8.2 節。正常主機必須使用已設定的 Viewer gateway 完成列出／撤銷／重新核對；`--attest-no-public-share-gateway` 只適用於能證明從未設定 gateway、從未發出 `/view#…` 的主機，不能在 token 遺失、網絡失敗或 gateway 暫時不可用時代替撤銷。

### 每日開啟（首席導學風紀）

1. 開啟唯一正式網站，按「管理員登入」。不要收藏或派發內部 `/auth/*` 路徑。
2. 使用 Access policy 內精確列明的管理員電郵，輸入 Cloudflare 寄出的單次驗證碼；驗證成功後同一網站建立簽署管理員 session 並解鎖工作台。
3. 首頁的「第一次使用？請由這裏開始」及選單「開始使用」會帶領新手先核對名單，再生成草稿。
4. 「交接指引」會同時顯示三項資料準備狀態、目前機器驗證狀態，以及仍需真人完成的四個重點。看到「報告已過期」時，代表程式或驗證規則在上次報告後有改動；只由 IT 支援重新執行發布候選驗證，不要用真實資料自行試錯。
5. 工作完成後按「登出」。簽署管理員 session 最長 8 小時且受 Access 到期時間約束；登出會先清除該 session，再結束 Cloudflare Access session。共用裝置不可只關閉分頁。

只有 Cloudflare 故障或主機維護時才雙擊 `START_SING_YIN_ROSTER.cmd`。啟動器會重用既有服務，並在 8080 被佔用時選用 8081–8099；使用黑色視窗顯示的完整 localhost，不要猜測埠號。

### 新學年名單交接（首席導學風紀）

「交接指引」的「準備新學年名單」不是刪除歷史的重置。只在本學年最後一份週表、請假調整及公平核對均完成後使用：

1. 先核對最近備份有效、舊週表可讀及公平帳本已對帳。
2. 閱讀確認視窗的後果，輸入畫面指定的完整確認詞。
3. 系統取得全主機 maintenance lock，建立操作前已驗證備份，封存目前所有啟用風紀及撤回尚未使用的生成前請假，再建立操作後已驗證備份。
4. 舊週表、公平帳本、審計及已封存姓名均保留；日常名單變成空白後，才匯入新學年名單。相同中文姓名可在新學年建立新的獨立記錄，不會改寫舊記錄。
5. 如結果不符預期，不要手動改 SQLite；到「系統設定」依受控還原程序選擇操作前備份。

若封存已提交但操作後備份未能完成，系統會保留 maintenance recovery lock，阻擋所有後續寫入，並顯示 OP 支援編號。不要重複操作、重新開機或自行刪除維護標記；保持主機運行，由受控 IT 支援先驗證操作前備份，再決定受控還原或建立新的已驗證基準。這個鎖定是為了避免新寫入令操作前復原點變得有損。

此功能適合每年交接，不可取代第 8.2 節的一次性舊示範資料退休工具；後者會清理整個未正式啟用的官方資料集及舊備份，只由受控維護者執行。

### 首次設定（教師顧問或 IT 支援）

1. 複製 `.env.example` 為 `.env`。本機模式首次啟動會自動建立 `data/runtime/.nicegui-storage-secret`，後續啟動會沿用；不要把此檔案加入 Git、上載或複製進 PDF／交接包。只有未來 `server` 模式才必須由學校受控環境變數提供至少 32 字元的 `SING_YIN_STORAGE_SECRET`。
2. 安裝需求並在專用、受控的校內電腦啟動：

```powershell
python -m pip install --require-hashes -r requirements.lock
python -X utf8 -m nicegui_app.main
```

3. `SING_YIN_OPEN_BROWSER` 預設為 `true`，令首次開啟更直接；受控或無介面運行可設為 `false`。
4. 只使用 `http://127.0.0.1:8080`；現時程式刻意只綁定 localhost。
5. 完成一批更新後先執行 `python -X utf8 scripts\verify_update.py`。它會按 Git 變更自動選擇 `docs`、`tests`、`assurance`、`worker` 或 `full`，並顯示執行及略過理由；未知路徑一律升級，不會靜默少驗證。只有正式 runtime、政策、資料庫、依賴、Worker、Windows 主機或正式證據閘門改動，才需要先安裝 `requirements-dev.lock`、Chromium 及 Deno，再由同一命令啟動完整 `verify_release_candidate.py`。目前完整入口共有 14 道閘門：Git 邊界、安全掃描、Cloudflare Worker Deno 契約、獨立圖標互動狀態機、完整 Python 測試、編譯、依賴、桌面 UI、跨頁效能／記憶體、隔離寫入／PDF／還原、手機適應、嚴格部署就緒、統一訪客隔離及備份失敗復原。它自行建立臨時資料庫、備份及日誌，絕不採用正式學校資料路徑；只有 `logs/release-candidate-report.json` 的所有項目均為 `pass` 且 runtime 指紋仍相符，才算機器驗證完成。文件、測試及 CI 改動另有聚焦證據，不會令已證實的 runtime 誤報過期；詳細矩陣見 `docs/UPDATE_WORKFLOW.md`。這不能取代下方的人手驗收。
   `D:\code_v3` 是開發及驗證副本，`C:\SingYinRoster` 是目前工作排程器實際執行的安裝副本；修改前者不會自動更新後者。完成驗證後仍須依 Windows 專用主機手冊第 12 節備份、停止、更新、重新啟動及核對，否則瀏覽器會繼續顯示舊版。
6. 不要在 `verify_update.py` 或完整 verifier 通過後再重跑同一套 hygiene／security；它們已由所選 profile 擁有。只有單獨調查某一道閘門時才直接執行相應腳本。發布前仍須人工閱讀 `git status --short`，不可用未核對的 `git add -A`；沒有真正 commit 歷史、被追蹤的運行資料，或尚未加入 Git 的發布敏感程式／遷移／Cloudflare／設定／交接文件，都會由 repository hygiene 阻擋。

### 操作失敗與本機支援記錄

- 若操作未能完成，畫面會顯示一個 `OP-...` 支援編號。失敗不會自行發布值班表；先檢查輸入、請假及校規限制，再安全重試一次。
- 「資料已儲存，但備份未完成」不是普通失敗：資料已提交，絕不可重試。系統會以 `event=operator_action_partial` 記錄，不含姓名或表單內容；依畫面先核對已提交結果，再建立手動已驗證快照。
- 每個正常 HTTP 請求亦會得到 `REQ-...` 追蹤編號（在 `X-Request-ID` 回應標頭）。它讓 IT 支援把「某次開啟／下載／頁面錯誤」與本機日誌連結；首席導學風紀通常只需提供畫面上的 `OP-...`。
- 如問題持續，把 OP 或 REQ 編號交給教師顧問或 IT 支援。他們可在系統資料夾執行：`python -X utf8 scripts\inspect_support_log.py --reference OP-XXXXXXXX`；這個工具只讀取最近的匹配本機記錄。不要把整份日誌上載至公開網站或個人雲端。
- `logs/app.log` 會以 UTF-8 輪替，並在受控終端即時顯示相同的安全記錄。每行只記錄事件、受控操作／路由分類、狀態、耗時、例外類型、程式位置及 OP／REQ 追蹤編號；系統不會寫入姓名、請假原因、表單內容、查詢字串、值班表內容或 PDF 內容。瀏覽器關閉 localhost 連線所產生的 Windows 64／10054 重設只會記為資訊事件；其他未捕捉的異步錯誤仍會保留為嚴重事件並交回系統處理，不能因為「消除紅字」而被隱藏。
- `.env` 可用 `SING_YIN_LOG_DIR` 指定另一個受控本機資料夾；`SING_YIN_LOG_LEVEL`、`SING_YIN_LOG_CONSOLE`、`SING_YIN_LOG_MAX_BYTES` 及 `SING_YIN_LOG_BACKUP_COUNT` 可調整受控本機診斷行為。不可設定為 OneDrive、Google Drive 或其他未經學校批准的同步位置。
- 一般使用意見、流程疑問及交接建議可電郵 `s10777@syss.edu.hk`。技術問題先附畫面上的 OP／REQ 編號及簡短描述；診斷確有需要時可附上相關資料，寄出前請核對收件人及附件，並只提供解決問題所需的部分。

### YouTube 音樂（首席導學風紀自選）

登入入口每次開啟都會以 50% 音量嘗試播放歡迎音樂一次，其後保留所有明確選擇的音量，包括 25%。如瀏覽器攔截聲音，入口會顯示「開啟音樂進入」與「安靜繼續」；只有前者在該次按鍵／點擊內直接重試，不會由其他頁面操作暗中重試。登入後的本機情境音樂保留獨立的工作台偏好：新版結構只會把仍等於舊版精確 24% 或 35% 預設的瀏覽器升級一次，首席導學風紀可在耳機控制／設定關閉跨頁自動播放。同一首本機歌曲如適用於跳轉前後兩頁，系統會在目前瀏覽器 session 延續播放位置及播放／暫停狀態，不會從頭開始；換歌或關閉瀏覽器 session 則不沿用。音樂狀態不影響名單、排班、公平、備份或 PDF。

1. 公開歌單功能可選使用，無需帳戶、付費或 API key。在「設定」貼上公開 YouTube 歌單連結，填寫不含學生資料的顯示名稱，並選擇適用頁面。
2. 回到指定頁面按耳機圖示。YouTube 以完整可見控制窗顯示，且不會隨本機情境音樂自動播放；由操作員使用原生控制開始、暫停、調校音量及換歌。
3. 如需站內搜尋，由維護者在本機 `.env` 設定 `SING_YIN_YOUTUBE_API_KEY`。一般歌單播放不需要；key 不可提交至 Git、貼入介面或交給下一任私人帳戶保管。
4. 音樂與提示音是個人操作偏好，不進入排班資料庫、公平帳本、PDF、審計或交接包。顧問老師核對時不需要設定或操作音樂。
5. 歌單名稱與搜尋字不得含學生姓名、班別、請假或值班內容。日後啟用遠端存取前，重新確認校方網絡、YouTube 使用及音樂播放安排。
6. 播放窗採用 YouTube privacy-enhanced 網域、無 referrer、無自動播放及無未使用的 JavaScript 控制 API；搜尋縮圖只接受官方 YouTube 圖片主機。這些保護不代表可把學生資料輸入搜尋框。
7. 首頁經文的「預設設定」會在淺色模式優先清晰指引、深色模式優先安靜安慰；首席導學風紀可改為固定方向。音樂已採相同語法：淺色建議「明亮專注」、深色建議「安靜反思」，也可固定選擇。切換外觀不會自動開始歌曲。
8. 可把獲准使用的 HTTPS YouTube／YouTube Music 影片、Shorts 或公開歌單分享連結保存到 `music/youtube-imports/`。每次最多 25 首、每首 25 MB、合計 150 MB；匯入器不登入、不讀 cookies，並與排班 SQLite、備份及交接包分開。完整技術決定見 `docs/MUSIC_IMPORT_DECISION.md`。

## 單一網站遠端交接：Guest 示範、管理員編輯與唯讀 Viewer

開始交接前，先閱讀[部署與遠端存取決策指南](DEPLOYMENT_DECISION.md)、[Cloudflare 手冊](CLOUDFLARE_REMOTE_ACCESS_SETUP.md)及[單一網站存取手冊](PUBLIC_ROSTER_VIEWER.md)。只派發 canonical workers.dev 主網址；不另發管理員、WARP、localhost、VPC 或 `/auth/*` 網址。

桌面、tablet 與手機均使用同一主網址、登入、資料及權限；不要建立或派發 `/mobile`、第二個子網域或另一套登入。在 900px 或以下，窄屏只是同一網站的獨立排列：上方為單行頁首，下方固定顯示 **Dashboard／Rosters／Prefects／More**；語言、深淺模式、聲音、登出及較少使用的頁面由 **More** 導覽抽屜開啟。抽屜必須可捲動到底，底部導航必須避開手機安全區，並不得遮蓋最後一個表單欄位、按鈕或頁尾。鍵盤及讀屏順序先讀本頁內容，再到固定底部導航；由共享導航進入新頁時焦點移至 `main`，讀屏不必重新猜測頁面位置。**More** 在次要頁可視覺上保持 active，但它仍是 menu trigger，不可自稱 `aria-current=page`；抽屜內實際頁面才是 current item。鍵盤開啟抽屜後，焦點移到抽屜並在其中以 Tab／Shift+Tab 循環；按 Escape 或背景關閉後，焦點返回 **More**。手機軟鍵盤開啟時，`visualViewport` 邏輯會暫時讓固定底欄退開並把焦點欄位移到安全區；頁面在 256 CSS px／200% zoom 仍須 reflow，只有明確資料區可局部橫向捲動。Tablet 的操作表單保持單欄，證據／參考資料才使用雙欄。

1. 核對主網址未登入時顯示統一品牌入口，不會自動要求所有人登入。
2. 按「訪客體驗」後，Worker 建立最長 30 分鐘 Guest session；NiceGUI 顯示與管理員相同的路由及元件，但只使用虛構記憶體 workspace。
3. 核對「管理員登入」由 path-specific Cloudflare Access policy 接管；只有 exact-email 管理員收到並正確輸入 Cloudflare One-time PIN 才可通過。系統沒有自製密碼資料表或帳戶復原頁。
4. Worker 對 Guest／Admin 分別建立有限期 session，移除瀏覽器身份標頭，再向 origin 注入 HMAC 簽署的 `mode`、`subject`、`sid`、`exp`、`auth_epoch` 及 `kid`。NiceGUI 重新驗證後才建立 `PageContext`；瀏覽器自報角色或電郵永遠不可信。
5. 主動「登出」會清除應用 session、Guest workspace、待下載檔案及同 session 分頁狀態，再結束 Cloudflare Access session。前任離任時更新 exact-email policy，不交接前任密碼。
6. 具名 Tunnel 只連至 `127.0.0.1:8080`；NiceGUI 不綁 `0.0.0.0`，也不開放資料庫、備份目錄或檔案分享埠。
7. 同時核對 `/healthz` 及 `/readyz`；只有 `writeReady=true`、沒有 maintenance／recovery／pending backup obligation 時才接受正式寫入。
8. 以虛構已發布週表實測同 host `/view#…` 連結的建立、普通瀏覽器直達、到期及撤銷；Guest 不能建立正式 Viewer 連結。
9. 本機及 WARP 只保留作維護後備。Worker／origin 的 session、principal、Viewer 及 Tunnel secret 值不可出現在版本庫、文件、截圖或交接包。

### rc21 已完成發布紀錄與後續候選次序

rc21 的正式部署證據固定為 tag `v1.2.0-rc.21`／commit `f7df4d0170e6bacd65340cc893992a17b5ed4aed`／fingerprint `e7b2a52a004968b899a76de583ca86cb1d575d2a9bbba4cedd5e0e7ab67361b1`。正式備份 `20260726-003841-844011-manual_verified_backup.sqlite3` 及其隔離還原已通過；Worker 沒有改動，仍為 `f780feb2-671a-4feb-b6f6-b7f9d5b31e89`。第一級回退是 rc20／`e3d84858abfe23714929a87c4bcf76e55999ce7c`，rc18／`fd504a8` 只作第二級已驗證基線。下列 rc20 命令與證據保留作歷史程序參考，不可當作目前版本重跑。

1. 在最後來源 commit 只執行一次 `python -X utf8 scripts\verify_update.py --release`；它已擁有完整 pytest、瀏覽器、Worker、效能、備份失敗及部署就緒閘門，不要再重複跑同一套檢查。
2. rc20 的正式發布證據固定為 tag `v1.2.0-rc.20`／commit `e3d84858abfe23714929a87c4bcf76e55999ce7c`／fingerprint `93c6c93866c617862c790a4ed939d9acbe789dcdfaf512c9519aff9e0b4e6d3a`；14／14 gate、839 項 Python、3 項 motion 及 40 項 Worker contract 全部通過。受控切換、正式備份、隔離還原及 canonical smoke 已完成；任何來源改動都不能沿用這份證據。
3. 保存目前 rc20／`e3d84858` 及 Worker `f780feb2-671a-4feb-b6f6-b7f9d5b31e89` 作現行不可變版本；另保留 rc18／`fd504a8` 作第一級回退。後續候選仍須在受控切換及線上核對完成後才可寫成已部署。
4. rc20 當時由提升權限的 PowerShell 從乾淨候選工作樹執行下列命令；這是歷史紀錄，**不可重跑**。後續候選須使用新的獲批准標籤與乾淨工作樹：

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass `
     -File C:\Users\lichu\.codex\worktrees\rc20-candidate\scripts\deploy_windows_release.ps1 `
     -SourceRoot C:\Users\lichu\.codex\worktrees\rc20-candidate `
     -HostRoot C:\SingYinRoster `
     -ReleaseRef v1.2.0-rc.20 `
     -TaskName "Sing Yin Roster Host" `
     -RuntimeUser SingYinRosterSvc
   ```

   腳本在切換前建立正式已驗證快照、完成隔離還原、進入 maintenance、停止受保護工作、安裝 exact bundle、執行 additive migration `0011_assist_assignment_mode`、重新啟動並核對健康。未來候選的工作樹若不存在，須以該次新 annotated tag 重建乾淨工作樹，不可改用一般開發樹。
5. 核對 `/healthz`、`/readyz`、管理員本機工作流及備份義務。
6. rc20 的 Worker source／設定與歷史 rc18 Worker 完全相同，因此發布時沒有重新部署 Worker，並在紀錄填上「刻意沿用 verified version `f780feb2-671a-4feb-b6f6-b7f9d5b31e89`」。只有日後 Worker source 或受保護設定實際改變，才使用 staged Worker rollout。
7. 在 canonical 網址核對 Public、Admin、Guest、Viewer、WebSocket、登出、到期及跨分頁隔離；所有能力仍須由伺服器拒絕優先，而非依賴隱藏按鈕。另按[正式驗收證據矩陣](ACCEPTANCE_EVIDENCE.md)以真實 touch phone／tablet、1440×1024 desktop 和鍵盤逐項核對 rc20 的 Assist 模式切換、可值班日、首屏 CTA、200% zoom、軟鍵盤、route focus、44px 目標、兩個 themes、reduced motion 及 forced colours。
8. rc20 的線上證據已通過並可供真人驗收。未來候選在正式切換前失敗時保持當時 live 版本不動；Windows 或 Worker 受控腳本在切換後失敗時，先閱讀其 deployment report，確認自動 rollback 的 `attempted`／`succeeded` 及精確 previous commit／version，不要盲目重跑或手動複製檔案。
9. 如 live rc20 發現 Assist 模式、可值班日、窄屏、鍵盤、焦點、主題或入口回歸，立即停止接受正式寫入並記錄 canonical URL、時間、裝置、route 及非敏感畫面。由受控腳本把 Windows origin 恢復至第一級回退 rc18／`fd504a8`；Worker 本次未改，應繼續保持 `f780feb2-671a-4feb-b6f6-b7f9d5b31e89` 的 100% traffic。不可 `git reset --hard`、直接覆寫 C-host 或留下未經證明的混合版本。
10. 回退後重新核對 host commit、工作排程 owner、受保護 loopback endpoint、`/healthz`、`/readyz`／`writeReady=true`、無 maintenance／recovery／pending backup obligation，以及 canonical Public／Guest／Admin／Viewer／WebSocket／登出。只有 rc18 使用者流程及資料狀態再次一致才恢復日常操作；若不能證明回退完成，保持 maintenance／唯讀並交由 IT 處理。

## 正式驗收清單

先閱讀[正式驗收證據矩陣](ACCEPTANCE_EVIDENCE.md)。它標示每一項已有甚麼直接自動化證據，以及哪些部分必須由首席導學風紀或教師顧問親自確認。`release-candidate-report.json` 的 `humanAcceptanceRequired` 必須保持為 `true`，直至下列真人項目逐項完成。

網站「交接指引」是這份矩陣的操作摘要：桌面以三欄顯示名單／週表／備份準備度，手機改為依次堆疊；下方分開顯示機器證據與真人驗收。顏色以外亦有圖示、標題及說明文字，按鈕維持至少 44px 高。網站摘要不能取代本文件的逐項簽核。

### 首席導學風紀

- [ ] 可用實際名單建立一個測試週，且所有中文姓名、職務與可值班日正確。
- [ ] 漏填中文姓名、班別或可值班日時，畫面會指向需要修正的欄位且不開始寫入；停用風紀前會顯示保留歷史及沒有即時復原的確認。
- [ ] 用只含虛構中文姓名的 CSV／XLSX 完成一次「工作表 → 欄位配對 → 預覽 → 明確匯入」；確認預覽前不會寫入，公式／不支援格式會被拒絕。
- [ ] 如啟用可選 DeepSeek 建議，以測試檔確認建議只填入欄位選單，仍須人工核對及預覽；未配置時，手動配對仍可完成同一流程。
- [ ] 週開始日期不是星期一或尚未載入替補時，畫面會在本頁提示修正，不會開始寫入；生成前請假、草稿修改、發布後請假調整及撤回原因留空均可安全完成，且仍留下版本、審計、公平及備份證據。
- [ ] 在兩個分頁開啟同一風紀或草稿，先在其中一頁儲存，再從舊頁嘗試儲存；舊頁必須要求重新載入及核對，而不是覆蓋新資料。
- [ ] 助理首席導學風紀只被安排為 Assist. in charge；導學風紀只出現在 302、303、202 室。
- [ ] 新週預設固定星期模式，既有週保留已保存模式；固定模式只為受請假影響的該次當值使用合資格替補，靈活模式按週次作可重現輪換並在可行時避開個人上週相同星期，兩者均不會安排未選的可值班日。
- [ ] 302 每日一人、303 每日兩人、202 只在星期一/三/四每次兩人；同日無重複、生成安排無連續日。
- [ ] 生成前請假會使草稿避開該人；新增請假後舊草稿被拒絕發布，重新生成後才可發布。
- [ ] 發布前確認視窗有被閱讀；發布後公平帳本只增加一次。
- [ ] 發布後請假調整只提供合資格替補，並在帳本和審計中保留理由；完成收據準確列出原值班者扣回、替補者等額加回或保留空缺、更新後版本及備份狀態，並提醒舊 PDF 不會自行更新。
- [ ] 草稿下載及發布後準備的中文／英文週表 PDF 均為清晰單頁，檔名帶有正確 `v版本`，顯示正確崗位、星期、草稿／發布狀態及中文姓名；202 室星期二、五清楚標記為不開放。請假調整後的修正版必須顯示新替補及新版本。
- [ ] 核對週表匯出視窗的校徽開關；乾淨發布版不含「僅供內部使用」、頁碼或經文提示，只有刻意開啟補充頁腳時才出現附註。
- [ ] 在實體手機準備已發布週表後，按「分享 PDF（可選 WhatsApp）」會開啟系統分享面板；人工選擇 WhatsApp／正確群組、取消一次分享，並測試不支援時的下載附件後備路徑。內部公平審計必須只可下載，不可出現群組分享入口。
- [ ] 未登入一般瀏覽器開啟 canonical 網站時顯示統一入口；只有按「訪客體驗」或「管理員登入」後才建立相應 session。
- [ ] Guest 使用與管理員相同的 Dashboard、值班表、風紀、公平、交接、平台、工程、架構、手冊及經文頁，只見固定虛構中文姓名及 `DEMO` 狀態。
- [ ] Guest 可完成示範請假、生成、手動修改、發布、雙語 PDF／JSON、發布後請假調整及公平說明；AI、上載、匯入、外部音樂、正式分享、備份／還原及永久設定在服務層被拒絕。
- [ ] 同一 Guest 的兩個分頁取得獨立 workspace；複製分頁、重新整理、登出、30 分鐘到期、撤權及 origin 重啟均依安全模型處理，不能重播舊 revision 或交叉取得下載。
- [ ] 主動登出、管理 session 上限或 Access 較早到期後回到 public；缺少、過期、錯誤 audience／issuer 或非管理員電郵的 JWT 被拒絕，缺少、過期、遭竄改、auth epoch／kid 不符的 session 或 principal 在任何工作台回調均被拒絕。
- [ ] `/healthz` 及 `/readyz` 同時通過；以崩潰注入留下 backup obligation 後，重啟必須先修復，否則保持 degraded／唯讀而不可接受新寫入。
- [ ] 以虛構已發布週表建立同 host `/view#…` 連結；一般瀏覽器可查看中文姓名週表但不能修改。撤銷後約一分鐘確認舊完整連結不能再載入。
- [ ] 完成正式瀏覽器的 WebSocket 長連線／重新連線、檔案上載及 PDF 下載驗收；已記錄的 VPC probe 只作傳輸證據。
- [x] **歷史 rc18 基線（由 rc20 承接）：**隔離 Chromium 真觸控模擬已覆蓋 390×844 繁中淺色、320×760 英文深色／reduced motion 及 844×390 橫向：單行頁首、`Dashboard／Rosters／Prefects／More`、可捲動 More 抽屜、`aria-expanded`、開啟後焦點、Tab／Shift+Tab 循環、Escape／背景關閉及焦點恢復、手機資料卡、44px 操作、安全區、零橫向溢出及零 console/page error 均通過；live rc20 的擴展裝置矩陣另見 `ACCEPTANCE_EVIDENCE.md`。
- [x] **rc20 自動化與線上證據：**fingerprint-matched 14／14 report 已覆蓋裝置矩陣、reflow、reduced motion、navigation／focus、觸控目標、淺／深模式、Guest／Admin 流程及零 console／page error；來源固定為 `v1.2.0-rc.20`／`e3d84858`／`93c6c938…`，受控 Windows 切換及 canonical smoke 亦已完成。這些證據不能代替下列真人手機／平板驗收。
- [ ] 在同一 canonical 網址以實體 iPhone Safari 及 Android Chrome 重複手機驗收，集中檢查 200% zoom、鍵盤彈出及焦點欄位、跨頁 focus、More 語意、觸控 icon story、兩個 themes、reduced motion、forced colours、旋轉、瀏海與 home indicator 安全區；不用另建或測試 `/mobile` 網站。
- [ ] 在一個未儲存表單中測試外觀、聲音及語言：外觀／聲音即時切換而不清空輸入，啟用聲音有一次短確認；切換語言前必須先出現離開提示。再以鍵盤確認頁面內容先於底部重複導航。
- [ ] 內部公平審計 PDF 與群組週表分開；審計檔清楚標示為內部資料，且具名資料沒有被預設發群組。
- [ ] 以兩個已發布測試週產生一次期間報告，確認草稿被排除、最終請假調整被反映、繁中／英文 PDF 姓名保持中文，而且重複產生報告不改動公平點數。
- [ ] 核對報告把時數清楚稱為「已編排」而不是出席／證書；下載 JSON 後確認畫面說明它不是還原備份，亦沒有自動上載 GitHub。
- [ ] 「交接指引」三項狀態合理，並能由下一任按步驟獨立完成演練。
- [ ] 在測試資料上建立一次「交接備份包」，確認 ZIP 同時含 SQLite 快照、manifest 和還原說明，並把它移至受控加密位置。
- [ ] 在沒有任何快照的隔離測試資料上，確認交接包與還原入口停用，且「立即建立已驗證快照」是清楚的唯一下一步；建立後兩個入口才啟用。
- [ ] 在隔離備份目錄放置一個缺 manifest 的虛構快照，確認頁面只顯示安全分類與數量、不顯示原始錯誤；有效快照仍可建立交接包及受控還原。
- [ ] 正式名單在首次真實匯入前為零；重啟正式服務不會自動載入示範 seed。Practice Mode 重啟則仍能載入隔離虛構名單。
- [x] 機器隔離演練已完成「準備新學年名單」：真實瀏覽器確認指定語句、操作前後已驗證備份、啟用名單歸零、舊週表分配／公平帳本總數不變、單一封存審計，以及由空白頁匯入新學年虛構名單；聚焦工作流測試另證明相同中文姓名可建立新學年獨立記錄。正式交接時仍須由首席導學風紀按本節步驟真人核對一次。

### 教師顧問

- [ ] 審閱一次已發布表和一次請假調整的公平帳本，確認 `history_weight` 的解釋與學校做法一致。
- [ ] 驗證最近備份；在非正式資料副本完成一次受監督還原演練。
- [ ] 確認專用電腦、`.env` 秘密、加密離機備份位置及交接責任人。
- [ ] 遠端使用前完成上述單一網站 Access 登入／登出、JWT、VPC、WebSocket、上載及 PDF 驗收；未完成時只使用本機／WARP 維護後備。
- [ ] 核對 Worker／KV、Access exact-email policy、Tunnel／VPC、主機 `.env` 及 secret 輪換責任；確認任何文件、Git、截圖及支援紀錄均沒有 audience、JWT、cookie 或管理 token。
