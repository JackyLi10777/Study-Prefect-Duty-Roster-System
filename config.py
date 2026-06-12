# config.py (root shim / compatibility layer)
"""
Temporary root-level shim for the modular refactor (see approved plan.md).

All existing `from config import ...` and `import config` continue to work unchanged.

The real SSOT is now at:
    roster/config/constants.py
    (re-exported via roster/config/__init__.py and this shim)

This file will be cleaned up in the final phase after full verification.
"""
from roster.config import *  # noqa: F401,F403

print("✅ [shim] root config.py forwarding to roster.config (SSOT)")
