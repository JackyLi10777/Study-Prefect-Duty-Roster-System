import pathlib, py_compile, subprocess

# Fix prefects.py line 98: .classes() on string literal
p = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c = p.read_text("utf-8")

# Specific fix for line 98: .classes( is inside the _t() call on the EN string
# _t("..., "EN string".classes(...)) -> _t("..., "EN string")).classes(...)
old = '"_t(\"添加、编辑、导入和管理所有风纪记录。\", \"Add, edit, import, and manage all study prefect records.\".classes(\"text-sm text-slate-500 dark:text-slate-400 mb-4\")"'
new = '"_t(\"添加、编辑、导入和管理所有风纪记录。\", \"Add, edit, import, and manage all study prefect records.\")).classes(\"text-sm text-slate-500 dark:text-slate-400 mb-4\")"'
# Just do a targeted replace on the broken pattern
c = c.replace(
    '"Add, edit, import, and manage all study prefect records.\".classes(\"text-sm text-slate-500 dark:text-slate-400 mb-4\")))"',
    '"Add, edit, import, and manage all study prefect records.\")).classes(\"text-sm text-slate-500 dark:text-slate-400 mb-4\")"'
)
p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("Fixed prefects.py line 98")

# Also search for similar pattern in roster.py
p2 = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c2 = p2.read_text("utf-8")
# Check for .classes( on string literals not ui elements
import re
for i, line in enumerate(c2.split("\n"), 1):
    if re.search(r'" [A-Z][^"]+"\.classes\(', line):
        print(f"  ALSO BROKEN in roster.py:{i}: {line.strip()[:130]}")

# Tests
r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")
