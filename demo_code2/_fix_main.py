import pathlib

p = pathlib.Path(r"D:\code_v2\app\main.py")
c = p.read_text("utf-8")
changes = 0

# Fix 1: Design System page title
c = c.replace('"Professional Teal Design System v4.0"', 
               '_t("\u5c08\u696d\u9752\u85cd\u8272\u8a2d\u8a08\u7cfb\u7d71 v4.0", "Professional Teal Design System v4.0")')
changes += 1

# Fix 2: Design System subtitle
c = c.replace('"HyperOS Native - Sing Yin Secondary School Study Prefect Roster"',
               '_t("HyperOS Native - \u8056\u8a00\u4e2d\u5b78\u5b78\u7fd2\u98a8\u7d00\u503c\u73ed\u8868\u7cfb\u7d71", "HyperOS Native - Sing Yin Secondary School Study Prefect Roster")')
changes += 1

# Fix 3: KPI Cards label
c = c.replace('"KPI Cards (with HyperOS Gradient)"',
               '_t("KPI \u5361\u7247\uff08HyperOS \u6f38\u8b8a\u6548\u679c\uff09", "KPI Cards (with HyperOS Gradient)")')
changes += 1

# Fix 4: Buttons label
c = c.replace('"Buttons"', '_t("\u6309\u9215", "Buttons")')
changes += 1

# Fix 5: Button labels
c = c.replace('"Generate Roster"', '_t("\u751f\u6210\u503c\u73ed\u8868", "Generate Roster")')
c = c.replace('"Cancel"', '_t("\u53d6\u6d88", "Cancel")')
c = c.replace('"Delete"', '_t("\u522a\u9664", "Delete")')
changes += 3

# Fix 6: KPI values
c = c.replace('"Total Prefects"', '_t("\u7e3d\u98a8\u7d00\u6578", "Total Prefects")')
c = c.replace('"Avg Load (pts)"', '_t("\u5e73\u5747\u8ca0\u8377 (\u5206)", "Avg Load (pts)")')
c = c.replace('"Fairness Index"', '_t("\u516c\u5e73\u6307\u6578", "Fairness Index")')
c = c.replace('"Coverage Rate"', '_t("\u8986\u84cb\u7387", "Coverage Rate")')
changes += 4

# Add _t import at the top of the design function
if "from i18n.helpers import t as _t" not in c:
    old_func = "def design_system_page():\n    \"\"\"Professional Teal Design System v4.0 validation page.\"\"\"\n    from theme import Type"
    new_func = "def design_system_page():\n    \"\"\"Professional Teal Design System v4.0 validation page.\"\"\"\n    from i18n.helpers import t as _t\n    from theme import Type"
    c = c.replace(old_func, new_func)
    changes += 1
    print("Added _t import to design page")

p.write_text(c, "utf-8")
print(f"DONE: {changes} changes applied to main.py (Design System)")
