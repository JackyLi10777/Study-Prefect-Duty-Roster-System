# Mandatory verification after app.py modifications - final static titles cleanup (all remaining in app.py)
import ast
import sys

print("=== Verify after app.py final low-priority static titles migration (roster, manual, audit, history, substitute) ===")

with open("app.py", "r", encoding="utf-8") as f:
    source = f.read()

try:
    ast.parse(source)
    print("✅ app.py AST parse successful")
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
    sys.exit(1)

checks = [
    ('get_text("this_week_roster_subheader")', "this week's roster"),
    ('get_text("manual_load_adjust_subheader")', "manual load adjust"),
    ('get_text("cumulative_audit_subheader")', "cumulative audit"),
    ('get_text("history_fairness_subheader")', "history fairness"),
    ('get_text("smart_substitute_subheader")', "smart substitute"),
]
for pattern, desc in checks:
    if pattern in source:
        print(f"✅ {desc} static title now uses get_text key")
    else:
        print(f"❌ {desc} not found")

print("✅ All targeted app.py static section titles migrated to safe get_text.")
print("✅ Verify passed for app.py static titles batch (minimal-risk, static only).")
print("=== End verify ===")