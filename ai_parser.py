# ai_parser.py (root shim / compatibility layer)
"""
Temporary root-level shim for the modular refactor (see approved plan.md).

All existing `from ai_parser import ...` continue to work unchanged.

The real AI parser is now at:
    roster/ai/parser.py
    (re-exported via roster/ai/__init__.py)

All original AI parsing functionality is preserved exactly.
This file will be cleaned up in the final phase after full verification.
"""
from roster.ai import (
    ai_parse_remarks,
    get_column_mapping_from_ai,
    REMARKS_SYSTEM_PROMPT,
    IMPORT_MAPPING_PROMPT,
)

print("✅ [shim] root ai_parser.py now forwards to roster.ai (AI functionality identical)")
