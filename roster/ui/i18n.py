"""
roster/ui/i18n.py

Centralized language (i18n) management and the canonical _t translator.

This module is the single source for:
- Language detection and switching (ui_language session state).
- The public _t(zh, en) interface (for migration compatibility).
- Future support for key-based lookup (delegates to messages.get_text).

All language decisions remain strictly in the display layer.
Business/core modules must never import language logic for decisions.

Paired with:
- roster/ui/messages.py for the actual text registry and safe formatting.
- roster/data/state.py for initialization of 'ui_language'.

Safe patterns enforced here and in messages.py:
- Prefer get_text("key") for new strings.
- For dynamic: prefix = get_text("key"); result = f"{prefix} {var}"
- Never put .format(...) with variable assignment inside an f-string literal.

Student names and role data are never translated (they remain Chinese by design).
"""

import streamlit as st

# Re-export the implementation from the messages module for a single public API
from .messages import _t as _legacy_t, get_text

def _t(zh_text: str, en_text: str) -> str:
    """
    Canonical translator for the application.

    During the transition period this delegates to the legacy implementation
    in messages.py (which still accepts raw zh/en strings).

    New code should migrate to:
        from roster.ui.i18n import get_text
        text = get_text("some_key", var=val)

    This function will eventually become a thin wrapper or be deprecated.
    """
    return _legacy_t(zh_text, en_text)


def get_current_language() -> str:
    """Return current UI language ('zh' or 'en')."""
    return st.session_state.get("ui_language", "zh")


def is_english() -> bool:
    """Convenience helper."""
    return get_current_language() == "en"


def set_language(lang: str):
    """Set language (used by the language selector)."""
    if lang in ("zh", "en"):
        st.session_state.ui_language = lang


# Future extension point: register additional languages, load from JSON, etc.
# For now the MESSAGES in messages.py is the source of truth.

print("✅ roster/ui/i18n.py loaded - canonical language management (display layer only)")