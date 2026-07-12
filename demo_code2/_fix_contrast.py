import pathlib, py_compile

# 1. theme.py: TEXT_SECONDARY contrast boost + dark Chinese font-weight
p = pathlib.Path(r"D:\code_v2\app\theme.py")
c = p.read_text("utf-8")
c = c.replace("TEXT_SECONDARY = \"#94A3B8\"", "TEXT_SECONDARY = \"#CBD5E1\"")
old = "body.dark .shadow-sm {{ box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3); }}"
new = """body.dark .shadow-sm {{ box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3); }}

        /* Dark mode: Chinese text legibility (WCAG AA) */
        body.dark .text-body, body.dark table, body.dark .card, body.dark .q-card {{
            font-weight: 450;
        }}"""
c = c.replace(old, new)
p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("theme.py: TEXT_SECONDARY=#CBD5E1 + dark Chinese font-weight 450")

# 2. theme/css.py: ensure dark font-weight
p2 = pathlib.Path(r"D:\code_v2\app\theme\css.py")
c2 = p2.read_text("utf-8")
if "font-weight: 450" not in c2:
    c2 = c2.replace(
        "body.dark .text-body, body.dark .q-table td, body.dark .q-card {{ font-weight: 450; }}",
        "body.dark .text-body, body.dark .q-table td, body.dark .q-card {{ font-weight: 450; }}"
    )
    # Check if it already exists - if not, add after body.dark section
    if "font-weight: 450" not in c2:
        # Add to the dark mode adaptations section
        dark_section = "body.dark .q-card {{"
        c2 = c2.replace(dark_section, 
            "body.dark .text-body, body.dark .q-table td, body.dark .q-card {{ font-weight: 450; }}\n        " + dark_section)
    p2.write_text(c2, "utf-8")
    print("theme/css.py: added dark font-weight 450")
else:
    print("theme/css.py: dark font-weight already present")
py_compile.compile(str(p2), doraise=True)
print("theme/css.py OK")

# Verify
print()
print("TEXT_SECONDARY:", "CBD5E1" in p.read_text("utf-8"))
print("font-weight 450 in theme.py:", "font-weight: 450" in p.read_text("utf-8"))
print("font-weight 450 in css.py:", "font-weight: 450" in p2.read_text("utf-8"))
