import pathlib, py_compile

p = pathlib.Path(r"D:\code_v2\app\components\sidebar.py")
c = p.read_text("utf-8")

# 1. Add bordered=True and transition-colors to drawer
c = c.replace(
    'with ui.left_drawer(value=True, elevated=True).classes(',
    'with ui.left_drawer(value=True, elevated=True, bordered=True).classes('
)
c = c.replace(
    '"bg-white dark:bg-slate-900 w-64 dark:text-slate-200 border-r border-slate-200 dark:border-slate-700"',
    '"bg-white dark:bg-slate-900 w-64 dark:text-slate-200 border-r border-slate-200 dark:border-slate-700 transition-colors duration-200"'
)

# 2. Add mx-2 to separators
c = c.replace(
    'ui.separator().classes("mb-2 dark:bg-slate-700")',
    'ui.separator().classes("mb-2 dark:bg-slate-700 mx-2")'
)
c = c.replace(
    'ui.separator().classes("my-2 dark:bg-slate-700")',
    'ui.separator().classes("my-2 dark:bg-slate-700 mx-2")'
)

# 3. Active state: add left border indicator + cursor-pointer
c = c.replace(
    'bg = "bg-teal-50 dark:bg-teal-900/40" if is_active else "hover:bg-slate-100 dark:hover:bg-slate-800"',
    'bg = "bg-teal-50 dark:bg-teal-900/40 border-l-4 border-teal-600 dark:border-teal-400 pl-2" if is_active else "hover:bg-slate-100 dark:hover:bg-slate-800"'
)

# 4. Inactive text contrast improvement
c = c.replace(
    '"text-slate-600 dark:text-slate-400"',
    '"text-slate-600 dark:text-slate-300"'
)

# 5. Add cursor-pointer to nav links
c = c.replace(
    '.classes(f"no-underline {bg} mx-2 rounded-lg transition-colors duration-150")',
    '.classes(f"no-underline {bg} mx-2 rounded-lg transition-colors duration-150 cursor-pointer")'
)

# 6. Fix theme label contrast
c = c.replace(
    'ui.label(label_text).classes("text-xs text-slate-500 dark:text-slate-300")',
    'ui.label(label_text).classes("text-xs text-slate-500 dark:text-slate-400")'
)

p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print(f"sidebar.py updated: {c.count('dark:')} dark: classes")
print("Key additions: bordered, transition-colors, active left-border, cursor-pointer")

import subprocess
r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'CHECK'}")
