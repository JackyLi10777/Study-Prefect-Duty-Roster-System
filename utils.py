# utils.py (root shim / compatibility layer)
"""
Temporary root-level shim for the modular refactor (see approved plan.md).

All existing `from utils import generate_pdf, export_system_backup, ...`
continue to work unchanged.

The real utilities are now split under:
    roster/utils/
    (pdf.py, backup.py, importers.py)

All original functionality (PDF, JSON backup/restore, importers) is preserved exactly.
This file will be cleaned up in the final phase after full verification.
"""
from roster.utils import (
    get_cell_style,
    generate_pdf,
    export_system_backup,
    import_system_backup,
    process_roster_import,
    smart_process_roster_import,
)

# Re-export commonly referenced constants (for any legacy direct use in importers or pdf glue)
from roster.config import (
    GEMINI_MODEL,
    VERSION,
    PROJECT_FULL_NAME,
    NASA_COLORS,
    DAYS,
    ROWS_ROSTER,
)

print("✅ [shim] root utils.py now forwards to roster.utils (functionality identical)")
