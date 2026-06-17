# roster/core/engine.py
"""
roster.core.engine - 核心排班演算法模組

聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
公平性計算、驗證、智慧替補推薦 + 請假後撤銷調整

作者：首席導學風紀 26-27 LI Chuangjie Jacky
版本：v2.4 (post-refactor, roster/ package structure)

本模組嚴格實現 AGENTS.md §1 Core Project Rules 中的所有學校業務規則：
- 學生資格與數據規則（F.3-F.6、Study Prefect vs AHP、fixed/available/history_weight）
- Room 302/303 限制（全天開放、無額外限制、權重1.0/1.5、2 slots 不同人）
- AHP 特權與硬限制（僅 Assist. in charge，-8.0 加成，三處門禁）
- 排班約束（固定優先、歷史公平、F.3 老帶新、每人每天一次、避免連續兩天）
- 值班後請假調整公平性機制

generation 必須保持 pure（不 mutate history_weight），僅 apply_post... 允許調整。
所有對 config helpers 的調用不得 bypass（見 AGENTS.md §3）。
"""

import pandas as pd
import random
from typing import List, Optional, Tuple, Dict
from roster.config import (
    DAYS, ROOMS_CONFIG,
    get_weight, is_assistant_head_only_role,
    is_room_open_on_weekday,
    DEFAULT_GLOBAL_LOAD_MULTIPLIER,
    get_roster_rows, get_base_role,
    normalize_students_role_column,
    AHP_ROLE as _AHP_ROLE, REGULAR_ROLE as _REGULAR_ROLE,
)

# Phase 1: Extracted constants for magic strings and role names (reduces duplication and magic values)
_UNASSIGNED_MARKERS = {"", "X", "⬜", "請假撤銷"}
_ASSIST_ROLE = "Assist. in charge"
_MENTEE_THRESHOLD = 2.0  # history_weight <= 2 auto-tags as mentee
_MENTOR_THRESHOLD = 5.0  # history_weight > 5 qualifies as mentor
_MENTORING_PAIR_BONUS = -2.0  # score bonus for pairing complementary types
# 使用統一中文職位（從 config 匯入，支援 legacy 英文）
# _AHP_ROLE and _REGULAR_ROLE 已從 config import 覆蓋


def _check_role_gate(is_assist_role: bool, person_role: str) -> bool:
    """
    Return True if the person_role is allowed for this role type.

    Strictly implements AGENTS.md §1.3 AHP privileges & restrictions (sing-yin-study-prefect-duty-roster):
    - If is_assist_role=True: only "Assistant 首席導學風紀" allowed.
    - Else: only regular "Study Prefect" allowed.

    This unifies the previously duplicated role gates in:
    1. Fixed-duty priority phase
    2. Fair candidate collection phase
    3. recommend_substitutes()

    Critical for maintaining school policy on leadership roles.
    """
    if is_assist_role:
        return person_role == _AHP_ROLE
    return person_role == _REGULAR_ROLE


def _is_mentee(info: dict) -> bool:
    """Return True if student needs mentoring based on flag or low history_weight."""
    hw = float(info.get("history_weight", 0))
    return bool(info.get("needs_mentoring", False)) or hw <= _MENTEE_THRESHOLD


def _is_mentor(info: dict) -> bool:
    """Return True if student qualifies as a mentor (experienced, not needing mentoring)."""
    hw = float(info.get("history_weight", 0))
    return hw > _MENTOR_THRESHOLD and not bool(info.get("needs_mentoring", False))


def _compute_fair_score(
    history_weight: float,
    global_mult: float,
    is_assist_and_ahp: bool
) -> float:
    """计算公平排班得分（低者优先）。

    实现 AGENTS.md §1.4 中的计分规则：
    - 基础：history_weight * global_load_multiplier
    - 轻微随机打破平局
    - AHP 在 Assist 槽位获得 -8.0 强力加成
    """
    score = history_weight * global_mult + random.uniform(0, 0.3)
    if is_assist_and_ahp:
        score -= 8.0
    return score


