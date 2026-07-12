"""
Hard rules for the i18n layer.
These rules are enforced globally and must never be bypassed.
"""


def prefect_display_name(prefect: dict) -> str:
    """Return the display name for a prefect.

    HARD RULE: Always returns the Chinese name, regardless of language mode.
    This is non-negotiable per school policy.

    Args:
        prefect: A dict or object with 'name_zh' and 'name' fields.

    Returns:
        The Chinese name if available, otherwise English name as fallback.
    """
    if hasattr(prefect, "name_zh"):
        zh = prefect.name_zh
        if zh and zh.strip():
            return zh
    elif isinstance(prefect, dict):
        zh = prefect.get("name_zh", "").strip()
        if zh:
            return zh
    # Fallback — should not happen if data is properly maintained
    if hasattr(prefect, "name"):
        return prefect.name
    return prefect.get("name", "Unknown") if isinstance(prefect, dict) else "Unknown"


def scripture_for_language(verse: dict, language: str = "zh") -> dict:
    """Return the appropriate scripture content for the given language.

    HARD RULE: Chinese mode returns Chinese text + Chinese reference.
    English mode returns English text + English reference.

    Args:
        verse: Dict with 'text', 'text_zh', 'ref', 'ref_zh' keys.
        language: 'zh' or 'en'.

    Returns:
        Dict with 'text' and 'ref' keys in the appropriate language.
    """
    if language == "zh":
        return {
            "text": verse.get("text_zh", verse.get("text", "")),
            "ref": verse.get("ref_zh", verse.get("ref", "")),
        }
    return {
        "text": verse.get("text", verse.get("text_zh", "")),
        "ref": verse.get("ref", verse.get("ref_zh", "")),
    }
