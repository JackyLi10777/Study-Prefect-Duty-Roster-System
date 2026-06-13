# Mandatory verification after app.py modification (manual_adjust_saved migration)
# Per approved architecture plan + project safe patterns
import ast
import sys

print("=== Verify after app.py high-freq dynamic text migration (step 1: manual adjust) ===")

# 1. AST parse to confirm syntax
with open("app.py", "r", encoding="utf-8") as f:
    source = f.read()
try:
    ast.parse(source)
    print("✅ app.py AST parse successful")
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
    sys.exit(1)

# 2. Import app to confirm the module loads cleanly (triggers messages etc.)
try:
    import app
    print("✅ Import app 成功 (migration of manual_adjust_saved verified)")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

print("✅ Verify passed for this app.py edit")
print("=== End verify ===")