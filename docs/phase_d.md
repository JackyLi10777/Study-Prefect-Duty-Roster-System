# Phase D: Mentoring Analytics Dashboard

**聖言中學導學風紀當值排班平台 — 師徒配對分析儀表板**

Version: v2.4+ (Phase D)
Date: 2026-06-19

---

## Overview

Phase D builds on the Automated Mentoring Pairing engine (Phase C) by adding lightweight analytics that help the Head Study Prefect measure and track the mentoring program's effectiveness.

## Features

### 1. Pairing Effectiveness Card

**Location:** Fairness/Dashboard sidebar section (after roster generation)

A 3-column `st.metric` card displaying:

| Metric | Description |
|--------|-------------|
| 🤝 Mentoring Pairs | Number of mentor-mentee pairs formed this week vs. total possible |
| 📊 Pairing Rate | Percentage of possible 2-slot rooms that formed a pair |
| 🏷️ Rating | Qualitative assessment: Excellent (≥50%), Good (≥25%), Fair (<25%) |

**How it works:** Calls `annotate_mentoring_pairs()` on the current roster and students DataFrame. The denominator (possible pairs) is dynamically computed from the roster structure — it counts 2-slot rooms (Room 303 + Room 202) on days where both slots are open (not ⬜).

**Code:** `roster/ui/components.py` -> `render_pairing_effectiveness_card()`
**Helper:** `roster/core/engine.py` -> `compute_possible_mentoring_pairs()` (pure function, independently testable) → `render_pairing_effectiveness_card()`

### 2. Mentee Progress Tracker

**Location:** Collapsible expander below the Pairing Card

A table showing all students currently flagged as needing mentoring (`history_weight ≤ 2` or `needs_mentoring=True`) with:

| Column | Description |
|--------|-------------|
| Name / 姓名 | Student name |
| Form / 年級 | Form level (F.3-F.5) |
| Current Weight / 當前點數 | Current `history_weight` |
| Change / 變化 | Weight difference since baseline (+ improving, - needs attention) |
| Trend / 趨勢 | Visual indicator: ⬇ Improving / ➡ Stable / ⬆ Needs attention / － No baseline |

**Baseline workflow:**
1. Click "📸 Save Current as Baseline" to snapshot all mentee weights
2. Generate a new roster (which updates `history_weight`)
3. Return to the tracker to see per-student weight changes and trends
4. Click "🗑️ Clear Baseline" to reset

**Storage:** Uses `st.session_state.mentee_baseline` (dict of name → weight) and `st.session_state.mentee_baseline_date`. No persistent storage — baseline resets on app restart.

**Code:** `roster/ui/components.py` -> `render_pairing_effectiveness_card()`
**Helper:** `roster/core/engine.py` -> `compute_possible_mentoring_pairs()` (pure function, independently testable) → `render_mentee_progress_tracker()`

### 3. Roster Board Mentoring Indicators

**Location:** Main roster board

When a mentor-mentee pair is assigned to the same 2-slot room (Room 303 or Room 202 on open days), both cells display:
- Teal left border (`border-left:4px solid #0F766E`)
- Tinted background (`rgba(15,118,110,0.08)`)

A legend above the board explains all mentoring-related badges.

## Badge Color System

| Badge | Color | Hex | Meaning |
|-------|-------|-----|---------|
| 🤝 師徒配對 | Teal | `#0F766E` | Mentoring pair in this room |
| 🆕 新加入 | Teal | `#0F766E` | New prefect (history_weight=0) |
| 👤 需要老帶新 | Amber | `#F59E0B` | Auto-detected mentee (hw ≤ 2) |
| ✅ 指定老帶新 | Purple | `#7C3AED` | Manually flagged as needing mentoring |
| 一般 | Gray | `#6B7280` | Normal (not mentee or mentor) |

## Defensive Coding

The Mentee Progress Tracker handles these edge cases:

| Case | Behavior |
|------|----------|
| Missing `needs_mentoring` column | Defaults to `False` for all students |
| Empty mentee list | Shows info message instead of empty table |
| Students deleted after baseline capture | Silently skipped (no crash) |
| Baseline cleared mid-session | Resets to "No baseline" display |



## Deployment Verification Checklist

After each deployment to Streamlit Cloud, verify:

### Pairing Effectiveness Card
- [ ] Card appears in sidebar after roster generation
- [ ] 3 columns display: Pairs (X/8), Rate (X%), Rating (Excellent/Good/Fair)
- [ ] Values update after generating new roster
- [ ] Readable in both Light and Dark modes

### Mentee Progress Tracker
- [ ] Expander opens/closes smoothly
- [ ] Table shows students with history_weight <= 2 or needs_mentoring=True
- [ ] Save Baseline snapshots weights; Clear Baseline resets
- [ ] Trend indicators (?/?/?) correct after generating new roster
- [ ] Empty mentee list shows info message
- [ ] Missing needs_mentoring column handled gracefully

### Badge System
- [ ] All 5 badge colors match documented hex values
- [ ] Badges consistent between auto-tag legend and roster board legend

### Roster Board
- [ ] Mentoring pair cells: teal left border (#0F766E) + tinted background
- [ ] Room 202 Tue/Fri shows ?, no pairing highlight

### General
- [ ] 49/49 tests passing
- [ ] No browser console errors

## Future Enhancements (Phase D Priority 3+)

- **Weekly Mentoring Summary in PDF**: Add a summary section to exported PDFs showing pair count, rate, and mentee list
- **Automatic baseline snapshots**: Auto-save baseline on first visit each week
- **Multi-week sparkline chart**: Visualize mentee weight trends over time
- **Pairing quality vs. random baseline**: Statistical comparison of actual pair rate vs. expected

## Related Files

| File | Role |
|------|------|
| `roster/ui/components.py` | `render_pairing_effectiveness_card()`, `render_mentee_progress_tracker()` |
| `app.py` | Calls both functions in the fairness dashboard section |
| `roster/core/engine.py` | `annotate_mentoring_pairs()`, `_is_mentee()`, `_is_mentor()` |
| `tests/test_engine.py` | `TestMentoringPairing` class (10 tests) |
