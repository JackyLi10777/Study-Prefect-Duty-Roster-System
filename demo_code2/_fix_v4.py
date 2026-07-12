import pathlib, py_compile

# FIX prefects.py: remove orphaned ) after line continuation \
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c2 = p2.read_text("utf-8")
# Lines end with: ) \)  -> should be: ) \
c2 = c2.replace(") \\)\n", ") \\\n")
p2.write_text(c2, "utf-8")
try:
    py_compile.compile(str(p2), doraise=True)
    print("prefects.py OK!")
except py_compile.PyCompileError as e:
    print(f"prefects.py: {e}")

# FIX roster.py: try/if body indentation
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
lines = p.read_text("utf-8").split("\n")
# Line 135 (idx 134): "if daily:" should be at 24+4=28 but is at 24 after fix, needs 28
# Actually line 134 (daily = ) is at 28, line 135 (if daily:) is at 24 -> needs 28
lines[134] = "    " + lines[134]  # if daily: 20+4+4=28
# Lines 136-138: body of if - check
for i in range(135, min(140, len(lines))):
    stripped = lines[i].strip()
    if not stripped:
        continue
    cur_indent = len(lines[i]) - len(lines[i].lstrip())
    if cur_indent <= 28 and 135 <= i <= 139:
        lines[i] = "    " + lines[i]  # inside if body
p.write_text("\n".join(lines), "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py OK!")
except py_compile.PyCompileError as e:
    print(f"roster.py: {e}")
    # Show lines around error
    import re
    m = re.search(r'line (\d+)', str(e))
    if m:
        ln = int(m.group(1))
        for off in range(-2, 3):
            i = ln + off - 1
            if 0 <= i < len(lines):
                sp = len(lines[i]) - len(lines[i].lstrip())
                print(f"  L{i+1} ({sp}sp): {lines[i][:130]}")

print()
for f in ["dashboard.py","roster.py","prefects.py"]:
    fp = pathlib.Path(f"D:/code_v2/app/pages/{f}")
    try:
        py_compile.compile(str(fp), doraise=True)
        print(f"  OK: {f}")
    except py_compile.PyCompileError:
        print(f"  FAIL: {f}")
