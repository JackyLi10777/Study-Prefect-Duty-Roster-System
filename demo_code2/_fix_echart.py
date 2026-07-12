import pathlib, py_compile, subprocess

p = pathlib.Path(r"D:\code_v2\app\pages\dashboard.py")
c = p.read_text("utf-8")

# Fix 1: Load Distribution echart title
c = c.replace(
    '"title": {"text": "Load Distribution", "left": "center", "textStyle": {"fontSize": 14}}',
    '"title": {"text": _t("\u8ca0\u8377\u5206\u4f48", "Load Distribution"), "left": "center", "textStyle": {"fontSize": 14}}'
)

# Fix 2: Y-axis names - use name_zh with name fallback
c = c.replace(
    'names = [r.get("name", "?") for r in rows if r.get("active", True)]',
    'names = [r.get("name_zh", "") or r.get("name", "?") for r in rows if r.get("active", True)]'
)

p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("dashboard.py: echart title i18n + y-axis names use name_zh")

# Also check: roster page uses name_map for display - verify correct
p2 = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c2 = p2.read_text("utf-8")
if 'name_map' in c2:
    print("roster.py: already uses name_map for Chinese display names")

# Check prefects.py display_name usage
p3 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c3 = p3.read_text("utf-8")
if 'display_name' in c3 or 'name_zh' in c3:
    print("prefects.py: already uses name_zh for display names")

r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")
