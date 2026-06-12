# roster/data/demo.py
"""
Demo and sample data for the roster system.

Extracted from original data.py during modularization.
All content and behavior kept identical per the migration plan.
"""

import pandas as pd
from roster.config import DAYS, DEFAULT_GLOBAL_LOAD_MULTIPLIER


def get_demo_dataframe() -> pd.DataFrame:
    """
    官方示範名冊（可直接一鍵載入測試使用）

    包含多位 Assistant Head Study Prefect 與普通 Study Prefect，
    預設 history_weight 與 remarks 用來示範公平演算法與 AI 解析。
    完全符合 AGENTS.md §1 學生規則與 §5 驗證需求。
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
