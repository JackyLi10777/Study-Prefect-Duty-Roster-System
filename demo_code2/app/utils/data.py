"""
Data persistence layer for the Sing Yin Study Prefect Duty Roster System.

Stores prefect data as CSV in the project root (data/prefects.csv).
The CSV is human-readable and can be edited in Excel/Sheets when needed.

Supports:
- load_prefects() — read prefects from CSV
- save_prefects() — write prefects to CSV
- load_roster_history() / save_roster_history() — future expansion

CSV columns:
    name, name_zh, form, class_name, role, available_days,
    history_weight, remarks, date_joined, active
"""

import csv
import os
import json
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

PREFECTS_CSV = Path(__file__).resolve().parent.parent.parent / "data" / "prefects.csv"

from models.enums import Role, Form, Weekday

# Google Sheets connector (graceful fallback to CSV)
try:
    from utils.sheets import (
        load_prefects_from_sheets, save_prefects_to_sheets,
        is_available as sheets_available, status_message as sheets_status,
    )
except ImportError:
    load_prefects_from_sheets = None
    save_prefects_to_sheets = None
    sheets_available = lambda: False
    sheets_status = lambda: "Google Sheets not available. Using CSV."


def load_prefects(filepath: Optional[Path] = None) -> List[dict]:
    """Load prefects from Google Sheets (SSOT) or CSV fallback."""
    if sheets_available():
        result = load_prefects_from_sheets()
        if result is not None:
            return result
    # Fallback to CSV
    """Load prefect records from CSV. Returns list of dicts for Prefect.from_dict()."""
    path = filepath or PREFECTS_CSV
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            # Parse available days from comma-separated string
            avail_str = row.get("available_days", "")
            available = [
                Weekday[w.strip()] for w in avail_str.split(",") if w.strip()
            ] if avail_str else []
            rows.append({
                "name": row.get("name", "").strip(),
                "name_zh": row.get("name_zh", "").strip(),
                "form": Form[row.get("form", "F3").strip()],
                "class_name": row.get("class_name", "").strip(),
                "role": Role[row.get("role", "STUDY_PREFECT").strip()],
                "available": available,
                "history_weight": float(row.get("history_weight", 0)),
                "remarks": row.get("remarks", "").strip(),
                "date_joined": row.get("date_joined", "").strip() or str(date.today()),
                "active": row.get("active", "true").strip().lower() == "true",
            })
        return rows


def save_prefects(prefects: list, filepath: Optional[Path] = None) -> str:
    """Save prefects to Google Sheets + CSV backup (dual-write)."""
    sheets_ok = False
    if sheets_available():
        sheets_ok = save_prefects_to_sheets(prefects)
    # Always write CSV as backup
    """Save a list of Prefect objects/dicts to CSV. Returns the file path."""
    path = filepath or PREFECTS_CSV
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "name", "name_zh", "form", "class_name", "role",
        "available_days", "history_weight", "remarks", "date_joined", "active",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in prefects:
            # Support both Prefect objects and plain dicts
            if hasattr(p, "name"):
                name = p.name
                available = ",".join(w.name for w in p.available) if p.available else ""
                row = {
                    "name": p.name,
                    "name_zh": getattr(p, "name_zh", ""),
                    "form": p.form.name,
                    "class_name": getattr(p, "class_name", ""),
                    "role": p.role.name,
                    "available_days": available,
                    "history_weight": p.history_weight,
                    "remarks": getattr(p, "remarks", ""),
                    "date_joined": getattr(p, "date_joined", str(date.today())),
                    "active": str(getattr(p, "active", True)).lower(),
                }
            else:
                available = ",".join(
                    w.name if hasattr(w, "name") else str(w)
                    for w in p.get("available", [])
                ) if p.get("available") else ""
                row = {
                    "name": p.get("name", ""),
                    "name_zh": p.get("name_zh", ""),
                    "form": p["form"].name if hasattr(p["form"], "name") else str(p.get("form", "")),
                    "class_name": p.get("class_name", ""),
                    "role": p["role"].name if hasattr(p["role"], "name") else str(p.get("role", "")),
                    "available_days": available,
                    "history_weight": p.get("history_weight", 0),
                    "remarks": p.get("remarks", ""),
                    "date_joined": p.get("date_joined", str(date.today())),
                    "active": str(p.get("active", True)).lower(),
                }
            writer.writerow(row)
    return str(path)


