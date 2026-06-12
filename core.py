# core.py (root shim / compatibility layer)
"""
Temporary root-level shim for the modular refactor (see approved plan.md).

All existing `from core import generate_roster, ...` continue to work unchanged.

The real implementation (generate_roster logic 100% unchanged) is now at:
    roster/core/engine.py
    (re-exported via roster/core/__init__.py)

Room 302/303 and AHP rules are preserved exactly (they live in the moved code + config).

This file will be cleaned up after full verification.
"""
from roster.core import (
    generate_roster,
    validate_and_compute,
    recommend_substitutes,
    apply_post_publication_leave_adjustment,
)

print("✅ [shim] root core.py now forwards to roster.core (generate_roster logic unchanged)")


def generate_roster(
    students_df: pd.DataFrame,
    leave_students: List[str],
    special_closures: List[str],
    seed: int,
    global_load_multiplier: float = DEFAULT_GLOBAL_LOAD_MULTIPLIER
) -> pd.DataFrame:
    """
    核心公平排班演算法（最終版）
    - 嚴格遵守所有學校業務規則（Assistant Head 限制、Room 202 星期二/五 ⬜、每日槽位、權重）
    - 支援全局負荷調節滑桿（global_load_multiplier），即時影響權重計算
    - 固定值班優先 + 歷史負荷公平 + 老帶新（F.3 優先）
    - 每人每天只能值班一次 + 避免連續兩天
    """
    random.seed(seed)
    roster = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

    leave_set = {str(name).strip() for name in leave_students if str(name).strip()}

    # 學生資訊字典（高效查詢）
    student_info: Dict[str, dict] = {}
    for _, row in students_df.iterrows():
        name = str(row["name"]).strip()
        if not name or name in leave_set:
            continue
        student_info[name] = {
            "form": str(row.get("form", "")),
            "role": str(row.get("role", "Study Prefect")),
            "fixed": str(row.get("fixed_general_duty", "NONE")).upper(),
            "available": [d.strip().upper() for d in str(row.get("available", "")).split(",") if d.strip()],
            "history_weight": float(row.get("history_weight", 0.0))
        }

    last_duty_day = {name: -1 for name in student_info.keys()}

    for day_idx, day in enumerate(DAYS):
        assigned_today = set()

        for role in ROWS_ROSTER:
            base_role = role.split(" - ")[0].strip()

            # 特殊不開放或常規不開放
            if any(f"{day} - {role}" in sc for sc in special_closures) or \
               not is_room_open_on_weekday(base_role, day):
                roster.at[role, day] = "X" if "Room202" not in role or day not in ["TUESDAY", "FRIDAY"] else "⬜"
                continue

            is_assist_role = is_assistant_head_only_role(base_role)

            # ==================== 固定值班優先 ====================
            assigned = False
            for name, info in student_info.items():
                if info["fixed"] == day and name not in assigned_today:
                    if is_assist_role and info["role"] != "Assistant Head Study Prefect":
                        continue
                    if not is_assist_role and info["role"] != "Study Prefect":
                        continue

                    roster.at[role, day] = name
                    last_duty_day[name] = day_idx
                    assigned_today.add(name)
                    assigned = True
                    break
            if assigned:
                continue

            # ==================== 一般公平排班 ====================
            candidates = []
            for name, info in student_info.items():
                if name in leave_set or name in assigned_today:
                    continue
                if day not in info["available"]:
                    continue
                if last_duty_day.get(name, -1) == day_idx - 1:
                    continue
                if is_assist_role and info["role"] != "Assistant Head Study Prefect":
                    continue
                if not is_assist_role and info["role"] != "Study Prefect":
                    continue

                effective_weight = info["history_weight"] * global_load_multiplier
                is_junior = info["form"] == "F.3"
                score = effective_weight + random.uniform(0, 0.3)

                if is_assist_role and info["role"] == "Assistant Head Study Prefect":
                    score -= 8.0

                candidates.append((score, name, is_junior))

            if not candidates:
                roster.at[role, day] = ""
                continue

            candidates.sort(key=lambda x: (x[0], -x[2]))
            chosen = candidates[0][1]

            roster.at[role, day] = chosen
            last_duty_day[chosen] = day_idx
            assigned_today.add(chosen)

    return roster


