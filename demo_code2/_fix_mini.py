import pathlib, py_compile, re

# Fix roster.py: try block indent
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
lines = p.read_text("utf-8").split("\n")
# Line 135: add 4 spaces (inside try block)
lines[134] = "    " + lines[134]
p.write_text("\n".join(lines), "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py OK!")
except py_compile.PyCompileError as e:
    print(f"roster.py: {e}")

# Fix prefects.py: extra ) from regex
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c2 = p2.read_text("utf-8")
# Fix: _t("X", "Y")) -> _t("X", "Y")
c2 = re.sub(r'_t\("([^"]+)"\s*,\s*"([^"]+)"\)\)', r'_t("\1", "\2")', c2)
p2.write_text(c2, "utf-8")
try:
    py_compile.compile(str(p2), doraise=True)
    print("prefects.py OK!")
except py_compile.PyCompileError as e:
    print(f"prefects.py: {e}")

# Quick check all
print()
for f in [r"D:\code_v2\app\pages\dashboard.py", r"D:\code_v2\app\pages\roster.py", r"D:\code_v2\app\pages\prefects.py"]:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  OK: {pathlib.Path(f).name}")
    except py_compile.PyCompileError:
        print(f"  FAIL: {pathlib.Path(f).name}")
