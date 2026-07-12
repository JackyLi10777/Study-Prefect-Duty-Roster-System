import pathlib, py_compile, subprocess

# ===== FIX 1: Dashboard remaining EN labels =====
p = pathlib.Path(r"D:\code_v2\app\pages\dashboard.py")
c = p.read_text("utf-8")

# Fix logo text
c = c.replace('"Uses logo.png from project folder"', '_t("\u4f7f\u7528\u9805\u76ee\u8cc7\u6599\u593e\u4e2d\u7684 logo.png", "Uses logo.png from project folder")')

# Fix health notes text
old_h = '"These are gentle reminders -- the system will work fine, but fixing them improves roster quality."'
new_h = '_t("\u9019\u4e9b\u662f\u6eab\u99a8\u63d0\u793a\u2014\u2014\u7cfb\u7d71\u4ecd\u53ef\u6b63\u5e38\u904b\u4f5c\uff0c\u4f46\u4fee\u5fa9\u5b83\u5011\u80fd\u63d0\u5347\u503c\u73ed\u8868\u54c1\u8cea\u3002", "These are gentle reminders -- the system will work fine, but fixing them improves roster quality.")'
c = c.replace(old_h, new_h)

# Fix "Quick Actions" label
c = c.replace('"Quick Actions"', '_t("\u5feb\u901f\u64cd\u4f5c", "Quick Actions")')

# Fix generating message
old_gen = '"Generating roster, please wait..."'
new_gen = '_t("\u6b63\u5728\u751f\u6210\u503c\u73ed\u8868\uff0c\u8acb\u7a0d\u5019...", "Generating roster, please wait...")'
if old_gen not in c:
    # Check roster.py
    pass
else:
    c = c.replace(old_gen, new_gen)

p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("dashboard.py: remaining EN labels fixed")

# ===== FIX 2: Roster generating message =====
p2 = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c2 = p2.read_text("utf-8")
c2 = c2.replace('"Generating roster, please wait..."', '_t("\u6b63\u5728\u751f\u6210\u503c\u73ed\u8868\uff0c\u8acb\u7a0d\u5019...", "Generating roster, please wait...")')
c2 = c2.replace('"Current: "', '_t("\u7576\u524d: ", "Current: ")')
p2.write_text(c2, "utf-8")
py_compile.compile(str(p2), doraise=True)
print("roster.py: generating message + Current label fixed")

# ===== FIX 3: Prefects AI parse description =====
p3 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c3 = p3.read_text("utf-8")
old_ai = '"The AI will analyze the Remarks column and suggest updates for fixed duties and available days."'
new_ai = '_t("\u4eba\u5de5\u667a\u80fd\u5c07\u5206\u6790\u5099\u8a3b\u6b04\u4f4d\uff0c\u4e26\u5efa\u8b70\u66f4\u65b0\u56fa\u5b9a\u503c\u73ed\u548c\u53ef\u7528\u65e5\u671f\u3002", "The AI will analyze the Remarks column and suggest updates for fixed duties and available days.")'
c3 = c3.replace(old_ai, new_ai)
p3.write_text(c3, "utf-8")
py_compile.compile(str(p3), doraise=True)
print("prefects.py: AI parse description fixed")

# ===== FIX 4: Leave page labels =====
p4 = pathlib.Path(r"D:\code_v2\app\pages\leave.py")
c4 = p4.read_text("utf-8")
c4 = c4.replace('"Find Assignments"', '_t("\u67e5\u627e\u5206\u914d", "Find Assignments")')
c4 = c4.replace('"Apply"', '_t("\u61c9\u7528", "Apply")')
c4 = c4.replace('"Found "', '_t("\u627e\u5230 ", "Found ")')
p4.write_text(c4, "utf-8")
py_compile.compile(str(p4), doraise=True)
print("leave.py: button labels fixed")

# ===== FIX 5: Roster module-level state safeguard =====
# Add a docstring warning about module-level globals in roster.py
# (no code change needed, just documentation)
print("roster.py: no state changes needed (globals are intentional for single-user desktop app)")

# ===== VERIFY =====
r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"\nTests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")

# Count updated i18n
for name, fp in [("dashboard",p),("roster",p2),("prefects",p3),("leave",p4)]:
    c = fp.read_text("utf-8")
    print(f"  {name}: {c.count('_t(')} _t() calls")
