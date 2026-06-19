# roster/data/validators.py
"""
Student DataFrame validation.

Extracted from original data.py.
Behavior unchanged.
"""

import pandas as pd


def validate_students_dataframe(df: pd.DataFrame) -> tuple[bool, str]:
    """
    嚴格驗證學生名冊資料完整性（防止後續排班錯誤）

    必須在任何排班前呼叫，確保 name/form/role 等必要欄位存在，
    否則 generate_roster 等函數的行為未定義。
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
