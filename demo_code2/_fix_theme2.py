import pathlib

# Fix theme.py toggle_theme
p = pathlib.Path(r"D:\code_v2\app\theme.py")
c = p.read_text("utf-8")

old_toggle = "def toggle_theme():\n    current = get_theme()\n    new = \"dark\" if current == \"light\" else \"light\"\n    app.storage.user[THEME_KEY] = new\n    ui.run_javascript(f\"document.body.classList.remove('{current}');document.body.classList.add('{new}');\")"

new_toggle = """def toggle_theme():
    current = get_theme()
    new = "dark" if current == "light" else "light"
    app.storage.user[THEME_KEY] = new
    ui.run_javascript(f"document.body.classList.remove('{current}');document.body.classList.add('{new}');")
    # Refresh drawers to pick up dark: Tailwind classes
    ui.run_javascript("document.querySelectorAll('.q-drawer').forEach(d => { if(document.body.classList.contains('dark')) d.classList.add('dark-mode-drawer'); else d.classList.remove('dark-mode-drawer'); });")"""

if old_toggle in c:
    c = c.replace(old_toggle, new_toggle)
    p.write_text(c, "utf-8")
    print("Theme toggle enhanced")
else:
    print("WARNING: toggle_theme pattern not found")
    # Find the function
    idx = c.find("def toggle_theme():")
    if idx >= 0:
        end_idx = c.find("\ndef ", idx + 20)
        print(f"Found at {idx}, ends at {end_idx}")
        print(c[idx:idx+200])
