import pathlib, re, py_compile

def fix_triple_t(content):
    """Fix triple-nested _t() calls recursively"""
    # Pattern: _t("zh", _t("zh2", _t("zh3", "en"))) -> _t("zh", "en")
    # More generally: _t(X, _t(Y, _t(Z, W))) -> _t(X, W)
    pattern = r'_t\(("[^"]*"),\s*_t\(("[^"]*"),\s*_t\(("[^"]*"),\s*("[^"]*"\)\)\))'
    while True:
        new_content = re.sub(pattern, r'_t(\1, \4', content)
        if new_content == content:
            break
        content = new_content
    return content

# Fix roster.py
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c = p.read_text("utf-8")

# Fix triple-nested _t
c = fix_triple_t(c)

# Fix indentation: line 110 needs 16 spaces (inside with ui.tab_panel)
lines = c.split("\n")
for i, line in enumerate(lines):
    if i >= 108 and i <= 111:
        print(f"Line {i+1}: {line[:120]}")
    
# Fix line 109-110: line 110 needs to be indented under with block
c = c.replace(
    "            with ui.tab_panel(tab_adj):\n                # Leave Adjustment\n            with ui.expansion(",
    "            with ui.tab_panel(tab_adj):\n                # Leave Adjustment\n                with ui.expansion("
)

p.write_text(c, "utf-8")

try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py SYNTAX OK!")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")
    lines = c.split("\n")
    for i in [109, 110, 111, 144, 145, 146]:
        if i < len(lines):
            print(f"  L{i}: {lines[i-1][:120]}")

# Now fix prefects.py and dashboard.py for same triple-t issue
for fname in ["dashboard.py", "prefects.py"]:
    fp = pathlib.Path(r"D:\code_v2\app\pages") / fname
    c2 = fp.read_text("utf-8")
    c2 = fix_triple_t(c2)
    fp.write_text(c2, "utf-8")
    try:
        py_compile.compile(str(fp), doraise=True)
        print(f"{fname} SYNTAX OK")
    except py_compile.PyCompileError as e:
        print(f"{fname} SYNTAX ERROR: {e}")
