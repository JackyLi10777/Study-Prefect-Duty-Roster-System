# Sing Yin Study Prefect Duty Roster System — Quick Start

**Daily workflow (2–3 minutes each week)**

## Every Week

1. Open the app: `python app/main.py` → http://localhost:8080
2. Check the Dashboard — both status dots should be green:
   - 🟢 Sheets Connected
   - 🟢 DeepSeek Ready
3. Go to **Roster** → **Generate and View** tab
4. Click **Generate Roster** → review the duty assignments
5. If needed, go to **Adjust and Edit** tab for leave adjustments or manual swaps
6. Click **Export PDF/HTML** to download the roster
7. Share the file in the prefect group chat

## Managing Prefects

- **Add a new prefect**: Go to **Prefects** page → **Add Prefect**
- **Update a prefect**: Edit directly in Google Sheets (simplest), or use the Prefects page
- **AI Smart Import**: On the Prefects page, click **AI Parse Remarks** to auto-fill fixed duties and availability from the Remarks column

## Backup

- **Backup**: Dashboard → **Backup System** → downloads a JSON file
- **Restore**: Dashboard → **Restore from Backup** → upload the JSON file
- Do this weekly — it takes 5 seconds and protects all your data



## First-Time Setup: Import Your Real Prefect Data

If you have not yet imported real school prefect data:
1. Prepare a CSV file with your prefect data (you can edit one in Excel)
2. Make a backup first: Dashboard → **Backup System** → download JSON
3. Go to **Prefects** → click **Import CSV**
4. Upload your CSV → review the mapping preview table (green badges = AI-confident, amber = alias match)
5. Adjust any wrong mappings via dropdown → click **Confirm Import**
6. Check the notification: it tells you how many prefects were imported and any warnings
7. Go to **Prefects** page → verify all names, forms, and roles look correct
8. Go to **Roster** → click **Generate Roster** to test

For detailed CSV column requirements, see HANDOVER.md Section 4.
## Need Help?

Read the full setup guide: `SETUP.md`
Contact the previous Head Study Prefect for assistance.
