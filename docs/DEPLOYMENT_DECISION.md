# 部署與遠端存取決策指南 / Deployment and remote-access decision guide

## 結論 / Recommendation

**現時不要把系統直接「上傳到雲端」。**

第一個受控遠端版本應採用：**專用學校主機 + Cloudflare Tunnel + Cloudflare Access**。NiceGUI 程序、SQLite 資料庫、PDF、備份及本機日誌仍留在受控主機；Cloudflare 提供身份驗證、TLS 和到該主機的受控通道，但不會成為此系統的應用資料庫。這是由本機走向遠端存取，而不是將學生資料搬到公開雲端。

真正雲端部署只在學校確認有跨校區、長期高可用或集中 IT 維護需要後才考慮。它需要獨立架構項目，不可視為 Tunnel 的下一個按鈕。

## 三種模式 / Three operating models

| 模式 | 資料位置 | 誰可進入 | 適合情況 | 目前狀態 |
|---|---|---|---|---|
| A. 本機正式使用 / Local-only | 專用校內電腦 | 在該電腦操作的人 | 首次發布、最小風險、單一負責人 | **現時批准** |
| B. 受控遠端存取 / Controlled remote access | 專用校內主機為系統資料來源；Cloudflare 處理受保護流量與身份驗證 | 當任首席導學風紀；顧問老師只在需要核對時進入 | 首席導學風紀需在校外受控操作，顧問老師完成後檢視 | **可行，但未批准** |
| C. 真正雲端部署 / Cloud-hosted application | 學校批准的雲端主機及受控持久化儲存 | 應用程式身份權限 + 網絡存取規則 | 多校區、高可用、IT 集中維護 | **未設計，不可直接遷移** |

## 為甚麼不直接用 Cloudflare Pages 或 Quick Tunnel？

目前系統需要長時間運行的 Python NiceGUI 程序、即時瀏覽器連線及可寫入的 SQLite、備份和日誌目錄。靜態網站平台不提供這些持久狀態；把現有資料夾同步到公開平台也不符合私隱要求。

Cloudflare 的 Quick Tunnel 只適合短暫開發展示，不適合正式使用，且官方文件指出它不支援 Server-Sent Events。任何含真實學生資料的公開或隨機網址都是禁止的。

## B 模式：Cloudflare Tunnel + Access 的批准閘門

在任何人安裝 `cloudflared`、建立 Tunnel 或增加 DNS 記錄前，教師顧問必須以書面完成以下決定：

1. **資料責任人：** 指定教師顧問、首席導學風紀、IT 支援及緊急聯絡人。
2. **身份來源：** 只使用獲學校批准的身份提供者及帳戶；不可用公開「任何有電郵即可登入」規則。
3. **名單與權限：** 列明可進入的群組、撤銷離任幹事的程序，以及最短合理 session duration。
4. **應用內權限：** 現時程式尚未把 Cloudflare 身份轉換為應用內角色。因此第一個遠端版本只可 allow 當任首席導學風紀及顧問老師；首席是唯一日常寫入者，顧問只作完成後核對。若要讓一般導學風紀登入，必須先實作及測試應用內讀寫權限。
5. **主機與資料：** 使用專用、受密碼保護、全磁碟加密及自動更新的學校主機；資料庫、備份、`.env`、PDF 和日誌不可放入個人雲端同步位置。
6. **復原：** 定義加密離機備份位置、保留期、還原演練頻率及遺失裝置處理程序。
7. **監察與事故：** 設定 Tunnel 健康通知、保留適量 Access 稽核紀錄，並定義帳戶停用、誤發表及遺失資料的處理人。
8. **驗收：** 只以虛構資料完成完整遠端流程，確認 Access 拒絕未授權帳戶、系統可以登出／撤銷、PDF 不會公開，才可考慮真實資料。

