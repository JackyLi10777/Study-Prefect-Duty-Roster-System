# Sing Yin Study Prefect Duty Roster System — Handover Guide

**交接手冊 Handover Guide**
**Version:** 1.0
**Date:** 2026-06-29
**For:** Future Head Study Prefects and System Maintainers

---

## 1. Project Overview

### What This System Does

The Sing Yin Study Prefect Duty Roster System is a professional tool for generating fair weekly duty rosters for the Study Prefect team. It replaces the old Streamlit version with a modern NiceGUI-based interface.

**Core Capabilities:**
- Generate weekly duty rosters using a fairness-weighted algorithm
- Handle leave requests after roster publication
- Manually edit assignments with smart substitute recommendations
- Export professional PDF/HTML rosters for distribution
- Manage prefect data via Google Sheets or CSV
- AI-powered remarks parsing and data import
- Full backup/restore with audit logging

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | NiceGUI (Python) + Quasar components |
| Design | Professional Teal v4.0 (HyperOS Native) |
| Data | Google Sheets (primary) + CSV (fallback) |
| Backup | JSON + auto-backup on generation |
| AI | DeepSeek V4 Flash |
| Tests | pytest — 52 tests |

### Architecture

```
app/
├── main.py              Entry point + route registration
├── theme.py             Design system v4.0 (all colors, CSS, dark mode)
├── pages/
│   ├── dashboard.py     Home page — scripture, KPI, backup, mentoring
│   ├── roster.py        Tabbed roster — Generate & View / Adjust & Edit
│   └── prefects.py      Prefect CRUD + AI Parse + CSV import
├── models/              Data structures — Prefect, WeeklyRoster, enums
├── services/            Business logic — generation, fairness, leave, AI
└── utils/               Infrastructure — data, sheets, backup, pdf, audit
```

**Key principle:** Business logic (services/) never imports UI code (pages/). This keeps the system clean and testable.

---

## 2. Development Environment Setup

### Prerequisites

- Python 3.12+
- Git (optional, for version control)
- A Google account (for Sheets integration)
- A DeepSeek API key (for AI features)

### Step-by-Step Setup

```bash
# 1. Navigate to the project folder
cd D:\code_v2

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables (copy from template)
copy .env.example .env
# Edit .env with your actual values:
#   SY_SHEETS_KEY=service_account.json
#   SY_SHEETS_ID=your_google_sheet_id
#   SY_DEEPSEEK_KEY=sk-your-key-here

# 4. Start the app
python app/main.py

# 5. Open browser
# http://localhost:8080
```

### Required Files

| File | Purpose | Source |
|------|---------|--------|
| `service_account.json` | Google Sheets API authentication | Google Cloud Console |
| `logo.png` | School badge for PDF export | Replace with your school logo |
| `.env` | Environment variables | Copy from `.env.example` |

---

## 3. Production / School Deployment

### Current Deployment

The system currently runs **locally on Windows 11**. The Head Study Prefect starts the app on their laptop and shares the exported roster PDF via group chat.

### Starting the App for Daily Use

```bash
cd D:\code_v2
python app/main.py
# Open http://localhost:8080
```

The app runs as long as the terminal window stays open. Close the terminal to stop the app.

### Future Deployment Options

- **Streamlit Cloud** — The old version ran here. The new version can also be deployed to Streamlit Cloud with `requirements.txt` and `packages.txt`.
- **Local server** — Keep running on the Head Study Prefect's laptop (current approach).
- **Shared machine** — Install on a school computer that stays on during school hours.

---

## 4. Data Import & Migration

### Importing Real Prefect Data

**Method 1: CSV Import (Recommended for first-time setup)**
1. Prepare a CSV file with your prefect data
2. Go to Prefects page → click **Import CSV**
3. Upload your CSV file
4. The system will auto-detect columns (AI + alias-based) and show a **mapping preview table** with confidence badges (green=AI, amber=alias, gray=unmapped)
5. You can manually override any column mapping via dropdown, then click **Confirm Import**
6. The import supports both CSV and Excel files

**Method 2: Google Sheets**
1. Create a Google Sheet with the Prefects sheet
2. Column headers: `name, name_zh, form, class_name, role, available_days, history_weight, remarks, date_joined, active`
3. Share with the service account email
4. Set `SY_SHEETS_ID` to your sheet ID
5. The app will read directly from Sheets on startup

**Method 3: Manual Entry**
1. Go to Prefects page → click **Add Prefect**
2. Fill in each prefect one by one

### CSV Column Reference

