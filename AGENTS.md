# AGENTS.md — Sing Yin Study Prefect Duty Roster System

**聖言中學導學風紀當值排班平台**  
Sing Yin Secondary School Study Prefect Duty Roster Platform

**Purpose for AI Agents & Developers**  
This file defines the **authoritative project rules**, business constraints, coding standards, and architectural invariants. All changes to duty assignment logic, student data handling, or roster generation **MUST** respect these rules.

Current working branch: `ai`

---

## 1. Core Project Rules (MUST BE ENFORCED)

These rules come directly from school policy and are hardcoded in the system (primarily `config.py` and `core.py`).

### 1.1 Student / Prefect Rules (Eligibility & Data)

- **Forms**: Only F.3, F.4, F.5, F.6 are valid prefects.
- **Roles** (strictly two values):
  - `"Study Prefect"` — regular prefect. Can only be assigned to room duties (302, 303, 202).
  - `"Assistant Head Study Prefect"` (AHP) — leadership role. Has **exclusive** access to the "Assist. in charge" position.
- **Required data fields per student** (in `students_df`):
  - `name` (string, non-empty, unique for practical purposes)
  - `form` (F.3–F.6)
  - `class`
  - `role` (exactly one of the two values above)
  - `fixed_general_duty` ("NONE" or one of MONDAY–FRIDAY)
  - `available` (comma-separated uppercase day list, e.g. "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY")
  - `history_weight` (float — cumulative prior workload; **lower value = higher priority** for new assignments)
  - `history_duties` (int, informational)
  - `remarks` (free text; can be AI-parsed for fixed/available/role updates)
- **F.3 Junior Preference ("老帶新")**: In fair selection, when scores tie, F.3 students are preferred (sort key uses `-is_junior`).
- **Leave handling**: Students in the current leave list are completely excluded from `student_info` and all candidate pools for the week.
- **One duty per day rule**: No prefect may be assigned more than one slot on the same day (enforced via `assigned_today` set across all roles).
- **History & Fairness**: `history_weight` is the persistent fairness anchor. New assignments add their weight (or manual override) on top. The audit table and bar chart are **always sorted ascending** by final total load ("點數低者將優先派班").

**Validation rules** (enforced in `validate_students_dataframe` and `validate_and_compute`):
- No blank names.
- Required columns present.
- Names in roster must exist in the current student list (except special markers "X", "⬜", "請假撤銷").

### 1.2 Room 302 / 303 Restrictions & Assignment Rules

**Room 302 (Study Room)**:
- 1 slot per day.
- Weight: **1.0**
- Open: **All weekdays** (Monday–Friday). No calendar restrictions.
- AHP allowed: **No** (`allow_assistant_head_only: False`).
- No additional restrictions (no experience gate, no special pairing with other rooms).

**Room 303 (HW Completion)**:
- **2 slots per day** (represented as two rows: "Room 303 (HW Completion) - 1" and "- 2").
- Weight: **1.5 per slot**.
- Open: **All weekdays** (Monday–Friday). No calendar restrictions.
- AHP allowed: **No**.
- The two slots on the same day must go to **different** prefects (enforced by `assigned_today`).
- No special "restrictions" or priority rules beyond the above. "Room302 經驗豐富" in remarks is only for optional AI parsing — it does **not** affect the scheduler.

**General Room Rules (all rooms)**:
- Roster rows are defined in `ROWS_ROSTER` (config.py). 302 and 303 use the slot-count pattern in `ROOMS_CONFIG`, but actual multiplicity is currently achieved via duplicated rows in `ROWS_ROSTER` + " - 1/- 2" suffixes.
- `base_role = role.split(" - ")[0].strip()` is used to match against `ROOMS_CONFIG` keys.
- `get_weight(role)` and `is_assistant_head_only_role(base_role)` are the canonical lookup functions.
- Special user closures (from the multiselect) are intended to block specific (day, room) combinations, but the current string-matching implementation is fragile (see Known Issues).
- Room 202 is the **only** room with hard calendar restrictions (closed Tuesday & Friday → marked "⬜").

