"""
Google Sheets Connector for the Sing Yin Study Prefect Duty Roster System.

Provides read/write access to Google Sheets as the Single Source of Truth (SSOT).
Supports graceful degradation to CSV if Sheets is unavailable (see utils/data.py).

Setup:
1. Create a Google Cloud project and enable Sheets API
2. Create a Service Account and download the JSON key
3. Share your Google Sheet with the service account email (as Editor)
4. Set environment variable: SY_SHEETS_KEY=path/to/service_account.json
5. Set environment variable: SY_SHEETS_ID=your_google_sheet_id
"""

import os
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Callable

# ---- Config ----
SHEETS_KEY_FILE = os.environ.get("SY_SHEETS_KEY", "service_account.json")
SHEETS_ID = os.environ.get("SY_SHEETS_ID", "")
PREFECTS_SHEET_NAME = "Prefects"
CACHE_TTL_SECONDS = 30  # How long to cache reads before re-fetching
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds, doubles each retry

# ---- Auth ----
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]




def _retry_with_backoff(fn, name="sheets_op"):
    """Call fn() with exponential backoff on transient failures.

    Retries up to MAX_RETRIES times with delays of 1s, 2s, 4s.
    Logs each retry attempt to audit log.
    Returns fn() result on success, raises last exception on final failure.
    """
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                time.sleep(delay)
                try:
                    from utils.audit import log_action
                    log_action("sheets_retry_" + name, "attempt " + str(attempt+1) + "/" + str(MAX_RETRIES) + " after " + str(delay) + "s: " + str(e)[:100])
                except: pass
    raise last_err

