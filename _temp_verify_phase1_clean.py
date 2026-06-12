"""Phase 1 clean verification script (no Chinese characters).
Only core checks for behavior preservation after refactoring.
"""

import sys
sys.path.insert(0, '.')

import pandas as pd

def main():
    print("=== Phase 1 Clean Verification ===")
    
    # Load demo data
    try:
        from data import get_demo_dataframe
        students = get_demo_dataframe()
        print("1. Demo data loaded: {} prefects".format(len(students)))
    except Exception as e:
        print("ERROR loading demo: {}".format(e))
        return
    
    # Generate roster with seed=42
    try:
        from core import generate_roster
        roster = generate_roster(students, [], [], seed=42, global_load_multiplier=1.0)
        print("2. generate_roster executed with seed=42")
    except Exception as e:
        print("ERROR in generate_roster: {}".format(e))
        return
    
    # AHP check: only in "Assist. in charge"
    assist_values = roster.loc["Assist. in charge"].values
    ahp_only = True
    for v in assist_values:
        if v and v not in ("X", "⬜") and "Assistant Head" not in str(v):
            ahp_only = False
            break
    print("3. AHP only in Assist. in charge: {}".format("PASS" if ahp_only else "FAIL"))
    
    # Room 302/303 open on all weekdays (no X or blank for these roles on Mon-Fri)
    days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
    room302_open = True
    room303_open = True
    for d in days:
        v302 = roster.at["Room 302 (Study Room)", d]
        v303 = roster.at["Room 303 (HW Completion) - 1", d]
        if v302 in ("", "X", "⬜"):
            room302_open = False
        if v303 in ("", "X", "⬜"):
            room303_open = False
    print("4. Room 302 open all weekdays: {}".format("PASS" if room302_open else "FAIL"))
    print("5. Room 303 open all weekdays: {}".format("PASS" if room303_open else "FAIL"))
    
    # 1 duty per day check
    one_per_day = True
    for d in days:
        day_values = []
        for role in roster.index:
            val = roster.at[role, d]
            if val and val not in ("X", "⬜"):
                day_values.append(val)
        if len(day_values) != len(set(day_values)):
            one_per_day = False
            break
    print("6. 1 duty per day (no duplicates): {}".format("PASS" if one_per_day else "FAIL"))
    
    # Same seed consistency
    roster2 = generate_roster(students, [], [], seed=42, global_load_multiplier=1.0)
    consistent = roster.equals(roster2)
    print("7. Same seed=42 produces identical roster: {}".format("PASS" if consistent else "FAIL"))
    
    print("\n=== Verification Complete ===")
    if ahp_only and room302_open and room303_open and one_per_day and consistent:
        print("ALL CORE CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED")

if __name__ == "__main__":
    main()
