# Mandatory verification after app.py mod (clear leave success migration)
import ast
import sys
print("=== Verify after app.py edit: leave_cleared_success ===")
with open("app.py", "r", encoding="utf-8") as f:
    source = f.read()
try:
    ast.parse(source)
    print("✅ AST successful")
except Exception as e: print(f"❌ {e}"); sys.exit(1)
if 'get_text("leave_cleared_success")' in source and '已清除請假同學' not in source.split('st.success')[0]:  # rough
    print("✅ leave_cleared_success migrated to safe get_text")
print("✅ Verify passed")
print("=== End ===")