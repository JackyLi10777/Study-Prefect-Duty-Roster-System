import pathlib

print("=== Verification of User-Reported Issues ===\n")

# 1. Design System page (main.py) - check _t() coverage
c = pathlib.Path(r"D:\code_v2\app\main.py").read_text("utf-8")
print("1. Design System page:")
print(f"   _t() calls: {c.count('_t(')}")
# Show all _t usages
import re
t_calls = re.findall(r'_t\("([^"]+)",\s*"([^"]+)"\)', c)
for zh, en in t_calls:
    print(f"   {zh} / {en}")
# Check for remaining English without _t in the design function
design_start = c.find("def design_system_page")
design_end = c.find("\n\n@", design_start)
design_code = c[design_start:design_end] if design_end > 0 else c[design_start:]
en_strings = re.findall(r'"([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)"', design_code)
print(f"   Remaining EN strings: {[s for s in en_strings if s not in ['Professional Teal','HyperOS Native','Sing Yin','KPI Cards','HyperOS Gradient','Generate Roster','Study Prefect','Total Prefects','Fairness Index','Coverage Rate','Avg Load']]}")

# 2. Audit Log page
c2 = pathlib.Path(r"D:\code_v2\app\pages\audit.py").read_text("utf-8")
print(f"\n2. Audit Log page: {c2.count('_t(')} _t() calls")
en_s = re.findall(r'"([A-Z][a-zA-Z\s]+)"', c2)
print(f"   EN strings: {[s for s in en_s if len(s) > 10 and s not in ['Track system actions','No audit records yet','Records appear automatically']][:5]}")

# 3. Prefects page - check prefect name display
c3 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py").read_text("utf-8")
print(f"\n3. Prefects page: {c3.count('_t(')} _t() calls")
# Check display_name logic
if "p.name_zh" in c3:
    print("   display_name uses name_zh: YES")
else:
    print("   display_name uses name_zh: NO - ISSUE!")
# Check for "Prefect Management" hardcoded
if '"Prefect Management"' in c3:
    print('   "Prefect Management" hardcoded: YES - ISSUE!')
else:
    print('   "Prefect Management" hardcoded: NO')

# 4. Roster page empty state
c4 = pathlib.Path(r"D:\code_v2\app\pages\roster.py").read_text("utf-8")
print(f"\n4. Roster page: empty state = {'YES' if 'No Roster Generated Yet' in c4 or '尚未生成' in c4 else 'NO - ISSUE!'}")

# 5. Scripture language-aware
c5 = pathlib.Path(r"D:\code_v2\app\pages\dashboard.py").read_text("utf-8")
print(f"\n5. Dashboard scripture:")
print(f"   language-aware: {'YES' if 'is_zh()' in c5 and 'verse.get' in c5 else 'NO'}")
print(f"   'scripture-zone' count: {c5.count('scripture-zone')} (should be 1 in CSS + 1 in code = 2)")

# 6. Dark mode sidebar
c6 = pathlib.Path(r"D:\code_v2\app\theme.py").read_text("utf-8")
print(f"\n6. Theme toggle: sidebar refresh = {'YES' if 'q-drawer' in c6 else 'NO - ISSUE!'}")

# 7. Dashboard buttons
print(f"\n7. Dashboard: {c5.count('_t(')} _t() calls")
en_buttons = re.findall(r'"([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)"', c5)
common = ['Operational Overview','Active Prefects','Study Prefects','Data Health Notes',
          'Quick Actions','Manage Prefects','Generate Roster','Open Prefects','Open Roster',
          'Open Leave','Backup System','Restore from Backup','Audit Log','Recent Changes',
          'Welcome to the','Daily scripture','Load Distribution','Mentoring Pairs','Backup Now']
remaining = [s for s in en_buttons if not any(c in s for c in common)]
print(f"   Remaining EN: {remaining[:8]}")
