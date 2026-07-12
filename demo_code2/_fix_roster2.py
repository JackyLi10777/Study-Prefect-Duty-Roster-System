import pathlib, py_compile

# Fix roster.py: The entire leave adjustment tab section needs indentation fix
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c = p.read_text("utf-8")

# Fix: lines after "with ui.expansion" need 4 more spaces
# Line 111: ui.label should have 16 spaces (inside with expansion -> inside with tab_panel)
# But looking at the diagram, with tab_panel is at 12 spaces, with expansion at 16, body at 20
# Actually: with tab_panels=4, with tab_panel=8, with expansion=12, body=16... 
# But the file shows tab_panel at 12 spaces indent. Let me just fix the relative indent.

# The issue: line 110 (with expansion) has 16 spaces, line 111 (ui.label) has 12 spaces
# Line 111 should have 20 spaces (16 + 4 for the with block body)
c = c.replace(
    '                with ui.expansion(_t("\u8acb\u5047\u8abf\u6574", "Leave Adjustment"), icon="event_busy").classes("w-full"):\n                ui.label(_t(',
    '                with ui.expansion(_t("\u8acb\u5047\u8abf\u6574", "Leave Adjustment"), icon="event_busy").classes("w-full"):\n                    ui.label(_t('
)

# Fix other lines in the leave section: they have 12 spaces, need 16
# from services.leave_service -> should be 16 spaces
c = c.replace(
    '                from services.leave_service import LeaveAdjustmentService\n                p_dicts',
    '                    from services.leave_service import LeaveAdjustmentService\n                    p_dicts'
)
c = c.replace(
    '                    p_dicts = [{"name": p.name, "history_weight": p.history_weight, "available": [d.name for d in p.available]} for p in (_prefects_cache or [])]\n                leave_svc',
    '                    p_dicts = [{"name": p.name, "history_weight": p.history_weight, "available": [d.name for d in p.available]} for p in (_prefects_cache or [])]\n                    leave_svc'
)
c = c.replace(
    '                    leave_svc = LeaveAdjustmentService(prefects=p_dicts)\n                leave_prefect',
    '                    leave_svc = LeaveAdjustmentService(prefects=p_dicts)\n                    leave_prefect'
)
c = c.replace(
    '                    leave_prefect = ui.select(label=_t',
    '                    leave_prefect = ui.select(label=_t'
)
# Actually, leave_prefect was already at 20 spaces in prev fix, check...
# Let me just fix remaining 12-space lines
for i in range(3):
    c = c.replace('\n                day_options', '\n                    day_options')
    c = c.replace('\n                adj_day', '\n                    adj_day')
    c = c.replace('\n                room_options', '\n                    room_options')
    c = c.replace('\n                adj_room', '\n                    adj_room')
    c = c.replace('\n                adj_slot', '\n                    adj_slot')
    c = c.replace('\n                adj_replace', '\n                    adj_replace')
    c = c.replace('\n                def _apply_leave', '\n                    def _apply_leave')
    c = c.replace('\n                ui.button(_t("\u78ba\u8a8d', '\n                    ui.button(_t("\u78ba\u8a8d')

p.write_text(c, "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py OK")
except py_compile.PyCompileError as e:
    print(f"roster.py: {e}")
    lines = c.split("\n")
    for i in [109, 110, 111, 112, 113, 114]:
        if i < len(lines):
            sp = len(lines[i]) - len(lines[i].lstrip())
            print(f"  L{i+1}: indent={sp} {lines[i][:120]}")

# Fix prefects.py line 126
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c2 = p2.read_text("utf-8")
lines2 = c2.split("\n")
if len(lines2) > 125:
    print(f"prefects L126: {lines2[125][:150]}")
    # Fix the corrupted line
    c2 = c2.replace(
        '"_t("\\u6d3b\\u8e8d", _t("\\u6d3b\\u8e8d", "Active"), "zh":',
        '"_t("\\u6d3b\\u8e8d", "Active"), "zh":'
    )
    # Also try the actual Chinese chars version
    c2 = c2.replace(
        '_t("\u6d3b\u8e8d", _t("\u6d3b\u8e8d", "Active")',
        '_t("\u6d3b\u8e8d", "Active")'
    )
    p2.write_text(c2, "utf-8")
    try:
        py_compile.compile(str(p2), doraise=True)
        print("prefects.py OK")
    except py_compile.PyCompileError as e:
        print(f"prefects.py: {e}")