**Weights impact**:
- Used in audit calculations, manual weight overrides, PDF, and (most importantly) `apply_post_publication_leave_adjustment` (which always uses the base `get_weight`, not the manual value).

### 1.3 AHP (Assistant Head Study Prefect) Privileges & Restrictions

This is the **strictest and most important policy** in the entire system.

**Privileges**:
- AHPs are the **only** prefects eligible for the "Assist. in charge" leadership slot (1 per day, 5 per week).
- When competing for an "Assist. in charge" slot, AHPs receive a large score bonus: `score -= 8.0`.
- Fixed duties declared by an AHP can only claim the Assist slot on that day.

**Hard Restrictions**:
- AHPs are **completely barred** from all room duties (Room 302, 303-1/2, 202-1/2).
- Regular "Study Prefect" students are **completely barred** from the "Assist. in charge" slot.
- The role-type gate is enforced in **three independent places** for safety:
  1. Fixed-duty priority phase in `generate_roster`.
  2. Fair candidate collection phase in `generate_roster`.
  3. `recommend_substitutes()` (smart replacement finder).
- In `student_info` and filtering code the exact strings `"Assistant Head Study Prefect"` and `"Study Prefect"` are used for comparison.

**Implications**:
- The number of AHPs in the roster should roughly match the number of Assist slots (demo data is balanced with 5 AHPs).
- Changing AHP eligibility is a **policy decision**, not a coding convenience. Any relaxation requires new UI controls or config flags.
- AHPs still participate in the global fairness system via `history_weight`.

### 1.4 Scheduling Constraints & Algorithm Rules (generate_roster)

The generator (`core.py`) **must** follow this order and logic on every run:

1. **Setup**: Build `student_info` (exclude leaves), initialize `last_duty_day` and `assigned_today`.
2. **Per-day, per-role loop** (order matters: Assist → 302 → 303-1 → 303-2 → 202-1 → 202-2):
   - Apply closure gate (special + calendar via `is_room_open_on_weekday`).
   - Determine `is_assist_role`.
   - **Fixed-duty priority** (highest precedence): First matching student in DataFrame order that has `fixed_general_duty == day` **and** passes the role gate **and** is free today wins.
   - **Fair selection** (if no fixed match):
     - Strict filters: not on leave, not assigned today, day in `available`, not consecutive previous day (`last_duty_day != day_idx-1`), role gate.
     - Score = `(history_weight * global_load_multiplier) + random.uniform(0, 0.3)`
     - AHP Assist bonus: `-8.0`
     - Junior flag for tie-break.
     - Sort: `(score, -is_junior)` — lowest load wins; F.3 wins exact-score ties.
3. **Invariants the code must maintain**:
   - Never assign the same person to two slots on the same day.
   - Never assign on the immediately previous day.
   - Role separation between AHP and regular prefects is absolute.
   - Return a fresh `roster_df` (never mutate the input students_df during generation).
   - `global_load_multiplier` only affects scoring for this run (slider 0.8–2.0).

**Post-generation rules**:
- `validate_and_compute` must add this week's weights (respecting manual overrides or falling back to `get_weight`) on top of existing `history_weight`.
- "請假撤銷" cells are **always skipped** in weight calculations, duplicate checks, and vacancy warnings.

**Leave Adjustment Rules** (`apply_post_publication_leave_adjustment`):
- Directly mutates the original person's `history_weight` by subtracting the slot weight.
- Optionally gives the weight to a replacement and updates the roster cell.
- Or marks the cell "請假撤銷" if no replacement.
- This is the primary mechanism for maintaining fairness after the roster is published.

---

## 2. Coding Standards & Development Rules

