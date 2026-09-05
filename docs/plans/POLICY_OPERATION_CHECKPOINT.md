# 學年設定共同交易準備

本批接續 [設定資料層 checkpoint](POLICY_SETTINGS_CHECKPOINT.md)，深化現有操作 Module，
不另建政策審計或正式命令收據系統。這不是設定頁、正式 schema 初始化、完整
Official／Guest workflow、備份恢復演練或部署證明。

## 共用命令身份

`roster_core.command_identity.normalize_command_id` 採既有正式操作的 trim／64 字契約，
保留合法 Unicode；空白、錯誤型別、過長及孤立 surrogate 明確拒絕。
設定準備層原先的 128 字內部契約收斂至此；未曾接入正式設定資料。

現有 `PageContextWorkflowAdapter` 在重新驗證 principal 後，把相同的正規化編號交給
target 與 ContextVar actor，避免操作收據和審計採用不同字串。
需要 command_id 的操作不能以無效值觸發自動生成；legacy workflow 仍只在省略
（None）時保留原本的 actor／生成編號路徑。不重寫既有 Guest registry 的收據格式。

## 一個由 caller 擁有的交易

`TransactionPolicyRepository` 是內部、單次交易生命週期的 Adapter。它使用明確提供的
Session 及現有 `PersistenceWorkflowMixin` helpers，不發現資料庫路徑，不開新 Session，
不自行 BEGIN、commit、rollback 或執行備份。

caller 必須先驗證有效 principal、取得維護／寫入 fence、啟用 SQLite 外鍵，並以
`BEGIN IMMEDIATE` 開始實際交易。Adapter 的檢查不代替 principal 的即時認證。
交易中依序處理：

1. 核對明確操作種類、已正規化 command 及綁定的管理員 actor。
2. 由現有 operation_commands 判斷精確重送；重送讀取收據指定的不可變修訂。
3. 新命令執行政策版本 CAS，新增 revision 並更新 current 指標。
4. 在同一 Session 保存既有 audit、operation receipt 及 pending backup obligation。

政策請求先經共用的嚴格序列化與指紋計算，交予既有 claim 的 payload 僅為明確字串
digest，不讓 legacy `default=str` 重新解釋政策欄位。收據只指向學年及修訂，
不是第二份可修改的政策文件。這條路徑不使用 prelaunch_policy_commands。

回傳的修訂在 caller commit 前仍是暫定結果；任何錯誤都要求 caller 回滾整筆交易。
Adapter 不得跨錯誤、commit、rollback 或 Session 關閉重用。
caller commit 並釋放連線後，仍須使用既有備份義務履行及修復流程；pending obligation
不等於備份完成。界面應保留「已保存、備份待修復」的區別，不提示重新建立同一業務，
也不能宣稱已完成可恢復性驗證。

## 尚未接線

- 本批不將 Adapter 加入應用 bootstrap 或設定頁，也不自動初始化演練／正式庫。
- 新正式 schema／readiness／restore 的共同表契約仍待完成；測試建表不是正式啟用。
- 外層權限、維護 fence、命令重送與備份待修復收據仍須形成完整操作 Interface。
- Guest 設定須納入既有 replace_state 的隔離、版本、收據與到期生命週期。
- 待確認年度複製、政策採用、日期席位發布、動態輸出及分鐘年報仍未完成。

本批定向驗證：共同交易 36 項、政策設定 97 項，連同 command identity、operation
context、codec 及 compiler 共 291 項通過；原有備份義務另 4 項回歸通過。
獨立 review 核對交易、重送、actor、外鍵及生命週期，未見剩餘阻塞問題。
其中 actor 原字串、關閉外鍵及失敗 read 後重用均先以失敗案例確認再修正。

完整驗證／CI 結果仍以本批最終乾淨提交及 PR 證據為準；上述定向結果不代表
正式工作流、備份恢復或端到端啟用已通過。
