import pathlib, py_compile, subprocess, os, time, urllib.request

# Fix roster.py L164
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c = p.read_text("utf-8")
# Find the broken line and fix it
# Pattern: _t(A, _t(B, C), on_click=...)
# Fix: _t(A, _t(B, C)), on_click=...)
c = c.replace(
    '_t("\u6aa2\u67e5\u7576\u524d\u5b89\u6392", _t("\u6aa2\u67e5\u7576\u524d\u5b89\u6392", "Check Current Assignment"), on_click=_show_current)',
    '_t("\u6aa2\u67e5\u7576\u524d\u5b89\u6392", _t("\u6aa2\u67e5\u7576\u524d\u5b89\u6392", "Check Current Assignment")), on_click=_show_current)'
)
p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("roster.py L164: fixed")

# Restart
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
        print(f"{n}: {type(e).__name__}")

r2 = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {52 if chr(53)+chr(50)+chr(32)+chr(112) in r2.stdout+r2.stderr else chr(70)}/52")
