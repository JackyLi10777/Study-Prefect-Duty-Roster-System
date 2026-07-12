"""roster.ai - AI parsing layer (Gemini integration).

Re-exports the AI parser functions.
The module handles remarks parsing and column mapping for imports.
Must respect exact role strings and day names per AGENTS.md.
"""

from .parser import (
    ai_parse_remarks,
    get_column_mapping_from_ai,
    REMARKS_SYSTEM_PROMPT,
    IMPORT_MAPPING_PROMPT,
)
