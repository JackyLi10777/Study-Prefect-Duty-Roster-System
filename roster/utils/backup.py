# roster/utils/backup.py
"""
roster.utils.backup - 系統完整備份 / 還原（解決 Streamlit Cloud 休眠）

這是 AGENTS.md 中「Cloud 備份（強烈建議）」機制的核心實作。
必須與 roster/data/state.py 的 initialize_session_state 搭配使用，
並永遠執行 reindex(index=get_roster_rows(), columns=DAYS) 以維持不變式。
"""

import streamlit as st
import pandas as pd
import json
import datetime
import base64

from roster.config import get_roster_rows, DAYS, VERSION

# ====================== 系統完整備份 / 還原（解決 Cloud 休眠） ======================
def export_system_backup(master_report_df: pd.DataFrame) -> str:
    """導出完整系統狀態（包含全局負荷滑桿）"""
    backup_data = {
        "students_df": st.session_state.students_df.to_dict(orient="records"),
        "roster_df": st.session_state.roster_df.to_dict(orient="index"),
        "manual_weights": st.session_state.manual_weights.to_dict(orient="index"),
        "master_report": master_report_df.to_dict(orient="records") if not master_report_df.empty else [],
        "leave_tracker_input": st.session_state.get("leave_tracker_input", []),
        "global_load_multiplier": st.session_state.get("global_load_multiplier", 1.0),
        "logo_data": base64.b64encode(st.session_state.logo_data).decode() if st.session_state.get("logo_data") else None,
        "version": VERSION,
        "timestamp": datetime.datetime.now().isoformat()
    }
    return json.dumps(backup_data, ensure_ascii=False, indent=2)


def import_system_backup(uploaded_json_file):
    """還原完整系統狀態"""
    try:
        data = json.load(uploaded_json_file)

        # 還原學生名冊
        if "students_df" in data:
            st.session_state.students_df = pd.DataFrame(data["students_df"])

        # 還原排班表
        if "roster_df" in data:
            restored_roster = pd.DataFrame.from_dict(data["roster_df"], orient="index")
            st.session_state.roster_df = restored_roster.reindex(index=get_roster_rows(), columns=DAYS).fillna("")

        # 還原手動調整負荷
        if "manual_weights" in data:
            manual_df = pd.DataFrame.from_dict(data["manual_weights"], orient="index")
            st.session_state.manual_weights = manual_df.reindex(index=get_roster_rows(), columns=DAYS).fillna(0.0)

        # 還原全局負荷滑桿
        if "global_load_multiplier" in data:
            st.session_state.global_load_multiplier = float(data["global_load_multiplier"])

        # 還原請假人員
        st.session_state.leave_tracker_input = data.get("leave_tracker_input", [])

        # 還原校徽
        if data.get("logo_data"):
            st.session_state.logo_data = base64.b64decode(data["logo_data"])

        st.sidebar.success("🔮 備份已完美還原（包含全局負荷滑桿與所有數據）！")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"❌ 還原失敗: {str(e)}")
