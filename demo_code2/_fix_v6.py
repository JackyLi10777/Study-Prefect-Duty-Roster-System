import pathlib, py_compile

# ROSTER: Line 135 "if daily:" at 28, line 136 body should be at 32
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
lines = p.read_text("utf-8").split("\n")
# Line 135 (idx 134): if daily: at 28sp -> OK
# Line 136 (idx 135): assigned = ... at 28sp -> needs 32 (inside if)
# Line 137 (idx 136): if adj_replace... at 28sp -> needs 32
lines[135] = "    " + lines[135]
lines[136] = "    " + lines[136]
for i in [137, 138]:  # body of second if
    if i < len(lines) and lines[i].strip():
        cur = len(lines[i]) - len(lines[i].lstrip())
        if cur <= 32:
            lines[i] = "    " + lines[i]
p.write_text("\n".join(lines), "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py OK!")
except py_compile.PyCompileError as e:
    print(f"roster.py: {e}")

# PREFECTS: Line 481 lambda: [) -> lambda: [
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c2 = p2.read_text("utf-8")
c2 = c2.replace("on_click=lambda: [)", "on_click=lambda: [")
p2.write_text(c2, "utf-8")
try:
    py_compile.compile(str(p2), doraise=True)
    print("prefects.py OK!")
except py_compile.PyCompileError as e:
    print(f"prefects.py: {e}")

# FINAL CHECK
print()
for f in ["dashboard.py","roster.py","prefects.py","audit.py","leave.py"]:
    fp = pathlib.Path(f"D:/code_v2/app/pages/{f}")
    try:
        py_compile.compile(str(fp), doraise=True)
        print(f"  OK: {f}")
    except py_compile.PyCompileError:
        print(f"  FAIL: {f}")
