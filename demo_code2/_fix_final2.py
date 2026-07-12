import pathlib, py_compile, re

# Fix roster.py: indent lines 123-140 (inside def _apply_leave)
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
lines = p.read_text("utf-8").split("\n")

# Find def _apply_leave(): and indent everything until next def or empty line at same level
in_apply_leave = False
apply_leave_indent = 0
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("def _apply_leave():"):
        in_apply_leave = True
        apply_leave_indent = len(line) - len(line.lstrip())
        continue
    if in_apply_leave:
        current_indent = len(line) - len(line.lstrip())
        if stripped == "" or current_indent <= apply_leave_indent:
            in_apply_leave = False
        elif current_indent < apply_leave_indent + 4:
            # Add 4 more spaces
            lines[i] = "    " + line

c = "\n".join(lines)
p.write_text(c, "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py OK!")
except py_compile.PyCompileError as e:
    print(f"roster.py: {e}")

# Fix prefects.py: line 126 has "},)" should be "},"
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c2 = p2.read_text("utf-8")
# Fix: "活跃","Active"),"zh":"活踍"},) -> "活跃","Active"),"zh":"活踍"},
c2 = re.sub(r'\},\s*\)\s*$', r'},', c2, flags=re.MULTILINE)
p2.write_text(c2, "utf-8")
try:
    py_compile.compile(str(p2), doraise=True)
    print("prefects.py OK!")
except py_compile.PyCompileError as e:
    print(f"prefects.py: {e}")
    lines2 = c2.split("\n")
    for i in range(124, min(128, len(lines2))):
        print(f"  L{i+1}: {lines2[i][:150]}")

# Verify all
print("\n=== VERIFY ===")
for fpath in [
    r"D:\code_v2\app\pages\dashboard.py",
    r"D:\code_v2\app\pages\roster.py",
    r"D:\code_v2\app\pages\prefects.py",
    r"D:\code_v2\app\pages\audit.py",
    r"D:\code_v2\app\main.py",
]:
    try:
        py_compile.compile(fpath, doraise=True)
        print(f"  OK: {pathlib.Path(fpath).name}")
    except py_compile.PyCompileError as e:
        print(f"  FAIL: {pathlib.Path(fpath).name}: {str(e)[:120]}")