def _get_client():
    """Lazy-init the gspread client. Returns None if unavailable."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        key_path = Path(SHEETS_KEY_FILE)
        if not key_path.exists():
            return None  # No key file — Sheets unavailable

        creds = Credentials.from_service_account_file(str(key_path), scopes=SCOPES)
        return gspread.authorize(creds)
    except (ImportError, Exception):
        return None


# ---- Caching ----
_cache: Dict = {}
_cache_time: float = 0.0


def _is_cache_valid() -> bool:
    """Check whether the in-memory cache is still fresh."""
    return bool(_cache) and (time.time() - _cache_time) < CACHE_TTL_SECONDS


def invalidate_cache():
    """Force a re-fetch on next read."""
    global _cache, _cache_time
    _cache = {}
    _cache_time = 0.0


# ---- Core API ----
def is_available() -> bool:
    """Check if Google Sheets is configured and accessible."""
    return bool(SHEETS_ID) and _get_client() is not None


def load_prefects_from_sheets() -> Optional[List[Dict]]:
    """Read prefects from Google Sheets.

    Returns a list of dicts (same format as CSV load_prefects), or None
    if Sheets is unavailable.

    Column mapping (Sheet column name -> dict key):
        name, name_zh, form, class_name, role, available_days,
        history_weight, remarks, date_joined, active
    """
    if not is_available():
        return None

    global _cache, _cache_time

    # Check cache (direct access, no function call that would trigger global-before-declare)
    if _cache and (time.time() - _cache_time) < CACHE_TTL_SECONDS:
        return _cache.get("prefects")

    try:
        client = _get_client()
        sheet = _retry_with_backoff(
            lambda: client.open_by_key(SHEETS_ID).worksheet(PREFECTS_SHEET_NAME),
            "open_sheet"
        )
        records = sheet.get_all_records()
        if not records:
            return []

        from models.enums import Weekday, Role, Form

        rows = []
        for r in records:
            avail_str = str(r.get("available_days", ""))
            available = []
            if avail_str:
                for w in avail_str.split(","):
                    w = w.strip().upper()
                    if w in Weekday.__members__:
                        available.append(Weekday[w])

            role_str = str(r.get("role", "STUDY_PREFECT")).strip().upper()
            role = Role[role_str] if role_str in Role.__members__ else Role.STUDY_PREFECT

            form_str = str(r.get("form", "F4")).strip().upper()
            form = Form[form_str] if form_str in Form.__members__ else Form.F4

            rows.append({
                "name": str(r.get("name", "")).strip(),
                "name_zh": str(r.get("name_zh", "")).strip(),
                "form": form,
                "class_name": str(r.get("class_name", "")).strip(),
                "role": role,
                "available": available,
                "history_weight": float(r.get("history_weight", 0)),
                "remarks": str(r.get("remarks", "")).strip(),
                "date_joined": str(r.get("date_joined", "")).strip(),
                "active": str(r.get("active", "TRUE")).strip().upper() == "TRUE",
            })

        _cache["prefects"] = rows
        _cache_time = time.time()
        return rows

    except Exception as e:
        try:
            from utils.audit import log_action
            log_action("sheets_load_error", str(e)[:200])
        except: pass
        return None


def save_prefects_to_sheets(prefects: list) -> bool:
    """Write prefects to Google Sheets. Returns True on success.

    Uses batch update for performance. Overwrites the entire sheet.
    """
    if not is_available():
        return False

    try:
        client = _get_client()
        sheet = _retry_with_backoff(
            lambda: client.open_by_key(SHEETS_ID).worksheet(PREFECTS_SHEET_NAME),
            "open_sheet"
        )

        # Build header + rows
        header = [
            "name", "name_zh", "form", "class_name", "role",
            "available_days", "history_weight", "remarks", "date_joined", "active",
        ]
        rows = [header]
        for p in prefects:
            name = p.name if hasattr(p, "name") else p.get("name", "")
            available = p.available if hasattr(p, "available") else p.get("available", [])
            avail_str = ",".join(
                a.name if hasattr(a, "name") else str(a) for a in available
            ) if available else ""
            form_val = p.form.name if hasattr(p.form, "name") else str(p.get("form", "F4"))
            role_val = p.role.name if hasattr(p.role, "name") else str(p.get("role", "STUDY_PREFECT"))
            rows.append([
                name,
                getattr(p, "name_zh", "") if hasattr(p, "name_zh") else p.get("name_zh", ""),
                form_val,
                getattr(p, "class_name", "") if hasattr(p, "class_name") else p.get("class_name", ""),
                role_val,
                avail_str,
                str(p.history_weight if hasattr(p, "history_weight") else p.get("history_weight", 0)),
                getattr(p, "remarks", "") if hasattr(p, "remarks") else p.get("remarks", ""),
                getattr(p, "date_joined", "") if hasattr(p, "date_joined") else p.get("date_joined", ""),
                str(getattr(p, "active", True) if hasattr(p, "active") else p.get("active", True)),
            ])

        # Batch clear + update
        _retry_with_backoff(lambda: sheet.clear(), "clear_sheet")
        _retry_with_backoff(lambda: sheet.update(rows, value_input_option="USER_ENTERED"), "update_sheet")

        # Invalidate cache so next read picks up fresh data
        invalidate_cache()
        return True

    except Exception as e:
        try:
            from utils.audit import log_action
            log_action("sheets_save_error", str(e)[:200])
        except: pass
        return False


def status_detail() -> dict:
    """Return detailed connection status with actionable guidance."""
    if not SHEETS_ID:
        return {"level":"offline","label":"Sheets: Not Configured","detail":"Set SY_SHEETS_ID in .env file","action":"See SETUP.md Steps 1-4"}
    key_path = Path(SHEETS_KEY_FILE)
    if not key_path.exists():
        return {"level":"offline","label":"Sheets: Key Missing","detail":"Service account key not found","action":"Download JSON key from Google Cloud Console. See SETUP.md Step 3."}
    try:
        client = _get_client()
        if client is None:
            return {"level":"warning","label":"Sheets: Auth Failed","detail":"Could not authenticate with Google","action":"Verify the key file is valid and not expired"}
        return {"level":"online","label":"Sheets: Connected","detail":"Google Sheets is connected and syncing","action":""}
    except Exception as e:
        return {"level":"warning","label":"Sheets: Connection Issue","detail":str(e)[:80],"action":"Check that the sheet is shared with the service account email"}

def status_message() -> str:
    """Return a human-readable status string for the Sheets connection."""
    if not SHEETS_ID:
        return "Google Sheets not configured (SY_SHEETS_ID not set). Using CSV."
    if not Path(SHEETS_KEY_FILE).exists():
        return f"Service account key not found at {SHEETS_KEY_FILE}. Using CSV."
    if not _get_client():
        return "Google Sheets authentication failed. Using CSV."
    return "Google Sheets connected and active."
