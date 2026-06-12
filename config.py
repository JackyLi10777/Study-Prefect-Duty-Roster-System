# config.py (root shim / compatibility layer)
"""
Ultra-thin root-level compatibility shim.

All legacy `from config import ...` continue to work.

**Strong recommendation (project-structure-advisor):** New code should import directly from `roster.config`.

Real SSOT: roster/config/constants.py (bilingual PROJECT_FULL_NAME / PROJECT_FULL_NAME_EN for UI Chinese vs Export English).
"""
from roster.config import *  # noqa: F401,F403

print("✅ [shim] root config.py → roster.config (SSOT, thin compat only)")
