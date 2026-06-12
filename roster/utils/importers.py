# roster/utils/importers.py
"""
Roster import engines (traditional + AI smart).

Extracted from original utils.py.
All content and behavior kept identical.

Note: dynamic AI import updated to package path for cleanliness.
Gemini setup moved here as it supports the smart importer.
"""

import streamlit as st
import pandas as pd
import io
import json
import datetime
import base64
import random

from roster.config import (
    DAYS, NASA_COLORS, get_role_style,
    PROJECT_FULL_NAME, VERSION, GEMINI_MODEL
)
from roster.data import get_demo_dataframe, get_sample_format_dataframe

# ====================== Gemini 配置（AI 導入後備使用） ======================
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    import google.generativeai as genai
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(GEMINI_MODEL)
else:
    model = None

# ====================== 名冊導入引擎（傳統格式） ======================
def process_roster_import(uploaded_file):
    """傳統格式 Excel/CSV 導入（後備方案）"""
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # 欄位智能映射
        mapping = {
            '姓名': 'name', 'name': 'name', 'Prefect Name': 'name', '學生姓名': 'name',
            '年級': 'form', 'form': 'form', 'Form': 'form',
            '班別': 'class', 'class': 'class', 'Class': 'class',
            '職級': 'role', 'role': 'role', 'Role': 'role',
            '學年固定總值班': 'fixed_general_duty', 'fixed_general_duty': 'fixed_general_duty',
            '可用日子': 'available', 'available': 'available',
            '歷史累計(次)': 'history_duties', 'history_duties': 'history_duties',
            '歷史動態(點)': 'history_weight', 'history_weight': 'history_weight',
            '備註': 'remarks', 'remarks': 'remarks'
        }

        df = df.rename(columns=lambda x: mapping.get(str(x).strip(), str(x).strip()))

        required_cols = ["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "remarks"]
        for col in required_cols:
            if col not in df.columns:
                if col == "fixed_general_duty":
                    df[col] = "NONE"
                elif col == "available":
                    df[col] = "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"
                elif col == "history_duties":
                    df[col] = 0
                elif col == "history_weight":
                    df[col] = 0.0
                else:
                    df[col] = ""

        df = df[required_cols].copy()
        df["name"] = df["name"].astype(str).str.strip()
        df = df[(df["name"] != "") & (df["name"] != "nan")]
        df["history_duties"] = pd.to_numeric(df["history_duties"], errors='coerce').fillna(0).astype(int)
        df["history_weight"] = pd.to_numeric(df["history_weight"], errors='coerce').fillna(0.0)

        st.session_state.students_df = df.reset_index(drop=True)
        st.sidebar.success(f"🎉 傳統格式導入成功！共 {len(df)} 位領袖生")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"❌ 傳統導入失敗: {str(e)}")


# ====================== AI 智能名冊導入 ======================
def smart_process_roster_import(uploaded_file):
    """AI 智能自動匹配欄位導入（Gemini 支援任意格式）"""
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        if df.empty or len(df.columns) < 2:
            st.error("❌ 檔案為空或格式不正確")
            return

        from roster.ai.parser import get_column_mapping_from_ai  # updated to new package path
        mapping = get_column_mapping_from_ai(df)

        rename_dict = {v: k for k, v in mapping.items() if v in df.columns}
        df = df.rename(columns=rename_dict)

        required_cols = ["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "remarks"]
        for col in required_cols:
            if col not in df.columns:
                if col == "fixed_general_duty":
                    df[col] = "NONE"
                elif col == "available":
                    df[col] = "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"
                elif col == "history_duties":
                    df[col] = 0
                elif col == "history_weight":
                    df[col] = 0.0
                else:
                    df[col] = ""

        df["name"] = df["name"].astype(str).str.strip()
        df = df[df["name"].notna() & (df["name"] != "")]
        df["history_duties"] = pd.to_numeric(df["history_duties"], errors="coerce").fillna(0).astype(int)
        df["history_weight"] = pd.to_numeric(df["history_weight"], errors="coerce").fillna(0.0)

        st.session_state.students_df = df[required_cols].reset_index(drop=True)
        st.success(f"🎉 AI 智能導入成功！已處理 {len(df)} 位領袖生（自動匹配欄位）")
        st.rerun()

    except Exception as e:
        st.error(f"❌ AI 智能導入失敗: {str(e)}")
        st.info("💡 提示：若 AI 無法解析，請改用「傳統格式導入」")
