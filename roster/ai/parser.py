# roster/ai/parser.py
"""
Sing Yin Study Prefect Duty Roster System
AI Parser - DeepSeek smart parsing for Remarks + column mapping

Author: Head Study Prefect 26-27 LI Chuangjie Jacky
Version: v2.4 (migrated from Gemini to DeepSeek)
"""

import streamlit as st
import pandas as pd
import json
import re

from openai import OpenAI

# ====================== DeepSeek config ======================
DEEPSEEK_MODEL = "DeepSeek-V4-Flash"  # upgraded from deprecated deepseek-chat


def _get_deepseek_client() -> OpenAI:
    """Initialize and return a DeepSeek client (OpenAI-compatible)."""
    api_key = st.secrets.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def _call_deepseek(system_prompt: str, user_prompt: str, temperature: float = 0.1, max_tokens: int = 2000) -> str:
    """Call DeepSeek chat API and return the response text. Returns empty string on failure."""
    client = _get_deepseek_client()
    if client is None:
        st.error("[DeepSeek] API Key 未配置，請在 Streamlit Cloud Secrets 中添加 DEEPSEEK_API_KEY")
        return ""

    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"[DeepSeek] API 調用失败：{str(e)}")
        return ""


# ====================== AI System Prompt - Remarks parsing ======================
REMARKS_SYSTEM_PROMPT = """
你是一位 Sing Yin Secondary School Study Prefect Team 的專業排班助理。
請根據「備註」(remarks) 欄位的中文內容，智能解析並更新以下欄位。
只輸出純 JSON，不要任何額外文字、解釋或 markdown。

可解析的欄位規則：
- "fixed_general_duty": 學年固定總值班 → MONDAY / TUESDAY / WEDNESDAY / THURSDAY / FRIDAY / NONE
- "available": 可用日子 → 用逗號分隔，例如 "MONDAY,WEDNESDAY,FRIDAY"
- "role": 職級 → "Study Prefect" 或 "Assistant 首席導學風紀"

如果備註中提到「師徒」「新任」「F.3」「Assistant Head」「固定值班」「Room302 優先」等關鍵字，請合理判斷並更新。

請嚴格遵守，只輸出 JSON。
"""


def ai_parse_remarks(students_df: pd.DataFrame) -> pd.DataFrame:
    """
    使用 DeepSeek AI 解析 Remarks 欄位，並自動更新 fixed_general_duty、available、role。

    - 使用 finally 確保 progress_bar 一定關閉
    - 清晰的錯誤處理與使用者提示
    - 單筆失敗不影響整體流程
    """
    if students_df.empty:
        st.warning("名冊為空，無法進行 AI 解析")
        return students_df

    client = _get_deepseek_client()
    if client is None:
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
                response_text = _call_deepseek(
                    system_prompt=REMARKS_SYSTEM_PROMPT,
                    user_prompt=f"備註內容：{remarks}",
                    temperature=0.1,
                    max_tokens=500,
                )

                if not response_text:
                    error_count += 1
                    progress_bar.progress((idx + 1) / total_rows)
                    continue

                # Clean possible markdown wrapping
                json_text = response_text
                if json_text.startswith("```json"):
                    json_text = json_text.split("```json")[1].split("```")[0].strip()
                elif json_text.startswith("```"):
                    json_text = json_text.split("```")[1].strip()

                parsed = json.loads(json_text)

                # Update fields
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
                # Single failure does not interrupt the overall flow
                st.warning(f"第 {idx+1} 筆備註解析失敗（已跳過）: {str(e)[:80]}")

            # Update progress
            progress_bar.progress((idx + 1) / total_rows)

    finally:
        # Always close the progress bar regardless of success or failure
        progress_bar.empty()

    # Final summary
    if success_count > 0:
        st.success(f"✅ AI 已成功解析並更新 {success_count} 筆資料")
    if error_count > 0:
        st.info(f"ℹ️ 有 {error_count} 筆備註無法解析，已自動跳過")

    return updated_df


# ====================== AI System Prompt - Column Mapping ======================
IMPORT_MAPPING_PROMPT = """
請分析以下 Excel/CSV 表格內容，將欄位自動對應到標準欄位名称。
只需輸出纯 JSON，不要任何额外文字或說明。

標準欄位定義：
- "name": 姓名
- "form": 年级 (F.3、F.4、F.5、F.6)
- "class": 班级
- "role": 职级 (Study Prefect 或 Assistant 首席導學風紀)
- "fixed_general_duty": 學年固定總值班
- "available": 可用日子
- "history_duties": 歷史累計次數
- "history_weight": 歷史累計點數
- "remarks": 備註

表格前幾行內容：
{table_sample}

請輸出以下格式的 JSON：
{{
  "name": "實際欄位名称",
  "form": "實際欄位名称",
  ...
}}
"""


def get_column_mapping_from_ai(df: pd.DataFrame) -> dict:
    """AI smart column mapping (used by smart_process_roster_import)."""
    client = _get_deepseek_client()
    if client is None:
        raise Exception("DeepSeek API 未配置")

    sample_text = df.head(8).to_string(index=False)
    prompt = IMPORT_MAPPING_PROMPT.format(table_sample=sample_text)

    response_text = _call_deepseek(
        system_prompt="你是一個專業的數据映射助手，能準确識別表格欄位。",
        user_prompt=prompt,
        temperature=0.0,
        max_tokens=1000,
    )

    if not response_text:
        raise Exception("DeepSeek 返回空響應")

    json_text = response_text
    if json_text.startswith("```json"):
        json_text = json_text.split("```json")[1].split("```")[0].strip()
    elif json_text.startswith("```"):
        json_text = json_text.split("```")[1].strip()

    return json.loads(json_text)
