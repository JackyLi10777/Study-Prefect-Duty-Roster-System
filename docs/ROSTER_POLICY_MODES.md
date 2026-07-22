# Assist. in charge 編排模式

本文件說明「值班表」生成頁的兩個 **Assist. in charge** 編排模式。模式只改變助理首席導學風紀（Assistant Head Study Prefect）的 Assist. in charge 分配方式；302、303、202 室的職務資格、房間開放日、公平帳本、`history_weight`、同日不重複及其他排班規則全部維持不變。

## 首席導學風紀怎樣選擇

| 畫面名稱 | 穩定模式碼 | 適合情況 | 實際行為 |
|---|---|---|---|
| 固定星期模式 | `legacy_fixed_weekday` | 希望 AHP 長期在固定星期服務，方便建立穩定責任 | 在啟用 AHP 名單及可值班日不變時，同一人會在其固定星期重複當值。若本週已登記請假，系統會為該次當值尋找合資格替補；若沒有替補，生成會停止並清楚說明空缺。 |
| 每週靈活模式 | `flexible_weekly` | 希望合資格 AHP 的星期安排按週作可重現輪換 | 系統以週次作穩定輪換鍵，並在公平與可值班條件容許時優先避開個人上週相同星期；同一名單、可值班日、請假、上週安排及週次會重現同一結果，不會因重新整理頁面而隨機改變。 |

- 新週次在介面預設選擇「固定星期模式」，操作員可在生成前改為「每週靈活模式」。
- 重開或重新生成既有草稿時，介面讀取該週已保存的模式，不會靜默改回新週預設。
- 兩種模式都只會安排合資格、該日可值班且沒有請假的助理首席導學風紀。其他角色不可擔任 Assist. in charge。
- 在「導學風紀名單」編輯助理首席導學風紀時，可將「固定 Assist. 星期（舊制）」保留為自動穩定分配，或指定一個已選為可值班的星期。固定模式優先沿用指定星期；第一次以自動方式生成固定模式後，系統會保存可表達的一人一日對應，避免日後新增 AHP 時令原有人員整批換日。靈活模式忽略此欄。
- 模式碼是規則與資料庫的唯一輸入；繁中／英文名稱只供畫面顯示，不可作政策鍵值。
- 已保存的固定星期不會在背景自動移動。需要改日時，先在「導學風紀名單」為該 AHP 明確選擇另一個可值班日，或改回「自動穩定分配」後再生成；系統仍會阻止任何固定日與可值班日互相矛盾的設定。

## 相容資料

舊資料可能保留 `fixed_general_duty`／`fixedGeneralDuty`。它是固定星期模式的相容元資料，也是名單中「固定 Assist. 星期（舊制）」的穩定值；它永遠不能繞過職務或可值班日。一般導學風紀的舊值會原樣保留，但不會影響 Assist. in charge。

## English operator summary

New weeks default to **Fixed-weekday mode** (`legacy_fixed_weekday`) in the UI. The same AHP repeats on a canonical weekday while the active AHP directory and availability remain unchanged. Recorded leave uses a qualified substitute for that duty this week; if none is available, generation stops with a clear vacancy explanation. **Flexible weekly mode** (`flexible_weekly`) uses a deterministic week key and, when fairness and availability permit, prefers to avoid each AHP's previous-week weekday. The same directory, availability, leave, previous-week assignments and week reproduce the same rotation. Existing weeks reopen with their persisted mode. Both modes enforce role, availability and leave policy; translated labels are never used as rule values.
