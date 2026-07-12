import pathlib, py_compile, subprocess, re
p = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c = p.read_text("utf-8")

# NUCLEAR: Fix ALL .classes( directly on English strings
fixes = [
    ("\"Add, edit, import, and manage all study prefect records.\".classes(", "\"Add, edit, import, and manage all study prefect records.\")).classes("),
    ("\"No Prefects Yet\".classes(", "\"No Prefects Yet\")).classes("),
    ("\"Add your first prefect to get started.\".classes(", "\"Add your first prefect to get started.\")).classes("),
    ("\"Available Days:\".classes(", "\"Available Days:\")).classes("),
]

for old, new in fixes:
    if old in c:
        c = c.replace(old, new)
        print(f"Fixed: {old[:50]}...")
    else:
        print(f"Not found: {old[:50]}...")

p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("prefects.py OK")

r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")
