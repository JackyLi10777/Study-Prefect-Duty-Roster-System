import ast
import sys
print("=== Second app.py verification (HELP_TEXT migration to messages) ===")
try:
    with open("app.py", "r", encoding="utf-8") as f:
        src = f.read()
    ast.parse(src)
    print("✅ AST OK")
    import app
    print("✅ import app 成功")
    from roster.ui.i18n import get_text
    print("get_text help full starts with:", get_text("help_text_full")[:60], "...")
except Exception as e:
    print("❌ ", type(e).__name__, str(e)[:150])
    sys.exit(1)
print("=== OK (display layer, no backup impact) ===")
