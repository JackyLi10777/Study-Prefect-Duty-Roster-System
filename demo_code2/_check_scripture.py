import pathlib

# Check scripture section (utf-8 safe)
c = pathlib.Path(r"D:\code_v2\app\pages\dashboard.py").read_text("utf-8")
idx = c.find("with ui.element(\"div\").classes(\"scripture-zone\"):")
end = c.find("ZONE 2:", idx)
print(c[idx:end])
print("\n=== Checking for duplicate scripture display ===")
# Count occurrences of "Daily Scripture" or "scripture" in the Python code
scripture_count = c.count("scripture-zone")
scripture_count2 = c.count("Daily Scripture")
print(f"'scripture-zone' occurrences: {scripture_count}")
print(f"'Daily Scripture' occurrences: {scripture_count2}")
# Also check if there are 2 verse rendering spots
verse_renders = c.count("verse[")
print(f"'verse[' accesses: {verse_renders}")
