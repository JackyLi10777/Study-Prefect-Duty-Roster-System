"""NiceGUI application package for the Sing Yin roster rebuild."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for package_path in (PROJECT_ROOT / "packages" / "roster_core", PROJECT_ROOT / "packages" / "roster_policy"):
    if str(package_path) not in sys.path:
        sys.path.insert(0, str(package_path))
