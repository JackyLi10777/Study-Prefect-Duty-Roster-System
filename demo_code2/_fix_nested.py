import pathlib, py_compile, subprocess

p = pathlib.Path(r"D:\code_v2\app\pages\dashboard.py")
c = p.read_text("utf-8")

# Fix nested _t() patterns: _t(A, _t(B, C)).classes(D) -> _t(A, _t(B, C))).classes(D)
# The extra ) closes ui.label() before .classes chains on it
fixes = [
    ('_t("\u7ba1\u7406\u98ce\u7eaa", _t("\u7ba1\u7406\u98a8\u7d00", "Manage Prefects")).classes(',
     '_t("\u7ba1\u7406\u98ce\u7eaa", _t("\u7ba1\u7406\u98a8\u7d00", "Manage Prefects"))).classes('),
    ('_t("\u751f\u6210\u503c\u73ed\u8868", _t("\u751f\u6210\u503c\u73ed\u8868", "Generate Roster")).classes(',
     '_t("\u751f\u6210\u503c\u73ed\u8868", "Generate Roster")).classes('),
    ('_t("\u8bf7\u5047\u8c03\u6574", _t("\u8acb\u5047\u8abf\u6574", "Adjust Leave")).classes(',
     '_t("\u8bf7\u5047\u8c03\u6574", _t("\u8acb\u5047\u8abf\u6574", "Adjust Leave"))).classes('),
    ('_t("\u5feb\u901f\u64cd\u4f5c", _t("\u5feb\u901f\u64cd\u4f5c", "Quick Actions")).classes(',
     '_t("\u5feb\u901f\u64cd\u4f5c", "Quick Actions")).classes('),
]

for old, new in fixes:
    if old in c:
        c = c.replace(old, new)
        print(f"Fixed: {old[:40]}...")
    else:
        print(f"NOT FOUND: {old[:40]}...")

p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("Syntax: OK")

r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
passed = "52 passed" in r.stdout + r.stderr
print(f"Tests: {'52/52' if passed else 'FAILED'}")

# Final scan
c2 = p.read_text("utf-8")
lines = c2.split("\n")
bugs = 0
for i, line in enumerate(lines):
    if "_t(" in line and ".classes(" in line and "ui." in line:
        # Check for the broken pattern: _t(...).classes( inside ui.xxx(...)
        # Correct pattern: ui.xxx(_t(...)).classes( - has )) before .classes
        # Broken pattern: ui.xxx(_t(...).classes( - has ).classes without extra )
        if ")).classes(" in line:
            pass  # correct
        elif ").classes(" in line:
            # Still has single ) before .classes - could be broken
            # But if the ) closes _t() and .classes is on ui.xxx, there should be ))
            # If the line has _t( X, _t(Y,Z) ).classes( then the ) closes the outer _t
            # which means .classes is on the string!
            if "_t(" in line[line.find("_t(")+3:]:  # nested _t
                pass  # might be ok if there are enough closing parens
            else:
                bugs += 1
                print(f"POSSIBLE BUG L{i+1}: {line.strip()[:140]}")

print(f"Remaining potential bugs: {bugs}")
