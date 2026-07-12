import pathlib

# Fix theme.py toggle_theme to also refresh sidebar
p = pathlib.Path(r"D:\code_v2\app\theme.py")
c = p.read_text("utf-8")

old = """def toggle_theme():
    current = get_theme()
    new = "dark" if current == "light" else "light"
    app.storage.user[THEME_KEY] = new
    ui.run_javascript(f"document.body.classList.remove('{current}');document.body.classList.add('{new}');")"""

new = """def toggle_theme():
    current = get_theme()
    new = "dark" if current == "light" else "light"
    app.storage.user[THEME_KEY] = new
    ui.run_javascript(f"document.body.classList.remove('{current}');document.body.classList.add('{new}');")
    # Also refresh any drawers/sidebars to pick up dark: classes
    ui.run_javascript("""
        setTimeout(() => {
            const drawers = document.querySelectorAll('.q-drawer');
            drawers.forEach(d => {
                if (document.body.classList.contains('dark')) {
                    d.classList.add('dark-mode-drawer');
                } else {
                    d.classList.remove('dark-mode-drawer');
                }
            });
        }, 50);
    """)"""

if old in c:
    c = c.replace(old, new)
    p.write_text(c, "utf-8")
    print("Theme toggle enhanced with sidebar refresh")
else:
    print("WARNING: toggle_theme pattern not found")
    # Try with different indentation
    for line in c.split("\n"):
        if "toggle_theme" in line:
            print(f"  Found at: {line[:80]}")

# Fix sidebar.py to add dark mode CSS for drawer
p2 = pathlib.Path(r"D:\code_v2\app\components\sidebar.py")
c2 = p2.read_text("utf-8")

# Add dark mode drawer CSS
old_css = "bg-white dark:bg-slate-900 w-64"
new_css = "bg-white dark:bg-slate-900 w-64 dark-mode-drawer"
c2 = c2.replace(old_css, new_css)

p2.write_text(c2, "utf-8")
print("Sidebar dark mode class added")

# Fix audit.py - add more i18n labels
p3 = pathlib.Path(r"D:\code_v2\app\pages\audit.py")
c3 = p3.read_text("utf-8")

# Fix 1: Description text
c3 = c3.replace('"Track system actions: roster generation, leave adjustment, data imports."',
                 '_t("\u8ffd\u8e64\u7cfb\u7d71\u64cd\u4f5c\uff1a\u503c\u73ed\u8868\u751f\u6210\u3001\u8acb\u5047\u8abf\u6574\u3001\u6578\u64da\u532f\u5165\u3002", "Track system actions: roster generation, leave adjustment, data imports.")')

# Fix 2: Empty state
c3 = c3.replace('"No audit records yet"',
                 '_t("\u66ab\u7121\u5be9\u8a08\u8a18\u9304", "No audit records yet")')
c3 = c3.replace('"Records appear automatically after roster generation, leave adjustments, etc."',
                 '_t("\u503c\u73ed\u8868\u751f\u6210\u3001\u8acb\u5047\u8abf\u6574\u7b49\u64cd\u4f5c\u5f8c\u8a18\u9304\u6703\u81ea\u52d5\u51fa\u73fe\u3002", "Records appear automatically after roster generation, leave adjustments, etc.")')

# Fix 3: Table columns
c3 = c3.replace('"Time"', '_t("\u6642\u9593", "Time")')
c3 = c3.replace('"Action"', '_t("\u64cd\u4f5c", "Action")')
c3 = c3.replace('"Detail"', '_t("\u8a73\u60c5", "Detail")')

p3.write_text(c3, "utf-8")
print("Audit log i18n updated")
print("ALL FIXES DONE")
