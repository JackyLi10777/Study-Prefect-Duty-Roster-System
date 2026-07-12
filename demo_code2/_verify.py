import pathlib, py_compile, subprocess, urllib.request

print("=== PASS 5: FINAL VERIFICATION ===\n")

# 1. Syntax
print("--- Syntax Check ---")
files = ["app/utils/logging_config.py","app/utils/context.py","app/utils/error_handler.py",
         "app/middleware/request_id.py","app/main.py"]
for f in files:
    try:
        py_compile.compile(str(pathlib.Path(f"D:/code_v2/{f}")), doraise=True)
        print(f"  OK: {f}")
    except py_compile.PyCompileError as e:
        print(f"  FAIL: {f}")

# 2. Tests
print("\n--- Test Suite ---")
r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
passed = "52 passed" in r.stdout + r.stderr
print(f"  {'52/52 PASSING' if passed else 'FAILED'}")

# 3. HTTP test
print("\n--- HTTP Request Test ---")
try:
    r = urllib.request.urlopen("http://localhost:8080/", timeout=5)
    rid = r.headers.get("X-Request-ID", "MISSING")
    print(f"  Dashboard: HTTP {r.status}, X-Request-ID: {rid}")
except Exception as e:
    print(f"  Dashboard: {type(e).__name__}")

# 4. Log file
print("\n--- Log File Check ---")
log = pathlib.Path("logs/app.log")
if log.exists():
    size = log.stat().st_size
    lines = log.read_text("utf-8").split("\n")
    print(f"  logs/app.log: {size} bytes, {len(lines)} lines")
    for l in lines[-4:-1]:
        if l.strip():
            print(f"    {l[:150]}")
else:
    print("  logs/app.log: NOT FOUND")

# 5. Code quality
print("\n--- Code Quality ---")
for f in files:
    c = pathlib.Path(f"D:/code_v2/{f}").read_text("utf-8")
    has_doc = chr(34)+chr(34)+chr(34) in c[:200]
    print(f"  {f.split('/')[-1]}: docstring={has_doc}")
