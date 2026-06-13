# Mandatory verification after app.py modification - final static titles cleanup (global load)
import ast
import sys

print("=== Verify after app.py final low-priority static titles migration (global load) ===")

with open("app.py", "r", encoding="utf-8") as f:
    source = f.read()

try:
    ast.parse(source)
    print("✅ app.py AST parse successful")
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
    sys.exit(1)

if 'get_text("global_load_slider_subheader")' in source and 'get_text("global_load_slider_caption")' in source:
    print("✅ Global load static titles now use get_text keys")
else:
    print("❌ Expected get_text patterns not found")
    sys.exit(1)

print("✅ Verify passed for this app.py static title edit")
print("=== End verify ===")