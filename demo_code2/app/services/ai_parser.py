"""
AI Smart Import Service for the Sing Yin Study Prefect Duty Roster System.

Parses natural-language remarks (Chinese) in the prefect records using
DeepSeek V4 Flash to auto-populate fixed_general_duty and available fields.

API Key: Set environment variable SY_DEEPSEEK_KEY with your DeepSeek API key.
"""

import json
import os
from typing import Dict, List, Optional

from openai import OpenAI

DEEPSEEK_MODEL = "DeepSeek-V4-Flash"
DEEPSEEK_KEY = os.environ.get("SY_DEEPSEEK_KEY", "")


REMARKS_SYSTEM_PROMPT = """
You are a professional scheduling assistant for the Sing Yin Secondary School Study Prefect Team.
Parse the Chinese "remarks" content and update the following fields intelligently.
Output ONLY pure JSON, no extra text, explanation, or markdown.

Rules for parsing:
- "fixed_general_duty": year-long fixed duty day -> MONDAY / TUESDAY / WEDNESDAY / THURSDAY / FRIDAY / NONE
- "available": comma-separated available days -> e.g. "MONDAY,WEDNESDAY,FRIDAY"
- "role": prefect role -> "Study Prefect" or "Assistant Head Study Prefect"

Keywords to watch for:
- "Room302" or "Room 302" -> available days unchanged, fixed duty may apply
- "固定星期一" / "固定星期三" -> fixed_general_duty
- "只可星期一三五" / "只有星期一和星期三" -> available
- "Assistant Head" / "AHP" / "助理首席" -> role
- "師徒" / "新任" / "F.3" -> role stays, mentoring flag

Always output only JSON. Example:
{"fixed_general_duty": "MONDAY", "available": "MONDAY,WEDNESDAY,FRIDAY", "role": "Study Prefect"}
"""


def _get_client() -> Optional[OpenAI]:
    """Initialize DeepSeek client (OpenAI-compatible). Returns None if key missing."""
    if not DEEPSEEK_KEY:
        return None
    return OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")


def _call_deepseek(system_prompt: str, user_prompt: str,
                   temperature: float = 0.1, max_tokens: int = 500) -> str:
    """Call DeepSeek API and return response text. Returns empty string on failure."""
    client = _get_client()
    if client is None:
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
    except Exception:
        return ""


def parse_single_remark(remarks: str) -> dict:
    """Parse a single remarks string into structured fields.

    Args:
        remarks: Chinese natural-language text from the remarks column.

    Returns:
        Dict with keys that were successfully parsed (fixed_general_duty, available, role).
        Returns empty dict if remarks is blank or API is unavailable.
    """
    remarks = str(remarks).strip()
    if not remarks or remarks.lower() in ("nan", "", "none"):
        return {}

    response = _call_deepseek(
        system_prompt=REMARKS_SYSTEM_PROMPT,
        user_prompt=f"Remarks: {remarks}",
        temperature=0.1,
        max_tokens=500,
    )
    if not response:
        return {}

    try:
        json_text = response
        if json_text.startswith("```json"):
            json_text = json_text.split("```json")[1].split("```")[0].strip()
        elif json_text.startswith("```"):
            json_text = json_text.split("```")[1].strip()
        return json.loads(json_text)
    except (json.JSONDecodeError, IndexError):
        return {}


def parse_all_remarks(prefects: list) -> List[dict]:
    """Parse remarks for all prefects and return changes.

    Args:
        prefects: List of Prefect objects or dicts.

    Returns:
        List of dicts with: {name, remarks, changes, original}
        Only includes prefects where changes were detected.
    """
    changes = []
    for p in prefects:
        name = p.name if hasattr(p, "name") else p.get("name", "")
        remarks = p.remarks if hasattr(p, "remarks") else p.get("remarks", "")
        if not remarks or str(remarks).strip().lower() in ("nan", "", "none"):
            continue

        parsed = parse_single_remark(str(remarks))
        if not parsed:
            continue

        change = {
            "name": name,
            "remarks": str(remarks),
            "changes": {},
            "original": {},
        }
        for field in ["fixed_general_duty", "available", "role"]:
            if field in parsed and parsed[field]:
                new_val = str(parsed[field]).upper()
                if field == "available":
                    new_val = [d.strip().upper() for d in new_val.split(",") if d.strip()]
                # Get original value
                if field == "available":
                    orig = p.available if hasattr(p, "available") else p.get("available", [])
                    orig = [d.name if hasattr(d, "name") else str(d) for d in orig] if orig else []
                elif field == "fixed_general_duty":
                    fd = getattr(p, "fixed_general_duty", None)
                    orig = fd if fd and fd != "NONE" else None
                else:
                    orig = p.role.name if hasattr(p, "role") and hasattr(p.role, "name") else str(getattr(p, "role", ""))
                if str(new_val) != str(orig):
                    change["changes"][field] = new_val
                    change["original"][field] = orig
        if change["changes"]:
            changes.append(change)
    return changes


def is_available() -> bool:
    """Check if the DeepSeek API is configured."""
    return bool(DEEPSEEK_KEY) and _get_client() is not None

def status_detail() -> dict:
    """Return detailed DeepSeek connection status with actionable guidance."""
    if not DEEPSEEK_KEY:
        return {"level":"warning","label":"DeepSeek: Not Configured","detail":"Set SY_DEEPSEEK_KEY in .env file","action":"Get a free API key at platform.deepseek.com. See SETUP.md Step 5."}
    try:
        client = _get_client()
        if client is None:
            return {"level":"warning","label":"DeepSeek: Auth Failed","detail":"Could not initialize DeepSeek client","action":"Verify your API key is valid"}
        return {"level":"online","label":"DeepSeek: Ready","detail":"AI features (parse remarks, column mapping) are available","action":""}
    except Exception as e:
        return {"level":"warning","label":"DeepSeek: Error","detail":str(e)[:80],"action":"Check your API key at platform.deepseek.com"}


def get_column_mapping_from_ai(sample_text: str) -> dict:
    """Use DeepSeek to map CSV/Excel columns to standard field names."""
    if not is_available():
        return {}
    user_prompt = (
        "Analyze this table and map columns to standard fields. "
        "Standard fields: name, name_zh, form, class_name, role, "
        "fixed_general_duty, available, history_weight, remarks. "
        "Output ONLY pure JSON like {\"name\": \"column_name\", ...}\n\n"
        + sample_text
    )
    response = _call_deepseek(
        system_prompt="You are a professional data mapping assistant.",
        user_prompt=user_prompt, temperature=0.0, max_tokens=1000,
    )
    if not response:
        return {}
    try:
        import json
        json_text = response
        if json_text.startswith("```json"):
            json_text = json_text.split("```json")[1].split("```")[0].strip()
        elif json_text.startswith("```"):
            json_text = json_text.split("```")[1].strip()
        return json.loads(json_text)
    except (json.JSONDecodeError, IndexError):
        return {}



def get_column_mapping_with_confidence(sample_text: str) -> dict:
    """Use DeepSeek to map CSV columns, returning dict with confidence info.

    Calls the existing get_column_mapping_from_ai() and wraps results.
    Returns {} if AI is unavailable or fails.
    All matched columns are marked with confidence='ai'.
    """
    raw_mapping = get_column_mapping_from_ai(sample_text)
    return raw_mapping  # Standard {std_field: actual_col} dict