- **Bilingual + Emoji style**: User-facing text (UI strings, PDF, help, warnings) uses Traditional Chinese + English + emojis. Keep the warm, professional, school-spirited tone. Code comments and docstrings may be bilingual.
- **Module docstrings**: Every `.py` file starts with a detailed header including version notes (e.g. "v2.3 Final"). Update them when making user-visible or logic changes.
- **Data handling**: Almost everything is pandas DataFrames. Roster is always indexed by `ROWS_ROSTER` and columns `DAYS`. When restoring from backup or reindexing, always do `.reindex(index=ROWS_ROSTER, columns=DAYS).fillna(...)`.
- **Session state**: `initialize_session_state()` (data.py) is the single place that guards against Cloud hibernation loss. New persistent state must be added there + to the backup/restore functions in utils.py.
- **Generation is pure**: `generate_roster` must not mutate student history. Only leave-adjustment and manual history edits are allowed to change `history_weight`.
- **Error / validation messages**: Keep the existing danger-alert / warning-alert patterns in app.py.
- **Randomness**: Always reseed with a fresh `random.randint` on each user-initiated generate (current practice). The small `+ random.uniform(0, 0.3)` is intentional for light non-determinism.
- **Dead code**: Do not leave unused parameters (e.g. the former `current_roster_df`) or unused imports/functions (e.g. `get_daily_slots` was dead until recently). Clean them.
- **String matching for rooms**: Centralized through `base_role` + `ROOMS_CONFIG` lookup helpers. Avoid ad-hoc string checks outside `config.py` and `core.py`.
- **Testing discipline** (until real tests exist): After any change to `core.py`/`config.py`, manually run the verification checklist in section 5 using the official demo data.

---

## 3. Important Files & Where Rules Live (Post-Refactor, v2.4)

專案已重構為 `roster/` 套件（見先前 migration plan）。根目錄的 *.py 現在是薄的**相容性 shim**，會轉發到 `roster.*` 以維持向後相容。所有規則與行為完全保留。

| File / Package Path                  | Role & Key Rules It Enforces / Contains |
|--------------------------------------|-----------------------------------------|
| `roster/config/` (root 有 shim `config.py`) | **SSOT for all rules** (AGENTS §1 & §3)。`DAYS`, `ROWS_ROSTER`, `ROOMS_CONFIG`（含 Room 302/303 權重 1.0/1.5、全天開放、allow_assistant_head_only、AHP 旗標）、`get_weight`、`is_assistant_head_only_role`、`is_room_open_on_weekday` 等 helper。**絕不可 bypass**。 |
| `roster/core/engine.py` (root 有 shim `core.py`) | **The scheduler and fairness engine**。`generate_roster`（完整實作 §1.1~1.4 學生規則、Room 302/303 限制、AHP 硬門禁、fixed 優先、history 公平、1-per-day + no-consecutive 等）、`validate_and_compute`、`recommend_substitutes`、`apply_post_publication_leave_adjustment`。 |
| `app.py` (根目錄，不動)               | 主 UI  orchestration、全域負荷滑桿、排班表顯示與編輯、手動權重、請假調整表單、驗證警告、匯出。所有對核心規則的呼叫都透過 shim/package。 |
| `roster/data/` (root 有 shim `data.py`) | 官方 demo 資料、`initialize_session_state`（Cloud 休眠守護者）、學生 DF 驗證、reindex 工具。 |
| `roster/ui/` (root 有 shim `ui_components.py`) | 側邊欄（名冊編輯、請假、AI 按鈕、備份）、控制按鈕（呼叫 generate）、每日金句、特殊不開放多選。 |
| `roster/utils/` (root 有 shim `utils.py`) | PDF 產生（必須與 config 樣式同步）、完整 JSON 備份/還原（Cloud 關鍵，含 reindex）、導入處理器。 |
| `roster/ai/` (root 有 shim `ai_parser.py`) | Gemini prompt 與 Remarks/欄位映射解析。必須嚴格遵守 config 中的 role 字串與日子格式。 |
| `roster/__init__.py`                 | 套件公開 API + 包級文件。 |
| `requirements.txt` / `packages.txt` | 依賴。 |
| `.streamlit/config.toml`             | 主題、上傳大小等。 |
| `AGENTS.md` / `README.md`            | 完整規則、結構說明、驗證 checklist、使用方式。 |

