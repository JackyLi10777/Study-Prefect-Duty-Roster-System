import pathlib, py_compile, re

def auto_fix_indentation(filepath):
    """Fix common indentation issues: def/if body at wrong indent."""
    lines = pathlib.Path(filepath).read_text("utf-8").split("\n")
    stack = []  # (indent_level, keyword)
    fixed = list(lines)
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        cur_indent = len(line) - len(line.lstrip())
        
        # Track def/with/if blocks
        if stripped.startswith("def ") and stripped.endswith(":"):
            # Next line should be cur_indent + 4
            for j in range(i+1, min(i+20, len(lines))):
                nxt = lines[j].strip()
                if not nxt:
                    continue
                nxt_indent = len(lines[j]) - len(lines[j].lstrip())
                if nxt_indent <= cur_indent:
                    # Fix: add 4 spaces
                    fixed[j] = "    " + lines[j]
                break
    
    return "\n".join(fixed)

# Fix roster.py
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c = auto_fix_indentation(str(p))
p.write_text(c, "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py OK!")
except py_compile.PyCompileError as e:
    print(f"roster.py: {str(e)[:200]}")

# Fix prefects.py: remove all double _t patterns
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c2 = p2.read_text("utf-8")
# Remove double-nested _t("X", _t("X", "Y") -> _t("X", "Y")
for _ in range(10):
    c2 = re.sub(r'_t\("([^"]*)"\s*,\s*_t\("[^"]*"\s*,\s*"([^"]*)"\s*\)', r'_t("\1", "\2"', c2)
# Fix extra closing parens after _t
c2 = re.sub(r'_t\(("[^"]*")\s*,\s*("[^"]*")\)\)', r'_t(\1, \2)', c2)
# Fix trailing comma in _t args: _t("X", "Y"),) -> _t("X", "Y"))
c2 = re.sub(r'_t\(("[^"]*")\s*,\s*("[^"]*")\s*\),\s*\)', r'_t(\1, \2))', c2)
p2.write_text(c2, "utf-8")
try:
    py_compile.compile(str(p2), doraise=True)
    print("prefects.py OK!")
except py_compile.PyCompileError as e:
    print(f"prefects.py: {str(e)[:200]}")
    import re as re2
    m = re2.search(r'line (\d+)', str(e))
    if m:
        ln = int(m.group(1))
        lines2 = c2.split("\n")
        for offset in range(-2, 3):
            idx = ln + offset - 1
            if 0 <= idx < len(lines2):
                print(f"  L{idx+1}: {lines2[idx][:150]}")

print("\n=== FINAL ===")
for f in [r"D:\code_v2\app\pages\dashboard.py", r"D:\code_v2\app\pages\roster.py", r"D:\code_v2\app\pages\prefects.py"]:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  OK: {pathlib.Path(f).name}")
    except py_compile.PyCompileError:
        print(f"  FAIL: {pathlib.Path(f).name}")