| Column | Required | Example | Notes |
|--------|----------|---------|-------|
| `name` | Yes | `CHAN Tai Man` | English name |
| `name_zh` | No | `陳大文` | Chinese name |
| `form` | Yes | `F5` | F.3, F.4, F.5, or F.6 |
| `class_name` | Yes | `5A` | Class identifier |
| `role` | Yes | `STUDY_PREFECT` | STUDY_PREFECT, ASSISTANT_HEAD_PREFECT, or HEAD_STUDY_PREFECT |
| `available_days` | No | `MON,TUE,WED,THU,FRI` | Comma-separated uppercase |
| `history_weight` | No | `0.0` | Start at 0 for new prefects |
| `remarks` | No | `固定星期一 Room 302` | Free text; AI can parse this |

---


## 4a. Phase 2 — Importing Real School Data

Before importing your real prefect data for the first time:
- [ ] Make a JSON backup first (Dashboard → Backup System)
- [ ] Verify your CSV has these columns: **name, form, class_name, role, available_days**
- [ ] Check that role values are: "Study Prefect", "Assistant Head Study Prefect", or "Head Study Prefect"
- [ ] Ensure form values are: F3, F4, F5 (not "F.3", "F.4", etc.)
- [ ] Review the mapping preview table carefully before confirming import
- [ ] After import, check the warnings notification — especially form assignments and duplicates
- [ ] Go to Prefects page → verify all prefects appear correctly with correct roles
- [ ] Generate a test roster to confirm everything works

**For a detailed step-by-step walkthrough with rollback plan, see [PHASE2_GUIDE.md](PHASE2_GUIDE.md).**

**Quick Column Reference (acceptable values):**

| Column | Acceptable Values |
|--------|------------------|
| `name` | Any English name, e.g. `CHAN Tai Man` |
| `form` | `F3`, `F4`, `F5` (NOT `F.3` or `Form 3`) |
| `class_name` | e.g. `5A`, `4B` |
| `role` | `Study Prefect`, `Assistant Head Study Prefect`, `Head Study Prefect` |
| `available_days` | Comma-separated uppercase, e.g. `MON,TUE,WED,THU,FRI` |


## 5. Daily Operations & Common Tasks

### Weekly Workflow (2-3 minutes)

1. **Start the app** — `python app/main.py` → http://localhost:8080
2. **Check Dashboard** — Status dots should be green
3. **Generate roster** — Roster → Generate and View → Generate Roster
4. **Review** — Check the vacancy banner and fairness chart
5. **Adjust if needed** — Adjust and Edit tab for leave/swaps
6. **Export** — Click Export PDF/HTML
7. **Share** — Send the file to the prefect group chat

### Common Tasks Quick Reference

| Task | Navigation |
|------|-----------|
| Generate roster | Roster → Generate and View → Generate Roster |
| Handle leave | Roster → Adjust and Edit → Leave Adjustment |
| Manual swap | Roster → Adjust and Edit → Manual Edit / Substitute |
| Export PDF | Roster → Generate and View → Export PDF/HTML |
| Add prefect | Prefects → Add Prefect |
| AI parse remarks | Prefects → AI Parse Remarks |
| Import CSV | Prefects → Import CSV |
| Backup | Dashboard → Backup System |
| Restore | Dashboard → Restore from Backup |
| View fairness | Dashboard → Fairness Chart |
| View mentoring | Dashboard → Mentoring Pairs |

---

## 6. Backup, Restore & Data Safety

### Backup Strategy (Triple Protection)

| Layer | What | Frequency |
|-------|------|-----------|
| **Google Sheets** | Primary data storage | Real-time sync |
| **CSV file** | Local fallback | Every save |
| **JSON backup** | Auto-backup on generation | Every roster generation |

### Manual Backup

Dashboard → **Backup System** → downloads a `.json` file. Do this weekly.

### Restore from Backup

Dashboard → **Restore from Backup** → upload the `.json` file. The system validates the backup before applying.

### Auto-Backup Location

`data/auto_backups/roster_YYYY-MM-DD.json` — created automatically after each roster generation. Keep the last 10–20 files.

### What to Do If Data Is Lost

1. Check `data/auto_backups/` for the most recent auto-backup
2. Restore from the most recent JSON backup
3. If no backup exists, re-import from CSV or Google Sheets
4. The CSV file (`data/prefects.csv`) is the last-resort fallback

---

## 7. Troubleshooting

### Quick Diagnosis

| Symptom | Check |
|---------|-------|
| App won't start | Is Python installed? Are dependencies installed? (`pip install -r requirements.txt`) |
| Sheets status red | Is `SY_SHEETS_KEY` set? Is `service_account.json` in the project folder? |
| DeepSeek status yellow | Is `SY_DEEPSEEK_KEY` set? AI features won't work but roster generation still does. |
| Generate button no response | Check the notification message. Usually means too few active prefects (< 3). |
| PDF export looks wrong | Is `logo.png` in the project folder? Toggle "Show Logo on PDF" on Dashboard. |

