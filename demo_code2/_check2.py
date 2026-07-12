import pathlib, re

print("=" * 60)
print("1. DESIGN SYSTEM PAGE")
print("=" * 60)
c = pathlib.Path(r"D:\code_v2\app\main.py").read_text("utf-8")
idx = c.find("def design_system_page")
code = c[idx:c.find("\n\n@", idx) if c.find("\n\n@", idx) > 0 else None]
# Show all ui.label and ui.button calls
labels = re.findall(r'ui\.label\(([^)]+)\)', code)
for l in labels:
    print(f"  label: {l[:120]}")
buttons = re.findall(r'ui\.button\(([^)]+)\)', code)
for b in buttons:
    print(f"  button: {b[:120]}")

print()
print("=" * 60)
print("2. PREFECTS - ROLE_CHOICES, buttons, title")
print("=" * 60)
c2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py").read_text("utf-8")
# ROLE_CHOICES
idx = c2.find("ROLE_CHOICES")
if idx > 0:
    print(c2[idx:idx+200])
# Title
for m in re.finditer(r'ui\.label\(_t\("([^"]+)",\s*"([^"]+)"\)', c2):
    if "Management" in m.group(2) or "管理" in m.group(1):
        print(f"  Title: {m.group(1)} / {m.group(2)}")
# Load Demo Data button
for m in re.finditer(r'ui\.button\(_t\("([^"]+)",\s*"([^"]+)"\)', c2):
    if "Demo" in m.group(2) or "Load" in m.group(2) or "示範" in m.group(1):
        print(f"  Demo button: {m.group(1)} / {m.group(2)}")
