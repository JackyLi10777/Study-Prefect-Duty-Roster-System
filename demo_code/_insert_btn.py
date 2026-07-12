path = r'D:\code v2\app\pages\roster.py'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# Find the Generate button line
target = '.props("color=teal-7").classes("rounded-lg font-semibold")\n\n        # ---- Roster Table'
if target in c:
    new_block = '.props("color=teal-7").classes("rounded-lg font-semibold")\n\n        # Export PDF button\n        def _export_pdf():\n            if not roster_rows:\n                ui.notify("Generate a roster first.", type="warning")\n                return\n            from utils.pdf import generate_roster_html\n            html_bytes = generate_roster_html(roster, prefects)\n            ui.download(html_bytes, "roster_" + str(roster.week_start) + ".html")\n\n        ui.button("Export PDF/HTML", icon="picture_as_pdf", on_click=_export_pdf) \\.props("outline color=teal-7").classes("rounded-lg font-semibold")\n\n        # ---- Roster Table'
    c = c.replace(target, new_block)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(c)
    print("PDF export button added")
else:
    print("Pattern not found - checking variants")
    if 'Generate Roster' in c:
        print("Found Generate Roster text")
    if '.props(\"color=teal-7\")' in c:
        print("Found color=teal-7")