### Getting Help

- Read **FAQ.md** for answers to 25 common questions
- Read **SETUP.md** for detailed setup instructions
- Read **QUICKSTART.md** for daily workflow reference
- Contact the previous Head Study Prefect for system-specific questions

---

## 8. Extending the System

### How to Add a New Feature

1. **Business logic** → Add to `services/` (never import NiceGUI here)
2. **UI** → Add to `pages/` (import from services/)
3. **Data** → Add to `models/` if new data structures needed
4. **Tests** → Add to `tests/` mirroring the source structure

### How to Modify School Rules

School rules live in:
- `models/enums.py` — Room, Weekday, Role definitions
- `models/roster.py` — SchoolRules class (AHP count, room capacities, closures)
- `services/roster_service.py` — Generation algorithm

**Example: Change Room 202 closure days**
```python
# In models/enums.py, modify the Room enum:
ROOM_202 = ("Room 202", 2, [Weekday.TUE, Weekday.FRI])  # Change closed days here
```

### How to Change the Design

All design tokens are in `theme.py`. The design system document is `Professional_Teal_Design_System.md`.

### Running Tests

```bash
cd D:\code_v2
python -m pytest tests/ -q
# Expected: 52 passed
```

Always run tests after making changes.

---

## 9. Key Files Reference

| File | Purpose | When to Edit |
|------|---------|-------------|
| `app/main.py` | Entry point, routes | Adding new pages |
| `app/theme.py` | Design system v4.0 | Changing colors, CSS, dark mode |
| `app/pages/roster.py` | Roster generation UI | Roster workflows |
| `app/pages/dashboard.py` | Home page | Adding KPI cards, scripture |
| `app/pages/prefects.py` | Prefect management | CRUD operations |
| `app/services/roster_service.py` | Generation engine | School rules, fairness |
| `app/services/leave_service.py` | Leave adjustment | Post-publication changes |
| `app/services/ai_parser.py` | DeepSeek integration | AI parsing logic |
| `app/models/enums.py` | Role, Form, Room, Weekday | Adding new roles/rooms |
| `app/models/roster.py` | SchoolRules | Changing capacities, closures |
| `app/utils/data.py` | CSV persistence | Data format |
| `app/utils/sheets.py` | Google Sheets sync | Sheets integration |
| `app/utils/backup.py` | JSON backup/restore | Backup logic |
| `requirements.txt` | Python dependencies | Adding libraries |
| `.env.example` | Environment template | Adding config vars |

---

## 10. Contact & Ownership

**System Creator:** LI Chuangjie (Head Study Prefect 26-27)
**Project Location:** `D:\code_v2\`
**Documentation:**
- `SETUP.md` — One-time setup guide
- `QUICKSTART.md` — Daily workflow reference
- `FAQ.md` — 25 common questions
- `HANDOVER.md` — This document
- `PROJECT_STATUS.md` — Technical status report
- `GROK_PROMPTS.md` — Meta-prompts for AI-assisted development

**Key Accounts:**
- Google Cloud Project: Sing Yin Roster System
- DeepSeek Platform: API key management
- Google Sheets: Prefect data storage

---

## Appendix A: Setup Checklist

- [ ] Python 3.12 installed
- [ ] `pip install -r requirements.txt` completed
- [ ] `service_account.json` obtained from Google Cloud Console
- [ ] Google Sheet created and shared with service account
- [ ] `SY_SHEETS_KEY`, `SY_SHEETS_ID`, `SY_DEEPSEEK_KEY` set in `.env`
- [ ] `logo.png` placed in project folder
- [ ] `python app/main.py` starts successfully
- [ ] Dashboard loads at http://localhost:8080
- [ ] Status dots are green (or yellow for DeepSeek if not configured)
- [ ] Sample data loaded (Prefects → Load Demo Data)
- [ ] First roster generated successfully

## Appendix B: Regular Maintenance Checklist

**Weekly:**
- [ ] Generate and export roster
- [ ] Download JSON backup (Dashboard → Backup System)
- [ ] Verify Google Sheets is syncing (check Sheets status dot)

**Monthly:**
- [ ] Review auto-backup files, keep last 10–20
- [ ] Update prefect data (new joiners, leavers, form changes)
- [ ] Run AI Parse Remarks if remarks column was updated

**Per Term:**
- [ ] Full data audit — check all prefects are active and correct
- [ ] Export a complete JSON backup and store it safely
- [ ] Review and update FAQ.md if new common issues emerged

---

*This Handover Guide was prepared on 2026-06-29. Keep it updated as the system evolves.*
