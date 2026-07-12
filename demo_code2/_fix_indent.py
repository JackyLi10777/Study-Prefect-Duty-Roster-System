import pathlib, py_compile

# FIX ROSTER: line 111 indentation
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c = p.read_text("utf-8")
c = c.replace(
    '                with ui.expansion(_t("\u8acb\u5047\u8abf\u6574", "Leave Adjustment"), icon="event_busy").classes("w-full"):\n                ui.label(_t(',
    '                with ui.expansion(_t("\u8acb\u5047\u8abf\u6574", "Leave Adjustment"), icon="event_busy").classes("w-full"):\n                    ui.label(_t('
)
c = c.replace(
    '                from services.leave_service import LeaveAdjustmentService',
    '                    from services.leave_service import LeaveAdjustmentService'
)
c = c.replace(
    '                p_dicts = [',
    '                    p_dicts = ['
)
c = c.replace(
    '                leave_svc = LeaveAdjustmentService',
    '                    leave_svc = LeaveAdjustmentService'
)
c = c.replace(
    '                leave_prefect = ui.select',
    '                    leave_prefect = ui.select'
)
# Fix manual edit section indentation too
c = c.replace(
    '            with ui.expansion(_t("\u624b\u52d5\u7de8\u8f2f / \u66ff\u88dc", "Manual Edit / Substitute"), icon="swap_horiz").classes("w-full mt-2"):\n                ui.label(',
    '            with ui.expansion(_t("\u624b\u52d5\u7de8\u8f2f / \u66ff\u88dc", "Manual Edit / Substitute"), icon="swap_horiz").classes("w-full mt-2"):\n                ui.label('
)
p.write_text(c, "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py OK")
except py_compile.PyCompileError as e:
    print(f"roster.py: {e}")

# FIX PREFECTS: Join split lines
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c2 = p2.read_text("utf-8")
c2 = c2.replace(
    'ai_btn = ui.button(_t("AI \u89e3\u6790\u5099\u8a3b", "AI Parse Remarks"), icon="auto_awesome",)\n                                    on_click=_ai_parse)',
    'ai_btn = ui.button(_t("AI \u89e3\u6790\u5099\u8a3b", "AI Parse Remarks"), icon="auto_awesome",\n                                    on_click=_ai_parse)'
)
c2 = c2.replace(
    'import_btn = ui.button(_t("\u5c0e\u5165CSV", "Import CSV"), icon="upload_file",)\n                    on_click=lambda: import_dialog.open())',
    'import_btn = ui.button(_t("\u5c0e\u5165CSV", "Import CSV"), icon="upload_file",\n                    on_click=lambda: import_dialog.open())'
)
p2.write_text(c2, "utf-8")
try:
    py_compile.compile(str(p2), doraise=True)
    print("prefects.py OK")
except py_compile.PyCompileError as e:
    print(f"prefects.py: {e}")

# FIX DASHBOARD: Join split lines
p3 = pathlib.Path(r"D:\code_v2\app\pages\dashboard.py")
c3 = p3.read_text("utf-8")
c3 = c3.replace(
    'ui.label(_t("\u6b61\u8fce\u4f7f\u7528\u98a8\u7d00\u503c\u73ed\u8868\u7cfb\u7d71\uff01", "Welcome to the Study Prefect Duty Roster!").classes())\n                        "text-body font-semibold text-teal-800 dark:text-teal-200")',
    'ui.label(_t("\u6b61\u8fce\u4f7f\u7528\u98a8\u7d00\u503c\u73ed\u8868\u7cfb\u7d71\uff01", "Welcome to the Study Prefect Duty Roster!")).classes(\n                        "text-body font-semibold text-teal-800 dark:text-teal-200")'
)
c3 = c3.replace(
    'ui.label(_t("\u8acb\u524d\u5f80\u98a8\u7d00\u7ba1\u7406\u9801\u9762\u52a0\u8f09\u793a\u7bc4\u6578\u64da\u4ee5\u958b\u59cb\u4f7f\u7528\u3002", "To get started, go to the Prefects page and load the sample data.").classes())\n                        "text-body-sm text-teal-700 dark:text-teal-300")',
    'ui.label(_t("\u8acb\u524d\u5f80\u98a8\u7d00\u7ba1\u7406\u9801\u9762\u52a0\u8f09\u793a\u7bc4\u6578\u64da\u4ee5\u958b\u59cb\u4f7f\u7528\u3002", "To get started, go to the Prefects page and load the sample data.")).classes(\n                        "text-body-sm text-teal-700 dark:text-teal-300")'
)
p3.write_text(c3, "utf-8")
try:
    py_compile.compile(str(p3), doraise=True)
    print("dashboard.py OK")
except py_compile.PyCompileError as e:
    print(f"dashboard.py: {e}")

# Final check on ALL modified files
print("\n=== FINAL SYNTAX CHECK ===")
for fpath in [
    r"D:\code_v2\app\pages\dashboard.py",
    r"D:\code_v2\app\pages\roster.py",
    r"D:\code_v2\app\pages\prefects.py",
    r"D:\code_v2\app\pages\audit.py",
    r"D:\code_v2\app\pages\leave.py",
    r"D:\code_v2\app\main.py",
    r"D:\code_v2\app\theme.py",
    r"D:\code_v2\app\components\sidebar.py",
]:
    try:
        py_compile.compile(fpath, doraise=True)
        print(f"  OK: {pathlib.Path(fpath).name}")
    except py_compile.PyCompileError as e:
        print(f"  FAIL: {pathlib.Path(fpath).name}: {str(e)[:150]}")
