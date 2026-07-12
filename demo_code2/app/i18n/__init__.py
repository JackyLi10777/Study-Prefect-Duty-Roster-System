"""app/i18n/ — Centralized internationalization. Re-exports for backward compatibility."""
from .helpers import t, lang, is_zh
from .rules import prefect_display_name, scripture_for_language
from .provider import set_language, toggle_language
