"""
roster - Sing Yin Study Prefect Duty Roster System (modular package)

聖言中學導學風紀當值排班平台

本套件嚴格實現 AGENTS.md 中定義的所有學校業務規則（§1 Core Project Rules）：
- 學生資格、角色區分（Study Prefect vs Assistant Head）、固定值班、可用日子、歷史負荷公平
- Room 302/303 全天開放、無額外限制、權重與槽位規則
- AHP 專屬 Assist. in charge 職位及硬限制
- 每人每天一次 + 避免連續兩天 + 固定優先 + F.3 老帶新
- 值班後請假調整的公平性機制

推薦使用方式（新程式碼）：
    from roster import generate_roster
    from roster.config import is_assistant_head_only_role, ROOMS_CONFIG
    from roster.data.state import initialize_session_state
    from roster.utils.backup import export_system_backup

根目錄的 config.py / core.py 等檔案為相容性 shim，舊程式碼仍可使用 `from core import ...`。

完整規則與驗證要求請務必閱讀 AGENTS.md。
"""

__version__ = "0.2.0"  # post full roster/ package migration

# Convenience re-exports (will be expanded as modules are moved)
from .config import *  # re-export SSOT  # noqa

# Core business logic (generate_roster etc. - the single source of rule enforcement)
from .core import *  # noqa

# Data layer (demo, state, validation, models)
from .data import *  # noqa

# Utilities (PDF, backup, importers)
from .utils import *  # noqa

# UI layer is imported lazily by app.py and streamlit_app_entrypoint;
# eager import here risks circular deadlock with roster.core on Cloud.
# from .ui import *  # noqa

# AI layer
from .ai import *  # noqa
