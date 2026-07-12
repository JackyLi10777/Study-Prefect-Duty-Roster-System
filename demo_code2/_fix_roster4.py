import pathlib, py_compile
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c = p.read_text("utf-8")

# Fix line 110: wrong indentation (12 spaces, needs 16) + triple nested _t
old_110 = '            with ui.expansion(_t("\u8acb\u5047\u8abf\u6574", _t("\u8acb\u5047\u8abf\u6574", _t("\u8acb\u5047\u8abf\u6574", "Leave Adjustment"))), icon="event_busy").classes("w-full"):'
new_110 = '                with ui.expansion(_t("\u8acb\u5047\u8abf\u6574", "Leave Adjustment"), icon="event_busy").classes("w-full"):'
if old_110 in c:
    c = c.replace(old_110, new_110)
    print("Fixed line 110 indentation + _t")
else:
    print(f"Pattern not found, trying alternatives...")
    # Find the line
    for i, line in enumerate(c.split("\n")):
        if "triple" in line or "Leave Adjustment" in line:
            if "with ui.expansion" in line:
                print(f"  Line {i+1}: {line[:100]}")

# Also check for corrupted manual edit label
for i, line in enumerate(c.split("\n")):
    if "_t" in line and line.count("_t(") > 2:
        print(f"  SUSPICIOUS line {i+1}: {line[:120]}")

p.write_text(c, "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py SYNTAX OK")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")
