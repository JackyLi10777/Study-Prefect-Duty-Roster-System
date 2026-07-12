import pathlib, py_compile, re

# ====== ULTIMATE FIX: Use structural pattern matching (not exact string matching) ======

# FIX prefects.py: The issue is trailing comma in _t calls like: _t("X","Y",)
# And doubly-nested _t like: _t("X", _t("X","Y")
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c2 = p2.read_text("utf-8")

# Remove all double-nested _t(X, _t(X, Y) patterns
while True:
    new_c2 = re.sub(r'_t\(("[^"]*")\s*,\s*_t\("[^"]*"\s*,\s*("[^"]*")\s*\)', r'_t(\1, \2', c2)
    if new_c2 == c2:
        break
    c2 = new_c2

# Remove trailing comma in _t args: _t("X","Y",) -> _t("X","Y")
c2 = re.sub(r'_t\(("[^"]+")\s*,\s*("[^"]+")\s*,\s*\)', r'_t(\1, \2)', c2)

# Remove extra closing parens: _t("X","Y")) -> _t("X","Y")
c2 = re.sub(r'_t\(("[^"]+")\s*,\s*("[^"]+")\s*\)\s*\)', r'_t(\1, \2)', c2)

p2.write_text(c2, "utf-8")
try:
    py_compile.compile(str(p2), doraise=True)
    print("prefects.py OK!")
except py_compile.PyCompileError as e:
    print(f"prefects.py: {e}")

# FIX roster.py: Fix indentation of _apply_leave function body
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
lines = p.read_text("utf-8").split("\n")

# Find def _apply_leave and fix body indentation
in_func = False
func_base = 0
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped == "def _apply_leave():":
        in_func = True
        func_base = len(line) - len(line.lstrip())
        continue
    if in_func:
        if stripped == "":
            continue
        cur_indent = len(line) - len(line.lstrip())
        if cur_indent <= func_base and not stripped.startswith("#"):
            in_func = False
            continue
        # If body line is at same indent as def, add 4 spaces
        if cur_indent == func_base:
            lines[i] = "    " + line

c = "\n".join(lines)
p.write_text(c, "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py OK!")
except py_compile.PyCompileError as e:
    print(f"roster.py: {e}")

print()
for f in [r"D:\code_v2\app\pages\dashboard.py", r"D:\code_v2\app\pages\roster.py", r"D:\code_v2\app\pages\prefects.py"]:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  OK: {pathlib.Path(f).name}")
    except py_compile.PyCompileError:
        print(f"  FAIL: {pathlib.Path(f).name}")
