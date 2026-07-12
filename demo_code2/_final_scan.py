import pathlib, subprocess, urllib.request, urllib.error

print("=== FINAL PRE-LAUNCH SCAN ===\n")

# 1. Syntax
files = ["app/pages/dashboard.py","app/pages/roster.py","app/pages/prefects.py",
         "app/pages/audit.py","app/pages/leave.py","app/main.py",
         "app/theme.py","app/components/sidebar.py"]
for f in files:
    try:
        __import__("py_compile").compile(str(pathlib.Path(f"D:/code_v2/{f}")), doraise=True)
    except Exception as e:
        print(f"FAIL: {f}")
        break
else:
    print(f"Syntax: {len(files)} files OK")

# 2. Tests
r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")

# 3. Page load check
pages = {"/":"dash","/prefects":"pref","/roster":"rost","/leave":"leave","/audit":"audit","/design":"design"}
for path, name in pages.items():
    try:
        r = urllib.request.urlopen(f"http://localhost:8080{path}", timeout=5)
        print(f"{name}: HTTP {r.status}")
    except urllib.error.HTTPError as e:
        print(f"{name}: HTTP {e.code} FAIL")
    except Exception as e:
        print(f"{name}: {type(e).__name__}")