**重要**：新程式碼請優先使用 `from roster.core.engine import generate_roster` 等。根 shim 僅供過渡與相容。結構變更後仍需遵守 AGENTS.md §2 Coding Standards 與 §5 Verification Checklist。

最近更新：已依據本次文件完善任務同步更新本節。

**Never bypass** the helpers in `config.py` when dealing with rooms, weights, or AHP status.

---

## 4. Known Critical Issues (Do Not Ignore)

1. **Duplicate validation bug** (`validate_and_compute`): Week-global "duplicate" check falsely flags normal multi-day fair assignments. Must treat as "same-day only".
2. **Special closures broken for 302/303**: The `f"{day} - {role}" in sc` test + short labels in the UI mean many user-specified closures are ignored.
3. **Non-declarative slot config**: `ROWS_ROSTER` duplication + string hacks + dead `daily_slots`. Risky to change 302/303 behavior.
4. Fixed-duty winner depends on DataFrame row order.
5. No automated tests.

---

## 5. Verification Checklist (Run After Any Rule-Affecting Change)

- Load the official demo data.
- Generate with multiplier 1.0 and 1.5, with/without leaves, with/without special closures (especially on 303).
- Verify:
  - Correct X / ⬜ for closed days and closures.
  - AHPs only appear in "Assist. in charge".
  - No regular prefect in Assist slot.
  - No person has >1 duty on any single day.
  - No consecutive-day assignments.
  - F.3 students win ties when appropriate.
  - Audit table sorted by final load ascending; "請假撤銷" cells contribute 0.
- Exercise the leave-adjust form (with and without replacement) and confirm history_weight changes correctly.
- Test substitute recommender — role gates respected.
- Export PDF and JSON backup; restore and confirm state is perfect.
- Manually force a same-day conflict and confirm it is flagged.

---

## 6. Non-Goals & Out-of-Scope

- General-purpose rostering tool for other organizations.
- Automatic resolution of insufficient availability (just report vacancies).
- Dark theme or mobile-first layout (wide desktop table + chart is intentional).
- Real-time multi-user editing.

---

**Last updated**: June 2026 (ai branch) — after deep analysis of duty logic, AHP gates, room handling, and the removal of the unused `current_roster_df` parameter.

**For AI agents**: Read this entire file + the docstrings at the top of `core.py` and `config.py` **before** suggesting or implementing any change to student filtering, room assignment, AHP logic, or the fairness model. The rules above are not suggestions — they reflect real school policy and the fairness expectations of the Study Prefect Team.

---

## 備份策略（Backup Strategy）

本系統運行於 Streamlit Cloud（無狀態環境），因此備份機制為核心功能之一。

### 資料分類
- **靜態資料**：姓名、年級、職位、可用日子、固定值班等。主要從 GitHub `data/` 資料夾載入。
- **動態資料**：累計點數、當週排班、手動調整、請假記錄、調整日誌等。需透過備份保存。

### 備份方式
- **JSON 備份（主要）**：只存放動態數據，檔案輕量。位於側邊欄提供下載與還原功能。
- **PDF 最後一頁（備援）**：匯出 PDF 時會在最後一頁附帶動態數據（標註「INTERNAL USE ONLY」），方便忘記下載 JSON 時使用。發群前務必移除此頁。
- **GitHub 長期保存**：重要備份建議手動上傳至 `backups/` 資料夾並 commit。

### 開發注意事項
- 任何涉及動態數據的修改，都應確保備份功能仍能正常運作。
- 新增功能時，需考慮是否需要將新狀態納入動態備份範圍。
- 備份提醒與引導文字應保持清楚且不冗長。Streamlit 本身對「強制觸發下載」有限制，體驗不一定好。
用戶可能會覺得煩（尤其是頻繁操作時）。
目前「提醒 + 手動下載」的方式已經足夠，且給了用戶選擇權。

---

*End of AGENTS.md*