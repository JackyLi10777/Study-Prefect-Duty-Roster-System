import pathlib, py_compile
p=pathlib.Path(r"D:\code_v2\app\pages\dashboard.py")
c=p.read_text("utf-8")
c=c.replace('.classes("w-full rounded-[20px] shadow-sm p-6")', '.classes("w-full rounded-[20px] shadow-sm dark:shadow-md p-6 dark:bg-slate-800")')
p.write_text(c,"utf-8")
py_compile.compile(str(p), doraise=True)
print(f"dashboard.py OK: {c.count(chr(100)+chr(97)+chr(114)+chr(107)+chr(58))} dark: classes")

# Re-run detector v2
import subprocess, sys
sys.path.insert(0, r"D:\code_v2\scripts")
import importlib, detect_dark_mode_leaks
importlib.reload(detect_dark_mode_leaks)
leaks = detect_dark_mode_leaks.find_leaks()
print(f"\nDetector v2 results: {len(leaks)} leaks")
if leaks:
    for f, ln, line in leaks:
        print(f"  {f}:{ln}: {line}")
else:
    print("CLEAN - zero dark mode color leaks!")

r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")
