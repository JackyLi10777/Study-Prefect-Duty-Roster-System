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
import os
from roster.config import get_roster_rows, DAYS, DEFAULT_GLOBAL_LOAD_MULTIPLIER
from roster.data.demo import get_demo_dataframe  # for fallback static data


def get_empty_students_df() -> pd.DataFrame:
    """
    建立空的學生名冊 DataFrame（供初始化使用）
    """
    return pd.DataFrame(columns=[
        "name", "form", "class", "role",
        "fixed_general_duty", "available",
        "history_duties", "history_weight", "needs_mentoring", "remarks"
    ])


def load_static_students() -> pd.DataFrame:
    """
    Load static student data (name, form, class, role, available, fixed_general_duty) from GitHub/repo file if available.
    GitHub (repo) is the source of truth for static data.
    Fallback to demo data (static portion only) if no file found.
    Dynamic fields (history_*) are initialized to 0.
    """
    possible_paths = ['students.csv', 'data/students.csv', 'resources/students.csv']
    for path in possible_paths:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                # Ensure required static columns
                static_cols = ["name", "form", "class", "role", "available", "fixed_general_duty"]
                for col in static_cols:
                    if col not in df.columns:
                        df[col] = ""
                df = df[static_cols].copy()
                # Initialize dynamic to 0
                df["history_duties"] = 0
                df["history_weight"] = 0.0
                df["needs_mentoring"] = False
                df["remarks"] = ""
                return df
            except Exception:
                pass  # fallback

    # Fallback: use demo but only static + init dynamic=0
    try:
        demo = get_demo_dataframe()
        static_cols = ["name", "form", "class", "role", "available", "fixed_general_duty"]
        df = demo[static_cols].copy()
        df["history_duties"] = 0
        df["history_weight"] = 0.0
        df["remarks"] = ""
        return df
    except:
        return get_empty_students_df()


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
        st.session_state.students_df = load_static_students()

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

    # New for features
    if 'history_loads' not in st.session_state:
        st.session_state.history_loads = []  # list of {'week': int, 'loads': dict name->load}

    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'

    if 'high_contrast' not in st.session_state:
        st.session_state.high_contrast = False

    if 'hc_previous_theme' not in st.session_state:
        st.session_state.hc_previous_theme = None

    if 'ui_language' not in st.session_state:
        st.session_state.ui_language = 'zh'  # 'zh' or 'en', but UI primarily Chinese per requirements

    if 'selected_students_for_bulk' not in st.session_state:
        st.session_state.selected_students_for_bulk = []

    # For roster version history
    if 'roster_versions' not in st.session_state:
        st.session_state.roster_versions = []  # list of {'version': int, 'timestamp': str, 'roster_df': dict, 'report_df': dict}

    # For semester service hours (calculate from roster, each duty ~1-1.5 hours based on weight)
    if 'semester_hours' not in st.session_state:
        st.session_state.semester_hours = {}  # name -> total hours

    # For search/filter
    if 'student_search' not in st.session_state:
        st.session_state.student_search = ""

    if 'roster_search' not in st.session_state:
        st.session_state.roster_search = ""

    # Ensure history_loads initialized (for trends)
    if 'history_loads' not in st.session_state:
        st.session_state.history_loads = []

    # Backup system state
    if 'last_backup_time' not in st.session_state:
        st.session_state.last_backup_time = None

    if 'backup_reminder' not in st.session_state:
        st.session_state.backup_reminder = False

    if 'backup_history' not in st.session_state:
        st.session_state.backup_history = []  # list of {'timestamp': str, 'json': str, 'version': int} for multi-version

    if 'adjustment_log' not in st.session_state:
        st.session_state.adjustment_log = []
