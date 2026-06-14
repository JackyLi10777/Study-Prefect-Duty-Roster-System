# roster/utils/backup.py
"""
roster.utils.backup - 系統完整備份 / 還原（解決 Streamlit Cloud 休眠）

這是 AGENTS.md 中「Cloud 備份（強烈建議）」機制的核心實作。
必須與 roster/data/state.py 的 initialize_session_state 搭配使用，
並永遠執行 reindex(index=get_roster_rows(), columns=DAYS) 以維持不變式。

增強功能：
- 自動備份提醒
- 多版本備份管理（in-memory history + 可下載特定版本）
- 備份完整性驗證
- Full Replace vs Smart Merge 還原選項
- 清晰狀態訊息與錯誤處理
- 涵蓋所有關鍵狀態（含新功能：history_loads, roster_versions, semester_hours, adjustment_log 等）
"""

import streamlit as st
import pandas as pd
import json
import datetime
import base64

from roster.config import get_roster_rows, DAYS, VERSION

# ====================== 備份資料產生（單一來源，確保涵蓋所有關鍵資料） ======================
def _create_backup_data(master_report_df: pd.DataFrame) -> dict:
    """建立完整備份資料字典。只包含 dynamic data（頻繁變動的資料），以保持檔案小巧。
    Static data (name, form, class, role, available, fixed_general_duty) 應從 GitHub 載入作為來源。
    """
    # 只保存 dynamic 部分 for students (name + dynamic fields for matching)
    students_dynamic = []
    for _, row in st.session_state.students_df.iterrows():
        students_dynamic.append({
            "name": str(row.get("name", "")).strip(),
            "history_duties": int(row.get("history_duties", 0)),
            "history_weight": float(row.get("history_weight", 0.0)),
            "needs_mentoring": bool(row.get("needs_mentoring", False)),
            "remarks": str(row.get("remarks", ""))
        })

    return {
        # Dynamic data only
        "students_dynamic": students_dynamic,  # name + dynamic fields only
        "roster_df": st.session_state.roster_df.to_dict(orient="index"),
        "manual_weights": st.session_state.manual_weights.to_dict(orient="index"),
        "master_report": master_report_df.to_dict(orient="records") if not master_report_df.empty else [],
        "leave_tracker_input": st.session_state.get("leave_tracker_input", []),
        "global_load_multiplier": st.session_state.get("global_load_multiplier", 1.0),
        "logo_data": base64.b64encode(st.session_state.logo_data).decode() if st.session_state.get("logo_data") else None,
        "version": VERSION,
        "timestamp": datetime.datetime.now().isoformat(),
        # 其他動態狀態
        "history_loads": st.session_state.get("history_loads", []),
        "theme": st.session_state.get("theme", "light"),
        "ui_language": st.session_state.get("ui_language", "zh"),
        "roster_versions": st.session_state.get("roster_versions", []),
        "semester_hours": st.session_state.get("semester_hours", {}),
        "adjustment_log": st.session_state.get("adjustment_log", []),
        "selected_students_for_bulk": st.session_state.get("selected_students_for_bulk", []),
        "student_search": st.session_state.get("student_search", ""),
        "roster_search": st.session_state.get("roster_search", ""),
    }

# ====================== 備份完整性驗證 ======================
def validate_backup_integrity(data: dict) -> tuple[bool, str]:
    """
    驗證備份 JSON 是否有效且包含必要資料。
    返回 (is_valid, message)
    """
    if not isinstance(data, dict):
        return False, "備份資料不是有效的字典結構"

    required_keys = [
        "students_dynamic", "roster_df", "manual_weights",
        "leave_tracker_input", "global_load_multiplier"
    ]
    missing = [k for k in required_keys if k not in data]
    if missing:
        return False, f"缺少必要欄位: {missing}"

    try:
        # 嘗試重建核心 DataFrames 驗證結構 (students_dynamic is list of dicts)
        pd.DataFrame(data["students_dynamic"])
        pd.DataFrame.from_dict(data["roster_df"], orient="index")
        pd.DataFrame.from_dict(data["manual_weights"], orient="index")
        # 驗證基本型別
        float(data.get("global_load_multiplier", 0))
        list(data.get("leave_tracker_input", []))
    except Exception as e:
        return False, f"資料結構損壞，無法解析: {str(e)}"

    # 檢查是否有至少一些學生資料（基本健全性）
    if not data.get("students_dynamic"):
        return False, "備份中沒有學生資料"

    return True, "備份完整性驗證通過"

