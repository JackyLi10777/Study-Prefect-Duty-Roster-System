import pathlib, py_compile

# ===== STEP 1: Rewrite sidebar.py with full dark mode support =====
p = pathlib.Path(r"D:\code_v2\app\components\sidebar.py")
c = p.read_text("utf-8")

# Fix 1: Add border to drawer for dark mode visibility
c = c.replace(
    "\"bg-white dark:bg-slate-900 w-64 dark:text-slate-200\"",
    "\"bg-white dark:bg-slate-900 w-64 dark:text-slate-200 border-r border-slate-200 dark:border-slate-700\""
)

# Fix 2: Add dark: separator styling
c = c.replace(
    'ui.separator().classes("mb-2")',
    'ui.separator().classes("mb-2 dark:bg-slate-700")'
)
c = c.replace(
    'ui.separator().classes("my-2")',
    'ui.separator().classes("my-2 dark:bg-slate-700")'
)

# Fix 3: Improve active link styling for dark mode
c = c.replace(
    'bg = "bg-teal-50 dark:bg-teal-900/30" if is_active else ""',
    'bg = "bg-teal-50 dark:bg-teal-900/40" if is_active else "hover:bg-slate-100 dark:hover:bg-slate-800"'
)

# Fix 4: Add link hover effect
c = c.replace(
    '.classes(f"no-underline {bg} mx-2 rounded-lg")',
    '.classes(f"no-underline {bg} mx-2 rounded-lg transition-colors duration-150")'
)

# Fix 5: Improve theme toggle label visibility in dark mode
c = c.replace(
    'ui.label(label_text).classes("text-xs text-slate-500 dark:text-slate-400")',
    'ui.label(label_text).classes("text-xs text-slate-500 dark:text-slate-300")'
)

# Fix 6: Add dark mode styling for language toggle inactive button
c = c.replace(
    '"flat round size=sm color=teal-7" if lang == "zh" else "flat round size=sm"',
    '"flat round size=sm color=teal-7" if lang == "zh" else "flat round size=sm text-slate-500 dark:text-slate-400"'
)
c = c.replace(
    '"flat round size=sm color=teal-7" if lang == "en" else "flat round size=sm"',
    '"flat round size=sm color=teal-7" if lang == "en" else "flat round size=sm text-slate-500 dark:text-slate-400"'
)

# Fix 7: Fix brand icon color in dark mode (was already dark:text-teal-400, keep)
# Fix 8: Fix brand label in dark mode (was already dark:text-teal-400, keep)

p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("sidebar.py: Full dark mode synchronization - OK")
print(f"  dark: classes: {c.count('dark:')}")

# ===== STEP 2: Update toggle_theme to properly refresh sidebar =====
p2 = pathlib.Path(r"D:\code_v2\app\theme.py")
c2 = p2.read_text("utf-8")

# Enhance toggle_theme JavaScript to also refresh sidebar DOM classes
old_toggle = '''    ui.run_javascript(\"document.querySelectorAll('.q-drawer').forEach(d => { if(document.body.classList.contains('dark')) d.classList.add('dark-mode-drawer'); else d.classList.remove('dark-mode-drawer'); });\")'''

new_toggle = '''    ui.run_javascript(\"\"\"
        var isDark = document.body.classList.contains('dark');
        document.querySelectorAll('.q-drawer').forEach(function(d) {
            if (isDark) { d.classList.add('dark-mode-drawer'); }
            else { d.classList.remove('dark-mode-drawer'); }
        });
        // Also refresh Quasar components that might cache styles
        if (typeof window.QQuasar !== 'undefined') {
            window.QQuasar.dark.set(isDark);
        }
    \"\"\")'''

if old_toggle in c2:
    c2 = c2.replace(old_toggle, new_toggle)
    p2.write_text(c2, "utf-8")
    print("theme.py: Enhanced toggle_theme with Quasar dark mode refresh")
else:
    print("theme.py: toggle_theme pattern not updated (may already be enhanced)")

py_compile.compile(str(p2), doraise=True)
print("theme.py: OK")

# ===== STEP 3: Verify and run tests =====
import subprocess
r = subprocess.run(["python", "-m", "pytest", "tests/", "-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"\nTests: {'52/52' if '52 passed' in r.stdout + r.stderr else 'FAILED'}")

# Summary
print(f"\n=== SUMMARY ===")
print(f"sidebar.py: {c.count('dark:')} dark: classes (was 10)")
print(f"theme.py toggle_theme: {'enhanced' if 'QQuasar' in c2 else 'standard'}")
