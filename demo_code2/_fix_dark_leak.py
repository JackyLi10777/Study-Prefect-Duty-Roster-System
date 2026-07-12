import pathlib, py_compile

# ===== APPROACH 1: Centralized dark mode CSS overrides in theme/css.py =====
p = pathlib.Path(r"D:\code_v2\app\theme\css.py")
c = p.read_text("utf-8")

# Add comprehensive dark mode overrides for common color leaks
dark_overrides = """

        /* =====================================================================
           DARK MODE COLOR LEAK PREVENTION (Iteration 18.5)
           Force-override common light-mode colors in dark mode
           ===================================================================== */
        body.dark .bg-white { background-color: #1E293B !important; }
        body.dark .bg-slate-50 { background-color: #1E293B !important; }
        body.dark .bg-gray-50 { background-color: #1E293B !important; }
        body.dark .bg-slate-100 { background-color: #334155 !important; }
        body.dark .bg-teal-50 { background-color: rgba(20,184,166,0.10) !important; }
        body.dark .bg-amber-50 { background-color: rgba(245,158,11,0.10) !important; }
        body.dark .text-slate-900 { color: #F1F5F9 !important; }
        body.dark .text-black { color: #F1F5F9 !important; }
        body.dark .text-slate-800 { color: #E2E8F0 !important; }
        body.dark .text-slate-700 { color: #CBD5E1 !important; }
        body.dark .border-slate-200 { border-color: #475569 !important; }
        body.dark .border-gray-300 { border-color: #475569 !important; }
        body.dark .border-slate-300 { border-color: #64748B !important; }
        body.dark .shadow-sm { box-shadow: 0 1px 3px rgba(0,0,0,0.40) !important; }
        body.dark .shadow-md { box-shadow: 0 4px 14px rgba(0,0,0,0.40) !important; }
        body.dark .shadow-lg { box-shadow: 0 8px 28px rgba(0,0,0,0.45) !important; }
        /* Table dark mode */
        body.dark .q-table { background-color: #1E293B !important; }
        body.dark .q-table th { background-color: #334155 !important; color: #F1F5F9 !important; }
        body.dark .q-table td { color: #E2E8F0 !important; border-color: #475569 !important; }
        body.dark .q-table tbody tr:nth-child(even) { background-color: #1A2332 !important; }
        /* Drawer/Sidebar dark mode */
        body.dark .q-drawer { background-color: #0F172A !important; }
        body.dark .q-drawer .q-item { color: #E2E8F0 !important; }
        /* Dialog/Modal */
        body.dark .q-dialog .q-card { background-color: #1E293B !important; }
        /* Input fields */
        body.dark .q-field__control { background-color: #1E293B !important; color: #F1F5F9 !important; }
        body.dark .q-field__native { color: #F1F5F9 !important; }
        /* Outline buttons */
        body.dark .q-btn--outline { border-color: #475569 !important; color: #CBD5E1 !important; }
        /* Separator */
        body.dark .q-separator { background-color: #475569 !important; }
        /* Tabs */
        body.dark .q-tab { color: #CBD5E1 !important; }
        body.dark .q-tab--active { color: #14B8A6 !important; }
        /* Expansion items */
        body.dark .q-expansion-item .q-card { background-color: #1E293B !important; }
        /* Status dots keep their own colors */
        body.dark .status-dot.online { background: #10B981; }
        body.dark .status-dot.offline { background: #EF4444; }
        body.dark .status-dot.warning { background: #F59E0B; }
"""

# Insert before the closing </style> tag
c = c.replace("    </style>", dark_overrides + "\n    </style>")
p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("theme/css.py: Added comprehensive dark mode color leak overrides")

# ===== APPROACH 2: Fix sidebar dark mode =====
p2 = pathlib.Path(r"D:\code_v2\app\components\sidebar.py")
c2 = p2.read_text("utf-8")
# Add dark: variants to sidebar classes
c2 = c2.replace('"bg-white dark:bg-slate-900 w-64"', '"bg-white dark:bg-slate-900 w-64 dark:text-slate-200"')
# Fix sidebar brand area
c2 = c2.replace('"w-full items-center px-4 py-5 gap-2 bg-gradient-to-br from-teal-50 to-white dark:from-teal-900/30 dark:to-slate-900"',
                 '"w-full items-center px-4 py-5 gap-2 bg-gradient-to-br from-teal-50 to-white dark:from-teal-900/40 dark:to-slate-900"')
p2.write_text(c2, "utf-8")
py_compile.compile(str(p2), doraise=True)
print("sidebar.py: Dark mode enhancements")

# ===== APPROACH 3: Fix dashboard remaining color leaks =====
p3 = pathlib.Path(r"D:\code_v2\app\pages\dashboard.py")
c3 = p3.read_text("utf-8")
# Fix welcome banner dark mode
c3 = c3.replace('"w-full bg-teal-50 dark:bg-teal-900/20 border-l-4 border-teal-500 p-4 mb-4 rounded-r-lg"',
                 '"w-full bg-teal-50 dark:bg-teal-900/30 border-l-4 border-teal-500 dark:border-teal-400 p-4 mb-4 rounded-r-lg"')
# Fix health notes dark mode
c3 = c3.replace('"w-full bg-amber-50/70 dark:bg-amber-900/10 border-l-4 border-amber-300 p-3 mb-4 rounded-r-lg opacity-90"',
                 '"w-full bg-amber-50/70 dark:bg-amber-900/20 border-l-4 border-amber-300 dark:border-amber-500 p-3 mb-4 rounded-r-lg opacity-90"')
# Fix backup reminder dark mode
c3 = c3.replace('"w-full bg-amber-50 dark:bg-amber-900/20 border-l-4 border-amber-400 p-4 mb-2 rounded-r-lg"',
                 '"w-full bg-amber-50 dark:bg-amber-900/30 border-l-4 border-amber-400 dark:border-amber-500 p-4 mb-2 rounded-r-lg"')
# Fix Quick Action cards
c3 = c3.replace('"flex-1 min-w-[200px] rounded-xl shadow-sm p-5"',
                 '"flex-1 min-w-[200px] rounded-xl shadow-sm p-5 dark:bg-slate-800"')
# Fix KPI cards container
c3 = c3.replace('"gap-4 w-full flex-wrap"',
                 '"gap-4 w-full flex-wrap dark:text-slate-100"')
p3.write_text(c3, "utf-8")
py_compile.compile(str(p3), doraise=True)
print("dashboard.py: Dark mode color leak fixes")

# ===== Check results =====
for name, fp in [("prefects", r"D:\code_v2\app\pages\prefects.py"),
                  ("roster", r"D:\code_v2\app\pages\roster.py"),
                  ("dashboard", r"D:\code_v2\app\pages\dashboard.py")]:
    c = pathlib.Path(fp).read_text("utf-8")
    print(f"  {name}: {c.count('dark:')} dark: classes, {c.count('dark:bg-slate-800')} dark:bg-slate-800")

# Run tests
import subprocess
r = subprocess.run(["python", "-m", "pytest", "tests/", "-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print("\nTests:", "52/52" if "52 passed" in r.stdout + r.stderr else "FAILED")