def sample_prefects() -> list:
    """Return sample prefects as dicts. Used for first-time setup or demo."""
    return [
        {"name": "CHAN Tai Man", "name_zh": "Chen Da Wen", "form": Form.F5, "class_name": "5A",
         "role": Role.ASSISTANT_HEAD_PREFECT, "available": [
             Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI],
         "history_weight": 0.0, "remarks": "", "date_joined": str(date.today()), "active": True},
        {"name": "WONG Siu Ming", "name_zh": "Huang Xiao Ming", "form": Form.F5, "class_name": "5B",
         "role": Role.ASSISTANT_HEAD_PREFECT, "available": [
             Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI],
         "history_weight": 0.0, "remarks": "", "date_joined": str(date.today()), "active": True},
        {"name": "LEE Ka Wai", "name_zh": "Li Jia Wei", "form": Form.F4, "class_name": "4A",
         "role": Role.ASSISTANT_HEAD_PREFECT, "available": [
             Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI],
         "history_weight": 0.0, "remarks": "", "date_joined": str(date.today()), "active": True},
        {"name": "NG Mei Ling", "name_zh": "Wu Mei Ling", "form": Form.F4, "class_name": "4B",
         "role": Role.ASSISTANT_HEAD_PREFECT, "available": [
             Weekday.MON, Weekday.TUE, Weekday.THU, Weekday.FRI],
         "history_weight": 0.0, "remarks": "", "date_joined": str(date.today()), "active": True},
        {"name": "HO Chun Yin", "name_zh": "He Jun Xian", "form": Form.F4, "class_name": "4C",
         "role": Role.ASSISTANT_HEAD_PREFECT, "available": [
             Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI],
         "history_weight": 0.0, "remarks": "", "date_joined": str(date.today()), "active": True},
        {"name": "CHEUNG Hiu Tung", "name_zh": "Zhang Xiao Tong", "form": Form.F4, "class_name": "4A",
         "role": Role.STUDY_PREFECT, "available": [
             Weekday.MON, Weekday.WED, Weekday.FRI],
         "history_weight": 0.0, "remarks": "", "date_joined": str(date.today()), "active": True},
        {"name": "FUNG Ka Yan", "name_zh": "Feng Jia Xin", "form": Form.F4, "class_name": "4B",
         "role": Role.STUDY_PREFECT, "available": [
             Weekday.MON, Weekday.TUE, Weekday.THU],
         "history_weight": 0.0, "remarks": "", "date_joined": str(date.today()), "active": True},
        {"name": "LAM Siu Hong", "name_zh": "Lin Xiao Kang", "form": Form.F3, "class_name": "3A",
         "role": Role.STUDY_PREFECT, "available": [
             Weekday.TUE, Weekday.WED, Weekday.THU],
         "history_weight": 0.0, "remarks": "", "date_joined": str(date.today()), "active": True},
        {"name": "TANG Wing Sze", "name_zh": "Deng Yong Shi", "form": Form.F3, "class_name": "3B",
         "role": Role.STUDY_PREFECT, "available": [
             Weekday.MON, Weekday.THU, Weekday.FRI],
         "history_weight": 0.0, "remarks": "", "date_joined": str(date.today()), "active": True},
        {"name": "YIP Tsz Ching", "name_zh": "Ye Zi Qing", "form": Form.F3, "class_name": "3C",
         "role": Role.STUDY_PREFECT, "available": [
             Weekday.MON, Weekday.WED, Weekday.FRI],
         "history_weight": 0.0, "remarks": "", "date_joined": str(date.today()), "active": True},
    ]


def ensure_sample_data():
    """Create sample prefects CSV if none exists."""
    if not PREFECTS_CSV.exists():
        save_prefects(sample_prefects())
        return True
    return False


def load_demo_data() -> list:
    """Load demo prefect data from JSON file (supports both old and new format).

    New format: {"prefects": [...], "roster_history": [...], "leave_records": [...]}
    Old format: [...] (list of prefect dicts)
    """
    demo_path = Path(__file__).resolve().parent.parent.parent / "data" / "sample_data.json"
    if demo_path.exists():
        with open(demo_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data  # Old format
        return data.get("prefects", sample_prefects())
    return sample_prefects()


def load_demo_roster_history() -> list:
    """Load demo roster history from sample_data.json and convert to WeeklyRoster objects.

    Returns list of (week_start_str, day_name, room_assignments_dict) tuples
    that can be used by the Roster page to populate history.
    """
    demo_path = Path(__file__).resolve().parent.parent.parent / "data" / "sample_data.json"
    if not demo_path.exists():
        return []
    with open(demo_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return []  # Old format, no history
    return data.get("roster_history", [])


def load_demo_leave_records() -> list:
    """Load demo leave adjustment records from sample_data.json."""
    demo_path = Path(__file__).resolve().parent.parent.parent / "data" / "sample_data.json"
    if not demo_path.exists():
        return []
    with open(demo_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return []
    return data.get("leave_records", [])