Cloudflare Access 的 self-hosted application 預設拒絕存取，使用者必須符合 Allow policy 才可進入；不要使用 Bypass 作為長期登入方法。Cloudflare Tunnel 以由內向外的連線將公開 hostname 映射到主機上的 `http://127.0.0.1:8080`，不需要開啟入站防火牆連接埠。Tunnel route 必須啟用 **Protect with Access**，讓 `cloudflared` 驗證 Access token；NiceGUI 仍只綁定 loopback，並以 Host allow-list 只接受 localhost 與已批准的公開 hostname。[Cloudflare Tunnel setup](https://developers.cloudflare.com/tunnel/setup/) [Cloudflare self-hosted application protection](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/) [Access policies](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/)

## B 模式：受控實作順序（批准後才可執行）

1. 將系統移至專用學校主機，先完成本機正式驗收、`SING_YIN_STORAGE_SECRET` 更換、中文字型確認及還原演練。
2. 在 Cloudflare 建立受管 Tunnel；主機只需對外建立連線，NiceGUI 仍只聆聽 `127.0.0.1:8080`。
3. 建立單一專用 hostname，例如 `roster.school.example`，映射到 `http://127.0.0.1:8080`；不公開資料庫、備份、日誌或資料夾路徑。
4. 先建立 Cloudflare Access self-hosted application，設定學校 IdP、Allow policy、MFA／device posture（如學校具備）及適當 session duration；確認不存在 Bypass 規則。
5. 僅以虛構資料，用「允許帳戶、拒絕帳戶、已撤銷帳戶」各測一次登入；並測試 NiceGUI 長時間頁面、PDF 下載、登出與 session 到期行為。
6. 以隔離資料庫做兩個瀏覽器的發布競爭與請假調整測試；確認 SQLite 交易仍是最終的公平帳本保護。
7. 由教師顧問簽署驗收後，才轉用真實資料。每學期重審 allow-list、離任帳戶、備份還原及 Tunnel 健康。

Tunnel 狀態只說明 `cloudflared` 可連到 Cloudflare，不代表應用程式本身健康；要同時監察主機、SQLite 備份及實際登入流程。Tunnel 副本可提高連線可用性，但不會替 SQLite 或應用程式提供跨主機資料庫容錯；不要把同一 SQLite 檔案放到多台主機上同時寫入。[Cloudflare Tunnel monitoring](https://developers.cloudflare.com/tunnel/monitoring/) [Tunnel configuration](https://developers.cloudflare.com/tunnel/configuration/)

## C 模式：真正雲端部署需要甚麼？

這是 L3 架構改動，最低限度需要：

- 一部長時間運行、受更新管理的雲端 VM 或容器主機，而不是靜態網站主機。
- 加密的持久化磁碟與受控備份；或在完成遷移、測試及還原演練後，改用受管理的 PostgreSQL。
- 不再依賴單一 SQLite 檔案作多主機寫入；任何資料庫遷移都必須保留 `history_weight`、審計、備份及還原語義。
- 應用內使用者與角色模型、Access 身份整合、session／登出策略，以及教師顧問可撤銷的權限管理。
- 私隱影響評估、資料所在區域、保留期、事故處理、成本上限及校方 IT 維護責任。
- 完整災難復原演練：主機遺失、資料庫還原、Access／IdP 故障、帳戶撤銷及 PDF 外發錯誤。

在上述條件未完成前，C 模式不是較「高級」的版本；對目前值班工作來說，它反而會增加資料風險及交接成本。

## English summary

The current approved deployment is localhost-only. The recommended future remote-access model is a dedicated school host running the existing NiceGUI and SQLite system, connected through Cloudflare Tunnel and protected by Cloudflare Access. The school host remains the system of record; Cloudflare provides the authenticated route rather than the application's database.

Do not use Quick Tunnels, a public URL, or a static hosting platform for real student data. Cloudflare Access is only the front door: the current application does not yet translate Access identity into in-app roles. Until that capability exists, remote access must be limited to the teacher advisor and current Head Study Prefect.

True cloud hosting is a separate L3 project requiring a long-running Python host, durable encrypted storage or a tested database migration, application-level roles, backup and restore exercises, retention decisions, and formal school approval.
