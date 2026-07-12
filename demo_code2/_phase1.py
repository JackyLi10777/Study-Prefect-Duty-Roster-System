import pathlib, re, subprocess

print("=== PHASE 1: FULL SYSTEM SCAN ===\n")

# 1.1 i18n
print("--- 1.1 i18n Completeness ---")
for name in ["dashboard","roster","prefects","audit","leave"]:
    c = pathlib.Path(f"app/pages/{name}.py").read_text("utf-8")
    t_count = c.count("_t(")
    en_labels = re.findall(r"ui\.label\(\"([A-Z][^\"]+)\"", c)
    en_buttons = re.findall(r"ui\.button\(\"([A-Z][^\"]+)\"", c)
    print(f"  {name}: {t_count} _t(), labels={en_labels[:3]}, buttons={en_buttons[:3]}")

c_d = pathlib.Path("app/main.py").read_text("utf-8")
print(f"  design (main): {c_d.count('_t(')} _t()")

# 1.2 Dark mode color leaks
print("\n--- 1.2 Dark Mode Color Leak Scan ---")
for name in ["dashboard","roster","prefects","audit","leave"]:
    c = pathlib.Path(f"app/pages/{name}.py").read_text("utf-8")
    bw = len(re.findall(r"bg-white(?!.*dark:)", c))
    b200 = len(re.findall(r"border-slate-200(?!.*dark:)", c))
    s900 = len(re.findall(r"text-slate-900(?!.*dark:)", c))
    total = bw + b200 + s900
    if total > 0:
        print(f"  {name}: {total} LEAKS (bg-white={bw}, border-slate-200={b200}, text-slate-900={s900})")
    else:
        print(f"  {name}: CLEAN")

# Also check sidebar and main
for name, fp in [("sidebar","app/components/sidebar.py"),("main","app/main.py")]:
    c = pathlib.Path(fp).read_text("utf-8")
    bw = len(re.findall(r"bg-white(?!.*dark:)", c))
    total = bw + len(re.findall(r"border-slate-200(?!.*dark:)", c)) + len(re.findall(r"text-slate-900(?!.*dark:)", c))
    print(f"  {name}: {total} LEAKS" if total > 0 else f"  {name}: CLEAN")

# 1.3 Functional check
print("\n--- 1.3 Functional & UX Gaps ---")
sc = pathlib.Path("app/pages/dashboard.py").read_text("utf-8")
print(f"  Scripture lang-aware: {'is_zh()' in sc}")
ro = pathlib.Path("app/pages/roster.py").read_text("utf-8")
print(f"  Roster empty state: {'No Roster Generated Yet' in ro or chr(23578)+chr(26410)+chr(29983)+chr(25104) in ro}")
so = pathlib.Path("app/components/sounds.py").read_text("utf-8")
print(f"  Sound functions: {len(re.findall(r'def (\w+)', so))}")

# 1.4 Code quality
print("\n--- 1.4 Code Quality & Stability ---")
r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True)
passed = "52 passed" in r.stdout + r.stderr
print(f"  Tests: {'52/52 PASSING' if passed else 'FAILED'}")

# Module-level globals
for name in ["roster","prefects","dashboard"]:
    c = pathlib.Path(f"app/pages/{name}.py").read_text("utf-8")
    globals_count = len(re.findall(r"^[a-z_]+\\s*=\\s*(None|\[\]|\{\})", c, re.MULTILINE))
    if globals_count > 0:
        print(f"  {name}: {globals_count} module-level globals (state risk)")

# Dark mode summary
print("\n--- Dark Mode Coverage Summary ---")
for name in ["dashboard","roster","prefects","audit","leave"]:
    c = pathlib.Path(f"app/pages/{name}.py").read_text("utf-8")
    print(f"  {name}: {c.count('dark:')} dark: classes")
sc_sidebar = pathlib.Path("app/components/sidebar.py").read_text("utf-8")
print(f"  sidebar: {sc_sidebar.count('dark:')} dark: classes")

print("\n=== PHASE 1 COMPLETE ===")
