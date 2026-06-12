# data.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
數據層模組 - 示範名冊、格式範例、Session State 初始化與驗證

作者：Head Study Prefect 26-27 LI Chuangjie Jacky
版本：v2.3 Final（完整支援 6 行多槽位排班、全局負荷滑桿、Streamlit Cloud 休眠防護）
"""

import pandas as pd
import streamlit as st
from config import ROWS_ROSTER, DAYS, DEFAULT_GLOBAL_LOAD_MULTIPLIER

def get_demo_dataframe() -> pd.DataFrame:
    """
    官方示範名冊（可直接一鍵載入測試使用）
    包含 Assistant Head Study Prefect 與普通 Study Prefect
    支援歷史負荷與備註解析，符合所有學校業務規則
    """
    demo_data = [
        {
            "name": "李創杰",
            "form": "F.5",
            "class": "5D",
            "role": "Assistant Head Study Prefect",
            "fixed_general_duty": "NONE",
            "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 12,
            "history_weight": 18.5,
            "remarks": "老帶新，F.3 優先，領導核心"
        },
        {
            "name": "陳子軒",
            "form": "F.5",
            "class": "5A",
            "role": "Study Prefect",
            "fixed_general_duty": "MONDAY",
            "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 9,
            "history_weight": 13.5,
            "remarks": ""
        },
        {
            "name": "黃家樂",
            "form": "F.4",
            "class": "4B",
            "role": "Study Prefect",
            "fixed_general_duty": "NONE",
            "available": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 7,
            "history_weight": 10.0,
            "remarks": "Room302 經驗豐富"
        },
        {
            "name": "張凱傑",
            "form": "F.4",
            "class": "4A",
            "role": "Study Prefect",
            "fixed_general_duty": "NONE",
            "available": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 9,
            "history_weight": 13.5,
            "remarks": ""
        },
        {
            "name": "林俊賢",
            "form": "F.3",
            "class": "3C",
            "role": "Study Prefect",
            "fixed_general_duty": "NONE",
            "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 4,
            "history_weight": 5.5,
            "remarks": "新任，老帶新"
        },
        {
            "name": "吳柏樂",
            "form": "F.3",
            "class": "3A",
            "role": "Study Prefect",
            "fixed_general_duty": "NONE",
            "available": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 3,
            "history_weight": 4.0,
            "remarks": ""
        },
        {
            "name": "劉子浩",
            "form": "F.5",
            "class": "5B",
            "role": "Assistant Head Study Prefect",
            "fixed_general_duty": "WEDNESDAY",
            "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 15,
            "history_weight": 22.0,
            "remarks": "固定星期三值班，領導經驗豐富"
        },
        {
            "name": "歐陽浚鋒",
            "form": "F.4",
            "class": "4C",
            "role": "Assistant Head Study Prefect",
            "fixed_general_duty": "NONE",
            "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 8,
            "history_weight": 12.0,
            "remarks": ""
        },
        {
            "name": "許舜喬",
            "form": "F.3",
            "class": "3C",
            "role": "Assistant Head Study Prefect",
            "fixed_general_duty": "NONE",
            "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 5,
            "history_weight": 7.5,
            "remarks": "新任 Assistant Head"
        },
        {
            "name": "何梓皓",
            "form": "F.3",
            "class": "3B",
            "role": "Assistant Head Study Prefect",
            "fixed_general_duty": "NONE",
            "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 4,
            "history_weight": 6.0,
            "remarks": ""
        },
        {
            "name": "何俊霆",
            "form": "F.3",
            "class": "3B",
            "role": "Study Prefect",
            "fixed_general_duty": "NONE",
            "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 3,
            "history_weight": 4.5,
            "remarks": ""
        },
    ]
    df = pd.DataFrame(demo_data)
    df["history_duties"] = pd.to_numeric(df["history_duties"], errors='coerce').fillna(0).astype(int)
    df["history_weight"] = pd.to_numeric(df["history_weight"], errors='coerce').fillna(0.0)
    return df


def get_sample_format_dataframe() -> pd.DataFrame:
    """
    名冊格式範例（供使用者下載參考，用於傳統格式導入）
    """
    sample_data = [
        {
            "姓名": "李創杰",
            "年級": "F.5",
            "班別": "5D",
            "職級": "Assistant Head Study Prefect",
            "學年固定總值班": "NONE",
            "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "歷史累計(次)": 12,
            "歷史動態(點)": 18.5,
            "備註": "老帶新，F.3 優先，領導核心"
        },
        {
            "姓名": "陳子軒",
            "年級": "F.5",
            "班別": "5A",
            "職級": "Study Prefect",
            "學年固定總值班": "MONDAY",
            "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "歷史累計(次)": 9,
            "歷史動態(點)": 13.5,
            "備註": ""
        },
        {
            "姓名": "黃家樂",
            "年級": "F.4",
            "班別": "4B",
            "職級": "Study Prefect",
            "學年固定總值班": "NONE",
            "可用日子": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "歷史累計(次)": 7,
            "歷史動態(點)": 10.0,
            "備註": "Room302 經驗豐富"
        },
        {
            "姓名": "張凱傑",
            "年級": "F.4",
            "班別": "4A",
            "職級": "Study Prefect",
            "學年固定總值班": "NONE",
            "可用日子": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "歷史累計(次)": 9,
            "歷史動態(點)": 13.5,
            "備註": ""
        },
        {
            "姓名": "林俊賢",
            "年級": "F.3",
            "班別": "3C",
            "職級": "Study Prefect",
            "學年固定總值班": "NONE",
            "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "歷史累計(次)": 4,
            "歷史動態(點)": 5.5,
            "備註": "新任，老帶新"
        },
    ]
    return pd.DataFrame(sample_data)


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
    必須放在 app.py 最前面呼叫
    """
    if 'students_df' not in st.session_state:
        st.session_state.students_df = get_empty_students_df()

    if 'roster_df' not in st.session_state:
        st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

    if 'manual_weights' not in st.session_state:
        st.session_state.manual_weights = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna(0.0)

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


def validate_students_dataframe(df: pd.DataFrame) -> tuple[bool, str]:
    """
    嚴格驗證學生名冊資料完整性（防止後續排班錯誤）
    """
    if df.empty or len(df) == 0:
        return False, "名冊為空，請先載入學生資料"

    required_cols = ["name", "form", "role"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        return False, f"缺少必要欄位：{missing}"

    if df["name"].isna().any() or (df["name"].astype(str).str.strip() == "").any():
        return False, "存在空白姓名，請修正後再繼續"

    return True, f"✅ 驗證通過，共 {len(df)} 位領袖生"


print("✅ data.py 已載入完成 - 數據初始化與驗證模組就緒")