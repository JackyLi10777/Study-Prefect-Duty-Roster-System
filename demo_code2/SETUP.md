# Sing Yin Study Prefect Duty Roster System — Setup Guide

**For:** Future Head Study Prefects (non-technical)
**Time to complete:** 30–45 minutes (one-time setup)
**Result:** A fully working duty roster generation system running on your computer

---

## Quick Overview

This system helps you:
- Generate fair weekly duty rosters for all Study Prefects
- Handle leave requests and adjust assignments
- Export professional PDFs for distribution
- Keep all data permanently in Google Sheets (never lost)

You only need to set this up **once**. After setup, the daily workflow takes 2–3 minutes.

---

## What You Need Before Starting

| Item | Where to get it | Cost |
|------|----------------|------|
| A Google account (any Gmail works) | gmail.com | Free |
| A DeepSeek API key | platform.deepseek.com | Free (usage-based, ~$1/month for typical use) |
| Python 3.12 installed on your computer | python.org → Downloads | Free |
| This project folder (given to you by the previous Head Prefect) | USB / Google Drive / GitHub | — |

---

## Step 1: Create a Google Cloud Project

1. Go to https://console.cloud.google.com
2. Sign in with your Google account
3. Click the project dropdown (top-left) → **New Project**
4. Name: `Sing Yin Roster System` → Click **Create**
5. Wait 10–20 seconds for the project to be created

---

## Step 2: Enable Google Sheets API

1. In the Google Cloud Console, search for "Google Sheets API"
2. Click **Google Sheets API** → Click **Enable**
3. Wait for it to activate (takes ~5 seconds)

---

## Step 3: Create a Service Account

1. In the Google Cloud Console, go to **APIs & Services** → **Credentials**
2. Click **+ Create Credentials** → **Service Account**
3. Name: `singyin-roster` → Click **Create and Continue**
4. Role: Select **Editor** → Click **Continue** → Click **Done**
5. Click on the newly created service account email
6. Go to **Keys** tab → **Add Key** → **Create New Key** → **JSON**
7. Save the downloaded file as `service_account.json`
8. Place this file in the project folder (next to `main.py`)

---

## Step 4: Create Your Google Sheet

1. Go to https://sheets.google.com → **Blank spreadsheet**
2. Name the spreadsheet: `Sing Yin Prefect Data`
3. Rename the first sheet tab to: `Prefects`
4. Add these exact column headers in row 1:

```
name | name_zh | form | class_name | role | available_days | history_weight | remarks | date_joined | active
```

5. Click **Share** (top-right) → Enter the service account email (looks like `singyin-roster@...iam.gserviceaccount.com`)
6. Set permission to **Editor** → Click **Send**
7. Copy the spreadsheet ID from the URL:
   - URL looks like: `https://docs.google.com/spreadsheets/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ/edit`
   - The ID is the long string between `/d/` and `/edit`: `1aBcDeFgHiJkLmNoPqRsTuVwXyZ`

---

## Step 5: Get a DeepSeek API Key

1. Go to https://platform.deepseek.com
2. Sign up / Sign in
3. Go to **API Keys** → **Create new key**
4. Copy the key (looks like `sk-xxxxxxxxxxxxxxxxxxxxxxxx`)

---

## Step 6: Configure Environment Variables

**On Windows (Command Prompt):**
```
setx SY_SHEETS_KEY "service_account.json"
setx SY_SHEETS_ID "1aBcDeFgHiJkLmNoPqRsTuVwXyZ"
setx SY_DEEPSEEK_KEY "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
```
Then restart your computer or Command Prompt.

**On macOS / Linux (Terminal):**
```bash
echo 'export SY_SHEETS_KEY="service_account.json"' >> ~/.bashrc
echo 'export SY_SHEETS_ID="1aBcDeFgHiJkLmNoPqRsTuVwXyZ"' >> ~/.bashrc
echo 'export SY_DEEPSEEK_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"' >> ~/.bashrc
source ~/.bashrc
```

---

## Step 7: Install and Run

1. Open Terminal (Mac) or Command Prompt (Windows)
2. Navigate to the project folder:
   ```bash
   cd path/to/project
   ```
3. Install dependencies (one-time):
   ```bash
   pip install -r requirements.txt
   ```
4. Start the app:
   ```bash
   python app/main.py
   ```
5. Open your browser to: **http://localhost:8080**

You should see the Dashboard with the Daily Scripture and "Sheets Connected" status dot in green.

---

## Step 8: First Run — Load Demo Data

1. Go to the **Prefects** page (sidebar or Dashboard → "Manage Prefects")
2. Click **Load Demo Data** — this populates 11 prefects + duty history into your Google Sheet
3. Go to the **Roster** page → click **Generate and View** tab → click **Generate Roster**
4. You should see a complete 5-day roster with AHP assignments and room duties

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Sheets Offline" status dot (red) | Check Step 3–4: Is service_account.json in the project folder? Did you share the Sheet with the service account email? Is the SY_SHEETS_ID correct? |
| "DeepSeek Not Set" status dot (yellow) | Check Step 5–6: Did you set SY_DEEPSEEK_KEY? AI features (smart import, remarks parsing) will not work without it, but the roster generation still works. |
| "Module not found" error | Run `pip install -r requirements.txt` again |
| "Address already in use" | Another program is using port 8080. Stop it, or change the port in `app/main.py` line: `port=8080` |
| Google Sheets not updating | Wait 30 seconds (cache TTL). If still not updating, restart the app. |

---

## Daily Workflow (After Setup)

**Every week (2–3 minutes):**

1. Open the app (`python app/main.py` → http://localhost:8080)
2. Dashboard shows status dots — both should be green
3. Go to **Roster** → **Generate and View** tab
4. Click **Generate Roster** → review the table
5. If any prefect is on leave, go to **Adjust and Edit** tab → use Leave Adjustment
6. Click **Export PDF/HTML** to download the roster
7. Share the file in the prefect group chat

**When new prefects join or leave:**
- Edit directly in Google Sheets (or use the Prefects page)
- If a prefect has remarks like "固定星期一 Room 302", use **AI Parse Remarks** button to auto-fill their fixed duty and availability

---

*Last updated: 2026-06-24*
*Document maintained by the Head Study Prefect*