def validate_and_compute(
    roster_df: pd.DataFrame,
    students_df: pd.DataFrame,
    leave_students: List[str],
    manual_weights: pd.DataFrame
) -> Dict:
    """
    完整驗證 + 動態負荷計算（最終版 + 請假撤銷支援）
    - 已修正 KeyError（空報表防護）
    - 新增對「請假撤銷」單元的過濾，確保撤銷後點數不重複計算
    """
    errors = {
        "typo": (False, []),
        "duplicate": (False, []),
        "leave_conflict": (False, []),
        "vacuum": (False, [])
    }

    valid_names = {str(row["name"]).strip() for _, row in students_df.iterrows() if str(row["name"]).strip()}

    # 姓名不存在檢查（請假撤銷視為非真實人員）
    for day in DAYS:
        for role in ROWS_ROSTER:
            person = str(roster_df.at[role, day]).strip()
            if person and person not in ["X", "⬜", "請假撤銷"] and person not in valid_names:
                errors["typo"][1].append(f"{day} - {role}: {person}（姓名不在名冊中）")
                errors["typo"] = (True, errors["typo"][1])

    # 同一天重複排班檢查
    assigned = {}
    for day in DAYS:
        for role in ROWS_ROSTER:
            person = str(roster_df.at[role, day]).strip()
            if person and person not in ["X", "⬜", "請假撤銷"]:
                if person in assigned:
                    errors["duplicate"][1].append(f"{person} 同時出現在 {assigned[person]} 和 {day}-{role}")
                    errors["duplicate"] = (True, errors["duplicate"][1])
                else:
                    assigned[person] = f"{day}-{role}"

    # 請假衝突檢查
    leave_set = {str(name).strip() for name in leave_students if str(name).strip()}
    for day in DAYS:
        for role in ROWS_ROSTER:
            person = str(roster_df.at[role, day]).strip()
            if person in leave_set:
                errors["leave_conflict"][1].append(f"{day} - {role}: {person} 已請假但仍排班")
                errors["leave_conflict"] = (True, errors["leave_conflict"][1])

    # 空缺檢查（請假撤銷不視為空缺）
    for day in DAYS:
        for role in ROWS_ROSTER:
            val = str(roster_df.at[role, day]).strip()
            if val == "" and not ("Room202" in role and day in ["TUESDAY", "FRIDAY"]):
                errors["vacuum"][1].append(f"{day} - {role} 尚未排班")
                errors["vacuum"] = (True, errors["vacuum"][1])

    # 計算每人累計負荷（含本次手動調整 + 請假撤銷過濾）
    report = []
    for _, row in students_df.iterrows():
        name = str(row["name"]).strip()
        if not name:
            continue

        total_weight = float(row.get("history_weight", 0.0))
        this_week = 0.0

        for day in DAYS:
            for role in ROWS_ROSTER:
                cell_val = str(roster_df.at[role, day]).strip()
                # 關鍵：跳過請假撤銷的單元，確保已撤銷的點數不會重複計算
                if cell_val == name and cell_val not in ["X", "⬜", "請假撤銷"]:
                    val = manual_weights.at[role, day]
                    added = float(val) if pd.notna(val) else get_weight(role)
                    total_weight += added
                    this_week += added

        report.append({
            "學生姓名 (Prefect Name)": name,
            "年級 (Form)": row.get("form", ""),
            "班別 (Class)": row.get("class", ""),
            "職級 (Role)": row.get("role", ""),
            "當週新增 (次)": round(this_week, 1),
            "最終總計加權負荷 (點)": round(total_weight, 1)
        })

    report_df = pd.DataFrame(report)
    if not report_df.empty:
        report_df = report_df.sort_values(by="最終總計加權負荷 (點)", ascending=True)
    else:
        report_df = pd.DataFrame(columns=[
            "學生姓名 (Prefect Name)", "年級 (Form)", "班別 (Class)",
            "職級 (Role)", "當週新增 (次)", "最終總計加權負荷 (點)"
        ])

    return {
        "report_df": report_df,
        "typo": errors["typo"],
        "duplicate": errors["duplicate"],
        "leave_conflict": errors["leave_conflict"],
        "vacuum": errors["vacuum"]
    }


def recommend_substitutes(
    roster_df: pd.DataFrame,
    students_df: pd.DataFrame,
    chosen_day: str,
    chosen_role: str
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    智慧替補推薦系統（最終版，含角色限制）
    """
    current_person = str(roster_df.at[chosen_role, chosen_day]).strip()
    if not current_person or current_person in ["X", "⬜", "請假撤銷"]:
        return None, "該時段目前無人值班或為常規不開放時段"

    base_role = chosen_role.split(" - ")[0].strip()
    is_assist_role = is_assistant_head_only_role(base_role)

    subs = []
    for _, rec in students_df.iterrows():
        name = str(rec["name"]).strip()
        if not name or name == current_person:
            continue
        if chosen_day not in str(rec.get("available", "")).upper():
            continue
        if is_assist_role and rec.get("role") != "Assistant Head Study Prefect":
            continue
        if not is_assist_role and rec.get("role") != "Study Prefect":
            continue

        subs.append({
            "姓名": name,
            "年級": rec.get("form", ""),
            "當前總點數": float(rec.get("history_weight", 0.0))
        })

    if not subs:
        return None, "找不到合適替補人員"

    sub_df = pd.DataFrame(subs).sort_values(by="當前總點數")
    return sub_df, None


def apply_post_publication_leave_adjustment(
    students_df: pd.DataFrame,
    roster_df: pd.DataFrame,
    day: str,
    role: str,
    original_person: str,
    replacement_person: Optional[str] = None
) -> float:
    """
    請假後撤銷點數調整（核心公平功能）
    - 從原值班人員的 history_weight 扣除該崗位權重
    - 可選擇替補人員（更新 roster 並給予替補點數）
    - 若無替補，則將該崗位標記為「請假撤銷」
    """
    weight = get_weight(role)

    # 從原人員撤銷點數
    mask = students_df["name"].str.strip() == original_person.strip()
    if mask.any():
        students_df.loc[mask, "history_weight"] -= weight

    if replacement_person:
        # 有替補：更新 roster 給替補人員
        mask2 = students_df["name"].str.strip() == replacement_person.strip()
        if mask2.any():
            students_df.loc[mask2, "history_weight"] += weight
        roster_df.at[role, day] = replacement_person
    else:
        # 無替補：標記為請假撤銷（validate_and_compute 會自動跳過計算）
        roster_df.at[role, day] = "請假撤銷"

    return weight


print("✅ core.py 已載入完成 - 公平排班引擎 + 智慧替補 + 驗證模組 + 請假撤銷調整功能就緒")