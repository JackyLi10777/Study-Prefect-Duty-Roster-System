# roster/utils/importers.py
"""
Roster import engines (traditional + AI smart).

Extracted from original utils.py.
All content and behavior kept identical.

AI backend: DeepSeek (deepseek-chat, OpenAI-compatible API).
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
    PROJECT_FULL_NAME, VERSION
)
from roster.data import get_demo_dataframe, get_sample_format_dataframe

# ====================== Traditional Import ======================
def process_roster_import(uploaded_file):
    """Traditional format Excel/CSV import (backup option)."""
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Smart column mapping
        mapping = {
            '姓名': 'name', 'name': 'name', 'Prefect Name': 'name', '学生姓名': 'name',
            '年级': 'form', 'form': 'form', 'Form': 'form',
            '班级': 'class', 'class': 'class', 'Class': 'class',
            '职级': 'role', 'role': 'role', 'Role': 'role',
            '学年固定总值班': 'fixed_general_duty', 'fixed_general_duty': 'fixed_general_duty',
            '可用日子': 'available', 'available': 'available',
            '历史累计(次)': 'history_duties', 'history_duties': 'history_duties',
            '历史动态(点)': 'history_weight', 'history_weight': 'history_weight',
            '备注': 'remarks', 'remarks': 'remarks',
            'needs_mentoring': 'needs_mentoring', 'Needs Mentoring': 'needs_mentoring'
        }

        df = df.rename(columns=lambda x: mapping.get(str(x).strip(), str(x).strip()))

        required_cols = ["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "needs_mentoring", "remarks"]
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
                elif col == "needs_mentoring":
                    df[col] = False
                else:
                    df[col] = ""

        df = df[required_cols].copy()
        df["name"] = df["name"].astype(str).str.strip()
        df = df[(df["name"] != "") & (df["name"] != "nan")]
        df["history_duties"] = pd.to_numeric(df["history_duties"], errors='coerce').fillna(0).astype(int)
        df["history_weight"] = pd.to_numeric(df["history_weight"], errors='coerce').fillna(0.0)

        st.session_state.students_df = df.reset_index(drop=True)
        st.sidebar.success(f"✅ 传统格式导入成功！共 {len(df)} 位领袖生")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"❌ 传统导入失败: {str(e)}")


# ====================== AI Smart Import ======================
def smart_process_roster_import(uploaded_file):
    """AI smart auto-matching column import (DeepSeek, supports any format)."""
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        if df.empty or len(df.columns) < 2:
            st.error("❌ 文件为空或格式不正确")
            return

        from roster.ai.parser import get_column_mapping_from_ai
        mapping = get_column_mapping_from_ai(df)

        rename_dict = {v: k for k, v in mapping.items() if v in df.columns}
        df = df.rename(columns=rename_dict)

        required_cols = ["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "needs_mentoring", "remarks"]
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
                elif col == "needs_mentoring":
                    df[col] = False
                else:
                    df[col] = ""

        df["name"] = df["name"].astype(str).str.strip()
        df = df[df["name"].notna() & (df["name"] != "")]
        df["history_duties"] = pd.to_numeric(df["history_duties"], errors="coerce").fillna(0).astype(int)
        df["history_weight"] = pd.to_numeric(df["history_weight"], errors="coerce").fillna(0.0)

        st.session_state.students_df = df[required_cols].reset_index(drop=True)
        st.success(f"✅ AI 智能导入成功！已处理 {len(df)} 位领袖生（自动匹配栏位）")
        st.rerun()

    except Exception as e:
        st.error(f"❌ AI 智能导入失败: {str(e)}")
        st.info("💡 提示：若 AI 无法解析，请改用「传统格式导入」")
