import pathlib, py_compile
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c = p.read_text("utf-8")

# Fix indentation: line 109 should be indented under with block
c = c.replace("            with ui.tab_panel(tab_adj):\n            # Leave Adjustment",
               "            with ui.tab_panel(tab_adj):\n                # Leave Adjustment")

# Fix triple-nested _t (all on one logical line)
import re
# Find the pattern and fix it
old_pattern = '_t("\u8acb\u5047\u8abf\u6574", _t("\u8acb\u5047\u8abf\u6574", _t("\u8acb\u5047\u8abf\u6574", "Leave Adjustment")))'
if old_pattern in c:
    c = c.replace(old_pattern, '_t("\u8acb\u5047\u8abf\u6574", "Leave Adjustment")')
    print("Fixed triple-nested _t")

# Also check for other corrupted patterns
corruptions = [
    ('_t("\u624b\u52d5\u7de8\u8f2f / \u66ff\u88dc", "_t(\\"\u624b\u52d5\u7de8\u8f2f / \u66ff\u88dc\\", \\"Manual Edit / Substitute\\")")', 
     '_t("\u624b\u52d5\u7de8\u8f2f / \u66ff\u88dc", "Manual Edit / Substitute")'),
]
for old_p, new_p in corruptions:
    if old_p in c:
        c = c.replace(old_p, new_p)
        print(f"Fixed corruption")

p.write_text(c, "utf-8")

try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py SYNTAX OK")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")
    # Show the problematic line
    lines = c.split("\n")
    print(f"Line 108: {lines[107]}")
    print(f"Line 109: {lines[108]}")
    print(f"Line 110: {lines[109]}")
