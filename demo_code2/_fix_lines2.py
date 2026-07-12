import pathlib, py_compile

# Fix roster.py: indent line 124 (+4) and lines 125-134 (+4)
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
lines = p.read_text("utf-8").split("\n")
# Line 124: add 4 spaces
lines[123] = "    " + lines[123]
# Lines 125-135: add 4 spaces (inside def body)
for i in range(124, 135):
    if i < len(lines) and lines[i].strip():
        cur_indent = len(lines[i]) - len(lines[i].lstrip())
        if cur_indent == 20:
            lines[i] = "    " + lines[i]
p.write_text("\n".join(lines), "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py OK!")
except py_compile.PyCompileError as e:
    print(f"roster.py: {str(e)[:200]}")

# Fix prefects.py: unindent line 351
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
lines2 = p2.read_text("utf-8").split("\n")
# Line 351 should match indent of line 350
lines2[350] = lines2[350][4:]  # remove 4 spaces
p2.write_text("\n".join(lines2), "utf-8")
try:
    py_compile.compile(str(p2), doraise=True)
    print("prefects.py OK!")
except py_compile.PyCompileError as e:
    print(f"prefects.py: {str(e)[:200]}")

# CHECK
print()
for f in [r"D:\code_v2\app\pages\dashboard.py", r"D:\code_v2\app\pages\roster.py", r"D:\code_v2\app\pages\prefects.py",
          r"D:\code_v2\app\pages\audit.py", r"D:\code_v2\app\main.py", r"D:\code_v2\app\theme.py", r"D:\code_v2\app\components\sidebar.py"]:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  OK: {pathlib.Path(f).name}")
    except py_compile.PyCompileError as e:
        print(f"  FAIL: {pathlib.Path(f).name}")
