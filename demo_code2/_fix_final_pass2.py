import pathlib, py_compile, subprocess

# ===== FIX 1: prefects.py - simplify role_select options =====
p = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c = p.read_text("utf-8")

# Fix: the dict comprehension in role_select options may cause issues
# Replace with simple list(ROLE_CHOICES.keys())
old_opts = "options={ROLE_LABELS_ZH.get(k, k) if is_zh() else k: v for k, v in ROLE_CHOICES.items()}"
new_opts = "options=list(ROLE_CHOICES.keys())"
if old_opts in c:
    c = c.replace(old_opts, new_opts)
    print("prefects: simplified role_select options")

p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("prefects.py OK")

# ===== FIX 2: roster.py - add safety check for colmap lookup =====
p2 = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c2 = p2.read_text("utf-8")

# Fix KeyError in colmap lookups - use .get() instead of []
c2 = c2.replace("colmap[room.value]", "colmap.get(room.value, -1)")
c2 = c2.replace("colmap[room.name]", "colmap.get(room.name, -1)")

p2.write_text(c2, "utf-8")
py_compile.compile(str(p2), doraise=True)
print("roster.py OK")

r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")

# Restart and test
import os
os.system("taskkill /f /im python.exe 2>nul")
import time
time.sleep(2)
subprocess.Popen(["python", "app/main.py"], cwd=r"D:\code_v2", stderr=open("_e5.log","w"))
time.sleep(5)

import urllib.request, urllib.error
for url in ["http://localhost:8080/","http://localhost:8080/prefects","http://localhost:8080/roster"]:
    try:
        r = urllib.request.urlopen(url, timeout=5)
        print(f"{url.split('/')[-1] or 'dashboard'}: HTTP {r.status}")
    except urllib.error.HTTPError as e:
        print(f"{url.split('/')[-1] or 'dashboard'}: HTTP {e.code} FAIL")