# ====================== 系統完整備份 / 還原 ======================
def export_system_backup(master_report_df: pd.DataFrame) -> str:
    """導出完整系統狀態。同時將此版本加入 in-memory 備份歷史（多版本管理）。"""
    backup_data = _create_backup_data(master_report_df)
    json_str = json.dumps(backup_data, ensure_ascii=False, indent=2)

    # 多版本管理：將此備份加入歷史（限制最多 10 個）
    history = st.session_state.get("backup_history", [])
    history.append({
        "timestamp": backup_data["timestamp"],
        "version": len(history) + 1,
        "json": json_str,
        "size": len(json_str)
    })
    if len(history) > 10:
        history = history[-10:]  # 保留最新 10 個
    st.session_state.backup_history = history
    st.session_state.last_backup_time = backup_data["timestamp"]
    st.session_state.backup_reminder = False  # 備份後清除提醒

    return json_str

def import_system_backup(uploaded_json_file, replace_mode: str = "full"):
    """
    還原完整系統狀態。
    replace_mode: "full" (完全取代) 或 "smart_merge" (智慧合併)
    先執行完整性驗證。
    """
    try:
        data = json.load(uploaded_json_file)

        # 步驟1: 完整性驗證
        is_valid, msg = validate_backup_integrity(data)
        if not is_valid:
            st.sidebar.error(f"❌ 備份驗證失敗: {msg}")
            return

        st.sidebar.info(f"✅ 備份驗證通過: {msg}")

        if replace_mode == "full":
            # Full Replace - 傳統完全取代模式
            _apply_full_replace(data)
            st.sidebar.success("🔄 完整取代還原成功！所有資料已更新。")
        else:
            # Smart Merge - 智慧合併模式
            _apply_smart_merge(data)
            st.sidebar.success("🔀 智慧合併還原成功！學生資料已合併，當週排班以備份為主。")

        # 還原後清除提醒
        st.session_state.backup_reminder = False
        st.rerun()

    except json.JSONDecodeError:
        st.sidebar.error("❌ 還原失敗: 無效的 JSON 格式。請確認檔案正確。")
    except Exception as e:
        st.sidebar.error(f"❌ 還原失敗: {str(e)}")

def _apply_full_replace(data: dict):
    """完整取代邏輯（原行為） - 只更新 dynamic 資料，static 保持當前 (從 GitHub 載入)"""
    # 還原 dynamic 學生資料 (students_dynamic)
    if "students_dynamic" in data:
        backup_dyn = {item["name"]: item for item in data["students_dynamic"]}
        for idx, row in st.session_state.students_df.iterrows():
            name = str(row["name"]).strip()
            if name in backup_dyn:
                dyn = backup_dyn[name]
                st.session_state.students_df.at[idx, "history_duties"] = dyn.get("history_duties", 0)
                st.session_state.students_df.at[idx, "history_weight"] = dyn.get("history_weight", 0.0)
                st.session_state.students_df.at[idx, "remarks"] = dyn.get("remarks", "")
                st.session_state.students_df.at[idx, "needs_mentoring"] = dyn.get("needs_mentoring", False)

    if "roster_df" in data:
        restored_roster = pd.DataFrame.from_dict(data["roster_df"], orient="index")
        st.session_state.roster_df = restored_roster.reindex(index=get_roster_rows(), columns=DAYS).fillna("")

    if "manual_weights" in data:
        manual_df = pd.DataFrame.from_dict(data["manual_weights"], orient="index")
        st.session_state.manual_weights = manual_df.reindex(index=get_roster_rows(), columns=DAYS).fillna(0.0)

    if "global_load_multiplier" in data:
        st.session_state.global_load_multiplier = float(data["global_load_multiplier"])

    st.session_state.leave_tracker_input = data.get("leave_tracker_input", [])

    if data.get("logo_data"):
        st.session_state.logo_data = base64.b64decode(data["logo_data"])

    # 還原新狀態
    for key in ["history_loads", "theme", "ui_language", "roster_versions", "semester_hours", "adjustment_log"]:
        if key in data:
            st.session_state[key] = data.get(key, [])

