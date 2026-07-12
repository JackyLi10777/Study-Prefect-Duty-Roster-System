import pathlib, py_compile

# ===== ROSTER: Fix line 63 + 111 =====
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c = p.read_text("utf-8")

# Line 63: missing ) before .classes
c = c.replace(
    'ui.label(_t("\u503c\u73ed\u8868\u751f\u6210", _t("\u503c\u73ed\u8868\u751f\u6210", "Roster Generation").classes(Type.H3)',
    'ui.label(_t("\u503c\u73ed\u8868\u751f\u6210", "Roster Generation")).classes(Type.H3)'
)

# Line 111: missing ) before .classes
c = c.replace(
    'ui.label(_t("\u767c\u5e03\u5f8c\u5982\u6709\u98a8\u7d00\u8acb\u5047\uff0c\u53ef\u5728\u6b64\u64a4\u92b7\u5176\u5206\u6578\u4e26\u5b89\u6392\u66ff\u88dc\u3002", "Adjust leave after roster publication.").classes',
    'ui.label(_t("\u767c\u5e03\u5f8c\u5982\u6709\u98a8\u7d00\u8acb\u5047\uff0c\u53ef\u5728\u6b64\u64a4\u92b7\u5176\u5206\u6578\u4e26\u5b89\u6392\u66ff\u88dc\u3002", "Adjust leave after roster publication.")).classes'
)

# Line 123: "Confirm & Apply Adjustment" missing ) before on_click
c = c.replace(
    'ui.button(_t("\u78ba\u8a8d\u4e26\u61c9\u7528\u8abf\u6574", "Confirm & Apply Adjustment"), on_click=_apply_leave)',
    'ui.button(_t("\u78ba\u8a8d\u4e26\u61c9\u7528\u8abf\u6574", "Confirm & Apply Adjustment"), on_click=_apply_leave)'
)

# Line 167: "Check Current Assignment" missing ) before on_click
c = c.replace(
    'ui.button(_t("\u6aa2\u67e5\u7576\u524d\u5b89\u6392", "Check Current Assignment"), on_click=_show_current)',
    'ui.button(_t("\u6aa2\u67e5\u7576\u524d\u5b89\u6392", "Check Current Assignment"), on_click=_show_current)'
)

p.write_text(c, "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py SYNTAX OK")
except py_compile.PyCompileError as e:
    print(f"roster.py SYNTAX ERROR: line? {e}")
    lines = c.split("\n")
    for i in [62, 63, 64]:
        print(f"  L{i+1}: {lines[i][:150]}")

# ===== PREFECTS: Fix line 118 =====
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c2 = p2.read_text("utf-8")
# The issue: _t("中文姓名", "Chinese Name" -> missing closing ) before "zh":
# Current: "name_zh": {"en": _t("中文姓名", "Chinese Name", "zh": "中文名"},
# Should be: "name_zh": {"en": _t("中文姓名", "Chinese Name"), "zh": "中文名"},
c2 = c2.replace(
    '_t("\u4e2d\u6587\u59d3\u540d", "Chinese Name", "zh":',
    '_t("\u4e2d\u6587\u59d3\u540d", "Chinese Name"), "zh":'
)
p2.write_text(c2, "utf-8")
try:
    py_compile.compile(str(p2), doraise=True)
    print("prefects.py SYNTAX OK")
except py_compile.PyCompileError as e:
    print(f"prefects.py SYNTAX ERROR: {e}")

# ===== DASHBOARD: Fix line 180 =====
p3 = pathlib.Path(r"D:\code_v2\app\pages\dashboard.py")
c3 = p3.read_text("utf-8")
# Line 180: ui.label(_t("...", "...").classes  -> missing ) before .classes
c3 = c3.replace(
    'ui.label(_t("\u6bcf\u65e5\u91d1\u53e5\u3001\u7cfb\u7d71\u72b6\u6001\u3001KPI\u6982\u89c8\u3001\u5907\u4efd\u4e0e\u8fd8\u539f", "Daily scripture, system status, KPI overview, backup & restore.").classes',
    'ui.label(_t("\u6bcf\u65e5\u91d1\u53e5\u3001\u7cfb\u7d71\u72b6\u6001\u3001KPI\u6982\u89c8\u3001\u5907\u4efd\u4e0e\u8fd8\u539f", "Daily scripture, system status, KPI overview, backup & restore.")).classes'
)
p3.write_text(c3, "utf-8")
try:
    py_compile.compile(str(p3), doraise=True)
    print("dashboard.py SYNTAX OK")
except py_compile.PyCompileError as e:
    print(f"dashboard.py SYNTAX ERROR: {e}")
