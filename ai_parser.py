# ai_parser.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
AI 解析模組 - Gemini 智能解析 Remarks + 欄位映射

作者：Head Study Prefect 26-27 LI Chuangjie Jacky
版本：v2.3 Final（已徹底解決「一直解析中...」卡住問題）
"""

import streamlit as st
import pandas as pd
import json
import re

from config import GEMINI_MODEL

# ====================== Gemini 配置 ======================
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    import google.generativeai as genai
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(GEMINI_MODEL)
else:
    model = None


# ====================== AI 系統提示 - Remarks 解析 ======================
REMARKS_SYSTEM_PROMPT = """
你是一位 Sing Yin Secondary School Study Prefect Team 的專業排班助理。
請根據「備註 (remarks)」欄位的中文內容，智能解析並更新以下欄位。
只輸出純 JSON，不要任何額外文字、解釋或 markdown。

可解析的欄位規則：
- "fixed_general_duty": 學年固定總值班 → MONDAY / TUESDAY / WEDNESDAY / THURSDAY / FRIDAY / NONE
- "available": 可用日子 → 用逗號分隔，例如 "MONDAY,WEDNESDAY,FRIDAY"
- "role": 職級 → "Study Prefect" 或 "Assistant Head Study Prefect"

如果備註中提到「老帶新」「新任」「F.3」「Assistant Head」「固定值班」「Room302 優先」等關鍵字，請合理判斷並更新。

請嚴格遵守，只輸出 JSON。
"""


def ai_parse_remarks(students_df: pd.DataFrame) -> pd.DataFrame:
    """
    使用 Gemini AI 解析 Remarks 欄位，並自動更新 fixed_general_duty、available、role
    已徹底解決「一直解析中...」卡住問題：
    - 使用 finally 確保 progress_bar 一定關閉
    - 清晰的錯誤處理與使用者提示
    - 單筆失敗不影響整體流程
    """
    if model is None:
        st.error("❌ Gemini API 未設定，請在 .streamlit/secrets.toml 加入 GEMINI_API_KEY")
        return students_df

    if students_df.empty:
        st.warning("名冊為空，無法進行 AI 解析")
        return students_df

    updated_df = students_df.copy()
    progress_bar = st.progress(0)
    total_rows = len(students_df)
    success_count = 0
    error_count = 0

    try:
        for idx, row in students_df.iterrows():
            remarks = str(row.get("remarks", "")).strip()
            if not remarks or remarks.lower() in ["nan", "", "none"]:
                progress_bar.progress((idx + 1) / total_rows)
                continue

            try:
                prompt = f"{REMARKS_SYSTEM_PROMPT}\n\n備註內容：{remarks}"
                response = model.generate_content(prompt)
                json_text = response.text.strip()

                # 清理可能的 markdown 包裝
                if json_text.startswith("```json"):
                    json_text = json_text.split("```json")[1].split("```")[0].strip()
                elif json_text.startswith("```"):
                    json_text = json_text.split("```")[1].strip()

                parsed = json.loads(json_text)

                # 更新欄位
                updated = False
                if "fixed_general_duty" in parsed and parsed["fixed_general_duty"]:
                    updated_df.at[idx, "fixed_general_duty"] = str(parsed["fixed_general_duty"]).upper()
                    updated = True
                if "available" in parsed and parsed["available"]:
                    updated_df.at[idx, "available"] = str(parsed["available"]).upper()
                    updated = True
                if "role" in parsed and parsed["role"]:
                    updated_df.at[idx, "role"] = str(parsed["role"])
                    updated = True

                if updated:
                    success_count += 1

            except Exception as e:
                error_count += 1
                # 單筆失敗不中斷整體流程
                st.warning(f"第 {idx+1} 筆備註解析失敗（已跳過）: {str(e)[:80]}")

            # 更新進度條
            progress_bar.progress((idx + 1) / total_rows)

    finally:
        # 無論成功或失敗，一定關閉進度條
        progress_bar.empty()

    # 最終提示
    if success_count > 0:
        st.success(f"✅ AI 已成功解析並更新 {success_count} 筆資料")
    if error_count > 0:
        st.info(f"ℹ️ 有 {error_count} 筆備註無法解析，已自動跳過")

    return updated_df


# ====================== AI 系統提示 - 欄位映射 ======================
IMPORT_MAPPING_PROMPT = """
請分析以下 Excel/CSV 表格內容，將欄位自動對應到標準欄位名稱。
只需輸出純 JSON，不要任何額外文字或說明。

標準欄位定義：
- "name": 姓名
- "form": 年級 (F.3、F.4、F.5、F.6)
- "class": 班別
- "role": 職級 (Study Prefect 或 Assistant Head Study Prefect)
- "fixed_general_duty": 學年固定總值班
- "available": 可用日子
- "history_duties": 歷史累計次數
- "history_weight": 歷史累計點數
- "remarks": 備註

表格前8行內容：
{table_sample}

請輸出以下格式的 JSON：
{
  "name": "實際欄位名稱",
  "form": "實際欄位名稱",
  ...
}
"""


def get_column_mapping_from_ai(df: pd.DataFrame) -> dict:
    """AI 智能欄位映射（供 smart_process_roster_import 使用）"""
    if model is None:
        raise Exception("Gemini API 未設定")

    sample_text = df.head(8).to_string(index=False)
    prompt = IMPORT_MAPPING_PROMPT.format(table_sample=sample_text)

    response = model.generate_content(prompt)
    json_text = response.text.strip()

    if json_text.startswith("```json"):
        json_text = json_text.split("```json")[1].split("```")[0].strip()
    elif json_text.startswith("```"):
        json_text = json_text.split("```")[1].strip()

    return json.loads(json_text)


print("✅ ai_parser.py 已載入完成 - AI 解析引擎已強化（永遠不會卡在「解析中...」）")