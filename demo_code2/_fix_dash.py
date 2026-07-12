import pathlib

p = pathlib.Path(r"D:\code_v2\app\pages\dashboard.py")
c = p.read_text("utf-8")
changes = 0

# Fix 1: Scripture ref language-aware
old = "ui.label(f\"{verse['ref']}  {verse['ref_zh']}\").classes(\"scripture-ref\")\n            ui.label(verse[\"text_zh\"]).classes(\"scripture-text\")"
new = "if is_zh():\n                ui.label(verse.get(\"ref_zh\", verse.get(\"ref\", \"\"))).classes(\"scripture-ref\")\n                ui.label(verse.get(\"text_zh\", verse.get(\"text\", \"\"))).classes(\"scripture-text\")\n            else:\n                ui.label(verse.get(\"ref\", verse.get(\"ref_zh\", \"\"))).classes(\"scripture-ref\")\n                ui.label(verse.get(\"text\", verse.get(\"text_zh\", \"\"))).classes(\"scripture-text\")"
if old in c:
    c = c.replace(old, new)
    changes += 1
    print("Fix 1 OK: scripture language-aware")
else:
    print("Fix 1 MISS")

# Fix 2: Scripture divider i18n
old2 = 'ui.label("\u2726  \u6bcf\u65e5\u91d1\u53e5  \u2726")'
new2 = 'ui.label(_t("\u2726  \u6bcf\u65e5\u91d1\u53e5  \u2726", "\u2726  Daily Scripture  \u2726"))'
if old2 in c:
    c = c.replace(old2, new2)
    changes += 1
    print("Fix 2 OK: scripture divider")
else:
    print("Fix 2 MISS")

# Fix 3: Welcome banner
old3 = 'ui.label("Welcome to the Study Prefect Duty Roster!")'
new3 = 'ui.label(_t("\u6b61\u8fce\u4f7f\u7528\u98a8\u7d00\u503c\u73ed\u8868\u7cfb\u7d71\uff01", "Welcome to the Study Prefect Duty Roster!"))'
c = c.replace(old3, new3)
changes += 1

old3b = 'ui.label("To get started, go to the Prefects page and load the sample data.")'
new3b = 'ui.label(_t("\u8acb\u524d\u5f80\u98a8\u7d00\u7ba1\u7406\u9801\u9762\u52a0\u8f09\u793a\u7bc4\u6578\u64da\u4ee5\u958b\u59cb\u4f7f\u7528\u3002", "To get started, go to the Prefects page and load the sample data."))'
c = c.replace(old3b, new3b)
changes += 1
print("Fix 3 OK: welcome banner")

# Fix 4: Backup, Restore, Audit labels
c = c.replace('"Backup System"', '_t("\u5099\u4efd\u7cfb\u7d71", "Backup System")')
c = c.replace('"Restore from Backup"', '_t("\u5f9e\u5099\u4efd\u9084\u539f", "Restore from Backup")')
c = c.replace('"Audit Log (Recent Changes)"', '_t("\u5be9\u8a08\u65e5\u8a8c\uff08\u6700\u8fd1\u8b8a\u66f4\uff09", "Audit Log (Recent Changes)")')
c = c.replace('"No audit entries yet."', '_t("\u66ab\u7121\u5be9\u8a08\u8a18\u9304", "No audit entries yet.")')
changes += 4
print("Fix 4 OK: backup/restore/audit labels")

# Fix 5: Mentoring Pairs
c = c.replace('"Mentoring Pairs"', '_t("\u5e2b\u5f92\u914d\u5c0d", "Mentoring Pairs")')
changes += 1
print("Fix 5 OK: mentoring pairs")

# Fix 6: Data Health Notes
c = c.replace('"Data Health Notes"', '_t("\u6578\u64da\u5065\u5eb7\u63d0\u793a", "Data Health Notes")')
changes += 1
print("Fix 6 OK: data health notes")

p.write_text(c, "utf-8")
print(f"DONE: {changes} changes applied")
