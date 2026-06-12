"""roster.utils - Technical utility layer.

- PDF generation (must sync styles with roster.config)
- JSON backup/restore (Cloud critical, always reindexes)
- Import processors (traditional + AI)

All original public functions from utils.py are re-exported.
No business rules live here.
"""

from .pdf import get_cell_style, generate_pdf, generate_service_certificate
from .backup import (
    export_system_backup, import_system_backup,
    trigger_backup_reminder, clear_backup_reminder, get_backup_history,
    get_dynamic_backup_json,  # used by pdf and for advanced cases
)
from .importers import process_roster_import, smart_process_roster_import
