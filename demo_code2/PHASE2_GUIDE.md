# Phase 2 — Real Data Testing Guide

**Sing Yin Study Prefect Duty Roster System**
**For:** Head Study Prefect preparing to use real school prefect data
**Time to read:** 5 minutes
**Purpose:** Safe, confident transition from demo data to real production use

---

## Overview — You Can Do This!

Welcome! You've practiced with demo data, and now you're ready for the real thing. **This is an exciting step** — you're about to start generating actual weekly duty rosters for the Sing Yin Study Prefect team.

Here's the good news: the system has **multiple safety nets** built in:
- **Backup system** — you can undo anything with one click
- **Duplicate detection** — the system warns you if two prefects have the same name
- **Import summary** — after importing, you'll see exactly what changed
- **State guards** — the system prevents common mistakes before they happen

**If anything feels off, you can always roll back.** There's no way to permanently lose data if you follow the backup step below. Let's get started!

---

## 1. Safe Workflow: First Real Data Import

### Before You Start (2 minutes)

- [ ] **Take a backup.** Dashboard → Backup System → download JSON. Save as `backup_before_real_import.json`.
- [ ] **Open your real prefect data** in Excel or Google Sheets.
- [ ] **Check these things:**

| Check This | Why It Matters |
|-----------|----------------|
| At least 5 active prefects? | 3 minimum; 5+ gives much fairer assignments |
| All names unique? (No duplicate English names) | The system uses names as IDs |
| Roles correct? (Study Prefect / Assistant Head Study Prefect / Head Study Prefect) | "AHP" and "assistant head" are also accepted |
| Forms in right format? (F3, F4, F5 — not "F.3" or "Form 3") | Wrong format → defaulted to F4 |
| Remarks in Chinese? (e.g., "固定星期一 Room 302") | AI can auto-parse these into fixed duties |

### Import Step by Step

1. **Prefects page** → **Import CSV**
2. **Upload your CSV file**
3. **Review the mapping preview:**
   - 🟢 Green = AI-confident mapping
   - 🟡 Amber = Matched by name similarity
   - ⬜ Gray = Not mapped — use the dropdown to map it manually
4. **Fix any wrong mappings** via the dropdowns
5. **Click "確認匯入 (Confirm Import)"**
6. **Read the confirmation notification:**
   - How many prefects imported?
   - Any "invalid form" warnings? → Those were set to F4 — fix them on the Prefects page
   - Any "duplicate name" warnings? → Duplicates were skipped — check your CSV
7. **Prefects page** → verify the table:
   - All names present?
   - Roles correct? (AHP = "Assistant Head Study Prefect")
   - Forms correct? (not all F4)
8. **Roster page** → **Generate Roster** (test run)
9. **Take another backup** → Dashboard → Backup System → `backup_after_import.json`

---

## 2. How to Know Your Import Was Successful ✅

After completing the steps above, you should see:

- ✅ **Prefects page** shows all your prefects with correct names, roles, and forms
- ✅ **Generate Roster** produces a 5-day roster without errors
- ✅ **Dashboard KPI** shows the correct number of active prefects and AHPs
- ✅ **No red error notifications** when generating

If you see all four of these, your import was successful! 🎉

---

## 3. Demo Data vs Real Data

| | Demo Data | Real Data |
|---|----------|-----------|
| Purpose | Practice, testing, demo | Actual school operations |
| Load via | Prefects → Load Demo Data | Prefects → Import CSV |
| Content | 11 sample prefects + fake history | Your actual school prefects |
| Safe to overwrite? | Yes — reload anytime | No — always backup first! |

**Tip:** Practice the import flow with demo data first. When ready, switch to real data.

---

## 4. ⚠️ Rollback: What to Do If Something Goes Wrong

**Don't panic!** You have a backup. Here's how to undo:

> 1. Dashboard → **Restore from Backup**
> 2. Upload `backup_before_real_import.json`
> 3. System restores everything to pre-import state
> 4. Verify Prefects page — your old data is back

**Key rule: Always backup before importing.** You cannot lose data permanently if you follow this rule.

---

## 5. First Real Roster: What to Observe

After generating your first real roster, check:

| Area | What to Look For |
|------|-----------------|
| **AHP posts** | One per day (Mon–Fri), each assigned to a different AHP |
| **Room 202** | Empty on Tuesday and Friday (it's closed those days) |
| **Room 202** | Filled on Mon, Wed, Thu (2 prefects each) |
| **Room 302** | 1 prefect per day |
| **Room 303** | 2 prefects per day |
| **Fairness** | Junior prefects (lower history_weight) should generally get more assignments |
| **Dashboard chart** | Should show meaningful differences between prefects after generation |

If the roster looks roughly balanced with no glaring gaps, **you're doing it right.**

---

## 6. Common First-Time Concerns

**"What if I make a mistake during import?"**
→ Restore from the backup you made in Step 1. Takes 10 seconds. No data is lost.

**"Will importing real data delete my demo data?"**
→ Yes — importing replaces current data. That's why you backup first. You can always switch back and forth.

**"Will the first roster look messy?"**
→ Possibly! Real data is imperfect. Some slots may be unfilled (shown as yellow warnings). That's normal — it tells you which days need more prefects.

**"What if Google Sheets status is red?"**
→ The system still works using local CSV storage. Your data is safe. Green status just means cloud sync is active. See SETUP.md Step 3-4 to fix.

**"Can I test before committing?"**
→ Yes! Load Demo Data first, practice the import flow, then restore your backup and import real data when ready.

---

## 7. First 2 Weeks of Real Usage

### Week 1 — Getting Started
- [ ] Import real prefect data (follow Section 1)
- [ ] Generate Week 1 roster — review assignments
- [ ] Export PDF and share with the prefect team
- [ ] Note any surprises (wrong forms, missing prefects, etc.)

### Week 2 — Going Deeper
- [ ] Generate Week 2 roster — fairness should now reflect Week 1 history
- [ ] Try a **leave adjustment**: simulate one prefect absent → apply a substitute
- [ ] Check the Dashboard **fairness chart** — does it show meaningful differences?
- [ ] Try **AI Parse Remarks** if Remarks column has Chinese text
- [ ] Do a **manual backup** (Dashboard → Backup System)

### After 2 Weeks — You're a Pro
- [ ] Update FAQ.md if you found new common issues
- [ ] Clean up old auto-backups (keep last 10–20)
- [ ] Update prefect data (new joiners, leavers, form changes)
- [ ] **Congratulations!** You're now running the roster system confidently.

---

## 8. Quick Troubleshooting

| Situation | What to Do |
|-----------|-----------|
| "Only 2 active prefects" | You need at least 3 active prefects. Check Prefects page. |
| A prefect never gets assigned | Check their available days. Only Mon–Wed means no Thu–Fri assignments. |
| Room 202 has assignments Tue/Fri | This is a bug — Room 202 is closed those days. Take a screenshot. |
| AI Parse Remarks not working | Is `SY_DEEPSEEK_KEY` set? Check Dashboard status dot. |
| "0 prefects imported" | Check CSV column names. Try Load Demo Data first to verify import works. |

---

*This guide was prepared on 2026-06-27. Update it as you gain experience with real data.*
