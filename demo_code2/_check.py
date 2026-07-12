import pathlib, re

# ROSTER.PY: Fix missing parens on lines 44-47
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c = p.read_text("utf-8")
lines = c.split("\n")

# Show the exact content around the problem
for i in range(43, 48):
    if i < len(lines):
        print(f"L{i+1}: {lines[i]}")

# Fix missing closing paren in KPI labels
fixes = [
    ('KpiCard(str(active), _t("\u6d3b\u8e8d\u98a8\u7d00", "Active Prefects"), gradient=True)',
     'KpiCard(str(active), _t("\u6d3b\u8e8d\u98a8\u7d00", "Active Prefects"), gradient=True)'),
]
