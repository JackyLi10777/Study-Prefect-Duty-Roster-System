"""Central paths and durable application-level constants."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Configuration constants are imported before ``main.run`` executes. Load the
# project environment here so database and backup paths declared in .env are
# not silently replaced by their defaults. Explicit process variables retain
# priority because python-dotenv does not override them by default.
load_dotenv(PROJECT_ROOT / ".env")


def _bounded_int_environment(
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    """Read an integer environment setting without allowing unsafe extremes."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value.strip())
    except (AttributeError, ValueError):
        return default
    return min(maximum, max(minimum, value))


def _boolean_environment(name: str, *, default: bool = False) -> bool:
    """Read one explicit boolean without treating arbitrary text as truthy."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


SQLITE_BUSY_TIMEOUT_MS = _bounded_int_environment(
    "SING_YIN_SQLITE_BUSY_TIMEOUT_MS",
    default=10_000,
    minimum=1_000,
    maximum=60_000,
)
SQL_DIAGNOSTICS_ENABLED = _boolean_environment("SING_YIN_SQL_DIAGNOSTICS")
SLOW_SQL_MS = _bounded_int_environment(
    "SING_YIN_SLOW_SQL_MS",
    default=100,
    minimum=1,
    maximum=60_000,
)
BRAND_ASSET_DIR = PROJECT_ROOT / "nicegui_app" / "assets" / "brand"
SERVICE_WEAVE_ASSET_DIR = BRAND_ASSET_DIR / "service-weave"
MUSIC_DIR = PROJECT_ROOT / "music"
FAVICON_CREST_PATH = BRAND_ASSET_DIR / "sing-yin-crest-favicon.png"
NAVIGATION_CREST_PATH = BRAND_ASSET_DIR / "sing-yin-crest-navigation.png"
DISPLAY_PRINT_CREST_PATH = BRAND_ASSET_DIR / "sing-yin-crest-display-print.png"
DISPLAY_WEB_CREST_PATH = BRAND_ASSET_DIR / "sing-yin-crest-display-web.png"
SERVICE_WEAVE_FAVICON_PATH = SERVICE_WEAVE_ASSET_DIR / "service-weave-favicon-512-v1.png"
SERVICE_WEAVE_NAVIGATION_LIGHT_PATH = SERVICE_WEAVE_ASSET_DIR / "service-weave-navigation-light-256-v1.png"
SERVICE_WEAVE_NAVIGATION_DARK_PATH = SERVICE_WEAVE_ASSET_DIR / "service-weave-navigation-dark-256-v1.png"
SERVICE_WEAVE_WINDOWS_ICON_PATH = SERVICE_WEAVE_ASSET_DIR / "service-weave-windows-v1.ico"
DATA_DIR = PROJECT_ROOT / "data"
CANONICAL_DATABASE_PATH = DATA_DIR / "runtime" / "sing-yin-roster.sqlite3"
CANONICAL_BACKUP_DIR = DATA_DIR / "backups"
CANONICAL_LOG_DIR = PROJECT_ROOT / "logs"
CANONICAL_SUPPORT_DIR = DATA_DIR / "support"
PRACTICE_DATA_DIR = DATA_DIR / "practice"
DEFAULT_DATABASE_PATH = Path(os.getenv("SING_YIN_DATABASE_PATH", CANONICAL_DATABASE_PATH))
DEFAULT_BACKUP_DIR = Path(os.getenv("SING_YIN_BACKUP_DIR", CANONICAL_BACKUP_DIR))
PREFECT_SEED_PATH = DATA_DIR / "demo" / "prefects.zh-HK.seed.json"
DEVOTIONAL_SEED_PATH = DATA_DIR / "devotional" / "daily-verses.seed.json"
POLICY_VERSION = "2026.09.04-unified-duty-hours"
CANONICAL_PUBLIC_URL = os.getenv(
    "SING_YIN_PUBLIC_URL",
    "https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/",
).strip().rstrip("/") + "/"


def support_directory() -> Path:
    """Return the local incident inbox root.

    Unlike database constants this is resolved at call time so isolated tests
    and recovery tools can safely override it without importing production
    state first.
    """

    configured = os.getenv("SING_YIN_SUPPORT_DIR", "").strip()
    return Path(configured) if configured else CANONICAL_SUPPORT_DIR
