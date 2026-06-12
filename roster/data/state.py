# roster/data/state.py
"""
roster.data.state - 資料層：Session State 初始化與空 DataFrame 輔助

Critical for Streamlit Cloud hibernation resilience (per AGENTS.md §2 & §3)。

initialize_session_state 必須是**唯一中央守護者**，且「必須放在 app.py 最前面呼叫」。
它負責初始化所有與排班公平性、請假、負荷調整相關的 session 狀態，
確保 Cloud 休眠後資料不會遺失（搭配 utils/backup.py 的 JSON 備份機制）。

所有新 persistent state 都必須在此處註冊 + 同步更新 backup/restore 邏輯。
"""

import pandas as pd
import streamlit as st
from roster.config import get_roster_rows, DAYS, DEFAULT_GLOBAL_LOAD_MULTIPLIER


def get_empty_students_df() -> pd.DataFrame:
    """
    建立空的學生名冊 DataFrame（供初始化使用）
    """
    return pd.DataFrame(columns=[
        "name", "form", "class", "role",
        "fixed_general_duty", "available",
        "history_duties", "history_weight", "remarks"
    ])


def initialize_session_state():
    """
    完整初始化所有 session_state（徹底解決 Streamlit Cloud 休眠後資料遺失問題）
    必須放在 app.py 最前面呼叫（AGENTS.md §2 強制要求）。

    負責的狀態包含：
    - students_df / roster_df / manual_weights（核心公平數據）
    - global_load_multiplier（本次排班負荷倍率）
    - leave_tracker_input（請假）
    - master_report_df（審計）
    - logo_data / current_verse 等 UI 狀態

    新增任何需要持久化的 state 都必須在此處初始化，
    並同步更新 roster/utils/backup.py 的 export/import 邏輯。
    """
    if 'students_df' not in st.session_state:
        st.session_state.students_df = get_empty_students_df()

    if 'roster_df' not in st.session_state:
        st.session_state.roster_df = pd.DataFrame(index=get_roster_rows(), columns=DAYS).fillna("")

    if 'manual_weights' not in st.session_state:
        st.session_state.manual_weights = pd.DataFrame(index=get_roster_rows(), columns=DAYS).fillna(0.0)

    if 'logo_data' not in st.session_state:
        st.session_state.logo_data = None

    if 'show_clear_confirm' not in st.session_state:
        st.session_state.show_clear_confirm = False

    if 'leave_tracker_input' not in st.session_state:
        st.session_state.leave_tracker_input = []

    if 'master_report_df' not in st.session_state:
        st.session_state.master_report_df = pd.DataFrame()

    if 'global_load_multiplier' not in st.session_state:
        st.session_state.global_load_multiplier = DEFAULT_GLOBAL_LOAD_MULTIPLIER

    if 'current_verse' not in st.session_state:
        st.session_state.current_verse = None
