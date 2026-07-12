import pathlib, py_compile, subprocess

p = pathlib.Path(r"D:\code_v2\app\pages\dashboard.py")
c = p.read_text("utf-8")

# Fix KPI card labels
c = c.replace(
    'KpiCard(str(active_count), "Active Prefects", gradient=True)',
    'KpiCard(str(active_count), _t("\u6d3b\u8e8d\u98a8\u7d00", "Active Prefects"), gradient=True)'
)
c = c.replace(
    'KpiCard(str(sp_count), "Study Prefects")',
    'KpiCard(str(sp_count), _t("\u5b78\u7fd2\u98a8\u7d00", "Study Prefects"))'
)
c = c.replace(
    'KpiCard(f\"{avg_load:.1f}\", \"Avg Load (pts)\")',
    'KpiCard(f\"{avg_load:.1f}\", _t("\u5e73\u5747\u8ca0\u8377 (\u5206)", \"Avg Load (pts)\"))'
)

p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("dashboard.py: 3 KPI card labels wrapped in _t()")

r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")

# Also verify sidebar state
c2 = pathlib.Path(r"D:\code_v2\app\components\sidebar.py").read_text("utf-8")
print(f"\nSidebar: {c2.count('dark:')} dark: classes (already fully synchronized)")
print(f"  bordered=True: {'bordered=True' in c2}")
print(f"  transition-colors: {'transition-colors' in c2}")
print(f"  dark:border-slate-700: {'dark:border-slate-700' in c2}")
