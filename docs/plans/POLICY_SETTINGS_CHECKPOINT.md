# 學年設定資料層 checkpoint

狀態：未接現行 runtime 的內部準備，不是正式空庫初始化、完整 C 階段或部署證明。
依 [整體計劃](20260905-system-integration.md) 與
[ADR-0002](../adr/0002-dated-roster-core-and-publication-snapshots.md)，先驗證設定閉環，
再與排班、發布、輸出及操作頁面共同接線。原始工作區和資料庫未改動。

## 可依賴的內部行為

- `roster_policy.policy_codec` 保存嚴格 version-1 weekly policy 文件。
  房間、人數、啟用、星期、開放／服務時段及連動狀態使用既有純規則驗證；
  未知欄位、重複 JSON key、無效 Unicode 或無效設定明確失敗，不回退為預設。
- `roster_core.policy_settings.PolicySettings` 提供 `initialize`、`current`、
  `revision`、`save`、`preview_reset` 與 `reset`。
  `PolicyRevision` 只包含學年起始年份、修訂號及不可變 `WeeklyPolicy`。
  學年 key 不隱含 CP 活動日期或報告起止日的自動篩選。
- 新學年初始化只建立 revision 1；已存在學年不能用另一個初始化命令偷偷重設。
  每個有效新保存／還原命令建立新修訂，即使值相同；相同命令重送不再增加。
- `save` 必須提供 `expected_revision` 與 `command_id`。同 id／同 canonical
  請求重送取得原已提交修訂，即使後來已有其他修訂；改用同 id 做不同工作則衝突。
  新命令使用舊修訂時拒絕，不能覆蓋另一分頁已保存的設定。
- `preview_reset` 不寫入，列出房間、人數、啟用、星期、兩段時段及連動的差異。
  `reset` 驗證不可變歷史來源和預設目標；篡改預覽、過期新命令均拒絕。
  仍保留所有舊設定修訂，不讀寫名冊或任何發布版本。
- 修訂號採共同 signed-64-bit 正整數範圍，禁止 bool／超大整數及再增值溢位。
  服務分鐘仍由時段精確計算；此層不產生已編排服務總數。

## 儲存 Seam 與限制

`MemoryPolicyRepository` 是每實例隔離的暫存 Adapter；不是瀏覽器持久快取，
也尚未與現有 Guest workspace registry 接線。正式候選 Adapter
`SQLitePolicyRepository` 只使用明確傳入的 SQLAlchemy SQLite Engine。
建構無 I/O；`create_schema()` 才會建立三張 `prelaunch_policy_*` 準備表。
所有自動化都使用臨時測試庫，不會尋找或連接應用的既有資料庫路徑。

兩個 Adapter 共用規則、差異及命令指紋，只分開處理原子持久化。
SQLite 在新連線啟用外鍵，以 `BEGIN IMMEDIATE` 同時保存修訂、目前指標及命令收據；
先查重送收據，再核对版本。讀取以單一查詢取得設定，解碼前釋放連線。
失敗明確返回，三項寫入一起回滾；沒有背景輪詢、timer 或自動預設重設。

這個準備實作以嚴格版本化設定文件保存政策內容，沒有另一份可修改的逐欄位設定表。
現階段只按學年及修訂取整份政策，JSON 不承擔搜尋或可執行規則。
此接口尚未供 frontend 使用；正式 schema／Alembic 和共同交易 Adapter 的接線仍待完成，
不將 preparatory `create_schema()` 宣稱為正式啟用的初始化程序。

後續共同交易準備見 [操作 checkpoint](POLICY_OPERATION_CHECKPOINT.md)：
在 caller 提供的交易內沿用既有審計、命令收據及備份義務，不把本頁的 standalone
Adapter 直接嵌入正式寫入交易；命令身份亦已收斂至正式操作的 trim／64 字契約。

## 驗證與仍未交付

本次定向檢查：95 個設定儲存案例、47 個 codec 案例、74 個 compiler 案例通過。
包含重開 SQLite、兩個獨立 Engine 同時保存、失敗注入後三表回滾、重送、
壞文件、篡改預覽、Unicode、版本上限及解碼前連線歸還。
完整驗證／CI須以各次乾淨精確提交的證據判定，不由上述定向數字推論。

尚未提供正式／Guest workflow 的權限與 actor、備份義務或原有命令協調器接線；
這些必須納入共同交易设计後才開放設定頁，不能在正式保存後另以獨立寫入假裝原子。
亦未提供學年交接複製、已發布快照、人物資格、排班、CP 日期不可值班、
跨模式防重複、分鐘年報或動態20行輸出。`PolicyRevision` 不是 `PublicationSnapshot`，
設定保存成功也不表示既有草稿已採用或已發布排班被更正。
