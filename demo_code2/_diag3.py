import pathlib

print("=== Pass 3: Dark Mode Investigation ===\n")

# 1. Sidebar
c = pathlib.Path(r"D:\code_v2\app\components\sidebar.py").read_text("utf-8")
print(f"Sidebar dark: classes: {c.count('dark:')}")
for feat in ["dark:bg-slate-900","dark:border-slate-700","dark:text-slate-200",
             "dark:bg-slate-700","dark:bg-teal-900/40","dark:hover:bg-slate-800",
             "transition-colors","dark:text-slate-300","dark:text-slate-400"]:
    print(f"  [{chr(89) if feat in c else chr(78)}] {feat}")

# 2. Dashboard
c2 = pathlib.Path(r"D:\code_v2\app\pages\dashboard.py").read_text("utf-8")
print(f"\nDashboard dark: classes: {c2.count('dark:')}")

# 3. CSS overrides  
c4 = pathlib.Path(r"D:\code_v2\app\theme\css.py").read_text("utf-8")
print(f"CSS !important overrides: {c4.count('!important')}")
print(f"CSS dark font-weight 450: {'font-weight: 450' in c4}")
print(f"CSS dark table overrides: {'body.dark .q-table' in c4}")
print(f"CSS dark drawer overrides: {'body.dark .q-drawer' in c4}")

# 4. Toggle theme
c3 = pathlib.Path(r"D:\code_v2\app\theme.py").read_text("utf-8")
print(f"\nToggle has Quasar: {'QQuasar' in c3}")
print(f"Toggle has drawer refresh: {'q-drawer' in c3}")
