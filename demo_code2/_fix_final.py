import pathlib, py_compile

# ============= ROSTER.PY =============
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c = p.read_text("utf-8")

# Fix line 46: _t("學習風紀", "Study Prefects") missing closing )
c = c.replace('_t("\u5b78\u7fd2\u98a8\u7d00", "Study Prefects")\n',
               '_t("\u5b78\u7fd2\u98a8\u7d00", "Study Prefects"))\n')

# Fix line 47: _t("平均負荷 (分)", "Avg Load (pts)") missing closing )
c = c.replace('_t("\u5e73\u5747\u8ca0\u8377 (\u5206)", "Avg Load (pts)")\n',
               '_t("\u5e73\u5747\u8ca0\u8377 (\u5206)", "Avg Load (pts)"))\n')

# Fix line 65-67: Extra parens from corrupted _t
c = c.replace('_t("\u751f\u6210\u503c\u73ed\u8868", "Generate Roster"))),',
               '_t("\u751f\u6210\u503c\u73ed\u8868", "Generate Roster")),')
c = c.replace('_t("\u91cd\u7f6e\u8ca0\u8377", "Reset Loads"))),',
               '_t("\u91cd\u7f6e\u8ca0\u8377", "Reset Loads")),')
c = c.replace('_t("\u532f\u51fa PDF/HTML", "Export PDF/HTML"))),',
               '_t("\u532f\u51fa PDF/HTML", "Export PDF/HTML")),')

# Fix line 110: Extra ))) on expansion
c = c.replace('_t("\u8acb\u5047\u8abf\u6574", "Leave Adjustment"))), icon=',
               '_t("\u8acb\u5047\u8abf\u6574", "Leave Adjustment")), icon=')

# Fix line 145: Extra ))) on manual edit expansion
c = c.replace('_t("\u624b\u52d5\u7de8\u8f2f / \u66ff\u88dc", "Manual Edit / Substitute"))), icon=',
               '_t("\u624b\u52d5\u7de8\u8f2f / \u66ff\u88dc", "Manual Edit / Substitute")), icon=')

# Fix line 124: "Confirm & Apply Adjustment" extra parens
c = c.replace('_t("\u78ba\u8a8d\u4e26\u61c9\u7528\u8abf\u6574", "Confirm & Apply Adjustment"))),',
               '_t("\u78ba\u8a8d\u4e26\u61c9\u7528\u8abf\u6574", "Confirm & Apply Adjustment")),')

# Fix line 168: "Check Current Assignment" extra parens
c = c.replace('_t("\u6aa2\u67e5\u7576\u524d\u5b89\u6392", "Check Current Assignment"))),',
               '_t("\u6aa2\u67e5\u7576\u524d\u5b89\u6392", "Check Current Assignment")),')

# Fix line 110: indentation (needs 16 spaces, currently has 12)
c = c.replace('            with ui.expansion(_t("\u8acb\u5047\u8abf\u6574", "Leave Adjustment")),',
               '                with ui.expansion(_t("\u8acb\u5047\u8abf\u6574", "Leave Adjustment")),')

p.write_text(c, "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py SYNTAX OK")
except py_compile.PyCompileError as e:
    print(f"roster.py SYNTAX ERROR: {e}")
    lines = c.split("\n")
    for i in [45, 46, 64, 65, 66, 109, 110, 144, 145]:
        if i < len(lines):
            print(f"  L{i+1}: {lines[i][:150]}")

# ============= PREFECTS.PY =============
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c2 = p2.read_text("utf-8")

# Fix line 118: double-nested _t
c2 = c2.replace('_t("\u4e2d\u6587\u59d3\u540d", _t("\u4e2d\u6587\u59d3\u540d", "Chinese Name")',
                 '_t("\u4e2d\u6587\u59d3\u540d", "Chinese Name"')

# Fix line 299: _t("活跃", "Active")))  -> _t("活跃", "Active")
c2 = c2.replace('_t("\u6d3b\u8e8d", "Active"))), "field":',
                 '_t("\u6d3b\u8e8d", "Active")), "field":')

# Fix line 88: "AI Parse Remarks" extra parens  
c2 = c2.replace('_t("AI \u89e3\u6790\u5099\u8a3b", "AI Parse Remarks"))),',
                 '_t("AI \u89e3\u6790\u5099\u8a3b", "AI Parse Remarks")),')

# Fix line 244: "Start Parsing" extra parens
c2 = c2.replace('_t("\u958b\u59cb\u5206\u6790", "Start Parsing"))),',
                 '_t("\u958b\u59cb\u5206\u6790", "Start Parsing")),')

p2.write_text(c2, "utf-8")
try:
    py_compile.compile(str(p2), doraise=True)
    print("prefects.py SYNTAX OK")
except py_compile.PyCompileError as e:
    print(f"prefects.py SYNTAX ERROR: {e}")
    lines2 = c2.split("\n")
    for i in [116, 117, 118, 297, 298, 299]:
        if i < len(lines2):
            print(f"  L{i+1}: {lines2[i][:150]}")

# ============= DASHBOARD.PY =============
p3 = pathlib.Path(r"D:\code_v2\app\pages\dashboard.py")
c3 = p3.read_text("utf-8")
# Check around line 183 for the error
lines3 = c3.split("\n")
for i in range(178, 190):
    if i < len(lines3):
        print(f"dash L{i+1}: {lines3[i][:150]}")
