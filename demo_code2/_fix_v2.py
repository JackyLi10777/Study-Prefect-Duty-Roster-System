import pathlib, py_compile, re

# Fix prefects.py: trailing comma in _t call
p = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c = p.read_text("utf-8")
# Pattern: label=_t("X", "Y",) -> label=_t("X", "Y"))
c = re.sub(r'_t\("([^"]+)"\s*,\s*"([^"]+)"\s*,\s*\)', r'_t("\1", "\2"))', c)
p.write_text(c, "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("prefects.py OK!")
except py_compile.PyCompileError as e:
    print(f"prefects.py: {str(e)[:200]}")

# Fix roster.py: the _apply_leave function body needs proper indent
p2 = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
lines = p2.read_text("utf-8").split("\n")
# Find _apply_leave function and indent its body
start_idx = None
for i, line in enumerate(lines):
    if line.strip() == "def _apply_leave():":
        start_idx = i
        base_indent = len(line) - len(line.lstrip())
        break

if start_idx:
    # Indent all subsequent non-empty lines at same level as def
    for i in range(start_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if not stripped:
            continue
        cur_indent = len(lines[i]) - len(lines[i].lstrip())
        if cur_indent < base_indent + 4:
            # Return to outer scope
            if cur_indent <= base_indent and stripped not in ("",):
                # Check if this is a comment or continuation
                if not stripped.startswith("#") and not stripped.startswith(")"):
                    break
        if cur_indent == base_indent:
            # Body should be base+4
            lines[i] = "    " + lines[i]

c2 = "\n".join(lines)
p2.write_text(c2, "utf-8")
try:
    py_compile.compile(str(p2), doraise=True)
    print("roster.py OK!")
except py_compile.PyCompileError as e:
    print(f"roster.py: {str(e)[:200]}")

print("\n=== FINAL ===")
for f in [r"D:\code_v2\app\pages\dashboard.py", r"D:\code_v2\app\pages\roster.py", r"D:\code_v2\app\pages\prefects.py"]:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  OK: {pathlib.Path(f).name}")
    except py_compile.PyCompileError:
        print(f"  FAIL: {pathlib.Path(f).name}")