def _apply_smart_merge(data: dict):
    """
    智慧合併邏輯：
    - students_dynamic: 按姓名合併/更新 dynamic fields（static 保持當前）
    - roster_df, manual_weights, master_report: 傾向使用備份（當週特定）
    - leave_tracker_input, adjustment_log: 合併
    - 其他狀態 (history, versions, hours 等): 合併
    """
    # 智慧合併學生 dynamic 資料（按 name）
    if "students_dynamic" in data:
        backup_dyn = {item["name"]: item for item in data["students_dynamic"]}
        for idx, row in st.session_state.students_df.iterrows():
            name = str(row["name"]).strip()
            if name in backup_dyn:
                dyn = backup_dyn[name]
                st.session_state.students_df.at[idx, "history_duties"] = dyn.get("history_duties", row.get("history_duties", 0))
                st.session_state.students_df.at[idx, "history_weight"] = dyn.get("history_weight", row.get("history_weight", 0.0))
                st.session_state.students_df.at[idx, "remarks"] = dyn.get("remarks", row.get("remarks", ""))
                st.session_state.students_df.at[idx, "needs_mentoring"] = dyn.get("needs_mentoring", row.get("needs_mentoring", False))

    # 當週特定資料傾向替換
    if "roster_df" in data:
        restored_roster = pd.DataFrame.from_dict(data["roster_df"], orient="index")
        st.session_state.roster_df = restored_roster.reindex(index=get_roster_rows(), columns=DAYS).fillna("")

    if "manual_weights" in data:
        manual_df = pd.DataFrame.from_dict(data["manual_weights"], orient="index")
        st.session_state.manual_weights = manual_df.reindex(index=get_roster_rows(), columns=DAYS).fillna(0.0)

    if "global_load_multiplier" in data:
        st.session_state.global_load_multiplier = float(data["global_load_multiplier"])

    # 合併 list 型資料
    current_leave = set(st.session_state.get("leave_tracker_input", []))
    current_leave.update(data.get("leave_tracker_input", []))
    st.session_state.leave_tracker_input = list(current_leave)

    current_log = st.session_state.get("adjustment_log", [])
    current_log.extend(data.get("adjustment_log", []))
    st.session_state.adjustment_log = current_log[-50:]  # 限制長度

    # 合併其他狀態
    for key in ["history_loads", "roster_versions", "semester_hours"]:
        if key in data:
            current = st.session_state.get(key, {})
            if isinstance(current, list):
                current.extend(data.get(key, []))
                st.session_state[key] = current[-20:] if key in ["history_loads", "roster_versions"] else current
            else:
                current.update(data.get(key, {}))
                st.session_state[key] = current

    # logo 等直接替換
    if data.get("logo_data"):
        st.session_state.logo_data = base64.b64decode(data["logo_data"])

    if "theme" in data:
        st.session_state.theme = data.get("theme", "light")
    if "ui_language" in data:
        st.session_state.ui_language = data.get("ui_language", "zh")

# ====================== 輔助函式（供 UI 使用） ======================
def get_backup_history():
    """取得目前 session 中的多版本備份歷史（最新在前）"""
    return st.session_state.get("backup_history", [])

def trigger_backup_reminder():
    """在重要操作後呼叫，觸發側邊欄提醒。"""
    st.session_state.backup_reminder = True

def clear_backup_reminder():
    """在執行備份後清除提醒。"""
    st.session_state.backup_reminder = False

def get_dynamic_backup_json(master_report_df: pd.DataFrame) -> str:
    """取得當前動態資料的 JSON 字串（不觸發歷史記錄，用於 PDF 備份頁）。"""
    backup_data = _create_backup_data(master_report_df)
    return json.dumps(backup_data, ensure_ascii=False, indent=2)
