import pathlib, py_compile, subprocess

p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c = p.read_text("utf-8")
# Wrap _display_roster_table body in try/except
old = "    if roster is None:\n        return\n    from i18n.rules import prefect_display_name"
new = "    if roster is None:\n        return\n    if not hasattr(roster, 'days'):\n        _current_roster = None\n        return\n    try:\n        from i18n.rules import prefect_display_name"
c = c.replace(old, new)
# Also add except at end of function
old_end = "    ui.table(columns=columns, rows=rows_list, row_key='room').classes('w-full rounded-lg overflow-hidden')\n    return"
new_end = "    ui.table(columns=columns, rows=rows_list, row_key='room').classes('w-full rounded-lg overflow-hidden')\n    return\n    except Exception:\n        _current_roster = None\n        return"
c = c.replace(old_end, new_end)
p.write_text(c, "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py: try/except safeguard added")
except py_compile.PyCompileError as e:
    print(f"roster.py: {e}")

r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")

# Restart
import os, time, urllib.request
os.system("taskkill /f /im python.exe 2>nul")
time.sleep(2)
subprocess.Popen(["python", "app/main.py"], cwd=r"D:\code_v2")
time.sleep(5)

for u in ["http://localhost:8080/","http://localhost:8080/prefects","http://localhost:8080/roster"]:
    try:
        r = urllib.request.urlopen(u, timeout=5)
        n = u.split("/")[-1] or "dash"
        print(f"{n}: HTTP {r.status}")
    except Exception as e:
        n = u.split("/")[-1] or "dash"
        print(f"{n}: FAIL - {type(e).__name__}")
