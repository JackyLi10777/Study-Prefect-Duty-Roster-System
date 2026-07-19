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
PRACTICE_DATA_DIR = DATA_DIR / "practice"
DEFAULT_DATABASE_PATH = Path(os.getenv("SING_YIN_DATABASE_PATH", CANONICAL_DATABASE_PATH))
DEFAULT_BACKUP_DIR = Path(os.getenv("SING_YIN_BACKUP_DIR", CANONICAL_BACKUP_DIR))
PREFECT_SEED_PATH = DATA_DIR / "demo" / "prefects.zh-HK.seed.json"
DEVOTIONAL_SEED_PATH = DATA_DIR / "devotional" / "daily-verses.seed.json"
POLICY_VERSION = "2026.07.10"
CANONICAL_PUBLIC_URL = os.getenv(
    "SING_YIN_PUBLIC_URL",
    "https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/",
).strip().rstrip("/") + "/"