def generate_roster(
    students_df: pd.DataFrame,
    leave_students: List[str],
    special_closures: List[str],
    seed: int,
    global_load_multiplier: float = DEFAULT_GLOBAL_LOAD_MULTIPLIER
) -> pd.DataFrame:
    """
    核心公平排班演算法（最終版，roster/core/engine.py）

    嚴格實現 AGENTS.md §1.4 Scheduling Constraints & Algorithm Rules 以及 §1.1-1.3 的所有學校業務規則。

    功能：
    - 固定值班優先（最高優先權）
    - 歷史負荷公平（history_weight * global_load_multiplier，越低越優先）
    - F.3 老帶新 tie-break
    - AHP 特權加成（Assist 槽位 score -= 8.0）
    - 每人每天只能值班一次 + 避免連續兩天
    - Room 302/303/202 限制與權重
    - 特殊不開放與請假處理

    參數：
    - students_df: 必須包含 name/form/role/fixed_general_duty/available/history_weight 等欄位（見 data/models）
    - leave_students: 本週請假人員列表（完全排除候選）
    - special_closures: 使用者指定的不開放時段（格式 "DAY - RoomXXX"）
    - seed: 隨機種子（確保可重現但仍有輕微隨機性）
    - global_load_multiplier: 0.8~2.0，影響本次歷史權重計算（考試季可調高讓低負荷者優先）

    返回：
    - pd.DataFrame: index=get_roster_rows() (即 ROWS_ROSTER), columns=DAYS，值為人名或 "X"/"⬜"/""

    不變式（必須維持）：
    - generation 為 pure，不會 mutate 任何學生的 history_weight（僅 apply_post_publication_leave_adjustment 允許調整）
    - 輸出 roster 總是 reindex 到 get_roster_rows() x DAYS

    參考 AGENTS.md §1 及 §5 Verification Checklist。
    """
    # 角色名稱正規化：支援中英文輸入（由 config 中的 ROLE_MAP 驅動）
    students_df = normalize_students_role_column(students_df)
    random.seed(seed)
    roster = pd.DataFrame(index=get_roster_rows(), columns=DAYS).fillna("")

    leave_set = {str(name).strip() for name in leave_students if str(name).strip()}

    # 【學生規則 - AGENTS.md §1.1】
    # 僅 F.3-F.6 有效；role 嚴格區分（Study Prefect 只能房間，AHP 僅 Assist）；
    # fixed_general_duty 優先；available 限制日子；history_weight 是公平基準（越低越優先）；
    # F.3 享有老帶新 tie-break 優勢。
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
            "history_weight": float(row.get("history_weight", 0.0)),
            "needs_mentoring": bool(row.get("needs_mentoring", False)),
            "is_mentee": _is_mentee(row),
            "is_mentor": _is_mentor(row)
        }

    last_duty_day = {name: -1 for name in student_info.keys()}

    for day_idx, day in enumerate(DAYS):
        assigned_today = set()

        for role in get_roster_rows():
            base_role = get_base_role(role)

            # 【Room 302/303 限制 - AGENTS.md §1.2】
            # Room 302：1 slot/天，weight=1.0，全天開放（MON-FRI），非 AHP-only，無額外經驗限制。
            # Room 303：2 slots/天（-1/-2），weight=1.5/槽，全天開放，非 AHP-only，同一日兩槽必須不同人（由 assigned_today 保證）。
            # 僅 Room 202 有硬限制（Tue/Fri 關閉 → ⬜）。
            # 特殊不開放由 special_closures 控制（注意當前實現有已知 bug，見 AGENTS §4）。
            if any(f"{day} - {role}" in sc for sc in special_closures) or \
               not is_room_open_on_weekday(base_role, day):
                roster.at[role, day] = "X" if "Room 202" not in role or day not in ["TUESDAY", "FRIDAY"] else "⬜"
                continue


            # Track first slot occupant for mentoring pairing in 2-slot rooms
            first_slot_occupant = None
            base_role_name = get_base_role(role)
            if base_role_name in ["Room 303", "Room 202"] and " - 2" in role:
                first_role = role.replace(" - 2", " - 1")
                first_p = str(roster.at[first_role, day]).strip()
                if first_p and first_p in student_info:
                    first_slot_occupant = first_p

            is_assist_role = is_assistant_head_only_role(base_role)

            # ==================== 固定值班優先 ====================
            # 學年預先安排的義務具有最高優先權，必須先滿足。
            assigned = False
            for name, info in student_info.items():
                if info["fixed"] == day and name not in assigned_today:
                    # 【AHP 特權與限制 - AGENTS.md §1.3】
                    # Assistant 首席導學風紀 僅能擔任 "Assist. in charge"（領導職位）；
                    # 普通 Study Prefect 完全禁止進入 Assist 槽；
                    # AHP 完全禁止值守一般房間（302/303/202）。
                    # 門禁在 fixed 與 fair 兩階段各實作一次，recommend 也重複檢查。
                    if not _check_role_gate(is_assist_role, info["role"]):
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
                if day_idx > 0 and last_duty_day.get(name, -1) == day_idx - 1:
                    continue
                # AHP 門禁（已統一為 _check_role_gate，確保安全且無重複）
                if not _check_role_gate(is_assist_role, info["role"]):
                    continue

                is_junior = info["form"] == "F.3"
                is_assist_and_ahp = is_assist_role and info["role"] == _AHP_ROLE
                score = _compute_fair_score(
                    info["history_weight"], global_load_multiplier, is_assist_and_ahp
                )

                # Mentoring pairing bonus for 2-slot rooms (Room 303, Room 202)
                if first_slot_occupant and name != first_slot_occupant:
                    occ_info = student_info.get(first_slot_occupant, {})
                    if occ_info.get("is_mentee") and info.get("is_mentor"):
                        score += _MENTORING_PAIR_BONUS
                    elif occ_info.get("is_mentor") and info.get("is_mentee"):
                        score += _MENTORING_PAIR_BONUS

                candidates.append((score, name, is_junior))

            if not candidates:
                roster.at[role, day] = ""
                continue

            # 排序：score 越低越優先；同分時 F.3（is_junior=True）勝出（-is_junior）
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
    Complete validation + dynamic workload computation (final version + leave revocation support).

    Validation items (per AGENTS.md §1 & §5):
    - typo: Name not in roster (leave revocation treated as non-real, auto-skipped)
    - duplicate: Same-day duplicate duty (note: known bug in current impl may flag cross-day normal assignments, see AGENTS §4)
    - leave_conflict: Leave person still assigned
    - vacuum: Vacancies (Room202 Tue/Fri ⬜ not counted as vacancy; leave revocation not counted)

    Workload calculation:
    - Accumulate current duty weight from student's prior history_weight (supports manual_weights override)
    - Strictly skip "請假撤銷" (leave revocation) cells to ensure post-adjustment fairness is not double-counted
    - Output report is always sorted ascending by "Cumulative Weighted Load (points)" (lower load = higher priority for assignments)

    UI display uses Chinese columns via data/models helpers (streamlit-best-practices); exports use professional English columns while preserving original Chinese student names.
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
        for role in get_roster_rows():
            person = str(roster_df.at[role, day]).strip()
            if person and person not in _UNASSIGNED_MARKERS and person not in valid_names:
                errors["typo"][1].append(f"{day} - {role}: {person}（姓名不在名冊中）")
                errors["typo"] = (True, errors["typo"][1])

    # 同一天重複排班檢查（AGENTS §4 指出目前實作有 bug，會誤報跨天正常排班）
    assigned = {}
    for day in DAYS:
        for role in get_roster_rows():
            person = str(roster_df.at[role, day]).strip()
            if person and person not in _UNASSIGNED_MARKERS:
                if person in assigned:
                    errors["duplicate"][1].append(f"{person} 同時出現在 {assigned[person]} 和 {day}-{role}")
                    errors["duplicate"] = (True, errors["duplicate"][1])
                else:
                    assigned[person] = f"{day}-{role}"

    # 請假衝突檢查
    leave_set = {str(name).strip() for name in leave_students if str(name).strip()}
    for day in DAYS:
        for role in get_roster_rows():
            person = str(roster_df.at[role, day]).strip()
            if person in leave_set:
                errors["leave_conflict"][1].append(f"{day} - {role}: {person} 已請假但仍排班")
                errors["leave_conflict"] = (True, errors["leave_conflict"][1])

    # 空缺檢查（請假撤銷不視為空缺；Room202 Tue/Fri 的 ⬜ 也不算空缺）
    for day in DAYS:
        for role in get_roster_rows():
            val = str(roster_df.at[role, day]).strip()
            if val == "" and not ("Room 202" in role and day in ["TUESDAY", "FRIDAY"]):
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
            for role in get_roster_rows():
                cell_val = str(roster_df.at[role, day]).strip()
                # 【關鍵公平規則】跳過「請假撤銷」單元，確保值班後調整的點數不會被重複計算
                # 符合 AGENTS.md §1.4 Leave Adjustment Rules
                if cell_val == name and cell_val not in _UNASSIGNED_MARKERS:
                    val = manual_weights.at[role, day]
                    added = float(val) if pd.notna(val) else get_weight(role)
                    total_weight += added
                    this_week += added

        report.append({
            "Student Name": name,
            "Form": row.get("form", ""),
            "Class": row.get("class", ""),
            "Role": row.get("role", ""),
            "This Week Added (points)": round(this_week, 1),
            "Cumulative Weighted Load (points)": round(total_weight, 1)
        })

    report_df = pd.DataFrame(report)
    if not report_df.empty:
        report_df = report_df.sort_values(by="Cumulative Weighted Load (points)", ascending=True)
    else:
        report_df = pd.DataFrame(columns=[
            "Student Name", "Form", "Class",
            "Role", "This Week Added (points)", "Cumulative Weighted Load (points)"
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
    Smart substitute recommendation system (final version, with role restrictions).

    Strictly follows AGENTS.md §1.3 AHP privileges & §1.1 student rules:
    - Assist slot only recommends AHPs
    - Regular room slots only recommend regular Study Prefects
    - Must match the day's available days
    - Sorted by current history_weight ascending (fairness priority)

    UI display renames columns to Chinese; internal uses English for consistency with export logic.
    """
    current_person = str(roster_df.at[chosen_role, chosen_day]).strip()
    if not current_person or current_person in _UNASSIGNED_MARKERS:
        return None, "該時段目前無人值班或為常規不開放時段"

    base_role = get_base_role(chosen_role)
    is_assist_role = is_assistant_head_only_role(base_role)

    subs = []
    for _, rec in students_df.iterrows():
        name = str(rec["name"]).strip()
        if not name or name == current_person:
            continue
        if chosen_day not in str(rec.get("available", "")).upper():
            continue
        # AHP 門禁（已統一使用 _check_role_gate）
        if not _check_role_gate(is_assist_role, rec.get("role")):
            continue

        subs.append({
            "Name": name,
            "Form": rec.get("form", ""),
            "Current Load (points)": float(rec.get("history_weight", 0.0))
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
    請假後撤銷點數調整（AGENTS.md §1.4 核心公平功能，v2.4 最重要新功能）

    - 從原值班人員的 history_weight 直接扣除該崗位權重（永久影響後續排班公平性）
    - 可選擇替補人員（同時給替補加權重 + 更新 roster）
    - 若無替補，則將該崗位標記為「請假撤銷」（validate 與計分都會自動跳過）
    - 權重一律使用 get_weight(role) 的基礎值（不考慮本次 manual override）

    這是值班表發布後維持長期公平的唯一合法機制。
    """
    weight = get_weight(role)

    # 從原人員撤銷點數（直接 mutate，符合設計）
    mask = students_df["name"].str.strip() == original_person.strip()
    if mask.any():
        students_df.loc[mask, "history_weight"] -= weight

    if replacement_person:
        # 有替補：更新 roster 給替補人員並加權重
        mask2 = students_df["name"].str.strip() == replacement_person.strip()
        if mask2.any():
            students_df.loc[mask2, "history_weight"] += weight
        roster_df.at[role, day] = replacement_person
    else:
        # 無替補：標記為請假撤銷（validate_and_compute 會自動跳過計算，確保公平）
        roster_df.at[role, day] = "請假撤銷"

    return weight




def annotate_mentoring_pairs(roster_df: pd.DataFrame, students_df: pd.DataFrame) -> dict:
    """
    Analyze the roster and return metadata about mentoring pairs for UI display.

    Returns a dict mapping "(role)_(day)" -> "paired" for slots where a mentee
    and mentor are assigned to the same 2-slot room (Room 303 or Room 202).
    """
    look = {}
    for _, row in students_df.iterrows():
        name = str(row["name"]).strip()
        if name:
            look[name] = {
                "history_weight": float(row.get("history_weight", 0)),
                "needs_mentoring": bool(row.get("needs_mentoring", False)),
            }

    pairs = {}
    for role in ["Room 303 (HW Completion)", "Room 202 (F1 Study Group)"]:
        for day in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]:
            if "Room 202" in role and day in ["TUESDAY", "FRIDAY"]:
                continue
            r1 = role + " - 1"
            r2 = role + " - 2"
            p1 = str(roster_df.at[r1, day]).strip() if r1 in roster_df.index else ""
            p2 = str(roster_df.at[r2, day]).strip() if r2 in roster_df.index else ""
            if p1 and p2 and p1 in look and p2 in look:
                mentee1 = look[p1]["needs_mentoring"] or look[p1]["history_weight"] <= _MENTEE_THRESHOLD
                mentee2 = look[p2]["needs_mentoring"] or look[p2]["history_weight"] <= _MENTEE_THRESHOLD
                mentor1 = look[p1]["history_weight"] > _MENTOR_THRESHOLD and not look[p1]["needs_mentoring"]
                mentor2 = look[p2]["history_weight"] > _MENTOR_THRESHOLD and not look[p2]["needs_mentoring"]
                if (mentee1 and mentor2) or (mentee2 and mentor1):
                    pair_key = role + "_" + day
                    pairs[pair_key] = "paired"
    return pairs
