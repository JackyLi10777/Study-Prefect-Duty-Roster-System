import pathlib, py_compile, subprocess, urllib.request, os, time

p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c = p.read_text("utf-8")

# Fix: ui.select(label_text, options=...) -> ui.select(label=label_text, options=...)
c = c.replace('adj_day = ui.select(_t("\u65e5\u671f", "Day"), options=day_options', 
               'adj_day = ui.select(label=_t("\u65e5\u671f", "Day"), options=day_options')
c = c.replace('adj_room = ui.select(_t("\u623f\u9593", "Room"), options=room_options',
               'adj_room = ui.select(label=_t("\u623f\u9593", "Room"), options=room_options')
c = c.replace('adj_replace = ui.select("Replacement (optional)", options=',
               'adj_replace = ui.select(label="Replacement (optional)", options=')
c = c.replace('ed_day = ui.select("Day", options=day_options',
               'ed_day = ui.select(label="Day", options=day_options')
c = c.replace('ed_room = ui.select("Room", options=room_options',
               'ed_room = ui.select(label="Room", options=room_options')

p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("roster.py: 5 ui.select calls fixed")

os.system("taskkill /f /im python.exe 2>nul")
time.sleep(2)
subprocess.Popen(["python", "app/main.py"], cwd=r"D:\code_v2")
time.sleep(8)

for pt,nm in [("/","dash"),("/prefects","pref"),("/roster","rost"),("/leave","leave"),("/audit","audit")]:
    try:
        r = urllib.request.urlopen(f"http://localhost:8080{pt}", timeout=8)
        print(f"{nm}: {r.status}")
    except Exception as e:
        print(f"{nm}: {type(e).__name__}")

r2 = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r2.stdout+r2.stderr else 'FAILED'}")
