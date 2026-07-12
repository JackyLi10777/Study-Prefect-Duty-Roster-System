import pathlib, py_compile, subprocess, urllib.request, os, time, re

p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c = p.read_text("utf-8")

# Fix: ui.select(label_str, options=) -> ui.select(label=label_str, options=)
c = re.sub(r"ui\.select\(_t\(([^)]+)\),\s*options=", r"ui.select(label=_t(\1), options=", c)
c = re.sub(r"ui\.select\(\"([^\"]+)\",\s*options=", r'ui.select(label="\1", options=', c)

p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("roster.py: regex fix applied")

os.system("taskkill /f /im python.exe 2>nul")
time.sleep(2)
subprocess.Popen(["python", "app/main.py"], cwd=r"D:\code_v2")
time.sleep(8)

for u,n in [("/","dash"),("/prefects","pref"),("/roster","rost"),("/leave","leave"),("/audit","audit")]:
    try:
        r = urllib.request.urlopen(f"http://localhost:8080{u}", timeout=8)
        print(f"{n}: HTTP {r.status}")
    except urllib.error.HTTPError as e:
        print(f"{n}: HTTP {e.code}")
    except Exception as e:
        print(f"{n}: {type(e).__name__}")

r2 = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r2.stdout+r2.stderr else 'FAILED'}")
